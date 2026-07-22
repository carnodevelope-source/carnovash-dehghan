<template>
  <div v-if="open" class="vehicle-details-modal-overlay" @click.self="$emit('close')">
    <section class="vehicle-details-modal-panel vehicle-details-details-panel">
      <header class="vehicle-details-modal-head">
        <div>
          <p class="vehicle-details-modal-step">{{ title }}</p>
          <h2>{{ vehicle?.car_model || '-' }} - {{ vehicle?.car_color || '-' }}</h2>
        </div>
        <button class="vehicle-details-close-btn" @click="$emit('close')">✕</button>
      </header>

      <div v-if="loading" class="vehicle-details-modal-loading">در حال بارگذاری...</div>
      <div v-else-if="vehicle" class="vehicle-details-grid">
        <section class="vehicle-details-card vehicle-details-full vehicle-details-summary-strip">
          <div class="vehicle-details-summary-kpi">
            <span>وضعیت خودرو</span>
            <strong>{{ formatStatus(vehicle.status) }}</strong>
          </div>
          <div class="vehicle-details-summary-kpi">
            <span>وضعیت پرداخت</span>
            <strong>{{ formatPaymentStatus(vehicle.payment_status) }}</strong>
          </div>
          <div class="vehicle-details-summary-kpi">
            <span>جمع خدمات</span>
            <strong>{{ formatMoney(jobServiceListSubtotal(vehicle.job)) }}</strong>
          </div>
          <div class="vehicle-details-summary-kpi">
            <span>مبلغ نهایی</span>
            <strong>{{ formatMoney(vehicle.job?.final_total) }}</strong>
          </div>
        </section>

        <section class="vehicle-details-card">
          <h3>مشخصات خودرو</h3>
          <div class="vehicle-details-info-grid">
            <div class="vehicle-details-plate-field">
              <span>پلاک</span>
              <PlateBadge
                :plate-number="vehicle.plate_number"
                :plate-left="vehicle.plate_left"
                :plate-letter="vehicle.plate_letter"
                :plate-mid="vehicle.plate_mid"
                :plate-right="vehicle.plate_right"
                :plate-type="vehicle.plate_type || 'car'"
                compact
              />
            </div>
            <p><span>مدل</span><strong>{{ vehicle.car_model || '-' }}</strong></p>
            <p><span>رنگ</span><strong>{{ vehicle.car_color || '-' }}</strong></p>
            <p><span>زمان ورود</span><strong>{{ formatDateTime(vehicle.check_in_at) }}</strong></p>
          </div>
        </section>

        <section class="vehicle-details-card">
          <h3>راننده و پذیرش</h3>
          <div class="vehicle-details-info-grid">
            <p><span>نام راننده</span><strong>{{ vehicle.driver_name || '-' }}</strong></p>
            <p v-if="canSeeDriverGender"><span>جنسیت راننده</span><strong>{{ driverGenderLabel(vehicle.driver_gender) }}</strong></p>
            <p><span>شماره راننده</span><strong>{{ vehicle.driver_phone || '-' }}</strong></p>
            <p><span>ایجاد</span><strong>{{ formatDateTime(vehicle.created_at) }}</strong></p>
            <p><span>آخرین بروزرسانی</span><strong>{{ formatDateTime(vehicle.updated_at) }}</strong></p>
          </div>
          <div class="vehicle-details-note-box">{{ vehicle.notes || 'بدون توضیحات' }}</div>
        </section>

        <section class="vehicle-details-card vehicle-details-full">
          <h3>اطلاعات تخصیص و مالی</h3>
          <div class="vehicle-details-info-grid vehicle-details-info-grid-four">
            <p><span>پرسنل تخصیص</span><strong>{{ assignedWorkersLabel(vehicle.job) }}</strong></p>
            <p><span>همه پرسنل سفارش</span><strong>{{ assignedWorkersFullLabel(vehicle.job) }}</strong></p>
            <p><span>نوع سهم</span><strong>{{ workerPaymentTypeLabel(vehicle.job?.worker_payment_type) }}</strong></p>
            <p><span>درصد سهم</span><strong>{{ formatPercent(vehicle.job?.worker_payment_percent) }}</strong></p>
            <p><span>سهم ثابت</span><strong>{{ formatMoney(vehicle.job?.worker_payment_fixed) }}</strong></p>
            <p><span>سهم پرسنل</span><strong>{{ formatMoney(workerTotalWithTip(vehicle.job)) }}</strong></p>
            <p><span>سهم کارواش</span><strong>{{ formatMoney(vehicle.job?.carwash_share_amount) }}</strong></p>
            <p><span>تخفیف مجموعه</span><strong>{{ formatMoney(vehicle.job?.facility_discount_total) }}</strong></p>
            <p><span>تخفیف امتیاز مشتری</span><strong>{{ formatMoney(vehicle.job?.loyalty_discount_total) }}</strong></p>
            <p><span>تخفیف دستی</span><strong>{{ formatMoney(vehicle.job?.manual_discount_total) }}</strong></p>
            <p><span>جمع تخفیف</span><strong>{{ formatMoney(vehicle.job?.total_discount || vehicle.job?.discount_total) }}</strong></p>
            <p><span>انعام</span><strong>{{ formatMoney(vehicle.job?.tip_amount) }}</strong></p>
            <p><span>مالیات</span><strong>{{ formatMoney(vehicle.job?.tax_total) }}</strong></p>
          </div>
        </section>

        <section class="vehicle-details-card vehicle-details-full">
          <h3>خدمات ثبت‌شده</h3>
          <div v-if="vehicle.job?.service_lines?.length" class="vehicle-details-list">
            <div v-for="line in vehicle.job.service_lines" :key="line.id" class="vehicle-details-list-item vehicle-details-service-item">
              <div>
                <span class="vehicle-details-service-title">{{ line.service_name }}</span>
                <small v-if="Number(line.discount_amount || 0) > 0" class="vehicle-details-service-discount-note">
                  تخفیف خدمت: {{ formatMoney(line.discount_amount) }}
                </small>
              </div>
              <div class="vehicle-details-service-price-box">
                <strong>{{ formatMoney(serviceLineBaseTotal(line)) }}</strong>
              </div>
            </div>
          </div>
          <p v-else class="vehicle-details-empty-row">خدمتی ثبت نشده است.</p>
        </section>

        <section class="vehicle-details-card vehicle-details-full">
          <h3>تاریخچه وضعیت</h3>
          <div v-if="vehicle.status_logs?.length" class="vehicle-details-list">
            <div v-for="log in vehicle.status_logs" :key="log.id" class="vehicle-details-list-item">
              <span>{{ formatStatus(log.from_status) }} ← {{ formatStatus(log.to_status) }}</span>
              <strong>{{ formatDateTime(log.changed_at) }}</strong>
            </div>
          </div>
          <p v-else class="vehicle-details-empty-row">لاگ وضعیتی ثبت نشده است.</p>
        </section>

        <section v-if="showActions" class="vehicle-details-card vehicle-details-full">
          <div class="vehicle-details-actions">
            <button
              type="button"
              class="vehicle-details-secondary-btn"
              @click="$emit('edit-vehicle')"
            >
              ویرایش اطلاعات مراجعه
            </button>
            <button
              v-if="!vehicle.is_plate_blocked"
              type="button"
              class="vehicle-details-secondary-btn"
              @click="$emit('block-plate')"
            >
              بلاک کردن پلاک
            </button>
            <button
              v-else
              type="button"
              class="vehicle-details-secondary-btn vehicle-details-blocked-btn"
              @click="$emit('unblock-plate')"
            >
              خارج کردن از لیست سیاه
            </button>
            <button
              v-if="vehicle.status !== 'cancelled'"
              type="button"
              class="vehicle-details-danger-btn"
              @click="$emit('cancel')"
            >
              لغو سفارش
            </button>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatThousandsToman } from '../../utils/money'
import PlateBadge from './PlateBadge.vue'
import { useAuthStore } from '../../store/auth.store'

defineProps({
  open: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  vehicle: { type: Object, default: null },
  title: { type: String, default: 'جزئیات کامل خودرو' },
  showActions: { type: Boolean, default: true }
})

defineEmits(['close', 'cancel', 'block-plate', 'unblock-plate', 'edit-vehicle'])

const authStore = useAuthStore()
const canSeeDriverGender = computed(() => authStore.role !== 'worker')

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

const driverGenderLabel = (value) => ({
  male: 'مرد',
  female: 'زن'
}[value] || '-')

const workerPaymentTypeLabel = (value) => ({
  fixed: 'ثابت',
  hourly: 'ساعتی',
  percent: 'درصدی'
}[value] || '-')

const formatMoney = (value) => formatThousandsToman(value)
const serviceLineBaseTotal = (line) => {
  const quantity = Number(line?.quantity || 1) || 1
  return Number(line?.line_total || 0) + Number(line?.discount_amount || 0)
}
const jobServiceListSubtotal = (job) => {
  const stored = Number(job?.services_total || 0)
  if (stored > 0) return stored
  return (Array.isArray(job?.service_lines) ? job.service_lines : []).reduce(
    (sum, line) => sum + serviceLineBaseTotal(line),
    0
  )
}
const formatPercent = (value) => `${Number(value || 0).toLocaleString('fa-IR')}٪`
const formatDateTime = (value) => {
  if (!value) return '-'
  return new Intl.DateTimeFormat('fa-IR', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

const assignedWorkersLabel = (job) => {
  if (!job) return 'تخصیص نشده'
  const names = Array.isArray(job.assigned_workers_names)
    ? job.assigned_workers_names.filter((item) => String(item || '').trim().length > 0)
    : []
  if (names.length) return names.join('، ')
  return job.assigned_worker_name || 'تخصیص نشده'
}

const assignedWorkersFullLabel = (job) => {
  const snapshot = Array.isArray(job?.assigned_workers_snapshot) ? job.assigned_workers_snapshot : []
  const names = snapshot
    .map((item) => String(item?.name || '').trim())
    .filter((item, index, arr) => item && arr.indexOf(item) === index)
  if (names.length) return names.join('، ')
  return assignedWorkersLabel(job)
}

const workerTotalWithTip = (job) => {
  if (!job) return 0
  return Number(job.worker_share_amount || 0) + Number(job.workers_tip_share_amount || 0)
}
</script>

<style scoped>
.vehicle-details-modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, .35); backdrop-filter: blur(3px); z-index: 90; display: flex; align-items: center; justify-content: center; padding: 20px; overflow-y: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; }
.vehicle-details-modal-panel { width: min(1280px, 100%); height: calc(100vh - 40px); max-height: calc(100vh - 40px); background: #fff; border-radius: 20px; overflow: hidden; display: flex; flex-direction: column; min-height: 0; box-shadow: 0 24px 60px -20px rgba(15,23,42,.4); }
.vehicle-details-details-panel { width: min(1100px, 100%); }
.vehicle-details-modal-head { padding: 18px 22px; border-bottom: 1px solid #e3e6ed; display: flex; align-items: center; justify-content: space-between; }
.vehicle-details-modal-head h2 { margin: 0; font-size: 22px; }
.vehicle-details-modal-step { margin: 0 0 6px; color: #64748b; font-size: 12px; }
.vehicle-details-close-btn { width: 38px; height: 38px; border: 1px solid #dbe3ef; border-radius: 10px; background: #fff; cursor: pointer; }
.vehicle-details-modal-loading { padding: 16px 22px; }
.vehicle-details-grid { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; -webkit-overflow-scrolling: touch; padding: 18px 22px 24px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.vehicle-details-card { border: 1px solid #e2e8f0; border-radius: 16px; padding: 16px; background: #fff; }
.vehicle-details-card h3 { margin: 0 0 10px; font-size: 16px; }
.vehicle-details-full { grid-column: 1 / -1; }
.vehicle-details-summary-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; background: linear-gradient(90deg, #f8fbff, #eef4ff); }
.vehicle-details-summary-kpi { border: 1px solid #dbeafe; border-radius: 12px; padding: 10px; display: grid; gap: 4px; }
.vehicle-details-summary-kpi span { color: #64748b; font-size: 12px; }
.vehicle-details-summary-kpi strong { color: #0f172a; font-size: 15px; }
.vehicle-details-info-grid { display: grid; gap: 8px; }
.vehicle-details-info-grid-four { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.vehicle-details-info-grid p { margin: 0; border: 1px solid #e2e8f0; background: #f8fafc; border-radius: 10px; padding: 9px 10px; display: grid; gap: 4px; }
.vehicle-details-info-grid p span { color: #64748b; font-size: 12px; }
.vehicle-details-info-grid p strong { color: #0f172a; font-size: 13px; font-weight: 700; }
.vehicle-details-plate-field { margin: 0; border: 1px solid #e2e8f0; background: #f8fafc; border-radius: 10px; padding: 9px 10px; display: grid; gap: 8px; }
.vehicle-details-plate-field > span { color: #64748b; font-size: 12px; }
.vehicle-details-note-box { margin-top: 10px; border: 1px dashed #cbd5e1; border-radius: 10px; padding: 10px; color: #334155; font-size: 13px; background: #f8fafc; }
.vehicle-details-list { display: grid; gap: 8px; }
.vehicle-details-list-item { border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; background: #fdfefe; }
.vehicle-details-service-item { background: #f8fbff; }
.vehicle-details-service-title { display: block; color: #0f172a; font-weight: 700; margin-bottom: 2px; }
.vehicle-details-list-item small { color: #64748b; font-size: 11px; }
.vehicle-details-service-discount-note { display:block; margin-top:4px; color:#b91c1c; font-size:11px; font-weight:700; }
.vehicle-details-service-price-box { display:grid; justify-items:end; gap:4px; }
.vehicle-details-service-base-price { color:#94a3b8; text-decoration:line-through; font-size:11px; }
.vehicle-details-empty-row { margin: 0; color: #64748b; font-size: 13px; }
.vehicle-details-actions { display:flex; justify-content:flex-end; gap:10px; }
.vehicle-details-secondary-btn,.vehicle-details-danger-btn { border:none; border-radius:10px; padding:8px 12px; cursor:pointer; }
.vehicle-details-secondary-btn { background:#e2e8f0; color:#334155; }
.vehicle-details-blocked-btn { background:#fee2e2; color:#991b1b; }
.vehicle-details-danger-btn { background:#fee2e2; color:#b91c1c; }
.vehicle-details-danger-btn:disabled { background:#e5e7eb; color:#94a3b8; cursor:not-allowed; }
@media (max-width: 1100px) {
  .vehicle-details-grid { grid-template-columns: 1fr; }
  .vehicle-details-summary-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .vehicle-details-info-grid-four { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 768px) {
  .vehicle-details-modal-overlay { padding: 8px; }
  .vehicle-details-modal-panel { height: calc(100dvh - 16px); max-height: calc(100dvh - 16px); border-radius: 14px; }
  .vehicle-details-grid { padding: 14px; }
  .vehicle-details-summary-strip,
  .vehicle-details-info-grid,
  .vehicle-details-info-grid-four { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .vehicle-details-list-item,
  .vehicle-details-actions { flex-direction: column; align-items: stretch; }
}
</style>
