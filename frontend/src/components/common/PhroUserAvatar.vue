<template>
  <el-avatar
    :size="size"
    :src="src || undefined"
    class="phro-user-avatar"
    :class="`phro-user-avatar--${variant}`"
    :style="avatarStyle"
  >
    <slot>{{ fallback }}</slot>
  </el-avatar>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: { type: Number, default: 40 },
  src: { type: String, default: '' },
  fallback: { type: String, default: '' },
  /** panel：奶油模块区 | sidebar：侧边栏用户区 */
  variant: {
    type: String,
    default: 'panel',
    validator: (value) => ['panel', 'sidebar'].includes(value),
  },
})

const AVATAR_BG = {
  panel: 'var(--phro-user-avatar-bg-panel, #f9efec)',
  sidebar: 'var(--phro-user-avatar-bg-sidebar, #f9efec)',
}

const avatarStyle = computed(() => ({
  '--phro-user-avatar-fill': AVATAR_BG[props.variant] || AVATAR_BG.panel,
  '--el-avatar-text-size': `${Math.max(12, Math.round(props.size * 0.4))}px`,
}))
</script>

<style lang="scss" scoped>
.phro-user-avatar {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  user-select: none;
  -webkit-user-select: none;
  pointer-events: none;
  border: 2px solid rgba($phro-gold, 0.55);
  background-color: var(--phro-user-avatar-fill) !important;
  color: $phro-text-deep;
  font-weight: 600;

  :deep(img) {
    background-color: var(--phro-user-avatar-fill);
    object-fit: cover;
    pointer-events: none;
  }
}
</style>
