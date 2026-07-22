<template>
  <Teleport to="body">
    <div
      v-if="menu.visible"
      class="phro-context-menu-backdrop"
      @mousedown="menu.close()"
      @contextmenu.prevent="menu.close()"
    />
    <Transition
      name="phro-context-menu"
      :duration="BUBBLE_TRANSITION_MS"
      @after-leave="onAfterLeave"
    >
      <div
        v-if="menu.visible"
        ref="panelRef"
        class="phro-context-menu"
        :style="panelStyle"
        role="menu"
        @mousedown.stop
        @contextmenu.stop.prevent
      >
        <div class="phro-context-menu__shell">
          <div
            ref="bubbleRef"
            class="phro-context-menu__bubble"
            :class="{ 'is-clip-ready': isClipReady }"
            :style="bubbleStyle"
          >
            <button
              v-for="item in menu.items"
              :key="item.id ?? item.label"
              type="button"
              class="phro-context-menu__item"
              :class="{
                'phro-context-menu__item--danger': item.danger,
                'is-disabled': item.disabled,
              }"
              role="menuitem"
              :disabled="item.disabled"
              @click="menu.runItem(item)"
            >
              <el-icon v-if="itemIcon(item)" class="phro-context-menu__item-icon">
                <component :is="itemIcon(item)" />
              </el-icon>
              <span class="phro-context-menu__item-label">{{ item.label }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { CopyDocument, Select } from '@element-plus/icons-vue'
import { usePhroBubbleClip } from '@/composables/usePhroBubbleClip'
import { usePhroContextMenuStore } from '@/stores/phroContextMenu'

const ARROW_LEFT_DEFAULT = 18
const MENU_OFFSET_Y = 10
const BUBBLE_TRANSITION_MS = 200

const menu = usePhroContextMenuStore()
const panelRef = ref(null)
const bubbleRef = ref(null)
const panelX = ref(0)
const panelY = ref(0)
const arrowLeft = ref(ARROW_LEFT_DEFAULT)
const bubbleActive = ref(false)

const { clipStyle, scheduleSync, isClipReady } = usePhroBubbleClip(bubbleRef, {
  variant: 'top',
  arrow: arrowLeft,
  enabled: bubbleActive,
})

const panelStyle = computed(() => ({
  top: `${panelY.value}px`,
  left: `${panelX.value}px`,
  transformOrigin: `${arrowLeft.value}px 7px`,
}))

const bubbleStyle = computed(() => ({
  '--arrow-left': `${arrowLeft.value}px`,
  ...clipStyle.value,
}))

const ICON_MAP = {
  copy: CopyDocument,
  'select-all': Select,
}

/** @param {{ icon?: string }} item */
function itemIcon(item) {
  return item.icon ? ICON_MAP[item.icon] : null
}

watch(
  () => menu.visible,
  async (visible) => {
    if (!visible) return

    bubbleActive.value = true

    panelX.value = menu.x - ARROW_LEFT_DEFAULT
    panelY.value = menu.y + MENU_OFFSET_Y
    arrowLeft.value = ARROW_LEFT_DEFAULT

    await nextTick()
    const panel = panelRef.value
    if (!panel) return

    const rect = panel.getBoundingClientRect()
    const padding = 8
    let x = menu.x - ARROW_LEFT_DEFAULT
    let y = menu.y + MENU_OFFSET_Y
    let arrow = ARROW_LEFT_DEFAULT

    if (x + rect.width > window.innerWidth - padding) {
      x = Math.max(padding, window.innerWidth - rect.width - padding)
    }
    if (x < padding) {
      x = padding
    }
    if (y + rect.height > window.innerHeight - padding) {
      y = Math.max(padding, window.innerHeight - rect.height - padding)
    }

    arrow = Math.min(Math.max(menu.x - x, 14), Math.max(14, rect.width - 14))
    panelX.value = x
    panelY.value = y
    arrowLeft.value = arrow
    scheduleSync()
  },
)

function onAfterLeave() {
  if (menu.visible) return
  bubbleActive.value = false
  menu.clearContent()
}

function onKeyDown(event) {
  if (event.key === 'Escape' && menu.visible) {
    menu.close()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro-theme;

.phro-context-menu-backdrop {
  position: fixed;
  inset: 0;
  z-index: 4000;
}

.phro-context-menu {
  position: fixed;
  z-index: 4001;
  min-width: 128px;
  font-family: $font-family-phro;
  user-select: none;
  -webkit-user-select: none;
}

.phro-context-menu__shell {
  filter:
    drop-shadow(0 0 0 1px $phro-glass-border)
    drop-shadow(0 8px 28px rgba(20, 0, 8, 0.28));
}

.phro-context-menu__bubble {
  --arrow-left: 18px;
  --tail-size: 7px;
  @include phro-theme.phro-bubble-tail-top;
  filter: none;

  &::before {
    opacity: 1;
  }

  &:not(.is-clip-ready)::before {
    opacity: 0;
  }
}

.phro-context-menu__item {
  @include phro-theme.phro-btn-base;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  width: 100%;
  min-width: 112px;
  height: auto;
  margin: 0;
  padding: 9px 14px;
  font-size: 13px;
  line-height: 1.2;
  color: $phro-text-deep;
  background: $phro-btn-bg;
}

.phro-context-menu__item-icon {
  flex-shrink: 0;
  font-size: 14px;
  color: rgba($phro-gold, 0.82);
}

.phro-context-menu__item-label {
  min-width: 0;
}

.phro-context-menu__item--danger:not(:disabled) {
  border-color: rgba($phro-rose, 0.55);

  .phro-context-menu__item-icon {
    color: rgba($phro-rose, 0.9);
  }

  &:hover,
  &:focus-visible {
    border-color: rgba($phro-rose, 0.72);
    box-shadow:
      inset 3px 0 0 rgba($phro-rose, 0.85),
      0 0 0 1px rgba($phro-rose, 0.28);
  }

  &:active {
    border-color: rgba($phro-crimson, 0.65);
    box-shadow:
      inset 4px 0 0 $phro-rose,
      0 0 0 1px rgba($phro-rose, 0.32);
  }
}

.phro-context-menu__item.is-disabled,
.phro-context-menu__item:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>

<style lang="scss">
.phro-context-menu-enter-from,
.phro-context-menu-leave-to {
  opacity: 0;
  transform: translateY(-12px) scale(0.96);
}

.phro-context-menu-enter-from .phro-context-menu__bubble.is-clip-ready::before,
.phro-context-menu-leave-to .phro-context-menu__bubble.is-clip-ready::before {
  opacity: 0;
}

.phro-context-menu-enter-active,
.phro-context-menu-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.phro-context-menu-leave-active {
  pointer-events: none;
}

.phro-context-menu-enter-active .phro-context-menu__bubble::before,
.phro-context-menu-leave-active .phro-context-menu__bubble::before {
  transition: opacity 0.2s ease;
}
</style>
