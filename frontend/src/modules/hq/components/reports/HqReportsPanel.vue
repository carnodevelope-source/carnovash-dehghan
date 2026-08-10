<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../../../services/api'
import BaseDatePicker from '../../../../components/base/BaseDatePicker.vue'
import { parseJalaliToIso, formatJalaliDate, formatJalaliDateTime } from '../../../../utils/date'
import {
  formatMoney, formatFaNumber, formatPercent, formatPercentChange, formatRelativeDate, deltaTone, signedMoney
} from '../../utils/formatters.js'
import { resolveReportRange, readQueryState, buildQueryPatch } from '../../utils/query-state.js'
import {
  REPORT_WORKSPACES, REPORT_RANGE_OPTIONS, HQ_SHARE_FEATURE_ORDER, HQ_SHARE_FEATURE_LABELS, TENANT_REPORT_TABS
} from '../../constants/hq-report-tabs.js'
import HqPageHeader from '../shared/HqPageHeader.vue'
import HqKpiCard from '../shared/HqKpiCard.vue'
import HqStatusBadge from '../shared/HqStatusBadge.vue'
import HqEmptyState from '../shared/HqEmptyState.vue'
import HqTrendChart from '../shared/HqTrendChart.vue'
import '../../styles/hq-ui.css'

const props = defineProps({ carwashes: { type: Array, default: () => [] } })

const route = useRoute()
const router = useRouter()

const defaultRange = resolveReportRange('month')
const ui = reactive({
  workspace: 'internal', networkTab: 'revenue', rangeKey: 'month',
  start: defaultRange.start, end: defaultRange.end, compare: false,
  tenant: '', tenantTab: 'overall', hqShare: 'sms_wallet', health: ''
})
const snap = reactive({
  summary: {}, rows: [], trends: [], feature_summary: [], wallet_transactions: [], highlights: {}, fetchedAt: null
})
const load = reactive({ main: false, mainError: '', refreshing: false })
const tenant = reactive({ loading: false, error: '', data: null })
const carwashSearch = ref('')
const carwashActivity = ref('all')
const showExtraKpis = ref(false)
const walletDrawer = reactive({ open: false, tenantId: null, tab: 'all' })
const ledger = reactive({ search: '', walletType: '', direction: '', shareGroup: '' })
const walletAttention = ref(false)

const paymentPlanLabel = (v) => ({ cash: 'نقدی', installment: 'قسطی', manual: 'دستی', wallet: 'کیف پول' }[v] || 'نامشخص')
const paymentMethodLabel = (v) => ({ cash: 'نقد', card: 'کارت', pos: 'POS', cheque: 'چک', online: 'آنلاین', wallet: 'کیف پول' }[v] || v || '—')
const paymentStatusLabel = (v) => ({ success: 'موفق', pending: 'در انتظار', failed: 'ناموفق', refunded: 'برگشت' }[v] || v || '—')
const attendanceEventLabel = (v) => ({ check_in: 'ورود', check_out: 'خروج' }[v] || v || '—')
const plateTypeLabel = (v) => ({ car: 'خودرو', motorcycle: 'موتور' }[v] || v || '—')

function syncQuery(patch) {
  router.replace({ query: buildQueryPatch({ ...route.query, tab: 'reports' }, patch) })
}
function applyQueryFromRoute() {
  const q = readQueryState(route, {
    workspace: 'internal', networkTab: 'revenue', range: 'month', start: defaultRange.start, end: defaultRange.end,
    compare: '', tenant: '', tenantTab: 'overall', hqShare: 'sms_wallet', health: ''
  })
  ui.workspace = q.workspace
  ui.networkTab = q.networkTab
  ui.rangeKey = q.range || 'month'
  ui.compare = q.compare === '1'
  ui.tenant = q.tenant
  ui.tenantTab = q.tenantTab
  ui.hqShare = q.hqShare
  ui.health = q.health
  if (q.start || q.end) { ui.start = q.start; ui.end = q.end }
  else if (ui.rangeKey !== 'all') { const r = resolveReportRange(ui.rangeKey); ui.start = r.start; ui.end = r.end }
  else { ui.start = ''; ui.end = '' }
}
function pushUiState(extra = {}) {
  syncQuery({
    workspace: ui.workspace, networkTab: ui.networkTab, range: ui.rangeKey, start: ui.start, end: ui.end,
    compare: ui.compare && ui.start && ui.end, tenant: ui.tenant, tenantTab: ui.tenantTab,
    hqShare: ui.hqShare, health: ui.health, ...extra
  })
}
function setRange(key) {
  ui.rangeKey = key
  const r = resolveReportRange(key)
  ui.start = r.start
  ui.end = r.end
  pushUiState()
  loadReports()
  if (ui.tenant) loadTenantReport()
}
function onCustomDate() {
  ui.rangeKey = 'custom'
}
function setWorkspace(key) { ui.workspace = key; pushUiState() }

async function loadReports() {
  if (!snap.fetchedAt) load.main = true
  else load.refreshing = true
  load.mainError = ''
  try {
    const { data } = await api.get('/auth/hq/reports/', {
      params: { start: parseJalaliToIso(ui.start) || undefined, end: parseJalaliToIso(ui.end) || undefined }
    })
    Object.assign(snap, {
      summary: data?.summary || {}, rows: data?.rows || [], trends: data?.trends || [],
      feature_summary: data?.feature_summary || [], wallet_transactions: data?.wallet_transactions || [],
      highlights: data?.highlights || {}, fetchedAt: new Date().toISOString()
    })
  } catch (e) {
    load.mainError = 'دریافت گزارش مرکزی ناموفق بود. دوباره تلاش کنید.'
    if (!snap.fetchedAt) { snap.summary = {}; snap.rows = [] }
  } finally { load.main = false; load.refreshing = false }
}

async function loadTenantReport() {
  const id = Number(ui.tenant || 0)
  if (!id) { tenant.data = null; return }
  tenant.loading = true
  tenant.error = ''
  try {
    const { data } = await api.get(`/auth/hq/carwashes/${id}/reports/`, {
      params: { start: parseJalaliToIso(ui.start) || undefined, end: parseJalaliToIso(ui.end) || undefined }
    })
    tenant.data = data || null
  } catch (e) {
    tenant.error = 'دریافت گزارش کارواش انتخابی ناموفق بود.'
    tenant.data = null
  } finally { tenant.loading = false }
}

const freshnessLabel = computed(() => snap.fetchedAt ? `آخرین بروزرسانی ${formatJalaliDateTime(snap.fetchedAt)}` : '')
const periodLabel = computed(() => {
  if (ui.start && ui.end) return `${ui.start} تا ${ui.end}`
  if (ui.start) return `از ${ui.start}`
  if (ui.end) return `تا ${ui.end}`
  return 'کل تاریخ'
})
const canCompare = computed(() => Boolean(ui.start && ui.end))
const showDelta = computed(() => ui.compare && canCompare.value)

const rowMap = computed(() => {
  const m = new Map()
  ;(snap.rows || []).forEach((r) => m.set(Number(r.tenant_id), r))
  return m
})

const workspaceBadges = computed(() => ({
  internal: (snap.rows || []).filter((r) => r.health === 'risk' && Number(r.rah_share_total) > 0).length
    + (Number(snap.summary.feature_remaining_total) > 0 ? 1 : 0),
  carwash: ui.tenant ? 1 : 0,
  wallet: (snap.rows || []).filter((r) => r.wallet_charge_health === 'empty').length,
  network: (snap.rows || []).filter((r) => r.health === 'risk').length
}))

const carnoHint = computed(() => {
  const parts = []
  const total = Number(snap.summary.hq_share_total || 0)
  if (!total) return ''
  ;(snap.feature_summary || []).forEach((f) => {
    const amt = Number(f.paid_amount || 0)
    if (amt > 0) parts.push(`${f.tab_label || f.label} ${formatPercent((amt / total) * 100)}`)
  })
  const sms = Number(snap.summary.sms_cost_total || 0)
  if (sms > 0) parts.push(`پیامک ${formatPercent((sms / total) * 100)}`)
  return parts.slice(0, 3).join(' · ')
})
const rahHint = computed(() => {
  const n = (snap.rows || []).filter((r) => Number(r.rah_share_total) > 0).length
  return n ? `${formatFaNumber(n)} شعبه دارای سهم` : ''
})
const featureHint = computed(() => {
  const r = Number(snap.summary.feature_remaining_total || 0)
  return r > 0 ? 'نیاز به پیگیری تسویه' : 'بدون مانده'
})

const shareTrends = computed(() => {
  const rows = [...(snap.trends || [])]
    .filter((t) => t?.date)
    .sort((a, b) => String(a.date).localeCompare(String(b.date)))
    .map((t) => ({
      date: t.date,
      hq_share_total: Number(t.hq_share_total || 0),
      rah_share_total: Number(t.rah_share_total || 0),
      wallet_deposit_total: Number(t.wallet_deposit_total || 0),
      wallet_withdraw_total: Number(t.wallet_withdraw_total || 0),
      paid_amount: Number(t.paid_amount || 0),
      net_amount: Number(t.net_amount || 0),
      sms_cost_total: Number(t.sms_cost_total || 0)
    }))
  // Keep chart readable: prefer last ~45 daily points for denser real trends.
  return rows.length > 45 ? rows.slice(-45) : rows
})
const shareSeries = [
  { key: 'hq_share_total', label: 'کارنو', color: '#1976d2', fill: 'rgba(25, 118, 210, 0.22)' },
  { key: 'rah_share_total', label: 'آراکار', color: '#7c3aed', fill: 'rgba(124, 58, 237, 0.18)' }
]

const compositionItems = computed(() => {
  const items = (snap.feature_summary || []).map((f) => ({
    key: f.key, label: f.tab_label || f.label, amount: Number(f.paid_amount || 0)
  }))
  const sms = Number(snap.summary.sms_cost_total || 0)
  if (sms) items.push({ key: 'sms', label: 'هزینه SMS', amount: sms })
  const total = items.reduce((s, i) => s + i.amount, 0) || 1
  return items.map((i) => ({ ...i, pct: (i.amount / total) * 100 })).filter((i) => i.amount > 0)
})

const hqShareTabs = computed(() => HQ_SHARE_FEATURE_ORDER.map((key) => ({
  key, label: HQ_SHARE_FEATURE_LABELS[key] || key,
  count: key === 'sms_wallet'
    ? filteredSmsRows.value.length
    : hqFeatureRows(key).length
})))

function hqFeatureRows(featureKey) {
  if (featureKey === 'sms_wallet') return filteredSmsRows.value
  if (featureKey === 'excel_import') {
    const purchases = (snap.rows || []).map((row) => ({
      tenant_id: row.tenant_id, tenant_name: row.tenant_name,
      feature: (row.feature_breakdown || []).find((f) => f.feature_key === featureKey),
      isVirtual: false
    })).filter((r) => r.feature)
    const virtual = (snap.wallet_transactions || [])
      .filter((t) => t.reference_type === 'customer_import_excel' && t.share_group === 'hq')
      .map((t) => ({
        tenant_id: t.tenant_id, tenant_name: t.tenant_name, isVirtual: true,
        feature: { label: 'وارد کردن مشتریان با اکسل', payment_plan: 'wallet', paid_amount: t.share_amount || t.amount, remaining_amount: 0, installment_months: 0, share_group: 'hq' }
      }))
    return [...purchases, ...virtual]
  }
  return (snap.rows || []).map((row) => ({
    tenant_id: row.tenant_id, tenant_name: row.tenant_name,
    feature: (row.feature_breakdown || []).find((f) => f.feature_key === featureKey)
  })).filter((r) => r.feature)
}

const filteredSmsRows = computed(() => (snap.wallet_transactions || [])
  .filter((t) => t.wallet_type === 'sms' && t.direction === 'out' && t.share_group === 'hq'))
const activeHqShareRows = computed(() => hqFeatureRows(ui.hqShare))
const hqShareFooterSum = computed(() => activeHqShareRows.value.reduce((s, r) => {
  if (ui.hqShare === 'sms_wallet') return s + Number(r.share_amount || r.amount || 0)
  return s + Number(r.feature?.paid_amount || 0)
}, 0))

const rahRows = computed(() => {
  let rows = (snap.rows || []).filter((r) => Number(r.rah_share_total) > 0)
  if (ui.health) rows = rows.filter((r) => r.health === ui.health)
  return rows.sort((a, b) => Number(b.rah_share_total || 0) - Number(a.rah_share_total || 0))
})

const activeCarwashes = computed(() => (props.carwashes || []).filter((c) => c.is_active !== false))
const carwashList = computed(() => {
  const q = carwashSearch.value.trim().toLowerCase()
  return activeCarwashes.value.filter((c) => {
    if (q && !`${c.name} ${c.address || ''}`.toLowerCase().includes(q)) return false
    const row = rowMap.value.get(Number(c.id))
    const active = row && (row.vehicles_count || row.paid_amount || row.last_activity_at)
    if (carwashActivity.value === 'active') return Boolean(active)
    if (carwashActivity.value === 'idle') return !active
    return true
  }).map((c) => ({ ...c, report: rowMap.value.get(Number(c.id)) || null }))
})
const selectedCarwash = computed(() => activeCarwashes.value.find((c) => String(c.id) === String(ui.tenant)))
const tenantSummary = computed(() => tenant.data?.summary || {})
const tenantRows = computed(() => {
  const tab = TENANT_REPORT_TABS.find((t) => t.key === ui.tenantTab)
  if (!tab || !tenant.data) return []
  return Array.isArray(tenant.data[tab.rowsKey]) ? tenant.data[tab.rowsKey] : []
})
const tenantTabCounts = computed(() => TENANT_REPORT_TABS.reduce((acc, tab) => {
  acc[tab.key] = Array.isArray(tenant.data?.[tab.rowsKey]) ? tenant.data[tab.rowsKey].length : 0
  return acc
}, {}))

const tenantColumns = computed(() => ({
  overall: [['driver_name', 'راننده'], ['plate_number', 'پلاک'], ['status', 'وضعیت'], ['final_total', 'نهایی'], ['carwash_share', 'کارواش'], ['worker_share', 'نیرو'], ['discount_total', 'تخفیف'], ['tip_amount', 'انعام'], ['worker_name', 'نیرو'], ['services', 'خدمات'], ['created_at', 'تاریخ']],
  carwash: [['driver_name', 'راننده'], ['plate_number', 'پلاک'], ['carwash_share', 'حق کارواش'], ['worker_name', 'نیرو'], ['created_at', 'تاریخ']],
  worker: [['driver_name', 'راننده'], ['plate_number', 'پلاک'], ['worker_share', 'حق نیرو'], ['worker_name', 'نیرو'], ['created_at', 'تاریخ']],
  tips: [['driver_name', 'راننده'], ['plate_number', 'پلاک'], ['tip_amount', 'انعام'], ['worker_name', 'نیرو'], ['products', 'کالا'], ['created_at', 'تاریخ']],
  revenue: [['created_at', 'تاریخ'], ['driver_name', 'راننده'], ['payment_method', 'روش'], ['payment_status', 'وضعیت'], ['final_total', 'نهایی'], ['received_amount', 'دریافتی'], ['outstanding_amount', 'مانده']],
  attendance: [['worker_name', 'نیرو'], ['event_type', 'رویداد'], ['source', 'منبع'], ['event_at', 'زمان']],
  blacklist: [['plate_number', 'پلاک'], ['plate_type', 'نوع'], ['note', 'یادداشت'], ['blocked_by_name', 'ثبت‌کننده'], ['created_at', 'تاریخ']]
}[ui.tenantTab] || []))

function tenantCell(row, col) {
  const [key, , type] = col
  const v = row[key]
  if (type === 'money') return formatMoney(v)
  if (key === 'created_at' || key === 'event_at') return formatJalaliDateTime(v)
  if (key === 'payment_method') return paymentMethodLabel(v)
  if (key === 'payment_status') return paymentStatusLabel(v)
  if (key === 'event_type') return attendanceEventLabel(v)
  if (key === 'plate_type') return plateTypeLabel(v)
  return v ?? '—'
}

const walletNetFlow = computed(() => Number(snap.summary.wallet_deposit_total || 0) - Number(snap.summary.wallet_withdraw_total || 0))
const walletTrends = computed(() => (snap.trends || []).slice(-12))
const walletTrendMax = computed(() => Math.max(...walletTrends.value.map((t) => Math.max(Number(t.wallet_deposit_total || 0), Number(t.wallet_withdraw_total || 0))), 1))

const ledgerRows = computed(() => {
  let rows = [...(snap.wallet_transactions || [])]
  const q = ledger.search.trim().toLowerCase()
  if (q) rows = rows.filter((r) => `${r.tenant_name} ${r.description} ${r.reference_type}`.toLowerCase().includes(q))
  if (ledger.walletType === 'sms') rows = rows.filter((r) => r.wallet_type === 'sms')
  else if (ledger.walletType === 'regular') rows = rows.filter((r) => r.wallet_type !== 'sms')
  if (ledger.direction) rows = rows.filter((r) => r.direction === ledger.direction)
  if (ledger.shareGroup) rows = rows.filter((r) => r.share_group === ledger.shareGroup)
  return rows.sort((a, b) => new Date(b.transacted_at || 0) - new Date(a.transacted_at || 0))
})

const drawerRow = computed(() => (snap.rows || []).find((r) => Number(r.tenant_id) === Number(walletDrawer.tenantId)))
const drawerTxs = computed(() => {
  let txs = (snap.wallet_transactions || []).filter((t) => Number(t.tenant_id) === Number(walletDrawer.tenantId))
  if (walletDrawer.tab === 'in') txs = txs.filter((t) => t.direction === 'in')
  if (walletDrawer.tab === 'out') txs = txs.filter((t) => t.direction === 'out')
  if (walletDrawer.tab === 'sms') txs = txs.filter((t) => t.wallet_type === 'sms')
  return txs
})

const networkRows = computed(() => {
  let rows = [...(snap.rows || [])]
  if (ui.networkTab === 'revenue') rows.sort((a, b) => Number(b.paid_amount || 0) - Number(a.paid_amount || 0))
  else {
    if (walletAttention.value) rows = rows.filter((r) => ['empty', 'idle'].includes(r.wallet_charge_health))
    rows.sort((a, b) => Number(b.wallet_balance || 0) - Number(a.wallet_balance || 0))
  }
  return rows
})
const networkTrendMax = computed(() => Math.max(...walletTrends.value.map((t) => Math.max(Number(t.paid_amount || 0), Number(t.net_amount || 0))), 1))
const rankLabel = (i) => formatFaNumber(i + 1)

function openWalletDrawer(id) { walletDrawer.tenantId = id; walletDrawer.open = true; walletDrawer.tab = 'all' }
function selectTenant(id) { ui.tenant = String(id); pushUiState() }

watch(() => route.query, (q, prev) => {
  const keys = ['workspace', 'networkTab', 'range', 'start', 'end', 'compare', 'tenant', 'tenantTab', 'hqShare', 'health']
  const changed = keys.some((k) => String(q?.[k] || '') !== String(prev?.[k] || ''))
  if (changed) applyQueryFromRoute()
})

let rangeTimer = null
watch([() => ui.start, () => ui.end], () => {
  if (rangeTimer) clearTimeout(rangeTimer)
  rangeTimer = setTimeout(() => {
    pushUiState()
    loadReports()
    if (ui.tenant) loadTenantReport()
  }, 250)
})
watch(() => ui.tenant, () => { pushUiState(); loadTenantReport() })
watch(() => ui.workspace, () => pushUiState())
watch(() => ui.tenantTab, () => pushUiState())
watch(() => ui.hqShare, () => pushUiState())
watch(() => ui.health, () => pushUiState())
watch(() => ui.networkTab, () => pushUiState())
watch(() => ui.compare, () => pushUiState())

onMounted(() => { applyQueryFromRoute(); loadReports(); if (ui.tenant) loadTenantReport() })
</script>

<template>
  <div class="hq-reports hq-surface" dir="rtl">
    <HqPageHeader breadcrumb="پنل HQ / گزارشات" title="گزارشات مرکزی"
      subtitle="سهم کارنو و آراکار، کیف پول و عملکرد شعب در یک نما"
      :freshness="freshnessLabel">
      <template #actions>
        <button type="button" class="hq-btn primary" :disabled="load.refreshing" @click="loadReports">
          <span v-if="load.refreshing" class="spin" /> بروزرسانی
        </button>
      </template>
    </HqPageHeader>

    <div class="control-bar">
      <div class="range-chips">
        <button v-for="opt in REPORT_RANGE_OPTIONS" :key="opt.key" type="button"
          class="chip" :class="{ active: ui.rangeKey === opt.key }" @click="setRange(opt.key)">{{ opt.label }}</button>
      </div>
      <div class="date-row">
        <BaseDatePicker v-model="ui.start" placeholder="از تاریخ" @update:model-value="onCustomDate" />
        <BaseDatePicker v-model="ui.end" placeholder="تا تاریخ" @update:model-value="onCustomDate" />
        <label v-if="canCompare" class="compare-toggle">
          <input v-model="ui.compare" type="checkbox" /> مقایسه با دوره قبل
        </label>
      </div>
      <div class="control-meta">
        <span>{{ periodLabel }}</span>
        <button type="button" class="hq-btn ghost sm" :disabled="load.refreshing" @click="loadReports">
          <span v-if="load.refreshing" class="spin sm" /> تازه‌سازی
        </button>
      </div>
    </div>

    <div class="workspace-tabs" role="tablist">
      <button v-for="ws in REPORT_WORKSPACES" :key="ws.key" type="button" role="tab"
        class="ws-tab" :class="{ active: ui.workspace === ws.key }" @click="setWorkspace(ws.key)">
        <span class="ws-icon" :data-icon="ws.icon" />
        <span class="ws-copy"><strong>{{ ws.label }}</strong><small>{{ ws.hint }}</small></span>
        <span v-if="workspaceBadges[ws.key]" class="ws-badge">{{ formatFaNumber(workspaceBadges[ws.key]) }}</span>
      </button>
    </div>

    <div v-if="load.mainError" class="section-error">
      <p>{{ load.mainError }}</p>
      <button type="button" class="hq-btn primary sm" @click="loadReports">تلاش مجدد</button>
    </div>

    <!-- INTERNAL -->
    <section v-else-if="ui.workspace === 'internal'" class="panel">
      <div class="kpi-row">
        <HqKpiCard label="سهم کارنو" :value="formatMoney(snap.summary.hq_share_total)" tone="carno"
          tooltip="فقط wallet OUT گروه hq" :hint="carnoHint" />
        <HqKpiCard label="سهم آراکار" :value="formatMoney(snap.summary.rah_share_total)" tone="arakar"
          tooltip="فقط wallet OUT گروه rah" :hint="rahHint" />
        <HqKpiCard label="مانده اقساط آپشن‌ها" :value="formatMoney(snap.summary.feature_remaining_total)"
          :tone="Number(snap.summary.feature_remaining_total) > 0 ? 'warning' : 'default'" :hint="featureHint" />
      </div>

      <div class="analysis-grid">
        <article class="chart-card trend-card">
          <div class="chart-head">
            <h3>روند سهم‌ها</h3>
            <p>بر اساس تراکنش‌های واقعی بازه انتخابی — شناور برای جزئیات روزانه</p>
          </div>
          <HqTrendChart :points="shareTrends" :series="shareSeries" :height="240" />
        </article>
        <article class="chart-card comp">
          <h3>ترکیب سهم کارنو</h3>
          <ul v-if="compositionItems.length" class="comp-list">
            <li v-for="item in compositionItems" :key="item.key">
              <span>{{ item.label }}</span><strong>{{ formatMoney(item.amount) }}</strong><em>{{ formatPercent(item.pct) }}</em>
            </li>
          </ul>
          <HqEmptyState v-else title="بدون ترکیب" description="در این بازه منبع سهم کارنو ثبت نشده است." />
        </article>
      </div>

      <div class="seg-tabs" role="tablist">
        <button v-for="tab in hqShareTabs" :key="tab.key" type="button" role="tab"
          :class="{ active: ui.hqShare === tab.key }" @click="ui.hqShare = tab.key; pushUiState()">
          {{ tab.label }} <span class="count">{{ formatFaNumber(tab.count) }}</span>
        </button>
      </div>

      <div class="hq-table-wrap">
        <table>
          <thead>
            <tr v-if="ui.hqShare === 'sms_wallet'">
              <th>کارواش</th><th>کیف</th><th>نوع</th><th>مبلغ</th><th>شرح</th><th>زمان</th><th>سهم</th>
            </tr>
            <tr v-else>
              <th>کارواش</th><th>قابلیت</th><th>پلن</th><th>پرداخت‌شده</th><th>مانده</th><th>اقساط</th><th>سهم</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in activeHqShareRows" :key="`${ui.hqShare}-${row.tenant_id}-${i}`">
              <template v-if="ui.hqShare === 'sms_wallet'">
                <td><button type="button" class="link" @click="openWalletDrawer(row.tenant_id)">{{ row.tenant_name }}</button></td>
                <td>{{ row.wallet_name || '—' }}</td>
                <td><HqStatusBadge kind="direction" :value="row.direction" /></td>
                <td class="num">{{ formatMoney(row.amount) }}</td>
                <td class="desc" :title="row.description">{{ row.description || row.reference_type || '—' }}</td>
                <td>{{ formatJalaliDateTime(row.transacted_at) }}</td>
                <td><HqStatusBadge kind="share" :value="row.share_group" /></td>
              </template>
              <template v-else>
                <td>{{ row.tenant_name }}<small v-if="row.isVirtual" class="virtual" title="ایجادشده از تراکنش کیف پول"> ⚡</small></td>
                <td>{{ row.feature?.label || '—' }}</td>
                <td>{{ paymentPlanLabel(row.feature?.payment_plan) }}</td>
                <td class="num">{{ formatMoney(row.feature?.paid_amount) }}</td>
                <td class="num">
                  <span v-if="!Number(row.feature?.remaining_amount)" class="settled">تسویه‌شده</span>
                  <template v-else>{{ formatMoney(row.feature?.remaining_amount) }}</template>
                </td>
                <td>{{ row.feature?.installment_months ? `${formatFaNumber(row.feature.installment_months)} قسط` : '—' }}</td>
                <td><HqStatusBadge kind="share" :value="row.feature?.share_group" /></td>
              </template>
            </tr>
            <tr v-if="!activeHqShareRows.length"><td colspan="7"><HqEmptyState title="بدون ردیف" description="در این تب برای بازه انتخابی داده‌ای نیست." /></td></tr>
          </tbody>
          <tfoot v-if="activeHqShareRows.length"><tr><td colspan="7" class="foot">جمع ردیف‌های نمایش‌داده‌شده: {{ formatMoney(hqShareFooterSum) }}</td></tr></tfoot>
        </table>
      </div>

      <header class="section-head">
        <div><h3>سهم آراکار و عملکرد عملیاتی شعب</h3><p>فقط شعب دارای سهم آراکار در بازه انتخابی</p></div>
        <select v-model="ui.health" class="filter-select" @change="pushUiState()">
          <option value="">همه سلامت‌ها</option>
          <option value="strong">عالی</option><option value="stable">باثبات</option>
          <option value="risk">نیازمند توجه</option><option value="idle">بدون فعالیت</option>
        </select>
      </header>
      <div v-if="snap.highlights?.top_margin || snap.highlights?.watchlist" class="insights">
        <article v-if="snap.highlights.top_margin"><small>بیشترین سهم آراکار</small><strong>{{ snap.highlights.top_margin.tenant_name }}</strong></article>
        <article v-if="snap.highlights.watchlist"><small>بیشترین مطالبات</small><strong>{{ snap.highlights.watchlist.tenant_name }} — {{ formatMoney(snap.highlights.watchlist.pending_amount) }}</strong></article>
      </div>
      <div class="hq-table-wrap">
        <table>
          <thead><tr><th>رتبه</th><th>کارواش</th><th>درآمد وصولی</th><th>هزینه</th><th>سهم آراکار</th><th>مطالبات</th><th>خودرو</th><th>سلامت</th></tr></thead>
          <tbody>
            <tr v-for="(row, i) in rahRows" :key="row.tenant_id">
              <td>{{ formatFaNumber(i + 1) }}</td>
              <td><strong>{{ row.tenant_name }}</strong><small>{{ formatRelativeDate(row.last_activity_at) }}</small></td>
              <td class="num">{{ formatMoney(row.paid_amount) }}</td>
              <td class="num">{{ formatMoney(row.expense_total) }}</td>
              <td class="num">{{ formatMoney(row.rah_share_total) }}</td>
              <td class="num">{{ formatMoney(row.pending_amount) }}</td>
              <td>{{ formatFaNumber(row.vehicles_count) }}</td>
              <td><HqStatusBadge kind="health" :value="row.health" /></td>
            </tr>
            <tr v-if="!rahRows.length"><td colspan="8"><HqEmptyState title="بدون شعبه" description="شعبه‌ای با سهم آراکار در این بازه نیست." /></td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- CARWASH -->
    <section v-else-if="ui.workspace === 'carwash'" class="panel carwash-layout">
      <aside class="cw-sidebar cw-desktop">
        <input v-model="carwashSearch" class="search" placeholder="جستجو..." />
        <select v-model="carwashActivity" class="filter-select full"><option value="all">همه</option><option value="active">فعال در بازه</option><option value="idle">بدون فعالیت</option></select>
        <button v-for="item in carwashList" :key="item.id" type="button" class="cw-item" :class="{ active: String(item.id) === ui.tenant }" @click="selectTenant(item.id)">
          <strong>{{ item.name }}</strong>
          <small>{{ item.report?.last_activity_at ? formatRelativeDate(item.report.last_activity_at) : '—' }} · {{ formatFaNumber(item.report?.vehicles_count || 0) }} خودرو</small>
          <HqStatusBadge v-if="item.report?.health" kind="health" :value="item.report.health" />
        </button>
      </aside>
      <div class="cw-mobile">
        <select :value="ui.tenant" class="filter-select full" @change="selectTenant($event.target.value)">
          <option value="">انتخاب کارواش...</option>
          <option v-for="item in carwashList" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
      </div>
      <div class="cw-main">
        <HqEmptyState v-if="!ui.tenant" title="کارواش انتخاب نشده" description="برای مشاهده گزارش، یک کارواش را انتخاب کنید." />
        <template v-else>
          <header class="section-head sticky">
            <div><h3>{{ selectedCarwash?.name || tenant.data?.tenant?.name }}</h3>
              <HqStatusBadge v-if="rowMap.get(Number(ui.tenant))?.health" kind="health" :value="rowMap.get(Number(ui.tenant)).health" />
              <small>{{ periodLabel }}</small></div>
            <button type="button" class="hq-btn ghost sm" :disabled="tenant.loading" @click="loadTenantReport">بروزرسانی</button>
          </header>
          <div v-if="tenant.error" class="section-error"><p>{{ tenant.error }}</p><button type="button" class="hq-btn primary sm" @click="loadTenantReport">تلاش مجدد</button></div>
          <div v-else-if="tenant.loading && !tenant.data" class="loading-note">در حال دریافت...</div>
          <template v-else-if="tenant.data">
            <div class="kpi-row">
              <HqKpiCard label="مبلغ نهایی" :value="formatMoney(tenantSummary.final_total)" tone="spotlight" />
              <HqKpiCard label="حق کارواش" :value="formatMoney(tenantSummary.carwash_total)" />
              <HqKpiCard label="حق نیرو" :value="formatMoney(tenantSummary.worker_total)" />
              <HqKpiCard label="تعداد خودرو" :value="formatFaNumber(tenantSummary.vehicles_count)" />
            </div>
            <button type="button" class="toggle-extra" @click="showExtraKpis = !showExtraKpis">{{ showExtraKpis ? '▲' : '▼' }} KPIهای مکمل</button>
            <div v-if="showExtraKpis" class="kpi-row compact">
              <HqKpiCard compact label="قبل تخفیف" :value="formatMoney(tenantSummary.before_discount_total)" />
              <HqKpiCard compact label="تخفیف" :value="formatMoney(tenantSummary.discount_total)" />
              <HqKpiCard compact label="انعام" :value="formatMoney(tenantSummary.tips_total)" />
              <HqKpiCard compact label="پرداختنی نیرو" :value="formatMoney(tenantSummary.payable_worker_total)" />
              <HqKpiCard compact label="بیمه" :value="formatMoney(tenantSummary.insurance_total)" />
            </div>
            <div class="seg-tabs">
              <button v-for="tab in TENANT_REPORT_TABS" :key="tab.key" type="button" :class="{ active: ui.tenantTab === tab.key }" @click="ui.tenantTab = tab.key; pushUiState()">
                {{ tab.label }} <span class="count">{{ formatFaNumber(tenantTabCounts[tab.key]) }}</span>
              </button>
            </div>
            <div class="hq-table-wrap">
              <table>
                <thead><tr><th v-for="col in tenantColumns" :key="col[0]">{{ col[1] }}</th></tr></thead>
                <tbody>
                  <tr v-for="(row, i) in tenantRows" :key="i"><td v-for="col in tenantColumns" :key="col[0]">{{ tenantCell(row, col) }}</td></tr>
                  <tr v-if="!tenantRows.length"><td :colspan="tenantColumns.length"><HqEmptyState title="بدون رکورد" description="در این تب برای بازه انتخابی رکوردی نیست." /></td></tr>
                </tbody>
              </table>
            </div>
          </template>
        </template>
      </div>
    </section>

    <!-- WALLET -->
    <section v-else-if="ui.workspace === 'wallet'" class="panel">
      <div class="kpi-row">
        <HqKpiCard label="کل موجودی" :value="formatMoney(snap.summary.wallet_balance_total)" tone="spotlight" />
        <HqKpiCard label="کل واریزی" :value="formatMoney(snap.summary.wallet_deposit_total)" />
        <HqKpiCard label="کل برداشت" :value="formatMoney(snap.summary.wallet_withdraw_total)" />
        <HqKpiCard label="خالص جریان" :value="formatMoney(walletNetFlow)" />
      </div>
      <div class="kpi-row compact">
        <HqKpiCard compact label="شارژ درگاه" :value="formatMoney(snap.summary.wallet_gateway_charge_total)" />
        <HqKpiCard compact label="شارژ دستی" :value="formatMoney(snap.summary.wallet_manual_charge_total)" />
        <HqKpiCard compact label="موجودی پیامک" :value="formatMoney(snap.summary.wallet_sms_balance_total)" />
        <HqKpiCard compact label="SMS ارسال / هزینه" :value="`${formatFaNumber(snap.summary.sms_sent_count)} / ${formatMoney(snap.summary.sms_cost_total)}`" />
      </div>
      <article class="chart-card">
        <h3>جریان روزانه</h3>
        <div class="bar-chart dual">
          <div v-for="(t, i) in walletTrends" :key="i" class="bar-col" :title="`${formatJalaliDate(t.date)} — واریز ${formatMoney(t.wallet_deposit_total)} / برداشت ${formatMoney(t.wallet_withdraw_total)}`">
            <div class="bar in" :style="{ height: `${Math.max(6, (Number(t.wallet_deposit_total || 0) / walletTrendMax) * 80)}px` }" />
            <div class="bar out" :style="{ height: `${Math.max(6, (Number(t.wallet_withdraw_total || 0) / walletTrendMax) * 80)}px` }" />
          </div>
        </div>
      </article>
      <div class="filters">
        <input v-model="ledger.search" class="search" placeholder="جستجو کارواش / شرح..." />
        <select v-model="ledger.walletType" class="filter-select"><option value="">همه کیف‌ها</option><option value="regular">عادی</option><option value="sms">پیامک</option></select>
        <select v-model="ledger.direction" class="filter-select"><option value="">همه جهت‌ها</option><option value="in">واریز</option><option value="out">برداشت</option></select>
        <select v-model="ledger.shareGroup" class="filter-select"><option value="">همه سهم‌ها</option><option value="hq">کارنو</option><option value="rah">آراکار</option><option value="none">بدون سهم</option></select>
      </div>
      <p class="notice">حداکثر ۲۵۰ تراکنش اخیر</p>
      <div class="hq-table-wrap">
        <table>
          <thead><tr><th>کارواش</th><th>کیف</th><th>نوع</th><th>جهت</th><th>مبلغ</th><th>شرح/مرجع</th><th>ثبت‌کننده</th><th>زمان</th><th>سهم</th></tr></thead>
          <tbody>
            <tr v-for="row in ledgerRows" :key="row.id">
              <td><button type="button" class="link" @click="openWalletDrawer(row.tenant_id)">{{ row.tenant_name }}</button></td>
              <td>{{ row.wallet_name || '—' }}</td>
              <td>{{ row.wallet_type === 'sms' ? 'پیامک' : 'عادی' }}</td>
              <td><HqStatusBadge kind="direction" :value="row.direction" /></td>
              <td class="num">{{ signedMoney(row.amount, row.direction) }}</td>
              <td class="desc" :title="`${row.description || ''} ${row.reference_type || ''}`">{{ row.description || row.reference_type || '—' }}</td>
              <td>{{ row.created_by_name || '—' }}</td>
              <td>{{ formatJalaliDateTime(row.transacted_at) }}</td>
              <td><HqStatusBadge kind="share" :value="row.share_group" /></td>
            </tr>
            <tr v-if="!ledgerRows.length"><td colspan="9"><HqEmptyState title="بدون تراکنش" description="تراکنشی با این فیلترها نیست." action-label="پاک‌کردن فیلتر" @action="Object.assign(ledger, { search: '', walletType: '', direction: '', shareGroup: '' })" /></td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- NETWORK -->
    <section v-else class="panel">
      <div class="seg-tabs">
        <button type="button" :class="{ active: ui.networkTab === 'revenue' }" @click="ui.networkTab = 'revenue'; pushUiState()">گزارش درآمد</button>
        <button type="button" :class="{ active: ui.networkTab === 'wallet' }" @click="ui.networkTab = 'wallet'; pushUiState()">گزارش کیف پول</button>
      </div>
      <template v-if="ui.networkTab === 'revenue'">
        <div class="kpi-row">
          <HqKpiCard label="درآمد وصولی" :value="formatMoney(snap.summary.paid_amount)" tone="spotlight"
            :delta="showDelta ? formatPercentChange(snap.summary.revenue_change_percent) : ''" :delta-tone="deltaTone(snap.summary.revenue_change_percent)" />
          <HqKpiCard label="خالص" :value="formatMoney(snap.summary.net_total)"
            :delta="showDelta ? formatPercentChange(snap.summary.net_change_percent) : ''" :delta-tone="deltaTone(snap.summary.net_change_percent)" />
          <HqKpiCard label="تعداد خودرو" :value="formatFaNumber(snap.summary.vehicles_count)"
            :delta="showDelta ? formatPercentChange(snap.summary.vehicles_change_percent) : ''" :delta-tone="deltaTone(snap.summary.vehicles_change_percent)" />
          <HqKpiCard label="نرخ وصول" :value="formatPercent(snap.summary.collection_rate)"
            :delta="showDelta ? 'بدون داده مقایسه' : ''" delta-tone="neutral" />
        </div>
        <div class="kpi-row compact">
          <HqKpiCard compact label="قبل تخفیف" :value="formatMoney(Number(snap.summary.paid_amount || 0) + Number(snap.summary.discount_total || 0))" />
          <HqKpiCard compact label="تخفیف" :value="formatMoney(snap.summary.discount_total)" />
          <HqKpiCard compact label="میانگین فاکتور" :value="formatMoney(snap.summary.average_ticket)" />
          <HqKpiCard compact label="مطالبات" :value="formatMoney(snap.summary.pending_amount)" />
        </div>
        <div v-if="snap.highlights?.top_revenue || snap.highlights?.top_volume" class="insights">
          <article v-if="snap.highlights.top_revenue"><small>بیشترین درآمد</small><strong>{{ snap.highlights.top_revenue.tenant_name }}</strong></article>
          <article v-if="snap.highlights.top_volume"><small>بیشترین حجم</small><strong>{{ snap.highlights.top_volume.tenant_name }}</strong></article>
          <article v-if="snap.highlights.watchlist"><small>نیازمند توجه</small><strong>{{ snap.highlights.watchlist.tenant_name }}</strong></article>
        </div>
        <article class="chart-card"><h3>روند درآمد / خالص</h3>
          <div class="bar-chart dual">
            <div v-for="(t, i) in walletTrends" :key="i" class="bar-col">
              <div class="bar in" :style="{ height: `${Math.max(6, (Number(t.paid_amount || 0) / networkTrendMax) * 80)}px` }" />
              <div class="bar rah" :style="{ height: `${Math.max(6, (Number(t.net_amount || 0) / networkTrendMax) * 80)}px` }" />
            </div>
          </div>
        </article>
        <div class="hq-table-wrap">
          <table>
            <thead><tr><th>رتبه</th><th>کارواش</th><th>سلامت</th><th>درآمد</th><th>قبل تخفیف</th><th>تخفیف</th><th>خالص</th><th>میانگین</th><th>مطالبات</th><th>پرداخت</th></tr></thead>
            <tbody>
              <tr v-for="(row, i) in networkRows" :key="row.tenant_id" :class="{ risk: row.health === 'risk' }">
                <td><span class="rank" :class="{ top: i < 3 }">{{ rankLabel(i) }}</span></td>
                <td><strong>{{ row.tenant_name }}</strong></td>
                <td><HqStatusBadge kind="health" :value="row.health" /></td>
                <td class="num">{{ formatMoney(row.paid_amount) }}</td>
                <td class="num">{{ formatMoney(Number(row.paid_amount || 0) + Number(row.discount_total || 0)) }}</td>
                <td class="num">{{ formatMoney(row.discount_total) }}</td>
                <td class="num">{{ formatMoney(row.net_amount) }}</td>
                <td class="num">{{ formatMoney(row.average_ticket) }}</td>
                <td class="num">{{ formatMoney(row.pending_amount) }}</td>
                <td>{{ formatFaNumber(row.payments_count) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <template v-else>
        <div class="kpi-row compact">
          <HqKpiCard compact label="کل موجودی" :value="formatMoney(snap.summary.wallet_balance_total)" />
          <HqKpiCard compact label="عادی" :value="formatMoney(snap.summary.wallet_regular_balance_total)" />
          <HqKpiCard compact label="پیامک" :value="formatMoney(snap.summary.wallet_sms_balance_total)" />
          <HqKpiCard compact label="درگاه" :value="formatMoney(snap.summary.wallet_gateway_charge_total)" />
          <HqKpiCard compact label="دستی" :value="formatMoney(snap.summary.wallet_manual_charge_total)" />
        </div>
        <label class="compare-toggle"><input v-model="walletAttention" type="checkbox" /> نیازمند توجه (خالی / بدون فعالیت)</label>
        <div class="hq-table-wrap">
          <table>
            <thead><tr><th>رتبه</th><th>کارواش</th><th>سلامت شارژ</th><th>کل</th><th>عادی</th><th>پیامک</th><th>واریز</th><th>برداشت</th><th>درگاه</th><th>دستی</th></tr></thead>
            <tbody>
              <tr v-for="(row, i) in networkRows" :key="row.tenant_id">
                <td><span class="rank" :class="{ top: i < 3 }">{{ rankLabel(i) }}</span></td>
                <td>{{ row.tenant_name }}</td>
                <td><HqStatusBadge kind="wallet" :value="row.wallet_charge_health" /></td>
                <td class="num">{{ formatMoney(row.wallet_balance) }}</td>
                <td class="num">{{ formatMoney(row.wallet_regular_balance) }}</td>
                <td class="num">{{ formatMoney(row.wallet_sms_balance) }}</td>
                <td class="num">{{ formatMoney(row.wallet_deposit_total) }}</td>
                <td class="num">{{ formatMoney(row.wallet_withdraw_total) }}</td>
                <td class="num">{{ formatMoney(row.wallet_gateway_charge_total) }}</td>
                <td class="num">{{ formatMoney(row.wallet_manual_charge_total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </section>

    <Teleport to="body">
      <div v-if="walletDrawer.open" class="drawer-backdrop" @click.self="walletDrawer.open = false">
        <aside class="drawer">
          <header><h3>{{ drawerRow?.tenant_name || 'ریز کیف پول' }}</h3><button type="button" class="hq-btn ghost sm" @click="walletDrawer.open = false">بستن</button></header>
          <div class="kpi-row compact">
            <HqKpiCard compact label="کل موجودی" :value="formatMoney(drawerRow?.wallet_balance)" />
            <HqKpiCard compact label="عادی" :value="formatMoney(drawerRow?.wallet_regular_balance)" />
            <HqKpiCard compact label="پیامک" :value="formatMoney(drawerRow?.wallet_sms_balance)" />
            <HqKpiCard compact label="خالص جریان" :value="formatMoney(Number(drawerRow?.wallet_deposit_total || 0) - Number(drawerRow?.wallet_withdraw_total || 0))" />
          </div>
          <div class="seg-tabs compact">
            <button v-for="t in [['all','همه'],['in','واریزها'],['out','برداشت‌ها'],['sms','پیامک']]" :key="t[0]" type="button" :class="{ active: walletDrawer.tab === t[0] }" @click="walletDrawer.tab = t[0]">{{ t[1] }}</button>
          </div>
          <div class="hq-table-wrap drawer-table">
            <table>
              <thead><tr><th>نوع</th><th>جهت</th><th>مبلغ</th><th>شرح</th><th>زمان</th></tr></thead>
              <tbody>
                <tr v-for="tx in drawerTxs" :key="tx.id">
                  <td>{{ tx.wallet_type === 'sms' ? 'پیامک' : 'عادی' }}</td>
                  <td><HqStatusBadge kind="direction" :value="tx.direction" /></td>
                  <td class="num">{{ signedMoney(tx.amount, tx.direction) }}</td>
                  <td>{{ tx.description || '—' }}</td>
                  <td>{{ formatJalaliDateTime(tx.transacted_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </aside>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.hq-reports { background: transparent; }
.control-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: grid;
  gap: 0.75rem;
  padding: 0.95rem 1.05rem;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(25, 118, 210, 0.12);
  border-radius: 16px;
  box-shadow: 0 12px 30px rgba(15, 37, 69, 0.05);
}
.range-chips, .date-row, .control-meta, .filters, .seg-tabs, .workspace-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.chip, .seg-tabs button {
  border: 1px solid rgba(25, 118, 210, 0.12);
  background: #f5f8fc;
  border-radius: 999px;
  min-height: 38px;
  padding: 0 0.95rem;
  cursor: pointer;
  font-weight: 650;
  font-size: 13px;
  color: #0f2545;
  transition: all 180ms ease;
}
.chip:hover, .seg-tabs button:hover { background: #fff; border-color: rgba(25, 118, 210, 0.24); }
.chip.active, .seg-tabs button.active {
  background: #1976d2;
  border-color: #1976d2;
  color: #fff;
  box-shadow: 0 8px 18px rgba(25, 118, 210, 0.22);
}
.ws-tab {
  flex: 1 1 190px;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  text-align: right;
  min-width: 0;
  border: 1px solid rgba(25, 118, 210, 0.12);
  background: #fff;
  border-radius: 16px;
  min-height: 68px;
  padding: 0.75rem 0.9rem;
  cursor: pointer;
  transition: all 180ms ease;
  box-shadow: 0 8px 20px rgba(15, 37, 69, 0.03);
}
.ws-tab:hover { border-color: rgba(25, 118, 210, 0.24); transform: translateY(-1px); }
.ws-tab.active {
  border-color: rgba(25, 118, 210, 0.4);
  background: linear-gradient(165deg, #eef6ff 0%, #ffffff 70%);
  box-shadow: 0 12px 26px rgba(25, 118, 210, 0.1);
}
.ws-copy { display: grid; gap: 0.12rem; min-width: 0; }
.ws-copy strong { font-size: 13.5px; color: #0c3d78; font-weight: 750; }
.ws-copy small { font-size: 11.5px; color: #6b7c93; }
.ws-badge {
  margin-right: auto;
  background: #fee2e2;
  color: #991b1b;
  border-radius: 999px;
  padding: 0.12rem 0.5rem;
  font-size: 11px;
  font-weight: 750;
}
.ws-icon {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: linear-gradient(145deg, #e8f2fc, #f5f9ff);
  border: 1px solid rgba(25, 118, 210, 0.12);
  flex-shrink: 0;
}
.compare-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 13px;
  color: #5b6b82;
  background: #f5f8fc;
  border-radius: 999px;
  padding: 0.35rem 0.75rem;
  border: 1px solid rgba(25, 118, 210, 0.1);
}
.panel { display: grid; gap: 1rem; }
.kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.8rem; }
.kpi-row.compact { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
.analysis-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 0.85rem; }
.chart-card {
  background: #fff;
  border: 1px solid rgba(25, 118, 210, 0.12);
  border-radius: 16px;
  padding: 1.05rem;
  min-height: 260px;
  box-shadow: 0 10px 24px rgba(15, 37, 69, 0.03);
}
.chart-card h3 { margin: 0 0 0.85rem; font-size: 15px; color: #0c3d78; font-weight: 750; }
.chart-head { margin-bottom: 0.55rem; }
.chart-head h3 { margin: 0; }
.chart-head p { margin: 0.28rem 0 0; color: #6b7c93; font-size: 12px; line-height: 1.5; }
.trend-card { min-height: 320px; }
.area-chart, .bar-chart { display: flex; align-items: flex-end; gap: 5px; min-height: 150px; padding: 0.25rem 0.1rem; }
.area-col, .bar-col { flex: 1; display: flex; align-items: flex-end; gap: 2px; justify-content: center; min-width: 0; }
.bar {
  border-radius: 6px 6px 2px 2px;
  min-width: 8px;
  transition: height 180ms ease;
  opacity: 0.92;
}
.bar.hq, .bar.in { background: linear-gradient(180deg, #4ea1ea, #1976d2); }
.bar.rah { background: linear-gradient(180deg, #9b6cf0, #6d28d9); }
.bar.out { background: linear-gradient(180deg, #f07171, #dc2626); opacity: 0.88; }
.legend { margin-top: 0.75rem; font-size: 12px; color: #6b7c93; display: flex; gap: 0.85rem; align-items: center; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-left: 0.28rem; }
.dot.hq { background: #1976d2; } .dot.rah { background: #6d28d9; }
.comp-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.6rem; }
.comp-list li {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 0.55rem;
  font-size: 13px;
  align-items: center;
  padding: 0.55rem 0.65rem;
  border-radius: 12px;
  background: #f7faff;
  border: 1px solid rgba(25, 118, 210, 0.08);
}
.comp-list em { color: #6b7c93; font-style: normal; font-size: 12px; }
.hq-table-wrap {
  overflow: auto;
  border: 1px solid rgba(25, 118, 210, 0.12);
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 37, 69, 0.03);
}
.hq-table-wrap table { width: 100%; border-collapse: collapse; font-size: 13px; }
.hq-table-wrap thead th {
  position: sticky; top: 0; z-index: 1; text-align: right;
  padding: 0.82rem 0.7rem; font-size: 11.5px; font-weight: 750; color: #647892;
  background: linear-gradient(180deg, #f8fbff, #f3f7fc);
  border-bottom: 1px solid rgba(25, 118, 210, 0.12); white-space: nowrap;
}
.hq-table-wrap td { padding: 0.88rem 0.7rem; border-bottom: 1px solid #eef2f7; vertical-align: middle; }
.hq-table-wrap tbody tr { transition: background 160ms ease; }
.hq-table-wrap tbody tr:hover { background: rgba(232, 242, 252, 0.55); }
.hq-table-wrap td.num { white-space: nowrap; font-variant-numeric: tabular-nums; font-weight: 650; color: #0f2545; }
.hq-table-wrap td.desc { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #5b6b82; }
.hq-table-wrap tfoot .foot { font-weight: 750; background: #f7faff; color: #0c3d78; }
.hq-table-wrap tr.risk { box-shadow: inset -3px 0 0 #dc2626; }
.rank {
  display: inline-flex; min-width: 1.7rem; justify-content: center;
  font-variant-numeric: tabular-nums; color: #64748b; font-weight: 650;
}
.rank.top {
  color: #0c3d78; font-weight: 800; background: #e8f2fc;
  border-radius: 999px; padding: 0.12rem 0.5rem;
}
.settled { color: #166534; font-weight: 750; }
.section-head { display: flex; justify-content: space-between; gap: 0.75rem; align-items: flex-start; flex-wrap: wrap; }
.section-head h3 { margin: 0; font-size: 1.05rem; color: #0c3d78; font-weight: 780; }
.section-head p, .notice { margin: 0.25rem 0 0; font-size: 12.5px; color: #6b7c93; line-height: 1.6; }
.insights { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.65rem; }
.insights article {
  background: #fff; border: 1px solid rgba(25, 118, 210, 0.12); border-radius: 14px;
  padding: 0.85rem; box-shadow: 0 8px 18px rgba(15, 37, 69, 0.03);
}
.insights small { color: #6b7c93; font-size: 11.5px; }
.insights strong { display: block; margin-top: 0.25rem; color: #0c3d78; }
.carwash-layout { grid-template-columns: 1fr; display: grid; gap: 0.9rem; align-items: start; }
.cw-desktop { display: none; }
.cw-mobile { display: block; }
@media (min-width: 1024px) {
  .carwash-layout { grid-template-columns: 320px 1fr; }
  .cw-desktop { display: grid; }
  .cw-mobile { display: none; }
}
.cw-sidebar {
  position: sticky; top: 84px; gap: 0.55rem; max-height: calc(100vh - 110px);
  overflow: auto; padding: 0.85rem; background: #fff;
  border: 1px solid rgba(25, 118, 210, 0.12); border-radius: 16px;
  box-shadow: 0 10px 24px rgba(15, 37, 69, 0.03);
}
.cw-item {
  display: grid; gap: 0.25rem; text-align: right;
  border: 1px solid rgba(25, 118, 210, 0.1); border-radius: 12px;
  padding: 0.72rem 0.8rem; background: #f7faff; cursor: pointer;
  transition: all 160ms ease;
}
.cw-item:hover { background: #fff; border-color: rgba(25, 118, 210, 0.24); }
.cw-item.active {
  border-color: #1976d2;
  background: linear-gradient(165deg, #eef6ff, #ffffff);
  box-shadow: 0 8px 18px rgba(25, 118, 210, 0.1);
}
.cw-main { display: grid; gap: 0.9rem; min-width: 0; }
.search, .filter-select {
  height: 40px; border: 1px solid rgba(25, 118, 210, 0.14); border-radius: 12px;
  padding: 0 0.75rem; background: #fff; font-size: 13px;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.search:focus, .filter-select:focus {
  outline: none; border-color: #1976d2; box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.12);
}
.filter-select.full { width: 100%; }
.section-error {
  display: flex; gap: 0.75rem; align-items: center; justify-content: space-between;
  padding: 0.9rem 1rem; border-radius: 14px; background: #feeeee; color: #991b1b;
  border: 1px solid rgba(153, 27, 27, 0.12);
}
.link {
  border: 0; background: none; color: #1976d2; cursor: pointer; font-weight: 650; padding: 0;
}
.link:hover { color: #0f62b3; text-decoration: underline; }
.spin {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.35);
  border-top-color: currentColor; border-radius: 50%; animation: spin 0.8s linear infinite;
}
.spin.sm { border-color: rgba(15,98,179,0.25); border-top-color: #0f62b3; }
.count {
  background: #eef3fa; border-radius: 999px; padding: 0.05rem 0.4rem;
  font-size: 11px; margin-right: 0.25rem; color: #5b6b82; font-weight: 700;
}
.drawer-backdrop {
  position: fixed; inset: 0; background: rgba(12, 28, 52, 0.38);
  backdrop-filter: blur(2px); z-index: 240; display: flex; justify-content: flex-start;
}
.drawer {
  width: min(560px, 100vw); height: 100%; background: #fff; padding: 1.1rem;
  overflow: auto; display: grid; gap: 0.85rem; align-content: start;
  box-shadow: 12px 0 36px rgba(15, 37, 69, 0.16);
}
.drawer header {
  display: flex; justify-content: space-between; align-items: center;
  position: sticky; top: 0; background: rgba(255,255,255,0.96); backdrop-filter: blur(8px);
  padding-bottom: 0.55rem; border-bottom: 1px solid rgba(25, 118, 210, 0.1);
}
.drawer header h3 { margin: 0; color: #0c3d78; font-size: 1.1rem; }
.drawer-table { max-height: 50vh; }
.toggle-extra {
  border: 0; background: none; color: #0f62b3; cursor: pointer;
  font-weight: 700; font-size: 13px; justify-self: start;
}
.virtual { color: #d97706; font-size: 11px; font-weight: 650; }
.loading-note { color: #6b7c93; font-size: 13px; }
.control-meta span {
  display: inline-flex; align-items: center; min-height: 34px;
  padding: 0 0.75rem; border-radius: 999px; background: #f5f8fc;
  color: #5b6b82; font-size: 12.5px; border: 1px solid rgba(25, 118, 210, 0.1);
}
@media (max-width: 1023px) {
  .carwash-layout { grid-template-columns: 1fr; }
  .analysis-grid { grid-template-columns: 1fr; }
}
@media (max-width: 767px) {
  .control-bar { position: static; }
  .drawer { width: 100vw; }
  .ws-tab { flex: 1 1 100%; }
}
@media (prefers-reduced-motion: reduce) {
  .chip, .seg-tabs button, .ws-tab, .bar, .hq-btn, .cw-item { transition: none; }
  .spin { animation: none; }
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
