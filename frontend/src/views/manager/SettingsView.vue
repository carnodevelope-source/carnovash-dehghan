<template>
  <AppShell
    title="تنظیمات"
    subtitle="پیکربندی پرسنل، خدمات و موجودی"
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

        <template v-if="activeTab === 'workers'">
          <div class="head-row">
            <h2>مدیریت پرسنل</h2>
            <button class="primary-btn" @click="openWorkerModal()">افزودن پرسنل</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>نام</th>
                  <th>شماره</th>
                  <th>نوع پرداخت</th>
                  <th>مقدار پرداخت</th>
                  <th>درصد انعام</th>
                  <th>تاریخ بروزرسانی</th>
                  <th>وضعیت</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in filteredWorkers" :key="item.id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ item.full_name }}</td>
                  <td>{{ item.phone || '-' }}</td>
                  <td>{{ item.payment_type === 'fixed' ? 'تومانی' : item.payment_type === 'hourly' ? 'ساعتی' : 'درصدی' }}</td>
                  <td>{{ formatWorkerPayment(item) }}</td>
                  <td>{{ Number(item.tip_share_percent || 0).toLocaleString('fa-IR') }}٪</td>
                  <td>{{ formatDate(item.updated_at) }}</td>
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
                  <th>ردیف</th>
                  <th>نام</th>
                  <th>شرح</th>
                  <th>قیمت فروش</th>
                  <th>موجودی</th>
                  <th>تاریخ بروزرسانی</th>
                  <th>فعال</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in filteredProducts" :key="item.id" class="clickable-row" @click="openProductHistoryModal(item)">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ item.name }}</td>
                  <td>{{ item.description || '-' }}</td>
                  <td>{{ money(item.sale_price) }}</td>
                  <td>{{ Number(item.stock_qty || 0).toLocaleString('fa-IR') }}</td>
                  <td>{{ formatDate(item.updated_at) }}</td>
                  <td>{{ item.is_active ? 'بله' : 'خیر' }}</td>
                  <td>
                    <button class="table-btn" @click.stop="openProductModal(item)">ویرایش</button>
                    <button class="table-btn danger" @click.stop="deleteProduct(item)">حذف</button>
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
                  <th>ردیف</th>
                  <th>نام</th>
                  <th>شرح</th>
                  <th>قیمت</th>
                  <th>مدت</th>
                  <th>تاریخ بروزرسانی</th>
                  <th>فعال</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in filteredServices" :key="item.id" class="clickable-row" @click="openServiceHistoryModal(item)">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ item.name }}</td>
                  <td>{{ item.description || '-' }}</td>
                  <td>{{ money(item.base_price) }}</td>
                  <td>{{ item.estimated_duration_minutes }} دقیقه</td>
                  <td>{{ formatDate(item.updated_at) }}</td>
                  <td>{{ item.is_active ? 'بله' : 'خیر' }}</td>
                  <td>
                    <button class="table-btn" @click.stop="openServiceModal(item)">ویرایش</button>
                    <button class="table-btn danger" @click.stop="deleteService(item)">حذف</button>
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
            <section class="general-settings-card">
              <div class="general-settings-head">
                <div>
                  <strong>تنظیمات تخفیف مشتری</strong>
                  <p class="helper-text">مبنای تخفیف ستاره‌ای مشتری را از اینجا تنظیم کنید.</p>
                </div>
              </div>
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
            </section>
            <section class="general-settings-card payment-settings-card">
              <div class="general-settings-head">
                <div>
                  <strong>ویژگی‌های شیوه پرداخت</strong>
                  <p class="helper-text">اطلاعات بانکی، کارت‌خوان و توضیحات پرداخت کارواش را اینجا ثبت کنید.</p>
                </div>
              </div>
              <div class="payment-settings-grid">
                <label class="general-setting-label">
                  <span>بانک اصلی</span>
                  <input v-model.trim="generalSettings.preferred_bank_name" type="text" placeholder="مثلا بانک ملت" />
                </label>
                <label class="general-setting-label">
                  <span>نام صاحب حساب</span>
                  <input v-model.trim="generalSettings.bank_account_holder" type="text" placeholder="مثلا علی رضایی" />
                </label>
                <label class="general-setting-label">
                  <span>شماره کارت</span>
                  <input v-model.trim="generalSettings.bank_card_number" type="text" inputmode="numeric" placeholder="مثلا 6037991234567890" />
                </label>
                <label class="general-setting-label">
                  <span>شماره شبا</span>
                  <input v-model.trim="generalSettings.bank_account_iban" type="text" placeholder="IRxxxxxxxxxxxxxxxxxxxxxxxx" />
                </label>
                <label class="general-setting-label">
                  <span>نام دستگاه پوز</span>
                  <input v-model.trim="generalSettings.pos_device_name" type="text" placeholder="مثلا پوز صندوق ۱" />
                </label>
                <label class="general-setting-label">
                  <span>کد یا ترمینال پوز</span>
                  <input v-model.trim="generalSettings.pos_terminal_id" type="text" placeholder="مثلا TID-2048" />
                </label>
                <label class="general-setting-label full-width">
                  <span>توضیحات شیوه پرداخت</span>
                  <textarea v-model.trim="generalSettings.payment_methods_note" rows="4" placeholder="مثلا برای مبالغ بالا کارت به کارت فقط به همین حساب انجام شود یا توضیحات مربوط به پوز و تسویه را بنویسید." />
                </label>
              </div>
            </section>
            <section class="general-settings-card printer-settings-card">
              <div class="general-settings-head">
                <div>
                  <strong>تنظیمات فیش پرینتر</strong>
                  <p class="helper-text">مشخصات چاپ فیش و نحوه خروجی گرفتن از صندوق را از این بخش تنظیم کنید.</p>
                </div>
              </div>
              <div class="printer-settings-grid">
                <label class="row-check printer-toggle">
                  <input v-model="generalSettings.receipt_printer_enabled" type="checkbox" />
                  <span>فیش پرینتر فعال باشد</span>
                </label>
                <label class="general-setting-label">
                  <span>نام پرینتر</span>
                  <input v-model.trim="generalSettings.receipt_printer_name" type="text" placeholder="مثلا Epson TM-T20III" />
                </label>
                <label class="general-setting-label">
                  <span>عرض کاغذ</span>
                  <select v-model="generalSettings.receipt_printer_paper_width">
                    <option value="58mm">58mm</option>
                    <option value="80mm">80mm</option>
                    <option value="a4">A4</option>
                  </select>
                </label>
                <label class="general-setting-label">
                  <span>تعداد نسخه چاپ</span>
                  <input v-model.number="generalSettings.receipt_print_copies" type="number" min="1" max="5" />
                </label>
                <div class="printer-checks">
                  <label class="row-check"><input v-model="generalSettings.receipt_auto_print" type="checkbox" /><span>چاپ خودکار بعد از ترخیص</span></label>
                  <label class="row-check"><input v-model="generalSettings.receipt_show_logo" type="checkbox" /><span>نمایش لوگو در فیش</span></label>
                  <label class="row-check"><input v-model="generalSettings.receipt_show_qr" type="checkbox" /><span>نمایش QR در فیش</span></label>
                </div>
                <label class="general-setting-label full-width">
                  <span>متن پایین فیش</span>
                  <textarea v-model.trim="generalSettings.receipt_footer_note" rows="4" placeholder="مثلا: با تشکر از اعتماد شما - ساعات پاسخگویی ۸ تا ۲۲" />
                </label>
              </div>
            </section>
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
          <template v-if="modal.type === 'workers'">
            <label><span>نام کامل</span><input v-model="forms.worker.full_name" required /></label>
            <label><span>شماره موبایل</span><input v-model="forms.worker.phone" required /></label>
            <label>
              <span>نوع پرداخت پرسنل</span>
              <select v-model="forms.worker.payment_type">
                <option value="percent">درصدی</option>
                <option value="fixed">تومانی</option>
                <option value="hourly">ساعتی</option>
              </select>
            </label>
            <label>
              <span>{{ forms.worker.payment_type === 'percent' ? 'درصد دریافتی' : forms.worker.payment_type === 'hourly' ? 'مبلغ ساعتی (هزار تومان)' : 'مبلغ دریافتی (هزار تومان)' }}</span>
              <input type="number" :min="0" :max="forms.worker.payment_type === 'percent' ? 100 : null" v-model.number="forms.worker.payment_value" required />
            </label>
            <label><span>درصد انعام</span><input type="number" min="0" max="100" v-model.number="forms.worker.tip_share_percent" required /></label>
            <label class="row-check"><input type="checkbox" v-model="forms.worker.is_available" /><span>فعال</span></label>
            <section class="full entrusted-card" :class="{ active: forms.worker.has_entrusted_item }">
              <div class="entrusted-head">
                <div>
                  <strong>امانات پرسنل</strong>
                  <small>اگر چیزی به این پرسنل امانت داده‌اید، این بخش را تکمیل کنید.</small>
                </div>
                <label class="row-check entrusted-toggle">
                  <input type="checkbox" v-model="forms.worker.has_entrusted_item" />
                  <span>ثبت امانت</span>
                </label>
              </div>
              <div v-if="forms.worker.has_entrusted_item" class="entrusted-grid">
                <label class="full">
                  <span>شرح</span>
                  <textarea v-model="forms.worker.entrusted_item_description" rows="3" placeholder="مثلا: کاردک، دستگاه، لباس کار یا هر مورد امانی" />
                </label>
                <label>
                  <span>تعداد</span>
                  <input type="number" min="0" step="0.01" v-model.number="forms.worker.entrusted_item_quantity" />
                </label>
                <label>
                  <span>قیمت (هزار تومان)</span>
                  <input type="number" min="0" v-model.number="forms.worker.entrusted_item_price" />
                </label>
              </div>
            </section>
          </template>

          <template v-else-if="modal.type === 'products'">
            <label><span>نام</span><input v-model="forms.product.name" required /></label>
            <label class="full"><span>شرح</span><textarea v-model="forms.product.description" rows="3" /></label>
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
            <label class="full"><span>شرح</span><textarea v-model="forms.service.description" rows="3" /></label>
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

    <div v-if="productHistoryModal.open" class="modal-overlay" @click.self="closeProductHistoryModal">
      <section class="modal-panel history-panel">
        <header class="modal-head">
          <div>
            <h3>تاریخچه خرید {{ productHistoryModal.product?.name || '' }}</h3>
            <small class="modal-subtitle">همه خریدهای ثبت‌شده برای این محصول</small>
          </div>
          <button class="close-btn" @click="closeProductHistoryModal">✕</button>
        </header>
        <div v-if="productHistoryModal.loading" class="history-loading">در حال بارگذاری...</div>
        <div v-else class="history-body">
          <div class="history-summary" v-if="productHistoryModal.product">
            <article><span>قیمت فروش فعلی</span><strong>{{ money(productHistoryModal.product.sale_price) }}</strong></article>
            <article><span>قیمت خرید فعلی</span><strong>{{ money(productHistoryModal.product.cost_price) }}</strong></article>
            <article><span>تعداد خریدها</span><strong>{{ Number(productHistoryModal.history.length || 0).toLocaleString('fa-IR') }}</strong></article>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>تاریخ</th>
                  <th>تعداد</th>
                  <th>قیمت خرید</th>
                  <th>قیمت فروش</th>
                  <th>ثبت‌کننده</th>
                  <th>توضیح</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in productHistoryModal.history" :key="row.id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ dateTime(row.moved_at) }}</td>
                  <td>{{ Number(row.quantity || 0).toLocaleString('fa-IR') }}</td>
                  <td>{{ money(row.unit_cost) }}</td>
                  <td>{{ money(row.sale_price_snapshot) }}</td>
                  <td>{{ row.created_by_name || '-' }}</td>
                  <td>{{ row.note || '-' }}</td>
                </tr>
                <tr v-if="!productHistoryModal.history.length">
                  <td colspan="7">برای این محصول هنوز خریدی ثبت نشده است.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <div v-if="serviceHistoryModal.open" class="modal-overlay" @click.self="closeServiceHistoryModal">
      <section class="modal-panel history-panel">
        <header class="modal-head">
          <div>
            <h3>۵ تغییر آخر {{ serviceHistoryModal.service?.name || '' }}</h3>
            <small class="modal-subtitle">آخرین تغییرات قیمت، مدت و وضعیت این خدمت</small>
          </div>
          <button class="close-btn" @click="closeServiceHistoryModal">✕</button>
        </header>
        <div v-if="serviceHistoryModal.loading" class="history-loading">در حال بارگذاری...</div>
        <div v-else class="history-body">
          <div class="history-summary" v-if="serviceHistoryModal.service">
            <article><span>قیمت فعلی</span><strong>{{ money(serviceHistoryModal.service.base_price) }}</strong></article>
            <article><span>مدت فعلی</span><strong>{{ serviceHistoryModal.service.estimated_duration_minutes }} دقیقه</strong></article>
            <article><span>تعداد لاگ‌ها</span><strong>{{ Number(serviceHistoryModal.history.length || 0).toLocaleString('fa-IR') }}</strong></article>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>تاریخ</th>
                  <th>نوع تغییر</th>
                  <th>قیمت ثبت‌شده</th>
                  <th>مدت ثبت‌شده</th>
                  <th>وضعیت</th>
                  <th>ثبت‌کننده</th>
                  <th>جزئیات تغییر</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in serviceHistoryModal.history" :key="row.id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ dateTime(row.created_at) }}</td>
                  <td>{{ serviceActionLabel(row.action_type) }}</td>
                  <td>{{ money(row.base_price_snapshot) }}</td>
                  <td>{{ row.estimated_duration_snapshot }} دقیقه</td>
                  <td>{{ row.is_active_snapshot ? 'فعال' : 'غیرفعال' }}</td>
                  <td>{{ row.changed_by_name || '-' }}</td>
                  <td>{{ serviceChangeSummaryText(row.change_summary) }}</td>
                </tr>
                <tr v-if="!serviceHistoryModal.history.length">
                  <td colspan="8">برای این خدمت هنوز تغییری ثبت نشده است.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
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
import { formatJalaliDate } from '../../utils/date'
import { formatThousandsToman, fromThousandsTomanInput } from '../../utils/money'

const authStore = useAuthStore()
const search = ref('')
const activeTab = ref('workers')
const errorMessage = ref('')

const tabs = [
  { key: 'workers', label: 'پرسنل' },
  { key: 'products', label: 'محصولات' },
  { key: 'services', label: 'خدمات' },
  { key: 'general', label: 'تنظیمات عمومی' }
]

const workers = ref([])
const products = ref([])
const services = ref([])
const inventoryItems = ref([])
const generalSettings = reactive({
  discount_percent_per_half_star: 0,
  preferred_bank_name: '',
  bank_account_holder: '',
  bank_card_number: '',
  bank_account_iban: '',
  pos_device_name: '',
  pos_terminal_id: '',
  payment_methods_note: '',
  receipt_printer_enabled: false,
  receipt_printer_name: '',
  receipt_printer_paper_width: '80mm',
  receipt_print_copies: 1,
  receipt_auto_print: false,
  receipt_show_logo: false,
  receipt_show_qr: false,
  receipt_footer_note: ''
})
const generalSettingsSaving = ref(false)

const modal = reactive({ open: false, type: '', id: null, title: '' })
const productHistoryModal = reactive({ open: false, loading: false, product: null, history: [] })
const serviceHistoryModal = reactive({ open: false, loading: false, service: null, history: [] })
const forms = reactive({
  worker: {
    full_name: '',
    phone: '',
    payment_type: 'percent',
    payment_value: 0,
    tip_share_percent: 0,
    is_available: true,
    has_entrusted_item: false,
    entrusted_item_description: '',
    entrusted_item_quantity: 0,
    entrusted_item_price: 0
  },
  product: { name: '', description: '', sale_price: 0, cost_price: 0, unit: 'unit', min_stock: 0, is_active: true },
  purchase: { product_id: 0, quantity: 1, unit_cost: 0, sale_price: 0, note: '' },
  service: { name: '', description: '', base_price: 0, estimated_duration_minutes: 30, is_active: true }
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

const money = (v) => formatThousandsToman(v)
const toThousandsDisplay = (value) => Math.round(Number(value || 0) / 1000)
const fromThousandsInput = (value) => fromThousandsTomanInput(value)

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
  if (['fixed', 'hourly'].includes(worker?.payment_type || 'percent')) return money(worker?.payment_value || 0)
  return `${Number(worker?.payment_value || 0).toLocaleString('fa-IR')}٪`
}
const serviceActionLabel = (value) => ({
  created: 'ایجاد',
  updated: 'ویرایش',
  deactivated: 'غیرفعال‌سازی',
  deleted: 'حذف'
}[value] || 'ویرایش')
const serviceChangeSummaryText = (summary) => {
  const entries = Object.values(summary || {})
  if (!entries.length) return 'بدون جزئیات'
  return entries.map((item) => `${item.label}: ${item.from ?? '-'} ← ${item.to ?? '-'}`).join(' | ')
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
const filteredProducts = computed(() => productsWithStock.value.filter((i) => (`${i.name} ${i.description || ''} ${i.unit || ''}`).includes(search.value)))
const filteredServices = computed(() => services.value.filter((i) => (`${i.name} ${i.description || ''}`).includes(search.value)))
const fullStarDiscountLabel = computed(() => `${Number((Number(generalSettings.discount_percent_per_half_star || 0) * 2).toFixed(2)).toLocaleString('fa-IR')}٪`)

watch(() => forms.purchase.product_id, (newProductId) => {
  const selected = products.value.find((item) => Number(item.id) === Number(newProductId))
  if (!selected) return
  forms.purchase.unit_cost = toThousandsDisplay(selected.cost_price || 0)
  forms.purchase.sale_price = toThousandsDisplay(selected.sale_price || 0)
})

const loadAll = async () => {
  try {
    const [w, p, s, inv] = await Promise.all([
      api.get('/workers/'),
      api.get('/products/'),
      api.get('/services/'),
      api.get('/inventory/')
    ])
    workers.value = Array.isArray(w.data) ? w.data : []
    products.value = Array.isArray(p.data) ? p.data : []
    services.value = Array.isArray(s.data) ? s.data : []
    inventoryItems.value = Array.isArray(inv.data) ? inv.data : []
    try {
      const gs = await api.get('/services/general-settings/')
      generalSettings.discount_percent_per_half_star = Number(gs.data?.discount_percent_per_half_star || 0)
      generalSettings.preferred_bank_name = gs.data?.preferred_bank_name || ''
      generalSettings.bank_account_holder = gs.data?.bank_account_holder || ''
      generalSettings.bank_card_number = gs.data?.bank_card_number || ''
      generalSettings.bank_account_iban = gs.data?.bank_account_iban || ''
      generalSettings.pos_device_name = gs.data?.pos_device_name || ''
      generalSettings.pos_terminal_id = gs.data?.pos_terminal_id || ''
      generalSettings.payment_methods_note = gs.data?.payment_methods_note || ''
      generalSettings.receipt_printer_enabled = Boolean(gs.data?.receipt_printer_enabled)
      generalSettings.receipt_printer_name = gs.data?.receipt_printer_name || ''
      generalSettings.receipt_printer_paper_width = gs.data?.receipt_printer_paper_width || '80mm'
      generalSettings.receipt_print_copies = Number(gs.data?.receipt_print_copies || 1)
      generalSettings.receipt_auto_print = Boolean(gs.data?.receipt_auto_print)
      generalSettings.receipt_show_logo = Boolean(gs.data?.receipt_show_logo)
      generalSettings.receipt_show_qr = Boolean(gs.data?.receipt_show_qr)
      generalSettings.receipt_footer_note = gs.data?.receipt_footer_note || ''
    } catch {
      generalSettings.discount_percent_per_half_star = 0
      generalSettings.preferred_bank_name = ''
      generalSettings.bank_account_holder = ''
      generalSettings.bank_card_number = ''
      generalSettings.bank_account_iban = ''
      generalSettings.pos_device_name = ''
      generalSettings.pos_terminal_id = ''
      generalSettings.payment_methods_note = ''
      generalSettings.receipt_printer_enabled = false
      generalSettings.receipt_printer_name = ''
      generalSettings.receipt_printer_paper_width = '80mm'
      generalSettings.receipt_print_copies = 1
      generalSettings.receipt_auto_print = false
      generalSettings.receipt_show_logo = false
      generalSettings.receipt_show_qr = false
      generalSettings.receipt_footer_note = ''
    }
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || 'خطا در بارگذاری داده‌ها'
  }
}

const saveGeneralSettings = async () => {
  generalSettingsSaving.value = true
  try {
    const payload = {
      discount_percent_per_half_star: Number(generalSettings.discount_percent_per_half_star || 0),
      preferred_bank_name: generalSettings.preferred_bank_name || '',
      bank_account_holder: generalSettings.bank_account_holder || '',
      bank_card_number: generalSettings.bank_card_number || '',
      bank_account_iban: generalSettings.bank_account_iban || '',
      pos_device_name: generalSettings.pos_device_name || '',
      pos_terminal_id: generalSettings.pos_terminal_id || '',
      payment_methods_note: generalSettings.payment_methods_note || '',
      receipt_printer_enabled: Boolean(generalSettings.receipt_printer_enabled),
      receipt_printer_name: generalSettings.receipt_printer_name || '',
      receipt_printer_paper_width: generalSettings.receipt_printer_paper_width || '80mm',
      receipt_print_copies: Number(generalSettings.receipt_print_copies || 1),
      receipt_auto_print: Boolean(generalSettings.receipt_auto_print),
      receipt_show_logo: Boolean(generalSettings.receipt_show_logo),
      receipt_show_qr: Boolean(generalSettings.receipt_show_qr),
      receipt_footer_note: generalSettings.receipt_footer_note || ''
    }
    const response = await api.patch('/services/general-settings/', payload)
    generalSettings.discount_percent_per_half_star = Number(response.data?.discount_percent_per_half_star || 0)
    generalSettings.preferred_bank_name = response.data?.preferred_bank_name || ''
    generalSettings.bank_account_holder = response.data?.bank_account_holder || ''
    generalSettings.bank_card_number = response.data?.bank_card_number || ''
    generalSettings.bank_account_iban = response.data?.bank_account_iban || ''
    generalSettings.pos_device_name = response.data?.pos_device_name || ''
    generalSettings.pos_terminal_id = response.data?.pos_terminal_id || ''
    generalSettings.payment_methods_note = response.data?.payment_methods_note || ''
    generalSettings.receipt_printer_enabled = Boolean(response.data?.receipt_printer_enabled)
    generalSettings.receipt_printer_name = response.data?.receipt_printer_name || ''
    generalSettings.receipt_printer_paper_width = response.data?.receipt_printer_paper_width || '80mm'
    generalSettings.receipt_print_copies = Number(response.data?.receipt_print_copies || 1)
    generalSettings.receipt_auto_print = Boolean(response.data?.receipt_auto_print)
    generalSettings.receipt_show_logo = Boolean(response.data?.receipt_show_logo)
    generalSettings.receipt_show_qr = Boolean(response.data?.receipt_show_qr)
    generalSettings.receipt_footer_note = response.data?.receipt_footer_note || ''
    t('تنظیمات عمومی ذخیره شد')
  } catch (e) {
    t(apiErrorText(e), 'error')
  } finally {
    generalSettingsSaving.value = false
  }
}

const openWorkerModal = (item = null) => {
  modal.open = true
  modal.type = 'workers'
  modal.id = item?.id || null
  modal.title = modal.id ? 'ویرایش پرسنل' : 'افزودن پرسنل'
  forms.worker.full_name = item?.full_name || ''
  forms.worker.phone = item?.phone || ''
  forms.worker.payment_type = item?.payment_type || 'percent'
  forms.worker.payment_value = forms.worker.payment_type === 'fixed'
    ? toThousandsDisplay(item?.payment_value || 0)
    : Number(item?.payment_value || 0)
  forms.worker.tip_share_percent = Number(item?.tip_share_percent || 0)
  forms.worker.is_available = item?.is_available ?? true
  forms.worker.has_entrusted_item = Boolean(item?.has_entrusted_item)
  forms.worker.entrusted_item_description = item?.entrusted_item_description || ''
  forms.worker.entrusted_item_quantity = Number(item?.entrusted_item_quantity || 0)
  forms.worker.entrusted_item_price = toThousandsDisplay(item?.entrusted_item_price || 0)
}

const openProductModal = (item = null) => {
  modal.open = true
  modal.type = 'products'
  modal.id = item?.id || null
  modal.title = modal.id ? 'ویرایش محصول' : 'افزودن محصول'
  Object.assign(forms.product, {
    name: item?.name || '',
    description: item?.description || '',
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

const openProductHistoryModal = async (item) => {
  if (!item?.id) return
  productHistoryModal.open = true
  productHistoryModal.loading = true
  productHistoryModal.product = item
  productHistoryModal.history = []
  try {
    const { data } = await api.get(`/inventory/product-history/${item.id}/`)
    productHistoryModal.product = data?.product || item
    productHistoryModal.history = Array.isArray(data?.history) ? data.history : []
  } catch (e) {
    t(apiErrorText(e), 'error')
    closeProductHistoryModal()
  } finally {
    productHistoryModal.loading = false
  }
}

const closeProductHistoryModal = () => {
  productHistoryModal.open = false
  productHistoryModal.loading = false
  productHistoryModal.product = null
  productHistoryModal.history = []
}

const openServiceHistoryModal = async (item) => {
  if (!item?.id) return
  serviceHistoryModal.open = true
  serviceHistoryModal.loading = true
  serviceHistoryModal.service = item
  serviceHistoryModal.history = []
  try {
    const { data } = await api.get(`/services/${item.id}/history/`)
    serviceHistoryModal.service = data?.service || item
    serviceHistoryModal.history = Array.isArray(data?.history) ? data.history : []
  } catch (e) {
    t(apiErrorText(e), 'error')
    closeServiceHistoryModal()
  } finally {
    serviceHistoryModal.loading = false
  }
}

const closeServiceHistoryModal = () => {
  serviceHistoryModal.open = false
  serviceHistoryModal.loading = false
  serviceHistoryModal.service = null
  serviceHistoryModal.history = []
}

const openServiceModal = (item = null) => {
  modal.open = true
  modal.type = 'services'
  modal.id = item?.id || null
  modal.title = modal.id ? 'ویرایش خدمت' : 'افزودن خدمت'
  Object.assign(forms.service, {
    name: item?.name || '',
    description: item?.description || '',
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

const formatDate = (value) => formatJalaliDate(value)
const dateTime = (value) => formatJalaliDate(value)

const submitModal = async () => {
  try {
    if (modal.type === 'workers') {
      const paymentValueNormalized = forms.worker.payment_type === 'fixed'
        ? fromThousandsInput(forms.worker.payment_value)
        : Number(forms.worker.payment_value || 0)
      const workerPayload = {
        full_name: forms.worker.full_name,
        phone: forms.worker.phone,
        is_available: forms.worker.is_available,
        payment_type: forms.worker.payment_type,
        payment_value: Number.isFinite(Number(paymentValueNormalized)) ? Number(paymentValueNormalized) : 0,
        tip_share_percent: Number(forms.worker.tip_share_percent || 0),
        has_entrusted_item: Boolean(forms.worker.has_entrusted_item),
        entrusted_item_description: forms.worker.has_entrusted_item ? (forms.worker.entrusted_item_description || '').trim() : '',
        entrusted_item_quantity: forms.worker.has_entrusted_item ? Number(forms.worker.entrusted_item_quantity || 0) : 0,
        entrusted_item_price: forms.worker.has_entrusted_item ? fromThousandsInput(forms.worker.entrusted_item_price || 0) : 0
      }
      if (modal.id) await api.patch(`/workers/${modal.id}/`, workerPayload)
      else await api.post('/workers/', workerPayload)
      t('پرسنل ذخیره شد')
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
.clickable-row { cursor: pointer; }
.clickable-row:hover td { background: #f8fbff; }
.modal-overlay { position: fixed; inset: 0; background: rgba(15,23,42,.45); display: flex; align-items: center; justify-content: center; padding: 18px; z-index: 99; }
.modal-panel { width: min(980px,100%); background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; }
.history-panel { width: min(1100px,100%); }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid #e2e8f0; }
.modal-subtitle { display: block; margin-top: 4px; color: #64748b; font-size: 12px; }
.close-btn { border: 0; background: #f1f5f9; border-radius: 8px; width: 30px; height: 30px; cursor: pointer; }
.modal-form { padding: 14px; display: grid; gap: 10px; grid-template-columns: repeat(3, minmax(0, 1fr)); align-items: end; }
.modal-form label { display: grid; gap: 5px; }
.modal-form input, .modal-form select { height: 42px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 0 10px; background: #fff; }
.modal-form textarea { border: 1px solid #cbd5e1; border-radius: 10px; padding: 10px; background: #fff; font: inherit; resize: vertical; }
.row-check { display: flex !important; align-items: center; gap: 8px; }
.full { grid-column: 1 / -1; }
.entrusted-card {
  grid-column: 1 / -1;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid #dbe7f5;
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
  display: grid;
  gap: 12px;
}
.entrusted-card.active {
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.12);
  border-color: #bfd7ff;
}
.entrusted-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.entrusted-head strong { color: #0f172a; font-size: 15px; }
.entrusted-head small { display: block; margin-top: 4px; color: #64748b; }
.entrusted-toggle { white-space: nowrap; }
.entrusted-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; grid-column: 1 / -1; }
.history-loading, .history-body { padding: 14px; }
.history-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }
.history-summary article { border: 1px solid #e2e8f0; border-radius: 12px; padding: 10px; background: #f8fbff; display: grid; gap: 6px; }
.history-summary span { color: #64748b; font-size: 12px; }
.history-summary strong { color: #0f172a; font-size: 14px; }
.general-settings-form { display: grid; gap: 14px; }
.general-settings-card {
  border: 1px solid #dbe7f5;
  border-radius: 18px;
  padding: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
  display: grid;
  gap: 10px;
}
.general-settings-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.general-settings-head strong { color: #0f172a; font-size: 15px; }
.general-setting-label { display: grid; gap: 6px; }
.general-setting-label input,
.general-setting-label textarea {
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 10px 12px;
  background: #fff;
  font: inherit;
}
.general-setting-label input { height: 44px; }
.payment-settings-card {
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
}
.payment-settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.printer-settings-card {
  background: linear-gradient(180deg, #fffdfa 0%, #fff7ed 100%);
}
.printer-settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.printer-settings-grid select {
  height: 44px;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 0 12px;
  background: #fff;
  font: inherit;
}
.printer-toggle {
  grid-column: 1 / -1;
  padding: 12px 14px;
  border: 1px dashed #fdba74;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
}
.printer-checks {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.full-width { grid-column: 1 / -1; }
.helper-text { margin: 0; color: #475569; font-size: 13px; }
.error-box { margin-bottom: 10px; padding: 10px; background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; border-radius: 10px; }
.toast { position: fixed; left: 20px; bottom: 20px; padding: 10px 14px; border-radius: 10px; color: #fff; z-index: 120; }
.toast.success { background: #16a34a; }
.toast.error { background: #dc2626; }
@media (max-width: 960px) {
  .modal-form, .history-summary { grid-template-columns: 1fr; }
  .entrusted-head, .entrusted-grid { grid-template-columns: 1fr; display: grid; }
  .payment-settings-grid, .printer-settings-grid, .printer-checks { grid-template-columns: 1fr; }
}
</style>




