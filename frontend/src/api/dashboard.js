import request from '@/utils/request'

/** 汇总统计 */
export function getStatistics(params = {}) {
  return request.get('/dashboard/statistics', { params })
}

/** 每日检测趋势 */
export function getTrend(params = {}) {
  return request.get('/dashboard/trend', { params })
}

/** 类别分布 */
export function getClassDistribution(params = {}) {
  return request.get('/dashboard/class-dist', { params })
}

/** 场景分布 */
export function getSceneDistribution(params = {}) {
  return request.get('/dashboard/scene-dist', { params })
}

/** 任务类型分布 */
export function getTypeDistribution(params = {}) {
  return request.get('/dashboard/type-dist', { params })
}
