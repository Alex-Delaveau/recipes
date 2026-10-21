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
            {{ drawnRecipes.length ? $t('Fork_Draw_Again') : $t('Fork_Draw_Go', {n: drawSize}) }}
        </v-btn>

        <v-alert v-if="error" type="error" variant="tonal" class="mt-4" :text="$t('Fork_Load_Error')"></v-alert>

        <template v-if="drawnRecipes.length">
            <h2 class="fork-draw__section mt-6">{{ $t('Fork_Draw_List', {n: drawnRecipes.length}, drawnRecipes.length) }}</h2>
            <v-list class="py-0" bg-color="transparent">
                <v-list-item v-for="r in drawnRecipes" :key="r.id" class="fork-draw__row" min-height="72" :to="{name: 'RecipeViewPage', params: {id: r.id}}">
                    <template #prepend>
                        <v-avatar size="56" rounded="lg" class="me-3 fork-draw__thumb">
                            <v-img v-if="r.image" :src="r.image" cover :alt="r.name"></v-img>
                            <v-icon v-else icon="$recipes" size="22"></v-icon>
                        </v-avatar>
                    </template>
                    <v-list-item-title class="fork-draw__name">{{ r.name }}</v-list-item-title>
                    <v-list-item-subtitle v-if="r.totalTime > 0">
                        <v-icon icon="fa-regular fa-clock" size="12" class="me-1"></v-icon>{{ r.totalTime }} {{ $t('min') }}
                    </v-list-item-subtitle>
                    <template #append>
                        <v-btn icon variant="text" size="44" :aria-label="$t('Fork_Draw_Replace', {name: r.name})" :loading="replacing == r.id"
                               @click.prevent.stop="replace(r)">
                            <v-icon icon="fa-solid fa-shuffle" size="16"></v-icon>
                        </v-btn>
                        <v-btn icon variant="text" size="44" :aria-label="$t('Fork_Draw_Remove', {name: r.name})" @click.prevent.stop="remove(r)">
                            <v-icon icon="fa-solid fa-xmark" size="18"></v-icon>
                        </v-btn>
                    </template>
                </v-list-item>
            </v-list>
            <p class="text-body-2 text-medium-emphasis mt-2" v-if="exhausted">{{ $t('Fork_Draw_No_More') }}</p>
            <div class="d-flex flex-wrap ga-2 mt-4">
                <v-btn variant="tonal" size="large" prepend-icon="fa-solid fa-plus" :loading="adding" @click="addOne()">{{ $t('Fork_Draw_Add_One') }}</v-btn>
                <v-spacer></v-spacer>
                <v-btn variant="text" size="large" @click="clear()">{{ $t('Fork_Draw_Clear') }}</v-btn>
            </div>
        </template>
        <p v-else-if="!drawing && !error" class="text-body-2 text-medium-emphasis mt-6 text-center">{{ $t('Fork_Draw_Help') }}</p>
    </v-container>

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
import {DrawnRecipe, drawnRecipes, drawRecipes, drawSize} from "@/fork/recipeDraw";
import {forkHomeFilters} from "@/fork/homeFilters";

const {t} = useI18n()

const drawing = ref(false)
const adding = ref(false)
const replacing = ref<number | null>(null)
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
    run(drawing, async () => {
        const drawn = await drawRecipes(drawSize.value)
        if (drawnRecipes.value.length) remember(t('Fork_Draw_Replaced_All'))
        drawnRecipes.value = drawn
        exhausted.value = drawn.length < drawSize.value
    })
}

function remove(r: DrawnRecipe) {
    remember(t('Fork_Draw_Removed', {name: r.name}))
    drawnRecipes.value = drawnRecipes.value.filter(x => x.id != r.id)
}

/** another recipe in the same place, none already in the list */
function replace(r: DrawnRecipe) {
    replacing.value = r.id
    run(ref(false), async () => {
        const [next] = await drawRecipes(1, drawnRecipes.value.map(x => x.id))
        if (!next) {
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
    run(adding, async () => {
        const [next] = await drawRecipes(1, drawnRecipes.value.map(x => x.id))
        if (next) drawnRecipes.value = [...drawnRecipes.value, next]
        else exhausted.value = true
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
