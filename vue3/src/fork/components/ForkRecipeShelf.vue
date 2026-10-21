<template>
    <!-- A shelf answers one question ("in less than 30 min"): a few recipes side by side, "see all" opens the full list -->
    <section class="fork-shelf" v-if="recipes.length">
        <div class="fork-shelf__head">
            <h2 class="fork-shelf__name">{{ title }}</h2>
            <v-btn variant="text" color="primary" size="large" class="fork-shelf__all" @click="emit('see-all')">{{ $t('Fork_See_All') }}</v-btn>
        </div>
        <div class="fork-shelf__row">
            <router-link v-for="r in recipes" :key="r.id" :to="{name: 'RecipeViewPage', params: {id: r.id}}" class="fork-shelf__item">
                <fork-recipe-thumb :name="r.name" :image="r.image" :size="128"></fork-recipe-thumb>
                <span class="fork-shelf__title">{{ r.name }}</span>
                <span class="fork-shelf__meta" v-if="totalTime(r) > 0">{{ totalTime(r) }} {{ $t('min') }}</span>
            </router-link>
        </div>
    </section>
</template>

<script setup lang="ts">
import {PropType} from "vue";
import {KitchenRecipe} from "@/fork/api";
import ForkRecipeThumb from "@/fork/components/ForkRecipeThumb.vue";

defineProps({
    title: {type: String, required: true},
    recipes: {type: Array as PropType<KitchenRecipe[]>, required: true},
})
const emit = defineEmits(['see-all'])

function totalTime(r: KitchenRecipe) {
    return (r.workingTime ?? 0) + (r.waitingTime ?? 0)
}
</script>

<style scoped>
.fork-shelf__head {
    display: flex;
    align-items: center;
    gap: var(--fork-space-2);
}

.fork-shelf__name {
    flex: 1;
    font-size: var(--fork-text-lg);
    font-weight: 600;
    line-height: 1.3;
}

.fork-shelf__all {
    min-height: var(--fork-tap);
}

/* scrolls sideways on a phone; bleeds to the screen edge so the next card shows it can be scrolled */
.fork-shelf__row {
    display: flex;
    gap: var(--fork-space-3);
    overflow-x: auto;
    margin: 0 calc(-1 * var(--fork-space-4));
    padding: var(--fork-space-1) var(--fork-space-4) var(--fork-space-2);
    scroll-snap-type: x proximity;
    scroll-padding-inline: var(--fork-space-4);
}

.fork-shelf__item {
    flex: none;
    width: 128px;
    display: flex;
    flex-direction: column;
    gap: var(--fork-space-1);
    color: inherit;
    text-decoration: none;
    scroll-snap-align: start;
}

.fork-shelf__title {
    font-size: var(--fork-text-sm);
    font-weight: 600;
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.fork-shelf__meta {
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
