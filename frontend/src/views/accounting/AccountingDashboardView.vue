<template>
  <div class="dashboard-page" dir="rtl">
    <header class="topbar">
      <div class="topbar-left">
        <span class="brand">CarWash</span>
        <div class="search-box">
          <input ref="searchInputRef" v-model="filters.search" type="text" placeholder="جستجو (F7)" @keydown.f7.prevent="focusSearch" />
        </div>
      </div>
      <div class="topbar-right">
        <div class="profile"><p class="profile-name">حسابدار</p></div>
      </div>
    </header>

    <div class="layout">
      <aside class="sidebar">
        <nav>
          <RouterLink class="menu-item" :class="{ active: currentTab === 'inventory' }" to="/accounting?tab=inventory">انبار</RouterLink>
          <RouterLink class="menu-item" :class="{ active: currentTab === 'purchases' }" to="/accounting?tab=purchases">خرید</RouterLink>
          <RouterLink class="menu-item" :class="{ active: currentTab === 'sales' }" to="/accounting?tab=sales">فروش</RouterLink>
          <RouterLink class="menu-item" :class="{ active: currentTab === 'vouchers' }" to="/accounting?tab=vouchers">سند حسابداری</RouterLink>
        </nav>
      </aside>

      <main class="content">
        

        <section class="tabs-bar">
          <button v-for="tab in tabs" :key="tab.key" class="chip" :class="{ active: currentTab === tab.key }" @click="setTab(tab.key)">
            {{ tab.label }}
          </button>
          <section class="content-head">
          <button class="primary-btn add-main-btn" @click="openCreateModal">افزودن جدید</button>
        </section>
        </section>

        <section class="card">
          
          <div class="toolbar-grid">
            <select v-if="currentTab === 'inventory'" v-model="filters.category" class="field">
              <option value="">همه گروه‌ها</option>
              <option v-for="category in bootstrap.categories" :key="category" :value="category">{{ category }}</option>
            </select>
            
            <select v-if="currentTab === 'inventory'" v-model="filters.lowStock" class="field">
              <option value="">همه وضعیت‌ها</option>
              <option value="1">کم‌تر از حد سفارش</option>
            </select>
            <select v-if="currentTab === 'purchases'" v-model="filters.status" class="field">
              <option value="">همه وضعیت‌ها</option>
              <option value="draft">پیش‌نویس</option>
              <option value="confirmed">تأیید شده</option>
              <option value="cancelled">لغو شده</option>
            </select>
            <select v-if="currentTab === 'sales'" v-model="filters.settlementType" class="field">
              <option value="">همه نوع تسویه</option>
              <option value="cash">نقد</option>
              <option value="card">کارتخوان</option>
              <option value="credit">نسیه</option>
            </select>
            <select v-if="currentTab === 'vouchers'" v-model="filters.referenceType" class="field">
              <option value="">همه مراجع</option>
              <option value="manual">دستی</option>
              <option value="purchase_invoice">خرید</option>
              <option value="sales_invoice">فروش</option>
            </select>
          </div>
        </section>

        <section class="card">
        <div v-if="state.loading" class="state-box">در حال بارگذاری...</div>
        <div v-else-if="state.error" class="state-box error">{{ state.error }}</div>
        <div v-else-if="!activeRows.length" class="state-box">موردی ثبت نشده است.</div>

        <template v-else>
          <table class="data-table">
            <thead>
              <tr v-if="currentTab === 'inventory'">
                <th>ردیف</th><th>کد</th><th>نام</th><th>گروه</th><th>واحد</th><th>خرید</th><th>فروش</th><th>موجودی</th><th>حد سفارش</th><th>وضعیت</th><th>عملیات</th>
              </tr>
              <tr v-else-if="currentTab === 'purchases'">
                <th>شماره فاکتور</th><th>تاریخ</th><th>تأمین‌کننده</th><th>مبلغ کل</th><th>پرداختی</th><th>مانده</th><th>وضعیت</th><th>شرح</th><th>عملیات</th>
              </tr>
              <tr v-else-if="currentTab === 'sales'">
                <th>شماره فاکتور</th><th>تاریخ</th><th>مشتری</th><th>مبلغ کل</th><th>نوع تسویه</th><th>پرداختی</th><th>مانده</th><th>وضعیت</th><th>عملیات</th>
              </tr>
              <tr v-else>
                <th>شماره سند</th><th>تاریخ</th><th>شرح</th><th>نوع مرجع</th><th>شماره مرجع</th><th>وضعیت</th><th>جمع بدهکار</th><th>جمع بستانکار</th><th>عملیات</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in activeRows" :key="row.id">
                <template v-if="currentTab === 'inventory'">
                  <td>{{ rowNumber(index) }}</td>
                  <td>{{ row.code }}</td>
                  <td>{{ row.name }}</td>
                  <td>{{ row.category || '-' }}</td>
                  <td>{{ row.unit }}</td>
                  <td>{{ money(row.buy_price) }}</td>
                  <td>{{ money(row.sell_price) }}</td>
                  <td>{{ decimal(row.quantity) }}</td>
                  <td>{{ decimal(row.min_quantity) }}</td>
                  <td><span :class="['badge', row.low_stock ? 'warning' : 'success']">{{ row.low_stock ? 'کمبود' : 'موجود' }}</span></td>
                </template>
                <template v-else-if="currentTab === 'purchases'">
                  <td>{{ row.invoice_no }}</td>
                  <td>{{ row.invoice_date }}</td>
                  <td>{{ row.supplier_name || '-' }}</td>
                  <td>{{ money(row.grand_total) }}</td>
                  <td>{{ money(row.paid_amount) }}</td>
                  <td>{{ money(row.remaining_amount) }}</td>
                  <td><span class="badge">{{ statusLabel(row.status) }}</span></td>
                  <td>{{ row.description || '-' }}</td>
                </template>
                <template v-else-if="currentTab === 'sales'">
                  <td>{{ row.invoice_no }}</td>
                  <td>{{ row.invoice_date }}</td>
                  <td>{{ row.customer_name || '-' }}</td>
                  <td>{{ money(row.grand_total) }}</td>
                  <td>{{ settlementLabel(row.settlement_type) }}</td>
                  <td>{{ money(row.paid_amount) }}</td>
                  <td>{{ money(row.remaining_amount) }}</td>
                  <td><span class="badge">{{ statusLabel(row.status) }}</span></td>
                </template>
                <template v-else>
                  <td>{{ row.voucher_no }}</td>
                  <td>{{ row.date }}</td>
                  <td>{{ row.description || '-' }}</td>
                  <td>{{ referenceLabel(row.reference_type) }}</td>
                  <td>{{ row.reference_id || '-' }}</td>
                  <td><span class="badge">{{ voucherStatusLabel(row.status) }}</span></td>
                  <td>{{ money(row.total_debit) }}</td>
                  <td>{{ money(row.total_credit) }}</td>
                </template>
                <td class="actions">
                  <button class="icon-btn" @click="openViewModal(row)">مشاهده</button>
                  <button class="icon-btn" @click="openEditModal(row)">ویرایش</button>
                  <button
                    v-if="currentTab !== 'vouchers' && row.status === 'draft'"
                    class="icon-btn accent"
                    @click="confirmRow(row)"
                  >
                    تأیید
                  </button>
                  <button class="icon-btn danger" @click="deleteRow(row)">حذف</button>
                </td>
              </tr>
            </tbody>
          </table>

          <div class="pagination">
            <button class="page-btn" :disabled="state.page <= 1" @click="changePage(state.page - 1)">قبلی</button>
            <span>صفحه {{ state.page }} از {{ totalPages }}</span>
            <button class="page-btn" :disabled="state.page >= totalPages" @click="changePage(state.page + 1)">بعدی</button>
          </div>
        </template>
      </section>
      </main>
    </div>

    <div v-if="modal.open" class="modal-backdrop" @click.self="closeModal">
      <section class="modal-panel">
        <header class="modal-head">
          <div>
            <p>{{ modalModeLabel }}</p>
            <h3>{{ modalTitle }}</h3>
          </div>
          <button class="close-btn" @click="closeModal">×</button>
        </header>

        <div v-if="modal.mode === 'view'" class="details-panel">
          <pre>{{ JSON.stringify(modal.data, null, 2) }}</pre>
        </div>

        <form v-else class="modal-body" @submit.prevent="submitModal">
          <template v-if="currentTab === 'inventory'">
            <div class="grid cols-2">
              <input v-model="inventoryForm.code" class="field" placeholder="کد کالا" required />
              <input v-model="inventoryForm.name" class="field" placeholder="نام کالا" required />
              <input v-model="inventoryForm.category" class="field" placeholder="گروه کالا" />
              <input v-model="inventoryForm.unit" class="field" placeholder="واحد" required />
              <input v-model.number="inventoryForm.buy_price" class="field" type="number" min="0" placeholder="آخرین قیمت خرید" required />
              <input v-model.number="inventoryForm.sell_price" class="field" type="number" min="0" placeholder="قیمت فروش" required />
              <input v-model.number="inventoryForm.quantity" class="field" type="number" min="0" placeholder="موجودی اولیه" required />
              <input v-model.number="inventoryForm.min_quantity" class="field" type="number" min="0" placeholder="حداقل موجودی" required />
            </div>
          </template>

          <template v-else-if="currentTab === 'purchases' || currentTab === 'sales'">
            <div class="grid cols-2">
              <input v-model="invoiceForm.factor_no" class="field" placeholder="شماره فاکتور" required />
              <input v-model="invoiceForm.date_jalali" class="field" placeholder="تاریخ شمسی 1405/01/01" required />
              <select v-if="currentTab === 'purchases'" v-model.number="invoiceForm.party_id" class="field" required>
                <option :value="null">تأمین‌کننده</option>
                <option v-for="party in supplierOptions" :key="party.id" :value="party.id">{{ party.name }}</option>
              </select>
              <select v-else v-model.number="invoiceForm.party_id" class="field" required>
                <option :value="null">مشتری</option>
                <option v-for="party in customerOptions" :key="party.id" :value="party.id">{{ party.name }}</option>
              </select>
              <select v-if="currentTab === 'purchases'" v-model="invoiceForm.payment_type" class="field">
                <option value="cash">نقدی</option>
                <option value="bank">بانکی</option>
                <option value="mixed">ترکیبی</option>
                <option value="credit">نسیه</option>
              </select>
              <select v-else v-model="invoiceForm.settlement_type" class="field">
                <option value="cash">نقد</option>
                <option value="card">کارتخوان</option>
                <option value="credit">نسیه</option>
              </select>
              <input v-model.number="invoiceForm.paid_amount" class="field" type="number" min="0" placeholder="مبلغ پرداختی" />
              <textarea v-model="invoiceForm.description" class="field textarea" placeholder="شرح"></textarea>
            </div>

            <div class="line-card">
              <div class="line-head">
                <strong>ردیف‌ها</strong>
                <button type="button" class="icon-btn" @click="addInvoiceLine">افزودن ردیف</button>
              </div>
              <div class="line-grid-head">
                <span>کالا</span>
                <span>واحد</span>
                <span>موجودی فعلی</span>
                <span>تعداد/مقدار</span>
                <span>قیمت واحد</span>
                <span>تخفیف</span>
                <span>مالیات</span>
                <span>مبلغ کل ردیف</span>
                <span>عملیات</span>
              </div>
              <div v-for="(line, index) in invoiceForm.items" :key="index" class="line-row">
                <select v-model.number="line.item_id" class="field" @change="syncLineProduct(index)">
                  <option :value="null">انتخاب کالا</option>
                  <option v-for="item in inventoryOptions" :key="item.id" :value="item.id">{{ item.name }}</option>
                </select>
                <input :value="line.unit" class="field" placeholder="واحد" readonly />
                <input :value="line.stock" class="field" placeholder="موجودی فعلی" readonly />
                <input v-model.number="line.quantity" class="field" type="number" min="0" placeholder="تعداد" />
                <input v-model.number="line.unit_price" class="field" type="number" min="0" placeholder="قیمت واحد" />
                <input v-model.number="line.discount" class="field" type="number" min="0" placeholder="تخفیف" />
                <input v-model.number="line.tax" class="field" type="number" min="0" placeholder="مالیات" />
                <input :value="money(lineTotal(line))" class="field" placeholder="مبلغ کل" readonly />
                <button type="button" class="icon-btn danger" @click="removeInvoiceLine(index)">حذف</button>
              </div>
              <div class="totals-box">
                <span>جمع کل: {{ money(invoiceGrandTotal) }}</span>
                <span>مانده: {{ money(Math.max(0, invoiceGrandTotal - Number(invoiceForm.paid_amount || 0))) }}</span>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="grid cols-2">
              <input v-model="voucherForm.voucher_no" class="field" placeholder="شماره سند" />
              <input v-model="voucherForm.date_jalali" class="field" placeholder="تاریخ شمسی 1405/01/01" required />
              <select v-model="voucherForm.status" class="field">
                <option value="draft">پیش‌نویس</option>
                <option value="posted">ثبت نهایی</option>
              </select>
              <textarea v-model="voucherForm.description" class="field textarea full" placeholder="شرح سند"></textarea>
            </div>
            <div class="line-card">
              <div class="line-head">
                <strong>ردیف‌های سند</strong>
                <button type="button" class="icon-btn" @click="addVoucherLine">افزودن ردیف</button>
              </div>
              <div class="voucher-grid-head">
                <span>حساب</span>
                <span>شرح ردیف</span>
                <span>بدهکار</span>
                <span>بستانکار</span>
                <span>عملیات</span>
              </div>
              <div v-for="(line, index) in voucherForm.voucher_entries" :key="index" class="line-row voucher">
                <select v-model.number="line.account_id" class="field">
                  <option :value="null">انتخاب حساب</option>
                  <option v-for="account in bootstrap.accounts" :key="account.id" :value="account.id">{{ account.code }} - {{ account.name }}</option>
                </select>
                <input v-model="line.row_description" class="field" placeholder="شرح ردیف" />
                <input v-model.number="line.debit" class="field" type="number" min="0" placeholder="بدهکار" />
                <input v-model.number="line.credit" class="field" type="number" min="0" placeholder="بستانکار" />
                <button type="button" class="icon-btn danger" @click="removeVoucherLine(index)">حذف</button>
              </div>
              <div class="totals-box">
                <span>جمع بدهکار: {{ money(voucherDebitTotal) }}</span>
                <span>جمع بستانکار: {{ money(voucherCreditTotal) }}</span>
              </div>
            </div>
          </template>

          <footer class="modal-actions">
            <button type="button" class="icon-btn" @click="closeModal">انصراف</button>
            <button type="submit" class="primary-btn">ذخیره</button>
          </footer>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RouterLink } from 'vue-router'
import api from '../../services/api'

const route = useRoute()
const router = useRouter()
const searchInputRef = ref(null)

const tabs = [
  { key: 'inventory', label: 'انبار' },
  { key: 'purchases', label: 'خرید' },
  { key: 'sales', label: 'فروش' },
  { key: 'vouchers', label: 'سند حسابداری' }
]

const currentTab = ref(route.query.tab || 'inventory')
const state = reactive({
  loading: false,
  error: '',
  page: 1,
  pageSize: 20,
  total: 0,
  inventory: [],
  purchases: [],
  sales: [],
  vouchers: []
})
const bootstrap = reactive({ categories: [], parties: [], accounts: [] })
const filters = reactive({ search: '', category: '', lowStock: '', status: '', settlementType: '', referenceType: '' })
const modal = reactive({ open: false, mode: 'create', data: null })

const inventoryForm = reactive({ code: '', name: '', category: '', unit: 'عدد', buy_price: 0, sell_price: 0, quantity: 0, min_quantity: 0 })
const invoiceForm = reactive({ id: null, factor_no: '', date_jalali: '', party_id: null, description: '', payment_type: 'cash', settlement_type: 'cash', paid_amount: 0, items: [] })
const voucherForm = reactive({ id: null, voucher_no: '', date_jalali: '', status: 'draft', description: '', voucher_entries: [] })

const supplierOptions = computed(() => bootstrap.parties.filter((item) => ['supplier', 'both'].includes(item.party_type)))
const customerOptions = computed(() => bootstrap.parties.filter((item) => ['customer', 'both'].includes(item.party_type)))
const inventoryOptions = computed(() => state.inventory)
const activeRows = computed(() => state[currentTab.value] || [])
const totalPages = computed(() => Math.max(1, Math.ceil(state.total / state.pageSize)))
const modalTitle = computed(() => ({
  inventory: 'کالا',
  purchases: 'فاکتور خرید',
  sales: 'فاکتور فروش',
  vouchers: 'سند حسابداری'
}[currentTab.value]))
const modalModeLabel = computed(() => modal.mode === 'create' ? 'ثبت جدید' : modal.mode === 'edit' ? 'ویرایش' : 'جزئیات')

const invoiceGrandTotal = computed(() => invoiceForm.items.reduce((sum, item) => sum + lineTotal(item), 0))
const voucherDebitTotal = computed(() => voucherForm.voucher_entries.reduce((sum, item) => sum + Number(item.debit || 0), 0))
const voucherCreditTotal = computed(() => voucherForm.voucher_entries.reduce((sum, item) => sum + Number(item.credit || 0), 0))

const setTab = async (tab) => {
  currentTab.value = tab
  state.page = 1
  await router.replace({ query: { ...route.query, tab } })
  await refreshActive()
}

const money = (value) => Number(value || 0).toLocaleString('fa-IR')
const decimal = (value) => Number(value || 0).toLocaleString('fa-IR')
const statusLabel = (value) => ({ draft: 'پیش‌نویس', confirmed: 'تأیید شده', cancelled: 'لغو شده' }[value] || '-')
const settlementLabel = (value) => ({ cash: 'نقد', card: 'کارتخوان', credit: 'نسیه' }[value] || '-')
const voucherStatusLabel = (value) => ({ draft: 'پیش‌نویس', posted: 'ثبت شده', cancelled: 'لغو شده' }[value] || '-')
const referenceLabel = (value) => ({ manual: 'دستی', purchase_invoice: 'خرید', sales_invoice: 'فروش' }[value] || '-')
const rowNumber = (index) => ((state.page - 1) * state.pageSize) + index + 1
const focusSearch = () => searchInputRef.value?.focus()
const lineTotal = (line) => Math.max(0, ((Number(line.quantity || 0) * Number(line.unit_price || 0)) - Number(line.discount || 0) + Number(line.tax || 0)))

const emptyInvoiceLine = () => ({ item_id: null, unit: '', stock: 0, quantity: 0, unit_price: 0, discount: 0, tax: 0, description: '' })
const emptyVoucherLine = () => ({ account_id: null, debit: 0, credit: 0, row_description: '' })

const parseJalaliToIso = (input) => {
  const value = (input || '').trim().replace(/-/g, '/')
  const match = value.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/)
  if (!match) return ''
  const jy = Number(match[1]) - 979
  const jm = Number(match[2]) - 1
  const jd = Number(match[3]) - 1
  const jDaysInMonth = [31,31,31,31,31,31,30,30,30,30,30,29]
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

const gregorianToJalali = (isoDate) => {
  if (!isoDate) return ''
  const [gyRaw, gmRaw, gdRaw] = isoDate.split('-')
  const gy = Number(gyRaw) - 1600
  const gm = Number(gmRaw) - 1
  const gd = Number(gdRaw) - 1
  const gDaysInMonth = [31,28,31,30,31,30,31,31,30,31,30,31]
  let gDayNo = 365 * gy + Math.floor((gy + 3) / 4) - Math.floor((gy + 99) / 100) + Math.floor((gy + 399) / 400)
  for (let i = 0; i < gm; i += 1) gDayNo += gDaysInMonth[i]
  if (gm > 1 && ((gy + 1600) % 4 === 0 && ((gy + 1600) % 100 !== 0 || (gy + 1600) % 400 === 0))) gDayNo += 1
  gDayNo += gd
  let jDayNo = gDayNo - 79
  const jNp = Math.floor(jDayNo / 12053)
  jDayNo %= 12053
  let jy = 979 + 33 * jNp + 4 * Math.floor(jDayNo / 1461)
  jDayNo %= 1461
  if (jDayNo >= 366) {
    jy += Math.floor((jDayNo - 1) / 365)
    jDayNo = (jDayNo - 1) % 365
  }
  const jDaysInMonth = [31,31,31,31,31,31,30,30,30,30,30,29]
  let jm = 0
  while (jm < 11 && jDayNo >= jDaysInMonth[jm]) {
    jDayNo -= jDaysInMonth[jm]
    jm += 1
  }
  const jd = jDayNo + 1
  return `${jy}/${String(jm + 1).padStart(2, '0')}/${String(jd).padStart(2, '0')}`
}

const resetForms = () => {
  Object.assign(inventoryForm, { code: '', name: '', category: '', unit: 'عدد', buy_price: 0, sell_price: 0, quantity: 0, min_quantity: 0 })
  Object.assign(invoiceForm, { id: null, factor_no: '', date_jalali: '', party_id: null, description: '', payment_type: 'cash', settlement_type: 'cash', paid_amount: 0, items: [emptyInvoiceLine()] })
  Object.assign(voucherForm, { id: null, voucher_no: '', date_jalali: '', status: 'draft', description: '', voucher_entries: [emptyVoucherLine()] })
}

const openCreateModal = () => {
  modal.open = true
  modal.mode = 'create'
  modal.data = null
  resetForms()
}

const openViewModal = (row) => {
  modal.open = true
  modal.mode = 'view'
  modal.data = row
}

const openEditModal = (row) => {
  modal.open = true
  modal.mode = 'edit'
  modal.data = row
  resetForms()
  if (currentTab.value === 'inventory') {
    Object.assign(inventoryForm, {
      code: row.code,
      name: row.name,
      category: row.category || '',
      unit: row.unit,
      buy_price: row.buy_price,
      sell_price: row.sell_price,
      quantity: row.quantity,
      min_quantity: row.min_quantity
    })
  } else if (currentTab.value === 'purchases' || currentTab.value === 'sales') {
    Object.assign(invoiceForm, {
      id: row.id,
      factor_no: row.invoice_no,
      date_jalali: gregorianToJalali(row.invoice_date),
      party_id: currentTab.value === 'purchases' ? row.supplier : row.customer,
      description: row.description || '',
      payment_type: row.payment_type || 'cash',
      settlement_type: row.settlement_type || 'cash',
      paid_amount: row.paid_amount || 0,
      items: (row.items || []).map((item) => ({
        item_id: item.item_id,
        unit: item.unit,
        stock: item.current_quantity,
        quantity: item.quantity,
        unit_price: item.unit_price,
        discount: item.discount,
        tax: item.tax,
        description: item.description || ''
      }))
    })
  } else {
      Object.assign(voucherForm, {
        id: row.id,
        voucher_no: row.voucher_no,
        date_jalali: gregorianToJalali(row.date),
        status: row.status || 'draft',
        description: row.description || '',
        voucher_entries: (row.voucher_entries || []).map((item) => ({
        account_id: item.account,
        debit: item.debit,
        credit: item.credit,
        row_description: item.row_description || ''
      }))
    })
  }
}

const closeModal = () => {
  modal.open = false
  modal.data = null
}

const addInvoiceLine = () => invoiceForm.items.push(emptyInvoiceLine())
const removeInvoiceLine = (index) => { if (invoiceForm.items.length > 1) invoiceForm.items.splice(index, 1) }
const addVoucherLine = () => voucherForm.voucher_entries.push(emptyVoucherLine())
const removeVoucherLine = (index) => { if (voucherForm.voucher_entries.length > 1) voucherForm.voucher_entries.splice(index, 1) }

const syncLineProduct = (index) => {
  const selected = state.inventory.find((item) => item.id === invoiceForm.items[index].item_id)
  if (!selected) return
  invoiceForm.items[index].unit = selected.unit
  invoiceForm.items[index].stock = selected.quantity
  invoiceForm.items[index].unit_price = currentTab.value === 'purchases' ? Number(selected.buy_price || 0) : Number(selected.sell_price || 0)
}

const loadBootstrap = async () => {
  const [{ data }, inventoryResponse] = await Promise.all([
    api.get('/accounting/bootstrap/'),
    api.get('/accounting/inventory/', { params: { page: 1, page_size: 200 } })
  ])
  bootstrap.categories = data.categories || []
  bootstrap.parties = data.parties || []
  bootstrap.accounts = data.accounts || []
  state.inventory = inventoryResponse.data.results || []
}

const refreshActive = async () => {
  state.loading = true
  state.error = ''
  try {
    const params = { page: state.page, page_size: state.pageSize, search: filters.search || undefined }
    let endpoint = '/accounting/inventory/'
    if (currentTab.value === 'inventory') {
      params.category = filters.category || undefined
      params.low_stock = filters.lowStock || undefined
    } else if (currentTab.value === 'purchases') {
      endpoint = '/accounting/purchases/'
      params.status = filters.status || undefined
    } else if (currentTab.value === 'sales') {
      endpoint = '/accounting/sales/'
      params.settlement_type = filters.settlementType || undefined
    } else {
      endpoint = '/accounting/vouchers/'
      params.reference_type = filters.referenceType || undefined
    }
    const { data } = await api.get(endpoint, { params })
    state[currentTab.value] = data.results || []
    state.page = data.page || 1
    state.pageSize = data.page_size || 20
    state.total = data.total || 0
  } catch (error) {
    state.error = error?.response?.data?.detail || 'بارگذاری اطلاعات ناموفق بود.'
  } finally {
    state.loading = false
  }
}

const changePage = async (page) => {
  state.page = page
  await refreshActive()
}

const submitModal = async () => {
  try {
    if (currentTab.value === 'inventory') {
      const payload = { ...inventoryForm }
      if (modal.mode === 'edit') await api.put(`/accounting/inventory/${modal.data.id}/`, payload)
      else await api.post('/accounting/inventory/', payload)
    } else if (currentTab.value === 'purchases' || currentTab.value === 'sales') {
      const payload = {
        factor_no: invoiceForm.factor_no,
        date: parseJalaliToIso(invoiceForm.date_jalali),
        description: invoiceForm.description,
        paid_amount: Number(invoiceForm.paid_amount || 0),
        items: invoiceForm.items.map((item) => ({
          item_id: item.item_id,
          quantity: Number(item.quantity || 0),
          unit_price: Number(item.unit_price || 0),
          discount: Number(item.discount || 0),
          tax: Number(item.tax || 0),
          description: item.description || ''
        }))
      }
      if (currentTab.value === 'purchases') {
        payload.supplier_id = invoiceForm.party_id
        payload.payment_type = invoiceForm.payment_type
        if (modal.mode === 'edit') await api.put(`/accounting/purchases/${modal.data.id}/`, payload)
        else await api.post('/accounting/purchases/', payload)
      } else {
        payload.customer_id = invoiceForm.party_id
        payload.settlement_type = invoiceForm.settlement_type
        if (modal.mode === 'edit') await api.put(`/accounting/sales/${modal.data.id}/`, payload)
        else await api.post('/accounting/sales/', payload)
      }
    } else {
      if (voucherDebitTotal.value !== voucherCreditTotal.value) {
        state.error = 'جمع بدهکار و بستانکار باید برابر باشد.'
        return
      }
      const payload = {
        voucher_no: voucherForm.voucher_no,
        date: parseJalaliToIso(voucherForm.date_jalali),
        description: voucherForm.description,
        status: voucherForm.status,
        voucher_entries: voucherForm.voucher_entries.map((item) => ({
          account_id: item.account_id,
          debit: Number(item.debit || 0),
          credit: Number(item.credit || 0),
          row_description: item.row_description || ''
        }))
      }
      if (modal.mode === 'edit') await api.put(`/accounting/vouchers/${modal.data.id}/`, payload)
      else await api.post('/accounting/vouchers/', payload)
    }
    closeModal()
    await loadBootstrap()
    await refreshActive()
  } catch (error) {
    state.error = error?.response?.data?.detail || JSON.stringify(error?.response?.data || {}) || 'ذخیره ناموفق بود.'
  }
}

const deleteRow = async (row) => {
  const confirmed = window.confirm('این مورد حذف شود؟')
  if (!confirmed) return
  try {
    const endpoint = currentTab.value === 'inventory'
      ? `/accounting/inventory/${row.id}/`
      : currentTab.value === 'purchases'
        ? `/accounting/purchases/${row.id}/`
        : currentTab.value === 'sales'
          ? `/accounting/sales/${row.id}/`
          : `/accounting/vouchers/${row.id}/`
    await api.delete(endpoint)
    await refreshActive()
  } catch (error) {
    state.error = error?.response?.data?.detail || 'حذف ناموفق بود.'
  }
}

const confirmRow = async (row) => {
  const confirmed = window.confirm('فاکتور تأیید شود؟')
  if (!confirmed) return
  try {
    const endpoint = currentTab.value === 'purchases'
      ? `/accounting/purchases/${row.id}/confirm/`
      : `/accounting/sales/${row.id}/confirm/`
    await api.post(endpoint)
    await refreshActive()
  } catch (error) {
    state.error = error?.response?.data?.detail || 'تأیید ناموفق بود.'
  }
}

watch(() => route.query.tab, (value) => {
  if (value && value !== currentTab.value) currentTab.value = value
})

watch(
  () => [filters.search, filters.category, filters.lowStock, filters.status, filters.settlementType, filters.referenceType, currentTab.value],
  async () => {
    state.page = 1
    await refreshActive()
  }
)

onMounted(async () => {
  resetForms()
  await loadBootstrap()
  await refreshActive()
})
</script>

<style scoped>
.dashboard-page{min-height:100vh;background:#f8fafc}
.topbar{height:72px;display:flex;justify-content:space-between;align-items:center;padding:0 20px;background:#fff;border-bottom:1px solid #e2e8f0}
.topbar-left{display:flex;align-items:center;gap:12px}.brand{font-weight:700;color:#1e293b}.search-box input{height:40px;border:1px solid #cbd5e1;border-radius:10px;padding:0 12px;min-width:280px}.profile-name{margin:0;font-weight:700}
.layout{display:grid;grid-template-columns:220px 1fr;gap:14px;padding:14px}.sidebar{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:10px;height:fit-content}.menu-item{display:block;padding:10px;border-radius:10px;color:#334155;text-decoration:none}.menu-item.active{background:#dbeafe;color:#1d4ed8;font-weight:700}
.content{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px}
.content-head{display:flex;justify-content:center}
.add-main-btn{min-width:20px;height:44px;margin-right: 30px;}
.tabs-bar{display:flex;gap:8px;margin-bottom:14px}.chip{border:0;background:#e2e8f0;color:#334155;padding:8px 14px;border-radius:10px;cursor:pointer}.chip.active{background:#2563eb;color:#fff}
.card{border:1px solid #e2e8f0;border-radius:12px;padding:14px;margin-bottom:12px}
.toolbar-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
.field { width: 100%; min-height: 42px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 0 10px; background: #fff; font-family: inherit; }
.textarea { min-height: 90px; padding-top: 10px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { border-bottom:1px solid #e2e8f0; padding:10px 8px; text-align:right; vertical-align: middle; white-space:nowrap; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; }
.icon-btn,.page-btn{border:0;border-radius:10px;padding:8px 12px;cursor:pointer;background:#e2e8f0}
.icon-btn.accent{background:#fef3c7;color:#92400e}.icon-btn.danger{background:#fee2e2;color:#991b1b}
.primary-btn{border:0;border-radius:10px;padding:8px 12px;cursor:pointer;background:#2563eb;color:#fff}
.badge{display:inline-flex;align-items:center;border-radius:999px;padding:4px 10px;background:#e2e8f0}
.badge.warning{background:#fef3c7}.badge.success{background:#d1fae5}
.pagination { display: flex; align-items: center; justify-content: space-between; margin-top: 14px; }
.state-box { min-height: 180px; display: flex; align-items: center; justify-content: center; color: #475569; }
.state-box.error { color: #991b1b; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(11, 22, 17, 0.48); display: flex; align-items: center; justify-content: center; padding: 18px; z-index: 100; }
.modal-panel { width: min(1180px, 100%); max-height: calc(100vh - 36px); overflow: auto; border-radius: 16px; background: #fff; border:1px solid #e2e8f0; }
.modal-head { display: flex; align-items: center; justify-content: space-between; padding: 20px; border-bottom: 1px solid #e2e8f0; }
.modal-head p, .modal-head h3 { margin: 0; }
.close-btn { width: 38px; height: 38px; border: 0; border-radius: 10px; background: #f1f5f9; cursor: pointer; }
.modal-body, .details-panel { padding: 20px; display: grid; gap: 16px; }
.grid { display: grid; gap: 12px; }
.grid.cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid .full { grid-column: 1 / -1; }
.line-card { border:1px solid #e2e8f0;border-radius:12px;padding:14px;display:grid;gap:12px;background:#fff; }
.line-head { display: flex; align-items: center; justify-content: space-between; }
.line-row { display: grid; grid-template-columns: 1.4fr repeat(7, 1fr) auto; gap: 8px; }
.line-row.voucher { grid-template-columns: 1.4fr 1.4fr 1fr 1fr auto; }
.line-grid-head,.voucher-grid-head{display:grid;gap:8px;font-size:12px;font-weight:700;color:#475569;margin-bottom:6px}
.line-grid-head{grid-template-columns:1.4fr repeat(7,1fr) auto}
.voucher-grid-head{grid-template-columns:1.4fr 1.4fr 1fr 1fr auto}
.totals-box { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-top: 10px; border-top: 1px dashed #cbd5e1; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; }
pre { margin: 0; white-space: pre-wrap; word-break: break-word; background: #0f172a; color: #e2e8f0; padding: 16px; border-radius: 12px; }
@media (max-width: 1100px) {
  .layout{grid-template-columns:1fr}.search-box input{min-width:180px}
  .toolbar-grid { grid-template-columns: 1fr 1fr; }
  .line-grid-head,.voucher-grid-head{display:none}
  .line-row, .line-row.voucher, .grid.cols-2 { grid-template-columns: 1fr; }
}
</style>
