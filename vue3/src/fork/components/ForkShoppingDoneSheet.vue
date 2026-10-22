<template>
    <!-- "Shopping done": the total paid, compared with the estimate, adjusts the estimated prices of what was checked -->
    <v-bottom-sheet v-model="sheet" max-width="640" scrollable>
        <v-card class="fork-done">
            <v-card-title class="d-flex align-center pt-4">
                <span class="flex-grow-1 text-wrap">{{ $t('Fork_Shopping_Finished') }}</span>
                <v-btn icon="$close" variant="text" size="44" :aria-label="$t('Close')" @click="sheet = false"></v-btn>
            </v-card-title>

            <v-card-text>
                <!-- 1. what was paid -->
                <template v-if="step == 'paid'">
                    <p class="text-body-1 mb-3">{{ $t('Fork_Shopping_Paid_Help') }}</p>
                    <v-form @submit.prevent="compare()">
                        <v-text-field v-model="paidText" :label="$t('Fork_Shopping_Paid')" variant="outlined" inputmode="decimal" autocomplete="off"
                                      suffix="€" autofocus hide-details="auto" :rules="[v => !v || parseAmount(v) !== null || $t('Fork_Price_Number')]"
                                      class="fork-done__paid"></v-text-field>
                    </v-form>
                    <p class="text-body-2 text-medium-emphasis mt-2" v-if="estimate">
                        {{ $t('Fork_Shopping_Estimated_Cart', {price: euros(estimate.checkedTotal, locale)}) }}
                        <template v-if="cartMissing">· {{ $t('Fork_Price_Missing', {n: cartMissing}, cartMissing) }}</template>
                    </p>
                </template>

                <!-- 2. the gap, before anything changes -->
                <template v-else-if="step == 'compare' && adjustment">
                    <div class="fork-done__gap" role="status">
                        <div>{{ $t('Fork_Shopping_Gap', {paid: euros(adjustment.paid, locale), estimated: euros(adjustment.estimated, locale)}) }}</div>
                        <div class="fork-done__percent" v-if="adjustment.percent != null">
                            {{ $t('Fork_Shopping_Gap_Percent', {percent: signed(adjustment.percent)}) }}
                        </div>
                        <div class="text-body-2" v-if="adjustment.percent != null">
                            {{ $t('Fork_Shopping_Gap_Detail', {gap: euros(adjustment.paid - adjustment.confirmedPart - adjustment.estimatedPart, locale), part: euros(adjustment.estimatedPart, locale)}) }}
                        </div>
                        <div class="text-body-2" v-else>{{ $t('Fork_Shopping_Nothing_To_Adjust') }}</div>
                    </div>
                    <v-alert v-if="adjustment.blocked" type="warning" variant="tonal" density="compact" class="mt-3"
                             :text="$t('Fork_Shopping_Blocked', {n: adjustment.missing.length}, adjustment.missing.length)"></v-alert>
                    <v-alert v-else-if="alreadyAdjusted" type="info" variant="tonal" density="compact" class="mt-3"
                             :text="$t('Fork_Shopping_Already_Adjusted')"></v-alert>
                    <p class="text-body-2 text-medium-emphasis mt-2">{{ $t('Fork_Shopping_Adjust_Help') }}</p>

                    <h3 class="fork-done__section">{{ $t('Fork_Shopping_Items') }}</h3>
                    <v-list class="py-0" bg-color="transparent">
                        <template v-for="item in cartItems" :key="item.food.id">
                            <v-list-item min-height="52" class="fork-done__item">
                                <v-list-item-title class="text-wrap">{{ item.food.name }}</v-list-item-title>
                                <v-list-item-subtitle>
                                    <template v-if="item.cost != null">{{ euros(item.cost, locale) }} · {{ item.source == 'estimated' ? $t('Fork_Price_Estimated') : $t('Fork_Price_Confirmed') }}</template>
                                    <template v-else>{{ item.reason == 'no_conversion' ? $t('Fork_Price_Reason_No_Conversion') : $t('Fork_Price_Reason_No_Price') }}</template>
                                </v-list-item-subtitle>
                                <template #append>
                                    <v-btn variant="text" size="large" @click="startCorrect(item)" :aria-label="$t('Fork_Shopping_Correct_Item', {name: item.food.name})">
                                        {{ $t('Fork_Shopping_Correct') }}
                                    </v-btn>
                                </template>
                            </v-list-item>
                            <v-form v-if="correcting == item.food.id" class="fork-done__correct" @submit.prevent="correct(item)">
                                <v-text-field v-model="itemPaidText" :label="$t('Fork_Shopping_Item_Paid', {name: item.food.name})" variant="outlined"
                                              inputmode="decimal" autocomplete="off" suffix="€" autofocus hide-details="auto"
                                              :error-messages="itemError"></v-text-field>
                                <v-btn color="primary" variant="flat" size="large" type="submit" :loading="busy"
                                       :disabled="parseAmount(itemPaidText) === null">{{ $t('Save') }}</v-btn>
                            </v-form>
                        </template>
                    </v-list>
                </template>

                <!-- 3. done -->
                <template v-else-if="step == 'done'">
                    <div class="fork-done__gap" role="status">
                        <v-icon icon="fa-solid fa-check" size="20" class="me-2"></v-icon>
                        {{ adjusted > 0 ? $t('Fork_Shopping_Adjusted', {n: adjusted}, adjusted) : $t('Fork_Shopping_Nothing_Adjusted') }}
                    </div>
                    <p class="text-body-2 text-medium-emphasis mt-2">{{ $t('Fork_Shopping_Clear_Cart_Now') }}</p>
                </template>

                <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mt-3" :text="$t('Fork_Load_Error')"></v-alert>
            </v-card-text>

            <v-card-actions class="pa-4 ga-2">
                <template v-if="step == 'paid'">
                    <v-btn variant="text" size="large" @click="skip()">{{ $t('Fork_Skip') }}</v-btn>
                    <v-spacer></v-spacer>
                    <v-btn color="primary" variant="flat" size="large" :loading="busy" :disabled="parseAmount(paidText) === null || !parseAmount(paidText)"
                           @click="compare()">{{ $t('Fork_Shopping_Compare') }}</v-btn>
                </template>
                <template v-else-if="step == 'compare'">
                    <v-btn variant="text" size="large" @click="skip()">{{ $t('Fork_Skip') }}</v-btn>
                    <v-spacer></v-spacer>
                    <v-btn color="primary" variant="flat" size="large" :loading="busy"
                           :disabled="!adjustment || adjustment.factor == null || adjustment.blocked || alreadyAdjusted"
                           @click="apply()">{{ $t('Fork_Shopping_Adjust') }}</v-btn>
                </template>
                <template v-else>
                    <v-btn variant="text" size="large" @click="sheet = false">{{ $t('Close') }}</v-btn>
                    <v-spacer></v-spacer>
                    <v-btn color="primary" variant="flat" size="large" @click="sheet = false; emit('clear-cart')">{{ $t('Fork_Shopping_Clear_Cart') }}</v-btn>
                </template>
            </v-card-actions>
        </v-card>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
import {computed, PropType, ref, watch} from "vue";
import {useStorage} from "@vueuse/core";
import {useI18n} from "vue-i18n";
import {Adjustment, adjustAfterShopping, correctShoppingItem, estimateShopping, euros, parseAmount, PriceError, ShoppingPrice,
    ShoppingPriceItem} from "@/fork/prices";

const props = defineProps({
    /** ids of the checked entries (what went through the till) */
    entries: {type: Array as PropType<number[]>, required: true},
})
const emit = defineEmits(['changed', 'clear-cart'])
const sheet = defineModel<boolean>({default: false})

const {t, locale} = useI18n()
const step = ref<'paid' | 'compare' | 'done'>('paid')
const paidText = ref('')
const estimate = ref<ShoppingPrice | null>(null)
const adjustment = ref<Adjustment | null>(null)
const adjusted = ref(0)
const busy = ref(false)
const error = ref(false)
const correcting = ref<number | null>(null)
const itemPaidText = ref('')
const itemError = ref('')

// a cart adjusts the prices once: reopening "shopping done" before clearing the cart does not move them again
const lastAdjustedCart = useStorage('fork_price_adjusted_cart', '')
const cartKey = computed(() => [...props.entries].sort((a, b) => a - b).join(','))
const alreadyAdjusted = computed(() => cartKey.value != '' && lastAdjustedCart.value == cartKey.value)

const cartItems = computed(() => estimate.value?.items.filter(i => i.checked) ?? [])
const cartMissing = computed(() => cartItems.value.filter(i => i.cost == null).length)

watch(sheet, (open) => {
    if (!open) return
    step.value = 'paid'
    paidText.value = ''
    adjustment.value = null
    correcting.value = null
    error.value = false
    refresh()
})

function signed(percent: number) {
    return percent > 0 ? `+${percent}` : String(percent)
}

async function guard(action: () => Promise<void>) {
    busy.value = true
    error.value = false
    try {
        await action()
    } catch {
        error.value = true
    } finally {
        busy.value = false
    }
}

async function refresh() {
    await guard(async () => {
        estimate.value = await estimateShopping(props.entries)
    })
}

function compare() {
    const paid = parseAmount(paidText.value)
    if (!paid) return
    guard(async () => {
        adjustment.value = await adjustAfterShopping(props.entries, paid, false)
        step.value = 'compare'
    })
}

function apply() {
    const paid = parseAmount(paidText.value)
    if (!paid) return
    guard(async () => {
        adjusted.value = (await adjustAfterShopping(props.entries, paid, true)).adjusted
        lastAdjustedCart.value = cartKey.value
        step.value = 'done'
        emit('changed')
    })
}

function startCorrect(item: ShoppingPriceItem) {
    correcting.value = correcting.value == item.food.id ? null : item.food.id
    itemPaidText.value = ''
    itemError.value = ''
}

/** "the salmon was 6.90 €": that price becomes confirmed, and the comparison is done again without it */
function correct(item: ShoppingPriceItem) {
    const paid = parseAmount(itemPaidText.value)
    if (paid === null) return
    guard(async () => {
        try {
            await correctShoppingItem(item.food.id, item.entries, paid)
        } catch (err) {
            if (err instanceof PriceError) {
                itemError.value = t('Fork_Price_Reason_No_Conversion')
                return
            }
            throw err
        }
        correcting.value = null
        emit('changed')
        estimate.value = await estimateShopping(props.entries)
        const total = parseAmount(paidText.value)
        if (total) adjustment.value = await adjustAfterShopping(props.entries, total, false)
    })
}

/** optional: nothing changes */
function skip() {
    sheet.value = false
}
</script>

<style scoped>
.fork-done__paid :deep(input) {
    font-size: var(--fork-text-xl);
}

.fork-done__gap {
    display: flex;
    flex-direction: column;
    gap: var(--fork-space-1);
    padding: var(--fork-space-3) var(--fork-space-4);
    border-radius: var(--fork-radius-card);
    background: rgb(var(--v-theme-surface-variant));
    font-size: var(--fork-text-md);
}

.fork-done__percent {
    font-size: var(--fork-text-lg);
    font-weight: 700;
}

.fork-done__section {
    font-size: var(--fork-text-md);
    font-weight: 600;
    margin: var(--fork-space-4) 0 var(--fork-space-1);
}

.fork-done__item {
    padding-inline: 0 !important;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-done__correct {
    display: flex;
    gap: var(--fork-space-2);
    align-items: flex-start;
    padding: var(--fork-space-2) 0;
}

.fork-done__correct > :first-child {
    flex: 1;
    min-width: 0;
}
</style>
