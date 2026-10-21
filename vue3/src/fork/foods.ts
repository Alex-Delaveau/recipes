import {ApiApi, Automation, AutomationTypeEnum} from "@/openapi";

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
