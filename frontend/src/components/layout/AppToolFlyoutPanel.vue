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
import { showPhroConfirm } from '@/utils/phroMessageBox'
import { useAppToolMenuStore } from '@/stores/appToolMenu'
import { useFeixunWindowsStore } from '@/stores/feixunWindows'
import { useUserStore } from '@/stores/user'

/** @typedef {'feixun' | 'user'} AppToolMenuSection */

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
const userStore = useUserStore()

const rootRef = ref(null)
const bubbleRef = ref(null)
const panelHeight = ref(defaultPanelHeight(props.section))
const layoutStable = ref(false)

const isChatRoute = computed(() => route.path.startsWith('/chat'))
const isProfileRoute = computed(() => route.path.startsWith('/profile'))

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
  cursor: pointer;
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
</style>
