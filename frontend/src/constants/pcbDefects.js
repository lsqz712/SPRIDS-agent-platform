/** SPRIDS — PCB 缺陷检测场景常量 */

export const PCB_SCENE = {
  id: 1,
  name: 'pcb_smt',
  display_name: 'PCB SMT 缺陷检测',
  category: 'industry',
  class_names: [
    'short_circuit',
    'open_circuit',
    'missing_hole',
    'solder_defect',
    'scratch',
    'misalignment',
  ],
  class_names_cn: {
    short_circuit: '短路',
    open_circuit: '开路',
    missing_hole: '缺孔',
    solder_defect: '焊点缺陷',
    scratch: '划痕',
    misalignment: '错位',
  },
}

export const DEFECT_COLORS = {
  short_circuit: '#e74c3c',
  open_circuit: '#e67e22',
  missing_hole: '#9b59b6',
  solder_defect: '#3498db',
  scratch: '#1abc9c',
  misalignment: '#f1c40f',
}

export const TASK_TYPES = [
  { key: 'single', label: '单图检测' },
  { key: 'batch', label: '批量检测' },
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
