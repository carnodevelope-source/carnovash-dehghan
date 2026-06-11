<template>
  <section class="step-two" dir="rtl">
    <header class="step-two-header">
      <div class="header-main">
        <div v-if="!isPieceWash" class="plate-badge" dir="ltr">
          <div class="plate-blue">IR</div>
          <div class="plate-white">
            <span>{{ plateParts.left }}</span>
            <span>{{ plateParts.letter }}</span>
            <span>{{ plateParts.mid }}</span>
            <span class="plate-separator"></span>
            <span>{{ plateParts.right }}</span>
          </div>
        </div>

        <div class="vehicle-meta">
          <div class="vehicle-title-row">
            <h3>{{ vehicleTitle }}</h3>
            <span class="badge-muted" :class="{ 'badge-danger': isPlateBlocked }">{{ isPlateBlocked ? 'پلاک بلاک‌شده' : 'عادی' }}</span>
          </div>
          <p>
            <span>{{ vehicleDriver || 'بدون نام راننده' }}</span>
            <span class="dot"></span>
            <span>{{ vehiclePhone || 'شماره ثبت نشده' }}</span>
          </p>
        </div>
      </div>

      <div class="header-actions">
        <div class="assigning-badge">
          <span class="pulse"></span>
          <span>در حال تخصیص</span>
        </div>
        <button type="button" class="icon-btn" @click="emit('close')" aria-label="بستن">
          ×
        </button>
      </div>
    </header>

    <div class="step-two-grid">
      <section class="col services-col">
        <div class="col-head">
          <h4>انتخاب خدمات</h4>
          <div v-if="!isPieceWash" class="search-box">
            <input v-model="serviceSearch" type="text" placeholder="جستجوی خدمات..." />
          </div>
          <div class="category-row">
            
          </div>
        </div>

        <div class="col-list">
          <template v-if="isPieceWash">
            <article class="piece-wash-box">
              <h5>خدمت ثابت: قطعه‌شویی</h5>
              <label class="service-discount-row">
                <span>مبلغ قطعه‌شویی (تومان)</span>
                <input :value="toThousandsInput(pieceWashPrice)" type="number" min="0" @input="pieceWashPrice = fromThousandsInput($event.target.value)" />
                <small class="unit-note">عدد را به هزار تومان وارد کنید.</small>
              </label>
              <label class="service-discount-row textarea-row">
                <span>اطلاعات قطعه</span>
                <textarea v-model="pieceDetails" rows="5" placeholder="نام قطعه، تعداد، توضیح و نکات لازم"></textarea>
              </label>
            </article>
          </template>
          <label
            v-else
            v-for="service in filteredServices"
            :key="service.id"
            class="service-card"
            :class="{ selected: isServiceSelected(service.id) }"
          >
            <input
              :checked="isServiceSelected(service.id)"
              type="checkbox"
              @change="toggleService(service.id)"
            />
            <div class="checkmark">✓</div>

            <div class="service-body">
              <div class="service-head">
                <h5>{{ service.name }}</h5>
                <strong>{{ formatMoney(service.base_price) }}</strong>
              </div>
              <div class="service-discount-row">
                <label>درصد تخفیف خدمت</label>
                <input type="number" min="0" max="100" :value="serviceDiscountPercents[service.id] || 0" @input="setServiceDiscountPercent(service.id, $event.target.value)" />
                <small class="unit-note">اگر وارد نشود ۰٪ در نظر گرفته می‌شود.</small>
              </div>
              <p>{{ service.description || 'بدون توضیحات' }}</p>
            </div>
          </label>

          <p v-if="!loading && !filteredServices.length" class="empty">خدمتی پیدا نشد.</p>
          <div v-if="loading" class="empty spinner-empty">
            <BaseSpinner size="52px" color="#1d4ed8" ball-color="#60a5fa" label="   ..." />
          </div>
          <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
        </div>
      </section>

      <section class="col staff-col">
        <div class="col-head">
          <div class="staff-title-row">
            <h4>تخصیص پرسنل</h4>
            <span>{{ availableWorkersCount }} نر حاضر</span>
          </div>
          <div class="search-box">
            <input v-model="workerSearch" type="text" placeholder="جستجوی نام پرسنل..." />
          </div>
        </div>

        <div class="col-list">
          <article
            v-for="worker in filteredWorkers"
            :key="worker.id"
            class="worker-card"
            :class="{ selected: isWorkerSelected(worker.id) }"
            @click="toggleWorker(worker.id)"
          >
            <div class="worker-top">
              <div class="worker-ident">
                <div class="avatar">{{ workerAvatar(worker) }}</div>
                <div>
                  <h5>{{ worker.full_name }}</h5>
                  <p>{{ worker.role || 'پرسنل کارواش' }}</p>
                </div>
              </div>
              <span class="worker-status" :class="`status-${workerStatus(worker).key}`">
                <span class="status-dot"></span>
                {{ workerStatus(worker).label }}
              </span>
            </div>

            <div class="worker-jobs">
              <span>سفارشات در حال انجام:</span>
              <strong>{{ Number(worker.active_jobs_count || 0).toLocaleString('fa-IR') }}</strong>
            </div>

            <div v-if="isPrimaryWorker(worker.id)" class="worker-share-readonly">
              <span>پرداخت از تنظیمات مدیر:</span>
              <strong>{{ shareType === 'percent' ? `${toFaNumber(clampedPercent)}` : formatMoney(shareValueNumeric) }}</strong>
            </div>
          </article>

          <p v-if="!loading && !filteredWorkers.length" class="empty">پرسنلی پیدا نشد.</p>
          <div v-if="loading" class="empty spinner-empty">
            <BaseSpinner size="52px" color="#1d4ed8" ball-color="#60a5fa" label="   ..." />
          </div>
        </div>
      </section>

      <aside class="col summary-col">
        <div class="summary-head">
          <h4>خلاصه تخصیص</h4>
        </div>

        <div class="summary-body">
          <section>
            <h6>خدمات انتخاب شده</h6>
            <div v-if="selectedServices.length" class="summary-list">
              <div v-for="service in selectedServices" :key="service.id" class="summary-row">
                <span>{{ service.name }}</span>
                <strong>{{ formatMoney(service.base_price) }}</strong>
              </div>
            </div>
            <p v-else class="empty">خدمتی انتخاب نشده است.</p>
          </section>

          <hr />

          <section>
            <h6>پرسنل مجری</h6>
            <div v-if="selectedWorkers.length" class="selected-worker-list">
              <div v-for="worker in selectedWorkers" :key="worker.id" class="selected-worker-box">
                <div class="avatar small">{{ workerAvatar(worker) }}</div>
                <div class="selected-worker-copy">
                  <p>{{ worker.full_name }}</p>
                  <small>{{ selectedWorkers.length > 1 ? 'درصد سهم اجرا' : 'سهم اجرا: ۱۰۰٪' }}</small>
                </div>
                <label v-if="selectedWorkers.length > 1" class="worker-share-input">
                  <input
                    :value="getWorkerSharePercent(worker.id)"
                    type="number"
                    min="0"
                    max="100"
                    @input="setWorkerSharePercent(worker.id, $event.target.value)"
                  />
                  <span>٪</span>
                </label>
                <div v-else class="worker-share-pill">
                  {{ toFaNumber(getWorkerSharePercent(worker.id)) }}٪
                </div>
              </div>
            </div>
            <p v-else class="empty">پرسنلی انتخاب نشده است.</p>
          </section>

          <hr />

          <section class="totals">
            <p v-if="isPlateBlocked" class="blocked-plate-note">
              این پلاک بلاک شده است. برای ثبت خودرو و ساخت کارت، پرداخت باید همین حالا تایید شود.
            </p>
            <div class="summary-row">
              <span>تخفیف دستی (تومان):</span>
              <input :value="toThousandsInput(manualDiscountTotal)" type="number" min="0" @input="manualDiscountTotal = fromThousandsInput($event.target.value)" />
              <small class="unit-note">عدد تخفیف را به هزار تومان وارد کنید.</small>
            </div>
            <div class="summary-row">
              <span>مبلغ کل خدمات:</span>
              <strong>{{ formatMoney(servicesTotal) }}</strong>
            </div>
            <div class="summary-row share-row">
              <span>
                سهم پرسنل
                <template v-if="shareType === 'percent'">({{ toFaNumber(clampedPercent) }}٪)</template>
              </span>
              <strong>{{ formatMoney(workerShareAmount) }}</strong>
            </div>
            <div class="summary-row final-row">
              <span>سهم کارواش:</span>
              <strong>{{ formatMoney(carwashShareAmount) }}</strong>
            </div>
          </section>
        </div>

        <footer class="summary-foot">
          <label v-if="isPlateBlocked" class="blocked-payment-check">
            <input v-model="blockedPlatePaymentConfirmed" type="checkbox" />
            <span>پرداخت شد</span>
          </label>
          <div class="summary-foot-actions">
            <button type="button" class="secondary-foot-btn" @click="emit('back')">بازگشت</button>
            <button type="button" class="primary-btn" :disabled="!canAssign" @click="onAssign">
              تایید و تخصیص کار
            </button>
          </div>
        </footer>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '../../services/api'
import BaseSpinner from '../base/BaseSpinner.vue'
import { formatThousandsToman, formatThousandsTomanValue, fromThousandsTomanInput } from '../../utils/money'

const props = defineProps({
  vehicleInfo: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['back', 'assign', 'close'])

const loading = ref(false)
const errorMessage = ref('')
const services = ref([])
const workers = ref([])
const selectedServiceIds = ref([])
const selectedWorkerIds = ref([])
const shareType = ref('percent')
const shareValueInput = ref('40')
const serviceSearch = ref('')
const workerSearch = ref('')
const activeCategory = ref('همه موارد')
const manualDiscountTotal = ref(0)
const serviceDiscountPercents = ref({})
const workerSharePercents = ref({})
const blockedPlatePaymentConfirmed = ref(false)
const pieceWashPrice = ref(0)
const pieceDetails = ref('')

const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (d) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
  .replace(/[^\d.]/g, '')

const toFaNumber = (value) => Number(value || 0).toLocaleString('fa-IR')

const formatMoney = (value) => formatThousandsToman(value)
const toThousandsInput = (value) => formatThousandsTomanValue(value, { maximumFractionDigits: 0 })
const fromThousandsInput = (value) => fromThousandsTomanInput(normalizeDigits(value))

const parsePlate = (raw) => {
  const parts = String(raw || '').trim().split(/\s+/).filter(Boolean)
  return {
    left: parts[0] || '--',
    letter: parts[1] || '-',
    mid: parts[2] || '---',
    right: parts[3] || '--'
  }
}

const normalizedVehicle = computed(() => {
  const data = props.vehicleInfo || {}
  const fromRaw = parsePlate(data.plate || data.plate_number)
  const providedStaffIds = Array.isArray(data.staffIds)
    ? data.staffIds.map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0)
    : []
  const fallbackStaffId = data.staffId ? Number(data.staffId) : null
  return {
    id: data.id ?? null,
    plateLeft: String(data.plateLeft || data.plate_left || fromRaw.left || '').trim(),
    plateLetter: String(data.plateLetter || data.plate_letter || fromRaw.letter || '').trim(),
    plateMid: String(data.plateMid || data.plate_mid || fromRaw.mid || '').trim(),
    plateRight: String(data.plateRight || data.plate_right || fromRaw.right || '').trim(),
    model: String(data.model || data.car_model || '').trim(),
    color: String(data.color || data.car_color || '').trim(),
    driver: String(data.driver || data.driver_name || '').trim(),
    mobile: String(data.mobile || data.driver_phone || '').trim(),
    note: String(data.note || data.notes || '').trim(),
    isPieceWash: Boolean(data.isPieceWash || data.is_piece_wash),
    pieceDetails: String(data.pieceDetails || data.piece_details || '').trim(),
    pieceWashPrice: Number(data.pieceWashPrice || 0),
    serviceIds: Array.isArray(data.serviceIds) ? data.serviceIds.map((id) => Number(id)) : [],
    staffId: fallbackStaffId,
    staffIds: providedStaffIds.length ? providedStaffIds : (fallbackStaffId ? [fallbackStaffId] : [])
  }
})
const isPieceWash = computed(() => normalizedVehicle.value.isPieceWash)

const plateParts = computed(() => {
  const v = normalizedVehicle.value
  if (v.isPieceWash) return 'قطعه‌شویی'
  return {
    left: v.plateLeft || '--',
    letter: v.plateLetter || '-',
    mid: v.plateMid || '---',
    right: v.plateRight || '--'
  }
})

const vehicleTitle = computed(() => {
  const v = normalizedVehicle.value
  if (v.isPieceWash) {
    return v.driver.trim().length > 0 && normalizeDigits(v.mobile).length > 0
  }
  const value = `${v.model} ${v.color}`.trim()
  return value || 'خودرو بدون مشخصات'
})

const vehicleDriver = computed(() => normalizedVehicle.value.driver)
const vehiclePhone = computed(() => normalizedVehicle.value.mobile)
const isPlateBlocked = computed(() => Boolean(props.vehicleInfo?.is_plate_blocked))

const availableWorkersCount = computed(() => workers.value.filter((worker) => worker.is_available !== false).length)

const serviceCategories = computed(() => {
  const unique = new Set(['همه موارد'])
  services.value.forEach((item) => {
    const label = (item.category_name || '').trim()
    if (label) unique.add(label)
  })
  return [...unique]
})

const filteredServices = computed(() => {
  if (isPieceWash.value) return []
  const query = serviceSearch.value.trim().toLowerCase()
  return services.value.filter((item) => {
    const matchesCategory = activeCategory.value === 'همه موارد' || (item.category_name || '') === activeCategory.value
    if (!matchesCategory) return false
    if (!query) return true
    return `${item.name || ''} ${item.description || ''} ${item.code || ''}`.toLowerCase().includes(query)
  })
})

const filteredWorkers = computed(() => {
  const query = workerSearch.value.trim().toLowerCase()
  return workers.value.filter((item) => {
    if (!query) return true
    return `${item.full_name || ''} ${item.phone || ''}`.toLowerCase().includes(query)
  })
})

const selectedServices = computed(() => {
  if (isPieceWash.value) {
    return pieceWashPrice.value > 0
      ? [{ id: -1, name: 'قطعه‌شویی', base_price: Number(pieceWashPrice.value || 0) }]
      : []
  }
  const idSet = new Set(selectedServiceIds.value.map((id) => Number(id)))
  return services.value.filter((item) => idSet.has(Number(item.id)))
})

const selectedWorkers = computed(() => {
  const idSet = new Set(selectedWorkerIds.value.map((id) => Number(id)))
  return workers.value.filter((item) => idSet.has(Number(item.id)))
})
const primarySelectedWorker = computed(() => selectedWorkers.value[0] || null)
const selectedWorkerPercentIds = computed(() => selectedWorkers.value.map((worker) => Number(worker.id)))

const servicesTotal = computed(() => selectedServices.value.reduce((sum, item) => sum + Number(item.base_price || 0), 0))
const serviceDiscountAmount = (service) => {
  const basePrice = Number(service?.base_price || 0)
  const percent = Math.max(0, Math.min(100, Number(serviceDiscountPercents.value[service?.id] || 0)))
  return Math.round((basePrice * percent) / 100)
}
const servicesDiscountTotal = computed(() => (
  isPieceWash.value
    ? 0
    : selectedServices.value.reduce((sum, item) => sum + serviceDiscountAmount(item), 0)
))

const shareValueNumeric = computed(() => Number(normalizeDigits(shareValueInput.value) || 0))

const clampedPercent = computed(() => Math.min(100, Math.max(0, shareValueNumeric.value)))

const workerShareAmount = computed(() => {
  if (!primarySelectedWorker.value) return 0
  if (shareType.value === 'fixed') {
    return Math.min(servicesTotal.value, Math.max(0, shareValueNumeric.value))
  }
  return Math.round((servicesTotal.value * clampedPercent.value) / 100)
})

const carwashShareAmount = computed(() => Math.max(0, servicesTotal.value - workerShareAmount.value))
const defaultWorkerSharePercents = (count) => {
  const workerCount = Math.max(0, Number(count || 0))
  if (!workerCount) return []
  const base = Math.floor(100 / workerCount)
  let remainder = 100 - (base * workerCount)
  return Array.from({ length: workerCount }, () => {
    const value = base + (remainder > 0 ? 1 : 0)
    if (remainder > 0) remainder -= 1
    return value
  })
}
const allocatePercentByWeights = (total, weights) => {
  const normalizedTotal = Math.max(0, Math.floor(Number(total || 0)))
  if (!weights.length) return []
  const safeWeights = weights.map((weight) => Math.max(0, Number(weight || 0)))
  const weightTotal = safeWeights.reduce((sum, weight) => sum + weight, 0)
  if (weightTotal <= 0) return defaultWorkerSharePercents(weights.length)

  const rawValues = safeWeights.map((weight) => (normalizedTotal * weight) / weightTotal)
  const baseValues = rawValues.map((value) => Math.floor(value))
  let remainder = normalizedTotal - baseValues.reduce((sum, value) => sum + value, 0)
  const fractionIndexes = rawValues
    .map((value, index) => ({ index, fraction: value - Math.floor(value) }))
    .sort((a, b) => b.fraction - a.fraction)

  for (let i = 0; i < fractionIndexes.length && remainder > 0; i += 1) {
    baseValues[fractionIndexes[i].index] += 1
    remainder -= 1
  }

  return baseValues
}
const normalizeWorkerSharePercents = (ids, source = workerSharePercents.value) => {
  const normalizedIds = ids.map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0)
  if (!normalizedIds.length) return {}
  if (normalizedIds.length === 1) return { [normalizedIds[0]]: 100 }

  const currentValues = normalizedIds.map((id) => Math.max(0, Math.floor(Number(source?.[id] || 0))))
  const hasAnyValue = currentValues.some((value) => value > 0)
  const nextValues = hasAnyValue
    ? allocatePercentByWeights(100, currentValues)
    : defaultWorkerSharePercents(normalizedIds.length)

  return normalizedIds.reduce((accumulator, id, index) => {
    accumulator[id] = nextValues[index] ?? 0
    return accumulator
  }, {})
}
const setServiceDiscountPercent = (serviceId, value) => {
  const nextValue = Math.max(0, Math.min(100, Math.floor(Number(normalizeDigits(value) || 0))))
  serviceDiscountPercents.value = {
    ...serviceDiscountPercents.value,
    [serviceId]: nextValue
  }
}

const hasRequiredVehicleInfo = computed(() => {
  const v = normalizedVehicle.value
  const hasPlate = v.plateLeft.length === 2 && v.plateLetter.length === 1 && v.plateMid.length === 3 && v.plateRight.length === 2
  const hasModel = v.model.length > 0
  const hasColor = v.color.length > 0
  const hasPhone = normalizeDigits(v.mobile).length > 0
  return hasPlate && hasModel && hasColor && hasPhone
})
const hasValidShare = computed(() => {
  if (!shareValueInput.value.trim()) return false
  if (shareType.value === 'percent') return clampedPercent.value > 0 && clampedPercent.value <= 100
  return shareValueNumeric.value > 0
})
const canAssign = computed(() => (
  hasRequiredVehicleInfo.value
  && selectedServices.value.length > 0
  && selectedWorkers.value.length > 0
  && hasValidShare.value
  && (!isPieceWash.value || pieceDetails.value.trim().length > 0)
  && (!isPlateBlocked.value || blockedPlatePaymentConfirmed.value)
))

const isServiceSelected = (id) => selectedServiceIds.value.includes(Number(id))

const toggleService = (id) => {
  const normalizedId = Number(id)
  if (isServiceSelected(normalizedId)) {
    selectedServiceIds.value = selectedServiceIds.value.filter((item) => Number(item) !== normalizedId)
    return
  }
  selectedServiceIds.value = [...selectedServiceIds.value, normalizedId]
}

const workerStatus = (worker) => {
  if (worker.is_available === false || worker.load_status === 'busy') return { key: 'busy', label: 'مشغول' }
  if (worker.load_status === 'normal' || Number(worker.active_jobs_count || 0) > 0) return { key: 'normal', label: 'در حال کار' }
  return { key: 'free', label: 'آزاد' }
}

const isWorkerSelected = (id) => selectedWorkerIds.value.includes(Number(id))
const isPrimaryWorker = (id) => Number(primarySelectedWorker.value?.id) === Number(id)
const getWorkerSharePercent = (id) => Math.max(0, Math.min(100, Number(workerSharePercents.value[Number(id)] || 0)))
const toggleWorker = (id) => {
  const normalizedId = Number(id)
  if (isWorkerSelected(normalizedId)) {
    selectedWorkerIds.value = selectedWorkerIds.value.filter((item) => Number(item) !== normalizedId)
    return
  }
  selectedWorkerIds.value = [...selectedWorkerIds.value, normalizedId]
}
const setWorkerSharePercent = (id, rawValue) => {
  const workerId = Number(id)
  const selectedIds = selectedWorkerPercentIds.value
  if (!selectedIds.includes(workerId)) return
  if (selectedIds.length === 1) {
    workerSharePercents.value = { [workerId]: 100 }
    return
  }

  const parsed = Math.max(0, Math.min(100, Math.floor(Number(normalizeDigits(rawValue) || 0))))
  const otherIds = selectedIds.filter((selectedId) => selectedId !== workerId)
  const remaining = Math.max(0, 100 - parsed)
  const otherWeights = otherIds.map((otherId) => Math.max(0, Number(workerSharePercents.value[otherId] || 0)))
  const distributedOthers = otherWeights.some((weight) => weight > 0)
    ? allocatePercentByWeights(remaining, otherWeights)
    : defaultWorkerSharePercents(otherIds.length).map((value) => Math.floor((value * remaining) / 100))
  const balancedOthers = allocatePercentByWeights(remaining, distributedOthers)
  const nextPercents = { [workerId]: parsed }

  otherIds.forEach((otherId, index) => {
    nextPercents[otherId] = balancedOthers[index] ?? 0
  })

  workerSharePercents.value = nextPercents
}

const workerAvatar = (worker) => {
  const raw = String(worker?.avatar || '').trim()
  if (raw) return raw
  const name = String(worker?.full_name || '').trim()
  if (!name) return '--'
  const parts = name.split(' ').filter(Boolean)
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`
  return name.slice(0, 2)
}

const applyWorkerPaymentDefaults = (worker) => {
  if (!worker) {
    shareType.value = 'percent'
    shareValueInput.value = '0'
    return
  }
  const paymentType = worker.payment_type || ((Number(worker.default_fixed_wage || 0) > 0) ? 'fixed' : 'percent')
  const paymentValue = Number(worker.payment_value || 0)
  shareType.value = paymentType === 'fixed' ? 'fixed' : 'percent'
  shareValueInput.value = String(Math.max(0, paymentValue))
}

const buildPayload = () => {
  const vehicle = normalizedVehicle.value
  const plate = [vehicle.plateLeft, vehicle.plateLetter, vehicle.plateMid, vehicle.plateRight]
    .map((item) => String(item || '').trim())
    .filter(Boolean)
    .join(' ')

  return {
    vehicle: {
      id: vehicle.id,
      plate,
      plateLeft: vehicle.plateLeft,
      plateLetter: vehicle.plateLetter,
      plateMid: vehicle.plateMid,
      plateRight: vehicle.plateRight,
      model: vehicle.model,
      color: vehicle.color,
      driver: vehicle.driver,
      mobile: vehicle.mobile,
      note: vehicle.note,
      isPieceWash: vehicle.isPieceWash,
      pieceDetails: pieceDetails.value.trim()
    },
    services: isPieceWash.value
      ? [{
          title: 'قطعه‌شویی',
          price: Math.max(0, Number(pieceWashPrice.value || 0)),
          discount_amount: 0
        }]
      : selectedServices.value.map((item) => ({
          id: item.id,
          title: item.name,
          price: Number(item.base_price || 0),
          discount_amount: serviceDiscountAmount(item)
        })),
    staff: primarySelectedWorker.value
      ? {
          id: primarySelectedWorker.value.id,
          name: primarySelectedWorker.value.full_name
        }
      : null,
    staffMembers: selectedWorkers.value.map((worker) => ({
      id: worker.id,
      name: worker.full_name,
      worker_share_percent: getWorkerSharePercent(worker.id)
    })),
    share: {
      type: shareType.value,
      value: shareType.value === 'percent' ? clampedPercent.value : Math.max(0, shareValueNumeric.value)
    },
    manual_discount_total: Math.max(0, Number(manualDiscountTotal.value || 0)) + servicesDiscountTotal.value,
    blocked_plate_payment_confirmed: blockedPlatePaymentConfirmed.value
  }
}

const onAssign = () => {
  if (!canAssign.value) return
  emit('assign', buildPayload())
}

const hydrateFromVehicleInfo = () => {
  const vehicle = normalizedVehicle.value
  selectedServiceIds.value = [...new Set(vehicle.serviceIds.map((id) => Number(id)).filter((id) => !Number.isNaN(id)))]
  selectedWorkerIds.value = [...new Set((vehicle.staffIds || []).map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0))]
  blockedPlatePaymentConfirmed.value = false
  serviceDiscountPercents.value = {}
  pieceDetails.value = vehicle.pieceDetails || ''
  pieceWashPrice.value = isPieceWash.value ? Math.max(0, Number(vehicle.pieceWashPrice || 0)) : 0
  workerSharePercents.value = normalizeWorkerSharePercents(selectedWorkerIds.value)
}

const loadInitialData = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const [serviceResp, workerResp] = await Promise.all([
      api.get('/services/'),
      api.get('/workers/')
    ])
    services.value = (Array.isArray(serviceResp.data) ? serviceResp.data : [])
      .filter((item) => item.is_active !== false)
      .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0))

    workers.value = (Array.isArray(workerResp.data) ? workerResp.data : [])

    const hasDefaultCategory = serviceCategories.value.includes(activeCategory.value)
    if (!hasDefaultCategory) activeCategory.value = 'همه موارد'

    const validServiceIds = new Set(services.value.map((item) => Number(item.id)))
    selectedServiceIds.value = selectedServiceIds.value.filter((id) => validServiceIds.has(Number(id)))
    if (isPieceWash.value && pieceWashPrice.value <= 0) {
      const pieceWashService = services.value.find((item) => String(item.name || '').trim() === 'قطعه‌شویی')
      pieceWashPrice.value = Number(pieceWashService?.base_price || 0)
    }

    const validWorkerIds = new Set(workers.value.map((item) => Number(item.id)))
    selectedWorkerIds.value = selectedWorkerIds.value.filter((id) => validWorkerIds.has(Number(id)))
    if (!selectedWorkerIds.value.length && workers.value.length) selectedWorkerIds.value = [Number(workers.value[0].id)]
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || 'بارگذاری اطلاعات خدمات و پرسنل ناموفق بود.'
  } finally {
    loading.value = false
  }
}

watch(() => props.vehicleInfo, hydrateFromVehicleInfo, { immediate: true, deep: true })
watch(primarySelectedWorker, applyWorkerPaymentDefaults, { immediate: true })
watch(selectedWorkerPercentIds, (ids) => {
  workerSharePercents.value = normalizeWorkerSharePercents(ids, workerSharePercents.value)
}, { immediate: true })

onMounted(loadInitialData)
</script>

<style scoped>
.step-two {
  background: #edf5ff;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.step-two-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 32px;
  border-bottom: 1px solid #d4e4ff;
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 2;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 22px;
}

.plate-badge {
  display: flex;
  align-items: stretch;
  border: 2px solid #001a42;
  border-radius: 10px;
  overflow: hidden;
  background: #001a42;
}

.plate-blue {
  background: #0058be;
  color: #fff;
  width: 34px;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid rgba(255, 255, 255, 0.2);
}

.plate-white {
  background: #fff;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 0 12px;
  color: #001a42;
  font-weight: 700;
  font-size: 13px;
}

.plate-separator {
  width: 1px;
  height: 16px;
  background: rgba(0, 26, 66, 0.25);
}

.vehicle-meta h3 {
  margin: 0;
  font-size: 22px;
  color: #191c1e;
}

.vehicle-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.badge-muted {
  background: rgba(87, 223, 254, 0.35);
  color: #006172;
  border-radius: 999px;
  padding: 2px 9px;
  font-size: 11px;
  font-weight: 700;
}

.badge-danger {
  background: #fee2e2;
  color: #991b1b;
}

.vehicle-meta p {
  margin: 6px 0 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #424754;
  font-size: 13px;
}

.dot {
  width: 4px;
  height: 4px;
  border-radius: 99px;
  background: #bfd7ff;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.assigning-badge {
  border: 1px solid rgba(132, 85, 239, 0.25);
  background: rgba(132, 85, 239, 0.08);
  color: #6b38d4;
  border-radius: 12px;
  padding: 8px 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 99px;
  background: #6b38d4;
  box-shadow: 0 0 0 0 rgba(107, 56, 212, 0.45);
  animation: pulse 1.7s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(107, 56, 212, 0.45);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(107, 56, 212, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(107, 56, 212, 0);
  }
}

.icon-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 99px;
  background: transparent;
  color: #424754;
  font-size: 26px;
  line-height: 1;
  cursor: pointer;
}

.icon-btn:hover {
  background: #e6f1ff;
}

.step-two-grid {
  display: grid;
  grid-template-columns: 35% 35% 30%;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.col {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.services-col,
.staff-col {
  border-left: 1px solid #d4e4ff;
}

.services-col {
  background: #f2f8ff;
}

.staff-col {
  background: #f2f8ff;
}

.summary-col {
  background: #fff;
}

.col-head {
  padding: 22px 20px 14px;
  display: grid;
  gap: 12px;
  flex-shrink: 0;
}

.col-head h4,
.summary-head h4 {
  margin: 0;
  color: #191c1e;
  font-size: 24px;
  font-weight: 700;
}

.staff-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.staff-title-row span {
  font-size: 13px;
  color: #424754;
}

.search-box input {
  width: 100%;
  height: 48px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: #e8f2ff;
  padding: 0 14px;
  color: #191c1e;
}

.search-box input:focus {
  outline: none;
  background: #fff;
  border-color: #0058be;
  box-shadow: 0 0 0 2px rgba(0, 88, 190, 0.15);
}

.category-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.category-row::-webkit-scrollbar {
  display: none;
}

.category-chip {
  border: none;
  border-radius: 999px;
  padding: 8px 14px;
  white-space: nowrap;
  background: #deecff;
  color: #424754;
  cursor: pointer;
}

.category-chip.active {
  background: #0058be;
  color: #fff;
  box-shadow: 0 8px 20px rgba(0, 88, 190, 0.25);
}

.col-list {
  padding: 0 20px 20px;
  overflow-y: auto;
  overflow-x: hidden;
  display: grid;
  gap: 12px;
}

.service-card {
  position: relative;
  border: 1px solid #bfd7ff;
  border-radius: 16px;
  background: #fff;
  padding: 14px;
  display: grid;
  grid-template-columns: 26px 1fr;
  gap: 10px;
  cursor: pointer;
}

.service-card input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.checkmark {
  width: 22px;
  height: 22px;
  border: 2px solid #727785;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: transparent;
  margin-top: 2px;
}

.service-card.selected {
  background: rgba(216, 226, 255, 0.4);
  border: 2px solid #0058be;
}

.service-card.selected .checkmark {
  border-color: #0058be;
  background: #0058be;
  color: #fff;
}

.service-head {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 8px;
}

.service-head h5,
.worker-ident h5 {
  margin: 0;
  font-size: 18px;
  color: #191c1e;
}

.service-head strong {
  color: #0058be;
  font-size: 15px;
}

.service-body p {
  margin: 6px 0 0;
  color: #424754;
  font-size: 13px;
  line-height: 1.7;
}
.service-discount-row {
  margin-top: 8px;
  display: grid;
  gap: 4px;
}
.service-discount-row label {
  font-size: 12px;
  color: #475569;
}
.service-discount-row input,
.totals input {
  height: 34px;
  border: 1px solid #bfd7ff;
  border-radius: 8px;
  padding: 0 8px;
  width: 140px;
}
.unit-note {
  color: #64748b;
  font-size: 11px;
}

.piece-wash-box {
  border: 1px solid #bfd7ff;
  border-radius: 18px;
  padding: 16px;
  background: #fff;
  display: grid;
  gap: 12px;
}

.piece-wash-box h5 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.textarea-row textarea {
  width: 100%;
  min-height: 110px;
  border: 1px solid #bfd7ff;
  border-radius: 10px;
  padding: 10px;
  resize: vertical;
  background: #f8fbff;
  font: inherit;
}

.worker-card {
  border: 1px solid #bfd7ff;
  border-radius: 20px;
  padding: 15px;
  background: #fff;
  cursor: pointer;
}

.worker-card.selected {
  border: 2px solid #0058be;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08);
}

.worker-top {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 12px;
}

.worker-ident {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #acedff;
  color: #001f26;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
}

.avatar.small {
  width: 32px;
  height: 32px;
  font-size: 12px;
  background: #0058be;
  color: #fff;
}

.worker-ident p {
  margin: 3px 0 0;
  color: #424754;
  font-size: 12px;
}

.worker-status {
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 99px;
}

.status-free {
  background: rgba(0, 104, 122, 0.12);
  color: #00687a;
}

.status-free .status-dot {
  background: #00687a;
}

.status-normal {
  background: rgba(245, 158, 11, 0.15);
  color: #a16207;
}

.status-normal .status-dot {
  background: #a16207;
}

.status-busy {
  background: rgba(186, 26, 26, 0.1);
  color: #ba1a1a;
}

.status-busy .status-dot {
  background: #ba1a1a;
}

.worker-jobs {
  margin-top: 12px;
  border-radius: 12px;
  background: #e6f1ff;
  padding: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #424754;
  font-size: 13px;
}

.worker-jobs strong {
  color: #191c1e;
}

.worker-share-readonly {
  margin-top: 12px;
  border-radius: 10px;
  background: #deecff;
  color: #1e3a8a;
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.worker-share-readonly strong {
  font-size: 13px;
}

.worker-share {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.share-type {
  background: #deecff;
  border-radius: 10px;
  padding: 3px;
  display: inline-flex;
}

.share-type button {
  border: none;
  background: transparent;
  color: #424754;
  border-radius: 7px;
  padding: 7px 11px;
  cursor: default;
  opacity: 0.9;
}

.share-type button.active {
  background: #fff;
  color: #191c1e;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.1);
}

.share-value {
  flex: 1;
  position: relative;
}

.share-value input {
  width: 100%;
  height: 38px;
  border: 1px solid #bfd7ff;
  border-radius: 10px;
  background: #f2f8ff;
  text-align: center;
  padding: 0 56px 0 10px;
}

.share-value span {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #424754;
  font-size: 12px;
}

.summary-head {
  padding: 22px 20px;
  border-bottom: 1px solid #d4e4ff;
}

.summary-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
  display: grid;
  gap: 16px;
}

.summary-body h6 {
  margin: 0 0 10px;
  color: #424754;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}

.summary-list {
  display: grid;
  gap: 8px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  color: #191c1e;
  font-size: 14px;
}

.summary-row strong {
  color: #191c1e;
}

.selected-worker-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background: #e6f1ff;
  border-radius: 12px;
  padding: 9px;
}

.selected-worker-list {
  display: grid;
  gap: 8px;
}

.selected-worker-box p {
  margin: 0;
  color: #191c1e;
  font-weight: 700;
}

.selected-worker-copy {
  flex: 1;
  min-width: 0;
}

.selected-worker-box small {
  color: #424754;
}

.worker-share-input {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(104, 135, 187, 0.2);
}

.worker-share-input input {
  width: 54px;
  border: none;
  background: transparent;
  color: #14532d;
  font: inherit;
  font-weight: 700;
  text-align: center;
  outline: none;
}

.worker-share-input span,
.worker-share-pill {
  color: #14532d;
  font-size: 13px;
  font-weight: 800;
}

.worker-share-pill {
  min-width: 68px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(104, 135, 187, 0.18);
}

.summary-body hr {
  margin: 0;
  border: 0;
  border-top: 1px solid #d4e4ff;
}

.totals {
  display: grid;
  gap: 10px;
  margin-top: auto;
}

.blocked-plate-note {
  margin: 0;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fff1f2;
  color: #9f1239;
  font-size: 13px;
  line-height: 1.8;
}

.share-row {
  color: #6b38d4;
}

.share-row strong {
  color: #6b38d4;
}

.final-row {
  background: rgba(216, 226, 255, 0.6);
  border-radius: 12px;
  padding: 11px;
  color: #0058be;
}

.final-row strong {
  color: #0058be;
  font-size: 18px;
}

.summary-foot {
  border-top: 1px solid #d4e4ff;
  padding: 16px 20px;
  display: grid;
  gap: 10px;
}

.summary-foot-actions {
  display: grid;
  grid-template-columns: minmax(0, 132px) minmax(0, 1fr);
  gap: 10px;
}

.blocked-payment-check {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid #fecdd3;
  border-radius: 12px;
  background: #fff7f7;
  color: #7f1d1d;
  font-weight: 700;
}

.blocked-payment-check input {
  width: 18px;
  height: 18px;
}

.primary-btn {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  color: #fff;
  background: linear-gradient(90deg, #0058be, #2170e4);
  box-shadow: 0 8px 20px rgba(0, 88, 190, 0.25);
}

.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.secondary-foot-btn {
  width: 100%;
  height: 48px;
  border: 1px solid #c7d8f4;
  border-radius: 12px;
  background: #ffffff;
  color: #1e3a5f;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.secondary-foot-btn:hover {
  background: #eef4ff;
}

.empty,
.error {
  margin: 0;
  border-radius: 12px;
  padding: 11px;
  font-size: 13px;
}

.empty {
  background: #e6f1ff;
  color: #424754;
}

.spinner-empty {
  display: grid;
  justify-items: center;
  gap: 8px;
}

.error {
  background: #ffdad6;
  color: #93000a;
}

@media (max-width: 1380px) {
  .step-two-grid {
    grid-template-columns: 1fr;
  }

  .services-col,
  .staff-col {
    border-left: none;
    border-bottom: 1px solid #d4e4ff;
  }

  .summary-col {
    min-height: 380px;
  }
}

@media (max-width: 768px) {
  .step-two-header {
    padding: 14px;
    align-items: start;
    flex-direction: column;
    gap: 12px;
  }

  .header-main {
    width: 100%;
    flex-direction: column;
    align-items: start;
    gap: 10px;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .col-head,
  .col-list,
  .summary-head,
  .summary-body,
  .summary-foot {
    padding-right: 14px;
    padding-left: 14px;
  }

  .service-head {
    flex-direction: column;
    align-items: start;
  }

  .worker-share {
    flex-direction: column;
    align-items: stretch;
  }

}
</style>

