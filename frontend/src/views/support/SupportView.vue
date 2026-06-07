<template>
  <AppShell
    title="پشتیبانی"
    subtitle="مدیریت تیکت‌ها و ارتباط با پشتیبانی"
    :show-search="true"
    search-placeholder="جستجو بر اساس شناسه، عنوان یا درخواست‌کننده..."
    :search-query="searchQuery"
    @update:search-query="searchQuery = $event"
  >
    <div class="support-content">
      <section class="tickets-shell">
        <header class="tickets-head">
          <div class="tickets-head-copy">
            <h1>مرکز تیکت</h1>
            <p>روی هر تیکت بزنید تا گفت‌وگوی کامل، زمان پاسخ و سابقه پیام‌ها باز شود.</p>
          </div>
          <div class="head-actions">
            <button class="icon-btn" type="button" @click="focusSearch" aria-label="جستجو">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="11" cy="11" r="6" stroke="currentColor" stroke-width="1.8" />
                <path d="m16 16 4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              </svg>
            </button>
            <button class="icon-btn" type="button" @click="toggleStatusFilter" aria-label="فیلتر">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M4 6h16l-6 7v5l-4 2v-7L4 6Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
              </svg>
            </button>
            <button class="new-ticket-btn compact" type="button" @click="openCreateTicketModal">+ تیکت جدید</button>
          </div>
        </header>

        <section class="status-track">
          <button
            v-for="(item, index) in statusTrack"
            :key="item.key"
            type="button"
            class="status-node"
            :class="{ active: activeStatusTab === item.key }"
            @click="activeStatusTab = item.key"
          >
            <span class="status-icon" :class="statusClass(item.key)">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="3" y="5" width="18" height="14" rx="3" stroke="currentColor" stroke-width="1.7" />
                <path d="m4.5 8 6.5 4.5c.62.43 1.37.43 1.99 0L19.5 8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
              </svg>
            </span>
            <span class="status-count">{{ toFa(item.count) }}</span>
            <span class="status-label">{{ item.label }}</span>
            <span v-if="index < statusTrack.length - 1" class="status-line"></span>
          </button>
        </section>

        <section class="support-board">
          <aside class="tickets-list-panel">
            <header class="list-panel-head">
              <div>
                <strong>فهرست تیکت‌ها</strong>
                <small>{{ toFa(filteredTickets.length) }} مورد در این وضعیت</small>
              </div>
            </header>

            <div v-if="filteredTickets.length" class="tickets-list">
              <article
                v-for="ticket in filteredTickets"
                :key="ticket.id"
                class="ticket-row"
                :class="{ selected: detailState.ticket?.id === ticket.id }"
                @click="openTicketDetail(ticket.id)"
              >
                <div class="ticket-row-main">
                  <div class="ticket-row-top">
                    <strong>{{ ticket.subject }}</strong>
                    <span class="status-pill" :class="statusClass(ticket.status)">{{ statusLabel(ticket.status) }}</span>
                  </div>
                  <p>{{ ticket.last_message_preview || ticket.message }}</p>
                  <div class="ticket-row-meta">
                    <span class="mono">#{{ ticket.id }}</span>
                    <span>{{ formatDateTime(ticket.updated_at) }}</span>
                  </div>
                </div>
                <div class="ticket-row-side">
                  <small>{{ ticket.assigned_to_name || 'بدون تخصیص' }}</small>
                  <span class="message-count">{{ toFa(ticket.messages_count || 0) }} پیام</span>
                </div>
              </article>
            </div>

            <div v-else class="empty-state list-empty">
              <div class="empty-icon" aria-hidden="true">
                <svg viewBox="0 0 64 64" fill="none">
                  <circle cx="32" cy="32" r="27" stroke="currentColor" stroke-width="2.4" />
                  <path d="m22 33 8 8 14-18" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </div>
              <h2>همه چی آرومه</h2>
              <p>در حال حاضر هیچ تیکتی در این وضعیت ندارید</p>
              <button class="new-ticket-btn" type="button" @click="openCreateTicketModal">+ نوشتن تیکت</button>
            </div>
          </aside>

          <section class="chat-panel">
            <div v-if="detailState.loading" class="chat-loading">در حال بارگذاری گفت‌وگو...</div>

            <template v-else-if="detailState.ticket">
              <header class="chat-head">
                <div class="chat-head-copy">
                  <div class="chat-title-row">
                    <h2>{{ detailState.ticket.subject }}</h2>
                    <span class="status-pill" :class="statusClass(detailState.ticket.status)">
                      {{ statusLabel(detailState.ticket.status) }}
                    </span>
                  </div>
                  <p>{{ detailState.ticket.message }}</p>
                </div>
                <div class="chat-head-id">
                  <span class="mono">#{{ detailState.ticket.id }}</span>
                </div>
              </header>

              <section class="chat-summary-grid">
                <article class="summary-card">
                  <span>پشتیبان</span>
                  <strong>{{ detailState.ticket.assigned_to_name || 'هنوز تخصیص نشده' }}</strong>
                  <small>مرکز تیکت</small>
                </article>
                <article class="summary-card">
                  <span>اولین پاسخ</span>
                  <strong>{{ formatDateTime(detailState.ticket.first_response_at) }}</strong>
                  <small>{{ detailState.ticket.responded_by_name || 'بدون پاسخ' }}</small>
                </article>
                <article class="summary-card">
                  <span>آخرین پاسخ</span>
                  <strong>{{ formatDateTime(detailState.ticket.responded_at || detailState.ticket.last_message_at) }}</strong>
                  <small>{{ lastResponderLabel(detailState.ticket) }}</small>
                </article>
                <article class="summary-card">
                  <span>آخرین بروزرسانی</span>
                  <strong>{{ formatDateTime(detailState.ticket.updated_at) }}</strong>
                  <small>{{ toFa(detailState.ticket.messages?.length || 0) }} پیام ثبت شده</small>
                </article>
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
                      <strong>{{ message.sender_name || '-' }}</strong>
                      <span class="sender-tag" :class="messageAlignmentClass(message)">
                        {{ messageRoleLabel(message) }}
                      </span>
                    </div>
                    <p>{{ message.body }}</p>
                    <small>{{ formatDateTime(message.created_at) }}</small>
                  </div>
                </article>
              </section>

              <section class="reply-shell">
                <div class="reply-head">
                  <strong>ارسال پاسخ به تیکت</strong>
                  <small v-if="detailState.ticket.status === 'closed'">این تیکت بسته شده و فقط قابل مشاهده است.</small>
                  <small v-else>پیام شما در همان گفت‌وگوی تیکت برای مرکز پشتیبانی ثبت می‌شود.</small>
                </div>
                <div class="reply-form">
                  <textarea
                    v-model.trim="detailState.replyBody"
                    :disabled="detailState.sendingReply || detailState.ticket.status === 'closed'"
                    rows="4"
                    placeholder="پاسخ خود را اینجا بنویسید..."
                    @keydown.ctrl.enter.prevent="submitReply"
                  />
                  <div class="reply-actions">
                    <span class="hint">ارسال سریع با `Ctrl + Enter`</span>
                    <button
                      type="button"
                      class="primary-btn"
                      :disabled="detailState.sendingReply || detailState.ticket.status === 'closed' || !detailState.replyBody"
                      @click="submitReply"
                    >
                      {{ detailState.sendingReply ? 'در حال ارسال...' : 'ارسال پیام' }}
                    </button>
                  </div>
                </div>
              </section>

              <div v-if="canRateTicket(detailState.ticket)" class="rating-box">
                <strong>رضایت از پاسخ پشتیبانی</strong>
                <div class="rating-stars">
                  <button
                    v-for="score in [1, 2, 3, 4, 5]"
                    :key="score"
                    type="button"
                    class="rating-star-btn"
                    :class="{ active: score <= detailState.feedbackScore }"
                    @click="detailState.feedbackScore = score"
                  >
                    ★
                  </button>
                </div>
                <textarea v-model.trim="detailState.feedbackText" rows="3" placeholder="اختیاری: کیفیت پاسخ را توضیح دهید..." />
                <div class="rating-actions">
                  <button type="button" class="primary-btn" @click="submitTicketFeedback">ثبت رضایت</button>
                </div>
              </div>

              <div v-else-if="detailState.ticket.customer_satisfaction" class="rating-box rating-box-static">
                <strong>رضایت ثبت‌شده</strong>
                <div class="rating-static">{{ detailState.ticket.customer_satisfaction.toLocaleString('fa-IR') }} / ۵</div>
                <p>{{ detailState.ticket.customer_feedback || 'بازخورد متنی ثبت نشده است.' }}</p>
              </div>
            </template>

            <div v-else class="empty-chat-state">
              <div class="empty-chat-visual">
                <svg viewBox="0 0 120 120" fill="none" aria-hidden="true">
                  <path d="M28 32c0-8.837 7.163-16 16-16h32c8.837 0 16 7.163 16 16v24c0 8.837-7.163 16-16 16H58l-18 14v-14h-4c-8.837 0-16-7.163-16-16V32Z" stroke="currentColor" stroke-width="4" stroke-linejoin="round" />
                  <path d="M46 40h28M46 54h18" stroke="currentColor" stroke-width="4" stroke-linecap="round" />
                </svg>
              </div>
              <h2>یک تیکت را انتخاب کنید</h2>
              <p>برای دیدن گفت‌وگوی کامل، زمان پاسخ پشتیبان و ارسال پیام جدید، از ستون سمت راست یک تیکت را باز کنید.</p>
            </div>
          </section>
        </section>
      </section>
    </div>

    <div v-if="ticketModal.open" class="modal-overlay" @click.self="closeCreateTicketModal">
      <section class="modal-panel">
        <header class="modal-head">
          <h3>ثبت تیکت جدید</h3>
          <button class="close-btn" type="button" @click="closeCreateTicketModal">×</button>
        </header>
        <form class="modal-form" @submit.prevent="submitTicket">
          <label>
            <span>عنوان</span>
            <input v-model.trim="ticketModal.subject" required placeholder="مثلا: خطا در ثبت واریز" />
          </label>
          <label class="full">
            <span>شرح</span>
            <textarea v-model.trim="ticketModal.description" rows="4" required placeholder="جزئیات کامل مشکل را وارد کنید..." />
          </label>
          <div class="modal-actions">
            <button type="button" class="secondary-btn" @click="closeCreateTicketModal">انصراف</button>
            <button type="submit" class="primary-btn">ثبت تیکت</button>
          </div>
        </form>
      </section>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import AppShell from '../../components/layout/AppShell.vue'
import api from '../../services/api'
import { formatJalaliDate, formatJalaliDateTime } from '../../utils/date'

const searchQuery = ref('')
const activeStatusTab = ref('open')
const tickets = ref([])
const messageThreadRef = ref(null)

const statusCount = computed(() => tickets.value.reduce((acc, item) => {
  if (acc[item.status] === undefined) acc[item.status] = 0
  acc[item.status] += 1
  return acc
}, { open: 0, pending: 0, answered: 0, closed: 0 }))

const statusTrack = computed(() => [
  { key: 'open', label: 'تیکت های باز', count: statusCount.value.open },
  { key: 'pending', label: 'در انتظار پیگیری', count: statusCount.value.pending },
  { key: 'answered', label: 'پاسخ داده شده', count: statusCount.value.answered },
  { key: 'closed', label: 'بسته شده', count: statusCount.value.closed }
])

const filteredTickets = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return tickets.value.filter((item) => {
    if (item.status !== activeStatusTab.value) return false
    if (!query) return true
    const haystack = `${item.id} ${item.subject} ${item.created_by_name || ''} ${item.last_message_preview || ''}`.toLowerCase()
    return haystack.includes(query)
  })
})

const ticketModal = reactive({
  open: false,
  subject: '',
  description: ''
})

const detailState = reactive({
  loading: false,
  ticket: null,
  replyBody: '',
  sendingReply: false,
  feedbackScore: 0,
  feedbackText: ''
})

const toFa = (value) => Number(value || 0).toLocaleString('fa-IR')

const statusLabel = (value) => ({
  open: 'باز',
  pending: 'در انتظار پیگیری',
  answered: 'پاسخ داده شده',
  closed: 'بسته شده'
}[value] || 'باز')

const statusClass = (value) => ({
  open: 'open',
  pending: 'in-progress',
  answered: 'resolved',
  closed: 'closed'
}[value] || 'open')

const isSupportMessage = (message) => ['hq_support', 'hq_admin'].includes(message?.sender_platform_role)

const messageAlignmentClass = (message) => (isSupportMessage(message) ? 'support' : 'tenant')

const messageRoleLabel = (message) => (isSupportMessage(message) ? 'مرکز پشتیبانی' : 'کاربر کارواش')

const lastResponderLabel = (ticket) => {
  if (ticket?.responded_by_name && ticket?.responded_at) {
    return `پاسخ توسط ${ticket.responded_by_name}`
  }
  if (ticket?.messages?.length) {
    const lastMessage = ticket.messages[ticket.messages.length - 1]
    return isSupportMessage(lastMessage) ? 'آخرین پیام از پشتیبانی' : 'آخرین پیام از کارواش'
  }
  return 'بدون پاسخ'
}

const focusSearch = () => {
  const element = document.querySelector('.search-box input')
  if (element) element.focus()
}

const toggleStatusFilter = () => {
  const order = ['open', 'pending', 'answered', 'closed']
  const currentIndex = order.findIndex((item) => item === activeStatusTab.value)
  activeStatusTab.value = order[(currentIndex + 1) % order.length]
}

const openCreateTicketModal = () => {
  ticketModal.open = true
}

const closeCreateTicketModal = () => {
  ticketModal.open = false
  ticketModal.subject = ''
  ticketModal.description = ''
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
  if (thread) {
    thread.scrollTop = thread.scrollHeight
  }
}

const openTicketDetail = async (ticketId, options = {}) => {
  if (!ticketId) return
  detailState.loading = true
  if (!options.keepReply) {
    detailState.replyBody = ''
  }
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
  if (!['answered', 'closed'].includes(ticket.status)) return false
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
  if (!detailState.ticket?.id || !detailState.replyBody || detailState.sendingReply) return
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

const formatDate = (value) => formatJalaliDate(value)
const formatDateTime = (value) => formatJalaliDateTime(value)

const ensureActiveTicket = async () => {
  const visibleIds = filteredTickets.value.map((item) => item.id)
  if (!visibleIds.length) {
    resetDetailState()
    return
  }
  if (detailState.ticket?.id && visibleIds.includes(detailState.ticket.id)) {
    return
  }
  await openTicketDetail(visibleIds[0])
}

const loadTickets = async (options = {}) => {
  const previousTicketId = detailState.ticket?.id
  const { data } = await api.get('/auth/support/tickets/')
  tickets.value = Array.isArray(data) ? data : []
  if (options.preserveSelection && previousTicketId) {
    const exists = tickets.value.some((item) => item.id === previousTicketId)
    if (exists) {
      return
    }
  }
  await ensureActiveTicket()
}

const submitTicket = async () => {
  const { data } = await api.post('/auth/support/tickets/', {
    subject: ticketModal.subject,
    message: ticketModal.description
  })
  activeStatusTab.value = 'open'
  closeCreateTicketModal()
  await loadTickets({ preserveSelection: true })
  await openTicketDetail(data.id)
}

watch(activeStatusTab, async () => {
  await ensureActiveTicket()
})

watch(searchQuery, async () => {
  await ensureActiveTicket()
})

onMounted(async () => {
  await loadTickets()
})
</script>

<style scoped>
.support-content {
  display: grid;
}

.tickets-shell {
  min-height: calc(100vh - 124px);
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: 18px;
  padding: 22px;
  border-radius: 28px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.12), transparent 28%),
    linear-gradient(180deg, #f8fbff 0%, #edf3f9 100%);
  border: 1px solid #dbe4ef;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.tickets-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.tickets-head-copy {
  display: grid;
  gap: 6px;
}

.tickets-head h1 {
  margin: 0;
  font-size: 28px;
  color: #0f172a;
  font-weight: 800;
}

.tickets-head p {
  margin: 0;
  color: #5b6b80;
  font-size: 14px;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-btn {
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.85);
  color: #385071;
  display: grid;
  place-items: center;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px #d9e2ee;
}

.icon-btn svg {
  width: 18px;
  height: 18px;
}

.status-track {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.status-node {
  position: relative;
  border: 0;
  border-radius: 18px;
  padding: 12px 10px;
  cursor: pointer;
  display: grid;
  justify-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.7);
  box-shadow: inset 0 0 0 1px #dde6f1;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.status-node:hover,
.status-node.active {
  transform: translateY(-1px);
  background: #ffffff;
  box-shadow: 0 14px 30px rgba(29, 78, 216, 0.12), inset 0 0 0 1px #cfe0ff;
}

.status-icon {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #64748b;
  background: #dae2ee;
}

.status-icon svg {
  width: 20px;
  height: 20px;
}

.status-icon.open { background: #dbeafe; color: #1d4ed8; }
.status-icon.in-progress { background: #fef3c7; color: #b45309; }
.status-icon.resolved { background: #dcfce7; color: #166534; }
.status-icon.closed { background: #e2e8f0; color: #475569; }
.status-count {
  font-size: 12px;
  color: #475569;
  background: #dbe5f3;
  border-radius: 999px;
  padding: 1px 8px;
}

.status-label {
  font-size: 13px;
  color: #334155;
  font-weight: 700;
}

.status-line {
  position: absolute;
  top: 31px;
  left: -10px;
  width: 18px;
  height: 2px;
  background: #c6d1df;
}

.support-board {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  gap: 18px;
}

.tickets-list-panel,
.chat-panel {
  min-height: 0;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #dde6f1;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.06);
}

.tickets-list-panel {
  display: grid;
  grid-template-rows: auto 1fr;
}

.list-panel-head {
  padding: 16px 18px;
  border-bottom: 1px solid #e7edf5;
  background: linear-gradient(180deg, #fdfefe 0%, #f5f9ff 100%);
}

.list-panel-head strong {
  display: block;
  color: #0f172a;
  font-size: 15px;
}

.list-panel-head small {
  color: #64748b;
}

.tickets-list {
  min-height: 0;
  overflow: auto;
  display: grid;
  align-content: start;
}

.ticket-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 16px 18px;
  border-bottom: 1px solid #edf2f7;
  cursor: pointer;
  transition: background 0.18s ease, transform 0.18s ease;
}

.ticket-row:hover {
  background: #f8fbff;
}

.ticket-row.selected {
  background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
  box-shadow: inset 3px 0 0 #2563eb;
}

.ticket-row-main {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.ticket-row-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ticket-row-top strong {
  color: #0f172a;
  font-size: 14px;
}

.ticket-row-main p {
  margin: 0;
  color: #526173;
  font-size: 13px;
  line-height: 1.8;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ticket-row-meta,
.ticket-row-side {
  display: grid;
  gap: 6px;
}

.ticket-row-meta {
  color: #64748b;
  font-size: 12px;
}

.ticket-row-side {
  justify-items: end;
  color: #64748b;
  font-size: 12px;
}

.message-count {
  padding: 5px 9px;
  border-radius: 999px;
  background: #eef4fb;
  color: #31527e;
  font-weight: 700;
}

.chat-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto auto;
}

.chat-loading,
.empty-chat-state {
  min-height: 100%;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  padding: 32px;
  color: #5a6a7f;
}

.empty-chat-visual {
  width: 96px;
  height: 96px;
  color: #2563eb;
}

.empty-chat-visual svg {
  width: 100%;
  height: 100%;
}

.empty-chat-state h2 {
  margin: 0;
  color: #0f172a;
}

.empty-chat-state p {
  margin: 0;
  max-width: 460px;
  text-align: center;
  line-height: 1.9;
}

.chat-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 22px 24px 18px;
  border-bottom: 1px solid #e8eef5;
  background:
    radial-gradient(circle at top left, rgba(14, 165, 233, 0.12), transparent 26%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.chat-head-copy {
  display: grid;
  gap: 8px;
}

.chat-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.chat-title-row h2 {
  margin: 0;
  color: #0f172a;
  font-size: 22px;
}

.chat-head-copy p {
  margin: 0;
  color: #5a6a7e;
  line-height: 1.9;
}

.chat-head-id {
  color: #2563eb;
}

.chat-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding: 16px 24px 0;
}

.summary-card {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: 18px;
  background: #f8fbff;
  border: 1px solid #dfebf7;
}

.summary-card span {
  color: #64748b;
  font-size: 12px;
}

.summary-card strong {
  color: #0f172a;
  font-size: 14px;
}

.summary-card small {
  color: #5b6b80;
}

.message-thread {
  min-height: 0;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 14px;
  padding: 22px 24px;
  background:
    linear-gradient(180deg, rgba(248, 251, 255, 0.65), rgba(255, 255, 255, 0.96)),
    repeating-linear-gradient(
      0deg,
      transparent 0,
      transparent 31px,
      rgba(219, 234, 254, 0.22) 31px,
      rgba(219, 234, 254, 0.22) 32px
    );
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
  width: min(72%, 640px);
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 22px;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.06);
}

.message-bubble.support {
  background: #ffffff;
  border: 1px solid #dde7f2;
  border-top-right-radius: 8px;
}

.message-bubble.tenant {
  background: linear-gradient(135deg, #0f5ed7 0%, #0f766e 100%);
  color: #ffffff;
  border-top-left-radius: 8px;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.message-meta strong {
  color: inherit;
  font-size: 13px;
}

.sender-tag {
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.sender-tag.support {
  background: #e8f1ff;
  color: #1d4ed8;
}

.sender-tag.tenant {
  background: rgba(255, 255, 255, 0.18);
  color: #ffffff;
}

.message-bubble p {
  margin: 0;
  line-height: 2;
  color: inherit;
}

.message-bubble small {
  color: inherit;
  opacity: 0.8;
}

.reply-shell,
.rating-box {
  margin: 0 24px 18px;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid #dde7f1;
  background: #ffffff;
}

.reply-head {
  display: grid;
  gap: 4px;
  margin-bottom: 12px;
}

.reply-head strong {
  color: #0f172a;
}

.reply-head small {
  color: #64748b;
}

.reply-form {
  display: grid;
  gap: 10px;
}

.reply-form textarea,
.rating-box textarea,
.modal-form input,
.modal-form textarea {
  width: 100%;
  border: 1px solid #cdd8e5;
  border-radius: 14px;
  padding: 12px 14px;
  font: inherit;
  background: #fbfdff;
  resize: vertical;
}

.reply-form textarea:disabled {
  background: #f1f5f9;
}

.reply-actions,
.rating-actions,
.modal-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.hint {
  color: #64748b;
  font-size: 12px;
}

.rating-box {
  display: grid;
  gap: 10px;
}

.rating-box-static p {
  margin: 0;
  color: #475569;
}

.rating-stars {
  display: flex;
  gap: 6px;
}

.rating-star-btn {
  border: 0;
  background: transparent;
  color: #cbd5e1;
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.rating-star-btn.active {
  color: #f59e0b;
}

.rating-static {
  color: #0f172a;
  font-weight: 800;
  font-size: 18px;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-weight: 700;
}

.status-pill {
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  display: inline-block;
  white-space: nowrap;
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

.empty-state {
  min-height: 340px;
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 10px;
  color: #64748b;
  padding: 18px;
}

.list-empty {
  min-height: 100%;
}

.empty-icon {
  width: 96px;
  height: 96px;
  color: #1d4ed8;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.empty-state h2 {
  margin: 0;
  color: #2563eb;
  font-size: 28px;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.new-ticket-btn {
  border: 0;
  border-radius: 14px;
  background: linear-gradient(90deg, #0f5ed7, #2563eb);
  color: #fff;
  font-weight: 700;
  height: 46px;
  padding: 0 26px;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.28);
}

.new-ticket-btn.compact {
  height: 38px;
  padding: 0 16px;
  border-radius: 12px;
  box-shadow: none;
}

.primary-btn,
.secondary-btn {
  border: 0;
  border-radius: 12px;
  padding: 11px 16px;
  cursor: pointer;
  font-weight: 700;
}

.primary-btn {
  background: linear-gradient(90deg, #0058be, #00687a);
  color: #fff;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-btn {
  background: #e2e8f0;
  color: #334155;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  z-index: 90;
}

.modal-panel {
  width: min(740px, 100%);
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  overflow: hidden;
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 18px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fbff;
}

.modal-head h3 {
  margin: 0;
  color: #0f172a;
}

.close-btn {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 9px;
  background: #e2e8f0;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
}

.modal-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 16px;
}

.modal-form label {
  display: grid;
  gap: 6px;
}

.modal-form label span {
  font-weight: 700;
  color: #334155;
  font-size: 13px;
}

.modal-form .full {
  grid-column: 1 / -1;
}

@media (max-width: 1280px) {
  .support-board {
    grid-template-columns: 340px minmax(0, 1fr);
  }

  .chat-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .support-board {
    grid-template-columns: 1fr;
  }

  .chat-panel {
    min-height: 720px;
  }
}

@media (max-width: 800px) {
  .tickets-shell {
    padding: 16px;
  }

  .tickets-head {
    display: grid;
  }

  .status-track {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .status-line {
    display: none;
  }

  .chat-head,
  .ticket-row {
    grid-template-columns: 1fr;
  }

  .chat-summary-grid {
    grid-template-columns: 1fr;
  }

  .message-bubble {
    width: min(90%, 100%);
  }

  .modal-form {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .head-actions {
    flex-wrap: wrap;
  }

  .ticket-row {
    padding: 14px;
  }

  .chat-head,
  .message-thread,
  .reply-shell,
  .rating-box {
    padding-left: 16px;
    padding-right: 16px;
    margin-left: 16px;
    margin-right: 16px;
  }

  .chat-head {
    margin: 0;
    padding-top: 18px;
    padding-bottom: 16px;
  }

  .reply-actions,
  .rating-actions,
  .modal-actions {
    display: grid;
    justify-content: stretch;
  }
}
</style>
