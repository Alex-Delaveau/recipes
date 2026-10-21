// Web Share Target helper. No imports on purpose: scripts/fork/tests runs this file directly with node.

const URL_RE = /https?:\/\/[^\s<>"'«»]+/i

/**
 * First http(s) URL found in the shared fields, in this order: url, text, title.
 * Apps share "Recette de tarte https://…" in `text`, sometimes with an empty or bogus `url`.
 */
export function extractSharedUrl(...fields: Array<string | null | undefined | (string | null)[]>): string | null {
    for (const field of fields) {
        const values = Array.isArray(field) ? field : [field]
        for (const value of values) {
            if (typeof value !== 'string') continue
            const match = value.match(URL_RE)
            if (match) return match[0].replace(/[).,;:!?\]]+$/, '')
        }
    }
    return null
}
