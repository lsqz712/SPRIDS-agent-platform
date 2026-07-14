/** @param {Element} root */
export function selectAllInElement(root) {
  if (root instanceof HTMLInputElement || root instanceof HTMLTextAreaElement) {
    root.focus()
    root.select()
    return
  }

  const selection = window.getSelection()
  if (!selection) return

  const range = document.createRange()
  range.selectNodeContents(root)
  selection.removeAllRanges()
  selection.addRange(range)
}

/** @param {string} text */
export async function copyText(text) {
  if (!text) return
  await navigator.clipboard.writeText(text)
}

const SELECTABLE_SELECTOR = [
  'input',
  'textarea',
  '[contenteditable="true"]',
  '.msg-bubble',
  '.msg-body',
  '.msg-text',
  '.markdown-body',
  '.chat-input',
  '.phro-table-wrap',
].join(', ')

/** @param {Element} target */
export function findSelectableRoot(target) {
  if (!(target instanceof Element)) return null
  return target.closest(SELECTABLE_SELECTOR)
}

/** @param {Element} target */
export function findTextSelectRoot(target) {
  if (!(target instanceof Element)) return null
  return (
    target.closest('.msg-bubble, .msg-text, .markdown-body, .chat-input, input, textarea, [contenteditable="true"]')
    ?? findSelectableRoot(target)
  )
}

/** @param {MouseEvent} event */
export function buildTextContextMenuItems(event) {
  const target = event.target
  if (!(target instanceof Element)) return null

  const selectable = findSelectableRoot(target)
  if (!selectable) return null

  const selection = window.getSelection()
  const selectedText = selection?.toString() ?? ''
  const textRoot = findTextSelectRoot(target)
  if (!textRoot) return null

  /** @type {import('@/stores/phroContextMenu').PhroContextMenuItem[]} */
  const items = []

  items.push({
    id: 'copy',
    label: '复制',
    icon: 'copy',
    disabled: !selectedText,
    action: () => copyText(selectedText),
  })

  items.push({
    id: 'select-all',
    label: '全选',
    icon: 'select-all',
    action: () => selectAllInElement(textRoot),
  })

  return items
}
