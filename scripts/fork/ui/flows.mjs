#!/usr/bin/env node
// Functional journey checks for the fork (headless, phone viewport): they click through the screens like a user and
// assert what the acceptance criteria promise. Every flow restores the data it changed.
//
// Usage (dev server running, see scripts/fork/serve.sh):
//   node scripts/fork/ui/flows.mjs [--base http://127.0.0.1:8000] [--only p1,p2]
// Exit code 1 if a check fails. Run by `verify.sh --ui` after the screenshots.

import { execFileSync } from 'node:child_process'
import { existsSync } from 'node:fs'
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

// ---- flows ----
const FLOWS = {
  // P1: recipes home with search, filter sheet and shortcuts
  async p1(page) {
    await page.goto(base + '/', { waitUntil: 'networkidle' })
    check(await page.getByPlaceholder('Rechercher une recette').isVisible(), 'search field visible on the home screen')
    const all = await eventually(async () => (await texts(page, '.fork-recipe-card__title')).length >= 4 && texts(page, '.fork-recipe-card__title'))
    check(all && all.length >= 4, `photo cards listed (${all?.length})`)

    await page.getByPlaceholder('Rechercher une recette').fill('curry')
    const found = await eventually(async () => { const t = await texts(page, '.fork-recipe-card__title'); return t.length === 1 && t })
    check(found && found[0].includes('Curry'), 'text search narrows the list')
    await page.getByPlaceholder('Rechercher une recette').fill('')

    await page.getByRole('button', { name: 'Filtres' }).click()
    await page.locator('.v-bottom-sheet .v-chip', { hasText: '≤ 30 min' }).click()
    const quick = await eventually(async () => { const t = await texts(page, '.fork-recipe-card__title'); return t.length === 3 && t })
    check(quick && !quick.some((t) => t.includes('Curry')), 'total time ≤ 30 min drops the 35 min curry')
    await page.locator('.v-bottom-sheet .v-chip', { hasText: '≤ 30 min' }).click() // off again

    await page.locator('.v-bottom-sheet .v-autocomplete input').first().fill('Courg')
    await page.locator('.v-overlay .v-list-item', { hasText: 'Courgette' }).first().click()
    await page.keyboard.press('Escape')
    const ranked = await eventually(async () => { const t = await texts(page, '.fork-recipe-card__title'); return t.length === 1 && t })
    check(ranked && ranked[0].includes('Poêlée'), 'ingredient on hand lists the recipes using it')
    check(await page.locator('.fork-recipe-card', { hasText: '1/4 ingrédients' }).count() === 1, 'card shows how many ingredients are on hand')
    await page.goto(base + '/', { waitUntil: 'networkidle' }) // module state survives SPA navigation only

    await page.locator('.fork-home__shortcuts .v-chip', { hasText: 'Pas faites depuis longtemps' }).click()
    const forgotten = await eventually(async () => { const t = await texts(page, '.fork-recipe-card__title'); return t.length >= 4 && t })
    check(forgotten && forgotten.length >= 4, 'shortcut "pas faites depuis longtemps" lists recipes')
    await page.locator('.fork-home__shortcuts .v-chip', { hasText: 'Récentes' }).click()
    await page.waitForTimeout(800)
    check(!(await page.locator('.v-alert--variant-tonal.text-error').count()), 'shortcut "récentes" loads without error')
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

  // M3: food tree, move in 2 taps, quick edit, "no aisle" filter
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
  },

  // M3: URL import review proposes the closest existing food; choosing it creates a FOOD_ALIAS
  async importreview(page) {
    const jsonld = JSON.stringify({ '@context': 'https://schema.org', '@type': 'Recipe', name: 'Flow import test',
      recipeIngredient: ['1 Citrons', '100 g Gingembre'], recipeInstructions: [{ '@type': 'HowToStep', text: 'Mélanger.' }] })
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
    const text = await card.innerText()
    check(/Citrons\s*\S*\s*Citron/.test(text.replace(/\n/g, ' ')), 'closest existing food proposed (Citrons -> Citron)')
    await card.locator('.fork-matches__row', { hasText: 'Citrons' }).getByRole('button', { name: "Utiliser l'existant" }).click()
    check(await eventually(async () => !(await card.locator('.fork-matches__row', { hasText: 'Citrons' }).count())), 'choice applied')
    const chips = await texts(page, '.v-stepper-window .v-chip')
    check(chips.some((c) => c.trim() === 'Citron') && !chips.some((c) => c.trim() === 'Citrons'), 'ingredient now uses the existing food')
    const autos = (await api(page, 'GET', '/api/automation/?page_size=100')).data
    const alias = (autos.results ?? autos).find((x) => x.type === 'FOOD_ALIAS' && x.param_1 === 'Citrons')
    check(alias && alias.param_2 === 'Citron', 'FOOD_ALIAS Citrons -> Citron created')
    if (alias) await api(page, 'DELETE', `/api/automation/${alias.id}/`)
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
