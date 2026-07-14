<template>
  <PhroPageShell
    title="缺陷类型"
    subtitle="缺陷字典管理 · 严重等级标注"
    scroll-body
  >
    <template #actions>
      <div class="actions-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索编码/名称"
          class="search-input"
          @keyup.enter="loadDefectTypes"
        >
          <template #prefix>
            <el-icon class="el-input__icon"><Search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="filterSeverity"
          placeholder="严重等级"
          class="filter-select"
          @change="loadDefectTypes"
        >
          <el-option label="全部" value="" />
          <el-option label="轻微" value="minor" />
          <el-option label="中等" value="major" />
          <el-option label="严重" value="critical" />
        </el-select>
        <button type="button" class="phro-btn" @click="showCreateForm = true">
          添加缺陷类型
        </button>
      </div>
    </template>

    <div class="defect-container">
      <div class="phro-module defect-list">
        <el-table :data="defectList" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="code" label="编码" width="120" />
          <el-table-column prop="name" label="名称" width="150" />
          <el-table-column prop="name_cn" label="中文名称" width="120" />
          <el-table-column prop="severity" label="严重等级" width="100">
            <template #default="scope">
              <el-tag :type="getSeverityTagType(scope.row.severity)" size="small">
                {{ getSeverityLabel(scope.row.severity) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" />
          <el-table-column prop="is_active" label="状态" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success' : 'info'" size="small">
                {{ scope.row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <button
                type="button"
                class="phro-btn phro-btn--small"
                @click="editDefectType(scope.row)"
              >
                编辑
              </button>
              <button
                type="button"
                class="phro-btn phro-btn--small phro-btn--secondary"
                @click="deleteDefectType(scope.row.id)"
              >
                删除
              </button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="defectList.length === 0" class="empty-state">
          <el-icon class="empty-icon"><CollectionTag /></el-icon>
          <p>暂无缺陷类型</p>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreateForm" :title="editingDefect ? '编辑缺陷类型' : '添加缺陷类型'" width="500px">
      <el-form :model="defectForm" label-width="100px">
        <el-form-item label="缺陷编码">
          <el-input v-model="defectForm.code" placeholder="如 SHORT_01" />
        </el-form-item>
        <el-form-item label="缺陷名称">
          <el-input v-model="defectForm.name" placeholder="如 Short Circuit" />
        </el-form-item>
        <el-form-item label="中文名称">
          <el-input v-model="defectForm.name_cn" placeholder="如 短路" />
        </el-form-item>
        <el-form-item label="严重等级">
          <el-select v-model="defectForm.severity">
            <el-option label="轻微" value="minor" />
            <el-option label="中等" value="major" />
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="defectForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="defectForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button type="button" class="phro-btn phro-btn--secondary" @click="closeForm">
          取消
        </button>
        <button type="button" class="phro-btn" @click="saveDefectType">
          {{ editingDefect ? '保存' : '添加' }}
        </button>
      </template>
    </el-dialog>
  </PhroPageShell>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, CollectionTag } from '@element-plus/icons-vue'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import { getDefectTypesApi, createDefectTypeApi, updateDefectTypeApi, deleteDefectTypeApi } from '@/api/defectTypes'

const defectList = ref([])
const searchKeyword = ref('')
const filterSeverity = ref('')
const showCreateForm = ref(false)
const editingDefect = ref(null)

const defectForm = reactive({
  code: '',
  name: '',
  name_cn: '',
  severity: 'major',
  description: '',
  is_active: true,
})

async function loadDefectTypes() {
  const params = {
    keyword: searchKeyword.value || undefined,
    severity: filterSeverity.value || undefined,
  }
  try {
    const res = await getDefectTypesApi(params)
    if (res.code === 200) {
      defectList.value = res.data || []
    }
  } catch (error) {
    ElMessage.error('加载缺陷类型失败')
  }
}

function editDefectType(defect) {
  editingDefect.value = defect
  defectForm.code = defect.code
  defectForm.name = defect.name
  defectForm.name_cn = defect.name_cn
  defectForm.severity = defect.severity
  defectForm.description = defect.description || ''
  defectForm.is_active = defect.is_active
  showCreateForm.value = true
}

function closeForm() {
  showCreateForm.value = false
  editingDefect.value = null
  defectForm.code = ''
  defectForm.name = ''
  defectForm.name_cn = ''
  defectForm.severity = 'major'
  defectForm.description = ''
  defectForm.is_active = true
}

async function saveDefectType() {
  if (!defectForm.code || !defectForm.name || !defectForm.name_cn) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    if (editingDefect.value) {
      const res = await updateDefectTypeApi(editingDefect.value.id, defectForm)
      if (res.code === 200) {
        ElMessage.success('更新成功')
      }
    } else {
      const res = await createDefectTypeApi(defectForm)
      if (res.code === 201) {
        ElMessage.success('添加成功')
      }
    }
    closeForm()
    loadDefectTypes()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

async function deleteDefectType(defectTypeId) {
  try {
    await ElMessageBox.confirm('确定删除此缺陷类型？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await deleteDefectTypeApi(defectTypeId)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      loadDefectTypes()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function getSeverityTagType(severity) {
  const map = {
    minor: 'success',
    major: 'warning',
    critical: 'danger',
  }
  return map[severity] || 'info'
}

function getSeverityLabel(severity) {
  const map = {
    minor: '轻微',
    major: '中等',
    critical: '严重',
  }
  return map[severity] || severity
}

onMounted(loadDefectTypes)
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.actions-bar {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  width: 200px;
}

.filter-select {
  width: 120px;
}

.defect-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: $phro-text-mid;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

:deep(.el-table) {
  background: $phro-panel-bg;
  border: $phro-divider-width solid $phro-border;
  border-radius: $phro-radius;
  overflow: hidden;
}

:deep(.el-table th) {
  background: rgba($phro-gold, 0.08);
  color: $phro-gold;
  font-weight: 600;
}

:deep(.el-table td) {
  color: $phro-text-deep;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: rgba($phro-gold, 0.02);
}
</style>