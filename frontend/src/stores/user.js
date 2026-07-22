/**
 * 用户状态管理
 * 管理用户登录信息、Token、角色等
 */
import { defineStore } from 'pinia'
import { loginApi, getUserInfoApi, updateProfileApi, changePasswordApi, uploadAvatarApi } from '@/api/auth'
import { readFileAsDataUrl, resolveAvatarUrl } from '@/utils/avatar'

const TOKEN_KEY = 'rsod_token'
const USER_KEY = 'rsod_user'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: (() => { try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch { return null } })(),
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => {
      const name = state.user?.username || ''
      if (name === '预览用户') return '漂泊者'
      return name
    },
    avatar: (state) => resolveAvatarUrl(state.user?.avatar || ''),
    roles: (state) => state.user?.roles || [],
    isSuperuser: (state) => state.user?.is_superuser || false,
  },

  actions: {
    async login(credentials) {
      const res = await loginApi(credentials)
      // 兼容 success_response 包装：{code, data: {access_token, user}, message}
      const data = res.data || res

      this.token = data.access_token
      localStorage.setItem(TOKEN_KEY, data.access_token)

      this.user = data.user
      localStorage.setItem(USER_KEY, JSON.stringify(data.user))

      return res
    },

    async fetchUserInfo() {
      try {
        const res = await getUserInfoApi()
        // 兼容 success_response 包装
        const user = res.data || res
        this.user = user
        localStorage.setItem(USER_KEY, JSON.stringify(user))
      } catch {
        this.logout()
      }
    },

    async updateProfile(data) {
      if (this.token === 'dev-preview') {
        this.user = { ...this.user, ...data }
        localStorage.setItem(USER_KEY, JSON.stringify(this.user))
        return this.user
      }
      const res = await updateProfileApi(data)
      const user = res.data || res
      this.user = user
      localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      return user
    },

    async changePassword(data) {
      if (this.token === 'dev-preview') {
        return { message: '预览模式：密码修改已模拟成功' }
      }
      return changePasswordApi(data)
    },

    async uploadAvatar(file) {
      if (this.token === 'dev-preview') {
        const avatar = await readFileAsDataUrl(file)
        this.user = { ...this.user, avatar }
        localStorage.setItem(USER_KEY, JSON.stringify(this.user))
        return this.user
      }
      const res = await uploadAvatarApi(file)
      const user = res.data || res
      this.user = user
      localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      return user
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },

    /** 开发环境：跳过登录，直接进入内页预览 */
    devPreviewLogin() {
      const mockUser = {
        id: 0,
        username: '漂泊者',
        email: 'preview@phrolova.local',
        phone: null,
        avatar: '',
        roles: ['admin'],
        is_superuser: true,
        is_active: true,
        created_at: new Date().toISOString(),
        last_login_at: new Date().toISOString(),
      }

      this.token = 'dev-preview'
      this.user = mockUser
      localStorage.setItem(TOKEN_KEY, this.token)
      localStorage.setItem(USER_KEY, JSON.stringify(mockUser))
    },

    /** 将旧预览账号迁移为漂泊者 */
    migratePreviewUser() {
      if (this.user?.username === '预览用户') {
        this.user = { ...this.user, username: '漂泊者' }
        localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      }
    },
  },
})
