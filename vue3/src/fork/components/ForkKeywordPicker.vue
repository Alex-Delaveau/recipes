<template>
    <!-- Keywords: existing ones by search, a new one by typing it (created when the recipe is saved) -->
    <v-combobox
        v-model="selection"
        v-model:search="search"
        :items="items"
        :label="label"
        item-title="name"
        item-value="id"
        return-object
        multiple
        chips
        closable-chips
        clear-on-select
        hide-details
        variant="outlined"
        :loading="loading"
        @update:focused="(f: boolean) => { if (f) load() }"
    ></v-combobox>
</template>

<script setup lang="ts">
import {computed, ref} from "vue";
import {watchDebounced} from "@vueuse/core";
import {ApiApi} from "@/openapi";

interface KeywordItem {
    id: number
    name: string
}

defineProps({
    label: {type: String, default: ''},
})
const model = defineModel<KeywordItem[]>({default: []})
const search = ref('')
const items = ref<KeywordItem[]>([])
const loading = ref(false)

/** typed text becomes {id: 0, name}: a keyword created on save */
const selection = computed({
    get: () => model.value,
    set: (values: (KeywordItem | string)[]) => {
        const result: KeywordItem[] = []
        values.forEach(v => {
            const item = typeof v == 'string' ? (items.value.find(i => i.name.toLowerCase() == v.trim().toLowerCase()) ?? {id: 0, name: v.trim()}) : v
            if (item.name && !result.some(r => r.name.toLowerCase() == item.name.toLowerCase())) result.push(item)
        })
        model.value = result
    },
})

function load() {
    loading.value = true
    new ApiApi().apiKeywordList({query: search.value ?? '', pageSize: 25}).then(r => {
        items.value = r.results.map(k => ({id: k.id!, name: k.name}))
    }).catch(() => {
        items.value = []
    }).finally(() => {
        loading.value = false
    })
}

watchDebounced(search, () => load(), {debounce: 250})
</script>
