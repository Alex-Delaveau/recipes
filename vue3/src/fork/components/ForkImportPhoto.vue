<template>
    <!-- Photo of an import: shown as it will be kept, with "crop"; the crop is applied by the server at save time -->
    <div class="fork-import-photo">
        <v-img v-if="!crop" :src="src" max-height="30vh"></v-img>
        <div v-else class="fork-import-crop" role="img" :aria-label="$t('Fork_Crop_Done')"
             :style="{aspectRatio: String(aspect), ...cropPreviewStyle(src, crop)}"></div>
        <v-btn class="mt-2" variant="tonal" prepend-icon="fa-solid fa-crop-simple" @click="open = true">
            {{ crop ? $t('Fork_Crop_Again') : $t('Fork_Crop') }}
        </v-btn>
        <fork-image-cropper v-model="open" :src="src" @apply="(c: ImageCrop, a: number) => { crop = c; aspect = a }"></fork-image-cropper>
    </div>
</template>

<script setup lang="ts">
import {ref} from "vue";
import ForkImageCropper from "@/fork/components/ForkImageCropper.vue";
import {cropPreviewStyle, ImageCrop} from "@/fork/images";

defineProps({
    src: {type: String, required: true},
})
const crop = defineModel<ImageCrop | null>('crop', {default: null})
const aspect = defineModel<number>('aspect', {default: 16 / 9})
const open = ref(false)
</script>

<style scoped>
.fork-import-crop {
    width: 100%;
    border-radius: 8px;
}
</style>
