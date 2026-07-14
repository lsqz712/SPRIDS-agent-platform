import request from '@/utils/request'

export function getDefectTypesApi(params) {
  return request.get('/defect-types', { params })
}

export function createDefectTypeApi(data) {
  return request.post('/defect-types', data)
}

export function updateDefectTypeApi(defectTypeId, data) {
  return request.put(`/defect-types/${defectTypeId}`, data)
}

export function deleteDefectTypeApi(defectTypeId) {
  return request.delete(`/defect-types/${defectTypeId}`)
}