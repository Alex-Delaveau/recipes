<template>
    <!-- Recipe photo, or a tinted tile with the initial when there is none (two missing photos stay told apart) -->
    <div class="fork-thumb" :style="{width: px, height: px, borderRadius: radius, background: image ? undefined : tint.bg}">
        <v-img v-if="image" :src="image" cover :alt="''" class="fork-thumb__img"></v-img>
        <span v-else class="fork-thumb__initial" :style="{color: tint.fg, fontSize: initialSize}" aria-hidden="true">{{ initial }}</span>
    </div>
</template>

<script setup lang="ts">
import {computed} from "vue";

const props = defineProps({
    name: {type: String, required: true},
    image: {type: String as () => string | null | undefined, default: null},
    size: {type: Number, default: 52},
})

// muted warm tiles, each with a text color that reaches 4.5:1
const TINTS = [
    {bg: '#F3E1D3', fg: '#7A3B1C'}, {bg: '#E4EDDF', fg: '#2F5A40'}, {bg: '#F4E9C8', fg: '#6B4E00'},
    {bg: '#E7E0F0', fg: '#4B3A6E'}, {bg: '#DCEAEE', fg: '#22525E'}, {bg: '#F2DCDC', fg: '#7A2E2E'},
]

const px = computed(() => `${props.size}px`)
const radius = computed(() => `${Math.round(props.size / 5)}px`)
const initialSize = computed(() => `${Math.round(props.size * 0.42)}px`)
const initial = computed(() => (props.name.trim()[0] ?? '?').toUpperCase())
const tint = computed(() => {
    let h = 0
    for (const c of props.name) h = (h * 31 + c.charCodeAt(0)) >>> 0
    return TINTS[h % TINTS.length]!
})
</script>

<style scoped>
.fork-thumb {
    flex: none;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}

.fork-thumb__img {
    width: 100%;
    height: 100%;
}

.fork-thumb__initial {
    font-weight: 700;
    line-height: 1;
}
</style>
