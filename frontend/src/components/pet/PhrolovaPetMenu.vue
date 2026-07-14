<template>
  <Teleport to="body">
    <div
      v-if="petStore.menuOpen"
      class="phrolova-pet-menu-panel"
      :class="{ 'phrolova-pet-menu-panel--dragging': isDragging }"
      :style="panelStyle"
    >
      <header
        class="phrolova-pet-menu-panel__head"
        @pointerdown="onDragStart"
      >
        <span class="phrolova-pet-menu-panel__title">桌宠控制</span>
        <button
          type="button"
          class="phrolova-pet-menu-panel__close"
          title="关闭"
          @pointerdown.stop
          @click="petStore.closeMenu()"
        >
          ×
        </button>
      </header>

      <div class="phrolova-pet-menu-panel__body">
        <div class="phrolova-pet-menu-panel__columns">
          <div
            v-for="(columnSections, columnIndex) in menuColumns"
            :key="columnIndex"
            class="phrolova-pet-menu-panel__column"
          >
            <section
              v-for="section in columnSections"
              :key="section.id"
              class="phrolova-pet-menu-panel__section"
            >
              <h4 class="phrolova-pet-menu-panel__section-title">{{ section.title }}</h4>
              <div class="phrolova-pet-menu-panel__list">
                <button
                  v-for="item in section.items"
                  :key="item.id"
                  type="button"
                  class="phrolova-pet-menu-panel__chip"
              :class="{
                'phrolova-pet-menu-panel__chip--toggle': item.kind === 'toggle',
                'phrolova-pet-menu-panel__chip--reset': item.kind === 'reset',
                'is-on': item.kind === 'toggle' && isToggleOn(item),
              }"
                  :disabled="!canControl"
                  :title="chipTitle(item)"
                  @click="handleAction(item)"
                >
                  <template v-if="item.kind === 'toggle'">
                    <span class="phrolova-pet-menu-panel__chip-label">{{ item.label }}</span>
                    <span class="phrolova-pet-menu-panel__chip-state">
                      {{ isToggleOn(item) ? '开' : '关' }}
                    </span>
                  </template>
                  <template v-else>
                    {{ item.label }}
                  </template>
                </button>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { PHROLOVA_PET_MENU_SECTIONS } from '@/utils/phrolovaPetMenu'
import { usePhrolovaPetStore } from '@/stores/phrolovaPet'

const STORAGE_POS = 'phro_pet_menu_pos'
const PANEL_WIDTH = 300
const DRAG_THRESHOLD = 4

const LEFT_SECTION_IDS = ['decoration', 'animation']
const RIGHT_SECTION_IDS = ['expression', 'form', 'settings']

const menuColumns = computed(() => {
  const left = PHROLOVA_PET_MENU_SECTIONS.filter((section) => LEFT_SECTION_IDS.includes(section.id))
  const right = PHROLOVA_PET_MENU_SECTIONS.filter((section) => RIGHT_SECTION_IDS.includes(section.id))
  return [left, right]
})

const petStore = usePhrolovaPetStore()
const pos = ref(loadPos())
const isDragging = ref(false)

/** @type {{ pointerId: number, startX: number, startY: number, lastX: number, lastY: number, originX: number, originY: number, moved: boolean } | null} */
let dragSession = null

const canControl = computed(() => petStore.visible && !!petStore.runtime)

/** @param {import('@/utils/phrolovaPetMenu').PhrolovaPetMenuAction} item */
function isToggleOn(item) {
  if (item.kind !== 'toggle') return false
  return petStore.toggleStates[item.id] ?? item.defaultOn !== false
}

/** @param {import('@/utils/phrolovaPetMenu').PhrolovaPetMenuAction} item */
function chipTitle(item) {
  if (item.hint) return item.hint
  if (item.kind === 'toggle') {
    return `${item.label}：${isToggleOn(item) ? '开（点击关闭）' : '关（点击开启）'}`
  }
  return item.label
}

const panelStyle = computed(() => ({
  left: `${pos.value.x}px`,
  top: `${pos.value.y}px`,
  width: `${PANEL_WIDTH}px`,
}))

function loadPos() {
  try {
    const raw = localStorage.getItem(STORAGE_POS)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Number.isFinite(parsed.x) && Number.isFinite(parsed.y)) {
        return clampPos(parsed)
      }
    }
  } catch {
    // ignore
  }

  return defaultPos()
}

function defaultPos() {
  const rightReserve = 220
  return clampPos({
    x: Math.max(218, window.innerWidth - PANEL_WIDTH - rightReserve - 16),
    y: Math.max(16, window.innerHeight - 480),
  })
}

function clampPos(next) {
  const rightReserve = 220
  const maxX = Math.max(8, window.innerWidth - PANEL_WIDTH - rightReserve)
  const maxY = Math.max(8, window.innerHeight - 120)
  return {
    x: Math.min(Math.max(8, next.x), maxX),
    y: Math.min(Math.max(8, next.y), maxY),
  }
}

function savePos() {
  localStorage.setItem(STORAGE_POS, JSON.stringify(pos.value))
}

function clearDragListeners() {
  window.removeEventListener('pointermove', onWindowPointerMove)
  window.removeEventListener('pointerup', onWindowPointerUp)
  window.removeEventListener('pointercancel', onWindowPointerUp)
}

function onWindowPointerMove(event) {
  if (!dragSession || event.pointerId !== dragSession.pointerId) return

  if (!dragSession.moved) {
    const totalDx = event.clientX - dragSession.startX
    const totalDy = event.clientY - dragSession.startY
    if (Math.hypot(totalDx, totalDy) < DRAG_THRESHOLD) return
    dragSession.moved = true
    isDragging.value = true
  }

  event.preventDefault()
  dragSession.lastX = event.clientX
  dragSession.lastY = event.clientY
  pos.value = clampPos({
    x: dragSession.originX + (event.clientX - dragSession.startX),
    y: dragSession.originY + (event.clientY - dragSession.startY),
  })
}

function onWindowPointerUp(event) {
  if (!dragSession || event.pointerId !== dragSession.pointerId) return

  if (dragSession.moved) {
    savePos()
  }

  clearDragListeners()
  dragSession = null
  isDragging.value = false
}

/** @param {PointerEvent} event */
function onDragStart(event) {
  if (event.button !== 0) return

  dragSession = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    lastX: event.clientX,
    lastY: event.clientY,
    originX: pos.value.x,
    originY: pos.value.y,
    moved: false,
  }

  window.addEventListener('pointermove', onWindowPointerMove)
  window.addEventListener('pointerup', onWindowPointerUp)
  window.addEventListener('pointercancel', onWindowPointerUp)
}

function handleResize() {
  pos.value = clampPos(pos.value)
  savePos()
}

/** @param {import('@/utils/phrolovaPetMenu').PhrolovaPetMenuAction} action */
function handleAction(action) {
  if (!petStore.visible) {
    ElMessage.warning('请先显示桌宠')
    return
  }
  if (!petStore.runtime) {
    ElMessage.warning('桌宠正在加载，请稍后再试')
    return
  }

  petStore.runMenuAction(action)
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  clearDragListeners()
  dragSession = null
  isDragging.value = false
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
@use '@/assets/styles/phro-theme.scss' as phro;
@use '@/assets/styles/phro-cursor.scss' as phro-cursor;

.phrolova-pet-menu-panel {
  position: fixed;
  z-index: 210;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  pointer-events: auto;
  font-family: $font-family-phro;
  @include phro.phro-glass-window;
  box-shadow: 0 8px 28px rgba(40, 0, 12, 0.28);
}

.phrolova-pet-menu-panel--dragging {
  user-select: none;

  .phrolova-pet-menu-panel__head {
    @include phro-cursor.phro-cursor-grabbing;
  }
}

.phrolova-pet-menu-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-shrink: 0;
  padding: 8px 10px;
  border-bottom: 1px solid rgba($phro-gold, 0.18);
  @include phro-cursor.phro-cursor-grab;
  touch-action: none;
}

.phrolova-pet-menu-panel__title {
  font-size: 12px;
  font-weight: 600;
  color: $phro-cream;
  letter-spacing: 0.04em;
  text-shadow: 0 1px 6px rgba(20, 0, 8, 0.55);
}

.phrolova-pet-menu-panel__close {
  width: 22px;
  height: 22px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: $phro-cream-muted;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;

  &:hover {
    color: $phro-cream;
    background: rgba($phro-gold, 0.18);
  }
}

.phrolova-pet-menu-panel__body {
  padding: 8px 10px 10px;
}

.phrolova-pet-menu-panel__columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  align-items: stretch;
}

.phrolova-pet-menu-panel__column {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  height: 100%;
}

.phrolova-pet-menu-panel__section + .phrolova-pet-menu-panel__section {
  margin-top: 0;
}

.phrolova-pet-menu-panel__section-title {
  margin: 0 0 4px;
  font-size: 11px;
  font-weight: 600;
  color: $phro-gold-light;
  letter-spacing: 0.04em;
  text-shadow: 0 1px 4px rgba(20, 0, 8, 0.45);
}

.phrolova-pet-menu-panel__list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.phrolova-pet-menu-panel__chip {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 5px 8px;
  border: 1px solid rgba($phro-gold, 0.2);
  border-radius: 6px;
  background: rgba($phro-panel-bg, 0.9);
  color: $phro-text-deep;
  font-size: 11px;
  line-height: 1.3;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;

  &:hover:not(:disabled) {
    border-color: rgba($phro-gold, 0.45);
    background: rgba($phro-panel-bg, 1);
  }

  &--toggle {
    justify-content: space-between;
  }

  &--reset {
    justify-content: center;
    color: $phro-text-mid;
  }

  &.is-on {
    border-color: rgba($phro-gold, 0.55);
    box-shadow: inset 2px 0 0 rgba($phro-gold, 0.85);
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}

.phrolova-pet-menu-panel__chip-label {
  font-size: 11px;
}

.phrolova-pet-menu-panel__chip-state {
  min-width: 14px;
  font-size: 10px;
  font-weight: 600;
  color: $phro-text-mid;
  text-align: right;

  .is-on & {
    color: rgba($phro-gold, 0.95);
  }
}
</style>
