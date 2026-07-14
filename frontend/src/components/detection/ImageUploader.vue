<template>
  <div
    class="image-uploader"
    :class="{ 'is-dragover': dragOver, 'is-disabled': disabled }"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="dragOver = false"
    @drop.prevent="onDrop"
    @click="openPicker"
  >
    <input
      ref="inputRef"
      type="file"
      class="hidden-input"
      :accept="accept"
      :multiple="multiple"
      :disabled="disabled"
      @change="onInputChange"
    />
    <el-icon class="upload-icon"><UploadFilled /></el-icon>
    <p class="upload-title">{{ title }}</p>
    <p class="upload-hint">{{ hint }}</p>
    <slot />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'

const props = defineProps({
  accept: { type: String, default: 'image/*' },
  multiple: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  title: { type: String, default: '拖拽文件到此处，或点击上传' },
  hint: { type: String, default: '支持 JPG / PNG / WEBP' },
})

const emit = defineEmits(['select'])

const inputRef = ref(null)
const dragOver = ref(false)

function openPicker() {
  if (props.disabled) return
  inputRef.value?.click()
}

function emitFiles(fileList) {
  const files = Array.from(fileList || [])
  if (!files.length) return
  emit('select', props.multiple ? files : files[0])
}

function onInputChange(e) {
  emitFiles(e.target.files)
  e.target.value = ''
}

function onDragOver() {
  if (props.disabled) return
  dragOver.value = true
}

function onDrop(e) {
  dragOver.value = false
  if (props.disabled) return
  emitFiles(e.dataTransfer?.files)
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.image-uploader {
  @include phro.phro-module-box;
  border-style: dashed;
  border-width: 2px;
  padding: 28px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;

  &:hover:not(.is-disabled) {
    border-color: rgba($phro-gold, 0.55);
    background: rgba($phro-panel-bg, 0.95);
  }

  &.is-dragover {
    border-color: $phro-gold;
    background: rgba($phro-gold, 0.12);
  }

  &.is-disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
}

.hidden-input {
  display: none;
}

.upload-icon {
  font-size: 36px;
  color: $phro-gold;
  margin-bottom: 10px;
}

.upload-title {
  margin: 0 0 6px;
  font-size: 14px;
  color: $phro-text-deep;
}

.upload-hint {
  margin: 0;
  font-size: 12px;
  color: $phro-text-mid;
}
</style>
