<template>
  <div class="detection-params">
    <div class="param-row">
      <label>置信度阈值 {{ confThreshold.toFixed(2) }}</label>
      <el-slider
        v-model="confThreshold"
        :min="0.1"
        :max="0.95"
        :step="0.05"
        :show-tooltip="false"
        @change="emitChange"
      />
    </div>
    <div class="param-row">
      <label>IoU 阈值 {{ iouThreshold.toFixed(2) }}</label>
      <el-slider
        v-model="iouThreshold"
        :min="0.1"
        :max="0.9"
        :step="0.05"
        :show-tooltip="false"
        @change="emitChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ confThreshold: 0.25, iouThreshold: 0.45 }),
  },
})

const emit = defineEmits(['update:modelValue'])

const confThreshold = ref(props.modelValue.confThreshold)
const iouThreshold = ref(props.modelValue.iouThreshold)

watch(
  () => props.modelValue,
  (v) => {
    confThreshold.value = v.confThreshold
    iouThreshold.value = v.iouThreshold
  },
  { deep: true },
)

function emitChange() {
  emit('update:modelValue', {
    confThreshold: confThreshold.value,
    iouThreshold: iouThreshold.value,
  })
}
</script>

<style lang="scss" scoped>
.detection-params {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.param-row {
  label {
    display: block;
    font-size: 12px;
    color: $phro-text-mid;
    margin-bottom: 4px;
  }

  :deep(.el-slider__runway) {
    background: rgba($phro-panel-bg, 0.5);
  }

  :deep(.el-slider__bar) {
    background: linear-gradient(90deg, $phro-rose, $phro-gold);
  }

  :deep(.el-slider__button) {
    border-color: $phro-gold;
    background: $phro-panel-bg;
  }
}
</style>
