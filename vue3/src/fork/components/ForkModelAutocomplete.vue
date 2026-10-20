<template>
    <!-- Multi-select with server-side search, sized for touch (replaces the small vueform multiselect in fork screens) -->
    <v-autocomplete
        v-model="model"
        v-model:search="search"
        :items="items"
        :loading="loading"
        :label="label"
        item-title="name"
        item-value="id"
        return-object
        multiple
        chips
        closable-chips
        clear-on-select
        hide-details
        no-filter
        variant="outlined"
        :no-data-text="$t('No_Results')"
        @update:focused="(f: boolean) => { if (f) load() }"
    ></v-autocomplete>
</template>

<script setup lang="ts">
import {PropType, ref, watch} from "vue";
import {ApiApi} from "@/openapi";
import {watchDebounced} from "@vueuse/core";

export interface ForkNamedItem {
    id: number
    name: string
}

const props = defineProps({
    model: {type: String as PropType<'food' | 'keyword'>, required: true},
    label: {type: String, default: ''},
})

const model = defineModel<ForkNamedItem[]>({default: []})
const search = ref('')
const items = ref<ForkNamedItem[]>([])
const loading = ref(false)

function load() {
    const api = new ApiApi()
    loading.value = true
    const request = props.model == 'food'
        ? api.apiFoodList({query: search.value, pageSize: 25})
        : api.apiKeywordList({query: search.value, pageSize: 25})
    request.then(r => {
        // keep the selected items in the list so their chips keep a label
        const results = r.results.map(x => ({id: x.id!, name: x.name}))
        items.value = [...model.value, ...results.filter(x => !model.value.some(m => m.id == x.id))]
    }).finally(() => {
        loading.value = false
    })
}

watchDebounced(search, () => load(), {debounce: 250})
watch(model, () => {
    search.value = ''
})
</script>
