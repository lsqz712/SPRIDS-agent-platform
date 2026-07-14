/**
 * 解析用户头像 URL（支持相对路径、绝对 URL、Base64）
 */
export function resolveAvatarUrl(avatar) {
  if (!avatar) return ''
  if (avatar.startsWith('data:') || avatar.startsWith('http://') || avatar.startsWith('https://')) {
    return avatar
  }
  if (avatar.startsWith('/')) return avatar
  return `/api/storage/${avatar}`
}

/**
 * 读取本地图片为 Data URL（预览模式使用）
 */
export function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('读取文件失败'))
    reader.readAsDataURL(file)
  })
}

export const AVATAR_ACCEPT = 'image/jpeg,image/png,image/webp,image/gif'
export const AVATAR_MAX_BYTES = 2 * 1024 * 1024

export function validateAvatarFile(file) {
  if (!file) return '请选择图片文件'
  if (!file.type.startsWith('image/')) return '仅支持图片文件'
  if (!['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.type)) {
    return '仅支持 JPG、PNG、WEBP、GIF 格式'
  }
  if (file.size > AVATAR_MAX_BYTES) return '头像大小不能超过 2MB'
  return ''
}
