import request from '@/utils/request'

export function getBatchesApi(params) {
  return request.get('/batches', { params })
}

export function createBatchApi(data) {
  return request.post('/batches', data)
}

export function getBatchDetailApi(batchId) {
  return request.get(`/batches/${batchId}`)
}

export function updateBatchApi(batchId, data) {
  return request.put(`/batches/${batchId}`, data)
}

export function deleteBatchApi(batchId) {
  return request.delete(`/batches/${batchId}`)
}

export function getBatchStatisticsApi(batchId) {
  return request.get(`/batches/${batchId}/statistics`)
}