<template>
  <PhroPageShell title="个人中心" subtitle="账号信息与安全设置">
    <div class="profile-board phro-module">
      <header class="profile-hero">
        <div class="profile-hero-main">
          <button
            type="button"
            class="profile-avatar-btn"
            :class="{ 'is-uploading': uploadingAvatar }"
            :disabled="uploadingAvatar"
            title="点击上传头像"
            @click="openAvatarPicker"
          >
            <PhroUserAvatar
              :size="72"
              :src="userStore.avatar"
              variant="panel"
              :fallback="userStore.username?.charAt(0)?.toUpperCase()"
            />
            <span class="profile-avatar-mask">
              <span v-if="uploadingAvatar">上传中…</span>
              <span v-else>更换头像</span>
            </span>
          </button>
          <input
            ref="avatarInputRef"
            type="file"
            class="profile-avatar-input"
            :accept="AVATAR_ACCEPT"
            @change="onAvatarSelected"
          />
          <div class="profile-hero-text">
            <h3 class="profile-name">{{ profile.username || userStore.username }}</h3>
            <p class="profile-subtitle">{{ roleLabel }}</p>
            <div v-if="roleTags.length" class="profile-tags">
              <span v-for="tag in roleTags" :key="tag" class="phro-tag">{{ tag }}</span>
            </div>
          </div>
        </div>
        <span class="profile-status" :class="{ 'is-muted': profile.is_active === false }">
          {{ profile.is_active === false ? '账号已禁用' : '账号正常' }}
        </span>
      </header>

      <div class="profile-grid">
        <section class="profile-block">
          <div class="profile-block-head">
            <h3 class="phro-module-title">账户概览</h3>
          </div>
          <ul class="profile-info-list">
            <li>
              <span class="label">用户 ID</span>
              <span class="value">{{ profile.id ?? '—' }}</span>
            </li>
            <li>
              <span class="label">注册时间</span>
              <span class="value">{{ formatTime(profile.created_at) }}</span>
            </li>
            <li>
              <span class="label">最近登录</span>
              <span class="value">{{ formatTime(profile.last_login_at) }}</span>
            </li>
            <li>
              <span class="label">所属平台</span>
              <span class="value">Phrolova Agent Platform</span>
            </li>
            <li>
              <span class="label">业务系统</span>
              <span class="value">SPRIDS · PCB 检测</span>
            </li>
          </ul>
        </section>

        <section class="profile-block profile-block--stack">
          <div class="profile-block-section">
            <div class="profile-block-head">
              <div>
                <h3 class="phro-module-title">基本信息</h3>
                <p class="profile-block-desc">用户名、邮箱与手机号可在编辑后保存</p>
              </div>
              <button type="button" class="phro-btn phro-btn--sm" @click="openProfileDialog">编辑</button>
            </div>
            <ul class="profile-info-list profile-info-list--rows">
              <li>
                <span class="label">用户名</span>
                <span class="value">{{ profile.username || '—' }}</span>
              </li>
              <li>
                <span class="label">邮箱</span>
                <span class="value">{{ profile.email || '—' }}</span>
              </li>
              <li>
                <span class="label">手机号</span>
                <span class="value">{{ profile.phone || '—' }}</span>
              </li>
              <li>
                <span class="label">超级管理员</span>
                <span class="value">{{ userStore.isSuperuser ? '是' : '否' }}</span>
              </li>
            </ul>
          </div>

          <div class="profile-block-split" />

          <div class="profile-block-section profile-block-section--grow">
            <div class="profile-block-head">
              <div>
                <h3 class="phro-module-title">安全设置</h3>
                <p class="profile-block-desc">定期更换密码可提升账号安全性</p>
              </div>
              <button type="button" class="phro-btn phro-btn--sm" @click="openPasswordDialog">修改密码</button>
            </div>
            <ul class="profile-security-list">
              <li>
                <span class="dot" />
                <span>登录密码已加密存储，平台无法查看明文</span>
              </li>
              <li>
                <span class="dot" />
                <span>修改资料或密码后，当前会话保持有效</span>
              </li>
              <li>
                <span class="dot" />
                <span>若发现异常登录，请立即修改密码并联系管理员</span>
              </li>
            </ul>
          </div>
        </section>
      </div>

      <!-- 角色申请 -->
      <section v-if="roleApps.length || userStore.isSuperuser" class="profile-block" style="margin-top:16px">
        <div class="profile-block-head">
          <h3 class="phro-module-title">{{ userStore.isSuperuser ? '角色审批' : '我的角色申请' }}</h3>
        </div>
        <el-table v-if="userStore.isSuperuser" :data="roleApps" stripe size="small" max-height="300">
          <el-table-column prop="username" label="申请人" width="100" />
          <el-table-column prop="email" label="邮箱" width="180" />
          <el-table-column label="申请角色" width="140">
            <template #default="{ row }">{{ row.role_display_name }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status==='pending'?'warning':row.status==='approved'?'success':'danger'" size="small">
                {{ row.status==='pending'?'待审批':row.status==='approved'?'已通过':'已拒绝' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" v-if="userStore.isSuperuser">
            <template #default="{ row }">
              <template v-if="row.status==='pending'">
                <el-button size="small" type="success" @click="handleApprove(row.id,'approved')">通过</el-button>
                <el-button size="small" type="danger" @click="handleApprove(row.id,'rejected')">拒绝</el-button>
              </template>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
        <div v-else-if="roleApps.length" class="profile-apps-list">
          <div v-for="app in roleApps" :key="app.id" class="profile-app-item">
            <span>{{ app.role_display_name }}</span>
            <el-tag :type="app.status==='pending'?'warning':app.status==='approved'?'success':'danger'" size="small">
              {{ app.status==='pending'?'待审批':app.status==='approved'?'已通过':'已拒绝' }}
            </el-tag>
            <span class="app-time">{{ formatTime(app.applied_at) }}</span>
          </div>
        </div>
        <div v-else class="profile-app-empty">暂无角色申请记录</div>
      </section>

      <footer class="profile-footer">
        <p class="profile-footer-note">账号信息来自登录会话，可随时同步最新数据</p>
        <div class="profile-footer-actions">
          <button type="button" class="phro-btn phro-btn--sm" :disabled="loading" @click="refreshProfile">
            {{ loading ? '同步中…' : '同步账号信息' }}
          </button>
          <button type="button" class="phro-btn phro-btn--sm phro-btn--danger" @click="handleLogout">退出登录</button>
        </div>
      </footer>
    </div>

    <el-dialog
      v-model="profileDialogVisible"
      title="编辑资料"
      width="440px"
      class="phro-dialog"
      append-to-body
      :close-on-click-modal="false"
      destroy-on-close
      @closed="resetProfileForm"
    >
      <p class="phro-dialog-desc">可修改用户名、邮箱与手机号。</p>
      <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-position="top">
        <div class="phro-dialog-field">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="profileForm.username" placeholder="3-50 个字符" :prefix-icon="User" />
          </el-form-item>
        </div>
        <div class="phro-dialog-field">
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="profileForm.email" placeholder="请输入邮箱" :prefix-icon="Message" />
          </el-form-item>
        </div>
        <div class="phro-dialog-field">
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="profileForm.phone" placeholder="请输入手机号（可选）" :prefix-icon="Phone" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="phro-dialog__footer">
          <button type="button" class="phro-btn" @click="profileDialogVisible = false">取消</button>
          <button type="button" class="phro-btn phro-btn--primary" :disabled="savingProfile" @click="saveProfile">
            {{ savingProfile ? '保存中…' : '保存' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="440px"
      class="phro-dialog"
      append-to-body
      :close-on-click-modal="false"
      destroy-on-close
      @closed="resetPasswordForm"
    >
      <p class="phro-dialog-desc">请输入当前密码并设置新密码。</p>
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-position="top">
        <div class="phro-dialog-field">
          <el-form-item label="当前密码" prop="old_password">
            <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入当前密码" :prefix-icon="Lock" />
          </el-form-item>
        </div>
        <div class="phro-dialog-field">
          <el-form-item label="新密码" prop="new_password">
            <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="至少 6 位" :prefix-icon="Lock" />
          </el-form-item>
        </div>
        <div class="phro-dialog-field">
          <el-form-item label="确认新密码" prop="confirm_password">
            <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="再次输入新密码" :prefix-icon="Lock" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="phro-dialog__footer">
          <button type="button" class="phro-btn" @click="passwordDialogVisible = false">取消</button>
          <button type="button" class="phro-btn phro-btn--primary" :disabled="savingPassword" @click="savePassword">
            {{ savingPassword ? '提交中…' : '更新密码' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <PhroAvatarCropper
      v-model:visible="avatarCropVisible"
      :image-src="avatarCropSrc"
      @confirm="onAvatarCropped"
    />
  </PhroPageShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Message, Phone, Lock, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PhroPageShell from '@/components/layout/PhroPageShell.vue'
import PhroAvatarCropper from '@/components/profile/PhroAvatarCropper.vue'
import PhroUserAvatar from '@/components/common/PhroUserAvatar.vue'
import request from '@/utils/request'
import { useUserStore } from '@/stores/user'
import { showPhroConfirm } from '@/utils/phroMessageBox'
import { AVATAR_ACCEPT, validateAvatarFile } from '@/utils/avatar'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const roleApps = ref([])

async function loadRoleApps() {
  try {
    if (userStore.isSuperuser) {
      const res = await request.get('/roles/applications/')
      roleApps.value = res.data || res || []
    } else {
      const res = await request.get('/roles/me/applications')
      roleApps.value = res.data || res || []
    }
  } catch (e) { console.error('load apps failed:', e) }
}

async function handleApprove(applicationId, status) {
  try {
    await request.post(`/roles/applications/${applicationId}/approve`, { status, comment: status === 'approved' ? '审批通过' : '已拒绝' })
    ElMessage.success(status === 'approved' ? '已通过' : '已拒绝')
    loadRoleApps()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}
const uploadingAvatar = ref(false)
const avatarInputRef = ref(null)
const avatarCropVisible = ref(false)
const avatarCropSrc = ref('')
const savingProfile = ref(false)
const savingPassword = ref(false)
const profileDialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const profileFormRef = ref(null)
const passwordFormRef = ref(null)

const ROLE_LABELS = {
  admin: '管理员',
  operator: '质检操作员',
  engineer: '数据工程师',
  viewer: '普通访客',
}

const profile = computed(() => userStore.user || {})

const roleTags = computed(() => {
  const roles = userStore.roles || []
  return roles.map((r) => ROLE_LABELS[r] || r)
})

const roleLabel = computed(() => {
  if (userStore.isSuperuser) return '系统管理员'
  if (roleTags.value.length) return roleTags.value.join(' · ')
  return 'Phrolova Agent Platform'
})

const profileForm = reactive({
  username: '',
  email: '',
  phone: '',
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const profileRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为 3-50 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  phone: [
    { pattern: /^$|^1[3-9]\d{9}$/, message: '请输入有效手机号', trigger: 'blur' },
  ],
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== passwordForm.new_password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

function syncProfileForm() {
  profileForm.username = profile.value.username || ''
  profileForm.email = profile.value.email || ''
  profileForm.phone = profile.value.phone || ''
}

watch(profile, syncProfileForm, { immediate: true, deep: true })

function formatTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN')
}

function openProfileDialog() {
  syncProfileForm()
  profileFormRef.value?.clearValidate()
  profileDialogVisible.value = true
}

function openPasswordDialog() {
  resetPasswordForm()
  passwordDialogVisible.value = true
}

function resetProfileForm() {
  syncProfileForm()
  profileFormRef.value?.clearValidate()
}

function resetPasswordForm() {
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  passwordFormRef.value?.clearValidate()
}

function openAvatarPicker() {
  if (uploadingAvatar.value) return
  avatarInputRef.value?.click()
}

function clearAvatarCropSrc() {
  if (avatarCropSrc.value) {
    URL.revokeObjectURL(avatarCropSrc.value)
    avatarCropSrc.value = ''
  }
}

async function onAvatarSelected(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  const error = validateAvatarFile(file)
  if (error) {
    ElMessage.warning(error)
    return
  }

  clearAvatarCropSrc()
  avatarCropSrc.value = URL.createObjectURL(file)
  avatarCropVisible.value = true
}

async function onAvatarCropped(blob) {
  clearAvatarCropSrc()
  const file = new File([blob], 'avatar.jpg', { type: 'image/jpeg' })

  uploadingAvatar.value = true
  try {
    await userStore.uploadAvatar(file)
    ElMessage.success('头像已更新')
  } catch {
    /* 拦截器已提示 */
  } finally {
    uploadingAvatar.value = false
  }
}

watch(avatarCropVisible, (visible) => {
  if (!visible) {
    clearAvatarCropSrc()
  }
})

async function refreshProfile() {
  if (userStore.token === 'dev-preview') {
    ElMessage.info('预览模式：展示本地账号信息')
    syncProfileForm()
    return
  }
  loading.value = true
  try {
    await userStore.fetchUserInfo()
    ElMessage.success('账号信息已同步')
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return

  savingProfile.value = true
  try {
    await userStore.updateProfile({
      username: profileForm.username.trim(),
      email: profileForm.email.trim(),
      phone: profileForm.phone.trim() || null,
    })
    ElMessage.success('资料已保存')
    profileDialogVisible.value = false
  } catch {
    /* 拦截器已提示 */
  } finally {
    savingProfile.value = false
  }
}

async function savePassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return

  savingPassword.value = true
  try {
    await userStore.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success(userStore.token === 'dev-preview' ? '预览模式：密码修改已模拟成功' : '密码已更新')
    passwordDialogVisible.value = false
  } catch {
    /* 拦截器已提示 */
  } finally {
    savingPassword.value = false
  }
}

async function handleLogout() {
  try {
    await showPhroConfirm('确定要退出登录吗？', '退出登录', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
    })
    userStore.logout()
    router.push('/login')
  } catch {
    /* 用户取消 */
  }
}

onMounted(() => {
  loadRoleApps()
  if (userStore.token && userStore.token !== 'dev-preview' && !userStore.user?.email) {
    refreshProfile()
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.profile-board {
  flex: 1;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 18px $phro-window-padding $phro-window-padding;
}

.profile-hero {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba($phro-rose, 0.18);
}

.profile-hero-main {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.profile-avatar-btn {
  position: relative;
  flex-shrink: 0;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 50%;

  &:disabled {
    cursor: not-allowed;
  }

  &:hover:not(:disabled) .profile-avatar-mask,
  &:focus-visible:not(:disabled) .profile-avatar-mask {
    opacity: 1;
  }
}

.profile-avatar-input {
  display: none;
}

.profile-avatar-btn :deep(.phro-user-avatar) {
  display: block;
}

.profile-avatar-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(40, 8, 16, 0.52);
  color: $phro-cream;
  font-size: 11px;
  letter-spacing: 0.04em;
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
}

.profile-avatar-btn.is-uploading .profile-avatar-mask {
  opacity: 1;
}

.profile-hero-text {
  min-width: 0;
}

.profile-name {
  margin: 0 0 2px;
  font-size: 20px;
  font-weight: 600;
  color: $phro-text-deep;
}

.profile-subtitle {
  margin: 0 0 8px;
  font-size: 12px;
  color: $phro-text-mid;
}

.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.profile-status {
  flex-shrink: 0;
  font-size: 12px;
  padding: 5px 14px;
  border-radius: 999px;
  background: rgba($phro-gold, 0.15);
  border: 1px solid rgba($phro-gold, 0.4);
  color: $phro-text-deep;

  &.is-muted {
    background: rgba($phro-rose, 0.1);
    border-color: rgba($phro-rose, 0.35);
    color: $phro-rose;
  }
}

.profile-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(240px, 34%) minmax(0, 1fr);
  gap: 0;
  border: 1px solid rgba($phro-rose, 0.16);
  border-radius: $phro-radius-sm;
  overflow: hidden;
}

.profile-block {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 16px 18px;

  &:first-child {
    background: rgba($phro-rose, 0.04);
    border-right: 1px solid rgba($phro-rose, 0.14);
  }

  &--stack {
    padding: 0;
  }
}

.profile-block-section {
  padding: 16px 18px;

  &--grow {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
}

.profile-block-split {
  height: 1px;
  margin: 0 18px;
  background: rgba($phro-rose, 0.14);
}

.profile-block--stack {
  display: flex;
  flex-direction: column;
}

.profile-block-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;

  .phro-module-title {
    margin-bottom: 4px;
    padding-bottom: 0;
    border-bottom: none;
  }
}

.profile-block-desc {
  margin: 0;
  font-size: 12px;
  color: $phro-text-mid;
}

.profile-info-list {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;

  li {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 11px 0;
    border-bottom: 1px solid rgba($phro-rose, 0.1);

    &:last-child {
      border-bottom: none;
    }
  }

  &--rows li {
    display: grid;
    grid-template-columns: 88px minmax(0, 1fr);
    gap: 12px;
    align-items: baseline;
    flex-direction: row;
  }

  .label {
    font-size: 11px;
    color: $phro-text-mid;
  }

  .value {
    font-size: 13px;
    color: $phro-text-deep;
    word-break: break-all;
  }
}

.profile-security-list {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;

  li {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 0;
    font-size: 13px;
    line-height: 1.55;
    color: $phro-text-mid;
    border-bottom: 1px solid rgba($phro-rose, 0.08);

    &:last-child {
      border-bottom: none;
    }
  }

  .dot {
    flex-shrink: 0;
    width: 6px;
    height: 6px;
    margin-top: 7px;
    border-radius: 50%;
    background: rgba($phro-gold, 0.75);
  }
}

.profile-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba($phro-rose, 0.18);
}

.profile-footer-note {
  margin: 0;
  font-size: 12px;
  color: $phro-text-mid;
}

.profile-footer-actions {
  display: flex;
  flex-shrink: 0;
  gap: 10px;
}

.phro-btn--danger {
  color: $phro-cream;
  background: linear-gradient(135deg, rgba($phro-rose, 0.9), rgba($phro-crimson, 0.95));
  border-color: rgba($phro-gold, 0.35);
}

@media (max-width: 900px) {
  .profile-board {
    height: auto;
  }

  .profile-grid {
    grid-template-columns: 1fr;
  }

  .profile-block:first-child {
    border-right: none;
    border-bottom: 1px solid rgba($phro-rose, 0.14);
  }

  .profile-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .profile-footer-actions {
    justify-content: flex-end;
  }
}
</style>
