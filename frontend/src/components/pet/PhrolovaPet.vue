<template>
  <div class="phrolova-pet-root">
    <div
      v-show="petStore.visible"
      ref="petRef"
      class="phrolova-pet"
      :class="{ 'phrolova-pet--dragging': isDragging }"
      :style="petStyle"
    >
      <div
        ref="stageRef"
        class="phrolova-pet__stage"
        :style="stageStyle"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createPhrolovaPetStage } from '@/utils/phrolovaPet'
import { levelToStageSize, readStoredSizeLevel } from '@/utils/phrolovaPetSize'
import { usePhrolovaPetStore } from '@/stores/phrolovaPet'

const STORAGE_POS = 'phro_pet_pos'

const petStore = usePhrolovaPetStore()
const pos = ref(loadPos())
const petRef = ref(null)
const stageRef = ref(null)

let petRuntime = null
let mountSeq = 0
const isDragging = ref(false)

const stageStyle = computed(() => ({
  width: `${petStore.stageSize}px`,
  height: `${petStore.stageSize}px`,
}))

const petStyle = computed(() => ({
  left: `${pos.value.x}px`,
  top: `${pos.value.y}px`,
  width: `${petStore.stageSize}px`,
  height: `${petStore.stageSize}px`,
}))

function loadPos() {
  try {
    const raw = localStorage.getItem(STORAGE_POS)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Number.isFinite(parsed.x) && Number.isFinite(parsed.y)) {
        return parsed
      }
    }
  } catch {
    // ignore
  }

  return {
    x: Math.max(16, window.innerWidth - levelToStageSize(readStoredSizeLevel()) - 40),
    y: Math.max(16, window.innerHeight - levelToStageSize(readStoredSizeLevel()) - 32),
  }
}

function savePos() {
  localStorage.setItem(STORAGE_POS, JSON.stringify(pos.value))
}

function bindRuntime(runtime) {
  petStore.setRuntime({
    playLockMotion: runtime.playLockMotion,
    setExpressionByIndex: runtime.setExpressionByIndex,
    dispatchMenuAction: runtime.dispatchMenuAction,
  })
}

watch(
  () => petStore.stageSize,
  (size) => {
    pos.value = clampPos(pos.value)
    savePos()
    petRuntime?.resizeStage?.(size)
  },
)

watch(
  () => petStore.visible,
  async (value) => {
    if (value) {
      await nextTick()
      if (petRuntime) {
        resumePet()
        return
      }
      await mountPet()
      return
    }

    pausePet()
    petStore.setLoadError('')
  },
)

function clampPos(next) {
  const size = petStore.stageSize
  const maxX = Math.max(8, window.innerWidth - size - 8)
  const maxY = Math.max(8, window.innerHeight - size - 8)
  return {
    x: Math.min(Math.max(8, next.x), maxX),
    y: Math.min(Math.max(8, next.y), maxY),
  }
}

function handleResize() {
  pos.value = clampPos(pos.value)
  savePos()
}

async function mountPet() {
  if (!stageRef.value || petRuntime) return

  const seq = mountSeq

  try {
    petStore.setLoadError('')
    const runtime = await createPhrolovaPetStage(stageRef.value, {
      stageSize: petStore.stageSize,
      onDragStart: () => {
        isDragging.value = true
      },
      onDragDelta: (dx, dy) => {
        pos.value = clampPos({
          x: pos.value.x + dx,
          y: pos.value.y + dy,
        })
      },
      onDragEnd: () => {
        isDragging.value = false
        savePos()
      },
      onToggleStatesChange: (states) => {
        petStore.setToggleStates(states)
      },
    })

    if (seq !== mountSeq) {
      runtime.destroy()
      return
    }

    petRuntime = runtime
    if (!petStore.visible) {
      runtime.pause()
      petStore.detachRuntime()
      return
    }
    bindRuntime(runtime)
  } catch (error) {
    if (seq !== mountSeq) return

    console.error('[PhrolovaPet] Live2D load failed', error)
    const message = error instanceof Error ? error.message : '桌宠加载失败'
    petStore.setLoadError(message)
    ElMessage.error('弗洛洛桌宠加载失败，请稍后重试')
  }
}

function pausePet() {
  if (!petRuntime) return

  try {
    petRuntime.pause()
  } catch (error) {
    console.error('[PhrolovaPet] pause failed', error)
  }

  petStore.detachRuntime()
}

function resumePet() {
  if (!petRuntime) return

  try {
    petRuntime.resume()
  } catch (error) {
    console.error('[PhrolovaPet] resume failed', error)
  }

  bindRuntime(petRuntime)
}

function destroyPet() {
  mountSeq += 1

  const runtime = petRuntime
  petRuntime = null
  petStore.clearRuntime()

  if (!runtime) return

  try {
    runtime.destroy()
  } catch (error) {
    console.error('[PhrolovaPet] destroy failed', error)
  }

  if (stageRef.value?.isConnected) {
    stageRef.value.replaceChildren()
  }
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  if (petStore.visible) {
    await nextTick()
    await mountPet()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  isDragging.value = false
  destroyPet()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-cursor.scss' as phro-cursor;

.phrolova-pet-root {
  position: fixed;
  inset: 0;
  z-index: 200;
  pointer-events: none;
}

.phrolova-pet {
  position: fixed;
  pointer-events: auto;
  background: transparent;
  @include phro-cursor.phro-cursor-grab;
  user-select: none;
  touch-action: none;

  &:not(.phrolova-pet--dragging) {
    transition: width 0.16s ease, height 0.16s ease;
  }
}

.phrolova-pet--dragging {
  @include phro-cursor.phro-cursor-grabbing;
}

.phrolova-pet__stage {
  display: block;
  overflow: visible;
  touch-action: none;
  @include phro-cursor.phro-cursor-grab;

  .phrolova-pet:not(.phrolova-pet--dragging) & {
    transition: width 0.16s ease, height 0.16s ease;
  }

  :deep(canvas) {
    display: block;
    background: transparent !important;
    cursor: inherit;
  }
}

.phrolova-pet--dragging .phrolova-pet__stage {
  @include phro-cursor.phro-cursor-grabbing;

  :deep(canvas) {
    cursor: inherit;
  }
}
</style>
