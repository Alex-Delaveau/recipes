#!/usr/bin/env node
// Functional journey checks for the fork (headless, phone viewport): they click through the screens like a user and
// assert what the acceptance criteria promise. Every flow restores the data it changed.
//
// Usage (dev server running, see scripts/fork/serve.sh):
//   node scripts/fork/ui/flows.mjs [--base http://127.0.0.1:8000] [--only p1,p2]
// Exit code 1 if a check fails. Run by `verify.sh --ui` after the screenshots.

import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium as pw } from 'playwright-core'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, '../../..')

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`)
  if (i === -1) return fallback
  const v = process.argv[i + 1]
  return v && !v.startsWith('--') ? v : true
}

const base = String(arg('base', process.env.FORK_BASE_URL || 'http://127.0.0.1:8000')).replace(/\/$/, '')
const only = arg('only') ? String(arg('only')).split(',') : null

async function resolveBrowser() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) return { executablePath: process.env.CHROME_PATH, args: [] }
  try {
    const p = pw.executablePath()
    if (p && existsSync(p)) return { executablePath: p, args: [] }
  } catch { /* no Playwright-managed browser */ }
  const { default: sparticuz } = await import('@sparticuz/chromium')
  return { executablePath: await sparticuz.executablePath(), args: sparticuz.args.filter((a) => a !== '--single-process') }
}

function sessionId() {
  const python = existsSync(join(ROOT, '.venv/bin/python')) ? join(ROOT, '.venv/bin/python') : 'python3'
  return execFileSync(python, [join(ROOT, 'scripts/fork/dev_session.py')], {
    cwd: ROOT, env: { ...process.env, DJANGO_SETTINGS_MODULE: 'recipes.settings', DEBUG: '1' }, stdio: ['ignore', 'pipe', 'ignore'],
  }).toString().trim().split('\n').pop()
}

// ---- tiny assertion helpers ----
const results = []
let current = null

function check(ok, what) {
  current.checks.push({ ok: Boolean(ok), what })
  if (!ok) console.log(`    [FAIL] ${what}`)
  else console.log(`    [ok]   ${what}`)
}

async function eventually(fn, timeout = 8000) {
  const end = Date.now() + timeout
  let last
  while (Date.now() < end) {
    try {
      last = await fn()
      if (last) return last
    } catch { /* retry */ }
    await new Promise((r) => setTimeout(r, 200))
  }
  return last
}

/** JSON API call from inside the page (session + CSRF cookie of the logged-in user) */
async function api(page, method, path, body) {
  return page.evaluate(async ({ method, path, body }) => {
    const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || ''
    const r = await fetch(path, { method, headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf }, body: body ? JSON.stringify(body) : undefined })
    return { status: r.status, data: r.status === 204 ? null : await r.json().catch(() => null) }
  }, { method, path, body })
}

const texts = (page, selector) => page.locator(selector).allInnerTexts()

// screens that only a click-through reaches (wizard screens 2-4...): published with the route captures
const SHOTS = join(ROOT, '.fork/screens/flows')
async function shot(page, name, scheme = 'light') {
  mkdirSync(SHOTS, { recursive: true })
  if (scheme === 'dark') await page.emulateMedia({ colorScheme: 'dark' })
  await page.waitForTimeout(400)
  const suffix = scheme === 'dark' ? 'dark' : 'mobile'
  await page.screenshot({ path: join(SHOTS, `${name}-${suffix}-screen.jpg`), type: 'jpeg', quality: 80 }).catch(() => {})
  if (scheme === 'dark') { await page.emulateMedia({ colorScheme: 'light' }); await page.waitForTimeout(200) }
}

// ---- flows ----
const FLOWS = {
  // P1: recipes home with search, filter sheet and shortcuts
  async p1(page) {
    await page.goto(base + '/', { waitUntil: 'networkidle' })
    check(await page.getByPlaceholder('Rechercher une recette').isVisible(), 'search field visible on the home screen')
    const all = await eventually(async () => (await texts(page, '.fork-recipe-row__title')).length >= 4 && texts(page, '.fork-recipe-row__title'))
    check(all && all.length >= 4, `photo cards listed (${all?.length})`)

    await page.getByPlaceholder('Rechercher une recette').fill('curry')
    const found = await eventually(async () => { const t = await texts(page, '.fork-recipe-row__title'); return t.length === 1 && t })
    check(found && found[0].includes('Curry'), 'text search narrows the list')
    await page.getByPlaceholder('Rechercher une recette').fill('')

    await page.getByRole('button', { name: 'Filtres' }).click()
    await page.locator('.v-bottom-sheet .v-chip', { hasText: '≤ 30 min' }).click()
    const quick = await eventually(async () => { const t = await texts(page, '.fork-recipe-row__title'); return t.length === 3 && t })
    check(quick && !quick.some((t) => t.includes('Curry')), 'total time ≤ 30 min drops the 35 min curry')
    await page.locator('.v-bottom-sheet .v-chip', { hasText: '≤ 30 min' }).click() // off again

    await page.locator('.v-bottom-sheet .v-autocomplete input').first().fill('Courg')
    await page.locator('.v-overlay .v-list-item', { hasText: 'Courgette' }).first().click()
    await page.keyboard.press('Escape')
    const ranked = await eventually(async () => { const t = await texts(page, '.fork-recipe-row__title'); return t.length === 1 && t })
    check(ranked && ranked[0].includes('Poêlée'), 'ingredient on hand lists the recipes using it')
    check(await page.locator('.fork-recipe-row', { hasText: '1/4 ingrédients' }).count() === 1, 'card shows how many ingredients are on hand')
    await page.goto(base + '/', { waitUntil: 'networkidle' }) // module state survives SPA navigation only

    await page.locator('.fork-home__shortcuts .v-chip', { hasText: 'Pas faites depuis longtemps' }).click()
    const forgotten = await eventually(async () => { const t = await texts(page, '.fork-recipe-row__title'); return t.length >= 4 && t })
    check(forgotten && forgotten.length >= 4, 'shortcut "pas faites depuis longtemps" lists recipes')
    await page.locator('.fork-home__shortcuts .v-chip', { hasText: 'Récentes' }).click()
    await page.waitForTimeout(800)
    check(!(await page.locator('.v-alert--variant-tonal.text-error').count()), 'shortcut "récentes" loads without error')
    const recent = page.locator('.fork-home__shortcuts .v-chip', { hasText: 'Récentes' })
    check((await recent.getAttribute('aria-pressed')) === 'true' && !(await recent.locator('.v-chip__filter').count()), 'selected shortcut: one icon, no extra check mark')
    await recent.click()
    check(await eventually(async () => (await recent.getAttribute('aria-pressed')) === 'false', 3000), 'tapping it again switches it off')
  },

  // every recipe: a preview on the home, "see all" opens a grid grouped by letter, a letter bar, a list view, a search
  async allrecipes(page) {
    await page.goto(base + '/', { waitUntil: 'networkidle' })
    const total = (await api(page, 'GET', '/api/kitchen/recipes/?page_size=1')).data.count
    check(await eventually(async () => (await page.locator('.fork-home__list .fork-recipe-row').count()) === Math.min(total, 6), 5000), `home shows a preview of every recipe (${Math.min(total, 6)})`)
    await page.locator('.fork-home__all').getByRole('link', { name: 'Tout voir' }).click()
    await page.waitForURL('**/recipes/all')
    await page.evaluate(() => localStorage.removeItem('fork_all_recipes_view'))
    await page.reload({ waitUntil: 'networkidle' })
    const cards = page.locator('.fork-all__card')
    check(await eventually(async () => (await cards.count()) === total, 5000), `all ${total} recipes, as a grid by default`)
    const letters = await texts(page, '.fork-all__group-letter')
    check(letters.length >= 2 && letters.join('') === [...letters].sort().join(''), `grouped by letter, in order (${letters.join(' ')})`)
    await shot(page, 'recipes-all')
    const last = letters[letters.length - 1]
    await page.locator('.fork-all__letter', { hasText: new RegExp(`^${last}$`) }).click()
    check(await eventually(async () => page.evaluate((l) => { const r = document.getElementById('fork-letter-' + l).getBoundingClientRect(); return r.top >= 0 && r.top < 260 }, last), 3000), `the letter bar jumps to "${last}"`)
    await page.getByRole('button', { name: 'Afficher en liste' }).click()
    check(await eventually(async () => (await page.locator('.fork-all__list .fork-recipe-row').count()) === total, 3000), 'list view')
    await page.reload({ waitUntil: 'networkidle' })
    check(await eventually(async () => (await page.locator('.fork-all__list .fork-recipe-row').count()) === total, 5000), 'the chosen view stays after a reload')
    await page.getByPlaceholder('Rechercher une recette').fill('carbo')
    check(await eventually(async () => (await page.locator('.fork-recipe-row').count()) === 1, 3000), 'search narrows the list')
    await page.evaluate(() => localStorage.removeItem('fork_all_recipes_view'))
  },

  // home "this week" card: the drawn dishes first, folds to one line (kept on the device), replace / remove / undo
  async week(page) {
    await page.goto(base + '/', { waitUntil: 'networkidle' })
    await page.evaluate(() => { localStorage.removeItem('fork_recipe_draw'); localStorage.setItem('fork_recipe_draw_size', '3'); localStorage.removeItem('fork_week_open') })
    await page.reload({ waitUntil: 'networkidle' })
    const card = page.locator('.fork-week')
    check(await eventually(() => card.getByRole('button', { name: 'Tirer 3 recettes' }).isVisible(), 5000), 'empty week: one button draws the dishes')
    await card.getByRole('button', { name: 'Tirer 3 recettes' }).click()
    const rows = card.locator('.fork-week__row')
    check(await eventually(async () => (await rows.count()) === 3, 5000), '3 dishes drawn on the home')
    check(await page.locator('.fork-shelf').count() >= 1 && (await page.locator('.fork-recipe-row').count()) >= 4, 'then the shelves and every recipe, one per line')
    await shot(page, 'home-week')
    const toggle = card.locator('.fork-week__toggle')
    await toggle.click()
    check(await eventually(async () => (await toggle.getAttribute('aria-expanded')) === 'false' && !(await rows.count()), 3000), 'folds to one line')
    check((await card.locator('.fork-week__strip .fork-thumb').count()) === 3, 'folded: the dishes stay visible as thumbnails')
    await shot(page, 'home-week-folded')
    await page.reload({ waitUntil: 'networkidle' })
    check(await eventually(async () => (await card.locator('.fork-week__toggle').getAttribute('aria-expanded')) === 'false', 4000), 'stays folded after a reload')
    await card.locator('.fork-week__toggle').click()
    await eventually(async () => (await rows.count()) === 3, 3000)
    const names = async () => texts(page, '.fork-week__recipe')
    const before = await names()
    await rows.first().getByRole('button', { name: /Retirer/ }).click()
    check(await eventually(async () => (await rows.count()) === 2, 3000), 'remove from the home')
    await page.locator('.v-snackbar').getByRole('button', { name: 'Annuler' }).click()
    check(await eventually(async () => (await rows.count()) === 3, 3000), 'undo')
    await rows.first().getByRole('button', { name: /Remplacer/ }).click()
    check(await eventually(async () => (await names())[0] !== before[0], 5000), 'replace from the home')
    await card.getByRole('link', { name: 'Ajouter au menu' }).click()
    check(await eventually(() => page.locator('.fork-draw__plan').isVisible(), 5000), '"add to the meal plan" opens the plan sheet')
    await page.evaluate(() => localStorage.removeItem('fork_recipe_draw'))
  },

  // draw X recipes at random: a short list, remove or replace one at a time, kept on the device
  async draw(page) {
    await page.goto(base + '/', { waitUntil: 'networkidle' })
    await page.evaluate(() => { localStorage.removeItem('fork_recipe_draw'); localStorage.setItem('fork_recipe_draw_size', '3') })
    await page.reload({ waitUntil: 'networkidle' }) // the stored values are read when the app starts
    await page.goto(base + '/recipes/draw', { waitUntil: 'networkidle' })
    await eventually(() => page.getByRole('button', { name: 'Tirer 3 recettes' }).isVisible())
    await page.getByRole('button', { name: 'Une recette de moins' }).click()
    await page.getByRole('button', { name: 'Une recette de plus' }).click()
    await page.getByRole('button', { name: 'Tirer 3 recettes' }).click()
    const rows = page.locator('.fork-draw__row')
    check(await eventually(async () => (await rows.count()) === 3, 5000), '3 recipes drawn')
    const names = async () => texts(page, '.fork-draw__name')
    const first = await names()
    check(new Set(first).size === 3, 'no recipe twice')

    await rows.first().getByRole('button', { name: /Retirer/ }).click()
    check(await eventually(async () => (await rows.count()) === 2, 3000), 'one removed')
    await page.locator('.v-snackbar').getByRole('button', { name: 'Annuler' }).click()
    check(await eventually(async () => (await rows.count()) === 3, 3000), 'undo puts it back')

    await rows.first().getByRole('button', { name: /Remplacer/ }).click()
    const replaced = await eventually(async () => { const n = await names(); return n[0] !== first[0] && n }, 5000)
    check(replaced && replaced.length === 3 && new Set(replaced).size === 3, `replaced in place by another recipe (${replaced && replaced[0]})`)

    await page.getByRole('button', { name: 'Une de plus' }).click()
    check(await eventually(async () => (await rows.count()) === 4, 5000), 'one more added')
    await page.getByRole('button', { name: 'Une de plus' }).click()
    check(await eventually(() => page.getByText("Plus d'autre recette qui corresponde.").isVisible(), 5000), 'says when no other recipe is left (4 in the demo)')
    await shot(page, 'recipe-draw')

    await page.reload({ waitUntil: 'networkidle' })
    check(await eventually(async () => (await rows.count()) === 4, 4000), 'the list stays on the device after a reload')
    await page.goto(base + '/', { waitUntil: 'networkidle' })
    check(await eventually(() => page.locator('.fork-week').getByText('4 plats tirés au sort').isVisible(), 3000), 'the home "this week" card shows the list')
    await page.goto(base + '/recipes/draw', { waitUntil: 'networkidle' })
    await eventually(async () => (await rows.count()) === 4, 4000)

    // the drawn list goes to the meal plan (one a day, ingredients to shopping) and to the shopping list alone
    const ids = async (path) => new Set(((await api(page, 'GET', path)).data.results ?? []).map((x) => x.id))
    const plansBefore = await ids('/api/meal-plan/?page_size=200')
    const listsBefore = await ids('/api/shopping-list-recipe/?page_size=200')
    const entriesBefore = await ids('/api/shopping-list-entry/?page_size=500')
    const typesBefore = await ids('/api/meal-type/?page_size=100')
    await page.getByRole('button', { name: 'Ajouter au menu' }).click()
    const sheet = page.locator('.fork-draw__plan')
    if (typesBefore.size === 0) {
      await eventually(() => sheet.getByRole('button', { name: 'Créer « Dîner »' }).isVisible(), 5000)
      await sheet.getByRole('button', { name: 'Créer « Dîner »' }).click()
      check(await eventually(async () => (await ids('/api/meal-type/?page_size=100')).size === 1, 5000), 'no meal type yet: "Dîner" created in one tap')
    }
    check(await eventually(() => sheet.getByRole('button', { name: 'Planifier 4 repas' }).isEnabled(), 5000), 'plan sheet ready (meal type chosen by default)')
    await shot(page, 'recipe-draw-plan')
    const firstDay = await sheet.getByLabel('Premier jour').inputValue()
    // the 3rd meal fails once: 2 are planned, the retry sends only the 2 others (no duplicate)
    let posts = 0
    await page.route('**/api/meal-plan/', (route) => {
      if (route.request().method() === 'POST' && ++posts === 3) return route.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
      return route.fallback()
    })
    await sheet.getByRole('button', { name: 'Planifier 4 repas' }).click()
    check(await eventually(() => sheet.getByText("2 sur 4 faits, puis une erreur. Réessayer n'envoie que le reste.").isVisible(), 10000), 'a failure part way says how far it went')
    await sheet.getByRole('button', { name: 'Planifier 2 repas' }).click()
    check(await eventually(() => page.getByText('4 repas ajoutés au menu').isVisible(), 10000), 'the retry plans the rest: 4 meals in all')
    await page.unroute('**/api/meal-plan/')
    const plans = ((await api(page, 'GET', '/api/meal-plan/?page_size=200')).data.results ?? []).filter((p) => !plansBefore.has(p.id))
    const days = plans.map((p) => p.from_date.slice(0, 10)).sort()
    const consecutive = days.every((d, i) => i === 0 || (new Date(d) - new Date(days[i - 1])) / 86400000 === 1)
    check(plans.length === 4 && new Set(plans.map((p) => p.recipe?.id)).size === 4 && consecutive, `one recipe a day, 4 days in a row, no duplicate (${days.join(', ')})`)
    check(days[0] === firstDay, `starts on the chosen first day (${firstDay})`)
    const mealTime = (plans[0]?.meal_type?.time || '12:00').slice(0, 5)
    check(plans.every((p) => p.meal_type?.id === plans[0].meal_type?.id && p.from_date.includes(`T${mealTime}`)), `same meal for all, at its time (${plans[0]?.meal_type?.name} ${mealTime})`)
    const plannedLists = ((await api(page, 'GET', '/api/shopping-list-recipe/?page_size=200')).data.results ?? []).filter((l) => !listsBefore.has(l.id))
    const newEntries = ((await api(page, 'GET', '/api/shopping-list-entry/?page_size=500')).data.results ?? []).filter((x) => !entriesBefore.has(x.id))
    check(plannedLists.length === 4 && newEntries.length > 0, `their ingredients went to the shopping list (${plannedLists.length} recipes, ${newEntries.length} items)`)

    await page.getByRole('button', { name: 'Ajouter aux courses' }).click()
    check(await eventually(() => page.locator('.fork-draw__shop').getByText(/sont déjà dans les courses/).isVisible(), 3000), 'warns that these recipes are already on the shopping list')
    await page.locator('.fork-draw__shop').getByRole('button', { name: 'Ajouter' }).click()
    check(await eventually(() => page.getByText('4 recettes ajoutées aux courses').isVisible(), 10000), '4 recipes added to shopping')
    const allLists = ((await api(page, 'GET', '/api/shopping-list-recipe/?page_size=200')).data.results ?? []).filter((l) => !listsBefore.has(l.id))
    check(allLists.length === 8, `shopping alone adds 4 more recipes (${allLists.length})`)

    // restore
    for (const p of plans) await api(page, 'DELETE', `/api/meal-plan/${p.id}/`)
    for (const l of allLists) await api(page, 'DELETE', `/api/shopping-list-recipe/${l.id}/`)
    for (const e of ((await api(page, 'GET', '/api/shopping-list-entry/?page_size=500')).data.results ?? []).filter((x) => !entriesBefore.has(x.id))) {
      await api(page, 'DELETE', `/api/shopping-list-entry/${e.id}/`)
    }
    check((await ids('/api/meal-plan/?page_size=200')).size === plansBefore.size, 'meal plan restored')
    for (const id of await ids('/api/meal-type/?page_size=100')) if (!typesBefore.has(id)) await api(page, 'DELETE', `/api/meal-type/${id}/`)

    await page.getByRole('button', { name: 'Vider la liste' }).click()
    check(await eventually(async () => (await rows.count()) === 0, 3000), 'list cleared')
  },

  // P2: servings scale every quantity, cook mode one step per screen
  async p2(page, ctx) {
    await page.goto(`${base}/recipe/${ctx.curry}`, { waitUntil: 'networkidle' })
    const firstAmount = () => page.locator('.fork-ingredients__row .fork-ingredients__amount').first().innerText()
    check((await firstAmount()).includes('1'), 'first ingredient at base servings')
    for (let i = 0; i < 3; i++) await page.getByRole('button', { name: 'Une portion de plus' }).click()
    check((await firstAmount()).includes('2'), 'quantities doubled after 3 → 6 servings (ingredient list)')
    check((await page.locator('.fork-recipe__instructions').allInnerTexts()).join(' ').includes('800'), 'quantities doubled in the step text too')

    await page.getByRole('link', { name: 'Mode cuisine' }).click()
    await page.waitForURL(/\/cook/)
    await eventually(() => page.getByText('Étape 1 sur 4').isVisible())
    check(await page.getByText('Étape 1 sur 4').isVisible(), 'cook mode opens on the first screen')
    check(!(await page.locator('.fork-bottom-nav').count()), 'cook mode is full screen (no bottom bar)')
    await page.getByRole('button', { name: 'Suivant' }).click()
    check(await page.getByText('Étape 2 sur 4').isVisible(), 'next button goes forward')
    const size = await page.locator('.fork-cook__instructions').evaluate((el) => getComputedStyle(el).fontSize)
    check(size === '24px', `step text at 24 px (${size})`)
    const stepText = await page.locator('.fork-cook__content').innerText()
    check(stepText.includes('Oignon') && stepText.includes('2 pièces'), 'step ingredients recalled at the chosen servings')
    // swipe left = next
    const box = await page.locator('.fork-cook__content').boundingBox()
    await page.touchscreen.tap(box.x + 10, box.y + 10).catch(() => {})
    await page.evaluate(() => {
      const el = document.querySelector('.fork-cook')
      const touch = (x) => [new Touch({ identifier: 1, target: el, clientX: x, clientY: 300 })]
      el.dispatchEvent(new TouchEvent('touchstart', { touches: touch(320), changedTouches: touch(320), bubbles: true }))
      el.dispatchEvent(new TouchEvent('touchmove', { touches: touch(120), changedTouches: touch(120), bubbles: true }))
      el.dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: touch(120), bubbles: true }))
    })
    check(await eventually(() => page.getByText('Étape 3 sur 4').isVisible(), 2000), 'swipe left goes forward')
    await page.getByRole('button', { name: 'Précédent' }).click()
    check(await page.getByText('Étape 2 sur 4').isVisible(), 'back button goes backward')
    await page.getByRole('button', { name: 'Quitter le mode cuisine' }).click()
    await page.waitForURL(/\/recipe\/\d+\?servings=6/)
    check(true, 'leaving cook mode returns to the recipe with the chosen servings')
  },

  // M5: durations in the step text start timers; several timers, pause, +1 min, stop; they survive a reload
  async timers(page, ctx) {
    const timerRows = page.locator('.fork-timers__row')
    const curry = (await api(page, 'GET', `/api/recipe/${ctx.curry}/`)).data
    const step = curry.steps[1]
    await api(page, 'PATCH', `/api/step/${step.id}/`, { time: 20 }) // step.time chip, restored below
    try {
      await page.goto(`${base}/recipe/${ctx.curry}`, { waitUntil: 'networkidle' })
      await page.evaluate(() => localStorage.removeItem('fork_timers'))
      await page.reload({ waitUntil: 'networkidle' })
      const link = page.locator('.fork-recipe__instructions .fork-timer-link', { hasText: '15 min' })
      check(await eventually(() => link.isVisible()), '"15 min" in the step text is tappable (recipe view)')
      await link.click()
      check(await eventually(() => timerRows.first().isVisible(), 3000), 'tapping it starts a timer shown in the timers bar')
      const time = () => timerRows.first().locator('.fork-timers__time').innerText()
      check(/^1[45]:\d\d$/.test(await time()), `countdown from 15:00 (${await time()})`)
      check((await timerRows.first().innerText()).includes('Mijoter · 15 min'), 'timer labelled with its step and duration')
      await timerRows.first().getByRole('button', { name: 'Mettre en pause' }).click()
      const paused = await time()
      await page.waitForTimeout(1500)
      check(await time() === paused && await timerRows.first().getByRole('button', { name: 'Reprendre' }).isVisible(), 'pause freezes the countdown')
      await timerRows.first().getByRole('button', { name: 'Ajouter une minute' }).click()
      check(/^1[56]:\d\d$/.test(await time()), `+1 min adds a minute (${await time()})`)
      await timerRows.first().getByRole('button', { name: 'Reprendre' }).click()

      await page.locator('.fork-recipe__time-chip').first().click()
      check(await eventually(async () => (await timerRows.count()) === 2, 3000), 'the step time chip starts a second timer')

      // a range asks which duration
      const poulet = (await api(page, 'GET', '/api/recipe/?query=poulet&page_size=1')).data.results[0]
      await page.goto(`${base}/recipe/${poulet.id}`, { waitUntil: 'networkidle' })
      check(await eventually(async () => (await timerRows.count()) === 2), 'timers follow to another page')
      await page.locator('.fork-timer-link', { hasText: '16 à 18 min' }).click()
      const sheet = page.locator('.v-bottom-sheet')
      check(await eventually(() => sheet.getByText('Quelle durée ?').isVisible(), 3000), 'a range opens a duration choice')
      const options = await sheet.locator('.v-btn', { hasText: 'min' }).allInnerTexts()
      check(options.join('|') === '16 min|17 min|18 min', `low, middle and high proposed (${options.join(', ')})`)
      await shot(page, 'timer-range')
      await sheet.getByRole('button', { name: '17 min' }).click()
      const summary = page.locator('.fork-timers__summary')
      check(await eventually(() => summary.isVisible(), 3000) && (await summary.innerText()).includes('3 minuteurs'), 'a third timer collapses the bar into one summary row')
      await summary.click()
      check(await eventually(async () => (await page.locator('.fork-timers__row[role="timer"]').count()) === 3, 3000), 'the summary row opens the full list')
      await shot(page, 'timers-bar')
      await shot(page, 'timers-bar', 'dark')

      // timers rely on their end time: a reload keeps them; an elapsed one shows as done
      await page.evaluate(() => {
        const list = JSON.parse(localStorage.getItem('fork_timers'))
        list[0].endAt = Date.now() + 1500
        localStorage.setItem('fork_timers', JSON.stringify(list))
      })
      await page.reload({ waitUntil: 'networkidle' })
      check(await eventually(async () => (await page.locator('.fork-timers__summary').innerText()).includes('3 minuteurs')), 'timers survive a reload')
      check(await eventually(() => page.locator('.fork-timers__row--done', { hasText: 'Terminé' }).isVisible(), 5000), 'a timer reaching its end time rings as done (shown even when collapsed)')

      // cook mode shows them above its buttons, durations tappable there too
      await page.goto(`${base}/recipe/${ctx.curry}/cook`, { waitUntil: 'networkidle' })
      check(await eventually(() => page.locator('.fork-cook__nav .fork-timers__row').first().isVisible()), 'cook mode shows the timers above its buttons')
      await page.getByRole('button', { name: 'Suivant' }).click()
      await page.getByRole('button', { name: 'Suivant' }).click()
      check(await page.locator('.fork-cook__instructions .fork-timer-link', { hasText: '15 min' }).isVisible(), 'durations tappable in cook mode')
      check(await page.locator('.fork-cook__time').isVisible(), 'step time chip shown in cook mode')
      await shot(page, 'cook-timers')
      const stopButtons = page.locator('.fork-timers').getByRole('button', { name: 'Arrêter le minuteur' })
      for (let i = 0; i < 3; i++) {
        if (await page.locator('.fork-timers__summary[aria-expanded="false"]').count()) await page.locator('.fork-timers__summary').click()
        await stopButtons.first().click()
      }
      check(await eventually(async () => !(await page.locator('.fork-timers').count()), 3000), 'stop removes the timers')
    } finally {
      await api(page, 'PATCH', `/api/step/${step.id}/`, { time: step.time ?? 0 })
      await page.evaluate(() => localStorage.removeItem('fork_timers')).catch(() => {})
    }
  },

  // M5: "Terminé" opens "Bon appétit": rating and comment are optional, Save and Skip both log the cooking
  async cookdone(page, ctx) {
    const logs = async () => {
      const d = (await api(page, 'GET', `/api/cook-log/?recipe=${ctx.curry}&page_size=100`)).data
      return d.results ?? d
    }
    const before = new Set((await logs()).map((l) => l.id))
    const created = []
    try {
      await page.goto(`${base}/recipe/${ctx.curry}?servings=5`, { waitUntil: 'networkidle' })
      await page.getByRole('link', { name: 'Mode cuisine' }).click()
      await page.waitForURL(/\/cook/)
      await eventually(() => page.getByText('Étape 1 sur 4').isVisible())
      for (let i = 0; i < 3; i++) await page.getByRole('button', { name: 'Suivant' }).click()
      await page.getByRole('button', { name: 'Terminé' }).click()
      check(await eventually(() => page.getByText('Bon appétit !').isVisible(), 3000), '"Terminé" opens the "Bon appétit" screen')
      check(await page.getByText('Cuisiné pour 5 portions').isVisible(), 'servings recalled')
      await page.locator('.fork-cook__rating .v-rating__item').nth(3).locator('button, input').first().click()
      await page.getByLabel('Commentaire (facultatif)').fill('Un peu plus de citron')
      await shot(page, 'cook-done')
      await shot(page, 'cook-done', 'dark')
      await page.getByRole('button', { name: 'Enregistrer' }).click()
      await page.waitForURL(/\/recipe\/\d+(\?servings=5)?$/)
      check(!page.url().includes('/cook'), 'back to the recipe after saving')
      const saved = (await logs()).filter((l) => !before.has(l.id))
      saved.forEach((l) => created.push(l.id))
      check(saved.length === 1 && saved[0].rating === 4 && saved[0].servings === 5 && saved[0].comment === 'Un peu plus de citron',
        `cook log saved with rating, servings and comment (${JSON.stringify(saved.map((l) => [l.rating, l.servings, l.comment]))})`)

      await page.goto(`${base}/recipe/${ctx.curry}/cook`, { waitUntil: 'networkidle' })
      await eventually(() => page.getByText('Étape 1 sur 4').isVisible())
      for (let i = 0; i < 3; i++) await page.getByRole('button', { name: 'Suivant' }).click()
      await page.getByRole('button', { name: 'Terminé' }).click()
      await page.getByRole('button', { name: 'Passer' }).click()
      await page.waitForURL(/\/recipe\/\d+/)
      const skipped = (await logs()).filter((l) => !before.has(l.id) && !created.includes(l.id))
      skipped.forEach((l) => created.push(l.id))
      check(skipped.length === 1 && skipped[0].rating == null && skipped[0].servings === 3, '"Passer" logs the cooking too, without rating')

      const forgotten = (await api(page, 'GET', '/api/kitchen/recipes/?sort=forgotten&page_size=50')).data
      const names = (forgotten.results ?? forgotten).map((r) => r.name)
      check(names[names.length - 1]?.includes('Curry'), `"pas faites depuis longtemps" now lists the curry last (${names.join(', ')})`)
    } finally {
      for (const id of created) await api(page, 'DELETE', `/api/cook-log/${id}/`)
    }
  },

  // M5: a link shared to the PWA (share_target) imports the first URL of url, text or title
  async share(page) {
    const sent = []
    await page.route('**/api/recipe-from-source/', (r) => {
      sent.push(JSON.parse(r.request().postData() || '{}').url)
      return r.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ error: true, msg: 'test' }) })
    })
    try {
      const text = encodeURIComponent('Recette de tarte aux pommes https://www.example.org/recettes/tarte-123 à essayer')
      await page.goto(`${base}/recipe/import?title=Tarte&text=${text}&url=`, { waitUntil: 'networkidle' })
      check(await eventually(() => sent.length >= 1, 5000), 'opening the share target starts an import')
      check(sent.length === 1 && sent[0] === 'https://www.example.org/recettes/tarte-123', `only the URL found in the shared text is imported (${sent.join(', ')})`)
      sent.length = 0
      await page.goto(`${base}/recipe/import?title=${encodeURIComponent('Tarte https://x.example.org/t')}`, { waitUntil: 'networkidle' })
      check(await eventually(() => sent[0] === 'https://x.example.org/t', 5000), 'a URL in the title only works too')
    } finally {
      await page.unroute('**/api/recipe-from-source/')
    }
  },

  // M5: "Au menu" card on the phone home, only when a meal is planned (today, or tomorrow after 21:00)
  async menu(page, ctx) {
    const card = page.locator('.fork-menu')
    const clean = async () => {
      const d = (await api(page, 'GET', '/api/meal-plan/?page_size=100')).data
      for (const p of (d.results ?? d).filter((p) => (p.title || '').startsWith('[flow]') || p.note === '[flow]')) await api(page, 'DELETE', `/api/meal-plan/${p.id}/`)
    }
    await page.goto(base + '/', { waitUntil: 'networkidle' })
    await clean()
    const day = await page.evaluate(() => {
      const d = new Date()
      if (d.getHours() >= 21) d.setDate(d.getDate() + 1)
      return { iso: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`, tomorrow: new Date().getHours() >= 21 }
    })
    const existing = (await api(page, 'GET', `/api/meal-plan/?from_date=${day.iso}&to_date=${day.iso}`)).data
    if (!(existing.results ?? existing).length) {
      await page.reload({ waitUntil: 'networkidle' })
      await page.waitForTimeout(800)
      check(!(await card.count()), 'no card when nothing is planned')
    }
    const types = (await api(page, 'GET', '/api/meal-type/?page_size=10')).data
    let mealType = (types.results ?? types)[0]
    let createdType = null
    if (!mealType) {
      createdType = (await api(page, 'POST', '/api/meal-type/', { name: 'Dîner', order: 0 })).data
      mealType = createdType
    }
    const curry = (await api(page, 'GET', `/api/recipe/${ctx.curry}/`)).data
    const plan = await api(page, 'POST', '/api/meal-plan/', {
      recipe: { id: curry.id, name: curry.name, keywords: [] }, servings: 4, note: '[flow]', from_date: day.iso, to_date: day.iso,
      meal_type: { id: mealType.id, name: mealType.name }, title: '',
    })
    const titled = await api(page, 'POST', '/api/meal-plan/', {
      title: 'Restes', note: '[flow]', servings: 2, from_date: day.iso, to_date: day.iso, meal_type: { id: mealType.id, name: mealType.name },
    })
    try {
      check(plan.status === 201 && titled.status === 201, `meal plan entries created (${plan.status}, ${titled.status})`)
      await page.reload({ waitUntil: 'networkidle' })
      check(await eventually(() => card.isVisible()), 'card shown on the phone home when a meal is planned')
      check((await card.innerText()).includes(day.tomorrow ? 'Au menu demain' : "Au menu aujourd'hui"), 'card says today (or tomorrow after 21:00)')
      check(await card.locator('div.fork-menu__row', { hasText: 'Restes' }).isVisible(), 'an entry without recipe shows its title (no link)')
      await shot(page, 'home-menu')
      await shot(page, 'home-menu', 'dark')
      await card.locator('a.fork-menu__row', { hasText: 'Curry' }).click()
      await page.waitForURL(/\/recipe\/\d+\?servings=4/)
      check(true, 'a tap opens the recipe at the planned servings')
    } finally {
      for (const p of [plan, titled]) if (p.data?.id) await api(page, 'DELETE', `/api/meal-plan/${p.data.id}/`)
      if (createdType) await api(page, 'DELETE', `/api/meal-type/${createdType.id}/`)
    }
  },

  // P3: add to shopping, untick what you have
  async p3(page, ctx) {
    await page.goto(`${base}/recipe/${ctx.curry}?servings=6`, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Ajouter à la liste de courses' }).click()
    const rows = page.locator('.fork-shop-sheet [role="checkbox"]')
    await eventually(async () => (await rows.count()) > 0)
    const n = await rows.count()
    const checked = await page.locator('.fork-shop-sheet [role="checkbox"][aria-checked="true"]').count()
    check(n === 8 && checked === 8, `every ingredient listed and checked (${checked}/${n})`)
    check((await page.locator('.fork-shop-sheet').innerText()).includes('800'), 'amounts at the chosen servings (6)')
    await rows.first().click()
    check(await page.getByRole('button', { name: 'Ajouter 7 articles' }).isVisible(), 'unticking one item updates the count')
    const before = (await api(page, 'GET', '/api/shopping-list-recipe/?page_size=100')).data
    await page.getByRole('button', { name: 'Ajouter 7 articles' }).click()
    await eventually(() => page.getByText('7 articles ajoutés aux courses').isVisible())
    check(await page.getByText('7 articles ajoutés aux courses').isVisible(), 'confirmation shown')
    const after = (await api(page, 'GET', '/api/shopping-list-recipe/?page_size=100')).data
    const beforeIds = new Set((before.results ?? before).map((r) => r.id))
    const created = (after.results ?? after).filter((r) => !beforeIds.has(r.id))
    check(created.length === 1, 'one recipe added to the household list')
    const entries = (await api(page, 'GET', '/api/shopping-list-entry/?page_size=200')).data
    const mine = (entries.results ?? entries).filter((e) => e.list_recipe === created[0]?.id)
    check(mine.length === 7, `7 shopping entries created (${mine.length})`)
    for (const r of created) await api(page, 'DELETE', `/api/shopping-list-recipe/${r.id}/`)
  },

  // P4: one-tap check, cart, undo, quick add, sync from the other device
  async p4(page) {
    await page.goto(base + '/shopping', { waitUntil: 'networkidle' })
    await eventually(() => page.locator('.fork-shopping__row').first().isVisible())
    const aisles = await texts(page, '.fork-shopping__aisle')
    check(aisles.length >= 2, `list grouped by aisle (${aisles.join(' / ')})`)
    const row = page.locator('.fork-shopping__row:not(.fork-shopping__row--done)', { hasText: 'Citron' })
    await row.click()
    const cart = page.locator('.fork-shopping__row--done', { hasText: 'Citron' })
    check(await eventually(() => cart.isVisible(), 3000), 'one tap moves the item to "dans le panier"')
    await page.locator('.v-snackbar').getByRole('button', { name: 'Annuler' }).click()
    check(await eventually(async () => !(await cart.count()) && (await row.isVisible()), 3000), 'undo brings it back')
    await page.waitForTimeout(1200) // let the sync queue flush

    const count = async () => (await page.locator('.fork-shopping__row').count())
    const n0 = await count()
    await page.getByPlaceholder('Ajouter, ex. 2 citrons').fill('1 Poivron')
    await page.keyboard.press('Enter')
    check(await eventually(() => page.locator('.fork-shopping__row', { hasText: 'Poivron' }).isVisible(), 6000), 'free text "1 Poivron" added')
    const aisle = await page.locator('section', { has: page.locator('.fork-shopping__row', { hasText: 'Poivron' }) }).locator('.fork-shopping__aisle').innerText()
    check(/l[ée]gumes/i.test(aisle), `added item takes its aisle (${aisle})`)
    await page.getByRole('button', { name: 'Annuler' }).first().click()
    check(await eventually(async () => (await count()) === n0, 4000), 'undo removes the added item')

    // another household member adds an item: it shows up without reloading (auto sync)
    const food = (await api(page, 'GET', '/api/food/?query=Ail&page_size=1')).data.results[0]
    const created = await api(page, 'POST', '/api/shopping-list-entry/', { food: { id: food.id, name: food.name }, amount: 1, unit: null })
    check(created.status === 201, 'entry created through the API (other device)')
    check(await eventually(() => page.locator('.fork-shopping__row', { hasText: /^\s*Ail/ }).first().isVisible(), 12000), 'it appears without reloading')
    await api(page, 'DELETE', `/api/shopping-list-entry/${created.data.id}/`)

    // check everything: simple end message
    const rowsToCheck = page.locator('.fork-shopping__row:not(.fork-shopping__row--done)')
    const ids = []
    await page.reload({ waitUntil: 'networkidle' })
    await eventually(() => rowsToCheck.first().isVisible())
    const total = await rowsToCheck.count()
    for (let i = 0; i < total; i++) { await rowsToCheck.first().click(); ids.push(i) }
    check(await eventually(() => page.getByText('Tout est dans le panier.').isVisible(), 3000), 'end message once everything is checked')
    for (let i = 0; i < total; i++) await page.getByRole('button', { name: 'Annuler' }).first().click()
    check(await eventually(async () => (await rowsToCheck.count()) === total, 4000), 'undo restores every item')
    await page.waitForTimeout(1500)
  },

  // M5: in the shop without network: checks kept on the device (even after a reload), sent when the network is back
  async offline(page) {
    const context = page.context()
    // record wake lock requests (headless Chromium has no real screen to keep on)
    await context.addInitScript(() => {
      window.__forkWakeLocks = []
      if (!navigator.wakeLock) return
      navigator.wakeLock.request = async (type) => {
        const lock = Object.assign(new EventTarget(), { type, released: false, release: async () => { lock.released = true; lock.dispatchEvent(new Event('release')) } })
        window.__forkWakeLocks.push(lock)
        return lock
      }
    })
    const serverEntry = async (id) => (await (await context.request.get(`${base}/api/shopping-list-entry/${id}/`)).json())
    await page.goto(base + '/shopping', { waitUntil: 'networkidle' })
    await page.evaluate(() => { localStorage.removeItem('fork_shopping_sync_queue') })
    await page.reload({ waitUntil: 'networkidle' })
    const row = page.locator('.fork-shopping__row:not(.fork-shopping__row--done)', { hasText: 'Citron' })
    await eventually(() => row.isVisible())
    const ids = (await api(page, 'GET', '/api/shopping-list-entry/?page_size=200')).data.results
      .filter((e) => e.food?.name === 'Citron' && !e.checked).map((e) => e.id)
    check(ids.length > 0, `an unchecked "Citron" entry to work with (${ids.length})`)
    // the service worker controls the page before going offline (it serves the app shell when reloading offline)
    // (as on the phone: the upstream service worker caches pages and API answers it has served)
    await page.evaluate(() => navigator.serviceWorker?.ready.then(() => true)).catch(() => {})
    await page.reload({ waitUntil: 'networkidle' })
    check(await page.evaluate(() => !!navigator.serviceWorker?.controller), 'service worker controls the shopping page')
    check(await eventually(() => page.evaluate(() => window.__forkWakeLocks?.some((l) => !l.released))), 'screen kept on while the list is open')
    try {
      await context.setOffline(true)
      check(await eventually(() => page.getByText('Dernier état connu de la liste').isVisible(), 3000), 'offline banner shown')
      await row.click()
      const cart = page.locator('.fork-shopping__row--done', { hasText: 'Citron' })
      check(await eventually(() => cart.isVisible(), 3000), 'checking works offline')
      check(await eventually(() => page.getByText('1 modification en attente').isVisible(), 3000), 'indicator "1 modification en attente"')
      const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('fork_shopping_sync_queue') || '[]'))
      check(stored.some((q) => q.checked && ids.every((id) => q.ids.includes(id))), 'pending check stored on the device')
      await shot(page, 'shopping-offline')
      await shot(page, 'shopping-offline', 'dark')

      // closing the app (here: a reload, still offline) loses nothing; the last known list is shown
      await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => {})
      check(await eventually(() => cart.isVisible(), 10000), 'after an offline reload the list shows, the item still in the cart')
      check(await eventually(() => page.getByText('1 modification en attente').isVisible(), 3000), 'still 1 change waiting after the reload')
      check((await serverEntry(ids[0])).checked === false, 'nothing reached the server while offline')

      await context.setOffline(false)
      check(await eventually(async () => (await serverEntry(ids[0])).checked === true, 15000), 'back online: the check is sent to the server')
      check(await eventually(async () => !(await page.getByText('modification en attente').count()), 5000), 'indicator gone once sent')
      await page.locator('.fork-bottom-nav .v-btn', { hasText: 'Recettes' }).click()
      check(await eventually(() => page.evaluate(() => window.__forkWakeLocks.length > 0 && window.__forkWakeLocks.every((l) => l.released))), 'screen released when leaving the list')
    } finally {
      await context.setOffline(false)
      await context.request.post(`${base}/api/shopping-list-entry/bulk/`, {
        data: { ids, checked: false }, headers: { 'X-CSRFToken': (await context.cookies()).find((c) => c.name === 'csrftoken')?.value ?? '' },
      })
      await page.evaluate(() => localStorage.removeItem('fork_shopping_sync_queue')).catch(() => {})
    }
  },

  // M3: food tree, move in 2 taps, quick edit, "no aisle" filter
  // clear the list: only the cart, or everything; confirmed first, undo brings everything back
  async clearshopping(page) {
    const all = async () => (await api(page, 'GET', '/api/shopping-list-entry/?page_size=200')).data.results
    const before = await all()
    const food = async (q) => (await api(page, 'GET', `/api/food/?query=${q}&page_size=1`)).data.results[0]
    const ail = await food('Ail'), poivron = await food('Poivron')
    const inCart = (await api(page, 'POST', '/api/shopping-list-entry/', { food: { id: ail.id, name: ail.name }, amount: 1, unit: null })).data
    await api(page, 'PATCH', `/api/shopping-list-entry/${inCart.id}/`, { checked: true })
    const toBuy = (await api(page, 'POST', '/api/shopping-list-entry/', { food: { id: poivron.id, name: poivron.name }, amount: 2, unit: null })).data

    await page.goto(base + '/shopping', { waitUntil: 'networkidle' })
    await eventually(() => page.locator('.fork-shopping__row--done', { hasText: /^\s*Ail/ }).first().isVisible())
    const menu = () => page.getByRole('button', { name: 'Options' }).click()

    // the cart only
    await menu()
    await page.getByText('Retirer les articles du panier').click()
    const dialog = page.locator('.fork-shopping__clear')
    check(await eventually(() => dialog.isVisible(), 3000), 'confirmation before removing the cart')
    await dialog.getByRole('button', { name: 'Retirer' }).click()
    check(await eventually(async () => (await page.locator('.fork-shopping__row--done').count()) === 0, 6000), 'cart emptied on screen')
    check(await eventually(async () => !(await all()).some(e => e.id === inCart.id), 6000), 'checked entry deleted on the server')
    check((await all()).some(e => e.id === toBuy.id), 'items still to buy are kept')

    // everything: cancel first, then confirm
    const rows = async () => page.locator('.fork-shopping__row').count()
    const n = await rows()
    await menu()
    await page.getByText('Vider la liste').click()
    check(await eventually(() => dialog.getByText(/articles? seront? supprimés? de la liste/).isVisible(), 3000), 'the dialog says how many items go')
    await dialog.getByRole('button', { name: 'Annuler' }).click()
    check(await eventually(async () => !(await dialog.isVisible()), 3000) && (await rows()) === n, 'cancel keeps the list')
    await menu()
    await page.getByText('Vider la liste').click()
    await shot(page, 'shopping-clear-mobile')
    await dialog.getByRole('button', { name: 'Vider' }).click()
    check(await eventually(() => page.getByText('La liste de courses est vide.').isVisible(), 8000), 'list emptied')
    check(await eventually(async () => (await all()).filter(e => before.some(b => b.id === e.id) || e.id === toBuy.id).length === 0, 6000), 'entries deleted on the server')

    // undo: the whole list comes back, then the cart (the undo button keeps both)
    await page.locator('.v-snackbar').getByRole('button', { name: 'Annuler' }).click()
    check(await eventually(async () => (await rows()) === n, 8000), 'undo brings every item back')
    await page.getByRole('button', { name: 'Annuler' }).first().click()
    const checkedBefore = before.filter(e => e.checked).length
    check(await eventually(async () => (await page.locator('.fork-shopping__row--done').count()) >= checkedBefore + 1, 8000), 'undo again brings the cart back')
    check(await eventually(async () => (await all()).length === before.length + 2, 6000), 'entries recreated on the server')

    // restore: drop the two items added by this flow (recreated by the undo)
    await page.waitForTimeout(800)
    const mine = [(e) => e.food?.id === poivron.id && Number(e.amount) === 2, (e) => e.food?.id === ail.id && Number(e.amount) === 1]
    for (const added of mine) {
      const extra = (await all()).filter(added).slice(before.filter(added).length)
      for (const e of extra) await api(page, 'DELETE', `/api/shopping-list-entry/${e.id}/`)
    }
    check((await all()).length === before.length, `list restored (${before.length} entries)`)
  },

  // M7: food prices (queue, food sheet), estimate on the recipe and the shopping list, "shopping done" adjustment
  async prices(page) {
    const kfoods = async () => (await api(page, 'GET', '/api/kitchen/foods/')).data
    const byName = async (name) => (await kfoods()).foods.find((f) => f.name === name)
    const priceOf = async (name) => (await api(page, 'GET', `/api/kitchen/foods/${(await byName(name)).id}/price/`)).data.price
    const names = ['Lardons', 'Lait de coco', 'Parmesan', 'Citron']
    const before = {}
    let cartBefore = null
    for (const n of names) before[n] = { id: (await byName(n)).id, price: await priceOf(n) }
    const restore = async () => {
      for (const n of names) {
        const b = before[n]
        if (!b.price) await api(page, 'PUT', `/api/kitchen/foods/${b.id}/price/`, { price: null })
        else if (b.price.source === 'estimated') await api(page, 'PUT', `/api/kitchen/foods/${b.id}/price/`, { suggest: true })
        else await api(page, 'PUT', `/api/kitchen/foods/${b.id}/price/`, { price: b.price.price, per: b.price.per })
      }
    }
    try {
      // foods page: counter of the queue, prices in the list (≈ = estimated)
      await page.goto(base + '/foods', { waitUntil: 'networkidle' })
      const queue = page.locator('.fork-foods__queue', { hasText: 'sans prix' })
      check(await eventually(() => queue.isVisible()), `queue counter on the foods page (${await queue.innerText().catch(() => '')})`)
      check(/≈ 25,00\s€ \/ kg/.test(await page.locator('.fork-foods__row', { hasText: 'Parmesan' }).innerText()), 'estimated price shown in the foods list')

      // the queue: the average price in one tap, or a price typed in
      await queue.click()
      await eventually(() => page.locator('.fork-noprice__food').isVisible())
      await shot(page, 'noprice')
      const first = (await page.locator('.fork-noprice__food').innerText()).trim()
      const suggestion = page.getByRole('button', { name: /€ \/ (kg|L|pièce)/ })
      check(await suggestion.isVisible(), `average price proposed for ${first}`)
      await suggestion.click()
      check(await eventually(async () => (await page.locator('.fork-noprice__food').innerText()).trim() !== first, 4000), 'one tap: next food')
      check((await priceOf(first))?.source === 'estimated', 'the average price is stored as estimated')
      const second = (await page.locator('.fork-noprice__food').innerText()).trim()
      await page.locator('.fork-price__amount input').fill('12,50')
      await page.getByRole('button', { name: 'Enregistrer ce prix' }).click()
      check(await eventually(() => page.getByText('Tous les aliments achetés ont un prix.').isVisible(), 4000), 'queue emptied')
      const typed = await priceOf(second)
      check(typed?.price === 12.5 && typed.source === 'confirmed', `typed price stored as confirmed (${second}: ${JSON.stringify(typed)})`)

      // food sheet: price field, the estimate is replaced by a confirmed price
      await page.goto(base + '/foods', { waitUntil: 'networkidle' })
      await page.locator('.fork-foods__row', { hasText: 'Parmesan' }).click()
      const sheet = page.locator('.fork-food-sheet')
      check(await eventually(() => sheet.getByText('estimé').isVisible(), 4000), 'the sheet tells an estimated price')
      await sheet.locator('.fork-price__amount input').fill('24')
      await shot(page, 'food-sheet-price')
      await sheet.getByRole('button', { name: 'Sauvegarder' }).click()
      check(await eventually(async () => /^(?!≈)24,00\s€ \/ kg$/.test((await page.locator('.fork-foods__row', { hasText: 'Parmesan' }).locator('.fork-foods__price').innerText()).trim()), 5000),
        'confirmed price in the list, without ≈')

      // recipe: price at the servings chosen
      const recipe = (await api(page, 'GET', '/api/recipe/?query=carbonara&page_size=1')).data.results[0]
      await page.goto(base + `/recipe/${recipe.id}`, { waitUntil: 'networkidle' })
      const line = page.locator('.fork-recipe__price')
      check(await eventually(() => line.isVisible(), 5000), 'price shown on the recipe')
      const t1 = await line.innerText()
      check(/≈ \d+,\d\d\s€ · \d+,\d\d\s€\/pers\./.test(t1), `total and per serving (${t1.replace(/\s+/g, ' ')})`)
      await page.getByRole('button', { name: 'Une portion de plus' }).click()
      check(await eventually(async () => (await line.innerText()) !== t1, 3000), `follows the servings (${(await line.innerText()).replace(/\s+/g, ' ')})`)
      await shot(page, 'recipe-price')

      // shopping list: total at the top, whole packages, then "shopping done"
      await page.goto(base + '/shopping', { waitUntil: 'networkidle' })
      const total = page.locator('.fork-shopping__price')
      check(await eventually(() => total.isVisible(), 6000), `total at the top of the list (${(await total.innerText().catch(() => '')).replace(/\s+/g, ' ')})`)
      check(await eventually(() => page.locator('.fork-shopping__row', { hasText: 'Pâtes' }).getByText('1 paquet').isVisible(), 4000), 'pasta counted in whole packages')
      // a known cart: what was already in it goes back to the list for the time of the flow
      cartBefore = (await texts(page, '.fork-shopping__row--done .fork-shopping__food')).map((t) => t.trim())
      for (const name of cartBefore) await page.locator('.fork-shopping__row--done', { hasText: name }).first().click()
      for (const name of ['Citron', 'Pâtes']) {
        await page.locator('.fork-shopping__row:not(.fork-shopping__row--done)', { hasText: name }).first().click()
        await eventually(() => page.locator('.fork-shopping__row--done', { hasText: name }).isVisible(), 3000)
      }
      await page.waitForTimeout(1500) // the checks reach the server
      await page.getByRole('button', { name: 'Options' }).click()
      await page.getByText('Courses terminées').click()
      const done = page.locator('.fork-done')
      await eventually(() => done.isVisible(), 3000)
      // cart: pasta, one 500 g package at 1.20 € (confirmed), citron 2 x 120 g at 3.50 €/kg (estimated) = 0.84
      await done.locator('.fork-done__paid input').fill('2,46')
      await done.getByRole('button', { name: 'Comparer' }).click()
      const gap = done.locator('.fork-done__gap')
      check(await eventually(async () => /payé 2,46\s€ · estimé 2,04\s€/.test(await gap.innerText()), 4000), `gap shown before saving (${(await gap.innerText().catch(() => '')).replace(/\s+/g, ' ')})`)
      check(/\+50 %/.test(await gap.innerText()), 'the gap only moves the estimated part (+50 %)')
      check((await priceOf('Citron')).price === 3.5, 'nothing changed before "adjust"')
      await shot(page, 'shopping-done-gap')
      await done.getByRole('button', { name: 'Ajuster les prix' }).click()
      check(await eventually(() => done.getByText('1 prix ajusté').isVisible(), 4000), 'one estimated price adjusted')
      const citronAfter = await priceOf('Citron')
      check(Math.abs(citronAfter.price - 3.5 * 1.25) < 0.02 && citronAfter.source === 'estimated', `smoothed: half of the gap (${citronAfter.price})`)
      check((await priceOf('Parmesan')).price === 24, 'the confirmed price did not move')
      await done.locator('.v-card-actions').getByRole('button', { name: 'Fermer' }).click()

      // one item corrected: its price becomes confirmed, nothing estimated is left to adjust
      await page.getByRole('button', { name: 'Options' }).click()
      await page.getByText('Courses terminées').click()
      await done.locator('.fork-done__paid input').fill('3,50')
      await done.getByRole('button', { name: 'Comparer' }).click()
      await eventually(() => done.getByRole('button', { name: 'Corriger le prix de Citron' }).isVisible(), 4000)
      await done.getByRole('button', { name: 'Corriger le prix de Citron' }).click()
      await done.getByLabel('Payé pour Citron').fill('0,90')
      await done.locator('.fork-done__correct').getByRole('button', { name: 'Sauvegarder' }).click()
      check(await eventually(async () => (await priceOf('Citron'))?.source === 'confirmed', 4000), `one tap correction: confirmed (${JSON.stringify(await priceOf('Citron'))})`)
      check(Math.abs((await priceOf('Citron')).price - 3.75) < 0.01, '0,90 € for 2 x 120 g: 3,75 € / kg')
      check(await eventually(() => done.getByText('Aucun prix estimé dans le panier').isVisible(), 4000), 'then nothing estimated is left to adjust')
      await done.getByRole('button', { name: 'Passer' }).click()
      check(await eventually(async () => !(await done.isVisible()), 3000), '"skip" closes without changing anything')
    } finally {
      // the cart as it was
      if (cartBefore) {
        await page.goto(base + '/shopping', { waitUntil: 'networkidle' }).catch(() => {})
        for (const name of ['Citron', 'Pâtes']) {
          const row = page.locator('.fork-shopping__row--done', { hasText: name }).first()
          if (await row.isVisible().catch(() => false)) await row.click()
        }
        for (const name of cartBefore) {
          const row = page.locator('.fork-shopping__row:not(.fork-shopping__row--done)', { hasText: name }).first()
          if (await row.isVisible().catch(() => false)) await row.click()
        }
        await page.waitForTimeout(1500)
      }
      await restore()
    }
    check(JSON.stringify(await priceOf('Citron')) === JSON.stringify(before.Citron.price), 'prices restored')
  },

  async foods(page) {
    await page.goto(base + '/foods', { waitUntil: 'networkidle' })
    const family = page.locator('.fork-foods__family', { hasText: 'Légumes' })
    check(await eventually(() => family.isVisible()), 'families listed (Légumes)')
    check(await page.locator('.fork-foods__row', { hasText: 'Courgette' }).isVisible(), 'members listed under their family')
    check(!(await page.locator('table').count()), 'no table on the food screen')
    await family.locator('.fork-foods__family-toggle').click()
    check(!(await page.locator('.fork-foods__row', { hasText: 'Courgette' }).count()), 'family folds')
    await family.locator('.fork-foods__family-toggle').click()

    await page.getByPlaceholder('Rechercher un aliment').fill('echal')
    const found = await eventually(async () => { const t = await texts(page, '.fork-foods__name'); return t.length === 2 && t })
    check(found && found.every((t) => /chalote/i.test(t)), 'instant search ignores accents and case')
    await page.getByPlaceholder('Rechercher un aliment').fill('')

    // move "Citron" into "Légumes": move button, then the family
    const citron = page.locator('.fork-foods__row', { hasText: /^\s*Citron/ })
    await citron.getByRole('button', { name: 'Déplacer vers une autre famille' }).click()
    await page.locator('.v-bottom-sheet .v-list-item', { hasText: 'Légumes' }).click()
    const moved = await eventually(async () => (await page.locator('.fork-foods__group', { has: page.locator('.fork-foods__family', { hasText: 'Légumes' }) })
      .locator('.fork-foods__row', { hasText: /^\s*Citron/ }).count()) === 1)
    check(moved, 'food moved to another family in 2 taps')
    await page.locator('.fork-foods__row', { hasText: /^\s*Citron/ }).getByRole('button', { name: 'Déplacer vers une autre famille' }).click()
    await page.locator('.v-bottom-sheet .v-list-item', { hasText: 'Aucune famille' }).click()
    check(await eventually(async () => (await page.locator('.fork-foods__group', { hasText: 'Sans famille' }).locator('.fork-foods__row', { hasText: /^\s*Citron/ }).count()) === 1),
      'moved back to the top level')

    // quick edit in a bottom sheet: never in shopping
    await page.locator('.fork-foods__row', { hasText: /^\s*Citron/ }).click()
    const sheet = page.locator('.fork-food-sheet')
    await sheet.getByLabel('Jamais en courses').check()
    await sheet.getByRole('button', { name: 'Sauvegarder' }).click()
    check(await eventually(() => page.locator('.fork-foods__row', { hasText: /^\s*Citron/ }).getByText('Jamais en courses').isVisible()), 'quick edit saved without leaving the page')
    await page.locator('.fork-foods__row', { hasText: /^\s*Citron/ }).click()
    await sheet.getByLabel('Jamais en courses').uncheck()
    await sheet.getByRole('button', { name: 'Sauvegarder' }).click()
    await page.waitForTimeout(800)
  },

  // M3: "to sort" queue, one tap per aisle; a food created from the shopping list gets its aisle
  async tosort(page) {
    const created = await api(page, 'POST', '/api/food/', { name: 'Aaa navets flow' })
    check(created.status === 201, 'food created (as an import or a typed line would)')
    const food = (await api(page, 'GET', `/api/food/${created.data.id}/`)).data
    check(food.supermarket_category?.name === 'Fruits & légumes', `suggested aisle applied at creation (${food.supermarket_category?.name})`)
    await page.goto(base + '/foods/to-sort', { waitUntil: 'networkidle' })
    await eventually(() => page.locator('.fork-sort__food').isVisible())
    check((await page.locator('.fork-sort__food').innerText()).includes('Aaa navets flow'), 'new food waits in the queue')
    const left = await page.locator('text=/encore \\d+/').innerText()
    await page.locator('.fork-sort__aisle', { hasText: 'Épicerie salée' }).click()
    check(await eventually(async () => !(await page.locator('.fork-sort__food', { hasText: 'Aaa navets flow' }).count())), 'one tap files it and shows the next food')
    const after = (await api(page, 'GET', `/api/food/${food.id}/`)).data
    check(after.supermarket_category?.name === 'Épicerie salée', 'aisle saved')
    check(left !== (await page.locator('text=/encore \\d+|Tous les aliments/').first().innerText()), 'queue counter decreases')
    await api(page, 'DELETE', `/api/food/${food.id}/`)

    // not something to sort: a bad name, never bought, not a food at all
    const make = async (name) => (await api(page, 'POST', '/api/food/', { name })).data
    const bad = await make("d'Aaazeau + 30 ml"), never = await make('Aaazglace pilée'), junk = await make('Aaaznouveaux')
    await page.reload({ waitUntil: 'networkidle' })
    const showFood = async (name) => {
      for (let i = 0; i < 60; i++) {
        if ((await page.locator('.fork-sort__food').innerText().catch(() => '')).includes(name)) return true
        await page.getByRole('button', { name: 'Plus tard' }).click()
      }
      return false
    }
    check(await showFood("d'Aaazeau"), 'bad name in the queue')
    await page.getByRole('button', { name: 'Renommer' }).click()
    await page.locator('.v-dialog').getByLabel('Nouveau nom').fill('Aaazeau')
    await page.locator('.v-dialog').getByRole('button', { name: 'Sauvegarder' }).click()
    check(await eventually(async () => (await api(page, 'GET', `/api/food/${bad.id}/`)).data?.name === 'Aaazeau', 5000), 'renamed from the queue')
    check(await eventually(() => page.locator('.fork-sort__food', { hasText: 'Aaazeau' }).isVisible(), 3000), 'still to sort under its new name')

    check(await showFood('Aaazglace'), 'never-bought food in the queue')
    await page.getByRole('button', { name: 'Jamais en courses' }).click()
    check(await eventually(async () => (await api(page, 'GET', `/api/food/${never.id}/`)).data?.ignore_shopping === true, 5000), '"never in shopping" saved')
    check(await eventually(async () => !(await page.locator('.fork-sort__food', { hasText: 'Aaazglace' }).count()), 3000), 'and it leaves the queue')

    check(await showFood('Aaaznouveaux'), 'junk food in the queue')
    await page.getByRole('button', { name: 'Supprimer' }).click()
    const dlg = page.locator('.fork-sort__delete')
    check(await eventually(() => dlg.getByText("Aucune recette ne l'utilise.").isVisible(), 3000), 'delete asks first (no recipe uses it)')
    await shot(page, 'tosort-delete')
    await dlg.getByRole('button', { name: 'Supprimer' }).click()
    check(await eventually(async () => (await api(page, 'GET', `/api/food/${junk.id}/`)).status === 404, 5000), 'food deleted')
    for (const f of [bad, never]) await api(page, 'DELETE', `/api/food/${f.id}/`)
    const autos = (await api(page, 'GET', '/api/automation/?page_size=200')).data
    for (const a of (autos.results ?? autos).filter((x) => /aaaz/i.test(x.param_1 || ''))) await api(page, 'DELETE', `/api/automation/${a.id}/`)
  },

  // names left over by imports: one list, merge into the existing food or rename, all at once
  async foodnames(page) {
    const make = async (name) => (await api(page, 'POST', '/api/food/', { name })).data
    const huile = await make('Zzhuile')
    const created = [await make("à soupe d'zzhuile"), await make('à café zzcumin moulu'), await make('à soupe zzcumin moulu')]
    const kept = await make('de la zzcrème')
    await page.goto(base + '/foods', { waitUntil: 'networkidle' })
    check(await eventually(() => page.getByText(/4 noms d'aliments à corriger/).isVisible()), 'foods page announces the names to fix')
    await page.getByText(/noms d'aliments à corriger/).click()
    await eventually(() => page.locator('.fork-names__row').first().isVisible())
    const rows = page.locator('.fork-names__row', { hasText: /zz/i })
    check((await rows.count()) === 4, 'the four names are listed')
    // a name to keep as it is
    await page.locator('.fork-names__row', { hasText: 'de la zzcrème' }).getByRole('button', { name: 'Options' }).click()
    await page.getByText('Garder ce nom').click()
    check(await eventually(async () => (await rows.count()) === 3, 4000), '"keep this name" removes it from the list')
    await page.reload({ waitUntil: 'networkidle' })
    await eventually(() => page.locator('.fork-names__row').first().isVisible())
    check((await rows.count()) === 3, 'and it stays out after a reload')
    check(await page.locator('.fork-names__row', { hasText: "à soupe d'zzhuile" }).getByText('fusion avec « Zzhuile »').isVisible(), 'merge into the existing food proposed')
    await shot(page, 'food-names')
    await page.getByRole('button', { name: /Tout corriger/ }).click()
    await page.locator('.v-dialog').getByRole('button', { name: 'Corriger' }).click()
    check(await eventually(() => page.getByText('Aucun nom à corriger.').isVisible(), 15000), 'all fixed')
    const status = async (f) => (await api(page, 'GET', `/api/food/${f.id}/`)).status
    check((await status(created[0])) === 404 && (await status(huile)) === 200, '"à soupe d\'zzhuile" merged into Zzhuile')
    const cumin = (await api(page, 'GET', '/api/food/?query=zzcumin&page_size=10')).data.results
    check(cumin.length === 1 && cumin[0].name === 'zzcumin moulu', `one "zzcumin moulu" left (${cumin.map((f) => f.name).join(', ')})`)
    const autos = (await api(page, 'GET', '/api/automation/?page_size=200')).data
    const aliases = (autos.results ?? autos).filter((x) => x.type === 'FOOD_ALIAS' && /zz/i.test(x.param_1 || ''))
    check(aliases.length === 3, `old names kept as aliases (${aliases.length})`)
    for (const a of aliases) await api(page, 'DELETE', `/api/automation/${a.id}/`)
    for (const f of [huile, kept, ...cumin]) await api(page, 'DELETE', `/api/food/${f.id}/`)
  },

  // M3: generic aisle order, set once, followed by the shopping list
  async aisles(page) {
    await page.goto(base + '/foods/aisles', { waitUntil: 'networkidle' })
    await eventually(() => page.locator('.fork-aisles__row').first().isVisible())
    const before = await texts(page, '.fork-aisles__name')
    check(before[0].includes('légumes') && before[before.length - 1].length > 0, 'generic order starts with fruits and vegetables')
    await page.getByRole('button', { name: /^Descendre/ }).first().click()
    const changed = await eventually(async () => { const t = await texts(page, '.fork-aisles__name'); return t[1] === before[0] && t })
    check(changed, 'an aisle moves down')
    await page.reload({ waitUntil: 'networkidle' })
    check((await texts(page, '.fork-aisles__name'))[1] === before[0], 'order saved')
    await page.locator('.fork-aisles__row').nth(1).getByRole('button', { name: /^Monter/ }).click()
    check(await eventually(async () => (await texts(page, '.fork-aisles__name'))[0] === before[0]), 'order restored')
    await page.waitForTimeout(500)

    await page.goto(base + '/shopping', { waitUntil: 'networkidle' })
    await eventually(() => page.locator('.fork-shopping__aisle').first().isVisible())
    const aisles = (await texts(page, '.fork-shopping__aisle')).filter((t) => !/PANIER/.test(t))
    const rank = (t) => before.findIndex((b) => b.split('\n')[0].toUpperCase().trim() === t.trim())
    const ranks = aisles.map(rank)
    check(ranks.every((r, i) => r >= 0 && (i === 0 || r > ranks[i - 1])), `shopping list follows the generic order (${aisles.join(' / ')})`)
  },

  // M3: probable duplicates, merge with preview, FOOD_ALIAS created
  async duplicates(page) {
    const a = (await api(page, 'POST', '/api/food/', { name: 'Zzflow poireau' })).data
    const b = (await api(page, 'POST', '/api/food/', { name: 'zzflow poireaux' })).data
    await page.goto(base + '/foods/duplicates', { waitUntil: 'networkidle' })
    const card = page.locator('.v-card', { hasText: /zzflow poireaux/i }).filter({ hasText: /Zzflow poireau\b/ })
    check(await eventually(() => card.first().isVisible()), 'plural duplicate proposed')
    check((await card.first().innerText()).includes('À rattacher à'), 'merge preview shown (recipes and items)')
    await card.first().getByRole('button', { name: 'Fusionner' }).click()
    await page.locator('.v-dialog').getByRole('button', { name: 'Fusionner' }).click()
    check(await eventually(async () => !(await card.count()), 5000), 'pair gone after the merge')
    const left = [(await api(page, 'GET', `/api/food/${a.id}/`)).status, (await api(page, 'GET', `/api/food/${b.id}/`)).status]
    check(left.filter((s) => s === 200).length === 1, 'one food left')
    const autos = (await api(page, 'GET', '/api/automation/?page_size=100')).data
    const alias = (autos.results ?? autos).find((x) => x.type === 'FOOD_ALIAS' && /zzflow/i.test(x.param_1 || ''))
    check(alias && /zzflow/i.test(alias.param_2), `FOOD_ALIAS created (${alias?.param_1} -> ${alias?.param_2})`)
    if (alias) await api(page, 'DELETE', `/api/automation/${alias.id}/`)
    for (const f of [a, b]) await api(page, 'DELETE', `/api/food/${f.id}/`)

    // neither name fits: both merged under a third one
    const c = (await api(page, 'POST', '/api/food/', { name: 'zzognion' })).data
    const d = (await api(page, 'POST', '/api/food/', { name: 'Zzognions' })).data
    await page.reload({ waitUntil: 'networkidle' })
    const pair = page.locator('.v-card', { hasText: /zzognion/i })
    check(await eventually(() => pair.first().isVisible()), 'second pair proposed')
    await pair.first().getByRole('button', { name: 'Autre nom…' }).click()
    await page.locator('.v-dialog').getByLabel('Nouveau nom').fill('Zzoignon')
    await shot(page, 'duplicates-other-name')
    await page.locator('.v-dialog').getByRole('button', { name: 'Fusionner' }).click()
    check(await eventually(async () => !(await pair.count()), 6000), 'pair gone')
    const now = (await api(page, 'GET', '/api/food/?query=zzo&page_size=10')).data.results
    check(now.length === 1 && now[0].name === 'Zzoignon', `one food under the new name (${now.map((f) => f.name).join(', ')})`)
    const autos2 = (await api(page, 'GET', '/api/automation/?page_size=200')).data
    const aliases = (autos2.results ?? autos2).filter((x) => x.type === 'FOOD_ALIAS' && /zzognion/i.test(x.param_1 || ''))
    check(aliases.length === 2 && aliases.every((x) => x.param_2 === 'Zzoignon'), `both old names point to it (${aliases.map((x) => x.param_1 + '->' + x.param_2).join(', ')})`)
    for (const x of aliases) await api(page, 'DELETE', `/api/automation/${x.id}/`)
    for (const f of now) await api(page, 'DELETE', `/api/food/${f.id}/`)

    // merge everything: asks first (the demo duplicates are kept: cancelled)
    await page.getByRole('button', { name: /Tout fusionner/ }).click()
    check(await eventually(() => page.locator('.v-dialog').getByText(/Fusionner \d+ doublons? \?/).isVisible(), 3000), '"merge all" asks first, with the count')
    await page.locator('.v-dialog').getByRole('button', { name: 'Annuler' }).click()
  },

  // an imported photo can be framed before saving (the server downloads and crops it at save time)
  async importcrop(page) {
    const jsonld = JSON.stringify({ '@context': 'https://schema.org', '@type': 'Recipe', name: 'Flow crop test', image: base + '/static/assets/logo_color_512.png',
      recipeIngredient: ['1 citron'], recipeInstructions: [{ '@type': 'HowToStep', text: 'Presser.' }] })
    await page.goto(base + '/recipe/import', { waitUntil: 'networkidle' })
    await page.locator('.v-card', { hasText: 'JSON/HTML' }).first().click()
    await page.getByRole('button', { name: 'Suivant' }).first().click()
    await page.locator('textarea').first().fill(`<script type="application/ld+json">${jsonld}</` + 'script>')
    await page.getByRole('button', { name: 'Chargement' }).click()
    const crop = page.getByRole('button', { name: 'Recadrer' })
    for (let i = 0; i < 6 && !(await crop.isVisible().catch(() => false)); i++) {
      await page.waitForTimeout(800)
      if (await crop.isVisible().catch(() => false)) break
      await page.locator('button:visible', { hasText: /^\s*Suivant\s*$/ }).last().click().catch(() => {})
    }
    check(await eventually(() => crop.isVisible(), 8000), 'the image step offers to crop the imported photo')
    await crop.click()
    await eventually(() => page.locator('.fork-crop__img').isVisible(), 5000)
    await page.locator('.fork-crop').getByRole('button', { name: '4:3' }).click()
    await page.locator('.fork-crop').getByRole('button', { name: 'Appliquer' }).click()
    check(await eventually(() => page.locator('.fork-import-crop').isVisible(), 3000), 'framed photo previewed in the import')
    check(await page.getByRole('button', { name: 'Recadrer à nouveau' }).isVisible(), 'and it can be framed again')
  },

  // M3 + M4: URL import review: French recognition, closest existing food proposed; choosing it creates a FOOD_ALIAS
  async importreview(page) {
    const jsonld = JSON.stringify({ '@context': 'https://schema.org', '@type': 'Recipe', name: 'Flow import test',
      recipeIngredient: ['3 citrons', '1 oignon rouge émincé', "2 c. à soupe d'huile d'olive"], recipeInstructions: [{ '@type': 'HowToStep', text: 'Mélanger.' }] })
    await page.goto(base + '/recipe/import', { waitUntil: 'networkidle' })
    await page.locator('.v-card', { hasText: 'JSON/HTML' }).first().click()
    await page.getByRole('button', { name: 'Suivant' }).first().click()
    await page.locator('textarea').first().fill(`<script type="application/ld+json">${jsonld}</` + 'script>')
    await page.getByRole('button', { name: 'Chargement' }).click()
    const card = page.locator('.fork-matches')
    // walk the wizard (image, keywords...) up to the step editor
    for (let i = 0; i < 5 && !(await card.isVisible()); i++) {
      await page.waitForTimeout(800)
      if (await card.isVisible()) break
      await page.locator('button:visible', { hasText: /^\s*Suivant\s*$/ }).last().click().catch(() => {})
    }
    check(await eventually(() => card.isVisible(), 10000), 'unknown foods listed in the import review')
    const chips = await texts(page, '.v-stepper-window .v-chip')
    check(chips.some((c) => c.trim() === 'Citron'), 'French plural brought back to the existing food at import')
    check(chips.some((c) => c.trim() === 'c. à soupe') && chips.some((c) => c.trim().toLowerCase() === "huile d'olive"), 'French unit and article handled at import')
    const row = card.locator('.fork-matches__row', { hasText: 'oignon rouge' })
    check(await row.isVisible() && /Oignon/.test(await row.innerText()), 'closest existing food proposed (oignon rouge -> Oignon)')
    const proposed = (await row.locator('strong').innerText()).trim()
    await row.getByRole('button', { name: "Utiliser l'existant" }).click()
    check(await eventually(async () => !(await card.locator('.fork-matches__row', { hasText: 'oignon rouge' }).count())), 'choice applied')
    const after = await texts(page, '.v-stepper-window .v-chip')
    check(after.some((c) => c.trim() === proposed) && !after.some((c) => c.trim() === 'oignon rouge'), 'ingredient now uses the existing food')
    const autos = (await api(page, 'GET', '/api/automation/?page_size=100')).data
    const alias = (autos.results ?? autos).find((x) => x.type === 'FOOD_ALIAS' && x.param_1 === 'oignon rouge')
    check(alias && alias.param_2 === proposed, `FOOD_ALIAS oignon rouge -> ${proposed} created`)
    if (alias) await api(page, 'DELETE', `/api/automation/${alias.id}/`)
  },

  // M4: recipe wizard in 4 screens, live French recognition, draft kept, single ingredient list; edit with the same screens
  async wizard(page) {
    await page.goto(base + '/recipe/new', { waitUntil: 'networkidle' })
    await page.evaluate(() => localStorage.removeItem('fork-recipe-draft-new'))
    await page.reload({ waitUntil: 'networkidle' })
    check(!(await page.locator('.fork-bottom-nav').count()), 'wizard is full screen')
    await page.getByLabel('Nom de la recette').fill('Flow poêlée test')
    await page.getByRole('button', { name: 'Une portion de plus' }).click()
    await page.getByRole('button', { name: 'Suivant' }).click()
    check(await page.getByText('2 sur 4').isVisible(), 'screen 2: ingredients')

    await page.getByLabel('Ingrédients, un par ligne').fill("2 courgettes coupées en dés\n1 c. à soupe d'huile d'olive\n1 gousse d'ail\n1 citron")
    const preview = page.locator('.fork-wizard__preview-row')
    check(await eventually(async () => (await preview.count()) === 4), 'live recognition while typing')
    check((await preview.first().innerText()).includes('Courgette'), 'plural brought back to the existing food')
    await shot(page, 'wizard-2-recognition')
    await page.getByRole('button', { name: 'Ajouter 4 ingrédients' }).click()
    const rows = page.locator('.fork-wizard__ingredient')
    check(await eventually(async () => (await rows.count()) === 4), 'pasted lines added')
    check((await rows.nth(0).innerText()).includes('coupées en dés'), 'precision kept as a note')
    check((await rows.nth(1).innerText()).includes('c. à soupe'), 'French unit recognised')
    await shot(page, 'wizard-2-ingredients')
    await rows.nth(3).click()
    await page.locator('.fork-line-sheet').getByLabel('Quantité').fill('2')
    await shot(page, 'wizard-2-line-sheet')
    await page.locator('.fork-line-sheet').getByRole('button', { name: 'Appliquer' }).click()
    check(await eventually(async () => (await rows.nth(3).innerText()).startsWith('2')), 'line corrected in a bottom sheet')
    await page.getByRole('button', { name: 'Précédent' }).click()
    check(await page.getByLabel('Nom de la recette').inputValue() === 'Flow poêlée test', 'going back keeps what was typed')
    await page.getByRole('button', { name: 'Suivant' }).click()
    check((await rows.count()) === 4, 'forward again keeps the ingredients')
    await page.getByRole('button', { name: 'Suivant' }).click()

    const steps = page.locator('.fork-wizard__step textarea:not(.v-textarea__sizer)')
    await steps.nth(0).fill('Couper les légumes.')
    await page.getByRole('button', { name: 'Ajouter une étape' }).click()
    await steps.nth(1).fill("Faire revenir dans l'huile.")
    await page.getByRole('button', { name: 'Ajouter une étape' }).click()
    await steps.nth(2).fill('Servir.')
    await page.getByRole('button', { name: "Monter l'étape 3" }).click()
    check(await steps.nth(1).inputValue() === 'Servir.', 'steps can be reordered')
    await page.getByRole('button', { name: "Descendre l'étape 2" }).click()
    await shot(page, 'wizard-3-steps')
    await page.getByRole('button', { name: 'Suivant' }).click()

    await page.getByLabel('Préparation (min)').fill('10')
    await page.getByLabel('Cuisson (min)').fill('15')
    await page.locator('.v-combobox input').fill('Flowtest')
    await page.keyboard.press('Enter')
    await page.locator('input[type=file]').setInputFiles(join(ROOT, 'mediafiles/recipes/seed_4.jpg'))
    check(await eventually(() => page.locator('.fork-wizard__photo').isVisible()), 'photo picked from the gallery')
    await page.keyboard.press('Escape')
    await shot(page, 'wizard-4-details')
    await page.waitForTimeout(600) // draft saved after 300 ms
    await page.reload({ waitUntil: 'networkidle' })
    check(await page.getByText('Votre brouillon a été restauré.').isVisible(), 'draft restored after leaving the page')
    check(await page.getByLabel('Préparation (min)').inputValue() === '10', 'draft keeps the screen and the values')
    await page.locator('input[type=file]').setInputFiles(join(ROOT, 'mediafiles/recipes/seed_4.jpg')) // a file cannot be kept in a draft
    await page.getByRole('button', { name: 'Sauvegarder' }).click()
    await page.waitForURL(/\/recipe\/\d+$/, { timeout: 15000 })
    const id = Number(page.url().split('/').pop())
    const recipe = (await api(page, 'GET', `/api/recipe/${id}/`)).data
    check(recipe.name === 'Flow poêlée test' && recipe.servings === 3, 'saved with name and servings')
    check(recipe.steps.length === 3 && recipe.steps[0].ingredients.length === 4 && recipe.steps.slice(1).every((s) => s.ingredients.length === 0),
      'single ingredient list stored in the first step')
    check(recipe.steps.map((s) => s.instruction).join('|') === "Couper les légumes.|Faire revenir dans l'huile.|Servir.", 'steps in order')
    const foods = recipe.steps[0].ingredients.map((i) => i.food.name)
    check(foods.includes('Courgette') && foods.includes("Huile d'olive") && foods.includes('Ail') && foods.includes('Citron'), `existing foods used (${foods.join(', ')})`)
    check(recipe.working_time === 10 && recipe.waiting_time === 15 && recipe.keywords.some((k) => k.name === 'Flowtest'), 'details saved')
    check(!!recipe.image, 'photo uploaded')
    check(await eventually(() => page.locator('.fork-ingredients__row').first().isVisible()) && !(await page.locator('.fork-recipe__group').count()),
      'recipe view shows one list')

    // edit with the same screens
    await page.goto(`${base}/recipe/${id}/edit`, { waitUntil: 'networkidle' })
    await eventually(async () => (await page.getByLabel('Nom de la recette').inputValue()) === 'Flow poêlée test')
    await page.getByLabel('Nom de la recette').fill('Flow poêlée modifiée')
    for (let i = 0; i < 3; i++) await page.getByRole('button', { name: 'Suivant' }).click()
    // frame the stored photo as a square: cropped by the server after the save
    await page.getByRole('button', { name: 'Recadrer' }).click()
    const cropper = page.locator('.fork-crop')
    await eventually(() => cropper.locator('.fork-crop__img').isVisible(), 5000)
    await cropper.getByRole('button', { name: '1:1' }).click()
    await page.waitForTimeout(300)
    const frameBox = await cropper.locator('.fork-crop__frame').boundingBox()
    await page.mouse.move(frameBox.x + frameBox.width / 2, frameBox.y + frameBox.height / 2)
    await page.mouse.down()
    await page.mouse.move(frameBox.x + frameBox.width / 2 - 40, frameBox.y + frameBox.height / 2, { steps: 5 })
    await page.mouse.up()
    await shot(page, 'photo-crop')
    await cropper.getByRole('button', { name: 'Appliquer' }).click()
    check(await eventually(() => page.getByRole('img', { name: 'Photo recadrée' }).isVisible(), 3000), 'framed photo previewed before saving')
    await page.getByRole('button', { name: 'Sauvegarder' }).click()
    await page.waitForURL(new RegExp(`/recipe/${id}$`), { timeout: 15000 })
    const edited = (await api(page, 'GET', `/api/recipe/${id}/`)).data
    check(edited.name === 'Flow poêlée modifiée', 'existing recipe edited')
    const size = await page.evaluate((src) => new Promise((resolve) => { const i = new Image(); i.onload = () => resolve([i.naturalWidth, i.naturalHeight]); i.onerror = () => resolve([0, 0]); i.src = src }), edited.image)
    check(edited.image !== recipe.image && size[0] > 0 && Math.abs(size[0] - size[1]) <= 1, `photo cropped to a square by the server (${size.join('×')})`)
    check(edited.steps[0].ingredients.map((i) => i.id).join() === recipe.steps[0].ingredients.map((i) => i.id).join(), 'ingredients updated in place, not duplicated')

    // a recipe split by step keeps its split
    const curry = (await api(page, 'GET', '/api/recipe/?query=curry&page_size=1')).data.results[0]
    const before = (await api(page, 'GET', `/api/recipe/${curry.id}/`)).data
    await page.goto(`${base}/recipe/${curry.id}/edit`, { waitUntil: 'networkidle' })
    await page.evaluate((cid) => localStorage.removeItem(`fork-recipe-draft-${cid}`), curry.id)
    await page.reload({ waitUntil: 'networkidle' })
    await eventually(async () => (await page.getByLabel('Nom de la recette').inputValue()).length > 0)
    await page.getByRole('button', { name: 'Suivant' }).click()
    check(await eventually(async () => (await page.locator('.fork-wizard__group').count()) === 3), 'split recipe shows its ingredients by step')
    for (let i = 0; i < 2; i++) await page.getByRole('button', { name: 'Suivant' }).click()
    await page.getByRole('button', { name: 'Sauvegarder' }).click()
    await page.waitForURL(new RegExp(`/recipe/${curry.id}$`), { timeout: 15000 })
    const after = (await api(page, 'GET', `/api/recipe/${curry.id}/`)).data
    check(after.steps.map((s) => s.ingredients.length).join() === before.steps.map((s) => s.ingredients.length).join(), 'split kept after saving')

    await api(page, 'DELETE', `/api/recipe/${id}/`)
    const kw = (await api(page, 'GET', '/api/keyword/?query=Flowtest')).data
    for (const k of kw.results ?? []) await api(page, 'DELETE', `/api/keyword/${k.id}/`)
  },
}

async function main() {
  const sid = sessionId()
  const { executablePath, args } = await resolveBrowser()
  const browser = await pw.launch({ executablePath, args, headless: true })
  const host = new URL(base).hostname
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true, locale: 'fr-FR', timezoneId: 'Europe/Paris', reducedMotion: 'reduce' })
  const warm = await context.newPage()
  await warm.goto(base + '/accounts/login/', { waitUntil: 'domcontentloaded' }).catch(() => {})
  await warm.close()
  await context.addCookies([{ name: 'sessionid', value: sid, domain: host, path: '/' }])

  const page = await context.newPage()
  page.setDefaultTimeout(10000)
  const errors = []
  page.on('pageerror', (e) => errors.push(String(e)))
  page.on('response', (r) => { if (r.status() >= 400 && r.url().includes('/api/')) console.log(`    [info] HTTP ${r.status()} ${r.request().method()} ${r.url()}`) })
  page.on('console', (m) => { if (m.type() === 'error') console.log(`    [info] console: ${m.text().slice(0, 200)}`) })
  await page.goto(base + '/', { waitUntil: 'domcontentloaded' })
  const recipes = (await api(page, 'GET', '/api/recipe/?query=curry&page_size=1')).data
  const ctx = { curry: recipes.results?.[0]?.id }

  for (const [name, flow] of Object.entries(FLOWS)) {
    if (only && !only.includes(name)) continue
    current = { name, checks: [] }
    results.push(current)
    console.log(`== ${name}`)
    try {
      await flow(page, ctx)
    } catch (e) {
      check(false, `flow crashed: ${String(e).split('\n')[0]}`)
      await page.screenshot({ path: join(ROOT, `.fork/flow-${name}.png`) }).catch(() => {})
      console.log(`    [info] screenshot: .fork/flow-${name}.png; ${String(e).split('\n').slice(1, 4).join(' ')}`)
    }
  }
  if (errors.length) {
    results.push({ name: 'js-errors', checks: errors.map((e) => ({ ok: false, what: e })) })
    errors.forEach((e) => console.log(`    [FAIL] JS error: ${e}`))
  }
  await browser.close()

  const failed = results.flatMap((r) => r.checks.filter((c) => !c.ok))
  const total = results.reduce((s, r) => s + r.checks.length, 0)
  console.log(failed.length ? `FLOWS: FAIL (${failed.length}/${total})` : `FLOWS: OK (${total} checks)`)
  process.exit(failed.length ? 1 : 0)
}

main().catch((e) => { console.error(e); process.exit(1) })
