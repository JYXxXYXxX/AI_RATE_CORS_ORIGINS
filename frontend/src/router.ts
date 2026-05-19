import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from './stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'landing',
    redirect: '/app'
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('./pages/LoginPage.vue')
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('./pages/RegisterPage.vue')
  },
  {
    path: '/app',
    component: () => import('./layouts/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'app-home',
        component: () => import('./pages/AppHomePage.vue')
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        meta: { requiresAuth: true },
        component: () => import('./pages/DashboardPage.vue')
      },
      {
        path: 'new',
        name: 'new-analysis',
        meta: { requiresAuth: true },
        component: () => import('./pages/NewAnalysisPage.vue')
      },
      {
        path: 'report/:runId',
        name: 'report',
        meta: { requiresAuth: true },
        component: () => import('./pages/ReportPage.vue'),
        props: true
      },
      {
        path: 'report/:runId/print',
        name: 'report-print',
        component: () => import('./pages/PrintReportPage.vue'),
        props: true
      },
      {
        path: 'account',
        name: 'account',
        meta: { requiresAuth: true },
        component: () => import('./pages/AccountPage.vue')
      },
      {
        path: 'rewrite/:runId',
        name: 'rewrite',
        meta: { requiresAuth: true },
        component: () => import('./pages/RewritePage.vue'),
        props: true
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router
