/**
 * 前端全局错误监控与上报
 */
import { ElMessage } from 'element-plus'

const REPORT_TO_BACKEND = false
const REPORT_API = '/api/errors/report'

function reportError(errorInfo) {
  console.error('[ErrorReporter]', errorInfo)

  try {
    const errors = JSON.parse(localStorage.getItem('error_logs') || '[]')
    errors.push({
      ...errorInfo,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
    })
    if (errors.length > 50) {
      errors.splice(0, errors.length - 50)
    }
    localStorage.setItem('error_logs', JSON.stringify(errors))
  } catch (e) {
    console.warn('ErrorReporter: localStorage 写入失败', e)
  }

  if (REPORT_TO_BACKEND) {
    fetch(REPORT_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(errorInfo),
    }).catch(() => {})
  }
}

export function setupErrorReporting(app) {
  app.config.errorHandler = (err, _instance, info) => {
    reportError({
      type: 'vue_error',
      message: err.message,
      stack: err.stack,
      component: info,
    })
    try {
      ElMessage?.error('页面渲染出错，请刷新重试')
    } catch {
      // Element Plus 未加载时静默处理
    }
  }

  window.onerror = (message, source, lineno, colno, error) => {
    reportError({
      type: 'js_error',
      message,
      source,
      lineno,
      colno,
      stack: error?.stack,
    })
  }

  window.onunhandledrejection = (event) => {
    reportError({
      type: 'promise_rejection',
      message: event.reason?.message || String(event.reason),
      stack: event.reason?.stack,
    })
    event.preventDefault()
  }

  console.log('[ErrorReporter] 全局错误监控已启用')
}
