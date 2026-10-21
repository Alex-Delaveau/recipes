from rest_framework import serializers

from cookbook.serializer import RecipeOverviewSerializer


class KitchenRecipeSerializer(RecipeOverviewSerializer):
    """Recipe card data for the fork's home screen, plus how many of the "on hand" foods the recipe uses."""
    matched_foods = serializers.IntegerField(read_only=True, default=None)
    total_foods = serializers.IntegerField(read_only=True, default=None)
    last_cooked = serializers.DateTimeField(source='lastcooked', read_only=True, default=None)

    class Meta(RecipeOverviewSerializer.Meta):
        fields = RecipeOverviewSerializer.Meta.fields + ('matched_foods', 'total_foods')
