<template>
  <AppShell
    title="گزارشات"
    subtitle="تحلیل مالی و عملیاتی"
  >
    <div class="reports-content">
        <section class="filters-card">
          <div class="field search-field">
            <span>جستجو</span>
            <input v-model="filters.q" type="text" placeholder="راننده، شماره، نیرو، مدل یا پلاک..." />
          </div>
          <div class="field">
            <span>از تاریخ (شمسی)</span>
            <BaseDatePicker v-model="filters.startJalali" placeholder="1405/01/01" />
          </div>
          <div class="field">
            <span>تا تاریخ (شمسی)</span>
            <BaseDatePicker v-model="filters.endJalali" placeholder="1405/01/30" />
          </div>
          <button class="secondary-btn clear-btn" @click="resetFilters">حذف فیلتر</button>
        </section>

        <section class="summary-grid">
          <article class="kpi-card"><p>تعداد خودرو</p><strong>{{ Number(summary.vehicles_count || 0).toLocaleString('fa-IR') }}</strong></article>
          <article class="kpi-card"><p>حق کارواش</p><strong>{{ money(summary.carwash_total) }}</strong></article>
          <article class="kpi-card"><p>حق نیرو</p><strong>{{ money(summary.worker_total) }}</strong></article>
          <article class="kpi-card"><p>انعام</p><strong>{{ money(summary.tips_total) }}</strong></article>
        </section>

        <section class="tabs-summary-row">
          <div class="tabs-bar">
            <button v-for="tab in tabs" :key="tab.key" class="chip" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
          </div>
          <div class="payout-boxes">
            <article class="payout-card">
              <p>جمع پرداختی حقوق</p>
              <strong>{{ money(summary.payable_worker_total) }}</strong>
            </article>
            <article class="payout-card">
              <p>جمع انعام</p>
              <strong>{{ money(summary.payable_tip_total) }}</strong>
            </article>
            <button
              v-if="activeTab === 'worker'"
              class="primary-btn payout-action-btn"
              :disabled="settlingPayout"
              @click="settlePayout('worker')"
            >
              {{ settlingPayout ? 'در حال ثبت...' : 'پرداخت شد' }}
            </button>
            <button
              v-else-if="activeTab === 'tips'"
              class="primary-btn payout-action-btn"
              :disabled="settlingPayout"
              @click="settlePayout('tips')"
            >
              {{ settlingPayout ? 'در حال ثبت...' : 'پرداخت شد' }}
            </button>
          </div>
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
    </div>
  </AppShell>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import api from '../../services/api'
import { useAuthStore } from '../../store/auth.store'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import AppShell from '../../components/layout/AppShell.vue'

const authStore = useAuthStore()
const activeTab = ref('overall')
const errorMessage = ref('')
const filters = reactive({ startJalali: '', endJalali: '', q: '' })
const summary = reactive({
  vehicles_count: 0,
  carwash_total: 0,
  worker_total: 0,
  tips_total: 0,
  payable_worker_total: 0,
  payable_tip_total: 0
})
const data = reactive({ overall_report: [], carwash_report: [], worker_report: [], tips_report: [], attendance_report: [] })
const settlingPayout = ref(false)

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

const parseJalaliToIso = (input) => {
  const value = (input || '').trim().replace(/-/g, '/')
  const match = value.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/)
  if (!match) return ''
  const jy = Number(match[1]) - 979
  const jm = Number(match[2]) - 1
  const jd = Number(match[3]) - 1
  const jDaysInMonth = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
  let jDayNo = 365 * jy + Math.floor(jy / 33) * 8 + Math.floor(((jy % 33) + 3) / 4)
  for (let i = 0; i < jm; i += 1) jDayNo += jDaysInMonth[i]
  jDayNo += jd
  let gDayNo = jDayNo + 79
  let gy = 1600 + 400 * Math.floor(gDayNo / 146097)
  gDayNo %= 146097
  let leap = true
  if (gDayNo >= 36525) {
    gDayNo -= 1
    gy += 100 * Math.floor(gDayNo / 36524)
    gDayNo %= 36524
    if (gDayNo >= 365) gDayNo += 1
    else leap = false
  }
  gy += 4 * Math.floor(gDayNo / 1461)
  gDayNo %= 1461
  if (gDayNo >= 366) {
    leap = false
    gDayNo -= 1
    gy += Math.floor(gDayNo / 365)
    gDayNo %= 365
  }
  const gdMonth = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  let gm = 0
  while (gm < 12 && gDayNo >= gdMonth[gm]) {
    gDayNo -= gdMonth[gm]
    gm += 1
  }
  const gd = gDayNo + 1
  return `${gy}-${String(gm + 1).padStart(2, '0')}-${String(gd).padStart(2, '0')}`
}

let fetchToken = 0
const fetchReports = async () => {
  const token = ++fetchToken
  errorMessage.value = ''
  try {
    const start = parseJalaliToIso(filters.startJalali)
    const end = parseJalaliToIso(filters.endJalali)
    if ((filters.startJalali && !start) || (filters.endJalali && !end)) {
      errorMessage.value = 'فرمت تاریخ شمسی معتبر نیست.'
      return
    }
    const { data: payload } = await api.get('/reports/dashboard/', {
      params: {
        start: start || undefined,
        end: end || undefined,
        q: (filters.q || '').trim() || undefined
      }
    })
    if (token !== fetchToken) return
    Object.assign(summary, payload.summary || {})
    data.overall_report = payload.overall_report || []
    data.carwash_report = payload.carwash_report || []
    data.worker_report = payload.worker_report || []
    data.tips_report = payload.tips_report || []
    data.attendance_report = payload.attendance_report || []
  } catch (error) {
    if (token !== fetchToken) return
    errorMessage.value = error?.response?.data?.detail || 'بارگذاری گزارشات ناموفق بود.'
  }
}

const settlePayout = async (kind) => {
  const start = parseJalaliToIso(filters.startJalali)
  const end = parseJalaliToIso(filters.endJalali)
  if ((filters.startJalali && !start) || (filters.endJalali && !end)) {
    errorMessage.value = 'فرمت تاریخ شمسی معتبر نیست.'
    return
  }
  settlingPayout.value = true
  try {
    await api.post('/reports/payouts/settle/', {
      kind,
      start: start || undefined,
      end: end || undefined,
      q: (filters.q || '').trim() || undefined
    })
    await fetchReports()
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || 'ثبت وضعیت پرداخت ناموفق بود.'
  } finally {
    settlingPayout.value = false
  }
}

let filterTimer = null
const scheduleAutoFetch = () => {
  if (filterTimer) clearTimeout(filterTimer)
  filterTimer = setTimeout(() => {
    fetchReports()
  }, 280)
}

watch(() => [filters.q, filters.startJalali, filters.endJalali], () => {
  scheduleAutoFetch()
})

const resetFilters = () => {
  filters.startJalali = ''
  filters.endJalali = ''
  filters.q = ''
}

onMounted(async () => {
  await authStore.fetchMe()
  await fetchReports()
})
</script>

<style scoped>
.reports-content{font-size:13px}
.filters-card{display:grid;grid-template-columns:minmax(260px,1.2fr) 1fr 1fr auto;gap:8px;padding:10px;border:1px solid #e2e8f0;border-radius:12px;margin-bottom:10px;align-items:end}
.field{display:grid;gap:5px;font-size:12px}
.field input{height:38px;border:1px solid #cbd5e1;border-radius:10px;padding:0 10px;font-size:12px}
.search-field input{background:#f8fbff}
.summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}
.kpi-card{border:1px solid #e2e8f0;border-radius:12px;padding:10px;background:#f8fbff}
.kpi-card p{margin:0;color:#64748b;font-size:12px}
.kpi-card strong{display:block;margin-top:6px;font-size:15px;color:#0f172a}
.tabs-bar{display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap}
.tabs-summary-row{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:start;margin-bottom:10px}
.payout-boxes{display:flex;align-items:stretch;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.payout-card{border:1px solid #dbeafe;background:#f8fbff;border-radius:12px;padding:8px 10px;min-width:150px}
.payout-card p{margin:0;color:#64748b;font-size:11px}
.payout-card strong{display:block;margin-top:6px;color:#0f172a;font-size:13px}
.payout-action-btn{height:40px;white-space:nowrap}
.chip{border:0;background:#e2e8f0;color:#334155;padding:6px 12px;border-radius:999px;cursor:pointer;font-size:12px}
.chip.active{background:#2563eb;color:#fff}
.primary-btn{border:0;border-radius:10px;padding:8px 12px;cursor:pointer;background:linear-gradient(90deg,#2563eb,#0891b2);color:#fff}
.table-card{border:1px solid #e2e8f0;border-radius:12px;padding:10px}
.table-card h3{margin:0 0 8px;font-size:15px}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:12px}
th,td{padding:7px 6px;border-bottom:1px solid #e2e8f0;text-align:right;white-space:normal;vertical-align:top;line-height:1.5;word-break:break-word}
.secondary-btn{border:0;border-radius:10px;padding:8px 12px;cursor:pointer;background:#e2e8f0;height:38px}
.error-box{margin-bottom:10px;padding:10px;background:#fee2e2;color:#991b1b;border:1px solid #fecaca;border-radius:10px}
@media (max-width:1200px){
  .filters-card{grid-template-columns:1fr 1fr}
  .clear-btn{grid-column:1 / -1}
  .tabs-summary-row{grid-template-columns:1fr}
  .payout-boxes{justify-content:flex-start}
}
@media (max-width:1100px){
  .summary-grid{grid-template-columns:repeat(2,1fr)}
}
@media (max-width:760px){
  .filters-card{grid-template-columns:1fr}
}
</style>


