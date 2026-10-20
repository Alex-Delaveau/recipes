<template>
    <!-- Ingredient lines: quantity first, scaled by the chosen servings -->
    <div class="fork-ingredients" :class="{'fork-ingredients--large': large}">
        <template v-for="(ingredient, index) in ingredients" :key="ingredient.id ?? index">
            <div class="fork-ingredients__header" v-if="ingredient.isHeader">{{ ingredient.note }}</div>
            <div class="fork-ingredients__row" v-else>
                <span class="fork-ingredients__amount">
                    <span v-if="ingredient.amount != 0 && !ingredient.noAmount" v-html="calculateFoodAmount(ingredient.amount, factor, useUserPreferenceStore().userSettings.useFractions)"></span>
                    {{ ingredientToUnitString(ingredient, factor) }}
                </span>
                <span class="fork-ingredients__food">
                    {{ ingredientToFoodString(ingredient, factor) }}
                    <span class="fork-ingredients__note" v-if="ingredient.note">{{ ingredient.note }}</span>
                </span>
            </div>
        </template>
    </div>
</template>

<script setup lang="ts">
import {PropType} from "vue";
import {Ingredient} from "@/openapi";
import {calculateFoodAmount} from "@/utils/number_utils";
import {ingredientToFoodString, ingredientToUnitString} from "@/utils/model_utils";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore";

defineProps({
    ingredients: {type: Array as PropType<Ingredient[]>, required: true},
    factor: {type: Number, required: true},
    /** cook mode: quantities at 20 px (DESIGN.md) */
    large: {type: Boolean, default: false},
})
</script>

<style scoped>
.fork-ingredients__row {
    display: flex;
    gap: var(--fork-space-3);
    padding: var(--fork-space-2) 0;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    font-size: var(--fork-text-md);
    line-height: 24px;
}

.fork-ingredients__row:last-child {
    border-bottom: none;
}

.fork-ingredients__amount {
    flex: 0 0 auto;
    min-width: 28%;
    max-width: 50%;
    font-weight: 600;
    text-align: right;
}

.fork-ingredients__food {
    flex: 1 1 auto;
    min-width: 0;
    overflow-wrap: anywhere;
}

.fork-ingredients__note {
    display: block;
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-ingredients__header {
    font-weight: 600;
    font-size: var(--fork-text-sm);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    margin-top: var(--fork-space-4);
}

.fork-ingredients__header:first-child {
    margin-top: 0;
}

.fork-ingredients--large .fork-ingredients__row {
    font-size: var(--fork-text-lg);
    line-height: 28px;
    padding: var(--fork-space-3) 0;
}

.fork-ingredients--large .fork-ingredients__note {
    font-size: var(--fork-text-md);
}
</style>
