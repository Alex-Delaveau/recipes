<template>
    <!-- Recipe wizard (M4): 4 screens instead of tabs; the draft is kept on the device until saved -->
    <div class="fork-wizard">
        <header class="fork-wizard__bar">
            <v-btn icon variant="text" size="48" :aria-label="$t('Close')" @click="close()">
                <v-icon icon="$close"></v-icon>
            </v-btn>
            <div class="fork-wizard__heading">
                <div class="fork-wizard__title">{{ recipeId ? $t('Fork_Edit_Recipe') : $t('Fork_New_Recipe') }}</div>
                <div class="fork-wizard__progress-label">{{ $t('Fork_Screen_Of', {n: draft.screen + 1, total: SCREENS.length}) }} · {{ $t(SCREENS[draft.screen]!) }}</div>
            </div>
            <v-btn icon variant="text" size="48" :aria-label="$t('Options')">
                <v-icon icon="fa-solid fa-ellipsis-vertical"></v-icon>
                <v-menu activator="parent">
                    <v-list>
                        <v-list-item prepend-icon="fa-solid fa-rotate-left" :title="$t('Fork_Discard_Draft')" min-height="48" @click="discard()"></v-list-item>
                        <v-list-item v-if="recipeId" prepend-icon="fa-solid fa-sliders" :title="$t('Fork_Full_Editor')" min-height="48"
                                     :to="{name: 'ModelEditPage', params: {model: 'recipe', id: recipeId}}"></v-list-item>
                    </v-list>
                </v-menu>
            </v-btn>
        </header>
        <v-progress-linear :model-value="(draft.screen + 1) / SCREENS.length * 100" color="primary" height="4"></v-progress-linear>

        <main class="fork-wizard__content">
            <v-alert v-if="restored" type="info" variant="tonal" class="mb-4" closable :text="$t('Fork_Draft_Restored')" @click:close="restored = false"></v-alert>
            <v-alert v-if="loadError" type="error" variant="tonal" class="mb-4" :text="$t('Fork_Load_Error')"></v-alert>
            <v-skeleton-loader v-if="loading" type="heading, paragraph"></v-skeleton-loader>
            <template v-else-if="loadError"></template>

            <!-- 1. name and servings -->
            <section v-else-if="draft.screen == 0">
                <v-text-field v-model="draft.name" :label="$t('Fork_Recipe_Name')" variant="outlined" autocomplete="off" autofocus class="mb-4"
                              :hint="draft.name.trim() ? '' : $t('Fork_Name_To_Continue')" persistent-hint enterkeyhint="next"
                              @keydown.enter.prevent="next()"></v-text-field>
                <fork-servings-stepper v-model="draft.servings" :label="$t('Servings')"></fork-servings-stepper>
            </section>

            <!-- 2. ingredients -->
            <section v-else-if="draft.screen == 1">
                <v-textarea v-model="pasteText" :label="$t('Fork_Ingredients_Input')" :placeholder="$t('Fork_Ingredients_Placeholder')"
                            variant="outlined" auto-grow rows="3" hide-details autocomplete="off" persistent-placeholder class="mb-2"></v-textarea>
                <div v-if="preview.length" class="fork-wizard__preview" aria-live="polite">
                    <div class="text-caption text-medium-emphasis mb-1">{{ $t('Fork_Recognised') }}</div>
                    <div v-for="(p, i) in preview" :key="i" class="fork-wizard__preview-row">
                        <span class="font-weight-bold" v-if="p.amount">{{ formatAmount(p.amount) }}</span>
                        <span class="font-weight-bold" v-if="p.unit">{{ p.unit }}</span>
                        <span>{{ p.food }}</span>
                        <span class="text-medium-emphasis" v-if="p.note">({{ p.note }})</span>
                    </div>
                </div>
                <v-btn color="primary" variant="flat" size="large" block class="mt-2 mb-4" :disabled="!pasteText.trim()" :loading="parsing"
                       prepend-icon="$create" @click="addLines()">
                    {{ $t('Fork_Add_N_Ingredients', {n: pasteLines.length}, pasteLines.length) }}
                </v-btn>

                <template v-for="(step, si) in ingredientSteps" :key="step.key">
                    <h2 class="fork-wizard__group" v-if="ingredientSteps.length > 1">{{ step.name || $t('Step') + ' ' + (draft.steps.indexOf(step) + 1) }}</h2>
                    <v-list class="py-0" bg-color="transparent">
                        <v-list-item v-for="ing in step.ingredients" :key="ing.key" min-height="52" class="fork-wizard__ingredient"
                                     @click="editLine(step, ing)">
                            <v-list-item-title class="text-wrap">
                                <span class="font-weight-bold me-1" v-if="ing.amount">{{ formatAmount(ing.amount) }}</span>
                                <span class="font-weight-bold me-1" v-if="ing.unit">{{ ing.unit }}</span>
                                <span>{{ ing.food }}</span>
                            </v-list-item-title>
                            <v-list-item-subtitle>
                                <span v-if="ing.note">{{ ing.note }}</span>
                                <span v-if="ing.known === false" class="fork-wizard__new"><template v-if="ing.note"> · </template>{{ $t('Fork_New_Food_Badge') }}</span>
                            </v-list-item-subtitle>
                            <template #append>
                                <v-icon icon="fa-solid fa-pen" size="14" class="text-medium-emphasis"></v-icon>
                            </template>
                        </v-list-item>
                    </v-list>
                </template>
                <p class="text-body-2 text-medium-emphasis mt-2" v-if="ingredientCount == 0 && !preview.length">{{ $t('Fork_No_Ingredient_Yet') }}</p>
            </section>

            <!-- 3. steps -->
            <section v-else-if="draft.screen == 2">
                <div v-for="(step, index) in draft.steps" :key="step.key" class="fork-wizard__step">
                    <div class="d-flex align-center ga-2 mb-1">
                        <span class="fork-wizard__step-number">{{ index + 1 }}</span>
                        <span class="flex-grow-1 text-body-2 text-medium-emphasis">{{ step.ingredients.length ? $t('Fork_N_Ingredients_Attached', {n: step.ingredients.length}, step.ingredients.length) : '' }}</span>
                        <v-btn icon variant="text" size="44" :disabled="index == 0" :aria-label="$t('Fork_Step_Up', {n: index + 1})" @click="moveStep(index, -1)">
                            <v-icon icon="fa-solid fa-arrow-up" size="14"></v-icon>
                        </v-btn>
                        <v-btn icon variant="text" size="44" :disabled="index == draft.steps.length - 1" :aria-label="$t('Fork_Step_Down', {n: index + 1})"
                               @click="moveStep(index, 1)">
                            <v-icon icon="fa-solid fa-arrow-down" size="14"></v-icon>
                        </v-btn>
                        <v-btn icon variant="text" size="44" class="ms-4" :disabled="draft.steps.length == 1" :aria-label="$t('Fork_Step_Delete', {n: index + 1})"
                               @click="removeStep(index)">
                            <v-icon icon="$delete" size="14"></v-icon>
                        </v-btn>
                    </div>
                    <v-textarea v-model="step.instruction" :placeholder="$t('Fork_Step_Placeholder')" :aria-label="$t('Step') + ' ' + (index + 1)"
                                variant="outlined" auto-grow rows="2" hide-details></v-textarea>
                </div>
                <v-btn variant="tonal" size="large" block prepend-icon="$create" class="mt-2" @click="addStep()">{{ $t('Fork_Add_Step') }}</v-btn>
            </section>

            <!-- 4. details -->
            <section v-else-if="draft.screen == 3">
                <div class="d-flex ga-3">
                    <v-text-field v-model.number="draft.workingTime" :label="$t('Fork_Prep_Minutes')" variant="outlined" inputmode="numeric"
                                  autocomplete="off" @focus="(e: FocusEvent) => (e.target as HTMLInputElement).select()"></v-text-field>
                    <v-text-field v-model.number="draft.waitingTime" :label="$t('Fork_Cook_Minutes')" variant="outlined" inputmode="numeric"
                                  autocomplete="off" @focus="(e: FocusEvent) => (e.target as HTMLInputElement).select()"></v-text-field>
                </div>
                <fork-keyword-picker v-model="draft.keywords" :label="$t('Keywords')" class="mb-6"></fork-keyword-picker>

                <div class="fork-wizard__label">{{ $t('Fork_Photo') }}</div>
                <v-img v-if="photoPreview && !photoCrop" :src="photoPreview" :aspect-ratio="16/9" cover class="fork-wizard__photo mb-2"></v-img>
                <div v-else-if="photoPreview && photoCrop" class="fork-wizard__photo mb-2" role="img" :aria-label="$t('Fork_Crop_Done')"
                     :style="{aspectRatio: String(photoAspect), ...cropPreviewStyle(photoPreview, photoCrop)}"></div>
                <input ref="photoInput" type="file" accept="image/*" class="d-none" @change="pickPhoto">
                <div class="fork-wizard__photo-actions">
                    <v-btn variant="tonal" size="large" prepend-icon="fa-solid fa-image" @click="photoInput?.click()">
                        {{ photoPreview ? $t('Fork_Change_Photo') : $t('Fork_Choose_Photo') }}
                    </v-btn>
                    <v-btn v-if="photoPreview" variant="tonal" size="large" prepend-icon="fa-solid fa-crop-simple" @click="cropOpen = true">
                        {{ photoCrop ? $t('Fork_Crop_Again') : $t('Fork_Crop') }}
                    </v-btn>
                </div>
                <fork-image-cropper v-model="cropOpen" :src="photoPreview ?? ''" @apply="(c: ImageCrop, a: number) => { photoCrop = c; photoAspect = a }"></fork-image-cropper>
            </section>
        </main>

        <footer class="fork-wizard__nav">
            <div class="fork-wizard__nav-inner">
                <v-btn size="x-large" variant="tonal" class="flex-grow-1" :disabled="draft.screen == 0" prepend-icon="fa-solid fa-arrow-left" @click="previous()">
                    {{ $t('Fork_Previous') }}
                </v-btn>
                <v-btn size="x-large" color="primary" variant="flat" class="flex-grow-1" append-icon="fa-solid fa-arrow-right" :disabled="!canGoOn"
                       @click="next()" v-if="draft.screen < SCREENS.length - 1">
                    {{ $t('Next') }}
                </v-btn>
                <v-btn size="x-large" color="primary" variant="flat" class="flex-grow-1" prepend-icon="$save" :loading="saving" :disabled="!draft.name.trim() || loadError || loading"
                       @click="save()" v-else>
                    {{ $t('Save') }}
                </v-btn>
            </div>
        </footer>

        <fork-ingredient-line-sheet v-model="lineSheet" :ingredient="editing?.ingredient ?? null" @save="applyLine" @remove="removeLine"></fork-ingredient-line-sheet>
    </div>
</template>

<script setup lang="ts">
import {computed, onMounted, ref, useTemplateRef, watch} from "vue";
import {useRouter} from "vue-router";
import {useI18n} from "vue-i18n";
import {watchDebounced} from "@vueuse/core";
import {ApiApi, Recipe} from "@/openapi";
import {ErrorMessageType, MessageType, useMessageStore} from "@/stores/MessageStore";
import {useFileApi} from "@/composables/useFileApi";
import {ParsedLine, parseLines} from "@/fork/api";
import ForkImageCropper from "@/fork/components/ForkImageCropper.vue";
import {cropPreviewStyle, cropRecipeImage, ImageCrop} from "@/fork/images";
import {clearDraft, DraftIngredient, DraftStep, draftFromRecipe, draftToRecipe, emptyDraft, fromParsed, loadDraft, newKey, RecipeDraft, storeDraft} from "@/fork/recipeDraft";
import ForkServingsStepper from "@/fork/components/ForkServingsStepper.vue";
import ForkIngredientLineSheet from "@/fork/components/ForkIngredientLineSheet.vue";
import ForkKeywordPicker from "@/fork/components/ForkKeywordPicker.vue";

const SCREENS = ['Fork_Screen_Name', 'Ingredients', 'Steps', 'Fork_Screen_Details']

const props = defineProps({
    /** recipe to edit; absent for a new recipe */
    id: {type: String, required: false},
})

const router = useRouter()
const {t} = useI18n()
const {updateRecipeImage} = useFileApi()

/** a new recipe gets its id at the first save: a retry (e.g. after a failed photo upload) updates it, never duplicates */
const savedId = ref<number | null>(null)
const recipeId = computed(() => props.id ? Number(props.id) : savedId.value)
/** draft key: the recipe edited, or "new" until the page is left (the id of a just created recipe is not a draft key) */
const draftId = computed(() => props.id ? Number(props.id) : null)
const draft = ref<RecipeDraft>(emptyDraft())
const loading = ref(false)
const loadError = ref(false)
const restored = ref(false)
const saving = ref(false)
const pasteText = ref('')
const preview = ref<ParsedLine[]>([])
const parsing = ref(false)
const lineSheet = ref(false)
const editing = ref<{ step: DraftStep, ingredient: DraftIngredient } | null>(null)
const photoFile = ref<File | null>(null)
const photoPreview = ref<string | null>(null)
const photoInput = useTemplateRef<HTMLInputElement>('photoInput')
let ready = false
/** snapshot of the draft as loaded: it is only kept on the device once the user changed something */
let pristine = ''

const pasteLines = computed(() => pasteText.value.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0))
/** steps holding ingredients; a new recipe has one list, in its first step */
const ingredientSteps = computed(() => {
    const withIngredients = draft.value.steps.filter(s => s.ingredients.length > 0)
    return withIngredients.length ? withIngredients : [draft.value.steps[0]!]
})
const ingredientCount = computed(() => draft.value.steps.reduce((n, s) => n + s.ingredients.length, 0))
const canGoOn = computed(() => draft.value.screen != 0 || draft.value.name.trim().length > 0)

function formatAmount(amount: number) {
    return Number.isInteger(amount) ? String(amount) : String(Math.round(amount * 100) / 100).replace('.', ',')
}

// ---- navigation
function next() {
    if (canGoOn.value && draft.value.screen < SCREENS.length - 1) {
        if (draft.value.screen == 1 && pasteLines.value.length) addLines() // do not lose typed lines
        draft.value.screen++
        window.scrollTo({top: 0})
    }
}

function previous() {
    if (draft.value.screen > 0) {
        draft.value.screen--
        window.scrollTo({top: 0})
    }
}

/** leaving keeps the draft on the device */
function close() {
    if (draftId.value) router.push({name: 'RecipeViewPage', params: {id: draftId.value}})
    else router.push({name: 'StartPage'})
}

function discard() {
    clearDraft(draftId.value)
    restored.value = false
    load(false)
}

// ---- ingredients
watchDebounced(pasteText, () => {
    const lines = pasteLines.value
    if (!lines.length) {
        preview.value = []
        return
    }
    parseLines(lines).then(r => {
        if (pasteLines.value.join('\n') == lines.join('\n')) preview.value = r
    }).catch(() => {
        preview.value = []
    })
}, {debounce: 400})

function addLines() {
    const lines = pasteLines.value
    if (!lines.length) return
    parsing.value = true
    pasteText.value = ''
    parseLines(lines).then(r => {
        ingredientSteps.value[0]!.ingredients.push(...r.map(fromParsed))
        preview.value = []
    }).catch(err => {
        pasteText.value = lines.join('\n')
        useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
    }).finally(() => {
        parsing.value = false
    })
}

function editLine(step: DraftStep, ingredient: DraftIngredient) {
    editing.value = {step, ingredient}
    lineSheet.value = true
}

function applyLine(value: DraftIngredient) {
    if (!editing.value) return
    const list = editing.value.step.ingredients
    const index = list.findIndex(i => i.key == value.key)
    if (index != -1) list.splice(index, 1, value)
}

function removeLine(value: DraftIngredient) {
    if (!editing.value) return
    editing.value.step.ingredients = editing.value.step.ingredients.filter(i => i.key != value.key)
}

// ---- steps
function addStep() {
    draft.value.steps.push({key: newKey(), name: '', instruction: '', ingredients: []})
}

function moveStep(index: number, delta: number) {
    const steps = draft.value.steps
    const [moved] = steps.splice(index, 1)
    steps.splice(index + delta, 0, moved!)
}

/** a deleted step gives its ingredients to the first remaining step: nothing typed is lost */
function removeStep(index: number) {
    const steps = draft.value.steps
    const [removed] = steps.splice(index, 1)
    if (removed && removed.ingredients.length) steps[0]!.ingredients.push(...removed.ingredients)
}

// ---- photo from the gallery
function pickPhoto(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (!file) return
    photoFile.value = file
    photoPreview.value = URL.createObjectURL(file)
    photoCrop.value = null
}

// ---- framing of the photo, applied by the server after the save (new photo or the stored one)
const cropOpen = ref(false)
const photoCrop = ref<ImageCrop | null>(null)
const photoAspect = ref(16 / 9)

// ---- save
async function save() {
    if (!draft.value.name.trim()) {
        draft.value.screen = 0
        return
    }
    if (pasteLines.value.length) {
        await new Promise<void>(resolve => {
            addLines()
            const stop = watch(parsing, (p) => {
                if (!p) {
                    stop()
                    resolve()
                }
            })
        })
        if (pasteLines.value.length) return // the lines could not be read: they are back in the field, nothing saved
    }
    const api = new ApiApi()
    saving.value = true
    try {
        // the recipe as stored right now: fields the wizard does not edit are kept as they are
        const base: Recipe | null = recipeId.value ? await api.apiRecipeRetrieve({id: recipeId.value}) : null
        const recipe = draftToRecipe(draft.value, base)
        const saved = recipeId.value ? await api.apiRecipeUpdate({id: recipeId.value, recipe}) : await api.apiRecipeCreate({recipe})
        savedId.value = saved.id!
        clearDraft(draftId.value)
        ready = false
        if (photoFile.value || photoCrop.value) {
            // the recipe is saved: a failed photo upload is reported, it does not undo the save
            try {
                if (photoFile.value) {
                    const image = await updateRecipeImage(saved.id!, photoFile.value)
                    if (!image?.image) throw new Error('image not saved')
                }
                if (photoCrop.value) await cropRecipeImage(saved.id!, photoCrop.value)
            } catch {
                useMessageStore().addMessage(MessageType.WARNING, {title: t('Fork_Photo_Failed'), text: ''}, 5000)
            }
        }
        router.replace({name: 'RecipeViewPage', params: {id: saved.id!}})
    } catch (err) {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    } finally {
        saving.value = false
    }
}

// ---- load and keep the draft
function start(value: RecipeDraft, fromStorage: boolean) {
    draft.value = value
    restored.value = fromStorage
    pristine = fromStorage ? '' : JSON.stringify(value)
    ready = true
}

function load(useDraft = true) {
    ready = false
    const stored = useDraft ? loadDraft(draftId.value) : null
    if (!draftId.value) {
        start(stored ?? emptyDraft(), stored != null)
        return
    }
    loading.value = true
    new ApiApi().apiRecipeRetrieve({id: draftId.value}).then(r => {
        photoPreview.value = r.image ?? null
        // a draft older than the recipe (changed since in the full editor, by the other household member...) is dropped
        if (stored && stored.savedAt >= new Date(r.updatedAt).getTime()) {
            start(stored, true)
        } else {
            if (stored) clearDraft(draftId.value)
            start(draftFromRecipe(r), false)
        }
    }).catch(() => {
        loadError.value = true
    }).finally(() => {
        loading.value = false
    })
}

watchDebounced(draft, () => {
    if (ready && JSON.stringify(draft.value) != pristine) {
        storeDraft({...draft.value, recipeId: draftId.value})
    }
}, {deep: true, debounce: 300})

onMounted(() => load())
</script>

<style scoped>
.fork-wizard {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    min-height: 100dvh;
    background: rgb(var(--v-theme-background));
}

.fork-wizard__bar {
    display: flex;
    align-items: center;
    gap: var(--fork-space-2);
    padding: var(--fork-space-2);
    padding-top: calc(var(--fork-space-2) + env(safe-area-inset-top));
}

.fork-wizard__heading {
    flex: 1 1 auto;
    min-width: 0;
}

.fork-wizard__title {
    font-size: var(--fork-text-md);
    font-weight: 600;
}

.fork-wizard__progress-label {
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-wizard__content {
    flex: 1 1 auto;
    width: 100%;
    max-width: 760px;
    margin: 0 auto;
    padding: var(--fork-space-6) var(--fork-space-4);
}

.fork-wizard__label {
    font-size: var(--fork-text-md);
    font-weight: 600;
    margin-bottom: var(--fork-space-2);
}

.fork-wizard__preview {
    padding: var(--fork-space-2) var(--fork-space-3);
    border-radius: var(--fork-radius-card);
    background: rgb(var(--v-theme-surface-variant));
}

.fork-wizard__preview-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--fork-space-1);
    font-size: var(--fork-text-sm);
    line-height: 24px;
}

.fork-wizard__group {
    font-size: var(--fork-text-sm);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: var(--fork-space-4);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-wizard__ingredient {
    padding-inline: 0 !important;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-wizard__ingredient :deep(.v-list-item-subtitle) {
    opacity: 1;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-wizard__new {
    color: rgb(var(--v-theme-secondary));
    font-weight: 600;
}

.fork-wizard__step {
    margin-bottom: var(--fork-space-4);
}

.fork-wizard__step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 28px;
    height: 28px;
    border-radius: 50%;
    background: rgb(var(--v-theme-primary));
    color: rgb(var(--v-theme-on-primary));
    font-weight: 600;
    font-size: var(--fork-text-sm);
}

.fork-wizard__photo-actions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: var(--fork-space-2);
}

.fork-wizard__photo {
    border-radius: var(--fork-radius-card);
}

.fork-wizard__nav {
    position: sticky;
    bottom: 0;
    padding: var(--fork-space-3) var(--fork-space-4);
    padding-bottom: calc(var(--fork-space-3) + env(safe-area-inset-bottom));
    background: rgb(var(--v-theme-background));
    border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-wizard__nav-inner {
    display: flex;
    gap: var(--fork-space-3);
    max-width: 760px;
    margin: 0 auto;
}

.fork-wizard__nav .v-btn {
    min-height: 56px;
    flex: 1 1 0; /* equal widths: the buttons do not move from one screen to the next */
}
</style>
