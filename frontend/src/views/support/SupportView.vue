<template>
  <AppShell
    title="پشتیبانی"
    subtitle="مرکز تیکت، پیگیری گفتگوها و ارتباط ساختاریافته با تیم پشتیبانی"
    :show-search="true"
    search-placeholder="جستجو بر اساس شماره تیکت، عنوان، دسته‌بندی یا متن گفتگو..."
    :search-query="searchQuery"
    @update:search-query="searchQuery = $event"
  >
    <template #header-actions>
      <button type="button" class="ghost-btn" @click="focusSearch">جستجو</button>
      <button type="button" class="primary-btn" @click="openCreateTicketModal">ثبت تیکت جدید</button>
    </template>

    <div class="support-page">
      <section class="support-sla-banner">
        تیکت‌ها در تایم اداری حداکثر نیم ساعت و در تایم غیر اداری حداکثر ۲۴ ساعت پاسخ داده خواهند شد.
      </section>

      <section class="stats-grid">
        <article
          v-for="item in statusTrack"
          :key="item.key"
          class="stat-card"
          :class="[statusClass(item.key), { active: activeStatusTab === item.key }]"
          @click="activeStatusTab = item.key"
        >
          <div class="stat-icon">{{ statusGlyph(item.key) }}</div>
          <strong>{{ toFa(item.count) }}</strong>
          <span>{{ item.label }}</span>
          <small>{{ item.description }}</small>
        </article>
      </section>

      <section class="workspace-grid">
        <aside class="surface-card inbox-card">
          <header class="panel-head">
            <div>
              <p class="panel-kicker">Ticket Inbox</p>
              <h3>لیست تیکت‌های من</h3>
              <span>{{ toFa(filteredTickets.length) }} مورد در وضعیت {{ activeStatusLabel }}</span>
            </div>
            <button type="button" class="mini-btn" @click="toggleStatusFilter">بعدی</button>
          </header>

          <div class="chip-row">
            <button
              v-for="item in categoryTabs"
              :key="item.key"
              type="button"
              class="chip-btn"
              :class="{ active: activeCategoryTab === item.key }"
              @click="activeCategoryTab = item.key"
            >
              {{ item.label }}
            </button>
          </div>

          <div class="inbox-summary-grid">
            <article class="summary-tile">
              <small>منتظر پاسخ من</small>
              <strong>{{ toFa(waitingForUserCount) }}</strong>
            </article>
            <article class="summary-tile">
              <small>در حال بررسی</small>
              <strong>{{ toFa(inProgressCount) }}</strong>
            </article>
          </div>

          <div v-if="filteredTickets.length" class="ticket-list">
            <article
              v-for="ticket in filteredTickets"
              :key="ticket.id"
              class="ticket-row"
              :class="{ selected: detailState.ticket?.id === ticket.id }"
              @click="openTicketDetail(ticket.id)"
            >
              <div class="ticket-row-top">
                <strong>{{ ticket.subject }}</strong>
                <span class="status-pill" :class="statusClass(ticket.status)">{{ clientStatusLabel(ticket) }}</span>
              </div>
              <p>{{ ticket.last_message_preview || ticket.message }}</p>
              <div class="ticket-row-tags">
                <span class="meta-pill">{{ categoryLabel(ticket.category) }}</span>
                <span class="meta-pill">{{ priorityLabel(ticket.priority) }}</span>
                <span class="meta-pill mono">#{{ ticket.id }}</span>
              </div>
              <div class="ticket-row-meta">
                <span>{{ formatDateTime(ticket.updated_at) }}</span>
                <span>{{ ticketLastResponder(ticket) }}</span>
                <span>{{ toFa(ticket.messages_count || 0) }} پیام</span>
              </div>
            </article>
          </div>

          <div v-else class="empty-state">
            <div class="empty-icon" aria-hidden="true">
              <svg viewBox="0 0 64 64" fill="none">
                <circle cx="32" cy="32" r="27" stroke="currentColor" stroke-width="2.4" />
                <path d="m22 33 8 8 14-18" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </div>
            <h3>تیکتی در این نما نیست</h3>
            <p>فیلتر وضعیت یا دسته‌بندی را تغییر دهید، یا یک تیکت تازه ثبت کنید.</p>
            <button type="button" class="primary-btn" @click="openCreateTicketModal">ثبت تیکت</button>
          </div>
        </aside>

        <section class="surface-card conversation-card">
          <div v-if="detailState.loading" class="loading-state">در حال بارگذاری گفتگو...</div>

          <template v-else-if="detailState.ticket">
            <header class="conversation-head">
              <div class="conversation-copy">
                <span class="panel-kicker">Conversation</span>
                <div class="conversation-title">
                  <h3>{{ detailState.ticket.subject }}</h3>
                  <span class="status-pill" :class="statusClass(detailState.ticket.status)">
                    {{ clientStatusLabel(detailState.ticket) }}
                  </span>
                </div>
                <p>{{ detailState.ticket.message }}</p>
              </div>

              <div class="conversation-tags">
                <span class="meta-pill">{{ categoryLabel(detailState.ticket.category) }}</span>
                <span class="meta-pill">{{ priorityLabel(detailState.ticket.priority) }}</span>
                <span class="meta-pill mono">#{{ detailState.ticket.id }}</span>
              </div>
            </header>

            <section class="metric-strip">
              <article class="metric-card">
                <small>آخرین پاسخ</small>
                <strong>{{ ticketLastResponder(detailState.ticket) }}</strong>
              </article>
              <article class="metric-card">
                <small>آخرین بروزرسانی</small>
                <strong>{{ formatDateTime(detailState.ticket.updated_at) }}</strong>
              </article>
              <article class="metric-card">
                <small>پاسخ‌اول</small>
                <strong>{{ firstResponseLabel(detailState.ticket) }}</strong>
              </article>
              <article class="metric-card">
                <small>رضایت</small>
                <strong>{{ satisfactionLabel(detailState.ticket.customer_satisfaction) }}</strong>
              </article>
            </section>

            <section v-if="detailState.ticket.attachments?.length" class="ticket-attachments-shell">
              <div class="reply-head">
                <strong>فایل‌های پیوست</strong>
                <small>{{ toFa(detailState.ticket.attachments.length) }} فایل</small>
              </div>
              <div class="ticket-attachments-list">
                <a
                  v-for="attachment in detailState.ticket.attachments"
                  :key="attachment.id"
                  class="ticket-attachment-item"
                  :href="attachment.file_url"
                  target="_blank"
                  rel="noreferrer"
                >
                  <strong>{{ attachment.original_name || 'فایل پیوست' }}</strong>
                  <span>مشاهده فایل</span>
                </a>
              </div>
            </section>

            <section ref="messageThreadRef" class="message-thread">
              <article
                v-for="message in detailState.ticket.messages || []"
                :key="message.id"
                class="message-row"
                :class="messageAlignmentClass(message)"
              >
                <div class="message-bubble" :class="messageAlignmentClass(message)">
                  <div class="message-meta">
                    <span class="sender-tag" :class="messageAlignmentClass(message)">
                      {{ messageRoleLabel(message) }}
                    </span>
                    <small>{{ formatDateTime(message.created_at) }}</small>
                  </div>
                  <p>{{ message.body }}</p>
                </div>
              </article>
            </section>

            <section class="reply-shell">
              <div class="reply-head">
                <strong>ارسال پاسخ</strong>
                <small v-if="detailState.ticket.status === 'closed'">این تیکت بسته شده و فقط برای مشاهده است.</small>
                <small v-else>پاسخ کوتاه، شفاف و مستند بنویسید. با `Ctrl + Enter` هم ارسال می‌شود.</small>
              </div>

              <div v-if="detailState.ticket.status !== 'closed'" class="reply-form">
                <textarea
                  v-model.trim="detailState.replyBody"
                  :disabled="detailState.sendingReply"
                  rows="4"
                  placeholder="پاسخ تکمیلی خود را بنویسید..."
                  @keydown.ctrl.enter.prevent="submitReply"
                />
                <div class="reply-actions">
                  <span class="hint">{{ toFa(detailState.replyBody.length) }} کاراکتر</span>
                  <button
                    type="button"
                    class="primary-btn"
                    :disabled="detailState.sendingReply || !detailState.replyBody"
                    @click="submitReply"
                  >
                    {{ detailState.sendingReply ? 'در حال ارسال...' : 'ارسال پیام' }}
                  </button>
                </div>
              </div>

              <div v-else class="closed-note">
                <span class="status-pill closed">تیکت بسته شده</span>
                <p>اگر هنوز مشکل باقی است، یک تیکت جدید با ارجاع به شماره همین تیکت ثبت کنید.</p>
              </div>
            </section>

            <section v-if="detailState.ticket.status === 'closed'" class="feedback-shell">
              <div class="reply-head">
                <strong>نظر شما درباره این تیکت</strong>
                <small v-if="canRateTicket(detailState.ticket)">تجربه رسیدگی را ثبت کنید تا کیفیت پشتیبانی بهتر شود.</small>
                <small v-else>نظر شما قبلا برای این تیکت ثبت شده است.</small>
              </div>

              <template v-if="canRateTicket(detailState.ticket)">
                <div class="rating-stars">
                  <button
                    v-for="score in 5"
                    :key="score"
                    type="button"
                    class="rating-star-btn"
                    :class="{ active: detailState.feedbackScore >= score }"
                    @click="detailState.feedbackScore = score"
                  >
                    ★
                  </button>
                </div>
                <textarea
                  v-model.trim="detailState.feedbackText"
                  rows="3"
                  placeholder="اگر خواستید، خیلی کوتاه تجربه خود از رسیدگی این تیکت را بنویسید..."
                />
                <div class="reply-actions">
                  <span class="hint">امتیاز شما برای ارزیابی کیفیت پشتیبانی استفاده می‌شود.</span>
                  <button type="button" class="primary-btn" :disabled="!detailState.feedbackScore" @click="submitTicketFeedback">
                    ثبت نظر
                  </button>
                </div>
              </template>

              <div v-else class="feedback-static">
                <div class="feedback-score">{{ satisfactionLabel(detailState.ticket.customer_satisfaction) }}</div>
                <p v-if="detailState.ticket.customer_feedback">{{ detailState.ticket.customer_feedback }}</p>
                <p v-else>برای این تیکت امتیاز ثبت شده است.</p>
              </div>
            </section>
          </template>

          <div v-else class="empty-state conversation-empty">
            <div class="empty-icon" aria-hidden="true">
              <svg viewBox="0 0 120 120" fill="none">
                <path d="M28 32c0-8.837 7.163-16 16-16h32c8.837 0 16 7.163 16 16v24c0 8.837-7.163 16-16 16H58l-18 14v-14h-4c-8.837 0-16-7.163-16-16V32Z" stroke="currentColor" stroke-width="4" stroke-linejoin="round" />
                <path d="M46 40h28M46 54h18" stroke="currentColor" stroke-width="4" stroke-linecap="round" />
              </svg>
            </div>
            <h3>یک تیکت را انتخاب کنید</h3>
            <p>برای دیدن جزئیات کامل، پاسخ‌های پشتیبانی و ادامه گفتگو، از ستون سمت راست یک تیکت را باز کنید.</p>
          </div>
        </section>

      </section>
    </div>

    <div v-if="ticketModal.open" class="modal-overlay" @click.self="closeCreateTicketModal">
      <section class="modal-panel">
        <header class="modal-head">
          <div>
            <span class="panel-kicker">New Ticket</span>
            <h3>ثبت تیکت جدید</h3>
            <p>درخواست را دقیق ثبت کنید تا سریع‌تر به واحد درست ارجاع شود.</p>
          </div>
          <button type="button" class="close-btn" @click="closeCreateTicketModal">×</button>
        </header>

        <div class="modal-layout">
          <form class="modal-form" @submit.prevent="submitTicket">
            <div v-if="isWalletCardPaymentDraft" class="wallet-ticket-notice full">
              <strong>ثبت آماده برای مدیر کارواش</strong>
              <p>{{ walletCardPaymentNotice }}</p>
            </div>

            <label>
              <span>دسته‌بندی</span>
              <select v-model="ticketModal.category" :disabled="isWalletCardPaymentDraft">
                <option value="technical">مشکل فنی</option>
                <option value="financial">مشکل پرداخت</option>
                <option value="operations">سفارش و عملیات</option>
                <option value="account">حساب کاربری</option>
                <option value="other">سایر</option>
              </select>
            </label>

            <label>
              <span>اولویت</span>
              <select v-model="ticketModal.priority" :disabled="isWalletCardPaymentDraft">
                <option value="low">کم</option>
                <option value="medium">متوسط</option>
                <option value="high">زیاد</option>
                <option value="urgent">فوری</option>
              </select>
            </label>

            <label class="full">
              <span>عنوان تیکت</span>
              <input v-model.trim="ticketModal.subject" :readonly="isWalletCardPaymentDraft" required placeholder="مثلا: پرداخت انجام شد ولی سفارش ثبت نشد" />
            </label>

            <label class="full">
              <span>{{ isWalletCardPaymentDraft ? 'شرح آماده مدیر + تکمیل اطلاعات تراکنش' : 'شرح کامل' }}</span>
              <textarea
                v-model.trim="ticketModal.description"
                rows="5"
                required
                :placeholder="isWalletCardPaymentDraft ? 'متن آماده را نگه دارید و فقط اطلاعات تراکنش یا توضیح رسید را تکمیل کنید...' : 'زمان رخداد، نتیجه مورد انتظار، خطا یا جزئیات مرتبط را کامل بنویسید...'"
              />
            </label>

            <template v-if="ticketModal.category === 'financial'">
              <label>
                <span>شماره تراکنش</span>
                <input v-model.trim="ticketModal.context.transaction_id" placeholder="مثلا 9854123" />
              </label>
              <label>
                <span>مبلغ پرداخت</span>
                <input v-model.trim="ticketModal.context.payment_amount" placeholder="مثلا 250000" />
              </label>
              <label>
                <span>تاریخ پرداخت</span>
                <BaseDatePicker v-model="ticketModal.context.payment_date" placeholder="انتخاب تاریخ پرداخت" :clearable="false" />
              </label>
              <label>
                <span>شماره سفارش</span>
                <input v-model.trim="ticketModal.context.order_number" placeholder="مثلا 1482" />
              </label>
            </template>

            <template v-else-if="ticketModal.category === 'operations'">
              <label>
                <span>شماره سفارش</span>
                <input v-model.trim="ticketModal.context.order_number" placeholder="مثلا 1482" />
              </label>
              <label>
                <span>خدمت یا سرویس</span>
                <input v-model.trim="ticketModal.context.service_name" placeholder="مثلا سرامیک بدنه" />
              </label>
            </template>

            <template v-else-if="ticketModal.category === 'technical'">
              <label>
                <span>نوع دستگاه</span>
                <input v-model.trim="ticketModal.context.device_type" placeholder="مثلا موبایل اندروید" />
              </label>
              <label>
                <span>مرورگر / اپ</span>
                <input v-model.trim="ticketModal.context.browser_name" placeholder="مثلا Chrome 136" />
              </label>
              <label>
                <span>سیستم‌عامل</span>
                <input v-model.trim="ticketModal.context.os_name" placeholder="مثلا Android 14" />
              </label>
            </template>

            <template v-else-if="ticketModal.category === 'account'">
              <label>
                <span>موبایل حساب</span>
                <input v-model.trim="ticketModal.context.account_phone" placeholder="09xxxxxxxxx" />
              </label>
              <label>
                <span>موضوع حساب</span>
                <input v-model.trim="ticketModal.context.account_issue" placeholder="مثلا ورود یا تغییر شماره" />
              </label>
            </template>

            <div class="form-note full">
              <strong>{{ isWalletCardPaymentDraft ? 'راهنمای ثبت پرداخت' : 'نکته امنیتی' }}</strong>
              <p>{{ isWalletCardPaymentDraft ? 'اگر امکان ارسال رسید در همین تیکت را دارید، تصویر رسید را هم اضافه کنید. در غیر این صورت شماره تراکنش، مبلغ و زمان پرداخت را کامل بنویسید و ساختار آماده را تغییر ندهید.' : 'رمز عبور، اطلاعات کامل کارت بانکی یا کدهای امنیتی را داخل تیکت ارسال نکنید.' }}</p>
            </div>

            <label v-if="ticketModal.category === 'financial'" class="full receipt-upload-field">
              <span>آپلود رسید</span>
              <input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf" @change="handleReceiptFileChange" />
              <small v-if="selectedReceiptName" class="receipt-file-name">{{ selectedReceiptName }}</small>
            </label>

            <div class="modal-actions full">
              <button type="button" class="secondary-btn" @click="closeCreateTicketModal">انصراف</button>
              <button type="submit" class="primary-btn">ثبت تیکت</button>
            </div>
          </form>
        </div>
      </section>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '../../components/layout/AppShell.vue'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import api from '../../services/api'
import { formatJalaliDateTime } from '../../utils/date'

const route = useRoute()
const router = useRouter()
const searchQuery = ref('')
const activeStatusTab = ref('open')
const activeCategoryTab = ref('all')
const tickets = ref([])
const messageThreadRef = ref(null)

const getEmptyContext = () => ({
  transaction_id: '',
  payment_amount: '',
  payment_date: '',
  order_number: '',
  service_name: '',
  device_type: '',
  browser_name: '',
  os_name: '',
  account_phone: '',
  account_issue: ''
})

const getTodayJalaliString = () => {
  const parts = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).formatToParts(new Date())
  const year = parts.find((item) => item.type === 'year')?.value || '1405'
  const month = parts.find((item) => item.type === 'month')?.value || '01'
  const day = parts.find((item) => item.type === 'day')?.value || '01'
  return `${year}/${month}/${day}`
}

const statusCount = computed(() => tickets.value.reduce((acc, item) => {
  if (acc[item.status] === undefined) acc[item.status] = 0
  acc[item.status] += 1
  return acc
}, { open: 0, pending: 0, answered: 0, closed: 0 }))

const statusTrack = computed(() => [
  { key: 'open', label: 'باز', count: statusCount.value.open, description: 'تازه ثبت شده یا هنوز پاسخ نگرفته' },
  { key: 'pending', label: 'در حال بررسی', count: statusCount.value.pending, description: 'گفتگو ادامه دارد و در صف رسیدگی است' },
  { key: 'answered', label: 'پاسخ داده شده', count: statusCount.value.answered, description: 'پشتیبانی پاسخ داده و منتظر اقدام شماست' },
  { key: 'closed', label: 'بسته شده', count: statusCount.value.closed, description: 'پرونده‌های پایان‌یافته و آرشیوشده' }
])

const categoryTabs = [
  { key: 'all', label: 'همه' },
  { key: 'technical', label: 'فنی' },
  { key: 'financial', label: 'مالی' },
  { key: 'operations', label: 'عملیاتی' },
  { key: 'account', label: 'حساب' },
  { key: 'other', label: 'سایر' }
]

const ticketModal = reactive({
  open: false,
  mode: 'default',
  subject: '',
  description: '',
  category: 'technical',
  priority: 'medium',
  context: getEmptyContext(),
  receiptFile: null
})

const detailState = reactive({
  loading: false,
  ticket: null,
  replyBody: '',
  sendingReply: false,
  feedbackScore: 0,
  feedbackText: ''
})

const activeStatusLabel = computed(() => ({
  open: 'باز',
  pending: 'در حال بررسی',
  answered: 'پاسخ داده شده',
  closed: 'بسته شده'
}[activeStatusTab.value] || 'باز'))

const activeStatusDescription = computed(() => statusTrack.value.find((item) => item.key === activeStatusTab.value)?.description || '')
const requiresActionCount = computed(() => Number(statusCount.value.open || 0) + Number(statusCount.value.pending || 0) + Number(statusCount.value.answered || 0))
const waitingForUserCount = computed(() => Number(statusCount.value.answered || 0))
const inProgressCount = computed(() => Number(statusCount.value.pending || 0) + Number(statusCount.value.open || 0))

const filteredTickets = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return tickets.value.filter((item) => {
    if (item.status !== activeStatusTab.value) return false
    if (activeCategoryTab.value !== 'all' && item.category !== activeCategoryTab.value) return false
    if (!query) return true
    const haystack = `${item.id} ${item.subject} ${item.message || ''} ${item.category || ''} ${item.last_message_preview || ''}`.toLowerCase()
    return haystack.includes(query)
  })
})

const isWalletCardPaymentDraft = computed(() => ticketModal.mode === 'wallet-card-payment')
const walletCardPaymentNotice = computed(() => {
  if (!isWalletCardPaymentDraft.value) return ''
  return 'این متن از طرف مدیر کارواش برای ثبت پرداخت کارت به کارت آماده شده است. فقط شماره یا کد تراکنش را تکمیل کنید. اگر امکان بارگذاری رسید را دارید، رسید واریز را هم به تیکت اضافه کنید و بدون تغییر ساختار آماده، ثبت را بزنید.'
})
const selectedReceiptName = computed(() => ticketModal.receiptFile?.name || '')

const ticketActivityFeed = computed(() => {
  const ticket = detailState.ticket
  if (!ticket) return []
  const events = [
    {
      id: `create-${ticket.id}`,
      created_at: ticket.created_at,
      tone: 'info',
      title: 'تیکت ثبت شد',
      description: `درخواست با عنوان «${ticket.subject}» ایجاد شد.`
    }
  ]
  if (ticket.first_response_at) {
    events.push({
      id: `first-response-${ticket.id}`,
      created_at: ticket.first_response_at,
      tone: 'success',
      title: 'اولین پاسخ ثبت شد',
      description: `اولین پاسخ توسط ${ticket.responded_by_name || 'پشتیبانی'} ارسال شد.`
    })
  }
  if (Array.isArray(ticket.messages)) {
    ticket.messages.forEach((message) => {
      events.push({
        id: `message-${message.id}`,
        created_at: message.created_at,
        tone: message.sender_platform_role ? 'primary' : 'neutral',
        title: messageRoleLabel(message),
        description: (message.body || '').slice(0, 120)
      })
    })
  }
  if (ticket.closed_at) {
    events.push({
      id: `closed-${ticket.id}`,
      created_at: ticket.closed_at,
      tone: 'muted',
      title: 'تیکت بسته شد',
      description: 'فرآیند رسیدگی برای این درخواست پایان یافته است.'
    })
  }
  return events.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
})

const toFa = (value) => Number(value || 0).toLocaleString('fa-IR')
const formatDateTime = (value) => formatJalaliDateTime(value)

const statusGlyph = (value) => ({
  open: '✉',
  pending: '◔',
  answered: '✓',
  closed: '□'
}[value] || '✉')

const statusClass = (value) => ({
  open: 'open',
  pending: 'in-progress',
  answered: 'resolved',
  closed: 'closed'
}[value] || 'open')

const categoryLabel = (value) => ({
  technical: 'فنی',
  financial: 'مالی',
  operations: 'عملیاتی',
  account: 'حساب',
  other: 'سایر'
}[value] || 'سایر')

const priorityLabel = (value) => ({
  low: 'کم',
  medium: 'متوسط',
  high: 'زیاد',
  urgent: 'فوری'
}[value] || 'متوسط')

const clientStatusLabel = (ticket) => {
  if (!ticket) return '-'
  return ({
    open: 'باز',
    pending: 'در حال بررسی',
    answered: 'پاسخ داده شده',
    closed: 'بسته شده'
  }[ticket.status] || 'باز')
}

const isSupportMessage = (message) => ['hq_support', 'hq_admin'].includes(message?.sender_platform_role)
const messageAlignmentClass = (message) => (isSupportMessage(message) ? 'support' : 'tenant')
const messageRoleLabel = (message) => (isSupportMessage(message) ? 'مرکز پشتیبانی' : 'کارواش')

const ticketLastResponder = (ticket) => {
  if (ticket?.responded_by_name && ticket?.responded_at) return `پاسخ توسط ${ticket.responded_by_name}`
  if (ticket?.messages?.length) {
    const lastMessage = ticket.messages[ticket.messages.length - 1]
    return isSupportMessage(lastMessage) ? 'آخرین پیام از پشتیبانی' : 'آخرین پیام از کارواش'
  }
  return 'بدون پاسخ'
}

const firstResponseLabel = (ticket) => {
  if (!ticket?.first_response_at) return 'هنوز ثبت نشده'
  return formatDateTime(ticket.first_response_at)
}

const satisfactionLabel = (value) => {
  if (!value) return 'ثبت نشده'
  return `${toFa(value)} از ۵`
}

const focusSearch = () => {
  const element = document.querySelector('.search-box input')
  if (element) element.focus()
}

const focusLatestTicket = async () => {
  if (!tickets.value.length) return
  await openTicketDetail(tickets.value[0].id)
}

const toggleStatusFilter = () => {
  const order = ['open', 'pending', 'answered', 'closed']
  const currentIndex = order.findIndex((item) => item === activeStatusTab.value)
  activeStatusTab.value = order[(currentIndex + 1) % order.length]
}

const buildStructuredMessage = () => {
  const lines = [String(ticketModal.description || '').trim()]
  const contextLines = []

  const fieldMap = {
    transaction_id: 'شماره تراکنش',
    payment_amount: 'مبلغ پرداخت',
    payment_date: 'تاریخ پرداخت',
    order_number: 'شماره سفارش',
    service_name: 'سرویس',
    device_type: 'نوع دستگاه',
    browser_name: 'مرورگر / اپ',
    os_name: 'سیستم‌عامل',
    account_phone: 'موبایل حساب',
    account_issue: 'موضوع حساب'
  }

  Object.entries(ticketModal.context).forEach(([key, value]) => {
    const text = String(value || '').trim()
    if (!text) return
    contextLines.push(`${fieldMap[key]}: ${text}`)
  })

  if (contextLines.length) {
    lines.push('')
    lines.push('اطلاعات مرتبط:')
    lines.push(...contextLines)
  }

  return lines.join('\n').trim()
}

const openCreateTicketModal = () => {
  ticketModal.open = true
  ticketModal.mode = 'default'
}

const openWalletPaymentTicketModal = () => {
  const amount = String(route.query.amount || '').trim()
  const walletName = String(route.query.wallet_name || '').trim()
  const walletId = String(route.query.wallet_id || '').trim()
  ticketModal.open = true
  ticketModal.mode = 'wallet-card-payment'
  ticketModal.category = 'financial'
  ticketModal.priority = 'high'
  ticketModal.subject = 'درخواست بررسی پرداخت کارت به کارت و شارژ کیف پول'
  ticketModal.description = [
    'نوع درخواست: wallet-card-payment',
    'اینجانب مدیر کارواش، مبلغ شارژ کیف پول را به صورت کارت به کارت پرداخت کرده‌ام.',
    'درخواست دارم پرداخت بررسی شود و در صورت تایید، کیف پول کارواش شارژ شود.',
    walletId ? `شناسه کیف پول مقصد: ${walletId}` : '',
    'شماره یا کد تراکنش و مشخصات رسید واریز را در این تیکت تکمیل می‌کنم.'
  ].filter(Boolean).join('\n')
  Object.assign(ticketModal.context, getEmptyContext(), {
    payment_amount: amount,
    payment_date: getTodayJalaliString(),
    order_number: walletName
  })
}

const handleReceiptFileChange = (event) => {
  const [file] = Array.from(event?.target?.files || [])
  ticketModal.receiptFile = file || null
}

const closeCreateTicketModal = () => {
  ticketModal.open = false
  ticketModal.mode = 'default'
  ticketModal.subject = ''
  ticketModal.description = ''
  ticketModal.category = 'technical'
  ticketModal.priority = 'medium'
  ticketModal.receiptFile = null
  Object.assign(ticketModal.context, getEmptyContext())
}

const resetDetailState = () => {
  detailState.loading = false
  detailState.ticket = null
  detailState.replyBody = ''
  detailState.sendingReply = false
  detailState.feedbackScore = 0
  detailState.feedbackText = ''
}

const scrollMessagesToBottom = async () => {
  await nextTick()
  const thread = messageThreadRef.value
  if (thread) thread.scrollTop = thread.scrollHeight
}

const openTicketDetail = async (ticketId, options = {}) => {
  if (!ticketId) return
  detailState.loading = true
  if (!options.keepReply) detailState.replyBody = ''
  try {
    const { data } = await api.get(`/auth/support/tickets/${ticketId}/`)
    detailState.ticket = data
    detailState.feedbackScore = Number(data?.customer_satisfaction || 0)
    detailState.feedbackText = data?.customer_feedback || ''
    await scrollMessagesToBottom()
  } finally {
    detailState.loading = false
  }
}

const canRateTicket = (ticket) => {
  if (!ticket) return false
  if (ticket.status !== 'closed') return false
  return !ticket.customer_satisfaction
}

const submitTicketFeedback = async () => {
  if (!detailState.ticket?.id || !detailState.feedbackScore) return
  const { data } = await api.post(`/auth/support/tickets/${detailState.ticket.id}/feedback/`, {
    customer_satisfaction: detailState.feedbackScore,
    customer_feedback: detailState.feedbackText
  })
  detailState.ticket = data
  await loadTickets()
}

const submitReply = async () => {
  if (!detailState.ticket?.id || !detailState.replyBody || detailState.sendingReply || detailState.ticket.status === 'closed') return
  detailState.sendingReply = true
  try {
    await api.post(`/auth/support/tickets/${detailState.ticket.id}/messages/`, {
      body: detailState.replyBody
    })
    detailState.replyBody = ''
    await Promise.all([
      openTicketDetail(detailState.ticket.id, { keepReply: true }),
      loadTickets({ preserveSelection: true })
    ])
  } finally {
    detailState.sendingReply = false
  }
}

const ensureActiveTicket = async () => {
  const visibleIds = filteredTickets.value.map((item) => item.id)
  if (!visibleIds.length) {
    resetDetailState()
    return
  }
  if (detailState.ticket?.id && visibleIds.includes(detailState.ticket.id)) return
  await openTicketDetail(visibleIds[0])
}

const loadTickets = async (options = {}) => {
  const previousTicketId = detailState.ticket?.id
  const { data } = await api.get('/auth/support/tickets/')
  tickets.value = Array.isArray(data) ? data : []
  if (options.preserveSelection && previousTicketId) {
    const exists = tickets.value.some((item) => item.id === previousTicketId)
    if (exists) return
  }
  await ensureActiveTicket()
}

const submitTicket = async () => {
  const payload = new FormData()
  payload.append('subject', ticketModal.subject)
  payload.append('message', buildStructuredMessage())
  payload.append('category', ticketModal.category)
  payload.append('priority', ticketModal.priority)
  if (ticketModal.receiptFile) {
    payload.append('attachments', ticketModal.receiptFile)
  }
  const { data } = await api.post('/auth/support/tickets/', payload)
  activeStatusTab.value = 'open'
  closeCreateTicketModal()
  await loadTickets({ preserveSelection: true })
  await openTicketDetail(data.id)
}

watch(activeStatusTab, async () => {
  await ensureActiveTicket()
})

watch(activeCategoryTab, async () => {
  await ensureActiveTicket()
})

watch(searchQuery, async () => {
  await ensureActiveTicket()
})

watch(() => ticketModal.category, (value) => {
  if (value === 'financial' && !ticketModal.context.payment_date) {
    ticketModal.context.payment_date = getTodayJalaliString()
  }
})

onMounted(async () => {
  await loadTickets()
  if (route.query.prefill === 'wallet-card-payment') {
    openWalletPaymentTicketModal()
    router.replace({ path: route.path, query: {} })
  }
})
</script>

<style scoped>
.support-page {
  display: grid;
  gap: 18px;
}

.support-sla-banner {
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, #ffffff, #f4edff);
  border: 1px solid #e8d9ff;
  color: #5b3f8c;
  font-weight: 800;
  line-height: 1.9;
}

.surface-card,
.modal-panel {
  border-radius: 32px;
  border: 1px solid rgba(226, 232, 240, 0.86);
  box-shadow: 0 24px 56px rgba(15, 23, 42, 0.06);
}

.hero-shell {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) 360px;
  gap: 18px;
  padding: 28px;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.16), transparent 26%),
    radial-gradient(circle at left bottom, rgba(59, 130, 246, 0.12), transparent 20%),
    linear-gradient(135deg, #ffffff 0%, #f2f8ff 56%, #edf5ff 100%);
}

.hero-kicker,
.panel-kicker,
.desk-pill {
  display: inline-flex;
  width: fit-content;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(0, 88, 190, 0.1);
  color: #0058be;
  font-size: 12px;
  font-weight: 800;
}

.hero-copy {
  display: grid;
  gap: 14px;
}

.hero-copy h2,
.panel-head h3,
.conversation-title h3,
.modal-head h3,
.empty-state h3 {
  margin: 0;
  color: #0f172a;
}

.hero-copy h2 {
  font-size: 38px;
  line-height: 1.35;
}

.hero-copy p,
.hero-spotlight p,
.ticket-row p,
.conversation-copy p,
.helper-card p,
.activity-row p,
.empty-state p,
.modal-head p,
.form-note p,
.feedback-static p,
.closed-note p {
  margin: 0;
  color: #526173;
  line-height: 1.9;
}

.hero-actions,
.panel-head,
.chip-row,
.ticket-row-top,
.ticket-row-meta,
.conversation-title,
.conversation-tags,
.reply-actions,
.block-head,
.detail-row,
.message-meta,
.modal-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.primary-btn,
.secondary-btn,
.ghost-btn,
.mini-btn,
.chip-btn,
.rating-star-btn {
  border: 0;
  cursor: pointer;
  font: inherit;
}

.primary-btn {
  border-radius: 16px;
  padding: 12px 18px;
  color: #fff;
  background: linear-gradient(135deg, #0058be, #0ea5e9);
  font-weight: 800;
  box-shadow: 0 18px 34px rgba(0, 88, 190, 0.18);
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-btn,
.ghost-btn,
.mini-btn {
  border-radius: 14px;
  min-height: 44px;
  padding: 0 16px;
  background: rgba(255, 255, 255, 0.9);
  color: #334155;
  border: 1px solid rgba(203, 213, 225, 0.9);
}

.hero-side,
.hero-mini-grid,
.stats-grid,
.workspace-grid,
.inbox-summary-grid,
.metric-strip,
.modal-layout,
.modal-form {
  display: grid;
  gap: 14px;
}

.hero-side {
  align-content: start;
}

.hero-spotlight,
.hero-mini-card,
.summary-tile,
.metric-card,
.reply-shell,
.feedback-shell,
.helper-card,
.side-card {
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.86);
  background: rgba(255, 255, 255, 0.9);
}

.hero-spotlight {
  padding: 20px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(15, 93, 215, 0.92));
  color: #fff;
}

.hero-spotlight small,
.hero-spotlight p {
  color: rgba(255, 255, 255, 0.78);
}

.hero-spotlight strong {
  display: block;
  margin: 10px 0 8px;
  font-size: 28px;
}

.hero-mini-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.hero-mini-card,
.summary-tile,
.metric-card,
.helper-card,
.side-card {
  padding: 16px;
}

.hero-mini-card small,
.summary-tile small,
.metric-card small,
.stat-card small,
.detail-row span,
.activity-row small,
.form-note strong,
.modal-form label span {
  color: #64748b;
  font-size: 12px;
}

.hero-mini-card strong,
.summary-tile strong,
.metric-card strong,
.stat-card strong,
.detail-row strong {
  color: #0f172a;
}

.hero-mini-card strong,
.summary-tile strong,
.stat-card strong {
  font-size: 24px;
}

.hero-mini-card span,
.panel-head span,
.ticket-row-meta,
.block-head span,
.feedback-static p {
  color: #64748b;
  font-size: 12px;
}

.stats-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.stat-card {
  padding: 18px;
  display: grid;
  gap: 6px;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(226, 232, 240, 0.86);
  cursor: pointer;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.04);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.stat-card:hover,
.stat-card.active {
  transform: translateY(-2px);
  box-shadow: 0 24px 46px rgba(15, 23, 42, 0.08);
}

.stat-card.open.active { background: linear-gradient(180deg, rgba(219, 234, 254, 0.88), rgba(255, 255, 255, 0.96)); }
.stat-card.in-progress.active { background: linear-gradient(180deg, rgba(254, 243, 199, 0.86), rgba(255, 255, 255, 0.96)); }
.stat-card.resolved.active { background: linear-gradient(180deg, rgba(220, 252, 231, 0.86), rgba(255, 255, 255, 0.96)); }
.stat-card.closed.active { background: linear-gradient(180deg, rgba(226, 232, 240, 0.82), rgba(255, 255, 255, 0.96)); }

.stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
}

.stat-card.open .stat-icon { background: #dbeafe; color: #1d4ed8; }
.stat-card.in-progress .stat-icon { background: #fef3c7; color: #b45309; }
.stat-card.resolved .stat-icon { background: #dcfce7; color: #166534; }
.stat-card.closed .stat-icon { background: #e2e8f0; color: #475569; }

.workspace-grid {
  grid-template-columns: minmax(320px, 400px) minmax(0, 1.35fr);
  align-items: start;
}

.surface-card {
  min-height: 0;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.06), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(248, 251, 255, 0.97));
}

.inbox-card,
.conversation-card{
  display: grid;
  gap: 14px;
  padding: 20px;
}

.chip-row {
  justify-content: flex-start;
}

.chip-btn {
  border-radius: 999px;
  padding: 9px 13px;
  background: #f1f5f9;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.chip-btn.active {
  background: linear-gradient(135deg, #dbeafe, #e0f2fe);
  color: #0f4aa8;
}

.inbox-summary-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.ticket-list,
.message-thread,
.activity-list,
.stack-list {
  display: grid;
  gap: 12px;
}

.ticket-list,
.message-thread {
  min-height: 0;
  overflow: auto;
}

.ticket-list {
  max-height: calc(100vh - 380px);
  align-content: start;
}

.ticket-row {
  display: grid;
  gap: 10px;
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.86);
  background: rgba(255, 255, 255, 0.92);
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.ticket-row:hover {
  transform: translateY(-1px);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.06);
}

.ticket-row.selected {
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.96), rgba(255, 255, 255, 0.98));
  box-shadow:
    0 20px 42px rgba(37, 99, 235, 0.12),
    inset 0 0 0 1px rgba(59, 130, 246, 0.18);
}

.ticket-row p {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ticket-row-tags,
.conversation-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-pill,
.meta-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 7px 11px;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.meta-pill {
  background: #f1f6fb;
  color: #44607c;
}

.status-pill.open {
  background: #e2e8f0;
  color: #334155;
}

.status-pill.in-progress {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-pill.resolved {
  background: #dcfce7;
  color: #166534;
}

.status-pill.closed {
  background: #f1f5f9;
  color: #475569;
}

.conversation-card {
  grid-template-rows: auto auto minmax(0, 1fr) auto auto;
}

.conversation-copy {
  display: grid;
  gap: 10px;
}

.metric-strip {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card strong {
  font-size: 14px;
  line-height: 1.8;
}

.message-thread {
  padding: 18px;
  border-radius: 28px;
  background: linear-gradient(180deg, rgba(247, 250, 255, 0.94), rgba(255, 255, 255, 0.98));
}

.message-row {
  display: flex;
}

.message-row.support {
  justify-content: flex-start;
}

.message-row.tenant {
  justify-content: flex-end;
}

.message-bubble {
  width: min(74%, 640px);
  display: grid;
  gap: 8px;
  padding: 15px 17px;
  border-radius: 24px;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.05);
}

.message-bubble.support {
  background: #fff;
  border-top-right-radius: 8px;
}

.message-bubble.tenant {
  background: linear-gradient(135deg, #0f5ed7, #0284c7);
  color: #fff;
  border-top-left-radius: 8px;
}

.sender-tag {
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
}

.sender-tag.support {
  background: #e8f1ff;
  color: #1d4ed8;
}

.sender-tag.tenant {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

.message-bubble p {
  margin: 0;
  line-height: 1.95;
  white-space: pre-wrap;
}

.message-meta small {
  color: inherit;
  opacity: 0.75;
}

.reply-shell,
.feedback-shell {
  padding: 18px;
  display: grid;
  gap: 12px;
}

.reply-head {
  display: grid;
  gap: 6px;
}

.reply-form {
  display: grid;
  gap: 10px;
}

.reply-form textarea,
.feedback-shell textarea,
.modal-form input,
.modal-form textarea,
.modal-form select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(203, 213, 225, 0.8);
  border-radius: 16px;
  padding: 10px 12px;
  font: inherit;
  background: rgba(248, 251, 255, 0.96);
  color: #0f172a;
  resize: vertical;
}

.reply-form textarea,
.feedback-shell textarea {
  min-height: 100px;
}

.modal-form textarea {
  min-height: 112px;
  max-height: 180px;
}

.reply-form textarea:focus,
.feedback-shell textarea:focus,
.modal-form input:focus,
.modal-form textarea:focus,
.modal-form select:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.35);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.08);
}

.modal-form input[readonly],
.modal-form select:disabled {
  opacity: 0.78;
  cursor: not-allowed;
  background: rgba(237, 242, 247, 0.96);
  color: #64748b;
}

.rating-stars {
  display: flex;
  gap: 8px;
}

.rating-star-btn {
  background: transparent;
  color: #cbd5e1;
  font-size: 30px;
  padding: 0;
  line-height: 1;
}

.rating-star-btn.active {
  color: #f59e0b;
}

.feedback-score {
  color: #0f172a;
  font-size: 22px;
  font-weight: 800;
}

.sidebar-block,
.side-card {
  display: grid;
  gap: 10px;
}

.detail-list {
  display: grid;
  gap: 10px;
}

.detail-row {
  padding: 10px 12px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.94);
}

.receipt-upload-field input[type="file"] {
  padding: 12px;
  border: 1px dashed rgba(168, 85, 247, 0.34);
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(250, 245, 255, 0.96), rgba(255, 255, 255, 0.98));
}

.receipt-file-name {
  color: #6d28d9;
  font-weight: 700;
}

.ticket-attachments-shell {
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.86);
  background: rgba(255, 255, 255, 0.92);
  display: grid;
  gap: 12px;
}

.ticket-attachments-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.ticket-attachment-item {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 18px;
  text-decoration: none;
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.98), rgba(245, 243, 255, 0.98));
  border: 1px solid rgba(216, 180, 254, 0.34);
}

.ticket-attachment-item strong {
  color: #1e293b;
}

.ticket-attachment-item span {
  color: #7c3aed;
  font-size: 12px;
  font-weight: 700;
}

.activity-row {
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.activity-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
}

.activity-dot.info,
.activity-dot.primary {
  background: #2563eb;
}

.activity-dot.success {
  background: #16a34a;
}

.activity-dot.neutral,
.activity-dot.muted {
  background: #94a3b8;
}

.helper-card.compact {
  padding: 12px;
}

.empty-inline {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.empty-state,
.loading-state {
  min-height: 260px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  text-align: center;
  color: #64748b;
}

.conversation-empty {
  min-height: 100%;
}

.empty-icon {
  width: 88px;
  height: 88px;
  color: #2563eb;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(15, 23, 42, 0.44);
  backdrop-filter: blur(8px);
  overflow: hidden;
}

.modal-panel {
  width: min(980px, 100%);
  max-height: min(86vh, 820px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.1), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 255, 0.98));
}

.modal-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 16px 20px 14px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
}

.close-btn {
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: 14px;
  background: #eff6ff;
  color: #0f4c81;
  font-size: 28px;
  cursor: pointer;
}

.modal-layout {
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  padding: 16px 20px 20px;
  overflow: auto;
  overscroll-behavior: contain;
}

.modal-form {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.modal-form label {
  display: grid;
  gap: 8px;
}

.modal-form .full {
  grid-column: 1 / -1;
}

.form-note {
  padding: 12px 14px;
  border-radius: 20px;
  background: rgba(254, 242, 242, 0.96);
  border: 1px solid rgba(254, 202, 202, 0.8);
  display: grid;
  gap: 4px;
}

.wallet-ticket-notice {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(236, 228, 255, 0.92), rgba(255, 255, 255, 0.98));
  border: 1px solid rgba(196, 181, 253, 0.72);
}

.wallet-ticket-notice strong {
  color: #4c1d95;
}

.wallet-ticket-notice p {
  margin: 0;
  color: #5b4b7a;
  line-height: 1.9;
}

.modal-side { display: none; }

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-weight: 700;
}

@media (max-width: 1460px) {
  .workspace-grid {
    grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);
  }
}

@media (max-width: 1180px) {
  .workspace-grid,
  .modal-layout {
    grid-template-columns: 1fr;
  }

  .stats-grid,
  .metric-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

}

@media (max-height: 760px) and (min-width: 761px) {
  .modal-panel {
    width: min(900px, 100%);
    max-height: calc(100vh - 24px);
  }

  .modal-layout {
    grid-template-columns: 1fr;
    padding: 14px 18px 18px;
  }

  .modal-form textarea {
    min-height: 86px;
  }
}

@media (max-width: 760px) {
  .inbox-card,
  .conversation-card,
  .modal-layout {
    padding: 16px;
  }

  .modal-head {
    padding: 14px 16px 12px;
  }

  .hero-copy h2 {
    font-size: 30px;
  }

  .stats-grid,
  .hero-mini-grid,
  .inbox-summary-grid,
  .metric-strip {
    grid-template-columns: 1fr;
  }

  .modal-form {
    grid-template-columns: 1fr;
  }

  .modal-form .full {
    grid-column: 1 / -1;
  }

  .message-bubble {
    width: min(92%, 100%);
  }

  .hero-actions,
  .panel-head,
  .ticket-row-top,
  .ticket-row-meta,
  .conversation-title,
  .conversation-tags,
  .reply-actions,
  .block-head,
  .detail-row,
  .message-meta,
  .modal-actions,
  .field-row {
    flex-direction: column;
    align-items: stretch;
  }

  .ticket-list {
    max-height: none;
  }

  .message-thread {
    padding: 14px;
  }

  .status-pill,
  .meta-pill {
    white-space: normal;
    text-align: center;
  }

  .modal-overlay {
    padding: 10px;
  }

  .modal-panel {
    max-height: calc(100vh - 20px);
    grid-template-rows: auto minmax(0, 1fr);
    overflow: hidden;
  }
}
</style>
