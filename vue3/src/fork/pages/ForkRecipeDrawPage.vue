<template>
    <!-- Draw X recipes at random: a short list for the coming days; remove or replace one at a time -->
    <v-container class="fork-draw" max-width="640">
        <div class="d-flex align-center ga-2 mb-2">
            <v-btn icon variant="text" size="48" :aria-label="$t('Back')" :to="{name: 'StartPage'}">
                <v-icon icon="fa-solid fa-arrow-left"></v-icon>
            </v-btn>
            <h1 class="fork-draw__title flex-grow-1">{{ $t('Fork_Draw') }}</h1>
        </div>

        <!-- how many, then draw -->
        <div class="fork-draw__setup">
            <span class="text-body-1 flex-grow-1">{{ $t('Fork_Draw_How_Many') }}</span>
            <v-btn icon variant="tonal" size="44" :disabled="drawSize <= 1" :aria-label="$t('Fork_Draw_Less')" @click="drawSize = Math.max(1, drawSize - 1)">
                <v-icon icon="fa-solid fa-minus" size="14"></v-icon>
            </v-btn>
            <span class="fork-draw__size" aria-live="polite">{{ drawSize }}</span>
            <v-btn icon variant="tonal" size="44" :disabled="drawSize >= 14" :aria-label="$t('Fork_Draw_More')" @click="drawSize = Math.min(14, drawSize + 1)">
                <v-icon icon="fa-solid fa-plus" size="14"></v-icon>
            </v-btn>
        </div>
        <p class="text-body-2 text-medium-emphasis mt-2" v-if="activeFilterCount > 0">{{ $t('Fork_Draw_With_Filters', {n: activeFilterCount}, activeFilterCount) }}</p>
        <v-btn color="primary" variant="flat" size="x-large" block class="mt-3" prepend-icon="fa-solid fa-dice" :loading="drawing" @click="drawAll()">
            {{ drawnRecipes.length ? $t('Fork_Draw_Again') : $t('Fork_Draw_Go', {n: drawSize}, drawSize) }}
        </v-btn>

        <v-alert v-if="error" type="error" variant="tonal" class="mt-4" :text="$t('Fork_Load_Error')"></v-alert>

        <template v-if="drawnRecipes.length">
            <h2 class="fork-draw__section mt-6">{{ $t('Fork_Draw_List', {n: drawnRecipes.length}, drawnRecipes.length) }}</h2>
            <v-list class="py-0" bg-color="transparent">
                <v-list-item v-for="r in drawnRecipes" :key="r.id" class="fork-draw__row" min-height="72">
                    <template #prepend>
                        <v-avatar size="56" rounded="lg" class="me-3 fork-draw__thumb">
                            <v-img v-if="r.image" :src="r.image" cover :alt="r.name"></v-img>
                            <v-icon v-else icon="$recipes" size="22"></v-icon>
                        </v-avatar>
                    </template>
                    <v-list-item-title class="fork-draw__name">
                        <router-link :to="{name: 'RecipeViewPage', params: {id: r.id}}" class="fork-draw__link">{{ r.name }}</router-link>
                    </v-list-item-title>
                    <v-list-item-subtitle v-if="r.totalTime > 0">
                        <v-icon icon="fa-regular fa-clock" size="12" class="me-1"></v-icon>{{ r.totalTime }} {{ $t('min') }}
                    </v-list-item-subtitle>
                    <template #append>
                        <v-btn icon variant="text" size="44" :aria-label="$t('Fork_Draw_Replace', {name: r.name})" :loading="replacing == r.id"
                               :disabled="busy && replacing != r.id" @click="replace(r)">
                            <v-icon icon="fa-solid fa-shuffle" size="16"></v-icon>
                        </v-btn>
                        <v-btn icon variant="text" size="44" :aria-label="$t('Fork_Draw_Remove', {name: r.name})" :disabled="busy" @click="remove(r)">
                            <v-icon icon="fa-solid fa-xmark" size="18"></v-icon>
                        </v-btn>
                    </template>
                </v-list-item>
            </v-list>
            <p class="text-body-2 text-medium-emphasis mt-2" v-if="exhausted">{{ $t('Fork_Draw_No_More') }}</p>

            <!-- the drawn week goes to the meal plan (one recipe a day) and/or the shopping list -->
            <div class="fork-draw__use mt-4">
                <v-btn color="primary" variant="flat" size="large" prepend-icon="fa-solid fa-calendar-plus" :disabled="busy" @click="openPlan()">{{ $t('Fork_Draw_To_Plan') }}</v-btn>
                <v-btn color="primary" variant="outlined" size="large" prepend-icon="$shopping" :disabled="busy" @click="openShop()">{{ $t('Fork_Draw_To_Shopping') }}</v-btn>
            </div>
            <div class="d-flex flex-wrap ga-2 mt-4">
                <v-btn variant="tonal" size="large" prepend-icon="fa-solid fa-plus" :loading="adding" :disabled="busy && !adding" @click="addOne()">{{ $t('Fork_Draw_Add_One') }}</v-btn>
                <v-spacer></v-spacer>
                <v-btn variant="text" size="large" @click="clear()">{{ $t('Fork_Draw_Clear') }}</v-btn>
            </div>
        </template>
        <p v-else-if="!drawing && !error" class="text-body-2 text-medium-emphasis mt-6 text-center">{{ $t('Fork_Draw_Help') }}</p>
    </v-container>

    <v-bottom-sheet v-model="planSheet" max-width="640">
        <v-card class="fork-draw__plan" :title="$t('Fork_Draw_To_Plan')">
            <v-card-text>
                <v-text-field v-model="planStart" type="date" :label="$t('Fork_Draw_First_Day')" hide-details class="mb-4"></v-text-field>
                <v-select v-model="planMealType" :items="mealTypes" item-title="name" return-object :label="$t('Meal_Type')" hide-details class="mb-2"
                          :loading="mealTypesLoading" no-data-text=""></v-select>
                <v-alert v-if="mealTypesLoadError" type="error" variant="tonal" class="mb-2" :text="$t('Fork_Load_Error')">
                    <div class="mt-2"><v-btn variant="tonal" @click="loadMealTypes()">{{ $t('Fork_Retry') }}</v-btn></div>
                </v-alert>
                <v-alert v-else-if="mealTypesEmpty" type="info" variant="tonal" class="mb-2" :text="$t('Fork_Draw_No_Meal_Type')">
                    <div class="mt-2">
                        <v-btn variant="flat" color="primary" :loading="creatingMealType" @click="createDinner()">{{ $t('Fork_Draw_Create_Dinner') }}</v-btn>
                    </div>
                </v-alert>
                <v-switch v-model="planShopping" :label="$t('Fork_Draw_Plan_Shopping')" color="primary" hide-details inset></v-switch>
                <v-alert v-if="planPending" type="warning" variant="tonal" class="mt-2"
                         :text="$t('Fork_Draw_Partial', {done: planOffset, n: planOffset + planPending.length})"></v-alert>
                <v-list density="compact" class="py-0 mt-2" bg-color="transparent">
                    <v-list-item v-for="(r, i) in planList" :key="r.id" class="px-0" min-height="36">
                        <template #prepend><span class="fork-draw__day">{{ dayLabel(planOffset + i) }}</span></template>
                        <v-list-item-title class="text-body-2">{{ r.name }}</v-list-item-title>
                    </v-list-item>
                </v-list>
            </v-card-text>
            <v-card-actions class="pa-4">
                <v-btn variant="text" size="large" @click="planSheet = false">{{ $t('Cancel') }}</v-btn>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="flat" size="large" :disabled="!planMealType || !planStart || planList.length == 0" :loading="planning" @click="plan()">
                    {{ $t('Fork_Draw_Plan_N', {n: planList.length}, planList.length) }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-bottom-sheet>

    <v-dialog v-model="shopConfirm" max-width="440">
        <v-card class="fork-draw__shop">
            <v-card-title class="text-wrap">{{ $t('Fork_Draw_Shop_Title', {n: shopList.length}, shopList.length) }}</v-card-title>
            <v-card-text class="pt-1">
                <p>{{ $t('Fork_Draw_Shop_Text') }}</p>
                <v-alert v-if="alreadyShopped > 0" type="warning" variant="tonal" class="mt-3"
                         :text="$t('Fork_Draw_Already_Shopped', {n: alreadyShopped}, alreadyShopped)"></v-alert>
                <v-alert v-if="shopPending" type="warning" variant="tonal" class="mt-3"
                         :text="$t('Fork_Draw_Partial', {done: shopDone, n: shopDone + shopPending.length})"></v-alert>
            </v-card-text>
            <v-card-actions class="pa-4">
                <v-spacer></v-spacer>
                <v-btn variant="text" size="large" @click="shopConfirm = false">{{ $t('Cancel') }}</v-btn>
                <v-btn color="primary" variant="flat" size="large" :loading="shopping" :disabled="shopList.length == 0" @click="shop()">{{ $t('Add') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <v-snackbar v-model="doneSnackbar" :timeout="6000" location="bottom" class="fork-draw__snackbar">
        {{ doneText }}
        <template #actions>
            <v-btn variant="text" color="primary" size="large" :to="doneLink">{{ $t('Fork_Draw_See') }}</v-btn>
        </template>
    </v-snackbar>

    <v-snackbar v-model="undoSnackbar" :timeout="4000" location="bottom" class="fork-draw__snackbar">
        {{ undoText }}
        <template #actions>
            <v-btn variant="text" color="primary" size="large" @click="undo()">{{ $t('Fork_Undo') }}</v-btn>
        </template>
    </v-snackbar>
</template>

<script setup lang="ts">
import {computed, ref} from "vue";
import {useI18n} from "vue-i18n";
import {ApiApi, MealType} from "@/openapi";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";
import {DrawnRecipe, drawnRecipes, drawRecipes, drawSize, planDay, planDraw, shopDraw} from "@/fork/recipeDraw";
import {forkHomeFilters} from "@/fork/homeFilters";

const {t, d} = useI18n()

const drawing = ref(false)
const adding = ref(false)
const replacing = ref<number | null>(null)
/** one change of the list at a time: two quick taps could otherwise draw the same recipe twice */
const busy = computed(() => drawing.value || adding.value || replacing.value != null)
const error = ref(false)
/** no other recipe matches: replace and add have nothing left to give */
const exhausted = ref(false)
const undoSnackbar = ref(false)
const undoText = ref('')
let lastState: DrawnRecipe[] | null = null

const activeFilterCount = computed(() => forkHomeFilters.have.length + forkHomeFilters.keywords.length + (forkHomeFilters.maxTime ? 1 : 0))

function remember(text: string) {
    lastState = [...drawnRecipes.value]
    undoText.value = text
    doneSnackbar.value = false
    undoSnackbar.value = true
}

function undo() {
    if (lastState) drawnRecipes.value = lastState
    lastState = null
    undoSnackbar.value = false
}

async function run<T>(flag: typeof drawing, action: () => Promise<T>) {
    flag.value = true
    error.value = false
    try {
        return await action()
    } catch {
        error.value = true
    } finally {
        flag.value = false
    }
}

function drawAll() {
    if (busy.value) return
    run(drawing, async () => {
        const drawn = await drawRecipes(drawSize.value)
        if (drawnRecipes.value.length) remember(t('Fork_Draw_Replaced_All'))
        drawnRecipes.value = drawn
        exhausted.value = drawn.length < drawSize.value
    })
}

function remove(r: DrawnRecipe) {
    if (busy.value) return
    remember(t('Fork_Draw_Removed', {name: r.name}))
    drawnRecipes.value = drawnRecipes.value.filter(x => x.id != r.id)
}

/** another recipe in the same place, none already in the list */
function replace(r: DrawnRecipe) {
    if (busy.value) return
    replacing.value = r.id
    run(ref(false), async () => {
        const [next] = await drawRecipes(1, drawnRecipes.value.map(x => x.id))
        if (!next || drawnRecipes.value.some(x => x.id == next.id)) {
            exhausted.value = true
            return
        }
        remember(t('Fork_Draw_Replaced', {name: r.name}))
        drawnRecipes.value = drawnRecipes.value.map(x => x.id == r.id ? next : x)
    }).finally(() => {
        replacing.value = null
    })
}

function addOne() {
    if (busy.value) return
    run(adding, async () => {
        const [next] = await drawRecipes(1, drawnRecipes.value.map(x => x.id))
        if (next && !drawnRecipes.value.some(x => x.id == next.id)) drawnRecipes.value = [...drawnRecipes.value, next]
        else exhausted.value = true
    })
}

// ---- to the meal plan / the shopping list ----
const planSheet = ref(false)
const planStart = ref('')
const planMealType = ref<MealType | null>(null)
const planShopping = ref(true)
const planning = ref(false)
/** after a failure part way: what is left to plan, and how many days are already planned */
const planPending = ref<DrawnRecipe[] | null>(null)
const planOffset = ref(0)
const planList = computed(() => planPending.value ?? drawnRecipes.value)
const mealTypes = ref<MealType[]>([])
const mealTypesLoading = ref(false)
const mealTypesEmpty = ref(false)
const mealTypesLoadError = ref(false)
const shopConfirm = ref(false)
const shopping = ref(false)
const shopPending = ref<DrawnRecipe[] | null>(null)
const shopDone = ref(0)
const shopList = computed(() => shopPending.value ?? drawnRecipes.value)
/** recipes already sent to the shopping list from this page (with the plan or alone): sending them again doubles them */
const shoppedIds = ref(new Set<number>())
const alreadyShopped = computed(() => shopList.value.filter(r => shoppedIds.value.has(r.id)).length)
const doneSnackbar = ref(false)
const doneText = ref('')
const doneLink = ref<{ name: string }>({name: 'MealPlanPage'})

function showDone(text: string, link: string) {
    undoSnackbar.value = false
    doneText.value = text
    doneLink.value = {name: link}
    doneSnackbar.value = true
}

function markShopped(recipes: DrawnRecipe[]) {
    shoppedIds.value = new Set([...shoppedIds.value, ...recipes.map(r => r.id)])
}

function isoDay(date: Date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function dayLabel(i: number) {
    return planStart.value ? d(planDay(planStart.value, i), {weekday: 'short', day: 'numeric', month: 'short'}) : ''
}

function loadMealTypes() {
    mealTypesLoading.value = true
    mealTypesLoadError.value = false
    new ApiApi().apiMealTypeList({pageSize: 100}).then(r => {
        mealTypes.value = r.results
        mealTypesEmpty.value = r.results.length == 0
        planMealType.value = r.results.find(m => /d[iî]ner|soir|dinner/i.test(m.name))
            ?? [...r.results].sort((a, b) => (b.time ?? '').localeCompare(a.time ?? ''))[0] ?? null
    }).catch(() => {
        mealTypesLoadError.value = true
    }).finally(() => {
        mealTypesLoading.value = false
    })
}

/** starts today (tomorrow after 21:00, like the "on the menu" card); the evening meal by default */
function openPlan() {
    if (!planPending.value) {
        const start = new Date()
        if (start.getHours() >= 21) start.setDate(start.getDate() + 1)
        planStart.value = isoDay(start)
        planOffset.value = 0
    }
    planSheet.value = true
    if (mealTypes.value.length == 0 && !mealTypesLoading.value) loadMealTypes()
}

/** a new space has no meal type: one tap creates the evening meal */
const creatingMealType = ref(false)

function createDinner() {
    if (creatingMealType.value) return
    creatingMealType.value = true
    new ApiApi().apiMealTypeCreate({mealType: {name: t('Fork_Draw_Dinner'), time: '19:30', order: 0} as MealType}).then(m => {
        mealTypes.value = [m]
        planMealType.value = m
        mealTypesEmpty.value = false
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.CREATE_ERROR, err)
    }).finally(() => {
        creatingMealType.value = false
    })
}

/** plans what is left; after a failure the sheet stays open and a retry sends only the rest (no duplicate meals) */
function plan() {
    if (!planMealType.value || !planStart.value || planning.value) return
    planning.value = true
    const recipes = [...planList.value]
    const withShopping = planShopping.value
    planDraw(recipes, planStart.value, planMealType.value, withShopping, planOffset.value).then(r => {
        if (withShopping) markShopped(recipes.slice(0, r.done))
        planOffset.value += r.done
        if (r.error) {
            planPending.value = recipes.slice(r.done)
            useMessageStore().addError(ErrorMessageType.CREATE_ERROR, r.error)
            return
        }
        const total = planOffset.value
        planPending.value = null
        planOffset.value = 0
        planSheet.value = false
        showDone(t('Fork_Draw_Planned', {n: total}, total), 'MealPlanPage')
    }).finally(() => {
        planning.value = false
    })
}

function openShop() {
    if (!shopPending.value) shopDone.value = 0
    shopConfirm.value = true
}

function shop() {
    if (shopping.value) return
    shopping.value = true
    const recipes = [...shopList.value]
    shopDraw(recipes).then(r => {
        markShopped(recipes.slice(0, r.done))
        shopDone.value += r.done
        if (r.error) {
            shopPending.value = recipes.slice(r.done)
            useMessageStore().addError(ErrorMessageType.CREATE_ERROR, r.error)
            return
        }
        const total = shopDone.value
        shopPending.value = null
        shopConfirm.value = false
        showDone(t('Fork_Draw_Shopped', {n: total}, total), 'ShoppingListPage')
    }).finally(() => {
        shopping.value = false
    })
}

function clear() {
    remember(t('Fork_Draw_Cleared'))
    drawnRecipes.value = []
    exhausted.value = false
}
</script>

<style scoped>
.fork-draw__title {
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
}

.fork-draw__setup {
    display: flex;
    align-items: center;
    gap: var(--fork-space-2);
}

.fork-draw__size {
    min-width: 32px;
    text-align: center;
    font-size: var(--fork-text-lg);
    font-weight: 600;
}

.fork-draw__section {
    font-size: var(--fork-text-sm);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    padding-bottom: var(--fork-space-2);
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-draw__row {
    padding-inline: 0 !important;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-draw__name {
    font-size: var(--fork-text-md);
    font-weight: 600;
    white-space: normal;
}

.fork-draw__use {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--fork-space-2);
}

.fork-draw__use :deep(.v-btn__content) {
    white-space: normal;
    line-height: 1.2;
}

.fork-draw__day {
    display: inline-block;
    min-width: 96px;
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-draw__link {
    color: inherit;
    text-decoration: none;
    display: inline-block;
    min-height: 24px;
}

.fork-draw__link:hover {
    text-decoration: underline;
}

.fork-draw__thumb {
    background: rgb(var(--v-theme-surface-variant));
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

/* keep the undo bar above the bottom navigation */
.fork-draw__snackbar :deep(.v-snackbar__wrapper) {
    margin-bottom: calc(var(--fork-bottom-nav) + var(--fork-space-2));
}

@media (min-width: 960px) {
    .fork-draw__snackbar :deep(.v-snackbar__wrapper) {
        margin-bottom: var(--fork-space-4);
    }
}
</style>
