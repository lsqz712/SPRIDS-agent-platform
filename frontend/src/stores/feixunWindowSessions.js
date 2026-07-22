/**
 * 飞讯窗口独立历史 — 工具函数（禁止跨窗口共享 sessions 数组引用）
 */
const MAX_SESSIONS = 50

export function deriveTitle(messages) {
  const firstUser = messages.find((message) => message.role === 'user' && message.content?.trim())
  if (!firstUser) return '新对话'
  const text = firstUser.content.trim()
  return text.length > 18 ? `${text.slice(0, 18)}…` : text
}

export function derivePreview(messages) {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const content = messages[i].content?.trim()
    if (content) {
      const text = content.replace(/\s+/g, ' ')
      return text.length > 28 ? `${text.slice(0, 28)}…` : text
    }
  }
  return '暂无消息'
}

export function sortSessions(sessions) {
  return [...sessions].sort((a, b) => {
    const timeA = a.lastMessageAt ?? a.updatedAt ?? 0
    const timeB = b.lastMessageAt ?? b.updatedAt ?? 0
    return timeB - timeA
  })
}

export function upsertSessionInList(sessions, { id, messages, lastMessageAt = Date.now() }) {
  if (!id || !messages?.length) return null

  const payload = {
    id,
    title: deriveTitle(messages),
    preview: derivePreview(messages),
    updatedAt: lastMessageAt,
    lastMessageAt,
    messages: messages.map((message) => ({
      role: message.role,
      content: message.content,
    })),
  }

  const idx = sessions.findIndex((session) => session.id === id)
  if (idx >= 0) {
    sessions[idx] = payload
  } else {
    sessions.unshift(payload)
  }

  const sorted = sortSessions(sessions).slice(0, MAX_SESSIONS)
  sessions.splice(0, sessions.length, ...sorted)
  return id
}

export function deleteSessionFromList(sessions, sessionId) {
  const idx = sessions.findIndex((session) => session.id === sessionId)
  if (idx < 0) return false
  sessions.splice(idx, 1)
  return true
}

export function renameSessionInList(sessions, sessionId, title) {
  const trimmed = title?.trim()
  if (!trimmed) return false

  const idx = sessions.findIndex((session) => session.id === sessionId)
  if (idx < 0) return false

  const nextTitle = trimmed.length > 30 ? `${trimmed.slice(0, 30)}…` : trimmed
  sessions[idx] = {
    ...sessions[idx],
    title: nextTitle,
    updatedAt: Date.now(),
  }
  const sorted = sortSessions(sessions)
  sessions.splice(0, sessions.length, ...sorted)
  return true
}

export function findSessionInList(sessions, sessionId) {
  return sessions.find((session) => session.id === sessionId) ?? null
}

export function createEmptySessions() {
  return []
}
