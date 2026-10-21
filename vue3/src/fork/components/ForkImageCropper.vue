<template>
    <!-- Frame a recipe photo: drag to move, pinch / wheel / slider to zoom, a choice of shapes. The server does the cut. -->
    <v-dialog v-model="open" :fullscreen="!mdAndUp" max-width="720" scrollable>
        <v-card class="fork-crop">
            <v-card-title class="d-flex align-center ga-2">
                <span class="flex-grow-1">{{ $t('Fork_Crop_Title') }}</span>
                <v-btn icon="$close" variant="text" size="44" :aria-label="$t('Close')" @click="open = false"></v-btn>
            </v-card-title>
            <v-card-text>
                <div ref="frame" class="fork-crop__frame" :style="{aspectRatio: String(aspect)}"
                     @pointerdown="down" @pointermove="move" @pointerup="up" @pointercancel="up" @wheel.prevent="wheel">
                    <img v-if="src" :src="src" alt="" draggable="false" class="fork-crop__img" :style="imgStyle" @load="loaded">
                    <div class="fork-crop__grid" aria-hidden="true"></div>
                </div>
                <p class="text-body-2 text-medium-emphasis mt-2">{{ $t('Fork_Crop_Help') }}</p>

                <div class="fork-crop__controls">
                    <v-icon icon="fa-solid fa-magnifying-glass-minus" size="16" aria-hidden="true"></v-icon>
                    <v-slider v-model="zoom" :min="1" :max="4" :step="0.01" hide-details color="primary" :aria-label="$t('Fork_Crop_Zoom')"
                              class="flex-grow-1"></v-slider>
                    <v-icon icon="fa-solid fa-magnifying-glass-plus" size="16" aria-hidden="true"></v-icon>
                </div>
                <v-btn-toggle v-model="aspect" mandatory variant="outlined" divided density="comfortable" class="mt-3 fork-crop__shapes">
                    <v-btn v-for="a in ASPECTS" :key="a.label" :value="a.value" size="large">{{ a.label }}</v-btn>
                </v-btn-toggle>
            </v-card-text>
            <v-card-actions class="pa-4">
                <v-btn variant="text" size="large" @click="reset()">{{ $t('Fork_Crop_Reset') }}</v-btn>
                <v-spacer></v-spacer>
                <v-btn variant="text" size="large" @click="open = false">{{ $t('Cancel') }}</v-btn>
                <v-btn color="primary" variant="flat" size="large" :disabled="!ready" @click="apply()">{{ $t('Fork_Crop_Apply') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import {computed, ref, useTemplateRef, watch} from "vue";
import {useElementSize} from "@vueuse/core";
import {useDisplay} from "vuetify";
import {ImageCrop} from "@/fork/images";

const ASPECTS = [{label: '16:9', value: 16 / 9}, {label: '4:3', value: 4 / 3}, {label: '1:1', value: 1}]

const props = defineProps({
    src: {type: String, default: ''},
})
const emit = defineEmits<{ apply: [crop: ImageCrop, aspect: number] }>()
const open = defineModel<boolean>({default: false})

const {mdAndUp} = useDisplay()
const frame = useTemplateRef<HTMLDivElement>('frame')
const {width: frameW, height: frameH} = useElementSize(frame)

/** recipe page and cards show the photo in 16:9: the default shape */
const aspect = ref(16 / 9)
const natural = ref({w: 0, h: 0})
const zoom = ref(1)
/** position of the image's top-left corner in the frame (px, <= 0) */
const offset = ref({x: 0, y: 0})
const ready = computed(() => natural.value.w > 0 && frameW.value > 0)

/** displayed image size: covers the frame at zoom 1 */
const shown = computed(() => {
    if (!ready.value) return {w: 0, h: 0}
    const base = Math.max(frameW.value / natural.value.w, frameH.value / natural.value.h)
    return {w: natural.value.w * base * zoom.value, h: natural.value.h * base * zoom.value}
})

function clamp(x: number, y: number) {
    return {
        x: Math.min(0, Math.max(frameW.value - shown.value.w, x)),
        y: Math.min(0, Math.max(frameH.value - shown.value.h, y)),
    }
}

const imgStyle = computed(() => ({
    width: `${shown.value.w}px`, height: `${shown.value.h}px`,
    transform: `translate(${offset.value.x}px, ${offset.value.y}px)`,
}))

function center() {
    offset.value = clamp((frameW.value - shown.value.w) / 2, (frameH.value - shown.value.h) / 2)
}

function reset() {
    zoom.value = 1
    lastZoom = 1
    center()
}

function loaded(e: Event) {
    const img = e.target as HTMLImageElement
    natural.value = {w: img.naturalWidth, h: img.naturalHeight}
    reset()
}

/** pinch and wheel go through the zoom value, like the slider */
function setZoom(next: number) {
    zoom.value = Math.min(4, Math.max(1, next))
}

// any zoom change (slider, pinch, wheel) keeps the frame's center in place: the framed subject stays put
let lastZoom = 1
watch(zoom, (z) => {
    if (Math.abs(z - lastZoom) > 1e-6 && ready.value) {
        const cx = frameW.value / 2, cy = frameH.value / 2
        const ratio = z / lastZoom
        offset.value = clamp(cx - (cx - offset.value.x) * ratio, cy - (cy - offset.value.y) * ratio)
    }
    lastZoom = z
})
watch([aspect, frameW, frameH], () => reset())
watch(() => props.src, () => {
    natural.value = {w: 0, h: 0}
})

// ---- drag to move, two fingers to zoom
const pointers = new Map<number, { x: number, y: number }>()
let pinchStart = 0
let pinchZoom = 1

function distance() {
    const [a, b] = Array.from(pointers.values())
    return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0
}

function down(e: PointerEvent) {
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    pointers.set(e.pointerId, {x: e.clientX, y: e.clientY})
    if (pointers.size == 2) {
        pinchStart = distance()
        pinchZoom = zoom.value
    }
}

function move(e: PointerEvent) {
    const last = pointers.get(e.pointerId)
    if (!last) return
    pointers.set(e.pointerId, {x: e.clientX, y: e.clientY})
    if (pointers.size == 1) {
        offset.value = clamp(offset.value.x + e.clientX - last.x, offset.value.y + e.clientY - last.y)
    } else if (pointers.size == 2 && pinchStart > 0) {
        setZoom(pinchZoom * distance() / pinchStart)
    }
}

function up(e: PointerEvent) {
    pointers.delete(e.pointerId)
    pinchStart = 0
}

function wheel(e: WheelEvent) {
    setZoom(zoom.value * (e.deltaY < 0 ? 1.1 : 1 / 1.1))
}

function apply() {
    if (!ready.value) return
    const w = Math.min(1, frameW.value / shown.value.w), h = Math.min(1, frameH.value / shown.value.h)
    const x = Math.min(1 - w, Math.max(0, -offset.value.x / shown.value.w))
    const y = Math.min(1 - h, Math.max(0, -offset.value.y / shown.value.h))
    emit('apply', {x, y, w, h}, aspect.value)
    open.value = false
}
</script>

<style scoped>
.fork-crop__frame {
    position: relative;
    width: 100%;
    overflow: hidden;
    border-radius: var(--fork-radius-card);
    background: rgb(var(--v-theme-surface-variant));
    touch-action: none;
    cursor: grab;
    user-select: none;
}

.fork-crop__img {
    position: absolute;
    top: 0;
    left: 0;
    max-width: none;
    pointer-events: none;
}

/* rule of thirds */
.fork-crop__grid {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: linear-gradient(to right, transparent calc(33.33% - 0.5px), rgba(255, 255, 255, 0.6) 33.33%, transparent calc(33.33% + 0.5px),
    transparent calc(66.66% - 0.5px), rgba(255, 255, 255, 0.6) 66.66%, transparent calc(66.66% + 0.5px)),
    linear-gradient(to bottom, transparent calc(33.33% - 0.5px), rgba(255, 255, 255, 0.6) 33.33%, transparent calc(33.33% + 0.5px),
        transparent calc(66.66% - 0.5px), rgba(255, 255, 255, 0.6) 66.66%, transparent calc(66.66% + 0.5px));
    box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.8);
}

.fork-crop__controls {
    display: flex;
    align-items: center;
    gap: var(--fork-space-3);
    margin-top: var(--fork-space-3);
    min-height: 44px;
}

.fork-crop__shapes :deep(.v-btn) {
    min-width: 64px;
}
</style>
