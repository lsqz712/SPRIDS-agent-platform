<template>
  <el-dialog
    :model-value="visible"
    title="裁剪头像"
    width="480px"
    class="phro-dialog phro-avatar-crop-dialog"
    append-to-body
    :close-on-click-modal="false"
    destroy-on-close
    @update:model-value="emit('update:visible', $event)"
    @opened="scheduleRender"
    @closed="handleClosed"
  >
    <p class="phro-dialog-desc">拖动图片调整位置，滚轮或滑块缩放，裁剪区域为圆形头像。</p>

    <div class="phro-avatar-crop" :class="{ 'is-loading': loading }">
      <div
        ref="stageRef"
        class="phro-avatar-crop-stage"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
        @pointerleave="onPointerUp"
        @wheel.prevent="onWheel"
      >
        <canvas
          ref="canvasRef"
          class="phro-avatar-crop-canvas"
          :width="CROP_VIEWPORT_SIZE"
          :height="CROP_VIEWPORT_SIZE"
        />
        <div class="phro-avatar-crop-mask" aria-hidden="true" />
        <div class="phro-avatar-crop-ring" aria-hidden="true" />
        <div v-if="loading" class="phro-avatar-crop-loading">图片加载中…</div>
      </div>

      <div class="phro-avatar-crop-toolbar">
        <div class="phro-avatar-crop-zoom">
          <span class="label">缩放</span>
          <input
            v-model.number="zoom"
            class="phro-avatar-crop-slider"
            type="range"
            min="1"
            max="3"
            step="0.01"
            @input="render"
          />
        </div>

        <div class="phro-avatar-crop-preview-wrap">
          <span class="label">预览</span>
          <canvas
            ref="previewRef"
            class="phro-avatar-crop-preview"
            :width="88"
            :height="88"
          />
        </div>
      </div>
    </div>

    <template #footer>
      <div class="phro-dialog__footer">
        <button type="button" class="phro-btn" :disabled="confirming" @click="emit('update:visible', false)">
          取消
        </button>
        <button
          type="button"
          class="phro-btn phro-btn--primary"
          :disabled="loading || confirming || !image"
          @click="handleConfirm"
        >
          {{ confirming ? '处理中…' : '确认上传' }}
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import {
  CROP_VIEWPORT_SIZE,
  clampCropOffset,
  computeBaseScale,
  cropAvatarToBlob,
  drawCropViewport,
  loadImageFromSrc,
} from '@/utils/avatarCrop'

const props = defineProps({
  visible: { type: Boolean, default: false },
  imageSrc: { type: String, default: '' },
})

const emit = defineEmits(['update:visible', 'confirm'])

const loading = ref(false)
const confirming = ref(false)
const image = ref(null)
const baseScale = ref(1)
const zoom = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)
const canvasRef = ref(null)
const previewRef = ref(null)
const stageRef = ref(null)

const dragging = ref(false)
const dragStart = ref({ x: 0, y: 0, offsetX: 0, offsetY: 0 })

function currentScale() {
  return baseScale.value * zoom.value
}

function currentState() {
  return {
    scale: currentScale(),
    offsetX: offsetX.value,
    offsetY: offsetY.value,
  }
}

function applyOffset(nextX, nextY) {
  if (!image.value) return
  const clamped = clampCropOffset(image.value, currentScale(), nextX, nextY)
  offsetX.value = clamped.offsetX
  offsetY.value = clamped.offsetY
}

function render() {
  if (!image.value) return

  const state = currentState()
  const mainCtx = canvasRef.value?.getContext('2d')
  if (mainCtx) {
    drawCropViewport(mainCtx, image.value, state)
  }

  cropAvatarToBlob(image.value, state, { outputSize: 88, quality: 0.9 })
    .then((blob) => {
      const previewCtx = previewRef.value?.getContext('2d')
      if (!previewCtx) return
      const url = URL.createObjectURL(blob)
      const previewImage = new Image()
      previewImage.onload = () => {
        previewCtx.clearRect(0, 0, 88, 88)
        previewCtx.drawImage(previewImage, 0, 0, 88, 88)
        URL.revokeObjectURL(url)
      }
      previewImage.src = url
    })
    .catch(() => {})
}

function scheduleRender() {
  nextTick(() => {
    render()
  })
}

function resetTransform() {
  zoom.value = 1
  offsetX.value = 0
  offsetY.value = 0
}

async function loadImage(src) {
  if (!src) {
    image.value = null
    return
  }

  loading.value = true
  try {
    const loaded = await loadImageFromSrc(src)
    image.value = loaded
    baseScale.value = computeBaseScale(loaded.width, loaded.height)
    resetTransform()
  } finally {
    loading.value = false
    scheduleRender()
  }
}

function onPointerDown(event) {
  if (!image.value || loading.value) return
  dragging.value = true
  dragStart.value = {
    x: event.clientX,
    y: event.clientY,
    offsetX: offsetX.value,
    offsetY: offsetY.value,
  }
  stageRef.value?.setPointerCapture?.(event.pointerId)
}

function onPointerMove(event) {
  if (!dragging.value) return
  const dx = event.clientX - dragStart.value.x
  const dy = event.clientY - dragStart.value.y
  applyOffset(dragStart.value.offsetX + dx, dragStart.value.offsetY + dy)
  render()
}

function onPointerUp(event) {
  if (!dragging.value) return
  dragging.value = false
  stageRef.value?.releasePointerCapture?.(event.pointerId)
}

function onWheel(event) {
  if (!image.value) return
  const delta = event.deltaY > 0 ? -0.08 : 0.08
  zoom.value = Math.min(3, Math.max(1, Number((zoom.value + delta).toFixed(2))))
  applyOffset(offsetX.value, offsetY.value)
  render()
}

async function handleConfirm() {
  if (!image.value || confirming.value) return
  confirming.value = true
  try {
    const blob = await cropAvatarToBlob(image.value, currentState())
    emit('confirm', blob)
    emit('update:visible', false)
  } finally {
    confirming.value = false
  }
}

function handleClosed() {
  dragging.value = false
  image.value = null
  resetTransform()
}

watch(
  () => [props.visible, props.imageSrc],
  ([visible, src]) => {
    if (visible && src) {
      loadImage(src)
    }
  },
  { immediate: true },
)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;
@use '@/assets/styles/phro-cursor.scss' as phro-cursor;

.phro-avatar-crop-loading {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba($phro-panel-bg, 0.82);
  font-size: 13px;
  color: $phro-text-mid;
}

.phro-avatar-crop.is-loading .phro-avatar-crop-stage {
  pointer-events: none;
}

.phro-avatar-crop {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.phro-avatar-crop-stage {
  position: relative;
  width: 280px;
  height: 280px;
  margin: 0 auto;
  border-radius: $phro-radius;
  overflow: hidden;
  @include phro-cursor.phro-cursor-grab;
  touch-action: none;
  user-select: none;
  @include phro.phro-module-box;
}

.phro-avatar-crop-canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.phro-avatar-crop-mask {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at center, transparent 138px, rgba(40, 8, 16, 0.42) 139px);
}

.phro-avatar-crop-ring {
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: 50%;
  width: 276px;
  height: 276px;
  margin: auto;
  border: 2px solid rgba($phro-gold, 0.75);
  box-shadow:
    0 0 0 1px rgba($phro-gold, 0.25),
    inset 0 0 0 1px rgba($phro-cream, 0.35);
}

.phro-avatar-crop-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 4px;
}

.phro-avatar-crop-zoom {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;

  .label {
    flex-shrink: 0;
    font-size: 12px;
    color: $phro-text-mid;
  }
}

.phro-avatar-crop-slider {
  flex: 1;
  min-width: 0;
  accent-color: $phro-rose;
  cursor: pointer;
}

.phro-avatar-crop-preview-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;

  .label {
    font-size: 12px;
    color: $phro-text-mid;
  }
}

.phro-avatar-crop-preview {
  display: block;
  width: 88px;
  height: 88px;
  border-radius: 50%;
  border: 2px solid rgba($phro-gold, 0.55);
  background: $phro-panel-bg;
}
</style>

<style lang="scss">
.phro-avatar-crop-dialog.el-dialog {
  .el-dialog__body {
    padding-bottom: 12px;
  }
}
</style>
