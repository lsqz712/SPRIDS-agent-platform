/**
 * 检测相关 API 接⼝
 *
 * 快捷按钮直接调⽤这些接⼝（跳过 LLM），结果渲染在对话中
 */
import request from "@/utils/request";
/**
 * 单图检测
 * @param {FormData} formData - 包含 file 字段的 FormData
 * @returns {Promise} - 检测结果（标注图 + ⽬标统计）
 */
export function detectSingle(formData) {
// 不设置 Content-Type，让 axios ⾃动添加 multipart/form-data + boundary
  return request.post("/detection/single", formData, {
    timeout: 60000,
  });
}
/**
 * 批量检测
 * @param {FormData} formData - 包含多个 files 字段的 FormData
 * @returns {Promise} - 批量检测结果
 */
export function detectBatch(formData) {
  return request.post("/detection/batch", formData, {
    timeout: 120000,
  });
}
/**
 * ZIP 检测
 * @param {FormData} formData - 包含 file 字段的 FormData
 * @returns {Promise} - ZIP 解压后的批量检测结果
 */
export function detectZip(formData) {
  return request.post("/detection/zip", formData, {
    timeout: 180000,
  });
}
/**
 * 视频检测
 * @param {FormData} formData - 包含 file 字段的 FormData（视频文件）
 * @returns {Promise} - { task_id, status, message }
 */
export function detectVideo(formData) {
  return request.post("/detection/video", formData, {
    timeout: 120000, // 视频上传可能较慢
  });
}

/**
 * 查询视频检测进度
 * @param {number} taskId - 视频检测任务 ID
 * @returns {Promise} - { status, progress, result, ... }
 */
export function getVideoStatus(taskId) {
  return request.get(`/detection/video/status/${taskId}`);
}

export function listDetections(page = 1, pageSize = 20) {
  return request.get("/detection/list", { params: { page, page_size: pageSize } });
}

export function getDetectionStatus(taskId) {
  return request.get(`/detection/status/${taskId}`);
}