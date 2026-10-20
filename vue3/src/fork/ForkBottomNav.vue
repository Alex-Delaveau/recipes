<template>
    <!-- Mobile navigation (DESIGN.md): 4 labeled entries, the page reserves its height through the Vuetify layout -->
    <v-bottom-navigation grow :height="64" class="fork-bottom-nav d-print-none" color="primary">
        <v-btn :to="{name: 'StartPage', params: {}}" exact>
            <v-icon icon="$recipes"></v-icon>
            <span>{{ $t('Recipes') }}</span>
        </v-btn>

        <v-btn :to="{name: 'ShoppingListPage', params: {}}">
            <v-icon icon="$shopping"></v-icon>
            <span>{{ $t('Shopping') }}</span>
        </v-btn>

        <v-btn @click="addSheet = true">
            <v-icon icon="fa-solid fa-circle-plus"></v-icon>
            <span>{{ $t('Add') }}</span>
        </v-btn>

        <v-btn @click="moreSheet = true">
            <v-icon icon="fa-solid fa-bars"></v-icon>
            <span>{{ $t('More') }}</span>
        </v-btn>
    </v-bottom-navigation>

    <v-bottom-sheet v-model="addSheet" close-on-content-click>
        <v-card :title="$t('Fork_Add_Recipe')" :border="false">
            <v-list nav class="pb-4">
                <v-list-item prepend-icon="fa-solid fa-globe" :title="$t('Fork_Add_From_Url')" min-height="56"
                             :to="{name: 'RecipeImportPage', params: {}}"></v-list-item>
                <v-list-item prepend-icon="fa-solid fa-pen" :title="$t('Fork_Add_Manual')" min-height="56"
                             :to="{name: 'ModelEditPage', params: {model: 'recipe'}}"></v-list-item>
            </v-list>
        </v-card>
    </v-bottom-sheet>

    <v-bottom-sheet v-model="moreSheet" close-on-content-click>
        <v-card :border="false">
            <v-list nav class="pb-4">
                <menu-user-info></menu-user-info>
                <v-divider class="mb-2"></v-divider>
                <component :is="item.component" :="item" :key="item.title" v-for="item in useNavigation().getBottomNavigation()"
                           min-height="48"></component>
            </v-list>
        </v-card>
    </v-bottom-sheet>
</template>

<script setup lang="ts">
import {ref} from "vue";
import {useNavigation} from "@/composables/useNavigation.ts";
import MenuUserInfo from "@/components/display/MenuUserInfo.vue";

const addSheet = ref(false)
const moreSheet = ref(false)
</script>

<style scoped>
.fork-bottom-nav {
    border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    padding-bottom: env(safe-area-inset-bottom);
}

.fork-bottom-nav :deep(.v-btn) {
    min-width: 64px;
}

.fork-bottom-nav :deep(.v-btn__content) {
    gap: var(--fork-space-1);
    font-size: var(--fork-text-xs);
}

.fork-bottom-nav :deep(.v-btn .v-icon) {
    font-size: 20px;
}
</style>
