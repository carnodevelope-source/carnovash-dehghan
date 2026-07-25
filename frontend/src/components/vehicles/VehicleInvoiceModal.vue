<template>
  <div v-if="open" class="vehicle-invoice-overlay" @click.self="emit('close')">
    <section class="vehicle-invoice-panel">
      <header class="vehicle-invoice-head">
        <div>
          <h3>فاکتور سفارش</h3>
          <p>قالب را انتخاب کنید و PDF بگیرید یا چاپ کنید.</p>
        </div>
        <button type="button" class="vehicle-invoice-close" @click="emit('close')">✕</button>
      </header>

      <div class="vehicle-invoice-toolbar">
        <button
          v-for="option in presetOptions"
          :key="option.key"
          type="button"
          class="vehicle-invoice-chip"
          :class="{ active: layout.preset === option.key }"
          @click="layout.preset = option.key"
        >
          <strong>{{ option.label }}</strong>
          <span>{{ option.hint }}</span>
        </button>
        <div class="vehicle-invoice-actions">
          <button type="button" class="vehicle-invoice-btn" :disabled="generating" @click="buildPdf">
            {{ generating ? 'در حال ساخت...' : 'بروزرسانی' }}
          </button>
          <button type="button" class="vehicle-invoice-btn" :disabled="!pdfUrl || generating" @click="downloadPdf">
            دانلود PDF
          </button>
          <button type="button" class="vehicle-invoice-btn primary" :disabled="!pdfUrl || generating" @click="printPdf">
            چاپ
          </button>
        </div>
      </div>

      <div v-if="generating" class="vehicle-invoice-loading">در حال ساخت فاکتور...</div>
      <div v-else-if="pdfUrl" class="vehicle-invoice-frame-wrap">
        <iframe ref="previewFrameRef" :src="pdfUrl" title="invoice-preview" class="vehicle-invoice-frame"></iframe>
      </div>
      <div v-else class="vehicle-invoice-empty">{{ errorMessage || 'فاکتور هنوز ساخته نشده است.' }}</div>
    </section>

    <div class="vehicle-invoice-stage" :style="stageStyle" aria-hidden="true">
      <div ref="templateRef" class="vehicle-invoice-template" :style="templateStyle">
        <article class="vehicle-invoice-sheet" :class="sheetClass" :style="sheetStyle" dir="rtl">
          <header>
            <strong>{{ carwashTitle }}</strong>
            <span>فاکتور نهایی سفارش</span>
            <span>شماره: {{ invoiceNumber }}</span>
            <span>تاریخ: {{ issuedAt }}</span>
          </header>

          <section class="vehicle-invoice-meta">
            <p><span>مشتری</span><strong>{{ customerName }}</strong></p>
            <p><span>تماس</span><strong>{{ customerPhone }}</strong></p>
            <p><span>خودرو</span><strong>{{ vehicleTitle }}</strong></p>
            <p><span>پلاک</span><strong>{{ plateLabel }}</strong></p>
          </section>

          <table>
            <thead>
              <tr>
                <th>عنوان</th>
                <th>تعداد</th>
                <th>مبلغ</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(line, index) in serviceLines" :key="`svc-${line.id || index}`">
                <td>{{ line.service_name || '-' }}</td>
                <td>{{ Number(line.quantity || 1).toLocaleString('en-US') }}</td>
                <td>{{ formatMoney(serviceLineTotal(line)) }}</td>
              </tr>
              <tr v-if="!serviceLines.length">
                <td colspan="3">خدمتی ثبت نشده است.</td>
              </tr>
            </tbody>
          </table>

          <section class="vehicle-invoice-totals">
            <p><span>جمع خدمات</span><strong>{{ formatMoney(servicesTotal) }}</strong></p>
            <p v-if="discountTotal > 0"><span>تخفیف</span><strong>{{ formatMoney(discountTotal) }}</strong></p>
            <p v-if="tipAmount > 0"><span>انعام</span><strong>{{ formatMoney(tipAmount) }}</strong></p>
            <p v-if="taxTotal > 0"><span>مالیات</span><strong>{{ formatMoney(taxTotal) }}</strong></p>
            <p class="grand"><span>مبلغ نهایی</span><strong>{{ formatMoney(finalTotal) }}</strong></p>
          </section>

          <footer>از اعتماد شما سپاسگزاریم</footer>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useAuthStore } from '../../store/auth.store'
import { formatThousandsToman } from '../../utils/money'

const props = defineProps({
  open: { type: Boolean, default: false },
  vehicle: { type: Object, default: null }
})

const emit = defineEmits(['close'])
const authStore = useAuthStore()

const layout = reactive({ preset: 'a4' })
const generating = ref(false)
const pdfUrl = ref('')
const errorMessage = ref('')
const templateRef = ref(null)
const previewFrameRef = ref(null)

const presetOptions = [
  { key: 'a4', label: 'A4', hint: 'فاکتور کامل' },
  { key: 'a5', label: 'A5', hint: 'جمع‌وجور' },
  { key: 'thermal', label: 'فیش', hint: 'پرینتر حرارتی' }
]

const job = computed(() => props.vehicle?.job || {})
const serviceLines = computed(() => (Array.isArray(job.value.service_lines) ? job.value.service_lines : []))

const pageMetrics = computed(() => {
  if (layout.preset === 'a5') {
    return { width: 138, minHeight: 190, padding: 4.5, margin: [5, 5, 5, 5], format: 'a5', orientation: 'portrait' }
  }
  if (layout.preset === 'thermal') {
    return { width: 74, minHeight: 140, padding: 3, margin: [3, 3, 3, 3], format: [80, 220], orientation: 'portrait' }
  }
  return { width: 198, minHeight: 270, padding: 5, margin: [6, 6, 6, 6], format: 'a4', orientation: 'portrait' }
})

const sheetStyle = computed(() => ({
  width: `${pageMetrics.value.width}mm`,
  maxWidth: `${pageMetrics.value.width}mm`,
  minHeight: `${pageMetrics.value.minHeight}mm`,
  padding: `${pageMetrics.value.padding}mm`
}))
const templateStyle = computed(() => ({
  width: `${pageMetrics.value.width}mm`,
  maxWidth: `${pageMetrics.value.width}mm`
}))
const stageStyle = computed(() => ({ width: `${pageMetrics.value.width}mm` }))
const sheetClass = computed(() => ({
  'is-a5': layout.preset === 'a5',
  'is-thermal': layout.preset === 'thermal'
}))

const carwashTitle = computed(() => {
  const name = String(authStore.user?.tenant_name || '').trim() || 'کارواش'
  return name.startsWith('کارواش') ? name : `کارواش ${name}`
})
const invoiceNumber = computed(() => `#${props.vehicle?.id || job.value.id || '-'}`)
const issuedAt = computed(() => {
  const raw = props.vehicle?.check_in_at || props.vehicle?.created_at
  if (!raw) return '-'
  return new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(raw))
})
const customerName = computed(() => props.vehicle?.driver_name || 'مشتری حضوری')
const customerPhone = computed(() => props.vehicle?.driver_phone || '-')
const vehicleTitle = computed(() => {
  const parts = [props.vehicle?.car_model, props.vehicle?.car_color].filter(Boolean)
  return parts.join(' - ') || '-'
})
const plateLabel = computed(() => {
  if (props.vehicle?.plate_type === 'motorcycle') {
    return `${props.vehicle?.plate_mid || ''} ${props.vehicle?.plate_letter || ''}`.trim() || props.vehicle?.plate_number || '-'
  }
  const parts = [
    props.vehicle?.plate_right,
    props.vehicle?.plate_letter,
    props.vehicle?.plate_mid,
    props.vehicle?.plate_left
  ].filter(Boolean)
  return parts.join(' ') || props.vehicle?.plate_number || '-'
})

const serviceLineTotal = (line) => {
  const quantity = Number(line?.quantity || 1) || 1
  return Number(line?.line_total || 0) + Number(line?.discount_amount || 0)
}
const servicesTotal = computed(() => {
  const stored = Number(job.value.services_total || 0)
  if (stored > 0) return stored
  return serviceLines.value.reduce((sum, line) => sum + serviceLineTotal(line), 0)
})
const discountTotal = computed(() => Number(job.value.total_discount || job.value.discount_total || 0))
const tipAmount = computed(() => Number(job.value.tip_amount || 0))
const taxTotal = computed(() => Number(job.value.tax_total || 0))
const finalTotal = computed(() => Number(job.value.final_total || 0))
const formatMoney = (value) => formatThousandsToman(value)

const revokePdfUrl = () => {
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = ''
  }
}

const buildPdf = async () => {
  if (!templateRef.value) return
  generating.value = true
  errorMessage.value = ''
  revokePdfUrl()
  try {
    await nextTick()
    const html2pdfModule = await import('html2pdf.js')
    const html2pdf = html2pdfModule.default || html2pdfModule
    const metrics = pageMetrics.value
    const worker = html2pdf()
      .set({
        margin: metrics.margin,
        filename: `invoice-${props.vehicle?.id || 'order'}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF: { unit: 'mm', format: metrics.format, orientation: metrics.orientation },
        pagebreak: { mode: ['css', 'legacy'] }
      })
      .from(templateRef.value)
      .toPdf()
    const pdf = await worker.get('pdf')
    pdfUrl.value = URL.createObjectURL(pdf.output('blob'))
  } catch (error) {
    console.error('VehicleInvoiceModal buildPdf error:', error)
    errorMessage.value = 'ساخت فایل فاکتور ناموفق بود.'
  } finally {
    generating.value = false
  }
}

const downloadPdf = () => {
  if (!pdfUrl.value) return
  const anchor = document.createElement('a')
  anchor.href = pdfUrl.value
  anchor.download = `invoice-${props.vehicle?.id || 'order'}.pdf`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

const printPdf = () => {
  const frame = previewFrameRef.value
  if (frame?.contentWindow) {
    frame.contentWindow.focus()
    frame.contentWindow.print()
    return
  }
  if (!pdfUrl.value) return
  const popup = window.open(pdfUrl.value, '_blank', 'noopener,noreferrer')
  if (popup) {
    window.setTimeout(() => {
      popup.focus()
      popup.print()
    }, 400)
  }
}

watch(
  () => [props.open, props.vehicle?.id, layout.preset],
  async ([isOpen]) => {
    if (!isOpen) {
      revokePdfUrl()
      errorMessage.value = ''
      return
    }
    await nextTick()
    await buildPdf()
  }
)
</script>

<style scoped>
.vehicle-invoice-overlay {
  position: fixed;
  inset: 0;
  z-index: 120;
  background: rgba(15, 23, 42, .42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.vehicle-invoice-panel {
  width: min(920px, 100%);
  max-height: calc(100vh - 32px);
  overflow: auto;
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 24px 60px -20px rgba(15, 23, 42, .45);
  padding: 16px;
  display: grid;
  gap: 12px;
}
.vehicle-invoice-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.vehicle-invoice-head h3 { margin: 0; font-size: 18px; }
.vehicle-invoice-head p { margin: 4px 0 0; color: #64748b; font-size: 12px; }
.vehicle-invoice-close {
  width: 36px;
  height: 36px;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
}
.vehicle-invoice-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.vehicle-invoice-chip {
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  border-radius: 12px;
  padding: 8px 12px;
  display: grid;
  gap: 2px;
  cursor: pointer;
  text-align: right;
}
.vehicle-invoice-chip.active {
  border-color: #2563eb;
  background: #eff6ff;
}
.vehicle-invoice-chip strong { font-size: 13px; color: #0f172a; }
.vehicle-invoice-chip span { font-size: 11px; color: #64748b; }
.vehicle-invoice-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-right: auto; }
.vehicle-invoice-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 10px;
  padding: 8px 12px;
  cursor: pointer;
  font-weight: 700;
}
.vehicle-invoice-btn.primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.vehicle-invoice-btn:disabled { opacity: .55; cursor: not-allowed; }
.vehicle-invoice-loading,
.vehicle-invoice-empty {
  min-height: 180px;
  display: grid;
  place-items: center;
  color: #64748b;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
}
.vehicle-invoice-frame-wrap {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  min-height: 420px;
}
.vehicle-invoice-frame {
  width: 100%;
  height: min(62vh, 620px);
  border: 0;
  background: #f8fafc;
}
.vehicle-invoice-stage {
  position: fixed;
  left: -10000px;
  top: 0;
  pointer-events: none;
  z-index: -1;
}
.vehicle-invoice-template,
.vehicle-invoice-sheet {
  background: #fff;
  color: #000;
  font-family: Tahoma, Arial, sans-serif;
}
.vehicle-invoice-sheet {
  display: grid;
  gap: 10px;
  box-sizing: border-box;
}
.vehicle-invoice-sheet header {
  display: grid;
  gap: 4px;
  text-align: center;
  border-bottom: 2px solid #000;
  padding-bottom: 8px;
}
.vehicle-invoice-sheet header strong { font-size: 16px; }
.vehicle-invoice-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
.vehicle-invoice-meta p,
.vehicle-invoice-totals p {
  margin: 0;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
}
.vehicle-invoice-sheet table {
  width: 100%;
  border-collapse: collapse;
}
.vehicle-invoice-sheet th,
.vehicle-invoice-sheet td {
  border: 1px solid #000;
  padding: 6px;
  text-align: center;
  font-size: 12px;
}
.vehicle-invoice-totals {
  display: grid;
  gap: 4px;
  border-top: 2px solid #000;
  padding-top: 8px;
}
.vehicle-invoice-totals .grand {
  font-size: 14px;
  font-weight: 900;
  border-top: 1px solid #000;
  padding-top: 6px;
}
.vehicle-invoice-sheet footer {
  text-align: center;
  font-size: 12px;
  padding-top: 6px;
}
.vehicle-invoice-sheet.is-thermal header strong { font-size: 13px; }
.vehicle-invoice-sheet.is-thermal .vehicle-invoice-meta { grid-template-columns: 1fr; }
.vehicle-invoice-sheet.is-thermal th,
.vehicle-invoice-sheet.is-thermal td { font-size: 10px; padding: 4px; }
</style>
