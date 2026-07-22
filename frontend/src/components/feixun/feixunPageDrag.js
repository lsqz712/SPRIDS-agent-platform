const DRAG_NO_SELECT_CLASS = 'feixun-drag-no-select'

function clearTextSelection() {
  window.getSelection()?.removeAllRanges()
}

function preventSelectStart(event) {
  event.preventDefault()
}

export function enableDragNoSelect() {
  document.body.classList.add(DRAG_NO_SELECT_CLASS)
  document.body.style.userSelect = 'none'
  document.addEventListener('selectstart', preventSelectStart, { capture: true })
  clearTextSelection()
}

export function disableDragNoSelect() {
  document.body.classList.remove(DRAG_NO_SELECT_CLASS)
  document.body.style.userSelect = ''
  document.removeEventListener('selectstart', preventSelectStart, { capture: true })
}

export const FRAME_GROUP_DRAG_THRESHOLD = 6
