from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, F, IntegerField, Max, Q, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from treebeard.exceptions import InvalidMoveToDescendant, InvalidPosition, PathOverflow

from cookbook.helper.permission_helper import CustomIsGuest, CustomIsUser, CustomTokenHasReadWriteScope
from cookbook.helper.recipe_search import RecipeSearch
from cookbook.helper.ingredient_parser import IngredientParser
from cookbook.models import Automation, Food, Recipe, SupermarketCategory, Unit
from kitchen import prices, services
from kitchen.models import KitchenFood
from cookbook.views.api import RecipePagination
from kitchen.serializers import KitchenRecipeSerializer

KITCHEN_PARAMS = ('have', 'max_time', 'sort')
SORTS = ('recent', 'forgotten', 'random')


def _int_list(values):
    return [int(v) for v in values if str(v).isdigit()]


@extend_schema(parameters=[
    OpenApiParameter(name='query', type=str),
    OpenApiParameter(name='keywords', type=int, many=True),
    OpenApiParameter(name='have', type=int, many=True, description='Foods on hand: recipes using the most of them come first'),
    OpenApiParameter(name='max_time', type=int, description='Maximum total time (working + waiting) in minutes'),
    OpenApiParameter(name='sort', type=OpenApiTypes.STR, enum=SORTS),
])
class KitchenRecipeListView(generics.ListAPIView):
    """
    Home screen search of the fork (journey P1). Wraps the upstream RecipeSearch (text, keywords...) and adds what it
    lacks without touching it: ranking by foods on hand (no stock involved), a total time limit and the
    "recent" / "not cooked for a long time" / "random" shortcuts.
    """
    serializer_class = KitchenRecipeSerializer
    permission_classes = [CustomIsGuest & CustomTokenHasReadWriteScope]
    pagination_class = RecipePagination

    def get_queryset(self):
        request = self.request
        user, space = request.user, request.space
        queryset = Recipe.objects.filter(space=space).filter(
            Q(private=False) | (Q(private=True) & (Q(created_by=user) | Q(shared=user))))

        params = {k: request.GET.get(k) if len(request.GET.getlist(k)) == 1 else request.GET.getlist(k)
                  for k in request.GET if k not in KITCHEN_PARAMS}
        queryset = RecipeSearch(request, **params).get_queryset(queryset)
        ordering = list(queryset.query.order_by)

        max_time = request.GET.get('max_time')
        if max_time and max_time.isdigit():
            queryset = queryset.annotate(
                fork_total_time=Coalesce('working_time', Value(0)) + Coalesce('waiting_time', Value(0))
            ).filter(fork_total_time__gt=0, fork_total_time__lte=int(max_time))  # no time given: unknown, not "quick"

        queryset = queryset.with_last_cooked(user, space)

        have = _int_list(request.GET.getlist('have'))
        if have:
            foods = Food.include_descendants(Food.objects.filter(space=space, id__in=have))
            queryset = queryset.annotate(
                matched_foods=Count('steps__ingredients__food', filter=Q(steps__ingredients__food__in=foods),
                                    distinct=True, output_field=IntegerField()),
                total_foods=Count('steps__ingredients__food', distinct=True, output_field=IntegerField()),
            ).filter(matched_foods__gt=0)
            ordering = ['-matched_foods', 'total_foods'] + ordering

        sort = request.GET.get('sort')
        if sort == 'random':
            ordering = ['?']
        elif sort == 'recent':
            queryset = queryset.with_last_viewed(user, space).filter(lastviewed__isnull=False)
            ordering = [F('lastviewed').desc()]
        elif sort == 'forgotten':
            # never cooked first, then the longest ago; by anyone of the space (the household cooks for everyone),
            # where upstream's "lastcooked" only counts the current user
            queryset = queryset.annotate(fork_last_cooked=Max('cooklog__created_at', filter=Q(cooklog__space=space)))
            ordering = [F('fork_last_cooked').asc(nulls_first=True), 'name']

        return queryset.order_by(*ordering).prefetch_related('keywords', 'created_by')


# ------------------------------------------------------------------------- food organisation (M3)

class KitchenUserMixin:
    permission_classes = [CustomIsUser & CustomTokenHasReadWriteScope]


def _food_or_404(request, pk):
    return get_object_or_404(Food, pk=pk, space=request.space)


def _category_or_none(request, value):
    if value in (None, '', 0):
        return None
    if not str(value).isdigit():
        raise ValidationError({'category': 'must be a category id'})
    return get_object_or_404(SupermarketCategory, pk=int(value), space=request.space)


def _food_dict(food, states):
    state = states.get(food.id)
    root_path = food.path[:Food.steplen]
    return {
        'id': food.id, 'name': food.name, 'plural_name': food.plural_name, 'depth': food.depth, 'numchild': food.numchild,
        'root_path': root_path, 'path': food.path,
        'category': {'id': food.supermarket_category_id, 'name': food.supermarket_category.name} if food.supermarket_category_id else None,
        'ignore_shopping': food.ignore_shopping,
        'is_family': food.depth == 1 and (food.numchild > 0 or bool(state and state.is_family)),
        'aisle_confirmed': state.aisle_confirmed if state else food.supermarket_category_id is not None,
    }


class KitchenFoodListView(KitchenUserMixin, APIView):
    """All foods of the space with what the 2-level tree screen needs (the screen builds the tree)."""

    def get(self, request):
        services.ensure_setup(request.space)
        foods = list(Food.objects.filter(space=request.space).select_related('supermarket_category', 'properties_food_unit').order_by('path'))
        states = {s.food_id: s for s in KitchenFood.objects.filter(space=request.space)}
        by_path = {f.path: f.id for f in foods if f.depth == 1}
        book = prices.PriceBook(request.space, foods)
        data = []
        for f in foods:
            d = _food_dict(f, states)
            d['price'] = book.display(f)
            d['family'] = by_path.get(d.pop('root_path')) if f.depth > 1 else None
            d.pop('path')
            data.append(d)
        return Response({'foods': data, 'to_sort': services.to_sort_queryset(request.space).count(),
                         'names_to_fix': len(services.names_to_fix(request.space)),
                         'no_price': prices.missing_queryset(request.space).count()})


class KitchenFoodMoveView(KitchenUserMixin, APIView):
    """Move a food into a family (it takes the family's aisle) or back to the top level (family: null)."""

    def post(self, request, pk):
        food = _food_or_404(request, pk)
        family_id = request.data.get('family')
        family = _food_or_404(request, family_id) if family_id else None
        try:
            services.move_to_family(food, family)
        except (ValueError, InvalidMoveToDescendant, InvalidPosition, PathOverflow):
            return Response({'error': True, 'msg': 'invalid move'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'id': food.id, 'family': family.id if family else None,
                         'category': food.supermarket_category_id})


class KitchenFoodAisleView(KitchenUserMixin, APIView):
    """Set or confirm the aisle of a food (one tap). Families pass it on to their members."""

    def post(self, request, pk):
        food = _food_or_404(request, pk)
        category = _category_or_none(request, request.data.get('category'))
        services.set_food_aisle(food, category)
        return Response({'id': food.id, 'category': category.id if category else None, 'to_sort': services.to_sort_queryset(request.space).count()})


class KitchenFoodFamilyView(KitchenUserMixin, APIView):
    """Mark a top-level food as a family (so an empty family stays a family)."""

    def post(self, request, pk):
        food = _food_or_404(request, pk)
        if food.depth != 1:
            return Response({'error': True, 'msg': 'only top level foods can be families'}, status=status.HTTP_400_BAD_REQUEST)
        state = services.kitchen_food(food)
        state.is_family = bool(request.data.get('is_family', True))
        state.save()
        return Response({'id': food.id, 'is_family': state.is_family})


class KitchenToSortView(KitchenUserMixin, APIView):
    """The "to sort" queue: foods whose suggested aisle is not confirmed yet."""

    def get(self, request):
        services.ensure_setup(request.space)
        queryset = services.to_sort_queryset(request.space).select_related('supermarket_category')
        states = {s.food_id: s for s in KitchenFood.objects.filter(space=request.space, food__in=queryset)}
        foods = list(queryset[:200])
        counts = services.usage_counts([f.id for f in foods])
        results = []
        for food in foods:
            state = states.get(food.id)
            results.append({'id': food.id, 'name': food.name, 'recipes': counts[food.id][0], 'shopping': counts[food.id][1],
                            'children': food.numchild,
                            'suggested': {'id': food.supermarket_category_id, 'name': food.supermarket_category.name} if food.supermarket_category_id else None,
                            'source': state.aisle_source if state else KitchenFood.SOURCE_NONE})
        return Response({'count': queryset.count(), 'results': results})


class KitchenFoodNamesView(KitchenUserMixin, APIView):
    """Food names to fix (left over by imports), with the proposed new name or the food to merge into."""

    def get(self, request):
        results = services.names_to_fix(request.space)
        return Response({'count': len(results), 'results': results})


class KitchenFoodKeepNameView(KitchenUserMixin, APIView):
    """Keep the current name of a food: it leaves the "names to fix" list."""

    def post(self, request, pk):
        services.keep_food_name(_food_or_404(request, pk))
        return Response({'id': pk})


class KitchenFoodDeleteView(KitchenUserMixin, APIView):
    """Delete a food that no recipe uses and that is not a family (checked at delete time); 409 otherwise."""

    def post(self, request, pk):
        reason = services.delete_unused_food(_food_or_404(request, pk))
        if reason:
            return Response({'error': True, 'reason': reason}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class KitchenAislesView(KitchenUserMixin, APIView):
    """Aisles in the generic order (GET) and new order (PUT {order: [category ids]})."""

    def _payload(self, request, aisles):
        # order_by(): Food's default ordering (name) would otherwise end up in the GROUP BY and count 1 per food
        counts = dict(Food.objects.filter(space=request.space).order_by().values('supermarket_category').annotate(n=Count('id'))
                      .values_list('supermarket_category', 'n'))
        kitchen = services.ensure_setup(request.space)
        return Response({'supermarket': kitchen.generic_supermarket_id,
                         'aisles': [{'id': c.id, 'name': c.name, 'foods': counts.get(c.id, 0)} for c in aisles]})

    def get(self, request):
        return self._payload(request, services.ordered_aisles(request.space))

    def put(self, request):
        order = request.data.get('order')
        if not isinstance(order, list):
            return Response({'error': True, 'msg': 'order must be a list of category ids'}, status=status.HTTP_400_BAD_REQUEST)
        return self._payload(request, services.set_aisle_order(request.space, [int(i) for i in order if str(i).isdigit()]))


class KitchenDuplicatesView(KitchenUserMixin, APIView):
    """Probable duplicates, with the number of recipes and shopping entries a merge would move."""

    def get(self, request):
        return Response({'results': services.find_duplicates(request.space)})


class KitchenDuplicateDismissView(KitchenUserMixin, APIView):
    """{a, b}: the pair is not a duplicate, never propose it again."""

    def post(self, request):
        a, b = _food_or_404(request, request.data.get('a')), _food_or_404(request, request.data.get('b'))
        services.dismiss_duplicate(request.space, a.id, b.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class KitchenFoodMatchView(KitchenUserMixin, APIView):
    """
    Import review: for each food name, whether a food with this name (or plural) exists, otherwise the closest existing
    food. {names: [...]} -> {results: {name: {exists, closest}}}
    """

    def post(self, request):
        names = request.data.get('names')
        if not isinstance(names, list):
            return Response({'error': True, 'msg': 'names must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        results = {}
        for name in [str(n) for n in names[:200]]:
            clean = name.strip()
            exists = Food.objects.filter(space=request.space).filter(Q(name__iexact=clean) | Q(plural_name__iexact=clean)).exists()
            alias = Automation.objects.filter(space=request.space, type=Automation.FOOD_ALIAS, disabled=False, param_1__iexact=clean).exists()
            results[name] = {'exists': exists or alias, 'closest': None if (exists or alias) else services.closest_food(request.space, clean)}
        return Response({'results': results})


# ------------------------------------------------------------------------- recipe wizard (M4)

class KitchenRecipeImageView(KitchenUserMixin, APIView):
    """
    Crop a recipe photo: {crop: {x, y, w, h} as fractions, image_url?}. With `image_url` (an import) the photo is
    downloaded like upstream's image endpoint does, else the recipe's current photo is cropped.
    """

    def put(self, request, pk):
        from kitchen import images
        user = request.user
        recipe = get_object_or_404(Recipe.objects.filter(space=request.space).filter(
            Q(private=False) | Q(created_by=user) | Q(shared=user)).distinct(), pk=pk)
        image_url = request.data.get('image_url') or None
        try:
            crop = images.parse_crop(request.data.get('crop') or {})
            url = images.save_cropped(recipe, image_url, crop)
        except images.CropError as e:
            return Response({'error': True, 'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'error': True, 'msg': 'the photo could not be fetched'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'id': recipe.id, 'image': url})


class KitchenParseView(KitchenUserMixin, APIView):
    """
    Live recognition for the recipe wizard: {lines: [...]} -> {results: [{original, amount, unit, food, note, food_id,
    unit_id, error}]}. Uses the upstream parser (with the fork's French reading) but, unlike /api/ingredient-parser/,
    creates no food or unit: they are created when the recipe is saved.
    """

    def post(self, request):
        lines = request.data.get('lines') if isinstance(request.data, dict) else None
        if not isinstance(lines, list):
            return Response({'error': True, 'msg': 'lines must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        parser = IngredientParser(request, cache_mode=True)
        results = []
        for line in [str(x) for x in lines[:200]]:
            item = {'original': line, 'amount': 0, 'unit': None, 'food': None, 'note': '', 'food_id': None, 'unit_id': None, 'error': False}
            if line.strip():
                try:
                    amount, unit, food, note = parser.parse(line)
                    item.update({'amount': amount, 'unit': unit, 'food': food, 'note': note})
                    item['food_id'] = Food.objects.filter(space=request.space).filter(Q(name__iexact=food) | Q(plural_name__iexact=food)).values_list('id', flat=True).first()
                    if unit:
                        item['unit_id'] = Unit.objects.filter(space=request.space).filter(Q(name__iexact=unit) | Q(plural_name__iexact=unit)).values_list('id', flat=True).first()
                except ValueError:
                    item.update({'food': line.strip()[:128], 'error': True})
            results.append(item)
        return Response({'results': results})


# ------------------------------------------------------------------------- price estimate (M7)

# prices, weights and packages above this are typing errors (and beyond the database columns)
MAX_NUMBER = Decimal(10) ** 7


def _decimal_or_none(data, key, positive=True):
    value = data.get(key)
    if value in (None, ''):
        return None
    try:
        number = Decimal(str(value).replace(',', '.'))
    except InvalidOperation:
        raise ValidationError({key: 'must be a number'})
    if not number.is_finite() or number >= MAX_NUMBER:
        raise ValidationError({key: 'must be a number'})
    if number < 0 or (positive and number == 0):
        raise ValidationError({key: 'must be positive'})
    return number


def _price_payload(food):
    """What the food sheet shows and edits: price per kg / l / piece, package, weight of a piece, dictionary price."""
    book = prices.PriceBook(food.space, [food])
    state = book.state(food)
    package = None
    if state and state.package_amount and state.package_kind:
        package = {'amount': float(state.package_amount), 'kind': state.package_kind,
                   'price': float(state.package_price) if state.package_price else None}
    return {'id': food.id, 'name': food.name, 'price': book.display(food), 'package': package,
            'piece_weight': float(state.piece_weight) if state and state.piece_weight else None,
            'suggestion': prices.suggestion(food)}


def _visible_recipes(request):
    return Recipe.objects.filter(space=request.space).filter(
        Q(private=False) | Q(created_by=request.user) | Q(shared=request.user)).distinct()


class KitchenFoodPriceView(KitchenUserMixin, APIView):
    """
    Price of a food (GET) and new price (PUT {price, per: kg|l|piece, package_amount, package_kind: g|ml|piece,
    package_price, piece_weight}): a price set here is confirmed. price null removes it. {suggest: true} stores the
    dictionary price, as estimated.
    """

    def get(self, request, pk):
        return Response(_price_payload(_food_or_404(request, pk)))

    def put(self, request, pk):
        food = _food_or_404(request, pk)
        data = request.data
        if data.get('suggest'):
            reason = prices.apply_suggestion(food)
            if reason:
                return Response({'error': True, 'reason': reason}, status=status.HTTP_400_BAD_REQUEST)
            food.refresh_from_db()
            return Response(_price_payload(food))
        try:
            with transaction.atomic():
                self._update(food, data)
        except prices.PriceError as e:
            # nothing saved: the package or weight typed with a refused price is not kept half way
            return Response({'error': True, 'reason': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        food.refresh_from_db()
        return Response(_price_payload(food))

    @staticmethod
    def _update(food, data):
        state = services.kitchen_food(food)
        if 'piece_weight' in data:
            state.piece_weight = _decimal_or_none(data, 'piece_weight')
        if 'package_amount' in data or 'package_price' in data:
            amount = _decimal_or_none(data, 'package_amount')
            kind = data.get('package_kind') or ''
            if amount is not None and kind not in dict(KitchenFood.KINDS):
                raise ValidationError({'package_kind': 'must be g, ml or piece'})
            state.package_amount = amount
            state.package_kind = kind if amount is not None else ''
            state.package_price = _decimal_or_none(data, 'package_price') if amount is not None else None
        state.save()
        if 'price' in data:
            prices.set_food_price(food, _decimal_or_none(data, 'price', positive=False), data.get('per') or 'kg')


class KitchenPriceMissingView(KitchenUserMixin, APIView):
    """The "foods without a price" queue: bought foods without a price, the most used first, with the dictionary price."""

    def get(self, request):
        queryset = prices.missing_queryset(request.space)
        foods = list(queryset[:200])
        counts = services.usage_counts([f.id for f in foods])
        results = [{'id': f.id, 'name': f.name, 'recipes': counts[f.id][0], 'shopping': counts[f.id][1],
                    'suggestion': prices.suggestion(f)} for f in foods]
        return Response({'count': queryset.count(), 'suggested': sum(1 for r in results if r['suggestion']), 'results': results})

    def post(self, request):
        """Store every dictionary price at once (as estimated)."""
        applied = prices.apply_all_suggestions(request.space)
        return Response({'applied': applied, 'count': prices.missing_queryset(request.space).count()})


class KitchenPriceRecipesView(KitchenUserMixin, APIView):
    """{recipes: [{id, servings?}]} -> {total, recipes: [{id, total, per_serving, servings, missing}], missing}."""

    def post(self, request):
        asked = request.data.get('recipes') if isinstance(request.data, dict) else None
        if not isinstance(asked, list):
            return Response({'error': True, 'msg': 'recipes must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        ids = _int_list([r.get('id') for r in asked[:50] if isinstance(r, dict)])
        recipes = {r.id: r for r in _visible_recipes(request).filter(id__in=ids)}
        requests = []
        for r in asked[:50]:
            recipe = recipes.get(int(r.get('id'))) if isinstance(r, dict) and str(r.get('id')).isdigit() else None
            if recipe is not None:
                servings = _decimal_or_none(r, 'servings')
                requests.append((recipe, servings))
        return Response(prices.estimate_recipes(request.space, requests))


def _entry_ids(request, key='entries'):
    ids = request.data.get(key) if isinstance(request.data, dict) else None
    if not isinstance(ids, list):
        raise ValidationError({key: 'must be a list of shopping entry ids'})
    return _int_list(ids)[:1000]


class KitchenPriceShoppingView(KitchenUserMixin, APIView):
    """{entries: [ids]} -> estimate of these shopping entries: {total, checked_total, items, missing}."""

    def post(self, request):
        entries = prices.entries_for(request.space, _entry_ids(request))
        return Response(prices.public(prices.estimate_entries(request.space, entries)))


class KitchenPriceAdjustView(KitchenUserMixin, APIView):
    """
    After shopping: {entries: [checked ids], paid, apply} -> comparison of what was paid and what was estimated, and
    (apply: true) the estimated prices of these entries moved towards it. Confirmed prices never move.
    """

    def post(self, request):
        paid = _decimal_or_none(request.data, 'paid')
        if paid is None:
            raise ValidationError({'paid': 'required'})
        entries = prices.entries_for(request.space, _entry_ids(request))
        return Response(prices.adjust_after_shopping(request.space, entries, paid, apply=bool(request.data.get('apply'))))


class KitchenPriceCorrectView(KitchenUserMixin, APIView):
    """One item of the shopping list: {food, entries: [ids], paid} -> the food's price becomes what was paid, confirmed."""

    def post(self, request):
        food = _food_or_404(request, request.data.get('food'))
        paid = _decimal_or_none(request.data, 'paid')
        if paid is None:
            raise ValidationError({'paid': 'required'})
        entries = [e for e in prices.entries_for(request.space, _entry_ids(request)) if e.food_id == food.id]
        try:
            prices.correct_item(request.space, food, entries, paid)
        except prices.PriceError as e:
            return Response({'error': True, 'reason': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        food.refresh_from_db()
        return Response(_price_payload(food))
