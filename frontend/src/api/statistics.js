import request from '@/utils/request'

export function getOverviewStatisticsApi() {
  return request.get('/statistics/overview')
}

export function getDailyTrendApi(params) {
  return request.get('/statistics/daily-trend', { params })
}

export function getDefectDistributionApi() {
  return request.get('/statistics/defect-distribution')
}

export function getSceneDistributionApi() {
  return request.get('/statistics/scene-distribution')
}