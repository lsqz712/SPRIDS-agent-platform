<template>
  <div
    ref="feixunPageRef"
    class="feixun-page"
    :class="{ 'feixun-page--dragging': isPageDragging }"
  >
    <div
      class="feixun-page-drag-surface"
      aria-hidden="true"
      @pointerdown="handlePageBackgroundPointerDown"
    />
    <div
      class="feixun-windows-host"
      :class="{ 'feixun-windows-host--sticky': windowsStore.isStickyLayout }"
    >
      <FeixunWindow
        v-for="window in openWindows"
        :key="window.id"
        :ref="(el) => setWindowRef(window.id, el)"
        :window-id="window.id"
        :is-focused="window.id === windowsStore.focusedWindowId"
        @focus="handleWindowFocus(window.id)"
        @dragging-change="handleDraggingChange(window.id, $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import FeixunWindow from '@/components/feixun/FeixunWindow.vue'
import {
  isPointInsideAnyWindowShell,
} from '@/components/feixun/feixunWindowHit'
import {
  enableDragNoSelect,
  disableDragNoSelect,
  FRAME_GROUP_DRAG_THRESHOLD,
} from '@/components/feixun/feixunPageDrag'
import { useFeixunWindowsStore } from '@/stores/feixunWindows'

const windowsStore = useFeixunWindowsStore()

const feixunPageRef = ref(null)
const windowRefs = ref({})
const isPageDragging = ref(false)
const frameDragState = ref(null)

const openWindows = computed(() => windowsStore.openWindows)

function setWindowRef(windowId, el) {
  if (el) {
    windowRefs.value[windowId] = el
    return
  }
  delete windowRefs.value[windowId]
}

function handleWindowFocus(windowId) {
  windowsStore.focusWindow(windowId)
}

function handleDraggingChange(windowId, dragging) {
  if (frameDragState.value?.active) return
  if (windowId === windowsStore.focusedWindowId) {
    isPageDragging.value = dragging
  }
}

function snapshotFrameOrigins() {
  return Object.fromEntries(
    windowsStore.openWindows.map((window) => [window.id, { ...window.offset }]),
  )
}

function stopFrameGroupDrag(event) {
  const state = frameDragState.value
  if (!state) return
  if (event && event.pointerId !== state.pointerId) return

  if (state.active) {
    windowsStore.roundAllWindowOffsets()
  }

  disableDragNoSelect()

  const page = feixunPageRef.value
  if (page?.hasPointerCapture?.(state.pointerId)) {
    page.releasePointerCapture(state.pointerId)
  }

  frameDragState.value = null
  isPageDragging.value = false
  document.removeEventListener('pointermove', handleFrameGroupDragMove)
  document.removeEventListener('pointerup', stopFrameGroupDrag)
  document.removeEventListener('pointercancel', stopFrameGroupDrag)
}

function handleFrameGroupDragMove(event) {
  const state = frameDragState.value
  if (!state || event.pointerId !== state.pointerId) return

  const dx = event.clientX - state.startX
  const dy = event.clientY - state.startY

  if (!state.active) {
    if (Math.hypot(dx, dy) < FRAME_GROUP_DRAG_THRESHOLD) return
    state.active = true
    isPageDragging.value = true
  }

  event.preventDefault()
  windowsStore.translateAllWindowOffsets(state.origins, dx, dy)
}

function startFrameGroupDrag(event) {
  const page = feixunPageRef.value
  if (!page) return

  frameDragState.value = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    origins: snapshotFrameOrigins(),
    active: false,
  }

  enableDragNoSelect()
  page.setPointerCapture(event.pointerId)
  document.addEventListener('pointermove', handleFrameGroupDragMove)
  document.addEventListener('pointerup', stopFrameGroupDrag)
  document.addEventListener('pointercancel', stopFrameGroupDrag)
}

function handlePageBackgroundPointerDown(event) {
  if (event.button !== 0) return

  if (windowsStore.isStickyLayout && isPointInsideAnyWindowShell(event.clientX, event.clientY)) {
    return
  }

  if (!windowsStore.openWindows.length) return

  event.preventDefault()

  if (windowsStore.isStickyLayout) {
    const focusedId = windowsStore.focusedWindowId
    if (!focusedId) return
    windowRefs.value[focusedId]?.startPageDrag?.(event)
    return
  }

  startFrameGroupDrag(event)
}

function syncAllWindowMetrics() {
  Object.values(windowRefs.value).forEach((windowRef) => {
    windowRef?.syncWindowLayoutMetrics?.()
  })
}

async function prepareStickyLayout() {
  syncAllWindowMetrics()
  await nextTick()
  syncAllWindowMetrics()
  await nextTick()
  windowsStore.setLayoutPageEl(feixunPageRef.value)
  return feixunPageRef.value
}

watch(
  () => windowsStore.layoutMode,
  async (mode) => {
    await nextTick()
    if (mode === 'sticky') {
      windowsStore.setLayoutPageEl(feixunPageRef.value)
      windowsStore.recomputeStickyFanLayout(feixunPageRef.value)
      return
    }
    syncAllWindowMetrics()
    await nextTick()
    syncAllWindowMetrics()
  },
)

onMounted(() => {
  windowsStore.ensureInitialWindow()
  windowsStore.setLayoutPrepareHook(prepareStickyLayout)
  windowsStore.setLayoutPageEl(feixunPageRef.value)
  if (windowsStore.isStickyLayout) {
    windowsStore.recomputeStickyFanLayout(feixunPageRef.value)
  }
})

onUnmounted(() => {
  stopFrameGroupDrag()
  windowsStore.setLayoutPrepareHook(null)
})
</script>

<style lang="scss" scoped>

.feixun-page {
  position: relative;
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 12px 20px;
  box-sizing: border-box;
  overflow: hidden;
  font-family: $font-family-phro;

  &.feixun-page--dragging {
    user-select: none;

    * {
      user-select: none !important;
      -webkit-user-select: none !important;
    }
  }
}

.feixun-page-drag-surface {
  position: absolute;
  inset: 0;
  z-index: 0;
  cursor: grab;
  touch-action: none;

  .feixun-page--dragging & {
    cursor: grabbing;
  }
}

.feixun-windows-host {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  isolation: isolate;
}
</style>
