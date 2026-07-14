<template>
  <PhroPageShell
    title="批次管理"
    subtitle="PCB批次列表 · 良品率统计 · 产线管理"
    scroll-body
  >
    <template #actions>
      <div class="actions-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索批次号/PCB型号"
          class="search-input"
          @keyup.enter="loadBatches"
        >
          <template #prefix>
            <el-icon class="el-input__icon"><Search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="filterStatus"
          placeholder="状态筛选"
          class="filter-select"
          @change="loadBatches"
        >
          <el-option label="全部" value="" />
          <el-option label="待检测" value="pending" />
          <el-option label="检测中" value="in_progress" />
          <el-option label="已完成" value="completed" />
        </el-select>
        <button type="button" class="phro-btn" @click="showCreateForm = true">
          创建批次
        </button>
      </div>
    </template>

    <div class="batches-container">
      <div class="phro-module batches-grid">
        <div
          v-for="batch in batchList"
          :key="batch.id"
          class="batch-card"
          @click="showBatchDetail(batch)"
        >
          <div class="batch-header">
            <div class="batch-no">{{ batch.batch_no }}</div>
            <el-tag :type="getBatchStatusTagType(batch.status)" size="small">
              {{ getBatchStatusLabel(batch.status) }}
            </el-tag>
          </div>
          <div class="batch-info">
            <div class="batch-pcb">{{ batch.pcb_type }}</div>
            <div class="batch-line">{{ batch.production_line }}</div>
          </div>
          <div class="batch-stats">
            <div class="stat-item">
              <span class="stat-value">{{ batch.total_count }}</span>
              <span class="stat-label">总数量</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ batch.inspected_count }}</span>
              <span class="stat-label">已检测</span>
            </div>
            <div class="stat-item pass-rate">
              <span class="stat-value" :class="{ warning: batch.pass_rate < 90 }">
                {{ (batch.pass_rate * 100).toFixed(1) }}%
              </span>
              <span class="stat-label">良品率</span>
            </div>
          </div>
          <div class="batch-footer">
            <span class="batch-time">{{ formatDate(batch.created_at) }}</span>
            <button
              type="button"
              class="phro-btn phro-btn--small"
              @click.stop="deleteBatch(batch.id)"
            >
              删除
            </button>
          </div>
        </div>

        <div v-if="batchList.length === 0" class="empty-state">
          <el-icon class="empty-icon"><Box /></el-icon>
          <p>暂无PCB批次</p>
        </div>
      </div>

      <div class="phro-module pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadBatches"
          @current-change="loadBatches"
        />
      </div>
    </div>

    <el-dialog v-model="showCreateForm" title="创建批次" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="批次号">
          <el-input v-model="createForm.batch_no" placeholder="如 BATCH-20250701-001" />
        </el-form-item>
        <el-form-item label="PCB型号">
          <el-input v-model="createForm.pcb_type" placeholder="如 PCB-V2.1" />
        </el-form-item>
        <el-form-item label="产线编号">
          <el-input v-model="createForm.production_line" placeholder="如 LINE-A01" />
        </el-form-item>
        <el-form-item label="总数量">
          <el-input-number v-model="createForm.total_count" :min="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button type="button" class="phro-btn phro-btn--secondary" @click="showCreateForm = false">
          取消
        </button>
        <button type="button" class="phro-btn" @click="createBatch">
          创建
        </button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="批次详情" width="600px">
      <div v-if="selectedBatch" class="batch-detail">
        <div class="detail-section">
          <h3>基本信息</h3>
          <div class="detail-row">
            <span class="detail-label">批次号</span>
            <span class="detail-value">{{ selectedBatch.batch_no }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">PCB型号</span>
            <span class="detail-value">{{ selectedBatch.pcb_type }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">产线编号</span>
            <span class="detail-value">{{ selectedBatch.production_line }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">状态</span>
            <el-tag :type="getBatchStatusTagType(selectedBatch.status)">
              {{ getBatchStatusLabel(selectedBatch.status) }}
            </el-tag>
          </div>
        </div>

        <div class="detail-section">
          <h3>检测统计</h3>
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-value">{{ selectedBatch.total_count }}</div>
              <div class="stat-label">总数量</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ selectedBatch.inspected_count }}</div>
              <div class="stat-label">已检测</div>
            </div>
            <div class="stat-card">
              <div class="stat-value success">{{ selectedBatch.pass_count }}</div>
              <div class="stat-label">良品</div>
            </div>
            <div class="stat-card">
              <div class="stat-value danger">{{ selectedBatch.fail_count }}</div>
              <div class="stat-label">不良品</div>
            </div>
            <div class="stat-card pass-rate-card" :class="{ warning: selectedBatch.pass_rate < 90 }">
              <div class="stat-value">{{ (selectedBatch.pass_rate * 100).toFixed(1) }}%</div>
              <div class="stat-label">良品率</div>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h3>时间信息</h3>
          <div class="detail-row">
            <span class="detail-label">创建时间</span>
            <span class="detail-value">{{ formatDate(selectedBatch.created_at) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">更新时间</span>
            <span class="detail-value">{{ formatDate(selectedBatch.updated_at) }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </PhroPageShell>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Box } from '@element-plus/icons-vue'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import { getBatchesApi, createBatchApi, getBatchDetailApi, deleteBatchApi } from '@/api/batches'

const batchList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const filterStatus = ref('')
const showCreateForm = ref(false)
const detailVisible = ref(false)
const selectedBatch = ref(null)

const createForm = reactive({
  batch_no: '',
  pcb_type: '',
  production_line: '',
  total_count: 1,
})

async function loadBatches() {
  const params = {
    page: currentPage.value,
    page_size: pageSize.value,
    keyword: searchKeyword.value || undefined,
    status: filterStatus.value || undefined,
  }
  try {
    const res = await getBatchesApi(params)
    if (res.code === 200) {
      batchList.value = res.data.items || []
      total.value = res.data.total || 0
    }
  } catch (error) {
    ElMessage.error('加载批次列表失败')
  }
}

async function createBatch() {
  if (!createForm.batch_no || !createForm.pcb_type || !createForm.production_line) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    const res = await createBatchApi(createForm)
    if (res.code === 201) {
      ElMessage.success('批次创建成功')
      showCreateForm.value = false
      createForm.batch_no = ''
      createForm.pcb_type = ''
      createForm.production_line = ''
      createForm.total_count = 1
      loadBatches()
    }
  } catch (error) {
    ElMessage.error('创建批次失败')
  }
}

async function showBatchDetail(batch) {
  try {
    const res = await getBatchDetailApi(batch.id)
    if (res.code === 200) {
      selectedBatch.value = res.data
      detailVisible.value = true
    }
  } catch (error) {
    ElMessage.error('加载批次详情失败')
  }
}

async function deleteBatch(batchId) {
  try {
    await ElMessageBox.confirm('确定删除此批次？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await deleteBatchApi(batchId)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      loadBatches()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function getBatchStatusTagType(status) {
  const map = {
    pending: 'info',
    in_progress: 'warning',
    completed: 'success',
  }
  return map[status] || 'info'
}

function getBatchStatusLabel(status) {
  const map = {
    pending: '待检测',
    in_progress: '检测中',
    completed: '已完成',
  }
  return map[status] || status
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

onMounted(loadBatches)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.actions-bar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  width: 250px;
}

.filter-select {
  width: 140px;
}

.batches-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.batches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.batch-card {
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

.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.batch-no {
  font-weight: 600;
  color: $phro-gold;
}

.batch-info {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 13px;
  color: $phro-text-deep;
}

.batch-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;

  &.pass-rate .stat-value.warning {
    color: $phro-rose;
  }
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: $phro-gold;

  &.success {
    color: #67c23a;
  }

  &.danger {
    color: $phro-rose;
  }
}

.stat-label {
  font-size: 12px;
  color: $phro-text-mid;
}

.batch-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: $phro-divider-width solid $phro-border;
}

.batch-time {
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

.batch-detail {
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

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
  }

  .stat-card {
    padding: 12px;
    background: $phro-panel-bg;
    border-radius: $phro-radius;
    text-align: center;

    &.pass-rate-card.warning .stat-value {
      color: $phro-rose;
    }
  }
}
</style>