<template>
    <!-- Estimated price ("≈ 6,40 € · 1,60 €/pers."), always with what it leaves out ("2 articles sans prix", tap for the list) -->
    <div class="fork-price-summary" :class="{'fork-price-summary--compact': compact}">
        <div class="fork-price-summary__text">
            <span class="fork-price-summary__total">
                <template v-if="label">{{ label }} </template>≈ {{ euros(total, locale) }}<template v-if="perServing != null"> · {{ $t('Fork_Price_Per_Serving', {price: euros(perServing, locale)}) }}</template>
            </span>
            <button v-if="missing.length" type="button" class="fork-price-summary__missing" @click.stop.prevent="open = true">
                {{ $t('Fork_Price_Missing', {n: missing.length}, missing.length) }}
            </button>
        </div>

    <v-dialog v-model="open" max-width="440" scrollable>
        <v-card :title="$t('Fork_Price_Missing_Title')">
            <v-card-text class="pa-0">
                <p class="text-body-2 text-medium-emphasis px-6 pb-2">{{ $t('Fork_Price_Missing_Help') }}</p>
                <v-list density="comfortable">
                    <v-list-item v-for="m in missing" :key="m.id" :title="m.name" min-height="48"
                                 :subtitle="m.reason == 'no_price' ? $t('Fork_Price_Reason_No_Price') : $t('Fork_Price_Reason_No_Conversion')"></v-list-item>
                </v-list>
            </v-card-text>
            <v-card-actions class="pa-4">
                <v-btn variant="text" size="large" @click="open = false">{{ $t('Close') }}</v-btn>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="flat" size="large" :to="{name: 'ForkNoPricePage'}" v-if="missing.some(m => m.reason == 'no_price')">
                    {{ $t('Fork_Price_Add') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
    </div>
</template>

<script setup lang="ts">
import {PropType, ref} from "vue";
import {useI18n} from "vue-i18n";
import {euros, MissingPrice} from "@/fork/prices";

defineProps({
    total: {type: Number, required: true},
    perServing: {type: Number as PropType<number | null>, default: null},
    missing: {type: Array as PropType<MissingPrice[]>, default: () => []},
    /** words before the price ("ces 5 plats") */
    label: {type: String, default: ''},
    compact: {type: Boolean, default: false},
})

const {locale} = useI18n()
const open = ref(false)
</script>

<style scoped>
.fork-price-summary {
    display: flex;
    align-items: flex-start;
    gap: var(--fork-space-2);
}

.fork-price-summary__text {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    column-gap: var(--fork-space-2);
    min-width: 0;
}

.fork-price-summary__total {
    font-size: var(--fork-text-md);
    font-weight: 600;
}

.fork-price-summary--compact .fork-price-summary__total {
    font-size: var(--fork-text-sm);
    font-weight: 500;
}

/* a real tap target, styled as a link */
.fork-price-summary__missing {
    min-height: 44px;
    padding: 0;
    border: 0;
    background: none;
    color: rgb(var(--v-theme-primary));
    font-size: var(--fork-text-sm);
    text-decoration: underline;
    cursor: pointer;
}
</style>
