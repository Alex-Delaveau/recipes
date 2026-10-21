from django.db.models.signals import post_save
from django.dispatch import receiver
from django_scopes import scopes_disabled

from cookbook.models import Food
from kitchen.models import KitchenSpace


@receiver(post_save, sender=Food)
def suggest_aisle_for_new_food(sender, instance=None, created=False, raw=False, **kwargs):
    """Every new food gets a suggested aisle, whatever creates it (import, typing, shopping list, API)."""
    if not created or raw or instance is None:
        return
    # only spaces that use the fork's aisle organisation (set up on first use): upstream behaviour is unchanged otherwise
    with scopes_disabled():
        if not KitchenSpace.objects.filter(space_id=instance.space_id).exists():
            return
    from kitchen.services import on_food_created
    on_food_created(instance)
