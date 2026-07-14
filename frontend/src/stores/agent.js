/**
 * 智能体对话状态管理（非飞讯窗口历史，飞讯每窗独立见 feixunWindows）
 */
import { defineStore } from 'pinia'

export const useAgentStore = defineStore('agent', {
  state: () => ({}),

  actions: {
    clear() {
      localStorage.removeItem('phrolova_chat_sessions')
    },
  },
})
