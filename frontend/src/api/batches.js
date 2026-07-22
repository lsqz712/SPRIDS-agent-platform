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

export function uploadBatchImagesApi(batchId, files) {
  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file)
  })
  return request.post(`/batches/${batchId}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function getBatchImagesApi(batchId) {
  return request.get(`/batches/${batchId}/images`)
}

export function detectBatchApi(batchId, data) {
  const formData = new FormData()
  if (data.conf !== undefined) {
    formData.append('conf', data.conf)
  }
  if (data.scene_id !== undefined) {
    formData.append('scene_id', data.scene_id)
  }
  return request.post(`/batches/${batchId}/detect`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

export function createBatchWithImagesApi(data) {
  const formData = new FormData()
  formData.append('batch_no', data.batch_no)
  formData.append('pcb_type', data.pcb_type)
  formData.append('production_line', data.production_line)
  if (data.total_count && data.total_count > 0) {
    formData.append('total_count', data.total_count)
  }
  if (data.files && data.files.length > 0) {
    data.files.forEach(file => {
      formData.append('files', file)
    })
  }
  return request.post('/batches', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}