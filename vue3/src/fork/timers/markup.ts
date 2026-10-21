// Turns the durations of a rendered step (HTML from the API) into tappable timer links.
// The result goes through the upstream `Instructions` component, which compiles it as a Vue template:
// text is re-escaped, braces included, so no step text can become a template expression.
import {detectDurations} from "./detect.ts";

/** elements whose text is left alone */
const SKIP = /^<\/?(a|code|pre|button|scalable-number|plural-name|script|style)\b/i

const ENTITIES: Record<string, string> = {amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', rsquo: '’', lsquo: '‘'}

function decode(text: string): string {
    return text.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (all, code: string) => {
        if (code[0] == '#') {
            const n = code[1] == 'x' || code[1] == 'X' ? parseInt(code.slice(2), 16) : parseInt(code.slice(1), 10)
            return Number.isFinite(n) ? String.fromCodePoint(n) : all
        }
        return ENTITIES[code.toLowerCase()] ?? all
    })
}

function escape(text: string): string {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\{/g, '&#123;').replace(/\}/g, '&#125;')
}

function markText(raw: string): string {
    if (!/\d|une?\s|demi|quart/i.test(raw)) return raw
    const text = decode(raw)
    const found = detectDurations(text)
    if (!found.length) return raw
    let out = ''
    let last = 0
    for (const d of found) {
        out += escape(text.slice(last, d.start))
        const max = d.maxSeconds !== undefined ? ` data-max="${d.maxSeconds}"` : ''
        out += `<span class="fork-timer-link" role="button" tabindex="0" data-seconds="${d.seconds}"${max}>${escape(d.text)}</span>`
        last = d.end
    }
    return out + escape(text.slice(last))
}

export function markDurations(html: string): string {
    let skipDepth = 0
    return html.split(/(<[^>]*>)/).map(part => {
        if (part.startsWith('<')) {
            const skip = part.match(SKIP)
            if (skip && !part.endsWith('/>')) skipDepth = Math.max(0, skipDepth + (part[1] == '/' ? -1 : 1))
            return part
        }
        return skipDepth > 0 ? part : markText(part)
    }).join('')
}
