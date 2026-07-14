import { chromium } from 'playwright'

const BASE = 'http://localhost:5173'

async function setupPage(page) {
  await page.goto(`${BASE}/login`)
  await page.evaluate(() => {
    localStorage.setItem('rsod_token', 'dev-preview')
    localStorage.setItem('rsod_user', JSON.stringify({ username: 'dev', nickname: 'Dev' }))
  })
  await page.goto(`${BASE}/chat`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.feixun-page', { timeout: 10000 })
  await page.waitForTimeout(800)
  await page.evaluate(async () => {
    const { useFeixunWindowsStore } = await import('/src/stores/feixunWindows.js')
    window.__FEIXUN_TEST_STORE__ = useFeixunWindowsStore()
  })
}

async function tryDrag(page, label, x, y) {
  const before = await page.evaluate(() =>
    window.__FEIXUN_TEST_STORE__.windows.map((w) => ({ ...w.offset })),
  )
  await page.mouse.move(x, y)
  await page.mouse.down()
  await page.mouse.move(x + 100, y + 60, { steps: 10 })
  await page.mouse.up()
  await page.waitForTimeout(150)
  const after = await page.evaluate(() =>
    window.__FEIXUN_TEST_STORE__.windows.map((w) => ({ ...w.offset })),
  )
  const moved = after.some((w, i) => w.x !== before[i].x || w.y !== before[i].y)
  console.log(`${label}: moved=${moved}`, { before, after })
  return moved
}

async function runViewport(width, height) {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width, height } })
  const page = await context.newPage()
  await setupPage(page)

  const info = await page.evaluate(() => {
    const pageRect = document.querySelector('.feixun-page')?.getBoundingClientRect()
    const shell = document.querySelector('.feixun-window-shell')?.getBoundingClientRect()
    return {
      layoutMode: window.__FEIXUN_TEST_STORE__.layoutMode,
      pageRect,
      shell,
      inflated:
        shell &&
        pageRect &&
        shell.width >= pageRect.width * 0.9 &&
        shell.height >= pageRect.height * 0.9,
    }
  })
  console.log(`\n=== viewport ${width}x${height} ===`)
  console.log(JSON.stringify(info, null, 2))

  const pageBox = await page.locator('.feixun-page').boundingBox()
  const results = []
  results.push(await tryDrag(page, 'top-left', pageBox.x + 8, pageBox.y + 8))
  results.push(
    await tryDrag(page, 'left-margin', pageBox.x + 8, pageBox.y + pageBox.height / 2),
  )
  results.push(
    await tryDrag(
      page,
      'center',
      pageBox.x + pageBox.width / 2,
      pageBox.y + pageBox.height / 2,
    ),
  )

  await browser.close()
  return results.every(Boolean)
}

async function main() {
  const sizes = [
    [1400, 900],
    [1280, 800],
    [1024, 768],
    [900, 700],
  ]
  const all = []
  for (const [w, h] of sizes) {
    all.push(await runViewport(w, h))
  }
  console.log('\nALL PASS:', all.every(Boolean))
  process.exit(all.every(Boolean) ? 0 : 1)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
