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
