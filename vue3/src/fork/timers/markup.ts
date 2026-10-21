// Turns the durations of a rendered step (HTML from the API) into tappable timer links.
// The result goes through the upstream `Instructions` component, which compiles it as a Vue template.
// Safety: the HTML is never decoded and re-encoded. Tags (attributes included, quotes respected) are copied as they
// are, and in text only <span> tags are inserted between characters: the step text itself is left byte for byte.
import {detectDurations} from "./detect.ts";

/** elements whose text is left alone */
const SKIP = /^<\/?(a|code|pre|button|scalable-number|plural-name|script|style|textarea)\b/i

/** a tag, comment or doctype; a ">" inside a quoted attribute value does not end it */
const TAG = /(<!--[\s\S]*?-->|<(?:[^>"']|"[^"]*"|'[^']*')*>)/

const ENTITIES: Record<string, string> = {amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', rsquo: '’', lsquo: '‘'}

/**
 * Text for detection, plus for each of its characters the offset in the raw HTML text.
 * Entities count as one character (unknown named entities stay as written, so they just never match a duration).
 */
function decodeWithOffsets(raw: string): { text: string, offsets: number[] } {
    let text = ''
    const offsets: number[] = []
    const re = /&(#x[0-9a-f]+|#\d+|[a-z]+);/gi
    let last = 0
    let m: RegExpExecArray | null
    const push = (chunk: string, at: number, sameOffset: boolean) => {
        for (let i = 0; i < chunk.length; i++) offsets.push(sameOffset ? at : at + i)
        text += chunk
    }
    while ((m = re.exec(raw)) !== null) {
        push(raw.slice(last, m.index), last, false)
        const code = m[1] ?? ''
        let char: string | undefined
        if (code[0] == '#') {
            const n = code[1] == 'x' || code[1] == 'X' ? parseInt(code.slice(2), 16) : parseInt(code.slice(1), 10)
            char = Number.isFinite(n) && n > 0 && n <= 0x10ffff ? String.fromCodePoint(n) : undefined
        } else {
            char = ENTITIES[code.toLowerCase()]
        }
        if (char !== undefined) push(char, m.index, true)
        else push(m[0], m.index, false)
        last = m.index + m[0].length
    }
    push(raw.slice(last), last, false)
    offsets.push(raw.length)
    return {text, offsets}
}

function markText(raw: string): string {
    const {text, offsets} = decodeWithOffsets(raw)
    const found = detectDurations(text)
    if (!found.length) return raw
    let out = ''
    let last = 0
    for (const d of found) {
        // never split a surrogate pair or an entity: offsets point at the first raw character of each text character
        const start = offsets[d.start] ?? raw.length
        const end = offsets[d.end] ?? raw.length
        if (end <= start) continue
        out += raw.slice(last, start)
        const max = d.maxSeconds !== undefined ? ` data-max="${d.maxSeconds}"` : ''
        out += `<span class="fork-timer-link" role="button" tabindex="0" data-seconds="${d.seconds}"${max}>${raw.slice(start, end)}</span>`
        last = end
    }
    return out + raw.slice(last)
}

export function markDurations(html: string): string {
    let skipDepth = 0
    return html.split(TAG).map(part => {
        if (part.startsWith('<')) {
            const skip = part.match(SKIP)
            if (skip && !part.endsWith('/>')) skipDepth = Math.max(0, skipDepth + (part[1] == '/' ? -1 : 1))
            return part
        }
        // a stray "<" or ">" in text means the HTML is not what bleach produces: leave it untouched
        return skipDepth > 0 || /[<>]/.test(part) ? part : markText(part)
    }).join('')
}
