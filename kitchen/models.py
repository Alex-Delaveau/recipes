from django.db import models
from django_scopes import ScopedManager

from cookbook.models import Food, Space, Supermarket, SupermarketCategory


class KitchenSpace(models.Model):
    """Fork settings of a space: the generic aisle order (a regular upstream Supermarket, selected by default)."""
    space = models.OneToOneField(Space, on_delete=models.CASCADE, related_name='kitchen')
    generic_supermarket = models.ForeignKey(Supermarket, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    objects = ScopedManager(space='space')


class KitchenFood(models.Model):
    """
    Fork state of a food: the aisle suggested when it was created and whether the user confirmed it
    (unconfirmed foods form the "to sort" queue), and whether it is a family (first level of the 2-level tree).
    """
    SOURCE_PARENT = 'parent'
    SOURCE_DICTIONARY = 'dictionary'
    SOURCE_SIMILAR = 'similar'
    SOURCE_NONE = 'none'
    SOURCE_USER = 'user'
    SOURCES = ((SOURCE_PARENT, 'parent'), (SOURCE_DICTIONARY, 'dictionary'), (SOURCE_SIMILAR, 'similar'), (SOURCE_NONE, 'none'),
               (SOURCE_USER, 'user'))

    food = models.OneToOneField(Food, on_delete=models.CASCADE, related_name='kitchen')
    is_family = models.BooleanField(default=False)
    aisle_source = models.CharField(max_length=16, choices=SOURCES, default=SOURCE_NONE)
    aisle_confirmed = models.BooleanField(default=False)
    space = models.ForeignKey(Space, on_delete=models.CASCADE)

    objects = ScopedManager(space='space')


class NotDuplicate(models.Model):
    """Pair of foods the user marked as "not a duplicate": the duplicates screen no longer proposes it."""
    food_a = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='+')
    food_b = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='+')
    space = models.ForeignKey(Space, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ScopedManager(space='space')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['food_a', 'food_b'], name='kitchen_not_duplicate_unique_pair')]
