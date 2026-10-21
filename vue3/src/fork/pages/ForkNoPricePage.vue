<template>
    <!-- "Foods without a price" queue, like "to sort": one food at a time, the average price in one tap, or a price typed in -->
    <v-container class="fork-noprice" max-width="640">
        <div class="d-flex align-center ga-2 mb-2">
            <v-btn icon variant="text" size="48" :aria-label="$t('Back')" :to="{name: 'ForkFoodsPage'}">
                <v-icon icon="fa-solid fa-arrow-left"></v-icon>
            </v-btn>
            <h1 class="fork-noprice__title flex-grow-1">{{ $t('Fork_No_Price_Title') }}</h1>
            <span class="text-body-2 text-medium-emphasis" v-if="queue.length" aria-live="polite">{{ $t('Fork_N_Left', {n: queue.length}, queue.length) }}</span>
        </div>

        <v-skeleton-loader v-if="loading" type="heading, button, button"></v-skeleton-loader>
        <v-alert v-else-if="error" type="error" variant="tonal" :text="$t('Fork_Load_Error')">
            <template #append>
                <v-btn variant="text" size="large" @click="load()">{{ $t('Fork_Retry') }}</v-btn>
            </template>
        </v-alert>

        <div v-else-if="!current" class="fork-noprice__done fork-starfield" role="status">
            <v-icon icon="fa-solid fa-check" size="28" class="mb-3"></v-icon>
            <p class="text-body-1">{{ $t('Fork_All_Priced') }}</p>
            <v-btn class="mt-4" variant="tonal" size="large" :to="{name: 'ForkFoodsPage'}">{{ $t('Fork_Foods') }}</v-btn>
        </div>

        <template v-else>
            <!-- every average price at once: the fastest start -->
            <v-card v-if="suggestedCount > 1" variant="tonal" color="secondary" class="mb-2">
                <v-card-text class="d-flex align-center flex-wrap ga-2">
                    <span class="flex-grow-1 text-body-2">{{ $t('Fork_Price_All_Suggested', {n: suggestedCount}, suggestedCount) }}</span>
                    <v-btn variant="flat" color="secondary" size="large" :loading="applyingAll" @click="applyAll()">{{ $t('Fork_Price_Apply_All') }}</v-btn>
                </v-card-text>
            </v-card>

            <div class="fork-noprice__food" :key="current.id">{{ current.name }}</div>
            <p class="text-body-2 text-medium-emphasis text-center mb-4">{{ usageText(current) }}</p>

            <template v-if="current.suggestion">
                <v-btn color="primary" variant="flat" size="x-large" block :loading="saving == 'suggest'" @click="useSuggestion()">
                    <v-icon icon="fa-solid fa-check" class="me-2"></v-icon>{{ perText(current.suggestion.price, current.suggestion.per) }}
                </v-btn>
                <p class="text-caption text-medium-emphasis mt-1 mb-4">{{ $t('Fork_Price_Suggestion_Help') }}</p>
            </template>
            <p v-else class="text-body-2 mb-2">{{ $t('Fork_Price_No_Suggestion') }}</p>

            <div class="fork-noprice__actions">
                <fork-price-fields v-model="form" :key="'f' + current.id"></fork-price-fields>
                <v-alert v-if="formError" type="warning" variant="tonal" density="compact" class="mt-2" :text="formError"></v-alert>
                <v-btn :color="current.suggestion ? undefined : 'primary'" :variant="current.suggestion ? 'outlined' : 'flat'" size="large" block class="mt-3"
                       :disabled="!form.price || priceFormInvalid(form)" :loading="saving == 'save'" @click="save()">
                    {{ $t('Fork_Price_Save') }}
                </v-btn>
                <v-btn variant="text" size="large" block class="mt-2" @click="later()">{{ $t('Fork_Later') }}</v-btn>
                <div class="fork-noprice__other">
                    <v-btn variant="text" size="large" prepend-icon="fa-solid fa-ban" :loading="saving == 'never'" @click="neverShopping()">
                        {{ $t('Fork_Never_In_Shopping') }}
                    </v-btn>
                </div>
            </div>
        </template>
    </v-container>
</template>

<script setup lang="ts">
import {computed, onMounted, ref, watch} from "vue";
import {useI18n} from "vue-i18n";
import {ApiApi} from "@/openapi";
import {PricePer} from "@/fork/api";
import {applyAllSuggestions, emptyPriceForm, euros, FoodPriceDetail, listMissingPrices, PriceError, priceFormInvalid, priceUpdateOf,
    setFoodPrice} from "@/fork/prices";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";
import ForkPriceFields from "@/fork/components/ForkPriceFields.vue";

type Item = FoodPriceDetail & { recipes: number, shopping: number }

const {t, locale} = useI18n()

const queue = ref<Item[]>([])
const loading = ref(true)
const error = ref(false)
const saving = ref<'suggest' | 'save' | 'never' | null>(null)
const applyingAll = ref(false)
const form = ref(emptyPriceForm())
const formError = ref('')

const current = computed(() => queue.value[0])
const suggestedCount = computed(() => queue.value.filter(f => f.suggestion).length)

// a new food: empty fields, in the unit its average price uses
watch(current, (food) => {
    form.value = emptyPriceForm()
    if (food?.suggestion) form.value.per = food.suggestion.per
    formError.value = ''
})

function perText(price: number, per: PricePer) {
    return t('Fork_Price_Per_' + per, {price: euros(price, locale.value)})
}

function usageText(food: Item) {
    const parts = []
    if (food.recipes) parts.push(t('Fork_In_Recipes', {n: food.recipes}, food.recipes))
    if (food.shopping) parts.push(t('Fork_In_Shopping', {n: food.shopping}, food.shopping))
    return parts.join(' · ')
}

function done(foodId: number) {
    queue.value = queue.value.filter(f => f.id != foodId)
}

async function run(kind: 'suggest' | 'save' | 'never', action: (food: Item) => Promise<unknown>) {
    const food = current.value
    if (!food || saving.value != null) return
    saving.value = kind
    try {
        await action(food)
        done(food.id)
    } catch (err) {
        if (err instanceof PriceError) formError.value = err.reason == 'reference' ? t('Fork_Price_Reference_Error') : t('Fork_Price_Number')
        else useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    } finally {
        saving.value = null
    }
}

function useSuggestion() {
    run('suggest', food => setFoodPrice(food.id, {suggest: true}))
}

function save() {
    run('save', food => setFoodPrice(food.id, priceUpdateOf(form.value, emptyPriceForm()) ?? {}))
}

/** never bought: it has no price to know */
function neverShopping() {
    run('never', food => new ApiApi().apiFoodPartialUpdate({id: food.id, patchedFood: {ignoreShopping: true}}))
}

function later() {
    if (queue.value.length > 1) queue.value = [...queue.value.slice(1), queue.value[0]!]
}

async function applyAll() {
    applyingAll.value = true
    try {
        await applyAllSuggestions()
        await load()
    } catch (err) {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    } finally {
        applyingAll.value = false
    }
}

async function load() {
    error.value = false
    try {
        queue.value = (await listMissingPrices()).results
    } catch {
        error.value = true
    } finally {
        loading.value = false
    }
}

onMounted(() => load())
</script>

<style scoped>
.fork-noprice__title {
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
}

.fork-noprice__food {
    font-size: var(--fork-text-xxl);
    line-height: 40px;
    font-weight: 600;
    text-align: center;
    margin: var(--fork-space-4) 0 var(--fork-space-1);
    overflow-wrap: anywhere;
}

.fork-noprice__actions {
    margin-top: var(--fork-space-2);
}

.fork-noprice__other {
    display: flex;
    justify-content: center;
    margin-top: var(--fork-space-1);
}

.fork-noprice__done {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--fork-space-8) var(--fork-space-4);
    border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: var(--fork-radius-card);
}
</style>
