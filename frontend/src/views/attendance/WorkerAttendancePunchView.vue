<template>
  <div class="attendance-screen" dir="rtl">
    <div class="ambient ambient-one"></div>
    <div class="ambient ambient-two"></div>

    <main class="attendance-shell">
      <section class="hero-card">
        <div class="hero-copy">
          <span class="eyebrow">حضور و غیاب پرسنل</span>
          <h1>{{ workerName }}</h1>
          <p>{{ tenantName || 'کارواش' }} · {{ statusLabel }}</p>
        </div>
        <div class="status-orb" :class="workerState.current_status || 'out'">
          <strong>{{ workerState.current_status === 'in' ? 'ON' : 'OFF' }}</strong>
          <span>{{ workerState.current_status === 'in' ? 'حاضر در شیفت' : 'خارج از شیفت' }}</span>
        </div>
      </section>

      <section class="panel-grid">
        <article class="glass-card action-card">
          <div class="card-head">
            <div>
              <span class="card-kicker">ثبت سریع</span>
              <h2>ورود و خروج امروز</h2>
            </div>
            <span class="clock">{{ nowLabel }}</span>
          </div>

          <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>
          <div v-if="successMessage" class="success-box">{{ successMessage }}</div>

          <div class="action-grid">
            <button class="action-btn checkin" :disabled="submitting || workerState.current_status === 'in'" @click="submitAttendance('in')">
              <span>ثبت ورود</span>
              <small>{{ workerState.current_status === 'in' ? 'قبلاً ثبت شده' : 'شروع شیفت' }}</small>
            </button>
            <button class="action-btn checkout" :disabled="submitting || workerState.current_status !== 'in'" @click="submitAttendance('out')">
              <span>{{ submitting ? 'در حال ثبت...' : 'ثبت خروج' }}</span>
              <small>{{ workerState.current_status === 'in' ? 'پایان شیفت' : 'ابتدا ورود ثبت شود' }}</small>
            </button>
          </div>

          <label class="note-field">
            <span>یادداشت</span>
            <textarea v-model.trim="note" rows="3" placeholder="مثلاً شروع شیفت عصر یا خروج برای مأموریت کوتاه"></textarea>
          </label>
        </article>

        <article class="glass-card stats-card">
          <div class="card-head">
            <div>
              <span class="card-kicker">وضعیت روز</span>
              <h2>خلاصه امروز</h2>
            </div>
          </div>
          <div class="stats-grid">
            <div class="stat-chip">
              <span>ساعت کار امروز</span>
              <strong>{{ workedHoursLabel }}</strong>
            </div>
            <div class="stat-chip">
              <span>تعداد ثبت‌ها</span>
              <strong>{{ toFa(workerState.today_events_count || 0) }}</strong>
            </div>
            <div class="stat-chip">
              <span>آخرین وضعیت</span>
              <strong>{{ statusLabel }}</strong>
            </div>
            <div class="stat-chip">
              <span>آخرین ثبت</span>
              <strong>{{ lastEventLabel }}</strong>
            </div>
          </div>

          <div class="timeline-shell">
            <div class="timeline-head">
              <h3>رویدادهای امروز</h3>
            </div>
            <div v-if="todayEvents.length" class="timeline-list">
              <article v-for="event in todayEvents" :key="event.id" class="timeline-item">
                <div class="event-dot" :class="event.event_type"></div>
                <div class="event-copy">
                  <strong>{{ event.event_type === 'in' ? 'ورود' : 'خروج' }}</strong>
                  <p>{{ dateTime(event.event_at) }}</p>
                </div>
                <small>{{ event.note || event.source }}</small>
              </article>
            </div>
            <p v-else class="empty-copy">هنوز ثبت حضوری برای امروز انجام نشده است.</p>
          </div>
        </article>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../services/api'
import { formatJalaliDateTime } from '../../utils/date'
import { resolveApiErrorMessage } from '../../utils/apiError'

const route = useRoute()
const note = ref('')
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const payload = ref({ worker: {}, tenant_name: '', last_event: null, today_events: [], server_time: '' })
const timer = ref(null)
const nowLabel = ref('')

const workerState = computed(() => payload.value.worker || {})
const todayEvents = computed(() => payload.value.today_events || [])
const tenantName = computed(() => payload.value.tenant_name || '')
const workerName = computed(() => workerState.value.full_name || 'پرسنل')
const statusLabel = computed(() => (workerState.value.current_status === 'in' ? 'حاضر در شیفت' : 'خارج از شیفت'))
const lastEventLabel = computed(() => payload.value.last_event?.event_at ? dateTime(payload.value.last_event.event_at) : 'بدون ثبت')
const workedHoursLabel = computed(() => `${toFa(workerState.value.today_worked_hours || 0)} ساعت`)

const toFa = (value) => Number(value || 0).toLocaleString('fa-IR')
const dateTime = (value) => formatJalaliDateTime(value)

const tickClock = () => {
  nowLabel.value = new Intl.DateTimeFormat('fa-IR-u-ca-persian', { hour: '2-digit', minute: '2-digit' }).format(new Date())
}

const loadData = async () => {
  try {
    const { data } = await api.get(`/workers/attendance/public/${route.params.token}/`, { meta: { trackLoading: false } })
    payload.value = data || {}
    errorMessage.value = ''
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بارگذاری صفحه حضور و غیاب ناموفق بود.')
  }
}

const submitAttendance = async (eventType) => {
  submitting.value = true
  successMessage.value = ''
  errorMessage.value = ''
  try {
    const { data } = await api.post(`/workers/attendance/public/${route.params.token}/`, {
      event_type: eventType,
      note: note.value || undefined
    })
    successMessage.value = data?.detail || 'ثبت با موفقیت انجام شد.'
    note.value = ''
    await loadData()
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'ثبت حضور و غیاب انجام نشد.')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  tickClock()
  timer.value = window.setInterval(tickClock, 30000)
  await loadData()
})

onBeforeUnmount(() => {
  if (timer.value) window.clearInterval(timer.value)
})
</script>

<style scoped>
.attendance-screen{position:relative;min-height:100vh;overflow:hidden;background:radial-gradient(circle at top right,#d8f3ff 0,#f5fbff 38%,#f7f8fc 100%);color:#0f172a}
.ambient{position:absolute;border-radius:999px;filter:blur(10px);opacity:.45}
.ambient-one{top:-80px;right:-40px;width:260px;height:260px;background:linear-gradient(135deg,#38bdf8,#93c5fd)}
.ambient-two{left:-100px;bottom:-120px;width:320px;height:320px;background:linear-gradient(135deg,#bfdbfe,#67e8f9)}
.attendance-shell{position:relative;z-index:1;max-width:1120px;margin:0 auto;padding:32px 18px 48px}
.hero-card{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:24px;border:1px solid rgba(255,255,255,.7);border-radius:28px;background:rgba(255,255,255,.72);box-shadow:0 22px 60px rgba(15,23,42,.08);backdrop-filter:blur(16px)}
.eyebrow{display:inline-flex;padding:6px 12px;border-radius:999px;background:#e0f2fe;color:#0369a1;font-size:12px;font-weight:700}
.hero-copy h1{margin:14px 0 6px;font-size:clamp(26px,4vw,42px)}
.hero-copy p{margin:0;color:#475569}
.status-orb{min-width:180px;padding:22px;border-radius:24px;color:#fff;text-align:center;box-shadow:0 16px 34px rgba(15,23,42,.18)}
.status-orb.in{background:linear-gradient(135deg,#059669,#22c55e)}
.status-orb.out{background:linear-gradient(135deg,#0f172a,#334155)}
.status-orb strong{display:block;font-size:34px;letter-spacing:2px}
.status-orb span{display:block;margin-top:8px;font-size:13px;opacity:.9}
.panel-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;margin-top:18px}
.glass-card{padding:22px;border:1px solid rgba(226,232,240,.9);border-radius:28px;background:rgba(255,255,255,.84);box-shadow:0 20px 48px rgba(15,23,42,.08);backdrop-filter:blur(18px)}
.card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:18px}
.card-kicker{display:block;color:#0284c7;font-size:12px;font-weight:700}
.card-head h2{margin:8px 0 0;font-size:22px}
.clock{padding:8px 12px;border-radius:999px;background:#eff6ff;color:#1d4ed8;font-size:12px;font-weight:700}
.action-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.action-btn{display:grid;gap:8px;padding:18px;border:none;border-radius:22px;color:#fff;text-align:right;cursor:pointer;transition:transform .18s ease,opacity .18s ease,box-shadow .18s ease}
.action-btn span{font-size:18px;font-weight:800}
.action-btn small{opacity:.88}
.action-btn.checkin{background:linear-gradient(135deg,#0284c7,#06b6d4);box-shadow:0 18px 34px rgba(6,182,212,.24)}
.action-btn.checkout{background:linear-gradient(135deg,#f97316,#fb7185);box-shadow:0 18px 34px rgba(249,115,22,.22)}
.action-btn:hover:not(:disabled){transform:translateY(-2px)}
.action-btn:disabled{opacity:.55;cursor:not-allowed}
.note-field{display:grid;gap:8px;margin-top:18px}
.note-field span{font-size:13px;color:#334155;font-weight:700}
.note-field textarea{resize:vertical;min-height:96px;padding:14px;border:1px solid #dbe5f0;border-radius:18px;background:#f8fbff;font:inherit}
.stats-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.stat-chip{padding:16px;border:1px solid #dbeafe;border-radius:20px;background:linear-gradient(180deg,#ffffff,#f0f9ff)}
.stat-chip span{display:block;color:#64748b;font-size:12px}
.stat-chip strong{display:block;margin-top:10px;font-size:20px}
.timeline-shell{margin-top:18px;padding-top:18px;border-top:1px solid #e2e8f0}
.timeline-head h3{margin:0 0 12px;font-size:16px}
.timeline-list{display:grid;gap:10px}
.timeline-item{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:10px;padding:12px 14px;border:1px solid #e2e8f0;border-radius:18px;background:#fff}
.event-dot{width:12px;height:12px;border-radius:999px}
.event-dot.in{background:#10b981;box-shadow:0 0 0 6px rgba(16,185,129,.12)}
.event-dot.out{background:#f97316;box-shadow:0 0 0 6px rgba(249,115,22,.12)}
.event-copy strong{display:block}
.event-copy p{margin:4px 0 0;color:#64748b;font-size:12px}
.empty-copy{margin:0;color:#64748b}
.error-box,.success-box{margin-bottom:14px;padding:12px 14px;border-radius:16px;font-size:13px}
.error-box{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca}
.success-box{background:#ecfdf5;color:#047857;border:1px solid #a7f3d0}
@media (max-width:900px){.panel-grid{grid-template-columns:1fr}.hero-card{flex-direction:column;align-items:flex-start}.status-orb{width:100%}}
@media (max-width:640px){.attendance-shell{padding:18px 12px 28px}.hero-card,.glass-card{border-radius:24px;padding:18px}.action-grid,.stats-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.card-head,.timeline-item{grid-template-columns:1fr}.clock{justify-self:start}.status-orb{min-width:0}.timeline-item{padding:12px}.action-btn span{font-size:15px}.action-btn small,.stat-chip span{font-size:11px}.stat-chip strong{font-size:16px}}
</style>
