import request from '@/utils/request'

export function getScenesApi() {
  return request.get('/detection/scenes')
}

export function detectSingleApi(formData) {
  return request.post('/detection/single', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function detectBatchApi(formData) {
  return request.post('/detection/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
  })
}

export function detectVideoApi(formData) {
  return request.post('/detection/video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
}

export function getTaskDetailApi(taskId) {
  return request.get(`/detection/tasks/${taskId}`)
}
