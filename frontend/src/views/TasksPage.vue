<template>
  <PhroPageShell
    title="任务管理"
    subtitle="检测任务列表 · 状态追踪 · 结果查看"
    scroll-body
  >
    <template #actions>
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索任务ID"
          class="search-input"
          @keyup.enter="loadTasks"
        >
          <template #prefix>
            <el-icon class="el-input__icon"><Search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="filterStatus"
          placeholder="状态筛选"
          class="filter-select"
          @change="loadTasks"
        >
          <el-option label="全部" value="" />
          <el-option label="待处理" value="pending" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-select
          v-model="filterType"
          placeholder="类型筛选"
          class="filter-select"
          @change="loadTasks"
        >
          <el-option label="全部" value="" />
          <el-option label="单图检测" value="single" />
          <el-option label="批量检测" value="batch" />
        </el-select>
      </div>
    </template>

    <div class="tasks-container">
      <div class="phro-module tasks-grid">
        <div
          v-for="task in taskList"
          :key="task.id"
          class="task-card"
          @click="showTaskDetail(task)"
        >
          <div class="task-header">
            <div class="task-id">任务 #{{ task.id }}</div>
            <el-tag :type="getStatusTagType(task.status)" size="small">
              {{ getStatusLabel(task.status) }}
            </el-tag>
          </div>
          <div class="task-info">
            <div class="task-type">
              {{ task.task_type === 'single' ? '单图检测' : '批量检测' }}
              <el-tag :type="getSourceTagType(task.source)" size="mini" class="source-tag">
                {{ getSourceLabel(task.source) }}
              </el-tag>
            </div>
            <div class="task-scene">{{ task.scene_name || '未知场景' }}</div>
          </div>
          <div class="task-stats">
            <div class="stat-item">
              <span class="stat-value">{{ task.total_images || 0 }}</span>
              <span class="stat-label">图像数</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ task.total_objects || 0 }}</span>
              <span class="stat-label">缺陷数</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ formatTime(task.total_inference_time) }}</span>
              <span class="stat-label">耗时</span>
            </div>
          </div>
          <div class="task-footer">
            <span class="task-time">{{ formatDate(task.created_at) }}</span>
            <button
              type="button"
              class="phro-btn phro-btn--small"
              @click.stop="deleteTask(task.id)"
            >
              删除
            </button>
          </div>
        </div>

        <div v-if="taskList.length === 0" class="empty-state">
          <el-icon class="empty-icon"><Document /></el-icon>
          <p>暂无检测任务</p>
        </div>
      </div>

      <div class="phro-module pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </div>

    <el-dialog v-model="detailVisible" title="任务详情" width="800px">
      <div v-if="selectedTask" class="task-detail">
        <div class="detail-section">
          <h3>基本信息</h3>
          <div class="detail-row">
            <span class="detail-label">任务ID</span>
            <span class="detail-value">#{{ selectedTask.id }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">任务类型</span>
            <span class="detail-value">
              {{ selectedTask.task_type === 'single' ? '单图检测' : '批量检测' }}
              <el-tag :type="getSourceTagType(selectedTask.source)" size="mini">
                {{ getSourceLabel(selectedTask.source) }}
              </el-tag>
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">检测场景</span>
            <span class="detail-value">{{ selectedTask.scene_name || '未知场景' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">状态</span>
            <el-tag :type="getStatusTagType(selectedTask.status)">
              {{ getStatusLabel(selectedTask.status) }}
            </el-tag>
          </div>
        </div>

        <div class="detail-section">
          <h3>检测统计</h3>
          <div class="detail-row">
            <span class="detail-label">检测图像</span>
            <span class="detail-value">{{ selectedTask.total_images || 0 }} 张</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">识别缺陷</span>
            <span class="detail-value">{{ selectedTask.total_objects || 0 }} 个</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">总耗时</span>
            <span class="detail-value">{{ formatTime(selectedTask.total_inference_time) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">置信度阈值</span>
            <span class="detail-value">{{ selectedTask.conf_threshold }}</span>
          </div>
        </div>

        <div class="detail-section">
          <h3>时间信息</h3>
          <div class="detail-row">
            <span class="detail-label">创建时间</span>
            <span class="detail-value">{{ formatDate(selectedTask.created_at) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">完成时间</span>
            <span class="detail-value">{{ selectedTask.completed_at ? formatDate(selectedTask.completed_at) : '-' }}</span>
          </div>
        </div>

        <div v-if="selectedTask.error_message" class="detail-section error-section">
          <h3>错误信息</h3>
          <p class="error-message">{{ selectedTask.error_message }}</p>
        </div>
      </div>
    </el-dialog>
  </PhroPageShell>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Document } from '@element-plus/icons-vue'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import { getTasksApi, deleteTaskApi, getTaskDetailApi } from '@/api/tasks'

const taskList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const filterStatus = ref('')
const filterType = ref('')
const detailVisible = ref(false)
const selectedTask = ref(null)

async function loadTasks() {
  const params = {
    page: currentPage.value,
    page_size: pageSize.value,
    keyword: searchKeyword.value || undefined,
    status: filterStatus.value || undefined,
    task_type: filterType.value || undefined,
  }
  try {
    const res = await getTasksApi(params)
    if (res.code === 200) {
      taskList.value = res.data.items || []
      total.value = res.data.total || 0
    }
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  }
}

async function showTaskDetail(task) {
  try {
    const res = await getTaskDetailApi(task.id)
    if (res.code === 200) {
      selectedTask.value = res.data
      detailVisible.value = true
    }
  } catch (error) {
    ElMessage.error('加载任务详情失败')
  }
}

async function deleteTask(taskId) {
  try {
    await ElMessageBox.confirm('确定删除此任务？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await deleteTaskApi(taskId)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      loadTasks()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function getStatusTagType(status) {
  const map = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[status] || 'info'
}

function getStatusLabel(status) {
  const map = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[status] || status
}

function getSourceTagType(source) {
  const map = {
    quick: 'primary',
    batch: 'success',
    manual: 'info',
  }
  return map[source] || 'info'
}

function getSourceLabel(source) {
  const map = {
    quick: '快捷检测',
    batch: '批次检测',
    manual: '手动创建',
  }
  return map[source] || '未知来源'
}

function formatTime(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds.toFixed(2)}s`
  const mins = Math.floor(seconds / 60)
  const secs = (seconds % 60).toFixed(2)
  return `${mins}m ${secs}s`
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

onMounted(loadTasks)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.search-bar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  width: 200px;
}

.filter-select {
  width: 140px;
}

.tasks-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.task-card {
  padding: 16px;
  background: $phro-panel-bg;
  border: $phro-divider-width solid $phro-border;
  border-radius: $phro-radius;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;

  &:hover {
    border-color: rgba($phro-gold, 0.5);
    box-shadow: 0 0 0 1px rgba($phro-gold, 0.22);
  }
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-id {
  font-weight: 600;
  color: $phro-gold;
}

.task-info {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 13px;
  color: $phro-text-deep;

  .task-type {
    display: flex;
    align-items: center;
    gap: 6px;
  }
}

.task-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: $phro-gold;
}

.stat-label {
  font-size: 12px;
  color: $phro-text-mid;
}

.task-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: $phro-divider-width solid $phro-border;
}

.task-time {
  font-size: 12px;
  color: $phro-text-mid;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: $phro-text-mid;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
}

.task-detail {
  .detail-section {
    margin-bottom: 20px;
    padding-bottom: 20px;
    border-bottom: $phro-divider-width solid $phro-border;

    &:last-child {
      border-bottom: none;
      margin-bottom: 0;
      padding-bottom: 0;
    }

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 12px;
      color: $phro-gold;
    }
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
  }

  .detail-label {
    color: $phro-text-mid;
  }

  .detail-value {
    color: $phro-text-deep;
    font-weight: 500;
  }

  .error-section {
    background: rgba($phro-rose, 0.08);
    padding: 16px;
    border-radius: $phro-radius;
  }

  .error-message {
    color: $phro-rose;
    font-size: 14px;
  }
}
</style>