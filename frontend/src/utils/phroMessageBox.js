import { ElMessageBox } from 'element-plus'

/**
 * 弗洛洛风格确认框 — 视觉与登录页 login-card 一致
 */
export function showPhroConfirm(message, title, options = {}) {
  return ElMessageBox.confirm(message, title, {
    customClass: 'phro-message-box',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    confirmButtonClass: 'phro-message-box__btn phro-message-box__btn--confirm',
    cancelButtonClass: 'phro-message-box__btn phro-message-box__btn--cancel',
    showClose: true,
    closeOnClickModal: false,
    closeOnPressEscape: true,
    distinguishCancelAndClose: true,
    ...options,
  })
}
