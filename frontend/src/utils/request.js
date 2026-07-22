/**
 * Axios 请求封装
 * - 统一 baseURL 配置
 * - 请求拦截器：自动注入 JWT Token
 * - 响应拦截器：统一错误处理、Token 过期处理
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

// ── 创建 Axios 实例 ──────────────────────────────────
const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── 请求拦截器 ──────────────────────────────────────
request.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.token && userStore.token !== 'dev-preview') {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// ── 响应拦截器 ──────────────────────────────────────
request.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const { response } = error

    if (response) {
      const msg =
        response.data?.message ||
        response.data?.detail ||
        `请求失败 (${response.status})`

      switch (response.status) {
        case 401: {
          ElMessage.error(msg || '登录已过期，请重新登录')
          const userStore = useUserStore()
          userStore.logout()
          router.push('/login')
          break
        }
        case 403:
          ElMessage.error(msg || '没有权限执行此操作')
          break
        case 404:
          ElMessage.error(msg || '请求的资源不存在')
          break
        case 422: {
          const data = response.data?.data
          if (Array.isArray(data) && data.length > 0) {
            ElMessage.error(data[0])
          } else {
            const detail = response.data?.detail
            if (Array.isArray(detail)) {
              ElMessage.error(detail[0]?.msg || msg || '参数验证失败')
            } else {
              ElMessage.error(msg || '参数验证失败')
            }
          }
          break
        }
        case 500:
          ElMessage.error(msg || '服务器内部错误')
          break
        default:
          ElMessage.error(msg)
      }
    } else {
      ElMessage.error('网络连接异常，请检查后端服务是否启动')
    }

    return Promise.reject(error)
  },
)

export default request
