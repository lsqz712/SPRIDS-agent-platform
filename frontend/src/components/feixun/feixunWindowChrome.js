/** 飞讯窗框耳片 — 与缩放无关，按 chromeBaseSize 锁定像素 */
/** 左右垂直边间距（$phro-ear-w / frame，不含外侧圆角弧） */
export const CHROME_EAR_STRAIGHT_RATIO = 12 / 100
/** SVG 耳片槽宽（含圆角柔化区，viewBox 15 / frame 100） */
export const CHROME_EAR_CAP_RATIO = 15 / 100
export const CHROME_EAR_CAP_VIEW_W = 15
export const CHROME_EAR_BAND_VIEW_H = 7
export const CHROME_EAR_CORNER_R = 3
export const EAR_BAND_FRAME_RATIO = 7 / 107
export const CHROME_FALLBACK_BASE = { width: 960, height: 680 }
/** 与 FeixunWindow $phro-window-padding 保持一致 */
export const CHROME_EAR_LOGO_PAD = 14

export const CHROME_FRAME_PATH =
  'M 3 -7 L 9 -7 Q 12 -7 12 -4 L 12 -3 Q 12 0 15 0 L 85 0 Q 88 0 88 -3 L 88 -4 Q 88 -7 91 -7 L 97 -7 Q 100 -7 100 -4 L 100 97 Q 100 100 97 100 L 3 100 Q 0 100 0 97 L 0 -4 Q 0 -7 3 -7 Z'

export const CHROME_CLOSE_GLOW_PATH =
  'M 85 0 Q 88 0 88 -3 L 88 -4 Q 88 -7 91 -7 L 97 -7 Q 100 -7 100 -4 L 100 0 Z'

/** 耳片（viewBox 0 -7 15 7） */
export const CHROME_EAR_LEFT_FILL_PATH =
  'M 15 0 Q 12 0 12 -3 L 12 -4 Q 12 -7 9 -7 L 3 -7 Q 0 -7 0 -4 L 0 0 Z'
export const CHROME_EAR_LEFT_STROKE_PATH =
  'M 15 0 Q 12 0 12 -3 L 12 -4 Q 12 -7 9 -7 L 3 -7 Q 0 -7 0 -4 L 0 0'
export const CHROME_EAR_RIGHT_FILL_PATH =
  'M 0 0 Q 3 0 3 -3 L 3 -4 Q 3 -7 6 -7 L 12 -7 Q 15 -7 15 -4 L 15 0 Z'
export const CHROME_EAR_RIGHT_STROKE_PATH =
  'M 0 0 Q 3 0 3 -3 L 3 -4 Q 3 -7 6 -7 L 12 -7 Q 15 -7 15 -4 L 15 0'
export const CHROME_CLOSE_GLOW_PATH_LOCAL =
  'M 0 0 Q 3 0 3 -3 L 3 -4 Q 3 -7 6 -7 L 12 -7 Q 15 -7 15 -4 L 15 0 Z'

/** 顶行桥接（全局坐标，viewBox 15 -7 70 7） */
export const CHROME_TOP_BRIDGE_STROKE_PATH = 'M 15 0 L 85 0'

/** 主体描边：不含 y=0 顶边（顶行负责） */
export const CHROME_BODY_STROKE_PATH =
  'M 0 0 L 0 97 Q 0 100 3 100 L 97 100 Q 100 100 100 97 L 100 0'

export const CHROME_SLICE_TOP_LEFT = { x: 0, y: -7, w: 15, h: 7 }
export const CHROME_SLICE_TOP_MID = { x: 15, y: -7, w: 70, h: 7 }
export const CHROME_SLICE_EAR_CAP = { x: 0, y: -7, w: 15, h: 7 }
export const CHROME_SLICE_BODY = { x: 0, y: 0, w: 100, h: 100 }

export function formatSliceViewBox({ x, y, w, h }) {
  return `${x} ${y} ${w} ${h}`
}

/** 左右垂直边之间的水平距离（不含耳片外侧短弧圆角扩展） */
export function computeEarStraightSpanPx(baseWidth) {
  if (!(baseWidth > 0)) {
    return Math.round(CHROME_FALLBACK_BASE.width * CHROME_EAR_STRAIGHT_RATIO)
  }
  return Math.round(baseWidth * CHROME_EAR_STRAIGHT_RATIO)
}

/** SVG 渲染槽宽（含圆角柔化，比 straight 宽 corner 区） */
export function computeEarCapPx(baseWidth) {
  if (!(baseWidth > 0)) {
    return Math.round(CHROME_FALLBACK_BASE.width * CHROME_EAR_CAP_RATIO)
  }
  return Math.round(baseWidth * CHROME_EAR_CAP_RATIO)
}

/** 便签模式水平步进 = 左右垂直边间距，不含外侧圆角 */
export function computeStickyFanStepPx(baseWidth) {
  return computeEarStraightSpanPx(baseWidth)
}

/** @deprecated 使用 computeEarCapPx */
export function computeEarWidthPx(frameWidth, frameHeight) {
  void frameHeight
  return computeEarCapPx(frameWidth)
}

export function computeEarBandPx(frameHeight) {
  return frameHeight * EAR_BAND_FRAME_RATIO
}

export function buildChromeLayoutVars(baseWidth, baseHeight, shellWidth = baseWidth) {
  if (!(baseWidth > 0 && baseHeight > 0)) return {}
  const capW = computeEarCapPx(baseWidth)
  const straightW = computeEarStraightSpanPx(baseWidth)
  const earBand = computeEarBandPx(baseHeight)
  const earVisH = earBand + CHROME_EAR_LOGO_PAD
  const resolvedShell = shellWidth > 0 ? shellWidth : baseWidth
  return {
    '--phro-chrome-ear-cap-w': `${capW}px`,
    '--phro-chrome-ear-w': `${straightW}px`,
    '--phro-chrome-ear-band': `${earBand}px`,
    '--phro-chrome-ear-vis-h': `${earVisH}px`,
    '--phro-chrome-ear-logo-pad': `${CHROME_EAR_LOGO_PAD}px`,
    '--phro-chrome-sticky-step-x': `${straightW}px`,
    '--phro-chrome-bridge-w': `${Math.max(0, resolvedShell - capW * 2)}px`,
    '--phro-chrome-base-w': `${baseWidth}px`,
    '--phro-chrome-base-h': `${baseHeight}px`,
  }
}

export function resolveChromeBaseSize(chromeBaseSize, baseSize) {
  if (chromeBaseSize?.width > 0 && chromeBaseSize?.height > 0) {
    return { width: chromeBaseSize.width, height: chromeBaseSize.height }
  }
  if (baseSize?.width > 0 && baseSize?.height > 0) {
    return { width: baseSize.width, height: baseSize.height }
  }
  return { ...CHROME_FALLBACK_BASE }
}

/** 外框高度：耳片带固定（7/107），仅主体区随 scaleY 伸缩 */
export function computeShellOuterHeight(baseH, scaleY) {
  const earBand = computeEarBandPx(baseH)
  return earBand + (baseH - earBand) * scaleY
}
