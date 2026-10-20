<template>
    <!-- Foods as a 2-level tree (family > food): collapsible families, instant search, "no aisle" filter, no table -->
    <v-container class="fork-foods" max-width="760">
        <div class="d-flex align-center ga-2 mb-3">
            <h1 class="fork-foods__title flex-grow-1">{{ $t('Fork_Foods') }}</h1>
            <v-btn icon variant="tonal" size="48" :aria-label="$t('Fork_New_Food')" @click="openSheet(null)">
                <v-icon icon="$create"></v-icon>
            </v-btn>
            <v-btn icon variant="text" size="48" :aria-label="$t('Options')">
                <v-icon icon="fa-solid fa-ellipsis-vertical"></v-icon>
                <v-menu activator="parent">
                    <v-list>
                        <v-list-item prepend-icon="fa-solid fa-clone" :title="$t('Fork_Duplicates')" :to="{name: 'ForkDuplicatesPage'}" min-height="48"></v-list-item>
                        <v-list-item prepend-icon="fa-solid fa-arrow-down-short-wide" :title="$t('Fork_Aisle_Order')" :to="{name: 'ForkAislesPage'}"
                                     min-height="48"></v-list-item>
                        <v-list-item prepend-icon="fa-solid fa-table" :title="$t('Fork_Table_View')" :to="{name: 'ModelListPage', params: {model: 'food'}}"
                                     min-height="48"></v-list-item>
                    </v-list>
                </v-menu>
            </v-btn>
        </div>

        <!-- "to sort" queue -->
        <v-card v-if="toSort > 0" class="fork-foods__queue mb-3" variant="tonal" color="secondary" :to="{name: 'ForkToSortPage'}">
            <v-card-text class="d-flex align-center ga-3">
                <v-icon icon="fa-solid fa-inbox"></v-icon>
                <span class="flex-grow-1 text-body-1">{{ $t('Fork_To_Sort_Count', {n: toSort}, toSort) }}</span>
                <span class="font-weight-bold">{{ $t('Fork_Sort_Now') }}</span>
                <v-icon icon="fa-solid fa-chevron-right" size="16"></v-icon>
            </v-card-text>
        </v-card>

        <v-text-field v-model="query" :placeholder="$t('Fork_Search_Foods')" :aria-label="$t('Fork_Search_Foods')" prepend-inner-icon="$search"
                      variant="solo-filled" flat rounded="lg" clearable hide-details autocomplete="off" type="search"></v-text-field>
        <div class="d-flex flex-wrap ga-2 mt-2">
            <v-chip :variant="noAisleOnly ? 'tonal' : 'outlined'" :color="noAisleOnly ? 'primary' : undefined" class="fork-foods__chip"
                    :prepend-icon="noAisleOnly ? 'fa-solid fa-check' : undefined" :aria-pressed="noAisleOnly" @click="noAisleOnly = !noAisleOnly">
                {{ $t('Fork_No_Aisle') }} ({{ noAisleCount }})
            </v-chip>
        </div>

        <div v-if="loading" class="mt-4">
            <v-skeleton-loader type="list-item, list-item, list-item, list-item"></v-skeleton-loader>
        </div>
        <v-alert v-else-if="error" type="error" variant="tonal" class="mt-4" :text="$t('Fork_Load_Error')">
            <template #append>
                <v-btn variant="text" size="large" @click="load()">{{ $t('Fork_Retry') }}</v-btn>
            </template>
        </v-alert>
        <div v-else-if="groups.length == 0" class="fork-foods__empty fork-starfield mt-4">
            <p>{{ foods.length == 0 ? $t('Fork_No_Foods') : $t('Fork_No_Food_Match') }}</p>
        </div>

        <section v-for="group in groups" :key="group.key" class="fork-foods__group mt-3">
            <!-- family header -->
            <div class="fork-foods__family" :class="{'fork-foods__family--open': isOpen(group)}">
                <button class="fork-foods__family-toggle" type="button" :aria-expanded="isOpen(group)" @click="toggle(group)">
                    <v-icon :icon="isOpen(group) ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-right'" size="14" class="me-3"></v-icon>
                    <span class="fork-foods__family-name">{{ group.name }}</span>
                    <span class="fork-foods__count">{{ group.items.length }}</span>
                    <span class="fork-foods__aisle ms-auto" v-if="group.family?.category">{{ group.family.category.name }}</span>
                </button>
                <v-btn icon variant="text" size="44" v-if="group.family" :aria-label="$t('Edit')" @click="openSheet(group.family)">
                    <v-icon icon="fa-solid fa-pen" size="14"></v-icon>
                </v-btn>
            </div>

            <v-list v-if="isOpen(group)" class="py-0" bg-color="transparent">
                <v-list-item v-for="food in group.items" :key="food.id" min-height="52" class="fork-foods__row" @click="openSheet(food)">
                    <v-list-item-title class="fork-foods__name">{{ food.name }}</v-list-item-title>
                    <v-list-item-subtitle>
                        <span v-if="food.category" :class="{'fork-foods__unconfirmed': !food.aisleConfirmed}">
                            {{ food.category.name }}<template v-if="!food.aisleConfirmed"> · {{ $t('Fork_Suggested') }}</template>
                        </span>
                        <span v-else class="text-error">{{ $t('Fork_No_Aisle') }}</span>
                        <span v-if="food.ignoreShopping"> · {{ $t('Fork_Never_In_Shopping') }}</span>
                    </v-list-item-subtitle>
                    <template #append>
                        <v-btn icon variant="text" size="44" :aria-label="$t('Fork_Move_To_Family')" @click.stop="openMove(food)">
                            <v-icon icon="fa-solid fa-right-left" size="16"></v-icon>
                        </v-btn>
                    </template>
                </v-list-item>
            </v-list>
        </section>
    </v-container>

    <!-- move to another family: the second tap -->
    <v-bottom-sheet v-model="moveSheet" max-width="640" scrollable>
        <v-card :title="$t('Fork_Move_Food', {food: moving?.name})">
            <v-card-text class="pa-0">
                <v-list>
                    <v-list-item v-for="f in families" :key="f.id" :title="f.name" :subtitle="f.category?.name" min-height="56"
                                 :active="moving?.family == f.id" :disabled="f.id == moving?.id" @click="move(f.id)"></v-list-item>
                    <v-list-item :title="$t('Fork_No_Family')" min-height="56" prepend-icon="fa-solid fa-arrow-up" @click="move(null)"
                                 v-if="moving?.family"></v-list-item>
                </v-list>
            </v-card-text>
        </v-card>
    </v-bottom-sheet>

    <fork-food-sheet v-model="sheet" :food="editing" :families="families" :aisles="aisles" @saved="load()"></fork-food-sheet>
</template>

<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
import {useI18n} from "vue-i18n";
import {KitchenAisle, KitchenFoodItem, listAisles, listKitchenFoods, moveFoodToFamily} from "@/fork/api";
import {searchKey} from "@/fork/foods";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";
import ForkFoodSheet from "@/fork/components/ForkFoodSheet.vue";

interface FoodGroup {
    key: string
    name: string
    family: KitchenFoodItem | null
    items: KitchenFoodItem[]
}

const {t} = useI18n()

const foods = ref<KitchenFoodItem[]>([])
const aisles = ref<KitchenAisle[]>([])
const toSort = ref(0)
const loading = ref(true)
const error = ref(false)
const query = ref('')
const noAisleOnly = ref(false)
const opened = ref(new Set<string>())
const sheet = ref(false)
const editing = ref<KitchenFoodItem | null>(null)
const moveSheet = ref(false)
const moving = ref<KitchenFoodItem | null>(null)

const families = computed(() => foods.value.filter(f => f.isFamily))
const noAisleCount = computed(() => foods.value.filter(f => !f.category && !f.isFamily).length)
const filtering = computed(() => !!query.value?.trim() || noAisleOnly.value)

/** families with their members, then the foods without a family; filtered by search and "no aisle" */
const groups = computed<FoodGroup[]>(() => {
    const key = searchKey(query.value ?? '')
    const keep = (f: KitchenFoodItem) => (!key || searchKey(f.name).includes(key) || searchKey(f.pluralName ?? '').includes(key))
        && (!noAisleOnly.value || !f.category)
    const result: FoodGroup[] = families.value.map(family => {
        const members = foods.value.filter(f => f.family == family.id)
        const familyMatches = key && searchKey(family.name).includes(key)
        return {key: `f${family.id}`, name: family.name, family, items: familyMatches && !noAisleOnly.value ? members : members.filter(keep)}
    }).filter(g => !filtering.value || g.items.length > 0 || (key && searchKey(g.name).includes(key)))
    const loose = foods.value.filter(f => !f.isFamily && f.family == null).filter(keep)
    if (loose.length) result.push({key: 'loose', name: t('Fork_Without_Family'), family: null, items: loose})
    return result
})

function isOpen(group: FoodGroup) {
    return filtering.value || opened.value.has(group.key)
}

function toggle(group: FoodGroup) {
    const next = new Set(opened.value)
    next.has(group.key) ? next.delete(group.key) : next.add(group.key)
    opened.value = next
}

function openSheet(food: KitchenFoodItem | null) {
    editing.value = food
    sheet.value = true
}

function openMove(food: KitchenFoodItem) {
    moving.value = food
    moveSheet.value = true
}

function move(familyId: number | null) {
    const food = moving.value
    if (!food) return
    moveSheet.value = false
    moveFoodToFamily(food.id, familyId).then(() => {
        if (familyId) opened.value = new Set([...opened.value, `f${familyId}`])
        load()
    }).catch(err => useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err))
}

let firstLoad = true

function load() {
    error.value = false
    Promise.all([listKitchenFoods(), listAisles()]).then(([f, a]) => {
        foods.value = f.foods.sort((x, y) => x.name.localeCompare(y.name))
        toSort.value = f.toSort
        aisles.value = a.aisles
        if (firstLoad && f.foods.length <= 80) {
            // small collections start unfolded; larger ones start folded to give an overview
            opened.value = new Set([...groups.value.map(g => g.key)])
        }
        firstLoad = false
    }).catch(() => {
        error.value = true
    }).finally(() => {
        loading.value = false
    })
}

onMounted(() => load())
</script>

<style scoped>
.fork-foods__title {
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
}

.fork-foods__chip {
    min-height: var(--fork-tap);
}

.fork-foods__family {
    display: flex;
    align-items: center;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-foods__family-toggle {
    display: flex;
    align-items: center;
    flex: 1 1 auto;
    min-width: 0;
    min-height: 52px;
    padding: 0 var(--fork-space-2) 0 0;
    text-align: start;
    color: inherit;
    font: inherit;
    background: none;
    border: none;
    cursor: pointer;
}

.fork-foods__family-name {
    font-size: var(--fork-text-md);
    font-weight: 600;
}

.fork-foods__count {
    margin-inline-start: var(--fork-space-2);
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-foods__aisle {
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 45%;
}

.fork-foods__row {
    padding-inline-start: var(--fork-space-6) !important;
    padding-inline-end: 0 !important;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-foods__name {
    font-size: var(--fork-text-md);
    white-space: normal;
}

.fork-foods__row :deep(.v-list-item-subtitle) {
    opacity: 1;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-foods__unconfirmed {
    font-style: italic;
}

.fork-foods__empty {
    padding: var(--fork-space-8) var(--fork-space-4);
    text-align: center;
    border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: var(--fork-radius-card);
}
</style>
