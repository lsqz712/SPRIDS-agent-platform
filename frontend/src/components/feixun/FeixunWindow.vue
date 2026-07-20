<template>
    <div
      ref="feixunWindowRef"
      class="feixun-window-shell"
      :data-window-id="windowId"
      :class="{
        'feixun-window-shell--dragging': isWindowDragging,
        'feixun-window-shell--resizing': isWindowResizing,
        'feixun-window-shell--inactive': !isFocused,
        'feixun-window-shell--sticky': isStickyMode,
      }"
      :style="windowShellStyle"
    >
      <div class="feixun-window-chrome" aria-hidden="true">
        <div class="feixun-window-chrome__top">
          <svg
            class="feixun-window-chrome__ear feixun-window-chrome__ear--left"
            :viewBox="formatSliceViewBox(CHROME_SLICE_TOP_LEFT)"
            preserveAspectRatio="none"
            overflow="hidden"
          >
            <path class="feixun-window-chrome__fill" :d="CHROME_EAR_LEFT_FILL_PATH" />
            <path class="feixun-window-chrome__stroke" :d="CHROME_EAR_LEFT_STROKE_PATH" />
          </svg>
          <svg
            class="feixun-window-chrome__bridge"
            :viewBox="formatSliceViewBox(CHROME_SLICE_TOP_MID)"
            preserveAspectRatio="none"
            overflow="hidden"
          >
            <path class="feixun-window-chrome__stroke" :d="CHROME_TOP_BRIDGE_STROKE_PATH" />
          </svg>
          <svg
            class="feixun-window-chrome__ear feixun-window-chrome__ear--right"
            :viewBox="formatSliceViewBox(CHROME_SLICE_EAR_CAP)"
            preserveAspectRatio="none"
            overflow="hidden"
          >
            <path class="feixun-window-chrome__fill" :d="CHROME_EAR_RIGHT_FILL_PATH" />
            <path class="feixun-window-chrome__stroke" :d="CHROME_EAR_RIGHT_STROKE_PATH" />
            <path class="feixun-window-close-glow__shape" :d="CHROME_CLOSE_GLOW_PATH_LOCAL" />
          </svg>
        </div>
        <div class="feixun-window-chrome__body">
          <svg
            class="feixun-window-chrome__body-svg"
            :viewBox="formatSliceViewBox(CHROME_SLICE_BODY)"
            preserveAspectRatio="none"
            overflow="hidden"
          >
            <path class="feixun-window-chrome__fill" :d="CHROME_FRAME_PATH" />
            <path class="feixun-window-chrome__stroke" :d="CHROME_BODY_STROKE_PATH" />
          </svg>
        </div>
      </div>

      <svg
        class="feixun-window-resize-north"
        viewBox="0 -7 100 107"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path
          class="feixun-window-resize-north__hit"
          d="M 3 -7 L 9 -7 Q 12 -7 12 -4 L 12 -3 Q 12 0 15 0 L 85 0 Q 88 0 88 -3 L 88 -4 Q 88 -7 91 -7 L 97 -7 Q 100 -7 100 -4"
          @pointerdown.stop="handleWindowResizeStart($event, 'n')"
        />
      </svg>

      <div
        class="feixun-window-ear feixun-window-ear--drag"
        aria-label="拖动窗口"
        @pointerdown.stop="handleWindowChromeDrag"
      />
      <div class="feixun-window-ear__logo-zone" aria-hidden="true">
        <img
          :src="phrolova.elementIcon"
          alt=""
          class="feixun-window-ear__icon"
          draggable="false"
        />
      </div>
      <button
        type="button"
        class="feixun-window-ear feixun-window-ear--close"
        aria-label="关闭窗口"
        @pointerdown.stop="raiseWindowToTop"
        @click.stop="closeFeixunWindow"
      />

      <div
        v-for="handle in RESIZE_HANDLES"
        :key="handle"
        class="window-resize-handle"
        :class="`window-resize-handle--${handle}`"
        @pointerdown.stop="handleWindowResizeStart($event, handle)"
      />

      <div class="feixun-window" @pointerdown="handleWindowDragStart">
      <aside class="feixun-sidebar">
        <div class="sidebar-header">
          <img :src="phrolova.avatar" alt="弗洛洛" class="sidebar-avatar" />
          <div class="sidebar-title">
            <span class="sidebar-name">弗洛洛</span>
            <span class="sidebar-status">在线</span>
          </div>
          <button
            type="button"
            class="sidebar-new-btn"
            :disabled="isLoading"
            @click="handleNewChat"
          >
            <span class="plus-icon">+</span>
          </button>
        </div>

        <div ref="historyListRef" class="history-list">
          <div
            v-for="session in chatSessions"
            :key="session.id"
            class="history-item"
            :class="{ active: isSessionActive(session.id) }"
            :data-session-id="session.id"
            @click="selectHistorySession(session.id)"
          >
            <div class="history-dot" :class="{ active: isSessionActive(session.id) }" />
            <div class="history-content">
              <input
                v-if="editingSessionId === session.id"
                v-model="editingTitle"
                class="history-title-input"
                maxlength="30"
                @click.stop
                @keydown.enter.stop="commitRenameSession(session)"
                @keydown.esc.stop="cancelRenameSession"
                @blur="handleRenameBlur(session)"
              />
              <span v-else class="history-title">{{ session.title }}</span>
              <span class="history-preview">{{ session.preview }}</span>
            </div>
            <div class="history-meta">
              <span class="history-time">{{ formatSessionTime(session.lastMessageAt ?? session.updatedAt) }}</span>
              <div class="history-actions" @click.stop>
                <button
                  type="button"
                  class="history-action-btn"
                  @click.stop="startRenameSession(session)"
                  title="重命名"
                >
                  <el-icon><EditPen /></el-icon>
                </button>
                <button
                  type="button"
                  class="history-action-btn danger"
                  @click.stop="handleDeleteSession(session)"
                  title="删除"
                >
                  <el-icon><Delete /></el-icon>
                </button>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- 中间对话 -->
      <section class="feixun-main">
        <div class="chat-panel">
          <header class="chat-header">
            <div class="chat-header-content">
              <img :src="phrolova.avatar" alt="" class="chat-header-avatar" />
              <div class="chat-header-info">
                <span class="chat-header-name">{{ phrolova.name }}</span>
                <span class="chat-header-status">智能检测助手</span>
              </div>
            </div>
            <div class="chat-header-actions">
              <button
                type="button"
                class="chat-header-action-btn"
                :class="{ active: showDetectionPanel }"
                @click="showDetectionPanel = !showDetectionPanel"
                :title="showDetectionPanel ? '隐藏检测工作台' : '显示检测工作台'"
              >
                <svg viewBox="0 0 24 24" class="action-icon">
                  <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                </svg>
              </button>
            </div>
          </header>

          <div class="chat-messages-container">
            <div
              ref="messageListRef"
              class="chat-messages"
              @scroll="handleMessageListScroll"
            >
          <div class="chat-watermark" />

          <div v-if="messages.length === 0" class="chat-empty">
            <p>开始与 {{ phrolova.name }} 的飞讯对话</p>
          </div>

          <template v-for="(msg, index) in messages" :key="index">
            <div v-if="msg.role === 'assistant'" class="msg-incoming">
              <img :src="phrolova.avatar" alt="" class="msg-avatar" />
              <div class="msg-body">
                <div v-if="msg.routeAgent" class="msg-route-badge">
                  {{ routeLabel(msg.routeAgent) }}
                </div>
                <div v-if="msg.toolCall" class="msg-tool-call">
                  <span class="tool-call-icon">⚙</span>
                  <span class="tool-call-name">{{ msg.toolCall.tool }}</span>
                  <span class="tool-call-input">{{ toolInputPreview(msg.toolCall.input) }}</span>
                </div>
                <div
                  class="msg-bubble incoming"
                  :class="{ typing: isTypingBubble(msg, index) }"
                >
                  <div
                    v-if="msg.content"
                    class="msg-text markdown-body"
                    v-html="renderMarkdown(msg.content)"
                  />
                  <span v-else-if="isTypingBubble(msg, index)" class="typing-ellipsis">...</span>
                </div>
              </div>
            </div>

            <div v-else class="msg-outgoing">
              <div class="msg-body">
                <div class="msg-bubble outgoing">
                  <div v-if="msg.image" class="msg-image">
                    <img :src="msg.image" alt="上传的图片" />
                  </div>
                  <div class="msg-text">{{ msg.content }}</div>
                </div>
              </div>
              <div class="msg-avatar user">
                <img v-if="userStore.avatar" :src="userStore.avatar" alt="" />
                <span v-else>{{ userInitial }}</span>
              </div>
            </div>
          </template>
            </div>

            <button
              v-if="showScrollToBottomBtn"
              type="button"
              class="phro-btn scroll-to-bottom-btn"
              @click="scrollToBottomAndStick"
            >
              回到底部
            </button>
          </div>

        <footer class="chat-input-bar">
          <textarea
            ref="inputRef"
            v-model="inputText"
            class="chat-input"
            rows="1"
            placeholder="输入消息与弗洛洛对话..."
            :disabled="isLoading"
            @keydown.enter.exact.prevent="handleSend"
            @input="autoResize"
          />
          <button
            type="button"
            class="phro-btn send-btn"
            :disabled="!inputText.trim() || isLoading"
            @click="handleSend"
          >
            发送
          </button>
        </footer>
        </div>
      </section>

      <!-- 右侧检测工作台 -->
      <aside v-show="showDetectionPanel" class="feixun-detection-panel">
        <div class="detection-panel-header">
          <h3>检测工作台</h3>
          <div class="detection-tabs">
            <button
              v-for="tab in TASK_TYPES"
              :key="tab.key"
              type="button"
              class="detection-tab"
              :class="{ active: detectionMode === tab.key }"
              @click="detectionMode = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>

        <div class="detection-panel-body">
          <div class="detection-section">
            <h4 class="detection-section-title">检测场景</h4>
            <p class="scene-name">{{ scene?.display_name || 'PCB SMT 缺陷检测' }}</p>
            <div class="class-tags">
              <span
                v-for="name in scene?.class_names || defaultClasses"
                :key="name"
                class="phro-tag"
              >
                {{ classCn(name) }}
              </span>
            </div>
          </div>

          <div class="detection-section">
            <h4 class="detection-section-title">检测参数</h4>
            <DetectionParams v-model="detectionParams" />
          </div>

          <div class="detection-section detection-section--grow">
            <h4 class="detection-section-title">上传</h4>
            <ImageUploader
              v-if="detectionMode === 'single'"
              :disabled="detectionLoading"
              title="上传单张 PCB 图像"
              @select="handleSingleDetect"
            />
            <ImageUploader
              v-else-if="detectionMode === 'batch'"
              multiple
              :disabled="detectionLoading"
              title="批量上传 PCB 图像"
              hint="可多选，支持 JPG / PNG / WEBP"
              @select="handleBatchDetect"
            />
            <ImageUploader
              v-else-if="detectionMode === 'video'"
              accept="video/*"
              :disabled="detectionLoading"
              title="上传检测视频"
              hint="支持 MP4 / WEBM"
              @select="handleVideoDetect"
            />
            <div v-else class="camera-panel">
              <div v-if="cameraDevices.length > 1" class="camera-select">
                <label class="camera-select-label">选择摄像头：</label>
                <select
                  v-model="selectedCamera"
                  class="camera-select-input"
                  :disabled="cameraRunning"
                >
                  <option
                    v-for="device in cameraDevices"
                    :key="device.device_id"
                    :value="device.device_id"
                  >
                    {{ device.name }} ({{ device.resolution }})
                  </option>
                </select>
              </div>
              <div v-if="cameraRunning" class="camera-video-container">
                <video ref="videoRef" class="camera-video" autoplay playsinline muted />
                <canvas ref="cameraCanvasRef" class="camera-overlay" />
              </div>
              <div class="camera-actions">
                <button
                  type="button"
                  class="phro-btn phro-btn--primary"
                  :disabled="cameraRunning"
                  @click="startCamera"
                >
                  开启摄像头
                </button>
                <button
                  type="button"
                  class="phro-btn"
                  :disabled="!cameraRunning"
                  @click="stopCamera"
                >
                  停止
                </button>
              </div>
            </div>
            <el-progress
              v-if="videoProgress > 0 && videoProgress < 100"
              :percentage="videoProgress"
              :stroke-width="8"
              class="video-progress"
            />
          </div>
        </div>

        <div class="detection-result-panel">
          <div class="result-preview">
            <BboxCanvas
              :image-src="previewImage"
              :detections="currentDetections"
              :active-index="activeDetection"
            />
          </div>
          <div class="result-list-panel">
            <DetectionResultPanel
              :detections="currentDetections"
              :active-index="activeDetection"
              :summary="resultSummary"
              @select="activeDetection = $event"
            />
          </div>
        </div>

        <div v-if="batchResults.length" class="batch-card">
          <h4 class="batch-title">批量结果概览</h4>
          <div class="batch-grid">
            <div
              v-for="(item, idx) in batchResults"
              :key="idx"
              class="batch-item"
              @click="selectBatchItem(item)"
            >
              <img :src="item.imageUrl" :alt="item.name" />
              <span>{{ item.name }}</span>
              <span class="batch-count">{{ item.detections.length }} 个缺陷</span>
            </div>
          </div>
        </div>
      </aside>
      </div>
    </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { showPhroConfirm } from '@/utils/phroMessageBox'
import { Delete, EditPen } from '@element-plus/icons-vue'
import { useFeixunWindowsStore } from '@/stores/feixunWindows'
import { sortSessions } from '@/stores/feixunWindowSessions'
import { useUserStore } from '@/stores/user'
import { renderMarkdown } from '@/utils/markdown'
import { streamChat } from '@/utils/stream'
import ImageUploader from '@/components/detection/ImageUploader.vue'
import BboxCanvas from '@/components/detection/BboxCanvas.vue'
import DetectionParams from '@/components/detection/DetectionParams.vue'
import DetectionResultPanel from '@/components/detection/DetectionResultPanel.vue'
import { TASK_TYPES, PCB_SCENE } from '@/constants/pcbDefects'
import {
  mockDetectSingle,
  mockDetectBatch,
  mockDetectVideo,
  mockGenerateFrameDetections,
  mockGetScenes,
  withApiFallback,
} from '@/services/spridsMock'
import { getScenesApi, detectSingleApi, detectBatchApi, detectVideoApi, getCamerasApi } from '@/api/detection'

import {
  buildChromeLayoutVars,
  computeEarBandPx,
  computeEarStraightSpanPx,
  computeShellOuterHeight,
  formatSliceViewBox,
  resolveChromeBaseSize,
  CHROME_FALLBACK_BASE,
  CHROME_FRAME_PATH,
  CHROME_SLICE_TOP_LEFT,
  CHROME_SLICE_TOP_MID,
  CHROME_SLICE_EAR_CAP,
  CHROME_SLICE_BODY,
  CHROME_EAR_LEFT_FILL_PATH,
  CHROME_EAR_RIGHT_FILL_PATH,
  CHROME_EAR_LEFT_STROKE_PATH,
  CHROME_EAR_RIGHT_STROKE_PATH,
  CHROME_TOP_BRIDGE_STROKE_PATH,
  CHROME_BODY_STROKE_PATH,
  CHROME_CLOSE_GLOW_PATH_LOCAL,
} from '@/components/feixun/feixunWindowChrome'

const props = defineProps({
  windowId: {
    type: String,
    required: true,
  },
  isFocused: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['focus', 'dragging-change'])

const windowsStore = useFeixunWindowsStore()
const userStore = useUserStore()

function generateSessionId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function normalizeMessages(list) {
  return list.filter((msg, index, arr) => {
    if (msg.role === 'assistant' && !msg.content?.trim() && index === arr.length - 1) {
      return false
    }
    return msg.content?.trim() || msg.role === 'assistant'
  })
}

const windowRecord = computed(() => windowsStore.getWindow(props.windowId))
const isStickyMode = computed(() => windowsStore.isStickyLayout)

const stickyStackIndex = computed(() => {
  if (!isStickyMode.value) return 0
  const index = windowsStore.openWindows.findIndex((window) => window.id === props.windowId)
  return index < 0 ? 0 : index
})

const stickyFanOffset = computed(() => {
  if (!isStickyMode.value) return { x: 0, y: 0 }

  const stepX = computeEarStraightSpanPx(getChromeBaseSize().width)

  return {
    x: stickyStackIndex.value * stepX,
    y: 0,
  }
})

const stickyShellSize = computed(() => {
  if (!isStickyMode.value) return null
  return resolveStickyShellSize()
})

function getLayoutOffset() {
  if (isStickyMode.value) {
    const base = windowsStore.stickyStack.offset ?? { x: 0, y: 0 }
    const fan = stickyFanOffset.value
    return { x: base.x + fan.x, y: base.y + fan.y }
  }
  return windowOffset.value
}

function getLayoutAnchor() {
  if (isStickyMode.value) {
    return windowsStore.stickyStack.anchor ?? { left: 0, top: 0 }
  }
  return windowAnchor.value
}

function setLayoutOffset(x, y) {
  if (isStickyMode.value) {
    const fan = stickyFanOffset.value
    windowsStore.patchStickyStackOffset({ x: x - fan.x, y: y - fan.y })
    return
  }
  windowOffset.value = { x, y }
}

function chatState() {
  return windowRecord.value?.chat ?? null
}

const messages = computed(() => windowRecord.value?.chat?.messages ?? [])
const currentSessionId = computed(() => windowRecord.value?.chat?.currentSessionId ?? null)
const isLoading = computed(() => windowRecord.value?.chat?.isLoading ?? false)

const feixunWindowRef = ref(null)
const inputText = ref('')
const inputRef = ref(null)
const imageInputRef = ref(null)
const pendingImage = ref(null)
const pendingImagePreview = ref(null)
const detectionMode = ref('single')
const detectionLoading = ref(false)
const scene = ref(PCB_SCENE)
const showDetectionPanel = ref(true)
const detectionParams = ref({ confThreshold: 0.25, iouThreshold: 0.45 })
const previewImage = ref('')
const currentDetections = ref([])
const activeDetection = ref(-1)
const resultSummary = ref(null)
const batchResults = ref([])
const videoProgress = ref(0)
const videoRef = ref(null)
const cameraCanvasRef = ref(null)
const cameraRunning = ref(false)
const cameraDevices = ref([])
const selectedCamera = ref(0)
let cameraStream = null
let cameraTimer = null
const defaultClasses = PCB_SCENE.class_names

const messageListRef = ref(null)
const historyListRef = ref(null)
const editingSessionId = ref(null)
const editingTitle = ref('')
const skipRenameBlurCommit = ref(false)
const stopStream = ref(null)
const suppressAutoScroll = ref(false)
const stickToBottom = ref(true)
const SCROLL_BOTTOM_THRESHOLD = 48

const WINDOW_DRAG_HOSTS = ['feixun-window', 'sidebar-panel', 'history-list']
const WINDOW_DRAG_SLOP = 8
const WINDOW_DRAG_THRESHOLD = 6
const WINDOW_OUTER_PAD = 14
const WINDOW_VERTICAL_SLACK = 40
const MIN_WINDOW_SCALE = 0.62
const RESIZE_HANDLES = ['nw', 'ne', 'e', 'se', 's', 'sw', 'w']
const windowOffset = computed({
  get: () => windowRecord.value?.offset ?? { x: 0, y: 0 },
  set: (value) => {
    windowsStore.patchWindow(props.windowId, { offset: value })
  },
})
const windowScaleX = computed({
  get: () => windowRecord.value?.scaleX ?? 1,
  set: (value) => {
    windowsStore.patchWindow(props.windowId, { scaleX: value })
  },
})
const windowScaleY = computed({
  get: () => windowRecord.value?.scaleY ?? 1,
  set: (value) => {
    windowsStore.patchWindow(props.windowId, { scaleY: value })
  },
})
const windowBaseSize = computed({
  get: () => windowRecord.value?.baseSize ?? { width: 0, height: 0 },
  set: (value) => {
    windowsStore.patchWindow(props.windowId, { baseSize: value })
  },
})
const windowAnchor = computed({
  get: () => windowRecord.value?.anchor ?? null,
  set: (value) => {
    windowsStore.patchWindow(props.windowId, { anchor: value })
  },
})
const isWindowDragging = ref(false)
const isWindowResizing = ref(false)
const windowDragState = ref(null)
const windowResizeState = ref(null)
const DRAG_NO_SELECT_CLASS = 'feixun-drag-no-select'

function clearTextSelection() {
  window.getSelection()?.removeAllRanges()
}

function preventSelectStart(event) {
  event.preventDefault()
}

function enableDragNoSelect() {
  document.body.classList.add(DRAG_NO_SELECT_CLASS)
  document.body.style.userSelect = 'none'
  document.addEventListener('selectstart', preventSelectStart, { capture: true })
  clearTextSelection()
}

function disableDragNoSelect() {
  document.body.classList.remove(DRAG_NO_SELECT_CLASS)
  document.body.style.userSelect = ''
  document.removeEventListener('selectstart', preventSelectStart, { capture: true })
}

function getChromeBaseSize() {
  return windowsStore.sharedChromeBase
}

function resolveStickyShellSize() {
  const snapshot = windowsStore.frameLayoutSnapshots?.[props.windowId]
  const recordSize = windowRecord.value?.baseSize
  let width = recordSize?.width > 0 ? recordSize.width : snapshot?.stickyShellSize?.width ?? snapshot?.baseSize?.width ?? 0
  let height = recordSize?.height > 0 ? recordSize.height : snapshot?.stickyShellSize?.height ?? snapshot?.baseSize?.height ?? 0

  if (width <= 0 || height <= 0) {
    const shared = windowsStore.sharedChromeBase
    width = shared.width
    height = shared.height
  }

  return { width, height }
}

const windowShellStyle = computed(() => {
  const earBase = getChromeBaseSize()
  const { x, y } = getLayoutOffset()
  const anchor = getLayoutAnchor()
  const scaleX = windowScaleX.value
  const scaleY = windowScaleY.value
  const layoutWidth = windowBaseSize.value.width > 0 ? windowBaseSize.value.width : 0
  const layoutHeight = windowBaseSize.value.height > 0 ? windowBaseSize.value.height : 0
  const shellWidth = layoutWidth > 0 ? layoutWidth * scaleX : 0
  const shellHeight = layoutHeight > 0 ? computeShellOuterHeight(layoutHeight, scaleY) : 0
  const chromeVars = buildChromeLayoutVars(
    earBase.width,
    earBase.height,
    shellWidth > 0 ? shellWidth : earBase.width * scaleX,
  )
  const shellZIndex = windowRecord.value?.zIndex ?? 1

  if (isStickyMode.value) {
    const stickyAnchor = getLayoutAnchor()
    const shellSize = stickyShellSize.value ?? windowsStore.sharedChromeBase
    const { width: baseW, height: baseH } = shellSize
    const { width: chromeW, height: chromeH } = resolveChromeBaseSize(earBase, shellSize)

    return {
      position: 'absolute',
      left: `${stickyAnchor.left + x}px`,
      top: `${stickyAnchor.top + y}px`,
      width: `${baseW * scaleX}px`,
      height: `${computeShellOuterHeight(baseH, scaleY)}px`,
      maxWidth: 'none',
      maxHeight: 'none',
      flex: 'none',
      margin: 0,
      transform: 'none',
      zIndex: shellZIndex,
      ...buildChromeLayoutVars(chromeW, chromeH, baseW * scaleX),
    }
  }

  if (anchor && layoutWidth > 0 && layoutHeight > 0) {
    return {
      position: 'absolute',
      left: `${anchor.left + x}px`,
      top: `${anchor.top + y}px`,
      width: `${shellWidth}px`,
      height: `${shellHeight}px`,
      maxWidth: 'none',
      maxHeight: 'none',
      margin: 0,
      transform: 'none',
      zIndex: shellZIndex,
      ...chromeVars,
    }
  }

  const frameSizeStyle =
    layoutWidth > 0 && layoutHeight > 0
      ? {
          width: `${shellWidth}px`,
          height: `${shellHeight}px`,
          maxWidth: 'none',
          maxHeight: 'none',
          flex: '0 0 auto',
        }
      : {
          width: '100%',
          maxWidth: `${CHROME_FALLBACK_BASE.width}px`,
          height: `calc(100% - ${WINDOW_VERTICAL_SLACK}px)`,
          maxHeight: `calc(100% - ${WINDOW_VERTICAL_SLACK}px)`,
        }

  return {
    position: 'absolute',
    left: '50%',
    top: '50%',
    transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`,
    margin: 0,
    zIndex: shellZIndex,
    ...frameSizeStyle,
    ...chromeVars,
  }
})

function isWindowDragSurface(target) {
  if (!(target instanceof Element)) return false
  return WINDOW_DRAG_HOSTS.some((className) => target.classList.contains(className))
}

const INTERACTIVE_DRAG_SELECTOR = [
  '.chat-panel',
  '.chat-messages',
  '.chat-input-bar',
  '.chat-header',
  '.msg-bubble',
  '.msg-text',
  '.history-item-body',
  '.history-action-btn',
  '.history-title-input',
  '.sidebar-new-chat',
  '.sidebar-partner',
  '.contact-notice',
  '.feixun-window-ear--close',
  'button',
  'input',
  'textarea',
  'a',
  'label',
].join(', ')

function isInteractiveDragTarget(target) {
  return target instanceof Element && !!target.closest(INTERACTIVE_DRAG_SELECTOR)
}

function isPointInExpandedGap(x, y, beforeRect, afterRect, horizontal = false) {
  if (horizontal) {
    const gapMid = (beforeRect.right + afterRect.left) / 2
    const gapSize = Math.max(afterRect.left - beforeRect.right, 0)
    const half = gapSize / 2 + WINDOW_DRAG_SLOP
    const top = Math.min(beforeRect.top, afterRect.top)
    const bottom = Math.max(beforeRect.bottom, afterRect.bottom)
    return x >= gapMid - half && x <= gapMid + half && y >= top && y <= bottom
  }

  const gapMid = (beforeRect.bottom + afterRect.top) / 2
  const gapSize = Math.max(afterRect.top - beforeRect.bottom, 0)
  const half = gapSize / 2 + WINDOW_DRAG_SLOP
  const left = Math.min(beforeRect.left, afterRect.left)
  const right = Math.max(beforeRect.right, afterRect.right)
  return y >= gapMid - half && y <= gapMid + half && x >= left && x <= right
}

function findVerticalGapHost(host, clientX, clientY) {
  const rect = host.getBoundingClientRect()
  if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) {
    return null
  }

  const children = [...host.children].filter((el) => el.getBoundingClientRect().height > 0)
  if (children.length < 2) return null

  for (let i = 1; i < children.length; i += 1) {
    const prevRect = children[i - 1].getBoundingClientRect()
    const currRect = children[i].getBoundingClientRect()
    if (isPointInExpandedGap(clientX, clientY, prevRect, currRect)) return host
  }

  return null
}

function findGapDragHost(clientX, clientY) {
  const root = feixunWindowRef.value
  if (!root) return null

  const winRect = root.getBoundingClientRect()
  if (
    clientX >= winRect.left &&
    clientX <= winRect.right &&
    clientY >= winRect.top &&
    clientY <= winRect.bottom
  ) {
    if (
      clientX <= winRect.left + WINDOW_OUTER_PAD ||
      clientX >= winRect.right - WINDOW_OUTER_PAD ||
      clientY <= winRect.top + WINDOW_OUTER_PAD ||
      clientY >= winRect.bottom - WINDOW_OUTER_PAD
    ) {
      return root
    }

    const columns = [...root.children]
    for (let i = 1; i < columns.length; i += 1) {
      const prevRect = columns[i - 1].getBoundingClientRect()
      const currRect = columns[i].getBoundingClientRect()
      if (isPointInExpandedGap(clientX, clientY, prevRect, currRect, true)) {
        return root
      }
    }
  }

  const innerHosts = root.querySelectorAll('.sidebar-panel, .history-list')
  for (const host of innerHosts) {
    const matched = findVerticalGapHost(host, clientX, clientY)
    if (matched) return matched
  }

  return null
}

function isCornerResizeHandle(handle) {
  return handle.length === 2
}

function clampScaleValue(value) {
  return Math.max(MIN_WINDOW_SCALE, value)
}

function syncWindowAnchor() {
  if (isStickyMode.value) return

  const win = feixunWindowRef.value
  if (!win) return

  const page = win.closest('.feixun-page')
  if (!page) return

  const pageRect = page.getBoundingClientRect()
  const winRect = win.getBoundingClientRect()
  const { x, y } = windowOffset.value

  windowAnchor.value = {
    left: winRect.left - pageRect.left - x,
    top: winRect.top - pageRect.top - y,
  }
}

function syncWindowLayoutMetrics() {
  if (isStickyMode.value) return
  syncWindowBaseSize()
  nextTick(() => {
    syncWindowAnchor()
  })
}

function syncWindowBaseSize() {
  if (isStickyMode.value) return

  const win = feixunWindowRef.value
  if (!win) return

  const scaleX = windowScaleX.value
  const scaleY = windowScaleY.value
  const measuredWidth = win.offsetWidth
  const measuredHeight = win.offsetHeight
  if (!(measuredWidth > 0 && measuredHeight > 0)) return

  let width = measuredWidth
  let height = measuredHeight

  if (scaleX !== 1 || scaleY !== 1) {
    if (windowBaseSize.value.width > 0 && windowBaseSize.value.height > 0) return
    width = measuredWidth / scaleX
    const chromeH = getChromeBaseSize().height || height
    const earBand = computeEarBandPx(chromeH)
    height = earBand + (measuredHeight - earBand) / scaleY
  }

  if (width > 0 && height > 0) {
    windowBaseSize.value = { width, height }
    const hasGlobalChrome = windowsStore.openWindows.some(
      (window) => window.chromeBaseSize?.width > 0 && window.chromeBaseSize?.height > 0,
    )
    if (!hasGlobalChrome) {
      windowsStore.patchWindow(props.windowId, {
        chromeBaseSize: { width, height },
      })
    }
  }
}

function computeResizeScales(handle, dx, dy, originScaleX, originScaleY) {
  const baseW = windowBaseSize.value.width
  const baseH = windowBaseSize.value.height
  if (!baseW || !baseH) {
    return { scaleX: originScaleX, scaleY: originScaleY }
  }

  const originW = baseW * originScaleX
  const originH = baseH * originScaleY
  let scaleX = originScaleX
  let scaleY = originScaleY

  if (handle.includes('e')) scaleX = (originW + dx) / baseW
  if (handle.includes('w')) scaleX = (originW - dx) / baseW
  if (handle.includes('s')) scaleY = (originH + dy) / baseH
  if (handle.includes('n')) scaleY = (originH - dy) / baseH

  if (isCornerResizeHandle(handle)) {
    const uniform = (scaleX + scaleY) / 2
    scaleX = uniform
    scaleY = uniform
  }

  return {
    scaleX: clampScaleValue(scaleX),
    scaleY: clampScaleValue(scaleY),
  }
}

function computeResizeOffset(
  handle,
  originScaleX,
  originScaleY,
  newScaleX,
  newScaleY,
  originX,
  originY,
) {
  const baseW = windowBaseSize.value.width
  const baseH = windowBaseSize.value.height
  const originW = baseW * originScaleX
  const newW = baseW * newScaleX
  const originShellH = computeShellOuterHeight(baseH, originScaleY)
  const newShellH = computeShellOuterHeight(baseH, newScaleY)

  let x = originX
  let y = originY

  if (handle.includes('w')) x = originX + (originW - newW)
  if (handle.includes('n')) y = originY + (originShellH - newShellH)

  return { x, y }
}

function startWindowResize(event, handle) {
  event.preventDefault()

  if (!windowBaseSize.value.width) {
    syncWindowBaseSize()
  }
  if (!isStickyMode.value && !windowAnchor.value) {
    syncWindowAnchor()
  }
  if (!windowBaseSize.value.width) return

  const offset = getLayoutOffset()

  isWindowResizing.value = true
  windowResizeState.value = {
    pointerId: event.pointerId,
    handle,
    startX: event.clientX,
    startY: event.clientY,
    originScaleX: windowScaleX.value,
    originScaleY: windowScaleY.value,
    originX: offset.x,
    originY: offset.y,
    captureTarget: event.currentTarget,
  }

  windowResizeState.value.captureTarget?.setPointerCapture?.(event.pointerId)

  enableDragNoSelect()
  document.addEventListener('pointermove', handleWindowResizeMove)
  document.addEventListener('pointerup', stopWindowResize)
  document.addEventListener('pointercancel', stopWindowResize)
}

function handleWindowResizeMove(event) {
  const state = windowResizeState.value
  if (!state || event.pointerId !== state.pointerId) return

  event.preventDefault()

  const dx = event.clientX - state.startX
  const dy = event.clientY - state.startY
  const { scaleX, scaleY } = computeResizeScales(
    state.handle,
    dx,
    dy,
    state.originScaleX,
    state.originScaleY,
  )
  const { x, y } = computeResizeOffset(
    state.handle,
    state.originScaleX,
    state.originScaleY,
    scaleX,
    scaleY,
    state.originX,
    state.originY,
  )

  windowScaleX.value = scaleX
  windowScaleY.value = scaleY
  setLayoutOffset(x, y)
}

function stopWindowResize(event) {
  const state = windowResizeState.value
  const captureTarget = state?.captureTarget

  const offset = getLayoutOffset()
  setLayoutOffset(Math.round(offset.x), Math.round(offset.y))

  if (captureTarget && state?.pointerId != null && captureTarget.hasPointerCapture?.(state.pointerId)) {
    captureTarget.releasePointerCapture(state.pointerId)
  }

  windowResizeState.value = null
  isWindowResizing.value = false
  disableDragNoSelect()
  document.removeEventListener('pointermove', handleWindowResizeMove)
  document.removeEventListener('pointerup', stopWindowResize)
  document.removeEventListener('pointercancel', stopWindowResize)
}

function handleWindowResizeStart(event, handle) {
  if (event.button !== 0) return
  raiseWindowToTop()
  startWindowResize(event, handle)
}

function startWindowDrag(event, options = {}) {
  const { captureTarget = feixunWindowRef.value } = options
  event.preventDefault()

  if (!isStickyMode.value && !windowAnchor.value) {
    syncWindowAnchor()
  }

  const { x, y } = getLayoutOffset()

  isWindowDragging.value = true
  emit('dragging-change', true)
  enableDragNoSelect()

  windowDragState.value = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: x,
    originY: y,
    captureTarget,
    active: false,
  }

  captureTarget?.setPointerCapture?.(event.pointerId)

  document.addEventListener('pointermove', handleWindowDragMove)
  document.addEventListener('pointerup', stopWindowDrag)
  document.addEventListener('pointercancel', stopWindowDrag)
}

function handleWindowDragMove(event) {
  const state = windowDragState.value
  if (!state || event.pointerId !== state.pointerId) return

  const dx = event.clientX - state.startX
  const dy = event.clientY - state.startY

  if (!state.active) {
    if (Math.hypot(dx, dy) < WINDOW_DRAG_THRESHOLD) return
    state.active = true
  }

  event.preventDefault()
  clearTextSelection()

  setLayoutOffset(state.originX + dx, state.originY + dy)
}

function stopWindowDrag(event) {
  const state = windowDragState.value
  const captureTarget = state?.captureTarget ?? feixunWindowRef.value

  if (state?.active) {
    const offset = getLayoutOffset()
    setLayoutOffset(Math.round(offset.x), Math.round(offset.y))
  }

  disableDragNoSelect()

  if (
    captureTarget &&
    state?.pointerId != null &&
    captureTarget.hasPointerCapture?.(state.pointerId)
  ) {
    captureTarget.releasePointerCapture(state.pointerId)
  }

  windowDragState.value = null
  isWindowDragging.value = false
  emit('dragging-change', false)
  document.removeEventListener('pointermove', handleWindowDragMove)
  document.removeEventListener('pointerup', stopWindowDrag)
  document.removeEventListener('pointercancel', stopWindowDrag)
}

function handleWindowChromeDrag(event) {
  if (event.button !== 0) return
  raiseWindowToTop()
  startWindowDrag(event, { captureTarget: event.currentTarget })
}

function raiseWindowToTop() {
  windowsStore.focusWindow(props.windowId)
}

function closeFeixunWindow() {
  if (isWindowResizing.value) stopWindowResize()
  if (isWindowDragging.value) stopWindowDrag()
  if (isLoading.value) stopActiveStream()
  saveLocalSession()
  windowsStore.closeWindow(props.windowId)
}

function saveLocalSession({ refreshTime = false } = {}) {
  const chat = chatState()
  if (!chat) return

  const msgs = normalizeMessages(chat.messages)
  if (!msgs.length) return

  const sessionId = chat.currentSessionId || generateSessionId()
  chat.currentSessionId = sessionId

  let lastMessageAt = Date.now()
  if (!refreshTime && sessionId) {
    const existing = windowsStore.findWindowSession(props.windowId, sessionId)
    lastMessageAt = existing?.lastMessageAt ?? existing?.updatedAt ?? Date.now()
  }

  windowsStore.upsertWindowSession(props.windowId, {
    id: sessionId,
    messages: msgs,
    lastMessageAt,
  })
}

function startPageDrag(event) {
  if (event.button !== 0) return
  const page = feixunWindowRef.value?.closest('.feixun-page')
  if (!page) return
  event.preventDefault()
  startWindowDrag(event, { captureTarget: page })
}

function measureShellPageOffset() {
  const win = feixunWindowRef.value
  const page = win?.closest('.feixun-page')
  if (!win || !page) return null

  const pageRect = page.getBoundingClientRect()
  const winRect = win.getBoundingClientRect()
  return {
    left: winRect.left - pageRect.left,
    top: winRect.top - pageRect.top,
  }
}

function syncWindowLayoutMetricsPublic() {
  syncWindowLayoutMetrics()
}

defineExpose({
  startPageDrag,
  syncWindowLayoutMetrics: syncWindowLayoutMetricsPublic,
  measureShellPageOffset,
})

function handleWindowDragStart(event) {
  if (event.button !== 0) return
  raiseWindowToTop()
  if (event.target instanceof Element && event.target.closest('.window-resize-handle')) return
  if (event.target instanceof Element && event.target.closest('.feixun-window-resize-north__hit')) return
  if (event.target instanceof Element && event.target.closest('.feixun-window-ear--close')) return
  if (isInteractiveDragTarget(event.target)) return

  const gapHost = findGapDragHost(event.clientX, event.clientY)
  if (gapHost) {
    startWindowDrag(event)
    return
  }

  if (isWindowDragSurface(event.target)) {
    startWindowDrag(event)
  }
}

const phrolova = {
  name: '弗洛洛',
  avatar: '/avatars/phrolova.webp',
  elementIcon: '/icons/Phro_Games_logo.webp',
}

function touchSessionAfterUserSend() {
  const chat = chatState()
  if (!chat) return

  if (!chat.currentSessionId) {
    chat.currentSessionId = generateSessionId()
  }
  const msgs = normalizeMessages(chat.messages)
  if (!msgs.length) return

  windowsStore.upsertWindowSession(props.windowId, {
    id: chat.currentSessionId,
    messages: msgs,
    lastMessageAt: Date.now(),
  })
}

const chatSessions = computed(() => sortSessions(windowRecord.value?.sessions ?? []))
const isNewChatActive = computed(() => {
  const chat = windowRecord.value?.chat
  return chat ? !chat.currentSessionId && chat.messages.length === 0 : true
})
const userInitial = computed(() =>
  userStore.username?.charAt(0)?.toUpperCase() || '漂',
)

const showScrollToBottomBtn = ref(false)

function isNearMessageBottom() {
  const el = messageListRef.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight <= SCROLL_BOTTOM_THRESHOLD
}

function handleMessageListScroll() {
  const nearBottom = isNearMessageBottom()
  stickToBottom.value = nearBottom
  if (nearBottom) {
    showScrollToBottomBtn.value = false
  }
}

function scrollToBottomAndStick() {
  showScrollToBottomBtn.value = false
  stickToBottom.value = true
  scrollToBottom()
}

function dismissScrollToBottomBtn() {
  showScrollToBottomBtn.value = false
}

function isSessionActive(sessionId) {
  return sessionId != null && sessionId === currentSessionId.value
}

function isTypingBubble(msg, index) {
  return (
    msg.role === 'assistant' &&
    !msg.content?.trim() &&
    isLoading.value &&
    index === messages.value.length - 1
  )
}

function routeLabel(route) {
  const labels = { detection: '🔍 检测', analysis: '📊 分析', knowledge: '📚 知识', model: '🤖 模型' }
  return labels[route] || route
}

function toolInputPreview(input) {
  if (!input) return ''
  const str = typeof input === 'string' ? input : JSON.stringify(input)
  return str.length > 60 ? str.slice(0, 60) + '…' : str
}

function formatSessionTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()

  if (isToday) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

function stopActiveStream() {
  if (stopStream.value) {
    stopStream.value()
    stopStream.value = null
  }
  const chat = chatState()
  if (chat) {
    chat.isLoading = false
  }
}

function selectHistorySession(sessionId) {
  if (isLoading.value) {
    stopActiveStream()
  }
  suppressAutoScroll.value = true
  stickToBottom.value = false
  dismissScrollToBottomBtn()

  saveLocalSession()

  const session = windowsStore.findWindowSession(props.windowId, sessionId)
  if (!session) return

  const chat = chatState()
  if (!chat) return

  chat.currentSessionId = session.id
  chat.messages.splice(0, chat.messages.length, ...session.messages.map((message) => ({ ...message })))

  nextTick(() => {
    scrollToTop()
    scrollActiveHistoryIntoView()
    suppressAutoScroll.value = false
  })
}

async function startRenameSession(session) {
  skipRenameBlurCommit.value = true
  editingSessionId.value = session.id
  editingTitle.value = session.title
  await nextTick()
  const input = historyListRef.value?.querySelector(
    `.history-item[data-session-id="${session.id}"] .history-title-input`,
  )
  input?.focus()
  input?.select()
  skipRenameBlurCommit.value = false
}

function cancelRenameSession() {
  editingSessionId.value = null
  editingTitle.value = ''
}

function handleRenameBlur(session) {
  if (skipRenameBlurCommit.value) return
  window.setTimeout(() => {
    if (editingSessionId.value !== session.id) return
    commitRenameSession(session)
  }, 0)
}

function commitRenameSession(session) {
  if (editingSessionId.value !== session.id) return

  const title = editingTitle.value.trim()
  if (!title) {
    ElMessage.warning('标题不能为空')
    return
  }

  if (windowsStore.renameWindowSession(props.windowId, session.id, title)) {
    ElMessage.success('已重命名')
  }
  cancelRenameSession()
}

function handleDeleteSession(session) {
  cancelRenameSession()

  showPhroConfirm(
    `确定删除「${session.title}」吗？此操作不可恢复。`,
    '删除对话',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    },
  )
    .then(() => {
      if (isLoading.value) {
        stopActiveStream()
      }

      if (windowsStore.deleteWindowSession(props.windowId, session.id)) {
        const chat = chatState()
        if (chat && chat.currentSessionId === session.id) {
          const next = sortSessions(windowRecord.value?.sessions ?? [])[0]
          if (next) {
            chat.currentSessionId = next.id
            chat.messages.splice(0, chat.messages.length, ...next.messages.map((message) => ({ ...message })))
          } else {
            chat.currentSessionId = null
            chat.messages.splice(0)
          }
          chat.isLoading = false
        }

        ElMessage.success('已删除')
        nextTick(() => {
          if (messages.value.length === 0) {
            scrollToTop()
          } else {
            scrollToBottom()
          }
          scrollActiveHistoryIntoView()
        })
      }
    })
    .catch(() => {})
}

function scrollActiveHistoryIntoView() {
  const list = historyListRef.value
  if (!list) return
  const activeItem = list.querySelector('.history-item.active')
  activeItem?.scrollIntoView({ block: 'nearest' })
}

function autoResize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 100)}px`
}

function scrollToTop() {
  nextTick(() => {
    requestAnimationFrame(() => {
      const el = messageListRef.value
      if (el) {
        el.scrollTop = 0
        el.scrollTo({ top: 0, behavior: 'instant' })
      }
    })
  })
}

function scrollToBottom() {
  nextTick(() => {
    const el = messageListRef.value
    if (el) {
      el.scrollTop = el.scrollHeight
      stickToBottom.value = true
    }
  })
}

function syncMessageScroll() {
  if (suppressAutoScroll.value) return
  if (messages.value.length === 0) {
    scrollToTop()
    stickToBottom.value = true
    return
  }
  if (stickToBottom.value) {
    scrollToBottom()
  }
}

watch(messages, syncMessageScroll, { deep: true })

watch(isLoading, (loading, wasLoading) => {
  if (loading) {
    dismissScrollToBottomBtn()
    return
  }
  if (wasLoading && messages.value.length > 0) {
    nextTick(() => {
      if (!isNearMessageBottom()) {
        showScrollToBottomBtn.value = true
      }
    })
  }
})

function handleWindowLayoutResize() {
  if (isStickyMode.value) return

  if (
    windowScaleX.value === 1 &&
    windowScaleY.value === 1 &&
    windowOffset.value.x === 0 &&
    windowOffset.value.y === 0
  ) {
    syncWindowLayoutMetrics()
  }
}

onMounted(() => {
  windowsStore.markWindowMounted(props.windowId)
  inputText.value = ''
  editingSessionId.value = null
  editingTitle.value = ''
  stickToBottom.value = true
  dismissScrollToBottomBtn()

  scrollToTop()
  nextTick(() => {
    syncWindowLayoutMetrics()
  })
  window.addEventListener('resize', handleWindowLayoutResize)
  loadScene()
})

onUnmounted(() => {
  stopActiveStream()
  if (windowsStore.getWindow(props.windowId)) {
    saveLocalSession()
  }
  stopWindowDrag()
  stopWindowResize()
  window.removeEventListener('resize', handleWindowLayoutResize)
  stopCamera()
})

function handleNewChat() {
  if (isLoading.value) {
    stopActiveStream()
  }
  saveLocalSession()
  windowsStore.resetWindowChat(props.windowId)
  dismissScrollToBottomBtn()
  scrollToTop()
}

function buildHistory() {
  return messages.value.map((msg) => ({
    role: msg.role,
    content: msg.content,
  }))
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text || isLoading.value) return

  const chat = chatState()
  if (!chat) return

  inputText.value = ''
  nextTick(autoResize)

  stickToBottom.value = true
  dismissScrollToBottomBtn()
  chat.messages.push({ role: 'user', content: text })
  touchSessionAfterUserSend()
  chat.messages.push({ role: 'assistant', content: '' })
  chat.isLoading = true

  stopStream.value = streamChat(
    '/api/chat/stream',
    {
      message: text,
      history: buildHistory().slice(0, -2),
    },
    {
      onMessage: (data) => {
        if (typeof data === 'string') {
          const last = chat.messages[chat.messages.length - 1]
          if (last?.role === 'assistant') last.content = (last.content || '') + data
          return
        }
        const last = chat.messages[chat.messages.length - 1]
        if (!last || last.role !== 'assistant') return

        switch (data.type) {
          case 'route': {
            // 显示路由信息
            last.routeAgent = data.content
            break
          }
          case 'text_chunk': {
            // 流式文本追加
            if (data.content) last.content = (last.content || '') + data.content
            break
          }
          case 'tool_call': {
            // 工具调用中
            last.toolCall = { tool: data.tool, input: data.input }
            break
          }
          case 'tool_result': {
            // 工具调用完成
            last.toolCall = null
            // 如果是检测结果，解析并渲染卡片
            try {
              const result = typeof data.result === 'string' ? JSON.parse(data.result) : data.result
              if (result && (result.total_objects !== undefined || result.task_id)) {
                last.detectionResult = result
              }
            } catch {}
            break
          }
          case 'error': {
            ElMessage.error(data.content)
            last.content = (last.content || '') + `\n⚠ ${data.content}`
            break
          }
          default: {
            // 兼容旧格式：直接 content 字段
            if (data.content) last.content = (last.content || '') + data.content
          }
        }
        last.loading = false
      },
      onDone: () => {
        chat.isLoading = false
        stopStream.value = null
        const last = chat.messages[chat.messages.length - 1]
        if (last?.role === 'assistant' && !last.content.trim()) {
          chat.messages.pop()
        }
        saveLocalSession({ refreshTime: true })
      },
      onError: (err) => {
        chat.isLoading = false
        stopStream.value = null
        ElMessage.error(err.message || '对话请求失败')
        const last = chat.messages[chat.messages.length - 1]
        if (last?.role === 'assistant' && !last.content.trim()) {
          chat.messages.pop()
        }
      },
    },
  )
}

async function uploadImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  
  const token = localStorage.getItem('rsod_token')
  const response = await fetch('/api/chat/upload', {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  })
  
  if (!response.ok) {
    throw new Error('图片上传失败')
  }
  
  return response.json()
}

function triggerImageUpload() {
  imageInputRef.value?.click()
}

async function handleImageSelect(event) {
  const file = event.target.files?.[0]
  if (!file) return
  
  try {
    pendingImage.value = file
    pendingImagePreview.value = URL.createObjectURL(file)
    inputText.value = '检测这张图片中的PCB缺陷'
    ElMessage.success('图片已准备好，点击「检测」按钮开始')
  } catch (e) {
    ElMessage.error('图片处理失败')
  }
  
  event.target.value = ''
}

async function handleDetect() {
  if (!pendingImage.value || isLoading.value) return
  
  const chat = chatState()
  if (!chat) return
  
  inputText.value = '检测这张图片中的PCB缺陷'
  stickToBottom.value = true
  dismissScrollToBottomBtn()
  chat.messages.push({ role: 'user', content: '检测图片', image: pendingImagePreview.value })
  touchSessionAfterUserSend()
  chat.messages.push({ role: 'assistant', content: '' })
  chat.isLoading = true
  
  try {
    const uploadResult = await uploadImage(pendingImage.value)
    const imagePath = uploadResult.image_path
    
    stopStream.value = streamChat(
      '/api/chat/stream',
      {
        message: '检测这张图片中的PCB缺陷',
        image_path: imagePath,
        history: buildHistory().slice(0, -2),
      },
      {
        onMessage: (data) => {
          if (typeof data === 'string') {
            const last = chat.messages[chat.messages.length - 1]
            if (last?.role === 'assistant') {
              last.content = (last.content || '') + data
            }
            return
          }
          if (data?.error) {
            ElMessage.error(data.error)
            const last = chat.messages[chat.messages.length - 1]
            if (last?.role === 'assistant') {
              last.content = `⚠ ${data.error}`
            }
            return
          }
          if (data?.content) {
            const last = chat.messages[chat.messages.length - 1]
            if (last?.role === 'assistant') {
              last.content = (last.content || '') + data.content
            }
          }
        },
        onDone: () => {
          chat.isLoading = false
          stopStream.value = null
          const last = chat.messages[chat.messages.length - 1]
          if (last?.role === 'assistant' && !last.content.trim()) {
            chat.messages.pop()
          }
          saveLocalSession({ refreshTime: true })
          pendingImage.value = null
          pendingImagePreview.value = null
        },
        onError: (err) => {
          chat.isLoading = false
          stopStream.value = null
          ElMessage.error(err.message || '检测请求失败')
          const last = chat.messages[chat.messages.length - 1]
          if (last?.role === 'assistant' && !last.content.trim()) {
            chat.messages.pop()
          }
          pendingImage.value = null
          pendingImagePreview.value = null
        },
      },
    )
  } catch (e) {
    chat.isLoading = false
    ElMessage.error(e.message || '图片上传失败')
    pendingImage.value = null
    pendingImagePreview.value = null
  }
}

function classCn(name) {
  return PCB_SCENE.class_names_cn[name] || name
}

async function sendDetectionResultToChat(taskId, detections, file) {
  const defectSummary = detections.map(d => 
    `${classCn(d.class_name)} (置信度: ${(d.confidence * 100).toFixed(1)}%)`
  ).join('、')

  const messageText = `我刚检测了一张图片，任务ID: ${taskId}，发现了 ${detections.length} 个缺陷：${defectSummary}。请帮我分析这些缺陷。`

  chat.messages.push({ role: 'user', content: messageText })
  touchSessionAfterUserSend()
  chat.messages.push({ role: 'assistant', content: '' })
  chat.isLoading = true

  try {
    const uploadResult = await uploadImage(file)
    const imagePath = uploadResult.image_path

    stopStream.value = streamChat(
      '/api/chat/stream',
      {
        message: messageText,
        image_path: imagePath,
        history: buildHistory().slice(0, -2),
      },
      {
        onMessage: (data) => {
          if (typeof data === 'string') {
            const last = chat.messages[chat.messages.length - 1]
            if (last?.role === 'assistant') {
              last.content = (last.content || '') + data
            }
            return
          }
          if (data?.error) {
            ElMessage.error(data.error)
            const last = chat.messages[chat.messages.length - 1]
            if (last?.role === 'assistant') {
              last.content = `⚠ ${data.error}`
            }
            return
          }
          if (data?.content) {
            const last = chat.messages[chat.messages.length - 1]
            if (last?.role === 'assistant') {
              last.content = (last.content || '') + data.content
            }
          }
        },
        onDone: () => {
          chat.isLoading = false
          stopStream.value = null
          const last = chat.messages[chat.messages.length - 1]
          if (last?.role === 'assistant' && !last.content.trim()) {
            chat.messages.pop()
          }
          saveLocalSession({ refreshTime: true })
        },
        onError: (err) => {
          chat.isLoading = false
          stopStream.value = null
          ElMessage.error(err.message || '分析请求失败')
          const last = chat.messages[chat.messages.length - 1]
          if (last?.role === 'assistant' && !last.content.trim()) {
            chat.messages.pop()
          }
        },
      },
    )
  } catch (e) {
    chat.isLoading = false
    ElMessage.error(e.message || '图片上传失败')
    const last = chat.messages[chat.messages.length - 1]
    if (last?.role === 'assistant' && !last.content.trim()) {
      chat.messages.pop()
    }
  }
}

async function loadScene() {
  scene.value = await withApiFallback(
    async () => {
      const res = await getScenesApi()
      return Array.isArray(res?.data) ? res.data[0] : res?.[0]
    },
    () => mockGetScenes().then((s) => s[0]),
  )
}

function setDetectionResult(imageUrl, detections, inferenceTime = 0) {
  previewImage.value = imageUrl
  currentDetections.value = detections
  activeDetection.value = detections.length ? 0 : -1
  resultSummary.value = {
    totalObjects: detections.length,
    inferenceTime: Math.round(inferenceTime || detections.reduce((s, d) => s + (d.inference_time || 0), 0)),
  }
}

async function handleSingleDetect(file) {
  detectionLoading.value = true
  batchResults.value = []
  try {
    const detectFormData = new FormData()
    detectFormData.append('file', file)
    detectFormData.append('conf', detectionParams.value.confThreshold)
    detectFormData.append('scene_id', scene.value.id || 1)

    const res = await detectSingleApi(detectFormData)

    const imageUrl = URL.createObjectURL(file)
    const detections = (res.defects || []).map((d, i) => ({
      id: Date.now() * 1000 + i,
      task_id: res.task_id || null,
      image_path: file.name,
      annotated_image_url: imageUrl,
      ...d,
      inference_time: d.inference_time || 0,
      image_width: res.image_width || 0,
      image_height: res.image_height || 0,
      created_at: new Date().toISOString(),
    }))

    setDetectionResult(imageUrl, detections, res.inference_time)

    ElMessage.success(`检测完成，发现 ${detections.length} 个缺陷（任务ID: ${res.task_id}）`)

    sendDetectionResultToChat(res.task_id, detections, file)
  } catch (e) {
    ElMessage.error(e.message || '检测失败')
  } finally {
    detectionLoading.value = false
  }
}

async function handleBatchDetect(files) {
  detectionLoading.value = true
  try {
    const detectFormData = new FormData()
    files.forEach((f) => detectFormData.append('files', f))
    detectFormData.append('conf', detectionParams.value.confThreshold)
    detectFormData.append('scene_id', scene.value.id || 1)

    const res = await detectBatchApi(detectFormData)

    const grouped = {}
    const fileMap = new Map(files.map((f, i) => [f.name, { file: f, index: i }]))

    (res.results || []).forEach((r) => {
      const imageName = r.image_path ? r.image_path.split(/[\\/]/).pop() : `image_${Date.now()}`
      const fileInfo = fileMap.get(imageName) || files[0]
      const imageUrl = fileInfo ? URL.createObjectURL(fileInfo.file) : ''

      if (!grouped[imageName]) {
        grouped[imageName] = {
          name: imageName,
          imageUrl: imageUrl,
          detections: [],
        }
      }

      (r.defects || []).forEach((d, i) => {
        grouped[imageName].detections.push({
          id: Date.now() * 1000 + grouped[imageName].detections.length,
          task_id: res.task_id || null,
          image_path: imageName,
          annotated_image_url: imageUrl,
          ...d,
          inference_time: d.inference_time || r.inference_time || 0,
          image_width: r.image_width || 0,
          image_height: r.image_height || 0,
          created_at: new Date().toISOString(),
        })
      })
    })

    batchResults.value = Object.values(grouped)
    if (batchResults.value.length) {
      selectBatchItem(batchResults.value[0])
    }

    const totalDetections = batchResults.value.reduce((sum, item) => sum + item.detections.length, 0)
    ElMessage.success(`批量检测完成，共 ${totalDetections} 个缺陷（任务ID: ${res.task_id}）`)
  } catch (e) {
    ElMessage.error(e.message || '批量检测失败')
  } finally {
    detectionLoading.value = false
  }
}

function selectBatchItem(item) {
  setDetectionResult(item.imageUrl, item.detections)
}

async function handleVideoDetect(file) {
  detectionLoading.value = true
  videoProgress.value = 0
  batchResults.value = []
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('conf', detectionParams.value.confThreshold)
    formData.append('scene_id', scene.value.id || 1)
    formData.append('frame_interval', 10)
    
    const res = await detectVideoApi(formData)
    videoProgress.value = 100
    currentDetections.value = res.results || []
    previewImage.value = ''
    resultSummary.value = {
      totalObjects: res.total_objects || 0,
      inferenceTime: res.total_inference_time || 0,
    }
    ElMessage.success(`视频检测完成：${file.name}，发现 ${res.total_objects || 0} 个缺陷`)
  } catch (e) {
    ElMessage.error(e.message || '视频检测失败')
  } finally {
    detectionLoading.value = false
    setTimeout(() => { videoProgress.value = 0 }, 1500)
  }
}

function drawCameraOverlay() {
  const video = videoRef.value
  const canvas = cameraCanvasRef.value
  if (!video || !canvas || !cameraRunning.value) return

  const w = video.videoWidth || 640
  const h = video.videoHeight || 480
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, w, h)

  const detections = mockGenerateFrameDetections(w, h, detectionParams.value)
  currentDetections.value = detections.map((d, i) => ({
    ...d,
    id: i,
    inference_time: 16,
  }))
  resultSummary.value = {
    totalObjects: detections.length,
    inferenceTime: 16,
  }

  detections.forEach((det) => {
    const [x1, y1, x2, y2] = det.bbox
    ctx.strokeStyle = det.color || '#e74c3c'
    ctx.lineWidth = 2
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
    const label = `${det.class_name_cn} ${(det.confidence * 100).toFixed(0)}%`
    ctx.fillStyle = det.color || '#e74c3c'
    ctx.fillRect(x1, Math.max(0, y1 - 18), ctx.measureText(label).width + 8, 18)
    ctx.fillStyle = '#fff'
    ctx.font = '12px sans-serif'
    ctx.fillText(label, x1 + 4, Math.max(12, y1 - 5))
  })
}

async function startCamera() {
  try {
    const constraints = cameraDevices.value.length > 0
      ? { video: { deviceId: { exact: `camera-${selectedCamera.value}` } } }
      : { video: true }
    
    cameraStream = await navigator.mediaDevices.getUserMedia(constraints)
    videoRef.value.srcObject = cameraStream
    cameraRunning.value = true
    previewImage.value = ''
    cameraTimer = setInterval(drawCameraOverlay, 500)
    ElMessage.success('摄像头已开启')
  } catch (e) {
    ElMessage.error('无法访问摄像头，请检查权限或设备连接')
  }
}

async function loadCameraDevices() {
  try {
    const res = await getCamerasApi()
    cameraDevices.value = res?.devices || []
    if (cameraDevices.value.length > 0) {
      selectedCamera.value = cameraDevices.value[0].device_id
    }
  } catch {
    cameraDevices.value = []
  }
}

function stopCamera() {
  cameraRunning.value = false
  if (cameraTimer) {
    clearInterval(cameraTimer)
    cameraTimer = null
  }
  cameraStream?.getTracks().forEach((t) => t.stop())
  cameraStream = null
  if (videoRef.value) videoRef.value.srcObject = null
  const canvas = cameraCanvasRef.value
  canvas?.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height)
}

function onFeixunMounted() {
  loadScene()
  loadCameraDevices()
}

function onFeixunUnmounted() {
  stopCamera()
}
</script>

<style lang="scss" scoped>

// 鸣潮飞讯 — 浅色双栏（参照游戏内界面）
$sidebar-ratio: 280 / 960;
$accent-yellow: #f0c040;
$accent-blue: #4a8fd4;
$text-dark: #2c2c2c;
$text-gray: #888;
$text-light: #aaa;
// 弗洛洛 — 酒红 · 暗紫 · 金（与登录页一致）
$phro-crimson-deep: #3a1020;
$phro-crimson: #7a1028;
$phro-rose: #b83048;
$phro-plum: #3d1828;
$phro-gold: #c9952e;
$phro-gold-light: #e8b86d;
$phro-cream: #f5e6c8;
$phro-cream-muted: #d4bca8;
$phro-text-warm: #9a7068;
$phro-text-deep: #5a3840;
$phro-text-mid: #8a5860;
$phro-panel-bg: #f9efec;
$phro-border: rgba($phro-rose, 0.42);
$phro-divider-width: 2px;
$phro-radius: 10px;
$phro-radius-sm: 8px;
$phro-module-gap: 10px;
// 统一由 .feixun-window-chrome-fill 绘制；与最初窗口毛玻璃一致
$phro-glass-bg: rgba(32, 6, 14, 0.42);
$phro-gap-fill: $phro-glass-bg;
$phro-window-padding: 14px;
$phro-window-vertical-slack: 40px;
$phro-resize-handle: 10px;
$phro-resize-corner: 14px;
$phro-btn-bg: $phro-panel-bg;
$bubble-in: mix($phro-rose, #ffffff, 14%);
$bubble-out: #ffffff;

@mixin phro-hover-accent {
  border-color: rgba($phro-gold, 0.5);
  box-shadow:
    inset 3px 0 0 rgba($phro-gold, 0.9),
    0 0 0 1px rgba($phro-gold, 0.22);
}

@mixin phro-selected-accent {
  border-color: rgba($phro-gold, 0.65);
  box-shadow:
    inset 4px 0 0 $phro-gold,
    0 0 0 1px rgba($phro-gold, 0.28);
}

@mixin phro-interactive-surface {
  background: $phro-btn-bg;

  &:hover:not(.active) {
    background: $phro-btn-bg;
    @include phro-hover-accent;
  }

  &.active,
  &.active:hover {
    background: $phro-btn-bg;
    @include phro-selected-accent;
  }
}

@mixin phro-module-box {
  background: $phro-panel-bg;
  border: $phro-divider-width solid $phro-border;
  border-radius: $phro-radius;
}

@mixin phro-module-stack {
  display: flex;
  flex-direction: column;
  gap: $phro-module-gap;
  min-height: 0;
}

@mixin phro-action-btn-states {
  background: $phro-btn-bg;

  &:hover:not(:disabled):not(.active) {
    background: $phro-btn-bg;
    @include phro-hover-accent;
  }

  &:active:not(:disabled):not(.active) {
    background: $phro-btn-bg;
    @include phro-selected-accent;
  }

  &.active,
  &.active:hover,
  &.active:active {
    background: $phro-btn-bg;
    color: $phro-text-deep;
    @include phro-selected-accent;
  }

  &:focus-visible:not(.active) {
    outline: none;
    background: $phro-btn-bg;
    @include phro-hover-accent;
  }

  &:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}

@mixin phro-panel-sections {
  @include phro-module-stack;
  flex: 1;
  overflow: hidden;

  > :not(.history-list):not(.chat-messages-container) {
    @include phro-module-box;
    flex-shrink: 0;
  }

  > .history-list {
    flex: 1;
    min-height: 0;
    border: none;
    border-radius: 0;
    background: transparent;
  }

  > .chat-messages-container {
    @include phro-module-box;
    flex: 1;
    min-height: 0;
    position: relative;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 0;
  }
}

$phro-ear-w: 12;
$phro-ear-h: 7;
$phro-ear-corner-r: 3;
$phro-body-h: 100;
$phro-frame-w: 100;
$phro-frame-h: 107;
$phro-ear-w-pct: calc(#{$phro-ear-w} / #{$phro-frame-w} * 100%);
$phro-ear-top-pct: calc(#{$phro-ear-h} / #{$phro-frame-h} * 100%);
$phro-ear-h-pct: calc(#{$phro-ear-h} / #{$phro-frame-h} * 100%);

.feixun-window-shell {
  position: absolute;
  display: flex;
  min-height: 0;
  overflow: visible;
  box-sizing: border-box;
  pointer-events: none;

  .feixun-window-chrome,
  .feixun-window-resize-north {
    pointer-events: none;
  }

  .feixun-window-ear--drag,
  .feixun-window-ear--close,
  .feixun-window,
  .window-resize-handle {
    pointer-events: auto;
  }

  .feixun-window-resize-north__hit {
    pointer-events: stroke;
  }

  &.feixun-window-shell--inactive {
    opacity: 0.94;
  }

  &.feixun-window-shell--dragging {
    cursor: grabbing;

    .feixun-window,
    .feixun-window-ear--drag {
      cursor: grabbing;
    }

    .feixun-window * {
      user-select: none !important;
      -webkit-user-select: none !important;
      cursor: inherit;
    }
  }

  &.feixun-window-shell--resizing .feixun-window {
    will-change: transform, width, height;

    * {
      user-select: none !important;
      -webkit-user-select: none !important;
    }
  }

  &.feixun-window-shell--sticky {
    position: absolute;
    align-self: auto;
    margin: 0;
    width: auto;
    height: auto;
    max-width: none;
    max-height: none;

    &.feixun-window-shell--inactive {
      opacity: 1;
    }
  }
}

.feixun-window-resize-north {
  position: absolute;
  inset: 0;
  z-index: 26;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
}

.feixun-window-resize-north__hit {
  fill: none;
  stroke: transparent;
  stroke-width: 12;
  pointer-events: stroke;
  cursor: ns-resize;
  touch-action: none;
  vector-effect: non-scaling-stroke;
}

.feixun-window-chrome {
  position: absolute;
  inset: 0;
  z-index: 0;
  display: flex;
  flex-direction: column;
  pointer-events: none;
  shape-rendering: geometricPrecision;
}

.feixun-window-chrome__top {
  display: flex;
  flex: 0 0 var(--phro-chrome-ear-band, #{$phro-ear-top-pct});
  height: var(--phro-chrome-ear-band, #{$phro-ear-top-pct});
  width: 100%;
  min-width: 0;
}

.feixun-window-chrome__ear {
  flex: 0 0 var(--phro-chrome-ear-cap-w, #{$phro-ear-w-pct});
  width: var(--phro-chrome-ear-cap-w, #{$phro-ear-w-pct});
  height: 100%;
  display: block;
}

.feixun-window-chrome__bridge {
  flex: 1 1 auto;
  width: auto;
  min-width: 0;
  height: 100%;
  display: block;
}

.feixun-window-chrome__body {
  flex: 1 1 auto;
  min-height: 0;
  width: 100%;
  filter: drop-shadow(0 12px 40px rgba(40, 0, 12, 0.35));
}

.feixun-window-chrome__body-svg {
  display: block;
  width: 100%;
  height: 100%;
}

.feixun-window-chrome__fill {
  fill: $phro-gap-fill;
  stroke: none;
  pointer-events: none;
}

.feixun-window-chrome__stroke {
  fill: none;
  stroke: rgba(232, 184, 109, 0.62);
  stroke-width: 1.75;
  stroke-linejoin: round;
  stroke-linecap: round;
  paint-order: stroke fill;
  vector-effect: non-scaling-stroke;
  pointer-events: none;
}

.feixun-window-ear {
  position: absolute;
  z-index: 25;
  box-sizing: border-box;
  border: none;
  background: transparent;
  pointer-events: auto;

  &--drag {
    left: 0;
    top: 0;
    width: var(--phro-chrome-ear-w, #{$phro-ear-w-pct});
    height: var(--phro-chrome-ear-band, #{$phro-ear-h-pct});
    min-width: var(--phro-chrome-ear-w, #{$phro-ear-w-pct});
    max-width: var(--phro-chrome-ear-w, #{$phro-ear-w-pct});
    min-height: var(--phro-chrome-ear-band, #{$phro-ear-h-pct});
    max-height: var(--phro-chrome-ear-band, #{$phro-ear-h-pct});
    flex-shrink: 0;
    cursor: grab;
    touch-action: none;
  }

  &--close {
    right: 0;
    top: 0;
    width: var(--phro-chrome-ear-w, #{$phro-ear-w-pct});
    height: var(--phro-chrome-ear-vis-h, calc(#{$phro-ear-top-pct} + #{$phro-window-padding}));
    min-width: var(--phro-chrome-ear-w, #{$phro-ear-w-pct});
    max-width: var(--phro-chrome-ear-w, #{$phro-ear-w-pct});
    flex-shrink: 0;
    padding: 0;
    margin: 0;
    appearance: none;
    cursor: pointer;
    background: transparent;
    border: none;

    &::before,
    &::after {
      content: '';
      position: absolute;
      left: 50%;
      top: 50%;
      z-index: 1;
      width: 62%;
      height: 2.5px;
      max-width: 16px;
      border-radius: 1px;
      background: $phro-cream;
      pointer-events: none;
    }

    &::before {
      transform: translate(-50%, -50%) rotate(45deg);
    }

    &::after {
      transform: translate(-50%, -50%) rotate(-45deg);
    }

    &:hover {
      &::before,
      &::after {
        background: #fff8ee;
      }
    }
  }
}

.feixun-window-close-glow__shape {
  fill: transparent;
  pointer-events: none;
  transition: fill 0.12s ease;
}

.feixun-window-shell:has(.feixun-window-ear--close:hover) .feixun-window-close-glow__shape {
  fill: rgba($phro-rose, 0.26);
}

.feixun-window-ear__logo-zone {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 25;
  width: var(--phro-chrome-ear-w, #{$phro-ear-w-pct});
  height: var(--phro-chrome-ear-vis-h, calc(#{$phro-ear-top-pct} + #{$phro-window-padding}));
  box-sizing: border-box;
  padding: var(--phro-chrome-ear-logo-pad, #{$phro-window-padding});
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.feixun-window-ear__icon {
  display: block;
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  object-position: center;
  pointer-events: none;
  user-select: none;
  -webkit-user-drag: none;
  mix-blend-mode: lighten;
  opacity: 0.95;
}

.feixun-window {
  position: absolute;
  z-index: 1;
  top: var(--phro-chrome-ear-band, #{$phro-ear-top-pct});
  left: 0;
  width: 100%;
  height: calc(100% - var(--phro-chrome-ear-band, #{$phro-ear-top-pct}));
  display: flex;
  min-height: 0;
  gap: $phro-module-gap;
  padding: $phro-window-padding;
  border: none;
  border-radius: 0;
  overflow: hidden;
  background: transparent;
  box-shadow: none;
  cursor: grab;
  touch-action: none;
  box-sizing: border-box;
  user-select: none;
  -webkit-user-select: none;
}

.window-resize-handle {
  position: absolute;
  z-index: 24;
  touch-action: none;
  background: transparent;

  &--nw {
    top: 0;
    left: 0;
    width: $phro-resize-corner;
    height: $phro-resize-corner;
    z-index: 27;
    cursor: nwse-resize;
  }

  &--ne {
    top: 0;
    right: 0;
    width: $phro-resize-corner;
    height: $phro-resize-corner;
    z-index: 27;
    cursor: nesw-resize;
  }

  &--s {
    bottom: 0;
    left: $phro-resize-corner;
    right: $phro-resize-corner;
    height: $phro-resize-handle;
    cursor: ns-resize;
  }

  &--e {
    top: var(--phro-chrome-ear-band, #{$phro-ear-top-pct});
    right: 0;
    bottom: $phro-resize-corner;
    width: $phro-resize-handle;
    cursor: ew-resize;
  }

  &--w {
    top: var(--phro-chrome-ear-band, #{$phro-ear-top-pct});
    left: 0;
    bottom: $phro-resize-corner;
    width: $phro-resize-handle;
    cursor: ew-resize;
  }

  &--se {
    right: 0;
    bottom: 0;
    width: $phro-resize-corner;
    height: $phro-resize-corner;
    cursor: nwse-resize;
  }

  &--sw {
    left: 0;
    bottom: 0;
    width: $phro-resize-corner;
    height: $phro-resize-corner;
    cursor: nesw-resize;
  }
}

.sidebar-partner,
.sidebar-new-chat,
.contact-notice,
.chat-header,
.chat-input-bar {
  touch-action: auto;
}

.history-item-body,
.phro-btn,
.history-action-btn,
.feixun-window-ear--close {
  cursor: pointer;
}

.chat-input,
.history-title-input {
  cursor: text;
  user-select: text;
}

.feixun-window-ear--drag {
  cursor: grab;
  touch-action: none;
}

// ── 左侧历史对话 ──
.feixun-sidebar {
  flex: 0 0 240px;
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: linear-gradient(180deg, rgba($phro-rose, 0.08) 0%, rgba($phro-cream, 0.05) 100%);
  border-right: 1px solid rgba($phro-rose, 0.15);
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  flex-shrink: 0;
  background: rgba($phro-panel-bg, 0.8);
  border-bottom: 1px solid rgba($phro-rose, 0.1);

  .sidebar-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid rgba($phro-gold, 0.3);
  }

  .sidebar-title {
    flex: 1;
    display: flex;
    flex-direction: column;

    .sidebar-name {
      font-size: 14px;
      font-weight: 600;
      color: $phro-text-deep;
    }

    .sidebar-status {
      font-size: 11px;
      color: $phro-gold;
    }
  }

  .sidebar-new-btn {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: 1px dashed rgba($phro-rose, 0.4);
    background: rgba($phro-rose, 0.05);
    color: $phro-rose;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      border-color: $phro-rose;
      background: rgba($phro-rose, 0.1);
    }

    &:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .plus-icon {
      font-weight: 300;
    }
  }
}

.phro-btn {
  color: $phro-text-deep;
  background: $phro-btn-bg;
  border: $phro-divider-width solid $phro-border;
  border-radius: $phro-radius-sm;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.2s, color 0.2s, box-shadow 0.2s, border-color 0.2s;
  appearance: none;
  @include phro-action-btn-states;
}

.sidebar-partner-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.sidebar-partner-name {
  font-size: 16px;
  font-weight: 600;
  color: $phro-text-deep;
  letter-spacing: 0.04em;
}

.sidebar-partner-hint {
  font-size: 11px;
  color: $phro-text-mid;
}

.sidebar-new-chat {
  width: 100%;
  margin: 0;
  padding: 10px 14px;
  font-size: 13px;
  text-align: left;
  position: relative;
}

.history-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 8px;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba($phro-gold, 0.4);
    border-radius: 2px;
  }
}

.history-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: $phro-radius-sm;
  background: rgba($phro-panel-bg, 0.6);
  transition: all 0.2s ease;
  cursor: pointer;

  &:hover {
    background: rgba($phro-panel-bg, 0.9);
    transform: translateX(2px);
  }

  &.active {
    background: rgba($phro-gold, 0.12);
    box-shadow: 0 2px 8px rgba($phro-gold, 0.15);

    .history-dot {
      background: $phro-gold;
      box-shadow: 0 0 6px rgba($phro-gold, 0.6);
    }

    .history-title {
      font-weight: 600;
      color: $phro-text-deep;
    }
  }
}

.history-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba($phro-gold, 0.3);
  flex-shrink: 0;
  transition: all 0.2s;
}

.history-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.history-title {
  font-size: 13px;
  color: $phro-text-deep;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-preview {
  font-size: 11px;
  color: $phro-text-mid;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.history-time {
  font-size: 10px;
  color: $phro-text-warm;
}

.history-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;

  .history-item:hover & {
    opacity: 1;
  }
}

.history-item-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}

.history-item-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  position: relative;
  z-index: 5;
  pointer-events: auto;

  :deep(.el-tooltip__trigger) {
    display: inline-flex;
  }
}

.history-title-input {
  width: 100%;
  padding: 2px 6px;
  border: 1px solid rgba($phro-gold, 0.55);
  border-radius: 4px;
  background: #fff;
  color: $phro-text-deep;
  font-size: 14px;
  line-height: 1.4;
  outline: none;

  &:focus {
    border-color: $phro-gold;
    box-shadow: 0 0 0 2px rgba($phro-gold, 0.2);
  }
}

.history-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: rgba($phro-text-mid, 0.85);
  cursor: pointer;
  transition: color 0.15s, background 0.15s, border-color 0.15s;
  appearance: none;
  pointer-events: auto;

  .el-icon {
    font-size: 14px;
  }

  &:hover {
    color: $phro-gold;
    background: rgba($phro-gold, 0.12);
    border-color: rgba($phro-gold, 0.35);
  }

  &.danger:hover {
    color: $phro-crimson;
    background: rgba($phro-rose, 0.14);
    border-color: rgba($phro-rose, 0.35);
  }
}

.history-time {
  flex-shrink: 0;
  font-size: 11px;
  color: rgba($phro-gold, 0.75);
  padding-top: 2px;
  white-space: nowrap;
}

.contact-notice {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;

  .notice-icon {
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    object-fit: contain;
  }

  .notice-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .notice-name {
    font-size: 13px;
    color: $phro-text-deep;
  }

  .notice-preview {
    font-size: 11px;
    color: $phro-text-mid;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

// ── 右侧对话 ──
.feixun-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.chat-panel {
  @include phro-panel-sections;
  flex: 1;
  cursor: default;
}

.chat-header {
  padding: 12px 16px;
  background: linear-gradient(180deg, rgba($phro-gold, 0.08) 0%, transparent 100%);
  border-bottom: 1px solid rgba($phro-rose, 0.1);
  cursor: default;
}

.chat-header-content {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.chat-header-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba($phro-gold, 0.4);
}

.chat-header-info {
  display: flex;
  flex-direction: column;
}

.chat-header-name {
  font-size: 15px;
  font-weight: 600;
  color: $phro-text-deep;
}

.chat-header-status {
  font-size: 11px;
  color: $phro-gold;
}

.chat-header-actions {
  display: flex;
  gap: 6px;
}

.chat-header-action-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid rgba($phro-rose, 0.2);
  background: rgba($phro-panel-bg, 0.5);
  color: $phro-text-warm;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: rgba($phro-gold, 0.5);
    background: rgba($phro-gold, 0.1);
    color: $phro-gold;
  }

  &.active {
    border-color: $phro-gold;
    background: rgba($phro-gold, 0.15);
    color: $phro-gold;
    box-shadow: 0 0 8px rgba($phro-gold, 0.2);
  }

  .action-icon {
    width: 16px;
    height: 16px;
    fill: currentColor;
  }
}

.chat-messages-container {
  cursor: default;
}

.chat-messages {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 16px;
  overscroll-behavior: contain;
  cursor: default;
  touch-action: auto;
  user-select: text;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba($phro-gold, 0.35);
    border-radius: 2px;
  }
}

.scroll-to-bottom-btn {
  position: absolute;
  left: 50%;
  bottom: 14px;
  z-index: 5;
  transform: translateX(-50%);
  padding: 6px 16px;
  font-size: 12px;
  box-shadow: 0 4px 16px rgba(40, 0, 12, 0.18);
  pointer-events: auto;
}

.chat-watermark {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.04);
  pointer-events: none;
  z-index: 0;

  &::before,
  &::after {
    content: '';
    position: absolute;
    border-radius: 50%;
    border: 1px solid rgba(0, 0, 0, 0.03);
  }

  &::before {
    inset: 20px;
  }

  &::after {
    inset: 50px;
  }
}

.chat-empty {
  position: relative;
  z-index: 1;
  margin: 0;
  padding: 8px 0 0;
  color: $phro-text-mid;
  font-size: 14px;
  text-align: center;
}

// ── 消息气泡 ──
$msg-bubble-tail-top: 14px;

.msg-incoming,
.msg-outgoing {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 20px;
}

.msg-outgoing {
  justify-content: flex-end;

  .msg-body {
    align-items: flex-end;
  }
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid rgba(0, 0, 0, 0.06);

  &.user {
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    background: $phro-panel-bg;
    font-size: 13px;
    font-weight: 600;
    color: $phro-text-deep;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      background: $phro-panel-bg;
    }
  }
}

.msg-route-badge {
  font-size: 10px;
  color: $phro-gold;
  padding: 1px 8px;
  border-radius: 10px;
  background: rgba($phro-gold, 0.1);
  border: 1px solid rgba($phro-gold, 0.2);
  display: inline-block;
  width: fit-content;
  margin-bottom: 2px;
}

.msg-tool-call {
  font-size: 11px;
  color: $phro-text-mid;
  padding: 3px 10px;
  border-radius: 6px;
  background: rgba($phro-rose, 0.08);
  border: 1px solid rgba($phro-rose, 0.15);
  display: flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  margin-bottom: 2px;
}

.tool-call-icon {
  font-size: 12px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tool-call-name {
  font-weight: 600;
  color: $phro-text-deep;
}

.tool-call-input {
  color: $phro-text-mid;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.msg-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 75%;
}

.msg-bubble {
  position: relative;
  padding: 12px 16px;
  border-radius: $phro-radius-sm;
  line-height: 1.65;
  word-break: break-word;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);

  &.incoming {
    background: $bubble-in;
    border: 1px solid rgba($phro-rose, 0.32);
    border-radius: 4px $phro-radius-sm $phro-radius-sm $phro-radius-sm;
    box-shadow: 0 1px 5px rgba($phro-crimson, 0.08);

    &::before,
    &::after {
      content: '';
      position: absolute;
      top: $msg-bubble-tail-top;
      width: 0;
      height: 0;
      border-style: solid;
    }

    &::before {
      left: -7px;
      border-width: 7px 7px 7px 0;
      border-color: transparent rgba($phro-rose, 0.32) transparent transparent;
    }

    &::after {
      left: -5px;
      border-width: 6px 6px 6px 0;
      border-color: transparent $bubble-in transparent transparent;
    }
  }

  &.outgoing {
    background: $bubble-out;
    border: 1px solid rgba($phro-rose, 0.26);
    border-radius: $phro-radius-sm 4px $phro-radius-sm $phro-radius-sm;
    box-shadow: 0 1px 4px rgba($phro-crimson, 0.06);

    &::before,
    &::after {
      content: '';
      position: absolute;
      top: $msg-bubble-tail-top;
      width: 0;
      height: 0;
      border-style: solid;
    }

    &::before {
      right: -7px;
      border-width: 7px 0 7px 7px;
      border-color: transparent transparent transparent rgba($phro-rose, 0.26);
    }

    &::after {
      right: -5px;
      border-width: 6px 0 6px 6px;
      border-color: transparent transparent transparent $bubble-out;
    }
  }

  &.typing {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 48px;
    min-height: 40px;
    padding: 10px 16px;
  }
}

.typing-ellipsis {
  display: inline-block;
  font-size: 16px;
  line-height: 1;
  letter-spacing: 2px;
  color: $phro-text-mid;
  animation: ellipsis-pulse 1.2s infinite ease-in-out;
}
.msg-text {
  font-size: 14px;
  color: $phro-text-deep;
}
.chat-input-bar {
  position: relative;
  z-index: 25;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 16px;
  background: rgba($phro-panel-bg, 0.8);
  border-top: 1px solid rgba($phro-rose, 0.1);
}

.chat-input {
  flex: 1;
  min-height: 38px;
  max-height: 100px;
  padding: 10px 14px;
  border: 1px solid rgba($phro-rose, 0.2);
  border-radius: $phro-radius;
  background: #fff;
  color: $text-dark;
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  outline: none;
  font-family: inherit;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.2s;

  &::-webkit-scrollbar {
    width: 0;
    height: 0;
    display: none;
  }

  &::placeholder {
    color: $phro-text-warm;
  }

  &:focus {
    border-color: rgba($phro-gold, 0.6);
    box-shadow: 0 0 0 3px rgba($phro-gold, 0.1), 0 2px 8px rgba($phro-gold, 0.15);
  }

  &:disabled {
    opacity: 0.5;
  }
}

.send-btn {
  flex-shrink: 0;
  height: 38px;
  padding: 0 20px;
  font-size: 14px;
  font-weight: 500;
  background: linear-gradient(135deg, rgba($phro-gold, 0.9) 0%, rgba($phro-rose, 0.8) 100%);
  border-color: rgba($phro-gold, 0.4);
  color: #fff;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, $phro-gold 0%, rgba($phro-rose, 0.9) 100%);
    box-shadow: 0 2px 8px rgba($phro-gold, 0.3);
  }

  &:disabled {
    opacity: 0.5;
  }
}
.msg-image {
  margin-bottom: 8px;
  border-radius: $phro-radius-sm;
  overflow: hidden;

  img {
    max-width: 200px;
    max-height: 200px;
    object-fit: contain;
  }
}

:deep(.markdown-body) {
  p {
    margin: 0 0 6px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  code {
    background: rgba(0, 0, 0, 0.05);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 0.9em;
  }
}

@keyframes ellipsis-pulse {
  0%,
  100% {
    opacity: 0.35;
  }

  50% {
    opacity: 1;
  }
}

.feixun-detection-panel {
  width: 280px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  border-left: 1px solid rgba($phro-rose, 0.2);
  overflow: hidden;
}

.detection-panel-header {
  h3 {
    margin: 0 0 8px;
    font-size: 14px;
    font-weight: 600;
    color: $phro-text-deep;
  }
}

.detection-tabs {
  display: flex;
  gap: 4px;
  background: rgba($phro-panel-bg, 0.8);
  padding: 4px;
  border-radius: $phro-radius-sm;
}

.detection-tab {
  flex: 1;
  padding: 6px 8px;
  font-size: 11px;
  color: $phro-text-mid;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    color: $phro-text-deep;
  }

  &.active {
    background: rgba($phro-gold, 0.15);
    color: $phro-gold;
    font-weight: 600;
  }
}

.detection-panel-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
  overflow: hidden;
}

.detection-section {
  @include phro-module-box;
  padding: 8px;
  border-radius: $phro-radius-sm;
  background: rgba($phro-panel-bg, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba($phro-gold, 0.15);
  transition: all 0.3s ease;

  &:hover {
    border-color: rgba($phro-gold, 0.3);
    box-shadow: 0 2px 12px rgba($phro-gold, 0.08);
  }

  &--grow {
    flex-shrink: 0;
    overflow: hidden;
  }
}

.detection-section-title {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 600;
  color: $phro-text-mid;
  display: flex;
  align-items: center;
  gap: 6px;

  &::before {
    content: '';
    width: 4px;
    height: 12px;
    background: $phro-gold;
    border-radius: 2px;
  }
}

.scene-name {
  font-size: 14px;
  color: $phro-text-deep;
  margin: 0 0 10px;
  font-weight: 500;
}

.class-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.camera-panel {
  position: relative;
  border-radius: $phro-radius;
  overflow: hidden;
  background: rgba($phro-panel-bg, 0.9);
  border: 1px solid rgba($phro-gold, 0.2);
  display: flex;
  flex-direction: column;
  padding: 12px;
}

.camera-select {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba($phro-text-deep, 0.05);
  border-radius: $phro-radius-sm;
  border: 1px solid rgba($phro-gold, 0.1);
  margin-bottom: 10px;

  .camera-select-label {
    font-size: 12px;
    color: $phro-text-mid;
    font-weight: 500;
  }

  .camera-select-input {
    flex: 1;
    padding: 6px 10px;
    border: 1px solid rgba($phro-gold, 0.2);
    border-radius: $phro-radius-sm;
    background: rgba($phro-cream, 0.05);
    font-size: 12px;
    color: $phro-text-deep;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover:not(:disabled) {
      border-color: rgba($phro-gold, 0.4);
    }

    &:focus {
      outline: none;
      border-color: $phro-gold;
      box-shadow: 0 0 0 2px rgba($phro-gold, 0.15);
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
}

.camera-video-container {
  position: relative;
  background: linear-gradient(145deg, rgba($phro-text-deep, 0.3), rgba($phro-text-deep, 0.5));
  border-radius: $phro-radius-sm;
  overflow: hidden;
  margin-bottom: 10px;
  border: 1px solid rgba($phro-gold, 0.1);
}

.camera-video,
.camera-overlay {
  width: 100%;
  display: block;
  max-height: 200px;
  object-fit: contain;
}

.camera-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.camera-actions {
  display: flex;
  gap: 8px;

  .phro-btn {
    flex: 1;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
    border-radius: $phro-radius-sm;
    transition: all 0.2s ease;

    &--primary {
      background: linear-gradient(145deg, rgba($phro-gold, 0.25), rgba($phro-gold, 0.15));
      border-color: rgba($phro-gold, 0.4);
      color: $phro-gold;

      &:hover:not(:disabled) {
        background: linear-gradient(145deg, rgba($phro-gold, 0.35), rgba($phro-gold, 0.2));
        box-shadow: 0 2px 8px rgba($phro-gold, 0.2);
      }
    }

    &:not(&--primary):hover:not(:disabled) {
      background: rgba($phro-gold, 0.1);
      border-color: rgba($phro-gold, 0.3);
    }

    &:disabled {
      opacity: 0.4;
    }
  }
}

.video-progress {
  margin-top: 10px;
}

.detection-result-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
}

.result-preview {
  height: 180px;
  @include phro-module-box;
  padding: 8px;
  overflow: hidden;
}

.result-list-panel {
  flex: 1;
  min-height: 0;
  @include phro-module-box;
  padding: 8px;
  overflow: hidden;
}

.batch-card {
  @include phro-module-box;
  padding: 10px;
}

.batch-title {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: $phro-text-mid;
}

.batch-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.batch-item {
  @include phro-module-box;
  padding: 6px;
  cursor: pointer;
  text-align: center;
  font-size: 11px;
  color: $phro-text-deep;
  transition: border-color 0.2s;

  &:hover {
    border-color: rgba($phro-gold, 0.55);
  }

  img {
    width: 100%;
    height: 50px;
    object-fit: cover;
    border-radius: 4px;
    margin-bottom: 4px;
  }

  .batch-count {
    display: block;
    color: $phro-gold;
    margin-top: 2px;
  }
}

:deep(.bbox-canvas-wrap) {
  height: 100%;
}

:deep(.result-panel) {
  height: 100%;
}
</style>
