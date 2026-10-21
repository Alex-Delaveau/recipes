// Pure detection of French durations in step text ("10 min", "1 h 30", "20 à 25 minutes").
// No imports on purpose: scripts/fork/tests runs this file directly with node (type stripping).

export interface DetectedDuration {
    /** offset of the match in the input text */
    start: number
    end: number
    text: string
    /** duration in seconds (lower bound for a range) */
    seconds: number
    /** upper bound in seconds, only for a range ("20 à 25 minutes") */
    maxSeconds?: number
}

const WORD_NUMBERS: Record<string, number> = {
    un: 1, une: 1, deux: 2, trois: 3, quatre: 4, cinq: 5, six: 6, sept: 7, huit: 8, neuf: 9, dix: 10,
    douze: 12, quinze: 15, vingt: 20, trente: 30, quarante: 40, 'quarante-cinq': 45, cinquante: 50,
}
const FRACTIONS: Record<string, number> = {'½': 0.5, '¼': 0.25, '¾': 0.75}

const NUM = String.raw`(?:\d+\s*\/\s*\d+|\d+(?:[.,]\d+)?(?:\s*[½¼¾])?|[½¼¾]|quarante-cinq|une|un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|douze|quinze|vingt|trente|quarante|cinquante)`
const H = String.raw`(?:heures?|hrs?|h)`
const M = String.raw`(?:minutes?|mins?|mn)`
const S = String.raw`(?:secondes?|secs?|s)`
const B = String.raw`(?![\p{L}\d])`
const BEFORE = String.raw`(?<![\p{L}\d.,/])`

// one duration, most specific forms first
const SINGLE = new RegExp([
    String.raw`${BEFORE}(?<quarters>un|trois)\s+quarts?\s+d['’]\s?heure${B}`,
    String.raw`${BEFORE}(?:une\s+)?(?<half>demi-heure)${B}`,
    String.raw`${BEFORE}(?<h>${NUM})\s*${H}(?:\s*(?:et\s+)?(?<hfrac>demie|quart)${B}|\s*(?<hm>\d{1,2})(?:\s*(?<hmu>${M}))?${B}|${B})`,
    String.raw`${BEFORE}(?<m>${NUM})\s*${M}(?:\s*(?<ms>\d{1,2})\s*${S}${B}|${B})`,
    String.raw`${BEFORE}(?<s>${NUM})\s*${S}${B}`,
].join('|'), 'giu')

// what may stand right before a duration to make it a range: "20 à", "2-", "entre 1 h et"
const RANGE_PREFIX = new RegExp(String.raw`${BEFORE}(?<low>${NUM})(?:\s*(?<lowUnit>${H}|${M}|${S}))?\s*(?:à|-|–|—|ou|et)\s*$`, 'iu')

const RANGE_SEP = /^\s*(?:à|-|–|—|ou|et)\s*$/iu

// a bare number after hours ("1 h 30") must not be a quantity ("1 h 30 g")
const MEASURE_AFTER = /^\s*(?:g|kg|mg|l|cl|ml|dl|cm|mm|°|%|personnes?|œufs?|oeufs?)(?![\p{L}])/iu

export function parseNumber(raw: string): number {
    const s = raw.trim().toLowerCase()
    const word = WORD_NUMBERS[s] ?? FRACTIONS[s]
    if (word !== undefined) return word
    const frac = s.match(/^(\d+)\s*\/\s*(\d+)$/)
    if (frac) return Number(frac[2]) ? Number(frac[1]) / Number(frac[2]) : NaN
    const mixed = s.match(/^(\d+(?:[.,]\d+)?)\s*([½¼¾])?$/)
    if (mixed) return parseFloat((mixed[1] ?? '').replace(',', '.')) + (mixed[2] ? FRACTIONS[mixed[2]] ?? 0 : 0)
    return NaN
}

function unitSeconds(unit: string): number {
    const u = unit.toLowerCase()
    if (u.startsWith('h')) return 3600
    if (u.startsWith('s')) return 1
    return 60
}

interface Single { start: number, end: number, seconds: number, unit: number }

function singles(text: string): Single[] {
    const out: Single[] = []
    SINGLE.lastIndex = 0
    let m: RegExpExecArray | null
    while ((m = SINGLE.exec(text)) !== null) {
        const g = m.groups ?? {}
        let end = m.index + m[0].length
        let seconds = NaN
        let unit = 60
        if (g.quarters) {
            seconds = (g.quarters.toLowerCase() === 'trois' ? 45 : 15) * 60
        } else if (g.half) {
            seconds = 1800
        } else if (g.h) {
            unit = 3600
            seconds = parseNumber(g.h) * 3600
            if (g.hfrac) seconds += g.hfrac.toLowerCase() === 'demie' ? 1800 : 900
            if (g.hm) {
                if (!g.hmu && MEASURE_AFTER.test(text.slice(end))) {
                    // "1 h 30 g": keep "1 h" only
                    end = m.index + m[0].search(/\s*\d{1,2}$/)
                } else {
                    seconds += Number(g.hm) * 60
                }
            }
        } else if (g.m) {
            seconds = parseNumber(g.m) * 60
            if (g.ms) seconds += Number(g.ms)
        } else if (g.s) {
            unit = 1
            seconds = parseNumber(g.s)
        }
        if (Number.isFinite(seconds) && seconds > 0 && seconds <= 48 * 3600) {
            out.push({start: m.index, end, seconds: Math.round(seconds), unit})
        }
    }
    return out
}

/** All durations found in a plain text, in order. Ranges are merged into one entry with maxSeconds. */
export function detectDurations(text: string): DetectedDuration[] {
    const found = singles(text)
    const out: DetectedDuration[] = []
    for (const cur of found) {
        let start = cur.start
        let low: number | undefined
        const prev = out[out.length - 1]
        if (prev && prev.maxSeconds === undefined && prev.seconds < cur.seconds && RANGE_SEP.test(text.slice(prev.end, cur.start))) {
            // the low part is a full duration itself: "15 s à 45 min", "1 h 30 à 2 h"
            out.pop()
            start = prev.start
            low = prev.seconds
        } else {
            // bare low number taking the unit of the high part: "20 à 25 minutes", "2-3 min"
            const prefix = text.slice(prev?.end ?? 0, cur.start).match(RANGE_PREFIX)
            if (prefix && prefix.index !== undefined) {
                const n = parseNumber(prefix.groups!.low ?? '')
                const unit = prefix.groups!.lowUnit ? unitSeconds(prefix.groups!.lowUnit) : cur.unit
                const candidate = Math.round(n * unit)
                if (Number.isFinite(candidate) && candidate > 0 && candidate < cur.seconds) {
                    low = candidate
                    start = (prev?.end ?? 0) + prefix.index
                }
            }
        }
        out.push(low !== undefined
            ? {start, end: cur.end, text: text.slice(start, cur.end), seconds: low, maxSeconds: cur.seconds}
            : {start: cur.start, end: cur.end, text: text.slice(cur.start, cur.end), seconds: cur.seconds})
    }
    return out
}

/** Compact, language-neutral display: "45 s", "10 min", "1 min 30 s", "1 h 30", "2 h". */
export function formatDuration(totalSeconds: number): string {
    const t = Math.max(0, Math.round(totalSeconds))
    const h = Math.floor(t / 3600)
    const m = Math.floor((t % 3600) / 60)
    const s = t % 60
    if (h > 0) return m > 0 ? `${h} h ${String(m).padStart(2, '0')}` : `${h} h`
    if (m > 0) return s > 0 ? `${m} min ${s} s` : `${m} min`
    return `${s} s`
}

/** Countdown display for a running timer: "4:05", "1:02:30". */
export function formatCountdown(ms: number): string {
    const t = Math.max(0, Math.ceil(ms / 1000))
    const h = Math.floor(t / 3600)
    const m = Math.floor((t % 3600) / 60)
    const s = String(t % 60).padStart(2, '0')
    return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${s}` : `${m}:${s}`
}
