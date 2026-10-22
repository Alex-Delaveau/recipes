<template>
    <!-- Price of a food: amount per kg / l / piece, the dictionary price in one tap, package and weight of a piece -->
    <div class="fork-price">
        <div class="fork-price__head">
            <span class="fork-price__label">{{ $t('Fork_Price') }}</span>
            <v-chip v-if="source && form.price" size="small" :color="source == 'estimated' ? 'warning' : 'success'" variant="tonal">
                {{ source == 'estimated' ? $t('Fork_Price_Estimated') : $t('Fork_Price_Confirmed') }}
            </v-chip>
        </div>
        <div class="fork-price__row">
            <v-text-field v-model="form.price" :label="$t('Fork_Price_Amount')" variant="outlined" inputmode="decimal" autocomplete="off"
                          suffix="€" hide-details="auto" :rules="[numberRule]" class="fork-price__amount"></v-text-field>
            <v-select v-model="form.per" :items="perItems" :label="$t('Fork_Price_Per_Label')" variant="outlined" hide-details
                      class="fork-price__per"></v-select>
        </div>
        <div v-if="suggestion && !form.price" class="fork-price__suggestion">
            <span>{{ $t('Fork_Price_Average', {price: perText(suggestion.price, suggestion.per)}) }}</span>
            <v-btn variant="tonal" color="primary" size="large" @click="useSuggestion()">{{ $t('Fork_Price_Use') }}</v-btn>
        </div>

        <v-expansion-panels v-model="more" variant="accordion" flat class="fork-price__more">
            <v-expansion-panel value="more">
                <v-expansion-panel-title>{{ $t('Fork_Price_More') }}</v-expansion-panel-title>
                <v-expansion-panel-text>
                    <p class="text-body-2 text-medium-emphasis mb-2">{{ $t('Fork_Package_Help') }}</p>
                    <div class="fork-price__row">
                        <v-text-field v-model="form.packageAmount" :label="$t('Fork_Package_Size')" variant="outlined" inputmode="decimal"
                                      autocomplete="off" hide-details="auto" :rules="[numberRule]"></v-text-field>
                        <v-select v-model="form.packageUnit" :items="packageUnits" variant="outlined" hide-details :aria-label="$t('Unit')"
                                  class="fork-price__per"></v-select>
                    </div>
                    <v-text-field v-model="form.packagePrice" :label="$t('Fork_Package_Price')" variant="outlined" inputmode="decimal"
                                  autocomplete="off" suffix="€" hide-details="auto" :rules="[numberRule]" class="mt-3"
                                  :disabled="!form.packageAmount"></v-text-field>
                    <v-text-field v-model="form.pieceWeight" :label="$t('Fork_Piece_Weight')" variant="outlined" inputmode="decimal"
                                  autocomplete="off" suffix="g" hide-details="auto" :rules="[numberRule]" class="mt-3"
                                  :hint="$t('Fork_Piece_Weight_Help')" persistent-hint></v-text-field>
                </v-expansion-panel-text>
            </v-expansion-panel>
        </v-expansion-panels>
    </div>
</template>

<script setup lang="ts">
import {computed, PropType, ref} from "vue";
import {useI18n} from "vue-i18n";
import {PricePer} from "@/fork/api";
import {decimalText, euros, FoodPriceDetail, parseAmount, PriceForm} from "@/fork/prices";

const props = defineProps({
    source: {type: String as PropType<'estimated' | 'confirmed' | null>, default: null},
    suggestion: {type: Object as PropType<FoodPriceDetail['suggestion']>, default: null},
    /** open the package and piece weight part */
    expanded: {type: Boolean, default: false},
})
const form = defineModel<PriceForm>({required: true})

const {t, locale} = useI18n()
const more = ref<string | undefined>(props.expanded ? 'more' : undefined)

const perItems = computed(() => (['kg', 'l', 'piece'] as PricePer[]).map(p => ({value: p, title: t('Fork_Price_Per_' + p, {price: ''}).trim()})))
const packageUnits = computed(() => [
    {value: 'g', title: 'g'}, {value: 'kg', title: 'kg'}, {value: 'ml', title: 'ml'}, {value: 'l', title: 'L'},
    {value: 'piece', title: t('Fork_Pieces')},
])

function numberRule(v: string) {
    return !v || parseAmount(v) !== null || t('Fork_Price_Number')
}

function perText(price: number, per: PricePer) {
    return t('Fork_Price_Per_' + per, {price: euros(price, locale.value)})
}

function useSuggestion() {
    if (!props.suggestion) return
    form.value.price = decimalText(props.suggestion.price, locale.value)
    form.value.per = props.suggestion.per
    if (props.suggestion.pieceWeight && !form.value.pieceWeight) form.value.pieceWeight = decimalText(props.suggestion.pieceWeight, locale.value)
}
</script>

<style scoped>
.fork-price__head {
    display: flex;
    align-items: center;
    gap: var(--fork-space-2);
    margin: var(--fork-space-2) 0;
}

.fork-price__label {
    font-size: var(--fork-text-md);
    font-weight: 600;
}

.fork-price__row {
    display: flex;
    gap: var(--fork-space-2);
    align-items: flex-start;
}

.fork-price__row > :first-child {
    flex: 1;
    min-width: 0;
}

.fork-price__per {
    flex: 0 0 132px;
}

.fork-price__suggestion {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--fork-space-2);
    margin-top: var(--fork-space-2);
    font-size: var(--fork-text-sm);
}

.fork-price__suggestion > span {
    flex: 1;
    min-width: 0;
}

.fork-price__more {
    margin-top: var(--fork-space-2);
}

.fork-price__more :deep(.v-expansion-panel-title) {
    min-height: var(--fork-tap);
    padding-inline: 0;
}

.fork-price__more :deep(.v-expansion-panel-text__wrapper) {
    padding-inline: 0;
}
</style>
