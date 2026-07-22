import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'

describe('AppSidebar 组件', () => {
  it('组件文件应该包含平台标题与个人中心', () => {
    const filePath = resolve(
      import.meta.dirname,
      '../../src/components/layout/AppSidebar.vue',
    )
    const content = readFileSync(filePath, 'utf-8')
    expect(content).toContain('Phrolova Agent Platform')
    expect(content).toContain('个人中心')
  })
})
