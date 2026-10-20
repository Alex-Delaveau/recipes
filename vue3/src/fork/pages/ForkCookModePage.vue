<template>
    <!-- Cook mode (DESIGN.md): one step per screen, full screen, large type, swipe or two big buttons, screen kept on -->
    <div class="fork-cook" ref="swipeArea">
        <header class="fork-cook__bar">
            <v-btn icon variant="text" size="48" :aria-label="$t('Fork_Cook_Exit')" @click="exit()">
                <v-icon icon="$close"></v-icon>
            </v-btn>
            <div class="fork-cook__heading">
                <div class="fork-cook__recipe">{{ recipe?.name }}</div>
                <div class="fork-cook__progress-label" v-if="screens.length">{{ $t('Fork_Step_Of', {n: current + 1, total: screens.length}) }}</div>
            </div>
            <span class="fork-cook__servings" v-if="recipe">
                <v-icon icon="fa-solid fa-user-group" size="16" class="me-1"></v-icon>{{ servings }}
            </span>
        </header>
        <v-progress-linear :model-value="screens.length ? (current + 1) / screens.length * 100 : 0" color="primary" height="4"></v-progress-linear>

        <main class="fork-cook__content" v-if="recipe && screen" :key="current" aria-live="polite">
            <template v-if="screen.kind == 'ingredients'">
                <h1 class="fork-cook__title">{{ $t('Fork_Cook_Get_Ready') }}</h1>
                <template v-for="g in groups" :key="g.title ?? 'all'">
                    <h2 class="fork-cook__group" v-if="g.title">{{ g.title }}</h2>
                    <fork-ingredient-list :ingredients="g.ingredients" :factor="factor" large></fork-ingredient-list>
                </template>
            </template>
            <template v-else>
                <h1 class="fork-cook__title">
                    <span class="fork-cook__number">{{ screen.number }}</span>
                    {{ screen.step.name }}
                </h1>
                <v-chip v-if="screen.step.time" variant="tonal" size="large" prepend-icon="fas fa-stopwatch" class="mb-4">{{ screen.step.time }} {{ $t('min') }}</v-chip>
                <fork-ingredient-list v-if="screen.step.ingredients.length && !singleList" :ingredients="screen.step.ingredients" :factor="factor" large
                                      class="fork-cook__step-ingredients"></fork-ingredient-list>
                <div class="fork-cook__instructions markdown-body">
                    <instructions :instructions_html="screen.step.instructionsMarkdown ?? ''" :ingredient_factor="factor"></instructions>
                </div>
            </template>
        </main>
        <main class="fork-cook__content" v-else-if="error">
            <v-alert type="error" variant="tonal" :text="$t('Fork_Load_Error')"></v-alert>
        </main>
        <main class="fork-cook__content" v-else>
            <v-skeleton-loader type="heading, paragraph, paragraph"></v-skeleton-loader>
        </main>

        <footer class="fork-cook__nav">
            <v-btn size="x-large" variant="tonal" class="flex-grow-1" :disabled="current == 0" prepend-icon="fa-solid fa-arrow-left" @click="previous()">
                {{ $t('Fork_Previous') }}
            </v-btn>
            <v-btn size="x-large" color="primary" variant="flat" class="flex-grow-1" append-icon="fa-solid fa-arrow-right" @click="next()" v-if="!isLast">
                {{ $t('Next') }}
            </v-btn>
            <v-btn size="x-large" color="primary" variant="flat" class="flex-grow-1" append-icon="fa-solid fa-check" @click="exit()" v-else>
                {{ $t('Fork_Cook_Done') }}
            </v-btn>
        </footer>
    </div>
</template>

<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref, useTemplateRef} from "vue";
import {useRoute, useRouter} from "vue-router";
import {useI18n} from "vue-i18n";
import {onKeyStroke, useSwipe, useTitle, useWakeLock} from "@vueuse/core";
import {ApiApi, Recipe, Step} from "@/openapi";
// @ts-ignore upstream component written in plain JS
import Instructions from "@/components/display/Instructions.vue";
import ForkIngredientList from "@/fork/components/ForkIngredientList.vue";
import {ingredientFactor, ingredientGroups} from "@/fork/recipe";

type CookScreen = { kind: 'ingredients' } | { kind: 'step', step: Step, number: number }

const props = defineProps({
    id: {type: String, required: true},
})

const route = useRoute()
const router = useRouter()
const {t} = useI18n()
const title = useTitle()
const {request, release} = useWakeLock()

const recipe = ref<Recipe | null>(null)
const error = ref(false)
const current = ref(0)
const servings = ref(1)
const swipeArea = useTemplateRef<HTMLElement>('swipeArea')

const factor = computed(() => recipe.value ? ingredientFactor(recipe.value, servings.value) : 1)
const groups = computed(() => recipe.value ? ingredientGroups(recipe.value, t) : [])
const cookSteps = computed(() => recipe.value ? recipe.value.steps.filter(s => s.instruction || s.ingredients.length) : [])
/** a "get ready" screen with every ingredient, unless the recipe has a single step (it shows them already) */
const prepScreen = computed(() => cookSteps.value.length > 1 && groups.value.some(g => g.ingredients.length))
/** single ingredient list (fork recipes): ingredients are all on the first screen, not repeated in the steps */
const singleList = computed(() => prepScreen.value && groups.value.length == 1)

const screens = computed<CookScreen[]>(() => {
    if (!recipe.value) return []
    const list: CookScreen[] = []
    if (prepScreen.value) list.push({kind: 'ingredients'})
    cookSteps.value.forEach((step, index) => {
        list.push({kind: 'step', step, number: index + 1})
    })
    return list
})
const screen = computed(() => screens.value[current.value])
const isLast = computed(() => current.value >= screens.value.length - 1)

function next() {
    if (!isLast.value) current.value++
}

function previous() {
    if (current.value > 0) current.value--
}

function exit() {
    router.push({name: 'RecipeViewPage', params: {id: props.id}, query: servings.value != recipe.value?.servings ? {servings: servings.value} : {}})
}

const {direction} = useSwipe(swipeArea, {
    threshold: 60,
    onSwipeEnd() {
        if (direction.value == 'left') next()
        if (direction.value == 'right') previous()
    },
})
onKeyStroke('ArrowRight', () => next())
onKeyStroke('ArrowLeft', () => previous())

onMounted(() => {
    // the browser may refuse (hidden tab, low battery, no permission): not an error for the user
    request("screen").catch(() => {})
    new ApiApi().apiRecipeRetrieve({id: Number(props.id)}).then(r => {
        recipe.value = r
        title.value = r.name
        const fromQuery = parseInt(String(route.query.servings ?? ''), 10)
        servings.value = fromQuery > 0 ? fromQuery : (r.servings ?? 1)
    }).catch(() => {
        error.value = true
    })
})

onBeforeUnmount(() => {
    release()
})
</script>

<style scoped>
.fork-cook {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    min-height: 100dvh;
    background: rgb(var(--v-theme-background));
    touch-action: pan-y;
}

.fork-cook__bar {
    display: flex;
    align-items: center;
    gap: var(--fork-space-2);
    padding: var(--fork-space-2) var(--fork-space-4) var(--fork-space-2) var(--fork-space-2);
    padding-top: calc(var(--fork-space-2) + env(safe-area-inset-top));
}

.fork-cook__heading {
    flex: 1 1 auto;
    min-width: 0;
}

.fork-cook__recipe {
    font-size: var(--fork-text-md);
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.fork-cook__progress-label, .fork-cook__servings {
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-cook__content {
    flex: 1 1 auto;
    width: 100%;
    max-width: 760px;
    margin: 0 auto;
    padding: var(--fork-space-6) var(--fork-space-4);
}

.fork-cook__title {
    display: flex;
    align-items: center;
    gap: var(--fork-space-3);
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
    margin-bottom: var(--fork-space-4);
}

.fork-cook__number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 40px;
    height: 40px;
    border-radius: 50%;
    background: rgb(var(--v-theme-primary));
    color: rgb(var(--v-theme-on-primary));
    font-size: var(--fork-text-lg);
}

.fork-cook__group {
    font-size: var(--fork-text-md);
    font-weight: 600;
    margin-top: var(--fork-space-4);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-cook__step-ingredients {
    margin-bottom: var(--fork-space-4);
    padding: 0 var(--fork-space-4);
    border-radius: var(--fork-radius-card);
    background: rgb(var(--v-theme-surface-variant));
}

/* the step text: 24 px (DESIGN.md, cook mode) */
.fork-cook__instructions {
    font-size: var(--fork-text-xl);
    line-height: 1.5;
}

.fork-cook__instructions :deep(p) {
    margin: 0 0 var(--fork-space-4);
}

.fork-cook__nav {
    position: sticky;
    bottom: 0;
    display: flex;
    gap: var(--fork-space-3);
    padding: var(--fork-space-3) var(--fork-space-4);
    padding-bottom: calc(var(--fork-space-3) + env(safe-area-inset-bottom));
    background: rgb(var(--v-theme-background));
    border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-cook__nav .v-btn {
    min-height: 56px;
}
</style>
