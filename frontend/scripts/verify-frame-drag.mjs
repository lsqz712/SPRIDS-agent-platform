import { chromium } from 'playwright'

const BASE = 'http://localhost:5173'

async function setupPage(page) {
  await page.goto(`${BASE}/login`)
  await page.evaluate(() => {
    localStorage.setItem('rsod_token', 'dev-preview')
    localStorage.setItem('rsod_user', JSON.stringify({ username: 'dev', nickname: 'Dev' }))
  })
  await page.goto(`${BASE}/chat`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.feixun-page-drag-surface', { timeout: 10000 })
  await page.waitForTimeout(800)
  await page.evaluate(async () => {
    const { useFeixunWindowsStore } = await import('/src/stores/feixunWindows.js')
    window.__FEIXUN_TEST_STORE__ = useFeixunWindowsStore()
  })
}

async function main() {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  await setupPage(page)

  const shell = page.locator('.feixun-window-shell').first()
  const shellBox = await shell.boundingBox()
  const metrics = await page.evaluate(() => {
    const store = window.__FEIXUN_TEST_STORE__.windows[0]
    const shellEl = document.querySelector('.feixun-window-shell')
    const shellRect = shellEl.getBoundingClientRect()
    const earBandPx = (shellRect.height * 7) / 107
    return {
      baseSize: store.baseSize,
      shellHeight: shellRect.height,
      earBandPx,
      edgeLineY: shellRect.top + earBandPx,
    }
  })

  const scaleBefore = await page.evaluate(() => window.__FEIXUN_TEST_STORE__.windows[0].scaleY)
  const northX = shellBox.x + shellBox.width * 0.5
  const northY = metrics.edgeLineY
  await page.mouse.move(northX, northY)
  await page.mouse.down()
  await page.mouse.move(northX, northY + 80, { steps: 12 })
  await page.mouse.up()
  await page.waitForTimeout(200)
  const scaleAfter = await page.evaluate(() => window.__FEIXUN_TEST_STORE__.windows[0].scaleY)
  const northResizeWorks = scaleAfter !== scaleBefore

  const gapY = shellBox.y + metrics.earBandPx * 0.35
  const before = await page.evaluate(() =>
    window.__FEIXUN_TEST_STORE__.windows.map((w) => ({ ...w.offset })),
  )
  await page.mouse.move(northX, gapY)
  await page.mouse.down()
  await page.mouse.move(northX + 80, gapY + 60, { steps: 10 })
  await page.mouse.up()
  await page.waitForTimeout(200)
  const after = await page.evaluate(() =>
    window.__FEIXUN_TEST_STORE__.windows.map((w) => ({ ...w.offset })),
  )
  const gapDragWorks =
    after.length > 0 &&
    after.every((w, i) => w.x === before[i].x + 80 && w.y === before[i].y + 60)

  console.log('north-on-edge-line:', northResizeWorks ? 'PASS' : 'FAIL', {
    northY,
    edgeLineY: metrics.edgeLineY,
    scaleBefore,
    scaleAfter,
  })
  console.log('ear-gap-drag:', gapDragWorks ? 'PASS' : 'FAIL', { gapY, before, after })

  const pass = northResizeWorks && gapDragWorks
  console.log('OVERALL:', pass ? 'PASS' : 'FAIL')
  await browser.close()
  process.exit(pass ? 0 : 1)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
