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
            <div class="batch-actions">
              <button
                type="button"
                class="phro-btn phro-btn--small"
                @click.stop="detectBatch(batch.id)"
                :disabled="batch.status === 'in_progress'"
              >
                一键检测
              </button>
              <button
                type="button"
                class="phro-btn phro-btn--small phro-btn--secondary"
                @click.stop="deleteBatch(batch.id)"
              >
                删除
              </button>
            </div>
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

    <el-dialog v-model="showCreateForm" title="创建批次" width="600px">
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
          <el-input-number v-model="createForm.total_count" :min="0" placeholder="不传则根据图片数量自动计算" />
          <span v-if="uploadedFiles.length > 0" class="ml-2 text-sm text-green-500">
            已上传 {{ uploadedFiles.length }} 张图片
          </span>
        </el-form-item>
        <el-form-item label="批次图片">
          <el-upload
            class="upload-demo"
            :action="''"
            :file-list="uploadedFiles"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            multiple
            accept="image/jpeg,image/png,image/jpg,image/bmp"
            list-type="picture-card"
          >
            <el-icon><Plus /></el-icon>
            <template #tip>
              <div class="el-upload__tip">支持 JPG、PNG 格式，可上传多张图片</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <button type="button" class="phro-btn phro-btn--secondary" @click="closeCreateForm">
          取消
        </button>
        <button type="button" class="phro-btn" @click="createBatch">
          创建
        </button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="批次详情" width="700px">
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
          <div class="section-header">
            <h3>检测统计</h3>
            <button
              type="button"
              class="phro-btn phro-btn--small"
              @click="detectBatch(selectedBatch.id)"
              :disabled="selectedBatch.status === 'in_progress'"
            >
              一键检测
            </button>
          </div>
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
              <div class="stat-value danger">{{ selectedBatch.total_defects ?? selectedBatch.fail_count }}</div>
              <div class="stat-label">缺陷总数</div>
            </div>
            <div class="stat-card pass-rate-card" :class="{ warning: selectedBatch.pass_rate < 90 }">
              <div class="stat-value">{{ (selectedBatch.pass_rate * 100).toFixed(1) }}%</div>
              <div class="stat-label">良品率</div>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-header">
            <h3>批次图片</h3>
            <button type="button" class="phro-btn phro-btn--small" @click="showUploadDialog = true">
              导入图片
            </button>
          </div>
          <div v-if="batchImages.length > 0" class="images-grid">
            <div v-for="img in batchImages" :key="img.id" class="image-item">
              <BboxCanvas :image-src="img.image_url" :detections="img.detections || []" />
              <div class="image-info">
                <span class="image-name">{{ img.filename }}</span>
                <el-tag :type="getImageStatusTagType(img.status)" size="small">
                  {{ getImageStatusLabel(img.status) }}
                </el-tag>
              </div>
            </div>
          </div>
          <div v-else class="empty-images">
            <el-icon class="empty-icon"><ImageIcon /></el-icon>
            <p>暂无图片，点击上方按钮导入</p>
          </div>
        </div>

        <div v-if="allDetections.length" class="detail-section">
          <h3>检测结果 ({{ allDetections.length }})</h3>
          <el-table :data="allDetections" size="small" max-height="300" stripe>
            <el-table-column prop="class_name_cn" label="缺陷类型" width="80" />
            <el-table-column label="置信度" width="80">
              <template #default="{ row }">{{ (row.confidence * 100).toFixed(0) }}%</template>
            </el-table-column>
            <el-table-column label="边界框" width="140">
              <template #default="{ row }">{{ row.bbox?.map(v=>Math.round(v)).join(', ') }}</template>
            </el-table-column>
          </el-table>
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

    <el-dialog v-model="showUploadDialog" title="导入图片" width="500px">
      <el-upload
        class="upload-demo"
        :action="''"
        :file-list="uploadFiles"
        :auto-upload="false"
        :on-change="handleUploadFileChange"
        :on-remove="handleUploadFileRemove"
        multiple
        accept="image/jpeg,image/png,image/jpg,image/bmp"
        list-type="picture-card"
      >
        <el-icon><Plus /></el-icon>
        <template #tip>
          <div class="el-upload__tip">支持 JPG、PNG 格式，可上传多张图片</div>
        </template>
      </el-upload>
      <template #footer>
        <button type="button" class="phro-btn phro-btn--secondary" @click="showUploadDialog = false">
          取消
        </button>
        <button type="button" class="phro-btn" @click="uploadImages">
          上传
        </button>
      </template>
    </el-dialog>
  </PhroPageShell>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Box, Plus, Picture as ImageIcon } from '@element-plus/icons-vue'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import BboxCanvas from '@/components/detection/BboxCanvas.vue'
import {
  getBatchesApi,
  createBatchWithImagesApi,
  getBatchDetailApi,
  deleteBatchApi,
  uploadBatchImagesApi,
  getBatchImagesApi,
  detectBatchApi,
} from '@/api/batches'

const batchList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const filterStatus = ref('')
const showCreateForm = ref(false)
const detailVisible = ref(false)
const showUploadDialog = ref(false)
const selectedBatch = ref(null)
const batchImages = ref([])
const allDetections = computed(() => batchImages.value.flatMap(img => img.detections || []))
const uploadedFiles = ref([])
const uploadFiles = ref([])

const createForm = reactive({
  batch_no: '',
  pcb_type: '',
  production_line: '',
  total_count: 0,
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

function handleFileChange(file, fileList) {
  uploadedFiles.value = fileList
}

function handleFileRemove(file, fileList) {
  uploadedFiles.value = fileList
}

function handleUploadFileChange(file, fileList) {
  uploadFiles.value = fileList
}

function handleUploadFileRemove(file, fileList) {
  uploadFiles.value = fileList
}

function closeCreateForm() {
  showCreateForm.value = false
  createForm.batch_no = ''
  createForm.pcb_type = ''
  createForm.production_line = ''
  createForm.total_count = 0
  uploadedFiles.value = []
}

async function createBatch() {
  if (!createForm.batch_no || !createForm.pcb_type || !createForm.production_line) {
    ElMessage.warning('请填写完整信息')
    return
  }
  const files = uploadedFiles.value.map(f => f.raw)
  try {
    const res = await createBatchWithImagesApi({
      batch_no: createForm.batch_no,
      pcb_type: createForm.pcb_type,
      production_line: createForm.production_line,
      total_count: createForm.total_count,
      files,
    })
    if (res.code === 201) {
      ElMessage.success('批次创建成功')
      closeCreateForm()
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
      batchImages.value = res.data.images || []
      detailVisible.value = true
    }
  } catch (error) {
    ElMessage.error('加载批次详情失败')
  }
}

async function uploadImages() {
  if (!selectedBatch.value || uploadFiles.value.length === 0) {
    ElMessage.warning('请选择要上传的图片')
    return
  }
  const files = uploadFiles.value.map(f => f.raw)
  try {
    const res = await uploadBatchImagesApi(selectedBatch.value.id, files)
    if (res.code === 200) {
      ElMessage.success('图片上传成功')
      showUploadDialog.value = false
      uploadFiles.value = []
      await showBatchDetail(selectedBatch.value)
      loadBatches()
    }
  } catch (error) {
    ElMessage.error('上传图片失败')
  }
}

async function detectBatch(batchId) {
  try {
    await ElMessageBox.confirm('确定要对该批次进行检测吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await detectBatchApi(batchId, { conf: 0.25 })
    if (res.code === 200) {
      ElMessage.success('批次检测任务已创建')
      loadBatches()
      if (detailVisible.value && selectedBatch.value && selectedBatch.value.id === batchId) {
        await showBatchDetail(selectedBatch.value)
      }
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('检测失败')
    }
  }
}

async function deleteBatch(batchId) {
  try {
    await ElMessageBox.confirm('确定删除此批次？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteBatchApi(batchId)
    ElMessage.success('删除成功')
    loadBatches()
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

function getImageStatusTagType(status) {
  const map = {
    pending: 'info',
    detected: 'warning',
    pass: 'success',
    fail: 'danger',
  }
  return map[status] || 'info'
}

function getImageStatusLabel(status) {
  const map = {
    pending: '待检测',
    detected: '已检测',
    pass: '良品',
    fail: '不良品',
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

.batch-actions {
  display: flex;
  gap: 8px;
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

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
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

  .images-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }

  .image-item {
    position: relative;
    border-radius: $phro-radius;
    overflow: hidden;
    border: $phro-divider-width solid $phro-border;

    .preview-img {
      width: 100%;
      height: 180px;
      object-fit: cover;
    }

    .image-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 8px;
      background: $phro-panel-bg;
    }

    .image-name {
      font-size: 11px;
      color: $phro-text-mid;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 70%;
    }
  }

  .empty-images {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 30px;
    color: $phro-text-mid;
  }
}
</style>