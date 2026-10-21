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
            <!-- not something to sort: a bad name, never bought, or not a food at all -->
            <div class="fork-sort__other">
                <v-btn variant="text" size="large" prepend-icon="fa-solid fa-pen" @click="openRename()">{{ $t('Fork_Rename') }}</v-btn>
                <v-btn variant="text" size="large" prepend-icon="fa-solid fa-ban" :loading="saving == -1" @click="neverShopping()">{{ $t('Fork_Never_In_Shopping') }}</v-btn>
                <v-btn variant="text" size="large" prepend-icon="fa-solid fa-trash-can" color="error" @click="deleting = true">{{ $t('Delete') }}</v-btn>
            </div>
            </div>
        </template>
    </v-container>

    <v-dialog v-model="renaming" max-width="440">
        <v-card v-if="current" :title="$t('Fork_Rename')">
            <v-card-text class="pt-1">
                <v-form @submit.prevent="rename()">
                    <v-text-field v-model="newName" :label="$t('Fork_New_Name')" autofocus hide-details="auto" autocomplete="off"
                                  :hint="$t('Fork_Other_Name_Help')" persistent-hint></v-text-field>
                </v-form>
            </v-card-text>
            <v-card-actions class="pa-4">
                <v-spacer></v-spacer>
                <v-btn variant="text" size="large" @click="renaming = false">{{ $t('Cancel') }}</v-btn>
                <v-btn color="primary" variant="flat" size="large" :disabled="!newName.trim()" :loading="saving == -2" @click="rename()">{{ $t('Save') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- deleting a food deletes its ingredient lines upstream: only offered for a food no recipe uses -->
    <v-dialog v-model="deleting" max-width="440">
        <v-card v-if="current" class="fork-sort__delete">
            <v-card-title class="text-wrap">{{ $t('Fork_Delete_Food_Title', {name: current.name}) }}</v-card-title>
            <v-card-text class="pt-1">
                <template v-if="current.recipes > 0">{{ $t('Fork_Food_Used', {n: current.recipes}, current.recipes) }}</template>
                <template v-else>
                    {{ $t('Fork_Delete_Food_Text') }}
                    <template v-if="current.shopping > 0">{{ $t('Fork_Delete_Food_Shopping', {n: current.shopping}, current.shopping) }}</template>
                </template>
            </v-card-text>
            <v-card-actions class="pa-4">
                <v-spacer></v-spacer>
                <v-btn variant="text" size="large" @click="deleting = false">{{ $t('Cancel') }}</v-btn>
                <v-btn v-if="current.recipes == 0" color="error" variant="flat" size="large" :loading="saving == -3" @click="remove()">{{ $t('Delete') }}</v-btn>
                <v-btn v-else color="primary" variant="flat" size="large" @click="deleting = false; openRename()">{{ $t('Fork_Rename') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
import {useI18n} from "vue-i18n";
import {ApiApi} from "@/openapi";
import {KitchenAisle, KitchenToSortItem, listAisles, listToSort, setFoodAisle} from "@/fork/api";
import {renameOrMergeFood} from "@/fork/foods";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";

const {t} = useI18n()

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
        done(food.id)
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    }).finally(() => {
        saving.value = null
    })
}

const renaming = ref(false)
const deleting = ref(false)
const newName = ref('')

function done(foodId: number) {
    queue.value = queue.value.filter(f => f.id != foodId)
}

function openRename() {
    newName.value = current.value?.name ?? ''
    renaming.value = true
}

/** a bad name ("d'eau + 30 ml"): renamed, or merged into the food that already has this name (it leaves the queue) */
function rename() {
    const food = current.value
    if (!food || !newName.value.trim() || saving.value != null) return
    saving.value = -2
    renameOrMergeFood(food, newName.value, t).then(r => {
        if (r.merged) done(food.id)
        else food.name = r.name
        renaming.value = false
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    }).finally(() => {
        saving.value = null
    })
}

/** never bought (water, salt from the garden...): no aisle needed */
function neverShopping() {
    const food = current.value
    if (!food || saving.value != null) return
    saving.value = -1
    new ApiApi().apiFoodPartialUpdate({id: food.id, patchedFood: {ignoreShopping: true}}).then(() => {
        done(food.id)
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    }).finally(() => {
        saving.value = null
    })
}

function remove() {
    const food = current.value
    if (!food || food.recipes > 0 || saving.value != null) return
    saving.value = -3
    new ApiApi().apiFoodDestroy({id: food.id}).then(() => {
        done(food.id)
        deleting.value = false
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.DELETE_ERROR, err)
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

.fork-sort__other {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--fork-space-1);
    margin-top: var(--fork-space-2);
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
