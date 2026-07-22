import request from '@/utils/request'

export function getHistoryRecordsApi(params) {
  return request.get('/history/records', { params })
}

export function getStatisticsApi() {
  return request.get('/history/statistics')
}

export function deleteRecordApi(id) {
  return request.delete(`/history/tasks/${id}`)
}
