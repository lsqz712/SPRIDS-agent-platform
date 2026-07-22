<template>
  <div class="result-panel">
    <div v-if="!detections.length" class="phro-empty">
      暂无检测结果
    </div>
    <ul v-else class="result-list">
      <li
        v-for="(det, index) in detections"
        :key="index"
        class="result-item"
        :class="{ active: index === activeIndex }"
        @click="$emit('select', index)"
      >
        <span class="dot" :style="{ background: colorOf(det.class_name) }" />
        <div class="result-body">
          <span class="result-name">{{ det.class_name_cn || det.class_name }}</span>
          <span class="result-conf">{{ (det.confidence * 100).toFixed(1) }}%</span>
        </div>
        <span class="result-bbox" :title="formatBbox(det.bbox)">{{ formatBbox(det.bbox) }}</span>
      </li>
    </ul>
    <div v-if="summary" class="result-summary">
      <div class="summary-row">
        <span>目标数</span>
        <strong>{{ summary.totalObjects }}</strong>
      </div>
      <div class="summary-row">
        <span>推理耗时</span>
        <strong>{{ summary.inferenceTime }} ms</strong>
      </div>
    </div>
  </div>
</template>

<script setup>
import { DEFECT_COLORS } from '@/constants/pcbDefects'

defineProps({
  detections: { type: Array, default: () => [] },
  activeIndex: { type: Number, default: -1 },
  summary: { type: Object, default: null },
})

defineEmits(['select'])

function colorOf(className) {
  return DEFECT_COLORS[className] || '#e74c3c'
}

function formatBbox(bbox) {
  if (!bbox?.length) return '-'
  return `[${bbox.map((n) => Math.round(n)).join(', ')}]`
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.result-panel {
  @include phro.phro-module-stack;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.result-list {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: $phro-radius-sm;
  cursor: pointer;
  transition: background 0.15s;
  min-width: 0;

  &:hover,
  &.active {
    background: rgba($phro-gold, 0.15);
  }
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.result-body {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.result-name {
  font-size: 13px;
  color: $phro-text-deep;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-conf {
  font-size: 12px;
  color: $phro-gold;
  font-weight: 600;
  flex-shrink: 0;
}

.result-bbox {
  font-size: 10px;
  color: $phro-text-mid;
  font-family: monospace;
  flex-shrink: 1;
  min-width: 0;
  max-width: 42%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-summary {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid rgba($phro-rose, 0.2);
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: $phro-text-mid;
  margin-bottom: 4px;

  strong {
    color: $phro-text-deep;
  }
}
</style>
