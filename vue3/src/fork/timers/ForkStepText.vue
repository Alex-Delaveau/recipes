<template>
    <!-- Step text (upstream Instructions) whose durations start a timer when tapped -->
    <div class="fork-step-text" @click="onActivate" @keydown.enter.space="onActivate">
        <instructions :key="marked" :instructions_html="marked" :ingredient_factor="factor"></instructions>
    </div>

    <v-bottom-sheet v-model="rangeSheet">
        <v-card v-if="range" :title="$t('Fork_Timer_Choose')" :subtitle="range.text">
            <v-card-text class="d-flex flex-column ga-2">
                <v-btn v-for="option in rangeOptions" :key="option" size="x-large" variant="tonal" block prepend-icon="fa-solid fa-stopwatch"
                       @click="startRange(option)">{{ formatDuration(option) }}
                </v-btn>
            </v-card-text>
        </v-card>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
import {computed, ref} from "vue";
// @ts-ignore upstream component written in plain JS
import Instructions from "@/components/display/Instructions.vue";
import {markDurations} from "@/fork/timers/markup";
import {formatDuration} from "@/fork/timers/detect";
import {useForkTimers} from "@/fork/timers/timers";

const props = defineProps({
    html: {type: String, required: true},
    factor: {type: Number, required: true},
    /** shown in the timers bar, e.g. "Curry · étape 2" */
    label: {type: String, required: true},
    recipeId: {type: Number, required: false},
})

const timers = useForkTimers()
const marked = computed(() => markDurations(props.html))
const rangeSheet = ref(false)
const range = ref<{ low: number, high: number, text: string } | null>(null)

/** low, high and, when they are far enough apart, the middle (rounded to the minute above 2 min) */
const rangeOptions = computed(() => {
    if (!range.value) return []
    const {low, high} = range.value
    const unit = high >= 120 ? 60 : 5
    const middle = Math.round((low + high) / 2 / unit) * unit
    return middle > low && middle < high ? [low, middle, high] : [low, high]
})

function onActivate(event: Event) {
    const link = (event.target as HTMLElement | null)?.closest?.('.fork-timer-link') as HTMLElement | null
    if (!link) return
    event.preventDefault()
    const seconds = Number(link.dataset.seconds)
    const max = link.dataset.max ? Number(link.dataset.max) : undefined
    const text = link.textContent?.trim() ?? ''
    if (max !== undefined) {
        range.value = {low: seconds, high: max, text}
        rangeSheet.value = true
    } else if (seconds > 0) {
        timers.start(seconds, props.label, text, props.recipeId)
    }
}

function startRange(seconds: number) {
    if (range.value) timers.start(seconds, props.label, range.value.text, props.recipeId)
    rangeSheet.value = false
}
</script>

<style>
/* not scoped: the links live inside the compiled step HTML */
.fork-timer-link {
    /* the vertical padding enlarges the tap area to 44 px without moving the lines; the tint stays on the text */
    padding: 10px 2px;
    margin: 0 -2px;
    background-clip: content-box;
    background-color: rgba(var(--v-theme-primary), 0.14);
    color: inherit;
    font-weight: 600;
    border-radius: 6px;
    cursor: pointer;
    text-decoration: underline dotted rgb(var(--v-theme-primary));
    text-underline-offset: 3px;
    -webkit-tap-highlight-color: transparent;
}

.fork-timer-link:focus-visible {
    outline: 2px solid rgb(var(--v-theme-primary));
    outline-offset: -8px;
}
</style>
