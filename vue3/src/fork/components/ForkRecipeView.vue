<template>
    <!-- Journey P2 "Cook a recipe": photo, time, servings and ingredients first, then the steps -->
    <div v-if="recipe.name == undefined">
        <v-skeleton-loader type="image" class="fork-recipe__hero-skeleton"></v-skeleton-loader>
        <v-container>
            <v-skeleton-loader type="heading, text, actions"></v-skeleton-loader>
            <v-skeleton-loader type="list-item-two-line, list-item-two-line, list-item-two-line" class="mt-4"></v-skeleton-loader>
        </v-container>
    </div>

    <div v-else class="fork-recipe">
        <v-img v-if="recipe.image" :src="recipe.image" cover :aspect-ratio="16/9" class="fork-recipe__hero" :alt="recipe.name"></v-img>

        <v-container class="fork-recipe__body">
            <v-row>
                <v-col cols="12" md="5" lg="4">
                    <div class="fork-recipe__aside">
                        <div class="d-flex align-start ga-2">
                            <h1 class="fork-recipe__title flex-grow-1">{{ recipe.name }}</h1>
                            <recipe-context-menu :recipe="recipe" :servings="servings" v-if="useUserPreferenceStore().isAuthenticated"></recipe-context-menu>
                        </div>
                        <p class="fork-recipe__description" v-if="recipe.description">{{ recipe.description }}</p>
                        <keywords-component variant="tonal" :keywords="recipe.keywords ?? []" class="mt-2" v-if="recipe.keywords?.length"></keywords-component>

                        <div class="fork-recipe__facts mt-4">
                            <div class="fork-recipe__time" v-if="totalTime(recipe) > 0">
                                <v-icon icon="fa-regular fa-clock" size="18" class="me-2"></v-icon>
                                <div>
                                    <div class="fork-recipe__time-total">{{ totalTime(recipe) }} {{ $t('min') }}</div>
                                    <div class="fork-recipe__time-detail">
                                        {{ $t('Fork_Time_Detail', {work: recipe.workingTime ?? 0, wait: recipe.waitingTime ?? 0}) }}
                                    </div>
                                </div>
                            </div>
                            <fork-servings-stepper v-model="servings" :label="recipe.servingsText || $t('Servings')"></fork-servings-stepper>
                        </div>
                        <!-- estimated price at the servings chosen (M7) -->
                        <fork-price-summary v-if="price" class="fork-recipe__price mt-3" :total="price.total * factor"
                                            :per-serving="servings > 0 ? price.total * factor / servings : null" :missing="price.missing"></fork-price-summary>

                        <div class="d-flex flex-column ga-2 mt-4 d-print-none">
                            <v-btn color="primary" size="x-large" block prepend-icon="fa-solid fa-fire-burner" v-if="hasSteps && !shared"
                                   :to="{name: 'ForkCookModePage', params: {id: recipe.id}, query: {servings: servings}}">
                                {{ $t('Fork_Cook_Mode') }}
                            </v-btn>
                            <v-btn variant="tonal" size="large" block prepend-icon="$shopping" v-if="useUserPreferenceStore().isAuthenticated && !shared"
                                   @click="shoppingSheet = true">
                                {{ $t('Add_to_Shopping') }}
                            </v-btn>
                        </div>

                        <section class="mt-6" v-if="groups.some(g => g.ingredients.length)">
                            <h2 class="fork-recipe__section">{{ $t('Ingredients') }}</h2>
                            <template v-for="g in groups" :key="g.title ?? 'all'">
                                <h3 class="fork-recipe__group" v-if="g.title">{{ g.title }}</h3>
                                <fork-ingredient-list :ingredients="g.ingredients" :factor="factor"></fork-ingredient-list>
                            </template>
                        </section>
                    </div>
                </v-col>

                <v-col cols="12" md="7" lg="8">
                    <section v-if="hasSteps">
                        <h2 class="fork-recipe__section">{{ $t('Steps') }}</h2>
                        <div class="fork-recipe__step" v-for="(step, index) in recipe.steps" :key="step.id">
                            <!-- sub-recipes and attached files keep the upstream step display -->
                            <step-view v-if="step.stepRecipe || step.file" :model-value="step" :step-number="index + 1"
                                       :ingredient-factor="factor"></step-view>
                            <template v-else>
                                <div class="d-flex align-center ga-3 mb-2">
                                    <span class="fork-recipe__step-number">{{ index + 1 }}</span>
                                    <span class="fork-recipe__step-title">{{ step.name }}</span>
                                    <v-chip v-if="step.time" variant="tonal" prepend-icon="fas fa-stopwatch" class="fork-recipe__time-chip"
                                            :aria-label="$t('Fork_Timer_Start_N', {duration: `${step.time} ${$t('min')}`})"
                                            @click="startStepTimer(step.time, step.name, index + 1)">{{ step.time }} {{ $t('min') }}</v-chip>
                                </div>
                                <div class="fork-recipe__instructions markdown-body">
                                    <fork-step-text :html="step.instructionsMarkdown ?? ''" :factor="factor" :recipe-id="recipe.id"
                                                    :recipe-name="recipe.name" :label="step.name?.trim() || $t('Fork_Timer_Label', {n: index + 1})"></fork-step-text>
                                </div>
                            </template>
                        </div>
                    </section>

                    <property-view v-model="recipe" :ingredient-factor="factor"></property-view>

                    <p class="fork-recipe__source mt-4" v-if="recipe.sourceUrl">
                        {{ $t('Imported_From') }} <a :href="recipe.sourceUrl" target="_blank" rel="noopener">{{ sourceHost }}</a>
                    </p>

                    <recipe-activity :recipe="recipe" :servings="servings" v-if="useUserPreferenceStore().userSettings.comments && !shared"
                                     class="mt-4"></recipe-activity>
                </v-col>
            </v-row>
        </v-container>

        <fork-add-to-shopping-sheet v-if="useUserPreferenceStore().isAuthenticated" v-model="shoppingSheet" :recipe="recipe"
                                    :servings="servings"></fork-add-to-shopping-sheet>
    </div>
</template>

<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref, watch} from "vue";
import {useI18n} from "vue-i18n";
import {useRoute, useRouter} from "vue-router";
import {useWakeLock} from "@vueuse/core";
import {Recipe} from "@/openapi";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore";
import RecipeContextMenu from "@/components/inputs/RecipeContextMenu.vue";
import KeywordsComponent from "@/components/display/KeywordsBar.vue";
import StepView from "@/components/display/StepView.vue";
import PropertyView from "@/components/display/PropertyView.vue";
import RecipeActivity from "@/components/display/RecipeActivity.vue";
import ForkIngredientList from "@/fork/components/ForkIngredientList.vue";
import ForkServingsStepper from "@/fork/components/ForkServingsStepper.vue";
import ForkAddToShoppingSheet from "@/fork/components/ForkAddToShoppingSheet.vue";
import ForkPriceSummary from "@/fork/components/ForkPriceSummary.vue";
import {estimateRecipes, RecipePrice} from "@/fork/prices";
import {ingredientFactor, ingredientGroups, totalTime} from "@/fork/recipe";
import ForkStepText from "@/fork/timers/ForkStepText.vue";
import {useForkTimers} from "@/fork/timers/timers";

const props = defineProps({
    servings: {type: Number, required: false},
    /** opened through a share link: no cooking or shopping actions */
    shared: {type: Boolean, default: false},
})

const recipe = defineModel<Recipe>({required: true})
const {t} = useI18n()
const router = useRouter()
const route = useRoute()
const {request, release} = useWakeLock()

const servings = ref(props.servings ?? recipe.value.servings ?? 1)
const shoppingSheet = ref(false)

// keep the servings in the URL: cook mode comes back to them, and a shared link keeps them
watch(servings, (value) => {
    router.replace({query: {...route.query, servings: value != recipe.value.servings ? String(value) : undefined}})
})

watch(() => recipe.value.servings, () => {
    if (props.servings == undefined && recipe.value.servings) {
        servings.value = recipe.value.servings
    }
})

// price of the recipe for its own servings, scaled like the ingredients; nothing shown when it cannot be computed
const price = ref<RecipePrice | null>(null)
watch(() => recipe.value.id, (id) => {
    price.value = null
    if (id == undefined || props.shared || !useUserPreferenceStore().isAuthenticated) return
    estimateRecipes([{id}]).then(r => {
        // a late answer for the recipe shown before is dropped
        if (recipe.value.id == id) price.value = r.recipes[0] ?? null
    }).catch(() => {})
}, {immediate: true})

const timers = useForkTimers()

function startStepTimer(minutes: number, name: string | undefined, number: number) {
    timers.start(minutes * 60, name?.trim() || t('Fork_Timer_Label', {n: number}), `${minutes} ${t('min')}`, recipe.value.id, recipe.value.name)
}

const factor = computed(() => ingredientFactor(recipe.value, servings.value))
const groups = computed(() => recipe.value.steps ? ingredientGroups(recipe.value, t) : [])
const hasSteps = computed(() => (recipe.value.steps ?? []).some(s => s.instruction || s.ingredients.length || s.stepRecipe || s.file))
const sourceHost = computed(() => {
    try {
        return new URL(recipe.value.sourceUrl!).host
    } catch {
        return recipe.value.sourceUrl
    }
})

onMounted(() => {
    // keep the screen on while a recipe is open (upstream behaviour)
    // the browser may refuse (hidden tab, low battery, no permission): not an error for the user
    request("screen").catch(() => {})
})

onBeforeUnmount(() => {
    release()
})
</script>

<style scoped>
.fork-recipe__hero {
    max-height: 45vh;
    background: rgb(var(--v-theme-surface-variant));
}

.fork-recipe__hero-skeleton :deep(.v-skeleton-loader__image) {
    height: 30vh;
}

@media (min-width: 960px) {
    .fork-recipe__hero {
        max-width: 1400px;
        margin: var(--fork-space-4) auto 0;
        border-radius: var(--fork-radius-card);
        max-height: 40vh;
    }

    .fork-recipe__aside {
        position: sticky;
        top: 64px;
    }
}

.fork-recipe__time-chip {
    min-height: 44px;
}

.fork-recipe__title {
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
    overflow-wrap: anywhere;
}

.fork-recipe__description {
    margin-top: var(--fork-space-2);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-recipe__facts {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--fork-space-4);
    padding: var(--fork-space-3) var(--fork-space-4);
    border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: var(--fork-radius-card);
}

.fork-recipe__time {
    display: flex;
    align-items: center;
}

.fork-recipe__time-total {
    font-size: var(--fork-text-lg);
    font-weight: 600;
    line-height: 1.2;
}

.fork-recipe__time-detail {
    font-size: var(--fork-text-xs);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-recipe__section {
    font-size: var(--fork-text-lg);
    font-weight: 600;
    margin-bottom: var(--fork-space-2);
}

.fork-recipe__group {
    font-size: var(--fork-text-sm);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: var(--fork-space-4);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-recipe__step {
    padding: var(--fork-space-4) 0;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-recipe__step:last-child {
    border-bottom: none;
}

.fork-recipe__step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 32px;
    height: 32px;
    border-radius: 50%;
    background: rgb(var(--v-theme-primary));
    color: rgb(var(--v-theme-on-primary));
    font-weight: 600;
}

.fork-recipe__step-title {
    font-weight: 600;
    flex-grow: 1;
}

.fork-recipe__instructions {
    font-size: var(--fork-text-md);
    line-height: 1.6;
}

.fork-recipe__instructions :deep(p) {
    margin: 0 0 var(--fork-space-2);
}

.fork-recipe__source {
    font-size: var(--fork-text-sm);
    overflow-wrap: anywhere;
}
</style>
