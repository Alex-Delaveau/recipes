// Price estimate (M7): client for the kitchen/prices endpoints and the formatting shared by the screens.
import {FoodPrice, kitchenFetch, PricePer} from "@/fork/api";
import {getCookie} from "@/utils/cookie";

export type PackageKind = 'g' | 'ml' | 'piece'

export interface FoodPriceDetail {
    id: number
    name: string
    price: FoodPrice | null
    package: { amount: number, kind: PackageKind, price: number | null } | null
    /** grams per piece */
    pieceWeight: number | null
    /** what the dictionary of average prices proposes */
    suggestion: { price: number, per: PricePer, pieceWeight: number | null } | null
}

export interface MissingPrice {
    id: number
    name: string
    reason: 'no_price' | 'no_conversion'
}

export interface RecipePrice {
    id: number
    total: number
    perServing: number
    servings: number
    missing: MissingPrice[]
}

export interface ShoppingPriceItem {
    food: { id: number, name: string }
    checked: boolean
    entries: number[]
    cost: number | null
    reason: 'no_price' | 'no_conversion' | null
    packages: number | null
    source: 'estimated' | 'confirmed'
}

export interface ShoppingPrice {
    total: number
    checkedTotal: number
    items: ShoppingPriceItem[]
    missing: MissingPrice[]
}

export interface Adjustment {
    paid: number
    estimated: number
    estimatedPart: number
    confirmedPart: number
    /** paid / estimated, on the estimated part only; null when no estimated price can move */
    factor: number | null
    percent: number | null
    adjusted: number
    missing: MissingPrice[]
}

export class PriceError extends Error {
    constructor(public reason: string) {
        super(reason)
    }
}

/** like kitchenFetch, but a 400 tells why ("reference", "no_conversion") */
async function priceFetch(path: string, method: string, body: any): Promise<any> {
    const response = await fetch(`/api/kitchen/${path}`, {
        method, credentials: 'same-origin', body: JSON.stringify(body),
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') ?? ''},
    })
    if (response.status == 400) {
        const data = await response.json().catch(() => ({}))
        throw new PriceError(data.reason ?? 'invalid')
    }
    if (!response.ok) throw new Error(`kitchen ${path}: HTTP ${response.status}`)
    return response.json()
}

function detail(d: any): FoodPriceDetail {
    return {
        id: d.id, name: d.name, price: d.price, package: d.package, pieceWeight: d.piece_weight,
        suggestion: d.suggestion ? {price: d.suggestion.price, per: d.suggestion.per, pieceWeight: d.suggestion.piece_weight} : null,
    }
}

export async function getFoodPrice(foodId: number): Promise<FoodPriceDetail> {
    return detail(await kitchenFetch(`foods/${foodId}/price/`))
}

export interface FoodPriceUpdate {
    price?: number | null
    per?: PricePer
    packageAmount?: number | null
    packageKind?: PackageKind | ''
    packagePrice?: number | null
    pieceWeight?: number | null
    /** store the dictionary price, as estimated */
    suggest?: boolean
}

export async function setFoodPrice(foodId: number, u: FoodPriceUpdate): Promise<FoodPriceDetail> {
    const body: any = {}
    if (u.suggest) body.suggest = true
    if (u.price !== undefined) {
        body.price = u.price
        body.per = u.per
    }
    if (u.packageAmount !== undefined) {
        body.package_amount = u.packageAmount
        body.package_kind = u.packageKind
        body.package_price = u.packagePrice ?? null
    }
    if (u.pieceWeight !== undefined) body.piece_weight = u.pieceWeight
    return detail(await priceFetch(`foods/${foodId}/price/`, 'PUT', body))
}

export async function listMissingPrices(): Promise<{ count: number, suggested: number, results: (FoodPriceDetail & { recipes: number, shopping: number })[] }> {
    const data = await kitchenFetch('prices/missing/')
    return {
        count: data.count, suggested: data.suggested,
        results: data.results.map((r: any) => ({...detail({...r, price: null, package: null, piece_weight: null}), recipes: r.recipes, shopping: r.shopping})),
    }
}

export async function applyAllSuggestions(): Promise<{ applied: number, count: number }> {
    return kitchenFetch('prices/missing/', {method: 'POST'})
}

function recipePrice(r: any): RecipePrice {
    return {id: r.id, total: r.total, perServing: r.per_serving, servings: r.servings, missing: r.missing}
}

export async function estimateRecipes(recipes: { id: number, servings?: number | null }[]): Promise<{ total: number, recipes: RecipePrice[], missing: MissingPrice[] }> {
    const data = await kitchenFetch('prices/recipes/', {method: 'POST', body: JSON.stringify({recipes})})
    return {total: data.total, recipes: data.recipes.map(recipePrice), missing: data.missing}
}

export async function estimateShopping(entries: number[]): Promise<ShoppingPrice> {
    const data = await kitchenFetch('prices/shopping/', {method: 'POST', body: JSON.stringify({entries})})
    return {total: data.total, checkedTotal: data.checked_total, items: data.items, missing: data.missing}
}

export async function adjustAfterShopping(entries: number[], paid: number, apply: boolean): Promise<Adjustment> {
    const d = await kitchenFetch('prices/shopping/adjust/', {method: 'POST', body: JSON.stringify({entries, paid, apply})})
    return {
        paid: d.paid, estimated: d.estimated, estimatedPart: d.estimated_part, confirmedPart: d.confirmed_part,
        factor: d.factor, percent: d.percent, adjusted: d.adjusted, missing: d.missing,
    }
}

export async function correctShoppingItem(foodId: number, entries: number[], paid: number): Promise<FoodPriceDetail> {
    return detail(await priceFetch('prices/shopping/correct/', 'POST', {food: foodId, entries, paid}))
}

// ---------------------------------------------------------------- formatting

/** "6,40 €" (two decimals under 100 €, none above) */
export function euros(value: number, locale: string) {
    const digits = Math.abs(value) >= 100 ? 0 : 2
    return new Intl.NumberFormat(locale, {style: 'currency', currency: 'EUR', minimumFractionDigits: digits, maximumFractionDigits: digits}).format(value)
}

/** a number typed by the user, with a comma or a dot; null when empty or not a positive number */
export function parseAmount(text: string | number | null | undefined): number | null {
    if (text === null || text === undefined) return null
    const value = Number(String(text).trim().replace(/\s/g, '').replace(',', '.'))
    return String(text).trim() !== '' && Number.isFinite(value) && value >= 0 ? value : null
}

// ---------------------------------------------------------------- price form (food sheet, "foods without a price")

export type PackageUnit = 'g' | 'kg' | 'ml' | 'l' | 'piece'

export interface PriceForm {
    price: string
    per: PricePer
    packageAmount: string
    packageUnit: PackageUnit
    packagePrice: string
    pieceWeight: string
}

const PACKAGE_UNITS: Record<PackageUnit, { kind: PackageKind, factor: number }> = {
    g: {kind: 'g', factor: 1}, kg: {kind: 'g', factor: 1000}, ml: {kind: 'ml', factor: 1}, l: {kind: 'ml', factor: 1000},
    piece: {kind: 'piece', factor: 1},
}

/** decimal text as the user reads it in their language ("2,5") */
export function decimalText(value: number | null | undefined, locale: string) {
    if (value === null || value === undefined) return ''
    return new Intl.NumberFormat(locale, {maximumFractionDigits: 4, useGrouping: false}).format(value)
}

export function emptyPriceForm(): PriceForm {
    return {price: '', per: 'kg', packageAmount: '', packageUnit: 'g', packagePrice: '', pieceWeight: ''}
}

export function priceFormOf(d: FoodPriceDetail | null, locale: string): PriceForm {
    const form = emptyPriceForm()
    if (!d) return form
    if (d.price) {
        form.price = decimalText(d.price.price, locale)
        form.per = d.price.per
    } else if (d.suggestion) {
        form.per = d.suggestion.per
    }
    if (d.package) {
        // 1000 g reads "1 kg"
        const big = d.package.kind != 'piece' && d.package.amount >= 1000 && d.package.amount % 100 == 0
        form.packageUnit = d.package.kind == 'piece' ? 'piece' : big ? (d.package.kind == 'g' ? 'kg' : 'l') : d.package.kind
        form.packageAmount = decimalText(big ? d.package.amount / 1000 : d.package.amount, locale)
        form.packagePrice = decimalText(d.package.price, locale)
    }
    form.pieceWeight = decimalText(d.pieceWeight, locale)
    return form
}

/** what to send for a form (only what changed since `initial`) */
export function priceUpdateOf(form: PriceForm, initial: PriceForm): FoodPriceUpdate | null {
    const update: FoodPriceUpdate = {}
    if (form.price != initial.price || (form.price && form.per != initial.per)) {
        update.price = parseAmount(form.price)
        update.per = form.per
    }
    if (form.packageAmount != initial.packageAmount || form.packageUnit != initial.packageUnit || form.packagePrice != initial.packagePrice) {
        const amount = parseAmount(form.packageAmount)
        const unit = PACKAGE_UNITS[form.packageUnit]
        update.packageAmount = amount ? amount * unit.factor : null
        update.packageKind = amount ? unit.kind : ''
        update.packagePrice = amount ? parseAmount(form.packagePrice) : null
    }
    if (form.pieceWeight != initial.pieceWeight) update.pieceWeight = parseAmount(form.pieceWeight) || null
    return Object.keys(update).length ? update : null
}

/** a form field that holds something that is not a number */
export function priceFormInvalid(form: PriceForm) {
    return [form.price, form.packageAmount, form.packagePrice, form.pieceWeight].some(v => v.trim() !== '' && parseAmount(v) === null)
}
