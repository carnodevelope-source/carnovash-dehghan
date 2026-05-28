<template>
  <div class="app-shell" dir="rtl">
    <aside class="sidebar">
      <div class="brand-box">
        <span class="brand-kicker">CarWash Suite</span>
        <strong>{{ title }}</strong>
      </div>
      <nav class="nav-groups">
        <section v-for="group in groups" :key="group.key" class="nav-group">
          <p class="group-title">{{ group.label }}</p>
          <RouterLink
            v-for="item in group.items"
            :key="item.route"
            class="nav-item"
            :class="{ active: isActive(item.route) }"
            :to="item.route"
          >
            {{ item.label }}
          </RouterLink>
        </section>
      </nav>
    </aside>

    <div class="shell-main">
      <header class="shell-header">
        <div>
          <p class="eyebrow">{{ eyebrow }}</p>
          <h1>{{ title }}</h1>
        </div>
        <div class="header-right">
          <slot name="header-actions" />
          <div class="profile-chip">
            <span>{{ authStore.user?.full_name || authStore.user?.username || 'کاربر' }}</span>
            <small>{{ roleLabel }}</small>
          </div>
        </div>
      </header>
      <main class="shell-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '../../store/auth.store'
import { navigationByRole } from '../../config/navigation'

const props = defineProps({
  title: { type: String, required: true },
  eyebrow: { type: String, default: '' }
})

const route = useRoute()
const authStore = useAuthStore()

const groups = computed(() => navigationByRole[authStore.role] || [])
const roleLabel = computed(() => ({
  accountant: 'حسابدار',
  admin: 'مدیر سیستم',
  manager: 'مدیر',
  owner: 'مالک',
  operator: 'اپراتور',
  worker: 'نیرو'
}[authStore.role] || 'کاربر'))

const isActive = (target) => route.fullPath === target || route.path === target.split('?')[0]
</script>

<style scoped>
.app-shell { min-height: 100vh; display: grid; grid-template-columns: 290px 1fr; background:
  radial-gradient(circle at top right, rgba(34, 197, 94, 0.10), transparent 20%),
  linear-gradient(180deg, #f7f7f2 0%, #eef2ea 100%); color: #142013; font-family: Vazirmatn, sans-serif; }
.sidebar { padding: 24px 18px; border-left: 1px solid rgba(20, 32, 19, 0.08); background:
  linear-gradient(180deg, rgba(13, 44, 28, 0.96), rgba(25, 69, 43, 0.94)); color: #f3f8f1; }
.brand-box { padding: 18px; border-radius: 20px; background: rgba(255, 255, 255, 0.06); box-shadow: inset 0 1px 0 rgba(255,255,255,0.08); }
.brand-box strong { display: block; margin-top: 6px; font-size: 22px; }
.brand-kicker { font-size: 12px; letter-spacing: 0.08em; color: #c9f1d2; }
.nav-groups { margin-top: 18px; display: grid; gap: 18px; }
.group-title { margin: 0 0 8px; font-size: 12px; color: #b9d6c1; }
.nav-item { display: block; padding: 12px 14px; border-radius: 14px; color: #f3f8f1; text-decoration: none; transition: .18s ease; }
.nav-item:hover { background: rgba(255, 255, 255, 0.08); transform: translateX(-2px); }
.nav-item.active { background: linear-gradient(135deg, #c8f169, #7ed957); color: #17311a; font-weight: 700; }
.shell-main { padding: 20px; display: grid; gap: 16px; }
.shell-header { min-height: 92px; border: 1px solid rgba(20, 32, 19, 0.08); border-radius: 24px; padding: 18px 22px; background: rgba(255, 255, 255, 0.72); backdrop-filter: blur(10px); display: flex; align-items: center; justify-content: space-between; }
.eyebrow { margin: 0 0 8px; font-size: 12px; color: #4e6a4c; }
.shell-header h1 { margin: 0; font-size: 28px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.profile-chip { min-width: 160px; padding: 10px 14px; border-radius: 16px; background: #132417; color: #f4f8f3; }
.profile-chip span, .profile-chip small { display: block; }
.profile-chip small { margin-top: 4px; color: #afd3b3; }
.shell-content { min-width: 0; }
@media (max-width: 1100px) {
  .app-shell { grid-template-columns: 1fr; }
  .sidebar { border-left: 0; border-bottom: 1px solid rgba(20, 32, 19, 0.08); }
  .shell-header { flex-direction: column; align-items: flex-start; gap: 12px; }
  .header-right { width: 100%; justify-content: space-between; }
}
</style>
