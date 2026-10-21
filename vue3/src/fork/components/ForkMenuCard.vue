<template>
    <!-- "On the menu": what the meal plan says for today (tomorrow after 21:00); hidden when nothing is planned -->
    <v-card v-if="plans.length" variant="tonal" color="secondary" class="fork-menu" :aria-label="title">
        <div class="fork-menu__title">
            <v-icon icon="fa-regular fa-calendar" size="16" class="me-2"></v-icon>{{ title }}
        </div>
        <component :is="plan.recipe ? 'router-link' : 'div'" v-for="plan in plans" :key="plan.id" class="fork-menu__row"
                   :class="{'fork-menu__row--link': plan.recipe}"
                   v-bind="plan.recipe ? {to: {name: 'RecipeViewPage', params: {id: plan.recipe.id}, query: servingsQuery(plan)}} : {}">
            <v-avatar v-if="plan.recipe?.image" :image="plan.recipe.image" size="44" rounded="lg"></v-avatar>
            <v-avatar v-else size="44" rounded="lg" color="secondary" variant="tonal">
                <v-icon icon="fa-solid fa-utensils" size="18"></v-icon>
            </v-avatar>
            <div class="fork-menu__text">
                <div class="fork-menu__name">{{ plan.recipe?.name ?? plan.title }}</div>
                <div class="fork-menu__meal">{{ plan.mealType.name }}</div>
            </div>
            <v-icon v-if="plan.recipe" icon="fa-solid fa-chevron-right" size="14" class="fork-menu__chevron"></v-icon>
        </component>
    </v-card>
</template>

<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
import {useI18n} from "vue-i18n";
import {ApiApi, MealPlan} from "@/openapi";

/** after this hour, the card shows tomorrow's meals: dinner is behind us */
const TOMORROW_FROM_HOUR = 21

const {t} = useI18n()
const plans = ref<MealPlan[]>([])
const tomorrow = ref(false)

const title = computed(() => tomorrow.value ? t('Fork_Menu_Tomorrow') : t('Fork_Menu_Today'))

function isoDay(date: Date) {
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function servingsQuery(plan: MealPlan) {
    return plan.servings && plan.servings != plan.recipe?.servings ? {servings: String(plan.servings)} : {}
}

onMounted(() => {
    const day = new Date()
    tomorrow.value = day.getHours() >= TOMORROW_FROM_HOUR
    if (tomorrow.value) day.setDate(day.getDate() + 1)
    const date = isoDay(day)
    new ApiApi().apiMealPlanList({fromDate: date, toDate: date}).then(r => {
        plans.value = r.results
            .filter(p => p.recipe || p.title)
            .sort((a, b) => (a.mealType.time ?? '').localeCompare(b.mealType.time ?? '') || (a.mealType.order ?? 0) - (b.mealType.order ?? 0))
            .slice(0, 3)
    }).catch(() => {
        // the card is a shortcut: without it, the home screen stays usable
        plans.value = []
    })
})
</script>

<style scoped>
.fork-menu {
    margin-top: var(--fork-space-3);
    padding: var(--fork-space-3) var(--fork-space-2) var(--fork-space-2);
}

.fork-menu__title {
    display: flex;
    align-items: center;
    padding: 0 var(--fork-space-2) var(--fork-space-1);
    font-size: var(--fork-text-sm);
    font-weight: 600;
}

.fork-menu__row {
    display: flex;
    align-items: center;
    gap: var(--fork-space-3);
    min-height: 56px;
    padding: var(--fork-space-1) var(--fork-space-2);
    border-radius: var(--fork-radius-card);
    color: rgb(var(--v-theme-on-surface));
    text-decoration: none;
}

.fork-menu__row--link:hover {
    background: rgba(var(--v-theme-on-surface), 0.04);
}

.fork-menu__text {
    flex: 1 1 auto;
    min-width: 0;
}

.fork-menu__name {
    font-size: var(--fork-text-md);
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.fork-menu__meal {
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-menu__chevron {
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
