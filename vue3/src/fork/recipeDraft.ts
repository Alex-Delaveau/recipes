/**
 * Draft of the recipe wizard (M4): what the 4 screens edit, saved on the device while typing, turned into an upstream
 * Recipe on save. Recipes created here keep a single ingredient list, stored in their first step (DECISIONS.md);
 * recipes split by step keep their split.
 */
import {Food, Ingredient, Keyword, Recipe, Step, Unit} from "@/openapi";
import {ParsedLine} from "@/fork/api";

export interface DraftIngredient {
    key: string
    amount: number
    unit: string | null
    food: string
    note: string
    original: string
    /** food already exists in the space (null: unknown yet) */
    known: boolean | null
    /** upstream ingredient when editing an existing recipe */
    raw?: Ingredient
}

export interface DraftStep {
    key: string
    name: string
    instruction: string
    ingredients: DraftIngredient[]
    raw?: Step
}

export interface RecipeDraft {
    recipeId: number | null
    name: string
    servings: number
    workingTime: number
    waitingTime: number
    keywords: { id: number, name: string }[]
    steps: DraftStep[]
    /** wizard screen, restored with the draft */
    screen: number
    savedAt: number
}

let counter = 0

export function newKey() {
    counter += 1
    return `k${Date.now().toString(36)}${counter}`
}

export function emptyDraft(): RecipeDraft {
    return {
        recipeId: null, name: '', servings: 2, workingTime: 0, waitingTime: 0, keywords: [],
        steps: [{key: newKey(), name: '', instruction: '', ingredients: []}], screen: 0, savedAt: Date.now(),
    }
}

export function fromParsed(line: ParsedLine): DraftIngredient {
    return {
        key: newKey(), amount: line.amount ?? 0, unit: line.unit, food: line.food ?? line.original.trim(), note: line.note ?? '',
        original: line.original, known: line.foodId != null,
    }
}

export function draftFromRecipe(recipe: Recipe): RecipeDraft {
    return {
        recipeId: recipe.id ?? null,
        name: recipe.name,
        servings: recipe.servings ?? 1,
        workingTime: recipe.workingTime ?? 0,
        waitingTime: recipe.waitingTime ?? 0,
        keywords: (recipe.keywords ?? []).filter(k => k.id != undefined).map(k => ({id: k.id!, name: k.name})),
        steps: recipe.steps.map(step => ({
            key: newKey(), name: step.name ?? '', instruction: step.instruction ?? '', raw: step,
            ingredients: step.ingredients.filter(i => !i.isHeader).map(i => ({
                key: newKey(), amount: Number(i.amount ?? 0), unit: i.unit?.name ?? null, food: i.food?.name ?? '', note: i.note ?? '',
                original: i.originalText ?? '', known: i.food != null, raw: i,
            })),
        })),
        screen: 0,
        savedAt: Date.now(),
    }
}

/** ingredient for the API: an edited food or unit is sent by name only, so the existing one is found (or created) and
 * never renamed (sending {id, name} would rename the food for every recipe) */
function toIngredient(d: DraftIngredient, order: number): Ingredient {
    const raw = d.raw
    const sameFood = raw?.food && raw.food.name == d.food
    const sameUnit = (raw?.unit?.name ?? null) == d.unit
    return {
        ...(raw ?? {}),
        food: sameFood ? raw!.food : ({name: d.food} as Food),
        unit: d.unit ? (sameUnit && raw?.unit ? raw.unit : ({name: d.unit} as Unit)) : null,
        amount: d.amount ?? 0,
        noAmount: !d.amount,
        note: d.note,
        order: order,
        isHeader: false,
        originalText: d.original || raw?.originalText || '',
    } as Ingredient
}

/** keeps every field of the recipe being edited (sub-recipes, files, nutrition...) and replaces what the wizard edits */
export function draftToRecipe(draft: RecipeDraft, base: Recipe | null): Recipe {
    const steps: Step[] = draft.steps.map((s, index) => {
        // header ingredients are not edited by the wizard: they stay where they were
        const headers = (s.raw?.ingredients ?? []).filter(i => i.isHeader)
        return {
            ...(s.raw ?? {showIngredientsTable: true, time: 0}),
            name: s.name,
            instruction: s.instruction,
            order: index,
            ingredients: [...headers, ...s.ingredients.map((d, i) => toIngredient(d, headers.length + i))],
        } as Step
    })
    return {
        ...(base ?? {internal: true, description: '', servingsText: ''}),
        name: draft.name.trim(),
        servings: Math.max(1, Math.round(draft.servings || 1)),
        workingTime: Math.max(0, Math.round(draft.workingTime || 0)),
        waitingTime: Math.max(0, Math.round(draft.waitingTime || 0)),
        keywords: draft.keywords.map(k => (k.id > 0 ? {id: k.id, name: k.name} : {name: k.name}) as Keyword),
        steps: steps,
    } as Recipe
}

// ---- device storage of the draft (the only state kept on one device, SPEC.md)

function storageKey(recipeId: number | null) {
    return `fork-recipe-draft-${recipeId ?? 'new'}`
}

export function loadDraft(recipeId: number | null): RecipeDraft | null {
    try {
        const raw = localStorage.getItem(storageKey(recipeId))
        return raw ? JSON.parse(raw) as RecipeDraft : null
    } catch {
        return null
    }
}

export function storeDraft(draft: RecipeDraft) {
    try {
        localStorage.setItem(storageKey(draft.recipeId), JSON.stringify({...draft, savedAt: Date.now()}))
    } catch {
        // storage full or disabled: the wizard still works, only the draft is not kept
    }
}

export function clearDraft(recipeId: number | null) {
    try {
        localStorage.removeItem(storageKey(recipeId))
    } catch {
        // ignore
    }
}
