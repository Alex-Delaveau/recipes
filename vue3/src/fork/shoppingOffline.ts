// Shopping in the shop without network: the check/uncheck queue of ShoppingStore and the last known list are kept
// on the device, so a closed app loses nothing and an offline reload still shows the list.
// The server stays the truth: the queue is only a send buffer, replayed when the network comes back.
import {ref} from "vue";
import {useStorage} from "@vueuse/core";
import {ShoppingListEntry} from "@/openapi";
import {IShoppingSyncQueueEntry} from "@/types/Shopping";

const QUEUE_KEY = 'fork_shopping_sync_queue'
const SNAPSHOT_KEY = 'fork_shopping_snapshot'
const DATE_FIELDS = ['createdAt', 'updatedAt', 'completedAt', 'delayUntil'] as const

/** number of entries whose checked state still has to reach the server */
export const pendingShoppingChanges = ref(0)

/** keep the screen on while the shopping list is open (this device, on by default) */
export const keepShoppingScreenOn = useStorage('fork_shopping_keep_screen_on', true)

function countPending(queue: IShoppingSyncQueueEntry[]) {
    return new Set(queue.flatMap(q => q.ids)).size
}

function read(key: string): unknown {
    try {
        return JSON.parse(localStorage.getItem(key) ?? 'null')
    } catch {
        return null
    }
}

function write(key: string, value: unknown) {
    try {
        if (value === null) localStorage.removeItem(key)
        else localStorage.setItem(key, JSON.stringify(value))
    } catch {
        // storage full or blocked: the queue still works in memory
    }
}

/** queue saved by a previous visit; requests that were in flight are sent again */
export function loadSyncQueue(): IShoppingSyncQueueEntry[] {
    const raw = read(QUEUE_KEY)
    const queue = (Array.isArray(raw) ? raw : [])
        .filter(q => q && Array.isArray(q.ids) && typeof q.checked == 'boolean')
        .map(q => ({
            ids: q.ids.filter((id: unknown) => typeof id == 'number'),
            checked: q.checked,
            status: String(q.status).includes('failed_before') ? 'waiting_failed_before' : 'waiting',
        } as IShoppingSyncQueueEntry))
        .filter(q => q.ids.length)
    pendingShoppingChanges.value = countPending(queue)
    return queue
}

export function saveSyncQueue(queue: IShoppingSyncQueueEntry[]) {
    write(QUEUE_KEY, queue.length ? queue.map(q => ({ids: q.ids, checked: q.checked, status: q.status})) : null)
    pendingShoppingChanges.value = countPending(queue)
}

/** entries just loaded from the server must not undo the checks that are still waiting to be sent */
export function applyPendingChecks(entries: Map<number, ShoppingListEntry>, queue: IShoppingSyncQueueEntry[]) {
    queue.forEach(q => q.ids.forEach(id => {
        const entry = entries.get(id)
        if (entry) entry.checked = q.checked
    }))
}

export function saveShoppingSnapshot(entries: Map<number, ShoppingListEntry>) {
    write(SNAPSHOT_KEY, Array.from(entries.values()))
}

/** last known list, or null if this device never loaded it */
export function loadShoppingSnapshot(): Map<number, ShoppingListEntry> | null {
    const raw = read(SNAPSHOT_KEY)
    if (!Array.isArray(raw)) return null
    const entries = new Map<number, ShoppingListEntry>()
    raw.forEach((e: any) => {
        if (typeof e?.id != 'number') return
        DATE_FIELDS.forEach(f => {
            if (typeof e[f] == 'string') e[f] = new Date(e[f])
        })
        entries.set(e.id, e as ShoppingListEntry)
    })
    return entries
}
