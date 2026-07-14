import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  buildBubbleClipPathLeft,
  buildBubbleClipPathTop,
} from '@/utils/phroBubbleClipPath'

/**
 * 维护气泡尺寸并在 clipStyle 中输出 --bubble-clip（由 Vue :style 绑定，避免被覆盖）
 * @param {import('vue').Ref<HTMLElement | null>} bubbleRef
 * @param {{
 *   variant: 'top' | 'left'
 *   arrow: import('vue').Ref<number>
 *   enabled?: import('vue').Ref<boolean> | (() => boolean)
 * }} options
 */
export function usePhroBubbleClip(bubbleRef, { variant, arrow, enabled = () => true }) {
  const metrics = ref({ width: 0, height: 0 })
  /** @type {ResizeObserver | null} */
  let resizeObserver = null

  function isEnabled() {
    return typeof enabled === 'function' ? enabled() : enabled.value
  }

  function syncMetrics() {
    const el = bubbleRef.value
    if (!el || !isEnabled()) return

    const width = el.offsetWidth
    const height = el.offsetHeight
    if (width <= 0 || height <= 0) return

    metrics.value = { width, height }
  }

  function bindObserver() {
    resizeObserver?.disconnect()
    const el = bubbleRef.value
    if (!el || !isEnabled()) return

    resizeObserver = new ResizeObserver(syncMetrics)
    resizeObserver.observe(el)
    syncMetrics()
  }

  function unbindObserver() {
    resizeObserver?.disconnect()
    resizeObserver = null
    metrics.value = { width: 0, height: 0 }
  }

  function scheduleSync() {
    nextTick(() => {
      syncMetrics()
      requestAnimationFrame(syncMetrics)
    })
  }

  const clipStyle = computed(() => {
    const { width, height } = metrics.value
    if (width <= 0 || height <= 0) return {}

    const clip =
      variant === 'top'
        ? buildBubbleClipPathTop(width, height, arrow.value)
        : buildBubbleClipPathLeft(width, height, arrow.value)

    return { '--bubble-clip': clip }
  })

  watch(
    bubbleRef,
    (el) => {
      if (el && isEnabled()) {
        bindObserver()
        syncMetrics()
        scheduleSync()
      } else {
        unbindObserver()
      }
    },
    { immediate: true },
  )

  watch(arrow, scheduleSync)

  if (enabled && typeof enabled !== 'function' && 'value' in enabled) {
    watch(enabled, (visible) => {
      if (visible) {
        bindObserver()
        scheduleSync()
      } else {
        unbindObserver()
      }
    })
  }

  onMounted(scheduleSync)

  onUnmounted(unbindObserver)

  const isClipReady = computed(
    () => metrics.value.width > 0 && metrics.value.height > 0,
  )

  return { clipStyle, scheduleSync, syncMetrics, isClipReady }
}
