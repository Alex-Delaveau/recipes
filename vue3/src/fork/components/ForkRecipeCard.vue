<template>
    <!-- Large photo card, readable one-handed (journey P1) -->
    <v-card :to="{name: 'RecipeViewPage', params: {id: recipe.id}}" class="fork-recipe-card h-100">
        <v-img :src="recipe.image ?? undefined" :aspect-ratio="16/9" cover class="fork-recipe-card__photo" :alt="recipe.name">
            <template #placeholder>
                <div class="fork-recipe-card__placeholder"><v-icon icon="$recipes" size="40"></v-icon></div>
            </template>
            <template #error>
                <div class="fork-recipe-card__placeholder"><v-icon icon="$recipes" size="40"></v-icon></div>
            </template>
            <div class="fork-recipe-card__placeholder" v-if="!recipe.image"><v-icon icon="$recipes" size="40"></v-icon></div>
        </v-img>
        <div class="pa-4">
            <div class="fork-recipe-card__title">{{ recipe.name }}</div>
            <div class="fork-recipe-card__meta mt-2">
                <span v-if="totalTime > 0"><v-icon icon="fa-regular fa-clock" size="14" class="me-1"></v-icon>{{ totalTime }} {{ $t('min') }}</span>
                <span v-if="recipe.servings"><v-icon icon="fa-solid fa-user-group" size="14" class="me-1"></v-icon>{{ $t('Fork_Servings_N', {n: recipe.servings}) }}</span>
                <span v-if="recipe.matchedFoods" class="text-secondary font-weight-medium">
                    <v-icon icon="fa-solid fa-carrot" size="14" class="me-1"></v-icon>{{ $t('Fork_Matched_Foods', {n: recipe.matchedFoods, total: recipe.totalFoods}) }}
                </span>
            </div>
        </div>
    </v-card>
</template>

<script setup lang="ts">
import {computed, PropType} from "vue";
import {KitchenRecipe} from "@/fork/api";

const props = defineProps({
    recipe: {type: Object as PropType<KitchenRecipe>, required: true},
})

const totalTime = computed(() => (props.recipe.workingTime ?? 0) + (props.recipe.waitingTime ?? 0))
</script>

<style scoped>
.fork-recipe-card {
    overflow: hidden;
}

.fork-recipe-card__photo {
    background: rgb(var(--v-theme-surface-variant));
}

.fork-recipe-card__placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    background: rgb(var(--v-theme-surface-variant));
}

.fork-recipe-card__title {
    font-size: var(--fork-text-lg);
    line-height: 28px;
    font-weight: 600;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.fork-recipe-card__meta {
    display: flex;
    flex-wrap: wrap;
    gap: var(--fork-space-1) var(--fork-space-4);
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
