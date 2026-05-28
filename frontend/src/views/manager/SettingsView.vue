<template>
  <div class="dashboard-page" dir="rtl">
    <header class="topbar">
      <div class="topbar-left">
        <span class="brand">CarWash</span>
        <div class="search-box"><input v-model="search" type="text" placeholder="جستجو در تنظیمات..." /></div>
      </div>
      <div class="topbar-right">
        <div class="profile"><p class="profile-name">{{ authStore.user?.full_name || authStore.user?.username || 'کاربر' }}</p></div>
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

      <main class="content settings-content">
        <section class="tabs-bar">
          <button v-for="tab in tabs" :key="tab.key" class="chip" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
        </section>

        <section class="card">
          <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>

          <template v-if="activeTab === 'workers'">
            <div class="head-row"><h2>مدیریت نیروها</h2><button class="primary-btn" @click="openWorkerModal()">افزودن نیرو</button></div>
            <div class="table-wrap"><table><thead><tr><th>نام</th><th>شماره</th><th>وضعیت</th><th>عملیات</th></tr></thead><tbody>
              <tr v-for="item in filteredWorkers" :key="item.id"><td>{{ item.full_name }}</td><td>{{ item.phone || '-' }}</td><td>{{ item.is_available ? 'فعال' : 'غیرفعال' }}</td><td><button class="table-btn" @click="openWorkerModal(item)">ویرایش</button> <button class="table-btn danger" @click="deleteWorker(item)">حذف</button></td></tr>
            </tbody></table></div>
          </template>

          <template v-else-if="activeTab === 'products'">
            <div class="head-row"><h2>مدیریت محصولات</h2><button class="primary-btn" @click="openProductModal()">افزودن محصول</button></div>
            <div class="table-wrap"><table><thead><tr><th>نام</th><th>SKU</th><th>قیمت فروش</th><th>فعال</th><th>عملیات</th></tr></thead><tbody>
              <tr v-for="item in filteredProducts" :key="item.id"><td>{{ item.name }}</td><td>{{ item.sku }}</td><td>{{ money(item.sale_price) }}</td><td>{{ item.is_active ? 'بله' : 'خیر' }}</td><td><button class="table-btn" @click="openProductModal(item)">ویرایش</button> <button class="table-btn danger" @click="deleteProduct(item)">حذف</button></td></tr>
            </tbody></table></div>
          </template>

          <template v-else>
            <div class="head-row"><h2>مدیریت خدمات</h2><button class="primary-btn" @click="openServiceModal()">افزودن خدمت</button></div>
            <div class="table-wrap"><table><thead><tr><th>نام</th><th>کد</th><th>قیمت</th><th>مدت</th><th>فعال</th><th>عملیات</th></tr></thead><tbody>
              <tr v-for="item in filteredServices" :key="item.id"><td>{{ item.name }}</td><td>{{ item.code || '-' }}</td><td>{{ money(item.base_price) }}</td><td>{{ item.estimated_duration_minutes }} دقیقه</td><td>{{ item.is_active ? 'بله' : 'خیر' }}</td><td><button class="table-btn" @click="openServiceModal(item)">ویرایش</button> <button class="table-btn danger" @click="deleteService(item)">حذف</button></td></tr>
            </tbody></table></div>
          </template>
        </section>
      </main>
    </div>

    <div v-if="modal.open" class="modal-overlay" @click.self="closeModal"><section class="modal-panel"><header class="modal-head"><h3>{{ modal.title }}</h3><button class="close-btn" @click="closeModal">✕</button></header>
      <form class="modal-form" @submit.prevent="submitModal">
        <template v-if="modal.type === 'workers'">
          <label><span>نام کامل</span><input v-model="forms.worker.full_name" required /></label>
          <label><span>شماره موبایل</span><input v-model="forms.worker.phone" required /></label>
          <label class="row-check"><input type="checkbox" v-model="forms.worker.is_available" /><span>فعال</span></label>
        </template>
        <template v-else-if="modal.type === 'products'">
          <label><span>نام</span><input v-model="forms.product.name" required /></label>
          <label><span>SKU</span><input v-model="forms.product.sku" required /></label>
          <label><span>قیمت فروش (هزار تومان)</span><input type="number" min="0" v-model.number="forms.product.sale_price" required /></label>
          <label><span>قیمت خرید (هزار تومان)</span><input type="number" min="0" v-model.number="forms.product.cost_price" required /></label>
          <label><span>واحد</span><input v-model="forms.product.unit" /></label>
          <label><span>حداقل موجودی</span><input type="number" min="0" v-model.number="forms.product.min_stock" /></label>
          <label class="row-check"><input type="checkbox" v-model="forms.product.is_active" /><span>فعال</span></label>
        </template>
        <template v-else>
          <label><span>نام خدمت</span><input v-model="forms.service.name" required /></label>
          <label><span>کد</span><input v-model="forms.service.code" /></label>
          <label><span>قیمت پایه (هزار تومان)</span><input type="number" min="0" v-model.number="forms.service.base_price" required /></label>
          <label><span>مدت (دقیقه)</span><input type="number" min="1" v-model.number="forms.service.estimated_duration_minutes" required /></label>
          <label class="row-check"><input type="checkbox" v-model="forms.service.is_active" /><span>فعال</span></label>
        </template>
        <div class="modal-actions"><button type="button" class="secondary-btn" @click="closeModal">انصراف</button><button class="primary-btn">ذخیره</button></div>
      </form>
    </section></div>

    <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.msg }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import api from '../../services/api'
import { useAuthStore } from '../../store/auth.store'

const route = useRoute()
const authStore = useAuthStore()
const search = ref('')
const activeTab = ref('workers')
const errorMessage = ref('')
const tabs = [{ key: 'workers', label: 'نیروها' }, { key: 'products', label: 'محصولات' }, { key: 'services', label: 'خدمات' }]
const workers = ref([])
const products = ref([])
const services = ref([])
const modal = reactive({ open: false, type: '', id: null, title: '' })
const forms = reactive({ worker: { full_name: '', phone: '', is_available: true }, product: { name: '', sku: '', sale_price: 0, cost_price: 0, unit: 'unit', min_stock: 0, is_active: true }, service: { name: '', code: '', base_price: 0, estimated_duration_minutes: 30, is_active: true } })
const toast = reactive({ show: false, type: 'success', msg: '' })
let timer = null
const t = (msg, type = 'success') => { toast.show = true; toast.msg = msg; toast.type = type; if (timer) clearTimeout(timer); timer = setTimeout(() => (toast.show = false), 2400) }
const money = (v) => `${Number(v || 0).toLocaleString('fa-IR')} تومان`
const toThousandsDisplay = (value) => Math.round(Number(value || 0) / 1000)
const fromThousandsInput = (value) => Math.round(Number(value || 0) * 1000)

const filteredWorkers = computed(() => workers.value.filter((i) => (`${i.full_name} ${i.phone || ''}`).includes(search.value)))
const filteredProducts = computed(() => products.value.filter((i) => (`${i.name} ${i.sku}`).includes(search.value)))
const filteredServices = computed(() => services.value.filter((i) => (`${i.name} ${i.code || ''}`).includes(search.value)))

const loadAll = async () => {
  try {
    const [w, p, s] = await Promise.all([api.get('/workers/'), api.get('/products/'), api.get('/services/')])
    workers.value = Array.isArray(w.data) ? w.data : []
    products.value = Array.isArray(p.data) ? p.data : []
    services.value = Array.isArray(s.data) ? s.data : []
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || 'خطا در بارگذاری داده‌ها'
  }
}

const openWorkerModal = (item = null) => { modal.open = true; modal.type = 'workers'; modal.id = item?.id || null; modal.title = modal.id ? '?????? ????' : '?????? ????'; forms.worker.full_name = item?.full_name || ''; forms.worker.phone = item?.phone || ''; forms.worker.is_available = item?.is_available ?? true }
const openProductModal = (item = null) => { modal.open = true; modal.type = 'products'; modal.id = item?.id || null; modal.title = modal.id ? 'ویرایش محصول' : 'افزودن محصول'; Object.assign(forms.product, { name: item?.name || '', sku: item?.sku || '', sale_price: toThousandsDisplay(item?.sale_price), cost_price: toThousandsDisplay(item?.cost_price), unit: item?.unit || 'unit', min_stock: Number(item?.min_stock || 0), is_active: item?.is_active ?? true }) }
const openServiceModal = (item = null) => { modal.open = true; modal.type = 'services'; modal.id = item?.id || null; modal.title = modal.id ? 'ویرایش خدمت' : 'افزودن خدمت'; Object.assign(forms.service, { name: item?.name || '', code: item?.code || '', base_price: toThousandsDisplay(item?.base_price), estimated_duration_minutes: Number(item?.estimated_duration_minutes || 30), is_active: item?.is_active ?? true }) }
const closeModal = () => { modal.open = false; modal.type = ''; modal.id = null }

const submitModal = async () => {
  try {
    if (modal.type === 'workers') {
      const workerPayload = {
        ...forms.worker,
        service_share_value: forms.worker.service_share_type === 'fixed'
          ? fromThousandsInput(forms.worker.service_share_value)
          : Number(forms.worker.service_share_value || 0)
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
  } catch (e) { t(e?.response?.data?.detail || 'ثبت ناموفق بود', 'error') }
}

const deleteWorker = async (item) => { if (!confirm('حذف شود؟')) return; await api.delete(`/workers/${item.id}/`); t('حذف شد'); await loadAll() }
const deleteProduct = async (item) => { if (!confirm('حذف شود؟')) return; await api.delete(`/products/${item.id}/`); t('حذف شد'); await loadAll() }
const deleteService = async (item) => { if (!confirm('حذف شود؟')) return; await api.delete(`/services/${item.id}/`); t('حذف شد'); await loadAll() }

onMounted(async () => { await authStore.fetchMe(); await loadAll() })
</script>

<style scoped>
.dashboard-page{min-height:100vh;background:#f8fafc}
.topbar{height:72px;display:flex;justify-content:space-between;align-items:center;padding:0 20px;background:#fff;border-bottom:1px solid #e2e8f0}
.topbar-left{display:flex;align-items:center;gap:12px}.brand{font-weight:700;color:#1e293b}.search-box input{height:40px;border:1px solid #cbd5e1;border-radius:10px;padding:0 12px;min-width:280px}.profile-name{margin:0;font-weight:700}
.layout{display:grid;grid-template-columns:220px 1fr;gap:14px;padding:14px}.sidebar{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:10px;height:fit-content}.menu-item{display:block;padding:10px;border-radius:10px;color:#334155;text-decoration:none}.menu-item.active{background:#dbeafe;color:#1d4ed8;font-weight:700}
.content{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:16px}.tabs-bar{display:flex;gap:8px;margin-bottom:14px}.chip{border:0;background:#e2e8f0;color:#334155;padding:8px 14px;border-radius:999px;cursor:pointer}.chip.active{background:#2563eb;color:#fff}
.card{border:1px solid #e2e8f0;border-radius:12px;padding:14px}.head-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}h2{margin:0;font-size:20px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #e2e8f0;text-align:right;white-space:nowrap}
.primary-btn,.secondary-btn{border:0;border-radius:10px;padding:8px 12px;cursor:pointer}.primary-btn{background:linear-gradient(90deg,#2563eb,#0891b2);color:#fff}.secondary-btn{background:#e2e8f0}.table-btn{border:0;background:#e2e8f0;padding:6px 10px;border-radius:8px;cursor:pointer}.table-btn.danger{background:#fee2e2;color:#991b1b}
.modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.45);display:flex;align-items:center;justify-content:center;padding:18px;z-index:99}.modal-panel{width:min(560px,100%);background:#fff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden}.modal-head{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid #e2e8f0}.close-btn{border:0;background:#f1f5f9;border-radius:8px;width:30px;height:30px;cursor:pointer}.modal-form{padding:14px;display:grid;gap:10px}.modal-form label{display:grid;gap:5px}.modal-form input{height:42px;border:1px solid #cbd5e1;border-radius:10px;padding:0 10px}.row-check{display:flex!important;align-items:center;gap:8px}.modal-actions{display:flex;justify-content:flex-end;gap:8px}
.error-box{margin-bottom:10px;padding:10px;background:#fee2e2;color:#991b1b;border:1px solid #fecaca;border-radius:10px}.toast{position:fixed;left:20px;bottom:20px;padding:10px 14px;border-radius:10px;color:#fff;z-index:120}.toast.success{background:#16a34a}.toast.error{background:#dc2626}
@media (max-width:960px){.layout{grid-template-columns:1fr}.search-box input{min-width:180px}}
</style>


