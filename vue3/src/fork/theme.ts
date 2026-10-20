// Fork design tokens (docs/fork/DESIGN.md) turned into Vuetify themes and component defaults.
import type {ThemeDefinition} from 'vuetify'

export const LIGHT_THEME = 'light'
export const DARK_THEME = 'dark'

/**
 * Values of the upstream UserPreference.theme field, reused by the fork without a migration:
 * TANDOOR (upstream default) follows the system, TANDOOR_DARK forces dark, FLATLY (legacy, unused by vue3) forces light.
 */
export const THEME_SYSTEM = 'TANDOOR'
export const THEME_DARK = 'TANDOOR_DARK'
export const THEME_LIGHT = 'FLATLY'

const light: ThemeDefinition = {
    dark: false,
    colors: {
        background: '#FAF8F5',
        surface: '#FAF8F5',
        'surface-bright': '#FFFFFF',
        'surface-light': '#F1EDE6',
        'surface-variant': '#F1EDE6',
        'on-surface-variant': '#1F1D1A',
        'on-background': '#1F1D1A',
        'on-surface': '#1F1D1A',
        // DESIGN.md starts at #C2552D; darkened so primary text reaches 4.5:1 on surface-variant
        primary: '#AF4A26',
        'on-primary': '#FFFFFF',
        secondary: '#3E6B5A',
        'on-secondary': '#FFFFFF',
        error: '#B3261E',
        'on-error': '#FFFFFF',
        success: '#3E6B5A',
        info: '#3E6B5A',
        warning: '#8A5A00',
        // upstream semantic colors, mapped onto the tokens
        tandoor: '#F1EDE6',
        save: '#AF4A26',
        create: '#AF4A26',
        edit: '#3E6B5A',
        delete: '#B3261E',
        cancel: '#5C5750',
        recipeImagePlaceholderBg: '#F1EDE6',
    },
    variables: {
        'border-color': '#1F1D1A',
        'border-opacity': 0.14,
        'medium-emphasis-opacity': 0.72,
        'high-emphasis-opacity': 0.95,
    },
}

const dark: ThemeDefinition = {
    dark: true,
    colors: {
        background: '#0B1020',
        surface: '#0B1020',
        'surface-bright': '#1C2340',
        'surface-light': '#141A2E',
        'surface-variant': '#141A2E',
        'on-surface-variant': '#E6E8F0',
        'on-background': '#E6E8F0',
        'on-surface': '#E6E8F0',
        primary: '#8FB3FF',
        'on-primary': '#0B1020',
        secondary: '#B9A6FF',
        'on-secondary': '#0B1020',
        error: '#FF8A80',
        'on-error': '#0B1020',
        success: '#B9A6FF',
        info: '#B9A6FF',
        warning: '#FFD180',
        tandoor: '#141A2E',
        save: '#8FB3FF',
        create: '#8FB3FF',
        edit: '#B9A6FF',
        delete: '#FF8A80',
        cancel: '#A9AEC2',
        recipeImagePlaceholderBg: '#141A2E',
    },
    variables: {
        'border-color': '#E6E8F0',
        'border-opacity': 0.16,
        'medium-emphasis-opacity': 0.75,
        'high-emphasis-opacity': 0.92,
    },
}

export const forkThemes = {[LIGHT_THEME]: light, [DARK_THEME]: dark}

/** Component defaults: flat surfaces with thin outlines, token radii, 44 px tap targets. */
export const forkDefaults = {
    VCard: {rounded: 'lg', elevation: 0, border: true},
    VSheet: {elevation: 0},
    VChip: {rounded: 'pill'},
    VBtn: {rounded: 'lg', elevation: 0},
    VAppBar: {elevation: 0},
    VNavigationDrawer: {elevation: 0},
    VBottomNavigation: {elevation: 0},
}

function systemPrefersDark(): boolean {
    return typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** Vuetify theme to show for a stored user preference (null/undefined before settings are loaded = system). */
export function resolveThemeName(preference: string | undefined | null, printMode = false): string {
    if (printMode || preference === THEME_LIGHT) return LIGHT_THEME
    if (preference === THEME_DARK) return DARK_THEME
    return systemPrefersDark() ? DARK_THEME : LIGHT_THEME
}

let systemListener = false

/** Calls `onChange` whenever the system color scheme changes (registered once). */
export function watchSystemTheme(onChange: () => void) {
    if (systemListener || typeof window === 'undefined' || !window.matchMedia) return
    systemListener = true
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', onChange)
}

/** Upstream default header color (sand, outside the tokens): the fork shows the surface token instead. */
const UPSTREAM_NAV_COLORS = ['#ddbf86', 'tandoor']

/** Header color: a color explicitly chosen by the user or space is kept, the upstream default becomes the surface. */
export function forkNavColor(color: string | undefined | null): string {
    if (!color || UPSTREAM_NAV_COLORS.includes(color.toLowerCase())) return 'surface'
    return color
}
