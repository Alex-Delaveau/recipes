<template>
    <!-- Servings stepper: two 44 px buttons around the value -->
    <div class="fork-stepper" role="group" :aria-label="label">
        <v-btn icon variant="tonal" size="44" :disabled="model <= 1" :aria-label="$t('Fork_Servings_Less')" @click="model = Math.max(1, model - 1)">
            <v-icon icon="fa-solid fa-minus"></v-icon>
        </v-btn>
        <div class="fork-stepper__value" aria-live="polite">
            <span class="fork-stepper__number">{{ model }}</span>
            <span class="fork-stepper__label">{{ label }}</span>
        </div>
        <v-btn icon variant="tonal" size="44" :aria-label="$t('Fork_Servings_More')" @click="model = model + 1">
            <v-icon icon="fa-solid fa-plus"></v-icon>
        </v-btn>
    </div>
</template>

<script setup lang="ts">
defineProps({
    label: {type: String, default: ''},
})

const model = defineModel<number>({required: true})
</script>

<style scoped>
.fork-stepper {
    display: flex;
    align-items: center;
    gap: var(--fork-space-3);
}

.fork-stepper__value {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 64px;
    line-height: 1.2;
}

.fork-stepper__number {
    font-size: var(--fork-text-lg);
    font-weight: 600;
}

.fork-stepper__label {
    font-size: var(--fork-text-xs);
    color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
