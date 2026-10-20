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

        <!-- shortcuts: browse without a filter -->
        <v-chip-group v-model="filters.sort" column selected-class="text-primary" class="mt-2 fork-home__shortcuts">
            <v-chip value="recent" filter variant="outlined" prepend-icon="fa-solid fa-clock-rotate-left">{{ $t('Fork_Shortcut_Recent') }}</v-chip>
            <v-chip value="random" filter variant="outlined" prepend-icon="fa-solid fa-shuffle" @click.capture="reshuffle">{{ $t('Fork_Shortcut_Random') }}</v-chip>
            <v-chip value="forgotten" filter variant="outlined" prepend-icon="fa-solid fa-hourglass-half">{{ $t('Fork_Shortcut_Forgotten') }}</v-chip>
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

        <horizontal-meal-plan-window class="mt-4" v-if="mdAndUp && useUserPreferenceStore().deviceSettings.start_showMealPlan"></horizontal-meal-plan-window>

        <p class="text-body-2 text-medium-emphasis mt-4 mb-2" v-if="!loading && !error && totalRecipes != 0" aria-live="polite">
            {{ $t('Fork_Recipes_Count', {n: count}, count) }}
        </p>

        <!-- loading -->
        <v-row v-if="loading && recipes.length == 0" class="mt-2">
            <v-col cols="12" sm="6" md="4" lg="3" v-for="i in 4" :key="i">
                <v-skeleton-loader type="image, list-item-two-line" class="rounded-lg"></v-skeleton-loader>
            </v-col>
        </v-row>

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
                    <v-list-item :to="{name: 'ModelEditPage', params: {model: 'Recipe'}}" prepend-icon="fa-solid fa-pen" :title="$t('Fork_Add_Manual')"
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

        <v-row v-else>
            <v-col cols="12" sm="6" md="4" lg="3" v-for="r in recipes" :key="r.id">
                <fork-recipe-card :recipe="r"></fork-recipe-card>
            </v-col>
        </v-row>

        <div class="text-center my-4" v-if="hasMore && !error">
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
import ForkRecipeCard from "@/fork/components/ForkRecipeCard.vue";
import ForkModelAutocomplete from "@/fork/components/ForkModelAutocomplete.vue";
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

function reshuffle() {
    // tapping "random" again draws a new selection instead of switching the shortcut off
    if (filters.sort == 'random') {
        setTimeout(() => {
            filters.sort = 'random'
        })
    }
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
    new ApiApi().apiRecipeList({pageSize: 1}).then(r => {
        totalRecipes.value = r.count
    }).catch(() => {
        totalRecipes.value = -1
    })
})
</script>

<style scoped>
.fork-home__shortcuts :deep(.v-chip) {
    min-height: var(--fork-tap);
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
