<template>
    <!-- "To sort" queue, emptied in a row: one food at a time, one tap per aisle -->
    <v-container class="fork-sort" max-width="640">
        <div class="d-flex align-center ga-2 mb-2">
            <v-btn icon variant="text" size="48" :aria-label="$t('Back')" :to="{name: 'ForkFoodsPage'}">
                <v-icon icon="fa-solid fa-arrow-left"></v-icon>
            </v-btn>
            <h1 class="fork-sort__title flex-grow-1">{{ $t('Fork_To_Sort') }}</h1>
            <span class="text-body-2 text-medium-emphasis" v-if="queue.length" aria-live="polite">{{ $t('Fork_N_Left', {n: queue.length}, queue.length) }}</span>
        </div>

        <v-skeleton-loader v-if="loading" type="heading, button, button, button"></v-skeleton-loader>
        <v-alert v-else-if="error" type="error" variant="tonal" :text="$t('Fork_Load_Error')"></v-alert>

        <div v-else-if="!current" class="fork-sort__done fork-starfield" role="status">
            <v-icon icon="fa-solid fa-check" size="28" class="mb-3"></v-icon>
            <p class="text-body-1">{{ $t('Fork_All_Sorted') }}</p>
            <v-btn class="mt-4" variant="tonal" size="large" :to="{name: 'ForkFoodsPage'}">{{ $t('Fork_Foods') }}</v-btn>
        </div>

        <template v-else>
            <div class="fork-sort__food" :key="current.id">{{ current.name }}</div>
            <v-btn v-if="current.suggested" color="primary" variant="flat" size="x-large" block class="mb-2" :loading="saving == current.suggested.id"
                   @click="assign(current.suggested.id)">
                <v-icon icon="fa-solid fa-check" class="me-2"></v-icon>{{ current.suggested.name }}
            </v-btn>
            <p class="text-caption text-medium-emphasis mb-4" v-if="current.suggested">{{ $t('Fork_Suggestion_Source_' + current.source) }}</p>
            <p class="text-body-2 mb-4" v-else>{{ $t('Fork_No_Suggestion') }}</p>

            <div class="fork-sort__actions">
            <div class="fork-sort__grid">
                <v-btn v-for="a in otherAisles" :key="a.id" variant="outlined" size="large" class="fork-sort__aisle" :loading="saving == a.id"
                       @click="assign(a.id)">{{ a.name }}
                </v-btn>
            </div>
            <v-btn variant="text" size="large" block class="mt-2" @click="later()">{{ $t('Fork_Later') }}</v-btn>
            </div>
        </template>
    </v-container>
</template>

<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
import {KitchenAisle, KitchenToSortItem, listAisles, listToSort, setFoodAisle} from "@/fork/api";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";

const queue = ref<KitchenToSortItem[]>([])
const aisles = ref<KitchenAisle[]>([])
const loading = ref(true)
const error = ref(false)
const saving = ref<number | null>(null)

const current = computed(() => queue.value[0])
const otherAisles = computed(() => aisles.value.filter(a => a.id != current.value?.suggested?.id))

function assign(categoryId: number) {
    const food = current.value
    if (!food || saving.value != null) return
    saving.value = categoryId
    setFoodAisle(food.id, categoryId).then(() => {
        queue.value = queue.value.filter(f => f.id != food.id)
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    }).finally(() => {
        saving.value = null
    })
}

/** skip for now: the food goes to the end of the queue */
function later() {
    if (queue.value.length > 1) queue.value = [...queue.value.slice(1), queue.value[0]!]
}

onMounted(() => {
    listToSort().then(q => listAisles().then(a => [q, a] as const)).then(([q, a]) => {
        queue.value = q.results
        aisles.value = a.aisles
    }).catch(() => {
        error.value = true
    }).finally(() => {
        loading.value = false
    })
})
</script>

<style scoped>
.fork-sort__title {
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
}

.fork-sort__food {
    font-size: var(--fork-text-xxl);
    line-height: 40px;
    font-weight: 600;
    text-align: center;
    margin: var(--fork-space-6) 0;
    overflow-wrap: anywhere;
}

/* one-handed: the aisle buttons sit in the lower half of the screen */
.fork-sort {
    display: flex;
    flex-direction: column;
    min-height: calc(100dvh - 48px - var(--fork-bottom-nav));
}

.fork-sort > :deep(*) {
    flex: 0 0 auto;
}

.fork-sort__actions {
    margin-top: auto;
    padding-top: var(--fork-space-4);
}

@media (min-width: 960px) {
    .fork-sort {
        min-height: 0;
    }
}

.fork-sort__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--fork-space-2);
}

.fork-sort__aisle {
    min-height: 56px;
    white-space: normal;
}

.fork-sort__aisle :deep(.v-btn__content) {
    white-space: normal;
    font-size: var(--fork-text-sm);
    line-height: 1.2;
}

.fork-sort__done {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--fork-space-8) var(--fork-space-4);
    border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: var(--fork-radius-card);
}
</style>
