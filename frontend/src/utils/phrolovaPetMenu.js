/**
 * 弗洛洛桌宠控制面板菜单项。
 * motionIndex 与 config.json standard.l2d_motion_lockhand 顺序一致。
 */

/** @typedef {'motion' | 'expression' | 'toggle' | 'reset'} PhrolovaPetMenuActionKind */

/**
 * @typedef {Object} PhrolovaPetMenuAction
 * @property {string} id
 * @property {string} label
 * @property {PhrolovaPetMenuActionKind} kind
 * @property {number} [motionIndex]
 * @property {number} [expressionIndex]
 * @property {boolean} [toggleExpression]
 * @property {number} [showMotionIndex]
 * @property {number} [hideMotionIndex]
 * @property {string} [paramId]
 * @property {string[]} [partIds]
 * @property {boolean} [paramInverted]
 * @property {boolean} [defaultOn]
 * @property {string} [hint]
 */

/**
 * @typedef {Object} PhrolovaPetMenuSection
 * @property {string} id
 * @property {string} title
 * @property {string} [description]
 * @property {PhrolovaPetMenuAction[]} items
 */

/** @type {PhrolovaPetMenuSection[]} */
export const PHROLOVA_PET_MENU_SECTIONS = [
  {
    id: 'decoration',
    title: '装饰部件',
    description: '点击切换开 / 关',
    items: [
      {
        id: 'ear',
        label: '猫耳',
        kind: 'toggle',
        showMotionIndex: 1,
        hideMotionIndex: 0,
        paramId: 'Param23',
        partIds: ['Part11', 'Part12'],
        defaultOn: true,
      },
      {
        id: 'tail',
        label: '猫尾',
        kind: 'toggle',
        showMotionIndex: 2,
        hideMotionIndex: 3,
        paramId: 'Param27',
        defaultOn: true,
      },
      {
        id: 'dango',
        label: '团子',
        kind: 'toggle',
        showMotionIndex: 4,
        hideMotionIndex: 5,
        paramId: 'Param17',
        defaultOn: false,
      },
      {
        id: 'eyepatch',
        label: '眼罩',
        kind: 'toggle',
        showMotionIndex: 7,
        hideMotionIndex: 6,
        paramId: 'Param2',
        paramInverted: true,
        defaultOn: false,
      },
      {
        id: 'sunglasses',
        label: '墨镜',
        kind: 'toggle',
        showMotionIndex: 8,
        hideMotionIndex: 9,
        paramId: 'Param8',
        defaultOn: false,
      },
      {
        id: 'blush',
        label: '脸红',
        kind: 'toggle',
        showMotionIndex: 10,
        hideMotionIndex: 11,
        paramId: 'Param3',
        defaultOn: false,
      },
      {
        id: 'face-dark',
        label: '脸黑',
        kind: 'toggle',
        showMotionIndex: 12,
        hideMotionIndex: 13,
        paramId: 'Param21',
        defaultOn: false,
      },
      {
        id: 'sign',
        label: '文字牌',
        kind: 'toggle',
        showMotionIndex: 14,
        hideMotionIndex: 15,
        paramId: 'Param6',
        defaultOn: false,
      },
    ],
  },
  {
    id: 'expression',
    title: '表情',
    description: '再次点击可恢复默认',
    items: [
      { id: 'expr-default', label: '默认', kind: 'expression', expressionIndex: 0 },
      {
        id: 'expr-sad',
        label: '忧郁',
        kind: 'expression',
        expressionIndex: 1,
        toggleExpression: true,
      },
      {
        id: 'expr-laugh',
        label: '大笑',
        kind: 'expression',
        expressionIndex: 2,
        toggleExpression: true,
      },
      {
        id: 'expr-cry',
        label: '哭泣',
        kind: 'expression',
        expressionIndex: 3,
        toggleExpression: true,
      },
      {
        id: 'expr-angry',
        label: '生气',
        kind: 'expression',
        expressionIndex: 4,
        toggleExpression: true,
      },
      {
        id: 'expr-speechless',
        label: '无语',
        kind: 'expression',
        expressionIndex: 5,
        toggleExpression: true,
      },
    ],
  },
  {
    id: 'form',
    title: '形态',
    items: [
      {
        id: 'form-chef',
        label: '厨娘',
        kind: 'toggle',
        showMotionIndex: 16,
        hideMotionIndex: 17,
        paramId: 'Param5',
        partIds: ['Part18'],
        defaultOn: false,
      },
      {
        id: 'form-injured',
        label: '受伤',
        kind: 'toggle',
        showMotionIndex: 18,
        hideMotionIndex: 19,
        paramId: 'Param16',
        partIds: ['Part24'],
        defaultOn: false,
      },
      {
        id: 'form-seafood',
        label: '海鲜',
        kind: 'toggle',
        showMotionIndex: 20,
        hideMotionIndex: 21,
        paramId: 'Param11',
        partIds: ['Part20'],
        defaultOn: false,
      },
    ],
  },
  {
    id: 'animation',
    title: '动画',
    items: [{ id: 'happy', label: '开心动画', kind: 'motion', motionIndex: 22 }],
  },
  {
    id: 'settings',
    title: '设置',
    items: [{ id: 'reset-defaults', label: '恢复默认设置', kind: 'reset' }],
  },
]

/** @returns {Record<string, boolean>} */
export function buildDefaultToggleStates() {
  /** @type {Record<string, boolean>} */
  const states = {}

  PHROLOVA_PET_MENU_SECTIONS.forEach((section) => {
    section.items.forEach((item) => {
      if (item.kind !== 'toggle') return
      states[item.id] = item.defaultOn !== false
    })
  })

  return states
}
