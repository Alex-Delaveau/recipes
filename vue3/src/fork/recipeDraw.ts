import {ref, watch} from "vue";
import {useStorage} from "@vueuse/core";
import {ApiApi, MealPlan, MealType} from "@/openapi";
import {KitchenRecipe, listKitchenRecipes} from "@/fork/api";
import {forkHomeFilters} from "@/fork/homeFilters";
import {estimateRecipes, MissingPrice} from "@/fork/prices";

/** what the draw list keeps of a recipe (enough to show the row without reloading it) */
export interface DrawnRecipe {
    id: number
    name: string
    image: string | null
    totalTime: number
    /** recipe servings (lists drawn before this field existed: read from the recipe when needed) */
    servings?: number
}

/**
 * "Draw X recipes": a short list for the coming days, kept on this device until the next draw
 * (closing the app or coming back from a recipe keeps it).
 */
export const drawnRecipes = useStorage<DrawnRecipe[]>('fork_recipe_draw', [])
export const drawSize = useStorage<number>('fork_recipe_draw_size', 5)

/** estimated price of the drawn recipes, each at its own servings (M7); null while unknown */
export const drawPrice = ref<{ total: number, missing: MissingPrice[] } | null>(null)
let drawPriceKey = ''

/** keeps `drawPrice` in step with the list, for the components showing it (one request per list change) */
export function useDrawPrice() {
    // prices may have changed on another screen: asked again on each screen that shows it
    drawPriceKey = ''
    watch(() => drawnRecipes.value.map(r => r.id).join(','), (key) => {
        if (key == drawPriceKey) return
        drawPriceKey = key
        if (!key) {
            drawPrice.value = null
            return
        }
        estimateRecipes(drawnRecipes.value.map(r => ({id: r.id}))).then(p => {
            if (key == drawPriceKey) drawPrice.value = {total: p.total, missing: p.missing}
        }).catch(() => {
            if (key == drawPriceKey) drawPriceKey = ''
        })
    }, {immediate: true})
    return drawPrice
}

function toDrawn(r: KitchenRecipe): DrawnRecipe {
    return {id: r.id!, name: r.name, image: r.image ?? null, totalTime: (r.workingTime ?? 0) + (r.waitingTime ?? 0), servings: r.servings ?? undefined}
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

async function servingsOf(r: DrawnRecipe) {
    if (r.servings && r.servings > 0) return r.servings
    const recipe = await new ApiApi().apiRecipeRetrieve({id: r.id})
    return recipe.servings && recipe.servings > 0 ? recipe.servings : 1
}

/** day `i` of the plan, from `start` (a yyyy-mm-dd string), at `time` ("19:30:00") local time, else noon like upstream */
export function planDay(start: string, i: number, time?: string | null) {
    const [y, m, d] = start.split('-').map(Number)
    const [hh, mm] = (time || '12:00').split(':').map(Number)
    return new Date(y!, m! - 1, d! + i, hh ?? 12, mm ?? 0)
}

/** how far a run went: the first `done` recipes are handled; `error` stopped the rest */
export interface DrawRun {
    done: number
    error: unknown
}

/**
 * one recipe per day from `start` (day `offset` for the first recipe given), at the recipe's servings, for the chosen
 * meal, at its time (set here, so the result does not depend on the server's time zone); the server adds the
 * ingredients to the shopping list when `addShopping` (upstream "addshopping"). Stops at the first error and says how
 * far it went, so a retry sends only the rest.
 */
export async function planDraw(recipes: DrawnRecipe[], start: string, mealType: MealType, addShopping: boolean, offset = 0): Promise<DrawRun> {
    const api = new ApiApi()
    let done = 0
    try {
        for (const r of recipes) {
            const day = planDay(start, offset + done, mealType.time)
            await api.apiMealPlanCreate({
                mealPlan: {
                    recipe: {id: r.id, name: r.name} as MealPlan['recipe'], servings: await servingsOf(r), title: '',
                    fromDate: day, toDate: day, mealType, addshopping: addShopping,
                } as MealPlan,
            })
            done++
        }
        return {done, error: null}
    } catch (error) {
        return {done, error}
    }
}

/** every recipe to the shopping list at its servings, without a meal plan (same server path as the recipe page) */
export async function shopDraw(recipes: DrawnRecipe[]): Promise<DrawRun> {
    const api = new ApiApi()
    let done = 0
    try {
        for (const r of recipes) {
            await api.apiRecipeShoppingUpdate({id: r.id, recipeShoppingUpdate: {servings: await servingsOf(r), ingredients: []}})
            done++
        }
        return {done, error: null}
    } catch (error) {
        return {done, error}
    }
}
