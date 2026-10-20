<template>
    <!-- Journey P3 "Recipe to shopping": every ingredient at the chosen servings, all checked; untick what you have -->
    <v-bottom-sheet v-model="sheet" max-width="640" scrollable>
        <v-card class="fork-shop-sheet">
            <v-card-title class="d-flex align-center pt-4">
                <span class="flex-grow-1">{{ $t('Add_to_Shopping') }}</span>
                <v-btn icon="$close" variant="text" :aria-label="$t('Close')" @click="sheet = false"></v-btn>
            </v-card-title>
            <div class="d-flex align-center justify-space-between flex-wrap ga-2 px-4 pb-2">
                <fork-servings-stepper v-model="sheetServings" :label="recipe.servingsText || $t('Servings')"></fork-servings-stepper>
                <v-btn variant="text" size="large" @click="toggleAll()">{{ allChecked ? $t('Fork_Uncheck_All') : $t('Fork_Check_All') }}</v-btn>
            </div>
            <p class="text-body-2 text-medium-emphasis px-4 pb-2">{{ $t('Fork_Uncheck_What_You_Have') }}</p>
            <v-divider></v-divider>

            <v-card-text class="pa-0">
                <v-progress-linear indeterminate v-if="loadingRelated"></v-progress-linear>
                <template v-for="group in groups" :key="group.recipe.id">
                    <v-list-subheader v-if="groups.length > 1">{{ group.recipe.name }}</v-list-subheader>
                    <v-list-item v-for="(entry, i) in group.entries" :key="(entry.ingredient.id ?? i) + '-' + group.recipe.id" min-height="56"
                                 @click="entry.checked = !entry.checked" :aria-checked="entry.checked" role="checkbox">
                        <template #prepend>
                            <v-checkbox-btn :model-value="entry.checked" color="primary" tabindex="-1" class="me-2"
                                            @update:model-value="(v: boolean) => entry.checked = v" @click.stop></v-checkbox-btn>
                        </template>
                        <div :class="{'text-medium-emphasis fork-shop-sheet__unchecked': !entry.checked}">
                            <span class="font-weight-bold me-1" v-if="entry.ingredient.amount && !entry.ingredient.noAmount"
                                  v-html="calculateFoodAmount(entry.ingredient.amount, factor, useUserPreferenceStore().userSettings.useFractions)"></span>
                            <span class="font-weight-bold me-1">{{ ingredientToUnitString(entry.ingredient, factor) }}</span>
                            <span>{{ ingredientToFoodString(entry.ingredient, factor) }}</span>
                            <span class="d-block text-caption" v-if="entry.ingredient.food?.ignoreShopping">{{ $t('Fork_Never_In_Shopping') }}</span>
                        </div>
                    </v-list-item>
                </template>
                <p class="pa-4 text-body-2" v-if="!loadingRelated && checkedCount == 0 && totalCount == 0">{{ $t('Fork_No_Ingredients') }}</p>
            </v-card-text>

            <v-divider></v-divider>
            <v-card-actions class="pa-4">
                <v-btn color="primary" variant="flat" size="x-large" block :disabled="checkedCount == 0" :loading="saving" @click="addToShopping()">
                    {{ $t('Fork_Add_N_Items', {n: checkedCount}, checkedCount) }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
import {computed, PropType, ref, watch} from "vue";
import {useI18n} from "vue-i18n";
import {ApiApi, Ingredient, Recipe, ShoppingListEntryBulkCreate, ShoppingListRecipe} from "@/openapi";
import {ErrorMessageType, MessageType, useMessageStore} from "@/stores/MessageStore";
import {useUserPreferenceStore} from "@/stores/UserPreferenceStore";
import {calculateFoodAmount} from "@/utils/number_utils";
import {ingredientToFoodString, ingredientToUnitString} from "@/utils/model_utils";
import ForkServingsStepper from "@/fork/components/ForkServingsStepper.vue";
import {ingredientFactor} from "@/fork/recipe";

interface SheetEntry {
    ingredient: Ingredient
    checked: boolean
}

interface SheetGroup {
    recipe: Recipe
    entries: SheetEntry[]
}

const props = defineProps({
    recipe: {type: Object as PropType<Recipe>, required: true},
    servings: {type: Number, required: true},
})
const emit = defineEmits(['created'])

const sheet = defineModel<boolean>({default: false})
const {t} = useI18n()

const sheetServings = ref(props.servings)
const groups = ref<SheetGroup[]>([])
const loadingRelated = ref(false)
const saving = ref(false)

const factor = computed(() => ingredientFactor(props.recipe, sheetServings.value))
const allEntries = computed(() => groups.value.flatMap(g => g.entries))
const checkedCount = computed(() => allEntries.value.filter(e => e.checked).length)
const totalCount = computed(() => allEntries.value.length)
const allChecked = computed(() => totalCount.value > 0 && checkedCount.value == totalCount.value)

/** one entry per ingredient with a food; foods flagged "never in shopping" (salt, water) start unchecked */
function entriesOf(recipe: Recipe): SheetEntry[] {
    return recipe.steps.flatMap(step => step.ingredients)
        .filter(i => !i.isHeader && i.food)
        .map(i => ({ingredient: i, checked: !i.food!.ignoreShopping}))
}

function prepare() {
    sheetServings.value = props.servings
    groups.value = [{recipe: props.recipe, entries: entriesOf(props.recipe)}]

    // sub-recipes used in a step are bought with the recipe, like the upstream dialog does
    if (props.recipe.steps.some(s => s.stepRecipe)) {
        const api = new ApiApi()
        loadingRelated.value = true
        api.apiRecipeRelatedList({id: props.recipe.id!}).then(related => {
            return Promise.all(related.map(r => api.apiRecipeRetrieve({id: r.id!})))
        }).then(recipes => {
            recipes.forEach(r => groups.value.push({recipe: r, entries: entriesOf(r)}))
        }).catch(err => {
            useMessageStore().addError(ErrorMessageType.FETCH_ERROR, err)
        }).finally(() => {
            loadingRelated.value = false
        })
    }
}

function toggleAll() {
    const value = !allChecked.value
    allEntries.value.forEach(e => e.checked = value)
}

function addToShopping() {
    const api = new ApiApi()
    saving.value = true
    const bulk = {
        entries: allEntries.value.filter(e => e.checked).map(e => ({
            amount: e.ingredient.noAmount ? 0 : e.ingredient.amount * factor.value,
            foodId: e.ingredient.food!.id!,
            unitId: e.ingredient.unit ? e.ingredient.unit.id! : null,
            ingredientId: e.ingredient.id!,
        })),
        shoppingListsIds: [],
    } as ShoppingListEntryBulkCreate
    const count = bulk.entries.length

    // entries without a shopping list belong to the household's shared list
    api.apiShoppingListRecipeCreate({shoppingListRecipe: {recipe: props.recipe.id, servings: sheetServings.value} as ShoppingListRecipe}).then(slr => {
        return api.apiShoppingListRecipeBulkCreateEntriesCreate({id: slr.id!, shoppingListEntryBulkCreate: bulk})
    }).then(() => {
        useMessageStore().addMessage(MessageType.SUCCESS, {title: t('Fork_Added_N_Items', {n: count}, count), text: ''}, 2500)
        sheet.value = false
        emit('created')
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.CREATE_ERROR, err)
    }).finally(() => {
        saving.value = false
    })
}

watch(sheet, (open) => {
    if (open) prepare()
})
</script>

<style scoped>
.fork-shop-sheet__unchecked {
    text-decoration: line-through;
}

.fork-shop-sheet :deep(.v-list-item) {
    padding-inline: var(--fork-space-4);
}
</style>
