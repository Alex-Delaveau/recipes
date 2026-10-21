from django.db.models import Count, F, IntegerField, Q, Value
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
from kitchen import services
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
            ).filter(fork_total_time__lte=int(max_time))

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
            # never cooked first, then the longest ago
            ordering = [F('lastcooked').asc(nulls_first=True), 'name']

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
        foods = list(Food.objects.filter(space=request.space).select_related('supermarket_category').order_by('path'))
        states = {s.food_id: s for s in KitchenFood.objects.filter(space=request.space)}
        by_path = {f.path: f.id for f in foods if f.depth == 1}
        data = []
        for f in foods:
            d = _food_dict(f, states)
            d['family'] = by_path.get(d.pop('root_path')) if f.depth > 1 else None
            d.pop('path')
            data.append(d)
        return Response({'foods': data, 'to_sort': services.to_sort_queryset(request.space).count(),
                         'names_to_fix': len(services.names_to_fix(request.space))})


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
                            'suggested': {'id': food.supermarket_category_id, 'name': food.supermarket_category.name} if food.supermarket_category_id else None,
                            'source': state.aisle_source if state else KitchenFood.SOURCE_NONE})
        return Response({'count': queryset.count(), 'results': results})


class KitchenFoodNamesView(KitchenUserMixin, APIView):
    """Food names to fix (left over by imports), with the proposed new name or the food to merge into."""

    def get(self, request):
        results = services.names_to_fix(request.space)
        return Response({'count': len(results), 'results': results})


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
