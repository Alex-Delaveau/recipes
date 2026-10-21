<template>
    <!-- Food names left over by imports ("à soupe d'huile"): merged into the existing food or renamed, one by one or all -->
    <v-container class="fork-names" max-width="760">
        <div class="d-flex align-center ga-2 mb-2">
            <v-btn icon variant="text" size="48" :aria-label="$t('Back')" :to="{name: 'ForkFoodsPage'}">
                <v-icon icon="fa-solid fa-arrow-left"></v-icon>
            </v-btn>
            <h1 class="fork-names__title flex-grow-1">{{ $t('Fork_Names_To_Fix') }}</h1>
        </div>
        <p class="text-body-2 text-medium-emphasis mb-4">{{ $t('Fork_Names_Help') }}</p>

        <v-skeleton-loader v-if="loading" type="list-item-two-line, list-item-two-line, list-item-two-line"></v-skeleton-loader>
        <v-alert v-else-if="error" type="error" variant="tonal" :text="$t('Fork_Load_Error')"></v-alert>
        <div v-else-if="rows.length == 0" class="fork-names__empty fork-starfield" role="status">
            <v-icon icon="fa-solid fa-check" size="28" class="mb-3"></v-icon>
            <p>{{ $t('Fork_No_Names_To_Fix') }}</p>
        </div>

        <template v-else>
            <v-btn color="primary" variant="flat" size="large" block class="mb-4" :loading="fixingAll" @click="confirmAll = true">
                {{ $t('Fork_Fix_All', {n: rows.length}) }}
                <template #loader>{{ $t('Fork_Progress', {done: progress, n: progressTotal}) }}</template>
            </v-btn>

            <v-list class="py-0" bg-color="transparent">
                <v-list-item v-for="row in rows" :key="row.id" class="fork-names__row" min-height="64">
                    <v-list-item-title class="fork-names__line">
                        <span class="fork-names__old">{{ row.name }}</span>
                        <v-icon icon="fa-solid fa-arrow-right" size="12" class="mx-2"></v-icon>
                        <span class="fork-names__new">{{ newName(row) }}</span>
                    </v-list-item-title>
                    <v-list-item-subtitle class="fork-names__how">{{ how(row) }}</v-list-item-subtitle>
                    <template #append>
                        <v-btn icon variant="text" size="44" :aria-label="$t('Options')" :disabled="fixingAll">
                            <v-icon icon="fa-solid fa-ellipsis-vertical" size="16"></v-icon>
                            <v-menu activator="parent">
                                <v-list>
                                    <v-list-item prepend-icon="fa-solid fa-pen" :title="$t('Fork_Other_Name')" min-height="48" @click="openOtherName(row)"></v-list-item>
                                    <v-list-item prepend-icon="fa-solid fa-check" :title="$t('Fork_Keep_Name')" min-height="48" @click="keep(row)"></v-list-item>
                                </v-list>
                            </v-menu>
                        </v-btn>
                        <v-btn variant="tonal" color="primary" size="large" :loading="busy == row.id" :disabled="fixingAll" @click="fixOne(row)">
                            {{ $t('Fork_Fix') }}
                        </v-btn>
                    </template>
                </v-list-item>
            </v-list>
        </template>
    </v-container>

    <!-- all at once -->
    <v-dialog v-model="confirmAll" max-width="440">
        <v-card :title="$t('Fork_Fix_All_Title', {n: rows.length}, rows.length)">
            <v-card-text class="pt-1">{{ $t('Fork_Fix_All_Text') }}</v-card-text>
            <v-card-actions class="pa-4">
                <v-spacer></v-spacer>
                <v-btn variant="text" size="large" @click="confirmAll = false">{{ $t('Cancel') }}</v-btn>
                <v-btn color="primary" variant="flat" size="large" @click="fixAll()">{{ $t('Fork_Fix') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <!-- another name than the proposed one -->
    <v-dialog :model-value="editing != null" max-width="440" @update:model-value="(v: boolean) => { if (!v) editing = null }">
        <v-card v-if="editing" :title="$t('Fork_Other_Name')">
            <v-card-text class="pt-1">
                <v-form @submit.prevent="saveOtherName()">
                    <v-text-field v-model="otherName" :label="$t('Fork_New_Name')" autofocus hide-details="auto" autocomplete="off"
                                  :hint="$t('Fork_Other_Name_Help')" persistent-hint></v-text-field>
                </v-form>
            </v-card-text>
            <v-card-actions class="pa-4">
                <v-spacer></v-spacer>
                <v-btn variant="text" size="large" @click="editing = null">{{ $t('Cancel') }}</v-btn>
                <v-btn color="primary" variant="flat" size="large" :disabled="!otherName.trim()" :loading="busy == editing.id" @click="saveOtherName()">
                    {{ $t('Fork_Fix') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import {onMounted, ref} from "vue";
import {useI18n} from "vue-i18n";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";
import {keepFoodName, KitchenNameFix, listNamesToFix} from "@/fork/api";
import {mergeFood, renameOrMergeFood} from "@/fork/foods";

const {t} = useI18n()

const rows = ref<KitchenNameFix[]>([])
const loading = ref(true)
const error = ref(false)
const busy = ref<number | null>(null)
const fixingAll = ref(false)
const confirmAll = ref(false)
const progress = ref(0)
const progressTotal = ref(0)
const editing = ref<KitchenNameFix | null>(null)
const otherName = ref('')

function newName(row: KitchenNameFix) {
    return row.target ? row.target.name : row.clean
}

function how(row: KitchenNameFix) {
    const usage = [t('Fork_N_Recipes', {n: row.recipes}, row.recipes), t('Fork_N_Items', {n: row.shopping}, row.shopping)].join(' · ')
    return `${row.target ? t('Fork_Fix_Merge', {name: newName(row)}) : t('Fork_Fix_Rename')} · ${usage}`
}

/**
 * merge into the target by id (it may be renamed in the same run: its id stays, the alias uses its clean name),
 * else rename (merged into a food that already has the name, if any)
 */
function apply(row: KitchenNameFix) {
    if (row.target) return mergeFood(row, {id: row.target.id, name: newName(row)}, t)
    return renameOrMergeFood(row, row.clean, t)
}

/** a real name ("4 épices"): kept, never proposed again while it stays the same */
function keep(row: KitchenNameFix) {
    keepFoodName(row.id).then(() => {
        rows.value = rows.value.filter(r => r.id != row.id)
    }).catch(err => useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err))
}

async function fixOne(row: KitchenNameFix) {
    busy.value = row.id
    try {
        await apply(row)
        rows.value = rows.value.filter(r => r.id != row.id)
    } catch (err) {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    } finally {
        busy.value = null
    }
}

/** one after the other, in the server order (renames first): stops at the first error, what is done stays done */
async function fixAll() {
    confirmAll.value = false
    fixingAll.value = true
    progress.value = 0
    progressTotal.value = rows.value.length
    try {
        for (const row of [...rows.value]) {
            await apply(row)
            progress.value++
        }
    } catch (err) {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    } finally {
        fixingAll.value = false
        load()
    }
}

function openOtherName(row: KitchenNameFix) {
    otherName.value = newName(row)
    editing.value = row
}

async function saveOtherName() {
    const row = editing.value
    if (!row || !otherName.value.trim()) return
    busy.value = row.id
    try {
        await renameOrMergeFood(row, otherName.value, t)
        editing.value = null
        load()
    } catch (err) {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    } finally {
        busy.value = null
    }
}

function load() {
    error.value = false
    listNamesToFix().then(r => {
        rows.value = r.results
    }).catch(() => {
        error.value = true
    }).finally(() => {
        loading.value = false
    })
}

onMounted(() => load())
</script>

<style scoped>
.fork-names__title {
    font-size: var(--fork-text-xl);
    line-height: 32px;
    font-weight: 600;
}

.fork-names__row {
    padding-inline: 0 !important;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-names__line {
    white-space: normal;
    -webkit-line-clamp: unset;
    line-clamp: unset;
    font-size: var(--fork-text-md);
}

.fork-names__old {
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    text-decoration: line-through;
}

.fork-names__new {
    font-weight: 600;
}

.fork-names__how {
    -webkit-line-clamp: unset;
    line-clamp: unset;
    font-size: var(--fork-text-sm);
    opacity: 1;
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    white-space: normal;
}

.fork-names__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--fork-space-8) var(--fork-space-4);
    border-radius: var(--fork-radius-card);
    border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
