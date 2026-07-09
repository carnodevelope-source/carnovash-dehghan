<template>
  <div class="dashboard-page" dir="rtl">
    <header ref="topbarRef" class="topbar">
      <div class="topbar-left">
        <button
          type="button"
          class="mobile-menu-toggle"
          :class="{ open: isMobileMenuOpen }"
          :aria-expanded="isMobileMenuOpen"
          aria-label="باز کردن منو"
          @click="toggleMobileMenu"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>
        <div class="brand-wrap">
          <span class="brand-mark">
            <IconlyIcon :name="currentPageIconName || 'home'" size="sm" />
          </span>
          <span class="brand">{{ tenantName }}</span>
          <span class="brand-sub">پنل مدیریت</span>
        </div>
        <div v-if="showSearch" class="search-box">
          <span class="search-box-icon">
            <IconlyIcon name="search" size="sm" />
          </span>
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
            <span class="profile-button-icon">
              <IconlyIcon name="profile" size="sm" />
            </span>
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
              <IconlyIcon name="logout" size="sm" />
              {{ isLoggingOut ? 'در حال خروج...' : 'خروج از حساب' }}
            </button>
          </div>
        </div>
      </div>
    </header>

    <div class="layout">
      <div
        v-if="isMobileMenuOpen"
        class="mobile-sidebar-overlay"
        :style="mobileShellStyle"
        @click="closeMobileMenu"
      ></div>

      <aside
        class="sidebar"
        :class="{ 'mobile-open': isMobileMenuOpen }"
        :style="mobileShellStyle"
      >
        <div class="mobile-sidebar-head">
          <div class="mobile-sidebar-brand">
            <strong>{{ tenantName }}</strong>
            <span>{{ roleLabel }}</span>
          </div>
          <button
            type="button"
            class="mobile-sidebar-close"
            aria-label="بستن منو"
            @click="closeMobileMenu"
          >
            ✕
          </button>
        </div>

        <div class="mobile-sidebar-login-art" aria-hidden="true">
          <img :src="mobileLoginArtSrc" alt="" />
        </div>

        <nav>
          <RouterLink
            v-for="item in navItems"
            :key="item.route"
            class="menu-item"
            :class="{ active: isActive(item.route) }"
            :to="item.route"
            @click="onMenuItemClick(item, $event)"
          >
            <span class="menu-item-icon-wrap">
              <IconlyIcon v-if="item.iconName" :name="item.iconName" size="sm" class="menu-item-icon" />
            </span>
            <span class="menu-item-label">{{ item.label }}</span>
            <span v-if="item.route === '/manager/wallet' && walletWarning.active" class="menu-warning-badge">
              {{ walletWarning.label }}
            </span>
          </RouterLink>
        </nav>

        <div class="premium-actions">
          <button v-if="!canAccessAttendance" type="button" class="menu-item menu-button" @click="goToAttendance">
            <span class="menu-item-icon-wrap"><IconlyIcon name="calendar" size="sm" /></span>
            <span class="menu-item-label">ورود و خروج</span>
          </button>
          <button type="button" class="menu-item menu-button" @click="showPremiumFeatureMessage">
            <span class="menu-item-icon-wrap"><IconlyIcon name="graph" size="sm" /></span>
            <span class="menu-item-label">حسابداری</span>
          </button>
        </div>
      </aside>

      <main class="content">
        <section v-if="walletWarning.smsZero" class="global-sms-warning">
          <strong>هشدار پیامک</strong>
          <span>موجودی کیف پول پیامک صفر است و هیچ پیامکی ارسال نخواهد شد.</span>
        </section>

        <header v-if="!hidePageHeader" class="page-head">
          <div class="page-title-wrap">
            <span class="page-title-icon">
              <IconlyIcon :name="currentPageIconName || 'home'" size="md" />
            </span>
            <div>
            <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
            <h1>{{ title }}</h1>
            </div>
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../store/auth.store'
import { navigationByRole, navigationRouteMeta } from '../../config/navigation'
import api from '../../services/api'
import { ATTENDANCE_ROUTE, getAttendanceUpgradeMessage, hasAttendanceAccess } from '../../utils/attendanceAccess'
import { notifyWarning } from '../../utils/notify'
import IconlyIcon from '../base/IconlyIcon.vue'

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  hidePageHeader: { type: Boolean, default: false },
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
const walletWarning = ref({ active: false, label: '', smsZero: false })
const isMobileMenuOpen = ref(false)
const topbarRef = ref(null)
const topbarHeight = ref(64)
const mobileLoginArtSrc = `${import.meta.env.BASE_URL}e5eb861941aac79bcfd5d1fdabf1d569.jpg`

const canAccessAttendance = computed(() => hasAttendanceAccess(authStore.user))
const navItems = computed(() => (
  (navigationByRole[authStore.role] || [])
    .flatMap((group) => group.items || [])
    .filter((item) => item.route !== ATTENDANCE_ROUTE || canAccessAttendance.value)
))
const mobileShellStyle = computed(() => ({
  '--mobile-topbar-offset': `${topbarHeight.value}px`
}))
const currentPageIconName = computed(() => {
  const routeKey = Object.keys(navigationRouteMeta)
    .sort((a, b) => b.length - a.length)
    .find((path) => route.path === path || (path !== '/' && route.path.startsWith(path)))
  return routeKey ? navigationRouteMeta[routeKey]?.iconName || '' : ''
})
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
  notifyWarning('برای فعال‌سازی این قابلیت باید اشتراک ویژه را خریداری کنید.', {
    title: 'اشتراک ویژه'
  })
}

const showAttendanceAccessMessage = () => {
  notifyWarning(getAttendanceUpgradeMessage(), {
    title: 'دسترسی حضور و غیاب'
  })
}

const onMenuItemClick = (item, event) => {
  if (item?.route === ATTENDANCE_ROUTE && !canAccessAttendance.value) {
    event?.preventDefault?.()
    showAttendanceAccessMessage()
    return
  }
  closeMobileMenu()
}

const goToAttendance = () => {
  if (canAccessAttendance.value) {
    closeMobileMenu()
    router.push(ATTENDANCE_ROUTE)
    return
  }
  showAttendanceAccessMessage()
}

const toggleMobileMenu = () => {
  closeProfileMenu()
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

const closeMobileMenu = () => {
  isMobileMenuOpen.value = false
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

const syncTopbarHeight = () => {
  topbarHeight.value = Math.max(64, Math.round(topbarRef.value?.offsetHeight || 64))
}

const syncBodyScroll = () => {
  document.body.classList.toggle('mobile-menu-open', isMobileMenuOpen.value)
}

const onWindowResize = () => {
  syncTopbarHeight()
  if (window.innerWidth > 900) closeMobileMenu()
}

const onWindowKeydown = (event) => {
  if (event.key === 'Escape') {
    closeMobileMenu()
    closeProfileMenu()
  }
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
    const smsZero = smsBalance <= 0
    walletWarning.value = {
      active: regularLow || smsLow,
      label: regularLow && smsLow ? 'کمبود موجودی' : regularLow ? 'موجودی کم' : 'شارژ پیامک کم',
      smsZero
    }
  } catch (_error) {
    walletWarning.value = { active: false, label: '', smsZero: false }
  }
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  window.addEventListener('resize', onWindowResize)
  window.addEventListener('keydown', onWindowKeydown)
  syncTopbarHeight()
  syncBodyScroll()
  loadWalletWarning()
})

watch(() => route.fullPath, () => {
  closeMobileMenu()
  closeProfileMenu()
})

watch(isMobileMenuOpen, () => {
  syncBodyScroll()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  window.removeEventListener('resize', onWindowResize)
  window.removeEventListener('keydown', onWindowKeydown)
  document.body.classList.remove('mobile-menu-open')
})
</script>

<style scoped>
.dashboard-page {
  min-height: 100vh;
  width: 100%;
  max-width: 100%;
  background: #f7f9fb;
  color: #191c1e;
  overflow-x: hidden;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  height: 64px;
  width: 100%;
  max-width: 100%;
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
  min-width: 0;
}
.topbar-left {
  flex: 1 1 auto;
}
.topbar-right {
  flex: 0 0 auto;
}

.brand {
  color: #0058be;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.brand-mark {
  width: 26px;
  height: 26px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #e8f1ff, #dbeafe);
  flex: 0 0 auto;
  --iconly-filter: brightness(0) saturate(100%) invert(31%) sepia(73%) saturate(1584%) hue-rotate(201deg) brightness(96%) contrast(98%);
}
.mobile-menu-toggle {
  display: none;
  width: 40px;
  height: 40px;
  border: 1px solid #d8e0ea;
  border-radius: 12px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  cursor: pointer;
  flex-shrink: 0;
  padding: 0;
  align-items: center;
  justify-content: center;
  gap: 4px;
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.mobile-menu-toggle span {
  display: block;
  width: 18px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.mobile-menu-toggle.open {
  border-color: #93c5fd;
  background: #eff6ff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.mobile-menu-toggle.open span:nth-child(1) {
  transform: translateY(6px) rotate(45deg);
}

.mobile-menu-toggle.open span:nth-child(2) {
  opacity: 0;
}

.mobile-menu-toggle.open span:nth-child(3) {
  transform: translateY(-6px) rotate(-45deg);
}
.brand-wrap { display: flex; align-items: center; gap: 8px; min-width: 0; }
.brand-sub { font-size: 12px; color: #64748b; border-right: 1px solid #cbd5e1; padding-right: 8px; }
.search-box { flex: 1 1 0; min-width: 0; position: relative; }
.search-box-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #64748b;
  pointer-events: none;
  --iconly-filter: brightness(0) saturate(100%) invert(48%) sepia(15%) saturate(909%) hue-rotate(176deg) brightness(90%) contrast(86%);
}

.search-box input {
  width: 100%;
  max-width: 100%;
  height: 40px;
  border: none;
  border-radius: 12px;
  background: #f2f4f6;
  padding: 0 38px 0 12px;
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
  min-width: 0;
}
.profile-button-icon {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: #eff6ff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  flex: 0 0 auto;
  --iconly-filter: brightness(0) saturate(100%) invert(31%) sepia(73%) saturate(1584%) hue-rotate(201deg) brightness(96%) contrast(98%);
}
.profile-button > div {
  min-width: 0;
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
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.profile-role {
  margin: 3px 0 0;
  font-size: 11px;
  color: #64748b;
}

.layout {
  display: flex;
  align-items: flex-start;
  min-width: 0;
  position: relative;
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
}

.sidebar {
  flex-shrink: 0;
  width: 240px;
  min-height: calc(100vh - 64px);
  padding: 24px 12px;
  background: #f2f4f6;
  border-left: 1px solid #e3e6ed;
  transition: transform 0.22s ease, opacity 0.22s ease;
}

.mobile-sidebar-head {
  display: none;
}

.mobile-sidebar-brand {
  display: grid;
  gap: 3px;
}

.mobile-sidebar-brand strong {
  color: #0f172a;
  font-size: 15px;
}

.mobile-sidebar-brand span {
  color: #64748b;
  font-size: 12px;
}

.mobile-sidebar-close {
  width: 40px;
  height: 40px;
  border: 1px solid #d8e0ea;
  border-radius: 12px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  font-size: 16px;
  cursor: pointer;
}

.mobile-sidebar-login-art {
  display: none;
}

.mobile-sidebar-login-art img {
  display: block;
  width: 100%;
  height: 172px;
  object-fit: cover;
  border-radius: 20px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.14);
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
.menu-item-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  --iconly-filter: brightness(0) saturate(100%) invert(40%) sepia(20%) saturate(899%) hue-rotate(177deg) brightness(92%) contrast(88%);
}
.menu-item-icon { opacity: 0.9; }
.menu-item-label { display: inline-flex; align-items: center; flex: 1; min-width: 0; }
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

.menu-item.active .menu-item-icon-wrap {
  background: #eff6ff;
  border-color: #bfdbfe;
  --iconly-filter: brightness(0) saturate(100%) invert(28%) sepia(88%) saturate(1449%) hue-rotate(205deg) brightness(99%) contrast(96%);
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
  min-width: 0;
  max-width: 100%;
  padding: 24px;
  overflow-x: hidden;
}

.global-sms-warning {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding: 14px 16px;
  border: 1px solid #fdba74;
  border-radius: 16px;
  background: linear-gradient(180deg, #fff7ed, #ffedd5);
  color: #9a3412;
}

.global-sms-warning strong {
  flex: 0 0 auto;
  font-size: 13px;
  font-weight: 800;
}

.global-sms-warning span {
  font-size: 13px;
  line-height: 1.8;
}

.mobile-sidebar-overlay {
  display: none;
}

.page-head {
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.page-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff, #eff6ff);
  border: 1px solid #dbeafe;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.08);
  flex: 0 0 auto;
  --iconly-filter: brightness(0) saturate(100%) invert(31%) sepia(73%) saturate(1584%) hue-rotate(201deg) brightness(96%) contrast(98%);
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
  flex-wrap: wrap;
  justify-content: flex-end;
  min-width: 0;
}

@media (max-width: 1024px) {
  .topbar {
    height: auto;
    padding: 12px 16px;
    flex-wrap: nowrap;
    gap: 10px;
  }

  .topbar-left,
  .topbar-right {
    width: auto;
  }

  .topbar-left {
    flex-wrap: nowrap;
    flex: 1 1 auto;
    justify-content: flex-start;
    gap: 10px;
  }

  .search-box {
    width: auto;
    order: 0;
    flex: 1 1 0;
    flex-basis: auto;
    min-width: 0;
  }

  .search-box input {
    width: 100%;
  }

  .page-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .page-title-wrap {
    width: 100%;
  }

  .page-actions {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 900px) {
  .layout {
    display: block;
  }

  .mobile-menu-toggle {
    display: inline-grid;
    place-items: center;
  }

  .sidebar {
    display: none;
    position: fixed;
    top: 0;
    right: 0;
    left: 0;
    width: auto;
    max-width: none;
    min-height: 0;
    height: 100dvh;
    padding: calc(var(--mobile-topbar-offset, 64px) + 10px) 12px 16px;
    margin-top: 0;
    border-left: 1px solid #e3e6ed;
    border-bottom: 0;
    border-radius: 0;
    box-shadow: 0 22px 50px rgba(15, 23, 42, 0.16);
    z-index: 30;
    overflow: auto;
    overflow-x: hidden;
    background: rgba(242, 244, 246, 0.98);
    backdrop-filter: blur(12px);
  }

  .mobile-sidebar-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 0 2px 12px;
    margin-bottom: 12px;
    border-bottom: 1px solid rgba(203, 213, 225, 0.7);
  }

  .mobile-sidebar-login-art {
    display: block;
    margin: 0 0 14px;
  }

  .sidebar nav,
  .premium-actions {
    display: grid;
    gap: 8px;
    overflow: visible;
    padding-bottom: 0;
  }

  .menu-item,
  .menu-button {
    flex: unset;
    white-space: normal;
  }

  .sidebar.mobile-open {
    display: block;
  }

  .mobile-sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.28);
    z-index: 25;
  }
}

@media (max-width: 768px) {
  .topbar {
    padding: 10px 12px;
  }

  .sidebar {
    padding: 10px;
  }

  .mobile-sidebar-login-art img {
    height: 150px;
    border-radius: 18px;
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

  .global-sms-warning {
    align-items: flex-start;
    padding: 12px 14px;
  }

  .brand-wrap {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 72px;
    max-width: 110px;
  }

  .brand {
    font-size: 12px;
  }

  .brand-sub {
    display: none;
  }

  .profile-button {
    width: auto;
    min-width: 0;
    justify-content: space-between;
    height: 38px;
  }

  .profile-name {
    font-size: 11px;
  }

  .profile-role {
    font-size: 9px;
    margin-top: 1px;
  }

  .search-box input {
    height: 38px;
    padding: 0 34px 0 10px;
    font-size: 12px;
  }

  .page-head h1 {
    font-size: 20px;
  }

  .page-subtitle {
    font-size: 11px;
  }
}

@media (max-width: 480px) {
  .topbar-left,
  .topbar-right {
    gap: 6px;
  }

  .profile-button {
    padding: 0 8px;
    gap: 6px;
  }

  .profile-name {
    font-size: 10px;
  }

  .profile-role {
    display: none;
  }

  .search-box input,
  .profile-button {
    height: 36px;
  }

  .mobile-menu-toggle {
    width: 36px;
    height: 36px;
    border-radius: 10px;
  }

  .mobile-menu-toggle span {
    width: 16px;
  }

  .brand-wrap {
    min-width: 58px;
    max-width: 82px;
  }

  .brand {
    font-size: 11px;
  }

  .search-box input {
    font-size: 11px;
    padding: 0 9px;
  }

  .profile-caret {
    display: none;
  }

  .page-title-icon {
    width: 38px;
    height: 38px;
    border-radius: 12px;
  }

  .content {
    padding: 10px;
  }

  .global-sms-warning {
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
  }

  .sidebar {
    width: auto;
    max-width: none;
    padding: calc(var(--mobile-topbar-offset, 64px) + 8px) 10px 14px;
  }

  .mobile-sidebar-login-art {
    margin-bottom: 12px;
  }

  .mobile-sidebar-login-art img {
    height: 132px;
    border-radius: 16px;
  }

  .menu-item {
    padding: 10px 12px;
    font-size: 12px;
  }

  .page-head {
    gap: 10px;
  }

  .page-head h1 {
    font-size: 18px;
  }
}
</style>
