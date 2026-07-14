/** @typedef {{ top: number, left: number, height: number }} ToolMenuAnchor */

/** 箭头尖端与侧栏右缘的空隙（px） */
export const FLYOUT_GAP = 12
/** 箭头向左伸出气泡的宽度，与 CSS 三角 border 一致 */
export const FLYOUT_ARROW_WIDTH = 7
export const ARROW_SIZE = 7

/**
 * @param {ToolMenuAnchor} anchor
 * @param {number} panelHeight
 */
export function computeFlyoutLayout(anchor, panelHeight) {
  const viewportTop = 8
  const viewportBottom = window.innerHeight - 8
  const left = anchor.left + FLYOUT_GAP + FLYOUT_ARROW_WIDTH

  let top = anchor.top
  let align = 'top'

  if (top + panelHeight > viewportBottom) {
    top = anchor.top + anchor.height - panelHeight
    align = 'bottom'
  }

  if (top < viewportTop) {
    top = viewportTop
  }

  const anchorCenter = anchor.top + anchor.height / 2
  let arrowTop = anchorCenter - top - ARROW_SIZE
  const arrowMin = 14
  const arrowMax = Math.max(arrowMin, panelHeight - 14 - ARROW_SIZE * 2)
  arrowTop = Math.min(Math.max(arrowMin, arrowTop), arrowMax)

  return {
    top,
    left,
    align,
    arrowTop,
  }
}

export const FLYOUT_WIDTH = {
  feixun: 168,
  pet: 300,
  user: 168,
}

/** @param {'feixun' | 'pet' | 'user'} section */
export function defaultPanelHeight(section) {
  if (section === 'feixun') return 88
  if (section === 'user') return 88
  return 420
}
