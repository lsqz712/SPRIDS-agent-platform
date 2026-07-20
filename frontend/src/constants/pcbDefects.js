/** SPRIDS — PCB 缺陷检测场景常量 */

export const PCB_SCENE = {
  id: 1,
  name: 'pcb_smt',
  display_name: 'PCB SMT 缺陷检测',
  category: 'industry',
  class_names: [
    'missing_hole',
    'mouse_bite',
    'open_circuit',
    'short',
    'spur',
    'spurious_copper',
  ],
  class_names_cn: {
    missing_hole: '缺孔',
    mouse_bite: '鼠咬',
    open_circuit: '开路',
    short: '短路',
    spur: '毛刺',
    spurious_copper: '残铜',
  },
}

export const DEFECT_COLORS = {
  missing_hole: '#27ae60',
  mouse_bite: '#e74c3c',
  open_circuit: '#e67e22',
  short: '#f1c40f',
  spur: '#9b59b6',
  spurious_copper: '#3498db',
}

export const TASK_TYPES = [
  { key: 'single', label: '单图检测' },
  { key: 'batch', label: '批量/ZIP' },
  { key: 'video', label: '视频检测' },
  { key: 'camera', label: '摄像头' },
]

export const TASK_STATUS_MAP = {
  pending: { label: '等待中', type: 'info' },
  processing: { label: '处理中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

export const TRAINING_STATUS_MAP = {
  pending: { label: '排队中', type: 'info' },
  running: { label: '训练中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
  cancelled: { label: '已取消', type: 'info' },
}
