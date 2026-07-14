<template>
  <PhroPageShell
    title="模型训练"
    subtitle="YOLOv11 训练任务配置与实时监控"
  >
    <div class="training-layout">
      <div class="phro-module">
        <h3 class="phro-module-title">训练配置</h3>
        <el-form label-position="top" class="training-form">
          <div class="phro-form-grid">
            <div class="phro-field">
              <label>基础模型</label>
              <el-select v-model="form.model_name" style="width: 100%">
                <el-option label="YOLOv11n（轻量）" value="yolov11n" />
                <el-option label="YOLOv11s" value="yolov11s" />
                <el-option label="YOLOv11m" value="yolov11m" />
              </el-select>
            </div>
            <div class="phro-field">
              <label>训练轮数 (Epochs)</label>
              <el-input-number v-model="form.epochs" :min="10" :max="500" style="width: 100%" />
            </div>
            <div class="phro-field">
              <label>图像尺寸</label>
              <el-select v-model="form.img_size" style="width: 100%">
                <el-option :label="640" :value="640" />
                <el-option :label="512" :value="512" />
                <el-option :label="800" :value="800" />
              </el-select>
            </div>
            <div class="phro-field">
              <label>Batch Size</label>
              <el-input-number v-model="form.batch_size" :min="1" :max="64" style="width: 100%" />
            </div>
            <div class="phro-field">
              <label>训练设备</label>
              <el-select v-model="form.device" style="width: 100%">
                <el-option label="GPU 0" value="0" />
                <el-option label="GPU 1" value="1" />
                <el-option label="CPU" value="cpu" />
              </el-select>
            </div>
            <div class="phro-field">
              <label>初始学习率</label>
              <el-input-number v-model="form.lr0" :min="0.0001" :max="0.1" :step="0.001" :precision="4" style="width: 100%" />
            </div>
          </div>
          <button
            type="button"
            class="phro-btn phro-btn--primary start-btn"
            :disabled="!!activeTask && activeTask.status === 'running'"
            @click="startTraining"
          >
            {{ activeTask?.status === 'running' ? '训练进行中…' : '启动训练' }}
          </button>
        </el-form>
      </div>

      <div class="phro-module phro-module--grow monitor-card">
        <h3 class="phro-module-title">训练监控</h3>
        <div class="phro-module-body">
        <div v-if="activeTask" class="task-status">
          <div class="phro-stat-grid">
            <div class="phro-stat-item">
              <div class="value">{{ activeTask.current_epoch }}/{{ activeTask.epochs }}</div>
              <div class="label">当前 Epoch</div>
            </div>
            <div class="phro-stat-item">
              <div class="value">{{ activeTask.progress }}%</div>
              <div class="label">进度</div>
            </div>
            <div class="phro-stat-item">
              <div class="value">{{ statusLabel }}</div>
              <div class="label">状态</div>
            </div>
            <div class="phro-stat-item">
              <div class="value">{{ latestMap50 }}</div>
              <div class="label">mAP50</div>
            </div>
          </div>
          <el-progress
            :percentage="activeTask.progress"
            :stroke-width="10"
            :status="activeTask.status === 'completed' ? 'success' : undefined"
            class="task-progress"
          />
        </div>
        <div v-else class="phro-empty">尚未启动训练任务</div>
        <LossChart :metrics="metrics" />
        </div>
      </div>
    </div>

    <div class="phro-module history-table-module">
      <h3 class="phro-module-title">历史训练任务</h3>
      <div class="phro-table-wrap">
        <el-table :data="taskList" stripe empty-text="暂无训练记录">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="model_name" label="模型" width="110" />
          <el-table-column prop="epochs" label="Epochs" width="90" />
          <el-table-column label="进度" width="100">
            <template #default="{ row }">{{ row.progress }}%</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">
                {{ statusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="160">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <button type="button" class="phro-btn phro-btn--sm" @click="viewTask(row)">
                查看
              </button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </PhroPageShell>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import LossChart from '@/components/training/LossChart.vue'
import { TRAINING_STATUS_MAP } from '@/constants/pcbDefects'
import {
  mockCreateTraining,
  mockPollTraining,
  mockListTraining,
  mockGetTrainingMetrics,
  withApiFallback,
} from '@/services/spridsMock'
import { createTrainingApi, listTrainingApi, getTrainingMetricsApi, getTrainingStatusApi } from '@/api/training'

const form = ref({
  model_name: 'yolov11n',
  epochs: 50,
  img_size: 640,
  batch_size: 16,
  device: '0',
  lr0: 0.01,
})

const activeTask = ref(null)
const metrics = ref([])
const taskList = ref([])
let pollTimer = null

const statusLabel = computed(() => statusText(activeTask.value?.status))
const latestMap50 = computed(() => {
  const last = metrics.value[metrics.value.length - 1]
  return last?.map50 != null ? (last.map50 * 100).toFixed(1) + '%' : '-'
})

function statusText(status) {
  return TRAINING_STATUS_MAP[status]?.label || status || '-'
}

function statusType(status) {
  return TRAINING_STATUS_MAP[status]?.type || 'info'
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

async function loadTasks() {
  taskList.value = await withApiFallback(
    () => listTrainingApi().then((r) => r?.data?.items || r?.items || r || []),
    () => mockListTraining(),
  )
}

async function startTraining() {
  try {
    const task = await withApiFallback(
      () => createTrainingApi({ scene_id: 1, ...form.value }).then((r) => r?.data || r),
      () => mockCreateTraining(form.value),
    )
    activeTask.value = task
    metrics.value = []
    await loadTasks()
    startPolling(task.id)
    ElMessage.success('训练任务已启动')
  } catch (e) {
    ElMessage.error(e.message || '启动失败')
  }
}

function startPolling(taskId) {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const { task, metrics: m } = await withApiFallback(
        async () => {
          const [status, metricsData] = await Promise.all([
            getTrainingStatusApi(taskId),
            getTrainingMetricsApi(taskId),
          ])
          return {
            task: status?.data || status,
            metrics: metricsData?.data || metricsData || [],
          }
        },
        () => mockPollTraining(taskId),
      )
      activeTask.value = task
      metrics.value = m
      if (task.status === 'completed' || task.status === 'failed') {
        stopPolling()
        await loadTasks()
        if (task.status === 'completed') ElMessage.success('训练已完成')
      }
    } catch {
      stopPolling()
    }
  }, 1200)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function viewTask(row) {
  activeTask.value = row
  metrics.value = await withApiFallback(
    () => getTrainingMetricsApi(row.id).then((r) => r?.data || r || []),
    () => mockGetTrainingMetrics(row.id),
  )
  if (row.status === 'running') startPolling(row.id)
  else stopPolling()
}

onMounted(loadTasks)
onBeforeUnmount(stopPolling)
</script>

<style lang="scss" scoped>
.training-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(280px, 340px) 1fr;
  gap: $phro-module-gap;
}

.history-table-module {
  flex-shrink: 0;
  max-height: 240px;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .phro-table-wrap {
    flex: 1;
    min-height: 0;
  }
}

.monitor-card {
  min-height: 0;
}

.training-form {
  :deep(.el-input-number),
  :deep(.el-select) {
    width: 100%;
  }

  :deep(.el-input__wrapper),
  :deep(.el-select__wrapper) {
    background: rgba($phro-panel-bg, 0.95);
    box-shadow: none;
    border: 1px solid rgba($phro-rose, 0.35);
  }
}

.start-btn {
  margin-top: 16px;
  width: 100%;
}

.task-status {
  margin-bottom: 12px;
  flex-shrink: 0;
}

.task-progress {
  margin-top: 8px;
}

@media (max-width: 900px) {
  .training-layout {
    grid-template-columns: 1fr;
  }

  .history-table-module {
    max-height: none;
  }
}
</style>
