<template>
    <!-- "This week": the recipes drawn at random, first on the home; folds to one line (kept on this device) -->
    <section class="fork-week">
        <div class="fork-week__head">
            <button type="button" class="fork-week__toggle" :aria-expanded="open" aria-controls="fork-week-body" @click="open = !open">
                <span class="fork-week__titles">
                    <span class="fork-week__title">{{ $t('Fork_Week') }}</span>
                    <span class="fork-week__sub">{{ drawnRecipes.length ? $t('Fork_Week_Count', {n: drawnRecipes.length}, drawnRecipes.length) : $t('Fork_Week_Empty_Short') }}<template
                        v-if="drawnRecipes.length && price"> · ≈ {{ euros(price.total, locale) }}</template></span>
                </span>
                <v-icon :icon="open ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'" size="16"></v-icon>
            </button>
            <v-btn icon variant="text" size="44" :to="{name: 'ForkRecipeDrawPage'}" :aria-label="$t('Fork_Week_Manage')">
                <v-icon icon="fa-solid fa-dice" size="18"></v-icon>
            </v-btn>
        </div>

        <!-- folded: the dishes at a glance -->
        <div v-if="!open && drawnRecipes.length" class="fork-week__strip" aria-hidden="true">
            <fork-recipe-thumb v-for="r in drawnRecipes.slice(0, 7)" :key="r.id" :name="r.name" :image="r.image" :size="36"></fork-recipe-thumb>
            <span v-if="drawnRecipes.length > 7" class="fork-week__more">+{{ drawnRecipes.length - 7 }}</span>
        </div>

        <div v-if="open" id="fork-week-body">
            <template v-if="drawnRecipes.length">
                <div v-for="r in drawnRecipes" :key="r.id" class="fork-week__row">
                    <fork-recipe-thumb :name="r.name" :image="r.image" :size="44"></fork-recipe-thumb>
                    <router-link :to="{name: 'RecipeViewPage', params: {id: r.id}}" class="fork-week__name">
                        <span class="fork-week__recipe">{{ r.name }}</span>
                        <span class="fork-week__time" v-if="r.totalTime > 0">{{ r.totalTime }} {{ $t('min') }}</span>
                    </router-link>
                    <v-btn icon variant="text" size="44" :aria-label="$t('Fork_Draw_Replace', {name: r.name})" :loading="replacing == r.id"
                           :disabled="busy && replacing != r.id" @click="replace(r)">
                        <v-icon icon="fa-solid fa-shuffle" size="15"></v-icon>
                    </v-btn>
                    <v-btn icon variant="text" size="44" :aria-label="$t('Fork_Draw_Remove', {name: r.name})" :disabled="busy" @click="remove(r)">
                        <v-icon icon="fa-solid fa-xmark" size="17"></v-icon>
                    </v-btn>
                </div>
                <p class="fork-week__note" v-if="exhausted">{{ $t('Fork_Draw_No_More') }}</p>
                <fork-price-summary v-if="price" class="mt-2" compact :total="price.total" :missing="price.missing"
                                    :label="$t('Fork_Price_These_Dishes', {n: drawnRecipes.length}, drawnRecipes.length)"></fork-price-summary>
                <div class="fork-week__use">
                    <v-btn color="primary" variant="flat" size="large" prepend-icon="fa-solid fa-calendar-plus" :disabled="busy"
                           :to="{name: 'ForkRecipeDrawPage', query: {action: 'plan'}}" :aria-label="$t('Fork_Draw_To_Plan')">{{ $t('Fork_Week_To_Plan') }}</v-btn>
                    <v-btn color="primary" variant="outlined" size="large" prepend-icon="$shopping" :disabled="busy"
                           :to="{name: 'ForkRecipeDrawPage', query: {action: 'shop'}}" :aria-label="$t('Fork_Draw_To_Shopping')">{{ $t('Fork_Week_To_Shopping') }}</v-btn>
                </div>
                <div class="fork-week__more-actions">
                    <v-btn variant="text" size="large" prepend-icon="fa-solid fa-plus" :loading="adding" :disabled="busy && !adding" @click="addOne()">{{ $t('Fork_Draw_Add_One') }}</v-btn>
                    <v-btn variant="text" size="large" prepend-icon="fa-solid fa-dice" :loading="drawing" :disabled="busy && !drawing" @click="drawAll()">{{ $t('Fork_Draw_Again') }}</v-btn>
                </div>
            </template>
            <template v-else>
                <p class="fork-week__note">{{ $t('Fork_Week_Empty') }}</p>
                <v-btn color="primary" variant="flat" size="large" block prepend-icon="fa-solid fa-dice" :loading="drawing" @click="drawAll()">
                    {{ $t('Fork_Draw_Go', {n: drawSize}, drawSize) }}
                </v-btn>
            </template>
            <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mt-3" :text="$t('Fork_Load_Error')"></v-alert>
        </div>
    </section>

    <v-snackbar v-model="undoSnackbar" :timeout="4000" location="bottom" class="fork-week__snackbar">
        {{ undoText }}
        <template #actions>
            <v-btn variant="text" color="primary" size="large" @click="undo()">{{ $t('Fork_Undo') }}</v-btn>
        </template>
    </v-snackbar>
</template>

<script setup lang="ts">
import {computed, ref} from "vue";
import {useStorage} from "@vueuse/core";
import {useI18n} from "vue-i18n";
import {DrawnRecipe, drawnRecipes, drawRecipes, drawSize, useDrawPrice} from "@/fork/recipeDraw";
import {euros} from "@/fork/prices";
import ForkRecipeThumb from "@/fork/components/ForkRecipeThumb.vue";
import ForkPriceSummary from "@/fork/components/ForkPriceSummary.vue";

const {t, locale} = useI18n()
const price = useDrawPrice()

/** unfolded or folded to one line: a choice of this device */
const open = useStorage('fork_week_open', true)

const drawing = ref(false)
const adding = ref(false)
const replacing = ref<number | null>(null)
const busy = computed(() => drawing.value || adding.value || replacing.value != null)
const error = ref(false)
const exhausted = ref(false)
const undoSnackbar = ref(false)
const undoText = ref('')
let lastState: DrawnRecipe[] | null = null

function remember(text: string) {
    lastState = [...drawnRecipes.value]
    undoText.value = text
    undoSnackbar.value = true
}

function undo() {
    if (lastState) drawnRecipes.value = lastState
    lastState = null
    undoSnackbar.value = false
}

async function run(flag: typeof drawing, action: () => Promise<void>) {
    flag.value = true
    error.value = false
    try {
        await action()
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
</script>

<style scoped>
.fork-week {
    padding: var(--fork-space-3) var(--fork-space-4) var(--fork-space-4);
    border-radius: var(--fork-radius-card);
    background: rgb(var(--v-theme-surface-bright));
    border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-week__head {
    display: flex;
    align-items: center;
    gap: var(--fork-space-1);
}

.fork-week__toggle {
    flex: 1;
    min-height: 48px;
    display: flex;
    align-items: center;
    gap: var(--fork-space-2);
    text-align: start;
    color: inherit;
    background: none;
    border: 0;
    padding: 0;
    cursor: pointer;
}

.fork-week__titles {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.fork-week__title {
    font-size: var(--fork-text-lg);
    font-weight: 700;
    line-height: 1.3;
}

.fork-week__sub, .fork-week__time, .fork-week__note, .fork-week__more {
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-week__strip {
    display: flex;
    align-items: center;
    gap: var(--fork-space-2);
    margin-top: var(--fork-space-1);
    overflow: hidden;
}

.fork-week__row {
    display: flex;
    align-items: center;
    gap: var(--fork-space-3);
    min-height: 60px;
    border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-week__name {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    color: inherit;
    text-decoration: none;
    min-height: 44px;
    justify-content: center;
}

.fork-week__recipe {
    font-size: var(--fork-text-md);
    font-weight: 600;
    line-height: 1.3;
}

.fork-week__note {
    margin: var(--fork-space-2) 0;
}

.fork-week__use {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--fork-space-2);
    margin-top: var(--fork-space-3);
}

.fork-week__use :deep(.v-btn__content) {
    white-space: normal;
    line-height: 1.2;
}

.fork-week__more-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    margin-top: var(--fork-space-1);
}

.fork-week__snackbar :deep(.v-snackbar__wrapper) {
    margin-bottom: calc(var(--fork-bottom-nav) + var(--fork-space-2));
}

@media (min-width: 960px) {
    .fork-week__snackbar :deep(.v-snackbar__wrapper) {
        margin-bottom: var(--fork-space-4);
    }
}
</style>
