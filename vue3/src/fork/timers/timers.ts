// Kitchen timers kept by the app itself (a PWA has no access to the system timer).
// A timer stores its end time, not a countdown: it survives reloads and a frozen background tab.
import {defineStore} from "pinia";
import {computed, ref, watch} from "vue";
import {useStorage} from "@vueuse/core";

export interface ForkTimer {
    id: string
    /** what the timer is for, e.g. "Curry · étape 2" */
    label: string
    /** the duration as written in the step, e.g. "20 min" */
    durationText: string
    recipeId?: number
    durationMs: number
    /** epoch ms when the timer rings, null when paused or done */
    endAt: number | null
    /** remaining time while paused */
    remainingMs: number
    done: boolean
}

/** an alarm older than this (app closed meanwhile) is shown as done, without sound */
const LATE_ALARM_MS = 60 * 1000
const RING_REPEAT_MS = 3000
const RING_MAX_MS = 60 * 1000

export const useForkTimers = defineStore('fork_timers', () => {
    const timers = useStorage<ForkTimer[]>('fork_timers', [], localStorage, {writeDefaults: false})
    const now = ref(Date.now())
    let tickId = 0
    let audio: AudioContext | null = null
    const ringing = new Map<string, number>()

    const active = computed(() => timers.value)
    const hasRunning = computed(() => timers.value.some(t => t.endAt !== null))

    function remainingMs(timer: ForkTimer) {
        if (timer.done) return 0
        return timer.endAt !== null ? Math.max(0, timer.endAt - now.value) : timer.remainingMs
    }

    function start(seconds: number, label: string, durationText: string, recipeId?: number) {
        unlockAudio()
        askNotificationPermission()
        const durationMs = Math.round(seconds * 1000)
        timers.value = [...timers.value, {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            label, durationText, recipeId, durationMs,
            endAt: Date.now() + durationMs, remainingMs: durationMs, done: false,
        }]
        tick()
    }

    function update(id: string, change: (t: ForkTimer) => Partial<ForkTimer>) {
        timers.value = timers.value.map(t => t.id == id ? {...t, ...change(t)} : t)
    }

    function pause(id: string) {
        update(id, t => t.endAt === null ? {} : {remainingMs: Math.max(0, t.endAt - Date.now()), endAt: null})
    }

    function resume(id: string) {
        unlockAudio()
        update(id, t => t.endAt !== null || t.done ? {} : {endAt: Date.now() + t.remainingMs})
        tick()
    }

    function addMinute(id: string) {
        unlockAudio()
        stopRinging(id)
        update(id, t => {
            if (t.done) return {done: false, endAt: Date.now() + 60000, remainingMs: 60000}
            if (t.endAt === null) return {remainingMs: t.remainingMs + 60000}
            return {endAt: t.endAt + 60000}
        })
        tick()
    }

    function stop(id: string) {
        stopRinging(id)
        timers.value = timers.value.filter(t => t.id != id)
    }

    function tick() {
        now.value = Date.now()
        for (const t of timers.value) {
            if (t.endAt !== null && t.endAt <= now.value) {
                const late = now.value - t.endAt > LATE_ALARM_MS
                update(t.id, () => ({done: true, endAt: null, remainingMs: 0}))
                if (!late) ring(t)
            }
        }
        clearTimeout(tickId)
        if (hasRunning.value) {
            tickId = window.setTimeout(tick, 250)
        }
    }

    // ---- alarm: sound, vibration, system notification when allowed ----

    function unlockAudio() {
        // must be created or resumed during a user gesture, or the browser keeps it muted
        try {
            const Ctx = window.AudioContext ?? (window as any).webkitAudioContext
            if (!Ctx) return
            if (!audio) audio = new Ctx()
            if (audio.state == 'suspended') audio.resume().catch(() => {})
        } catch {
            audio = null
        }
    }

    function beep() {
        if (!audio || audio.state != 'running') return
        const start = audio.currentTime
        for (let i = 0; i < 3; i++) {
            const osc = audio.createOscillator()
            const gain = audio.createGain()
            osc.type = 'sine'
            osc.frequency.value = 880
            gain.gain.setValueAtTime(0.0001, start + i * 0.35)
            gain.gain.exponentialRampToValueAtTime(0.4, start + i * 0.35 + 0.02)
            gain.gain.exponentialRampToValueAtTime(0.0001, start + i * 0.35 + 0.25)
            osc.connect(gain).connect(audio.destination)
            osc.start(start + i * 0.35)
            osc.stop(start + i * 0.35 + 0.3)
        }
    }

    function ring(timer: ForkTimer) {
        const started = Date.now()
        const once = () => {
            beep()
            // the browser refuses (and logs) a vibration before any tap on the page, e.g. right after a reload
            if ((navigator as any).userActivation?.hasBeenActive !== false) navigator.vibrate?.([300, 150, 300, 150, 300])
        }
        once()
        stopRinging(timer.id)
        ringing.set(timer.id, window.setInterval(() => {
            if (Date.now() - started > RING_MAX_MS || !timers.value.some(t => t.id == timer.id && t.done)) {
                stopRinging(timer.id)
            } else {
                once()
            }
        }, RING_REPEAT_MS))
        notify(timer)
    }

    function stopRinging(id: string) {
        const handle = ringing.get(id)
        if (handle !== undefined) {
            clearInterval(handle)
            ringing.delete(id)
        }
    }

    function askNotificationPermission() {
        // asked once, on the first timer the user starts; refusing changes nothing else
        if ('Notification' in window && Notification.permission == 'default') {
            Notification.requestPermission().catch(() => {})
        }
    }

    function notify(timer: ForkTimer) {
        if (!('Notification' in window) || Notification.permission != 'granted' || document.visibilityState == 'visible') return
        const title = timer.label
        const options = {body: timer.durationText, tag: `fork-timer-${timer.id}`}
        navigator.serviceWorker?.getRegistration().then(reg => {
            if (reg) return reg.showNotification(title, options)
            new Notification(title, options)
        }).catch(() => {})
    }

    // a reload or a background tab: recompute everything from the end times
    document.addEventListener('visibilitychange', () => tick())
    watch(hasRunning, (running) => {
        if (running) tick()
    })
    tick()

    return {timers: active, now, remainingMs, start, pause, resume, addMinute, stop}
})
