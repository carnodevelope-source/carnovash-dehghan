<template>
  <div class="dashboard-page">
    <header class="topbar">
      <div class="topbar-left">
        <span class="brand">CarWash</span>
        <div class="search-box">
          <input v-model="search" type="text" placeholder="جستجوی پلاک یا نام..." />
        </div>
      </div>
      <div class="topbar-right">
        <button class="primary-btn" @click="openVehicleModal">ثبت خودروی جدید</button>
        <div class="profile">
          <div>
            <p class="profile-name">اپراتور</p>
          </div>
        </div>
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

      <main class="content">
        <div class="filters">
          <button
            v-for="item in filterItems"
            :key="item.key"
            class="chip"
            :class="{ active: activeFilter === item.key }"
            @click="activeFilter = item.key"
          >
            {{ item.label }}
          </button>
        </div>

        <section class="cards-grid">
          <article
            v-for="car in filteredCars"
            :key="car.id"
            class="car-card"
            :class="{ 'card-released': car.statusKey === 'released' }"
            :style="{ borderRightColor: car.color }"
            @click="openVehicleDetails(car.id)"
          >
            <div class="card-head">
              <div class="status">
                <span class="dot" :style="{ backgroundColor: car.color }"></span>
                <span>{{ car.status }}</span>
              </div>
              <span class="time" :style="{ backgroundColor: car.badgeBg, color: car.badgeText }">{{ car.time }}</span>
            </div>

            <div class="plate-box">
              <div class="plate-white-wrap">
                <span class="plate-part plate-two">{{ car.plateTwoDigit }}</span>
                <span class="plate-part plate-letter">{{ car.plateLetter }}</span>
                <span class="plate-part plate-three">{{ car.plateThreeDigit }}</span>
              </div>
              <span class="plate-blue">{{ car.plateBlue }}</span>
            </div>

            <div class="car-info">
              <h3>{{ car.model }} - {{ car.colorName }}</h3>
              <p>{{ car.service }}</p>
              <p>راننده: {{ car.driverName }} | {{ car.driverPhone }}</p>
              <p>نیرو: {{ car.workerName }}</p>
            </div>

            <button
              v-if="car.statusKey !== 'released'"
              class="card-action"
              :class="car.actionClass"
              @click.stop="handleCardAction(car)"
            >
              {{ car.action }}
            </button>
            <div v-else class="card-passive-state">ترخیص انجام شد</div>
          </article>
        </section>
      </main>
    </div>

    <div v-if="showVehicleModal" class="modal-overlay" @click.self="closeVehicleModal">
      <section class="modal-panel">
        <header class="modal-head">
          <div>
            <p class="modal-step">مرحله {{ modalStep }} از فرآیند پذیرش</p>
            <h2>{{ modalStep === 1 ? 'ثبت ورود خودرو' : 'تخصیص خدمات و پرسنل' }}</h2>
          </div>
          <button class="close-btn" @click="closeVehicleModal">✕</button>
        </header>

        <VehicleEntryStepOne
          v-if="modalStep === 1"
          :vehicle-info="vehicleDraft"
          @continue="handleStepOneContinue"
          @refer="handleStepOneRefer"
        />
        <VehicleEntryStepTwo
          v-else
          :vehicle-info="vehicleDraft"
          @back="modalStep = 1"
          @refer="handleStepTwoRefer"
          @assign="handleStepTwoAssign"
        />
      </section>
    </div>

    <div v-if="showVehicleDetailsModal" class="modal-overlay" @click.self="closeVehicleDetails">
      <section class="modal-panel details-panel">
        <header class="modal-head">
          <div>
            <p class="modal-step">جزئیات کامل خودرو</p>
            <h2>{{ selectedVehicle?.car_model || '-' }} - {{ selectedVehicle?.car_color || '-' }}</h2>
          </div>
          <button class="close-btn" @click="closeVehicleDetails">✕</button>
        </header>

        <div v-if="selectedVehicle" class="details-grid">
          <section class="details-card full summary-strip">
            <div class="summary-kpi">
              <span>وضعیت خودرو</span>
              <strong>{{ formatStatus(selectedVehicle.status) }}</strong>
            </div>
            <div class="summary-kpi">
              <span>وضعیت پرداخت</span>
              <strong>{{ formatPaymentStatus(selectedVehicle.payment_status) }}</strong>
            </div>
            <div class="summary-kpi">
              <span>جمع خدمات</span>
              <strong>{{ formatMoney(selectedVehicle.job?.services_total) }}</strong>
            </div>
            <div class="summary-kpi">
              <span>مبلغ نهایی</span>
              <strong>{{ formatMoney(selectedVehicle.job?.final_total) }}</strong>
            </div>
          </section>

          <section class="details-card">
            <h3>مشخصات خودرو</h3>
            <div class="info-grid">
              <p><span>پلاک</span><strong>{{ selectedVehicle.plate_number || '-' }}</strong></p>
              <p><span>مدل</span><strong>{{ selectedVehicle.car_model || '-' }}</strong></p>
              <p><span>رنگ</span><strong>{{ selectedVehicle.car_color || '-' }}</strong></p>
              <p><span>زمان ورود</span><strong>{{ formatDateTime(selectedVehicle.check_in_at) }}</strong></p>
            </div>
          </section>

          <section class="details-card">
            <h3>راننده و پذیرش</h3>
            <div class="info-grid">
              <p><span>نام راننده</span><strong>{{ selectedVehicle.driver_name || '-' }}</strong></p>
              <p><span>شماره راننده</span><strong>{{ selectedVehicle.driver_phone || '-' }}</strong></p>
              <p><span>ایجاد</span><strong>{{ formatDateTime(selectedVehicle.created_at) }}</strong></p>
              <p><span>آخرین بروزرسانی</span><strong>{{ formatDateTime(selectedVehicle.updated_at) }}</strong></p>
            </div>
            <div class="note-box">{{ selectedVehicle.notes || 'بدون توضیحات' }}</div>
          </section>

          <section class="details-card full">
            <h3>اطلاعات تخصیص و مالی</h3>
            <div class="info-grid four">
              <p><span>پرسنل تخصیص</span><strong>{{ selectedVehicle.job?.assigned_worker_name || 'تخصیص نشده' }}</strong></p>
              <p><span>نوع سهم</span><strong>{{ selectedVehicle.job?.worker_payment_type === 'fixed' ? 'ثابت' : 'درصدی' }}</strong></p>
              <p><span>درصد سهم</span><strong>{{ formatPercent(selectedVehicle.job?.worker_payment_percent) }}</strong></p>
              <p><span>سهم ثابت</span><strong>{{ formatMoney(selectedVehicle.job?.worker_payment_fixed) }}</strong></p>
              <p><span>سهم پرسنل</span><strong>{{ formatMoney(selectedVehicle.job?.worker_share_amount) }}</strong></p>
              <p><span>سهم کارواش</span><strong>{{ formatMoney(selectedVehicle.job?.carwash_share_amount) }}</strong></p>
              <p><span>تخفیف</span><strong>{{ formatMoney(selectedVehicle.job?.discount_total) }}</strong></p>
              <p><span>مالیات</span><strong>{{ formatMoney(selectedVehicle.job?.tax_total) }}</strong></p>
            </div>
          </section>

          <section class="details-card full">
            <h3>خدمات ثبت‌شده</h3>
            <div v-if="selectedVehicle.job?.service_lines?.length" class="detail-list">
              <div v-for="line in selectedVehicle.job.service_lines" :key="line.id" class="detail-list-item service-item">
                <div>
                  <span class="service-title">{{ line.service_name }}</span>
                  <small>تعداد: {{ Number(line.quantity || 1).toLocaleString('fa-IR') }}</small>
                </div>
                <strong>{{ formatMoney(line.line_total) }}</strong>
              </div>
            </div>
            <p v-else class="empty-row">خدمتی ثبت نشده است.</p>
          </section>

          <section class="details-card full">
            <h3>تاریخچه وضعیت</h3>
            <div v-if="selectedVehicle.status_logs?.length" class="detail-list">
              <div v-for="log in selectedVehicle.status_logs" :key="log.id" class="detail-list-item">
                <span>{{ formatStatus(log.from_status) }} ← {{ formatStatus(log.to_status) }}</span>
                <strong>{{ formatDateTime(log.changed_at) }}</strong>
              </div>
            </div>
            <p v-else class="empty-row">لاگ وضعیتی ثبت نشده است.</p>
          </section>
        </div>
      </section>
    </div>
    <div v-if="showReleaseModal" class="modal-overlay" @click.self="closeReleaseModal">
      <section class="modal-panel release-panel">
        <header class="modal-head">
          <div>
            <p class="modal-step">ترخیص خودرو</p>
            <h2>اتمام کار و فروش محصولات</h2>
          </div>
          <button class="close-btn" @click="closeReleaseModal">✕</button>
        </header>
        <div v-if="releaseCheckoutLoading" class="release-loading">
          <p>در حال بارگذاری اطلاعات ترخیص...</p>
        </div>
        <div v-else class="release-layout">
          <div class="release-col">
            <div class="release-title">
              <h3>تایید خدمات</h3>
            </div>
            <div class="release-list">
              <article v-for="line in releaseForm.serviceLines" :key="line.id" class="service-check-item">
                <div>
                  <h4>{{ line.service_name }}</h4>
                  <p>تعداد: {{ Number(line.quantity || 0).toLocaleString('fa-IR') }}</p>
                </div>
                <div class="service-check-action">
                  <span>{{ formatMoney(line.line_total) }}</span>
                  <label>
                    <input
                      v-model="line.is_completed"
                      type="checkbox"
                    />
                    انجام شد
                  </label>
                </div>
              </article>
            </div>
            
          </div>

          <div class="release-col release-products-col">
            <div class="release-title">
              <h3>محصولات جانبی</h3>
            </div>
            <div class="release-product-search">
              <input v-model="releaseForm.productSearch" type="text" placeholder="جستجوی محصول..." />
            </div>
            <div class="release-list products-scroll">
              <article
                v-for="product in filteredReleaseProducts"
                :key="product.id"
                class="product-item"
                :class="{ unavailable: Number(product.available_quantity || 0) <= 0 }"
              >
                <div>
                  <h4>{{ product.name }}</h4>
                  <p :class="{ 'stock-empty': Number(product.available_quantity || 0) <= 0 }">
                    موجودی: {{ Number(product.available_quantity || 0).toLocaleString('fa-IR') }}
                  </p>
                  <span>{{ formatMoney(product.sale_price) }}</span>
                </div>
                <div class="qty-controls">
                  <button type="button" @click="decreaseReleaseProduct(product.id)">-</button>
                  <input
                    type="number"
                    min="0"
                    :max="Number(product.available_quantity || 0)"
                    :value="getReleaseProductQty(product.id)"
                    @input="setReleaseProductQty(product.id, $event.target.value)"
                  />
                  <button
                    type="button"
                    @click="increaseReleaseProduct(product.id)"
                    :disabled="Number(product.available_quantity || 0) <= Number(getReleaseProductQty(product.id))"
                  >
                    +
                  </button>
                </div>
              </article>
            </div>
          </div>

          <div class="release-col release-summary-col">
            <div class="release-title">
              <h3>خلاصه نهایی</h3>
            </div>
            <div class="summary-rows">
              <p><span>جمع خدمات</span><strong>{{ formatMoney(releaseSummary.servicesTotal) }}</strong></p>
              <p><span>جمع محصولات</span><strong>{{ formatMoney(releaseSummary.productsTotal) }}</strong></p>
              <p><span>انعام</span><strong>{{ formatMoney(releaseSummary.tipAmount) }}</strong></p>
              <p><span>جمع قابل تسهیم</span><strong>{{ formatMoney(releaseSummary.shareBaseTotal) }}</strong></p>
              <p class="summary-final"><span>جمع کل</span><strong>{{ formatMoney(releaseSummary.finalTotal) }}</strong></p>
            </div>
            <div class="summary-inputs">
              <label>
                <span>انعام (هزار تومان)</span>
                <input v-model.number="releaseForm.tipAmount" type="number" min="0" />
              </label>
            </div>
            <div class="summary-share">
              <p><span>سهم نیرو</span><strong>{{ formatMoney(releaseSummary.workerShare) }}</strong></p>
              <p><span>سهم کارواش</span><strong>{{ formatMoney(releaseSummary.carwashShare) }}</strong></p>
            </div>
            <label class="mark-paid forced-paid">
              <input type="checkbox" checked disabled />
              <span>در ترخیص، پرداخت به‌صورت خودکار کامل ثبت می‌شود</span>
            </label>
            <div class="release-actions">
              <button type="button" class="back-btn" @click="closeReleaseModal">انصراف</button>
              <button type="button" class="confirm-release-btn" :disabled="releaseSubmitting" @click="confirmReleaseVehicle">
                {{ releaseSubmitting ? 'در حال ثبت...' : 'تایید و ترخیص خودرو' }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../../store/auth.store'
import VehicleEntryStepOne from '../../components/operator/VehicleEntryStepOne.vue'
import VehicleEntryStepTwo from '../../components/operator/VehicleEntryStepTwo.vue'
import { useVehicleStore } from '../../store/vehicle.store'
import api from '../../services/api'

const search = ref('')
const activeFilter = ref('all')
const showVehicleModal = ref(false)
const showVehicleDetailsModal = ref(false)
const showReleaseModal = ref(false)
const releaseCheckoutLoading = ref(false)
const releaseSubmitting = ref(false)
const modalStep = ref(1)
const vehicleDraft = ref(null)
const releaseCandidate = ref(null)
const releaseForm = ref({
  serviceLines: [],
  availableProducts: [],
  productLinesByProductId: {},
  productSearch: '',
  tipAmount: 0,
  workerShareAmount: 0
})
const route = useRoute()
const authStore = useAuthStore()
const vehicleStore = useVehicleStore()
const { vehicles, selectedVehicle } = storeToRefs(vehicleStore)

const openVehicleModal = () => {
  modalStep.value = 1
  vehicleDraft.value = null
  showVehicleModal.value = true
}
const closeVehicleModal = () => {
  showVehicleModal.value = false
  modalStep.value = 1
  vehicleDraft.value = null
}
const openVehicleDetails = async (vehicleId) => {
  try {
    const { data } = await api.get(`/vehicles/${vehicleId}/`)
    vehicleStore.selectedVehicle = data
    showVehicleDetailsModal.value = true
  } catch (error) {
    console.error('fetchVehicleDetail error:', error?.response?.data || error)
    alert('بارگذاری جزئیات خودرو ناموفق بود.')
  }
}
const closeVehicleDetails = () => {
  showVehicleDetailsModal.value = false
}
const formatStatus = (value) => ({
  entered: 'وارد شده',
  assigned: 'تخصیص داده شده',
  in_progress: 'در حال انجام',
  ready_to_settle: 'آماده تسویه',
  released: 'تحویل شده',
  cancelled: 'لغو شده'
}[value] || '-')
const formatPaymentStatus = (value) => ({
  unpaid: 'پرداخت نشده',
  partial: 'پرداخت ناقص',
  paid: 'پرداخت کامل',
  refunded: 'مرجوع شده'
}[value] || '-')
const formatMoney = (value) => `${Number(value || 0).toLocaleString('fa-IR')} تومان`
const formatPercent = (value) => `${Number(value || 0).toLocaleString('fa-IR')}٪`
const formatDateTime = (value) => {
  if (!value) return '-'
  return new Intl.DateTimeFormat('fa-IR', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}
const handleCardAction = async (car) => {
  if (car.statusKey === 'released') return
  if (car.statusKey === 'ready_to_settle') {
    await openReleaseModal(car)
    return
  }
  const source = vehicleStore.vehicles.find((item) => item.id === car.id)
  if (!source) return
  vehicleDraft.value = {
    id: source.id,
    plate: source.plate_number,
    plate_left: source.plate_left,
    plate_letter: source.plate_letter,
    plate_mid: source.plate_mid,
    plate_right: source.plate_right,
    model: source.car_model,
    color: source.car_color,
    driver: source.driver_name,
    mobile: source.driver_phone,
    note: source.notes,
    serviceIds: Array.isArray(source.job?.service_lines) ? source.job.service_lines.map((s) => s.service) : [],
    staffId: source.job?.assigned_worker || null
  }
  modalStep.value = car.statusKey === 'entered' ? 1 : 2
  showVehicleModal.value = true
}
const closeReleaseModal = () => {
  showReleaseModal.value = false
  releaseCandidate.value = null
  releaseCheckoutLoading.value = false
  releaseSubmitting.value = false
  releaseForm.value = {
    serviceLines: [],
    availableProducts: [],
    productLinesByProductId: {},
    productSearch: '',
    tipAmount: 0,
    workerShareAmount: 0
  }
}
const openReleaseModal = async (car) => {
  releaseCandidate.value = car
  showReleaseModal.value = true
  releaseCheckoutLoading.value = true
  try {
    const { data } = await api.get(`/vehicles/${car.id}/release/`)
    const serviceLines = Array.isArray(data?.job?.service_lines)
      ? data.job.service_lines.map((line) => ({
        id: line.id,
        service_name: line.service_name,
        quantity: Number(line.quantity || 0),
        line_total: Number(line.line_total || 0),
        is_completed: Boolean(line.is_completed)
      }))
      : []
    const availableProducts = Array.isArray(data?.job?.available_products)
      ? data.job.available_products.map((item) => ({
        id: item.id,
        name: item.name,
        sku: item.sku,
        sale_price: Number(item.sale_price || 0),
        available_quantity: Number(item.available_quantity || 0),
        selected_quantity: Number(item.selected_quantity || 0)
      }))
      : []
    const productLinesByProductId = {}
    availableProducts.forEach((item) => {
      if (item.selected_quantity > 0) productLinesByProductId[item.id] = item.selected_quantity
    })
    releaseForm.value = {
      serviceLines,
      availableProducts,
      productLinesByProductId,
      productSearch: '',
      tipAmount: Number(data?.job?.tip_amount || 0),
      workerShareAmount: Number(data?.job?.worker_share_amount || 0)
    }
  } catch (error) {
    console.error('openReleaseModal error:', error?.response?.data || error)
    alert('بارگذاری اطلاعات ترخیص ناموفق بود.')
    closeReleaseModal()
  } finally {
    releaseCheckoutLoading.value = false
  }
}
const getReleaseProductQty = (productId) => Number(releaseForm.value.productLinesByProductId[productId] || 0)
const increaseReleaseProduct = (productId) => {
  const product = releaseForm.value.availableProducts.find((item) => item.id === productId)
  if (!product) return
  const current = getReleaseProductQty(productId)
  if (current >= Number(product.available_quantity || 0)) return
  releaseForm.value.productLinesByProductId[productId] = current + 1
}
const decreaseReleaseProduct = (productId) => {
  const current = getReleaseProductQty(productId)
  if (current <= 0) return
  const next = current - 1
  if (next === 0) {
    delete releaseForm.value.productLinesByProductId[productId]
    return
  }
  releaseForm.value.productLinesByProductId[productId] = next
}
const setReleaseProductQty = (productId, rawValue) => {
  const product = releaseForm.value.availableProducts.find((item) => item.id === productId)
  if (!product) return
  const maxQty = Math.max(0, Number(product.available_quantity || 0))
  const parsed = Math.floor(Number(rawValue || 0))
  const nextQty = Number.isFinite(parsed) ? Math.max(0, Math.min(maxQty, parsed)) : 0
  if (nextQty <= 0) {
    delete releaseForm.value.productLinesByProductId[productId]
    return
  }
  releaseForm.value.productLinesByProductId[productId] = nextQty
}
const filteredReleaseProducts = computed(() => {
  const items = releaseForm.value.availableProducts || []
  const query = (releaseForm.value.productSearch || '').trim()
  if (!query) return items
  return items.filter((item) => `${item.name || ''} ${item.sku || ''}`.includes(query))
})
const releaseSummary = computed(() => {
  const servicesTotal = releaseForm.value.serviceLines.reduce((sum, line) => (
    line.is_completed ? sum + Number(line.line_total || 0) : sum
  ), 0)
  const productsTotal = releaseForm.value.availableProducts.reduce((sum, product) => {
    const qty = getReleaseProductQty(product.id)
    return sum + (qty * Number(product.sale_price || 0))
  }, 0)
  const tipAmount = Math.max(0, Number(releaseForm.value.tipAmount || 0) * 1000)
  const shareBaseTotal = Math.max(0, servicesTotal)
  const finalTotal = shareBaseTotal + tipAmount
  const workerShare = Math.min(shareBaseTotal, Number(releaseForm.value.workerShareAmount || 0))
  const carwashShare = Math.max(0, shareBaseTotal - workerShare)
  const finalTotalWithProducts = Math.max(0, servicesTotal + productsTotal + tipAmount)
  return {
    servicesTotal,
    productsTotal,
    tipAmount,
    shareBaseTotal,
    finalTotal: finalTotalWithProducts,
    workerShare,
    carwashShare
  }
})
const confirmReleaseVehicle = async () => {
  if (!releaseCandidate.value?.id) return
  try {
    releaseSubmitting.value = true
    const service_lines = releaseForm.value.serviceLines.map((line) => ({
      id: line.id,
      is_completed: Boolean(line.is_completed)
    }))
    const product_lines = releaseForm.value.availableProducts
      .map((product) => ({
        product_id: product.id,
        quantity: getReleaseProductQty(product.id)
      }))
    const { data } = await api.patch(`/vehicles/${releaseCandidate.value.id}/release/`, {
      service_lines,
      product_lines,
      tip_amount: Math.max(0, Number(releaseForm.value.tipAmount || 0) * 1000)
    })
    const idx = vehicleStore.vehicles.findIndex((item) => item.id === releaseCandidate.value.id)
    if (idx >= 0) vehicleStore.vehicles[idx] = data
    closeReleaseModal()
  } catch (error) {
    console.error('confirmReleaseVehicle error:', error?.response?.data || error)
    alert('ترخیص خودرو ناموفق بود.')
  } finally {
    releaseSubmitting.value = false
  }
}
const handleStepOneContinue = (payload) => {
  vehicleDraft.value = payload
  modalStep.value = 2
}
const buildCreateOrUpdatePayload = (payload, status) => {
  const plateRaw = (payload?.vehicle?.plate || '').trim()
  const [leftPart = '', letterPart = '', midPart = '', rightPart = ''] = plateRaw.split(/\s+/).filter(Boolean)
  const left = String(payload?.vehicle?.plateLeft || payload?.vehicle?.plate_left || leftPart || '').trim()
  const letter = String(payload?.vehicle?.plateLetter || payload?.vehicle?.plate_letter || letterPart || '').trim()
  const mid = String(payload?.vehicle?.plateMid || payload?.vehicle?.plate_mid || midPart || '').trim()
  const right = String(payload?.vehicle?.plateRight || payload?.vehicle?.plate_right || rightPart || '').trim()
  const rebuiltPlate = [left, letter, mid, right].every(Boolean)
    ? `${left} ${letter} ${mid} ${right}`
    : plateRaw

  return {
    plate_number: rebuiltPlate,
    plate_left: left,
    plate_letter: letter,
    plate_mid: mid,
    plate_right: right,
    car_model: (payload?.vehicle?.model || '').trim(),
    car_color: (payload?.vehicle?.color || '').trim(),
    driver_name: (payload?.vehicle?.driver || '').trim(),
    driver_phone: (payload?.vehicle?.mobile || '').trim(),
    notes: (payload?.vehicle?.note || '').trim(),
    status,
    worker_id: payload?.staff?.id || null,
    worker_name: payload?.staff?.name || '',
    services: payload?.services || [],
    share: payload?.share || {}
  }
}

const saveVehicle = async (payload, status) => {
  const body = buildCreateOrUpdatePayload(payload, status)
  const editingId = payload?.vehicle?.id || vehicleDraft.value?.id || null
  if (editingId) {
    const { data } = await api.patch(`/vehicles/${editingId}/`, body)
    const idx = vehicleStore.vehicles.findIndex((item) => item.id === editingId)
    if (idx >= 0) vehicleStore.vehicles[idx] = data
    return data
  }
  return vehicleStore.createVehicle(body)
}

const handleStepOneRefer = async (payload) => {
  try {
    await saveVehicle({ vehicle: payload }, 'entered')
    closeVehicleModal()
  } catch (error) {
    console.error('refer step one error:', error?.response?.data || error)
    alert('ثبت ارجاع ناموفق بود.')
  }
}

const handleStepTwoRefer = async (payload) => {
  try {
    await saveVehicle(payload, 'entered')
    closeVehicleModal()
  } catch (error) {
    console.error('refer step two error:', error?.response?.data || error)
    alert('ثبت ارجاع ناموفق بود.')
  }
}

const handleStepTwoAssign = async (payload) => {
  try {
    await saveVehicle(payload, 'ready_to_settle')
    closeVehicleModal()
  } catch (error) {
    console.error('assign step two error:', error?.response?.data || error)
    alert('ثبت تخصیص ناموفق بود.')
  }
}
const cars = computed(() => vehicles.value.map((item) => ({
  id: item.id,
  statusKey: item.status,
  status: item.status === 'assigned' ? 'تخصیص داده شده' : item.status === 'in_progress' ? 'در حال انجام' : item.status === 'ready_to_settle' ? 'آماده ترخیص' : item.status === 'released' ? 'ترخیص شده' : 'ارجاع شده',
  color: item.status === 'assigned'
    ? '#0058be'
    : item.status === 'in_progress'
      ? '#0058be'
      : item.status === 'ready_to_settle'
        ? '#10b981'
        : item.status === 'released'
          ? '#f59e0b'
          : '#16a34a',
  badgeBg: '#eef2ff',
  badgeText: '#334155',
  time: 'از دیتابیس',
  plateTwoDigit: item.plate_left || '--',
  plateLetter: item.plate_letter || '-',
  plateThreeDigit: item.plate_mid || '---',
  plateBlue: item.plate_right || '--',
  model: item.car_model,
  colorName: item.car_color,
  plateDisplay: item.plate_number || '-',
  service: 'بر اساس خدمات ثبت‌شده',
  driverName: item.driver_name,
  driverPhone: item.driver_phone,
  finalTotal: item.job?.final_total || item.job?.services_total || 0,
  carwashShare: item.job?.carwash_share_amount || 0,
  workerName: item.status === 'assigned' ? 'تخصیص انجام شده' : 'تخصیص نشده',
  action: item.status === 'released' ? 'ترخیص انجام شد' : item.status === 'ready_to_settle' ? 'ترخیص خودرو' : 'تکمیل اطلاعات',
  actionClass: item.status === 'ready_to_settle' ? 'action-release' : item.status === 'released' ? 'action-done' : 'action-complete'
})))

const counts = computed(() => {
  const data = { entered: 0, in_progress: 0, released: 0, ready_to_settle: 0 }
  cars.value.forEach((item) => {
    if (Object.prototype.hasOwnProperty.call(data, item.statusKey)) data[item.statusKey] += 1
  })
  return data
})

const filterItems = computed(() => [
  { key: 'all', label: `همه خودروها (${cars.value.length})` },
  { key: 'entered', label: `وارد شده (${counts.value.entered})` },
  { key: 'in_progress', label: `در حال انجام (${counts.value.in_progress})` },
  { key: 'released', label: `تحویل شده (${counts.value.released})` },
  { key: 'ready_to_settle', label: `آماده تسویه (${counts.value.ready_to_settle})` }
])

const filteredCars = computed(() => {
  let items = cars.value
  if (activeFilter.value !== 'all') items = items.filter((item) => item.statusKey === activeFilter.value)
  if (!search.value.trim()) return items
  const query = search.value.trim()
  items = items.filter((item) => [item.plateTwoDigit, item.plateLetter, item.plateThreeDigit, item.plateBlue, item.model, item.driverName, item.driverPhone].join(' ').includes(query))
  return [...items].sort((first, second) => {
    const firstWeight = first.statusKey === 'released' ? 1 : 0
    const secondWeight = second.statusKey === 'released' ? 1 : 0
    return firstWeight - secondWeight
  })
})

onMounted(() => {
  vehicleStore.fetchVehicles()
})
</script>

<style scoped>
.dashboard-page { min-height: 100vh; background: #f7f9fb; font-family: Vazirmatn, sans-serif; color: #191c1e; }
.topbar { position: sticky; top: 0; z-index: 10; height: 64px; display: flex; justify-content: space-between; align-items: center; padding: 0 24px; background: rgba(255,255,255,.86); backdrop-filter: blur(12px); border-bottom: 1px solid #e3e6ed; }
.topbar-left,.topbar-right { display: flex; align-items: center; gap: 12px; }
.brand { color: #0058be; font-weight: 700; }
.search-box input { width: 260px; height: 40px; border: none; border-radius: 12px; background: #f2f4f6; padding: 0 12px; }
.search-box input:focus { outline: 2px solid #0058be; }
.primary-btn { height: 40px; border: none; border-radius: 12px; color: #fff; font-weight: 700; padding: 0 16px; background: linear-gradient(135deg, #0058be 0%, #57dffe 100%); cursor: pointer; }
.profile-name { margin: 0; font-size: 13px; font-weight: 700; }
.layout { display: flex; }
.sidebar { width: 240px; min-height: calc(100vh - 64px); padding: 24px 12px; background: #f2f4f6; border-left: 1px solid #e3e6ed; }
.menu-item { display: block; padding: 12px 14px; border-radius: 12px; text-decoration: none; color: #475569; font-weight: 600; }
.menu-item.active { background: #dbeafe; color: #0058be; }
.content { flex: 1; padding: 24px; }
.filters { display: flex; gap: 10px; overflow: auto; padding-bottom: 8px; }
.chip { border: none; border-radius: 999px; padding: 10px 16px; background: #e6e8ea; color: #4b5563;font-size:13px; font-weight: 500; white-space: nowrap; }
.chip.active { background: #0058be; color: #fff; }
.cards-grid { margin-top: 18px; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 20px; }
.car-card { background: #fff; border-right: 4px solid #0058be; border-radius: 16px; padding: 16px; box-shadow: 0 14px 30px -10px rgba(15,23,42,.12); display: flex; flex-direction: column; gap: 12px; transition: transform .2s ease, box-shadow .2s ease; }
.car-card:hover { transform: translateY(-3px); box-shadow: 0 20px 34px -14px rgba(15,23,42,.16); }
.car-card.card-released { opacity: .58; filter: grayscale(.2); }
.car-card.card-released:hover { transform: none; box-shadow: 0 14px 30px -10px rgba(15,23,42,.12); }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.status { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: #475569; }
.dot { width: 8px; height: 8px; border-radius: 99px; }
.time { font-size: 10px; padding: 4px 9px; border-radius: 999px; font-weight: 700; }
.plate-box { border-radius: 12px; padding: 10px; display: flex; align-items: stretch; justify-content: center; direction: ltr; overflow: hidden; }
.plate-white-wrap { display: flex; align-items: center; gap: 10px; background: #6f59ef18; color: #111827; border-radius: 7px 0 0 7px; padding: 4px 12px; }
.plate-part { display: inline-flex; align-items: center; justify-content: center; line-height: 1; }
.plate-two, .plate-three { font-size: 24px; font-weight: 700; height: 40px; padding-top: 12px; padding-bottom: 8px; }
.plate-letter { font-size: 24px; font-weight: 700; min-width: 20px; padding-top: 2px; }
.plate-blue { min-width: 52px; background: #2563eb; color: #ffffff; border-radius: 0 7px 7px 0; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 24px; line-height: 1; padding-top: 12px; padding-bottom: 8px; }
.car-info h3 { margin: 0 0 6px; font-size: 15px; }
.car-info p { margin: 3px 0; font-size: 13px; color: #64748b; }
.card-action { margin-top: auto; height: 42px; border: none; border-radius: 12px; font-weight: 700; }
.card-action.action-complete { background: #d0fadf; color: #166534; }
.card-action.action-release { background: #fef3c7; color: #92850e; }
.card-action.action-done { background: #e5e7eb; color: #374151; }
.card-passive-state { margin-top: auto; height: 42px; border-radius: 12px; border: 1px dashed #cbd5e1; color: #64748b; background: #f8fafc; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.release-panel { width: min(1380px, 100%); }
.release-loading { min-height: 280px; display: flex; align-items: center; justify-content: center; color: #64748b; font-size: 14px; }
.release-layout { padding: 24px; display: grid; gap: 20px; grid-template-columns: repeat(3, minmax(0, 1fr)); background: #f7f9fb; }
.release-col { background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 16px; display: flex; flex-direction: column; min-height: 620px; }
.release-products-col, .release-summary-col { border-right: 1px solid #e2e8f0; }
.release-title { padding-bottom: 10px; border-bottom: 1px solid #e2e8f0; margin-bottom: 12px; }
.release-title h3 { margin: 0; font-size: 20px; color: #111827; }
.release-list { display: grid; gap: 10px; overflow: auto; }
.service-check-item { border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; display: flex; justify-content: space-between; gap: 12px; background: #f8fbff; }
.service-check-item h4 { margin: 0 0 4px; font-size: 15px; color: #0f172a; }
.service-check-item p { margin: 0; font-size: 12px; color: #64748b; }
.service-check-action { display: grid; justify-items: end; gap: 8px; align-content: center; }
.service-check-action span { font-size: 13px; font-weight: 700; color: #0058be; }
.service-check-action label { font-size: 12px; color: #475569; display: inline-flex; align-items: center; gap: 6px; }
.release-secondary-btn { margin-top: auto; border: 1px solid #cbd5e1; border-radius: 12px; height: 44px; background: #f8fafc; font-weight: 700; color: #0f172a; cursor: pointer; }
.release-product-search { margin-bottom: 10px; }
.release-product-search input { width: 100%; height: 42px; border: 1px solid #cbd5e1; border-radius: 12px; padding: 0 12px; }
.products-scroll { max-height: 520px; padding-right: 4px; }
.product-item { border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; display: flex; justify-content: space-between; align-items: center; background: #fff; }
.product-item h4 { margin: 0 0 4px; font-size: 14px; color: #111827; }
.product-item p { margin: 0; font-size: 12px; color: #64748b; }
.product-item span { font-size: 13px; color: #00687a; font-weight: 700; }
.product-item.unavailable { opacity: .55; }
.product-item p.stock-empty { color: #ba1a1a; }
.qty-controls { display: inline-flex; align-items: center; gap: 10px; border: 1px solid #e2e8f0; border-radius: 10px; padding: 4px 6px; background: #f8fafc; }
.qty-controls button { width: 28px; height: 28px; border: 1px solid #dbe3ef; border-radius: 8px; background: #fff; cursor: pointer; }
.qty-controls button:disabled { opacity: .45; cursor: not-allowed; }
.qty-controls input { width: 72px; height: 28px; border: 1px solid #dbe3ef; border-radius: 8px; text-align: center; background: #fff; }
.summary-rows { display: grid; gap: 10px; }
.summary-rows p { margin: 0; display: flex; justify-content: space-between; font-size: 14px; color: #475569; }
.summary-rows p strong { color: #0f172a; }
.summary-rows p.summary-final { border-top: 1px solid #e2e8f0; padding-top: 12px; margin-top: 4px; font-size: 18px; font-weight: 800; color: #111827; }
.summary-inputs { margin-top: 14px; display: grid; gap: 10px; }
.summary-inputs label { display: grid; gap: 6px; }
.summary-inputs span { color: #64748b; font-size: 12px; }
.summary-inputs input { height: 40px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 0 10px; }
.summary-share { margin-top: 12px; border: 1px dashed #cbd5e1; border-radius: 12px; padding: 10px; background: #f8fafc; display: grid; gap: 8px; }
.summary-share p { margin: 0; display: flex; justify-content: space-between; font-size: 13px; color: #334155; }
.mark-paid { margin-top: 12px; display: inline-flex; align-items: center; gap: 8px; color: #334155; font-size: 13px; }
.mark-paid.forced-paid { opacity: .85; }
.release-actions { margin-top: auto; padding-top: 14px; display: flex; gap: 8px; }
.back-btn { flex: 1; height: 44px; border: 1px solid #cbd5e1; border-radius: 12px; background: #fff; color: #334155; font-weight: 700; cursor: pointer; }
.confirm-release-btn { flex: 1; height: 44px; border: none; border-radius: 12px; font-weight: 700; color: #92850e; background: #fef3c7; cursor: pointer; }
.confirm-release-btn:disabled { opacity: .65; cursor: not-allowed; }
.modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, .35); backdrop-filter: blur(3px); z-index: 60; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal-panel { width: min(1280px, 100%); max-height: calc(100vh - 40px); background: #fff; border-radius: 20px; overflow: auto; box-shadow: 0 24px 60px -20px rgba(15,23,42,.4); }
.modal-head { padding: 18px 22px; border-bottom: 1px solid #e3e6ed; display: flex; align-items: center; justify-content: space-between; }
.modal-head h2 { margin: 0; font-size: 22px; }
.modal-step { margin: 0 0 6px; color: #64748b; font-size: 12px; }
.close-btn { width: 38px; height: 38px; border: 1px solid #dbe3ef; border-radius: 10px; background: #fff; cursor: pointer; }
.details-panel { width: min(1100px, 100%); }
.details-grid { padding: 18px 22px 24px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.details-card { border: 1px solid #e2e8f0; border-radius: 16px; padding: 16px; background: #fff; }
.details-card h3 { margin: 0 0 10px; font-size: 16px; }
.details-card.full { grid-column: 1 / -1; }
.summary-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; background: linear-gradient(90deg, #f8fbff, #eef4ff); }
.summary-kpi { border: 1px solid #dbeafe; border-radius: 12px; padding: 10px; display: grid; gap: 4px; }
.summary-kpi span { color: #64748b; font-size: 12px; }
.summary-kpi strong { color: #0f172a; font-size: 15px; }
.info-grid { display: grid; gap: 8px; }
.info-grid.four { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.info-grid p { margin: 0; border: 1px solid #e2e8f0; background: #f8fafc; border-radius: 10px; padding: 9px 10px; display: grid; gap: 4px; }
.info-grid p span { color: #64748b; font-size: 12px; }
.info-grid p strong { color: #0f172a; font-size: 13px; font-weight: 700; }
.note-box { margin-top: 10px; border: 1px dashed #cbd5e1; border-radius: 10px; padding: 10px; color: #334155; font-size: 13px; background: #f8fafc; }
.detail-list { display: grid; gap: 8px; }
.detail-list-item { border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; background: #fdfefe; }
.service-item { background: #f8fbff; }
.service-title { display: block; color: #0f172a; font-weight: 700; margin-bottom: 2px; }
.detail-list-item small { color: #64748b; font-size: 11px; }
.empty-row { margin: 0; color: #64748b; font-size: 13px; }
@media (max-width: 1400px) { .cards-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (max-width: 1100px) {
  .sidebar { display: none; }
  .cards-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .details-grid { grid-template-columns: 1fr; }
  .summary-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .info-grid.four { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .release-layout { grid-template-columns: 1fr; }
  .release-col { min-height: auto; }
}
@media (max-width: 768px) {
  .topbar { padding: 0 12px; }
  .search-box input { width: 170px; }
  .cards-grid { grid-template-columns: 1fr; }
  .content { padding: 14px; }
  .modal-overlay { padding: 8px; }
  .modal-panel { max-height: calc(100vh - 16px); border-radius: 14px; }
}
</style>
