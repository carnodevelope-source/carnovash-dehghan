<template>
  <div class="dashboard-page" dir="rtl">
    <header class="topbar">
      <div class="topbar-left">
        <span class="brand">CarWash</span>
        <div class="search-box"><input v-model="filters.q" type="text" placeholder="جستجو راننده/نیرو..." /></div>
      </div>
      <div class="topbar-right">
        <button class="primary-btn" @click="fetchReports">اعمال فیلتر</button>
        <div class="profile"><p class="profile-name">{{ authStore.user?.full_name || authStore.user?.username || 'مدیر' }}</p></div>
      </div>
    </header>

    <div class="layout">
      <aside class="sidebar">
        <nav>
          <RouterLink class="menu-item" :class="{ active: route.name === 'operator-dashboard' }" to="/">مدیریت خودرو ها</RouterLink>
          <RouterLink v-if="authStore.canAccessManagerSettings" class="menu-item" :class="{ active: route.name === 'manager-settings' }" to="/manager/settings">تنظیمات</RouterLink>
          <RouterLink v-if="authStore.canAccessManagerSettings" class="menu-item" :class="{ active: route.name === 'manager-reports' }" to="/manager/reports">گزارشات</RouterLink>
        </nav>
      </aside>

      <main class="content reports-content">
        <section class="filters-card">
          <div class="field"><span>از تاریخ (شمسی)</span><input v-model="filters.startJalali" type="text" placeholder="1405/01/01" inputmode="numeric" /></div>
          <div class="field"><span>تا تاریخ (شمسی)</span><input v-model="filters.endJalali" type="text" placeholder="1405/01/30" inputmode="numeric" /></div>
          <button class="secondary-btn" @click="resetFilters">حذف فیلتر</button>
        </section>

        <section class="summary-grid">
          <article class="kpi-card"><p>تعداد خودرو</p><strong>{{ summary.vehicles_count.toLocaleString('fa-IR') }}</strong></article>
          <article class="kpi-card"><p>حق کارواش</p><strong>{{ money(summary.carwash_total) }}</strong></article>
          <article class="kpi-card"><p>حق نیرو</p><strong>{{ money(summary.worker_total) }}</strong></article>
          <article class="kpi-card"><p>انعام</p><strong>{{ money(summary.tips_total) }}</strong></article>
        </section>

        <section class="tabs-bar">
          <button v-for="tab in tabs" :key="tab.key" class="chip" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
        </section>

        <section class="table-card">
          <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>

          <template v-if="activeTab === 'overall'">
            <h3>گزارش کل</h3>
            <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>پلاک</th><th>حق کارواش</th><th>حق نیرو</th><th>انعام</th><th>نام نیرو</th><th>کالا</th><th>تاریخ</th></tr></thead><tbody>
              <tr v-for="row in data.overall_report" :key="`o-${row.row}`"><td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.plate_number }}</td><td>{{ money(row.carwash_share) }}</td><td>{{ money(row.worker_share) }}</td><td>{{ money(row.tip_amount) }}</td><td>{{ row.worker_name }}</td><td>{{ row.products || '-' }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
            </tbody></table></div>
          </template>

          <template v-else-if="activeTab === 'carwash'">
            <h3>گزارش حق کارواش</h3>
            <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>پلاک</th><th>حق کارواش</th><th>نام نیرو</th><th>تاریخ</th></tr></thead><tbody>
              <tr v-for="row in data.carwash_report" :key="`c-${row.row}`"><td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.plate_number }}</td><td>{{ money(row.carwash_share) }}</td><td>{{ row.worker_name }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
            </tbody></table></div>
          </template>

          <template v-else-if="activeTab === 'worker'">
            <h3>گزارش حق نیرو</h3>
            <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>پلاک</th><th>حق نیرو</th><th>نام نیرو</th><th>تاریخ</th></tr></thead><tbody>
              <tr v-for="row in data.worker_report" :key="`w-${row.row}`"><td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.plate_number }}</td><td>{{ money(row.worker_share) }}</td><td>{{ row.worker_name }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
            </tbody></table></div>
          </template>

          <template v-else-if="activeTab === 'tips'">
            <h3>گزارش انعام</h3>
            <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>پلاک</th><th>انعام</th><th>نام نیرو</th><th>کالا</th><th>تاریخ</th></tr></thead><tbody>
              <tr v-for="row in data.tips_report" :key="`t-${row.row}`"><td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.plate_number }}</td><td>{{ money(row.tip_amount) }}</td><td>{{ row.worker_name }}</td><td>{{ row.products || '-' }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
            </tbody></table></div>
          </template>

          <template v-else>
            <h3>گزارش ورود و خروج نیروها</h3>
            <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام نیرو</th><th>نوع رویداد</th><th>زمان</th><th>منبع</th></tr></thead><tbody>
              <tr v-for="row in data.attendance_report" :key="`a-${row.row}`"><td>{{ row.row }}</td><td>{{ row.worker_name }}</td><td>{{ row.event_type === 'in' ? 'ورود' : 'خروج' }}</td><td>{{ dateTime(row.event_at) }}</td><td>{{ row.source }}</td></tr>
            </tbody></table></div>
          </template>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import api from '../../services/api'
import { useAuthStore } from '../../store/auth.store'

const route = useRoute()
const authStore = useAuthStore()
const activeTab = ref('overall')
const errorMessage = ref('')
const filters = reactive({ startJalali: '', endJalali: '', q: '' })
const summary = reactive({ vehicles_count: 0, carwash_total: 0, worker_total: 0, tips_total: 0 })
const data = reactive({ overall_report: [], carwash_report: [], worker_report: [], tips_report: [], attendance_report: [] })

const tabs = [
  { key: 'overall', label: 'گزارش کل' },
  { key: 'carwash', label: 'حق کارواش' },
  { key: 'worker', label: 'حق نیرو' },
  { key: 'tips', label: 'انعام' },
  { key: 'attendance', label: 'ورود و خروج نیروها' }
]

const money = (v) => `${Number(v || 0).toLocaleString('fa-IR')} تومان`
const dateTime = (v) => {
  if (!v) return '-'
  return new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(v))
}

const jalaliToGregorian = (jy, jm, jd) => {
  const breaks = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178]
  const div = (a, b) => Math.floor(a / b)
  let bl = breaks.length
  let gy = jy + 621
  let leapJ = -14
  let jp = breaks[0]
  let jmBreak
  let jump = 0

  if (jy < jp || jy >= breaks[bl - 1]) return null

  for (let i = 1; i < bl; i += 1) {
    jmBreak = breaks[i]
    jump = jmBreak - jp
    if (jy < jmBreak) break
    leapJ += div(jump, 33) * 8 + div((jump % 33), 4)
    jp = jmBreak
  }

  let n = jy - jp
  leapJ += div(n, 33) * 8 + div(((n % 33) + 3), 4)
  if ((jump % 33) === 4 && jump - n === 4) leapJ += 1
  const leapG = div(gy, 4) - div((div(gy, 100) + 1) * 3, 4) - 150
  const march = 20 + leapJ - leapG
  if (jump - n < 6) n = n - jump + div(jump + 4, 33) * 33
  let leap = (((n + 1) % 33) - 1) % 4
  if (leap === -1) leap = 4

  let jdn1f = 0
  let i
  for (i = 0; i < jm - 1; i += 1) jdn1f += i < 6 ? 31 : 30
  let jdn = jdn1f + jd + march + (gy * 365) + div((gy + 3), 4) - div((gy + 99), 100) + div((gy + 399), 400) - 80

  let gDayNo = jdn
  let gYear = 1600 + 400 * div(gDayNo, 146097)
  gDayNo %= 146097
  let leapYear = true
  if (gDayNo >= 36525) {
    gDayNo -= 1
    gYear += 100 * div(gDayNo, 36524)
    gDayNo %= 36524
    if (gDayNo >= 365) gDayNo += 1
    else leapYear = false
  }
  gYear += 4 * div(gDayNo, 1461)
  gDayNo %= 1461
  if (gDayNo >= 366) {
    leapYear = false
    gDayNo -= 1
    gYear += div(gDayNo, 365)
    gDayNo %= 365
  }
  const gdMonth = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  let gMonth = 0
  while (gMonth < 12 && gDayNo >= gdMonth[gMonth]) {
    gDayNo -= gdMonth[gMonth]
    gMonth += 1
  }
  const gDay = gDayNo + 1
  return { gy: gYear, gm: gMonth + 1, gd: gDay, leap }
}

const parseJalaliToIso = (value) => {
  if (!value) return ''
  const normalized = value.replace(/-/g, '/').trim()
  const match = normalized.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/)
  if (!match) return null
  const jy = Number(match[1])
  const jm = Number(match[2])
  const jd = Number(match[3])
  if (jm < 1 || jm > 12 || jd < 1 || jd > 31) return null
  const g = jalaliToGregorian(jy, jm, jd)
  if (!g) return null
  const mm = String(g.gm).padStart(2, '0')
  const dd = String(g.gd).padStart(2, '0')
  return `${g.gy}-${mm}-${dd}`
}

const fetchReports = async () => {
  errorMessage.value = ''
  try {
    const start = parseJalaliToIso(filters.startJalali)
    const end = parseJalaliToIso(filters.endJalali)
    if ((filters.startJalali && !start) || (filters.endJalali && !end)) {
      errorMessage.value = 'فرمت تاریخ شمسی صحیح نیست. نمونه: 1405/01/01'
      return
    }
    const { data: payload } = await api.get('/reports/dashboard/', { params: { start: start || undefined, end: end || undefined, q: filters.q || undefined } })
    Object.assign(summary, payload.summary || {})
    data.overall_report = payload.overall_report || []
    data.carwash_report = payload.carwash_report || []
    data.worker_report = payload.worker_report || []
    data.tips_report = payload.tips_report || []
    data.attendance_report = payload.attendance_report || []
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || 'بارگذاری گزارشات ناموفق بود.'
  }
}

const resetFilters = async () => {
  filters.startJalali = ''
  filters.endJalali = ''
  filters.q = ''
  await fetchReports()
}

onMounted(async () => {
  await authStore.fetchMe()
  await fetchReports()
})
</script>

<style scoped>
.dashboard-page{min-height:100vh;background:#f8fafc}
.topbar{height:72px;display:flex;justify-content:space-between;align-items:center;padding:0 20px;background:#fff;border-bottom:1px solid #e2e8f0}
.topbar-left{display:flex;align-items:center;gap:12px}.brand{font-weight:700;color:#1e293b}.search-box input{height:40px;border:1px solid #cbd5e1;border-radius:10px;padding:0 12px;min-width:260px}.profile-name{margin:0;font-weight:700}
.layout{display:grid;grid-template-columns:220px 1fr;gap:14px;padding:14px}.sidebar{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:10px;height:fit-content}.menu-item{display:block;padding:10px;border-radius:10px;color:#334155;text-decoration:none}.menu-item.active{background:#dbeafe;color:#1d4ed8;font-weight:700}
.content{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:14px;font-size:13px}
.filters-card{display:grid;grid-template-columns:1fr 1fr auto;gap:8px;padding:10px;border:1px solid #e2e8f0;border-radius:12px;margin-bottom:10px}.field{display:grid;gap:5px;font-size:12px}.field input{height:38px;border:1px solid #cbd5e1;border-radius:10px;padding:0 10px;font-size:12px}
.summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}.kpi-card{border:1px solid #e2e8f0;border-radius:12px;padding:10px;background:#f8fbff}.kpi-card p{margin:0;color:#64748b;font-size:12px}.kpi-card strong{display:block;margin-top:6px;font-size:15px;color:#0f172a}
.tabs-bar{display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap}.chip{border:0;background:#e2e8f0;color:#334155;padding:6px 12px;border-radius:999px;cursor:pointer;font-size:12px}.chip.active{background:#2563eb;color:#fff}
.table-card{border:1px solid #e2e8f0;border-radius:12px;padding:10px}.table-card h3{margin:0 0 8px;font-size:15px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:12px}th,td{padding:7px 6px;border-bottom:1px solid #e2e8f0;text-align:right;white-space:normal;vertical-align:top;line-height:1.5;word-break:break-word}
.primary-btn,.secondary-btn{border:0;border-radius:10px;padding:8px 12px;cursor:pointer}.primary-btn{background:linear-gradient(90deg,#2563eb,#0891b2);color:#fff}.secondary-btn{background:#e2e8f0}
.error-box{margin-bottom:10px;padding:10px;background:#fee2e2;color:#991b1b;border:1px solid #fecaca;border-radius:10px}
@media (max-width:1100px){.summary-grid{grid-template-columns:repeat(2,1fr)}.filters-card{grid-template-columns:1fr}.layout{grid-template-columns:1fr}.search-box input{min-width:180px}}
</style>
