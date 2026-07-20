/**
 * 认证相关 API 接口
 */
import request from '@/utils/request'

/**
 * 用户注册
 * @param {Object} data - { username, email, password }
 */
export function registerApi(data) {
  return request.post('/auth/register', data)
}

/**
 * 用户登录
 * @param {Object} data - { username, password }
 * @returns {Promise} - { access_token, token_type, user }
 */
export function loginApi(data) {
  return request.post('/auth/login', data)
}

/**
 * 获取当前用户信息（需要 Token）
 */
export function getUserInfoApi() {
  return request.get('/auth/me')
}

/**
 * 更新当前用户资料
 * @param {Object} data - { username?, email?, phone?, avatar? }
 */
export function updateProfileApi(data) {
  return request.patch('/auth/me', data)
}

/**
 * 修改密码
 * @param {Object} data - { old_password, new_password }
 */
export function changePasswordApi(data) {
  return request.post('/auth/change-password', data)
}

/**
 * 忘记密码 - 请求密码重置
 * @param {Object} data - { email }
 */
export function forgotPasswordApi(data) {
  return request.post('/auth/forgot-password', data)
}

/**
 * 重置密码
 * @param {Object} data - { token, new_password }
 */
export function resetPasswordApi(data) {
  return request.post('/auth/reset-password', data)
}

/**
 * 上传当前用户头像
 * @param {File} file
 */
export function uploadAvatarApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/auth/me/avatar', formData)
}
