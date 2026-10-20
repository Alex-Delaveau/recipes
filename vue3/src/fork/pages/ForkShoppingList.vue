<template>
    <!-- Journey P4 "Shopping": grouped by aisle, one tap checks, "in the cart" below, undo, quick add -->
    <shopping-list-view v-if="detailedView"></shopping-list-view>

    <v-container class="fork-shopping" max-width="760" v-else>
        <div class="d-flex align-center ga-2 mb-3">
            <h1 class="fork-shopping__title flex-grow-1">{{ $t('Shopping_list') }}</h1>
            <v-progress-circular indeterminate size="20" width="2" v-if="useShoppingStore().currentlyUpdating" :aria-label="$t('Fork_Syncing')"></v-progress-circular>
            <v-btn icon variant="text" size="48" :disabled="useShoppingStore().undoStack.length == 0" :aria-label="$t('Fork_Undo')"
                   @click="useShoppingStore().undoChange()">
                <v-icon icon="fa-solid fa-rotate-left"></v-icon>
            </v-btn>
            <v-btn icon variant="text" size="48" :aria-label="$t('Options')">
                <v-icon icon="fa-solid fa-ellipsis-vertical"></v-icon>
                <v-menu activator="parent">
                    <v-list>
                        <v-list-item prepend-icon="fa-solid fa-list" :title="$t('Fork_Detailed_View')" @click="detailedView = true" min-height="48"></v-list-item>
                        <v-list-item prepend-icon="fa-solid fa-sliders" :title="$t('Settings')" :to="{name: 'ShoppingSettings'}" min-height="48"></v-list-item>
                    </v-list>
                </v-menu>
            </v-btn>
        </div>

        <!-- quick add in free text: "2 citrons" -->
        <v-form @submit.prevent="quickAdd()">
            <v-text-field
                v-model="newItem"
                :placeholder="$t('Fork_Quick_Add')"
                :aria-label="$t('Fork_Quick_Add')"
                prepend-inner-icon="$create"
                variant="solo-filled"
                flat
                rounded="lg"
                hide-details
                enterkeyhint="done"
                autocomplete="off"
                :loading="adding"
            >
                <template #append-inner>
                    <v-btn icon variant="text" size="44" type="submit" :disabled="!newItem.trim()" :aria-label="$t('Add')">
                        <v-icon icon="fa-solid fa-arrow-right"></v-icon>
                    </v-btn>
                </template>
            </v-text-field>
        </v-form>

        <v-alert v-if="useShoppingStore().hasFailedItems()" type="warning" variant="tonal" class="mt-3" :text="$t('ShoppingBackgroundSyncWarning')"></v-alert>

        <!-- loading -->
        <div v-if="!useShoppingStore().initialized" class="mt-4">
            <v-skeleton-loader type="list-item, list-item, list-item, list-item"></v-skeleton-loader>
        </div>

        <template v-else>
            <!-- empty list -->
            <div class="fork-shopping__empty fork-starfield" v-if="toBuy.length == 0 && inCart.length == 0">
                <v-icon icon="$shopping" size="32" class="mb-3"></v-icon>
                <p>{{ $t('Fork_Shopping_Empty') }}</p>
            </div>

            <!-- done: simple message, no animation -->
            <div class="fork-shopping__done" v-else-if="toBuy.length == 0" role="status">
                <v-icon icon="fa-solid fa-check" size="24" class="me-3"></v-icon>
                <span>{{ $t('Fork_Shopping_Done') }}</span>
            </div>

            <section v-for="group in toBuy" :key="group.name" class="mt-4">
                <h2 class="fork-shopping__aisle">{{ group.name }}</h2>
                <v-list class="py-0 fork-shopping__list" bg-color="transparent">
                    <v-list-item v-for="row in group.rows" :key="row.food.id" min-height="56" class="fork-shopping__row"
                                 role="checkbox" :aria-checked="false" @click="check(row)">
                        <template #prepend>
                            <span class="fork-shopping__box" aria-hidden="true"></span>
                        </template>
                        <v-list-item-title class="fork-shopping__food">{{ row.label }}</v-list-item-title>
                        <v-list-item-subtitle class="fork-shopping__amount" v-if="row.amount">{{ row.amount }}</v-list-item-subtitle>
                        <template #append>
                            <v-btn icon variant="text" size="44" :aria-label="$t('Edit')" @click.stop="openDetails(row)">
                                <v-icon icon="fa-solid fa-ellipsis-vertical" size="16"></v-icon>
                            </v-btn>
                        </template>
                    </v-list-item>
                </v-list>
            </section>

            <section v-if="inCart.length" class="mt-6">
                <h2 class="fork-shopping__aisle">{{ $t('Fork_In_Cart') }} ({{ inCart.length }})</h2>
                <v-list class="py-0" bg-color="transparent">
                    <v-list-item v-for="row in inCart" :key="row.food.id" min-height="48" class="fork-shopping__row fork-shopping__row--done"
                                 role="checkbox" :aria-checked="true" @click="uncheck(row)">
                        <template #prepend>
                            <span class="fork-shopping__box fork-shopping__box--checked" aria-hidden="true"><v-icon icon="fa-solid fa-check" size="12"></v-icon></span>
                        </template>
                        <v-list-item-title class="fork-shopping__food">{{ row.label }}</v-list-item-title>
                        <v-list-item-subtitle v-if="row.amount">{{ row.amount }}</v-list-item-subtitle>
                    </v-list-item>
                </v-list>
            </section>
        </template>

        <shopping-line-item-dialog v-if="detailsFood" v-model="detailsOpen" v-model:shopping-list-food="detailsFood"></shopping-line-item-dialog>
    </v-container>

    <v-snackbar v-model="undoSnackbar" :timeout="4000" location="bottom" class="fork-shopping__snackbar">
        {{ undoText }}
        <template #actions>
            <v-btn variant="text" color="primary" @click="undo()">{{ $t('Fork_Undo') }}</v-btn>
        </template>
    </v-snackbar>
</template>

<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref} from "vue";
import {useI18n} from "vue-i18n";
import {ApiApi, Food, ShoppingListEntry} from "@/openapi";
import {useShoppingStore} from "@/stores/ShoppingStore";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";
import {IShoppingListFood} from "@/types/Shopping";
import {isEntryVisible} from "@/utils/logic_utils";
import {pluralString} from "@/utils/model_utils";
import {roundDecimals} from "@/utils/number_utils";
import ShoppingListView from "@/components/display/ShoppingListView.vue";
import ShoppingLineItemDialog from "@/components/dialogs/ShoppingLineItemDialog.vue";

type ShoppingFood = NonNullable<ShoppingListEntry['food']>

interface ShoppingRow {
    food: ShoppingFood
    entries: ShoppingListEntry[]
    label: string
    amount: string
}

interface AisleGroup {
    name: string
    rows: ShoppingRow[]
}

const {t} = useI18n()

const detailedView = ref(false)
const newItem = ref('')
const adding = ref(false)
const undoSnackbar = ref(false)
const undoText = ref('')
const detailsOpen = ref(false)
const detailsFood = ref<IShoppingListFood | null>(null)

/** entries shown on this device: upstream visibility rules (lists, delayed), checked entries included */
const visibleEntries = computed(() => {
    const settings = {...useUserPreferenceStore().deviceSettings, shopping_show_checked_entries: true}
    return Array.from(useShoppingStore().entries.values()).filter(e => e.food && isEntryVisible(e, settings))
})

function rowsOf(entries: ShoppingListEntry[]): ShoppingRow[] {
    const byFood = new Map<number, ShoppingListEntry[]>()
    entries.forEach(e => byFood.set(e.food!.id!, [...(byFood.get(e.food!.id!) ?? []), e]))
    return Array.from(byFood.values()).map(list => {
        const food = list[0]!.food!
        // amounts summed per unit: "3 pièces + 500 g"
        const perUnit = new Map<string, { amount: number, unit: ShoppingListEntry['unit'] }>()
        list.forEach(e => {
            const key = e.unit?.id != undefined ? String(e.unit.id) : '-'
            const current = perUnit.get(key) ?? {amount: 0, unit: e.unit}
            current.amount += Number(e.amount)
            perUnit.set(key, current)
        })
        const total = list.reduce((sum, e) => sum + Number(e.amount), 0)
        const amount = Array.from(perUnit.values()).filter(a => a.amount > 0)
            .map(a => `${roundDecimals(a.amount)}${a.unit ? ' ' + pluralString(a.unit, a.amount) : ''}`).join(' + ')
        return {food, entries: list, label: pluralString(food as Food, total), amount}
    }).sort((a, b) => a.label.localeCompare(b.label))
}

/** what is left to buy, grouped by aisle in the order of the selected supermarket (alphabetical otherwise) */
const toBuy = computed<AisleGroup[]>(() => {
    const groups = new Map<string, ShoppingListEntry[]>()
    visibleEntries.value.filter(e => !e.checked).forEach(e => {
        const name = e.food!.supermarketCategory?.name ?? ''
        groups.set(name, [...(groups.get(name) ?? []), e])
    })
    const supermarket = useUserPreferenceStore().deviceSettings.shopping_selected_supermarket
    const order = supermarket ? supermarket.categoryToSupermarket.map(c => c.category.name) : []
    const rank = (name: string) => {
        if (name == '') return Number.MAX_SAFE_INTEGER // no aisle: last, so the walk through the shop comes first
        const i = order.indexOf(name)
        return i == -1 ? order.length : i
    }
    return Array.from(groups.entries())
        .sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b))
        .map(([name, entries]) => ({name: name || t('Fork_No_Aisle'), rows: rowsOf(entries)}))
})

const inCart = computed(() => rowsOf(visibleEntries.value.filter(e => e.checked)))

function check(row: ShoppingRow) {
    useShoppingStore().setEntriesCheckedState(row.entries, true, true)
    undoText.value = t('Fork_Checked_Item', {item: row.label})
    undoSnackbar.value = true
}

function uncheck(row: ShoppingRow) {
    useShoppingStore().setEntriesCheckedState(row.entries, false, true)
    undoText.value = t('Fork_Unchecked_Item', {item: row.label})
    undoSnackbar.value = true
}

function undo() {
    useShoppingStore().undoChange()
    undoSnackbar.value = false
}

function openDetails(row: ShoppingRow) {
    detailsFood.value = {food: row.food, entries: new Map(row.entries.map(e => [e.id!, e]))} as IShoppingListFood
    detailsOpen.value = true
}

/** free text goes through the ingredient parser, the food keeps its aisle */
function quickAdd() {
    const text = newItem.value.trim()
    if (!text) return
    adding.value = true
    new ApiApi().apiIngredientParserPostCreate({ingredientParserRequest: {ingredient: text}}).then(r => {
        if (!r.ingredient?.food) throw new Error('no food recognised')
        const entry = {
            amount: Math.max(r.ingredient.amount ?? 1, 1),
            unit: r.ingredient.unit,
            food: r.ingredient.food,
            shoppingLists: useShoppingStore().shoppingLists.filter(sl => useUserPreferenceStore().deviceSettings.shopping_selected_shopping_lists.includes(sl.id!)),
        } as ShoppingListEntry
        return useShoppingStore().createObject(entry, true)
    }).then(() => {
        newItem.value = ''
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.CREATE_ERROR, err)
    }).finally(() => {
        adding.value = false
    })
}

// ---- sync with the other household member: upstream auto sync, plus an immediate sync when the screen comes back ----
function autoSyncLoop() {
    clearTimeout(useShoppingStore().autoSyncTimeoutId)
    const timeout = Math.max(useUserPreferenceStore().userSettings.shoppingAutoSync ?? 0, 1) * 1000
    useShoppingStore().autoSyncTimeoutId = window.setTimeout(() => {
        if ((useUserPreferenceStore().userSettings.shoppingAutoSync ?? 0) > 0) {
            useShoppingStore().autoSync()
        }
        autoSyncLoop()
    }, timeout)
}

function onVisibilityChange() {
    const visible = document.visibilityState === 'visible'
    useShoppingStore().autoSyncHasFocus = visible
    if (visible && useShoppingStore().initialized) {
        useShoppingStore().autoSync()
    }
}

onMounted(() => {
    document.addEventListener('visibilitychange', onVisibilityChange)
    useShoppingStore().autoSyncHasFocus = document.visibilityState === 'visible'
    useShoppingStore().refreshFromAPI()
    useShoppingStore().loadShoppingLists()
    if (useUserPreferenceStore().deviceSettings.shopping_selected_supermarket != null) {
        // aisle order may have changed on another device
        new ApiApi().apiSupermarketRetrieve({id: useUserPreferenceStore().deviceSettings.shopping_selected_supermarket!.id!}).then(r => {
            useUserPreferenceStore().deviceSettings.shopping_selected_supermarket = r
        }).catch(() => {
        })
    }
    autoSyncLoop()
})

onBeforeUnmount(() => {
    document.removeEventListener('visibilitychange', onVisibilityChange)
    clearTimeout(useShoppingStore().autoSyncTimeoutId)
})
</script>

<style scoped>
.fork-shopping__title {
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
}

.fork-shopping__aisle {
    font-size: var(--fork-text-sm);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    padding: var(--fork-space-2) 0;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-shopping__row {
    padding-inline: 0 !important;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-shopping__food {
    font-size: var(--fork-text-md);
    white-space: normal;
}

.fork-shopping__amount {
    font-size: var(--fork-text-sm);
    opacity: 1;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-shopping__box {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    margin-inline-end: var(--fork-space-4);
    border: 2px solid rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    border-radius: 6px;
}

.fork-shopping__box--checked {
    background: rgb(var(--v-theme-secondary));
    border-color: rgb(var(--v-theme-secondary));
    color: rgb(var(--v-theme-on-secondary));
}

.fork-shopping__row--done .fork-shopping__food {
    text-decoration: line-through;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-shopping__empty, .fork-shopping__done {
    display: flex;
    align-items: center;
    margin-top: var(--fork-space-4);
    padding: var(--fork-space-4);
    border-radius: var(--fork-radius-card);
    border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-shopping__empty {
    flex-direction: column;
    text-align: center;
    padding: var(--fork-space-8) var(--fork-space-4);
}

.fork-shopping__done {
    background: rgba(var(--v-theme-secondary), 0.12);
    font-size: var(--fork-text-md);
    font-weight: 600;
}

/* keep the undo bar above the bottom navigation */
.fork-shopping__snackbar :deep(.v-snackbar__wrapper) {
    margin-bottom: calc(var(--fork-bottom-nav) + var(--fork-space-2));
}

@media (min-width: 960px) {
    .fork-shopping__snackbar :deep(.v-snackbar__wrapper) {
        margin-bottom: var(--fork-space-4);
    }
}
</style>
