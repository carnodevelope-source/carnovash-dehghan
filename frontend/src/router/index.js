import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth.store'
import { defaultRouteByRole } from '../config/navigation'
import { ATTENDANCE_ROUTE, getAttendanceUpgradeMessage, getFeatureLockNotice, hasAttendanceAccess, hasFeatureAccess } from '../utils/attendanceAccess'
import { notifyWarning } from '../utils/notify'
import { applyRouteSeo } from '../utils/seo'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/auth/LoginView.vue'),
    meta: {
      public: true,
      seo: {
        title: 'CarnoWash | ورود به سامانه مدیریت کارواش',
        description: 'ورود امن به سامانه CarnoWash برای مدیریت پذیرش خودرو، خدمات، گزارش‌ها، کیف پول و باشگاه مشتریان.',
        robots: 'index, follow',
        canonicalPath: '/login'
      }
    }
  },
  {
    path: '/attendance/:token',
    name: 'worker-attendance-public',
    component: () => import('../views/attendance/WorkerAttendancePunchView.vue'),
    meta: {
      public: true,
      seo: {
        title: 'ثبت حضور کارکنان | CarnoWash',
        description: 'صفحه اختصاصی ثبت حضور کارکنان در سامانه CarnoWash.',
        robots: 'noindex, nofollow',
        canonicalPath: '/login'
      }
    }
  },
  { path: '/hq', name: 'hq-panel', component: () => import('../views/hq/HqPanelView.vue'), meta: { hqOnly: true } },
  { path: '/', name: 'operator-dashboard', component: () => import('../views/operator/DashboardView.vue'), meta: { roles: ['admin', 'owner', 'manager', 'operator', 'worker'] } },
  { path: '/manager/wallet', name: 'manager-wallet', component: () => import('../views/manager/WalletView.vue'), meta: { roles: ['accountant', 'admin', 'owner', 'manager', 'operator', 'worker'] } },
  { path: '/manager/customer-club', name: 'manager-customer-club', component: () => import('../views/manager/CustomerClubView.vue'), meta: { roles: ['admin', 'manager'] } },
  { path: '/manager/attendance', name: 'manager-attendance', component: () => import('../views/manager/AttendanceView.vue'), meta: { roles: ['manager', 'admin', 'operator'] } },
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

const licenseSafeRoutes = new Set(['manager-wallet', 'support', 'login', 'hq-panel'])
const paidFeatureRoutes = {
  '/manager/customer-club': 'sms_club',
  '/manager/attendance': 'attendance'
}

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
    if (authStore.isLicenseLocked && !licenseSafeRoutes.has(to.name)) {
      notifyWarning(authStore.licenseStatus?.notice || 'برای ادامه استفاده باید پرداخت نرم‌افزار را تکمیل کنید.', { title: 'دسترسی قفل شده' })
      return '/manager/wallet'
    }
    if (!to.meta.roles.includes(authStore.role)) {
      return defaultRouteByRole[authStore.role] || '/'
    }
  }

  const requiredFeature = paidFeatureRoutes[to.path]
  if (requiredFeature && !hasFeatureAccess(authStore.user, requiredFeature)) {
    notifyWarning(
      getFeatureLockNotice(authStore.user, requiredFeature) || 'برای استفاده از این بخش باید آپشن مربوطه را از کیف پول خریداری یا قسط سررسید آن را پرداخت کنید.',
      { title: getFeatureLockNotice(authStore.user, requiredFeature) ? 'آپشن قفل است' : 'آپشن فعال نیست' }
    )
    return '/manager/wallet'
  }

  if (to.path === ATTENDANCE_ROUTE && !hasAttendanceAccess(authStore.user)) {
    notifyWarning(getAttendanceUpgradeMessage(), { title: 'دسترسی محدود' })
    return defaultRouteByRole[authStore.role] || '/'
  }

  if (to.path === '/' && authStore.isHq) return '/hq'

  return true
})

router.afterEach((to) => {
  applyRouteSeo(to)
})

export default router
