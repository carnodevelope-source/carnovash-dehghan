<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import api from '../../services/api'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import { useAuthStore } from '../../store/auth.store'
import { formatJalaliDate, formatJalaliDateTime, parseJalaliToIso } from '../../utils/date'

const props = defineProps({
  carwashes: { type: Array, default: () => [] }
})

const authStore = useAuthStore()
const loading = ref(false)
const error = ref('')
const success = ref('')
const summary = reactive({})
const capabilities = reactive({})
const catalog = reactive({ projects: [], products: [] })
const rows = ref([])
const count = ref(0)
const page = ref(1)
const pageSize = ref(20)
const numPages = ref(1)
const selectedIds = ref([])
const detail = ref(null)
const alerts = ref([])
const revenue = ref(null)
const reportKey = ref('all')
const clientId = ref('')
const clientDetail = ref(null)
const actionModal = reactive({
  open: false,
  subscription: null,
  action: 'activate',
  reason: '',
  note: '',
  days: 30,
  amount: '',
  plan_id: '',
  tracking_code: ''
})

const filters = reactive({
  search: '',
  project_id: '',
  product_key: '',
  status: '',
  payment_status: '',
  has_debt: false,
  near_expiry: false,
  ordering: '-updated_at',
  date_from: '',
  date_to: ''
})

const statusOptions = [
  { value: '', label: 'همه وضعیت‌ها' },
  { value: 'active', label: 'فعال' },
  { value: 'inactive', label: 'غیرفعال' },
  { value: 'expired', label: 'منقضی' },
  { value: 'near_expiry', label: 'نزدیک انقضا' },
  { value: 'blocked', label: 'مسدود' },
  { value: 'suspended', label: 'تعلیق' },
  { value: 'pending_payment', label: 'در انتظار پرداخت' },
  { value: 'pending_activation', label: 'در انتظار فعالسازی' },
  { value: 'cancelled', label: 'لغو' },
  { value: 'not_renewed', label: 'تمدیدنشده' }
]

const paymentStatusOptions = [
  { value: '', label: 'همه پرداخت‌ها' },
  { value: 'settled', label: 'تسویه' },
  { value: 'partial', label: 'جزئی' },
  { value: 'unpaid', label: 'پرداخت‌نشده' },
  { value: 'overdue', label: 'معوق' }
]

const specializedTabs = [
  { key: 'all', label: 'همه سرویس‌ها' },
  { key: 'license', label: 'لایسنس' },
  { key: 'wallet', label: 'کیف پول' },
  { key: 'attendance', label: 'ورود و خروج' },
  { key: 'cloud', label: 'فضای ابری' },
  { key: 'sms_club', label: 'باشگاه مشتریان' },
  { key: 'sms', label: 'پیامک' },
  { key: 'revenue', label: 'ماتریس درآمد' }
]

const actionOptions = computed(() => {
  const items = [
    { value: 'activate', label: 'فعالسازی' },
    { value: 'deactivate', label: 'غیرفعالسازی' },
    { value: 'suspend', label: 'تعلیق' },
    { value: 'unsuspend', label: 'رفع تعلیق' },
    { value: 'block', label: 'مسدودسازی' },
    { value: 'restore', label: 'بازگردانی' },
    { value: 'extend_days', label: 'تمدید روز' },
    { value: 'renew', label: 'تمدید با سفارش' },
    { value: 'change_plan', label: 'تغییر پلن' },
    { value: 'register_payment', label: 'ثبت پرداخت' },
    { value: 'apply_discount', label: 'تخفیف' },
    { value: 'forgive_debt', label: 'بخشش بدهی' },
    { value: 'free_activate', label: 'فعالسازی رایگان' }
  ]
  if (!capabilities.mutate_status) {
    return items.filter((item) => ['register_payment'].includes(item.value) && capabilities.register_payment)
  }
  return items
})

const kpiCards = computed(() => {
  const cards = [
    { key: 'clients_count', label: 'کلاینت‌ها', value: summary.clients_count },
    { key: 'active_count', label: 'فعال', value: summary.active_count },
    { key: 'inactive_count', label: 'غیرفعال', value: summary.inactive_count },
    { key: 'expired_count', label: 'منقضی', value: summary.expired_count },
    { key: 'near_expiry_count', label: 'نزدیک انقضا', value: summary.near_expiry_count },
    { key: 'blocked_count', label: 'مسدود', value: summary.blocked_count },
    { key: 'pending_payment_count', label: 'در انتظار پرداخت', value: summary.pending_payment_count }
  ]
  if (capabilities.see_financial) {
    cards.push(
      { key: 'sales_revenue', label: 'درآمد فروش', value: money(summary.sales_revenue), money: true },
      { key: 'renewal_revenue', label: 'درآمد تمدید', value: money(summary.renewal_revenue), money: true },
      { key: 'tax_collected', label: 'مالیات', value: money(summary.tax_collected), money: true },
      { key: 'discount_total', label: 'تخفیف', value: money(summary.discount_total), money: true },
      { key: 'receivables', label: 'مطالبات', value: money(summary.receivables), money: true },
      { key: 'overdue_total', label: 'معوقات', value: money(summary.overdue_total), money: true }
    )
  }
  if (capabilities.see_costs) {
    cards.push({ key: 'cost_total', label: 'هزینه', value: money(summary.cost_total), money: true })
  }
  if (capabilities.see_holding_profit) {
    cards.push({ key: 'net_profit', label: 'سود خالص', value: money(summary.net_profit), money: true })
  }
  return cards
})

const allSelected = computed(() => rows.value.length > 0 && selectedIds.value.length === rows.value.length)

const activeCarwashes = computed(() => (props.carwashes || []).filter((item) => item.is_active !== false))

function toFa(value) {
  return String(value ?? 0).replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[d])
}

function money(value) {
  const num = Number(value || 0)
  return `${toFa(num.toLocaleString('en-US'))} ریال`
}

function statusLabel(value) {
  return statusOptions.find((item) => item.value === value)?.label || value || '—'
}

function buildQuery(extra = {}) {
  const params = {
    page: page.value,
    page_size: pageSize.value,
    ordering: filters.ordering,
    ...extra
  }
  if (filters.search) params.search = filters.search
  if (filters.project_id) params.project_id = filters.project_id
  if (filters.product_key) params.product_key = filters.product_key
  if (filters.status) params.status = filters.status
  if (filters.payment_status) params.payment_status = filters.payment_status
  if (filters.has_debt) params.has_debt = '1'
  if (filters.near_expiry) params.near_expiry = '1'
  const dateFrom = parseJalaliToIso(filters.date_from)
  const dateTo = parseJalaliToIso(filters.date_to)
  if (dateFrom) params.date_from = dateFrom
  if (dateTo) params.date_to = dateTo
  if (clientId.value) params.tenant_id = clientId.value
  return params
}

async function loadCatalog() {
  const { data } = await api.get('/subscriptions/hq/catalog/')
  catalog.projects = data.projects || []
  catalog.products = data.products || []
  Object.assign(capabilities, data.capabilities || {})
}

async function loadSummary() {
  const { data } = await api.get('/subscriptions/hq/summary/', { params: buildQuery({ page: undefined, page_size: undefined }) })
  Object.keys(summary).forEach((key) => delete summary[key])
  Object.assign(summary, data || {})
}

async function loadRows() {
  loading.value = true
  error.value = ''
  try {
    if (reportKey.value === 'revenue') {
      const { data } = await api.get('/subscriptions/hq/revenue/', { params: buildQuery({ page: undefined, page_size: undefined }) })
      revenue.value = data
      rows.value = []
      return
    }
    const endpoint = reportKey.value === 'all'
      ? '/subscriptions/hq/subscriptions/'
      : `/subscriptions/hq/reports/${reportKey.value}/`
    const { data } = await api.get(endpoint, { params: buildQuery() })
    rows.value = data.results || []
    count.value = data.count || 0
    page.value = data.page || 1
    numPages.value = data.num_pages || 1
    if (data.summary) Object.assign(summary, data.summary)
    selectedIds.value = []
  } catch (err) {
    error.value = err?.response?.data?.detail || 'بارگذاری سرویس‌ها ناموفق بود.'
  } finally {
    loading.value = false
  }
}

async function loadAlerts() {
  const { data } = await api.get('/subscriptions/hq/alerts/', { params: { page_size: 20 } })
  alerts.value = data.results || []
}

async function loadClient() {
  if (!clientId.value) {
    clientDetail.value = null
    return
  }
  const { data } = await api.get(`/subscriptions/hq/clients/${clientId.value}/services/`)
  clientDetail.value = data
}

async function refreshAll() {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    await loadCatalog()
    await Promise.all([loadSummary(), loadRows(), loadAlerts(), loadClient()])
  } catch (err) {
    error.value = err?.response?.data?.detail || 'خطا در بارگذاری گزارش سرویس‌ها'
  } finally {
    loading.value = false
  }
}

async function openDetail(row) {
  const { data } = await api.get(`/subscriptions/hq/subscriptions/${row.id}/`)
  detail.value = data
}

function openAction(row, action = 'activate') {
  actionModal.open = true
  actionModal.subscription = row
  actionModal.action = action
  actionModal.reason = ''
  actionModal.note = ''
  actionModal.days = 30
  actionModal.amount = ''
  actionModal.plan_id = row.plan || ''
  actionModal.tracking_code = ''
}

async function submitAction() {
  if (!actionModal.subscription) return
  error.value = ''
  try {
    const payload = {
      action: actionModal.action,
      reason: actionModal.reason,
      note: actionModal.note,
      plan_id: actionModal.plan_id || undefined,
      payload: {
        days: actionModal.days,
        amount: actionModal.amount,
        discount_amount: actionModal.amount,
        plan_id: actionModal.plan_id,
        tracking_code: actionModal.tracking_code,
        idempotency_key: `hq-${actionModal.subscription.id}-${Date.now()}`
      }
    }
    await api.post(`/subscriptions/hq/subscriptions/${actionModal.subscription.id}/actions/`, payload)
    actionModal.open = false
    success.value = 'عملیات با موفقیت انجام شد.'
    await refreshAll()
  } catch (err) {
    error.value = err?.response?.data?.detail || err?.response?.data?.reason?.[0] || 'عملیات ناموفق بود.'
  }
}

async function runBulk(action) {
  if (!selectedIds.value.length) {
    error.value = 'حداقل یک ردیف را انتخاب کنید.'
    return
  }
  if (!capabilities.bulk) {
    error.value = 'دسترسی عملیات گروهی ندارید.'
    return
  }
  try {
    await api.post('/subscriptions/hq/bulk/', {
      action,
      subscription_ids: selectedIds.value
    })
    success.value = 'عملیات گروهی اجرا شد.'
    await refreshAll()
  } catch (err) {
    error.value = err?.response?.data?.detail || 'عملیات گروهی ناموفق بود.'
  }
}

async function exportCsv() {
  if (!capabilities.export) {
    error.value = 'دسترسی خروجی ندارید.'
    return
  }
  const response = await api.get('/subscriptions/hq/export/', {
    params: buildQuery({ page: undefined, page_size: undefined }),
    responseType: 'blob'
  })
  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'services-report.csv'
  link.click()
  window.URL.revokeObjectURL(url)
}

async function seedCatalog() {
  if (!authStore.isHqAdmin) return
  await api.post('/subscriptions/hq/seed/')
  success.value = 'کاتالوگ و اشتراک‌ها همگام شد.'
  await refreshAll()
}

function toggleAll() {
  if (allSelected.value) selectedIds.value = []
  else selectedIds.value = rows.value.map((row) => row.id)
}

function toggleOne(id) {
  if (selectedIds.value.includes(id)) selectedIds.value = selectedIds.value.filter((item) => item !== id)
  else selectedIds.value = [...selectedIds.value, id]
}

watch(activeCarwashes, (list) => {
  if (!clientId.value) return
  if (!list.some((item) => String(item.id) === String(clientId.value))) {
    clientId.value = ''
    clientDetail.value = null
  }
})

watch([() => filters.search, () => filters.project_id, () => filters.product_key, () => filters.status, () => filters.payment_status, () => filters.has_debt, () => filters.near_expiry, () => filters.ordering, () => filters.date_from, () => filters.date_to, reportKey, clientId], async () => {
  page.value = 1
  await Promise.all([loadSummary(), loadRows(), loadClient()])
})

watch(page, async () => {
  await loadRows()
})

onMounted(refreshAll)
</script>

<template>
  <section class="services-shell" dir="rtl">
    <header class="services-header">
      <div>
        <p class="kicker">گزارش متمرکز سرویس‌ها و اشتراک‌ها</p>
        <h2>سرویس‌ها و قابلیت‌ها</h2>
        <p>مشاهده خرید، تمدید، انقضا، مصرف و وضعیت مالی هر کلاینت به‌صورت داینامیک</p>
      </div>
      <div class="header-actions">
        <button type="button" class="ghost-btn" @click="refreshAll">به‌روزرسانی</button>
        <button v-if="capabilities.export" type="button" class="ghost-btn" @click="exportCsv">خروجی CSV</button>
        <button v-if="authStore.isHqAdmin" type="button" class="primary-btn" @click="seedCatalog">همگام‌سازی کاتالوگ</button>
      </div>
    </header>

    <div v-if="error" class="state-banner error">{{ error }}</div>
    <div v-if="success" class="state-banner success">{{ success }}</div>

    <div class="kpi-grid">
      <article v-for="card in kpiCards" :key="card.key" class="kpi-card">
        <small>{{ card.label }}</small>
        <strong>{{ card.money ? card.value : toFa(card.value || 0) }}</strong>
      </article>
    </div>

    <div class="filter-bar">
      <input v-model="filters.search" type="search" placeholder="جستجوی کلاینت، سرویس، قرارداد..." />
      <select v-model="filters.project_id">
        <option value="">همه پروژه‌ها</option>
        <option v-for="project in catalog.projects" :key="project.id" :value="project.id">{{ project.name }}</option>
      </select>
      <select v-model="filters.product_key">
        <option value="">همه سرویس‌ها</option>
        <option v-for="product in catalog.products" :key="product.id" :value="product.product_key">{{ product.title }}</option>
      </select>
      <select v-model="filters.status">
        <option v-for="item in statusOptions" :key="item.value || 'all'" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-model="filters.payment_status">
        <option v-for="item in paymentStatusOptions" :key="item.value || 'pay-all'" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-model="clientId">
        <option value="">همه کلاینت‌ها</option>
        <option v-for="item in activeCarwashes" :key="item.id" :value="String(item.id)">{{ item.name }}</option>
      </select>
      <label class="check"><input v-model="filters.has_debt" type="checkbox" /> بدهکار</label>
      <label class="check"><input v-model="filters.near_expiry" type="checkbox" /> نزدیک انقضا</label>
      <BaseDatePicker v-model="filters.date_from" placeholder="از تاریخ خرید" />
      <BaseDatePicker v-model="filters.date_to" placeholder="تا تاریخ خرید" />
      <select v-model="filters.ordering">
        <option value="-updated_at">جدیدترین تغییر</option>
        <option value="-purchased_at">تاریخ خرید</option>
        <option value="ends_at">نزدیک‌ترین انقضا</option>
        <option value="-final_amount">بیشترین مبلغ</option>
        <option value="-remaining_amount">بیشترین بدهی</option>
        <option value="client_name">نام کلاینت</option>
      </select>
    </div>

    <div class="subtabs">
      <button
        v-for="tab in specializedTabs"
        :key="tab.key"
        type="button"
        class="subtab"
        :class="{ active: reportKey === tab.key }"
        @click="reportKey = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="alerts.length" class="alerts-strip">
      <article v-for="alert in alerts" :key="alert.id" class="alert-card" :class="alert.severity">
        <strong>{{ alert.title }}</strong>
        <span>{{ alert.client_name }} — {{ alert.product_title }}</span>
        <small>{{ alert.message }}</small>
      </article>
    </div>

    <div v-if="clientDetail" class="client-panel">
      <h3>سرویس‌های {{ clientDetail.tenant?.name }}</h3>
      <div class="client-grid">
        <article v-for="sub in clientDetail.subscriptions || []" :key="`owned-${sub.id}`" class="owned-card">
          <strong>{{ sub.product_title }}</strong>
          <span>{{ statusLabel(sub.status) }}</span>
          <small v-if="capabilities.see_financial">{{ money(sub.final_amount) }} / مانده {{ money(sub.remaining_amount) }}</small>
          <button type="button" class="ghost-btn" @click="openDetail(sub)">جزئیات</button>
        </article>
        <article v-for="product in clientDetail.not_purchased || []" :key="`miss-${product.id}`" class="missing-card">
          <strong>{{ product.title }}</strong>
          <span>خریداری نشده</span>
        </article>
      </div>
    </div>

    <div v-if="capabilities.bulk && selectedIds.length" class="bulk-bar">
      <span>{{ toFa(selectedIds.length) }} مورد انتخاب شده</span>
      <button type="button" class="ghost-btn" @click="runBulk('activate')">فعالسازی گروهی</button>
      <button type="button" class="ghost-btn" @click="runBulk('deactivate')">غیرفعالسازی گروهی</button>
      <button type="button" class="ghost-btn" @click="runBulk('sms_expiry')">پیامک انقضا</button>
    </div>

    <div v-if="loading" class="state-box">در حال بارگذاری...</div>
    <div v-else-if="reportKey === 'revenue'" class="revenue-panel">
      <table>
        <thead>
          <tr>
            <th>سرویس</th>
            <th>تعداد</th>
            <th>فروش</th>
            <th>پرداخت‌شده</th>
            <th>مانده</th>
            <th v-if="capabilities.see_costs">هزینه</th>
            <th v-if="capabilities.see_holding_profit">سود</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in revenue?.by_product || []" :key="row.product_key">
            <td>{{ row.product_title }}</td>
            <td>{{ toFa(row.subscriptions_count) }}</td>
            <td>{{ money(row.sales) }}</td>
            <td>{{ money(row.paid) }}</td>
            <td>{{ money(row.remaining) }}</td>
            <td v-if="capabilities.see_costs">{{ money(row.cost) }}</td>
            <td v-if="capabilities.see_holding_profit">{{ money(row.net_profit) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else-if="!rows.length" class="state-box">سرویس یا اشتراکی با فیلتر فعلی یافت نشد.</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
            <th>کلاینت</th>
            <th>پروژه</th>
            <th>سرویس</th>
            <th>پلن</th>
            <th>وضعیت</th>
            <th>تاریخ خرید</th>
            <th>انقضا</th>
            <th>روز باقی</th>
            <th v-if="capabilities.see_financial">مبلغ نهایی</th>
            <th v-if="capabilities.see_financial">مانده</th>
            <th>مصرف</th>
            <th>عملیات</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td><input type="checkbox" :checked="selectedIds.includes(row.id)" @change="toggleOne(row.id)" /></td>
            <td>{{ row.client_name }}</td>
            <td>{{ row.project_name }}</td>
            <td>{{ row.product_title }}</td>
            <td>{{ row.plan_title || '—' }}</td>
            <td><span class="badge" :class="row.status">{{ statusLabel(row.status) }}</span></td>
            <td>{{ formatJalaliDate(row.purchased_at) }}</td>
            <td>{{ row.ends_at ? formatJalaliDate(row.ends_at) : '—' }}</td>
            <td>{{ row.days_remaining == null ? '—' : toFa(row.days_remaining) }}</td>
            <td v-if="capabilities.see_financial">{{ money(row.final_amount) }}</td>
            <td v-if="capabilities.see_financial">{{ money(row.remaining_amount) }}</td>
            <td>{{ toFa(row.usage_used || 0) }} / {{ toFa(row.usage_cap || 0) }}</td>
            <td class="ops">
              <button type="button" class="link-btn" @click="openDetail(row)">جزئیات</button>
              <button v-if="capabilities.mutate_status || capabilities.register_payment" type="button" class="link-btn" @click="openAction(row)">عملیات</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pager">
        <button type="button" class="ghost-btn" :disabled="page <= 1" @click="page -= 1">قبلی</button>
        <span>صفحه {{ toFa(page) }} از {{ toFa(numPages) }} ({{ toFa(count) }})</span>
        <button type="button" class="ghost-btn" :disabled="page >= numPages" @click="page += 1">بعدی</button>
      </div>
    </div>

    <div v-if="detail" class="drawer-backdrop" @click.self="detail = null">
      <aside class="drawer">
        <header>
          <div>
            <h3>{{ detail.subscription?.product_title }}</h3>
            <p>{{ detail.subscription?.client_name }}</p>
          </div>
          <button type="button" class="ghost-btn" @click="detail = null">بستن</button>
        </header>
        <div class="drawer-grid">
          <article><small>وضعیت</small><strong>{{ statusLabel(detail.subscription?.status) }}</strong></article>
          <article><small>تاریخ خرید</small><strong>{{ formatJalaliDate(detail.subscription?.purchased_at) }}</strong></article>
          <article><small>فعالسازی</small><strong>{{ formatJalaliDate(detail.subscription?.activated_at) }}</strong></article>
          <article><small>شروع / پایان</small><strong>{{ formatJalaliDate(detail.subscription?.starts_at) }} / {{ detail.subscription?.ends_at ? formatJalaliDate(detail.subscription.ends_at) : '—' }}</strong></article>
          <article v-if="capabilities.see_financial"><small>مبلغ نهایی</small><strong>{{ money(detail.subscription?.final_amount) }}</strong></article>
          <article v-if="capabilities.see_financial"><small>مانده</small><strong>{{ money(detail.subscription?.remaining_amount) }}</strong></article>
          <article><small>مصرف</small><strong>{{ toFa(detail.subscription?.usage_used) }} / {{ toFa(detail.subscription?.usage_cap) }}</strong></article>
        </div>
        <h4>دوره‌ها</h4>
        <ul>
          <li v-for="period in detail.periods || []" :key="`p-${period.id}`">
            {{ period.kind }} — {{ formatJalaliDate(period.starts_at) }} تا {{ period.ends_at ? formatJalaliDate(period.ends_at) : '—' }}
            <span v-if="capabilities.see_financial"> / {{ money(period.final_amount) }}</span>
          </li>
        </ul>
        <h4 v-if="capabilities.see_financial">پرداخت‌ها</h4>
        <ul v-if="capabilities.see_financial">
          <li v-for="payment in detail.payments || []" :key="`pay-${payment.id}`">
            {{ money(payment.amount) }} — {{ payment.method || '—' }} — {{ formatJalaliDateTime(payment.paid_at) }}
          </li>
        </ul>
        <h4>لاگ عملیات</h4>
        <ul>
          <li v-for="log in detail.audit_logs || []" :key="`a-${log.id}`">
            {{ log.action }} توسط {{ log.actor_name || 'سیستم' }} — {{ log.reason || log.note || '' }}
            <small v-if="log.created_at"> ({{ formatJalaliDateTime(log.created_at) }})</small>
          </li>
        </ul>
      </aside>
    </div>

    <div v-if="actionModal.open" class="drawer-backdrop" @click.self="actionModal.open = false">
      <aside class="drawer action-drawer">
        <h3>عملیات روی {{ actionModal.subscription?.product_title }}</h3>
        <label>عملیات
          <select v-model="actionModal.action">
            <option v-for="item in actionOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <label>دلیل
          <input v-model="actionModal.reason" type="text" />
        </label>
        <label>یادداشت
          <textarea v-model="actionModal.note" rows="3" />
        </label>
        <label v-if="['extend_days', 'free_activate'].includes(actionModal.action)">روز
          <input v-model.number="actionModal.days" type="number" min="1" />
        </label>
        <label v-if="['register_payment', 'apply_discount'].includes(actionModal.action)">مبلغ
          <input v-model="actionModal.amount" type="number" min="0" />
        </label>
        <label v-if="actionModal.action === 'register_payment'">کد پیگیری
          <input v-model="actionModal.tracking_code" type="text" />
        </label>
        <div class="header-actions">
          <button type="button" class="ghost-btn" @click="actionModal.open = false">انصراف</button>
          <button type="button" class="primary-btn" @click="submitAction">اجرا</button>
        </div>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.services-shell {
  display: grid;
  gap: 1rem;
}
.services-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  padding: 1.1rem 1.25rem;
}
.services-header h2 {
  margin: 0.15rem 0;
  color: #0f172a;
}
.services-header p,
.kicker {
  margin: 0;
  color: #64748b;
}
.header-actions,
.bulk-bar,
.pager,
.ops {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
}
.kpi-card,
.alert-card,
.owned-card,
.missing-card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 14px;
  padding: 0.85rem 1rem;
}
.kpi-card small,
.alert-card small {
  color: #64748b;
}
.kpi-card strong {
  display: block;
  margin-top: 0.35rem;
  font-size: 1.05rem;
  color: #0f172a;
}
.filter-bar,
.subtabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}
.filter-bar :deep(.base-date-picker) {
  min-width: 160px;
}
.filter-bar :deep(.picker-input) {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 10px;
  padding: 0.55rem 0.7rem;
  background: #fff;
}
.filter-bar input,
.filter-bar select,
.drawer label input,
.drawer label select,
.drawer label textarea {
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 10px;
  padding: 0.55rem 0.7rem;
  background: #fff;
  min-width: 140px;
}
.check {
  display: inline-flex;
  gap: 0.35rem;
  align-items: center;
  background: #fff;
  border-radius: 10px;
  padding: 0.45rem 0.7rem;
  border: 1px solid rgba(148, 163, 184, 0.2);
}
.subtab,
.ghost-btn,
.primary-btn,
.link-btn {
  border: 0;
  cursor: pointer;
}
.subtab,
.ghost-btn {
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  padding: 0.45rem 0.9rem;
  color: #334155;
}
.subtab.active,
.primary-btn {
  background: #0f172a;
  color: #fff;
  border-radius: 999px;
  padding: 0.5rem 1rem;
}
.table-wrap,
.revenue-panel,
.client-panel,
.state-box {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 16px;
  padding: 0.85rem;
  overflow: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  min-width: 980px;
}
th,
td {
  text-align: right;
  padding: 0.65rem 0.5rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
  font-size: 0.92rem;
}
.badge {
  display: inline-flex;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  background: #e2e8f0;
}
.badge.active,
.badge.near_expiry { background: #dcfce7; color: #166534; }
.badge.expired,
.badge.blocked,
.badge.suspended { background: #fee2e2; color: #991b1b; }
.badge.pending_payment,
.badge.pending_activation { background: #ffedd5; color: #9a3412; }
.link-btn {
  background: transparent;
  color: #0369a1;
  padding: 0;
}
.alerts-strip,
.client-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.65rem;
}
.alert-card.critical { border-color: rgba(220, 38, 38, 0.35); }
.alert-card.warning { border-color: rgba(217, 119, 6, 0.35); }
.missing-card { opacity: 0.75; }
.state-banner {
  border-radius: 12px;
  padding: 0.75rem 1rem;
}
.state-banner.error { background: #fef2f2; color: #991b1b; }
.state-banner.success { background: #ecfdf5; color: #065f46; }
.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  justify-content: flex-start;
  z-index: 40;
}
.drawer {
  width: min(460px, 100%);
  background: #fff;
  height: 100%;
  overflow: auto;
  padding: 1rem;
  display: grid;
  gap: 0.75rem;
}
.drawer header {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}
.drawer-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.55rem;
}
.drawer-grid article,
.drawer label {
  display: grid;
  gap: 0.35rem;
  background: #f8fafc;
  border-radius: 12px;
  padding: 0.7rem;
}
.bulk-bar {
  background: #0f172a;
  color: #fff;
  border-radius: 12px;
  padding: 0.7rem 0.9rem;
}
.bulk-bar .ghost-btn {
  color: #0f172a;
}
@media (max-width: 900px) {
  .services-header {
    flex-direction: column;
  }
  .drawer-backdrop {
    justify-content: stretch;
  }
  .drawer {
    width: 100%;
  }
}
</style>
