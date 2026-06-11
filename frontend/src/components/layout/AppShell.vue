<template>
  <div class="dashboard-page" dir="rtl">
    <header class="topbar">
      <div class="topbar-left">
        <div class="brand-wrap">
          <span class="brand">{{ tenantName }}</span>
          <span class="brand-sub">پنل مدیریت</span>
        </div>
        <div v-if="showSearch" class="search-box">
          <input
            :value="searchQuery"
            type="text"
            :placeholder="searchPlaceholder"
            @input="onSearchInput"
          />
        </div>
      </div>

      <div class="topbar-right">
        <div ref="profileMenuRef" class="profile-menu">
          <button type="button" class="profile-button" @click="toggleProfileMenu">
            <div>
              <p class="profile-name">{{ profileDisplayName }}</p>
              <p class="profile-role">{{ roleLabel }}</p>
            </div>
            <span class="profile-caret">▾</span>
          </button>

          <div v-if="isProfileMenuOpen" class="profile-dropdown">
            <button
              type="button"
              class="profile-dropdown-item"
              :disabled="isLoggingOut"
              @click="onLogoutClick"
            >
              {{ isLoggingOut ? 'در حال خروج...' : 'خروج از حساب' }}
            </button>
          </div>
        </div>
      </div>
    </header>

    <div class="layout">
      <aside class="sidebar">
        <nav>
          <RouterLink
            v-for="item in navItems"
            :key="item.route"
            class="menu-item"
            :class="{ active: isActive(item.route) }"
            :to="item.route"
            @click="onMenuItemClick(item, $event)"
          >
            <span class="menu-item-label">{{ item.label }}</span>
            <span v-if="item.route === '/manager/wallet' && walletWarning.active" class="menu-warning-badge">
              {{ walletWarning.label }}
            </span>
          </RouterLink>
        </nav>

        <div class="premium-actions">
          <button v-if="!canAccessAttendance" type="button" class="menu-item menu-button" @click="goToAttendance">ورود و خروج</button>
          <button type="button" class="menu-item menu-button" @click="showPremiumFeatureMessage">حسابداری</button>
        </div>
      </aside>

      <main class="content">
        <header class="page-head">
          <div>
            <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
            <h1>{{ title }}</h1>
          </div>

          <div class="page-actions">
            <slot name="header-actions" />
          </div>
        </header>

        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../store/auth.store'
import { navigationByRole } from '../../config/navigation'
import api from '../../services/api'
import { ATTENDANCE_ROUTE, getAttendanceUpgradeMessage, hasAttendanceAccess } from '../../utils/attendanceAccess'

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  showSearch: { type: Boolean, default: false },
  searchPlaceholder: { type: String, default: 'جستجو...' },
  searchQuery: { type: String, default: '' }
})

const emit = defineEmits(['update:searchQuery'])

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isProfileMenuOpen = ref(false)
const isLoggingOut = ref(false)
const profileMenuRef = ref(null)
const walletWarning = ref({ active: false, label: '' })

const canAccessAttendance = computed(() => hasAttendanceAccess(authStore.user))
const navItems = computed(() => (
  (navigationByRole[authStore.role] || [])
    .flatMap((group) => group.items || [])
    .filter((item) => item.route !== ATTENDANCE_ROUTE || canAccessAttendance.value)
))
const tenantName = computed(() => authStore.user?.tenant_name || 'CarWash')
const profileDisplayName = computed(() => {
  const full = String(authStore.user?.full_name || '').trim()
  if (full) return full
  const first = String(authStore.user?.first_name || '').trim()
  const last = String(authStore.user?.last_name || '').trim()
  const combined = `${first} ${last}`.trim()
  if (combined) return combined
  return authStore.user?.username || 'کاربر'
})

const roleLabel = computed(() => ({
  accountant: 'حسابدار',
  admin: 'ادمین',
  manager: 'مدیر',
  owner: 'مالک',
  operator: 'اپراتور',
  worker: 'پرسنل'
}[authStore.role] || 'کاربر'))

const isActive = (target) => {
  const normalizedTarget = String(target || '').split('?')[0]
  return route.path === normalizedTarget || route.fullPath === target
}

const onSearchInput = (event) => {
  emit('update:searchQuery', event?.target?.value || '')
}

const showPremiumFeatureMessage = () => {
  alert('برای فعال‌سازی این قابلیت باید اشتراک ویژه را خریداری کنید.')
}

const showAttendanceAccessMessage = () => {
  alert(getAttendanceUpgradeMessage())
}

const onMenuItemClick = (item, event) => {
  if (item?.route !== ATTENDANCE_ROUTE) return
  if (canAccessAttendance.value) return
  event?.preventDefault?.()
  showAttendanceAccessMessage()
}

const goToAttendance = () => {
  if (canAccessAttendance.value) {
    router.push(ATTENDANCE_ROUTE)
    return
  }
  showAttendanceAccessMessage()
}

const toggleProfileMenu = () => {
  isProfileMenuOpen.value = !isProfileMenuOpen.value
}

const closeProfileMenu = () => {
  isProfileMenuOpen.value = false
}

const onDocumentClick = (event) => {
  if (!profileMenuRef.value) return
  if (profileMenuRef.value.contains(event.target)) return
  closeProfileMenu()
}

const onLogoutClick = async () => {
  if (isLoggingOut.value) return
  isLoggingOut.value = true
  try {
    await authStore.logout()
    closeProfileMenu()
    await router.push('/login')
  } finally {
    isLoggingOut.value = false
  }
}

const loadWalletWarning = async () => {
  if (!['admin', 'manager', 'accountant'].includes(authStore.role)) return
  try {
    const { data } = await api.get('/payments/wallet/dashboard/')
    const regularBalance = Number(data?.summary?.regular_balance || 0)
    const smsBalance = Number(data?.summary?.sms_balance || 0)
    const regularLow = regularBalance <= 100000
    const smsLow = smsBalance <= 50000
    walletWarning.value = {
      active: regularLow || smsLow,
      label: regularLow && smsLow ? 'کمبود موجودی' : regularLow ? 'موجودی کم' : 'شارژ پیامک کم'
    }
  } catch (_error) {
    walletWarning.value = { active: false, label: '' }
  }
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  loadWalletWarning()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
})
</script>

<style scoped>
.dashboard-page {
  min-height: 100vh;
  background: #f7f9fb;
  color: #191c1e;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  height: 64px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #e3e6ed;
}

.topbar-left,
.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand {
  color: #0058be;
  font-weight: 700;
}
.brand-wrap { display: flex; align-items: center; gap: 8px; }
.brand-sub { font-size: 12px; color: #64748b; border-right: 1px solid #cbd5e1; padding-right: 8px; }

.search-box input {
  width: 260px;
  height: 40px;
  border: none;
  border-radius: 12px;
  background: #f2f4f6;
  padding: 0 12px;
}

.search-box input:focus {
  outline: 2px solid #0058be;
}

.profile-menu {
  position: relative;
}

.profile-button {
  height: 44px;
  border: 1px solid #e3e6ed;
  border-radius: 12px;
  background: #fff;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  cursor: pointer;
}

.profile-caret {
  color: #64748b;
  font-size: 12px;
}

.profile-dropdown {
  position: absolute;
  left: 0;
  top: calc(100% + 8px);
  min-width: 180px;
  background: #fff;
  border: 1px solid #e3e6ed;
  border-radius: 12px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.1);
  padding: 6px;
}

.profile-dropdown-item {
  width: 100%;
  height: 38px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  text-align: right;
  padding: 0 10px;
  font: inherit;
  color: #334155;
  cursor: pointer;
}

.profile-dropdown-item:hover {
  background: #f1f5f9;
}

.profile-dropdown-item:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.profile-name {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.profile-role {
  margin: 3px 0 0;
  font-size: 11px;
  color: #64748b;
}

.layout {
  display: flex;
}

.sidebar {
  width: 240px;
  min-height: calc(100vh - 64px);
  padding: 24px 12px;
  background: #f2f4f6;
  border-left: 1px solid #e3e6ed;
}

.sidebar nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 12px;
  text-decoration: none;
  color: #475569;
  font-weight: 600;
}
.menu-item-label { display: inline-flex; align-items: center; }
.menu-warning-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
  font-size: 11px;
  font-weight: 700;
}

.menu-item.active {
  background: #dbeafe;
  color: #0058be;
}

.premium-actions {
  margin-top: 10px;
  display: grid;
  gap: 4px;
}

.menu-button {
  width: 100%;
  border: 0;
  background: transparent;
  text-align: right;
  font: inherit;
  cursor: pointer;
}

.content {
  flex: 1;
  padding: 24px;
}

.page-head {
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.page-head h1 {
  margin: 0;
  font-size: 24px;
  color: #0f172a;
}

.page-subtitle {
  margin: 0 0 6px;
  color: #64748b;
  font-size: 12px;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 768px) {
  .topbar {
    padding: 0 12px;
  }

  .search-box input {
    width: 170px;
  }

  .layout {
    flex-direction: row;
  }

  .sidebar {
    width: 170px;
    padding: 14px 8px;
    min-height: calc(100vh - 64px);
  }

  .menu-item {
    padding: 10px 10px;
    font-size: 13px;
  }

  .profile-button {
    padding: 0 8px;
    gap: 8px;
  }

  .content {
    padding: 12px;
  }
}
</style>
