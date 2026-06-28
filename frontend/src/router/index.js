import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth.store'
import { defaultRouteByRole } from '../config/navigation'
import { ATTENDANCE_ROUTE, getAttendanceUpgradeMessage, hasAttendanceAccess } from '../utils/attendanceAccess'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/auth/LoginView.vue'), meta: { public: true } },
  { path: '/attendance/:token', name: 'worker-attendance-public', component: () => import('../views/attendance/WorkerAttendancePunchView.vue'), meta: { public: true } },
  { path: '/hq', name: 'hq-panel', component: () => import('../views/hq/HqPanelView.vue'), meta: { hqOnly: true } },
  { path: '/', name: 'operator-dashboard', component: () => import('../views/operator/DashboardView.vue'), meta: { roles: ['admin', 'owner', 'manager', 'operator', 'worker'] } },
  { path: '/manager/wallet', name: 'manager-wallet', component: () => import('../views/manager/WalletView.vue'), meta: { roles: ['accountant', 'admin', 'manager'] } },
  { path: '/manager/customer-club', name: 'manager-customer-club', component: () => import('../views/manager/CustomerClubView.vue'), meta: { roles: ['admin', 'manager'] } },
  { path: '/manager/attendance', name: 'manager-attendance', component: () => import('../views/manager/AttendanceView.vue'), meta: { roles: ['manager', 'admin'] } },
  { path: '/manager/reports', name: 'manager-reports', component: () => import('../views/manager/ReportsView.vue'), meta: { roles: ['manager', 'admin'] } },
  { path: '/support', name: 'support', component: () => import('../views/support/SupportView.vue'), meta: { roles: ['accountant', 'admin', 'owner', 'manager', 'operator', 'worker'] } },
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

  if (to.path === '/login') {
    if (!authStore.user) {
      await authStore.fetchMe()
    }
    if (authStore.user) {
      if (authStore.isHq) return '/hq'
      return defaultRouteByRole[authStore.role] || '/'
    }
    return true
  }

  if (to.meta?.public) {
    return true
  }

  if (!authStore.user) {
    await authStore.fetchMe()
  }

  if (to.meta?.hqOnly) {
    if (!authStore.user) return '/login'
    if (!authStore.isHq) return defaultRouteByRole[authStore.role] || '/'
    return true
  }

  if (to.meta?.roles?.length) {
    if (!authStore.user) return '/login'
    if (authStore.isHq) return '/hq'
    if (!to.meta.roles.includes(authStore.role)) {
      return defaultRouteByRole[authStore.role] || '/'
    }
  }

  if (to.path === ATTENDANCE_ROUTE && !hasAttendanceAccess(authStore.user)) {
    if (typeof window !== 'undefined') window.alert(getAttendanceUpgradeMessage())
    return defaultRouteByRole[authStore.role] || '/'
  }

  if (to.path === '/' && authStore.isHq) return '/hq'

  return true
})

export default router
