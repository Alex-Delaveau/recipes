// Hand-written client for the fork's kitchen/ endpoints (see DECISIONS.md: the generated client stays upstream-only).
import {RecipeOverview, RecipeOverviewFromJSON} from "@/openapi";
import {getCookie} from "@/utils/cookie";

export interface KitchenRecipe extends RecipeOverview {
    matchedFoods: number | null
    totalFoods: number | null
}

export interface KitchenPage<T> {
    count: number
    next: string | null
    results: T[]
}

export type KitchenRecipeSort = 'recent' | 'forgotten' | 'random'

export interface KitchenRecipeQuery {
    query?: string
    keywords?: number[]
    have?: number[]
    maxTime?: number | null
    sort?: KitchenRecipeSort | null
    page?: number
    pageSize?: number
}

export async function kitchenFetch(path: string, init: RequestInit = {}): Promise<any> {
    const response = await fetch(`/api/kitchen/${path}`, {
        ...init,
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') ?? '', ...(init.headers ?? {})},
    })
    if (!response.ok) {
        throw new Error(`kitchen ${path}: HTTP ${response.status}`)
    }
    return response.status == 204 ? null : response.json()
}

export async function listKitchenRecipes(q: KitchenRecipeQuery): Promise<KitchenPage<KitchenRecipe>> {
    const params = new URLSearchParams()
    if (q.query) params.set('query', q.query)
    q.keywords?.forEach(k => params.append('keywords', String(k)))
    q.have?.forEach(f => params.append('have', String(f)))
    if (q.maxTime) params.set('max_time', String(q.maxTime))
    if (q.sort) params.set('sort', q.sort)
    params.set('page', String(q.page ?? 1))
    params.set('page_size', String(q.pageSize ?? 24))

    const data = await kitchenFetch(`recipes/?${params.toString()}`)
    return {
        count: data.count,
        next: data.next,
        results: data.results.map((r: any) => ({
            ...RecipeOverviewFromJSON(r),
            matchedFoods: r.matched_foods ?? null,
            totalFoods: r.total_foods ?? null,
        })),
    }
}

// ---------------------------------------------------------------- food organisation (M3)

export interface KitchenCategory {
    id: number
    name: string
}

export interface KitchenFoodItem {
    id: number
    name: string
    pluralName: string | null
    depth: number
    numchild: number
    family: number | null
    category: KitchenCategory | null
    ignoreShopping: boolean
    isFamily: boolean
    aisleConfirmed: boolean
}

export interface KitchenAisle extends KitchenCategory {
    foods: number
}

export interface KitchenToSortItem {
    id: number
    name: string
    suggested: KitchenCategory | null
    source: string
}

export interface KitchenDuplicateSide {
    id: number
    name: string
    recipes: number
    shopping: number
}

export interface KitchenDuplicate {
    keep: KitchenDuplicateSide
    drop: KitchenDuplicateSide
    score: number
    reason: 'same' | 'extra_words' | 'spelling'
}

export interface KitchenFoodMatch {
    exists: boolean
    closest: { id: number, name: string, score: number, reason: string } | null
}

export async function listKitchenFoods(): Promise<{ foods: KitchenFoodItem[], toSort: number }> {
    const data = await kitchenFetch('foods/')
    return {
        toSort: data.to_sort,
        foods: data.foods.map((f: any) => ({
            id: f.id, name: f.name, pluralName: f.plural_name, depth: f.depth, numchild: f.numchild, family: f.family,
            category: f.category, ignoreShopping: f.ignore_shopping, isFamily: f.is_family, aisleConfirmed: f.aisle_confirmed,
        })),
    }
}

export function moveFoodToFamily(foodId: number, familyId: number | null) {
    return kitchenFetch(`foods/${foodId}/move/`, {method: 'POST', body: JSON.stringify({family: familyId})})
}

export function setFoodAisle(foodId: number, categoryId: number | null): Promise<{ to_sort: number }> {
    return kitchenFetch(`foods/${foodId}/aisle/`, {method: 'POST', body: JSON.stringify({category: categoryId})})
}

export function setFoodFamily(foodId: number, isFamily: boolean) {
    return kitchenFetch(`foods/${foodId}/family/`, {method: 'POST', body: JSON.stringify({is_family: isFamily})})
}

export async function listToSort(): Promise<{ count: number, results: KitchenToSortItem[] }> {
    return kitchenFetch('foods/to-sort/')
}

export async function listAisles(): Promise<{ supermarket: number, aisles: KitchenAisle[] }> {
    return kitchenFetch('aisles/')
}

export async function saveAisleOrder(ids: number[]): Promise<{ supermarket: number, aisles: KitchenAisle[] }> {
    return kitchenFetch('aisles/', {method: 'PUT', body: JSON.stringify({order: ids})})
}

export async function listDuplicates(): Promise<KitchenDuplicate[]> {
    return (await kitchenFetch('duplicates/')).results
}

export function dismissDuplicate(a: number, b: number) {
    return kitchenFetch('duplicates/dismiss/', {method: 'POST', body: JSON.stringify({a, b})})
}

export async function matchFoods(names: string[]): Promise<Record<string, KitchenFoodMatch>> {
    return (await kitchenFetch('foods/match/', {method: 'POST', body: JSON.stringify({names})})).results
}

// ---------------------------------------------------------------- recipe wizard (M4)

export interface ParsedLine {
    original: string
    amount: number
    unit: string | null
    food: string | null
    note: string
    foodId: number | null
    unitId: number | null
    error: boolean
}

/** live recognition of ingredient lines (French rules), nothing is created */
export async function parseLines(lines: string[]): Promise<ParsedLine[]> {
    const data = await kitchenFetch('parse/', {method: 'POST', body: JSON.stringify({lines})})
    return data.results.map((r: any) => ({
        original: r.original, amount: r.amount, unit: r.unit, food: r.food, note: r.note,
        foodId: r.food_id, unitId: r.unit_id, error: r.error,
    }))
}
