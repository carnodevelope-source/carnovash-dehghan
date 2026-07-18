<template>
  <AppShell title="حضور و غیاب" subtitle="پایش لحظه‌ای شیفت‌ها، لینک اختصاصی نیروها و لاگ ورود و خروج">
    <div class="attendance-view">
      <section class="tabs-bar">
        <button class="tab-chip" :class="{ active: activeTab === 'dashboard' }" @click="activeTab = 'dashboard'">
          <IconlyIcon name="home" size="sm" />داشبورد
        </button>
        <button class="tab-chip" :class="{ active: activeTab === 'reports' }" @click="activeTab = 'reports'">
          <IconlyIcon name="document" size="sm" />گزارشات
        </button>
      </section>

      <template v-if="activeTab === 'dashboard'">
      <section class="hero-panel">
        <div class="hero-copy">
          <span class="hero-tag">Blue Wash Workforce Console</span>
          <h2>کنترل زنده وضعیت نیروها</h2>
          <p>لینک اختصاصی، ثبت دستی منیجر، روند هفتگی و خلاصه ساعات کاری امروز در یک صفحه یکپارچه.</p>
        </div>
        <div class="hero-stats">
          <article class="hero-stat">
            <span>نیروهای حاضر</span>
            <strong>{{ toFa(summary.present_count || 0) }}</strong>
          </article>
          <article class="hero-stat">
            <span>خارج از شیفت</span>
            <strong>{{ toFa(summary.absent_count || 0) }}</strong>
          </article>
        </div>
      </section>
      </template>

      <template v-else>
        <section class="reports-hero">
          <div>
            <span class="section-kicker">Attendance Reports</span>
            <h2>گزارش ورود و خروج</h2>
            <p>فیلتر بازه زمانی، پرسنل و جست‌وجوی سریع را از همین‌جا اعمال کنید و گزارش کامل ورود و خروج را در همان تم گزارشات ببینید.</p>
          </div>
          <div class="hero-stats reports-stats">
            <article class="hero-stat">
              <span>کل رویدادها</span>
              <strong>{{ toFa(reportRows.length) }}</strong>
            </article>
            <article class="hero-stat">
              <span>ورودها</span>
              <strong>{{ toFa(reportCheckins) }}</strong>
            </article>
            <article class="hero-stat">
              <span>خروج‌ها</span>
              <strong>{{ toFa(reportCheckouts) }}</strong>
            </article>
          </div>
        </section>

        <section class="reports-range-bar">
          <button
            v-for="option in reportRangeOptions"
            :key="option.key"
            class="range-chip"
            :class="{ active: reportFilters.rangeKey === option.key }"
            @click="reportFilters.rangeKey = option.key"
          >
            <IconlyIcon :name="option.icon" size="sm" />
            {{ option.label }}
          </button>
        </section>

        <section class="reports-filters-card">
          <label class="report-field search-wide">
            <span><IconlyIcon name="search" size="xs" />جستجو</span>
            <input v-model.trim="reportFilters.q" type="text" placeholder="نام پرسنل یا منبع ثبت..." />
          </label>
          <label class="report-field">
            <span><IconlyIcon name="calendar" size="xs" />شروع بازه</span>
            <BaseDatePicker v-model="reportFilters.startJalali" placeholder="1405/01/01" />
          </label>
          <label class="report-field">
            <span><IconlyIcon name="calendar" size="xs" />پایان بازه</span>
            <BaseDatePicker v-model="reportFilters.endJalali" placeholder="1405/01/30" />
          </label>
          <label class="report-field">
            <span><IconlyIcon name="users3" size="xs" />پرسنل</span>
            <select v-model="reportFilters.workerId">
              <option value="">همه پرسنل</option>
              <option v-for="worker in workers" :key="worker.id" :value="String(worker.id)">{{ worker.full_name }}</option>
            </select>
          </label>
          <button class="ghost-btn btn-with-icon report-clear-btn" @click="resetReportFilters"><IconlyIcon name="filter" size="sm" />حذف فیلتر</button>
        </section>

        <div v-if="reportsErrorMessage" class="error-box">{{ reportsErrorMessage }}</div>

        <section class="section-card report-table-card">
          <header class="section-head">
            <div>
              <span class="section-kicker">Log Table</span>
              <h3>جدول گزارش ورود و خروج</h3>
            </div>
          </header>
          <div class="report-table-wrap">
            <table class="report-table">
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>نام پرسنل</th>
                  <th>نوع رویداد</th>
                  <th>منبع ثبت</th>
                  <th>زمان</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in reportRows" :key="`attendance-${row.row}`">
                  <td>{{ row.row }}</td>
                  <td>{{ row.worker_name }}</td>
                  <td>{{ row.event_type === 'in' ? 'ورود' : 'خروج' }}</td>
                  <td>{{ sourceLabel(row.source) }}</td>
                  <td>{{ dateTime(row.event_at) }}</td>
                </tr>
                <tr v-if="!reportRows.length">
                  <td colspan="5">برای این بازه گزارشی پیدا نشد.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>

      <section v-if="activeTab === 'dashboard'" class="toolbar-card">
        <label class="search-field">
          <span><IconlyIcon name="search" size="xs" />جستجوی نیرو</span>
          <input v-model.trim="filters.q" type="text" placeholder="نام، شماره موبایل یا وضعیت..." />
        </label>
        <label class="filter-field">
          <span><IconlyIcon name="category" size="xs" />وضعیت</span>
          <select v-model="filters.status">
            <option value="all">همه</option>
            <option value="in">حاضر</option>
            <option value="out">خارج از شیفت</option>
          </select>
        </label>
        <label class="filter-field">
          <span><IconlyIcon name="graph" size="xs" />بار کاری</span>
          <select v-model="filters.load">
            <option value="all">همه</option>
            <option value="free">آزاد</option>
            <option value="normal">نرمال</option>
            <option value="busy">شلوغ</option>
          </select>
        </label>
        <button class="ghost-btn btn-with-icon" @click="loadDashboard"><IconlyIcon name="show" size="sm" />بروزرسانی</button>
      </section>

      <div v-if="activeTab === 'dashboard' && errorMessage" class="error-box">{{ errorMessage }}</div>

      <section v-if="activeTab === 'dashboard'" class="content-grid">
        <div class="workers-column">
          <section class="section-card">
            <header class="section-head">
              <div>
                <span class="section-kicker">Team Access Cards</span>
                <h3>کارت نیروها و لینک اختصاصی</h3>
              </div>
              <strong>{{ toFa(filteredWorkers.length) }} نفر</strong>
            </header>

            <div v-if="attendanceUpgradeNotice" class="upgrade-banner">{{ attendanceUpgradeNotice }}</div>

            <div class="workers-grid">
              <article v-for="worker in filteredWorkers" :key="worker.id" class="worker-card" :class="worker.current_status">
                <div class="worker-head">
                  <div class="avatar">{{ worker.avatar }}</div>
                  <div class="worker-copy">
                    <strong>{{ worker.full_name }}</strong>
                    <span>{{ worker.phone || 'بدون شماره' }}</span>
                    <small v-if="worker.attendance_enabled === false" class="worker-upgrade-note">{{ worker.attendance_locked_reason }}</small>
                  </div>
                  <div class="status-pill" :class="worker.current_status">
                    {{ worker.current_status === 'in' ? 'حاضر' : 'خارج' }}
                  </div>
                </div>

                <div class="worker-meta">
                  <div class="meta-chip">
                    <span>ساعت امروز</span>
                    <strong>{{ toFa(worker.today_worked_hours || 0) }}</strong>
                  </div>
                  <div class="meta-chip">
                    <span>ثبت‌ها</span>
                    <strong>{{ toFa(worker.today_events_count || 0) }}</strong>
                  </div>
                  <div class="meta-chip">
                    <span>بار کاری</span>
                    <strong>{{ loadLabel(worker.load_status) }}</strong>
                  </div>
                </div>

                <div class="qr-row">
                  <img class="qr-frame" :class="{ disabled: worker.attendance_enabled === false }" :src="qrSrc(worker)" :alt="`QR ${worker.full_name}`" loading="lazy" />
                  <div class="qr-copy">
                    <span>لینک ورود و خروج</span>
                    <code>{{ fullAttendanceLink(worker) }}</code>
                    <small>برای اسکن یا بازکردن مستقیم توسط نیرو</small>
                  </div>
                </div>

                <div class="worker-actions">
                  <button class="primary-btn" :disabled="submittingWorkerId === worker.id || worker.current_status === 'in' || worker.attendance_enabled === false" @click="submitManagerEvent(worker, 'in')">
                    <IconlyIcon name="calendar" size="sm" />ثبت ورود
                  </button>
                  <button class="secondary-btn" :disabled="submittingWorkerId === worker.id || worker.current_status !== 'in' || worker.attendance_enabled === false" @click="submitManagerEvent(worker, 'out')">
                    <IconlyIcon name="logout" size="sm" />ثبت خروج
                  </button>
                  <button class="ghost-inline-btn" :disabled="worker.attendance_enabled === false" @click="copyLink(worker)"><IconlyIcon name="document" size="sm" />کپی لینک</button>
                  <button class="ghost-inline-btn" :disabled="worker.attendance_enabled === false" @click="openLink(worker)"><IconlyIcon name="show" size="sm" />باز کردن</button>
                  <button class="danger-inline-btn" :disabled="worker.attendance_enabled === false" @click="refreshToken(worker)"><IconlyIcon name="editSquare" size="sm" />بازسازی لینک</button>
                </div>
              </article>
            </div>
          </section>
        </div>

        <div class="insights-column">
          <section class="section-card">
            <header class="section-head">
              <div>
                <span class="section-kicker">Live Pulse</span>
                <h3>خلاصه و روند هفتگی</h3>
              </div>
            </header>
            <div class="kpi-grid">
              <article class="kpi-card">
                <span>کل رویدادهای امروز</span>
                <strong>{{ toFa(summary.today_events_count || 0) }}</strong>
              </article>
              <article class="kpi-card">
                <span>میانگین ساعت هر نفر</span>
                <strong>{{ averageHoursLabel }}</strong>
              </article>
              <article class="kpi-card">
                <span>ثبت‌های ورود هفته</span>
                <strong>{{ toFa(totalWeeklyCheckins) }}</strong>
              </article>
              <article class="kpi-card">
                <span>ثبت‌های خروج هفته</span>
                <strong>{{ toFa(totalWeeklyCheckouts) }}</strong>
              </article>
            </div>
            <div class="trend-list">
              <article v-for="item in trend" :key="item.date" class="trend-item">
                <div class="trend-copy">
                  <strong>{{ dateLabel(item.date) }}</strong>
                  <span>{{ toFa(item.checkins) }} ورود · {{ toFa(item.checkouts) }} خروج</span>
                </div>
                <div class="trend-bars">
                  <div class="bar in" :style="{ width: `${barWidth(item.checkins, weeklyMax)}%` }"></div>
                  <div class="bar out" :style="{ width: `${barWidth(item.checkouts, weeklyMax)}%` }"></div>
                </div>
              </article>
            </div>
          </section>

          <section class="section-card">
            <header class="section-head">
              <div>
                <span class="section-kicker">Activity Feed</span>
                <h3>آخرین رویدادها</h3>
              </div>
            </header>
            <div class="feed-list">
              <article v-for="event in recentEvents" :key="event.id" class="feed-item">
                <div class="feed-badge" :class="event.event_type">{{ event.event_type === 'in' ? 'IN' : 'OUT' }}</div>
                <div class="feed-copy">
                  <strong>{{ event.worker_name }}</strong>
                  <p>{{ dateTime(event.event_at) }}</p>
                </div>
                <small>{{ event.note || sourceLabel(event.source) }}</small>
              </article>
            </div>
          </section>
        </div>
      </section>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import AppShell from '../../components/layout/AppShell.vue'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import IconlyIcon from '../../components/base/IconlyIcon.vue'
import api from '../../services/api'
import { formatJalaliDate, formatJalaliDateTime } from '../../utils/date'
import { resolveApiErrorMessage } from '../../utils/apiError'

const activeTab = ref('dashboard')
const summary = ref({})
const workers = ref([])
const trend = ref([])
const recentEvents = ref([])
const errorMessage = ref('')
const reportsErrorMessage = ref('')
const submittingWorkerId = ref(null)
const filters = ref({ q: '', status: 'all', load: 'all' })
const reportRows = ref([])
const reportRangeOptions = [
  { key: 'today', label: 'امروز', icon: 'calendar' },
  { key: 'week', label: 'این هفته', icon: 'graph' },
  { key: 'month', label: 'این ماه', icon: 'document' },
  { key: 'all', label: 'کل', icon: 'category' }
]
const reportFilters = reactive({
  rangeKey: 'today',
  startJalali: '',
  endJalali: '',
  q: '',
  workerId: ''
})

const toFa = (value) => Number(value || 0).toLocaleString('fa-IR')
const dateTime = (value) => formatJalaliDateTime(value)
const dateLabel = (value) => formatJalaliDate(value)
const loadLabel = (value) => ({ free: 'آزاد', normal: 'نرمال', busy: 'شلوغ' }[value] || '-')
const sourceLabel = (value) => ({ manager: 'ثبت مدیر', link: 'لینک نیرو' }[value] || value || '-')

const filteredWorkers = computed(() => {
  const query = String(filters.value.q || '').trim().toLowerCase()
  return (workers.value || []).filter((worker) => {
    if (filters.value.status !== 'all' && worker.current_status !== filters.value.status) return false
    if (filters.value.load !== 'all' && worker.load_status !== filters.value.load) return false
    if (!query) return true
    const haystack = [worker.full_name, worker.phone, loadLabel(worker.load_status), worker.current_status === 'in' ? 'حاضر' : 'خارج']
      .join(' ')
      .toLowerCase()
    return haystack.includes(query)
  })
})

const averageHoursLabel = computed(() => {
  const total = Number(summary.value.today_worked_hours || 0)
  const count = Number(summary.value.workers_count || 0)
  return toFa(count ? (total / count).toFixed(1) : 0)
})

const totalWeeklyCheckins = computed(() => (trend.value || []).reduce((sum, item) => sum + Number(item.checkins || 0), 0))
const totalWeeklyCheckouts = computed(() => (trend.value || []).reduce((sum, item) => sum + Number(item.checkouts || 0), 0))
const weeklyMax = computed(() => {
  const values = (trend.value || []).flatMap((item) => [Number(item.checkins || 0), Number(item.checkouts || 0)])
  return Math.max(...values, 1)
})
const reportCheckins = computed(() => reportRows.value.filter((item) => item.event_type === 'in').length)
const reportCheckouts = computed(() => reportRows.value.filter((item) => item.event_type === 'out').length)
const attendanceUpgradeNotice = computed(() => {
  const workerCount = Number(summary.value.attendance_worker_count || 0)
  const freeLimit = Number(summary.value.attendance_free_workers_limit || 5)
  if (Number(summary.value.attendance_feature_purchased || 0) === 1) return ''
  if (workerCount <= freeLimit) return ''
  return `ورود و خروج تا ${freeLimit.toLocaleString('fa-IR')} نیرو رایگان است. برای نیروهای بیشتر باید آپشن ورود و خروج را از کیف پول خریداری کنید.`
})

const fullAttendanceLink = (worker) => `${window.location.origin}${worker.attendance_path || `/attendance/${worker.attendance_token}`}`
const qrSrc = (worker) => `https://api.qrserver.com/v1/create-qr-code/?size=132x132&data=${encodeURIComponent(fullAttendanceLink(worker))}`
const barWidth = (value, max) => Math.max(8, Math.round((Number(value || 0) / Math.max(Number(max || 1), 1)) * 100))

const toIsoDate = (value) => {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const resolveRangeDates = (rangeKey) => {
  if (rangeKey === 'all') return { start: '', end: '' }
  const now = new Date()
  const end = new Date(now)
  let start = new Date(now)
  if (rangeKey === 'today') return { start: toIsoDate(start), end: toIsoDate(end) }
  if (rangeKey === 'week') {
    const day = now.getDay()
    const offset = day === 0 ? 6 : day - 1
    start.setDate(now.getDate() - offset)
    return { start: toIsoDate(start), end: toIsoDate(end) }
  }
  if (rangeKey === 'month') {
    start = new Date(now.getFullYear(), now.getMonth(), 1)
    return { start: toIsoDate(start), end: toIsoDate(end) }
  }
  return { start: '', end: '' }
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
  return `${gy}-${String(gm + 1).padStart(2, '0')}-${String(gDayNo + 1).padStart(2, '0')}`
}

const loadDashboard = async () => {
  try {
    const { data } = await api.get('/workers/attendance/dashboard/')
    summary.value = data?.summary || {}
    workers.value = data?.workers || []
    trend.value = data?.trend || []
    recentEvents.value = data?.recent_events || []
    errorMessage.value = ''
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بارگذاری حضور و غیاب ناموفق بود.')
  }
}

let reportFetchToken = 0
const loadAttendanceReports = async () => {
  const token = ++reportFetchToken
  try {
    const manualStart = parseJalaliToIso(reportFilters.startJalali)
    const manualEnd = parseJalaliToIso(reportFilters.endJalali)
    const quickRange = resolveRangeDates(reportFilters.rangeKey)
    const workerId = Number.parseInt(reportFilters.workerId, 10)
    const { data } = await api.get('/reports/dashboard/', {
      params: {
        start: manualStart || quickRange.start || undefined,
        end: manualEnd || quickRange.end || undefined,
        q: reportFilters.q || undefined,
        worker_id: Number.isInteger(workerId) && workerId > 0 ? workerId : undefined,
      }
    })
    if (token !== reportFetchToken) return
    reportRows.value = Array.isArray(data?.attendance_report) ? data.attendance_report : []
    reportsErrorMessage.value = ''
  } catch (error) {
    if (token !== reportFetchToken) return
    reportsErrorMessage.value = resolveApiErrorMessage(error, 'بارگذاری گزارش ورود و خروج ناموفق بود.')
  }
}

const resetReportFilters = () => {
  reportFilters.rangeKey = 'today'
  reportFilters.startJalali = ''
  reportFilters.endJalali = ''
  reportFilters.q = ''
  reportFilters.workerId = ''
}

const submitManagerEvent = async (worker, eventType) => {
  if (worker?.attendance_enabled === false) {
    errorMessage.value = worker.attendance_locked_reason || attendanceUpgradeNotice.value
    return
  }
  submittingWorkerId.value = worker.id
  try {
    await api.post('/workers/attendance/events/', {
      worker_id: worker.id,
      event_type: eventType
    })
    await loadDashboard()
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'ثبت رویداد ناموفق بود.')
  } finally {
    submittingWorkerId.value = null
  }
}

const copyLink = async (worker) => {
  if (worker?.attendance_enabled === false) {
    errorMessage.value = worker.attendance_locked_reason || attendanceUpgradeNotice.value
    return
  }
  try {
    await navigator.clipboard.writeText(fullAttendanceLink(worker))
  } catch (_error) {
    errorMessage.value = 'کپی لینک روی این مرورگر انجام نشد.'
  }
}

const openLink = (worker) => {
  if (worker?.attendance_enabled === false) {
    errorMessage.value = worker.attendance_locked_reason || attendanceUpgradeNotice.value
    return
  }
  window.open(fullAttendanceLink(worker), '_blank', 'noopener')
}

const refreshToken = async (worker) => {
  if (worker?.attendance_enabled === false) {
    errorMessage.value = worker.attendance_locked_reason || attendanceUpgradeNotice.value
    return
  }
  try {
    await api.post(`/workers/${worker.id}/attendance-token/refresh/`)
    await loadDashboard()
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بازسازی لینک انجام نشد.')
  }
}

onMounted(loadDashboard)

let reportFilterTimer = null
watch(() => [activeTab.value, reportFilters.rangeKey, reportFilters.startJalali, reportFilters.endJalali, reportFilters.q, reportFilters.workerId], () => {
  if (activeTab.value !== 'reports') return
  if (reportFilterTimer) clearTimeout(reportFilterTimer)
  reportFilterTimer = setTimeout(loadAttendanceReports, 260)
})

watch(activeTab, async (value) => {
  if (value === 'reports') await loadAttendanceReports()
})
</script>

<style scoped>
.attendance-view{display:grid;gap:16px}
.tabs-bar{display:flex;gap:8px;flex-wrap:wrap}
.tab-chip{border:0;border-radius:999px;padding:10px 16px;background:#e2e8f0;color:#334155;cursor:pointer;font:inherit;font-weight:800;display:inline-flex;align-items:center;gap:8px}
.tab-chip.active{background:#0f4c81;color:#fff}
.tab-chip.active :deep(.iconly-shell){--iconly-filter: brightness(0) saturate(100%) invert(100%)}
.hero-panel{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;padding:24px;border-radius:30px;background:linear-gradient(135deg,#0f172a 0%,#0f4c81 48%,#0ea5e9 100%);color:#fff;overflow:hidden;position:relative;box-shadow:0 28px 70px rgba(15,23,42,.22)}
.reports-hero{display:grid;grid-template-columns:1.1fr .9fr;gap:16px;padding:24px;border-radius:30px;background:linear-gradient(135deg,#f8fbff 0%,#edf6ff 48%,#ffffff 100%);border:1px solid #dbe5f0;box-shadow:0 24px 56px rgba(15,23,42,.06)}
.reports-hero h2{margin:10px 0 8px;color:#0f172a;font-size:30px}
.reports-hero p{margin:0;color:#4b5d72;line-height:1.9}
.reports-stats .hero-stat{background:#fff;border:1px solid #dbe5f0;color:#0f172a}
.reports-stats .hero-stat span{color:#64748b}
.reports-range-bar{display:flex;gap:8px;flex-wrap:wrap}
.range-chip{border:1px solid #cbd5e1;background:#fff;color:#334155;padding:9px 16px;border-radius:999px;cursor:pointer;font-size:12px;font-weight:700;display:inline-flex;align-items:center;gap:8px}
.range-chip.active{background:#2563eb;border-color:#2563eb;color:#fff}
.range-chip.active :deep(.iconly-shell){--iconly-filter: brightness(0) saturate(100%) invert(100%)}
.reports-filters-card{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;padding:16px;border:1px solid #dbe5f0;border-radius:24px;background:linear-gradient(180deg,#fff,#f8fbff)}
.report-field{display:grid;gap:6px}
.report-field span{font-size:12px;color:#475569;font-weight:700;display:inline-flex;align-items:center;gap:6px}
.report-field input,.report-field select{height:44px;border:1px solid #cbd5e1;border-radius:16px;padding:0 14px;background:#fff;font:inherit}
.search-wide{grid-column:span 2}
.report-clear-btn{align-self:end}
.report-table-card{padding-top:16px}
.report-table-wrap{overflow:auto}
.report-table{width:100%;border-collapse:collapse}
.report-table th,.report-table td{padding:10px;border-bottom:1px solid #e2e8f0;text-align:right;white-space:nowrap}
.hero-panel::after{content:'';position:absolute;inset:auto -80px -100px auto;width:240px;height:240px;border-radius:999px;background:radial-gradient(circle,#ffffff55 0,#ffffff00 72%)}
.hero-tag{display:inline-flex;padding:6px 12px;border-radius:999px;background:#ffffff1a;border:1px solid #ffffff2b;font-size:12px;letter-spacing:.04em}
.hero-copy h2{margin:14px 0 10px;font-size:32px}
.hero-copy p{margin:0;max-width:560px;color:#d9ecff;line-height:1.9}
.hero-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.hero-panel .hero-stats{grid-template-columns:repeat(2,minmax(0,1fr))}
.hero-stat{padding:18px 20px;border-radius:22px;background:#ffffff14;border:1px solid #ffffff24;backdrop-filter:blur(8px)}
.hero-stat span{display:block;color:#dbeafe;font-size:12px}
.hero-stat strong{display:block;margin-top:10px;font-size:26px}
.toolbar-card{display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:12px;padding:16px;border:1px solid #dbe5f0;border-radius:24px;background:linear-gradient(180deg,#ffffff,#f8fbff)}
.search-field,.filter-field{display:grid;gap:6px}
.search-field span,.filter-field span{font-size:12px;color:#475569;font-weight:700;display:inline-flex;align-items:center;gap:6px}
.search-field input,.filter-field select{height:46px;border:1px solid #cbd5e1;border-radius:16px;padding:0 14px;background:#fff;font:inherit}
.content-grid{display:grid;grid-template-columns:1.25fr .75fr;gap:16px;align-items:start}
.section-card{padding:18px;border:1px solid #dbe5f0;border-radius:28px;background:#fff;box-shadow:0 18px 45px rgba(15,23,42,.05)}
.section-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:16px}
.section-kicker{display:block;color:#0284c7;font-size:12px;font-weight:800}
.section-head h3{margin:8px 0 0;font-size:22px;color:#0f172a}
.upgrade-banner{margin-bottom:14px;padding:12px 14px;border:1px solid #fde68a;border-radius:18px;background:#fffbeb;color:#92400e;font-size:13px;line-height:1.9}
.workers-grid{display:grid;gap:14px}
.worker-card{padding:16px;border-radius:24px;border:1px solid #dbeafe;background:linear-gradient(180deg,#ffffff,#f8fbff)}
.worker-card.in{box-shadow:0 16px 36px rgba(16,185,129,.08)}
.worker-card.out{box-shadow:0 16px 36px rgba(59,130,246,.06)}
.worker-head{display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center}
.avatar{display:grid;place-items:center;width:54px;height:54px;border-radius:18px;background:linear-gradient(135deg,#dbeafe,#a5f3fc);font-weight:800;color:#0f172a}
.worker-copy strong{display:block;font-size:17px}
.worker-copy span{display:block;margin-top:4px;color:#64748b;font-size:12px}
.worker-upgrade-note{display:block;margin-top:6px;color:#b45309;font-size:11px;line-height:1.8}
.status-pill{display:inline-flex;align-items:center;justify-content:center;padding:8px 12px;border-radius:999px;font-size:12px;font-weight:800}
.status-pill.in{background:#ecfdf5;color:#047857}
.status-pill.out{background:#f1f5f9;color:#334155}
.worker-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}
.meta-chip{padding:12px;border-radius:18px;background:#f8fafc;border:1px solid #e2e8f0}
.meta-chip span{display:block;color:#64748b;font-size:11px}
.meta-chip strong{display:block;margin-top:8px;font-size:15px}
.qr-row{display:grid;grid-template-columns:132px 1fr;gap:14px;margin-top:16px;padding:14px;border-radius:20px;background:linear-gradient(135deg,#eff6ff,#f8fafc)}
.qr-frame{width:132px;height:132px;border-radius:18px;background:#fff;padding:8px;border:1px solid #dbeafe;object-fit:cover}
.qr-frame.disabled{opacity:.35;filter:grayscale(1)}
.qr-copy{display:grid;align-content:center;gap:8px;min-width:0}
.qr-copy span{font-size:12px;color:#0284c7;font-weight:800}
.qr-copy code{display:block;padding:10px 12px;border-radius:14px;background:#fff;border:1px solid #dbeafe;color:#0f172a;font-size:11px;word-break:break-all}
.qr-copy small{color:#64748b}
.worker-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.primary-btn,.secondary-btn,.ghost-btn,.ghost-inline-btn,.danger-inline-btn{height:42px;border:none;border-radius:14px;padding:0 14px;font:inherit;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px}
.primary-btn{background:linear-gradient(135deg,#0284c7,#06b6d4);color:#fff;box-shadow:0 12px 24px rgba(6,182,212,.18)}
.secondary-btn{background:#0f172a;color:#fff}
.ghost-btn,.ghost-inline-btn{background:#eff6ff;color:#1d4ed8}
.danger-inline-btn{background:#fef2f2;color:#b91c1c}
.btn-with-icon{display:inline-flex;align-items:center;gap:8px}
.primary-btn :deep(.iconly-shell),
.secondary-btn :deep(.iconly-shell) { --iconly-filter: brightness(0) saturate(100%) invert(100%); }
.danger-inline-btn :deep(.iconly-shell) { --iconly-filter: brightness(0) saturate(100%) invert(20%) sepia(78%) saturate(2280%) hue-rotate(345deg) brightness(97%) contrast(92%); }
.primary-btn:disabled,.secondary-btn:disabled,.ghost-inline-btn:disabled,.danger-inline-btn:disabled{opacity:.55;cursor:not-allowed}
.kpi-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.kpi-card{padding:14px;border-radius:20px;border:1px solid #dbeafe;background:linear-gradient(180deg,#ffffff,#eff6ff)}
.kpi-card span{display:block;color:#64748b;font-size:12px}
.kpi-card strong{display:block;margin-top:10px;font-size:22px}
.trend-list{display:grid;gap:10px;margin-top:14px}
.trend-item{display:grid;grid-template-columns:1fr 140px;gap:10px;align-items:center;padding:12px;border:1px solid #e2e8f0;border-radius:18px}
.trend-copy strong{display:block}
.trend-copy span{display:block;margin-top:4px;color:#64748b;font-size:12px}
.trend-bars{display:grid;gap:8px}
.bar{height:10px;border-radius:999px}
.bar.in{background:linear-gradient(90deg,#0ea5e9,#22d3ee)}
.bar.out{background:linear-gradient(90deg,#fb923c,#f97316)}
.feed-list{display:grid;gap:10px;max-height:720px;overflow:auto;padding-left:4px}
.feed-item{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;padding:12px;border-radius:18px;background:#f8fafc;border:1px solid #e2e8f0}
.feed-badge{display:grid;place-items:center;min-width:52px;height:38px;border-radius:12px;font-size:12px;font-weight:900}
.feed-badge.in{background:#dcfce7;color:#166534}
.feed-badge.out{background:#ffedd5;color:#c2410c}
.feed-copy strong{display:block}
.feed-copy p{margin:4px 0 0;color:#64748b;font-size:12px}
.error-box{padding:12px 14px;border-radius:18px;background:#fef2f2;color:#b91c1c;border:1px solid #fecaca}
@media (max-width:1280px){.content-grid,.reports-hero{grid-template-columns:1fr}.hero-panel{grid-template-columns:1fr}.hero-stats{grid-template-columns:repeat(3,minmax(0,1fr))}.hero-panel .hero-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.reports-filters-card{grid-template-columns:repeat(2,minmax(0,1fr))}.search-wide{grid-column:1/-1}}
@media (max-width:900px){.toolbar-card{grid-template-columns:1fr 1fr}.search-field{grid-column:1/-1}.worker-meta{grid-template-columns:repeat(2,minmax(0,1fr))}.qr-row{grid-template-columns:1fr}.qr-frame{justify-self:center}}
@media (max-width:640px){.section-card,.hero-panel,.reports-hero{border-radius:24px}.toolbar-card,.kpi-grid,.reports-filters-card{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-stats{grid-template-columns:repeat(3,minmax(0,1fr))}.hero-panel .hero-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.worker-head,.feed-item{grid-template-columns:1fr}.status-pill{justify-self:start}.trend-item{grid-template-columns:1fr}.section-head{flex-direction:column;align-items:stretch}.hero-copy h2,.reports-hero h2{font-size:26px}.hero-panel,.section-card,.reports-hero{padding:16px}.qr-frame{width:100%;height:auto;aspect-ratio:1/1;max-width:180px}.meta-chip strong{font-size:14px}.hero-stat{padding:12px 10px;border-radius:16px}.hero-stat strong{font-size:18px}.worker-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.primary-btn,.secondary-btn,.ghost-inline-btn,.danger-inline-btn{padding:0 10px;font-size:12px}.search-wide{grid-column:1/-1}.report-table th,.report-table td{font-size:11px}}
</style>
