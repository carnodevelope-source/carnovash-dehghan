<template>
  <AppShell
    title="تنظیمات"
    subtitle="پیکربندی نیروها، خدمات و موجودی"
    :show-search="true"
    search-placeholder="جستجو در تنظیمات..."
    :search-query="search"
    @update:search-query="search = $event"
  >
    <div class="settings-content">
      <section class="tabs-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="chip"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </section>

      <section class="card">
        <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>

        <template v-if="activeTab === 'users'">
          <div class="head-row">
            <h2>مدیریت کاربران</h2>
            <button class="primary-btn" @click="openUserModal()">افزودن کاربر</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>نام</th>
                  <th>نام کاربری</th>
                  <th>شماره</th>
                  <th>نقش</th>
                  <th>وضعیت</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in filteredUsers" :key="item.id">
                  <td>{{ item.full_name || '-' }}</td>
                  <td>{{ item.username }}</td>
                  <td>{{ item.phone || '-' }}</td>
                  <td>{{ roleLabelMap[item.role] || item.role }}</td>
                  <td>{{ item.is_active ? 'فعال' : 'غیرفعال' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else-if="activeTab === 'workers'">
          <div class="head-row">
            <h2>مدیریت نیروها</h2>
            <button class="primary-btn" @click="openWorkerModal()">افزودن نیرو</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>نام</th>
                  <th>شماره</th>
                  <th>نوع پرداخت</th>
                  <th>مقدار پرداخت</th>
                  <th>درصد انعام</th>
                  <th>وضعیت</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in filteredWorkers" :key="item.id">
                  <td>{{ item.full_name }}</td>
                  <td>{{ item.phone || '-' }}</td>
                  <td>{{ item.payment_type === 'fixed' ? 'ریالی' : 'درصدی' }}</td>
                  <td>{{ formatWorkerPayment(item) }}</td>
                  <td>{{ Number(item.tip_share_percent || 0).toLocaleString('fa-IR') }}٪</td>
                  <td>{{ item.is_available ? 'فعال' : 'غیرفعال' }}</td>
                  <td>
                    <button class="table-btn" @click="openWorkerModal(item)">ویرایش</button>
                    <button class="table-btn danger" @click="deleteWorker(item)">حذف</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else-if="activeTab === 'products'">
          <div class="head-row">
            <h2>مدیریت محصولات</h2>
            <div class="head-actions">
              <button class="secondary-btn" @click="openProductPurchaseModal()">ثبت خرید جدید</button>
              <button class="primary-btn" @click="openProductModal()">افزودن محصول</button>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>نام</th>
                  <th>قیمت فروش</th>
                  <th>موجودی</th>
                  <th>فعال</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in filteredProducts" :key="item.id">
                  <td>{{ item.name }}</td>
                  <td>{{ money(item.sale_price) }}</td>
                  <td>{{ Number(item.stock_qty || 0).toLocaleString('fa-IR') }}</td>
                  <td>{{ item.is_active ? 'بله' : 'خیر' }}</td>
                  <td>
                    <button class="table-btn" @click="openProductModal(item)">ویرایش</button>
                    <button class="table-btn danger" @click="deleteProduct(item)">حذف</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else-if="activeTab === 'services'">
          <div class="head-row">
            <h2>مدیریت خدمات</h2>
            <button class="primary-btn" @click="openServiceModal()">افزودن خدمت</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>نام</th>
                  <th>قیمت</th>
                  <th>مدت</th>
                  <th>فعال</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in filteredServices" :key="item.id">
                  <td>{{ item.name }}</td>
                  <td>{{ money(item.base_price) }}</td>
                  <td>{{ item.estimated_duration_minutes }} دقیقه</td>
                  <td>{{ item.is_active ? 'بله' : 'خیر' }}</td>
                  <td>
                    <button class="table-btn" @click="openServiceModal(item)">ویرایش</button>
                    <button class="table-btn danger" @click="deleteService(item)">حذف</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else>
          <div class="head-row">
            <h2>تنظیمات عمومی</h2>
          </div>
          <div class="general-settings-form">
            <label class="general-setting-label">
              <span>درصد تخفیف به‌ازای هر نیم‌ستاره</span>
              <input
                v-model.number="generalSettings.discount_percent_per_half_star"
                type="number"
                min="0"
                max="100"
                step="0.01"
              />
            </label>
            <p class="helper-text">
              مثال: اگر این مقدار ۵٪ باشد، با هر ۱ ستاره کامل، تخفیف مشتری ۱۰٪ خواهد بود.
            </p>
            <p class="helper-text">
              پیش‌نمایش فعلی: ۱ ستاره کامل = {{ fullStarDiscountLabel }} تخفیف
            </p>
            <div class="modal-actions">
              <button class="primary-btn" :disabled="generalSettingsSaving" @click="saveGeneralSettings">
                {{ generalSettingsSaving ? 'در حال ذخیره...' : 'ذخیره تنظیمات عمومی' }}
              </button>
            </div>
          </div>
        </template>
      </section>
    </div>

    <div v-if="modal.open" class="modal-overlay" @click.self="closeModal">
      <section class="modal-panel">
        <header class="modal-head">
          <h3>{{ modal.title }}</h3>
          <button class="close-btn" @click="closeModal">✕</button>
        </header>

        <form class="modal-form" @submit.prevent="submitModal">
          <template v-if="modal.type === 'users'">
            <label><span>نام</span><input v-model="forms.user.first_name" required /></label>
            <label><span>نام خانوادگی</span><input v-model="forms.user.last_name" required /></label>
            <label><span>نام کاربری</span><input v-model="forms.user.username" required /></label>
            <label><span>شماره موبایل</span><input v-model="forms.user.phone" required /></label>
            <label>
              <span>نقش کاربر</span>
              <select v-model="forms.user.role" required>
                <option value="manager">مدیر</option>
                <option value="accountant">حسابدار</option>
                <option value="operator">اپراتور</option>
                <option value="worker">نیرو</option>
                <option v-if="authStore.role === 'admin'" value="owner">مالک</option>
                <option v-if="authStore.role === 'admin'" value="admin">ادمین</option>
              </select>
            </label>
            <label><span>رمز عبور</span><input v-model="forms.user.password" type="password" minlength="6" required /></label>
            <label class="row-check"><input type="checkbox" v-model="forms.user.is_active" /><span>فعال</span></label>
          </template>

          <template v-else-if="modal.type === 'workers'">
            <label><span>نام کامل</span><input v-model="forms.worker.full_name" required /></label>
            <label><span>شماره موبایل</span><input v-model="forms.worker.phone" required /></label>
            <label>
              <span>نوع پرداخت نیرو</span>
              <select v-model="forms.worker.payment_type">
                <option value="percent">درصدی</option>
                <option value="fixed">ریالی</option>
              </select>
            </label>
            <label>
              <span>{{ forms.worker.payment_type === 'fixed' ? 'مبلغ دریافتی (هزار تومان)' : 'درصد دریافتی' }}</span>
              <input type="number" :min="0" :max="forms.worker.payment_type === 'percent' ? 100 : null" v-model.number="forms.worker.payment_value" required />
            </label>
            <label><span>درصد انعام</span><input type="number" min="0" max="100" v-model.number="forms.worker.tip_share_percent" required /></label>
            <label class="row-check"><input type="checkbox" v-model="forms.worker.is_available" /><span>فعال</span></label>
          </template>

          <template v-else-if="modal.type === 'products'">
            <label><span>نام</span><input v-model="forms.product.name" required /></label>
            <label><span>قیمت فروش (هزار تومان)</span><input type="number" min="0" v-model.number="forms.product.sale_price" required /></label>
            <label><span>قیمت خرید (هزار تومان)</span><input type="number" min="0" v-model.number="forms.product.cost_price" required /></label>
            <label><span>واحد</span><input v-model="forms.product.unit" /></label>
            <label><span>حداقل موجودی</span><input type="number" min="0" v-model.number="forms.product.min_stock" /></label>
            <label class="row-check"><input type="checkbox" v-model="forms.product.is_active" /><span>فعال</span></label>
          </template>

          <template v-else-if="modal.type === 'product_purchase'">
            <label>
              <span>محصول</span>
              <select v-model.number="forms.purchase.product_id" required>
                <option :value="0" disabled>انتخاب محصول</option>
                <option v-for="item in products" :key="item.id" :value="item.id">{{ item.name }}</option>
              </select>
            </label>
            <label><span>تعداد خرید</span><input type="number" min="0.01" step="0.01" v-model.number="forms.purchase.quantity" required /></label>
            <label><span>قیمت خرید واحد (هزار تومان)</span><input type="number" min="0" v-model.number="forms.purchase.unit_cost" /></label>
            <label><span>قیمت فروش واحد (هزار تومان)</span><input type="number" min="0" v-model.number="forms.purchase.sale_price" /></label>
            <label><span>توضیح</span><input v-model="forms.purchase.note" placeholder="اختیاری" /></label>
          </template>

          <template v-else>
            <label><span>نام خدمت</span><input v-model="forms.service.name" required /></label>
            <label><span>قیمت پایه (هزار تومان)</span><input type="number" min="0" v-model.number="forms.service.base_price" required /></label>
            <label><span>مدت (دقیقه)</span><input type="number" min="1" v-model.number="forms.service.estimated_duration_minutes" required /></label>
            <label class="row-check"><input type="checkbox" v-model="forms.service.is_active" /><span>فعال</span></label>
          </template>

          <div class="modal-actions">
            <button type="button" class="secondary-btn" @click="closeModal">انصراف</button>
            <button class="primary-btn">ذخیره</button>
          </div>
        </form>
      </section>
    </div>

    <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.msg }}</div>
  </AppShell>
</template>
<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import api from '../../services/api'
import { useAuthStore } from '../../store/auth.store'
import AppShell from '../../components/layout/AppShell.vue'

const authStore = useAuthStore()
const search = ref('')
const activeTab = ref('workers')
const errorMessage = ref('')

const tabs = [
  { key: 'users', label: 'کاربران' },
  { key: 'workers', label: 'نیروها' },
  { key: 'products', label: 'محصولات' },
  { key: 'services', label: 'خدمات' },
  { key: 'general', label: 'تنظیمات عمومی' }
]

const users = ref([])
const workers = ref([])
const products = ref([])
const services = ref([])
const inventoryItems = ref([])
const generalSettings = reactive({
  discount_percent_per_half_star: 0
})
const generalSettingsSaving = ref(false)

const modal = reactive({ open: false, type: '', id: null, title: '' })
const forms = reactive({
  user: { first_name: '', last_name: '', username: '', phone: '', role: 'operator', password: '', is_active: true },
  worker: { full_name: '', phone: '', payment_type: 'percent', payment_value: 0, tip_share_percent: 0, is_available: true },
  product: { name: '', sale_price: 0, cost_price: 0, unit: 'unit', min_stock: 0, is_active: true },
  purchase: { product_id: 0, quantity: 1, unit_cost: 0, sale_price: 0, note: '' },
  service: { name: '', base_price: 0, estimated_duration_minutes: 30, is_active: true }
})

const toast = reactive({ show: false, type: 'success', msg: '' })
let timer = null

const t = (msg, type = 'success') => {
  toast.show = true
  toast.msg = msg
  toast.type = type
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => (toast.show = false), 2400)
}

const money = (v) => `${Number(v || 0).toLocaleString('fa-IR')} تومان`
const toThousandsDisplay = (value) => Math.round(Number(value || 0) / 1000)
const fromThousandsInput = (value) => Math.round(Number(value || 0) * 1000)

const apiErrorText = (error) => {
  const data = error?.response?.data
  if (!data) return 'ثبت ناموفق بود'
  if (typeof data.detail === 'string' && data.detail.trim()) return data.detail
  if (typeof data === 'string') return data
  const firstField = Object.keys(data)[0]
  if (!firstField) return 'ثبت ناموفق بود'
  const raw = data[firstField]
  if (Array.isArray(raw)) return String(raw[0] || 'ثبت ناموفق بود')
  if (raw && typeof raw === 'object') {
    const nestedKey = Object.keys(raw)[0]
    const nestedRaw = raw[nestedKey]
    if (Array.isArray(nestedRaw)) return String(nestedRaw[0] || 'ثبت ناموفق بود')
  }
  return String(raw || 'ثبت ناموفق بود')
}


const formatWorkerPayment = (worker) => {
  if ((worker?.payment_type || 'percent') === 'fixed') return money(worker?.payment_value || 0)
  return `${Number(worker?.payment_value || 0).toLocaleString('fa-IR')}٪`
}

const stockByProductId = computed(() => {
  const map = {}
  for (const item of inventoryItems.value) {
    const pid = Number(item.product)
    if (!Number.isFinite(pid)) continue
    map[pid] = Number(item.available_quantity ?? item.quantity_on_hand ?? 0)
  }
  return map
})

const productsWithStock = computed(() => products.value.map((item) => ({
  ...item,
  stock_qty: stockByProductId.value[Number(item.id)] ?? 0
})))

const filteredWorkers = computed(() => workers.value.filter((i) => (`${i.full_name} ${i.phone || ''}`).includes(search.value)))
const roleLabelMap = {
  admin: 'ادمین',
  owner: 'مالک',
  manager: 'مدیر',
  accountant: 'حسابدار',
  operator: 'اپراتور',
  worker: 'نیرو'
}
const filteredUsers = computed(() => users.value.filter((i) => (`${i.full_name || ''} ${i.username || ''} ${i.phone || ''}`).includes(search.value)))
const filteredProducts = computed(() => productsWithStock.value.filter((i) => (`${i.name} ${i.unit || ''}`).includes(search.value)))
const filteredServices = computed(() => services.value.filter((i) => (`${i.name}`).includes(search.value)))
const fullStarDiscountLabel = computed(() => `${Number((Number(generalSettings.discount_percent_per_half_star || 0) * 2).toFixed(2)).toLocaleString('fa-IR')}٪`)

watch(() => forms.purchase.product_id, (newProductId) => {
  const selected = products.value.find((item) => Number(item.id) === Number(newProductId))
  if (!selected) return
  forms.purchase.unit_cost = toThousandsDisplay(selected.cost_price || 0)
  forms.purchase.sale_price = toThousandsDisplay(selected.sale_price || 0)
})

const loadAll = async () => {
  try {
    const [u, w, p, s, inv] = await Promise.all([
      api.get('/auth/users/'),
      api.get('/workers/'),
      api.get('/products/'),
      api.get('/services/'),
      api.get('/inventory/')
    ])
    users.value = Array.isArray(u.data) ? u.data : []
    workers.value = Array.isArray(w.data) ? w.data : []
    products.value = Array.isArray(p.data) ? p.data : []
    services.value = Array.isArray(s.data) ? s.data : []
    inventoryItems.value = Array.isArray(inv.data) ? inv.data : []
    try {
      const gs = await api.get('/services/general-settings/')
      generalSettings.discount_percent_per_half_star = Number(gs.data?.discount_percent_per_half_star || 0)
    } catch {
      generalSettings.discount_percent_per_half_star = 0
    }
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || 'خطا در بارگذاری داده‌ها'
  }
}

const saveGeneralSettings = async () => {
  generalSettingsSaving.value = true
  try {
    const payload = {
      discount_percent_per_half_star: Number(generalSettings.discount_percent_per_half_star || 0)
    }
    const response = await api.patch('/services/general-settings/', payload)
    generalSettings.discount_percent_per_half_star = Number(response.data?.discount_percent_per_half_star || 0)
    t('تنظیمات عمومی ذخیره شد')
  } catch (e) {
    t(apiErrorText(e), 'error')
  } finally {
    generalSettingsSaving.value = false
  }
}

const openUserModal = () => {
  modal.open = true
  modal.type = 'users'
  modal.id = null
  modal.title = 'افزودن کاربر'
  Object.assign(forms.user, {
    first_name: '',
    last_name: '',
    username: '',
    phone: '',
    role: 'operator',
    password: '',
    is_active: true
  })
}

const openWorkerModal = (item = null) => {
  modal.open = true
  modal.type = 'workers'
  modal.id = item?.id || null
  modal.title = modal.id ? 'ویرایش نیرو' : 'افزودن نیرو'
  forms.worker.full_name = item?.full_name || ''
  forms.worker.phone = item?.phone || ''
  forms.worker.payment_type = item?.payment_type || 'percent'
  forms.worker.payment_value = forms.worker.payment_type === 'fixed'
    ? toThousandsDisplay(item?.payment_value || 0)
    : Number(item?.payment_value || 0)
  forms.worker.tip_share_percent = Number(item?.tip_share_percent || 0)
  forms.worker.is_available = item?.is_available ?? true
}

const openProductModal = (item = null) => {
  modal.open = true
  modal.type = 'products'
  modal.id = item?.id || null
  modal.title = modal.id ? 'ویرایش محصول' : 'افزودن محصول'
  Object.assign(forms.product, {
    name: item?.name || '',
    sale_price: toThousandsDisplay(item?.sale_price),
    cost_price: toThousandsDisplay(item?.cost_price),
    unit: item?.unit || 'unit',
    min_stock: Number(item?.min_stock || 0),
    is_active: item?.is_active ?? true
  })
}

const openProductPurchaseModal = (item = null) => {
  modal.open = true
  modal.type = 'product_purchase'
  modal.id = null
  modal.title = 'ثبت خرید جدید'
  Object.assign(forms.purchase, {
    product_id: Number(item?.id || 0),
    quantity: 1,
    unit_cost: toThousandsDisplay(item?.cost_price || 0),
    sale_price: toThousandsDisplay(item?.sale_price || 0),
    note: ''
  })
}

const openServiceModal = (item = null) => {
  modal.open = true
  modal.type = 'services'
  modal.id = item?.id || null
  modal.title = modal.id ? 'ویرایش خدمت' : 'افزودن خدمت'
  Object.assign(forms.service, {
    name: item?.name || '',
    base_price: toThousandsDisplay(item?.base_price),
    estimated_duration_minutes: Number(item?.estimated_duration_minutes || 30),
    is_active: item?.is_active ?? true
  })
}

const closeModal = () => {
  modal.open = false
  modal.type = ''
  modal.id = null
}

const submitModal = async () => {
  try {
    if (modal.type === 'users') {
      const firstName = String(forms.user.first_name || '').trim()
      const lastName = String(forms.user.last_name || '').trim()
      const userPayload = {
        first_name: firstName,
        last_name: lastName,
        full_name: `${firstName} ${lastName}`.trim(),
        username: forms.user.username,
        phone: forms.user.phone,
        role: forms.user.role,
        password: forms.user.password,
        is_active: !!forms.user.is_active
      }
      await api.post('/auth/users/', userPayload)
      t('کاربر ذخیره شد')
    } else if (modal.type === 'workers') {
      const paymentValueNormalized = forms.worker.payment_type === 'fixed'
        ? fromThousandsInput(forms.worker.payment_value)
        : Number(forms.worker.payment_value || 0)
      const workerPayload = {
        full_name: forms.worker.full_name,
        phone: forms.worker.phone,
        is_available: forms.worker.is_available,
        payment_type: forms.worker.payment_type,
        payment_value: Number.isFinite(Number(paymentValueNormalized)) ? Number(paymentValueNormalized) : 0,
        tip_share_percent: Number(forms.worker.tip_share_percent || 0)
      }
      if (modal.id) await api.patch(`/workers/${modal.id}/`, workerPayload)
      else await api.post('/workers/', workerPayload)
      t('نیرو ذخیره شد')
    } else if (modal.type === 'products') {
      const payload = {
        ...forms.product,
        sale_price: fromThousandsInput(forms.product.sale_price),
        cost_price: fromThousandsInput(forms.product.cost_price)
      }
      if (modal.id) await api.patch(`/products/${modal.id}/`, payload)
      else await api.post('/products/', payload)
      t('محصول ذخیره شد')
    } else if (modal.type === 'product_purchase') {
      const payload = {
        product_id: Number(forms.purchase.product_id || 0),
        quantity: Number(forms.purchase.quantity || 0),
        unit_cost: fromThousandsInput(forms.purchase.unit_cost || 0),
        sale_price: fromThousandsInput(forms.purchase.sale_price || 0),
        note: forms.purchase.note || ''
      }
      await api.post('/inventory/purchase/', payload)
      t('خرید محصول ثبت شد')
    } else {
      const payload = {
        ...forms.service,
        base_price: fromThousandsInput(forms.service.base_price)
      }
      if (modal.id) await api.patch(`/services/${modal.id}/`, payload)
      else await api.post('/services/', payload)
      t('خدمت ذخیره شد')
    }

    closeModal()
    await loadAll()
  } catch (e) {
    t(apiErrorText(e), 'error')
  }
}

const deleteWorker = async (item) => { if (!confirm('حذف شود؟')) return; await api.delete(`/workers/${item.id}/`); t('حذف شد'); await loadAll() }
const deleteProduct = async (item) => { if (!confirm('حذف شود؟')) return; await api.delete(`/products/${item.id}/`); t('حذف شد'); await loadAll() }
const deleteService = async (item) => { if (!confirm('حذف شود؟')) return; await api.delete(`/services/${item.id}/`); t('حذف شد'); await loadAll() }

onMounted(async () => {
  await authStore.fetchMe()
  await loadAll()
})
</script>

<style scoped>
.settings-content { min-width: 0; }
.tabs-bar { display: flex; gap: 8px; margin-bottom: 14px; }
.chip { border: 0; background: #e2e8f0; color: #334155; padding: 8px 14px; border-radius: 999px; cursor: pointer; }
.chip.active { background: #2563eb; color: #fff; }
.card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px; }
.head-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 10px; }
.head-actions { display: flex; gap: 8px; }
h2 { margin: 0; font-size: 20px; }
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right; white-space: nowrap; }
.primary-btn, .secondary-btn { border: 0; border-radius: 10px; padding: 8px 12px; cursor: pointer; }
.primary-btn { background: linear-gradient(90deg,#2563eb,#0891b2); color: #fff; }
.secondary-btn { background: #e2e8f0; }
.table-btn { border: 0; background: #e2e8f0; padding: 6px 10px; border-radius: 8px; cursor: pointer; margin-left: 6px; }
.table-btn.danger { background: #fee2e2; color: #991b1b; }
.modal-overlay { position: fixed; inset: 0; background: rgba(15,23,42,.45); display: flex; align-items: center; justify-content: center; padding: 18px; z-index: 99; }
.modal-panel { width: min(980px,100%); background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid #e2e8f0; }
.close-btn { border: 0; background: #f1f5f9; border-radius: 8px; width: 30px; height: 30px; cursor: pointer; }
.modal-form { padding: 14px; display: grid; gap: 10px; grid-template-columns: repeat(3, minmax(0, 1fr)); align-items: end; }
.modal-form label { display: grid; gap: 5px; }
.modal-form input, .modal-form select { height: 42px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 0 10px; background: #fff; }
.row-check { display: flex !important; align-items: center; gap: 8px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; grid-column: 1 / -1; }
.general-settings-form { display: grid; gap: 10px; max-width: 520px; }
.general-setting-label { display: grid; gap: 6px; }
.general-setting-label input { height: 42px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 0 10px; background: #fff; }
.helper-text { margin: 0; color: #475569; font-size: 13px; }
.error-box { margin-bottom: 10px; padding: 10px; background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; border-radius: 10px; }
.toast { position: fixed; left: 20px; bottom: 20px; padding: 10px 14px; border-radius: 10px; color: #fff; z-index: 120; }
.toast.success { background: #16a34a; }
.toast.error { background: #dc2626; }
@media (max-width: 960px) {
  .modal-form { grid-template-columns: 1fr; }
}
</style>




