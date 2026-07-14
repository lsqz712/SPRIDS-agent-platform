<template>
  <Teleport to="body">
    <Transition name="app-tool-flyout">
      <AppToolFlyoutPanel
        v-if="toolMenu.activeSection"
        :key="toolMenu.activeSection"
        :section="toolMenu.activeSection"
      />
    </Transition>
  </Teleport>
</template>

<script setup>
import { nextTick, onUnmounted, watch } from 'vue'
import { useAppToolMenuStore } from '@/stores/appToolMenu'
import AppToolFlyoutPanel from './AppToolFlyoutPanel.vue'

const toolMenu = useAppToolMenuStore()

function refreshAnchor() {
  if (toolMenu.activeSection) {
    toolMenu.updateAnchorRect()
  }
}

watch(
  () => toolMenu.activeSection,
  async (section) => {
    if (section) {
      await nextTick()
      toolMenu.updateAnchorRect()
      window.addEventListener('resize', refreshAnchor)
      window.addEventListener('scroll', refreshAnchor, true)
      return
    }
    window.removeEventListener('resize', refreshAnchor)
    window.removeEventListener('scroll', refreshAnchor, true)
  },
)

onUnmounted(() => {
  window.removeEventListener('resize', refreshAnchor)
  window.removeEventListener('scroll', refreshAnchor, true)
})
</script>

<style lang="scss">
.app-tool-flyout-leave-active {
  pointer-events: none;
}

.app-tool-flyout-enter-from .app-tool-flyout__bubble,
.app-tool-flyout-leave-to .app-tool-flyout__bubble {
  opacity: 0;
  transform: translateX(-12px) scale(0.96);
}

.app-tool-flyout-enter-from .app-tool-flyout__bubble.is-clip-ready::before,
.app-tool-flyout-leave-to .app-tool-flyout__bubble.is-clip-ready::before {
  opacity: 0;
}

.app-tool-flyout-enter-active .app-tool-flyout__bubble,
.app-tool-flyout-leave-active .app-tool-flyout__bubble {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.app-tool-flyout-enter-active .app-tool-flyout__bubble::before,
.app-tool-flyout-leave-active .app-tool-flyout__bubble::before {
  transition: opacity 0.2s ease;
}
</style>
