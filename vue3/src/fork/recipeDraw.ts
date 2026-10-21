import {useStorage} from "@vueuse/core";
import {ApiApi, MealPlan, MealType} from "@/openapi";
import {KitchenRecipe, listKitchenRecipes} from "@/fork/api";
import {forkHomeFilters} from "@/fork/homeFilters";

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

/** day `i` of the plan, from `start` (a yyyy-mm-dd string, local time) */
export function planDay(start: string, i: number) {
    const [y, m, d] = start.split('-').map(Number)
    return new Date(y!, m! - 1, d! + i)
}

/**
 * one recipe per day from `start`, at the recipe's servings, for the chosen meal; the server adds the ingredients to the
 * shopping list when `addShopping` (upstream "addshopping"). One after the other: stops at the first error.
 * Returns how many meals were planned.
 */
export async function planDraw(recipes: DrawnRecipe[], start: string, mealType: MealType, addShopping: boolean) {
    const api = new ApiApi()
    let done = 0
    for (const [i, r] of recipes.entries()) {
        const day = planDay(start, i)
        await api.apiMealPlanCreate({
            mealPlan: {
                recipe: {id: r.id, name: r.name} as MealPlan['recipe'], servings: await servingsOf(r), title: '',
                fromDate: day, toDate: day, mealType, addshopping: addShopping,
            } as MealPlan,
        })
        done++
    }
    return done
}

/** every recipe to the shopping list at its servings, without a meal plan (same server path as the recipe page) */
export async function shopDraw(recipes: DrawnRecipe[]) {
    const api = new ApiApi()
    let done = 0
    for (const r of recipes) {
        await api.apiRecipeShoppingUpdate({id: r.id, recipeShoppingUpdate: {servings: await servingsOf(r), ingredients: []}})
        done++
    }
    return done
}
