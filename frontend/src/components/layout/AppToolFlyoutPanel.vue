<template>
  <aside
    ref="rootRef"
    class="app-tool-flyout"
    :class="{ 'is-layout-stable': layoutStable }"
    :style="flyoutStyle"
    aria-label="工具子菜单"
  >
    <div class="app-tool-flyout__shell">
      <div
        ref="bubbleRef"
        class="app-tool-flyout__bubble"
        :class="{ 'is-clip-ready': isClipReady }"
        :style="bubbleStyle"
      >
      <template v-if="section === 'feixun'">
          <button
            type="button"
            class="app-tool-flyout__item"
            @click="openNewFeixunWindow"
          >
            <el-icon class="app-tool-flyout__item-icon">
              <CopyDocument />
            </el-icon>
            <span class="app-tool-flyout__item-label">新建窗口</span>
          </button>

          <button
            type="button"
            class="app-tool-flyout__item"
            @click="toggleFeixunLayoutMode"
          >
            <el-icon class="app-tool-flyout__item-icon">
              <Memo />
            </el-icon>
            <span class="app-tool-flyout__item-label">
              {{ windowsStore.isStickyLayout ? '切换为浮窗' : '切换为便签' }}
            </span>
          </button>
        </template>

        <template v-else-if="section === 'pet'">
          <div class="app-tool-flyout__pet-body">
            <div class="app-tool-flyout__pet-columns">
              <div
                v-for="(columnSections, columnIndex) in petMenuColumns"
                :key="columnIndex"
                class="app-tool-flyout__pet-column"
                :class="{ 'app-tool-flyout__pet-column--left': columnIndex === 0 }"
              >
                <section
                  v-for="menuSection in columnSections"
                  :key="menuSection.id"
                  class="app-tool-flyout__pet-section"
                >
                  <h4 class="app-tool-flyout__section-title">{{ menuSection.title }}</h4>
                  <div class="app-tool-flyout__pet-list">
                    <button
                      v-for="item in menuSection.items"
                      :key="item.id"
                      type="button"
                      class="app-tool-flyout__chip"
                      :class="{
                        'app-tool-flyout__chip--toggle': item.kind === 'toggle',
                        'app-tool-flyout__chip--reset': item.kind === 'reset',
                        'is-on': item.kind === 'toggle' && isPetToggleOn(item),
                      }"
                      :disabled="!canControlPet"
                      :title="petChipTitle(item)"
                      @click="handlePetAction(item)"
                    >
                      <template v-if="item.kind === 'toggle'">
                        <span class="app-tool-flyout__chip-label">{{ item.label }}</span>
                        <span class="app-tool-flyout__chip-state">
                          {{ isPetToggleOn(item) ? '开' : '关' }}
                        </span>
                      </template>
                      <template v-else>
                        {{ item.label }}
                      </template>
                    </button>
                  </div>
                </section>

                <section
                  v-if="columnIndex === 0"
                  class="app-tool-flyout__pet-section app-tool-flyout__pet-section--visibility"
                >
                  <h4 class="app-tool-flyout__section-title">隐藏</h4>
                  <div class="app-tool-flyout__pet-list">
                    <button
                      type="button"
                      class="app-tool-flyout__chip app-tool-flyout__chip--visibility"
                      :class="{ 'is-on': petStore.visible }"
                      @click="petStore.toggle()"
                    >
                      <span class="app-tool-flyout__chip-label">
                        {{ petStore.visible ? '隐藏桌宠' : '显示桌宠' }}
                      </span>
                    </button>
                  </div>
                </section>
              </div>
            </div>

            <section class="app-tool-flyout__pet-section app-tool-flyout__pet-section--size">
              <h4 class="app-tool-flyout__section-title">大小</h4>
              <input
                type="range"
                class="app-tool-flyout__pet-size-slider"
                min="0"
                max="100"
                step="1"
                :value="petStore.sizeLevel"
                aria-label="桌宠大小"
                @input="onPetSizeLevelInput"
              />
            </section>
          </div>
        </template>

        <template v-else>
          <button
            type="button"
            class="app-tool-flyout__item"
            :class="{ 'is-active': isProfileRoute }"
            @click="goToProfile"
          >
            <el-icon class="app-tool-flyout__item-icon">
              <User />
            </el-icon>
            <span class="app-tool-flyout__item-label">个人中心</span>
          </button>

          <button
            type="button"
            class="app-tool-flyout__item app-tool-flyout__item--danger"
            @click="confirmLogout"
          >
            <el-icon class="app-tool-flyout__item-icon">
              <SwitchButton />
            </el-icon>
            <span class="app-tool-flyout__item-label">退出登录</span>
          </button>
        </template>
      </div>
    </div>
  </aside>
</template>

<script setup>
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  CopyDocument,
  Memo,
  User,
  SwitchButton,
} from '@element-plus/icons-vue'
import {
  computeFlyoutLayout,
  defaultPanelHeight,
  FLYOUT_WIDTH,
} from '@/utils/appToolFlyoutLayout'
import { usePhroBubbleClip } from '@/composables/usePhroBubbleClip'
import { PHROLOVA_PET_MENU_SECTIONS, buildDefaultToggleStates } from '@/utils/phrolovaPetMenu'
import { showPhroConfirm } from '@/utils/phroMessageBox'
import { useAppToolMenuStore } from '@/stores/appToolMenu'
import { useFeixunWindowsStore } from '@/stores/feixunWindows'
import { usePhrolovaPetStore } from '@/stores/phrolovaPet'
import { useUserStore } from '@/stores/user'

/** @typedef {'feixun' | 'pet' | 'user'} AppToolMenuSection */

const LEFT_PET_SECTION_IDS = ['decoration', 'animation']
const RIGHT_PET_SECTION_IDS = ['expression', 'form', 'settings']

const props = defineProps({
  section: {
    /** @type {import('vue').PropType<AppToolMenuSection>} */
    type: String,
    required: true,
  },
})

const route = useRoute()
const router = useRouter()
const toolMenu = useAppToolMenuStore()
const windowsStore = useFeixunWindowsStore()
const petStore = usePhrolovaPetStore()
const userStore = useUserStore()

const rootRef = ref(null)
const bubbleRef = ref(null)
const panelHeight = ref(defaultPanelHeight(props.section))
const layoutStable = ref(false)

const isChatRoute = computed(() => route.path.startsWith('/chat'))
const isProfileRoute = computed(() => route.path.startsWith('/profile'))
const canControlPet = computed(() => petStore.visible && !!petStore.runtime)

const petMenuColumns = computed(() => {
  const left = PHROLOVA_PET_MENU_SECTIONS.filter((section) => LEFT_PET_SECTION_IDS.includes(section.id))
  const right = PHROLOVA_PET_MENU_SECTIONS.filter((section) => RIGHT_PET_SECTION_IDS.includes(section.id))
  return [left, right]
})

const layout = computed(() => {
  const anchor = toolMenu.anchors[props.section]
  return computeFlyoutLayout(anchor, panelHeight.value)
})

const flyoutStyle = computed(() => ({
  top: `${layout.value.top}px`,
  left: `${layout.value.left}px`,
  width: `${FLYOUT_WIDTH[props.section]}px`,
}))

const arrowTop = computed(() => layout.value.arrowTop)

const { clipStyle, scheduleSync, syncMetrics, isClipReady } = usePhroBubbleClip(bubbleRef, {
  variant: 'left',
  arrow: arrowTop,
})

const bubbleStyle = computed(() => ({
  '--arrow-top': `${layout.value.arrowTop}px`,
  ...clipStyle.value,
}))

/** @param {import('@/utils/phrolovaPetMenu').PhrolovaPetMenuAction} item */
function isPetToggleOn(item) {
  if (item.kind !== 'toggle') return false
  return petStore.toggleStates[item.id] ?? item.defaultOn !== false
}

/** @param {import('@/utils/phrolovaPetMenu').PhrolovaPetMenuAction} item */
function petChipTitle(item) {
  if (item.hint) return item.hint
  if (item.kind === 'toggle') {
    return `${item.label}：${isPetToggleOn(item) ? '开（点击关闭）' : '关（点击开启）'}`
  }
  return item.label
}

/** @param {import('@/utils/phrolovaPetMenu').PhrolovaPetMenuAction} action */
function handlePetAction(action) {
  if (action.kind === 'reset') {
    petStore.resetSizeLevel()
    if (!petStore.runtime) {
      petStore.setToggleStates(buildDefaultToggleStates())
      return
    }
  } else if (!petStore.visible) {
    ElMessage.warning('请先显示桌宠')
    return
  } else if (!petStore.runtime) {
    ElMessage.warning('桌宠正在加载，请稍后再试')
    return
  }

  petStore.runMenuAction(action)
}

/** @param {Event} event */
function onPetSizeLevelInput(event) {
  const target = event.target
  if (!(target instanceof HTMLInputElement)) return
  petStore.setSizeLevel(Number(target.value))
}

function measurePanelHeight() {
  const bubble = bubbleRef.value
  if (!bubble) return
  panelHeight.value = bubble.scrollHeight
}

let resizeObserver = null

function bindMeasure() {
  resizeObserver?.disconnect()
  const bubble = bubbleRef.value
  if (!bubble) return

  resizeObserver = new ResizeObserver(() => {
    panelHeight.value = bubble.scrollHeight
    scheduleSync()
  })
  resizeObserver.observe(bubble)
  panelHeight.value = bubble.scrollHeight
  scheduleSync()
}

watch(
  () => toolMenu.anchors[props.section],
  () => {
    nextTick(() => {
      measurePanelHeight()
      scheduleSync()
    })
  },
  { deep: true },
)

watch(
  () => panelHeight.value,
  () => scheduleSync(),
)

onMounted(async () => {
  await nextTick()
  syncMetrics()
  measurePanelHeight()
  bindMeasure()
  scheduleSync()
  await nextTick()
  layoutStable.value = true
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})

function goToProfile() {
  if (!isProfileRoute.value) {
    router.push('/profile')
  }
}

function openNewFeixunWindow() {
  windowsStore.createWindow()
  if (!isChatRoute.value) {
    router.push('/chat')
  }
}

async function toggleFeixunLayoutMode() {
  if (!isChatRoute.value) {
    await router.push('/chat')
    await nextTick()
    await nextTick()
  }
  await windowsStore.toggleLayoutMode()
  await nextTick()
}

function confirmLogout() {
  showPhroConfirm('确定要退出登录吗？', '退出登录', {
    confirmButtonText: '退出',
    cancelButtonText: '取消',
  })
    .then(() => {
      userStore.logout()
      router.push('/login')
    })
    .catch(() => {})
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-cursor.scss' as phro-cursor;
@use '@/assets/styles/phro-theme.scss' as phro-theme;

.app-tool-flyout {
  position: fixed;
  z-index: 220;
  font-family: $font-family-phro;
  pointer-events: auto;
  user-select: none;
  -webkit-user-select: none;

  &.is-layout-stable {
    transition: top 0.2s ease, left 0.2s ease;
  }
}

.app-tool-flyout__shell {
  filter:
    drop-shadow(0 0 0 1px $phro-glass-border)
    drop-shadow(0 8px 28px rgba(20, 0, 8, 0.28));
}

.app-tool-flyout__bubble {
  --arrow-top: 14px;
  --tail-size: 7px;
  transform-origin: left calc(var(--arrow-top, 14px) + var(--tail-size));
  @include phro-theme.phro-bubble-tail-left;
  filter: none;

  &::before {
    opacity: 1;
  }

  &:not(.is-clip-ready)::before {
    opacity: 0;
  }
}

.app-tool-flyout__item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: $phro-divider-width solid rgba($phro-gold, 0.22);
  border-radius: $phro-radius-sm;
  background: rgba($phro-panel-bg, 0.92);
  color: $phro-text-deep;
  text-align: left;
  @include phro-cursor.phro-cursor-pointer;
  appearance: none;
  transition: box-shadow 0.2s, border-color 0.2s;

  &:hover {
    border-color: rgba($phro-gold, 0.5);
    box-shadow:
      inset 3px 0 0 rgba($phro-gold, 0.9),
      0 0 0 1px rgba($phro-gold, 0.22);
  }

  &.is-active {
    border-color: rgba($phro-gold, 0.65);
    box-shadow:
      inset 3px 0 0 $phro-gold,
      0 0 0 1px rgba($phro-gold, 0.28);

    .app-tool-flyout__item-label {
      font-weight: 600;
    }
  }

  &--danger {
    color: $phro-rose;

    .app-tool-flyout__item-icon {
      color: rgba($phro-rose, 0.88);
    }

    &:hover {
      border-color: rgba($phro-rose, 0.55);
      box-shadow:
        inset 3px 0 0 rgba($phro-rose, 0.85),
        0 0 0 1px rgba($phro-rose, 0.22);
    }
  }
}

.app-tool-flyout__item-icon {
  flex-shrink: 0;
  font-size: 16px;
  color: rgba($phro-gold, 0.82);
}

.app-tool-flyout__item-label {
  min-width: 0;
  font-size: 12px;
  line-height: 1.35;
}

.app-tool-flyout__pet-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.app-tool-flyout__pet-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: stretch;
  gap: 8px;
  min-width: 0;
}

.app-tool-flyout__pet-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;

  &--left {
    .app-tool-flyout__pet-section--visibility {
      margin-top: auto;
    }
  }
}

.app-tool-flyout__section-title {
  margin: 0 0 4px;
  font-size: 11px;
  font-weight: 600;
  color: $phro-gold-light;
  letter-spacing: 0.04em;
  text-shadow: 0 1px 4px rgba(20, 0, 8, 0.45);
}

.app-tool-flyout__pet-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.app-tool-flyout__chip {
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
  @include phro-cursor.phro-cursor-pointer;
  appearance: none;
  transition: border-color 0.15s ease, background 0.15s ease;

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

  &--visibility {
    justify-content: center;
  }

  &.is-on {
    border-color: rgba($phro-gold, 0.55);
    box-shadow: inset 2px 0 0 rgba($phro-gold, 0.85);
  }

  &:disabled {
    opacity: 0.45;
    @include phro-cursor.phro-cursor-not-allowed;
  }
}

.app-tool-flyout__chip-label {
  font-size: 11px;
}

.app-tool-flyout__chip-state {
  min-width: 14px;
  font-size: 10px;
  font-weight: 600;
  color: $phro-text-mid;
  text-align: right;

  .is-on & {
    color: rgba($phro-gold, 0.95);
  }
}

.app-tool-flyout__pet-size-slider {
  display: block;
  width: 100%;
  height: 4px;
  margin: 0;
  accent-color: rgba($phro-gold, 0.85);
  @include phro-cursor.phro-cursor-pointer;
}

.app-tool-flyout__pet-section--size {
  flex-shrink: 0;
  padding-top: 2px;
  border-top: 1px solid rgba($phro-rose, 0.14);
}
</style>
