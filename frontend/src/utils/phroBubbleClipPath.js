/** @typedef {{ tailSize?: number; radius?: number; radiusInner?: number }} BubbleClipOptions */

const DEFAULTS = {
  tailSize: 7,
  radius: 10,
  radiusInner: 4,
}

/** @param {number} value */
function px(value) {
  return Math.round(value * 100) / 100
}

/**
 * @param {number} preferred
 * @param {number} width
 * @param {number} height
 * @param {number} tail
 * @param {number} inner
 */
function fitRadius(preferred, width, height, tail, inner = 0) {
  const maxByWidth = (width - tail - inner - 2) / 2
  const maxByHeight = (height - tail * 2 - inner - 2) / 2
  return px(Math.min(preferred, maxByWidth, maxByHeight, preferred))
}

/**
 * 顶部箭头 + 圆角矩形（右键菜单）
 * @param {number} width
 * @param {number} height
 * @param {number} arrowLeft
 * @param {BubbleClipOptions} [opts]
 */
export function buildBubbleClipPathTop(width, height, arrowLeft, opts = {}) {
  const t = opts.tailSize ?? DEFAULTS.tailSize
  const w = px(width)
  const h = px(height)
  const r = fitRadius(opts.radius ?? DEFAULTS.radius, w, h, t)
  const minA = t + r
  const maxA = w - t - r
  const a = maxA <= minA ? w / 2 : Math.min(Math.max(arrowLeft, minA), maxA)

  return `path('M ${px(a - t)} ${t} L ${a} 0 L ${px(a + t)} ${t} L ${px(w - r)} ${t} Q ${w} ${t} ${w} ${px(t + r)} L ${w} ${px(h - r)} Q ${w} ${h} ${px(w - r)} ${h} L ${r} ${h} Q 0 ${h} 0 ${px(h - r)} L 0 ${px(t + r)} Q 0 ${t} ${r} ${t} Z')`
}

/**
 * 左侧箭头 + 圆角矩形（侧栏飞讯子菜单）
 * @param {number} width
 * @param {number} height
 * @param {number} arrowTop
 * @param {BubbleClipOptions} [opts]
 */
export function buildBubbleClipPathLeft(width, height, arrowTop, opts = {}) {
  const t = opts.tailSize ?? DEFAULTS.tailSize
  const ri = opts.radiusInner ?? DEFAULTS.radiusInner
  const w = px(width)
  const h = px(height)
  const r = fitRadius(opts.radius ?? DEFAULTS.radius, w, h, t, ri)
  const minA = ri
  const maxA = h - t * 2 - ri
  const a = maxA <= minA ? (h - t * 2) / 2 : Math.min(Math.max(arrowTop, minA), maxA)
  const arrowBottom = px(a + t * 2)
  const bodyLeft = px(t + ri)

  return `path('M 0 ${px(a + t)} L ${t} ${arrowBottom} L ${t} ${px(h - ri)} Q ${t} ${h} ${bodyLeft} ${h} L ${px(w - r)} ${h} Q ${w} ${h} ${w} ${px(h - r)} L ${w} ${r} Q ${w} 0 ${px(w - r)} 0 L ${bodyLeft} 0 Q ${t} 0 ${t} ${ri} L ${t} ${px(a)} Z')`
}
