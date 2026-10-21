<template>
    <!-- Journey P1 "Choose what to eat": search first, filters in a bottom sheet, shortcuts and large photo cards -->
    <v-container class="fork-home" max-width="1400">
        <div class="d-flex ga-2 align-center">
            <v-text-field
                v-model="filters.query"
                :placeholder="$t('Fork_Search_Recipes')"
                prepend-inner-icon="$search"
                variant="solo-filled"
                flat
                rounded="lg"
                clearable
                hide-details
                type="search"
                inputmode="search"
                autocomplete="off"
                class="flex-grow-1"
                :aria-label="$t('Fork_Search_Recipes')"
            ></v-text-field>
            <v-badge :content="activeFilterCount" :model-value="activeFilterCount > 0" color="primary" offset-x="4" offset-y="4">
                <v-btn icon variant="tonal" size="56" rounded="lg" :aria-label="$t('Fork_Filters')" @click="filterSheet = true">
                    <v-icon icon="fa-solid fa-sliders"></v-icon>
                </v-btn>
            </v-badge>
        </div>

        <!-- phone: what is planned today; the desktop has the week banner below -->
        <fork-menu-card v-if="!mdAndUp"></fork-menu-card>

        <!-- shortcuts: lists without a filter (tap again to switch off) -->
        <v-chip-group v-model="filters.sort" selected-class="fork-home__chip--on" class="mt-2 fork-home__shortcuts">
            <v-chip value="recent" variant="outlined" prepend-icon="fa-solid fa-clock-rotate-left" :aria-pressed="filters.sort == 'recent'">
                {{ $t('Fork_Shortcut_Recent') }}
            </v-chip>
            <v-chip value="forgotten" variant="outlined" prepend-icon="fa-solid fa-hourglass-half" :aria-pressed="filters.sort == 'forgotten'">
                {{ $t('Fork_Shortcut_Forgotten') }}
            </v-chip>
        </v-chip-group>

        <!-- active filters, removable in one tap -->
        <div class="d-flex flex-wrap ga-2 mt-1" v-if="activeFilterCount > 0">
            <v-chip v-for="f in filters.have" :key="'f' + f.id" closable color="secondary" variant="tonal" prepend-icon="fa-solid fa-carrot"
                    @click:close="filters.have = filters.have.filter(x => x.id != f.id)">{{ f.name }}
            </v-chip>
            <v-chip v-if="filters.maxTime" closable color="secondary" variant="tonal" prepend-icon="fa-regular fa-clock"
                    @click:close="filters.maxTime = null">{{ $t('Fork_Max_Minutes', {n: filters.maxTime}) }}
            </v-chip>
            <v-chip v-for="k in filters.keywords" :key="'k' + k.id" closable color="secondary" variant="tonal" prepend-icon="fa-solid fa-tag"
                    @click:close="filters.keywords = filters.keywords.filter(x => x.id != k.id)">{{ k.name }}
            </v-chip>
        </div>

        <!-- browsing (no search, no filter): the week first, then a few shelves, then every recipe -->
        <template v-if="browsing && totalRecipes != 0">
            <fork-week-card class="mt-3"></fork-week-card>
            <horizontal-meal-plan-window class="mt-4" v-if="mdAndUp && useUserPreferenceStore().deviceSettings.start_showMealPlan"></horizontal-meal-plan-window>
            <fork-recipe-shelf class="mt-5" :title="$t('Fork_Shelf_Quick')" :recipes="quickShelf" @see-all="filters.maxTime = 30"></fork-recipe-shelf>
            <fork-recipe-shelf class="mt-4" :title="$t('Fork_Shortcut_Forgotten')" :recipes="forgottenShelf" @see-all="filters.sort = 'forgotten'"></fork-recipe-shelf>
            <div class="fork-home__all mt-5" v-if="!loading || recipes.length">
                <h2 class="fork-home__all-title">{{ $t('Fork_All_Recipes', {n: count}) }}</h2>
                <v-btn variant="text" color="primary" size="large" :to="{name: 'ForkAllRecipesPage'}">{{ $t('Fork_See_All') }}</v-btn>
            </div>
        </template>

        <p class="text-body-2 text-medium-emphasis mt-4 mb-1" v-else-if="!loading && !error && totalRecipes != 0" aria-live="polite">
            {{ $t('Fork_Recipes_Count', {n: count}, count) }}
        </p>

        <!-- loading -->
        <div v-if="loading && recipes.length == 0" class="mt-2">
            <v-skeleton-loader v-for="i in 4" :key="i" type="list-item-avatar-two-line"></v-skeleton-loader>
        </div>

        <!-- error -->
        <v-alert v-else-if="error" type="error" variant="tonal" class="mt-4" :text="$t('Fork_Load_Error')">
            <template #append>
                <v-btn variant="text" size="large" @click="reload()">{{ $t('Fork_Retry') }}</v-btn>
            </template>
        </v-alert>

        <!-- empty space: nothing created yet -->
        <v-card v-else-if="totalRecipes == 0" class="mt-4 fork-starfield" :title="$t('search_no_recipes')">
            <v-card-text>
                <v-list>
                    <v-list-item :to="{name: 'RecipeImportPage', params: {}}" prepend-icon="fa-solid fa-globe" :title="$t('Fork_Add_From_Url')"
                                 min-height="56"></v-list-item>
                    <v-list-item :to="{name: 'ForkRecipeNewPage', params: {}}" prepend-icon="fa-solid fa-pen" :title="$t('Fork_Add_Manual')"
                                 min-height="56"></v-list-item>
                </v-list>
            </v-card-text>
        </v-card>

        <!-- no result for these filters -->
        <v-card v-else-if="recipes.length == 0" class="mt-4 text-center pa-6" variant="outlined">
            <v-icon icon="fa-solid fa-bowl-food" size="32" class="mb-3 text-medium-emphasis"></v-icon>
            <p class="text-body-1">{{ filters.sort == 'recent' && activeFilterCount == 0 && !filters.query ? $t('Fork_No_Recent') : $t('Fork_No_Match') }}</p>
            <v-btn class="mt-4" variant="tonal" @click="resetAll()">{{ $t('Fork_Reset') }}</v-btn>
        </v-card>

        <!-- one recipe per line: quick to scan, two columns on a wide screen -->
        <div v-else class="fork-home__list">
            <fork-recipe-row v-for="r in shownRecipes" :key="r.id" :recipe="r"></fork-recipe-row>
        </div>

        <!-- browsing: a preview, "see all" opens the page made for browsing everything; results: page by page -->
        <div class="text-center my-4" v-if="browsing && recipes.length && count > PREVIEW_SIZE">
            <v-btn variant="tonal" size="large" :to="{name: 'ForkAllRecipesPage'}">{{ $t('Fork_See_All_N', {n: count}) }}</v-btn>
        </div>
        <div class="text-center my-4" v-else-if="!browsing && hasMore && !error">
            <v-btn variant="tonal" size="large" :loading="loading" @click="loadPage(page + 1)">{{ $t('Fork_Load_More') }}</v-btn>
        </div>
    </v-container>

    <v-bottom-sheet v-model="filterSheet" max-width="640">
        <v-card :title="$t('Fork_Filters')">
            <template #append>
                <v-btn icon="$close" variant="text" :aria-label="$t('Close')" @click="filterSheet = false"></v-btn>
            </template>
            <v-card-text>
                <div class="fork-home__section">{{ $t('Fork_Foods_On_Hand') }}</div>
                <fork-model-autocomplete model="food" v-model="filters.have" :label="$t('Fork_Foods_On_Hand_Hint')"></fork-model-autocomplete>

                <div class="fork-home__section mt-6">{{ $t('Fork_Total_Time') }}</div>
                <v-chip-group v-model="filters.maxTime" selected-class="text-primary">
                    <v-chip v-for="t in [15, 30, 60]" :key="t" :value="t" filter variant="outlined">{{ $t('Fork_Max_Minutes', {n: t}) }}</v-chip>
                </v-chip-group>

                <div class="fork-home__section mt-6">{{ $t('Keywords') }}</div>
                <fork-model-autocomplete model="keyword" v-model="filters.keywords" :label="$t('Fork_Keywords_Hint')"></fork-model-autocomplete>
            </v-card-text>
            <v-card-actions class="pa-4 ga-2">
                <v-btn variant="text" size="large" @click="resetFilters()">{{ $t('Fork_Reset') }}</v-btn>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="flat" size="large" :loading="loading" @click="filterSheet = false">
                    {{ $t('Fork_Show_Results', {n: count}, count) }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
import {computed, onMounted, ref, watch} from "vue";
import {watchDebounced} from "@vueuse/core";
import {useDisplay} from "vuetify";
import {ApiApi} from "@/openapi";
import {KitchenRecipe, listKitchenRecipes} from "@/fork/api";
import {forkHomeFilters as filters} from "@/fork/homeFilters";
import ForkRecipeRow from "@/fork/components/ForkRecipeRow.vue";
import ForkRecipeShelf from "@/fork/components/ForkRecipeShelf.vue";
import ForkWeekCard from "@/fork/components/ForkWeekCard.vue";
import ForkModelAutocomplete from "@/fork/components/ForkModelAutocomplete.vue";
import ForkMenuCard from "@/fork/components/ForkMenuCard.vue";
import HorizontalMealPlanWindow from "@/components/display/HorizontalMealPlanWindow.vue";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore";

const PAGE_SIZE = 24

const {mdAndUp} = useDisplay()

const filterSheet = ref(false)
const recipes = ref<KitchenRecipe[]>([])
const count = ref(0)
const page = ref(1)
const hasMore = ref(false)
const loading = ref(false)
const error = ref(false)
/** number of recipes in the space, -1 while unknown: tells "no recipe yet" apart from "no match" */
const totalRecipes = ref(-1)
let requestId = 0

const activeFilterCount = computed(() => filters.have.length + filters.keywords.length + (filters.maxTime ? 1 : 0))
/** nothing searched or filtered: the home shows the week, the shelves and every recipe by name */
const browsing = computed(() => !filters.query && activeFilterCount.value == 0 && !filters.sort)

const SHELF_SIZE = 10
/** browsing shows the first recipes by name only: the full list has its own page (grid, A-Z) */
const PREVIEW_SIZE = 6
const shownRecipes = computed(() => browsing.value ? recipes.value.slice(0, PREVIEW_SIZE) : recipes.value)
const quickShelf = ref<KitchenRecipe[]>([])
const forgottenShelf = ref<KitchenRecipe[]>([])

function loadShelves() {
    listKitchenRecipes({maxTime: 30, page: 1, pageSize: SHELF_SIZE}).then(r => {
        quickShelf.value = r.results
    }).catch(() => {
        quickShelf.value = []
    })
    listKitchenRecipes({sort: 'forgotten', page: 1, pageSize: SHELF_SIZE}).then(r => {
        forgottenShelf.value = r.results
    }).catch(() => {
        forgottenShelf.value = []
    })
}

function loadPage(p: number) {
    const id = ++requestId
    loading.value = true
    error.value = false
    listKitchenRecipes({
        query: filters.query ?? '',
        have: filters.have.map(f => f.id),
        keywords: filters.keywords.map(k => k.id),
        maxTime: filters.maxTime,
        sort: filters.sort,
        sortOrder: browsing.value ? 'name' : undefined,
        page: p,
        pageSize: PAGE_SIZE,
    }).then(r => {
        if (id != requestId) return // a newer search superseded this one
        recipes.value = p == 1 ? r.results : recipes.value.concat(r.results)
        count.value = r.count
        page.value = p
        // random order changes on every request: paging would repeat or skip recipes
        hasMore.value = r.next != null && filters.sort != 'random'
    }).catch(() => {
        if (id == requestId) error.value = true
    }).finally(() => {
        if (id == requestId) loading.value = false
    })
}

function reload() {
    loadPage(1)
}

function resetFilters() {
    filters.have = []
    filters.keywords = []
    filters.maxTime = null
}

function resetAll() {
    resetFilters()
    filters.query = ''
    filters.sort = null
}

watch(() => [filters.have, filters.keywords, filters.maxTime, filters.sort], () => reload(), {deep: true})
watchDebounced(() => filters.query, () => reload(), {debounce: 300})

onMounted(() => {
    reload()
    loadShelves()
    new ApiApi().apiRecipeList({pageSize: 1}).then(r => {
        totalRecipes.value = r.count
    }).catch(() => {
        totalRecipes.value = -1
    })
})
</script>

<style scoped>
.fork-home__all {
    display: flex;
    align-items: center;
    gap: var(--fork-space-2);
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-home__all-title {
    flex: 1;
    font-size: var(--fork-text-lg);
    font-weight: 600;
}

@media (min-width: 960px) {
    .fork-home__list {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        column-gap: var(--fork-space-6);
    }
}

.fork-home__shortcuts :deep(.v-chip) {
    min-height: var(--fork-tap);
}

/* selected shortcut: filled, a single icon (no extra check mark next to the shortcut's own icon) */
.fork-home__shortcuts :deep(.fork-home__chip--on) {
    background: rgba(var(--v-theme-primary), 0.12);
    border-color: rgb(var(--v-theme-primary));
    color: rgb(var(--v-theme-primary));
}

.fork-home__section {
    font-size: var(--fork-text-md);
    font-weight: 600;
    margin-bottom: var(--fork-space-2);
}

.v-chip-group :deep(.v-chip) {
    min-height: var(--fork-tap);
}

.v-chip.v-chip--closable {
    min-height: var(--fork-tap);
}
</style>
