import request from '@/utils/request'

export function getTasksApi(params) {
  return request.get('/tasks', { params })
}

export function createSingleTaskApi(formData) {
  return request.post('/tasks/single', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function createBatchTaskApi(formData) {
  return request.post('/tasks/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
  })
}

export function getTaskDetailApi(taskId) {
  return request.get(`/tasks/${taskId}`)
}

export function deleteTaskApi(taskId) {
  return request.delete(`/tasks/${taskId}`)
}

export function getTaskResultsApi(taskId, params) {
  return request.get(`/tasks/${taskId}/results`, { params })
}