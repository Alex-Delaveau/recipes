<template>
    <!-- Quick edit of a food in a bottom sheet, without leaving the page (name, plural, family, aisle, never in shopping) -->
    <v-bottom-sheet v-model="sheet" max-width="640" scrollable>
        <v-card class="fork-food-sheet">
            <v-card-title class="d-flex align-center pt-4">
                <span class="flex-grow-1 text-truncate">{{ food ? food.name : $t('Fork_New_Food') }}</span>
                <v-btn icon="$close" variant="text" :aria-label="$t('Close')" @click="sheet = false"></v-btn>
            </v-card-title>
            <v-card-text>
                <v-text-field v-model="form.name" :label="$t('Name')" variant="outlined" autocomplete="off" class="mb-2"
                              :rules="[v => !!v?.trim() || $t('Fork_Required')]"></v-text-field>
                <v-text-field v-model="form.pluralName" :label="$t('Plural')" variant="outlined" autocomplete="off" class="mb-2"
                              :placeholder="$t('Fork_Plural_Hint')"></v-text-field>
                <v-switch v-model="form.isFamily" :label="$t('Fork_Is_Family')" color="primary" hide-details class="mb-2"
                          v-if="!food || (food.depth == 1 && food.numchild == 0)"></v-switch>
                <v-select v-model="form.family" :items="familyItems" item-title="name" item-value="id" :label="$t('Fork_Family')"
                          variant="outlined" class="mb-2" v-if="!form.isFamily"></v-select>

                <div class="fork-food-sheet__label">{{ $t('Fork_Aisle') }}</div>
                <v-chip-group v-model="form.category" column selected-class="text-primary" class="mb-2">
                    <v-chip v-for="a in aisles" :key="a.id" :value="a.id" filter variant="outlined">{{ a.name }}</v-chip>
                </v-chip-group>
                <p class="text-caption text-medium-emphasis mb-2" v-if="form.family && familyAisle">
                    {{ $t('Fork_Aisle_Inherited', {aisle: familyAisle}) }}
                </p>

                <v-switch v-model="form.ignoreShopping" :label="$t('Fork_Never_In_Shopping')" color="primary" hide-details></v-switch>
            </v-card-text>
            <v-card-actions class="pa-4 ga-2">
                <v-btn variant="text" size="large" :to="{name: 'ModelEditPage', params: {model: 'Food', id: food.id}}" v-if="food">
                    {{ $t('Fork_All_Fields') }}
                </v-btn>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="flat" size="large" :loading="saving" :disabled="!form.name?.trim()" @click="save()">{{ $t('Save') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
import {computed, PropType, reactive, ref, watch} from "vue";
import {useI18n} from "vue-i18n";
import {ApiApi, Food} from "@/openapi";
import {ErrorMessageType, PreparedMessage, useMessageStore} from "@/stores/MessageStore";
import {KitchenAisle, KitchenFoodItem, moveFoodToFamily, setFoodAisle, setFoodFamily} from "@/fork/api";

const props = defineProps({
    /** food to edit, null to create one */
    food: {type: Object as PropType<KitchenFoodItem | null>, default: null},
    families: {type: Array as PropType<KitchenFoodItem[]>, required: true},
    aisles: {type: Array as PropType<KitchenAisle[]>, required: true},
})
const emit = defineEmits(['saved'])

const sheet = defineModel<boolean>({default: false})
const {t} = useI18n()
const saving = ref(false)

const form = reactive({
    name: '',
    pluralName: '' as string | null,
    family: null as number | null,
    category: null as number | null,
    ignoreShopping: false,
    isFamily: false,
})

const familyItems = computed(() => [{id: null, name: t('Fork_No_Family')},
    ...props.families.filter(f => f.id != props.food?.id).map(f => ({id: f.id, name: f.name}))])
const familyAisle = computed(() => props.families.find(f => f.id == form.family)?.category?.name)

watch(sheet, (open) => {
    if (!open) return
    form.name = props.food?.name ?? ''
    form.pluralName = props.food?.pluralName ?? ''
    form.family = props.food?.family ?? null
    form.category = props.food?.category?.id ?? null
    form.ignoreShopping = props.food?.ignoreShopping ?? false
    form.isFamily = props.food?.isFamily ?? false
})

// choosing a family proposes its aisle (members inherit it by default)
watch(() => form.family, (family, previous) => {
    if (family != previous && family != null && family != (props.food?.family ?? null)) {
        const aisle = props.families.find(f => f.id == family)?.category
        if (aisle) form.category = aisle.id
    }
})

async function save() {
    const api = new ApiApi()
    saving.value = true
    try {
        const fields = {name: form.name.trim(), pluralName: form.pluralName?.trim() || null, ignoreShopping: form.ignoreShopping}
        let id = props.food?.id
        if (id == undefined) {
            id = (await api.apiFoodCreate({food: fields as Food})).id!
        } else {
            await api.apiFoodPartialUpdate({id, patchedFood: fields})
        }
        if (form.isFamily != (props.food?.isFamily ?? false)) {
            await setFoodFamily(id, form.isFamily)
        }
        const family = form.isFamily ? null : form.family
        if (family != (props.food?.family ?? null)) {
            await moveFoodToFamily(id, family)
        }
        // saving confirms the aisle: the user saw it
        if (form.category != (props.food?.category?.id ?? null) || (form.category != null && !props.food?.aisleConfirmed)) {
            await setFoodAisle(id, form.category)
        }
        useMessageStore().addPreparedMessage(PreparedMessage.UPDATE_SUCCESS)
        sheet.value = false
        emit('saved', id)
    } catch (err) {
        useMessageStore().addError(ErrorMessageType.UPDATE_ERROR, err)
    } finally {
        saving.value = false
    }
}
</script>

<style scoped>
.fork-food-sheet__label {
    font-size: var(--fork-text-md);
    font-weight: 600;
    margin: var(--fork-space-2) 0;
}

.fork-food-sheet :deep(.v-chip) {
    min-height: var(--fork-tap);
}
</style>
