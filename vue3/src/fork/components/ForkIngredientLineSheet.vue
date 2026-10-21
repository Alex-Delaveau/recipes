<template>
    <!-- Correction of one recognised ingredient line, in a bottom sheet -->
    <v-bottom-sheet v-model="sheet" max-width="640" scrollable>
        <v-card class="fork-line-sheet">
            <v-card-title class="d-flex align-center pt-4">
                <span class="flex-grow-1">{{ $t('Fork_Edit_Ingredient') }}</span>
                <v-btn icon="$close" variant="text" :aria-label="$t('Close')" @click="sheet = false"></v-btn>
            </v-card-title>
            <v-card-text>
                <p class="text-body-2 text-medium-emphasis mb-3" v-if="form.original">« {{ form.original }} »</p>
                <div class="d-flex ga-2">
                    <v-text-field v-model="form.amount" :label="$t('Amount')" variant="outlined" inputmode="decimal" class="fork-line-sheet__amount"
                                  autocomplete="off"></v-text-field>
                    <v-text-field v-model="form.unit" :label="$t('Unit')" variant="outlined" autocomplete="off" clearable></v-text-field>
                </div>
                <v-text-field v-model="form.food" :label="$t('Food')" variant="outlined" autocomplete="off"
                              :rules="[v => !!v?.trim() || $t('Fork_Required')]"></v-text-field>
                <v-text-field v-model="form.note" :label="$t('Note')" variant="outlined" autocomplete="off" :placeholder="$t('Fork_Note_Hint')"></v-text-field>
            </v-card-text>
            <v-card-actions class="pa-4 ga-2">
                <v-btn variant="text" color="error" size="large" prepend-icon="$delete" @click="remove()">{{ $t('Delete') }}</v-btn>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="flat" size="large" :disabled="!form.food.trim()" @click="save()">{{ $t('Fork_Apply') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
import {PropType, reactive, watch} from "vue";
import {DraftIngredient} from "@/fork/recipeDraft";

const props = defineProps({
    ingredient: {type: Object as PropType<DraftIngredient | null>, default: null},
})
const emit = defineEmits<{ save: [value: DraftIngredient], remove: [value: DraftIngredient] }>()
const sheet = defineModel<boolean>({default: false})

const form = reactive({amount: '', unit: '' as string | null, food: '', note: '', original: ''})

watch(sheet, (open) => {
    if (!open || !props.ingredient) return
    form.amount = props.ingredient.amount ? String(props.ingredient.amount).replace('.', ',') : ''
    form.unit = props.ingredient.unit ?? ''
    form.food = props.ingredient.food
    form.note = props.ingredient.note
    form.original = props.ingredient.original
})

/** "1,5", "1/2", "1 1/2", "½", "1½", "1 ½" */
function parseAmount(text: string) {
    const clean = text.trim().replace(',', '.')
    const vulgar: Record<string, number> = {'¼': 0.25, '½': 0.5, '¾': 0.75, '⅓': 1 / 3, '⅔': 2 / 3}
    let m = clean.match(/^(?:(\d+)\s+)?(\d+)\/(\d+)$/)
    if (m) return (m[1] ? Number(m[1]) : 0) + (Number(m[3]) ? Number(m[2]) / Number(m[3]) : 0)
    m = clean.match(/^(\d+(?:\.\d+)?)?\s*([¼½¾⅓⅔])?$/)
    if (!m || clean == '') return NaN
    return (m[1] ? parseFloat(m[1]) : 0) + (m[2] ? vulgar[m[2]] ?? 0 : 0)
}

function save() {
    if (!props.ingredient) return
    const amount = parseAmount(String(form.amount))
    const food = form.food.trim()
    emit('save', {
        ...props.ingredient,
        amount: isNaN(amount) ? 0 : amount,
        unit: form.unit?.trim() || null,
        food: food,
        note: form.note.trim(),
        known: food == props.ingredient.food ? props.ingredient.known : null,
    })
    sheet.value = false
}

function remove() {
    if (props.ingredient) emit('remove', props.ingredient)
    sheet.value = false
}
</script>

<style scoped>
.fork-line-sheet__amount {
    flex: 0 0 35%;
}
</style>
