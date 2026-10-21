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

    # hidden reverse relation: the upstream generic merge (MergeMixin) walks Food's visible reverse relations and
    # cannot handle a one-to-one; lookups still work through related_query_name
    food = models.OneToOneField(Food, on_delete=models.CASCADE, related_name='+', related_query_name='kitchen')
    is_family = models.BooleanField(default=False)
    aisle_source = models.CharField(max_length=16, choices=SOURCES, default=SOURCE_NONE)
    aisle_confirmed = models.BooleanField(default=False)
    # name the user chose to keep on the "names to fix" screen ("4 épices"): not proposed again while it stays the same
    kept_name = models.CharField(max_length=128, blank=True, default='')

    # price (M7): the amount itself is the upstream "Price" property of the food; the fork keeps where it comes from
    PRICE_ESTIMATED = 'estimated'
    PRICE_CONFIRMED = 'confirmed'
    PRICE_SOURCES = ((PRICE_ESTIMATED, 'estimated'), (PRICE_CONFIRMED, 'confirmed'))
    # empty: no price, or a price set outside the fork (upstream screens), which counts as confirmed
    price_source = models.CharField(max_length=16, choices=PRICE_SOURCES, blank=True, default='')
    # number of observations the price stands for (estimate = 1, each adjustment after shopping adds one, capped):
    # the weight of the current price in the smoothing of the next adjustment
    price_weight = models.PositiveSmallIntegerField(default=1)
    # the property amount the fork last wrote: a different amount was set by hand elsewhere, so it is no longer an estimate
    price_value = models.DecimalField(max_digits=32, decimal_places=4, null=True, blank=True)
    # optional package bought as a whole ("500 g for 1.20 €"): amount in grams, millilitres or pieces
    KIND_WEIGHT = 'g'
    KIND_VOLUME = 'ml'
    KIND_PIECE = 'piece'
    KINDS = ((KIND_WEIGHT, 'g'), (KIND_VOLUME, 'ml'), (KIND_PIECE, 'piece'))
    package_amount = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    package_kind = models.CharField(max_length=8, choices=KINDS, blank=True, default='')
    package_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    # grams per piece ("1 onion = 150 g"), to convert counted ingredients when the price is per kilo (and back)
    piece_weight = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
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
