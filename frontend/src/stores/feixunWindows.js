/**
 * 飞讯多窗口 — 每窗独立布局、对话、历史（严禁跨窗口共享）
 */
import { defineStore } from 'pinia'
import {
  createEmptySessions,
  deleteSessionFromList,
  findSessionInList,
  renameSessionInList,
  sortSessions,
  upsertSessionInList,
} from './feixunWindowSessions'

import { computeStickyFanStepPx } from '@/components/feixun/feixunWindowChrome'

const LEGACY_SESSIONS_KEY = 'phrolova_chat_sessions'

function getSessionsKey() {
  try {
    const raw = localStorage.getItem('rsod_user')
    const user = raw ? JSON.parse(raw) : null
    const uid = user?.id || 'anonymous'
    return `phrolova_chat_sessions_${uid}`
  } catch {
    return LEGACY_SESSIONS_KEY
  }
}

const STICKY_STACK_ORIGIN = { left: 24, top: 24 }
const DEFAULT_STICKY_FAN_STEP = { x: 88, y: 0 }
const STICKY_FALLBACK_SIZE = { width: 1200, height: 750 }

function resolveStickyRefSize(windows, snapshots = {}) {
  for (const window of windows) {
    const snapshot = snapshots[window.id]
    const width =
      window.baseSize?.width ||
      snapshot?.stickyShellSize?.width ||
      snapshot?.baseSize?.width ||
      0
    const height =
      window.baseSize?.height ||
      snapshot?.stickyShellSize?.height ||
      snapshot?.baseSize?.height ||
      0
    if (width > 0 && height > 0) {
      return { width, height }
    }
  }
  return { ...STICKY_FALLBACK_SIZE }
}

function applyStickyStackZOrder(windows, focusedWindowId) {
  if (!windows.length) return

  const count = windows.length
  const focusIndex = windows.findIndex((window) => window.id === focusedWindowId)

  if (focusIndex < 0) {
    windows.forEach((window, index) => {
      window.zIndex = index + 1
    })
    return
  }

  // 自顶向下：选中窗 → 右侧顺序 → 左侧逆序
  const topToBottom = [windows[focusIndex]]

  for (let i = focusIndex + 1; i < count; i += 1) {
    topToBottom.push(windows[i])
  }

  for (let i = focusIndex - 1; i >= 0; i -= 1) {
    topToBottom.push(windows[i])
  }

  topToBottom.forEach((window, rankFromTop) => {
    window.zIndex = count - rankFromTop
  })
}

function computeStickyStackAnchor(pageEl, windows, snapshots, fanStep) {
  const { width, height } = resolveStickyRefSize(windows, snapshots)
  const count = Math.max(windows.length, 1)
  const stepX = fanStep?.x ?? DEFAULT_STICKY_FAN_STEP.x
  const stackWidth = width + Math.max(0, count - 1) * stepX

  const availWidth = pageEl?.clientWidth ?? 960
  const availHeight = pageEl?.clientHeight ?? 680

  return {
    left: Math.max(16, Math.round((availWidth - stackWidth) / 2)),
    top: Math.max(16, Math.round((availHeight - height) / 2)),
  }
}

let windowCounter = 0

function generateWindowId() {
  windowCounter += 1
  return `feixun-${Date.now()}-${windowCounter}`
}

function loadLegacySessions() {
  try {
    const raw = localStorage.getItem(getSessionsKey())
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed)
      ? sortSessions(
          parsed.map((session) => ({
            ...session,
            lastMessageAt: session.lastMessageAt ?? session.updatedAt ?? 0,
          })),
        )
      : createEmptySessions()
  } catch {
    return createEmptySessions()
  }
}

function persistLegacySessions(sessions) {
  localStorage.setItem(getSessionsKey(), JSON.stringify(sessions))
}

export function createEmptyChat() {
  return {
    messages: [],
    currentSessionId: null,
    isLoading: false,
  }
}

function createWindowRecord({ windowId, offsetIndex, zIndex, isInitial = false }) {
  const cascade = offsetIndex * 100
  return {
    id: windowId,
    instanceKey: `${windowId}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    isFresh: true,
    isInitial,
    zIndex,
    offset: { x: cascade, y: cascade },
    scaleX: 1,
    scaleY: 1,
    baseSize: { width: 0, height: 0 },
    chromeBaseSize: { width: 0, height: 0 },
    anchor: null,
    stickyEarOffset: { x: 0, y: 0 },
    chat: createEmptyChat(),
    sessions: isInitial ? loadLegacySessions() : createEmptySessions(),
  }
}

export function applyEmptyChat(chat) {
  if (!chat) return
  chat.currentSessionId = null
  chat.isLoading = false
  chat.messages.splice(0)
}

export const useFeixunWindowsStore = defineStore('feixunWindows', {
  state: () => ({
    windows: [],
    focusedWindowId: null,
    initialized: false,
    layoutMode: 'frame',
    stickyStack: {
      anchor: { left: 0, top: 0 },
      offset: { x: 0, y: 0 },
      fanStep: { ...DEFAULT_STICKY_FAN_STEP },
    },
    frameLayoutSnapshots: {},
    layoutPrepareHook: null,
    layoutPageEl: null,
  }),

  getters: {
    openWindows(state) {
      return state.windows
    },

    isStickyLayout(state) {
      return state.layoutMode === 'sticky'
    },

    sharedChromeBase(state) {
      for (const window of state.windows) {
        if (window.chromeBaseSize?.width > 0 && window.chromeBaseSize?.height > 0) {
          return { width: window.chromeBaseSize.width, height: window.chromeBaseSize.height }
        }
      }
      for (const window of state.windows) {
        if (window.baseSize?.width > 0 && window.baseSize?.height > 0) {
          return { width: window.baseSize.width, height: window.baseSize.height }
        }
      }
      return { ...STICKY_FALLBACK_SIZE }
    },
  },

  actions: {
    ensureInitialWindow() {
      if (this.initialized) return
      this.initialized = true
      if (this.windows.length === 0) {
        this.createWindow({ isInitial: true })
      }
    },

    createWindow({ isInitial = false } = {}) {
      const offsetIndex = isInitial ? 0 : this.windows.length
      const maxZ = this.windows.reduce((max, window) => Math.max(max, window.zIndex), 0)
      const windowId = generateWindowId()
      const record = createWindowRecord({
        windowId,
        offsetIndex,
        zIndex: maxZ + 1,
        isInitial,
      })

      applyEmptyChat(record.chat)
      this.windows.push(record)

      if (this.layoutMode === 'sticky') {
        const refSize = resolveStickyRefSize(
          this.windows.filter((window) => window.id !== windowId),
          this.frameLayoutSnapshots,
        )
        const refWindow = this.windows.find(
          (window) => window.id !== windowId && window.baseSize.width > 0,
        )
        if (refWindow) {
          record.baseSize = { ...refWindow.baseSize }
        } else if (refSize.width > 0 && refSize.height > 0) {
          record.baseSize = { ...refSize }
        }
        this.frameLayoutSnapshots[windowId] = {
          offset: { x: 0, y: 0 },
          anchor: null,
          scaleX: 1,
          scaleY: 1,
          baseSize: { width: 0, height: 0 },
          stickyShellSize:
            record.baseSize.width > 0 && record.baseSize.height > 0
              ? { ...record.baseSize }
              : { ...refSize },
          chromeBaseSize: { ...this.sharedChromeBase },
        }
        this.recomputeStickyFanLayout(this.layoutPageEl)
      }

      this.focusWindow(windowId)
      return windowId
    },

    focusWindow(windowId) {
      const target = this.windows.find((window) => window.id === windowId)
      if (!target) return

      this.focusedWindowId = windowId

      if (this.layoutMode === 'sticky') {
        applyStickyStackZOrder(this.windows, windowId)
        return
      }

      const maxZ = this.windows.reduce((max, window) => Math.max(max, window.zIndex), 0)
      target.zIndex = maxZ + 1
    },

    closeWindow(windowId) {
      const target = this.windows.find((window) => window.id === windowId)
      if (!target) return

      delete this.frameLayoutSnapshots[windowId]

      this.windows = this.windows.filter((window) => window.id !== windowId)

      if (this.focusedWindowId === windowId) {
        const remaining = this.windows
        this.focusedWindowId = remaining.length ? remaining[remaining.length - 1].id : null
      }

      if (this.windows.length === 0) {
        this.focusedWindowId = null
        this.initialized = false
      }

      if (this.layoutMode === 'sticky') {
        this.recomputeStickyFanLayout(this.layoutPageEl)
        this.syncStickyStackZOrder()
      }
    },

    setLayoutPageEl(pageEl) {
      this.layoutPageEl = pageEl ?? null
    },

    getWindow(windowId) {
      return this.windows.find((window) => window.id === windowId)
    },

    patchWindow(windowId, patch) {
      const target = this.getWindow(windowId)
      if (!target) return null
      const { chat, sessions, ...layoutPatch } = patch
      Object.assign(target, layoutPatch)
      return target
    },

    patchStickyStackOffset(offset) {
      this.stickyStack.offset = { x: offset.x, y: offset.y }
    },

    translateAllWindowOffsets(origins, dx, dy) {
      this.windows.forEach((window) => {
        const origin = origins[window.id]
        if (!origin) return
        this.patchWindow(window.id, {
          offset: { x: origin.x + dx, y: origin.y + dy },
        })
      })
    },

    roundAllWindowOffsets() {
      this.windows.forEach((window) => {
        this.patchWindow(window.id, {
          offset: {
            x: Math.round(window.offset.x),
            y: Math.round(window.offset.y),
          },
        })
      })
    },

    setLayoutPrepareHook(hook) {
      this.layoutPrepareHook = hook
    },

    async toggleLayoutMode() {
      if (this.layoutMode === 'frame') {
        let pageEl = null
        try {
          pageEl = await this.layoutPrepareHook?.()
        } catch (error) {
          console.warn('[feixunWindows] prepare sticky layout failed', error)
        }
        this.enterStickyLayout(pageEl)
        return
      }
      this.exitStickyLayout()
    },

    syncStickyStackZOrder() {
      if (this.layoutMode !== 'sticky') return
      applyStickyStackZOrder(this.windows, this.focusedWindowId)
    },

    recomputeStickyFanLayout(pageEl = null) {
      if (pageEl) {
        this.layoutPageEl = pageEl
      }

      const fanStep = {
        x: computeStickyFanStepPx(this.sharedChromeBase.width),
        y: 0,
      }
      this.stickyStack.fanStep = fanStep

      this.windows.forEach((window, index) => {
        this.patchWindow(window.id, {
          stickyEarOffset: {
            x: index * fanStep.x,
            y: 0,
          },
        })
      })

      if (this.layoutMode === 'sticky') {
        this.stickyStack.anchor = computeStickyStackAnchor(
          pageEl ?? this.layoutPageEl,
          this.windows,
          this.frameLayoutSnapshots,
          fanStep,
        )
      }
    },

    enterStickyLayout(pageEl = null) {
      this.frameLayoutSnapshots = {}
      const refSize = resolveStickyRefSize(this.windows)
      const sharedChrome = this.sharedChromeBase

      this.windows.forEach((window) => {
        const measuredBase =
          window.baseSize?.width > 0 && window.baseSize?.height > 0
            ? { ...window.baseSize }
            : null
        const stickyShellSize = measuredBase ?? { ...refSize }

        const chromeBaseSize =
          sharedChrome.width > 0 && sharedChrome.height > 0
            ? { ...sharedChrome }
            : window.chromeBaseSize?.width > 0
              ? { ...window.chromeBaseSize }
              : { ...stickyShellSize }

        this.frameLayoutSnapshots[window.id] = {
          offset: { ...window.offset },
          anchor: window.anchor ? { ...window.anchor } : null,
          scaleX: window.scaleX,
          scaleY: window.scaleY,
          baseSize: measuredBase ?? { width: 0, height: 0 },
          stickyShellSize,
          chromeBaseSize,
        }
      })

      this.stickyStack.offset = { x: 0, y: 0 }
      this.recomputeStickyFanLayout(pageEl)
      this.layoutMode = 'sticky'
      this.syncStickyStackZOrder()
    },

    exitStickyLayout() {
      const snapshots = { ...this.frameLayoutSnapshots }
      this.layoutMode = 'frame'

      this.windows.forEach((window, index) => {
        window.stickyEarOffset = { x: 0, y: 0 }
        const snapshot = snapshots[window.id]
        if (snapshot) {
          window.offset = { ...snapshot.offset }
          window.anchor = snapshot.anchor ? { ...snapshot.anchor } : null
          window.scaleX = snapshot.scaleX
          window.scaleY = snapshot.scaleY
          if (snapshot.baseSize?.width > 0 && snapshot.baseSize?.height > 0) {
            window.baseSize = { ...snapshot.baseSize }
          } else {
            window.baseSize = { width: 0, height: 0 }
          }
          if (snapshot.chromeBaseSize?.width > 0 && snapshot.chromeBaseSize?.height > 0) {
            window.chromeBaseSize = { ...snapshot.chromeBaseSize }
          }
          return
        }

        const cascade = index * 100
        window.offset = { x: cascade, y: cascade }
        window.anchor = null
      })

      this.frameLayoutSnapshots = {}
    },

    getSortedSessions(windowId) {
      const target = this.getWindow(windowId)
      return target ? sortSessions(target.sessions) : []
    },

    upsertWindowSession(windowId, payload) {
      const target = this.getWindow(windowId)
      if (!target) return null

      const id = upsertSessionInList(target.sessions, payload)
      if (id && target.isInitial) {
        persistLegacySessions(target.sessions)
      }
      return id
    },

    deleteWindowSession(windowId, sessionId) {
      const target = this.getWindow(windowId)
      if (!target) return false

      const removed = deleteSessionFromList(target.sessions, sessionId)
      if (removed && target.isInitial) {
        persistLegacySessions(target.sessions)
      }
      return removed
    },

    renameWindowSession(windowId, sessionId, title) {
      const target = this.getWindow(windowId)
      if (!target) return false

      const renamed = renameSessionInList(target.sessions, sessionId, title)
      if (renamed && target.isInitial) {
        persistLegacySessions(target.sessions)
      }
      return renamed
    },

    findWindowSession(windowId, sessionId) {
      const target = this.getWindow(windowId)
      if (!target) return null
      return findSessionInList(target.sessions, sessionId)
    },

    resetWindowChat(windowId) {
      const target = this.getWindow(windowId)
      if (!target?.chat) return
      applyEmptyChat(target.chat)
    },

    markWindowMounted(windowId) {
      const target = this.getWindow(windowId)
      if (!target) return
      if (target.isFresh) {
        applyEmptyChat(target.chat)
      }
      target.isFresh = false
    },
  },
})
