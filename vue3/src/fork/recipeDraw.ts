import {useStorage} from "@vueuse/core";
import {KitchenRecipe, listKitchenRecipes} from "@/fork/api";
import {forkHomeFilters} from "@/fork/homeFilters";

/** what the draw list keeps of a recipe (enough to show the row without reloading it) */
export interface DrawnRecipe {
    id: number
    name: string
    image: string | null
    totalTime: number
}

/**
 * "Draw X recipes": a short list for the coming days, kept on this device until the next draw
 * (closing the app or coming back from a recipe keeps it).
 */
export const drawnRecipes = useStorage<DrawnRecipe[]>('fork_recipe_draw', [])
export const drawSize = useStorage<number>('fork_recipe_draw_size', 5)

function toDrawn(r: KitchenRecipe): DrawnRecipe {
    return {id: r.id!, name: r.name, image: r.image ?? null, totalTime: (r.workingTime ?? 0) + (r.waitingTime ?? 0)}
}

/** `n` random recipes matching the home filters (foods on hand, time, keywords), none of `exclude` */
export async function drawRecipes(n: number, exclude: number[] = []): Promise<DrawnRecipe[]> {
    if (n <= 0) return []
    const page = await listKitchenRecipes({
        have: forkHomeFilters.have.map(f => f.id),
        keywords: forkHomeFilters.keywords.map(k => k.id),
        maxTime: forkHomeFilters.maxTime,
        sort: 'random',
        page: 1,
        pageSize: Math.min(n + exclude.length, 100),
    })
    return page.results.filter(r => !exclude.includes(r.id!)).slice(0, n).map(toDrawn)
}
