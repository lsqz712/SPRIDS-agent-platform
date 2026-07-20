<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <img src="/logo.webp" alt="logo" class="login-logo" />
        <h2>Phrolova Agent Platform</h2>
        <p>弗洛洛智能体平台</p>
      </div>

      <el-form
        ref="formRef"
        class="login-form"
        :model="loginForm"
        :rules="loginRules"
        label-width="0"
        size="large"
        @submit.prevent="handleLogin"
      >
        <div class="login-field login-module">
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
            />
          </el-form-item>
        </div>

        <div class="login-field login-module">
          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>
        </div>

        <button
          type="button"
          class="phro-btn login-btn login-module"
          :disabled="loading"
          @click="handleLogin"
        >
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </el-form>

      <div class="login-footer">
        <span>还没有账号？</span>
        <router-link to="/register">立即注册</router-link>
      </div>
    </div>

    <button
      v-if="isDev"
      type="button"
      class="dev-preview-btn"
      @click="enterDevPreview"
    >
      预览内页
    </button>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const isDev = import.meta.env.DEV

const loginForm = reactive({
  username: '',
  password: '',
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为 3-50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' },
  ],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await userStore.login({
      username: loginForm.username,
      password: loginForm.password,
    })
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch {
    // 错误已在 Axios 拦截器中统一处理
  } finally {
    loading.value = false
  }
}

function enterDevPreview() {
  const mockUser = {
    username: '漂泊者',
    avatar: '',
    roles: [],
    is_superuser: true,
  }

  userStore.$patch({
    token: 'dev-preview',
    user: mockUser,
  })
  localStorage.setItem('rsod_token', 'dev-preview')
  localStorage.setItem('rsod_user', JSON.stringify(mockUser))

  router.push(route.query.redirect || '/chat')
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/phro-theme.scss' as phro;

.login-page {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: url('/login-bg.jpg') center / cover no-repeat fixed;
}

.login-card {
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

.login-header {
  text-align: center;
  margin-bottom: 28px;

  .login-logo {
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

.login-form {
  @include phro.phro-module-stack;
  margin-bottom: 20px;
}

.login-module {
  @include phro.phro-module-box;
}

.login-field {
  padding: 4px 12px;
  cursor: text;

  :deep(.el-form-item) {
    margin-bottom: 0;
  }
}

.phro-btn {
  @include phro.phro-btn-base;
}

.login-btn {
  width: 100%;
  margin: 0;
  padding: 10px 14px;
  font-size: 13px;
  text-align: center;
}

.login-btn:disabled {
  cursor: not-allowed;
}

.login-footer {
  text-align: center;
  font-size: 13px;
  color: #c4a89c;
  text-shadow: 0 1px 4px rgba(40, 6, 16, 0.5);

  a {
    color: #e8b86d;
    margin-left: 4px;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;

    &:hover {
      color: #f5d89a;
      text-decoration: underline;
    }
  }
}

:deep(.el-input),
:deep(.el-input__wrapper),
:deep(.el-input__prefix),
:deep(.el-input__prefix-inner) {
  cursor: text;
}

:deep(.el-input__inner) {
  color: $phro-text-deep;
  font-family: inherit;
  cursor: text;
}

:deep(.el-input__suffix),
:deep(.el-input__suffix-inner),
:deep(.el-input__password) {
  cursor: pointer;
}

:deep(.el-input__prefix .el-icon),
:deep(.el-input__prefix-inner .el-icon),
:deep(.el-input__prefix .el-input__icon),
:deep(.el-input__prefix-inner .el-input__icon) {
  cursor: text;
  pointer-events: none;
}

:deep(.el-input__wrapper) {
  @include phro.phro-input-base;
  box-shadow: none !important;
  padding: 8px 12px;
  border: none;
  background: transparent !important;
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

.dev-preview-btn {
  position: fixed;
  right: 20px;
  bottom: 20px;
  padding: 6px 14px;
  font-size: 12px;
  font-family: $font-family-phro;
  color: rgba(245, 230, 200, 0.85);
  background: rgba(32, 6, 14, 0.55);
  border: 1px solid rgba(212, 175, 120, 0.35);
  border-radius: 16px;
  cursor: pointer;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  transition: all 0.2s;

  &:hover {
    color: #f5e6c8;
    background: rgba(32, 6, 14, 0.72);
    border-color: rgba(232, 184, 109, 0.55);
  }
}
</style>
