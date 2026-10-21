import {kitchenFetch} from "@/fork/api";

/** a crop as fractions of the (upright) image: {x, y} top-left corner, {w, h} size, all between 0 and 1 */
export interface ImageCrop {
    x: number
    y: number
    w: number
    h: number
}

/** the cropped look of `src` in a box of the crop's ratio, with CSS only (works for a photo of another site too) */
export function cropPreviewStyle(src: string, crop: ImageCrop) {
    const pos = (start: number, size: number) => size >= 1 ? 0 : (start / (1 - size)) * 100
    return {
        backgroundImage: `url("${src.replace(/"/g, '%22')}")`,
        backgroundSize: `${100 / crop.w}% ${100 / crop.h}%`,
        backgroundPosition: `${pos(crop.x, crop.w)}% ${pos(crop.y, crop.h)}%`,
        backgroundRepeat: 'no-repeat',
    }
}

/**
 * crop a recipe photo on the server: the photo at `imageUrl` (an import, downloaded by the server), else the recipe's
 * current photo
 */
export function cropRecipeImage(recipeId: number, crop: ImageCrop, imageUrl?: string | null): Promise<{ id: number, image: string }> {
    return kitchenFetch(`recipes/${recipeId}/image/`, {method: 'PUT', body: JSON.stringify({crop, image_url: imageUrl || undefined})})
}

/**
 * photo of an imported recipe: cropped on the server when the user framed it, else upstream's own path (`upstream`,
 * the import page's updateRecipeImage), unchanged
 */
export function saveImportImage<T>(recipeId: number, imageUrl: string | undefined | null, crop: ImageCrop | null,
                                   upstream: (recipeId: number, file: null, imageUrl?: string) => Promise<T>): Promise<unknown> {
    if (crop && imageUrl) return cropRecipeImage(recipeId, crop, imageUrl)
    return upstream(recipeId, null, imageUrl ?? undefined)
}
