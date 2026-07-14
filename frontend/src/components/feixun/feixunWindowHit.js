export const FEIXUN_WINDOW_HIT_SELECTOR = [
  '.feixun-window-ear--drag',
  '.feixun-window-ear--close',
  '.feixun-window',
  '.feixun-window-resize-north__hit',
  '.window-resize-handle',
].join(', ')

export function isFeixunWindowHitTarget(target) {
  return target instanceof Element && !!target.closest(FEIXUN_WINDOW_HIT_SELECTOR)
}

function isPointInsideRect(clientX, clientY, rect) {
  return (
    clientX >= rect.left &&
    clientX <= rect.right &&
    clientY >= rect.top &&
    clientY <= rect.bottom
  )
}

export function findTopmostWindowHitAt(clientX, clientY) {
  const elements = document.elementsFromPoint(clientX, clientY)
  for (const element of elements) {
    if (!(element instanceof Element)) continue
    const hit = element.closest(FEIXUN_WINDOW_HIT_SELECTOR)
    if (!hit) continue
    const windowId = hit.closest('.feixun-window-shell')?.getAttribute('data-window-id')
    if (windowId) return windowId
  }

  const shells = [...document.querySelectorAll('.feixun-window-shell')].sort(
    (a, b) => (parseInt(b.style.zIndex, 10) || 0) - (parseInt(a.style.zIndex, 10) || 0),
  )

  for (const shell of shells) {
    const hits = shell.querySelectorAll(FEIXUN_WINDOW_HIT_SELECTOR)
    for (const hit of hits) {
      if (isPointInsideRect(clientX, clientY, hit.getBoundingClientRect())) {
        return shell.getAttribute('data-window-id')
      }
    }
  }

  return null
}

function isPointOnWindowHit(clientX, clientY, shell) {
  const hits = shell.querySelectorAll(FEIXUN_WINDOW_HIT_SELECTOR)
  return [...hits].some((hit) =>
    isPointInsideRect(clientX, clientY, hit.getBoundingClientRect()),
  )
}

function isShellLayoutInflated(shellRect, pageRect) {
  if (!pageRect) return false
  return (
    shellRect.width >= pageRect.width * 0.9 &&
    shellRect.height >= pageRect.height * 0.9
  )
}

export function isPointInsideAnyWindowShell(clientX, clientY) {
  const pageRect = document.querySelector('.feixun-page')?.getBoundingClientRect()

  return [...document.querySelectorAll('.feixun-window-shell')].some((shell) => {
    const shellRect = shell.getBoundingClientRect()
    if (!isPointInsideRect(clientX, clientY, shellRect)) return false

    if (isShellLayoutInflated(shellRect, pageRect)) {
      return false
    }

    return !isPointOnWindowHit(clientX, clientY, shell)
  })
}
