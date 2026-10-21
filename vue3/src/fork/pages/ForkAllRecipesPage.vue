<template>
    <!-- Every recipe, made for browsing: a grid of photos (or one per line), grouped by letter, a letter bar to jump -->
    <v-container class="fork-all" max-width="1400">
        <div class="d-flex align-center ga-2 mb-2">
            <v-btn icon variant="text" size="48" :aria-label="$t('Back')" :to="{name: 'StartPage'}">
                <v-icon icon="fa-solid fa-arrow-left"></v-icon>
            </v-btn>
            <div class="flex-grow-1" style="min-width: 0">
                <h1 class="fork-all__title">{{ $t('Fork_All_Recipes_Title') }}</h1>
                <div class="fork-all__count" v-if="!loading">{{ $t('Fork_Recipes_Count', {n: recipes.length}, recipes.length) }}</div>
            </div>
            <v-btn-toggle v-model="view" mandatory density="comfortable" variant="outlined" divided class="fork-all__view flex-shrink-0">
                <v-btn value="grid" :aria-label="$t('Fork_View_Grid')" size="44"><v-icon icon="fa-solid fa-table-cells-large" size="16"></v-icon></v-btn>
                <v-btn value="list" :aria-label="$t('Fork_View_List')" size="44"><v-icon icon="fa-solid fa-list" size="16"></v-icon></v-btn>
            </v-btn-toggle>
        </div>

        <v-text-field v-model="query" :placeholder="$t('Fork_Search_Recipes')" :aria-label="$t('Fork_Search_Recipes')" prepend-inner-icon="$search"
                      variant="solo-filled" flat rounded="lg" clearable hide-details type="search" autocomplete="off"></v-text-field>

        <!-- jump to a letter -->
        <nav class="fork-all__letters" v-if="groups.length > 1" :aria-label="$t('Fork_Jump_To_Letter')">
            <button v-for="g in groups" :key="g.letter" type="button" class="fork-all__letter" @click="jump(g.letter)">{{ g.letter }}</button>
        </nav>

        <div v-if="loading" class="mt-4">
            <v-skeleton-loader v-for="i in 4" :key="i" type="list-item-avatar-two-line"></v-skeleton-loader>
        </div>
        <v-alert v-else-if="error" type="error" variant="tonal" class="mt-4" :text="$t('Fork_Load_Error')">
            <template #append>
                <v-btn variant="text" size="large" @click="load()">{{ $t('Fork_Retry') }}</v-btn>
            </template>
        </v-alert>
        <p v-else-if="groups.length == 0" class="text-body-1 text-medium-emphasis mt-6 text-center">{{ $t('Fork_No_Match') }}</p>

        <section v-for="g in groups" :key="g.letter" :id="'fork-letter-' + g.letter" class="fork-all__group">
            <h2 class="fork-all__group-letter">{{ g.letter }}</h2>
            <div v-if="view == 'grid'" class="fork-all__grid">
                <router-link v-for="r in g.recipes" :key="r.id" :to="{name: 'RecipeViewPage', params: {id: r.id}}" class="fork-all__card">
                    <fork-recipe-thumb :name="r.name" :image="r.image" :size="72" fluid></fork-recipe-thumb>
                    <span class="fork-all__name">{{ r.name }}</span>
                    <span class="fork-all__meta" v-if="totalTime(r) > 0">{{ totalTime(r) }} {{ $t('min') }}</span>
                </router-link>
            </div>
            <div v-else class="fork-all__list">
                <fork-recipe-row v-for="r in g.recipes" :key="r.id" :recipe="r"></fork-recipe-row>
            </div>
        </section>
    </v-container>
</template>

<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
import {useStorage} from "@vueuse/core";
import {KitchenRecipe, listKitchenRecipes} from "@/fork/api";
import {searchKey} from "@/fork/foods";
import ForkRecipeThumb from "@/fork/components/ForkRecipeThumb.vue";
import ForkRecipeRow from "@/fork/components/ForkRecipeRow.vue";

/** grid of photos or one recipe per line: a choice of this device */
const view = useStorage<'grid' | 'list'>('fork_all_recipes_view', 'grid')
const query = ref<string | null>('')
const recipes = ref<KitchenRecipe[]>([])
const loading = ref(true)
const error = ref(false)

function totalTime(r: KitchenRecipe) {
    return (r.workingTime ?? 0) + (r.waitingTime ?? 0)
}

function letterOf(name: string) {
    const first = searchKey(name).charAt(0).toUpperCase()
    return /[A-Z]/.test(first) ? first : '#'
}

/** recipes matching the search, by first letter (accents aside), in name order */
const groups = computed(() => {
    const key = searchKey(query.value ?? '')
    const result: { letter: string, recipes: KitchenRecipe[] }[] = []
    for (const r of recipes.value) {
        if (key && !searchKey(r.name).includes(key)) continue
        const letter = letterOf(r.name)
        let g = result.find(x => x.letter == letter)
        if (!g) {
            g = {letter, recipes: []}
            result.push(g)
        }
        g.recipes.push(r)
    }
    return result.sort((a, b) => a.letter == '#' ? 1 : b.letter == '#' ? -1 : a.letter.localeCompare(b.letter))
})

function jump(letter: string) {
    document.getElementById('fork-letter-' + letter)?.scrollIntoView({behavior: 'smooth', block: 'start'})
}

/** every recipe of the space (a few dozen to a few hundred): loaded once, page after page */
async function load() {
    loading.value = true
    error.value = false
    try {
        const all: KitchenRecipe[] = []
        for (let page = 1; page <= 20; page++) {
            const r = await listKitchenRecipes({sortOrder: 'name', page, pageSize: 100})
            all.push(...r.results)
            if (!r.next) break
        }
        recipes.value = all.sort((a, b) => a.name.localeCompare(b.name))
    } catch {
        error.value = true
    } finally {
        loading.value = false
    }
}

onMounted(() => load())
</script>

<style scoped>
.fork-all__title {
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
}

.fork-all__count {
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

/* stays under the app bar while scrolling: one tap to any letter */
.fork-all__letters {
    position: sticky;
    top: var(--v-layout-top, 56px);
    z-index: 2;
    display: flex;
    gap: var(--fork-space-1);
    overflow-x: auto;
    margin: var(--fork-space-2) calc(-1 * var(--fork-space-4)) 0;
    padding: var(--fork-space-2) var(--fork-space-4);
    background: rgb(var(--v-theme-background));
}

.fork-all__letter {
    flex: none;
    min-width: 44px;
    height: 44px;
    border-radius: 22px;
    border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    background: rgb(var(--v-theme-surface-bright));
    color: inherit;
    font-weight: 600;
    font-size: var(--fork-text-md);
    cursor: pointer;
}

.fork-all__group {
    /* the letter bar and the app bar stay above a section reached from the letter bar */
    scroll-margin-top: calc(var(--v-layout-top, 56px) + 64px);
}

.fork-all__group-letter {
    margin-top: var(--fork-space-4);
    padding-bottom: var(--fork-space-1);
    font-size: var(--fork-text-lg);
    font-weight: 700;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-all__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--fork-space-4) var(--fork-space-3);
    margin-top: var(--fork-space-3);
}

@media (min-width: 600px) {
    .fork-all__grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

@media (min-width: 960px) {
    .fork-all__grid {
        grid-template-columns: repeat(5, minmax(0, 1fr));
    }

    .fork-all__list {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        column-gap: var(--fork-space-6);
    }
}

.fork-all__card {
    display: flex;
    flex-direction: column;
    gap: var(--fork-space-1);
    color: inherit;
    text-decoration: none;
}

.fork-all__name {
    font-size: var(--fork-text-md);
    font-weight: 600;
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.fork-all__meta {
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
