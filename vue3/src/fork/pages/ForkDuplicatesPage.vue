<template>
    <!-- Probable duplicates (rather on desktop): preview of the merge, confirmation, upstream merge + FOOD_ALIAS -->
    <v-container class="fork-dup" max-width="900">
        <div class="d-flex align-center ga-2 mb-2">
            <v-btn icon variant="text" size="48" :aria-label="$t('Back')" :to="{name: 'ForkFoodsPage'}">
                <v-icon icon="fa-solid fa-arrow-left"></v-icon>
            </v-btn>
            <h1 class="fork-dup__title flex-grow-1">{{ $t('Fork_Duplicates') }}</h1>
        </div>
        <p class="text-body-2 text-medium-emphasis mb-4">{{ $t('Fork_Duplicates_Help') }}</p>

        <v-skeleton-loader v-if="loading" type="card, card"></v-skeleton-loader>
        <v-alert v-else-if="error" type="error" variant="tonal" :text="$t('Fork_Load_Error')"></v-alert>
        <div v-else-if="pairs.length == 0" class="fork-dup__empty fork-starfield" role="status">
            <v-icon icon="fa-solid fa-check" size="28" class="mb-3"></v-icon>
            <p>{{ $t('Fork_No_Duplicates') }}</p>
        </div>

        <template v-else>
        <v-btn color="primary" variant="flat" size="large" block class="mb-4" :loading="mergingAll" @click="confirmAll = true">
            {{ $t('Fork_Merge_All', {n: pairs.length}) }}
            <template #loader>{{ $t('Fork_Progress', {done: progress, n: progressTotal}) }}</template>
        </v-btn>
        <v-row dense>
            <v-col cols="12" md="6" v-for="pair in pairs" :key="pair.drop.id + '-' + pair.keep.id">
                <v-card class="h-100">
                    <v-card-text>
                        <div class="fork-dup__names">
                            <span class="fork-dup__drop">{{ pair.drop.name }}</span>
                            <v-icon icon="fa-solid fa-arrow-right" size="14" class="mx-2"></v-icon>
                            <span class="fork-dup__keep">{{ pair.keep.name }}</span>
                            <v-btn icon variant="text" size="44" class="ms-auto" :aria-label="$t('Fork_Swap')" @click="swap(pair)">
                                <v-icon icon="fa-solid fa-right-left" size="14"></v-icon>
                            </v-btn>
                        </div>
                        <div class="text-body-2 text-medium-emphasis">{{ $t('Fork_Duplicate_Reason_' + pair.reason) }}</div>
                        <div class="text-body-2 mt-2">{{ preview(pair) }}</div>
                    </v-card-text>
                    <v-card-actions class="px-4 pb-4 ga-2 flex-wrap justify-end">
                        <v-btn variant="text" size="large" @click="dismiss(pair)">{{ $t('Fork_Not_Duplicate') }}</v-btn>
                        <v-btn variant="text" size="large" @click="openOtherName(pair)">{{ $t('Fork_Other_Name') }}</v-btn>
                        <v-btn color="primary" variant="flat" size="large" @click="confirming = pair">{{ $t('Merge') }}</v-btn>
                    </v-card-actions>
                </v-card>
            </v-col>
        </v-row>
        </template>
    </v-container>

    <v-dialog :model-value="confirming != null" max-width="480" @update:model-value="(v: boolean) => { if (!v) confirming = null }">
        <v-card v-if="confirming" :title="$t('Fork_Merge_Title', {drop: confirming.drop.name, keep: confirming.keep.name})">
            <v-card-text>
                <p>{{ preview(confirming) }}</p>
                <p class="mt-2">{{ $t('Fork_Merge_Alias', {drop: confirming.drop.name, keep: confirming.keep.name}) }}</p>
            </v-card-text>
            <v-card-actions class="pa-4">
                <v-btn variant="text" size="large" @click="confirming = null">{{ $t('Cancel') }}</v-btn>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="flat" size="large" :loading="merging" @click="merge(confirming)">{{ $t('Merge') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- all at once, as shown (swap a pair first to keep the other name) -->
    <v-dialog v-model="confirmAll" max-width="480">
        <v-card :title="$t('Fork_Merge_All_Title', {n: pairs.length}, pairs.length)">
            <v-card-text class="pt-1">{{ $t('Fork_Merge_All_Text') }}</v-card-text>
            <v-card-actions class="pa-4">
                <v-spacer></v-spacer>
                <v-btn variant="text" size="large" @click="confirmAll = false">{{ $t('Cancel') }}</v-btn>
                <v-btn color="primary" variant="flat" size="large" @click="mergeAll()">{{ $t('Merge') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- neither name fits: both merged under a third one ("ognion" + "Ognions" -> "Oignon") -->
    <v-dialog :model-value="naming != null" max-width="480" @update:model-value="(v: boolean) => { if (!v) naming = null }">
        <v-card v-if="naming" :title="$t('Fork_Other_Name')">
            <v-card-text class="pt-1">
                <p class="mb-4">{{ $t('Fork_Other_Name_Pair', {a: naming.drop.name, b: naming.keep.name}) }}</p>
                <v-form @submit.prevent="mergeUnder()">
                    <v-text-field v-model="otherName" :label="$t('Fork_New_Name')" autofocus hide-details="auto" autocomplete="off"
                                  :hint="$t('Fork_Other_Name_Help')" persistent-hint></v-text-field>
                </v-form>
            </v-card-text>
            <v-card-actions class="pa-4">
                <v-spacer></v-spacer>
                <v-btn variant="text" size="large" @click="naming = null">{{ $t('Cancel') }}</v-btn>
                <v-btn color="primary" variant="flat" size="large" :disabled="!otherName.trim()" :loading="merging" @click="mergeUnder()">{{ $t('Merge') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import {onMounted, ref} from "vue";
import {useI18n} from "vue-i18n";
import {ApiApi, Food} from "@/openapi";
import {ErrorMessageType, PreparedMessage, useMessageStore} from "@/stores/MessageStore";
import {dismissDuplicate, KitchenDuplicate, listDuplicates} from "@/fork/api";
import {createFoodAlias, mergeFood, renameOrMergeFood} from "@/fork/foods";

const {t} = useI18n()

const pairs = ref<KitchenDuplicate[]>([])
const loading = ref(true)
const error = ref(false)
const confirming = ref<KitchenDuplicate | null>(null)
const merging = ref(false)

function preview(pair: KitchenDuplicate) {
    return t('Fork_Merge_Preview', {
        recipes: t('Fork_N_Recipes', {n: pair.drop.recipes}, pair.drop.recipes),
        items: t('Fork_N_Items', {n: pair.drop.shopping}, pair.drop.shopping),
        keep: pair.keep.name,
    })
}

function swap(pair: KitchenDuplicate) {
    const keep = pair.keep
    pair.keep = pair.drop
    pair.drop = keep
}

function dismiss(pair: KitchenDuplicate) {
    dismissDuplicate(pair.keep.id, pair.drop.id).then(() => {
        pairs.value = pairs.value.filter(p => p !== pair)
    }).catch(err => useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err))
}

/** upstream merge (ingredients and shopping entries move to the kept food), then the alias for the next imports */
async function merge(pair: KitchenDuplicate) {
    merging.value = true
    try {
        await new ApiApi().apiFoodMergeUpdate({id: pair.drop.id, target: pair.keep.id, food: {} as Food})
        confirming.value = null
        load()
        // the merge is done: an alias failure is reported but does not undo it
        await createFoodAlias(pair.drop.name, pair.keep.name, t)
        useMessageStore().addPreparedMessage(PreparedMessage.MERGE_SUCCESS)
    } catch (err) {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    } finally {
        merging.value = false
    }
}

const confirmAll = ref(false)
const mergingAll = ref(false)
const progress = ref(0)
const progressTotal = ref(0)
const naming = ref<KitchenDuplicate | null>(null)
const otherName = ref('')

/** every pair as shown, one after the other; a food already merged away in this run is skipped */
async function mergeAll() {
    confirmAll.value = false
    mergingAll.value = true
    const todo = [...pairs.value]
    const gone = new Set<number>()
    progress.value = 0
    progressTotal.value = todo.length
    try {
        for (const pair of todo) {
            if (!gone.has(pair.drop.id) && !gone.has(pair.keep.id)) {
                await mergeFood(pair.drop, pair.keep, t)
                gone.add(pair.drop.id)
            }
            progress.value++
        }
        useMessageStore().addPreparedMessage(PreparedMessage.MERGE_SUCCESS)
    } catch (err) {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    } finally {
        mergingAll.value = false
        load()
    }
}

function openOtherName(pair: KitchenDuplicate) {
    otherName.value = pair.keep.name
    naming.value = pair
}

/** both foods under a new name: merged together, then renamed (or merged into the food that has that name) */
async function mergeUnder() {
    const pair = naming.value
    const name = otherName.value.trim()
    if (!pair || !name) return
    merging.value = true
    try {
        await new ApiApi().apiFoodMergeUpdate({id: pair.drop.id, target: pair.keep.id, food: {} as Food})
        if (pair.drop.name.toLowerCase() != name.toLowerCase()) await createFoodAlias(pair.drop.name, name, t).catch(() => {})
        await renameOrMergeFood(pair.keep, name, t)
        naming.value = null
        useMessageStore().addPreparedMessage(PreparedMessage.MERGE_SUCCESS)
        load()
    } catch (err) {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    } finally {
        merging.value = false
    }
}

function load() {
    listDuplicates().then(r => {
        pairs.value = r
    }).catch(() => {
        error.value = true
    }).finally(() => {
        loading.value = false
    })
}

onMounted(() => load())
</script>

<style scoped>
.fork-dup__title {
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
}

.fork-dup__names {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    font-size: var(--fork-text-lg);
    color: rgb(var(--v-theme-on-surface));
}

.fork-dup__drop {
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.fork-dup__keep {
    font-weight: 600;
}

.fork-dup__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--fork-space-8) var(--fork-space-4);
    border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: var(--fork-radius-card);
}
</style>
