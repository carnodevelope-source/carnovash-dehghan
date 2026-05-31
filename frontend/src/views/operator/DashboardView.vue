<template>
  <AppShell
    title="مدیریت خودروها"
    subtitle="پذیرش، تخصیص و ترخیص خودروها"
    :show-search="true"
    search-placeholder="جستجوی پلاک یا نام..."
    :search-query="search"
    @update:search-query="search = $event"
  >
    <div class="dashboard-content">
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
          <button class="primary-btn" @click="openVehicleModal">ثبت خودروی جدید</button>
        
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
              <p class="customer-score-row">
                <span>امتیاز مشتری:</span>
                <span class="star-track">
                  <span class="star-bg">★★★★★</span>
                  <span class="star-fill" :style="{ width: `${customerScorePercent(car.customerScore)}%` }">★★★★★</span>
                </span>
              </p>
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
    </div>
  </AppShell>

  <div v-if="showVehicleModal" class="modal-overlay" @click.self="closeVehicleModal">
      <section class="modal-panel" :class="{ 'step-one-modal-panel': modalStep === 1, 'step-two-modal-panel': modalStep === 2 }">
        <template v-if="modalStep === 1">
          <header class="modal-head">
            <div>
              <p class="modal-step">مرحله {{ modalStep }} از فرآیند پذیرش</p>
              <h2>ثبت ورود خودرو</h2>
            </div>
            <button class="close-btn" @click="closeVehicleModal">✕</button>
          </header>
          <VehicleEntryStepOne
            :vehicle-info="vehicleDraft"
            @continue="handleStepOneContinue"
            @refer="handleStepOneRefer"
          />
        </template>

        <VehicleEntryStepTwo
          v-else
          :vehicle-info="vehicleDraft"
          @back="modalStep = 1"
          @close="closeVehicleModal"
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
              <p><span>پرسنل تخصیص</span><strong>{{ assignedWorkersLabel(selectedVehicle.job) }}</strong></p>
              <p><span>نوع سهم</span><strong>{{ selectedVehicle.job?.worker_payment_type === 'fixed' ? 'ثابت' : 'درصدی' }}</strong></p>
              <p><span>درصد سهم</span><strong>{{ formatPercent(selectedVehicle.job?.worker_payment_percent) }}</strong></p>
              <p><span>سهم ثابت</span><strong>{{ formatMoney(selectedVehicle.job?.worker_payment_fixed) }}</strong></p>
              <p><span>سهم پرسنل</span><strong>{{ formatMoney(workerTotalWithTip(selectedVehicle.job)) }}</strong></p>
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
          <BaseSpinner size="66px" color="#1d4ed8" ball-color="#60a5fa" label="در حال بارگذاری اطلاعات ترخیص..." />
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
              <p v-if="!releaseForm.serviceLines.length" class="empty-row">خدمتی برای این خودرو ثبت نشده است.</p>
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
              <p><span>تخفیف مشتری ({{ formatPercent(releaseSummary.customerDiscountPercent) }})</span><strong>{{ formatMoney(releaseSummary.discountAmount) }}</strong></p>
              <p><span>جمع انعام</span><strong>{{ formatMoney(releaseSummary.tipAmount) }}</strong></p>
            </div>
            <label class="tip-input-row">
              <span>انعام (هزار تومان)</span>
              <input v-model.number="releaseForm.tipAmount" type="number" min="0" step="1" />
            </label>
            <div class="summary-share">
              <p
                v-for="(worker, index) in releaseSummary.workerShares"
                :key="`${worker.name || 'worker'}-${index}`"
              >
                <span>سهم {{ worker.name || `نیروی ${Number(index + 1).toLocaleString('fa-IR')}` }}</span>
                <strong>{{ formatMoney(worker.amount) }}</strong>
              </p>
              <p v-if="!releaseSummary.workerShares.length">
                <span>سهم نیرو</span>
                <strong>{{ formatMoney(0) }}</strong>
              </p>
              <p class="summary-share-total">
                <span>جمع سهم کارواش</span>
                <strong>{{ formatMoney(releaseSummary.carwashShare) }}</strong>
              </p>
            </div>
            <p class="summary-final"><span>جمع کل</span><strong>{{ formatMoney(releaseSummary.finalTotal) }}</strong></p>
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
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import VehicleEntryStepOne from '../../components/operator/VehicleEntryStepOne.vue'
import VehicleEntryStepTwo from '../../components/operator/VehicleEntryStepTwo.vue'
import BaseSpinner from '../../components/base/BaseSpinner.vue'
import AppShell from '../../components/layout/AppShell.vue'
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
  assignedWorkers: [],
  workerShareAmount: 0,
  customerScore: 0,
  discountPercentPerHalfStar: 0
})
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
const customerScorePercent = (score) => {
  const normalized = Math.max(0, Math.min(5, Number(score || 0)))
  return (normalized / 5) * 100
}
const formatCustomerScore = (score) => `${Number(score || 0).toLocaleString('fa-IR')} / ۵`
const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (d) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
  .replace(/\D/g, '')
const splitPlate = (rawPlate) => String(rawPlate || '').trim().split(/\s+/).filter(Boolean)
const mapVehicleToDraft = (source = {}) => ({
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
  staffId: source.job?.assigned_worker || null,
  staffIds: Array.isArray(source.job?.assigned_workers_snapshot)
    ? source.job.assigned_workers_snapshot
      .map((item) => Number(item?.id))
      .filter((id) => Number.isFinite(id) && id > 0)
    : []
})
const assignedWorkersLabel = (job) => {
  if (!job) return 'تخصیص نشده'
  const names = Array.isArray(job.assigned_workers_names)
    ? job.assigned_workers_names.filter((item) => String(item || '').trim().length > 0)
    : []
  if (names.length) return names.join('، ')
  return job.assigned_worker_name || 'تخصیص نشده'
}
const workerTotalWithTip = (job) => {
  if (!job) return 0
  return Number(job.worker_share_amount || 0) + Number(job.workers_tip_share_amount || 0)
}
const hasCompletedStepOneData = (source = {}) => {
  const plateParts = splitPlate(source.plate_number)
  const left = String(source.plate_left || plateParts[0] || '').trim()
  const letter = String(source.plate_letter || plateParts[1] || '').trim()
  const mid = String(source.plate_mid || plateParts[2] || '').trim()
  const right = String(source.plate_right || plateParts[3] || '').trim()
  const hasPlate = left.length === 2 && letter.length === 1 && mid.length === 3 && right.length === 2
  const hasModel = String(source.car_model || '').trim().length > 0
  const hasColor = String(source.car_color || '').trim().length > 0
  const hasPhone = normalizeDigits(source.driver_phone).length > 0
  return hasPlate && hasModel && hasColor && hasPhone
}
const handleCardAction = async (car) => {
  if (car.statusKey === 'released') return
  if (car.statusKey === 'ready_to_settle') {
    await openReleaseModal(car)
    return
  }
  const source = vehicleStore.vehicles.find((item) => item.id === car.id)
  if (!source) return
  vehicleDraft.value = mapVehicleToDraft(source)
  modalStep.value = (car.statusKey === 'entered' && !hasCompletedStepOneData(source)) ? 1 : 2
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
    assignedWorkers: [],
    workerShareAmount: 0,
    customerScore: 0,
    discountPercentPerHalfStar: 0
  }
}
const openReleaseModal = async (car) => {
  releaseCandidate.value = car
  showReleaseModal.value = true
  releaseCheckoutLoading.value = true
  try {
    const [releaseResponse, settingsResponse] = await Promise.all([
      api.get(`/vehicles/${car.id}/release/`),
      api.get('/services/general-settings/').catch(() => ({ data: { discount_percent_per_half_star: 0 } }))
    ])
    const data = releaseResponse.data
    const discountPercentPerHalfStar = Math.max(
      0,
      Number(
        settingsResponse?.data?.discount_percent_per_half_star
        ?? data?.job?.discount_percent_per_half_star
        ?? 0
      )
    )
    const serviceLines = Array.isArray(data?.job?.service_lines)
      ? data.job.service_lines.map((line) => ({
        id: line.id,
        service_name: line.service_name,
        quantity: Number(line.quantity || 0),
        line_total: Number(line.line_total || 0),
        is_completed: true
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
      tipAmount: Math.max(0, Number(data?.job?.tip_amount || 0) / 1000),
      assignedWorkers: Array.isArray(data?.job?.assigned_workers)
        ? data.job.assigned_workers
          .map((item) => ({
            id: Number(item?.id || 0),
            name: String(item?.name || '').trim(),
            tip_share_percent: Number(item?.tip_share_percent || 0)
          }))
          .filter((item) => item.id > 0 && item.name.length > 0)
        : (Array.isArray(data?.job?.assigned_workers_names)
          ? data.job.assigned_workers_names
            .filter((item) => String(item || '').trim().length > 0)
            .map((name, index) => ({
              id: index + 1,
              name: String(name || '').trim(),
              tip_share_percent: 0
            }))
          : []),
      workerShareAmount: Number(data?.job?.worker_share_amount || 0),
      customerScore: Math.max(0, Number(data?.vehicle?.customer_score || releaseCandidate.value?.customerScore || 0)),
      discountPercentPerHalfStar
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
  const customerScore = Math.max(0, Math.min(5, Number(releaseForm.value.customerScore || 0)))
  const discountPercentPerHalfStar = Math.max(0, Number(releaseForm.value.discountPercentPerHalfStar || 0))
  const customerDiscountPercent = Math.max(0, Math.min(100, Number((discountPercentPerHalfStar * customerScore * 2).toFixed(2))))
  const discountBase = Math.max(0, servicesTotal + productsTotal)
  const discountAmount = Number((discountBase * customerDiscountPercent / 100).toFixed(2))
  const shareBaseTotal = Math.max(0, servicesTotal)
  const workerShareBase = Math.min(shareBaseTotal, Number(releaseForm.value.workerShareAmount || 0))
  const finalTotalWithProducts = Math.max(0, servicesTotal + productsTotal - discountAmount + tipAmount)
  const assignedWorkers = Array.isArray(releaseForm.value.assignedWorkers)
    ? releaseForm.value.assignedWorkers.filter((item) => String(item?.name || '').trim().length > 0)
    : []
  const workerCount = assignedWorkers.length
  const baseAmountsByWorker = []
  if (workerCount > 0 && workerShareBase > 0) {
    const baseAmount = Number((workerShareBase / workerCount).toFixed(2))
    let remaining = workerShareBase
    for (let i = 0; i < workerCount; i += 1) {
      const amount = i === workerCount - 1 ? Number(remaining.toFixed(2)) : baseAmount
      baseAmountsByWorker.push(amount)
      remaining = Number((remaining - amount).toFixed(2))
    }
  } else if (workerCount > 0) {
    assignedWorkers.forEach(() => baseAmountsByWorker.push(0))
  }
  const percentByWorker = assignedWorkers.map((worker) => {
    const value = Number(worker?.tip_share_percent || 0)
    return Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0))
  })
  const totalPercent = percentByWorker.reduce((sum, value) => sum + value, 0)
  const tipAmountsByWorker = assignedWorkers.map(() => 0)
  let allocatedTipTotal = 0
  if (tipAmount > 0 && workerCount > 0 && totalPercent > 0) {
    let distributed = 0
    for (let i = 0; i < workerCount; i += 1) {
      const divisor = totalPercent > 100 ? totalPercent : 100
      const raw = totalPercent > 100
        ? (tipAmount * percentByWorker[i]) / divisor
        : (tipAmount * percentByWorker[i]) / 100
      const amount = i === workerCount - 1
        ? Math.max(0, Number((tipAmount - distributed).toFixed(2)))
        : Number(raw.toFixed(2))
      tipAmountsByWorker[i] = amount
      distributed = Number((distributed + amount).toFixed(2))
    }
    allocatedTipTotal = Math.min(tipAmount, Number(distributed.toFixed(2)))
  }

  const workerShares = []
  if (workerCount > 0) {
    for (let i = 0; i < workerCount; i += 1) {
      workerShares.push({
        name: assignedWorkers[i]?.name || 'نیرو',
        amount: Number((Number(baseAmountsByWorker[i] || 0) + Number(tipAmountsByWorker[i] || 0)).toFixed(2))
      })
    }
  } else if (workerShareBase > 0) {
    workerShares.push({ name: 'نیرو', amount: workerShareBase })
  }
  const carwashShare = Math.max(
    0,
    Number((shareBaseTotal - workerShareBase + (tipAmount - allocatedTipTotal) - discountAmount).toFixed(2))
  )
  return {
    servicesTotal,
    productsTotal,
    customerScore,
    customerDiscountPercent,
    discountAmount,
    tipAmount,
    shareBaseTotal,
    finalTotal: finalTotalWithProducts,
    workerShare: Number((workerShareBase + allocatedTipTotal).toFixed(2)),
    workerShares,
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
const handleStepOneContinue = async (payload) => {
  try {
    const savedVehicle = await saveVehicle({ vehicle: payload }, 'entered')
    vehicleDraft.value = mapVehicleToDraft(savedVehicle)
    modalStep.value = 2
  } catch (error) {
    console.error('continue step one error:', error?.response?.data || error)
    alert('ذخیره اطلاعات مرحله اول ناموفق بود.')
  }
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
    staff_members: Array.isArray(payload?.staffMembers)
      ? payload.staffMembers.map((item) => ({
        id: item?.id,
        name: item?.name || ''
      }))
      : [],
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
  time: formatDateTime(item.check_in_at),
  plateTwoDigit: item.plate_left || '--',
  plateLetter: item.plate_letter || '-',
  plateThreeDigit: item.plate_mid || '---',
  plateBlue: item.plate_right || '--',
  model: item.car_model,
  colorName: item.car_color,
  plateDisplay: item.plate_number || '-',
  service: Array.isArray(item.job?.service_lines) && item.job.service_lines.length
    ? item.job.service_lines.map((line) => line.service_name || 'خدمت').join('، ')
    : 'خدمت ثبت نشده',
  driverName: item.driver_name,
  driverPhone: item.driver_phone,
  customerScore: Number(item.customer_score || 0),
  finalTotal: item.job?.final_total || item.job?.services_total || 0,
  carwashShare: item.job?.carwash_share_amount || 0,
  workerName: assignedWorkersLabel(item.job),
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
.dashboard-content { min-width: 0; }
.primary-btn { height: 40px; border: none; border-radius: 12px; color: #fff; font-weight: 700; padding: 0 16px; background: linear-gradient(135deg, #0058be 0%, #57dffe 100%); cursor: pointer;margin-right: 3%; }
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
.customer-score-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.customer-score-row strong { color: #0f172a; font-weight: 700; font-size: 12px; }
.star-track { position: relative; display: inline-block; line-height: 1; font-size: 14px; letter-spacing: 1px; }
.star-bg { color: #d1d5db; }
.star-fill { position: absolute; inset: 0 auto 0 0; overflow: hidden; white-space: nowrap; color: #f59e0b; }
.card-action { margin-top: auto; height: 42px; border: none; border-radius: 12px; font-weight: 700; }
.card-action.action-complete { background: #d0fadf; color: #166534; }
.card-action.action-release { background: #fef3c7; color: #92850e; }
.card-action.action-done { background: #e5e7eb; color: #374151; }
.card-passive-state { margin-top: auto; height: 42px; border-radius: 12px; border: 1px dashed #cbd5e1; color: #64748b; background: #f8fafc; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.release-panel { width: min(1380px, 100%); }
.release-loading { min-height: 280px; display: flex; align-items: center; justify-content: center; color: #64748b; font-size: 14px; }
.release-layout { padding: 24px; display: grid; gap: 20px; grid-template-columns: repeat(3, minmax(0, 1fr)); background: #edf5ff; }
.release-col { background: #f8fbff; border: 1px solid #d4e4ff; border-radius: 16px; padding: 16px; display: flex; flex-direction: column; min-height: 620px; box-shadow: 0 10px 24px -18px rgba(0,88,190,.35); }
.release-products-col, .release-summary-col { border-right: 1px solid #d4e4ff; }
.release-title { padding-bottom: 10px; border-bottom: 1px solid #d4e4ff; margin-bottom: 12px; }
.release-title h3 { margin: 0; font-size: 20px; color: #111827; }
.release-list { display: grid; gap: 10px; overflow: auto; }
.service-check-item { border: 1px solid #d4e4ff; border-radius: 12px; padding: 12px; display: flex; justify-content: space-between; gap: 12px; background: #eef5ff; }
.service-check-item h4 { margin: 0 0 4px; font-size: 15px; color: #0f172a; }
.service-check-item p { margin: 0; font-size: 12px; color: #64748b; }
.service-check-action { display: grid; justify-items: end; gap: 8px; align-content: center; }
.service-check-action span { font-size: 13px; font-weight: 700; color: #0058be; }
.service-check-action label { font-size: 12px; color: #475569; display: inline-flex; align-items: center; gap: 6px; }
.release-product-search { margin-bottom: 10px; }
.release-product-search input { width: 100%; height: 42px; border: 1px solid #bfd7ff; border-radius: 12px; padding: 0 12px; background: #edf5ff; }
.products-scroll { max-height: 520px; padding-right: 4px; }
.product-item { border: 1px solid #d4e4ff; border-radius: 12px; padding: 12px; display: flex; justify-content: space-between; align-items: center; background: #fdfefe; }
.product-item h4 { margin: 0 0 4px; font-size: 14px; color: #111827; }
.product-item p { margin: 0; font-size: 12px; color: #64748b; }
.product-item span { font-size: 13px; color: #00687a; font-weight: 700; }
.product-item.unavailable { opacity: .55; }
.product-item p.stock-empty { color: #ba1a1a; }
.qty-controls { display: inline-flex; align-items: center; gap: 10px; border: 1px solid #d4e4ff; border-radius: 10px; padding: 4px 6px; background: #edf5ff; }
.qty-controls button { width: 28px; height: 28px; border: 1px solid #bfd7ff; border-radius: 8px; background: #fff; cursor: pointer; }
.qty-controls button:disabled { opacity: .45; cursor: not-allowed; }
.qty-controls input { width: 72px; height: 28px; border: 1px solid #bfd7ff; border-radius: 8px; text-align: center; background: #fff; }
.summary-rows { display: grid; gap: 10px; }
.summary-rows p { margin: 0; display: flex; justify-content: space-between; font-size: 14px; color: #475569; }
.summary-rows p strong { color: #0f172a; }
.tip-input-row { margin-top: 10px; display: grid; gap: 6px; }
.tip-input-row span { color: #64748b; font-size: 12px; }
.tip-input-row input { height: 40px; border: 1px solid #bfd7ff; border-radius: 10px; padding: 0 10px; background: #f7fbff; }
.summary-share { margin-top: 12px; border: 1px dashed #bfd7ff; border-radius: 12px; padding: 10px; background: #edf5ff; display: grid; gap: 8px; }
.summary-share p { margin: 0; display: flex; justify-content: space-between; font-size: 13px; color: #334155; }
.summary-share .summary-share-total { border-top: 1px dashed #bfd7ff; padding-top: 8px; margin-top: 4px; font-weight: 700; }
.summary-final { margin: 12px 0 0; padding-top: 12px; border-top: 1px solid #d4e4ff; display: flex; justify-content: space-between; font-size: 18px; font-weight: 800; color: #111827; }
.mark-paid { margin-top: 12px; display: inline-flex; align-items: center; gap: 8px; color: #334155; font-size: 13px; }
.mark-paid.forced-paid { opacity: .85; }
.release-actions { margin-top: auto; padding-top: 14px; display: flex; gap: 8px; }
.back-btn { flex: 1; height: 44px; border: 1px solid #bfd7ff; border-radius: 12px; background: #fff; color: #334155; font-weight: 700; cursor: pointer; }
.confirm-release-btn { flex: 1; height: 44px; border: none; border-radius: 12px; font-weight: 700; color: #ffffff; background: linear-gradient(90deg,#0058be,#2170e4); cursor: pointer; box-shadow: 0 8px 20px rgba(0,88,190,.2); }
.confirm-release-btn:disabled { opacity: .65; cursor: not-allowed; }
.modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, .35); backdrop-filter: blur(3px); z-index: 60; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal-panel { width: min(1280px, 100%); max-height: calc(100vh - 40px); background: #fff; border-radius: 20px; overflow: auto; box-shadow: 0 24px 60px -20px rgba(15,23,42,.4); }
.step-one-modal-panel { overflow: hidden; }
.step-two-modal-panel { width: min(1440px, 100%); height: calc(100vh - 40px); max-height: calc(100vh - 40px); overflow: hidden; display: flex; flex-direction: column; min-height: 0; }
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
  .cards-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .details-grid { grid-template-columns: 1fr; }
  .summary-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .info-grid.four { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .release-layout { grid-template-columns: 1fr; }
  .release-col { min-height: auto; }
}
@media (max-width: 768px) {
  .cards-grid { grid-template-columns: 1fr; }
  .modal-overlay { padding: 8px; }
  .modal-panel { max-height: calc(100vh - 16px); border-radius: 14px; }
  .step-two-modal-panel { height: calc(100vh - 16px); max-height: calc(100vh - 16px); }
}
</style>


