import { chromium } from 'playwright'

const BASE = 'http://localhost:5173'

async function setupPage(page) {
  await page.goto(`${BASE}/login`)
  await page.evaluate(() => {
    localStorage.setItem('SPRIDS_token', 'dev-preview')
    localStorage.setItem('SPRIDS_user', JSON.stringify({ username: 'dev', nickname: 'Dev' }))
  })
  await page.goto(`${BASE}/chat`, { waitUntil: 'networkidle' })
  await page.waitForSelector('.feixun-window-shell', { timeout: 10000 })
  await page.waitForTimeout(800)
}

async function measureEars(page) {
  return page.evaluate(() => {
    const shell = document.querySelector('.feixun-window-shell')
    const ear = document.querySelector('.feixun-window-ear--drag')
    if (!shell || !ear) return null
    const shellRect = shell.getBoundingClientRect()
    const earRect = ear.getBoundingClientRect()
    const style = getComputedStyle(shell)
    return {
      shell: { w: shellRect.width, h: shellRect.height },
      ear: { w: earRect.width, h: earRect.height },
      vars: {
        earW: style.getPropertyValue('--phro-chrome-ear-w'),
        earBand: style.getPropertyValue('--phro-chrome-ear-band'),
      },
      baseSize: window.__PINIA__?.state?.value?.feixunWindows?.windows?.[0]?.baseSize,
      scale: {
        x: window.__PINIA__?.state?.value?.feixunWindows?.windows?.[0]?.scaleX,
        y: window.__PINIA__?.state?.value?.feixunWindows?.windows?.[0]?.scaleY,
      },
    }
  })
}

async function main() {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })
  await setupPage(page)

  await page.evaluate(async () => {
    const { useFeixunWindowsStore } = await import('/src/stores/feixunWindows.js')
    window.__STORE__ = useFeixunWindowsStore()
  })

  const before = await page.evaluate(() => {
    const store = window.__STORE__
    const shell = document.querySelector('.feixun-window-shell')
    const ear = document.querySelector('.feixun-window-ear--drag')
    const shellRect = shell.getBoundingClientRect()
    const earRect = ear.getBoundingClientRect()
    const style = getComputedStyle(shell)
    return {
      shell: { w: shellRect.width, h: shellRect.height },
      ear: { w: earRect.width, h: earRect.height },
      vars: {
        earW: style.getPropertyValue('--phro-chrome-ear-w'),
        earBand: style.getPropertyValue('--phro-chrome-ear-band'),
      },
      baseSize: { ...store.windows[0].baseSize },
      scale: { x: store.windows[0].scaleX, y: store.windows[0].scaleY },
    }
  })
  console.log('before:', before)

  const shellBox = await page.locator('.feixun-window-shell').first().boundingBox()
  const northX = shellBox.x + shellBox.width * 0.5
  const northY = shellBox.y + (shellBox.height * 7) / 107
  await page.mouse.move(northX, northY)
  await page.mouse.down()
  await page.mouse.move(northX, northY - 80, { steps: 12 })
  await page.mouse.up()
  await page.waitForTimeout(300)

  const after = await page.evaluate(() => {
    const store = window.__STORE__
    const shell = document.querySelector('.feixun-window-shell')
    const ear = document.querySelector('.feixun-window-ear--drag')
    const shellRect = shell.getBoundingClientRect()
    const earRect = ear.getBoundingClientRect()
    const style = getComputedStyle(shell)
    return {
      shell: { w: shellRect.width, h: shellRect.height },
      ear: { w: earRect.width, h: earRect.height },
      vars: {
        earW: style.getPropertyValue('--phro-chrome-ear-w'),
        earBand: style.getPropertyValue('--phro-chrome-ear-band'),
      },
      baseSize: { ...store.windows[0].baseSize },
      scale: { x: store.windows[0].scaleX, y: store.windows[0].scaleY },
    }
  })
  console.log('after:', after)

  const earFixed =
    Math.abs(after.ear.w - before.ear.w) < 1 && Math.abs(after.ear.h - before.ear.h) < 1
  console.log('ear-fixed:', earFixed ? 'PASS' : 'FAIL')

  await browser.close()
  process.exit(earFixed ? 0 : 1)
}

main().catch(console.error)
