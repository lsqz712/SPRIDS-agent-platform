<template>
  <PhroPageShell
    title="历史记录"
    subtitle="检测任务查询、筛选与详情"
  >
    <div class="phro-module phro-module--grow history-module">
      <div class="filter-bar">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索任务 ID / 场景"
          clearable
          style="width: 200px"
          @keyup.enter="loadRecords"
        />
        <el-select v-model="filters.task_type" placeholder="检测类型" clearable style="width: 130px">
          <el-option v-for="t in TASK_TYPES" :key="t.key" :label="t.label" :value="t.key" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
          <el-option label="已完成" value="completed" />
          <el-option label="处理中" value="processing" />
          <el-option label="失败" value="failed" />
        </el-select>
        <button type="button" class="phro-btn phro-btn--primary" @click="loadRecords">查询</button>
        <button type="button" class="phro-btn" @click="resetFilters">重置</button>
      </div>

      <div class="phro-table-wrap">
        <el-table
          v-loading="loading"
          :data="records"
          stripe
          empty-text="暂无检测记录，请先在检测工作台执行检测"
          @row-click="openDetail"
        >
          <el-table-column prop="id" label="任务 ID" width="90" />
          <el-table-column prop="scene_name" label="场景" min-width="140" />
          <el-table-column label="类型" width="100">
            <template #default="{ row }">{{ typeLabel(row.task_type) }}</template>
          </el-table-column>
          <el-table-column prop="total_images" label="图像数" width="80" />
          <el-table-column prop="total_objects" label="缺陷数" width="80" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">
                {{ statusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="160">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @change="loadRecords"
        />
      </div>
    </div>

    <el-drawer
      v-model="drawerVisible"
      title="检测任务详情"
      size="480px"
      direction="rtl"
      class="phro-drawer"
    >
      <template v-if="detail">
        <div class="detail-stats phro-stat-grid">
          <div class="phro-stat-item">
            <div class="value">{{ detail.task.total_objects }}</div>
            <div class="label">缺陷总数</div>
          </div>
          <div class="phro-stat-item">
            <div class="value">{{ detail.task.total_images }}</div>
            <div class="label">图像数</div>
          </div>
          <div class="phro-stat-item">
            <div class="value">{{ Math.round(detail.task.total_inference_time) }}</div>
            <div class="label">总耗时 ms</div>
          </div>
        </div>
        <h4 class="detail-subtitle">缺陷明细</h4>
        <ul class="detail-list">
          <li v-for="(r, i) in detail.results" :key="i">
            <span class="phro-tag">{{ r.class_name_cn || r.class_name }}</span>
            <span>{{ (r.confidence * 100).toFixed(1) }}%</span>
            <span class="detail-image">{{ r.image_path }}</span>
          </li>
        </ul>
      </template>
    </el-drawer>
  </PhroPageShell>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import { TASK_TYPES, TASK_STATUS_MAP } from '@/constants/pcbDefects'
import {
  mockGetHistory,
  mockGetTaskDetail,
  withApiFallback,
} from '@/services/spridsMock'
import { getHistoryRecordsApi } from '@/api/history'
import { getTaskDetailApi } from '@/api/detection'

const loading = ref(false)
const records = ref([])
const drawerVisible = ref(false)
const detail = ref(null)

const filters = reactive({
  keyword: '',
  task_type: '',
  status: '',
})

const pagination = reactive({
  page: 1,
  page_size: 10,
  total: 0,
})

function typeLabel(type) {
  return TASK_TYPES.find((t) => t.key === type)?.label || type
}

function statusText(status) {
  return TASK_STATUS_MAP[status]?.label || status
}

function statusType(status) {
  return TASK_STATUS_MAP[status]?.type || 'info'
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

async function loadRecords() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      ...filters,
    }
    const res = await withApiFallback(
      () => getHistoryRecordsApi(params).then((r) => r?.data || r),
      () => mockGetHistory(params),
    )
    records.value = res.items || []
    pagination.total = res.total || 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.keyword = ''
  filters.task_type = ''
  filters.status = ''
  pagination.page = 1
  loadRecords()
}

async function openDetail(row) {
  detail.value = await withApiFallback(
    () => getTaskDetailApi(row.id).then((r) => r?.data || r),
    () => mockGetTaskDetail(row.id),
  )
  drawerVisible.value = true
}

onMounted(loadRecords)
</script>

<style lang="scss" scoped>
.history-module {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
  align-items: center;

  :deep(.el-input__wrapper) {
    background: rgba($phro-panel-bg, 0.95);
    box-shadow: none;
    border: 1px solid rgba($phro-rose, 0.35);
  }
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.detail-subtitle {
  font-size: 14px;
  color: $phro-text-deep;
  margin: 16px 0 10px;
}

.detail-list {
  list-style: none;
  margin: 0;
  padding: 0;

  li {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid rgba($phro-gold, 0.15);
    font-size: 13px;
    color: $phro-cream-muted;
  }
}

.detail-image {
  margin-left: auto;
  font-size: 11px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.phro-drawer.el-drawer) {
  background: rgba(32, 6, 14, 0.92);
  backdrop-filter: blur(8px);

  .el-drawer__header {
    color: $phro-cream;
    margin-bottom: 12px;
  }

  .el-drawer__body {
    color: $phro-cream-muted;
  }
}
</style>
