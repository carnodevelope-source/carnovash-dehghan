<template>
  <section class="step-two" dir="rtl">
    <header class="step-two-header">
      <div class="header-main">
        <div class="header-copy">
          <h3>تخصیص خدمات و نیروها</h3>
          <p>خدمات را نهایی کنید و نیروهای حاضر را به این خودرو وصل کنید.</p>
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

    <div v-if="isServicePickerOpen && !isPieceWash" class="service-picker-overlay" role="dialog" aria-modal="true">
      <section class="service-picker-panel">
        <header class="service-picker-head">
          <div>
            <h4>انتخاب خدمات</h4>
            <p>{{ toFaNumber(tempSelectedServiceIds.length) }} خدمت انتخاب شده</p>
          </div>
          <button type="button" class="icon-btn" aria-label="بستن" @click="closeServicePicker">
            ×
          </button>
        </header>

        <div class="service-picker-grid">
          <button
            v-for="service in services"
            :key="service.id"
            type="button"
            class="service-bubble"
            :class="{ selected: isTempServiceSelected(service.id) }"
            :title="service.name"
            @click="toggleTempService(service.id)"
          >
            {{ service.name }}
          </button>
        </div>

        <p v-if="!loading && !services.length" class="empty">خدمتی پیدا نشد.</p>
        <div v-if="loading" class="empty spinner-empty">
          <BaseSpinner size="52px" color="#1d4ed8" ball-color="#60a5fa" label="   ..." />
        </div>

        <footer class="service-picker-foot">
          <button type="button" class="secondary-foot-btn" @click="closeServicePicker">انصراف</button>
          <button type="button" class="primary-btn" @click="confirmServicePicker">ثبت خدمات</button>
        </footer>
      </section>
    </div>

    <div v-if="preInvoiceModalOpen" class="service-picker-overlay" role="dialog" aria-modal="true" @click.self="closePreInvoiceModal">
      <section class="pre-invoice-panel">
        <header class="service-picker-head">
          <div>
            <h4>پیش‌فاکتور فیش</h4>
            <p>پیش‌نمایش مخصوص فیش پرینتر {{ preInvoicePaperWidthLabel }}</p>
          </div>
          <button type="button" class="icon-btn" aria-label="بستن" @click="closePreInvoiceModal">×</button>
        </header>
        <div class="pre-invoice-toolbar">
          <button type="button" class="invoice-format-chip" :class="{ active: preInvoicePaperWidth === '58mm' }" @click="preInvoicePaperWidth = '58mm'">
            <strong>58mm</strong>
            <span>فیش باریک</span>
          </button>
          <button type="button" class="invoice-format-chip" :class="{ active: preInvoicePaperWidth === '80mm' }" @click="preInvoicePaperWidth = '80mm'">
            <strong>80mm</strong>
            <span>فیش استاندارد</span>
          </button>
          <button type="button" class="primary-btn" @click="printPreInvoice">چاپ پیش‌فاکتور</button>
        </div>
        <div class="pre-invoice-preview-shell">
          <article class="pre-invoice-receipt" :style="preInvoiceReceiptStyle">
            <header>
              <strong>{{ preInvoiceCarwashTitle }}</strong>
              <small v-if="preInvoiceHeaderNote">{{ preInvoiceHeaderNote }}</small>
              <span>خدمات</span>
            </header>
            <section class="receipt-info-grid">
              <p><span>شماره پذیرش</span><strong>{{ preInvoiceAdmissionNumber }}</strong></p>
              <p><span>زمان</span><strong>{{ preInvoiceIssuedAt }}</strong></p>
              <p><span>مشتری</span><strong>{{ vehicleDriver || 'مشتری حضوری' }}</strong></p>
              <p><span>خودرو</span><strong>{{ vehicleTitle }}</strong></p>
              <p><span>پلاک</span><strong>{{ preInvoicePlateLabel }}</strong></p>
            </section>
            <table class="pre-invoice-table">
              <thead>
                <tr>
                  <th>شرح</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(service, index) in selectedServices" :key="`pre-invoice-${service.id || index}`">
                  <td>{{ toFaNumber(index + 1) }}. {{ service.name }}</td>
                </tr>
              </tbody>
            </table>
            <footer>
              <p v-if="receiptFooterNote">{{ receiptFooterNote }}</p>
              <strong>از اعتماد شما سپاسگزاریم</strong>
            </footer>
          </article>
        </div>
      </section>
    </div>

    <div class="step-two-grid">
      <section class="col services-col">
        <div class="col-head">
          <div class="service-title-row">
            <h4>خدمات</h4>
            <button v-if="!isPieceWash" type="button" class="edit-services-btn" @click="openServicePicker">
              ویرایش
            </button>
          </div>
        </div>

        <div class="col-list">
          <template v-if="isPieceWash">
            <article class="piece-wash-box">
              <h5>خدمت ثابت: قطعه‌شویی</h5>
              <label class="service-discount-row">
                <span>مبلغ قطعه‌شویی (تومان)</span>
                <input :value="toThousandsInput(pieceWashPrice)" type="text" inputmode="numeric" @input="pieceWashPrice = fromThousandsInput($event.target.value)" />
                <small class="unit-note">عدد را به هزارتومن وارد کنید.</small>
              </label>
              <label class="service-discount-row textarea-row">
                <span>اطلاعات قطعه</span>
                <textarea v-model="pieceDetails" rows="5" placeholder="نام قطعه، تعداد، توضیح و نکات لازم"></textarea>
              </label>
            </article>
          </template>
          <template v-else>
            <article
              v-for="service in selectedServices"
              :key="service.id"
              class="service-card selected listed-service-card"
            >
              <div class="service-body">
                <div class="service-head">
                  <h5>{{ service.name }}</h5>
                  <strong>{{ formatMoney(service.adjusted_price ?? service.base_price) }}</strong>
                </div>
                <div class="service-meta-row">
                  <p>{{ service.description || 'بدون توضیحات' }}</p>
                  <div class="service-adjuster">
                    <button type="button" class="service-adjust-btn" @click="adjustServicePrice(service.id, 'decrease')">-</button>
                    <button type="button" class="service-adjust-btn" @click="adjustServicePrice(service.id, 'increase')">+</button>
                  </div>
                </div>
              </div>
            </article>
          </template>

          <p v-if="!loading && !isPieceWash && !selectedServices.length" class="empty">برای انتخاب خدمات روی ویرایش بزنید.</p>
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
            :class="{ selected: isWorkerSelected(worker.id), 'queue-front': isQueueFront(worker.id) }"
            @click="toggleWorker(worker.id)"
          >
            <div class="worker-top">
              <div class="worker-ident">
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

            <div class="worker-queue-meta">
              <span>
                ورود:
                <strong>{{ formatQueueTime(worker.open_shift_started_at) }}</strong>
              </span>
              <span>
                نوبت:
                <strong>{{ formatQueueTime(worker.queue_position_at) }}</strong>
              </span>
              <span v-if="isQueueFront(worker.id)" class="queue-front-pill">اول صف</span>
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
          <button type="button" class="summary-invoice-btn" :disabled="!selectedServices.length" @click="openPreInvoiceModal">پیش‌فاکتور</button>
        </div>

        <div class="summary-body">
          <section>
            <h6>خدمات انتخاب شده</h6>
            <div v-if="selectedServices.length" class="summary-list">
              <div v-for="service in selectedServices" :key="service.id" class="summary-row">
                <span>{{ service.name }}</span>
                <strong>{{ formatMoney(service.adjusted_price ?? service.base_price) }}</strong>
              </div>
            </div>
            <p v-else class="empty">خدمتی انتخاب نشده است.</p>
          </section>

          <hr />

          <section>
            <h6>پرسنل مجری</h6>
            <div v-if="selectedWorkers.length" class="selected-worker-list">
              <div v-for="worker in selectedWorkers" :key="worker.id" class="selected-worker-box">
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
              <input :value="toThousandsInput(manualDiscountTotal)" type="text" inputmode="numeric" @input="manualDiscountTotal = fromThousandsInput($event.target.value)" />
              </div>
            <div class="summary-row">
              <span>مبلغ کل خدمات:</span>
              <strong>{{ formatMoney(servicesTotal) }}</strong>
            </div>
            <div class="summary-row">
              <span>تخفیف مجموعه</span>
              <strong>{{ formatMoney(facilityDiscountTotal) }}</strong>
            </div>
            <div class="loyalty-discount-card" :class="{ active: applyLoyaltyDiscount }">
              <div class="loyalty-discount-copy">
                <span>اعمال تخفیف امتیاز مشتری</span>
                <strong>{{ toFaNumber(customerLoyaltyDiscountPercent) }}٪</strong>
              </div>
              <button
                type="button"
                class="loyalty-discount-toggle"
                role="switch"
                :aria-checked="applyLoyaltyDiscount"
                @click="toggleLoyaltyDiscount"
              >
                <span></span>
              </button>
              <b>{{ formatMoney(effectiveLoyaltyDiscountAmount) }}</b>
            </div>
            <div v-if="manualServiceIncreaseTotal > 0" class="summary-row service-adjust-summary increase-row">
              <span>جمع افزایش دستی</span>
              <strong>{{ formatMoney(manualServiceIncreaseTotal) }}</strong>
            </div>
            <div v-if="manualServiceDecreaseTotal > 0" class="summary-row service-adjust-summary decrease-row">
              <span>جمع کاهش دستی</span>
              <strong>{{ formatMoney(manualServiceDecreaseTotal) }}</strong>
            </div>
            <div class="summary-row discount-row">
              <span>
                تخفیف دستی
                <template v-if="manualDiscountPercent > 0">({{ toFaNumber(manualDiscountPercent) }}٪)</template>
              </span>
              <strong>{{ formatMoney(effectiveManualDiscountTotal) }}</strong>
            </div>
            <div class="summary-row discount-row">
              <span>جمع تخفیف</span>
              <strong>{{ formatMoney(totalDiscountAmount) }}</strong>
            </div>
            <div class="summary-row net-row">
              <span>مبلغ بعد از تخفیف</span>
              <strong>{{ formatMoney(discountedServicesTotal) }}</strong>
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
          <label class="sms-notification-check" :class="{ disabled: !normalizedVehicle.smsAutoSendEnabled }">
            <input v-model="smsNotificationsEnabled" type="checkbox" :disabled="!normalizedVehicle.smsAutoSendEnabled" />
            <span>
              <strong>SMS</strong>
              <small>{{ normalizedVehicle.smsAutoSendEnabled ? 'ارسال پیامک تخصیص و ترخیص برای همین سفارش' : 'ارسال خودکار پیامک در تنظیمات غیرفعال است' }}</small>
            </span>
          </label>
          <div class="summary-foot-actions">
            <button type="button" class="secondary-foot-btn" @click="emit('back')">بازگشت</button>
            <button type="button" class="primary-btn" :disabled="!canAssign || submitting || actionLocked" @click="onAssign">
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
import { resolveApiErrorMessage } from '../../utils/apiError'
import { resolvePlateParts } from '../../utils/plate'

const props = defineProps({
  vehicleInfo: { type: Object, default: () => ({}) },
  submitting: { type: Boolean, default: false }
})

const emit = defineEmits(['back', 'assign', 'close'])

const loading = ref(false)
const errorMessage = ref('')
const services = ref([])
const workers = ref([])
const selectedServiceIds = ref([])
const tempSelectedServiceIds = ref([])
const selectedWorkerIds = ref([])
const shareType = ref('percent')
const shareValueInput = ref('40')
const workerSearch = ref('')
const manualDiscountTotal = ref(0)
const applyLoyaltyDiscount = ref(true)
const toggleLoyaltyDiscount = (event) => {
  applyLoyaltyDiscount.value = !applyLoyaltyDiscount.value
  event?.currentTarget?.blur?.()
}
const workerSharePercents = ref({})
const servicePriceAdjustments = ref({})
const blockedPlatePaymentConfirmed = ref(false)
const smsNotificationsEnabled = ref(true)
const pieceWashPrice = ref(0)
const pieceDetails = ref('')
const isServicePickerOpen = ref(false)
const hasOpenedInitialServicePicker = ref(false)
const activeVehicleKey = ref('')
const actionLocked = ref(false)
const preInvoiceModalOpen = ref(false)
const preInvoicePaperWidth = ref('80mm')
const receiptHeaderNote = ref('')
const receiptFooterNote = ref('')
const carwashName = ref('کارواش')

const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (d) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
  .replace(/[^\d.]/g, '')

const toFaNumber = (value) => Number(value || 0).toLocaleString('fa-IR')

const formatMoney = (value) => formatThousandsToman(value)
const toThousandsInput = (value) => formatThousandsTomanValue(value, { maximumFractionDigits: 0 })
const fromThousandsInput = (value) => fromThousandsTomanInput(normalizeDigits(value))

const normalizedVehicle = computed(() => {
  const data = props.vehicleInfo || {}
  const plateType = String(data.plateType || data.plate_type || 'car').trim() || 'car'
  const fromRaw = resolvePlateParts({ raw: data.plate || data.plate_number, plate_type: plateType })
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
    plateType,
    tariffType: String(data.tariffType || data.tariff_type || 'type_1').trim() || 'type_1',
    model: String(data.model || data.car_model || '').trim(),
    color: String(data.color || data.car_color || '').trim(),
    driver: String(data.driver || data.driver_name || '').trim(),
    mobile: String(data.mobile || data.driver_phone || '').trim(),
    smsNotificationsEnabled: data.smsNotificationsEnabled ?? data.sms_notifications_enabled ?? true,
    smsAutoSendEnabled: (
      data.smsAutoSendEnabled
      ?? data.sms_auto_send_enabled
      ?? data.sms_vehicle_auto_send_enabled
      ?? true
    ),
    note: String(data.note || data.notes || '').trim(),
    isPieceWash: Boolean(data.isPieceWash || data.is_piece_wash),
    pieceDetails: String(data.pieceDetails || data.piece_details || '').trim(),
    pieceWashPrice: Number(data.pieceWashPrice || 0),
    aiSessionId: String(data.aiSessionId || '').trim(),
    aiRawText: String(data.aiRawText || '').trim(),
    aiPersianText: String(data.aiPersianText || '').trim(),
    aiConvertedPlate: String(data.aiConvertedPlate || '').trim(),
    aiConvertedPlateLeft: String(data.aiConvertedPlateLeft || '').trim(),
    aiConvertedPlateLetter: String(data.aiConvertedPlateLetter || '').trim(),
    aiConvertedPlateMid: String(data.aiConvertedPlateMid || '').trim(),
    aiConvertedPlateRight: String(data.aiConvertedPlateRight || '').trim(),
    aiConvertedPlateType: String(data.aiConvertedPlateType || plateType).trim() || plateType,
    aiImageBase64: String(data.aiImageBase64 || '').trim(),
    aiConfidence: data.aiConfidence ?? null,
    aiLatencyMs: data.aiLatencyMs ?? null,
    serviceIds: Array.isArray(data.serviceIds) ? data.serviceIds.map((id) => Number(id)) : [],
    staffMembers: Array.isArray(data.staffMembers || data.staff_members)
      ? (data.staffMembers || data.staff_members)
        .map((item) => ({
          id: Number(item?.id || 0),
          name: String(item?.name || '').trim(),
          worker_share_percent: Math.max(0, Math.min(100, Number(item?.worker_share_percent || 0)))
        }))
        .filter((item) => item.id > 0)
      : [],
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
    const pieceOwner = String(v.driver || '').trim()
    return pieceOwner || 'قطعه‌شویی'
  }
  const value = `${v.model} ${v.color}`.trim()
  return value || 'خودرو بدون مشخصات'
})

const vehicleDriver = computed(() => normalizedVehicle.value.driver)
const vehiclePhone = computed(() => normalizedVehicle.value.mobile)
const isPlateBlocked = computed(() => Boolean(props.vehicleInfo?.is_plate_blocked))

const isWorkerPresent = (worker) => String(worker?.current_status || '').toLowerCase() === 'in'
const isQueueSelectableWorker = (worker) => isWorkerPresent(worker) && worker?.is_available !== false
const isWashAssignableWorker = (worker) => String(worker?.role_key || worker?.user?.role || worker?.role || '').trim().toLowerCase() === 'worker'
const queueFrontWorkerId = computed(() => {
  const assignableWorkers = workers.value.filter(isWashAssignableWorker)
  const preferred = assignableWorkers.find(isQueueSelectableWorker) || assignableWorkers.find(isWorkerPresent) || assignableWorkers[0]
  return preferred ? Number(preferred.id) : null
})

const filteredWorkers = computed(() => {
  const query = workerSearch.value.trim().toLowerCase()
  return workers.value.filter((item) => {
    if (!isWashAssignableWorker(item)) return false
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
  return services.value
    .filter((item) => idSet.has(Number(item.id)))
    .map((item) => {
      const adjustment = Number(servicePriceAdjustments.value[Number(item.id)] || 0)
      return {
        ...item,
        manual_adjustment: adjustment,
        list_price: Number(item.list_price ?? item.resolved_list_price ?? item.base_price ?? 0),
        adjusted_price: Math.max(0, Number(item.base_price || 0) + adjustment)
      }
    })
})

const selectedWorkers = computed(() => {
  const idSet = new Set(selectedWorkerIds.value.map((id) => Number(id)))
  return workers.value.filter((item) => idSet.has(Number(item.id)))
})
const primarySelectedWorker = computed(() => selectedWorkers.value[0] || null)
const selectedWorkerPercentIds = computed(() => selectedWorkers.value.map((worker) => Number(worker.id)))

const manualServiceIncreaseTotal = computed(() => selectedServices.value.reduce((sum, item) => {
  const adjustment = Number(item.manual_adjustment || 0)
  return sum + (adjustment > 0 ? adjustment : 0)
}, 0))
const manualServiceDecreaseTotal = computed(() => selectedServices.value.reduce((sum, item) => {
  const adjustment = Number(item.manual_adjustment || 0)
  return sum + (adjustment < 0 ? Math.abs(adjustment) : 0)
}, 0))
const serviceListSubtotal = computed(() => selectedServices.value.reduce((sum, item) => {
  return sum + Number(item.list_price || item.base_price || 0)
}, 0))
const servicesTotal = computed(() => selectedServices.value.reduce((sum, item) => sum + Number((item.adjusted_price ?? item.base_price) || 0), 0))
const facilityDiscountTotal = computed(() => Math.max(0, Number((serviceListSubtotal.value - servicesTotal.value).toFixed(2))))
const customerLoyaltyDiscountPercent = computed(() => Math.max(0, Number(
  props.vehicleInfo?.customer_loyalty_discount_percent
  ?? props.vehicleInfo?.customerLoyaltyDiscountPercent
  ?? 0
)))
const loyaltyDiscountAmount = computed(() => Number(((servicesTotal.value * customerLoyaltyDiscountPercent.value) / 100).toFixed(2)))
const effectiveLoyaltyDiscountAmount = computed(() => (applyLoyaltyDiscount.value ? loyaltyDiscountAmount.value : 0))
const effectiveManualDiscountTotal = computed(() => Math.min(
  Math.max(0, servicesTotal.value - effectiveLoyaltyDiscountAmount.value),
  Math.max(0, Number(manualDiscountTotal.value || 0))
))
const totalDiscountAmount = computed(() => Number((facilityDiscountTotal.value + effectiveLoyaltyDiscountAmount.value + effectiveManualDiscountTotal.value).toFixed(2)))
const discountedServicesTotal = computed(() => Math.max(0, servicesTotal.value - effectiveLoyaltyDiscountAmount.value - effectiveManualDiscountTotal.value))
const manualDiscountPercent = computed(() => (
  servicesTotal.value > 0
    ? Number(((effectiveManualDiscountTotal.value / servicesTotal.value) * 100).toFixed(1))
    : 0
))

const shareValueNumeric = computed(() => Number(normalizeDigits(shareValueInput.value) || 0))

const clampedPercent = computed(() => Math.min(100, Math.max(0, shareValueNumeric.value)))

const workerShareAmount = computed(() => {
  if (!primarySelectedWorker.value) return 0
  if (shareType.value === 'fixed') {
    return Math.min(discountedServicesTotal.value, Math.max(0, shareValueNumeric.value))
  }
  return Math.round((discountedServicesTotal.value * clampedPercent.value) / 100)
})

const carwashShareAmount = computed(() => Math.max(0, discountedServicesTotal.value - workerShareAmount.value))
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

const hasRequiredVehicleInfo = computed(() => {
  const v = normalizedVehicle.value
  const hasPhone = normalizeDigits(v.mobile).length > 0
  if (v.isPieceWash) {
    return hasPhone
  }
  return hasPhone
})
const hasValidShare = computed(() => {
  if (!shareValueInput.value.trim()) return false
  if (shareType.value === 'percent') return clampedPercent.value >= 0 && clampedPercent.value <= 100
  return shareValueNumeric.value >= 0
})
const canAssign = computed(() => (
  hasRequiredVehicleInfo.value
  && selectedServices.value.length > 0
  && selectedWorkers.value.length > 0
  && hasValidShare.value
  && (!isPieceWash.value || pieceDetails.value.trim().length > 0)
  && (!isPlateBlocked.value || blockedPlatePaymentConfirmed.value)
))

const isTempServiceSelected = (id) => tempSelectedServiceIds.value.includes(Number(id))
const openServicePicker = () => {
  if (isPieceWash.value) return
  tempSelectedServiceIds.value = [...selectedServiceIds.value]
  isServicePickerOpen.value = true
}
const closeServicePicker = () => {
  isServicePickerOpen.value = false
}
const confirmServicePicker = () => {
  selectedServiceIds.value = [...tempSelectedServiceIds.value]
  closeServicePicker()
}
const toggleTempService = (id) => {
  const normalizedId = Number(id)
  if (isTempServiceSelected(normalizedId)) {
    tempSelectedServiceIds.value = tempSelectedServiceIds.value.filter((item) => Number(item) !== normalizedId)
    return
  }
  tempSelectedServiceIds.value = [...tempSelectedServiceIds.value, normalizedId]
}
const openInitialServicePicker = () => {
  if (hasOpenedInitialServicePicker.value || isPieceWash.value || !services.value.length) return
  hasOpenedInitialServicePicker.value = true
  openServicePicker()
}

const workerStatus = (worker) => {
  if (!isWorkerPresent(worker)) return { key: 'off', label: 'خارج از شیفت' }
  if (worker.is_available === false || worker.load_status === 'busy') return { key: 'busy', label: 'مشغول' }
  if (worker.load_status === 'normal' || Number(worker.active_jobs_count || 0) > 0) return { key: 'normal', label: 'در حال کار' }
  return { key: 'free', label: 'آزاد' }
}

const isWorkerSelected = (id) => selectedWorkerIds.value.includes(Number(id))
const isPrimaryWorker = (id) => Number(primarySelectedWorker.value?.id) === Number(id)
const isQueueFront = (id) => Number(queueFrontWorkerId.value) === Number(id)
const getWorkerSharePercent = (id) => Math.max(0, Math.min(100, Number(workerSharePercents.value[Number(id)] || 0)))
const toggleWorker = (id) => {
  const normalizedId = Number(id)
  if (isWorkerSelected(normalizedId)) {
    selectedWorkerIds.value = selectedWorkerIds.value.filter((item) => Number(item) !== normalizedId)
    return
  }
  selectedWorkerIds.value = [...selectedWorkerIds.value, normalizedId]
}
const adjustServicePrice = (serviceId, direction) => {
  const normalizedId = Number(serviceId || 0)
  if (!normalizedId) return
  const service = services.value.find((item) => Number(item.id) === normalizedId)
  if (!service) return
  const step = 5000
  const current = Number(servicePriceAdjustments.value[normalizedId] || 0)
  const next = direction === 'increase' ? current + step : current - step
  const minAdjustment = -Math.max(0, Number(service.base_price || 0))
  servicePriceAdjustments.value = {
    ...servicePriceAdjustments.value,
    [normalizedId]: Math.max(minAdjustment, next)
  }
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

const formatQueueTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('fa-IR', {
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

const resolveWorkerPaymentConfig = (worker) => {
  if (!worker) return { type: 'percent', value: 0 }
  const paymentType = worker.payment_type || ((Number(worker.default_fixed_wage || 0) > 0) ? 'fixed' : 'percent')
  const paymentValue = Math.max(0, Number(worker.payment_value || 0))
  return {
    type: paymentType === 'fixed' ? 'fixed' : paymentType === 'hourly' ? 'fixed' : 'percent',
    value: paymentValue
  }
}

const applyWorkerPaymentDefaults = (workersList = selectedWorkers.value) => {
  const normalizedWorkers = Array.isArray(workersList) ? workersList.filter(Boolean) : []
  if (!normalizedWorkers.length) {
    shareType.value = 'percent'
    shareValueInput.value = '0'
    return
  }
  const configs = normalizedWorkers.map(resolveWorkerPaymentConfig)
  const uniqueTypes = [...new Set(configs.map((item) => item.type))]
  const resolvedType = uniqueTypes.length === 1 ? uniqueTypes[0] : configs[0].type
  const averageValue = configs.length
    ? configs.reduce((sum, item) => sum + Number(item.value || 0), 0) / configs.length
    : 0
  shareType.value = resolvedType === 'fixed' ? 'fixed' : 'percent'
  shareValueInput.value = String(Number(averageValue.toFixed(2)))
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
      plateType: vehicle.plateType,
      tariffType: vehicle.tariffType,
      model: vehicle.model,
      color: vehicle.color,
      driver: vehicle.driver,
      mobile: vehicle.mobile,
      smsNotificationsEnabled: normalizedVehicle.value.smsAutoSendEnabled !== false && smsNotificationsEnabled.value,
      note: vehicle.note,
      isPieceWash: vehicle.isPieceWash,
      pieceDetails: pieceDetails.value.trim(),
      aiSessionId: vehicle.aiSessionId,
      aiRawText: vehicle.aiRawText,
      aiPersianText: vehicle.aiPersianText,
      aiConvertedPlate: vehicle.aiConvertedPlate,
      aiConvertedPlateLeft: vehicle.aiConvertedPlateLeft,
      aiConvertedPlateLetter: vehicle.aiConvertedPlateLetter,
      aiConvertedPlateMid: vehicle.aiConvertedPlateMid,
      aiConvertedPlateRight: vehicle.aiConvertedPlateRight,
      aiConvertedPlateType: vehicle.aiConvertedPlateType,
      aiImageBase64: vehicle.aiImageBase64,
      aiConfidence: vehicle.aiConfidence,
      aiLatencyMs: vehicle.aiLatencyMs
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
          price: Number(item.manual_adjustment || 0) < 0 ? Number(item.base_price || 0) : Number((item.adjusted_price ?? item.base_price) || 0),
          discount_amount: Number(item.manual_adjustment || 0) < 0 ? Math.abs(Number(item.manual_adjustment || 0)) : 0
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
    manual_discount_total: effectiveManualDiscountTotal.value,
    apply_loyalty_discount: applyLoyaltyDiscount.value,
    blocked_plate_payment_confirmed: blockedPlatePaymentConfirmed.value
  }
}

const preInvoiceCarwashTitle = computed(() => {
  const name = String(carwashName.value || '').trim() || 'کارواش'
  return name.startsWith('کارواش') ? name : `کارواش ${name}`
})
const preInvoiceHeaderNote = computed(() => {
  const phonePattern = /(?:\+?98|0)?9[\d۰-۹٠-٩\s\-()]{8,}|0[1-8][\d۰-۹٠-٩\s\-()]{7,}/
  return String(receiptHeaderNote.value || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !phonePattern.test(line) && !/(تلفن|تماس|موبایل)/.test(line))
    .join('\n')
})
const preInvoicePaperWidthLabel = computed(() => (preInvoicePaperWidth.value === '58mm' ? '۵۸ میلی‌متر' : '۸۰ میلی‌متر'))
const preInvoiceReceiptStyle = computed(() => ({ width: preInvoicePaperWidth.value === '58mm' ? '58mm' : '80mm' }))
const preInvoiceAdmissionNumber = computed(() => {
  const raw = props.vehicleInfo?.admission_number || props.vehicleInfo?.admissionNumber || props.vehicleInfo?.id || ''
  return raw ? Number(raw).toLocaleString('fa-IR') : 'بعد از ثبت'
})
const preInvoiceIssuedAt = computed(() => new Intl.DateTimeFormat('fa-IR', {
  dateStyle: 'short',
  timeStyle: 'short'
}).format(new Date()))
const preInvoicePlateLabel = computed(() => {
  if (isPieceWash.value) return 'قطعه‌شویی'
  const parts = plateParts.value
  if (typeof parts === 'string') return parts
  return `${parts.right} ${parts.letter} ${parts.mid} - ${parts.left}`
})
const openPreInvoiceModal = () => {
  preInvoiceModalOpen.value = true
}
const closePreInvoiceModal = () => {
  preInvoiceModalOpen.value = false
}
const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#039;')
const preInvoiceRowsHtml = computed(() => selectedServices.value.map((service, index) => `
  <tr>
    <td>${escapeHtml(toFaNumber(index + 1))}. ${escapeHtml(service.name)}</td>
  </tr>
`).join(''))
const printPreInvoice = () => {
  const width = preInvoicePaperWidth.value === '58mm' ? '58mm' : '80mm'
  const popup = window.open('', '_blank', 'width=420,height=720')
  if (!popup) return
  popup.document.write(`<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>خدمات</title>
  <style>
    @page { size: ${width} auto; margin: 3mm; }
    * { box-sizing: border-box; color: #000 !important; font-weight: 900; }
    body { margin: 0; background: #fff; color: #000; font-family: Vazirmatn, Tahoma, Arial, sans-serif; direction: rtl; }
    .receipt { width: ${width}; max-width: ${width}; padding: 3mm; font-size: 11px; line-height: 1.75; }
    header, footer { text-align: center; display: grid; gap: 2px; padding-bottom: 6px; border-bottom: 1px dashed #111827; }
    footer { margin-top: 8px; padding-top: 6px; padding-bottom: 0; border-top: 1px dashed #111827; border-bottom: 0; }
    header strong { font-size: 14px; font-weight: 900; }
    header span { font-weight: 900; }
    .info, .totals { display: grid; gap: 3px; padding: 7px 0; border-bottom: 1px dashed #111827; }
    p { margin: 0; display: flex; justify-content: space-between; gap: 8px; }
    table { width: 100%; border-collapse: collapse; margin: 7px 0; }
    th, td { padding: 4px 0; border-bottom: 1px solid #111827; text-align: right; vertical-align: top; }
  </style>
</head>
<body>
  <article class="receipt">
    <header>
      <strong>${escapeHtml(preInvoiceCarwashTitle.value)}</strong>
      ${preInvoiceHeaderNote.value ? `<small>${escapeHtml(preInvoiceHeaderNote.value)}</small>` : ''}
      <span>خدمات</span>
    </header>
    <section class="info">
      <p><span>شماره پذیرش</span><strong>${escapeHtml(preInvoiceAdmissionNumber.value)}</strong></p>
      <p><span>زمان</span><strong>${escapeHtml(preInvoiceIssuedAt.value)}</strong></p>
      <p><span>مشتری</span><strong>${escapeHtml(vehicleDriver.value || 'مشتری حضوری')}</strong></p>
      <p><span>خودرو</span><strong>${escapeHtml(vehicleTitle.value)}</strong></p>
      <p><span>پلاک</span><strong>${escapeHtml(preInvoicePlateLabel.value)}</strong></p>
    </section>
    <table>
      <thead><tr><th>شرح</th></tr></thead>
      <tbody>${preInvoiceRowsHtml.value}</tbody>
    </table>
    <footer>
      ${receiptFooterNote.value ? `<p>${escapeHtml(receiptFooterNote.value)}</p>` : ''}
      <strong>از اعتماد شما سپاسگزاریم</strong>
    </footer>
  </article>
  <script>window.onload = () => { window.focus(); window.print(); }<\/script>
</body>
</html>`)
  popup.document.close()
}

const onAssign = () => {
  if (!canAssign.value || props.submitting || actionLocked.value) return
  actionLocked.value = true
  emit('assign', buildPayload())
}

const hydrateFromVehicleInfo = () => {
  const vehicle = normalizedVehicle.value
  const nextVehicleKey = [
    vehicle.id || '',
    vehicle.plateLeft,
    vehicle.plateLetter,
    vehicle.plateMid,
    vehicle.plateRight,
    vehicle.isPieceWash ? 'piece' : 'vehicle'
  ].join('|')
  if (nextVehicleKey !== activeVehicleKey.value) {
    activeVehicleKey.value = nextVehicleKey
    hasOpenedInitialServicePicker.value = false
    isServicePickerOpen.value = false
  }
  selectedServiceIds.value = [...new Set(vehicle.serviceIds.map((id) => Number(id)).filter((id) => !Number.isNaN(id)))]
  tempSelectedServiceIds.value = [...selectedServiceIds.value]
  servicePriceAdjustments.value = {}
  selectedWorkerIds.value = [...new Set((vehicle.staffIds || []).map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0))]
  blockedPlatePaymentConfirmed.value = false
  smsNotificationsEnabled.value = vehicle.smsAutoSendEnabled !== false && vehicle.smsNotificationsEnabled !== false
  applyLoyaltyDiscount.value = props.vehicleInfo?.apply_loyalty_discount !== false && props.vehicleInfo?.applyLoyaltyDiscount !== false
  pieceDetails.value = vehicle.pieceDetails || ''
  pieceWashPrice.value = isPieceWash.value ? Math.max(0, Number(vehicle.pieceWashPrice || 0)) : 0
  const existingWorkerSharePercents = (vehicle.staffMembers || []).reduce((accumulator, item) => {
    if (item.id > 0) accumulator[item.id] = Math.max(0, Math.min(100, Number(item.worker_share_percent || 0)))
    return accumulator
  }, {})
  workerSharePercents.value = normalizeWorkerSharePercents(selectedWorkerIds.value, existingWorkerSharePercents)
  ensureDefaultWorkerSelection()
  openInitialServicePicker()
}

watch(() => normalizedVehicle.value.smsAutoSendEnabled, (enabled) => {
  if (enabled === false) {
    smsNotificationsEnabled.value = false
    return
  }
  if (normalizedVehicle.value.smsNotificationsEnabled !== false) {
    smsNotificationsEnabled.value = true
  }
})

const ensureDefaultWorkerSelection = () => {
  if (selectedWorkerIds.value.length || !workers.value.length) return
  if (queueFrontWorkerId.value) {
    selectedWorkerIds.value = [Number(queueFrontWorkerId.value)]
  }
}

const loadInitialData = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const [serviceResp, workerResp] = await Promise.all([
      api.get('/services/', {
        params: {
          plate_type: normalizedVehicle.value.plateType,
          tariff_type: normalizedVehicle.value.tariffType,
        },
      }),
      api.get('/workers/')
    ])
    services.value = (Array.isArray(serviceResp.data) ? serviceResp.data : [])
      .filter((item) => item.is_active !== false)
      .map((item) => ({
        ...item,
        base_price: Number((item.resolved_sale_price ?? item.base_price) || 0),
        list_price: Number((item.resolved_list_price ?? item.base_price) || 0),
        estimated_duration_minutes: Number((item.resolved_duration_minutes ?? item.estimated_duration_minutes) || 0),
      }))
      .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0))

    workers.value = (Array.isArray(workerResp.data) ? workerResp.data : [])
      .filter(isWashAssignableWorker)
    try {
      const settingsResp = await api.get('/services/general-settings/')
      receiptHeaderNote.value = settingsResp.data?.receipt_header_note || ''
      receiptFooterNote.value = settingsResp.data?.receipt_footer_note || ''
      carwashName.value = settingsResp.data?.tenant_name || settingsResp.data?.carwash_name || ''
      const paperWidth = String(settingsResp.data?.receipt_printer_paper_width || '80mm').toLowerCase()
      preInvoicePaperWidth.value = paperWidth === '58mm' ? '58mm' : '80mm'
    } catch {
      receiptHeaderNote.value = ''
      receiptFooterNote.value = ''
    }

    const validServiceIds = new Set(services.value.map((item) => Number(item.id)))
    selectedServiceIds.value = selectedServiceIds.value.filter((id) => validServiceIds.has(Number(id)))
    tempSelectedServiceIds.value = tempSelectedServiceIds.value.filter((id) => validServiceIds.has(Number(id)))
    if (isPieceWash.value && pieceWashPrice.value <= 0) {
      const pieceWashService = services.value.find((item) => String(item.name || '').trim() === 'قطعه‌شویی')
      pieceWashPrice.value = Number(pieceWashService?.base_price || 0)
    }

    const validWorkerIds = new Set(workers.value.map((item) => Number(item.id)))
    selectedWorkerIds.value = selectedWorkerIds.value.filter((id) => validWorkerIds.has(Number(id)))
    ensureDefaultWorkerSelection()
    openInitialServicePicker()
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بارگذاری اطلاعات خدمات و پرسنل ناموفق بود.')
  } finally {
    loading.value = false
  }
}

watch(() => props.vehicleInfo, hydrateFromVehicleInfo, { immediate: true, deep: true })
watch(() => props.submitting, (value) => {
  if (!value) actionLocked.value = false
})
watch(selectedWorkers, (workersList) => {
  applyWorkerPaymentDefaults(workersList)
}, { immediate: true, deep: true })
watch(selectedWorkerPercentIds, (ids) => {
  workerSharePercents.value = normalizeWorkerSharePercents(ids, workerSharePercents.value)
}, { immediate: true })

onMounted(loadInitialData)
</script>

<style scoped>
.step-two {
  background:
    radial-gradient(circle at top right, rgba(30, 111, 217, 0.08), transparent 22%),
    linear-gradient(180deg, #edf5ff 0%, #f7f9fb 100%);
  display: flex;
  flex-direction: column;
  height: auto;
  min-height: 0;
  overflow: visible;
}

.step-two-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 28px;
  border-bottom: 1px solid rgba(212, 228, 255, 0.92);
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 4;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 22px;
}

.header-copy {
  display: grid;
  gap: 4px;
}

.header-copy h3 {
  margin: 0;
  font-size: 20px;
  color: #191c1e;
}

.header-copy p {
  margin: 0;
  color: #475569;
  font-size: 12px;
  line-height: 1.8;
}

.plate-badge {
  display: flex;
  align-items: stretch;
  border-radius: 10px;
  overflow: hidden;
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

.service-picker-overlay {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(15, 23, 42, 0.42);
}

.service-picker-panel {
  width: min(1180px, 100%);
  max-height: calc(100vh - 32px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(191, 215, 255, 0.92);
  border-radius: 26px;
  background:
    radial-gradient(circle at top right, rgba(0, 88, 190, 0.1), transparent 26%),
    #ffffff;
  box-shadow: 0 16px 42px -28px rgba(15, 23, 42, 0.7);
  overflow: hidden;
}

.pre-invoice-panel {
  width: min(760px, 100%);
  max-height: calc(100vh - 32px);
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(191, 215, 255, 0.92);
  border-radius: 24px;
  background: #f8fafc;
  box-shadow: 0 16px 42px -28px rgba(15, 23, 42, 0.7);
  overflow: hidden;
}

.pre-invoice-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.invoice-format-chip {
  min-height: 48px;
  border: 1px solid #dbe7f3;
  border-radius: 14px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  padding: 8px 12px;
  display: grid;
  gap: 2px;
  text-align: right;
}

.invoice-format-chip.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.invoice-format-chip span {
  font-size: 11px;
  color: #64748b;
}

.pre-invoice-preview-shell {
  min-height: 0;
  overflow: auto;
  display: grid;
  justify-items: center;
  padding: 14px;
  border-radius: 18px;
  background: #e5e7eb;
}

.pre-invoice-receipt {
  max-width: 100%;
  background: #fff;
  color: #000;
  padding: 12px;
  font-size: 11px;
  line-height: 1.8;
  font-weight: 900;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.12);
}

.pre-invoice-receipt * {
  color: #000 !important;
  font-weight: 900;
}

.pre-invoice-receipt header,
.pre-invoice-receipt footer {
  display: grid;
  gap: 3px;
  text-align: center;
  padding-bottom: 8px;
  border-bottom: 1px dashed #111827;
}

.pre-invoice-receipt footer {
  margin-top: 8px;
  padding-top: 8px;
  padding-bottom: 0;
  border-top: 1px dashed #111827;
  border-bottom: 0;
}

.pre-invoice-receipt header strong {
  font-size: 14px;
  font-weight: 900;
}

.pre-invoice-receipt header span {
  font-weight: 900;
}

.receipt-info-grid,
.receipt-total-block {
  display: grid;
  gap: 3px;
  padding: 8px 0;
  border-bottom: 1px dashed #111827;
}

.receipt-info-grid p,
.receipt-total-block p {
  margin: 0;
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.pre-invoice-table {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
}

.pre-invoice-table th,
.pre-invoice-table td {
  padding: 4px 0;
  border-bottom: 1px solid #111827;
  vertical-align: top;
  font-weight: 900;
}

.pre-invoice-table th:last-child,
.pre-invoice-table td:last-child {
  text-align: left;
  white-space: nowrap;
}

.receipt-final {
  font-size: 12px;
  font-weight: 900;
  border-top: 1px solid #111827;
  padding-top: 5px;
  margin-top: 3px !important;
}

.loyalty-discount-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 10px;
  border: 1px solid #dbe7f3;
  border-radius: 14px;
  background: #ffffff;
  contain: layout;
  overflow-anchor: none;
}

.loyalty-discount-card.active {
  border-color: #93c5fd;
  background: #eff6ff;
}

.loyalty-discount-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.loyalty-discount-copy span {
  color: #475569;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.loyalty-discount-copy strong,
.loyalty-discount-card b {
  color: #0f172a;
  font-size: 12px;
  font-weight: 900;
}

.loyalty-discount-card b {
  white-space: nowrap;
}

.loyalty-discount-toggle {
  width: 42px;
  height: 24px;
  border: 0;
  padding: 0;
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.loyalty-discount-toggle span {
  width: 42px;
  height: 24px;
  border-radius: 999px;
  background: #cbd5e1;
  position: relative;
  flex: 0 0 auto;
  transition: background 0.18s ease;
}

.loyalty-discount-toggle span::after {
  content: '';
  position: absolute;
  top: 3px;
  right: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.22);
  transition: transform 0.18s ease;
}

.loyalty-discount-toggle[aria-checked="true"] span {
  background: #2563eb;
}

.loyalty-discount-toggle[aria-checked="true"] span::after {
  transform: translateX(-18px);
}

.service-picker-head,
.service-picker-foot,
.service-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.service-picker-head h4 {
  margin: 0;
  color: #0f172a;
  font-size: 22px;
}

.service-picker-head p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.service-picker-grid {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  justify-content: flex-start;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
}

.service-bubble {
  flex: 0 0 auto;
  min-width: fit-content;
  max-width: 100%;
  min-height: 36px;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 999px;
  background: linear-gradient(180deg, #ffffff, #f8fbff);
  color: #263241;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 14px;
  line-height: 1.4;
  white-space: normal;
}

.service-bubble.selected {
  border-color: #0058be;
  background: linear-gradient(180deg, #0b6bdc, #0058be);
  color: #ffffff;
  box-shadow: 0 10px 22px -16px rgba(0, 88, 190, 0.65);
}

.edit-services-btn {
  border: 1px solid rgba(0, 88, 190, 0.18);
  border-radius: 12px;
  background: #e6f1ff;
  color: #0058be;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  padding: 8px 14px;
}

.edit-services-btn:hover {
  background: #dbeafe;
}

.step-two-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1.15fr) minmax(0, 0.95fr);
  gap: 16px;
  padding: 18px;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.col {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  border: 1px solid rgba(199, 220, 255, 0.92);
  border-radius: 26px;
  overflow: hidden;
  box-shadow: 0 22px 46px -38px rgba(15, 23, 42, 0.45);
}

.services-col,
.staff-col {
  border-left: 0;
}

.services-col {
  background:
    radial-gradient(circle at top, rgba(65, 211, 255, 0.1), transparent 32%),
    linear-gradient(180deg, #f8fbff, #eff6ff);
}

.staff-col {
  background:
    radial-gradient(circle at top, rgba(148, 163, 184, 0.09), transparent 34%),
    linear-gradient(180deg, #f8fbff, #f1f6ff);
}

.summary-col {
  background: rgba(255, 255, 255, 0.94);
}

.col-head {
  padding: 20px 20px 14px;
  display: grid;
  gap: 12px;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(212, 228, 255, 0.86);
}

.col-head h4,
.summary-head h4 {
  margin: 0;
  color: #191c1e;
  font-size: 22px;
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
  height: 46px;
  border: 1px solid rgba(191, 215, 255, 0.9);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
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
  padding: 16px 20px 20px;
  overflow-y: auto;
  overflow-x: hidden;
  display: grid;
  gap: 12px;
}

.service-card {
  position: relative;
  border: 1px solid rgba(191, 215, 255, 0.88);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.88);
  padding: 14px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  cursor: pointer;
  box-shadow: 0 18px 32px -30px rgba(15, 23, 42, 0.28);
  min-width: 0;
}

.listed-service-card {
  cursor: default;
}

.service-card input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.checkmark,
.worker-jobs,
.worker-share-readonly {
  display: none !important;
}

.service-card.selected {
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.96), rgba(219, 234, 254, 0.72));
  border: 2px solid #0058be;
  border-right-width: 5px;
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

.service-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 8px;
}

.service-body p {
  margin: 0;
  color: #424754;
  font-size: 13px;
  line-height: 1.7;
  overflow-wrap: anywhere;
  flex: 1;
  min-width: 0;
}

.service-adjuster {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-shrink: 0;
}

.service-adjust-btn {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(59, 130, 246, 0.22);
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #dbeafe 100%);
  color: #fff;
  color: #0f3a8a;
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.14);
}

.service-adjust-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(29, 78, 216, 0.4);
  background: linear-gradient(180deg, #eff6ff 0%, #bfdbfe 100%);
}

.service-adjust-btn:active {
  transform: translateY(0);
}

.service-adjust-summary {
  padding: 8px 10px;
  border-radius: 12px;
}

.increase-row {
  background: rgba(220, 252, 231, 0.9);
  color: #166534;
}

.decrease-row {
  background: rgba(254, 242, 242, 0.92);
  color: #b91c1c;
}

.increase-row strong,
.decrease-row strong {
  color: inherit;
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
  width: 100%;
  max-width: 160px;
}
.unit-note {
  color: #64748b;
  font-size: 11px;
}

.piece-wash-box {
  border: 1px solid rgba(191, 215, 255, 0.9);
  border-radius: 22px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.9);
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
  border: 1px solid rgba(191, 215, 255, 0.88);
  border-radius: 22px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.88);
  cursor: pointer;
  box-shadow: 0 18px 32px -30px rgba(15, 23, 42, 0.28);
}

.worker-card.selected {
  border: 2px solid #0058be;
  border-right-width: 5px;
  background: linear-gradient(180deg, rgba(232, 244, 255, 0.98), rgba(219, 234, 254, 0.92));
  box-shadow: 0 16px 28px -22px rgba(0, 88, 190, 0.35);
}

.worker-card.queue-front {
  background: linear-gradient(180deg, rgba(240, 253, 250, 0.96), rgba(236, 253, 245, 0.86));
  border-color: rgba(20, 184, 166, 0.55);
}

.worker-card.selected.queue-front {
  border-color: #0058be;
  background: linear-gradient(180deg, rgba(232, 244, 255, 0.98), rgba(219, 234, 254, 0.92));
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

.status-off {
  background: rgba(100, 116, 139, 0.12);
  color: #475569;
}

.status-off .status-dot {
  background: #64748b;
}

.worker-queue-meta {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)) auto;
  align-items: center;
  gap: 8px;
  color: #475569;
  font-size: 12px;
}

.worker-queue-meta span {
  min-width: 0;
}

.worker-queue-meta strong {
  color: #0f172a;
}

.queue-front-pill {
  border-radius: 999px;
  padding: 4px 9px;
  background: #ccfbf1;
  color: #0f766e;
  font-weight: 800;
  justify-self: end;
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
  padding: 20px 20px 16px;
  border-bottom: 1px solid rgba(212, 228, 255, 0.88);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.summary-invoice-btn {
  height: 38px;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 900;
  padding: 0 14px;
  cursor: pointer;
}

.summary-invoice-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.summary-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 18px 20px;
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
  min-width: 0;
}

.summary-row strong {
  color: #191c1e;
}

.summary-row span,
.summary-row strong {
  min-width: 0;
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
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

.net-row {
  background: rgba(14, 165, 233, 0.08);
  border-radius: 12px;
  padding: 11px;
  color: #0f4c81;
}

.net-row strong {
  color: #0f4c81;
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
  border-top: 1px solid rgba(212, 228, 255, 0.88);
  padding: 16px 20px 18px;
  display: grid;
  gap: 10px;
  background: rgba(255, 255, 255, 0.96);
}

.summary-foot-actions {
  display: grid;
  grid-template-columns: minmax(0, 132px) minmax(0, 1fr);
  gap: 10px;
}

.sms-notification-check,
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

.sms-notification-check {
  align-items: flex-start;
  border-color: #cfe1ff;
  background: linear-gradient(180deg, #ffffff, #f4f9ff);
  color: #0f172a;
}

.sms-notification-check.disabled {
  opacity: .62;
}

.sms-notification-check span {
  display: grid;
  gap: 2px;
}

.sms-notification-check small {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.7;
}

.blocked-payment-check input {
  width: 18px;
  height: 18px;
}

.sms-notification-check input {
  width: 18px;
  height: 18px;
  margin-top: 2px;
}

.primary-btn {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 16px;
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
  border-radius: 16px;
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

  .service-picker-grid {
    justify-content: flex-start;
  }

  .services-col,
  .staff-col {
    border-left: none;
  }

  .summary-col {
    min-height: 380px;
  }
}

@media (max-width: 768px) {
  .service-picker-overlay {
    padding: 8px;
  }

  .service-picker-panel {
    max-height: calc(100vh - 16px);
    border-radius: 20px;
    gap: 10px;
    padding: 12px;
  }

  .service-picker-head h4 {
    font-size: 16px;
  }

  .service-picker-head p,
  .edit-services-btn {
    font-size: 11px;
  }

  .service-picker-grid {
    gap: 5px;
  }

  .service-bubble {
    min-height: 30px;
    padding: 4px 10px;
    font-size: 10px;
  }

  .step-two {
    padding: 10px;
    gap: 10px;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .step-two-header {
    padding: 14px 14px 12px;
    align-items: start;
    flex-direction: column;
    gap: 10px;
    border: 1px solid rgba(201, 220, 245, 0.92);
    border-radius: 24px;
    box-shadow: 0 18px 34px -28px rgba(15, 23, 42, 0.35);
  }

  .header-main {
    width: 100%;
    flex-direction: row;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .header-copy h3 {
    font-size: 16px;
  }

  .header-copy p {
    font-size: 10px;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
    gap: 8px;
  }

  .plate-badge {
    transform: scale(0.9);
    transform-origin: right center;
    flex-shrink: 0;
  }

  .vehicle-meta {
    min-width: 0;
  }

  .vehicle-meta h3 {
    font-size: 15px;
    line-height: 1.5;
  }

  .vehicle-meta p {
    margin-top: 4px;
    font-size: 11px;
    line-height: 1.6;
    flex-wrap: wrap;
  }

  .badge-muted {
    font-size: 10px;
    padding: 2px 8px;
  }

  .assigning-badge {
    padding: 7px 10px;
    font-size: 11px;
  }

  .icon-btn {
    width: 36px;
    height: 36px;
    font-size: 22px;
  }

  .step-two-grid {
    grid-template-columns: 1fr;
    gap: 10px;
    min-height: auto;
    flex: none;
    padding: 0;
    overflow: visible;
  }

  .col,
  .summary-col {
    min-height: auto;
    border-radius: 24px;
  }

  .services-col,
  .staff-col {
    background: rgba(255, 255, 255, 0.88);
  }

  .col-head,
  .col-list,
  .summary-head,
  .summary-body,
  .summary-foot {
    padding-right: 12px;
    padding-left: 12px;
  }

  .col-head,
  .summary-head {
    padding-top: 13px;
    padding-bottom: 10px;
    gap: 10px;
  }

  .services-col .col-list,
  .staff-col .col-list {
    max-height: none;
    overflow: visible;
    padding-bottom: 12px;
    gap: 10px;
  }

  .services-col .col-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .staff-col .col-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .summary-col {
    position: static;
    bottom: auto;
    z-index: auto;
    box-shadow: none;
  }

  .summary-body {
    max-height: none;
    overflow: visible;
    padding-bottom: 10px;
    gap: 10px;
  }

  .summary-foot {
    padding-top: 12px;
    position: static;
    bottom: auto;
    background: rgba(255, 255, 255, 0.96);
  }

  .search-box input {
    height: 38px;
    border-radius: 14px;
    padding: 0 10px;
    font-size: 12px;
  }

  .service-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: start;
    gap: 8px;
  }

  .worker-share {
    flex-direction: column;
    align-items: stretch;
  }

  .staff-title-row,
  .worker-top {
    display: grid;
    grid-template-columns: 1fr;
  }

  .summary-foot-actions {
    display: grid;
    grid-template-columns: minmax(0, .78fr) minmax(0, 1.22fr);
  }

  .worker-ident,
  .selected-worker-box {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    gap: 8px;
  }

  .selected-worker-box .worker-share-input,
  .selected-worker-box .worker-share-pill {
    grid-column: 1 / -1;
    justify-self: stretch;
  }

  .summary-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 8px;
  }

  .summary-row input {
    grid-column: 1 / -1;
    width: 100%;
  }

  .summary-row .unit-note {
    grid-column: 1 / -1;
  }

  .loyalty-discount-card {
    min-height: 50px;
    gap: 8px;
    padding: 8px;
    grid-template-columns: minmax(0, 1fr) 38px auto;
  }

  .loyalty-discount-copy span {
    font-size: 10px;
    font-weight: 500;
    line-height: 1.4;
  }

  .loyalty-discount-copy strong,
  .loyalty-discount-card b {
    font-size: 11px;
  }

  .loyalty-discount-toggle {
    width: 38px;
    height: 22px;
  }

  .loyalty-discount-toggle span {
    width: 38px;
    height: 22px;
  }

  .loyalty-discount-toggle span::after {
    width: 16px;
    height: 16px;
  }

  .loyalty-discount-toggle[aria-checked="true"] span::after {
    transform: translateX(-16px);
  }

  .col-head h4,
  .summary-head h4 {
    font-size: 16px;
  }

  .service-card,
  .worker-card,
  .piece-wash-box {
    padding: 10px;
    border-radius: 18px;
  }

  .service-head h5,
  .worker-ident h5,
  .piece-wash-box h5 {
    font-size: 14px;
  }

  .selected-worker-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .service-head strong,
  .service-body p,
  .empty,
  .error,
  .summary-row,
  .selected-worker-box small,
  .blocked-plate-note {
    font-size: 11px;
  }

  .worker-ident p,
  .service-discount-row label,
  .unit-note,
  .summary-body h6,
  .staff-title-row span {
    font-size: 10px;
  }

  .service-discount-row input,
  .share-value input,
  .totals input,
  .textarea-row textarea {
    width: 100%;
  }

  .service-discount-row input,
  .totals input,
  .share-value input {
    height: 32px;
    font-size: 12px;
  }

  .textarea-row textarea {
    min-height: 84px;
  }

  .avatar {
    width: 36px;
    height: 36px;
    font-size: 12px;
  }

  .avatar.small {
    width: 28px;
    height: 28px;
    font-size: 10px;
  }

  .worker-status,
  .worker-share-pill,
  .worker-share-input span {
    font-size: 10px;
  }

  .primary-btn,
  .secondary-foot-btn {
    height: 40px;
    font-size: 12px;
  }

}

@media (max-width: 480px) {
  .service-picker-grid {
    justify-content: flex-start;
  }

  .service-bubble {
    min-height: 28px;
    font-size: 9px;
  }

  .service-picker-foot {
    gap: 8px;
  }

  .step-two-header {
    padding: 10px 12px;
  }

  .header-main {
    align-items: start;
  }

  .header-copy h3 {
    font-size: 14px;
  }

  .header-copy p {
    font-size: 9px;
  }

  .col-head,
  .col-list,
  .summary-head,
  .summary-body,
  .summary-foot {
    padding-right: 10px;
    padding-left: 10px;
  }

  .service-card,
  .worker-card,
  .piece-wash-box {
    padding: 9px;
  }

  .services-col .col-list,
  .staff-col .col-list {
    max-height: none;
  }

  .services-col .col-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .staff-col .col-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .summary-body {
    max-height: none;
  }

  .service-head h5,
  .worker-ident h5,
  .piece-wash-box h5,
  .col-head h4,
  .summary-head h4 {
    font-size: 13px;
  }

  .service-head strong,
  .worker-jobs,
  .worker-share-readonly,
  .service-body p,
  .empty,
  .error,
  .summary-row,
  .selected-worker-box small,
  .blocked-plate-note {
    font-size: 10px;
  }

  .service-discount-row input,
  .totals input,
  .share-value input,
  .search-box input {
    height: 30px;
    font-size: 11px;
  }

  .textarea-row textarea {
    min-height: 72px;
  }

  .loyalty-discount-card {
    grid-template-columns: minmax(0, 1fr) 36px auto;
    gap: 6px;
  }

  .loyalty-discount-copy span {
    font-size: 9px;
    font-weight: 500;
  }

  .loyalty-discount-toggle,
  .loyalty-discount-toggle span {
    width: 36px;
    height: 21px;
  }

  .loyalty-discount-toggle span::after {
    width: 15px;
    height: 15px;
  }

  .loyalty-discount-toggle[aria-checked="true"] span::after {
    transform: translateX(-15px);
  }
}
</style>
