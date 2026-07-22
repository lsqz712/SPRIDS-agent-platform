<template>
  <div ref="wrapRef" class="bbox-canvas-wrap">
    <img
      v-if="imageSrc"
      ref="imgRef"
      :src="imageSrc"
      class="bbox-image"
      alt="检测图像"
      @load="redraw"
    />
    <canvas ref="canvasRef" class="bbox-overlay" />
    <div v-if="!imageSrc" class="bbox-placeholder">
      <el-icon><Picture /></el-icon>
      <span>上传图像后在此预览检测结果</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { Picture } from '@element-plus/icons-vue'
import { DEFECT_COLORS } from '@/constants/pcbDefects'

const props = defineProps({
  imageSrc: { type: String, default: '' },
  detections: { type: Array, default: () => [] },
  activeIndex: { type: Number, default: -1 },
})

const wrapRef = ref(null)
const imgRef = ref(null)
const canvasRef = ref(null)
let ro = null

function redraw() {
  const wrap = wrapRef.value
  const img = imgRef.value
  const canvas = canvasRef.value
  if (!wrap || !canvas) return

  const w = wrap.clientWidth
  const h = wrap.clientHeight
  if (w < 2 || h < 2) return

  canvas.width = w
  canvas.height = h

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, w, h)

  if (!img?.complete || !img.naturalWidth) return

  const scale = Math.min(w / img.naturalWidth, h / img.naturalHeight)
  const drawW = img.naturalWidth * scale
  const drawH = img.naturalHeight * scale
  const offsetX = (w - drawW) / 2
  const offsetY = (h - drawH) / 2

  props.detections.forEach((det, index) => {
    const [x1, y1, x2, y2] = det.bbox || []
    if (x1 == null) return

    const sx1 = offsetX + x1 * scale
    const sy1 = offsetY + y1 * scale
    const sw = (x2 - x1) * scale
    const sh = (y2 - y1) * scale
    const color = DEFECT_COLORS[det.class_name] || '#e74c3c'
    const active = index === props.activeIndex

    ctx.strokeStyle = color
    ctx.lineWidth = active ? 3 : 2
    ctx.fillStyle = active ? `${color}33` : `${color}22`
    ctx.fillRect(sx1, sy1, sw, sh)
    ctx.strokeRect(sx1, sy1, sw, sh)

    const label = `${det.class_name_cn || det.class_name} ${(det.confidence * 100).toFixed(0)}%`
    ctx.font = '12px "Noto Sans SC", sans-serif'
    const tw = ctx.measureText(label).width + 8
    ctx.fillStyle = color
    ctx.fillRect(sx1, Math.max(0, sy1 - 18), tw, 18)
    ctx.fillStyle = '#fff'
    ctx.fillText(label, sx1 + 4, Math.max(12, sy1 - 5))
  })
}

watch(
  () => [props.imageSrc, props.detections, props.activeIndex],
  () => requestAnimationFrame(redraw),
  { deep: true },
)

onMounted(() => {
  ro = new ResizeObserver(() => redraw())
  if (wrapRef.value) ro.observe(wrapRef.value)
  redraw()
})

onBeforeUnmount(() => {
  ro?.disconnect()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.bbox-canvas-wrap {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-height: 240px;
  border-radius: $phro-radius-sm;
  overflow: hidden;
  background: rgba($phro-rose, 0.06);
}

.bbox-image {
  position: absolute;
  inset: 0;
  margin: auto;
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
  display: block;
}

.bbox-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.bbox-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: $phro-text-mid;
  font-size: 13px;

  .el-icon {
    font-size: 40px;
    color: $phro-gold;
  }
}
</style>
