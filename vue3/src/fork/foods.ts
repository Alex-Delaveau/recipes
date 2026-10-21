import {ApiApi, Automation, AutomationTypeEnum, Food} from "@/openapi";

/** accent and case insensitive key for instant search ("Échalote" matches "echal") */
export function searchKey(text: string) {
    return text.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/œ/gi, 'oe').toLowerCase().trim()
}

/**
 * FOOD_ALIAS automation (upstream): the next import or parsed line naming `from` uses the food `to` instead,
 * so the duplicate is not created again. Same shape as the upstream merge dialog.
 */
export function createFoodAlias(from: string, to: string, t: (key: string) => string) {
    return new ApiApi().apiAutomationCreate({
        automation: {
            name: `${t('Fork_Alias')} ${from} -> ${to}`.substring(0, 128),
            param1: from,
            param2: to,
            type: AutomationTypeEnum.FoodAlias,
        } as Automation,
    })
}

/**
 * upstream merge of `drop` into `keep` (ingredients and shopping entries move over), then the alias for the next imports.
 * The alias is best effort: the merge is not undone when it fails.
 */
export async function mergeFood(drop: { id: number, name: string }, keep: { id: number, name: string }, t: (key: string) => string) {
    await new ApiApi().apiFoodMergeUpdate({id: drop.id, target: keep.id, food: {} as Food})
    await createFoodAlias(drop.name, keep.name, t).catch(() => {})
}

/** existing food named `name` or with that plural (case and accents aside), other than `exceptId` */
export async function findFoodByName(name: string, exceptId?: number): Promise<{ id: number, name: string } | null> {
    const r = await new ApiApi().apiFoodList({query: name, pageSize: 50})
    const key = searchKey(name)
    const found = r.results.find(f => f.id != exceptId && (searchKey(f.name) == key || (f.pluralName && searchKey(f.pluralName) == key)))
    return found ? {id: found.id!, name: found.name} : null
}

/**
 * give a food a new name: merged into the food of that name when it exists, renamed otherwise.
 * Either way the old name becomes an alias. Returns the food that carries the name in the end.
 */
export async function renameOrMergeFood(food: { id: number, name: string }, newName: string, t: (key: string) => string) {
    const name = newName.trim()
    const existing = await findFoodByName(name, food.id)
    if (existing) {
        await mergeFood(food, existing, t)
        return {id: existing.id, name: existing.name, merged: true}
    }
    if (name != food.name) {
        await new ApiApi().apiFoodPartialUpdate({id: food.id, patchedFood: {name}})
        if (name.toLowerCase() != food.name.toLowerCase()) await createFoodAlias(food.name, name, t).catch(() => {})
    }
    return {id: food.id, name, merged: false}
}
