<template>
  <div class="forgot-password-page">
    <div class="forgot-card">
      <div class="forgot-header">
        <img src="/logo.webp" alt="logo" class="forgot-logo" />
        <h2>Phrolova Agent Platform</h2>
        <p>弗洛洛智能体平台</p>
      </div>

      <!-- 步骤1: 输入邮箱 -->
      <template v-if="step === 1">
        <p class="step-desc">请输入您的注册邮箱，我们将向您发送密码重置链接</p>

        <el-form
          ref="emailFormRef"
          class="forgot-form"
          :model="emailForm"
          :rules="emailRules"
          label-width="0"
          size="large"
          @submit.prevent="handleRequestReset"
        >
          <div class="forgot-field forgot-module">
            <el-form-item prop="email">
              <el-input
                v-model="emailForm.email"
                placeholder="请输入注册邮箱"
                :prefix-icon="Message"
              />
            </el-form-item>
          </div>

          <button
            type="button"
            class="phro-btn forgot-btn forgot-module"
            :disabled="sending"
            @click="handleRequestReset"
          >
            {{ sending ? '发送中…' : '发送重置链接' }}
          </button>
        </el-form>
      </template>

      <!-- 步骤2: 设置新密码 -->
      <template v-if="step === 2">
        <p class="step-desc">验证通过，请输入您的新密码</p>

        <el-form
          ref="resetFormRef"
          class="forgot-form"
          :model="resetForm"
          :rules="resetRules"
          label-width="0"
          size="large"
          @submit.prevent="handleResetPassword"
        >
          <div class="forgot-field forgot-module">
            <el-form-item prop="new_password">
              <el-input
                v-model="resetForm.new_password"
                type="password"
                placeholder="请输入新密码（至少 6 位）"
                :prefix-icon="Lock"
                show-password
              />
            </el-form-item>
          </div>

          <div class="forgot-field forgot-module">
            <el-form-item prop="confirmPassword">
              <el-input
                v-model="resetForm.confirmPassword"
                type="password"
                placeholder="请确认新密码"
                :prefix-icon="Lock"
                show-password
                @keyup.enter="handleResetPassword"
              />
            </el-form-item>
          </div>

          <button
            type="button"
            class="phro-btn forgot-btn forgot-module"
            :disabled="resetting"
            @click="handleResetPassword"
          >
            {{ resetting ? '重置中…' : '重置密码' }}
          </button>
        </el-form>
      </template>

      <!-- 步骤3: 成功 -->
      <template v-if="step === 3">
        <div class="success-section">
          <el-icon class="success-icon" :size="48" color="#67c23a"><CircleCheckFilled /></el-icon>
          <h3>密码重置成功</h3>
          <p>请使用新密码登录</p>
          <button
            type="button"
            class="phro-btn forgot-btn"
            @click="goToLogin"
          >
            返回登录
          </button>
        </div>
      </template>

      <div class="forgot-footer">
        <span>想起密码了？</span>
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Message, Lock, CircleCheckFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { forgotPasswordApi, resetPasswordApi } from '@/api/auth'

const router = useRouter()

const step = ref(1)
const emailFormRef = ref(null)
const resetFormRef = ref(null)
const sending = ref(false)
const resetting = ref(false)
const resetToken = ref('')

const emailForm = reactive({
  email: '',
})

const emailRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
}

const resetForm = reactive({
  new_password: '',
  confirmPassword: '',
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== resetForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const resetRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

async function handleRequestReset() {
  const valid = await emailFormRef.value.validate().catch(() => false)
  if (!valid) return

  sending.value = true
  try {
    const res = await forgotPasswordApi({ email: emailForm.email })
    // 保存令牌，跳转到设置密码步骤
    if (res.reset_token) {
      resetToken.value = res.reset_token
      step.value = 2
      ElMessage.success(res.message || '验证通过，请设置新密码')
    } else {
      ElMessage.success(res.message || '如果该邮箱已注册，重置链接已发送')
      // 没有令牌返回时，停留在步骤1
    }
  } catch {
    // 错误已在拦截器处理
  } finally {
    sending.value = false
  }
}

async function handleResetPassword() {
  const valid = await resetFormRef.value.validate().catch(() => false)
  if (!valid) return

  resetting.value = true
  try {
    await resetPasswordApi({
      token: resetToken.value,
      new_password: resetForm.new_password,
    })
    step.value = 3
    ElMessage.success('密码重置成功')
  } catch {
    // 错误已在拦截器处理
  } finally {
    resetting.value = false
  }
}

function goToLogin() {
  router.push('/login')
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.forgot-password-page {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: url('/login-bg.jpg') center / cover no-repeat fixed;
}

.forgot-card {
  width: 400px;
  max-width: calc(100vw - 40px);
  padding: 36px 40px;
  font-family: $font-family-phro;
  background: rgba(32, 6, 14, 0.42);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(212, 175, 120, 0.28);
  border-radius: $border-radius-lg;
  box-shadow: 0 12px 40px rgba(40, 0, 12, 0.35);
  box-sizing: border-box;
}

.forgot-header {
  text-align: center;
  margin-bottom: 20px;

  .forgot-logo {
    height: 52px;
    width: auto;
    max-width: 220px;
    margin-bottom: 12px;
    object-fit: contain;
    mix-blend-mode: lighten;
    filter: drop-shadow(0 2px 8px rgba(40, 6, 16, 0.4));
  }

  h2 {
    font-size: 22px;
    color: #f5e6c8;
    text-shadow: 0 2px 12px rgba(60, 8, 20, 0.75);
    margin-bottom: 6px;
  }

  p {
    font-size: 13px;
    color: #d4bca8;
    text-shadow: 0 1px 6px rgba(40, 6, 16, 0.6);
  }
}

.step-desc {
  text-align: center;
  font-size: 13px;
  color: #d4bca8;
  margin-bottom: 20px;
  text-shadow: 0 1px 4px rgba(40, 6, 16, 0.5);
  line-height: 1.5;
}

.forgot-form {
  @include phro.phro-module-stack;
  margin-bottom: 20px;
}

.forgot-module {
  @include phro.phro-module-box;
}

.forgot-field {
  padding: 4px 12px;

  :deep(.el-form-item) {
    margin-bottom: 0;
  }
}

.phro-btn {
  @include phro.phro-btn-base;
}

.forgot-btn {
  width: 100%;
  margin: 0;
  padding: 10px 14px;
  font-size: 13px;
  text-align: center;
}

.forgot-btn:disabled {
  cursor: not-allowed;
}

.forgot-footer {
  text-align: center;
  font-size: 13px;
  color: #c4a89c;
  text-shadow: 0 1px 4px rgba(40, 6, 16, 0.5);

  a {
    color: #e8b86d;
    margin-left: 4px;
    font-weight: 500;
    text-decoration: none;

    &:hover {
      color: #f5d89a;
      text-decoration: underline;
    }
  }
}

.success-section {
  text-align: center;
  padding: 20px 0;
  margin-bottom: 20px;

  .success-icon {
    margin-bottom: 16px;
  }

  h3 {
    font-size: 18px;
    color: #f5e6c8;
    margin-bottom: 8px;
  }

  p {
    font-size: 13px;
    color: #d4bca8;
    margin-bottom: 24px;
  }
}

:deep(.el-input__wrapper) {
  @include phro.phro-input-base;
  box-shadow: none !important;
  padding: 8px 12px;
  border: none;
  background: transparent !important;
}

:deep(.el-input__inner) {
  color: $phro-text-deep;
  font-family: inherit;
}

:deep(.el-input__inner::placeholder) {
  color: $phro-text-mid;
}

:deep(.el-input__prefix .el-icon) {
  color: $phro-text-warm;
}

:deep(.el-form-item__error) {
  color: #f0a090;
  font-size: 12px;
  text-shadow: 0 1px 2px rgba(40, 6, 16, 0.5);
  padding-top: 4px;
}
</style>
