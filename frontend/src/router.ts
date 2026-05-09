import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from './stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'landing',
    component: () => import('./pages/LandingPage.vue')
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
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('./pages/DashboardPage.vue')
      },
      {
        path: 'new',
        name: 'new-analysis',
        component: () => import('./pages/NewAnalysisPage.vue')
      },
      {
        path: 'report/:runId',
        name: 'report',
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
        component: () => import('./pages/AccountPage.vue')
      },
      {
        path: 'rewrite/:runId',
        name: 'rewrite',
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

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
