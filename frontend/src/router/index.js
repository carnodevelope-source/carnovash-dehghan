import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth.store'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/auth/LoginView.vue') },
  { path: '/', name: 'operator-dashboard', component: () => import('../views/operator/DashboardView.vue'), meta: { roles: ['admin', 'owner', 'manager', 'operator', 'worker'] } },
  { path: '/accounting', name: 'accounting-dashboard', component: () => import('../views/accounting/AccountingDashboardView.vue'), meta: { roles: ['accountant', 'admin', 'manager'] } },
  { path: '/manager/reports', name: 'manager-reports', component: () => import('../views/manager/ReportsView.vue'), meta: { roles: ['manager', 'admin'] } },
  {
    path: '/manager/settings',
    name: 'manager-settings',
    component: () => import('../views/manager/SettingsView.vue'),
    meta: { roles: ['manager', 'admin'] }
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFound.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  if (!authStore.user) {
    await authStore.fetchMe()
  }

  if (to.meta?.roles?.length) {
    if (!authStore.user) return '/login'
    if (!to.meta.roles.includes(authStore.role)) {
      if (authStore.role === 'accountant') return '/accounting'
      return '/'
    }
  }
  return true
})

export default router
