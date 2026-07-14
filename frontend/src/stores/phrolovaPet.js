import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { buildDefaultToggleStates } from '@/utils/phrolovaPetMenu'
import {
  clampSizeLevel,
  levelToStageSize,
  PHROLOVA_PET_DEFAULT_SIZE_LEVEL,
  PHROLOVA_PET_MIN_SIZE_LEVEL,
  PHROLOVA_PET_SIZE_LEVEL_STORAGE_KEY,
  readStoredSizeLevel,
} from '@/utils/phrolovaPetSize'

const STORAGE_VISIBLE = 'phro_pet_visible'

function readVisible() {
  const stored = localStorage.getItem(STORAGE_VISIBLE)
  if (stored === null) return true
  return stored !== '0'
}

function readInitialPetState() {
  const storedLevel = readStoredSizeLevel()
  const storedVisible = readVisible()

  if (!storedVisible) {
    return {
      sizeLevel: PHROLOVA_PET_MIN_SIZE_LEVEL,
      lastActiveSizeLevel:
        storedLevel > 0 ? storedLevel : PHROLOVA_PET_DEFAULT_SIZE_LEVEL,
      visible: false,
    }
  }

  const activeLevel =
    storedLevel > 0 ? storedLevel : PHROLOVA_PET_DEFAULT_SIZE_LEVEL

  return {
    sizeLevel: activeLevel,
    lastActiveSizeLevel: activeLevel,
    visible: true,
  }
}

/** @typedef {{
 *   playLockMotion?: (motionIndex: number) => void
 *   setExpressionByIndex?: (expressionIndex: number, toggleExpression?: boolean) => void
 *   dispatchMenuAction?: (action: import('@/utils/phrolovaPetMenu').PhrolovaPetMenuAction) => void
 * }} PhrolovaPetRuntime */

export const usePhrolovaPetStore = defineStore('phrolovaPet', () => {
  const initial = readInitialPetState()
  const visible = ref(initial.visible)
  const sizeLevel = ref(initial.sizeLevel)
  const lastActiveSizeLevel = ref(initial.lastActiveSizeLevel)
  const loadError = ref('')
  const menuOpen = ref(false)
  const toggleStates = ref(buildDefaultToggleStates())
  /** @type {import('vue').Ref<PhrolovaPetRuntime | null>} */
  const runtime = ref(null)

  const stageSize = computed(() => {
    const level = sizeLevel.value > 0 ? sizeLevel.value : lastActiveSizeLevel.value
    return levelToStageSize(level)
  })

  watch(visible, (value) => {
    localStorage.setItem(STORAGE_VISIBLE, value ? '1' : '0')
  })

  /** @param {number} level */
  function setSizeLevel(level) {
    const clamped = clampSizeLevel(level)
    sizeLevel.value = clamped
    localStorage.setItem(PHROLOVA_PET_SIZE_LEVEL_STORAGE_KEY, String(clamped))

    if (clamped <= 0) {
      hide()
      return
    }

    lastActiveSizeLevel.value = clamped
    show()
  }

  function resetSizeLevel() {
    setSizeLevel(PHROLOVA_PET_DEFAULT_SIZE_LEVEL)
  }

  function show() {
    loadError.value = ''
    visible.value = true
  }

  function hide() {
    visible.value = false
  }

  function toggle() {
    if (visible.value) {
      setSizeLevel(PHROLOVA_PET_MIN_SIZE_LEVEL)
      return
    }
    setSizeLevel(lastActiveSizeLevel.value || PHROLOVA_PET_DEFAULT_SIZE_LEVEL)
  }

  /** @param {PhrolovaPetRuntime | null} api */
  function setRuntime(api) {
    runtime.value = api
  }

  function detachRuntime() {
    runtime.value = null
  }

  function clearRuntime() {
    runtime.value = null
    toggleStates.value = buildDefaultToggleStates()
  }

  /** @param {Record<string, boolean>} states */
  function setToggleStates(states) {
    toggleStates.value = { ...states }
  }

  function openMenu() {
    menuOpen.value = true
  }

  function closeMenu() {
    menuOpen.value = false
  }

  /** @param {import('@/utils/phrolovaPetMenu').PhrolovaPetMenuAction} action */
  function runMenuAction(action) {
    runtime.value?.dispatchMenuAction?.(action)
  }

  function setLoadError(message) {
    loadError.value = message
  }

  return {
    visible,
    sizeLevel,
    stageSize,
    loadError,
    menuOpen,
    runtime,
    toggleStates,
    show,
    hide,
    toggle,
    setSizeLevel,
    resetSizeLevel,
    setRuntime,
    detachRuntime,
    clearRuntime,
    openMenu,
    closeMenu,
    runMenuAction,
    setToggleStates,
    setLoadError,
  }
})
