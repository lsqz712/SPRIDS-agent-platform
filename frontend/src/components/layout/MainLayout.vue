<template>
  <div class="main-layout">
    <div class="layout-body layout-body--feixun">
      <div class="layout-feixun-bg" aria-hidden="true" />
      <AppRightToolbar />
      <PhroContextMenu />
      <AppSidebar feixun-theme />
      <main
        class="layout-content"
        :class="{
          'layout-content--chat': isChatRoute,
          'layout-content--module': isModuleRoute,
        }"
      >
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppSidebar from './AppSidebar.vue'
import AppRightToolbar from './AppRightToolbar.vue'
import PhroContextMenu from '@/components/common/PhroContextMenu.vue'
import { usePhroContextMenuStore } from '@/stores/phroContextMenu'
import { buildTextContextMenuItems } from '@/utils/phroTextContextMenu'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const contextMenu = usePhroContextMenuStore()
const isDev = import.meta.env.DEV
const isChatRoute = computed(() => route.path.startsWith('/chat'))
const isModuleRoute = computed(() => !isChatRoute.value)

onMounted(() => {
  userStore.migratePreviewUser()
  document.addEventListener('contextmenu', handleLayoutContextMenu, true)
})

onUnmounted(() => {
  document.removeEventListener('contextmenu', handleLayoutContextMenu, true)
})

/** @param {MouseEvent} event */
function handleLayoutContextMenu(event) {
  const target = event.target
  if (!(target instanceof Element)) {
    event.preventDefault()
    return
  }

  if (!target.closest('.main-layout')) return

  if (target.closest('input, textarea, [contenteditable="true"]')) {
    return
  }

  const items = buildTextContextMenuItems(event)
  if (items?.length) {
    event.preventDefault()
    contextMenu.open({
      x: event.clientX,
      y: event.clientY,
      items,
    })
    return
  }

  event.preventDefault()
}

function exitToLogin() {
  userStore.logout()
  router.push('/login')
}
</script>

<style lang="scss" scoped>
.main-layout {
  width: 100%;
  height: 100%;
}

.layout-body {
  width: 100%;
  height: 100%;
  display: flex;
  overflow: hidden;
  min-height: 0;
  position: relative;

  &--feixun {
    user-select: none;
    -webkit-user-select: none;

    input,
    textarea,
    [contenteditable='true'] {
      user-select: text;
      -webkit-user-select: text;
    }

    :deep(.msg-bubble),
    :deep(.msg-body),
    :deep(.phro-table-wrap),
    :deep(.phro-table-wrap *) {
      user-select: text;
      -webkit-user-select: text;
    }

    > :not(.layout-feixun-bg):not(.app-sidebar) {
      position: relative;
      z-index: 1;
    }

    :deep(.app-sidebar) {
      position: relative;
      z-index: 210;
    }
  }
}

.layout-feixun-bg {
  position: fixed;
  inset: 0;
  background: url('/login-bg.jpg') center / cover no-repeat fixed;
  z-index: 0;
  pointer-events: none;
}

.layout-content {
  flex: 1;
  background: transparent;
  overflow-y: auto;
  padding: $spacing-lg;
  min-height: 0;

  &--chat {
    padding: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  &--module {
    padding: $phro-module-gap;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
}

.dev-exit-btn {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 1000;
  padding: 6px 14px;
  font-size: 12px;
  color: rgba(245, 230, 200, 0.85);
  background: rgba(32, 6, 14, 0.55);
  border: 1px solid rgba(212, 175, 120, 0.35);
  border-radius: 16px;
  cursor: pointer;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  transition: all 0.2s;

  &:hover {
    color: #f5e6c8;
    background: rgba(32, 6, 14, 0.72);
    border-color: rgba(232, 184, 109, 0.55);
  }
}
</style>
