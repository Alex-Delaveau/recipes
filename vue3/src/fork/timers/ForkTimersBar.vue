<template>
    <!-- Running timers, compact; follows the user from page to page (shell) and sits above the cook mode buttons -->
    <section v-if="store.timers.length" class="fork-timers" :class="{'fork-timers--floating': !inline}" :aria-label="$t('Fork_Timers')">
        <div v-for="timer in store.timers" :key="timer.id" class="fork-timers__row" :class="{'fork-timers__row--done': timer.done}"
             role="timer" :aria-live="timer.done ? 'assertive' : 'off'">
            <v-icon :icon="timer.done ? 'fa-solid fa-bell' : 'fa-solid fa-stopwatch'" size="18" class="fork-timers__icon"></v-icon>
            <div class="fork-timers__text">
                <div class="fork-timers__time">{{ timer.done ? $t('Fork_Timer_Done') : formatCountdown(store.remainingMs(timer)) }}</div>
                <div class="fork-timers__label">{{ timer.label }}</div>
            </div>
            <v-btn v-if="!timer.done" icon variant="text" size="44" :aria-label="timer.endAt === null ? $t('Fork_Timer_Resume') : $t('Fork_Timer_Pause')"
                   @click="timer.endAt === null ? store.resume(timer.id) : store.pause(timer.id)">
                <v-icon :icon="timer.endAt === null ? 'fa-solid fa-play' : 'fa-solid fa-pause'" size="18"></v-icon>
            </v-btn>
            <v-btn variant="text" size="small" class="fork-timers__plus" :aria-label="$t('Fork_Timer_Add_Minute')" @click="store.addMinute(timer.id)">+1 min</v-btn>
            <v-btn icon variant="text" size="44" :aria-label="$t('Fork_Timer_Stop')" @click="store.stop(timer.id)">
                <v-icon icon="fa-solid fa-xmark" size="20"></v-icon>
            </v-btn>
        </div>
    </section>
</template>

<script setup lang="ts">
import {useForkTimers} from "@/fork/timers/timers";
import {formatCountdown} from "@/fork/timers/detect";

defineProps({
    /** in the page flow (cook mode footer) instead of sticking above the bottom bar */
    inline: {type: Boolean, default: false},
})

const store = useForkTimers()
</script>

<style scoped>
.fork-timers {
    display: flex;
    flex-direction: column;
    gap: var(--fork-space-1);
    max-height: 168px;
    overflow-y: auto;
}

/* last element of v-main: sticks above the bottom bar while scrolling and takes its own room at the end of the page */
.fork-timers--floating {
    position: sticky;
    bottom: var(--v-layout-bottom, 0px);
    z-index: 5;
    margin: var(--fork-space-2) auto 0;
    max-width: 760px;
    padding: var(--fork-space-2) var(--fork-space-4) var(--fork-space-2);
    background: rgb(var(--v-theme-background));
    border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.fork-timers__row {
    display: flex;
    align-items: center;
    gap: var(--fork-space-1);
    min-height: 48px;
    padding: 0 var(--fork-space-1) 0 var(--fork-space-3);
    border-radius: var(--fork-radius-card);
    background: rgb(var(--v-theme-surface-variant));
}

.fork-timers__row--done {
    background: rgb(var(--v-theme-primary));
    color: rgb(var(--v-theme-on-primary));
}

.fork-timers__icon {
    flex: 0 0 auto;
}

.fork-timers__text {
    flex: 1 1 auto;
    min-width: 0;
    padding-left: var(--fork-space-2);
}

.fork-timers__time {
    font-size: var(--fork-text-lg);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    line-height: 24px;
}

.fork-timers__label {
    font-size: var(--fork-text-sm);
    line-height: 18px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    opacity: var(--v-medium-emphasis-opacity);
}

.fork-timers__row--done .fork-timers__label {
    opacity: 1;
}

.fork-timers .v-btn {
    flex: 0 0 auto;
}

.fork-timers__plus {
    min-width: 56px !important;
    height: 44px !important;
    font-weight: 600;
}
</style>
