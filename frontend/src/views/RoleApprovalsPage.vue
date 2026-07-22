<template>
  <PhroPageShell title="角色审批" subtitle="管理用户角色申请" scroll-body>
    <div class="phro-module">
      <el-table v-loading="loading" :data="applications" stripe empty-text="暂无待审批申请">
        <el-table-column prop="id" label="申请 ID" width="80" />
        <el-table-column prop="username" label="申请人" width="120" />
        <el-table-column prop="email" label="邮箱" width="180" />
        <el-table-column label="申请角色" width="160">
          <template #default="{ row }">{{ row.role_display_name }} ({{ row.role_name }})</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'pending' ? 'warning' : row.status === 'approved' ? 'success' : 'danger'" size="small">
              {{ row.status === 'pending' ? '待审批' : row.status === 'approved' ? '已通过' : '已拒绝' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="approve_comment" label="审批意见" min-width="150" />
        <el-table-column label="申请时间" width="170">
          <template #default="{ row }">{{ formatTime(row.applied_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" v-if="isAdmin">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <button type="button" class="phro-btn" style="margin-right:6px" @click="approve(row.id, 'approved')">通过</button>
              <button type="button" class="phro-btn" @click="approve(row.id, 'rejected')">拒绝</button>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </PhroPageShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import { useUserStore } from '@/stores/user'
import request from '@/utils/request'

const userStore = useUserStore()
const loading = ref(false)
const applications = ref([])
const isAdmin = computed(() => userStore.isSuperuser)

async function loadApplications() {
  loading.value = true
  try {
    const res = await request.get('/roles/applications/')
    applications.value = res.data || res || []
  } catch (e) {
    console.error('Load applications failed:', e)
  } finally {
    loading.value = false
  }
}

async function approve(applicationId, status) {
  try {
    await request.post(`/roles/applications/${applicationId}/approve`, {
      status,
      comment: status === 'approved' ? '审批通过' : '已拒绝',
    })
    ElMessage.success(status === 'approved' ? '已通过' : '已拒绝')
    loadApplications()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(loadApplications)
</script>
