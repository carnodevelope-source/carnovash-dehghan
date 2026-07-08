<template>
  <AppShell title="حضور و غیاب" subtitle="پایش لحظه‌ای شیفت‌ها، لینک اختصاصی نیروها و لاگ ورود و خروج">
    <div class="attendance-view">
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
          <article class="hero-stat">
            <span>ساعت کار امروز</span>
            <strong>{{ toFa(summary.today_worked_hours || 0) }}</strong>
          </article>
        </div>
      </section>

      <section class="toolbar-card">
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

      <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>

      <section class="content-grid">
        <div class="workers-column">
          <section class="section-card">
            <header class="section-head">
              <div>
                <span class="section-kicker">Team Access Cards</span>
                <h3>کارت نیروها و لینک اختصاصی</h3>
              </div>
              <strong>{{ toFa(filteredWorkers.length) }} نفر</strong>
            </header>

            <div class="workers-grid">
              <article v-for="worker in filteredWorkers" :key="worker.id" class="worker-card" :class="worker.current_status">
                <div class="worker-head">
                  <div class="avatar">{{ worker.avatar }}</div>
                  <div class="worker-copy">
                    <strong>{{ worker.full_name }}</strong>
                    <span>{{ worker.phone || 'بدون شماره' }}</span>
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
                    <span>سفارش فعال</span>
                    <strong>{{ toFa(worker.active_jobs_count || 0) }}</strong>
                  </div>
                  <div class="meta-chip">
                    <span>بار کاری</span>
                    <strong>{{ loadLabel(worker.load_status) }}</strong>
                  </div>
                </div>

                <div class="qr-row">
                  <img class="qr-frame" :src="qrSrc(worker)" :alt="`QR ${worker.full_name}`" loading="lazy" />
                  <div class="qr-copy">
                    <span>لینک ورود و خروج</span>
                    <code>{{ fullAttendanceLink(worker) }}</code>
                    <small>برای اسکن یا بازکردن مستقیم توسط نیرو</small>
                  </div>
                </div>

                <div class="worker-actions">
                  <button class="primary-btn" :disabled="submittingWorkerId === worker.id || worker.current_status === 'in'" @click="submitManagerEvent(worker, 'in')">
                    <IconlyIcon name="calendar" size="sm" />ثبت ورود
                  </button>
                  <button class="secondary-btn" :disabled="submittingWorkerId === worker.id || worker.current_status !== 'in'" @click="submitManagerEvent(worker, 'out')">
                    <IconlyIcon name="logout" size="sm" />ثبت خروج
                  </button>
                  <button class="ghost-inline-btn" @click="copyLink(worker)"><IconlyIcon name="document" size="sm" />کپی لینک</button>
                  <button class="ghost-inline-btn" @click="openLink(worker)"><IconlyIcon name="show" size="sm" />باز کردن</button>
                  <button class="danger-inline-btn" @click="refreshToken(worker)"><IconlyIcon name="editSquare" size="sm" />بازسازی لینک</button>
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
import { computed, onMounted, ref } from 'vue'
import AppShell from '../../components/layout/AppShell.vue'
import IconlyIcon from '../../components/base/IconlyIcon.vue'
import api from '../../services/api'
import { formatJalaliDate, formatJalaliDateTime } from '../../utils/date'
import { resolveApiErrorMessage } from '../../utils/apiError'

const summary = ref({})
const workers = ref([])
const trend = ref([])
const recentEvents = ref([])
const errorMessage = ref('')
const submittingWorkerId = ref(null)
const filters = ref({ q: '', status: 'all', load: 'all' })

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

const fullAttendanceLink = (worker) => `${window.location.origin}${worker.attendance_path || `/attendance/${worker.attendance_token}`}`
const qrSrc = (worker) => `https://api.qrserver.com/v1/create-qr-code/?size=132x132&data=${encodeURIComponent(fullAttendanceLink(worker))}`
const barWidth = (value, max) => Math.max(8, Math.round((Number(value || 0) / Math.max(Number(max || 1), 1)) * 100))

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

const submitManagerEvent = async (worker, eventType) => {
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
  try {
    await navigator.clipboard.writeText(fullAttendanceLink(worker))
  } catch (_error) {
    errorMessage.value = 'کپی لینک روی این مرورگر انجام نشد.'
  }
}

const openLink = (worker) => {
  window.open(fullAttendanceLink(worker), '_blank', 'noopener')
}

const refreshToken = async (worker) => {
  try {
    await api.post(`/workers/${worker.id}/attendance-token/refresh/`)
    await loadDashboard()
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بازسازی لینک انجام نشد.')
  }
}

onMounted(loadDashboard)
</script>

<style scoped>
.attendance-view{display:grid;gap:16px}
.hero-panel{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;padding:24px;border-radius:30px;background:linear-gradient(135deg,#0f172a 0%,#0f4c81 48%,#0ea5e9 100%);color:#fff;overflow:hidden;position:relative;box-shadow:0 28px 70px rgba(15,23,42,.22)}
.hero-panel::after{content:'';position:absolute;inset:auto -80px -100px auto;width:240px;height:240px;border-radius:999px;background:radial-gradient(circle,#ffffff55 0,#ffffff00 72%)}
.hero-tag{display:inline-flex;padding:6px 12px;border-radius:999px;background:#ffffff1a;border:1px solid #ffffff2b;font-size:12px;letter-spacing:.04em}
.hero-copy h2{margin:14px 0 10px;font-size:32px}
.hero-copy p{margin:0;max-width:560px;color:#d9ecff;line-height:1.9}
.hero-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
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
.workers-grid{display:grid;gap:14px}
.worker-card{padding:16px;border-radius:24px;border:1px solid #dbeafe;background:linear-gradient(180deg,#ffffff,#f8fbff)}
.worker-card.in{box-shadow:0 16px 36px rgba(16,185,129,.08)}
.worker-card.out{box-shadow:0 16px 36px rgba(59,130,246,.06)}
.worker-head{display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center}
.avatar{display:grid;place-items:center;width:54px;height:54px;border-radius:18px;background:linear-gradient(135deg,#dbeafe,#a5f3fc);font-weight:800;color:#0f172a}
.worker-copy strong{display:block;font-size:17px}
.worker-copy span{display:block;margin-top:4px;color:#64748b;font-size:12px}
.status-pill{display:inline-flex;align-items:center;justify-content:center;padding:8px 12px;border-radius:999px;font-size:12px;font-weight:800}
.status-pill.in{background:#ecfdf5;color:#047857}
.status-pill.out{background:#f1f5f9;color:#334155}
.worker-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}
.meta-chip{padding:12px;border-radius:18px;background:#f8fafc;border:1px solid #e2e8f0}
.meta-chip span{display:block;color:#64748b;font-size:11px}
.meta-chip strong{display:block;margin-top:8px;font-size:15px}
.qr-row{display:grid;grid-template-columns:132px 1fr;gap:14px;margin-top:16px;padding:14px;border-radius:20px;background:linear-gradient(135deg,#eff6ff,#f8fafc)}
.qr-frame{width:132px;height:132px;border-radius:18px;background:#fff;padding:8px;border:1px solid #dbeafe;object-fit:cover}
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
.primary-btn:disabled,.secondary-btn:disabled{opacity:.55;cursor:not-allowed}
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
@media (max-width:1280px){.content-grid{grid-template-columns:1fr}.hero-panel{grid-template-columns:1fr}.hero-stats{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:900px){.toolbar-card{grid-template-columns:1fr 1fr}.search-field{grid-column:1/-1}.worker-meta{grid-template-columns:repeat(2,minmax(0,1fr))}.qr-row{grid-template-columns:1fr}.qr-frame{justify-self:center}}
@media (max-width:640px){.section-card,.hero-panel{border-radius:24px}.toolbar-card,.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-stats{grid-template-columns:repeat(3,minmax(0,1fr))}.worker-head,.feed-item{grid-template-columns:1fr}.status-pill{justify-self:start}.trend-item{grid-template-columns:1fr}.section-head{flex-direction:column;align-items:stretch}.hero-copy h2{font-size:26px}.hero-panel,.section-card{padding:16px}.qr-frame{width:100%;height:auto;aspect-ratio:1/1;max-width:180px}.meta-chip strong{font-size:14px}.hero-stat{padding:12px 10px;border-radius:16px}.hero-stat strong{font-size:18px}.worker-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.primary-btn,.secondary-btn,.ghost-inline-btn,.danger-inline-btn{padding:0 10px;font-size:12px}}
</style>
