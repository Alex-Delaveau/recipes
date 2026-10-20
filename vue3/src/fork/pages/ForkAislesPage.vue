<template>
    <!-- Generic aisle order (set once): the shopping list follows it -->
    <v-container class="fork-aisles" max-width="640">
        <div class="d-flex align-center ga-2 mb-2">
            <v-btn icon variant="text" size="48" :aria-label="$t('Back')" :to="{name: 'ForkFoodsPage'}">
                <v-icon icon="fa-solid fa-arrow-left"></v-icon>
            </v-btn>
            <h1 class="fork-aisles__title flex-grow-1">{{ $t('Fork_Aisle_Order') }}</h1>
            <v-progress-circular indeterminate size="20" width="2" v-if="saving"></v-progress-circular>
        </div>
        <p class="text-body-2 text-medium-emphasis mb-4">{{ $t('Fork_Aisle_Order_Help') }}</p>

        <v-skeleton-loader v-if="loading" type="list-item, list-item, list-item, list-item"></v-skeleton-loader>
        <v-alert v-else-if="error" type="error" variant="tonal" :text="$t('Fork_Load_Error')"></v-alert>
        <ol v-else class="fork-aisles__list">
            <li v-for="(a, index) in aisles" :key="a.id" class="fork-aisles__row">
                <span class="fork-aisles__rank">{{ index + 1 }}</span>
                <span class="fork-aisles__name">
                    {{ a.name }}
                    <span class="fork-aisles__count">{{ $t('Fork_N_Foods', {n: a.foods}, a.foods) }}</span>
                </span>
                <v-btn icon variant="text" size="44" :disabled="index == 0 || saving" :aria-label="$t('Fork_Move_Up', {aisle: a.name})" @click="shift(index, -1)">
                    <v-icon icon="fa-solid fa-arrow-up" size="16"></v-icon>
                </v-btn>
                <v-btn icon variant="text" size="44" :disabled="index == aisles.length - 1 || saving" :aria-label="$t('Fork_Move_Down', {aisle: a.name})"
                       @click="shift(index, 1)">
                    <v-icon icon="fa-solid fa-arrow-down" size="16"></v-icon>
                </v-btn>
            </li>
        </ol>
    </v-container>
</template>

<script setup lang="ts">
import {onMounted, ref} from "vue";
import {KitchenAisle, listAisles, saveAisleOrder} from "@/fork/api";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";

const aisles = ref<KitchenAisle[]>([])
const loading = ref(true)
const error = ref(false)
const saving = ref(false)

function shift(index: number, delta: number) {
    const previous = aisles.value
    const next = [...aisles.value]
    const [moved] = next.splice(index, 1)
    next.splice(index + delta, 0, moved!)
    aisles.value = next
    saving.value = true
    saveAisleOrder(next.map(a => a.id)).then(r => {
        aisles.value = r.aisles
    }).catch(err => {
        aisles.value = previous
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    }).finally(() => {
        saving.value = false
    })
}

onMounted(() => {
    listAisles().then(r => {
        aisles.value = r.aisles
    }).catch(() => {
        error.value = true
    }).finally(() => {
        loading.value = false
    })
})
</script>

<style scoped>
.fork-aisles__title {
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
}

.fork-aisles__list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.fork-aisles__row {
    display: flex;
    align-items: center;
    gap: var(--fork-space-2);
    min-height: 56px;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-aisles__rank {
    flex: 0 0 28px;
    font-weight: 600;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-aisles__name {
    flex: 1 1 auto;
    min-width: 0;
    font-size: var(--fork-text-md);
}

.fork-aisles__count {
    display: block;
    font-size: var(--fork-text-sm);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
