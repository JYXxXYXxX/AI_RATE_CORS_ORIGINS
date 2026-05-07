import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'element-plus/es/components/message/style/css'
import './styles.css'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

// 全局错误边界：捕获 Vue 组件渲染错误
app.config.errorHandler = (err, vm, info) => {
  console.error('[Vue Error]', err, info)
  // 可在此接入 Sentry 等监控服务
}

// 捕获未处理的 Promise 拒绝
window.addEventListener('unhandledrejection', (event) => {
  console.error('[Unhandled Promise]', event.reason)
  // 可在此接入监控服务
})

// 初始化认证状态后再挂载路由和应用，确保路由守卫能读到正确的登录态
const auth = useAuthStore()
auth.init().finally(() => {
  app.use(router)
  app.mount('#app')
})
