/**
 * 应用入口文件
 * - 创建 Vue 应用实例
 * - 注册全局插件（Element Plus、Router、Pinia）
 * - 挂载应用
 */
import { createApp } from 'vue'

import '@/assets/styles/global.scss'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import pinia from './stores'
import { setupErrorReporting } from '@/utils/errorReporter'

const app = createApp(App)

setupErrorReporting(app)

app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
