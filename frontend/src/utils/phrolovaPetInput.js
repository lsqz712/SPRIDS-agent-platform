/**
 * 桌宠输入：仅鼠标（全局），不含键盘识别。
 */

/**
 * @param {{
 *   onMouseButton?: (button: 'left' | 'right' | 'side', pressed: boolean) => void
 *   onMouseMove?: (x: number, y: number) => void
 * }} handlers
 */
export function attachPhrolovaPetInput(handlers) {
  const pressedMouse = new Set()

  const onWindowBlur = () => {
    if (pressedMouse.size === 0) return

    pressedMouse.clear()
    handlers.onMouseButton?.('left', false)
    handlers.onMouseButton?.('right', false)
    handlers.onMouseButton?.('side', false)
  }

  const onMouseDown = (event) => {
    if (event.button === 0) {
      pressedMouse.add('left')
      handlers.onMouseButton?.('left', true)
      return
    }
    if (event.button === 2) {
      pressedMouse.add('right')
      handlers.onMouseButton?.('right', true)
      return
    }
    if (event.button === 1 || event.button === 3 || event.button === 4) {
      pressedMouse.add('side')
      handlers.onMouseButton?.('side', true)
    }
  }

  const onMouseUp = (event) => {
    if (event.button === 0) {
      pressedMouse.delete('left')
      handlers.onMouseButton?.('left', false)
      return
    }
    if (event.button === 2) {
      pressedMouse.delete('right')
      handlers.onMouseButton?.('right', false)
      return
    }
    if (event.button === 1 || event.button === 3 || event.button === 4) {
      pressedMouse.delete('side')
      handlers.onMouseButton?.('side', false)
    }
  }

  const onMouseMove = (event) => {
    handlers.onMouseMove?.(event.clientX, event.clientY)
  }

  const onContextMenu = () => {
    if (pressedMouse.has('right')) {
      pressedMouse.delete('right')
      handlers.onMouseButton?.('right', false)
    }
  }

  window.addEventListener('blur', onWindowBlur)
  window.addEventListener('mousedown', onMouseDown, true)
  window.addEventListener('mouseup', onMouseUp, true)
  window.addEventListener('mousemove', onMouseMove, true)
  window.addEventListener('contextmenu', onContextMenu, true)

  return {
    destroy() {
      window.removeEventListener('blur', onWindowBlur)
      window.removeEventListener('mousedown', onMouseDown, true)
      window.removeEventListener('mouseup', onMouseUp, true)
      window.removeEventListener('mousemove', onMouseMove, true)
      window.removeEventListener('contextmenu', onContextMenu, true)
      pressedMouse.clear()
    },
  }
}
