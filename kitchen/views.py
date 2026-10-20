from django.db.models import Count, F, IntegerField, Q, Value
from django.db.models.functions import Coalesce
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics

from cookbook.helper.permission_helper import CustomIsGuest
from cookbook.helper.recipe_search import RecipeSearch
from cookbook.models import Food, Recipe
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
    permission_classes = [CustomIsGuest]
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
