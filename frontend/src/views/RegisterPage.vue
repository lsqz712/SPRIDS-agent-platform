<template>
  <div class="register-page">
    <div class="register-card">
      <div class="register-header">
        <img src="/logo.webp" alt="logo" class="register-logo" />
        <h2>Phrolova Agent Platform</h2>
        <p>弗洛洛智能体平台</p>
      </div>

      <el-form
        ref="formRef"
        class="register-form"
        :model="registerForm"
        :rules="registerRules"
        label-width="0"
        size="large"
        @submit.prevent="handleRegister"
      >
        <div class="register-field register-module">
          <el-form-item prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
            />
          </el-form-item>
        </div>

        <div class="register-field register-module">
          <el-form-item prop="email">
            <el-input
              v-model="registerForm.email"
              placeholder="请输入邮箱"
              :prefix-icon="Message"
            />
          </el-form-item>
        </div>

        <div class="register-field register-module">
          <el-form-item prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码（至少 6 位）"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
        </div>

        <div class="register-field register-module">
          <el-form-item prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="请确认密码"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="handleRegister"
            />
          </el-form-item>
        </div>

        <button
          type="button"
          class="phro-btn register-btn register-module"
          :disabled="loading"
          @click="handleRegister"
        >
          {{ loading ? '注册中…' : '注 册' }}
        </button>
      </el-form>

      <div class="register-footer">
        <span>已有账号？</span>
        <router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { registerApi } from '@/api/auth'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为 3-50 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await registerApi({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch {
    // 错误已在 Axios 拦截器中统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.register-page {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: url('/login-bg.jpg') center / cover no-repeat fixed;
}

.register-card {
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

.register-header {
  text-align: center;
  margin-bottom: 28px;

  .register-logo {
    height: 52px;
    width: auto;
    max-width: 220px;
    margin-bottom: 16px;
    object-fit: contain;
    mix-blend-mode: lighten;
    filter: drop-shadow(0 2px 8px rgba(40, 6, 16, 0.4));
  }

  h2 {
    font-size: 22px;
    color: #f5e6c8;
    text-shadow: 0 2px 12px rgba(60, 8, 20, 0.75);
    margin-bottom: 8px;
  }

  p {
    font-size: 13px;
    color: #d4bca8;
    text-shadow: 0 1px 6px rgba(40, 6, 16, 0.6);
  }
}

.register-form {
  @include phro.phro-module-stack;
  margin-bottom: 20px;
}

.register-module {
  @include phro.phro-module-box;
}

.register-field {
  padding: 4px 12px;

  :deep(.el-form-item) {
    margin-bottom: 0;
  }
}

.phro-btn {
  @include phro.phro-btn-base;
}

.register-btn {
  width: 100%;
  margin: 0;
  padding: 10px 14px;
  font-size: 13px;
  text-align: center;
}

.register-footer {
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
