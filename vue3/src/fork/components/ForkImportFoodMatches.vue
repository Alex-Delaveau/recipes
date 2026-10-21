<template>
    <!-- Import review: unknown foods get the closest existing food proposed; choosing it creates a FOOD_ALIAS -->
    <v-card v-if="proposals.length || newFoods.length" class="fork-matches mb-4" variant="outlined">
        <v-card-title class="text-wrap">{{ $t('Fork_Unknown_Foods') }}</v-card-title>
        <v-card-text>
            <p class="text-body-2 text-medium-emphasis mb-2" v-if="proposals.length">{{ $t('Fork_Unknown_Foods_Help') }}</p>
            <div v-for="p in proposals" :key="p.name" class="fork-matches__row">
                <div class="fork-matches__names">
                    <span>{{ p.name }}</span>
                    <v-icon icon="fa-solid fa-arrow-right" size="12" class="mx-2"></v-icon>
                    <strong>{{ p.closest }}</strong>
                </div>
                <div class="d-flex ga-2">
                    <v-btn variant="text" size="large" @click="keep(p.name)">{{ $t('Fork_Keep_New') }}</v-btn>
                    <v-btn color="primary" variant="tonal" size="large" :loading="busy == p.name" @click="use(p.name, p.closest)">
                        {{ $t('Fork_Use_Existing') }}
                    </v-btn>
                </div>
            </div>
            <p class="text-body-2 mt-2" v-if="newFoods.length">
                {{ $t('Fork_New_Foods_Created', {foods: newFoods.join(', ')}) }}
            </p>
        </v-card-text>
    </v-card>
</template>

<script setup lang="ts">
import {computed, ref} from "vue";
import {useI18n} from "vue-i18n";
import {watchDebounced} from "@vueuse/core";
import {KitchenFoodMatch, matchFoods} from "@/fork/api";
import {createFoodAlias} from "@/fork/foods";
import {ErrorMessageType, useMessageStore} from "@/stores/MessageStore";

interface ImportIngredient {
    food?: { name: string } | null
}

const props = defineProps<{
    /** recipe of the import response (steps with ingredients whose food only has a name) */
    recipe: { steps: { ingredients: ImportIngredient[] }[] } | undefined
}>()

const {t} = useI18n()
const matches = ref<Record<string, KitchenFoodMatch>>({})
const kept = ref(new Set<string>())
const busy = ref<string | null>(null)

const names = computed(() => {
    const all = (props.recipe?.steps ?? []).flatMap(s => s.ingredients).map(i => i.food?.name?.trim()).filter((n): n is string => !!n)
    return Array.from(new Set(all))
})
const proposals = computed(() => names.value
    .filter(n => matches.value[n] && !matches.value[n]!.exists && matches.value[n]!.closest && !kept.value.has(n))
    .map(n => ({name: n, closest: matches.value[n]!.closest!.name})))
const newFoods = computed(() => names.value.filter(n => matches.value[n] && !matches.value[n]!.exists
    && (!matches.value[n]!.closest || kept.value.has(n))))

function refresh() {
    const missing = names.value.filter(n => !(n in matches.value))
    if (!missing.length) return
    matchFoods(missing).then(r => {
        matches.value = {...matches.value, ...r}
    }).catch(() => {
        // the review works without proposals
    })
}

function keep(name: string) {
    kept.value = new Set([...kept.value, name])
}

/** every ingredient named `name` uses the existing food, and an alias makes the next import do it by itself */
function use(name: string, existing: string) {
    busy.value = name
    createFoodAlias(name, existing, t).then(() => {
        (props.recipe?.steps ?? []).flatMap(s => s.ingredients).forEach(i => {
            if (i.food && i.food.name.trim() == name) i.food.name = existing
        })
        matches.value = {...matches.value, [existing]: {exists: true, closest: null}}
    }).catch(err => {
        useMessageStore().addError(ErrorMessageType.CREATE_ERROR, err)
    }).finally(() => {
        busy.value = null
    })
}

watchDebounced(names, () => refresh(), {debounce: 300, immediate: true})
</script>

<style scoped>
.fork-matches__row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--fork-space-2);
    padding: var(--fork-space-2) 0;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-matches__names {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    font-size: var(--fork-text-md);
}
</style>
