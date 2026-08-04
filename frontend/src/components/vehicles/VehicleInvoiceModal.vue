<template>
  <div v-if="open" class="invoice-modal-overlay" @click.self="emit('close')">
    <section class="modal-panel invoice-modal-panel">
      <header class="modal-head invoice-modal-head">
        <div>
          <h3>پیش‌نمایش فاکتور</h3>
          <p class="invoice-modal-subtitle">قالب چاپ را بین A4، A5 و فیش پرینتر عوض کنید و همان خروجی را برای PDF یا چاپ بگیرید.</p>
        </div>
        <button type="button" class="close-btn" @click="emit('close')">✕</button>
      </header>
      <div class="invoice-modal-body">
        <div class="invoice-format-toolbar">
          <div class="invoice-format-presets">
            <button
              v-for="option in invoicePresetOptions"
              :key="option.key"
              type="button"
              class="invoice-format-chip"
              :class="{ active: invoiceLayout.preset === option.key }"
              @click="invoiceLayout.preset = option.key"
            >
              <strong>{{ option.label }}</strong>
              <span>{{ option.hint }}</span>
            </button>
          </div>
          <div v-if="invoiceIsThermal" class="invoice-thermal-size-grid">
            <label>
              <span>عرض فیش (mm)</span>
              <input v-model.number="invoiceLayout.thermalWidthMm" type="number" min="48" max="120" step="1" />
            </label>
            <label>
              <span>طول فیش (mm)</span>
              <input v-model.number="invoiceLayout.thermalHeightMm" type="number" min="80" max="600" step="1" />
            </label>
          </div>
          <div class="invoice-modal-actions">
            <button type="button" class="secondary-btn" :disabled="loadingContext || invoiceGenerating" @click="downloadInvoicePdf">
              {{ invoiceGenerating ? 'در حال ساخت PDF...' : 'دانلود PDF' }}
            </button>
            <button type="button" class="secondary-btn" :disabled="loadingContext || invoiceGenerating" @click="printInvoiceHtml">
              {{ invoiceGenerating ? 'در حال چاپ...' : 'چاپ' }}
            </button>
          </div>
        </div>
        <div v-if="loadingContext" class="invoice-preview-loading">
          <BaseSpinner
            size="56px"
            color="#1d4ed8"
            ball-color="#60a5fa"
            label="در حال بارگذاری اطلاعات فاکتور..."
          />
        </div>
        <div v-show="!loadingContext" class="invoice-preview-frame-wrap">
          <div class="invoice-live-preview" :style="invoiceStageStyle">
            <div ref="invoiceTemplateRef" class="invoice-template" :style="invoiceTemplateStyle">
              <div class="invoice-sheet" :class="invoiceSheetClass" :style="invoiceSheetStyle">
          <template v-if="invoiceIsThermal">
            <header class="thermal-sheet-head">
              <strong>{{ invoiceCarwashTitle }}</strong>
              <small v-if="invoiceReceiptHeaderNote" class="receipt-custom-note">{{ invoiceReceiptHeaderNote }}</small>
            </header>

            <section class="thermal-info-grid">
              <p><span>شماره پذیرش:</span><strong>{{ invoiceAdmissionNumber }}</strong></p>
              <p><span>تاریخ:</span><strong>{{ invoiceIssuedAt }}</strong></p>
              <p><span>تعداد مراجعه:</span><strong>{{ Number(invoiceMeta.customerLoyaltyVisitCount || 0).toLocaleString('fa-IR') }}</strong></p>
              <p><span>امتیاز:</span><strong>{{ invoiceCustomerScoreLabel }}</strong></p>
              <p><span>تیپ نرخنامه:</span><strong>{{ invoiceTariffTypeNumber }}</strong></p>
              <p><span>مدل خودرو:</span><strong>{{ invoiceVehicleTitle }}</strong></p>
              <p><span>پلاک:</span><strong>{{ invoicePlateLabel }}</strong></p>
              <p><span>مشتری:</span><strong>{{ invoiceCustomerDisplayName }}</strong></p>
            </section>

            <section class="thermal-items-section">
              <table class="thermal-items-table">
                <thead>
                  <tr>
                    <th>شرح خدمات / کالا</th>
                    <th>مبلغ<br />(تومان)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(line, lineIndex) in invoiceServiceLines" :key="`thermal-service-${line.id || lineIndex}`">
                    <td>{{ Number(lineIndex + 1).toLocaleString('fa-IR') }}. {{ line.service_name }}</td>
                    <td>{{ moneyInputValue(invoiceServiceLineListTotal(line)) }}</td>
                  </tr>
                  <tr v-for="(product, productIndex) in invoiceProductLines" :key="`thermal-product-${product.id}`">
                    <td>{{ Number(invoiceServiceLines.length + productIndex + 1).toLocaleString('fa-IR') }}. {{ product.name }}</td>
                    <td>{{ moneyInputValue(product.total) }}</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <section class="thermal-total-block">
              <p><span>جمع کل</span><strong>{{ formatMoney(invoiceSubtotal) }}</strong></p>
              <p><span>جمع تخفیف</span><strong>{{ formatMoney(invoiceSummary.discountAmount) }}</strong></p>
              <p><span>انعام</span><strong>{{ formatMoney(invoiceSummary.tipAmount) }}</strong></p>
              <p v-if="invoiceSummary.taxAmount > 0"><span>مالیات</span><strong>{{ formatMoney(invoiceSummary.taxAmount) }}</strong></p>
              <p class="thermal-payable-total"><span>قیمت نهایی</span><strong>{{ formatMoney(invoiceSummary.finalTotal) }}</strong></p>
            </section>

            <footer class="thermal-sheet-footer">
              <p v-if="paymentBreakdownLabel">ترکیبی: {{ paymentBreakdownLabel }}</p>
              <p v-if="invoiceDueDateLabel">سررسید: {{ invoiceDueDateLabel }}</p>
              <p v-if="invoiceMeta.receiptFooterNote" class="receipt-custom-note">{{ invoiceMeta.receiptFooterNote }}</p>
              <strong>از اعتماد شما سپاسگزاریم</strong>
            </footer>
          </template>

          <template v-else>
            <header class="invoice-sheet-head">
              <div>
                <small>{{ invoiceCarwashContactLine || invoiceCarwashName }}</small>
                <small v-if="invoiceReceiptHeaderNote" class="receipt-custom-note">{{ invoiceReceiptHeaderNote }}</small>
                <strong>فاکتور نهایی سفارش</strong>
                <span>شماره فاکتور: {{ invoiceNumber }}</span>
              </div>
              <div class="invoice-sheet-meta">
                <strong>{{ invoiceCarwashTitle }}</strong>
                <span>تاریخ صدور: {{ invoiceIssuedAt }}</span>
                <span>تیپ نرخنامه: {{ invoiceTariffTypeNumber }}</span>
              </div>
            </header>

            <section class="invoice-identity-grid">
              <article>
                <small>اطلاعات مشتری</small>
                <p><span>نام</span><strong>{{ invoiceCustomerDisplayName }}</strong></p>
                <p><span>شماره تماس</span><strong>{{ invoiceCustomerPhone }}</strong></p>
                <p><span>امتیاز مشتری</span><strong>{{ formatCustomerScore(invoiceMeta.customerScore) }} | {{ customerScoreStars }}</strong></p>
                <p><span>درصد تخفیف امتیاز</span><strong>{{ Number(invoiceMeta.customerLoyaltyDiscountPercent || 0).toLocaleString('fa-IR') }}٪</strong></p>
                <p><span>تعداد مراجعات</span><strong>{{ Number(invoiceMeta.customerLoyaltyVisitCount || 0).toLocaleString('fa-IR') }}</strong></p>
              </article>
              <article>
                <small>مشخصات خودرو</small>
                <p><span>خودرو</span><strong>{{ invoiceVehicleTitle }}</strong></p>
                <p><span>پلاک</span><strong>{{ invoicePlateLabel }}</strong></p>
                <p><span>نوع پذیرش</span><strong>{{ invoiceAdmissionLabel }}</strong></p>
              </article>
              <article>
                <small>اطلاعات سفارش</small>
                <p><span>شماره پذیرش</span><strong>#{{ invoiceAdmissionNumber }}</strong></p>
                <p><span>وضعیت پرداخت</span><strong>{{ invoicePaymentStatusLabel }}</strong></p>
                <p><span>تاریخ ورود</span><strong>{{ invoiceCheckInLabel }}</strong></p>
              </article>
            </section>

            <section class="invoice-sheet-section">
              <div class="invoice-section-head">
                <strong>ریز خدمات انجام‌شده</strong>
              </div>
              <table class="invoice-table invoice-services-table">
                <thead>
                  <tr>
                    <th>عنوان</th>
                    <th>تعداد</th>
                    <th>مبلغ</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(line, lineIndex) in invoiceServiceLines" :key="`invoice-service-${line.id || lineIndex}`">
                    <td>{{ line.service_name }}</td>
                    <td>{{ Number(line.quantity || 1).toLocaleString('fa-IR') }}</td>
                    <td>{{ formatMoney(invoiceServiceLineListTotal(line)) }}</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <section v-if="invoiceProductLines.length" class="invoice-sheet-section">
              <div class="invoice-section-head">
                <strong>محصولات جانبی فروخته‌شده</strong>
              </div>
              <table class="invoice-table invoice-products-table">
                <thead>
                  <tr>
                    <th>عنوان</th>
                    <th>تعداد</th>
                    <th>قیمت واحد</th>
                    <th>مبلغ</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="product in invoiceProductLines" :key="`invoice-product-${product.id}`">
                    <td>{{ product.name }}</td>
                    <td>{{ Number(product.quantity || 0).toLocaleString('fa-IR') }}</td>
                    <td>{{ formatMoney(product.unitPrice) }}</td>
                    <td>{{ formatMoney(product.total) }}</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <section class="invoice-sheet-section invoice-payment-section">
              <div class="invoice-section-head">
                <strong>جزئیات پرداخت</strong>
              </div>
              <div class="invoice-payment-grid">
                <p><span>تیپ نرخنامه</span><strong>{{ invoiceTariffTypeNumber }}</strong></p>
                <p><span>وضعیت</span><strong>{{ invoicePaymentStatusLabel }}</strong></p>
                <p v-if="paymentBreakdownLabel"><span>پرداخت ترکیبی</span><strong>{{ paymentBreakdownLabel }}</strong></p>
                <p v-if="invoiceDueDateLabel"><span>سررسید</span><strong>{{ invoiceDueDateLabel }}</strong></p>
                <p v-if="invoiceChequeLabel"><span>اطلاعات چک</span><strong>{{ invoiceChequeLabel }}</strong></p>
              </div>
            </section>

            <section class="invoice-sheet-section invoice-total-section">
              <div class="invoice-section-head">
                <strong>خلاصه مالی مشتری</strong>
              </div>
              <div class="invoice-totals">
                <p><span>جمع کل</span><strong>{{ formatMoney(invoiceSubtotal) }}</strong></p>
                <p v-if="invoiceSummary.facilityDiscountAmount > 0"><span>تخفیف مجموعه</span><strong>{{ formatMoney(invoiceSummary.facilityDiscountAmount) }}</strong></p>
                <p v-if="invoiceSummary.customerDiscountAmount > 0"><span>تخفیف امتیاز مشتری</span><strong>{{ formatMoney(invoiceSummary.customerDiscountAmount) }}</strong></p>
                <p v-if="invoiceSummary.manualDiscountAmount > 0"><span>تخفیف دستی</span><strong>{{ formatMoney(invoiceSummary.manualDiscountAmount) }}</strong></p>
                <p><span>جمع تخفیف</span><strong>{{ formatMoney(invoiceSummary.discountAmount) }}</strong></p>
                <p><span>انعام</span><strong>{{ formatMoney(invoiceSummary.tipAmount) }}</strong></p>
                <p v-if="invoiceSummary.taxAmount > 0"><span>مالیات</span><strong>{{ formatMoney(invoiceSummary.taxAmount) }}</strong></p>
                <p class="invoice-grand-total"><span>قیمت نهایی</span><strong>{{ formatMoney(invoiceSummary.finalTotal) }}</strong></p>
              </div>
            </section>

            <footer class="invoice-sheet-footer">
              <p v-if="invoiceCustomerNote">توضیحات سفارش: {{ invoiceCustomerNote }}</p>
              <p v-if="invoiceMeta.receiptFooterNote" class="receipt-custom-note">{{ invoiceMeta.receiptFooterNote }}</p>
              <p>از اعتماد شما سپاسگزاریم</p>
            </footer>
          </template>
              </div>
            </div>
          </div>
        </div>
        <p v-if="invoiceErrorMessage" class="invoice-preview-error">{{ invoiceErrorMessage }}</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import BaseSpinner from '../base/BaseSpinner.vue'
import api from '../../services/api'
import { useAuthStore } from '../../store/auth.store'
import { formatThousandsToman, formatThousandsTomanValue } from '../../utils/money'
import { buildPlateNumber } from '../../utils/plate'
import { printHtmlElement, resolvePrintErrorMessage } from '../../utils/receiptPrinter'

const props = defineProps({
  open: { type: Boolean, default: false },
  vehicle: { type: Object, default: null }
})

const emit = defineEmits(['close'])
const authStore = useAuthStore()

const invoiceGenerating = ref(false)
const loadingContext = ref(false)
const invoicePdfUrl = ref('')
const invoiceErrorMessage = ref('')
const invoiceTemplateRef = ref(null)
const invoiceRenderTimer = ref(null)
const invoiceLayout = reactive({
  preset: 'a4',
  thermalWidthMm: 80,
  thermalHeightMm: 220
})
const invoiceMeta = reactive({
  serviceLines: [],
  productLines: [],
  customerScore: 0,
  customerLoyaltyVisitCount: 0,
  customerLoyaltyDiscountPercent: 0,
  receiptHeaderNote: '',
  receiptFooterNote: '',
  carwashAddress: '',
  managerPhone: '',
  receiptPrinterName: '',
  creditDueDate: '',
  chequeLabel: '',
  paymentBreakdownLabel: '',
  facilityDiscountAmount: 0,
  customerDiscountAmount: 0,
  manualDiscountAmount: 0,
  discountAmount: 0,
  tipAmount: 0,
  taxAmount: 0,
  finalTotal: 0,
  servicesTotal: 0,
  productsTotal: 0
})

const invoicePresetOptions = [
  { key: 'a4', label: 'A4', hint: 'فاکتور کامل' },
  { key: 'a5', label: 'A5', hint: 'جمع‌وجور' },
  { key: 'thermal', label: 'فیش', hint: 'پرینتر حرارتی' }
]

const moneyInputValue = (value) => formatThousandsTomanValue(value, { maximumFractionDigits: 0 })
const formatMoney = (value) => formatThousandsToman(value)
const formatCustomerScore = (score) => `${Number(score || 0).toLocaleString('fa-IR')} / ۵`
const paymentStatusLabel = (value) => ({
  unpaid: 'پرداخت نشده',
  partial: 'پرداخت ناقص',
  paid: 'پرداخت شده',
  refunded: 'مرجوع شده'
}[value] || 'در انتظار ثبت')

const sanitizeMillimeter = (value, fallback, min, max) => {
  const numeric = Number(value || 0)
  if (!Number.isFinite(numeric)) return fallback
  return Math.min(max, Math.max(min, numeric))
}

const invoiceIsThermal = computed(() => invoiceLayout.preset === 'thermal')
const invoiceThermalWidthMm = computed(() => sanitizeMillimeter(invoiceLayout.thermalWidthMm, 80, 48, 120))
const invoiceThermalHeightMm = computed(() => sanitizeMillimeter(invoiceLayout.thermalHeightMm, 220, 80, 600))
const invoicePageMetrics = computed(() => {
  if (invoiceLayout.preset === 'a5') {
    return {
      width: 138,
      minHeight: 200,
      padding: 4.5,
      gap: 6,
      margin: [5, 5, 5, 5],
      format: 'a5',
      printWidthMm: 148,
      printHeightMm: 210,
      printMarginMm: 5,
      thermal: false
    }
  }
  if (invoiceLayout.preset === 'thermal') {
    const paperWidth = invoiceThermalWidthMm.value
    const paperHeight = invoiceThermalHeightMm.value
    return {
      width: paperWidth,
      minHeight: Math.max(80, Math.min(paperHeight, 160)),
      padding: paperWidth <= 58 ? 1.6 : 2.2,
      gap: 4,
      margin: [1, 1, 1, 1],
      format: [paperWidth, paperHeight],
      printWidthMm: paperWidth,
      printHeightMm: null,
      printMarginMm: paperWidth <= 58 ? 1 : 1.5,
      printMinHeightMm: 80,
      thermal: true
    }
  }
  return {
    width: 198,
    minHeight: 285,
    padding: 5,
    gap: 7,
    margin: [6, 6, 6, 6],
    format: 'a4',
    printWidthMm: 210,
    printHeightMm: 297,
    printMarginMm: 6,
    thermal: false
  }
})
const invoicePrintPageOptions = computed(() => ({
  widthMm: invoicePageMetrics.value.printWidthMm,
  heightMm: invoicePageMetrics.value.printHeightMm,
  minHeightMm: invoicePageMetrics.value.printMinHeightMm || invoicePageMetrics.value.minHeight,
  marginMm: invoicePageMetrics.value.printMarginMm,
  thermal: Boolean(invoicePageMetrics.value.thermal)
}))
const invoiceSheetStyle = computed(() => ({
  width: `${invoicePageMetrics.value.width}mm`,
  maxWidth: `${invoicePageMetrics.value.width}mm`,
  minHeight: `${invoicePageMetrics.value.minHeight}mm`,
  padding: `${invoicePageMetrics.value.padding}mm`,
  gap: `${invoicePageMetrics.value.gap}px`
}))
const invoiceTemplateStyle = computed(() => ({
  width: `${invoicePageMetrics.value.width}mm`,
  maxWidth: `${invoicePageMetrics.value.width}mm`
}))
const invoiceStageStyle = computed(() => ({
  width: `${invoicePageMetrics.value.width}mm`
}))
const invoiceSheetClass = computed(() => ({
  'invoice-sheet-a5': invoiceLayout.preset === 'a5',
  'invoice-sheet-thermal': invoiceLayout.preset === 'thermal'
}))
const invoiceFileLabel = computed(() => (
  invoiceLayout.preset === 'thermal'
    ? `receipt-${props.vehicle?.id || 'carwash'}`
    : `invoice-${props.vehicle?.id || 'carwash'}`
))
const invoiceCarwashName = computed(() => (
  String(authStore.user?.tenant_name || '').trim() || 'کارواش'
))
const invoiceCarwashTitle = computed(() => {
  const name = invoiceCarwashName.value
  return name.startsWith('کارواش') ? name : `کارواش ${name}`
})
const invoiceCarwashContactLine = computed(() => {
  const parts = [
    String(invoiceMeta.carwashAddress || '').trim(),
    String(invoiceMeta.managerPhone || '').trim()
  ].filter(Boolean)
  return parts.join(' | ')
})
const invoiceReceiptHeaderNote = computed(() => String(invoiceMeta.receiptHeaderNote || '').trim())

const invoiceServiceLines = computed(() => {
  const lines = Array.isArray(invoiceMeta.serviceLines) ? invoiceMeta.serviceLines : []
  const completed = lines.filter((line) => Boolean(line?.is_completed))
  return completed.length ? completed : lines
})
const invoiceProductLines = computed(() => (
  Array.isArray(invoiceMeta.productLines) ? invoiceMeta.productLines : []
))
const invoiceServiceLineListTotal = (line) => (
  Number(line?.line_total || 0) + Number(line?.discount_amount || 0)
)
const invoiceSummary = computed(() => ({
  facilityDiscountAmount: Number(invoiceMeta.facilityDiscountAmount || 0),
  customerDiscountAmount: Number(invoiceMeta.customerDiscountAmount || 0),
  manualDiscountAmount: Number(invoiceMeta.manualDiscountAmount || 0),
  discountAmount: Number(invoiceMeta.discountAmount || 0),
  tipAmount: Number(invoiceMeta.tipAmount || 0),
  taxAmount: Number(invoiceMeta.taxAmount || 0),
  finalTotal: Number(invoiceMeta.finalTotal || 0),
  servicesTotal: Number(invoiceMeta.servicesTotal || 0),
  productsTotal: Number(invoiceMeta.productsTotal || 0)
}))
const invoiceSubtotal = computed(() => Number((
  invoiceSummary.value.servicesTotal + invoiceSummary.value.productsTotal
).toFixed(2)))

const invoiceAdmissionNumber = computed(() => Number(
  props.vehicle?.admission_number || props.vehicle?.admissionNumber || props.vehicle?.id || 0
).toLocaleString('fa-IR'))
const invoiceNumber = computed(() => `CW-${invoiceAdmissionNumber.value}`)
const invoiceTariffTypeNumber = computed(() => {
  const raw = String(props.vehicle?.tariff_type || props.vehicle?.tariffType || 'type_1').trim()
  const match = raw.match(/(\d+)/)
  return Number(match ? match[1] : 1).toLocaleString('fa-IR')
})
const invoiceCustomerName = computed(() => (
  String(props.vehicle?.driver_name || props.vehicle?.driverName || '').trim() || 'مشتری حضوری'
))
const invoiceCustomerDisplayName = computed(() => {
  const name = invoiceCustomerName.value
  const gender = String(props.vehicle?.driver_gender || props.vehicle?.driverGender || '').trim().toLowerCase()
  if (!name || name === 'مشتری حضوری') return name
  if (gender === 'male' && !/^(آقای|اقای)\s+/.test(name)) return `اقای ${name}`
  if (gender === 'female' && !/^خانم\s+/.test(name)) return `خانم ${name}`
  return name
})
const invoiceCustomerPhone = computed(() => (
  String(props.vehicle?.driver_phone || props.vehicle?.driverPhone || '').trim() || '-'
))
const invoiceCustomerScoreLabel = computed(() => (
  `${Number(invoiceMeta.customerScore || 0).toLocaleString('fa-IR')} از ۵`
))
const customerScoreStars = computed(() => (
  '★'.repeat(Math.round(Math.max(0, Math.min(5, Number(invoiceMeta.customerScore || 0))))) || '—'
))
const invoiceVehicleTitle = computed(() => {
  const model = String(props.vehicle?.car_model || props.vehicle?.model || '').trim()
  const color = String(props.vehicle?.car_color || props.vehicle?.colorName || '').trim()
  return `${model} ${color}`.trim() || 'قطعه‌شویی'
})
const invoicePlateLabel = computed(() => {
  const source = props.vehicle || {}
  const plateType = String(source.plate_type || source.plateType || '').trim()
  if (plateType === 'motorcycle') {
    return buildPlateNumber({
      plateType,
      mid: source.plate_mid || source.plateMid || '',
      letter: source.plate_letter || source.plateLetter || ''
    }) || String(source.plate_number || source.plateDisplay || '').trim() || 'قطعه‌شویی'
  }
  const right = String(source.plate_right || source.plateRight || '').trim()
  const letter = String(source.plate_letter || source.plateLetter || '').trim()
  const mid = String(source.plate_mid || source.plateMid || '').trim()
  const left = String(source.plate_left || source.plateLeft || '').trim()
  if (right && letter && mid && left) return `${right} ${letter} ${mid} - ${left}`
  return String(source.plate_number || source.plateDisplay || '').trim() || 'قطعه‌شویی'
})
const invoiceAdmissionLabel = computed(() => (
  props.vehicle?.is_piece_wash || props.vehicle?.isPieceWash ? 'قطعه‌شویی' : 'خودرو'
))
const invoiceCheckInLabel = computed(() => {
  const rawDate = props.vehicle?.check_in_at || props.vehicle?.checkInAt || props.vehicle?.created_at
  if (!rawDate) return '-'
  return new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(rawDate))
})
const invoicePaymentStatusLabel = computed(() => (
  invoiceSummary.value.finalTotal > 0
    ? paymentStatusLabel(props.vehicle?.payment_status)
    : 'تسویه شده'
))
const invoiceDueDateLabel = computed(() => String(invoiceMeta.creditDueDate || '').trim())
const invoiceChequeLabel = computed(() => String(invoiceMeta.chequeLabel || '').trim())
const paymentBreakdownLabel = computed(() => String(invoiceMeta.paymentBreakdownLabel || '').trim())
const invoiceCustomerNote = computed(() => (
  String(props.vehicle?.notes || props.vehicle?.note || '').trim()
))
const invoiceIssuedAt = computed(() => new Intl.DateTimeFormat('fa-IR', {
  dateStyle: 'medium',
  timeStyle: 'short'
}).format(new Date()))

const syncInvoiceLayoutFromPrinterSettings = (paperWidth) => {
  const value = String(paperWidth || '').trim().toLowerCase()
  if (value === 'a4') {
    invoiceLayout.preset = 'a4'
    return
  }
  if (value === 'a5') {
    invoiceLayout.preset = 'a5'
    return
  }
  invoiceLayout.preset = 'thermal'
  const mmMatch = value.match(/(\d+(?:\.\d+)?)\s*mm/)
  if (mmMatch) {
    invoiceLayout.thermalWidthMm = sanitizeMillimeter(Number(mmMatch[1]), 80, 48, 120)
  } else if (value === '58mm') {
    invoiceLayout.thermalWidthMm = 58
  } else {
    invoiceLayout.thermalWidthMm = 80
  }
}

const resetInvoiceMeta = () => {
  invoiceMeta.serviceLines = []
  invoiceMeta.productLines = []
  invoiceMeta.customerScore = 0
  invoiceMeta.customerLoyaltyVisitCount = 0
  invoiceMeta.customerLoyaltyDiscountPercent = 0
  invoiceMeta.receiptHeaderNote = ''
  invoiceMeta.receiptFooterNote = ''
  invoiceMeta.carwashAddress = ''
  invoiceMeta.managerPhone = ''
  invoiceMeta.receiptPrinterName = ''
  invoiceMeta.creditDueDate = ''
  invoiceMeta.chequeLabel = ''
  invoiceMeta.paymentBreakdownLabel = ''
  invoiceMeta.facilityDiscountAmount = 0
  invoiceMeta.customerDiscountAmount = 0
  invoiceMeta.manualDiscountAmount = 0
  invoiceMeta.discountAmount = 0
  invoiceMeta.tipAmount = 0
  invoiceMeta.taxAmount = 0
  invoiceMeta.finalTotal = 0
  invoiceMeta.servicesTotal = 0
  invoiceMeta.productsTotal = 0
}

const hydrateFromVehicleFallback = () => {
  const job = props.vehicle?.job || {}
  const serviceLines = Array.isArray(job.service_lines) ? job.service_lines : []
  const servicesTotal = Number(job.services_total || 0) || serviceLines.reduce(
    (sum, line) => sum + Number(line?.line_total || 0),
    0
  )
  const serviceListSubtotal = serviceLines.reduce(
    (sum, line) => sum + Number(line?.line_total || 0) + Number(line?.discount_amount || 0),
    0
  ) || (servicesTotal + Number(job.facility_discount_total || 0))
  const productsTotal = Number(job.products_total || 0)
  const facilityDiscountAmount = Number(job.facility_discount_total || 0)
  const customerDiscountAmount = Number(job.loyalty_discount_total || 0)
  const manualDiscountAmount = Number(job.manual_discount_total || 0)
  const discountAmount = Number(job.total_discount || job.discount_total || 0)
    || Number((facilityDiscountAmount + customerDiscountAmount + manualDiscountAmount).toFixed(2))
  const tipAmount = Number(job.tip_amount || 0)
  const taxAmount = Number(job.tax_total || 0)
  const finalTotal = Number(job.final_total || 0)
    || Math.max(0, serviceListSubtotal + productsTotal - discountAmount + taxAmount + tipAmount)

  invoiceMeta.serviceLines = serviceLines.map((line) => ({
    id: line.id,
    service_name: line.service_name,
    quantity: Number(line.quantity || 1),
    line_total: Number(line.line_total || 0),
    discount_amount: Number(line.discount_amount || 0),
    is_completed: line.is_completed !== false
  }))
  invoiceMeta.productLines = []
  invoiceMeta.customerScore = Number(props.vehicle?.customer_score || 0)
  invoiceMeta.customerLoyaltyVisitCount = Number(props.vehicle?.customer_loyalty_visit_count || 0)
  invoiceMeta.customerLoyaltyDiscountPercent = Number(props.vehicle?.customer_loyalty_discount_percent || 0)
  invoiceMeta.facilityDiscountAmount = facilityDiscountAmount
  invoiceMeta.customerDiscountAmount = customerDiscountAmount
  invoiceMeta.manualDiscountAmount = manualDiscountAmount
  invoiceMeta.discountAmount = discountAmount
  invoiceMeta.tipAmount = tipAmount
  invoiceMeta.taxAmount = taxAmount
  invoiceMeta.finalTotal = finalTotal
  invoiceMeta.servicesTotal = servicesTotal
  invoiceMeta.productsTotal = productsTotal
  invoiceMeta.paymentBreakdownLabel = ''
}

const loadInvoiceContext = async () => {
  const vehicleId = Number(props.vehicle?.id || 0)
  if (!vehicleId) {
    hydrateFromVehicleFallback()
    return
  }
  loadingContext.value = true
  invoiceErrorMessage.value = ''
  try {
    const [releaseResponse, settingsResponse] = await Promise.all([
      api.get(`/vehicles/${vehicleId}/release/`, { meta: { trackLoading: false } }),
      api.get('/services/general-settings/', { meta: { trackLoading: false } }).catch(() => ({ data: {} }))
    ])
    const data = releaseResponse?.data || {}
    const settings = settingsResponse?.data || {}
    const job = data?.job || {}
    const releaseVehicle = data?.vehicle || {}
    const storedJob = props.vehicle?.job || {}

    const serviceLines = Array.isArray(job.service_lines)
      ? job.service_lines.map((line) => ({
        id: line.id,
        service_name: line.service_name,
        quantity: Number(line.quantity || 1),
        line_total: Number(line.line_total || 0),
        discount_amount: Number(line.discount_amount || 0),
        is_completed: line.is_completed !== false
      }))
      : []

    const productLines = Array.isArray(job.product_lines)
      ? job.product_lines
        .map((line) => {
          const quantity = Number(line.quantity || 0)
          const unitPrice = Number(line.unit_price || 0)
          const total = Number(line.line_total || 0) || (quantity * unitPrice)
          return quantity > 0
            ? {
              id: line.id || line.product_id,
              name: line.product_name || line.name || 'محصول',
              quantity,
              unitPrice,
              total
            }
            : null
        })
        .filter(Boolean)
      : []

    const servicesTotal = Number(job.services_total || 0) || serviceLines.reduce(
      (sum, line) => sum + Number(line.line_total || 0),
      0
    )
    const serviceListSubtotal = Number(job.service_list_subtotal || 0)
      || serviceLines.reduce(
        (sum, line) => sum + Number(line.line_total || 0) + Number(line.discount_amount || 0),
        0
      )
      || (servicesTotal + Number(job.facility_discount_total || 0))
    const productsTotal = Number(job.products_total || 0)
      || productLines.reduce((sum, item) => sum + Number(item.total || 0), 0)
    const facilityDiscountAmount = Number(
      storedJob.facility_discount_total ?? job.facility_discount_total ?? 0
    )
    const customerDiscountAmount = Number(
      storedJob.loyalty_discount_total ?? job.loyalty_discount_total ?? 0
    )
    const manualDiscountAmount = Number(
      storedJob.manual_discount_total ?? job.manual_discount_total ?? 0
    )
    const discountAmount = Number(
      storedJob.total_discount
      ?? storedJob.discount_total
      ?? job.total_discount
      ?? job.discount_total
      ?? 0
    ) || Number((facilityDiscountAmount + customerDiscountAmount + manualDiscountAmount).toFixed(2))
    const tipAmount = Number(storedJob.tip_amount ?? job.tip_amount ?? 0)
    const taxEnabled = Boolean(settings.tax_enabled)
    const taxPercent = taxEnabled ? Math.max(0, Math.min(100, Number(settings.tax_percent || 0))) : 0
    const taxableTotal = Math.max(0, serviceListSubtotal + productsTotal - discountAmount)
    const computedTax = Number(((taxableTotal * taxPercent) / 100).toFixed(2))
    const taxAmount = Number(storedJob.tax_total || 0) || computedTax
    const computedFinal = Math.max(0, taxableTotal + taxAmount + tipAmount)
    const finalTotal = Number(storedJob.final_total || 0) || Number(job.final_total || 0) || computedFinal

    invoiceMeta.serviceLines = serviceLines
    invoiceMeta.productLines = productLines
    invoiceMeta.customerScore = Number(
      releaseVehicle.customer_score ?? props.vehicle?.customer_score ?? 0
    )
    invoiceMeta.customerLoyaltyVisitCount = Number(
      releaseVehicle.customer_loyalty_visit_count ?? props.vehicle?.customer_loyalty_visit_count ?? 0
    )
    invoiceMeta.customerLoyaltyDiscountPercent = Number(
      releaseVehicle.customer_loyalty_discount_percent ?? props.vehicle?.customer_loyalty_discount_percent ?? 0
    )
    invoiceMeta.receiptHeaderNote = settings.receipt_header_note || ''
    invoiceMeta.receiptFooterNote = settings.receipt_footer_note || ''
    invoiceMeta.carwashAddress = releaseVehicle.tenant_address
      || authStore.user?.tenant?.address
      || ''
    invoiceMeta.managerPhone = releaseVehicle.manager_phone || authStore.user?.phone || ''
    invoiceMeta.receiptPrinterName = settings.receipt_printer_name || ''
    invoiceMeta.facilityDiscountAmount = facilityDiscountAmount
    invoiceMeta.customerDiscountAmount = customerDiscountAmount
    invoiceMeta.manualDiscountAmount = manualDiscountAmount
    invoiceMeta.discountAmount = discountAmount
    invoiceMeta.tipAmount = tipAmount
    invoiceMeta.taxAmount = taxAmount
    invoiceMeta.finalTotal = finalTotal
    invoiceMeta.servicesTotal = servicesTotal
    invoiceMeta.productsTotal = productsTotal
    invoiceMeta.paymentBreakdownLabel = ''

    syncInvoiceLayoutFromPrinterSettings(settings.receipt_printer_paper_width || '80mm')
  } catch (error) {
    console.error('VehicleInvoiceModal loadInvoiceContext error:', error)
    hydrateFromVehicleFallback()
    invoiceErrorMessage.value = ''
  } finally {
    loadingContext.value = false
  }
}

const revokeInvoicePdfUrl = () => {
  if (invoicePdfUrl.value) {
    URL.revokeObjectURL(invoicePdfUrl.value)
    invoicePdfUrl.value = ''
  }
}

const buildInvoicePdf = async () => {
  if (!invoiceTemplateRef.value) return false
  invoiceGenerating.value = true
  invoiceErrorMessage.value = ''
  revokeInvoicePdfUrl()
  try {
    await nextTick()
    const html2pdfModule = await import('html2pdf.js')
    const html2pdf = html2pdfModule.default || html2pdfModule
    const worker = html2pdf()
      .set({
        margin: invoicePageMetrics.value.margin,
        filename: `${invoiceFileLabel.value}.pdf`,
        image: { type: 'png', quality: 1 },
        html2canvas: {
          scale: invoiceIsThermal.value ? 4 : 3,
          useCORS: true,
          backgroundColor: '#ffffff',
          logging: false,
          scrollX: 0,
          scrollY: 0,
          windowWidth: invoiceTemplateRef.value.scrollWidth,
          windowHeight: invoiceTemplateRef.value.scrollHeight
        },
        jsPDF: { unit: 'mm', format: invoicePageMetrics.value.format, orientation: 'portrait' },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      })
      .from(invoiceTemplateRef.value)
      .toPdf()
    const pdf = await worker.get('pdf')
    const blob = pdf.output('blob')
    invoicePdfUrl.value = URL.createObjectURL(blob)
    return true
  } catch (error) {
    console.error('VehicleInvoiceModal buildInvoicePdf error:', error)
    invoiceErrorMessage.value = 'ساخت فایل فاکتور ناموفق بود.'
    return false
  } finally {
    invoiceGenerating.value = false
  }
}

const downloadInvoicePdf = async () => {
  const ready = invoicePdfUrl.value ? true : await buildInvoicePdf()
  if (!ready || !invoicePdfUrl.value) return
  const anchor = document.createElement('a')
  anchor.href = invoicePdfUrl.value
  anchor.download = `${invoiceFileLabel.value}.pdf`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

const printInvoiceHtml = async () => {
  invoiceErrorMessage.value = ''
  if (!invoiceTemplateRef.value) {
    invoiceErrorMessage.value = 'محتوای فاکتور برای چاپ آماده نیست.'
    return
  }
  try {
    invoiceGenerating.value = true
    await nextTick()
    await printHtmlElement(invoiceTemplateRef.value, invoicePrintPageOptions.value)
  } catch (error) {
    console.error('VehicleInvoiceModal print error:', error)
    invoiceErrorMessage.value = resolvePrintErrorMessage(error)
  } finally {
    invoiceGenerating.value = false
  }
}

watch(
  () => [props.open, props.vehicle?.id],
  async ([isOpen]) => {
    if (!isOpen) {
      if (invoiceRenderTimer.value) window.clearTimeout(invoiceRenderTimer.value)
      invoiceGenerating.value = false
      invoiceErrorMessage.value = ''
      resetInvoiceMeta()
      revokeInvoicePdfUrl()
      return
    }
    await loadInvoiceContext()
    await nextTick()
  }
)

watch(
  () => [invoiceLayout.preset, invoiceLayout.thermalWidthMm, invoiceLayout.thermalHeightMm],
  () => {
    if (!props.open) return
    revokeInvoicePdfUrl()
  }
)

onBeforeUnmount(() => {
  if (invoiceRenderTimer.value) window.clearTimeout(invoiceRenderTimer.value)
  revokeInvoicePdfUrl()
})
</script>

<style scoped>
.invoice-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 120;
  background: rgba(15, 23, 42, .35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}
.modal-panel {
  width: min(1280px, 100%);
  max-width: 100%;
  max-height: calc(100vh - 40px);
  background: #fff;
  border-radius: 20px;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  display: flex;
  flex-direction: column;
  min-height: 0;
  box-shadow: 0 16px 42px -24px rgba(15, 23, 42, .45);
  contain: content;
}
.invoice-modal-panel {
  width: min(1120px, 100%);
  max-width: 100%;
  height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-head {
  padding: 18px 22px;
  border-bottom: 1px solid #e3e6ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.invoice-modal-head { align-items: flex-start; }
.invoice-modal-head h3 { margin: 0; font-size: 18px; }
.invoice-modal-subtitle { margin: 6px 0 0; color: #64748b; font-size: 12px; }
.close-btn {
  width: 38px;
  height: 38px;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
}
.invoice-modal-body {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  min-height: 0;
  min-width: 0;
  flex: 1;
  background: linear-gradient(180deg, #f8fbff, #edf5ff);
}
.invoice-format-toolbar {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 18px;
  background: rgba(255, 255, 255, .9);
  border: 1px solid #dbe7f5;
  box-shadow: 0 10px 26px rgba(15, 23, 42, .06);
}
.invoice-format-presets {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.invoice-format-chip {
  border: 1px solid #dbe7f5;
  border-radius: 14px;
  padding: 8px 12px;
  background: linear-gradient(180deg, #fff, #eef6ff);
  color: #334155;
  font-weight: 800;
  cursor: pointer;
  display: grid;
  gap: 2px;
  text-align: right;
  min-width: 0;
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease;
}
.invoice-format-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(15, 23, 42, .1);
}
.invoice-format-chip strong {
  font-size: 14px;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.invoice-format-chip span {
  font-size: 10px;
  color: #64748b;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.invoice-format-chip.active {
  background: linear-gradient(135deg, #0f172a, #0f4c81 58%, #0ea5e9);
  border-color: #0f4c81;
  color: #fff;
  box-shadow: 0 14px 28px rgba(14, 116, 144, .22);
}
.invoice-format-chip.active span { color: rgba(255, 255, 255, .78); }
.invoice-thermal-size-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.invoice-thermal-size-grid label { display: grid; gap: 6px; }
.invoice-thermal-size-grid span { font-size: 12px; color: #64748b; }
.invoice-thermal-size-grid input {
  width: 100%;
  min-width: 0;
  border: 1px solid #dbe7f5;
  border-radius: 12px;
  padding: 7px 9px;
  background: #fff;
  color: #0f172a;
  font-weight: 800;
  box-sizing: border-box;
}
.invoice-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: nowrap;
  align-items: center;
}
.secondary-btn {
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  cursor: pointer;
  background: #e2e8f0;
  color: #334155;
}
.invoice-modal-actions .secondary-btn {
  border-radius: 12px;
  min-height: 36px;
  padding: 0 11px;
  background: linear-gradient(180deg, #fff, #f1f7ff);
  border: 1px solid #d7e5f8;
  box-shadow: 0 6px 14px rgba(15, 23, 42, .05);
  white-space: nowrap;
}
.invoice-modal-actions .secondary-btn:disabled {
  opacity: .55;
  cursor: not-allowed;
}
.invoice-preview-loading,
.invoice-preview-empty {
  min-height: 380px;
  border: 1px dashed #bfd7ff;
  border-radius: 18px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  padding: 20px;
}
.invoice-preview-error {
  margin: 10px 2px 0;
  color: #b91c1c;
  font-size: 13px;
}
.invoice-preview-frame-wrap {
  min-height: 0;
  min-width: 0;
  border-radius: 18px;
  overflow: auto;
  border: 1px solid #dbe7f5;
  background: #eef3f8;
  box-shadow: 0 16px 36px rgba(15, 23, 42, .08);
  height: 100%;
  padding: 18px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}
.invoice-live-preview {
  margin: 0 auto;
  background: #fff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, .12);
}
.invoice-preview-frame {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  border: 0;
  background: #fff;
}
.invoice-template {
  background: #fff;
  padding: 0;
  box-sizing: border-box;
  overflow: hidden;
}
.invoice-template *,
.invoice-template *::before,
.invoice-template *::after { box-sizing: border-box; }
.invoice-sheet {
  direction: rtl;
  background: #fff;
  color: #0f172a;
  font-family: Tahoma, Arial, sans-serif;
  display: grid;
  box-sizing: border-box;
  overflow: hidden;
  max-width: 100%;
  contain: layout paint;
}
.invoice-sheet-a5 { font-size: 1em; }
.invoice-sheet-thermal {
  font-size: 1em;
  direction: rtl;
  background: #fff !important;
  color: #000 !important;
  font-family: Tahoma, Arial, sans-serif;
  line-height: 1.35;
}
.invoice-sheet-thermal,
.invoice-sheet-thermal * {
  color: #000 !important;
  background: #fff !important;
  background-color: #fff !important;
  box-shadow: none !important;
  text-shadow: none !important;
}
.invoice-sheet-thermal { border-radius: 0 !important; }
.invoice-sheet-thermal * { border-color: #000 !important; }
.invoice-sheet-head {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, .8fr);
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, #0f172a, #0f4c81 58%, #0ea5e9);
  color: #fff;
  min-width: 0;
  max-width: 100%;
}
.invoice-sheet-head > * { min-width: 0; }
.invoice-sheet-head small {
  display: block;
  font-size: 10px;
  color: rgba(255, 255, 255, .72);
  letter-spacing: 0;
}
.invoice-sheet-head strong {
  display: block;
  font-size: 18px;
  line-height: 1.35;
  margin-top: 2px;
  overflow-wrap: anywhere;
}
.invoice-sheet-head span {
  display: block;
  margin-top: 3px;
  color: rgba(255, 255, 255, .78);
  font-size: 10px;
  overflow-wrap: anywhere;
}
.invoice-sheet-meta {
  display: grid;
  gap: 4px;
  justify-items: end;
  min-width: 0;
  align-content: center;
}
.invoice-sheet-meta strong { font-size: 12px; overflow-wrap: anywhere; }
.invoice-identity-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}
.invoice-identity-grid article {
  border: 1px solid #dbe7f5;
  border-radius: 8px;
  padding: 7px;
  background: linear-gradient(180deg, #ffffff, #f8fbff);
  display: grid;
  gap: 4px;
  min-width: 0;
}
.invoice-identity-grid small {
  color: #0f4c81;
  font-size: 11px;
  font-weight: 800;
}
.invoice-identity-grid p {
  margin: 0;
  display: grid;
  grid-template-columns: minmax(0, .62fr) minmax(0, 1fr);
  gap: 6px;
  align-items: start;
  color: #334155;
  font-size: 10px;
  line-height: 1.55;
  min-width: 0;
}
.invoice-identity-grid p span { color: #64748b; min-width: 0; }
.invoice-identity-grid p strong {
  color: #0f172a;
  font-size: 10px;
  font-weight: 800;
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.invoice-sheet-section {
  display: grid;
  gap: 6px;
  min-width: 0;
  max-width: 100%;
}
.invoice-section-head strong { font-size: 12px; color: #0f172a; }
.invoice-table {
  width: 100%;
  max-width: 100%;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid #dbe7f5;
  border-radius: 8px;
  overflow: hidden;
}
.invoice-table th,
.invoice-table td {
  padding: 5px 7px;
  border-bottom: 1px solid #e2e8f0;
  text-align: right;
  font-size: 11px;
  line-height: 1.6;
  overflow-wrap: anywhere;
  word-break: break-word;
  min-width: 0;
  vertical-align: middle;
}
.invoice-table th {
  background: #eff6ff;
  color: #334155;
  font-weight: 800;
}
.invoice-services-table th:first-child,
.invoice-services-table td:first-child { width: 58%; }
.invoice-services-table th:nth-child(2),
.invoice-services-table td:nth-child(2) { width: 14%; text-align: center; }
.invoice-services-table th:nth-child(3),
.invoice-services-table td:nth-child(3) { width: 28%; }
.invoice-products-table th:first-child,
.invoice-products-table td:first-child { width: 48%; }
.invoice-products-table th:nth-child(2),
.invoice-products-table td:nth-child(2) { width: 12%; text-align: center; }
.invoice-products-table th:nth-child(3),
.invoice-products-table td:nth-child(3) { width: 20%; }
.invoice-products-table th:nth-child(4),
.invoice-products-table td:nth-child(4) { width: 20%; }
.invoice-table tr:last-child td { border-bottom: 0; }
.invoice-payment-section {
  border: 1px solid #dbe7f5;
  border-radius: 10px;
  padding: 7px 9px;
  background: #f8fbff;
}
.invoice-payment-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px 8px;
}
.invoice-payment-grid p {
  margin: 0;
  display: grid;
  grid-template-columns: minmax(0, .65fr) minmax(0, 1fr);
  gap: 8px;
  color: #334155;
  font-size: 10px;
  line-height: 1.6;
  min-width: 0;
}
.invoice-payment-grid p span,
.invoice-payment-grid p strong {
  min-width: 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.invoice-payment-grid p strong { color: #0f172a; }
.invoice-total-section {
  border: 1px solid #dbe7f5;
  border-radius: 10px;
  padding: 8px 10px;
  background: linear-gradient(180deg, #ffffff, #f8fbff);
}
.invoice-totals {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px 8px;
}
.invoice-totals p {
  margin: 0;
  display: grid;
  grid-template-columns: minmax(0, .75fr) minmax(0, 1fr);
  gap: 8px;
  color: #334155;
  font-size: 11px;
  min-width: 0;
}
.invoice-totals strong,
.invoice-totals span { min-width: 0; overflow-wrap: anywhere; }
.invoice-grand-total {
  grid-column: 1 / -1;
  padding-top: 6px;
  border-top: 1px dashed #bfd7ff;
  font-size: 14px;
  font-weight: 900;
  color: #0f172a;
}
.invoice-sheet-footer {
  padding-top: 6px;
  border-top: 1px dashed #cbd5e1;
  display: grid;
  gap: 3px;
}
.invoice-sheet-footer p {
  margin: 0;
  color: #475569;
  font-size: 10px;
  line-height: 1.7;
  overflow-wrap: anywhere;
  word-break: break-word;
  white-space: pre-line;
}
.thermal-sheet-head {
  display: grid;
  justify-items: center;
  gap: 5px;
  padding: 3px 0 8px;
  border-bottom: 2px solid #000;
  text-align: center;
}
.thermal-sheet-head strong {
  font-size: 26px;
  font-weight: 900;
  line-height: 1.22;
}
.thermal-sheet-head small {
  font-size: 11px;
  font-weight: 800;
  line-height: 1.65;
  max-width: 100%;
  overflow-wrap: anywhere;
}
.thermal-info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 5px 10px;
  padding: 8px 0;
  border-bottom: 2px solid #000;
}
.thermal-info-grid p {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  line-height: 1.55;
  min-width: 0;
}
.thermal-info-grid span { flex: 0 0 auto; font-weight: 700; }
.thermal-info-grid strong {
  min-width: 0;
  font-weight: 700;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.thermal-items-section { padding: 8px 0; }
.thermal-items-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  border: 1.5px solid #000;
}
.thermal-items-table th,
.thermal-items-table td {
  border: 1px solid #000;
  padding: 7px 5px;
  text-align: center;
  vertical-align: middle;
  font-size: 12px;
  line-height: 1.35;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.thermal-items-table th {
  font-weight: 900;
  font-size: 12px;
  line-height: 1.35;
}
.thermal-items-table th:first-child,
.thermal-items-table td:first-child { width: 62%; text-align: center; }
.thermal-items-table th:nth-child(2),
.thermal-items-table td:nth-child(2) { width: 38%; }
.thermal-total-block {
  display: grid;
  gap: 4px;
  padding: 6px 0 0;
}
.thermal-total-block p {
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
  line-height: 1.6;
}
.thermal-total-block span { font-weight: 800; }
.thermal-total-block strong {
  font-weight: 900;
  text-align: left;
  white-space: nowrap;
}
.thermal-payable-total {
  margin-top: 4px !important;
  padding: 8px 0 !important;
  border-top: 2px solid #000;
  border-bottom: 4px double #000;
  font-size: 16px !important;
  font-weight: 900;
}
.thermal-payable-total strong { font-size: 17px; }
.thermal-sheet-footer {
  display: grid;
  gap: 3px;
  padding-top: 8px;
}
.thermal-sheet-footer p {
  margin: 0;
  text-align: center;
  font-size: 11px;
  line-height: 1.65;
  font-weight: 800;
  white-space: pre-line;
  overflow-wrap: anywhere;
  word-break: break-word;
}
.thermal-sheet-footer .receipt-custom-note {
  padding-top: 6px;
  border-top: 1px dashed #000;
}
.thermal-sheet-footer strong {
  display: block;
  margin-top: 8px;
  text-align: center;
  font-size: 14px;
  font-weight: 900;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .invoice-modal-overlay { padding: 8px; }
  .invoice-modal-panel {
    height: calc(100dvh - 16px);
    max-height: calc(100dvh - 16px);
  }
  .invoice-format-toolbar {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
  .invoice-format-presets { grid-template-columns: 1fr; }
  .invoice-modal-actions { flex-direction: column; align-items: stretch; }
  .invoice-modal-actions .secondary-btn { width: 100%; }
  .invoice-thermal-size-grid,
  .invoice-identity-grid,
  .invoice-payment-grid,
  .invoice-totals { grid-template-columns: 1fr; }
  .invoice-sheet-head { grid-template-columns: 1fr; }
  .invoice-preview-loading,
  .invoice-preview-empty { min-height: 220px; }
}
</style>
