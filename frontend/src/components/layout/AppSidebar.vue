<template>
  <aside class="app-sidebar" :class="{ 'app-sidebar--feixun': feixunTheme }">
    <div class="app-sidebar-brand">
      <img src="/logo.webp" alt="logo" class="app-sidebar-logo" />
      <span class="app-sidebar-title">Phrolova Agent Platform</span>
    </div>

    <nav class="app-sidebar-nav">
      <div
        class="app-sidebar-group"
        :class="{ 'is-expanded': toolMenu.activeSection === 'feixun' }"
      >
        <div
          ref="feixunAnchorRef"
          class="app-sidebar-item app-sidebar-item--parent"
          :class="{ active: activeMenu === '/chat' }"
          @click="goToChat"
        >
          <el-icon class="app-sidebar-icon">
            <ChatDotRound />
          </el-icon>
          <span class="app-sidebar-label app-sidebar-parent-label">飞讯</span>

          <button
            type="button"
            class="app-sidebar-expand-toggle"
            :aria-expanded="toolMenu.activeSection === 'feixun'"
            :aria-label="toolMenu.activeSection === 'feixun' ? '收起飞讯子菜单' : '在右侧展开飞讯子菜单'"
            @click.stop="toggleToolMenu('feixun')"
          >
            <el-icon class="app-sidebar-expand-icon">
              <ArrowRight />
            </el-icon>
          </button>
        </div>
      </div>

      <router-link
        v-for="item in navMenuItems"
        :key="item.path"
        :to="item.path"
        class="app-sidebar-item"
        active-class="active"
      >
        <el-icon class="app-sidebar-icon">
          <component :is="item.icon" />
        </el-icon>
        <span class="app-sidebar-label">{{ item.title }}</span>
      </router-link>

      <div
        class="app-sidebar-group"
        :class="{ 'is-expanded': toolMenu.activeSection === 'pet' }"
      >
        <div
          ref="petAnchorRef"
          class="app-sidebar-item app-sidebar-item--parent app-sidebar-pet-toggle"
          :class="{ active: petStore.visible }"
        >
          <el-icon class="app-sidebar-icon">
            <MagicStick />
          </el-icon>
          <span class="app-sidebar-label app-sidebar-parent-label">弗洛洛桌宠</span>

          <button
            type="button"
            class="app-sidebar-expand-toggle"
            :aria-expanded="toolMenu.activeSection === 'pet'"
            :aria-label="toolMenu.activeSection === 'pet' ? '收起桌宠子菜单' : '在右侧展开桌宠子菜单'"
            @click.stop="toggleToolMenu('pet')"
          >
            <el-icon class="app-sidebar-expand-icon">
              <ArrowRight />
            </el-icon>
          </button>
        </div>
      </div>
    </nav>

    <div class="app-sidebar-footer">
      <div
        class="app-sidebar-group"
        :class="{ 'is-expanded': toolMenu.activeSection === 'user' }"
      >
        <div
          ref="userAnchorRef"
          class="app-sidebar-item app-sidebar-item--parent app-sidebar-user"
        >
          <PhroUserAvatar
            :size="32"
            :src="userStore.avatar"
            variant="sidebar"
            :fallback="userStore.username?.charAt(0)?.toUpperCase()"
          />
          <span class="app-sidebar-username app-sidebar-label">{{ userStore.username }}</span>

          <button
            type="button"
            class="app-sidebar-expand-toggle"
            :aria-expanded="toolMenu.activeSection === 'user'"
            :aria-label="toolMenu.activeSection === 'user' ? '收起用户子菜单' : '在右侧展开用户子菜单'"
            @click.stop="toggleToolMenu('user')"
          >
            <el-icon class="app-sidebar-expand-icon">
              <ArrowRight />
            </el-icon>
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowRight,
  ChatDotRound,
  Camera,
  Cpu,
  Clock,
  DataAnalysis,
  MagicStick,
} from '@element-plus/icons-vue'
import PhroUserAvatar from '@/components/common/PhroUserAvatar.vue'
import { useUserStore } from '@/stores/user'
import { useAppToolMenuStore } from '@/stores/appToolMenu'
import { usePhrolovaPetStore } from '@/stores/phrolovaPet'

defineProps({
  feixunTheme: {
    type: Boolean,
    default: false,
  },
})

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const toolMenu = useAppToolMenuStore()
const petStore = usePhrolovaPetStore()

const feixunAnchorRef = ref(null)
const petAnchorRef = ref(null)
const userAnchorRef = ref(null)

const activeMenu = computed(() => `/${route.path.split('/')[1]}`)

const navMenuItems = [
  { path: '/detection', title: '检测工作台', icon: Camera },
  { path: '/training', title: '模型训练', icon: Cpu },
  { path: '/history', title: '历史记录', icon: Clock },
  { path: '/dashboard', title: '数据看板', icon: DataAnalysis },
]

function goToChat() {
  if (!route.path.startsWith('/chat')) {
    router.push('/chat')
  }
}

/** @param {'feixun' | 'pet' | 'user'} section */
async function toggleToolMenu(section) {
  const anchorMap = {
    feixun: feixunAnchorRef.value,
    pet: petAnchorRef.value,
    user: userAnchorRef.value,
  }
  await nextTick()
  toolMenu.toggleSection(section, anchorMap[section])
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-cursor.scss' as phro-cursor;

.app-sidebar {
  position: relative;
  z-index: 210;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  width: $sidebar-width;
  height: 100%;
  padding: $phro-module-gap;
  background: $phro-glass-bg;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  overflow-y: auto;
  box-sizing: border-box;
  font-family: $font-family-phro;
  user-select: none;
  -webkit-user-select: none;

  &::-webkit-scrollbar {
    width: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba($phro-gold, 0.35);
    border-radius: 2px;
  }
}

.app-sidebar-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 8px 6px 14px;
  margin-bottom: $phro-module-gap;
  border-bottom: 1px solid rgba($phro-rose, 0.18);
  flex-shrink: 0;
}

.app-sidebar-logo {
  height: 36px;
  width: auto;
  max-width: 100%;
  object-fit: contain;
}

.app-sidebar-title {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
  text-align: center;
  color: #f5e6c8;
  text-shadow: 0 1px 6px rgba(40, 6, 16, 0.55);
  word-break: break-word;
}

.app-sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: $phro-module-gap;
  flex: 1;
  min-height: 0;
}

.app-sidebar-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.app-sidebar-item--parent {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  padding-right: 36px;
  @include phro-cursor.phro-cursor-pointer;
}

.app-sidebar-parent-label {
  flex: 1;
  min-width: 0;
}

.app-sidebar-expand-toggle {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  padding: 0;
  margin: 0;
  border: none;
  background: transparent;
  @include phro-cursor.phro-cursor-pointer;
  color: rgba($phro-gold, 0.82);
  appearance: none;
}

.app-sidebar-expand-icon {
  font-size: 14px;
  transition: transform 0.2s ease;
}

.app-sidebar-group.is-expanded .app-sidebar-expand-icon {
  transform: rotate(90deg);
}

.app-sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px 12px 18px;
  background: $phro-panel-bg;
  border: $phro-divider-width solid $phro-border;
  border-radius: $phro-radius;
  color: $phro-text-deep;
  text-decoration: none;
  @include phro-cursor.phro-cursor-pointer;
  transition: box-shadow 0.2s, border-color 0.2s, color 0.2s;
  -webkit-user-drag: none;
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;

  &:hover:not(.active) {
    border-color: rgba($phro-gold, 0.5);
    box-shadow:
      inset 3px 0 0 rgba($phro-gold, 0.9),
      0 0 0 1px rgba($phro-gold, 0.22);
  }

  &.active {
    background: $phro-panel-bg;
    border-color: rgba($phro-gold, 0.65);
    box-shadow:
      inset 4px 0 0 $phro-gold,
      0 0 0 1px rgba($phro-gold, 0.28);

    .app-sidebar-label {
      font-weight: 600;
    }
  }
}

.app-sidebar-pet-toggle {
  width: 100%;
  box-sizing: border-box;
}

.app-sidebar-icon {
  flex-shrink: 0;
  font-size: 18px;
  color: rgba($phro-gold, 0.82);
  pointer-events: none;
  -webkit-user-drag: none;
}

.app-sidebar-label {
  font-size: 14px;
  line-height: 1.4;
  color: $phro-text-deep;
  pointer-events: none;
  -webkit-user-drag: none;
}

.app-sidebar-footer {
  flex-shrink: 0;
  margin-top: $phro-module-gap;
  padding-top: $phro-module-gap;
  border-top: 1px solid rgba($phro-rose, 0.18);
  display: flex;
  flex-direction: column;
  gap: $phro-module-gap;
}

.app-sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  box-sizing: border-box;
}

.app-sidebar-user-avatar,
.app-sidebar-user :deep(.phro-user-avatar) {
  flex-shrink: 0;
}

.app-sidebar-username {
  flex: 1;
  min-width: 0;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
