import { attachPhrolovaPetInput } from './phrolovaPetInput'
import {
  getPetDecorationLayout,
  loadPhrolovaPetConfig,
} from './phrolovaPetConfig'
import {
  PHROLOVA_PET_MENU_SECTIONS,
  buildDefaultToggleStates,
} from './phrolovaPetMenu'

import {
  clampPetStageSize,
  PHROLOVA_PET_DEFAULT_STAGE_SIZE,
} from './phrolovaPetSize'

const LOCK_MOTION_DURATION_MS = 450
const HAPPY_MOTION_INDEX = 22
const HAPPY_MOTION_PARAM_IDS = ['Param15', 'Param14', 'Param30']

/** @param {import('./phrolovaPetMenu').PhrolovaPetMenuAction} action */
function getToggleParamValue(action, isOn) {
  if (action.paramInverted) return isOn ? 0 : 1
  return isOn ? 1 : 0
}

/** @param {import('./phrolovaPetMenu').PhrolovaPetMenuAction} action */
function getMotionStartParamValue(action, turningOn) {
  if (action.paramInverted) return turningOn ? 1 : 0
  return turningOn ? 0 : 1
}

let cubismCoreReady = null

export const PHROLOVA_PET_MODEL_URL = '/phrolova-pet/standard/cat_model/cat.model3.json'
/** 桌宠默认显示窗口边长（像素） */
export const PHROLOVA_PET_STAGE = {
  width: PHROLOVA_PET_DEFAULT_STAGE_SIZE,
  height: PHROLOVA_PET_DEFAULT_STAGE_SIZE,
}

/** 高 DPI 屏用物理像素渲染；小窗口从 1400 逻辑缩小，至少 2x 超采样减轻糊感 */
function getPetRenderResolution() {
  if (typeof window === 'undefined') return 1
  const dpr = window.devicePixelRatio || 1
  return Math.min(Math.max(dpr, 2), 2)
}

function loadCubismCore() {
  if (typeof window !== 'undefined' && window.Live2DCubismCore) {
    return Promise.resolve()
  }

  if (!cubismCoreReady) {
    cubismCoreReady = new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-live2d-cubism-core="1"]')
      if (existing) {
        existing.addEventListener('load', () => resolve(), { once: true })
        existing.addEventListener('error', () => reject(new Error('Cubism core load failed')), {
          once: true,
        })
        return
      }

      const script = document.createElement('script')
      script.src = '/vendor/live2dcubismcore.min.js'
      script.dataset.live2dCubismCore = '1'
      script.onload = () => resolve()
      script.onerror = () => reject(new Error('Cubism core load failed'))
      document.head.appendChild(script)
    })
  }

  return cubismCoreReady
}

function setModelParameter(model, id, value) {
  const coreModel = model?.internalModel?.coreModel
  if (!coreModel || typeof coreModel.setParameterValueById !== 'function') return

  coreModel.setParameterValueById(id, value)
}

function setPartOpacity(model, partId, opacity) {
  const coreModel = model?.internalModel?.coreModel
  if (!coreModel?.setPartOpacityById) return

  coreModel.setPartOpacityById(partId, opacity)
}

function resetHappyMotionParams(model) {
  HAPPY_MOTION_PARAM_IDS.forEach((paramId) => setModelParameter(model, paramId, 0))
}

function resetRestingLimbs(model) {
  setModelParameter(model, 'CatParamLeftHandDown', 0)
  const coreModel = model?.internalModel?.coreModel
  if (coreModel?.setPartOpacityById) {
    coreModel.setPartOpacityById('Part13', 1)
  }
}

/** 原版 Bongo Cat：Live2D 底对齐 + l2d_correct 缩放 */
function layoutLive2dModelNative(model, logicalSize, l2dCorrect, l2dOffset) {
  model.anchor.set(0.5, 1)
  model.scale.set(l2dCorrect)
  model.x = logicalSize / 2 + l2dOffset[0] * logicalSize
  model.y = logicalSize + l2dOffset[1] * logicalSize
}

function computeWorldFit(model, layout) {
  const { logicalSize, l2dCorrect, l2dOffset } = layout
  const im = model.internalModel
  const ow = im?.originalWidth ?? 0
  const oh = im?.originalHeight ?? 0
  if (!ow || !oh) {
    return { fit: 1, left: 0, top: 0, contentW: logicalSize, contentH: logicalSize }
  }

  const mw = ow * l2dCorrect
  const mh = oh * l2dCorrect
  const cx = logicalSize / 2 + l2dOffset[0] * logicalSize
  const footY = logicalSize + l2dOffset[1] * logicalSize
  const modelLeft = cx - mw / 2
  const modelTop = footY - mh

  const left = Math.min(modelLeft, 0)
  const top = Math.min(modelTop, 0)
  const right = Math.max(modelLeft + mw, logicalSize)
  const bottom = Math.max(footY, logicalSize)

  const contentW = right - left
  const contentH = bottom - top
  const fit = Math.min(logicalSize / contentW, logicalSize / contentH, 1) * 0.98

  return { fit, left, top, contentW, contentH }
}

function applyWorldFit(world, logicalSize, fitInfo) {
  const { fit, left, top, contentW, contentH } = fitInfo
  world.scale.set(fit)
  world.position.set(
    (logicalSize - contentW * fit) / 2 - left * fit,
    (logicalSize - contentH * fit) / 2 - top * fit,
  )
}

function applyMouseParams(model, pressedMouse) {
  setModelParameter(model, 'ParamMouseLeftDown', pressedMouse.has('left') ? 1 : 0)
  setModelParameter(model, 'ParamMouseRightDown', pressedMouse.has('right') ? 1 : 0)
}

const PET_DRAG_THRESHOLD = 5

/** 拖动桌宠窗口 */
function attachPetDrag(canvas, callbacks) {
  /** @type {{ pointerId: number, startX: number, startY: number, lastX: number, lastY: number, moved: boolean } | null} */
  let session = null

  const clearWindowListeners = () => {
    window.removeEventListener('pointermove', onWindowPointerMove)
    window.removeEventListener('pointerup', onWindowPointerUp)
    window.removeEventListener('pointercancel', onWindowPointerUp)
  }

  const onWindowPointerMove = (event) => {
    if (!session || event.pointerId !== session.pointerId) return

    if (!session.moved) {
      const totalDx = event.clientX - session.startX
      const totalDy = event.clientY - session.startY
      if (Math.hypot(totalDx, totalDy) < PET_DRAG_THRESHOLD) return
      session.moved = true
    }

    event.preventDefault()
    const dx = event.clientX - session.lastX
    const dy = event.clientY - session.lastY
    session.lastX = event.clientX
    session.lastY = event.clientY
    callbacks.onDragDelta?.(dx, dy)
  }

  const onWindowPointerUp = (event) => {
    if (!session || event.pointerId !== session.pointerId) return

    if (session.moved) {
      callbacks.onDragEnd?.()
    }

    clearWindowListeners()
    session = null
  }

  const onPointerDown = (event) => {
    if (event.button !== 0) return

    session = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      lastX: event.clientX,
      lastY: event.clientY,
      moved: false,
    }

    callbacks.onDragStart?.()
    window.addEventListener('pointermove', onWindowPointerMove)
    window.addEventListener('pointerup', onWindowPointerUp)
    window.addEventListener('pointercancel', onWindowPointerUp)
  }

  canvas.addEventListener('pointerdown', onPointerDown)

  return {
    destroy() {
      canvas.removeEventListener('pointerdown', onPointerDown)
      clearWindowListeners()
      session = null
    },
  }
}

/** @typedef {{ stageSize?: number, onDragStart?: () => void, onDragDelta?: (dx: number, dy: number) => void, onDragEnd?: () => void, onToggleStatesChange?: (states: Record<string, boolean>) => void }} PhrolovaPetStageOptions */

/** @param {HTMLElement} container @param {PhrolovaPetStageOptions} [options] */
export async function createPhrolovaPetStage(container, options = {}) {
  await loadCubismCore()

  const config = await loadPhrolovaPetConfig()
  const layout = getPetDecorationLayout(config)
  const { logicalSize, l2dCorrect, l2dOffset } = layout
  let stageW = clampPetStageSize(options.stageSize ?? PHROLOVA_PET_DEFAULT_STAGE_SIZE)
  let stageH = stageW
  let screenScale = stageW / logicalSize

  const [PIXI, live2d] = await Promise.all([
    import('pixi.js'),
    import('pixi-live2d-display/lib/cubism4'),
  ])

  const { Live2DModel, config: live2dConfig, MotionPriority } = live2d
  live2dConfig.motionFadingDuration = 0
  live2dConfig.idleMotionFadingDuration = 0
  live2dConfig.preserveExpressionOnMotion = true

  window.PIXI = PIXI

  const resolution = getPetRenderResolution()

  const app = new PIXI.Application({
    width: stageW,
    height: stageH,
    backgroundAlpha: 0,
    antialias: true,
    autoDensity: true,
    resolution,
  })

  app.view.style.display = 'block'
  app.view.style.pointerEvents = 'auto'
  container.replaceChildren()
  container.appendChild(app.view)

  const viewport = new PIXI.Container()
  viewport.scale.set(screenScale)
  app.stage.addChild(viewport)

  const scene = new PIXI.Container()

  const model = await Live2DModel.from(PHROLOVA_PET_MODEL_URL, {
    autoInteract: false,
    autoUpdate: true,
  })

  model.interactive = true
  model.buttonMode = true
  layoutLive2dModelNative(model, logicalSize, l2dCorrect, l2dOffset)
  resetRestingLimbs(model)

  scene.addChild(model)
  viewport.addChild(scene)

  const applyFit = () => {
    applyWorldFit(scene, logicalSize, computeWorldFit(model, layout))
  }
  applyFit()
  setTimeout(applyFit, 100)

  app.stage.interactive = true

  const pressedMouse = new Set()

  const syncMouseState = () => {
    applyMouseParams(model, pressedMouse)
  }

  syncMouseState()

  const updateMouseTracking = (clientX, clientY) => {
    const rect = app.view.getBoundingClientRect()
    if (!rect.width || !rect.height) return

    const xRatio = (clientX - rect.left) / rect.width
    const yRatio = (clientY - rect.top) / rect.height
    const clampedX = Math.min(1, Math.max(0, xRatio))
    const clampedY = Math.min(1, Math.max(0, yRatio))

    setModelParameter(model, 'ParamMouseX', clampedX * 2 - 1)
    setModelParameter(model, 'ParamMouseY', -(clampedY * 2 - 1))
  }

  const focusModelFromClient = (clientX, clientY) => {
    const rect = app.view.getBoundingClientRect()
    if (!rect.width || !rect.height) return

    const x = ((clientX - rect.left) / rect.width) * stageW
    const y = ((clientY - rect.top) / rect.height) * stageH
    const local = viewport.toLocal(new PIXI.Point(x, y))
    model.focus(local.x, local.y)
  }

  const input = attachPhrolovaPetInput({
    onMouseButton: (button, pressed) => {
      if (pressed) {
        pressedMouse.add(button)
      } else {
        pressedMouse.delete(button)
      }
      syncMouseState()
    },
    onMouseMove: (x, y) => {
      updateMouseTracking(x, y)
      focusModelFromClient(x, y)
    },
  })

  app.stage.on('pointermove', (event) => {
    const local = viewport.toLocal(event.data.global)
    model.focus(local.x, local.y)
  })

  let activeExpressionIndex = 0
  const toggleStates = buildDefaultToggleStates()
  /** @type {Map<string, number>} */
  const toggleGenerations = new Map()
  /** @type {Map<string, ReturnType<typeof setTimeout>>} */
  const toggleFinishTimers = new Map()
  /** @type {Map<string, import('./phrolovaPetMenu').PhrolovaPetMenuAction>} */
  const toggleActions = new Map()

  PHROLOVA_PET_MENU_SECTIONS.forEach((section) => {
    section.items.forEach((item) => {
      if (item.kind === 'toggle') {
        toggleActions.set(item.id, item)
      }
    })
  })

  const syncToggleStatesToStore = () => {
    options.onToggleStatesChange?.({ ...toggleStates })
  }

  /** @param {import('./phrolovaPetMenu').PhrolovaPetMenuAction} action */
  const enforceToggleVisual = (action, isOn) => {
    if (action.paramId) {
      setModelParameter(model, action.paramId, getToggleParamValue(action, isOn))
    }
    if (action.partIds?.length) {
      const opacity = isOn ? 1 : 0
      action.partIds.forEach((partId) => setPartOpacity(model, partId, opacity))
    }
  }

  const stopLockMotions = () => {
    const manager = model.internalModel?.motionManager
    if (manager?.stopAllMotions) {
      manager.stopAllMotions()
    }
  }

  const clearToggleFinishTimer = (toggleId) => {
    const timer = toggleFinishTimers.get(toggleId)
    if (timer === undefined) return
    window.clearTimeout(timer)
    toggleFinishTimers.delete(toggleId)
  }

  const clearAllToggleFinishTimers = () => {
    toggleFinishTimers.forEach((timer) => window.clearTimeout(timer))
    toggleFinishTimers.clear()
  }

  const playLockMotion = (motionIndex) => {
    if (motionIndex !== HAPPY_MOTION_INDEX) {
      resetHappyMotionParams(model)
    }

    stopLockMotions()

    const motionPromise = model.motion('CAT_motion_lock', motionIndex, MotionPriority.FORCE)
    if (motionPromise && typeof motionPromise.catch === 'function') {
      motionPromise.catch(() => {})
    }
  }

  /** @param {import('./phrolovaPetMenu').PhrolovaPetMenuAction} action */
  const playToggle = (action) => {
    const current = toggleStates[action.id] ?? action.defaultOn !== false
    const next = !current
    const generation = (toggleGenerations.get(action.id) ?? 0) + 1

    clearToggleFinishTimer(action.id)
    toggleGenerations.set(action.id, generation)
    toggleStates[action.id] = next
    syncToggleStatesToStore()

    const motionIndex = next ? action.showMotionIndex : action.hideMotionIndex

    if (action.paramId) {
      setModelParameter(model, action.paramId, getMotionStartParamValue(action, next))
    }
    if (next && action.partIds?.length) {
      action.partIds.forEach((partId) => setPartOpacity(model, partId, 1))
    }

    if (!Number.isFinite(motionIndex)) {
      enforceToggleVisual(action, next)
      return
    }

    playLockMotion(motionIndex)

    const timer = window.setTimeout(() => {
      toggleFinishTimers.delete(action.id)
      if (toggleGenerations.get(action.id) !== generation) return

      stopLockMotions()
      resetHappyMotionParams(model)
      enforceToggleVisual(action, next)
    }, LOCK_MOTION_DURATION_MS)

    toggleFinishTimers.set(action.id, timer)
  }

  toggleActions.forEach((action, id) => {
    const isOn = toggleStates[id] ?? action.defaultOn !== false
    enforceToggleVisual(action, isOn)
  })
  syncToggleStatesToStore()

  const applyExpression = (expressionIndex) => {
    const manager = model.internalModel?.motionManager?.expressionManager
    if (manager?.stopAllExpressions) {
      manager.stopAllExpressions()
    }

    const index = Math.min(Math.max(0, expressionIndex), 5)
    model.expression(index)
  }

  const setExpressionByIndex = (expressionIndex, toggleExpression = false) => {
    if (
      toggleExpression &&
      expressionIndex >= 1 &&
      expressionIndex <= 5 &&
      activeExpressionIndex === expressionIndex
    ) {
      activeExpressionIndex = 0
      applyExpression(0)
      return
    }

    activeExpressionIndex = expressionIndex
    applyExpression(expressionIndex)
  }

  const resetToDefaults = () => {
    clearAllToggleFinishTimers()
    stopLockMotions()
    resetHappyMotionParams(model)

    toggleActions.forEach((_, id) => {
      toggleGenerations.set(id, (toggleGenerations.get(id) ?? 0) + 1)
    })

    const defaults = buildDefaultToggleStates()
    Object.keys(toggleStates).forEach((id) => {
      delete toggleStates[id]
    })
    Object.assign(toggleStates, defaults)

    toggleActions.forEach((action, id) => {
      const isOn = defaults[id] ?? action.defaultOn !== false
      enforceToggleVisual(action, isOn)
    })

    activeExpressionIndex = 0
    applyExpression(0)
    resetRestingLimbs(model)
    syncToggleStatesToStore()
  }

  /** @param {import('./phrolovaPetMenu').PhrolovaPetMenuAction} action */
  const dispatchMenuAction = (action) => {
    switch (action.kind) {
      case 'toggle':
        playToggle(action)
        break
      case 'motion':
        if (Number.isFinite(action.motionIndex)) {
          playLockMotion(action.motionIndex)
        }
        break
      case 'expression':
        if (Number.isFinite(action.expressionIndex)) {
          setExpressionByIndex(action.expressionIndex, action.toggleExpression === true)
        }
        break
      case 'reset':
        resetToDefaults()
        break
      default:
        break
    }
  }

  const onMotionFinish = () => {
    syncMouseState()
  }

  if (typeof model.internalModel.motionManager.on === 'function') {
    model.internalModel.motionManager.on('motionFinish', onMotionFinish)
  }

  const petDrag = attachPetDrag(app.view, {
    onDragStart: options.onDragStart,
    onDragDelta: options.onDragDelta,
    onDragEnd: options.onDragEnd,
  })

  const handleRendererResize = () => {
    const nextResolution = getPetRenderResolution()
    if (nextResolution === app.renderer.resolution) return
    app.renderer.resolution = nextResolution
    app.renderer.resize(stageW, stageH)
  }
  window.addEventListener('resize', handleRendererResize)

  /** @param {number} nextSize */
  function resizeStage(nextSize) {
    stageW = clampPetStageSize(nextSize)
    stageH = stageW
    screenScale = stageW / logicalSize
    viewport.scale.set(screenScale)
    app.renderer.resize(stageW, stageH)
  }

  return {
    app,
    model,
    playLockMotion,
    setExpressionByIndex,
    dispatchMenuAction,
    resizeStage,
    getToggleStates: () => ({ ...toggleStates }),
    pause() {
      app.ticker?.stop()
      if (app.view) {
        app.view.style.visibility = 'hidden'
      }
    },
    resume() {
      if (app.view) {
        app.view.style.visibility = 'visible'
      }
      app.ticker?.start()
    },
    destroy() {
      try {
        window.removeEventListener('resize', handleRendererResize)
        clearAllToggleFinishTimers()
        petDrag.destroy()
        input.destroy()

        if (typeof model.internalModel?.motionManager?.off === 'function') {
          model.internalModel.motionManager.off('motionFinish', onMotionFinish)
        }

        app.stage.removeChildren()
        model.destroy()
        scene.destroy({ children: true })
        viewport.destroy({ children: true })

        app.ticker?.stop()
        app.destroy(false, { children: true, texture: false, baseTexture: false })

        if (app.view?.parentNode === container) {
          container.removeChild(app.view)
        }
      } catch (error) {
        console.error('[PhrolovaPet] runtime destroy failed', error)
      }
    },
  }
}
