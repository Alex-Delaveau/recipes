import {reactive} from "vue";
import {KitchenRecipeSort} from "@/fork/api";
import type {ForkNamedItem} from "@/fork/components/ForkModelAutocomplete.vue";

/**
 * Filters of the recipes home, kept at module level: coming back from a recipe restores the same search.
 * Per device and per tab on purpose (not shared between household members).
 */
export const forkHomeFilters = reactive({
    query: '' as string | null,
    have: [] as ForkNamedItem[],
    keywords: [] as ForkNamedItem[],
    maxTime: null as number | null,
    sort: null as KitchenRecipeSort | null,
})
