<template>
    <!-- One recipe on one line: easy to scan, readable without a photo (home lists) -->
    <router-link :to="{name: 'RecipeViewPage', params: {id: recipe.id}}" class="fork-recipe-row">
        <fork-recipe-thumb :name="recipe.name" :image="recipe.image" :size="52"></fork-recipe-thumb>
        <div class="fork-recipe-row__text">
            <span class="fork-recipe-row__title">{{ recipe.name }}</span>
            <span class="fork-recipe-row__meta">
                <span v-if="totalTime > 0"><v-icon icon="fa-regular fa-clock" size="12" class="me-1"></v-icon>{{ totalTime }} {{ $t('min') }}</span>
                <span v-if="recipe.matchedFoods" class="text-secondary font-weight-medium">
                    <v-icon icon="fa-solid fa-carrot" size="12" class="me-1"></v-icon>{{ $t('Fork_Matched_Foods', {n: recipe.matchedFoods, total: recipe.totalFoods}) }}
                </span>
            </span>
        </div>
        <v-icon icon="fa-solid fa-chevron-right" size="14" class="fork-recipe-row__chevron"></v-icon>
    </router-link>
</template>

<script setup lang="ts">
import {computed, PropType} from "vue";
import {KitchenRecipe} from "@/fork/api";
import ForkRecipeThumb from "@/fork/components/ForkRecipeThumb.vue";

const props = defineProps({
    recipe: {type: Object as PropType<KitchenRecipe>, required: true},
})

const totalTime = computed(() => (props.recipe.workingTime ?? 0) + (props.recipe.waitingTime ?? 0))
</script>

<style scoped>
.fork-recipe-row {
    display: flex;
    align-items: center;
    gap: var(--fork-space-3);
    min-height: 68px;
    padding: var(--fork-space-2) 0;
    color: inherit;
    text-decoration: none;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-recipe-row__text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
    min-width: 0;
}

.fork-recipe-row__title {
    font-size: var(--fork-text-md);
    font-weight: 600;
    line-height: 1.3;
}

.fork-recipe-row__meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0 var(--fork-space-3);
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-recipe-row__chevron {
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
