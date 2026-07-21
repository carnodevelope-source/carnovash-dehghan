<template>
  <AppShell title="گزارشات" subtitle="تحلیل مالی و عملیاتی">
    <div class="reports-content">
      <section class="range-bar">
        <button
          v-for="option in rangeOptions"
          :key="option.key"
          class="range-chip"
          :class="{ active: filters.rangeKey === option.key }"
          @click="setRange(option.key)"
        >
          <IconlyIcon :name="option.icon" size="sm" />
          {{ option.label }}
        </button>
      </section>

      <section class="filters-card">
        <div class="field search-field">
          <span><IconlyIcon name="search" size="xs" />جستجو</span>
          <input v-model="filters.q" type="text" placeholder="راننده، شماره، نیرو، مدل یا پلاک..." />
        </div>
        <div class="field">
          <span><IconlyIcon name="calendar" size="xs" />شروع بازه (شمسی)</span>
          <BaseDatePicker v-model="filters.startJalali" placeholder="1405/01/01" />
        </div>
        <div class="field">
          <span><IconlyIcon name="calendar" size="xs" />پایان بازه (شمسی)</span>
          <BaseDatePicker v-model="filters.endJalali" placeholder="1405/01/30" />
        </div>
        <div class="field">
          <span><IconlyIcon name="users3" size="xs" />نیرو</span>
          <select v-model="filters.workerId">
            <option value="">همه نیروها</option>
            <option v-for="worker in workers" :key="worker.id" :value="String(worker.id)">{{ worker.full_name }}</option>
          </select>
        </div>
        <div class="field">
          <span><IconlyIcon name="calendar" size="xs" />ماه بیمه</span>
          <select v-model="filters.insuranceMonthJalali">
            <option v-for="item in insuranceMonthOptions" :key="`filter-${item.value}`" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
        <div class="field">
          <span><IconlyIcon name="category" size="xs" />نوع وسیله</span>
          <select v-model="filters.plateType">
            <option value="">همه</option>
            <option value="car">خودرو</option>
            <option value="motorcycle">موتور سیکلت</option>
          </select>
        </div>
        <div class="field plate-field">
          <span><IconlyIcon name="filter" size="xs" />پلاک خودرو</span>
          <div class="plate-filter-shell">
            <div v-if="filters.plateType === 'motorcycle'" class="plate-filter-row plate-filter-row-motorcycle" dir="ltr">
              <div class="plate-filter-motor-main">
                <input v-model="filters.plateMid" type="text" maxlength="3" placeholder="345" />
                <input v-model="filters.plateLetter" type="text" maxlength="5" placeholder="67890" />
              </div>
              <span class="plate-filter-blue plate-filter-blue-motor">IR</span>
            </div>
            <div v-else class="plate-filter-row plate-filter-row-car" dir="ltr">
              <input v-model="filters.plateRight" type="text" maxlength="2" placeholder="67" />
              <input v-model="filters.plateLetter" type="text" maxlength="1" placeholder="ب" />
              <input v-model="filters.plateMid" type="text" maxlength="3" placeholder="345" />
              <input v-model="filters.plateLeft" class="plate-filter-blue plate-filter-blue-input" type="text" maxlength="2" placeholder="12" />
            </div>
          </div>
        </div>
        <div class="filters-actions">
          <button class="secondary-btn clear-btn btn-with-icon" @click="resetFilters"><IconlyIcon name="filter" size="sm" />حذف فیلتر</button>
          <section class="export-studio-actions">
            <button class="export-action-btn csv" :disabled="exportState.csvLoading" @click="exportCsv">
              <IconlyIcon name="document" size="sm" />
              {{ exportState.csvLoading ? 'در حال آماده‌سازی CSV...' : 'خروجی CSV' }}
            </button>
            <button class="export-action-btn pdf" :disabled="exportState.pdfLoading" @click="exportPdf">
              <IconlyIcon name="download" size="sm" />
              {{ exportState.pdfLoading ? 'در حال ساخت PDF...' : 'خروجی PDF' }}
            </button>
          </section>
        </div>
      </section>

      <section v-if="visibleSummaryCards.length" class="summary-grid">
        <article v-for="card in visibleSummaryCards" :key="card.key" class="kpi-card">
          <p>{{ card.label }}</p>
          <strong>{{ card.value }}</strong>
        </article>
      </section>

      <section class="tabs-bar">
        <button v-for="tab in tabs" :key="tab.key" class="chip" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key"><IconlyIcon :name="tab.icon" size="sm" />{{ tab.label }}</button>
      </section>

      <section ref="reportExportRef" class="table-card">
        <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>

        <template v-if="activeTab === 'overall'">
          <h3>گزارش کل</h3>
          <div class="table-wrap">
            <table>
              <thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>رنگ</th><th>پلاک</th><th>وضعیت</th><th>حق کارواش</th><th>حق نیرو</th><th>تخفیف</th><th>انعام</th><th>نام نیرو</th><th>خدمات</th><th>تاریخ</th></tr></thead>
              <tbody>
                <template v-for="row in data.overall_report" :key="`o-${serviceRowKey(row)}`">
                  <tr class="clickable-row" :class="{ expanded: isServicesExpanded(row) }" @click="openVehicleDetail(row.vehicle_id)">
                    <td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.car_color || '-' }}</td><td><PlateBadge class="report-plate" :plate-number="row.plate_number" :plate-left="row.plate_left" :plate-letter="row.plate_letter" :plate-mid="row.plate_mid" :plate-right="row.plate_right" :plate-type="row.plate_type || 'car'" compact /></td><td>{{ formatStatus(row.status) }}</td><td>{{ money(row.carwash_share) }}</td><td>{{ money(row.worker_share) }}</td><td>{{ money(row.discount_total) }}</td><td>{{ money(row.tip_amount) }}</td><td>{{ row.worker_name }}</td><td><div class="services-preview-cell"><span class="services-preview-text">{{ servicesPreview(row.services) }}</span><button v-if="hasExpandableServices(row.services)" type="button" class="services-toggle-btn" :class="{ active: isServicesExpanded(row) }" @click.stop="toggleServicesRow(row)"><span class="services-toggle-dots">•••</span></button></div></td><td>{{ dateTime(row.created_at) }}</td>
                  </tr>
                  <tr v-if="isServicesExpanded(row)" class="services-expanded-row">
                    <td colspan="14">
                      <div class="services-expanded-box">
                        <strong>همه خدمات انجام‌شده</strong>
                        <p>{{ normalizeServicesValue(row.services) }}</p>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else-if="activeTab === 'carwash'">
          <h3>گزارش حق کارواش</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>رنگ</th><th>پلاک</th><th>حق کارواش</th><th>نام نیرو</th><th>تاریخ</th></tr></thead><tbody>
            <tr v-for="row in data.carwash_report" :key="`c-${row.row}`"><td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.car_color || '-' }}</td><td><PlateBadge class="report-plate" :plate-number="row.plate_number" :plate-left="row.plate_left" :plate-letter="row.plate_letter" :plate-mid="row.plate_mid" :plate-right="row.plate_right" :plate-type="row.plate_type || 'car'" compact /></td><td>{{ money(row.carwash_share) }}</td><td>{{ row.worker_name }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
          </tbody></table></div>
        </template>

        <template v-else-if="activeTab === 'worker'">
          <div class="worker-head">
            <h3>گزارش حق نیرو</h3>
            <div v-if="selectedWorkerSummary" class="action-row">
              <button class="primary-btn btn-with-icon" @click="openPayoutModal('wage')"><IconlyIcon name="wallet" size="sm" />{{ payoutButtonLabel }}</button>
              <button class="primary-btn btn-with-icon" @click="openPayoutModal('insurance')"><IconlyIcon name="wallet" size="sm" />{{ insurancePayoutButtonLabel }}</button>
              <button class="secondary-btn btn-with-icon" @click="openPayoutModal('tip')"><IconlyIcon name="wallet" size="sm" />{{ tipPayoutButtonLabel }}</button>
            </div>
          </div>
          <div v-if="selectedWorkerSummary" class="worker-summary-grid">
            <article class="payout-card"><p>نوع پرداخت</p><strong>{{ workerPaymentTypeLabel(selectedWorkerSummary.payment_type) }}</strong></article>
            <article v-if="selectedWorkerSummary.payment_type === 'hourly'" class="payout-card"><p>ساعت کاری</p><strong>{{ workHoursLabel(selectedWorkerSummary.attendance_hours) }}</strong></article>
            <article v-if="selectedWorkerSummary.payment_type === 'hourly'" class="payout-card"><p>نرخ ساعتی</p><strong>{{ money(selectedWorkerSummary.hourly_wage) }}</strong></article>
            <article class="payout-card"><p>حق حقوق</p><strong>{{ money(selectedWorkerSummary.wage_total) }}</strong></article>
            <article class="payout-card"><p>پاداش</p><strong>{{ money(selectedWorkerSummary.bonus_total) }}</strong></article>
            <article class="payout-card"><p>جریمه</p><strong>{{ money(selectedWorkerSummary.penalty_total) }}</strong></article>
            <article class="payout-card"><p>پرداخت شده</p><strong>{{ money(selectedWorkerSummary.wage_paid_total) }}</strong></article>
            <article class="payout-card"><p>مانده حقوق</p><strong>{{ money(selectedWorkerSummary.payable_total) }}</strong></article>
            <article class="payout-card"><p>حق بیمه هر ماه</p><strong>{{ money(selectedWorkerSummary.insurance_monthly_amount) }}</strong></article>
            <article class="payout-card"><p>پرداخت بیمه تا این ماه</p><strong>{{ money(selectedWorkerSummary.insurance_paid_total) }}</strong></article>
            <article class="payout-card"><p>مانده بیمه تا این ماه</p><strong>{{ money(selectedWorkerSummary.insurance_balance) }}</strong></article>
            <article class="payout-card"><p>انعام</p><strong>{{ money(selectedWorkerSummary.tip_balance) }}</strong></article>
          </div>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>رنگ</th><th>پلاک</th><th>حق نیرو</th><th>نام نیرو</th><th>تاریخ</th></tr></thead><tbody>
            <tr v-for="row in data.worker_report" :key="`w-${row.row}`"><td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.car_color || '-' }}</td><td><PlateBadge class="report-plate" :plate-number="row.plate_number" :plate-left="row.plate_left" :plate-letter="row.plate_letter" :plate-mid="row.plate_mid" :plate-right="row.plate_right" :plate-type="row.plate_type || 'car'" compact /></td><td>{{ money(row.worker_share) }}</td><td>{{ row.worker_name }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
          </tbody></table></div>
          <div v-if="selectedWorkerSummary" class="transactions-shell">
            <div class="worker-head">
              <h3>تراکنش‌های مالی {{ selectedWorkerSummary.worker_name }}</h3>
              <div class="action-row">
                <button class="secondary-btn btn-with-icon" @click="openAdjustmentModal('bonus')"><IconlyIcon name="plus" size="sm" />ثبت پاداش</button>
                <button class="secondary-btn danger-soft btn-with-icon" @click="openAdjustmentModal('penalty')"><IconlyIcon name="trash" size="sm" />ثبت جریمه</button>
              </div>
            </div>
            <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نوع</th><th>مبلغ</th><th>ماه بیمه</th><th>سفارش</th><th>توضیح</th><th>زمان</th></tr></thead><tbody>
              <tr v-for="(row, index) in selectedWorkerTransactions" :key="row.id"><td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td><td>{{ payoutKindLabel(row.kind) }}</td><td>{{ money(row.amount) }}</td><td>{{ row.reference_month || '-' }}</td><td>{{ row.vehicle_job_id || '-' }}</td><td>{{ row.note || '-' }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
              <tr v-if="!selectedWorkerTransactions.length"><td colspan="7">تراکنشی ثبت نشده است.</td></tr>
            </tbody></table></div>
          </div>
        </template>

        <template v-else-if="activeTab === 'tips'">
          <h3>گزارش انعام</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>رنگ</th><th>پلاک</th><th>انعام</th><th>نام نیرو</th><th>کالا</th><th>تاریخ</th></tr></thead><tbody>
            <tr v-for="row in data.tips_report" :key="`t-${row.row}`"><td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.car_color || '-' }}</td><td><PlateBadge class="report-plate" :plate-number="row.plate_number" :plate-left="row.plate_left" :plate-letter="row.plate_letter" :plate-mid="row.plate_mid" :plate-right="row.plate_right" :plate-type="row.plate_type || 'car'" compact /></td><td>{{ money(row.tip_amount) }}</td><td>{{ row.worker_name }}</td><td>{{ row.products || '-' }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
          </tbody></table></div>
        </template>

        <template v-else-if="activeTab === 'revenue'">
          <h3>گزارش درآمد</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>تاریخ</th><th>راننده</th><th>شماره</th><th>مدل خودرو</th><th>رنگ</th><th>پلاک</th><th>روش پرداخت</th><th>وضعیت پرداخت</th><th>خدمات</th><th>محصولات</th><th>تخفیف</th><th>انعام</th><th>مبلغ نهایی</th><th>وصول شده</th><th>مانده</th><th>شماره چک</th><th>سررسید</th></tr></thead><tbody>
            <tr v-for="row in data.revenue_report" :key="`r-${row.row}`"><td>{{ row.row }}</td><td>{{ dateTime(row.created_at) }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.car_color || '-' }}</td><td><PlateBadge class="report-plate" :plate-number="row.plate_number" :plate-left="row.plate_left" :plate-letter="row.plate_letter" :plate-mid="row.plate_mid" :plate-right="row.plate_right" :plate-type="row.plate_type || 'car'" compact /></td><td>{{ paymentMethodLabel(row.payment_method) }}</td><td>{{ paymentStateLabel(row.payment_status) }}</td><td>{{ money(row.service_amount) }}</td><td>{{ money(row.product_amount) }}</td><td>{{ money(row.discount_amount) }}</td><td>{{ money(row.tip_amount) }}</td><td>{{ money(row.final_total) }}</td><td>{{ money(row.received_amount) }}</td><td>{{ money(row.outstanding_amount) }}</td><td>{{ row.cheque_number || '-' }}</td><td>{{ dateOnly(row.reminder_due_at) }}</td></tr>
          </tbody></table></div>
        </template>

        <template v-else-if="activeTab === 'attendance'">
          <h3>گزارش ورود و خروج</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام پرسنل</th><th>نوع رویداد</th><th>منبع ثبت</th><th>زمان</th></tr></thead><tbody>
            <tr v-for="row in data.attendance_report" :key="`a-${row.row}`"><td>{{ row.row }}</td><td>{{ row.worker_name }}</td><td>{{ row.event_type === 'in' ? 'ورود' : 'خروج' }}</td><td>{{ row.source === 'manager' ? 'مدیر' : row.source === 'link' ? 'لینک پرسنل' : (row.source || '-') }}</td><td>{{ dateTime(row.event_at) }}</td></tr>
            <tr v-if="!data.attendance_report.length"><td colspan="5">رکوردی برای این بازه پیدا نشد.</td></tr>
          </tbody></table></div>
        </template>

        <template v-else-if="activeTab === 'blacklist'">
          <h3>گزارش لیست سیاه</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>پلاک</th><th>نوع وسیله</th><th>توضیح</th><th>ثبت کننده</th><th>تاریخ ثبت</th></tr></thead><tbody>
            <tr v-for="row in data.blacklist_report" :key="`b-${row.id || row.row}`">
              <td>{{ row.row }}</td>
              <td><PlateBadge class="report-plate" :plate-number="row.plate_number" :plate-left="row.plate_left" :plate-letter="row.plate_letter" :plate-mid="row.plate_mid" :plate-right="row.plate_right" :plate-type="row.plate_type || 'car'" compact /></td>
              <td>{{ row.plate_type === 'motorcycle' ? 'موتور سیکلت' : 'خودرو' }}</td>
              <td>{{ row.note || '-' }}</td>
              <td>{{ row.blocked_by_name || '-' }}</td>
              <td>{{ dateTime(row.created_at) }}</td>
            </tr>
            <tr v-if="!data.blacklist_report.length"><td colspan="6">پلاکی در لیست سیاه برای این بازه پیدا نشد.</td></tr>
          </tbody></table></div>
        </template>

      </section>
    </div>
  </AppShell>

  <VehicleDetailsModal
    :open="vehicleModal.open"
    :loading="vehicleModal.loading"
    :vehicle="vehicleModal.data"
    title="جزئیات کامل خودرو"
    @close="closeVehicleModal"
    @cancel="cancelVehicle"
    @block-plate="blockVehiclePlate"
  />

  <div v-if="payoutModal.open" class="modal-overlay" @click.self="closePayoutModal">
    <section class="modal-panel action-panel">
      <header class="modal-head">
        <h3>{{ payoutModal.target === 'tip' ? 'پرداخت انعام' : payoutModal.target === 'insurance' ? 'پرداخت حق بیمه' : 'پرداخت حقوق' }} {{ selectedWorkerSummary?.worker_name || '' }}</h3>
        <button class="close-btn" @click="closePayoutModal">✕</button>
      </header>
      <div class="modal-body">
        <label><span>نوع پرداخت</span><select v-model="payoutModal.mode"><option value="full">{{ payoutModal.target === 'tip' ? 'کل انعام' : payoutModal.target === 'insurance' ? 'کل حق بیمه' : 'کل حقوق' }}</option><option value="partial">{{ payoutModal.target === 'tip' ? 'بخشی از انعام' : payoutModal.target === 'insurance' ? 'بخشی از حق بیمه' : 'بخشی از حقوق' }}</option></select></label>
        <label v-if="payoutModal.target === 'insurance'">
          <span>ماه بیمه (شمسی)</span>
          <select v-model="payoutModal.insuranceMonth">
            <option value="" disabled>انتخاب ماه</option>
            <option v-for="item in insuranceMonthOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </label>
        <label v-if="payoutModal.mode === 'partial'"><span>مبلغ (تومان)</span><input :value="moneyInputValue(payoutModal.amount)" type="text" inputmode="numeric" @input="payoutModal.amount = parseMoneyInput($event.target.value)" /></label>
        <p v-if="payoutModal.mode === 'partial'" class="helper-note" :class="{ error: payoutValidationMessage }">
          {{ payoutValidationMessage || `مانده قابل پرداخت: ${money(payoutModalMaxAmount)}. مبلغ باید کمتر از مانده باشد.` }}
        </p>
        <p v-if="payoutSubmitError" class="helper-note error">
          {{ payoutSubmitError }}
        </p>
        <label><span>توضیح</span><input v-model="payoutModal.note" type="text" /></label>
        <button class="primary-btn" :disabled="payoutModal.submitting" @click="submitPayout">{{ payoutModal.submitting ? 'در حال ثبت...' : 'ثبت پرداخت' }}</button>
      </div>
    </section>
  </div>

  <div v-if="adjustmentModal.open" class="modal-overlay" @click.self="closeAdjustmentModal">
    <section class="modal-panel action-panel">
      <header class="modal-head">
        <h3>{{ adjustmentModal.kind === 'bonus' ? 'ثبت پاداش' : 'ثبت جریمه' }} برای {{ selectedWorkerSummary?.worker_name || '' }}</h3>
        <button class="close-btn" @click="closeAdjustmentModal">✕</button>
      </header>
      <div class="modal-body">
        <label><span>مبلغ (تومان)</span><input :value="moneyInputValue(adjustmentModal.amount)" type="text" inputmode="numeric" @input="adjustmentModal.amount = parseMoneyInput($event.target.value)" /></label>
        <label><span>توضیح</span><input v-model.trim="adjustmentModal.note" type="text" placeholder="ثبت دلیل پاداش یا جریمه" /></label>
        <button class="primary-btn" :disabled="adjustmentModal.submitting" @click="submitAdjustment">{{ adjustmentModal.submitting ? 'در حال ثبت...' : 'ثبت' }}</button>
      </div>
    </section>
  </div>

  <div v-if="pdfFormatModal.open" class="modal-overlay" @click.self="closePdfFormatModal">
    <section class="modal-panel pdf-format-panel">
      <header class="modal-head">
        <h3>انتخاب قالب PDF</h3>
        <button class="close-btn" @click="closePdfFormatModal">✕</button>
      </header>
      <div class="pdf-format-body">
        <button class="pdf-format-option" @click="selectPdfFormat('a4')">
          <strong>A4</strong>
          <span>خروجی گزارش فعلی</span>
        </button>
        <button class="pdf-format-option receipt" :disabled="!selectedWorkerSummary?.worker_id" @click="selectPdfFormat('receipt')">
          <strong>فیش</strong>
          <span>{{ selectedWorkerSummary?.worker_id ? 'مخصوص پرینتر حرارتی' : 'اول نیرو را انتخاب کنید' }}</span>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import api from '../../services/api'
import { useAuthStore } from '../../store/auth.store'
import AppShell from '../../components/layout/AppShell.vue'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import IconlyIcon from '../../components/base/IconlyIcon.vue'
import PlateBadge from '../../components/vehicles/PlateBadge.vue'
import VehicleDetailsModal from '../../components/vehicles/VehicleDetailsModal.vue'
import { formatJalaliDate, formatJalaliDateTime } from '../../utils/date'
import { formatThousandsToman, formatThousandsTomanValue, fromThousandsTomanInput } from '../../utils/money'
import { resolveApiErrorMessage } from '../../utils/apiError'

const activeTab = ref('overall')
const authStore = useAuthStore()
const workers = ref([])
const errorMessage = ref('')
const rangeOptions = [
  { key: 'today', label: 'امروز', icon: 'calendar' },
  { key: 'week', label: 'این هفته', icon: 'graph' },
  { key: 'month', label: 'این ماه', icon: 'document' },
  { key: 'all', label: 'کل', icon: 'category' }
]

const currentJalaliMonthValue = () => {
  const parts = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    month: '2-digit'
  }).formatToParts(new Date())
  return parts.find((item) => item.type === 'month')?.value || '01'
}

const filters = reactive({
  rangeKey: 'today',
  startJalali: '',
  endJalali: '',
  q: '',
  workerId: '',
  insuranceMonthJalali: currentJalaliMonthValue(),
  plateType: '',
  plateLeft: '',
  plateLetter: '',
  plateMid: '',
  plateRight: ''
})
const summary = reactive({ vehicles_count: 0, carwash_total: 0, worker_total: 0, tips_total: 0, discount_total: 0, final_total: 0, before_discount_total: 0, payable_worker_total: 0, bonus_total: 0, penalty_total: 0 })
const sectionTotals = reactive({ overall: {}, carwash: {}, worker: {}, tips: {}, revenue: {}, attendance: {}, blacklist: {} })
const data = reactive({ overall_report: [], carwash_report: [], worker_report: [], tips_report: [], attendance_report: [], blacklist_report: [], revenue_report: [] })
const expandedServiceRows = ref({})
const selectedWorkerSummary = ref(null)
const selectedWorkerTransactions = ref([])
const vehicleModal = reactive({ open: false, loading: false, data: null })
const payoutModal = reactive({ open: false, submitting: false, target: 'wage', mode: 'full', amount: 0, note: '', insuranceMonth: '' })
const payoutSubmitError = ref('')
const adjustmentModal = reactive({ open: false, submitting: false, kind: 'bonus', amount: 0, note: '' })
const pdfFormatModal = reactive({ open: false })
const reportExportRef = ref(null)
const exportState = reactive({ csvLoading: false, pdfLoading: false })

const tabs = [
  { key: 'overall', label: 'گزارش کل', icon: 'document' },
  { key: 'carwash', label: 'حق کارواش', icon: 'wallet' },
  { key: 'worker', label: 'حق نیرو', icon: 'users3' },
  { key: 'tips', label: 'انعام', icon: 'message' },
  { key: 'revenue', label: 'گزارش درآمد', icon: 'graph' },
  { key: 'attendance', label: 'ورود و خروج', icon: 'calendar' },
  { key: 'blacklist', label: 'لیست سیاه', icon: 'danger' }
]
const moneyInputValue = (value) => formatThousandsTomanValue(value, { maximumFractionDigits: 0 })
const parseMoneyInput = (value) => fromThousandsTomanInput(normalizeDigits(value))

const insuranceMonthOptions = [
  { value: '01', label: 'فروردین' },
  { value: '02', label: 'اردیبهشت' },
  { value: '03', label: 'خرداد' },
  { value: '04', label: 'تیر' },
  { value: '05', label: 'مرداد' },
  { value: '06', label: 'شهریور' },
  { value: '07', label: 'مهر' },
  { value: '08', label: 'آبان' },
  { value: '09', label: 'آذر' },
  { value: '10', label: 'دی' },
  { value: '11', label: 'بهمن' },
  { value: '12', label: 'اسفند' }
]

const money = (v) => formatThousandsToman(v)
const dateTime = (v) => formatJalaliDate(v)
const dateOnly = (v) => formatJalaliDate(v)
const receiptDateTime = (v) => formatJalaliDateTime(v)
const faNumber = (value) => Number(value || 0).toLocaleString('fa-IR')
const formatStatus = (value) => ({ entered: 'در انتظار تکمیل', assigned: 'در انتظار تکمیل', in_progress: 'در حال انجام', ready_to_settle: 'در انتظار تکمیل', released: 'ترخیص شده', cancelled: 'لغو' }[value] || '-')
const workerPaymentTypeLabel = (value) => ({ hourly: 'ساعتی', fixed: 'ثابت', percent: 'درصدی' }[value] || '-')
const workHoursLabel = (value) => `${Number(value || 0).toLocaleString('fa-IR', { maximumFractionDigits: 2 })} ساعت`
const payoutKindLabel = (value) => ({ wage_payment: 'پرداخت حقوق', tip_payment: 'پرداخت انعام', insurance_payment: 'پرداخت حق بیمه', bonus: 'پاداش', penalty: 'جریمه' }[value] || value)
const paymentMethodLabel = (value) => ({ cash: 'نقدی', transfer: 'کارت به کارت', cheque: 'چک', credit: 'نسیه', pos: 'کارت‌خوان', manual: 'دستی' }[value] || value || '-')
const paymentStateLabel = (value) => ({ success: 'تسویه شده', pending: 'در انتظار', failed: 'ناموفق', refunded: 'مرجوعی' }[value] || value || '-')
const normalizeServicesValue = (value) => {
  const text = String(value || '').trim()
  return text || '-'
}
const hasExpandableServices = (value) => normalizeServicesValue(value).length > 24
const servicesPreview = (value) => {
  const text = normalizeServicesValue(value)
  if (text === '-' || text.length <= 24) return text
  return `${text.slice(0, 24).trim()}...`
}
const serviceRowKey = (row) => String(row?.vehicle_id || row?.row || '')
const isServicesExpanded = (row) => Boolean(expandedServiceRows.value[serviceRowKey(row)])
const toggleServicesRow = (row) => {
  const key = serviceRowKey(row)
  if (!key) return
  expandedServiceRows.value = {
    ...expandedServiceRows.value,
    [key]: !expandedServiceRows.value[key]
  }
}
const overallAmount = (key) => Number(sectionTotals.overall?.[key] ?? summary?.[key] ?? 0)
const overallFinalAmount = () => {
  const explicitTotal = overallAmount('final_total')
  if (explicitTotal > 0) return explicitTotal
  return overallAmount('carwash_total') + overallAmount('worker_total') + overallAmount('tips_total')
}
const overallBeforeDiscountAmount = () => (
  Math.round(overallFinalAmount()) + Math.round(overallAmount('discount_total'))
)
const visibleSummaryCards = computed(() => {
  if (activeTab.value === 'overall') {
    return [
      { key: 'visits_count', label: 'کل مراجعات', value: Number(overallAmount('vehicles_count')).toLocaleString('fa-IR') },
      { key: 'final_total', label: 'مبلغ نهایی', value: money(overallFinalAmount()) },
      { key: 'carwash_total', label: 'حق کارواش', value: money(overallAmount('carwash_total')) },
      { key: 'worker_total', label: 'حق نیرو', value: money(overallAmount('worker_total')) },
      { key: 'tips_total', label: 'انعام', value: money(overallAmount('tips_total')) },
      { key: 'discount_total', label: 'جمع تخفیف', value: money(overallAmount('discount_total')) },
      { key: 'before_discount_total', label: 'قبل از تخفیف', value: money(overallBeforeDiscountAmount()) }
    ]
  }
  if (activeTab.value === 'carwash') {
    return [
      { key: 'carwash_total', label: 'حق کارواش', value: money(summary.carwash_total) }
    ]
  }
  if (activeTab.value === 'worker') {
    return [
      { key: 'worker_total', label: 'حق نیرو', value: money(summary.worker_total) },
      { key: 'payable_worker_total', label: 'مانده حق نیرو', value: money(summary.payable_worker_total) },
      { key: 'insurance_total', label: 'مانده حق بیمه', value: money(summary.insurance_total) },
      { key: 'bonus_total', label: 'پاداش', value: money(summary.bonus_total) },
      { key: 'penalty_total', label: 'جریمه', value: money(summary.penalty_total) }
    ]
  }
  if (activeTab.value === 'tips') {
    return [
      { key: 'tips_total', label: 'انعام', value: money(summary.tips_total) }
    ]
  }
  if (activeTab.value === 'revenue') {
    return [
      { key: 'revenue_total', label: 'درآمد وصول‌شده', value: money(sectionTotals.revenue.revenue_total) }
    ]
  }
  if (activeTab.value === 'attendance') {
    const checkins = data.attendance_report.filter((item) => item.event_type === 'in').length
    const checkouts = data.attendance_report.filter((item) => item.event_type === 'out').length
    return [
      { key: 'attendance_count', label: 'کل رویدادها', value: Number(sectionTotals.attendance.count || 0).toLocaleString('fa-IR') },
      { key: 'attendance_checkins', label: 'ورودها', value: Number(checkins || 0).toLocaleString('fa-IR') },
      { key: 'attendance_checkouts', label: 'خروج‌ها', value: Number(checkouts || 0).toLocaleString('fa-IR') },
    ]
  }
  if (activeTab.value === 'blacklist') {
    return [
      { key: 'blacklist_count', label: 'تعداد پلاک‌های مسدود', value: Number(sectionTotals.blacklist.count || 0).toLocaleString('fa-IR') }
    ]
  }
  return []
})

const toIsoDate = (value) => {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const resolveRangeDates = (rangeKey) => {
  if (rangeKey === 'all') return { start: '', end: '' }
  const now = new Date()
  const end = new Date(now)
  let start = new Date(now)
  if (rangeKey === 'today') {
    return { start: toIsoDate(start), end: toIsoDate(end) }
  }
  if (rangeKey === 'week') {
    const day = now.getDay()
    const offset = day === 0 ? 6 : day - 1
    start.setDate(now.getDate() - offset)
    return { start: toIsoDate(start), end: toIsoDate(end) }
  }
  if (rangeKey === 'month') {
    start = new Date(now.getFullYear(), now.getMonth(), 1)
    return { start: toIsoDate(start), end: toIsoDate(end) }
  }
  return { start: '', end: '' }
}

const setRange = (rangeKey) => {
  filters.rangeKey = rangeKey
}

const reportPeriodLabel = computed(() => {
  if (filters.startJalali && filters.endJalali) return `از ${filters.startJalali} تا ${filters.endJalali}`
  const params = buildReportParams()
  const start = params.start ? formatJalaliDate(params.start) : ''
  const end = params.end ? formatJalaliDate(params.end) : ''
  if (start && end) return `از ${start} تا ${end}`
  if (start) return `از ${start}`
  if (end) return `تا ${end}`
  return 'کل دوره'
})

const buildReportParams = () => {
  const manualStart = parseJalaliToIso(filters.startJalali)
  const manualEnd = parseJalaliToIso(filters.endJalali)
  const quickRange = resolveRangeDates(filters.rangeKey)
  let start = manualStart || quickRange.start
  let end = manualEnd || quickRange.end
  if (start && end && start > end) {
    const temp = start
    start = end
    end = temp
  }
  const workerId = Number.parseInt(filters.workerId, 10)
  return {
    start: start || undefined,
    end: end || undefined,
    q: (filters.q || '').trim() || undefined,
    worker_id: Number.isInteger(workerId) && workerId > 0 ? workerId : undefined,
    insurance_month: normalizeInsuranceMonth(filters.insuranceMonthJalali),
    plate_type: filters.plateType || undefined,
    plate_left: filters.plateLeft || undefined,
    plate_letter: filters.plateLetter || undefined,
    plate_mid: filters.plateMid || undefined,
    plate_right: filters.plateRight || undefined
  }
}

const payoutButtonLabel = computed(() => `پرداخت حقوق ${selectedWorkerSummary.value?.worker_name || ''}`)
const insurancePayoutButtonLabel = computed(() => `پرداخت حق بیمه ${selectedWorkerSummary.value?.worker_name || ''}`)
const tipPayoutButtonLabel = computed(() => `پرداخت انعام ${selectedWorkerSummary.value?.worker_name || ''}`)
const selectedInsuranceMonthKey = computed(() => normalizeInsuranceMonth(payoutModal.insuranceMonth) || selectedWorkerSummary.value?.insurance_month || '')
const selectedInsuranceMonthPaidAmount = computed(() => {
  if (!selectedInsuranceMonthKey.value) return 0
  return selectedWorkerTransactions.value
    .filter((item) => item.kind === 'insurance_payment' && item.reference_month === selectedInsuranceMonthKey.value)
    .reduce((sum, item) => sum + Number(item.amount || 0), 0)
})
const selectedInsuranceMonthBalance = computed(() => {
  const monthlyAmount = Number(selectedWorkerSummary.value?.insurance_monthly_amount || 0)
  const dueStartMonth = normalizeInsuranceMonth(selectedWorkerSummary.value?.insurance_due_start_month)
  if (!isJalaliMonthOnOrAfter(selectedInsuranceMonthKey.value, dueStartMonth)) return 0
  return Math.max(0, monthlyAmount - selectedInsuranceMonthPaidAmount.value)
})
const payoutModalMaxAmount = computed(() => (
  payoutModal.target === 'tip'
    ? Number(selectedWorkerSummary.value?.tip_balance || 0)
    : payoutModal.target === 'insurance'
      ? selectedInsuranceMonthBalance.value
      : Number(selectedWorkerSummary.value?.payable_total || 0)
))
const payoutValidationMessage = computed(() => {
  if (payoutModal.mode !== 'partial') return ''
  const amount = Number(fromThousandsTomanInput(payoutModal.amount || 0))
  if (amount <= 0) return 'مبلغ پرداخت باید بیشتر از صفر باشد.'
  if (amount >= payoutModalMaxAmount.value) return `مبلغ واردشده از مانده بیشتر است. مبلغ باید کمتر از مانده باشد: ${money(payoutModalMaxAmount.value)}`
  return ''
})
const isPayoutAmountValid = computed(() => {
  if (payoutModal.mode !== 'partial') return payoutModalMaxAmount.value > 0
  const amount = Number(fromThousandsTomanInput(payoutModal.amount || 0))
  return amount > 0 && amount < payoutModalMaxAmount.value
})

const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
  .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))

const parseJalaliToIso = (input) => {
  const value = (input || '').trim().replace(/-/g, '/')
  const match = value.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/)
  if (!match) return ''
  const jy = Number(match[1]) - 979
  const jm = Number(match[2]) - 1
  const jd = Number(match[3]) - 1
  const jDaysInMonth = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
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
  return `${gy}-${String(gm + 1).padStart(2, '0')}-${String(gDayNo + 1).padStart(2, '0')}`
}

const normalizeInsuranceMonth = (value) => {
  const normalized = String(value || '').trim().replace(/-/g, '/')
  const parts = normalized.split('/')
  if (parts.length === 1) {
    const monthOnly = normalizeDigits(parts[0]).replace(/\D/g, '').slice(0, 2).padStart(2, '0')
    const year = resolveInsuranceYear()
    const monthNumber = Number(monthOnly)
    return monthNumber >= 1 && monthNumber <= 12 && year ? `${year}/${monthOnly}` : ''
  }
  if (parts.length < 2) return ''
  const year = normalizeDigits(parts[0]).replace(/\D/g, '').slice(0, 4)
  const month = normalizeDigits(parts[1]).replace(/\D/g, '').slice(0, 2).padStart(2, '0')
  const monthNumber = Number(month)
  if (!year || monthNumber < 1 || monthNumber > 12) return ''
  return `${year}/${month}`
}

const jalaliMonthIndex = (value) => {
  const monthValue = normalizeInsuranceMonth(value)
  if (!monthValue) return null
  const [year, month] = monthValue.split('/').map((item) => Number(item))
  if (!Number.isFinite(year) || !Number.isFinite(month)) return null
  return (year * 12) + month
}

const isJalaliMonthAfter = (left, right) => {
  const leftIndex = jalaliMonthIndex(left)
  const rightIndex = jalaliMonthIndex(right)
  return leftIndex !== null && rightIndex !== null && leftIndex > rightIndex
}

const isJalaliMonthOnOrAfter = (left, right) => {
  const leftIndex = jalaliMonthIndex(left)
  const rightIndex = jalaliMonthIndex(right)
  return leftIndex !== null && rightIndex !== null && leftIndex >= rightIndex
}

const insuranceMonthToFilterDate = (value) => {
  const monthValue = normalizeInsuranceMonth(value)
  return monthValue ? monthValue.split('/')[1] : ''
}

const getCurrentJalaliYear = () => {
  const formatter = new Intl.DateTimeFormat('fa-IR-u-ca-persian', { year: 'numeric' })
  const yearPart = formatter.formatToParts(new Date()).find((item) => item.type === 'year')
  return normalizeDigits(yearPart?.value || '').replace(/\D/g, '').slice(0, 4)
}

const resolveInsuranceYear = () => {
  const candidates = [
    selectedWorkerSummary.value?.insurance_month,
    filters.insuranceMonthJalali,
  ]
  for (const item of candidates) {
    const match = normalizeDigits(String(item || '')).match(/(\d{4})/)
    if (match?.[1]) return match[1]
  }
  return getCurrentJalaliYear()
}

const normalizePlateLetter = (value) => {
  const raw = String(value || '').replace(/\s+/g, '').slice(0, 1)
  const englishMap = { A: 'ا', B: 'ب', D: 'د', H: 'ه', J: 'ج', L: 'ل', M: 'م', N: 'ن', P: 'پ', S: 'س', T: 'ط', V: 'و', Y: 'ی' }
  const upper = raw.toUpperCase()
  if (englishMap[upper]) return englishMap[upper]
  return raw.replace(/[^آابپتثجچحخدذرزسشصضطظعغفقکگلمنوهی]/g, '')
}

const normalizePlateFilters = () => {
  if (filters.plateType !== 'motorcycle' && filters.plateType !== 'car') filters.plateType = ''
  filters.plateLeft = normalizeDigits(filters.plateLeft).replace(/\D/g, '').slice(0, 2)
  filters.plateRight = normalizeDigits(filters.plateRight).replace(/\D/g, '').slice(0, 2)
  filters.plateMid = normalizeDigits(filters.plateMid).replace(/\D/g, '').slice(0, 3)
  filters.plateLetter = filters.plateType === 'motorcycle'
    ? normalizeDigits(filters.plateLetter).replace(/\D/g, '').slice(0, 5)
    : normalizePlateLetter(filters.plateLetter)
  if (filters.plateType === 'motorcycle') {
    filters.plateLeft = ''
    filters.plateRight = ''
  }
}

const fetchWorkers = async () => {
  try {
    const { data } = await api.get('/workers/')
    workers.value = Array.isArray(data) ? data : []
  } catch (_error) {
    workers.value = []
  }
}

let fetchToken = 0
const fetchReports = async () => {
  const token = ++fetchToken
  errorMessage.value = ''
  try {
    const { data: payload } = await api.get('/reports/dashboard/', {
      params: buildReportParams()
    })
    if (token !== fetchToken) return
    Object.assign(summary, payload.summary || {})
    Object.assign(sectionTotals.overall, payload.section_totals?.overall || {})
    Object.assign(sectionTotals.carwash, payload.section_totals?.carwash || {})
    Object.assign(sectionTotals.worker, payload.section_totals?.worker || {})
    Object.assign(sectionTotals.tips, payload.section_totals?.tips || {})
    Object.assign(sectionTotals.attendance, payload.section_totals?.attendance || {})
    Object.assign(sectionTotals.blacklist, payload.section_totals?.blacklist || {})
    Object.assign(sectionTotals.revenue, payload.section_totals?.revenue || {})
    expandedServiceRows.value = {}
    data.overall_report = payload.overall_report || []
    data.carwash_report = payload.carwash_report || []
    data.worker_report = payload.worker_report || []
    data.tips_report = payload.tips_report || []
    data.attendance_report = payload.attendance_report || []
    data.blacklist_report = payload.blacklist_report || []
    data.revenue_report = payload.revenue_report || []
    selectedWorkerSummary.value = payload.selected_worker_summary || null
    selectedWorkerTransactions.value = payload.selected_worker_transactions || []
  } catch (error) {
    if (token !== fetchToken) return
    errorMessage.value = resolveApiErrorMessage(error, 'بارگذاری گزارشات ناموفق بود.')
  }
}

const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#039;')

const workerReceiptOrderPrice = (row) => {
  if (row?.service_total !== undefined && row?.service_total !== null) {
    const serviceTotal = Number(row.service_total || 0)
    if (serviceTotal > 0) return serviceTotal
  }
  if (row?.services_total !== undefined && row?.services_total !== null) {
    const servicesTotal = Number(row.services_total || 0)
    if (servicesTotal > 0) return servicesTotal
  }
  if (row?.service_amount !== undefined && row?.service_amount !== null) {
    const serviceAmount = Number(row.service_amount || 0)
    if (serviceAmount > 0) return serviceAmount
  }
  if (row?.final_total_without_tip !== undefined && row?.final_total_without_tip !== null) {
    const finalWithoutTip = Number(row.final_total_without_tip || 0)
    if (finalWithoutTip > 0) return finalWithoutTip
  }
  if (row?.final_total !== undefined && row?.final_total !== null) {
    const finalBase = Math.max(0, Number(row.final_total || 0) - Number(row.tip_amount || 0))
    if (finalBase > 0) return finalBase
  }
  const commissionPercent = Number(row?.worker_commission_percent || selectedWorkerSummary.value?.default_commission_percent || 0)
  const workerShare = Number(row?.worker_share || 0)
  if (workerShare > 0 && commissionPercent > 0) {
    return (workerShare * 100) / commissionPercent
  }
  return 0
}

const workerReceiptRows = computed(() => (
  Array.isArray(data.worker_report) ? data.worker_report : []
).map((row, index) => ({
  row: index + 1,
  date: receiptDateTime(row.created_at),
  car: row.car_model || '-',
  price: workerReceiptOrderPrice(row),
  tip: Number(row.tip_amount || 0),
  share: Number(row.worker_share || 0)
})))

const workerReceiptTotalServices = computed(() => workerReceiptRows.value.reduce((sum, row) => sum + row.price, 0))
const workerReceiptTotalTip = computed(() => workerReceiptRows.value.reduce((sum, row) => sum + row.tip, 0))
const workerReceiptStaffShare = computed(() => workerReceiptRows.value.reduce((sum, row) => sum + row.share, 0))
const workerReceiptGrandTotal = computed(() => workerReceiptStaffShare.value + workerReceiptTotalTip.value)

const buildWorkerReceiptElement = () => {
  const rowsHtml = workerReceiptRows.value.map((row) => `
    <tr>
      <td>${escapeHtml(faNumber(row.row))}</td>
      <td>${escapeHtml(row.date)}</td>
      <td>${escapeHtml(row.car)}</td>
      <td>${escapeHtml(money(row.price))}</td>
      <td>${escapeHtml(money(row.tip))}</td>
    </tr>
  `).join('')
  const element = document.createElement('div')
  element.innerHTML = `
    <article class="worker-receipt-pdf" dir="rtl">
      <header>
        <strong>${escapeHtml(authStore.user?.tenant_address || authStore.user?.tenant_name || '-')}</strong>
        <span>صورت‌حساب: ${escapeHtml(selectedWorkerSummary.value?.worker_name || '-')}</span>
        <span>دوره گزارش: ${escapeHtml(reportPeriodLabel.value)}</span>
      </header>
      <table>
        <thead>
          <tr><th>#</th><th>تاریخ</th><th>ماشین</th><th>قیمت</th><th>انعام</th></tr>
        </thead>
        <tbody>${rowsHtml || '<tr><td colspan="5">رکوردی ثبت نشده است.</td></tr>'}</tbody>
      </table>
      <footer>
        <p><span>جمع کل قیمت خدمات</span><strong>${escapeHtml(money(workerReceiptTotalServices.value))}</strong></p>
        <p><span>جمع کل انعام</span><strong>${escapeHtml(money(workerReceiptTotalTip.value))}</strong></p>
        <p><span>سهم پرسنل</span><strong>${escapeHtml(money(workerReceiptStaffShare.value))}</strong></p>
        <p class="grand"><span>سهم پرسنل + انعام</span><strong>${escapeHtml(money(workerReceiptGrandTotal.value))}</strong></p>
      </footer>
    </article>
  `
  const style = document.createElement('style')
  style.textContent = `
    .worker-receipt-pdf,.worker-receipt-pdf *{box-sizing:border-box;color:#000!important;background:#fff!important;background-color:#fff!important;box-shadow:none!important;text-shadow:none!important;border-color:#000!important;font-family:Tahoma,Arial,sans-serif!important;font-weight:900!important;letter-spacing:0!important}
    .worker-receipt-pdf{width:80mm;max-width:80mm;min-width:0;padding:3mm;direction:rtl;line-height:1.45;font-size:11px;overflow:hidden}
    .worker-receipt-pdf header{display:grid;gap:4px;text-align:center;padding-bottom:7px;border-bottom:2px solid #000}
    .worker-receipt-pdf header strong{font-size:13px;line-height:1.6}
    .worker-receipt-pdf header span{font-size:11px;line-height:1.6}
    .worker-receipt-pdf table{width:100%;max-width:100%;border-collapse:collapse;table-layout:fixed;margin-top:8px;border:2px solid #000}
    .worker-receipt-pdf th,.worker-receipt-pdf td{border:1.5px solid #000;padding:4px 2px;text-align:center;vertical-align:middle;font-size:8px;line-height:1.35;overflow-wrap:anywhere;word-break:break-word;white-space:normal}
    .worker-receipt-pdf th:first-child,.worker-receipt-pdf td:first-child{width:8%}
    .worker-receipt-pdf th:nth-child(2),.worker-receipt-pdf td:nth-child(2){width:25%}
    .worker-receipt-pdf th:nth-child(3),.worker-receipt-pdf td:nth-child(3){width:27%}
    .worker-receipt-pdf th:nth-child(4),.worker-receipt-pdf td:nth-child(4){width:20%}
    .worker-receipt-pdf th:nth-child(5),.worker-receipt-pdf td:nth-child(5){width:20%}
    .worker-receipt-pdf footer{display:grid;gap:4px;margin-top:8px;padding-top:7px;border-top:2px solid #000}
    .worker-receipt-pdf footer p{margin:0;display:flex;justify-content:space-between;gap:8px;font-size:12px;line-height:1.6}
    .worker-receipt-pdf footer .grand{padding-top:5px;border-top:2px solid #000;font-size:13px}
  `
  const wrapper = document.createElement('div')
  wrapper.style.position = 'fixed'
  wrapper.style.top = '0'
  wrapper.style.left = '0'
  wrapper.style.width = '80mm'
  wrapper.style.maxWidth = '80mm'
  wrapper.style.background = '#fff'
  wrapper.style.zIndex = '-1'
  wrapper.style.pointerEvents = 'none'
  wrapper.appendChild(style)
  wrapper.appendChild(element.firstElementChild)
  document.body.appendChild(wrapper)
  return wrapper
}

const exportPdfAsA4 = async () => {
  if (!reportExportRef.value) return
  await nextTick()
  const html2pdfModule = await import('html2pdf.js')
  const html2pdf = html2pdfModule.default || html2pdfModule
  const worker = html2pdf()
    .set({
      margin: 8,
      filename: `reports-${activeTab.value}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' },
      pagebreak: { mode: ['css', 'legacy'] }
    })
    .from(reportExportRef.value)
    .toPdf()
  const pdf = await worker.get('pdf')
  downloadBlob(pdf.output('blob'), `reports-${activeTab.value}.pdf`)
}

const exportWorkerReceiptPdf = async () => {
  if (activeTab.value !== 'worker' || !selectedWorkerSummary.value?.worker_id) {
    errorMessage.value = 'برای ساخت فیش، اول یک نیرو را از فیلتر انتخاب کنید.'
    return
  }
  await fetchReports()
  await nextTick()
  const receiptElement = buildWorkerReceiptElement()
  try {
    const html2pdfModule = await import('html2pdf.js')
    const html2pdf = html2pdfModule.default || html2pdfModule
    const pageHeight = Math.max(120, Math.min(600, 78 + (workerReceiptRows.value.length * 12)))
    await nextTick()
    const worker = html2pdf()
      .set({
        margin: 0,
        filename: `worker-receipt-${selectedWorkerSummary.value.worker_id}.pdf`,
        image: { type: 'jpeg', quality: 1 },
        html2canvas: { scale: 3, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF: { unit: 'mm', format: [80, pageHeight], orientation: 'portrait' },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      })
      .from(receiptElement.querySelector('.worker-receipt-pdf'))
      .toPdf()
    const pdf = await worker.get('pdf')
    downloadBlob(pdf.output('blob'), `worker-receipt-${selectedWorkerSummary.value.worker_id}.pdf`)
  } finally {
    receiptElement.remove()
  }
}

const closePdfFormatModal = () => {
  pdfFormatModal.open = false
}

const selectPdfFormat = async (format) => {
  closePdfFormatModal()
  exportState.pdfLoading = true
  errorMessage.value = ''
  try {
    if (format === 'receipt') await exportWorkerReceiptPdf()
    else await exportPdfAsA4()
  } catch (error) {
    console.error('exportPdf error:', error)
    errorMessage.value = 'ساخت خروجی PDF ناموفق بود.'
  } finally {
    exportState.pdfLoading = false
  }
}

const exportCsv = async () => {
  exportState.csvLoading = true
  errorMessage.value = ''
  try {
    const response = await api.get('/reports/export/', {
      params: {
        tab: activeTab.value,
        ...buildReportParams()
      },
      responseType: 'blob',
      meta: { trackLoading: false }
    })
    downloadBlob(response.data, `reports-${activeTab.value}.csv`)
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'دریافت خروجی CSV ناموفق بود.')
  } finally {
    exportState.csvLoading = false
  }
}

const exportPdf = async () => {
  if (activeTab.value === 'worker') {
    pdfFormatModal.open = true
    return
  }
  exportState.pdfLoading = true
  errorMessage.value = ''
  try {
    await exportPdfAsA4()
  } catch (error) {
    console.error('exportPdf error:', error)
    errorMessage.value = 'ساخت خروجی PDF ناموفق بود.'
  } finally {
    exportState.pdfLoading = false
  }
}

const resetFilters = () => {
  filters.rangeKey = 'today'
  filters.startJalali = ''
  filters.endJalali = ''
  filters.q = ''
  filters.workerId = ''
  filters.insuranceMonthJalali = currentJalaliMonthValue()
  filters.plateType = ''
  filters.plateLeft = ''
  filters.plateLetter = ''
  filters.plateMid = ''
  filters.plateRight = ''
  expandedServiceRows.value = {}
}

const openVehicleDetail = async (vehicleId) => {
  vehicleModal.open = true
  vehicleModal.loading = true
  vehicleModal.data = null
  try {
    const { data } = await api.get(`/vehicles/${vehicleId}/`)
    vehicleModal.data = data
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بارگذاری جزئیات سفارش ناموفق بود.')
    closeVehicleModal()
  } finally {
    vehicleModal.loading = false
  }
}
const closeVehicleModal = () => {
  vehicleModal.open = false
  vehicleModal.loading = false
  vehicleModal.data = null
}

const reloadVehicleDetail = async () => {
  const vehicleId = vehicleModal.data?.id
  if (!vehicleId) return
  vehicleModal.loading = true
  try {
    const { data } = await api.get(`/vehicles/${vehicleId}/`)
    vehicleModal.data = data
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بارگذاری جزئیات سفارش ناموفق بود.')
    closeVehicleModal()
  } finally {
    vehicleModal.loading = false
  }
}

const cancelVehicle = async () => {
  if (!vehicleModal.data?.id) return
  try {
    await api.patch(`/vehicles/${vehicleModal.data.id}/status/`, { status: 'cancelled' })
    await Promise.all([reloadVehicleDetail(), fetchReports()])
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'لغو سفارش ناموفق بود.')
  }
}

const blockVehiclePlate = async () => {
  if (!vehicleModal.data?.id) return
  try {
    await api.post(`/vehicles/${vehicleModal.data.id}/block-plate/`, {})
    await Promise.all([reloadVehicleDetail(), fetchReports()])
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بلاک کردن پلاک ناموفق بود.')
  }
}

const openPayoutModal = (target = 'wage') => {
  payoutModal.open = true
  payoutSubmitError.value = ''
  payoutModal.target = target
  payoutModal.mode = 'full'
  payoutModal.note = ''
  payoutModal.insuranceMonth = String(selectedWorkerSummary.value?.insurance_month || '').split('/')[1] || '01'
  payoutModal.amount = Math.max(0, Math.round(
    target === 'tip'
      ? selectedWorkerSummary.value?.tip_balance || 0
      : target === 'insurance'
        ? selectedInsuranceMonthBalance.value || 0
        : selectedWorkerSummary.value?.payable_total || 0
  ))
}
const closePayoutModal = () => {
  payoutModal.open = false
  payoutModal.submitting = false
  payoutModal.target = 'wage'
  payoutModal.insuranceMonth = ''
  payoutSubmitError.value = ''
}
const submitPayout = async () => {
  if (!selectedWorkerSummary.value?.worker_id) return
  payoutSubmitError.value = ''
  const normalizedInsuranceMonth = payoutModal.target === 'insurance'
    ? normalizeInsuranceMonth(payoutModal.insuranceMonth)
    : ''
  if (payoutModal.target === 'insurance' && !normalizedInsuranceMonth) {
    payoutSubmitError.value = 'الان نمی‌توانید ثبت کنید، چون ماه بیمه به‌صورت معتبر انتخاب نشده است.'
    errorMessage.value = payoutSubmitError.value
    return
  }
  if (payoutModal.target === 'insurance' && selectedInsuranceMonthBalance.value <= 0) {
    payoutSubmitError.value = `الان نمی‌توانید ثبت کنید، چون ماه ${normalizedInsuranceMonth} قبلا تسویه شده است.`
    errorMessage.value = payoutSubmitError.value
    return
  }
  if (!isPayoutAmountValid.value) {
    payoutSubmitError.value = 'الان نمی‌توانید ثبت کنید، چون مبلغ باید بیشتر از صفر و کمتر از مانده مجاز باشد.'
    errorMessage.value = payoutSubmitError.value
    return
  }
  payoutModal.submitting = true
  try {
    await api.post('/reports/workers/payouts/', {
      worker_id: selectedWorkerSummary.value.worker_id,
      payout_target: payoutModal.target,
      mode: payoutModal.mode,
      amount: payoutModal.mode === 'partial' ? fromThousandsTomanInput(payoutModal.amount || 0) : undefined,
      insurance_month: normalizedInsuranceMonth || undefined,
      note: payoutModal.note || undefined
    })
    if (payoutModal.target === 'insurance' && normalizedInsuranceMonth) {
      filters.insuranceMonthJalali = insuranceMonthToFilterDate(normalizedInsuranceMonth)
    }
    closePayoutModal()
    await fetchReports()
  } catch (error) {
    const fallback = payoutModal.target === 'tip'
      ? 'الان نمی‌توانید پرداخت انعام را ثبت کنید.'
      : payoutModal.target === 'insurance'
        ? 'الان نمی‌توانید پرداخت حق بیمه را ثبت کنید.'
        : 'الان نمی‌توانید پرداخت را ثبت کنید.'
    const reason = resolveApiErrorMessage(error, fallback)
    payoutSubmitError.value = reason.startsWith('الان نمی‌توانید')
      ? reason
      : `الان نمی‌توانید ثبت کنید، چون ${reason}`
    errorMessage.value = payoutSubmitError.value
  } finally {
    payoutModal.submitting = false
  }
}

const openAdjustmentModal = (kind) => {
  adjustmentModal.open = true
  adjustmentModal.kind = kind
  adjustmentModal.amount = 0
  adjustmentModal.note = ''
}
const closeAdjustmentModal = () => {
  adjustmentModal.open = false
  adjustmentModal.submitting = false
}
const submitAdjustment = async () => {
  if (!selectedWorkerSummary.value?.worker_id) return
  if (!adjustmentModal.note.trim()) {
    errorMessage.value = 'توضیح پاداش یا جریمه الزامی است.'
    return
  }
  adjustmentModal.submitting = true
  try {
    await api.post('/reports/workers/adjustments/', {
      worker_id: selectedWorkerSummary.value.worker_id,
      kind: adjustmentModal.kind,
      amount: Number(adjustmentModal.amount || 0),
      note: adjustmentModal.note.trim()
    })
    closeAdjustmentModal()
    await fetchReports()
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'ثبت تعدیل ناموفق بود.')
  } finally {
    adjustmentModal.submitting = false
  }
}

let filterTimer = null
watch(() => [filters.q, filters.rangeKey, filters.startJalali, filters.endJalali, filters.workerId, filters.insuranceMonthJalali, filters.plateType, filters.plateLeft, filters.plateLetter, filters.plateMid, filters.plateRight], () => {
  normalizePlateFilters()
  if (filterTimer) clearTimeout(filterTimer)
  filterTimer = setTimeout(fetchReports, 280)
})

watch(() => [payoutModal.target, payoutModal.mode, payoutModal.insuranceMonth], () => {
  if (payoutModal.target !== 'insurance' || payoutModal.mode !== 'full') return
  payoutModal.amount = Math.max(0, Math.round(selectedInsuranceMonthBalance.value || 0))
})

onMounted(async () => {
  await fetchWorkers()
  await fetchReports()
})
</script>

<style scoped>
.reports-content{font-size:13px}
.range-bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.range-chip{border:1px solid #cbd5e1;background:#fff;color:#334155;padding:9px 16px;border-radius:999px;cursor:pointer;font-size:12px;font-weight:700;display:inline-flex;align-items:center;gap:8px}
.range-chip.active{background:#2563eb;border-color:#2563eb;color:#fff}
.filters-card{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:10px;padding:14px;border:1px solid #e2e8f0;border-radius:16px;margin-bottom:10px;align-items:end;background:linear-gradient(180deg,#fff,#f8fbff)}
.field{display:grid;gap:5px;font-size:12px}
.field span{display:inline-flex;align-items:center;gap:6px}
.field input,.field select{height:38px;border:1px solid #cbd5e1;border-radius:10px;padding:0 10px;font-size:12px;background:#fff}
.search-field{grid-column:span 2}
.plate-field{grid-column:span 2}
.filters-actions{grid-column:span 5;display:flex;align-items:flex-end;justify-content:flex-start;gap:12px;flex-wrap:wrap}
.plate-filter-shell{padding:10px;border:1px solid #dbe5f0;border-radius:14px;background:linear-gradient(180deg,#fdfefe,#f3f7fb)}
.plate-filter-row{display:grid;grid-template-columns:62px 62px 86px 30px 62px;gap:8px;align-items:center}
.plate-filter-row span{display:inline-flex;align-items:center;justify-content:center;height:38px;color:#64748b;font-weight:700}
.plate-filter-row input{text-align:center;padding:0;border:1px solid #c9d6e5;background:#fff;box-shadow:inset 0 1px 0 rgba(255,255,255,.8)}
.plate-filter-row-car{direction:ltr}
.plate-filter-blue{border-radius:10px;background-color:#2563eb;border:1px solid #1d4ed8}
.plate-filter-blue-input{
  font-weight:700;
  background-color:#2563eb
}
.plate-filter-row .plate-filter-blue-input:focus{
  outline:none;
  border-color:#ffffff;
  box-shadow:0 0 0 3px rgba(191,219,254,.28);
  background-color:#2563eb
}
.plate-filter-row .plate-filter-blue-input::placeholder{color:rgba(255,255,255,.78);
  background-color:#2563eb}
.plate-filter-row-motorcycle{grid-template-columns:minmax(0,1fr) 44px}
.plate-filter-motor-main{display:grid;grid-template-columns:86px 1fr;gap:8px;align-items:center}
.plate-filter-blue-motor{min-width:44px}
.summary-grid{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:8px;margin-bottom:10px}
.kpi-card{border:1px solid #e2e8f0;border-radius:12px;padding:10px;background:#f8fbff}
.kpi-card p{margin:0;color:#64748b;font-size:12px}
.kpi-card strong{display:block;margin-top:6px;font-size:15px;color:#0f172a}
.tabs-bar{display:flex;gap:6px;flex-wrap:wrap}
.export-studio-actions{display:grid;grid-template-columns:repeat(2,minmax(180px,220px));justify-content:start;gap:12px}
.export-action-btn{border:0;border-radius:18px;padding:14px 16px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;font-size:13px;font-weight:700;transition:transform .18s ease, box-shadow .18s ease, opacity .18s ease}
.export-action-btn:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 14px 30px rgba(15,23,42,.14)}
.export-action-btn:disabled{opacity:.7;cursor:not-allowed}
.export-action-btn.csv{background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff}
.export-action-btn.pdf{background:#fff;border:1px solid #cbd5e1;color:#0f172a}
.chip{border:0;background:#e2e8f0;color:#334155;padding:6px 12px;border-radius:999px;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;gap:8px}
.chip.active,.primary-btn{background:#2563eb;color:#fff}
.primary-btn,.secondary-btn,.close-btn{border:0;border-radius:10px;padding:8px 12px;cursor:pointer}
.secondary-btn{background:#e2e8f0}
.btn-with-icon{display:inline-flex;align-items:center;gap:8px}
.danger-soft{background:#fee2e2;color:#991b1b}
.range-chip.active :deep(.iconly-shell),
.chip.active :deep(.iconly-shell),
.primary-btn :deep(.iconly-shell) { --iconly-filter: brightness(0) saturate(100%) invert(100%); }
.danger-soft :deep(.iconly-shell) { --iconly-filter: brightness(0) saturate(100%) invert(20%) sepia(78%) saturate(2280%) hue-rotate(345deg) brightness(97%) contrast(92%); }
.table-card{border:1px solid #e2e8f0;border-radius:12px;padding:10px}
.table-card h3{margin:0 0 8px;font-size:15px}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:12px}
th,td{padding:7px 6px;border-bottom:1px solid #e2e8f0;text-align:right;white-space:normal;vertical-align:top;line-height:1.5;word-break:break-word}
.error-box{margin-bottom:10px;padding:10px;background:#fee2e2;color:#991b1b;border:1px solid #fecaca;border-radius:10px}
.clickable-row{cursor:pointer}
.clickable-row.expanded{background:#f8fbff}
.services-preview-cell{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.services-preview-text{flex:1;min-width:0}
.report-plate{min-width:58px}
.report-plate:deep(.plate-badge){padding:2px;border-radius:10px}
.report-plate:deep(.plate-white-wrap){gap:4px;padding:2px 5px}
.report-plate:deep(.plate-two),
.report-plate:deep(.plate-three){height:18px;font-size:11px;padding-top:3px;padding-bottom:2px}
.report-plate:deep(.plate-letter){min-width:10px;font-size:11px}
.report-plate:deep(.plate-blue){min-width:24px;font-size:10px;padding-top:3px;padding-bottom:2px}
.report-plate:deep(.motor-blue){min-width:22px;font-size:5px;gap:2px;padding-top:4px;padding-bottom:3px}
.report-plate:deep(.plate-motorcycle .motor-main){padding:3px 5px 4px;gap:1px;border-radius:7px 0 0 7px}
.report-plate:deep(.plate-motorcycle .plate-cell){font-size:7px}
.report-plate:deep(.plate-motorcycle .plate-cell.mid){font-size:9px;letter-spacing:.08em}
.report-plate:deep(.plate-motorcycle .plate-cell.bottom){font-size:11px;letter-spacing:.06em}
.services-toggle-btn{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#475569;cursor:pointer;flex-shrink:0;transition:.18s ease}
.services-toggle-btn:hover,.services-toggle-btn.active{border-color:#2563eb;background:#eff6ff;color:#1d4ed8}
.services-toggle-dots{font-size:15px;line-height:1;transform:translateY(-1px)}
.services-expanded-row td{padding:0 6px 10px;background:#f8fbff}
.services-expanded-box{margin:0 0 0 auto;padding:12px 14px;border:1px dashed #bfdbfe;border-radius:14px;background:linear-gradient(180deg,#ffffff,#eff6ff)}
.services-expanded-box strong{display:block;margin-bottom:6px;color:#0f172a;font-size:12px}
.services-expanded-box p{margin:0;color:#334155;line-height:1.8}
.worker-head,.action-row{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}
.worker-summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
.payout-card{border:1px solid #dbeafe;background:#f8fbff;border-radius:12px;padding:8px 10px}
.payout-card p{margin:0;color:#64748b;font-size:11px}
.payout-card strong{display:block;margin-top:6px;color:#0f172a;font-size:13px}
.transactions-shell{margin-top:14px}
.modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.48);display:flex;align-items:center;justify-content:center;z-index:90;padding:18px}
.modal-panel{width:min(720px,100%);background:#fff;border-radius:16px;overflow:hidden}
.modal-head{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid #e2e8f0}
.modal-step{margin:0;color:#64748b;font-size:12px}
.modal-body{padding:16px}
.modal-body{display:grid;gap:12px;grid-template-columns:repeat(2,minmax(0,1fr))}
.modal-body label{display:grid;gap:6px}
.helper-note{grid-column:1 / -1;margin:-4px 0 0;color:#475569;font-size:12px}
.helper-note.error{color:#b91c1c}

.plate-filter-row .plate-filter-blue-input{
  outline:none;
  border-color:#bfdbfe;
  box-shadow:0 0 0 3px rgba(191,219,254,.28);
  color: white;
  background-color:#2563eb
}

.modal-body input,.modal-body select{height:42px;border:1px solid #cbd5e1;border-radius:10px;padding:0 10px}
.pdf-format-panel{width:min(460px,100%)}
.pdf-format-body{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding:16px}
.pdf-format-option{border:1px solid #cbd5e1;border-radius:14px;background:#fff;color:#0f172a;padding:16px;display:grid;gap:6px;text-align:right;cursor:pointer}
.pdf-format-option strong{font-size:18px}
.pdf-format-option span{font-size:12px;color:#475569}
.pdf-format-option.receipt{border-color:#0f172a;background:#f8fafc}
.pdf-format-option:disabled{opacity:.56;cursor:not-allowed}
@media (max-width:1400px){.summary-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media (max-width:1200px){.filters-card{grid-template-columns:repeat(2,minmax(0,1fr))}.search-field,.plate-field,.filters-actions{grid-column:span 2}.worker-summary-grid{grid-template-columns:repeat(2,1fr)}.filters-actions{justify-content:space-between}.export-studio-actions{grid-template-columns:repeat(2,minmax(0,1fr));justify-content:stretch}}
@media (max-width:760px){.reports-content{font-size:11px}.range-chip,.chip,.field,.field input,.field select,.modal-step{font-size:10px}.table-wrap{display:block;max-width:100%;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch}.table-wrap table{width:max-content;min-width:100%;table-layout:auto}.table-wrap th,.table-wrap td{white-space:nowrap;word-break:normal;overflow-wrap:normal}.primary-btn,.secondary-btn,.close-btn{font-size:10px;padding:7px 10px}.filters-card,.summary-grid,.worker-summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.plate-filter-row{grid-template-columns:42px 32px 56px 24px 42px;gap:6px}.search-field{grid-column:span 1}.plate-field{grid-column:span 2}.filters-card>.field:nth-child(4){grid-column:span 1}.worker-head,.action-row,.services-preview-cell,.filters-actions{flex-direction:column;align-items:stretch}.kpi-card p,.services-expanded-box strong,.payout-card p{font-size:10px}.kpi-card strong,.payout-card strong,.table-card h3{font-size:12px}.field input,.field select,.modal-body input,.modal-body select{height:34px}.range-bar,.tabs-bar{gap:5px}.modal-overlay{padding:10px}.modal-panel{max-height:calc(100vh - 20px);overflow:auto}.modal-body{grid-template-columns:repeat(2,minmax(0,1fr))}.report-plate{min-width:52px}.report-plate:deep(.plate-white-wrap){gap:3px;padding:2px 4px}.report-plate:deep(.plate-two),.report-plate:deep(.plate-three){height:14px;font-size:9px;padding-top:2px;padding-bottom:1px}.report-plate:deep(.plate-letter){min-width:8px;font-size:9px}.report-plate:deep(.plate-blue){min-width:18px;font-size:8px;padding-top:2px;padding-bottom:1px}.export-studio-actions{grid-template-columns:1fr}.export-action-btn,.clear-btn{width:100%}}
@media (max-width:480px){.reports-content{font-size:10px}.range-chip,.chip,.field,.field input,.field select{font-size:9px}.primary-btn,.secondary-btn,.close-btn{font-size:9px;padding:6px 9px}.kpi-card{padding:8px}.kpi-card p,.services-expanded-box strong,.services-expanded-box p,.payout-card p,.modal-step{font-size:9px}.kpi-card strong,.payout-card strong,.table-card h3{font-size:11px}.field input,.field select,.modal-body input,.modal-body select{height:32px}.plate-filter-shell,.table-card,.modal-body{padding:8px}.worker-head,.action-row{gap:6px}.filters-card,.summary-grid,.worker-summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.search-field{grid-column:span 1}.plate-field{grid-column:span 2}.filters-card>.field:nth-child(4){grid-column:span 1}.plate-filter-row{grid-template-columns:38px 26px 48px 22px 38px;gap:5px}}
</style>
