#!/usr/bin/env node
// Headless UI checks for the fork: screenshots + deterministic mobile checks.
//
// Usage (from repo root, dev server running, see scripts/fork/serve.sh):
//   node scripts/fork/ui/screenshots.mjs --label m1 [--base http://127.0.0.1:8000] [--only start,shopping]
//                                        [--viewports mobile,desktop] [--publish]
//
// Output: .fork/screens/<label>/<route>-<viewport>.jpg + report.json + report.md
// --publish also copies the mobile/desktop JPEGs to docs/fork/screens/<label>/ (committed, linked from the PR).
//
// Exit code 1 if a route marked "strict" in routes.json fails a check
// (horizontal overflow, JS error, console error, HTTP >= 400 on the document).

import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync } from 'node:fs'
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

const label = String(arg('label', 'adhoc'))
const base = String(arg('base', process.env.FORK_BASE_URL || 'http://127.0.0.1:8000')).replace(/\/$/, '')
const only = arg('only') ? String(arg('only')).split(',') : null
const publish = Boolean(arg('publish', false))
const config = JSON.parse(readFileSync(join(HERE, 'routes.json'), 'utf8'))
const viewportNames = arg('viewports') ? String(arg('viewports')).split(',') : ['mobile', 'small', 'desktop']

async function resolveBrowser() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) {
    return { executablePath: process.env.CHROME_PATH, args: [] }
  }
  try {
    const p = pw.executablePath()
    if (p && existsSync(p)) return { executablePath: p, args: [] }
  } catch { /* no Playwright-managed browser installed */ }
  // Fallback: a Chromium build shipped inside an npm package (works when the
  // Playwright CDN is not reachable, e.g. a restricted cloud network allowlist).
  const { default: sparticuz } = await import('@sparticuz/chromium')
  // --single-process (meant for AWS Lambda) kills the whole browser when a context closes.
  const args = sparticuz.args.filter((a) => a !== '--single-process')
  return { executablePath: await sparticuz.executablePath(), args }
}

function sessionId() {
  const python = existsSync(join(ROOT, '.venv/bin/python')) ? join(ROOT, '.venv/bin/python') : 'python3'
  return execFileSync(python, [join(ROOT, 'scripts/fork/dev_session.py')], {
    cwd: ROOT,
    env: { ...process.env, DJANGO_SETTINGS_MODULE: 'recipes.settings', DEBUG: '1' },
    stdio: ['ignore', 'pipe', 'ignore'],
  }).toString().trim().split('\n').pop()
}

async function firstId(sid, model) {
  const r = await fetch(`${base}/api/${model}/?page_size=1`, { headers: { Cookie: `sessionid=${sid}` } })
  if (!r.ok) throw new Error(`GET /api/${model}/ -> ${r.status}`)
  const data = await r.json()
  return data.results?.[0]?.id
}

// Noise from the headless environment, not from the app.
const IGNORED_CONSOLE = [/favicon/i, /service worker/i, /workbox/i, /Download the Vue Devtools/i, /Wake Lock/i]

async function checkPage(context, route, path, vpName, outDir) {
  const page = await context.newPage()
  const consoleErrors = []
  const pageErrors = []
  page.on('console', (m) => {
    if (m.type() === 'error' && !IGNORED_CONSOLE.some((re) => re.test(m.text()))) consoleErrors.push(m.text().slice(0, 300))
  })
  page.on('pageerror', (e) => {
    if (!IGNORED_CONSOLE.some((re) => re.test(String(e)))) pageErrors.push(String(e).slice(0, 300))
  })

  let status = 0
  try {
    const resp = await page.goto(base + path, { waitUntil: 'networkidle', timeout: 45000 })
    status = resp ? resp.status() : 0
  } catch (e) {
    pageErrors.push(`navigation: ${String(e).slice(0, 200)}`)
  }
  await page.waitForTimeout(800) // let transitions/animations settle

  const metrics = await page.evaluate((isMobile) => {
    const doc = document.documentElement
    const overflowPx = Math.max(0, doc.scrollWidth - window.innerWidth)
    const offenders = []
    if (overflowPx > 1) {
      for (const el of document.querySelectorAll('body *')) {
        const r = el.getBoundingClientRect()
        if (r.right > window.innerWidth + 1 && r.width > 0 && getComputedStyle(el).position !== 'fixed') {
          offenders.push(`${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}.${[...el.classList].slice(0, 3).join('.')}`)
          if (offenders.length >= 5) break
        }
      }
    }
    const small = []
    if (isMobile) {
      for (const el of document.querySelectorAll('a, button, [role="button"], input:not([type="hidden"]), select, textarea, .v-btn')) {
        const r = el.getBoundingClientRect()
        const visible = r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'
        if (visible && (r.width < 40 || r.height < 40)) {
          small.push(`${el.tagName.toLowerCase()} "${(el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 30)}" ${Math.round(r.width)}x${Math.round(r.height)}`)
        }
      }
    }
    return { overflowPx, offenders, smallTargets: small.length, smallTargetSamples: small.slice(0, 5), title: document.title }
  }, vpName !== 'desktop')

  const file = join(outDir, `${route.name}-${vpName}.jpg`)
  await page.screenshot({ path: file, fullPage: true, type: 'jpeg', quality: 70 })
  await page.close()

  const problems = []
  if (status >= 400) problems.push(`HTTP ${status}`)
  if (metrics.overflowPx > 1) problems.push(`horizontal overflow ${metrics.overflowPx}px (${metrics.offenders.join(', ')})`)
  if (pageErrors.length) problems.push(`${pageErrors.length} JS error(s): ${pageErrors[0]}`)
  if (consoleErrors.length) problems.push(`${consoleErrors.length} console error(s): ${consoleErrors[0]}`)
  return { route: route.name, path, viewport: vpName, status, strict: Boolean(route.strict), file, problems, ...metrics }
}

async function main() {
  const outDir = join(ROOT, '.fork/screens', label)
  mkdirSync(outDir, { recursive: true })

  const sid = sessionId()
  const ids = { recipe: await firstId(sid, 'recipe'), food: await firstId(sid, 'food') }
  const { executablePath, args } = await resolveBrowser()
  const browser = await pw.launch({ executablePath, args, headless: true })
  const host = new URL(base).hostname

  const results = []
  for (const vpName of viewportNames) {
    const vp = config.viewports[vpName]
    if (!vp) throw new Error(`unknown viewport ${vpName}`)
    const { width, height, ...rest } = vp
    for (const route of config.routes) {
      if (only && !only.includes(route.name)) continue
      const context = await browser.newContext({ viewport: { width, height }, ...rest, locale: 'fr-FR' })
      if (route.auth !== false) {
        await context.addCookies([{ name: 'sessionid', value: sid, domain: host, path: '/' }])
      }
      const path = route.path.replace(/\{(\w+)\}/g, (_, k) => ids[k] ?? '0')
      results.push(await checkPage(context, route, path, vpName, outDir))
      await context.close()
    }
  }
  await browser.close()

  const strictFailures = results.filter((r) => r.strict && r.problems.length)
  const lines = [`# UI check: ${label}`, '', `Base: ${base}`, '',
    '| route | viewport | strict | problems | small tap targets |', '|---|---|---|---|---|',
    ...results.map((r) => `| ${r.route} | ${r.viewport} | ${r.strict ? 'yes' : ''} | ${r.problems.join('; ') || 'OK'} | ${r.smallTargets ?? ''} |`),
    '', strictFailures.length ? `RESULT: FAIL (${strictFailures.length} strict check(s) failed)` : 'RESULT: OK']
  writeFileSync(join(outDir, 'report.json'), JSON.stringify(results, null, 2))
  writeFileSync(join(outDir, 'report.md'), lines.join('\n') + '\n')

  if (publish) {
    const pubDir = join(ROOT, 'docs/fork/screens', label)
    mkdirSync(pubDir, { recursive: true })
    for (const r of results) if (r.viewport !== 'small') copyFileSync(r.file, join(pubDir, `${r.route}-${r.viewport}.jpg`))
    copyFileSync(join(outDir, 'report.md'), join(pubDir, 'report.md'))
  }

  console.log(lines.join('\n'))
  console.log(`\nScreenshots: ${outDir}`)
  // exitCode (not process.exit) so piped stdout is flushed before the process ends
  process.exitCode = strictFailures.length ? 1 : 0
}

main().catch((e) => {
  console.error('UI CHECK ERROR:', e)
  process.exitCode = 2
})
