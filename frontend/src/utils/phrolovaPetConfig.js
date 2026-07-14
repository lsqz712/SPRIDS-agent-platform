const PET_CONFIG_URL = '/phrolova-pet/config.json'
const PET_WINDOW_SIZE = 1400

let cachedConfig = null

/** Bongo Cat config.json 含 // 行注释，需预处理后再 parse */
function parseJsonWithComments(text) {
  const stripped = text
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '')
    .replace(/,\s*([}\]])/g, '$1')

  return JSON.parse(stripped)
}

export async function loadPhrolovaPetConfig() {
  if (cachedConfig) return cachedConfig

  const response = await fetch(PET_CONFIG_URL)
  if (!response.ok) {
    throw new Error(`Failed to load pet config: ${response.status}`)
  }

  const text = await response.text()
  cachedConfig = parseJsonWithComments(text)
  return cachedConfig
}

export function getPetWindowSize(config) {
  const size = config?.decoration?.window_size
  if (Array.isArray(size) && size.length >= 1 && Number.isFinite(size[0])) {
    return size[0]
  }
  return PET_WINDOW_SIZE
}

const HAND_CANVAS_SIZE = 1400

/** @returns {{
 *   logicalSize: number
 *   l2dCorrect: number
 *   l2dOffset: [number, number]
 *   handOffset: [number, number]
 *   offsetX: [number, number]
 *   offsetY: [number, number]
 *   scalar: [number, number]
 *   leftHanded: boolean
 *   l2dHorizontalFlip: boolean
 * }} */
export function getPetDecorationLayout(config) {
  const decoration = config?.decoration ?? {}
  const logicalSize = getPetWindowSize(config)

  return {
    logicalSize,
    l2dCorrect: Number.isFinite(decoration.l2d_correct) ? decoration.l2d_correct : 1.987,
    l2dOffset: Array.isArray(decoration.l2d_offset) ? decoration.l2d_offset : [0, 0],
    handOffset: Array.isArray(decoration.hand_offset) ? decoration.hand_offset : [0, 0],
    offsetX: Array.isArray(decoration.offsetX) ? decoration.offsetX : [0, 0],
    offsetY: Array.isArray(decoration.offsetY) ? decoration.offsetY : [0, 0],
    scalar: Array.isArray(decoration.scalar) ? decoration.scalar : [1, 1],
    leftHanded: decoration.leftHanded === true,
    l2dHorizontalFlip: decoration.l2d_horizontal_flip === true,
  }
}

/**
 * 原生 hand 贴图落点：hand_offset + offsetX/Y[左右手] * scalar
 * @returns {{ side: 'left' | 'right', sideIdx: number, x: number, y: number, spriteScale: number }}
 */
export function resolveHandPlacement(vk, layout, handSideMap) {
  let side = handSideMap.get(vk) ?? 'right'
  if (layout.leftHanded) {
    side = side === 'left' ? 'right' : 'left'
  }
  const sideIdx = side === 'left' ? 0 : 1
  const scalar = Number.isFinite(layout.scalar[sideIdx]) ? layout.scalar[sideIdx] : 1

  return {
    side,
    sideIdx,
    x: layout.handOffset[0] + layout.offsetX[sideIdx] * scalar,
    y: layout.handOffset[1] + layout.offsetY[sideIdx] * scalar,
    spriteScale: layout.logicalSize / HAND_CANVAS_SIZE,
  }
}

/** 调试：列出常用键的坐标解析结果 */
export function auditHandPlacements(config, sampleVks = [89, 72, 85, 73, 79]) {
  const layout = getPetDecorationLayout(config)
  const handSideMap = buildHandSideMap(config.keyboard)
  const handMap = buildStandardHandMap(config.standard ?? {})
  const names = { 89: 'Y', 72: 'H', 85: 'U', 73: 'I', 79: 'O' }

  return sampleVks.map((vk) => ({
    key: names[vk] ?? vk,
    vk,
    handIndex: handMap.get(vk),
    placement: resolveHandPlacement(vk, layout, handSideMap),
  }))
}

/** @returns {Map<number, number>} Windows VK code -> hand sprite index */
export function buildStandardHandMap(standard) {
  const map = new Map()

  if (!standard?.hand) return map

  standard.hand.forEach((keys, index) => {
    if (!Array.isArray(keys)) return
    keys.forEach((vk) => {
      if (Number.isFinite(vk)) {
        map.set(vk, index)
      }
    })
  })

  return map
}

/** Live2D ParamGroup「按键」内可驱动的参数（不含 Param18 气泡） */
export const L2D_KEYBOARD_PARAM_IDS = [
  'Space',
  'Alt',
  'Ctrl',
  'Shift',
  'B1',
  'V1',
  'C1',
  'X1',
  'Z1',
  'Enter1',
  'G1',
  'F1',
  'D1',
  'S1',
  'A1',
  'T1',
  'R1',
  'E1',
  'W1',
  'Q1',
  'F5',
  'F4',
  'F3',
  'F2',
  'F0',
]

/**
 * Live2D 按键映射：仅使用 standard.keyboard（与原生 Q/W/E 一致）
 * @returns {Map<number, string>} Windows VK code -> Live2D parameter id
 */
export function buildL2dKeyboardParamMap(standard) {
  const map = new Map()
  const rows = standard?.keyboard

  if (!Array.isArray(rows)) return map

  rows.forEach((keys, index) => {
    const paramId = L2D_KEYBOARD_PARAM_IDS[index]
    if (!paramId || !Array.isArray(keys)) return

    keys.forEach((vk) => {
      if (Number.isFinite(vk)) {
        map.set(vk, paramId)
      }
    })
  })

  return map
}

/** @returns {Set<number>} 所有在 config 中登记过的可响应 VK */
export function buildKnownTypingVkSet(standard) {
  const vks = new Set()
  const handMap = buildStandardHandMap(standard)
  const l2dMap = buildL2dKeyboardParamMap(standard)

  handMap.forEach((_index, vk) => vks.add(vk))
  l2dMap.forEach((_param, vk) => vks.add(vk))

  return vks
}

/** 模型无独立参数时，仍触发通用按键手型（如 0、6–9） */
export function isGenericTypingVk(vk) {
  if (vk >= 48 && vk <= 57) return true
  if (vk >= 65 && vk <= 90) return true
  if (vk >= 96 && vk <= 111) return true
  return false
}

/** @returns {Map<number, 'left' | 'right'>} VK -> 使用哪只手（来自 keyboard 段的 lefthand/righthand） */
export function buildHandSideMap(keyboardSection) {
  const map = new Map()
  const keyboard = keyboardSection ?? {}

  const mark = (rows, side) => {
    if (!Array.isArray(rows)) return
    rows.forEach((keys) => {
      if (!Array.isArray(keys)) return
      keys.forEach((vk) => {
        if (Number.isFinite(vk)) {
          map.set(vk, side)
        }
      })
    })
  }

  mark(keyboard.lefthand, 'left')
  mark(keyboard.righthand, 'right')

  return map
}

/**
 * @returns {Array<{ keys: number[], motionIndex: number }>}
 * Chord: [modifier, key] e.g. Alt(18) + 1(49)
 */
export function buildMotionLockHandBindings(standard) {
  const bindings = []
  const rows = standard?.l2d_motion_lockhand

  if (!Array.isArray(rows)) return bindings

  rows.forEach((row, motionIndex) => {
    if (!Array.isArray(row) || row.length < 2) return
    bindings.push({
      keys: row.map((value) => Number(value)),
      motionIndex,
    })
  })

  return bindings
}

/**
 * @returns {Array<{ keys: number[], expressionIndex: number }>}
 */
export function buildExpressionBindings(standard) {
  const bindings = []
  const rows = standard?.l2d_expression

  if (!Array.isArray(rows)) return bindings

  rows.forEach((row, expressionIndex) => {
    if (!Array.isArray(row) || row.length < 2) return
    bindings.push({
      keys: row.map((value) => Number(value)),
      expressionIndex,
    })
  })

  return bindings
}

export const STANDARD_EXPRESSION_FILES = [
  'expression1.exp3.json',
  'expression2.exp3.json',
  'expression3.exp3.json',
  'expression4.exp3.json',
  'expression5.exp3.json',
  'expression6.exp3.json',
]
