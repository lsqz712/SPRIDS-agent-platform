import request from '@/utils/request'

export function createTrainingApi(data) {
  return request.post('/training/tasks', data)
}

export function listTrainingApi() {
  return request.get('/training/tasks')
}

export function getTrainingStatusApi(taskId) {
  return request.get(`/training/status/${taskId}`)
}

export function getTrainingMetricsApi(taskId) {
  return request.get(`/training/tasks/${taskId}/metrics`)
}
