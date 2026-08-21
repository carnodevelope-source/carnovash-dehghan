<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../services/api'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import { useAuthStore } from '../../store/auth.store'
import { formatJalaliDate, formatJalaliDateTime, parseJalaliToIso } from '../../utils/date'
import { formatMoney, formatFaNumber, formatDaysRemaining } from '../../modules/hq/utils/formatters.js'
import { readQueryState, buildQueryPatch } from '../../modules/hq/utils/query-state.js'
import {
  SERVICE_REPORT_TABS,
  SERVICE_STATUS_OPTIONS,
  SERVICE_PAYMENT_OPTIONS,
  SERVICE_ORDERING_OPTIONS
} from '../../modules/hq/constants/hq-report-tabs.js'
import { useHqCapabilities } from '../../modules/hq/composables/useHqCapabilities.js'
import HqPageHeader from '../../modules/hq/components/shared/HqPageHeader.vue'
import HqKpiCard from '../../modules/hq/components/shared/HqKpiCard.vue'
import HqStatusBadge from '../../modules/hq/components/shared/HqStatusBadge.vue'
import HqEmptyState from '../../modules/hq/components/shared/HqEmptyState.vue'
import '../../modules/hq/styles/hq-ui.css'

const props = defineProps({
  carwashes: { type: Array, default: () => [] }
})

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const QUERY_DEFAULTS = {
  tab: 'services',
  report: 'all',
  status: '',
  payment: '',
  tenant: '',
  ordering: '-updated_at',
  page: '1',
  search: '',
  project: '',
  product: '',
  has_debt: '',
  near_expiry: '',
  date_from: '',
  date_to: ''
}

const apiCapabilities = ref({})
const { seeFinancial, seeHoldingProfit, canMutateStatus, canRegisterPayment, canExport, canBulk } =
  useHqCapabilities(apiCapabilities)

const initialLoad = ref(true)
const refreshing = ref(false)
const tableLoading = ref(false)
const tableError = ref('')
const toast = ref('')
const lastUpdated = ref(null)

const summary = reactive({})
const catalog = reactive({ projects: [], products: [] })
const rows = ref([])
const count = ref(0)
const numPages = ref(1)
const revenue = ref(null)
const revenueGroup = ref('product')
const alerts = ref([])
const alertsOpen = ref(false)
const clientDetail = ref(null)
const selectedIds = ref([])
const detail = ref(null)
const detailTab = ref('overview')
const detailLoading = ref(false)
const openRowMenuId = ref(null)
const rowMenuStyle = ref({})
const moreFiltersOpen = ref(false)
const headerMenuOpen = ref(false)
const OVERLAY_Z = 240

function closeFloatingMenus() {
  openRowMenuId.value = null
  moreFiltersOpen.value = false
  headerMenuOpen.value = false
}

function positionRowMenu(anchorEl) {
  if (!anchorEl) return
  const rect = anchorEl.getBoundingClientRect()
  const menuWidth = 220
  const maxMenuHeight = 360
  const pad = 8
  let left = rect.right - menuWidth
  left = Math.max(pad, Math.min(left, window.innerWidth - menuWidth - pad))
  const spaceBelow = window.innerHeight - rect.bottom - pad
  const spaceAbove = rect.top - pad
  const placeBelow = spaceBelow >= Math.min(240, spaceAbove)
  const top = placeBelow
    ? rect.bottom + 6
    : Math.max(pad, rect.top - Math.min(maxMenuHeight, spaceAbove) - 6)
  const available = placeBelow ? spaceBelow : Math.max(120, top === pad ? spaceAbove : rect.top - top - 6)
  rowMenuStyle.value = {
    position: 'fixed',
    top: `${Math.round(top)}px`,
    left: `${Math.round(left)}px`,
    width: `${menuWidth}px`,
    maxHeight: `${Math.round(Math.min(maxMenuHeight, available))}px`,
    zIndex: String(OVERLAY_Z + 1)
  }
}

function toggleRowMenu(event, rowId) {
  event.preventDefault()
  event.stopPropagation()
  const anchor = event.currentTarget
  if (!(anchor instanceof Element)) return
  const id = Number(rowId)
  if (Number(openRowMenuId.value) === id) {
    openRowMenuId.value = null
    return
  }
  moreFiltersOpen.value = false
  headerMenuOpen.value = false
  positionRowMenu(anchor)
  openRowMenuId.value = id
  nextTick(() => positionRowMenu(anchor))
}

function onDocPointerDown(event) {
  if (openRowMenuId.value == null && !moreFiltersOpen.value && !headerMenuOpen.value) return
  const target = event.target
  if (!(target instanceof Element)) return
  if (target.closest('[data-hq-float-menu]') || target.closest('[data-hq-menu-trigger]')) return
  closeFloatingMenus()
}

function onViewportChange() {
  if (openRowMenuId.value != null) closeFloatingMenus()
}

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

const reportKey = ref('all')
const tenantId = ref('')
const page = ref(1)
const pageSize = 20
let searchTimer = null
let syncingFromRoute = false

const actionModal = reactive({
  open: false,
  loading: false,
  subscription: null,
  action: '',
  reason: '',
  note: '',
  days: 30,
  amount: '',
  plan_id: '',
  tracking_code: '',
  fieldError: '',
  generalError: '',
  confirmDebt: false
})

const bulkModal = reactive({
  open: false,
  loading: false,
  action: '',
  reason: '',
  note: '',
  error: ''
})

const seedConfirm = ref(false)
const seedLoading = ref(false)

const activeCarwashes = computed(() => (props.carwashes || []).filter((item) => item.is_active !== false))

const visibleReportTabs = computed(() =>
  SERVICE_REPORT_TABS.filter((tab) => !tab.financialOnly || seeFinancial.value)
)

const activeReportTab = computed(() =>
  SERVICE_REPORT_TABS.find((tab) => tab.key === reportKey.value) || SERVICE_REPORT_TABS[0]
)

const lockedProduct = computed(() => {
  const tab = activeReportTab.value
  if (!tab?.productKey || reportKey.value === 'all' || reportKey.value === 'revenue') return null
  return { key: tab.productKey, label: tab.lockedLabel || tab.label }
})

const alertCounts = computed(() => {
  const counts = { critical: 0, warning: 0, info: 0 }
  alerts.value.forEach((item) => {
    const key = item.severity || 'info'
    if (counts[key] !== undefined) counts[key] += 1
  })
  return counts
})

const blockedPendingCount = computed(() =>
  Number(summary.blocked_count || 0) + Number(summary.pending_payment_count || 0)
)

const kpiCards = computed(() => {
  const cards = [
    { key: 'clients', label: 'کلاینت فعال', value: formatFaNumber(summary.clients_count) },
    { key: 'active', label: 'سرویس فعال', value: formatFaNumber(summary.active_count) },
    { key: 'near', label: 'نزدیک انقضا', value: formatFaNumber(summary.near_expiry_count), tone: 'warning' },
    {
      key: 'blocked',
      label: 'مسدود/در انتظار اقدام',
      value: formatFaNumber(blockedPendingCount.value),
      tone: blockedPendingCount.value > 0 ? 'danger' : 'default'
    }
  ]
  if (seeFinancial.value) {
    cards.push(
      { key: 'sales', label: 'فروش کل', value: formatMoney(summary.sales_revenue) },
      { key: 'paid', label: 'وصول‌شده', value: formatMoney(summary.paid_revenue) },
      { key: 'recv', label: 'مطالبات', value: formatMoney(summary.receivables), tone: 'warning' }
    )
  }
  return cards
})

const revenueKpis = computed(() => {
  const s = revenue.value?.summary || summary
  const sales = Number(s.sales_revenue || 0)
  const paid = Number(s.paid_revenue || 0)
  const remaining = Number(s.receivables || 0)
  const rate = sales > 0 ? ((paid / sales) * 100).toFixed(1) : null
  return [
    { label: 'فروش', value: formatMoney(sales) },
    { label: 'وصول‌شده', value: formatMoney(paid) },
    { label: 'مانده', value: formatMoney(remaining) },
    { label: 'نرخ وصول', value: rate !== null ? `${formatFaNumber(rate)}٪` : '—' }
  ]
})

const revenueRows = computed(() => {
  const list = revenue.value?.by_product || []
  if (revenueGroup.value === 'share') {
    const map = {}
    list.forEach((row) => {
      const key = row.share_owner || 'none'
      if (!map[key]) {
        map[key] = {
          product_title: row.share_owner_label || '—',
          share_owner: key,
          share_owner_label: row.share_owner_label || '—',
          subscriptions_count: 0,
          sales: 0,
          paid: 0,
          remaining: 0
        }
      }
      map[key].subscriptions_count += Number(row.subscriptions_count || 0)
      map[key].sales += Number(row.sales || 0)
      map[key].paid += Number(row.paid || 0)
      map[key].remaining += Number(row.remaining || 0)
    })
    return Object.values(map)
  }
  return list
})

const revenueFooter = computed(() => {
  const list = revenueRows.value
  return list.reduce(
    (acc, row) => ({
      count: acc.count + Number(row.subscriptions_count || 0),
      sales: acc.sales + Number(row.sales || 0),
      paid: acc.paid + Number(row.paid || 0),
      remaining: acc.remaining + Number(row.remaining || 0)
    }),
    { count: 0, sales: 0, paid: 0, remaining: 0 }
  )
})

const allSelected = computed(() => rows.value.length > 0 && selectedIds.value.length === rows.value.length)
const hasActiveFilters = computed(() =>
  Boolean(
    filters.search ||
      filters.project_id ||
      filters.product_key ||
      filters.status ||
      filters.payment_status ||
      filters.has_debt ||
      filters.near_expiry ||
      filters.date_from ||
      filters.date_to ||
      tenantId.value
  )
)

const freshnessLabel = computed(() =>
  lastUpdated.value ? `آخرین بروزرسانی: ${formatJalaliDateTime(lastUpdated.value)}` : ''
)

const activeFilterChips = computed(() => {
  const chips = []
  if (filters.search) chips.push({ key: 'search', label: `جستجو: ${filters.search}` })
  if (filters.project_id) {
    const p = catalog.projects.find((x) => String(x.id) === String(filters.project_id))
    chips.push({ key: 'project', label: `پروژه: ${p?.name || filters.project_id}` })
  }
  if (lockedProduct.value) chips.push({ key: 'locked', label: lockedProduct.value.label, locked: true })
  else if (filters.product_key) {
    const pr = catalog.products.find((x) => x.product_key === filters.product_key)
    chips.push({ key: 'product', label: `سرویس: ${pr?.title || filters.product_key}` })
  }
  if (filters.status) {
    const s = SERVICE_STATUS_OPTIONS.find((x) => x.value === filters.status)
    chips.push({ key: 'status', label: `وضعیت: ${s?.label || filters.status}` })
  }
  if (seeFinancial.value && filters.payment_status) {
    const p = SERVICE_PAYMENT_OPTIONS.find((x) => x.value === filters.payment_status)
    chips.push({ key: 'payment', label: `پرداخت: ${p?.label || filters.payment_status}` })
  }
  if (tenantId.value) {
    const t = activeCarwashes.value.find((x) => String(x.id) === String(tenantId.value))
    chips.push({ key: 'tenant', label: `کلاینت: ${t?.name || tenantId.value}` })
  }
  if (filters.has_debt) chips.push({ key: 'has_debt', label: 'بدهکار' })
  if (filters.near_expiry) chips.push({ key: 'near_expiry', label: 'نزدیک انقضا' })
  if (filters.date_from) chips.push({ key: 'date_from', label: `از ${filters.date_from}` })
  if (filters.date_to) chips.push({ key: 'date_to', label: `تا ${filters.date_to}` })
  return chips
})

const alertsGrouped = computed(() => {
  const groups = { critical: [], warning: [], info: [] }
  alerts.value.forEach((item) => {
    const key = groups[item.severity] ? item.severity : 'info'
    groups[key].push(item)
  })
  return groups
})

const activeMenuRow = computed(() => {
  if (openRowMenuId.value == null) return null
  return rows.value.find((r) => Number(r.id) === Number(openRowMenuId.value)) || null
})

const ACTION_META = {
  activate: { label: 'فعال‌سازی', cta: 'فعال‌کردن سرویس', tone: 'primary', group: 'access', needsReason: true },
  deactivate: { label: 'غیرفعال‌سازی', cta: 'غیرفعال‌کردن سرویس', tone: 'danger', group: 'access', needsReason: true, warn: 'دسترسی سرویس قطع می‌شود.' },
  suspend: { label: 'تعلیق', cta: 'تعلیق سرویس', tone: 'warning', group: 'access', needsReason: true },
  unsuspend: { label: 'رفع تعلیق', cta: 'رفع تعلیق', tone: 'primary', group: 'access', needsReason: true },
  block: { label: 'مسدودسازی', cta: 'مسدودکردن سرویس', tone: 'danger', group: 'access', needsReason: true, warn: 'سرویس مسدود می‌شود.' },
  restore: { label: 'بازگردانی', cta: 'بازگردانی سرویس', tone: 'primary', group: 'access', needsReason: true },
  extend_days: { label: 'تمدید روز', cta: 'افزودن روز', tone: 'primary', group: 'contract', needsReason: true, needsDays: true },
  renew: { label: 'تمدید رسمی', cta: 'ثبت تمدید', tone: 'primary', group: 'contract', needsReason: true, needsPlan: true },
  change_plan: { label: 'تغییر پلن', cta: 'تغییر پلن', tone: 'primary', group: 'contract', needsPlan: true },
  register_payment: { label: 'ثبت پرداخت', cta: 'ثبت پرداخت', tone: 'success', group: 'finance', needsAmount: true },
  apply_discount: { label: 'اعمال تخفیف', cta: 'اعمال تخفیف', tone: 'warning', group: 'finance', needsReason: true, needsAmount: true },
  forgive_debt: { label: 'بخشش بدهی', cta: 'بخشش بدهی', tone: 'danger', group: 'finance', needsReason: true, needsConfirm: true },
  free_activate: { label: 'فعال‌سازی رایگان', cta: 'فعال‌سازی رایگان', tone: 'warning', group: 'special', needsReason: true, needsDays: true }
}

const STATUS_ACTIONS = {
  active: ['deactivate', 'suspend', 'block', 'extend_days', 'renew', 'change_plan', 'register_payment', 'apply_discount', 'forgive_debt'],
  near_expiry: ['extend_days', 'renew', 'deactivate', 'suspend', 'register_payment'],
  inactive: ['activate', 'free_activate', 'renew', 'change_plan'],
  expired: ['activate', 'renew', 'free_activate'],
  blocked: ['restore', 'deactivate'],
  suspended: ['unsuspend', 'deactivate', 'block'],
  pending_payment: ['activate', 'register_payment', 'apply_discount', 'forgive_debt'],
  pending_activation: ['activate', 'free_activate'],
  cancelled: ['activate', 'renew'],
  not_renewed: ['renew', 'activate', 'free_activate']
}

function getValidActions(sub) {
  if (!sub) return []
  const base = STATUS_ACTIONS[sub.status] || ['activate']
  const list = base.filter((action) => {
    const meta = ACTION_META[action]
    if (!meta) return false
    if (meta.group === 'access' || meta.group === 'contract' || meta.group === 'special') {
      if (!canMutateStatus.value) return false
    }
    if (meta.group === 'finance') {
      if (!canRegisterPayment.value || !seeFinancial.value) return false
      if (action === 'register_payment' && Number(sub.remaining_amount || 0) <= 0) return false
      if (action === 'forgive_debt' && Number(sub.remaining_amount || 0) <= 0) return false
    }
    if (action === 'change_plan' && !canMutateStatus.value) return false
    if (action === 'renew' && !(canMutateStatus.value || canRegisterPayment.value)) return false
    return true
  })
  return list.map((action) => ({ action, ...ACTION_META[action] }))
}

function groupedActions(sub) {
  const valid = getValidActions(sub)
  const groups = [
    { key: 'access', label: 'دسترسی' },
    { key: 'contract', label: 'قرارداد' },
    { key: 'finance', label: 'مالی' },
    { key: 'special', label: 'ویژه' }
  ]
  return groups
    .map((g) => ({ ...g, items: valid.filter((item) => item.group === g.key) }))
    .filter((g) => g.items.length)
}

function shareAccent(owner) {
  if (owner === 'carno' || owner === 'hq') return '#1976D2'
  if (owner === 'arakar' || owner === 'rah') return '#7C3AED'
  return 'transparent'
}

function remainingLabel(value) {
  const n = Number(value || 0)
  if (n <= 0) return 'تسویه‌شده'
  return formatMoney(n)
}

function collectionRate(row) {
  const sales = Number(row.sales || 0)
  const paid = Number(row.paid || 0)
  if (sales <= 0) return '—'
  return `${formatFaNumber(((paid / sales) * 100).toFixed(1))}٪`
}

function buildApiParams(extra = {}) {
  const params = {
    page: page.value,
    page_size: pageSize,
    ordering: filters.ordering,
    ...extra
  }
  if (filters.search) params.search = filters.search
  if (filters.project_id) params.project_id = filters.project_id
  const productKey = lockedProduct.value?.key || filters.product_key
  if (productKey) params.product_key = productKey
  if (filters.status) params.status = filters.status
  if (seeFinancial.value && filters.payment_status) params.payment_status = filters.payment_status
  if (filters.has_debt) params.has_debt = '1'
  if (filters.near_expiry) params.near_expiry = '1'
  const dateFrom = parseJalaliToIso(filters.date_from)
  const dateTo = parseJalaliToIso(filters.date_to)
  if (dateFrom) params.date_from = dateFrom
  if (dateTo) params.date_to = dateTo
  if (tenantId.value) params.tenant_id = tenantId.value
  return params
}

function syncRouteQuery() {
  if (syncingFromRoute) return
  const patch = buildQueryPatch(route.query, {
    tab: 'services',
    report: reportKey.value === 'all' ? '' : reportKey.value,
    status: filters.status,
    payment: seeFinancial.value ? filters.payment_status : '',
    tenant: tenantId.value,
    ordering: filters.ordering === '-updated_at' ? '' : filters.ordering,
    page: page.value > 1 ? page.value : '',
    search: filters.search,
    project: filters.project_id,
    product: lockedProduct.value ? '' : filters.product_key,
    has_debt: filters.has_debt,
    near_expiry: filters.near_expiry,
    date_from: filters.date_from,
    date_to: filters.date_to
  })
  router.replace({ query: patch })
}

function applyRouteQuery() {
  syncingFromRoute = true
  const q = readQueryState(route, QUERY_DEFAULTS)
  reportKey.value = q.report || 'all'
  filters.status = q.status || ''
  filters.payment_status = q.payment || ''
  tenantId.value = q.tenant || ''
  filters.ordering = q.ordering || '-updated_at'
  page.value = Math.max(1, Number(q.page || 1))
  filters.search = q.search || ''
  filters.project_id = q.project || ''
  filters.product_key = q.product || ''
  filters.has_debt = q.has_debt === '1'
  filters.near_expiry = q.near_expiry === '1'
  filters.date_from = q.date_from || ''
  filters.date_to = q.date_to || ''
  const tab = activeReportTab.value
  if (tab?.productKey && reportKey.value === tab.key) filters.product_key = tab.productKey
  syncingFromRoute = false
}

async function loadCatalog() {
  const { data } = await api.get('/subscriptions/hq/catalog/')
  catalog.projects = data.projects || []
  catalog.products = data.products || []
  apiCapabilities.value = data.capabilities || {}
}

async function loadSummary() {
  const { data } = await api.get('/subscriptions/hq/summary/', {
    params: buildApiParams({ page: undefined, page_size: undefined })
  })
  Object.keys(summary).forEach((k) => delete summary[k])
  Object.assign(summary, data || {})
}

async function loadRows() {
  tableLoading.value = true
  tableError.value = ''
  try {
    if (reportKey.value === 'revenue') {
      if (!seeFinancial.value) {
        revenue.value = null
        rows.value = []
        return
      }
      const { data } = await api.get('/subscriptions/hq/revenue/', {
        params: buildApiParams({ page: undefined, page_size: undefined })
      })
      revenue.value = data
      if (data.summary) Object.assign(summary, data.summary)
      rows.value = []
      selectedIds.value = []
      return
    }
    const endpoint =
      reportKey.value === 'all'
        ? '/subscriptions/hq/subscriptions/'
        : `/subscriptions/hq/reports/${reportKey.value}/`
    const { data } = await api.get(endpoint, { params: buildApiParams() })
    rows.value = data.results || []
    count.value = data.count || 0
    page.value = data.page || page.value
    numPages.value = data.num_pages || 1
    if (data.summary) Object.assign(summary, data.summary)
    revenue.value = null
    selectedIds.value = []
  } catch (err) {
    tableError.value = err?.response?.status === 403
      ? 'دسترسی این عملیات برای نقش شما فعال نیست.'
      : 'بارگذاری لیست سرویس‌ها ناموفق بود.'
  } finally {
    tableLoading.value = false
  }
}

async function loadAlerts() {
  const { data } = await api.get('/subscriptions/hq/alerts/', { params: { page_size: 100 } })
  alerts.value = data.results || []
}

async function loadClient() {
  if (!tenantId.value) {
    clientDetail.value = null
    return
  }
  const { data } = await api.get(`/subscriptions/hq/clients/${tenantId.value}/services/`)
  clientDetail.value = data
}

async function invalidateAfterMutation(includeRevenue = false) {
  await Promise.all([
    loadSummary(),
    loadRows(),
    loadAlerts(),
    loadClient(),
    detail.value?.subscription?.id ? reloadDetail(detail.value.subscription.id) : Promise.resolve()
  ])
  if (includeRevenue && reportKey.value === 'revenue') await loadRows()
}

async function refreshAll() {
  refreshing.value = true
  tableError.value = ''
  try {
    // Nothing below reads the catalog, so gating them on it only added a round trip.
    await Promise.all([loadCatalog(), loadSummary(), loadRows(), loadAlerts(), loadClient()])
    lastUpdated.value = new Date()
  } catch {
    tableError.value = 'خطا در بارگذاری گزارش سرویس‌ها.'
  } finally {
    refreshing.value = false
    initialLoad.value = false
  }
}

async function openDetail(row) {
  detailLoading.value = true
  detailTab.value = 'overview'
  detail.value = { loading: true }
  try {
    const { data } = await api.get(`/subscriptions/hq/subscriptions/${row.id}/`)
    detail.value = data
  } catch {
    detail.value = null
    tableError.value = 'بارگذاری جزئیات ناموفق بود.'
  } finally {
    detailLoading.value = false
  }
}

async function reloadDetail(id) {
  const { data } = await api.get(`/subscriptions/hq/subscriptions/${id}/`)
  detail.value = data
}

function openAction(row, action) {
  actionModal.open = true
  actionModal.subscription = row
  actionModal.action = action
  actionModal.reason = ''
  actionModal.note = ''
  actionModal.days = 30
  actionModal.amount = ''
  actionModal.plan_id = row.plan || ''
  actionModal.tracking_code = ''
  actionModal.fieldError = ''
  actionModal.generalError = ''
  actionModal.confirmDebt = false
  actionModal.loading = false
  closeFloatingMenus()
}

function closeActionModal() {
  if (actionModal.loading) return
  actionModal.open = false
}

function validateActionForm() {
  const meta = ACTION_META[actionModal.action]
  actionModal.fieldError = ''
  actionModal.generalError = ''
  if (!meta) return false
  if (meta.needsReason && !actionModal.reason.trim()) {
    actionModal.fieldError = 'ثبت دلیل الزامی است.'
    return false
  }
  if (meta.needsDays && Number(actionModal.days) <= 0) {
    actionModal.fieldError = 'تعداد روز باید بیشتر از صفر باشد.'
    return false
  }
  if (meta.needsAmount && Number(actionModal.amount) <= 0) {
    actionModal.fieldError = 'مبلغ باید بیشتر از صفر باشد.'
    return false
  }
  if (meta.needsPlan && actionModal.action === 'change_plan' && String(actionModal.plan_id) === String(actionModal.subscription?.plan)) {
    actionModal.fieldError = 'پلن جدید باید متفاوت از پلن فعلی باشد.'
    return false
  }
  if (meta.needsConfirm && !actionModal.confirmDebt) {
    actionModal.fieldError = 'تأیید بخشش بدهی الزامی است.'
    return false
  }
  if (actionModal.action === 'register_payment' && seeFinancial.value) {
    const remaining = Number(actionModal.subscription?.remaining_amount || 0)
    if (remaining > 0 && Number(actionModal.amount) > remaining) {
      actionModal.generalError = 'مبلغ از مانده بیشتر است.'
      return false
    }
  }
  return true
}

async function submitAction() {
  if (!actionModal.subscription || actionModal.loading) return
  const meta = ACTION_META[actionModal.action]
  if (meta?.group === 'finance' && !canRegisterPayment.value) return
  if ((meta?.group === 'access' || meta?.group === 'contract') && !canMutateStatus.value) return
  if (!validateActionForm()) return

  actionModal.loading = true
  try {
    const payload = {
      action: actionModal.action,
      reason: actionModal.reason.trim(),
      note: actionModal.note.trim(),
      plan_id: actionModal.plan_id || undefined,
      payload: {
        days: Number(actionModal.days),
        amount: actionModal.amount,
        discount_amount: actionModal.amount,
        plan_id: actionModal.plan_id,
        tracking_code: actionModal.tracking_code,
        idempotency_key: `hq-${actionModal.subscription.id}-${Date.now()}`
      }
    }
    await api.post(`/subscriptions/hq/subscriptions/${actionModal.subscription.id}/actions/`, payload)
    actionModal.open = false
    toast.value = meta?.cta ? `${meta.cta} انجام شد.` : 'عملیات با موفقیت انجام شد.'
    await invalidateAfterMutation(['register_payment', 'apply_discount', 'forgive_debt', 'renew'].includes(actionModal.action))
  } catch (err) {
    actionModal.generalError =
      err?.response?.data?.detail ||
      err?.response?.data?.reason?.[0] ||
      'عملیات ناموفق بود.'
  } finally {
    actionModal.loading = false
  }
}

function openBulk(action) {
  if (!selectedIds.value.length || !canBulk.value) return
  bulkModal.open = true
  bulkModal.action = action
  bulkModal.reason = ''
  bulkModal.note = ''
  bulkModal.error = ''
}

async function submitBulk() {
  if (!selectedIds.value.length || bulkModal.loading) return
  bulkModal.loading = true
  bulkModal.error = ''
  try {
    await api.post('/subscriptions/hq/bulk/', {
      action: bulkModal.action,
      subscription_ids: selectedIds.value,
      payload: { reason: bulkModal.reason, note: bulkModal.note }
    })
    bulkModal.open = false
    selectedIds.value = []
    toast.value = 'عملیات گروهی اجرا شد.'
    await invalidateAfterMutation()
  } catch (err) {
    bulkModal.error = err?.response?.data?.detail || 'عملیات گروهی ناموفق بود.'
  } finally {
    bulkModal.loading = false
  }
}

async function exportCsv() {
  if (!canExport.value) return
  const response = await api.get('/subscriptions/hq/export/', {
    params: buildApiParams({ page: undefined, page_size: undefined }),
    responseType: 'blob'
  })
  const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'services-report.csv'
  link.click()
  window.URL.revokeObjectURL(url)
  toast.value = 'خروجی CSV آماده شد.'
}

async function seedCatalog() {
  if (!authStore.isHqAdmin || seedLoading.value) return
  seedLoading.value = true
  try {
    await api.post('/subscriptions/hq/seed/')
    seedConfirm.value = false
    headerMenuOpen.value = false
    toast.value = 'کاتالوگ همگام‌سازی شد.'
    await refreshAll()
  } catch {
    tableError.value = 'همگام‌سازی کاتالوگ ناموفق بود.'
  } finally {
    seedLoading.value = false
  }
}

function clearAllFilters() {
  filters.search = ''
  filters.project_id = ''
  filters.product_key = lockedProduct.value?.key || ''
  filters.status = ''
  filters.payment_status = ''
  filters.has_debt = false
  filters.near_expiry = false
  filters.date_from = ''
  filters.date_to = ''
  tenantId.value = ''
  page.value = 1
}

function removeChip(chip) {
  if (chip.locked) return
  if (chip.key === 'search') filters.search = ''
  if (chip.key === 'project') filters.project_id = ''
  if (chip.key === 'product') filters.product_key = lockedProduct.value?.key || ''
  if (chip.key === 'status') filters.status = ''
  if (chip.key === 'payment') filters.payment_status = ''
  if (chip.key === 'tenant') tenantId.value = ''
  if (chip.key === 'has_debt') filters.has_debt = false
  if (chip.key === 'near_expiry') filters.near_expiry = false
  if (chip.key === 'date_from') filters.date_from = ''
  if (chip.key === 'date_to') filters.date_to = ''
}

function selectReport(key) {
  reportKey.value = key
  page.value = 1
  const tab = SERVICE_REPORT_TABS.find((t) => t.key === key)
  filters.product_key = tab?.productKey || ''
}

function toggleAll() {
  selectedIds.value = allSelected.value ? [] : rows.value.map((r) => r.id)
}

function toggleOne(id) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter((x) => x !== id)
    : [...selectedIds.value, id]
}

function onRowClick(row) {
  openDetail(row)
}

function openAlertSubscription(alert) {
  alertsOpen.value = false
  if (alert.subscription) openDetail({ id: alert.subscription })
  else if (alert.subscription_id) openDetail({ id: alert.subscription_id })
}

function closeClientContext() {
  tenantId.value = ''
}

function debouncedSearch(value) {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    filters.search = value
    page.value = 1
  }, 350)
}

const searchInput = ref('')
watch(
  () => filters.search,
  (v) => {
    if (searchInput.value !== v) searchInput.value = v
  },
  { immediate: true }
)
watch(searchInput, (v) => debouncedSearch(v))

watch(
  () => route.query,
  () => {
    applyRouteQuery()
    Promise.all([loadSummary(), loadRows(), loadClient()])
  },
  { deep: true }
)

watch(
  [
    reportKey,
    () => filters.search,
    () => filters.project_id,
    () => filters.product_key,
    () => filters.status,
    () => filters.payment_status,
    () => filters.has_debt,
    () => filters.near_expiry,
    () => filters.ordering,
    () => filters.date_from,
    () => filters.date_to,
    tenantId,
    page
  ],
  (_values, _old, onCleanup) => {
    if (syncingFromRoute) return
    let cancelled = false
    onCleanup(() => {
      cancelled = true
    })
    syncRouteQuery()
    Promise.all([loadSummary(), loadRows(), loadClient()]).then(() => {
      if (cancelled) return
    })
  }
)

watch(
  [
    () => filters.search,
    () => filters.project_id,
    () => filters.product_key,
    () => filters.status,
    () => filters.payment_status,
    () => filters.has_debt,
    () => filters.near_expiry,
    () => filters.ordering,
    () => filters.date_from,
    () => filters.date_to,
    tenantId,
    reportKey
  ],
  () => {
    if (syncingFromRoute) return
    page.value = 1
  }
)

watch(activeCarwashes, (list) => {
  if (!tenantId.value) return
  if (!list.some((item) => String(item.id) === String(tenantId.value))) tenantId.value = ''
})

watch(toast, (msg) => {
  if (!msg) return
  setTimeout(() => {
    toast.value = ''
  }, 3200)
})

onMounted(async () => {
  applyRouteQuery()
  document.addEventListener('mousedown', onDocPointerDown)
  window.addEventListener('resize', onViewportChange)
  window.addEventListener('scroll', onViewportChange, { capture: true, passive: true })
  await refreshAll()
})

onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  document.removeEventListener('mousedown', onDocPointerDown)
  window.removeEventListener('resize', onViewportChange)
  window.removeEventListener('scroll', onViewportChange, { capture: true })
})
</script>

<template>
  <section class="hq-services hq-surface" dir="rtl">
    <HqPageHeader
      breadcrumb="پنل HQ / سرویس‌ها"
      title="سرویس‌ها و اشتراک‌ها"
      subtitle="مدیریت اشتراک‌ها، وضعیت دسترسی و گزارش مالی شبکه"
      :freshness="freshnessLabel"
    >
      <template #actions>
        <button type="button" class="btn ghost" :disabled="refreshing" @click="refreshAll">
          {{ refreshing ? 'در حال بروزرسانی…' : 'بروزرسانی' }}
        </button>
        <button v-if="canExport" type="button" class="btn ghost" @click="exportCsv">خروجی CSV</button>
        <div v-if="authStore.isHqAdmin" class="menu-wrap">
          <button type="button" class="btn ghost icon" data-hq-menu-trigger aria-label="منوی بیشتر" @click="headerMenuOpen = !headerMenuOpen; moreFiltersOpen = false; openRowMenuId = null">⋯</button>
          <div v-if="headerMenuOpen" class="menu-pop" data-hq-float-menu>
            <button type="button" @click="seedConfirm = true; headerMenuOpen = false">همگام‌سازی کاتالوگ</button>
          </div>
        </div>
      </template>
    </HqPageHeader>

    <div v-if="toast" class="toast">{{ toast }}</div>

    <div class="alert-bar">
      <div class="alert-counts">
        <span class="count critical">{{ formatFaNumber(alertCounts.critical) }} بحرانی</span>
        <span class="count warning">{{ formatFaNumber(alertCounts.warning) }} هشدار</span>
        <span class="count info">{{ formatFaNumber(alertCounts.info) }} اطلاع</span>
      </div>
      <button type="button" class="btn link" @click="alertsOpen = true">مشاهده هشدارها</button>
    </div>

    <div class="kpi-row">
      <HqKpiCard
        v-for="card in kpiCards"
        :key="card.key"
        :label="card.label"
        :value="card.value"
        :tone="card.tone || 'default'"
      />
      <article v-if="seeHoldingProfit" class="holding-card">
        <small>سهم وصولی هلدینگ‌ها</small>
        <div class="holding-split">
          <div class="split carno">
            <span>کارنو</span>
            <strong>{{ formatMoney(summary.carno_paid) }}</strong>
          </div>
          <div class="split arakar">
            <span>آراکار</span>
            <strong>{{ formatMoney(summary.arakar_paid) }}</strong>
          </div>
        </div>
      </article>
    </div>

    <div class="report-tabs" role="tablist" aria-label="گزارش‌های سرویس">
      <button
        v-for="tab in visibleReportTabs"
        :key="tab.key"
        type="button"
        role="tab"
        class="report-tab"
        :class="{ active: reportKey === tab.key }"
        :aria-selected="reportKey === tab.key"
        @click="selectReport(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="filter-bar">
      <input v-model="searchInput" type="search" class="ctrl" placeholder="جستجوی کلاینت، سرویس، قرارداد…" aria-label="جستجو" />
      <select v-model="filters.project_id" class="ctrl" aria-label="پروژه">
        <option value="">همه پروژه‌ها</option>
        <option v-for="project in catalog.projects" :key="project.id" :value="String(project.id)">{{ project.name }}</option>
      </select>
      <select v-if="!lockedProduct" v-model="filters.product_key" class="ctrl" aria-label="سرویس">
        <option value="">همه سرویس‌ها</option>
        <option v-for="product in catalog.products" :key="product.id" :value="product.product_key">{{ product.title }}</option>
      </select>
      <span v-else class="chip locked">{{ lockedProduct.label }}</span>
      <select v-model="filters.status" class="ctrl" aria-label="وضعیت">
        <option v-for="item in SERVICE_STATUS_OPTIONS" :key="item.value || 'all'" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-if="seeFinancial" v-model="filters.payment_status" class="ctrl" aria-label="وضعیت پرداخت">
        <option v-for="item in SERVICE_PAYMENT_OPTIONS" :key="item.value || 'pay'" :value="item.value">{{ item.label }}</option>
      </select>
      <div class="menu-wrap">
        <button type="button" class="btn ghost" data-hq-menu-trigger @click="moreFiltersOpen = !moreFiltersOpen; headerMenuOpen = false; openRowMenuId = null">فیلترهای بیشتر</button>
        <div v-if="moreFiltersOpen" class="menu-pop filters-pop" data-hq-float-menu>
          <label>کلاینت<select v-model="tenantId" class="ctrl wide">
            <option value="">همه کلاینت‌ها</option>
            <option v-for="item in activeCarwashes" :key="item.id" :value="String(item.id)">{{ item.name }}</option>
          </select></label>
          <label class="check"><input v-model="filters.has_debt" type="checkbox" /> بدهکار</label>
          <label class="check"><input v-model="filters.near_expiry" type="checkbox" /> نزدیک انقضا</label>
          <label>از تاریخ<BaseDatePicker v-model="filters.date_from" placeholder="از تاریخ خرید" /></label>
          <label>تا تاریخ<BaseDatePicker v-model="filters.date_to" placeholder="تا تاریخ خرید" /></label>
          <label>مرتب‌سازی<select v-model="filters.ordering" class="ctrl wide">
            <option v-for="item in SERVICE_ORDERING_OPTIONS" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select></label>
        </div>
      </div>
      <button v-if="hasActiveFilters" type="button" class="btn link" @click="clearAllFilters">پاک‌کردن همه</button>
    </div>

    <div v-if="activeFilterChips.length" class="chips-row">
      <button
        v-for="chip in activeFilterChips"
        :key="chip.key"
        type="button"
        class="chip"
        :class="{ locked: chip.locked }"
        :disabled="chip.locked"
        @click="removeChip(chip)"
      >
        {{ chip.label }}<span v-if="!chip.locked"> ×</span>
      </button>
    </div>

    <article v-if="clientDetail" class="client-card">
      <header>
        <div>
          <h3>{{ clientDetail.tenant?.name }}</h3>
          <p>{{ formatFaNumber(clientDetail.summary?.active_count || 0) }} سرویس فعال</p>
          <p v-if="seeFinancial" class="muted">
            فروش {{ formatMoney(clientDetail.summary?.sales_revenue) }} · مانده {{ formatMoney(clientDetail.summary?.receivables) }}
          </p>
        </div>
        <button type="button" class="btn ghost" @click="closeClientContext">بستن</button>
      </header>
      <div class="owned-chips">
        <button
          v-for="sub in clientDetail.subscriptions || []"
          :key="sub.id"
          type="button"
          class="owned-chip"
          @click="openDetail(sub)"
        >
          <span>{{ sub.product_title }}</span>
          <HqStatusBadge :value="sub.status" />
        </button>
      </div>
      <details v-if="(clientDetail.not_purchased || []).length">
        <summary>سرویس‌های خریداری‌نشده ({{ formatFaNumber(clientDetail.not_purchased.length) }})</summary>
        <div class="missing-chips">
          <span v-for="product in clientDetail.not_purchased" :key="product.id" class="missing-chip">{{ product.title }}</span>
        </div>
      </details>
    </article>

    <div v-if="reportKey === 'revenue' && seeFinancial" class="panel">
      <div class="revenue-kpis">
        <HqKpiCard v-for="kpi in revenueKpis" :key="kpi.label" :label="kpi.label" :value="kpi.value" compact />
      </div>
      <div class="seg">
        <button type="button" :class="{ active: revenueGroup === 'product' }" @click="revenueGroup = 'product'">بر اساس سرویس</button>
        <button type="button" :class="{ active: revenueGroup === 'share' }" @click="revenueGroup = 'share'">بر اساس مالک سهم</button>
      </div>
      <div v-if="tableLoading && initialLoad" class="skeleton-table"><div v-for="n in 8" :key="n" class="sk-row" /></div>
      <div v-else-if="tableError" class="error-box">
        <p>{{ tableError }}</p>
        <button type="button" class="btn primary" @click="loadRows">تلاش مجدد</button>
      </div>
      <div v-else-if="!revenueRows.length" class="panel-body">
        <HqEmptyState
          :title="hasActiveFilters ? 'نتیجه‌ای با این فیلترها پیدا نشد.' : 'در این بازه داده‌ای ثبت نشده است.'"
          :action-label="hasActiveFilters ? 'پاک‌کردن فیلترها' : ''"
          @action="clearAllFilters"
        />
      </div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ revenueGroup === 'share' ? 'مالک سهم' : 'سرویس' }}</th>
              <th v-if="revenueGroup === 'product'">مالک سهم</th>
              <th>تعداد</th>
              <th>فروش</th>
              <th>وصول‌شده</th>
              <th>مانده</th>
              <th>نرخ وصول</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in revenueRows" :key="`${row.product_key || row.share_owner}-${row.product_title}`">
              <td>{{ row.product_title }}</td>
              <td v-if="revenueGroup === 'product'"><HqStatusBadge kind="share" :value="row.share_owner" /></td>
              <td>{{ formatFaNumber(row.subscriptions_count) }}</td>
              <td class="money">{{ formatMoney(row.sales) }}</td>
              <td class="money">{{ formatMoney(row.paid) }}</td>
              <td class="money">{{ formatMoney(row.remaining) }}</td>
              <td>{{ collectionRate(row) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td :colspan="revenueGroup === 'product' ? 2 : 1"><strong>جمع</strong></td>
              <td>{{ formatFaNumber(revenueFooter.count) }}</td>
              <td class="money">{{ formatMoney(revenueFooter.sales) }}</td>
              <td class="money">{{ formatMoney(revenueFooter.paid) }}</td>
              <td class="money">{{ formatMoney(revenueFooter.remaining) }}</td>
              <td>{{ collectionRate(revenueFooter) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>

    <div v-else class="panel">
      <div v-if="tableLoading && initialLoad" class="skeleton-table"><div v-for="n in 8" :key="n" class="sk-row" /></div>
      <div v-else-if="tableError" class="error-box">
        <p>{{ tableError }}</p>
        <button type="button" class="btn primary" @click="loadRows">تلاش مجدد</button>
      </div>
      <div v-else-if="!rows.length" class="panel-body">
        <HqEmptyState
          :title="hasActiveFilters ? 'نتیجه‌ای با این فیلترها پیدا نشد.' : 'در این بازه داده‌ای ثبت نشده است.'"
          :action-label="hasActiveFilters ? 'پاک‌کردن فیلترها' : ''"
          @action="clearAllFilters"
        />
      </div>
      <div v-else class="table-wrap" :class="{ dim: tableLoading }">
        <table>
          <thead>
            <tr>
              <th class="sticky-start"><input type="checkbox" :checked="allSelected" aria-label="انتخاب همه" @change="toggleAll" /></th>
              <th class="sticky-start second">کلاینت</th>
              <th>سرویس</th>
              <th>پلن</th>
              <th>وضعیت</th>
              <th>تاریخ خرید</th>
              <th>انقضا</th>
              <th v-if="seeFinancial">فروش</th>
              <th v-if="seeFinancial">وصول</th>
              <th v-if="seeFinancial">مانده</th>
              <th class="sticky-end">عملیات</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="row.id"
              class="data-row"
              :style="{ '--accent': shareAccent(row.share_owner) }"
              @click="onRowClick(row)"
            >
              <td class="sticky-start" @click.stop>
                <input type="checkbox" :checked="selectedIds.includes(row.id)" :aria-label="`انتخاب ${row.client_name}`" @change="toggleOne(row.id)" />
              </td>
              <td class="sticky-start second">{{ row.client_name }}</td>
              <td>
                <div class="service-cell">
                  <strong>{{ row.product_title }}</strong>
                  <HqStatusBadge kind="share" :value="row.share_owner" />
                </div>
              </td>
              <td>{{ row.feature_payment_plan_label || row.plan_title || '—' }}</td>
              <td><HqStatusBadge :value="row.status" /></td>
              <td>{{ formatJalaliDate(row.purchased_at) }}</td>
              <td>
                <div class="ends-cell">
                  <span>{{ row.ends_at ? formatJalaliDate(row.ends_at) : '—' }}</span>
                  <small v-if="row.ends_at && formatDaysRemaining(row.ends_at)">{{ formatDaysRemaining(row.ends_at) }}</small>
                </div>
              </td>
              <td v-if="seeFinancial" class="money">{{ formatMoney(row.final_amount) }}</td>
              <td v-if="seeFinancial" class="money">{{ formatMoney(row.paid_amount) }}</td>
              <td v-if="seeFinancial" class="money" :class="{ settled: Number(row.remaining_amount || 0) <= 0 }">{{ remainingLabel(row.remaining_amount) }}</td>
              <td class="sticky-end ops" @click.stop>
                <button
                  type="button"
                  class="btn ghost sm"
                  data-hq-menu-trigger
                  :aria-expanded="Number(openRowMenuId) === Number(row.id)"
                  @mousedown.stop.prevent="toggleRowMenu($event, row.id)"
                >
                  عملیات
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="pager">
          <button type="button" class="btn ghost" :disabled="page <= 1" @click="page -= 1">قبلی</button>
          <span>صفحه {{ formatFaNumber(page) }} از {{ formatFaNumber(numPages) }} ({{ formatFaNumber(count) }})</span>
          <button type="button" class="btn ghost" :disabled="page >= numPages" @click="page += 1">بعدی</button>
        </div>
      </div>
    </div>

    <div v-if="canBulk && selectedIds.length" class="bulk-bar">
      <span>{{ formatFaNumber(selectedIds.length) }} مورد انتخاب شده</span>
      <button type="button" class="btn ghost" @click="selectedIds = []">پاک‌کردن انتخاب</button>
      <button type="button" class="btn ghost" @click="openBulk('activate')">فعال‌سازی گروهی</button>
      <button type="button" class="btn ghost" @click="openBulk('deactivate')">غیرفعال‌سازی گروهی</button>
      <button type="button" class="btn ghost" @click="openBulk('sms_expiry')">پیامک انقضا</button>
    </div>

    <Teleport to="body">
      <div
        v-if="activeMenuRow"
        class="hq-float-menu menu-pop actions-pop"
        data-hq-float-menu
        :style="rowMenuStyle"
      >
        <template v-for="group in groupedActions(activeMenuRow)" :key="group.key">
          <p class="group-label">{{ group.label }}</p>
          <button
            v-for="item in group.items"
            :key="item.action"
            type="button"
            @click="openAction(activeMenuRow, item.action)"
          >
            {{ item.label }}
          </button>
        </template>
        <button type="button" @click="openDetail(activeMenuRow); closeFloatingMenus()">مشاهده جزئیات</button>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="alertsOpen" class="hq-overlay overlay" @click.self="alertsOpen = false">
        <aside class="drawer">
          <header class="drawer-head">
            <h3>مرکز هشدارها</h3>
            <button type="button" class="btn ghost" @click="alertsOpen = false">بستن</button>
          </header>
          <div v-if="!alerts.length" class="drawer-body">
            <HqEmptyState title="هشدار فعالی وجود ندارد." description="" />
          </div>
          <div v-else class="drawer-body">
            <section v-for="(label, severity) in { critical: 'بحرانی', warning: 'هشدار', info: 'اطلاع' }" :key="severity">
              <template v-if="alertsGrouped[severity]?.length">
                <h4 :class="severity">{{ label }} ({{ formatFaNumber(alertsGrouped[severity].length) }})</h4>
                <article v-for="alert in alertsGrouped[severity]" :key="alert.id" class="alert-item">
                  <strong>{{ alert.title }}</strong>
                  <p>{{ alert.client_name }} — {{ alert.product_title }}</p>
                  <small>{{ alert.message }}</small>
                  <button type="button" class="btn link" @click="openAlertSubscription(alert)">مشاهده اشتراک</button>
                </article>
              </template>
            </section>
          </div>
        </aside>
      </div>

      <div v-if="detail" class="hq-overlay overlay" @click.self="detail = null">
        <aside class="drawer detail-drawer">
          <header class="drawer-head">
            <div v-if="detail.loading" class="sk-head" />
            <div v-else>
              <h3>{{ detail.subscription?.product_title }}</h3>
              <p>{{ detail.subscription?.client_name }}</p>
              <HqStatusBadge :value="detail.subscription?.status" />
              <small v-if="detail.subscription?.contract_number || detail.subscription?.license_code" class="muted">
                {{ detail.subscription?.contract_number || detail.subscription?.license_code }}
              </small>
            </div>
            <button type="button" class="btn ghost" @click="detail = null">بستن</button>
          </header>
          <div v-if="detailLoading" class="drawer-body"><div class="sk-row" /><div class="sk-row" /><div class="sk-row" /></div>
          <template v-else>
            <div class="summary-grid">
              <article><small>تاریخ خرید</small><strong>{{ formatJalaliDate(detail.subscription?.purchased_at) }}</strong></article>
              <article><small>فعال‌سازی</small><strong>{{ formatJalaliDate(detail.subscription?.activated_at) }}</strong></article>
              <article><small>شروع</small><strong>{{ formatJalaliDate(detail.subscription?.starts_at) }}</strong></article>
              <article><small>انقضا</small><strong>{{ detail.subscription?.ends_at ? formatJalaliDate(detail.subscription.ends_at) : '—' }}</strong></article>
              <article><small>پلن</small><strong>{{ detail.subscription?.feature_payment_plan_label || detail.subscription?.plan_title || '—' }}</strong></article>
              <article v-if="detail.subscription?.usage_cap != null">
                <small>مصرف</small>
                <div class="usage">
                  <div class="usage-bar"><i :style="{ width: `${Math.min(100, Number(detail.subscription?.usage_percent || 0))}%` }" /></div>
                  <span>{{ formatFaNumber(detail.subscription?.usage_used) }} از {{ formatFaNumber(detail.subscription?.usage_cap) }}</span>
                </div>
              </article>
            </div>
            <div v-if="seeFinancial" class="summary-grid financial">
              <article><small>مبلغ نهایی</small><strong>{{ formatMoney(detail.subscription?.final_amount) }}</strong></article>
              <article><small>پرداخت‌شده</small><strong>{{ formatMoney(detail.subscription?.paid_amount) }}</strong></article>
              <article><small>مانده</small><strong>{{ remainingLabel(detail.subscription?.remaining_amount) }}</strong></article>
              <article><small>وضعیت پرداخت</small><HqStatusBadge kind="payment" :value="detail.subscription?.payment_status" /></article>
            </div>
            <div class="drawer-tabs" role="tablist">
              <button type="button" role="tab" :class="{ active: detailTab === 'overview' }" @click="detailTab = 'overview'">نمای کلی</button>
              <button type="button" role="tab" :class="{ active: detailTab === 'periods' }" @click="detailTab = 'periods'">دوره‌ها</button>
              <button v-if="seeFinancial" type="button" role="tab" :class="{ active: detailTab === 'payments' }" @click="detailTab = 'payments'">پرداخت‌ها</button>
              <button type="button" role="tab" :class="{ active: detailTab === 'audit' }" @click="detailTab = 'audit'">تاریخچه</button>
            </div>
            <div class="drawer-body">
              <div v-if="detailTab === 'overview'">
                <p class="muted">{{ detail.subscription?.product_title }} — {{ detail.subscription?.client_name }}</p>
              </div>
              <ul v-else-if="detailTab === 'periods'" class="timeline">
                <li v-for="period in detail.periods || []" :key="period.id">
                  <strong>{{ period.kind }}</strong>
                  <span>{{ formatJalaliDate(period.starts_at) }} تا {{ period.ends_at ? formatJalaliDate(period.ends_at) : '—' }}</span>
                  <small v-if="seeFinancial">{{ formatMoney(period.final_amount) }}</small>
                </li>
                <li v-if="!(detail.periods || []).length"><HqEmptyState title="دوره‌ای ثبت نشده است." /></li>
              </ul>
              <ul v-else-if="detailTab === 'payments' && seeFinancial" class="timeline">
                <li v-for="payment in detail.payments || []" :key="payment.id">
                  <strong>{{ formatMoney(payment.amount) }}</strong>
                  <span>{{ payment.method || '—' }} — {{ formatJalaliDateTime(payment.paid_at) }}</span>
                </li>
                <li v-if="!(detail.payments || []).length"><HqEmptyState title="سابقه پرداختی وجود ندارد." /></li>
              </ul>
              <ul v-else class="timeline">
                <li v-for="log in detail.audit_logs || []" :key="log.id">
                  <strong>{{ log.action }}</strong>
                  <span>{{ log.actor_name || 'سیستم' }} — {{ log.reason || log.note || '—' }}</span>
                  <small>{{ formatJalaliDateTime(log.created_at) }}</small>
                </li>
                <li v-if="!(detail.audit_logs || []).length"><HqEmptyState title="تاریخچه‌ای ثبت نشده است." /></li>
              </ul>
            </div>
            <footer v-if="getValidActions(detail.subscription).length" class="drawer-foot">
              <button
                v-for="item in getValidActions(detail.subscription).slice(0, 3)"
                :key="item.action"
                type="button"
                class="btn ghost"
                @click="openAction(detail.subscription, item.action)"
              >
                {{ item.label }}
              </button>
            </footer>
          </template>
        </aside>
      </div>

      <div v-if="actionModal.open" class="hq-overlay overlay" @click.self="closeActionModal">
        <div class="modal" role="dialog" aria-modal="true">
          <header>
            <h3>{{ ACTION_META[actionModal.action]?.label }}</h3>
            <p>{{ actionModal.subscription?.client_name }} — {{ actionModal.subscription?.product_title }}</p>
          </header>
          <div class="modal-body">
            <p class="muted">وضعیت فعلی: <HqStatusBadge :value="actionModal.subscription?.status" /></p>
            <p v-if="ACTION_META[actionModal.action]?.warn" class="warn">{{ ACTION_META[actionModal.action].warn }}</p>
            <label v-if="ACTION_META[actionModal.action]?.needsDays">تعداد روز<input v-model.number="actionModal.days" type="number" min="1" class="ctrl wide" /></label>
            <label v-if="ACTION_META[actionModal.action]?.needsAmount">مبلغ (تومان)<input v-model="actionModal.amount" type="number" min="0" class="ctrl wide" /></label>
            <label v-if="ACTION_META[actionModal.action]?.needsPlan">پلن<select v-model="actionModal.plan_id" class="ctrl wide">
              <option v-for="plan in catalog.products.find(p => p.id === actionModal.subscription?.product)?.plans || []" :key="plan.id" :value="plan.id">{{ plan.title }}</option>
            </select></label>
            <label v-if="actionModal.action === 'register_payment'">کد پیگیری<input v-model="actionModal.tracking_code" type="text" class="ctrl wide" /></label>
            <label v-if="ACTION_META[actionModal.action]?.needsReason">دلیل *<input v-model="actionModal.reason" type="text" class="ctrl wide" required /></label>
            <label>یادداشت<textarea v-model="actionModal.note" rows="2" class="ctrl wide" /></label>
            <label v-if="ACTION_META[actionModal.action]?.needsConfirm" class="check">
              <input v-model="actionModal.confirmDebt" type="checkbox" /> تأیید بخشش بدهی
            </label>
            <p v-if="actionModal.fieldError" class="field-error">{{ actionModal.fieldError }}</p>
            <p v-if="actionModal.generalError" class="field-error">{{ actionModal.generalError }}</p>
          </div>
          <footer>
            <button type="button" class="btn ghost" :disabled="actionModal.loading" @click="closeActionModal">انصراف</button>
            <button
              type="button"
              class="btn"
              :class="ACTION_META[actionModal.action]?.tone || 'primary'"
              :disabled="actionModal.loading"
              @click="submitAction"
            >
              {{ actionModal.loading ? 'در حال اجرا…' : ACTION_META[actionModal.action]?.cta }}
            </button>
          </footer>
        </div>
      </div>

      <div v-if="bulkModal.open" class="hq-overlay overlay" @click.self="bulkModal.open = false">
        <div class="modal">
          <header><h3>عملیات گروهی</h3></header>
          <div class="modal-body">
            <p>{{ formatFaNumber(selectedIds.length) }} اشتراک انتخاب شده — {{ bulkModal.action }}</p>
            <label>دلیل<input v-model="bulkModal.reason" type="text" class="ctrl wide" /></label>
            <label>یادداشت<textarea v-model="bulkModal.note" rows="2" class="ctrl wide" /></label>
            <p v-if="bulkModal.error" class="field-error">{{ bulkModal.error }}</p>
          </div>
          <footer>
            <button type="button" class="btn ghost" :disabled="bulkModal.loading" @click="bulkModal.open = false">انصراف</button>
            <button type="button" class="btn primary" :disabled="bulkModal.loading" @click="submitBulk">{{ bulkModal.loading ? 'در حال اجرا…' : 'اجرای گروهی' }}</button>
          </footer>
        </div>
      </div>

      <div v-if="seedConfirm" class="hq-overlay overlay" @click.self="seedConfirm = false">
        <div class="modal">
          <header><h3>همگام‌سازی کاتالوگ</h3></header>
          <div class="modal-body"><p>کاتالوگ سرویس‌ها از منبع legacy همگام‌سازی شود؟</p></div>
          <footer>
            <button type="button" class="btn ghost" @click="seedConfirm = false">انصراف</button>
            <button type="button" class="btn primary" :disabled="seedLoading" @click="seedCatalog">{{ seedLoading ? 'در حال اجرا…' : 'تأیید همگام‌سازی' }}</button>
          </footer>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.hq-services {
  background: transparent;
  padding-bottom: 5.5rem;
}
.btn {
  border: 0;
  border-radius: 12px;
  height: 40px;
  padding: 0 1rem;
  cursor: pointer;
  font-weight: 700;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  transition: background 180ms ease, box-shadow 180ms ease, transform 160ms ease, opacity 160ms ease;
}
.btn:active:not(:disabled) { transform: translateY(1px); }
.btn.primary {
  background: linear-gradient(180deg, #2b86e0, #1976d2);
  color: #fff;
  box-shadow: 0 10px 22px rgba(25, 118, 210, 0.22);
}
.btn.primary:hover:not(:disabled) { background: linear-gradient(180deg, #1f7adb, #0f62b3); }
.btn.ghost {
  background: #e8f2fc;
  color: #0f62b3;
  border: 1px solid rgba(25, 118, 210, 0.12);
}
.btn.ghost:hover:not(:disabled) { background: #dcecfb; }
.btn.link { background: transparent; color: #1976d2; height: auto; padding: 0; border: 0; box-shadow: none; }
.btn.link:hover { color: #0f62b3; text-decoration: underline; }
.btn.danger { background: #dc2626; color: #fff; }
.btn.warning { background: #d97706; color: #fff; }
.btn.success { background: #4caf50; color: #fff; }
.btn.sm { height: 32px; padding: 0 0.7rem; font-size: 12px; border-radius: 10px; }
.btn.icon { width: 40px; padding: 0; }
.toast {
  background: #eaf8ed;
  color: #166534;
  border: 1px solid rgba(22, 101, 52, 0.12);
  border-radius: 12px;
  padding: 0.7rem 0.95rem;
  font-size: 13px;
  font-weight: 650;
}
.alert-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  background: linear-gradient(180deg, #ffffff, #f9fbfe);
  border: 1px solid rgba(25, 118, 210, 0.12);
  border-radius: 16px;
  padding: 0.85rem 1.05rem;
  flex-wrap: wrap;
  box-shadow: 0 10px 24px rgba(15, 37, 69, 0.03);
}
.alert-counts { display: flex; gap: 0.55rem; flex-wrap: wrap; }
.count {
  font-size: 12px;
  font-weight: 750;
  padding: 0.28rem 0.62rem;
  border-radius: 999px;
  border: 1px solid transparent;
}
.count.critical { background: #feeeee; color: #991b1b; border-color: rgba(153, 27, 27, 0.1); }
.count.warning { background: #fff6e8; color: #9a3412; border-color: rgba(154, 52, 18, 0.1); }
.count.info { background: #e8f5fe; color: #075985; border-color: rgba(7, 89, 133, 0.1); }
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.8rem;
}
.holding-card {
  background: linear-gradient(165deg, #ffffff, #f8fbff);
  border: 1px solid rgba(25, 118, 210, 0.12);
  border-radius: 16px;
  padding: 1.05rem;
  grid-column: span 2;
  box-shadow: 0 10px 24px rgba(15, 37, 69, 0.03);
}
.holding-card small { color: #647892; font-size: 12.5px; font-weight: 650; }
.holding-split { display: grid; grid-template-columns: 1fr 1fr; gap: 0.65rem; margin-top: 0.55rem; }
.split {
  border-radius: 12px;
  padding: 0.65rem 0.75rem;
  display: grid;
  gap: 0.22rem;
  border: 1px solid transparent;
}
.split.carno { background: #e8f2fc; color: #0f62b3; border-color: rgba(15, 98, 179, 0.12); }
.split.arakar { background: #f4ecff; color: #6d28d9; border-color: rgba(109, 40, 217, 0.12); }
.split strong { font-size: 1.12rem; font-variant-numeric: tabular-nums; font-weight: 800; }
.report-tabs {
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding: 0.15rem 0.1rem 0.35rem;
}
.report-tab {
  flex: 0 0 auto;
  scroll-snap-align: start;
  border: 1px solid rgba(25, 118, 210, 0.12);
  background: #f5f8fc;
  color: #0f2545;
  border-radius: 999px;
  height: 38px;
  padding: 0 0.95rem;
  cursor: pointer;
  font-size: 13px;
  font-weight: 650;
  transition: all 180ms ease;
}
.report-tab:hover { background: #fff; border-color: rgba(25, 118, 210, 0.24); }
.report-tab.active {
  background: #1976d2;
  border-color: #1976d2;
  color: #fff;
  box-shadow: 0 8px 18px rgba(25, 118, 210, 0.22);
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  align-items: center;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(25, 118, 210, 0.12);
  border-radius: 16px;
  padding: 0.85rem;
  box-shadow: 0 10px 24px rgba(15, 37, 69, 0.03);
}
.ctrl {
  border: 1px solid rgba(25, 118, 210, 0.14);
  border-radius: 12px;
  height: 40px;
  padding: 0 0.75rem;
  background: #fff;
  min-width: 140px;
  font-size: 13px;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}
.ctrl:focus {
  outline: none;
  border-color: #1976d2;
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.12);
}
.ctrl.wide { width: 100%; min-width: 0; }
.chips-row, .owned-chips, .missing-chips { display: flex; flex-wrap: wrap; gap: 0.45rem; }
.chip {
  border: 1px solid rgba(25, 118, 210, 0.14);
  background: #e8f2fc;
  color: #0f62b3;
  border-radius: 999px;
  height: 30px;
  padding: 0 0.7rem;
  font-size: 12px;
  cursor: pointer;
  font-weight: 650;
}
.chip.locked { cursor: default; background: #f1f5f9; color: #475569; border-color: #e2e8f0; }
.client-card, .panel {
  background: #fff;
  border: 1px solid rgba(25, 118, 210, 0.12);
  border-radius: 16px;
  padding: 1rem;
  box-shadow: 0 10px 24px rgba(15, 37, 69, 0.03);
}
.client-card header { display: flex; justify-content: space-between; gap: 0.75rem; align-items: flex-start; }
.client-card h3 { margin: 0; color: #0c3d78; font-size: 1.1rem; font-weight: 800; }
.client-card p { margin: 0.28rem 0 0; color: #6b7c93; font-size: 13px; line-height: 1.6; }
.owned-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid rgba(25, 118, 210, 0.12);
  background: #f7faff;
  border-radius: 999px;
  height: 32px;
  padding: 0 0.7rem;
  cursor: pointer;
  font-size: 12px;
  transition: background 160ms ease;
}
.owned-chip:hover { background: #eef6ff; }
.missing-chip {
  background: #f8fafc;
  color: #647892;
  border: 1px dashed #d8e3f5;
  border-radius: 999px;
  padding: 0.28rem 0.65rem;
  font-size: 12px;
}
.revenue-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.65rem; margin-bottom: 0.85rem; }
.seg {
  display: inline-flex;
  border: 1px solid rgba(25, 118, 210, 0.14);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 0.85rem;
  background: #fff;
}
.seg button {
  border: 0;
  background: transparent;
  padding: 0.5rem 0.85rem;
  cursor: pointer;
  font-size: 12.5px;
  font-weight: 650;
  color: #5b6b82;
}
.seg button.active { background: #1976d2; color: #fff; }
.table-wrap { overflow: auto; border-radius: 12px; }
table { width: 100%; border-collapse: collapse; min-width: 980px; }
th, td {
  text-align: right;
  padding: 0.82rem 0.6rem;
  border-bottom: 1px solid #eef2f7;
  font-size: 13px;
  vertical-align: middle;
}
th {
  font-size: 11.5px;
  font-weight: 750;
  color: #647892;
  background: linear-gradient(180deg, #f8fbff, #f3f7fc);
  position: sticky;
  top: 0;
  z-index: 1;
}
tbody tr { transition: background 160ms ease; }
tbody tr:hover { background: rgba(232, 242, 252, 0.55); }
.money { white-space: nowrap; font-variant-numeric: tabular-nums; font-weight: 650; }
.money.settled { color: #166534; font-weight: 750; }
.data-row { cursor: pointer; position: relative; }
.data-row::before {
  content: '';
  position: absolute;
  inset-inline-start: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--accent, transparent);
  border-radius: 0 2px 2px 0;
}
.service-cell { display: grid; gap: 0.28rem; }
.ends-cell { display: grid; gap: 0.12rem; }
.ends-cell small { color: #6b7c93; font-size: 11.5px; }
.sticky-start { position: sticky; inset-inline-start: 0; background: #fff; z-index: 2; }
.sticky-start.second { inset-inline-start: 42px; }
.sticky-end { position: sticky; inset-inline-end: 0; background: #fff; z-index: 2; }
.ops { white-space: nowrap; }
.pager {
  display: flex;
  gap: 0.55rem;
  align-items: center;
  justify-content: center;
  padding-top: 0.9rem;
  font-size: 13px;
  color: #5b6b82;
}
.dim { opacity: 0.72; pointer-events: none; }
.bulk-bar {
  position: sticky;
  bottom: 0.85rem;
  z-index: 5;
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  align-items: center;
  background: linear-gradient(180deg, #134a8c, #0c3d78);
  color: #fff;
  border-radius: 16px;
  padding: 0.85rem 1rem;
  box-shadow: 0 14px 32px rgba(12, 61, 120, 0.28);
}
.bulk-bar .btn.ghost { color: #0f2545; background: #fff; }
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(12, 28, 52, 0.38);
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: flex-start;
  z-index: 240;
}
.drawer, .modal {
  background: #fff;
  height: 100%;
  overflow: auto;
  display: flex;
  flex-direction: column;
}
.drawer { width: min(580px, 100%); box-shadow: 12px 0 36px rgba(15, 37, 69, 0.16); }
.modal {
  width: min(480px, calc(100% - 2rem));
  height: auto;
  max-height: calc(100% - 2rem);
  margin: auto;
  border-radius: 18px;
  box-shadow: 0 20px 48px rgba(15, 37, 69, 0.2);
}
.drawer-head, .modal header, .modal footer, .drawer-foot {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 1.05rem 1.1rem;
  border-bottom: 1px solid rgba(25, 118, 210, 0.1);
  background: rgba(255,255,255,0.96);
}
.drawer-foot, .modal footer { border-bottom: 0; border-top: 1px solid rgba(25, 118, 210, 0.1); margin-top: auto; }
.drawer-body, .modal-body { padding: 1.05rem 1.1rem; display: grid; gap: 0.8rem; }
.drawer-head h3, .modal h3 { margin: 0; color: #0c3d78; font-weight: 800; }
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.6rem;
  padding: 0 1.1rem;
}
.summary-grid article {
  background: #f7faff;
  border: 1px solid rgba(25, 118, 210, 0.08);
  border-radius: 12px;
  padding: 0.7rem;
  display: grid;
  gap: 0.22rem;
}
.summary-grid small { color: #647892; font-size: 12px; }
.summary-grid strong { color: #0f2545; font-size: 13px; font-weight: 750; }
.usage-bar { height: 7px; background: #e8eef8; border-radius: 999px; overflow: hidden; }
.usage-bar i { display: block; height: 100%; background: linear-gradient(90deg, #4ea1ea, #1976d2); }
.drawer-tabs { display: flex; gap: 0.4rem; padding: 0 1.1rem; flex-wrap: wrap; }
.drawer-tabs button {
  border: 1px solid rgba(25, 118, 210, 0.14);
  background: #fff;
  border-radius: 999px;
  height: 32px;
  padding: 0 0.8rem;
  cursor: pointer;
  font-size: 12px;
  font-weight: 650;
  color: #5b6b82;
}
.drawer-tabs button.active { background: #1976d2; color: #fff; border-color: #1976d2; }
.timeline { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.65rem; }
.timeline li {
  background: #f7faff;
  border: 1px solid rgba(25, 118, 210, 0.08);
  border-radius: 12px;
  padding: 0.7rem;
  display: grid;
  gap: 0.18rem;
}
.alert-item {
  border: 1px solid rgba(25, 118, 210, 0.1);
  border-radius: 12px;
  padding: 0.8rem;
  display: grid;
  gap: 0.28rem;
  margin-bottom: 0.55rem;
  background: #fff;
}
.alert-item h4, .drawer-body h4 { margin: 0.75rem 0 0.35rem; font-size: 13px; }
.alert-item h4.critical, h4.critical { color: #991b1b; }
.alert-item h4.warning, h4.warning { color: #9a3412; }
.menu-wrap { position: relative; }
.menu-pop {
  position: absolute;
  inset-inline-start: 0;
  top: calc(100% + 0.35rem);
  min-width: 190px;
  background: #fff;
  border: 1px solid rgba(25, 118, 210, 0.14);
  border-radius: 12px;
  box-shadow: 0 14px 28px rgba(15, 37, 69, 0.12);
  z-index: 241;
  padding: 0.4rem;
  display: grid;
}
.hq-float-menu.menu-pop {
  position: fixed;
  inset-inline-start: auto;
  top: 0;
  overflow: auto;
  overscroll-behavior: contain;
}
.menu-pop button, .filters-pop label {
  text-align: right;
  border: 0;
  background: transparent;
  padding: 0.5rem 0.6rem;
  cursor: pointer;
  font-size: 13px;
  border-radius: 9px;
}
.menu-pop button:hover { background: #f5f8fc; }
.filters-pop { min-width: 270px; padding: 0.75rem; gap: 0.55rem; }
.actions-pop .group-label { margin: 0.25rem 0.15rem 0; font-size: 11px; color: #647892; font-weight: 750; }
.check { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 13px; }
.field-error, .warn { color: #991b1b; font-size: 12px; margin: 0; }
.muted { color: #6b7c93; font-size: 12.5px; }
.error-box { padding: 1.6rem; text-align: center; display: grid; gap: 0.65rem; place-items: center; }
.skeleton-table { display: grid; gap: 0.45rem; }
.sk-row, .sk-head {
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(90deg, #eef2f7 25%, #f8fafc 50%, #eef2f7 75%);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;
}
.sk-head { height: 64px; margin: 1rem; }
@keyframes shimmer { to { background-position: -200% 0; } }
@media (max-width: 768px) {
  .holding-card { grid-column: span 1; }
  .overlay { justify-content: stretch; }
  .drawer { width: 100%; }
  .modal { width: calc(100% - 1rem); max-height: 100%; margin: 0.5rem auto; }
}
@media (prefers-reduced-motion: reduce) {
  .btn, .report-tab, .chip, .owned-chip, tbody tr { transition: none; }
  .sk-row, .sk-head { animation: none; }
}
</style>
