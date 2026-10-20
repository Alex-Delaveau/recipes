import {Ingredient, Recipe, Step} from "@/openapi";

export interface IngredientGroup {
    title: string | null
    ingredients: Ingredient[]
}

/** title of a step: its own name or "Step n" */
export function stepTitle(step: Step, index: number, t: (key: string) => string) {
    return step.name ? step.name : `${t('Step')} ${index + 1}`
}

/**
 * Ingredients shown at the top of a recipe. Recipes created in the fork keep every ingredient in their first step
 * (single list); imported recipes split by step keep that split, one group per step (DECISIONS.md).
 */
export function ingredientGroups(recipe: Recipe, t: (key: string) => string): IngredientGroup[] {
    const steps = recipe.steps.map((step, index) => ({step, index})).filter(s => s.step.ingredients.length > 0)
    if (steps.length <= 1) {
        return [{title: null, ingredients: steps[0]?.step.ingredients ?? []}]
    }
    return steps.map(s => ({title: stepTitle(s.step, s.index, t), ingredients: s.step.ingredients}))
}

export function totalTime(recipe: { workingTime?: number, waitingTime?: number }) {
    return (recipe.workingTime ?? 0) + (recipe.waitingTime ?? 0)
}

/** servings chosen by the user turned into the factor applied to every quantity */
export function ingredientFactor(recipe: Recipe, servings: number) {
    return servings / Math.max(recipe.servings ?? 1, 1)
}
