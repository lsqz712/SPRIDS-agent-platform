import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

request.interceptors.request.use(
  (config) => {
    // FormData must NOT have Content-Type overridden
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const { response } = error
    if (response) {
      switch (response.status) {
        case 401:
          ElMessage.error('Login expired, please login again')
          useUserStore().logout()
          router.push('/login')
          break
        case 403: ElMessage.error('No permission'); break
        case 404: ElMessage.error('Resource not found'); break
        case 422:
          const detail = response.data?.detail
          ElMessage.error(Array.isArray(detail) ? detail[0]?.msg || 'Validation failed' : detail || 'Validation failed')
          break
        case 500: ElMessage.error('Server error'); break
        default: ElMessage.error(response.data?.detail || `Request failed (${response.status})`)
      }
    } else {
      ElMessage.error('Network error, check backend')
    }
    return Promise.reject(error)
  }
)

export default request
