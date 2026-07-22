/** 桌宠原始显示边长（像素），对应滑块 50 */
export const PHROLOVA_PET_DEFAULT_STAGE_SIZE = 260
export const PHROLOVA_PET_DEFAULT_SIZE_LEVEL = 50
export const PHROLOVA_PET_MIN_SIZE_LEVEL = 0
export const PHROLOVA_PET_MAX_SIZE_LEVEL = 100
export const PHROLOVA_PET_SIZE_LEVEL_STORAGE_KEY = 'phro_pet_size_level'
/** @deprecated 旧版像素存储，读取时自动迁移为等级 */
export const PHROLOVA_PET_LEGACY_SIZE_STORAGE_KEY = 'phro_pet_stage_size'

/** level 1 时约为默认尺寸的 12% */
const MIN_VISIBLE_RATIO = 0.12
/** level 100 时为默认尺寸的 2 倍 */
const MAX_SCALE_RATIO = 2

/** @param {number} level */
export function clampSizeLevel(level) {
  const value = Number(level)
  if (!Number.isFinite(value)) return PHROLOVA_PET_DEFAULT_SIZE_LEVEL
  return Math.min(
    PHROLOVA_PET_MAX_SIZE_LEVEL,
    Math.max(PHROLOVA_PET_MIN_SIZE_LEVEL, Math.round(value)),
  )
}

/**
 * 滑块等级 → 像素边长
 * 0：隐藏（返回默认尺寸供布局占位）
 * 50：260px（原始大小）
 * 100：520px（最大）
 * @param {number} level
 */
export function levelToStageSize(level) {
  const lv = clampSizeLevel(level)
  if (lv <= 0) return PHROLOVA_PET_DEFAULT_STAGE_SIZE

  if (lv <= PHROLOVA_PET_DEFAULT_SIZE_LEVEL) {
    const t = lv / PHROLOVA_PET_DEFAULT_SIZE_LEVEL
    const ratio = MIN_VISIBLE_RATIO + (1 - MIN_VISIBLE_RATIO) * t
    return Math.round(PHROLOVA_PET_DEFAULT_STAGE_SIZE * ratio)
  }

  const t =
    (lv - PHROLOVA_PET_DEFAULT_SIZE_LEVEL) /
    (PHROLOVA_PET_MAX_SIZE_LEVEL - PHROLOVA_PET_DEFAULT_SIZE_LEVEL)
  const maxSize = Math.round(PHROLOVA_PET_DEFAULT_STAGE_SIZE * MAX_SCALE_RATIO)
  return Math.round(
    PHROLOVA_PET_DEFAULT_STAGE_SIZE + t * (maxSize - PHROLOVA_PET_DEFAULT_STAGE_SIZE),
  )
}

/** @param {number} px */
export function stageSizeToLevel(px) {
  const size = Number(px)
  if (!Number.isFinite(size) || size <= 0) return PHROLOVA_PET_MIN_SIZE_LEVEL

  const defaultSize = PHROLOVA_PET_DEFAULT_STAGE_SIZE
  const maxSize = Math.round(defaultSize * MAX_SCALE_RATIO)

  if (size <= defaultSize) {
    const ratio = size / defaultSize
    if (ratio <= MIN_VISIBLE_RATIO) return 1
    const t = (ratio - MIN_VISIBLE_RATIO) / (1 - MIN_VISIBLE_RATIO)
    return clampSizeLevel(Math.round(t * PHROLOVA_PET_DEFAULT_SIZE_LEVEL))
  }

  const t = (size - defaultSize) / (maxSize - defaultSize)
  return clampSizeLevel(
    Math.round(
      PHROLOVA_PET_DEFAULT_SIZE_LEVEL +
        t * (PHROLOVA_PET_MAX_SIZE_LEVEL - PHROLOVA_PET_DEFAULT_SIZE_LEVEL),
    ),
  )
}

export function readStoredSizeLevel() {
  try {
    const levelRaw = localStorage.getItem(PHROLOVA_PET_SIZE_LEVEL_STORAGE_KEY)
    if (levelRaw !== null) {
      return clampSizeLevel(Number(levelRaw))
    }
    const legacyRaw = localStorage.getItem(PHROLOVA_PET_LEGACY_SIZE_STORAGE_KEY)
    if (legacyRaw !== null) {
      return stageSizeToLevel(Number(legacyRaw))
    }
  } catch {
    // ignore
  }
  return PHROLOVA_PET_DEFAULT_SIZE_LEVEL
}

/** @deprecated 使用 readStoredSizeLevel + levelToStageSize */
export function readStoredPetStageSize() {
  return levelToStageSize(readStoredSizeLevel())
}

/** @deprecated */
export function clampPetStageSize(size) {
  return levelToStageSize(stageSizeToLevel(size))
}
