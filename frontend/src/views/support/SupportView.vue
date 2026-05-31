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
            <h1>تیکت های من</h1>
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
              <span class="status-icon" :class="item.key">
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

          <section class="tickets-table-wrap">
            <header class="table-head">
              <span>عنوان</span>
              <span>شناسه</span>
              <span>وضعیت</span>
              <span>عملیات</span>
            </header>

            <div v-if="filteredTickets.length" class="table-body">
              <article v-for="ticket in filteredTickets" :key="ticket.id" class="ticket-row">
                <div class="ticket-col subject-col">
                  <strong>{{ ticket.subject }}</strong>
                  <small>{{ ticket.requester }}</small>
                </div>
                <div class="ticket-col mono">{{ ticket.id }}</div>
                <div class="ticket-col">
                  <span class="status-pill" :class="statusClass(ticket.status)">{{ statusLabel(ticket.status) }}</span>
                </div>
                <div class="ticket-col actions-col">
                  <button class="row-btn" type="button" @click="quickClose(ticket)">بستن</button>
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
              <h2>همه چی آرومه</h2>
              <p>در حال حاضر هیچ تیکت فعالی ندارید</p>
              <button class="new-ticket-btn" type="button" @click="openCreateTicketModal">+ نوشتن تیکت</button>
            </div>
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
          <label>
            <span>درخواست‌کننده</span>
            <input v-model.trim="ticketModal.requester" required placeholder="نام شخص یا واحد" />
          </label>
          <label>
            <span>اولویت</span>
            <select v-model="ticketModal.priority">
              <option value="low">کم</option>
              <option value="medium">متوسط</option>
              <option value="high">بالا</option>
              <option value="critical">بحرانی</option>
            </select>
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
import { computed, reactive, ref } from 'vue'
import { useAuthStore } from '../../store/auth.store'
import AppShell from '../../components/layout/AppShell.vue'

const authStore = useAuthStore()


const searchQuery = ref('')
const activeStatusTab = ref('all')

const tickets = ref([])

const statusCount = computed(() => tickets.value.reduce((acc, item) => {
  if (acc[item.status] === undefined) acc[item.status] = 0
  acc[item.status] += 1
  return acc
}, { open: 0, in_progress: 0, resolved: 0, closed: 0 }))

const statusTrack = computed(() => [
  { key: 'all', label: 'تیکت های باز', count: statusCount.value.open },
  { key: 'in_progress', label: 'در حال بررسی', count: statusCount.value.in_progress },
  { key: 'resolved', label: 'پاسخ داده شده', count: statusCount.value.resolved },
  { key: 'closed', label: 'بسته شده', count: statusCount.value.closed }
])

const filteredTickets = computed(() => {
  const query = searchQuery.value.trim()
  return tickets.value.filter((item) => {
    if (activeStatusTab.value === 'all') {
      if (item.status !== 'open') return false
    } else if (item.status !== activeStatusTab.value) {
      return false
    }

    if (!query) return true

    const haystack = `${item.id} ${item.subject} ${item.requester}`.toLowerCase()
    return haystack.includes(query.toLowerCase())
  })
})

const ticketModal = reactive({
  open: false,
  subject: '',
  requester: authStore.user?.full_name || authStore.user?.username || '',
  priority: 'medium',
  description: ''
})

const toFa = (value) => Number(value || 0).toLocaleString('fa-IR')

const statusLabel = (value) => ({
  open: 'باز',
  in_progress: 'در حال بررسی',
  resolved: 'پاسخ داده شده',
  closed: 'بسته شده'
}[value] || 'باز')

const statusClass = (value) => ({
  open: 'open',
  in_progress: 'in-progress',
  resolved: 'resolved',
  closed: 'closed'
}[value] || 'open')

const focusSearch = () => {
  const element = document.querySelector('.search-box input')
  if (element) element.focus()
}

const toggleStatusFilter = () => {
  const order = ['all', 'in_progress', 'resolved', 'closed']
  const currentIndex = order.findIndex((item) => item === activeStatusTab.value)
  activeStatusTab.value = order[(currentIndex + 1) % order.length]
}

const openCreateTicketModal = () => {
  ticketModal.open = true
}

const closeCreateTicketModal = () => {
  ticketModal.open = false
  ticketModal.subject = ''
  ticketModal.priority = 'medium'
  ticketModal.description = ''
}

const submitTicket = () => {
  const maxId = tickets.value
    .map((item) => Number((item.id || '').split('-')[1]))
    .filter((item) => Number.isFinite(item))
    .reduce((max, item) => Math.max(max, item), 1000)

  tickets.value.unshift({
    id: `SUP-${maxId + 1}`,
    subject: ticketModal.subject,
    requester: ticketModal.requester || (authStore.user?.full_name || authStore.user?.username || 'کاربر سیستم'),
    priority: ticketModal.priority,
    status: 'open',
    description: ticketModal.description,
    createdAt: new Date()
  })

  activeStatusTab.value = 'all'
  closeCreateTicketModal()
}

const quickClose = (ticket) => {
  ticket.status = 'closed'
}

</script>

<style scoped>
.support-content { display: grid; }

.tickets-shell {
  background: #eef2f7;
  border: 1px solid #dde5ef;
  border-radius: 20px;
  padding: 18px;
  min-height: calc(100vh - 124px);
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: 18px;
}

.tickets-head { display: flex; justify-content: space-between; align-items: center; }
.tickets-head h1 { margin: 0; font-size: 22px; color: #334155; font-weight: 700; }
.head-actions { display: flex; gap: 8px; }
.icon-btn {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 10px;
  background: #dde5ef;
  color: #475569;
  display: grid;
  place-items: center;
  cursor: pointer;
}
.icon-btn svg { width: 18px; height: 18px; }

.status-track {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.status-node {
  position: relative;
  border: 0;
  background: transparent;
  border-radius: 14px;
  padding: 10px 8px;
  cursor: pointer;
  display: grid;
  justify-items: center;
  gap: 5px;
}

.status-node.active {
  background: #e9f2ff;
}

.status-icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #64748b;
  background: #dae2ee;
}

.status-icon svg { width: 20px; height: 20px; }
.status-icon.all,
.status-node.active .status-icon { background: #1d4ed8; color: #fff; }
.status-icon.in_progress { background: #dbeafe; color: #1d4ed8; }
.status-icon.resolved { background: #dcfce7; color: #166534; }
.status-icon.closed { background: #e2e8f0; color: #475569; }
.status-count { font-size: 12px; color: #475569; background: #dbe5f3; border-radius: 999px; padding: 1px 8px; }
.status-label { font-size: 13px; color: #334155; font-weight: 600; }
.status-line {
  position: absolute;
  top: 28px;
  left: -8px;
  width: 16px;
  height: 2px;
  background: #c6d1df;
}

.tickets-table-wrap {
  border: 1px solid #dde5ef;
  border-radius: 16px;
  background: #f8fafd;
  overflow: hidden;
  display: grid;
  grid-template-rows: auto 1fr;
}

.table-head {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 8px;
  padding: 11px 14px;
  color: #64748b;
  font-size: 12px;
  border-bottom: 1px solid #dde5ef;
}

.table-body { display: grid; }
.ticket-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 8px;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #e5ebf3;
  background: #fff;
}
.ticket-row:last-child { border-bottom: 0; }
.ticket-col { font-size: 13px; color: #334155; }
.subject-col { display: grid; gap: 2px; }
.subject-col strong { color: #0f172a; }
.subject-col small { color: #64748b; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-weight: 700; color: #1d4ed8; }
.status-pill { padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; display: inline-block; }
.status-pill.open { background: #e2e8f0; color: #334155; }
.status-pill.in-progress { background: #dbeafe; color: #1d4ed8; }
.status-pill.resolved { background: #dcfce7; color: #166534; }
.status-pill.closed { background: #f1f5f9; color: #475569; }
.actions-col { display: flex; justify-content: flex-start; }
.row-btn { border: 0; border-radius: 9px; padding: 7px 10px; background: #fee2e2; color: #b91c1c; font-weight: 700; cursor: pointer; }

.empty-state {
  min-height: 340px;
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 10px;
  color: #64748b;
}
.empty-icon { width: 96px; height: 96px; color: #1d4ed8; }
.empty-icon svg { width: 100%; height: 100%; }
.empty-state h2 { margin: 0; color: #2563eb; font-size: 28px; }
.empty-state p { margin: 0; font-size: 14px; }
.new-ticket-btn {
  margin-top: 4px;
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

.modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.42); display: flex; align-items: center; justify-content: center; padding: 18px; z-index: 90; }
.modal-panel { width: min(740px, 100%); background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid #e2e8f0; background: #f8fbff; }
.modal-head h3 { margin: 0; color: #0f172a; }
.close-btn { width: 34px; height: 34px; border: 0; border-radius: 9px; background: #e2e8f0; cursor: pointer; font-size: 20px; line-height: 1; }
.modal-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; padding: 14px; }
.modal-form label { display: grid; gap: 6px; }
.modal-form label span { font-weight: 700; color: #334155; font-size: 13px; }
.modal-form input, .modal-form select, .modal-form textarea { border: 1px solid #cbd5e1; border-radius: 10px; padding: 8px 10px; font: inherit; background: #fff; }
.modal-form input, .modal-form select { height: 42px; }
.modal-form .full { grid-column: 1 / -1; }
.modal-actions { grid-column: 1 / -1; display: flex; justify-content: flex-end; gap: 8px; }
.primary-btn, .secondary-btn { border: 0; border-radius: 10px; padding: 9px 13px; cursor: pointer; font-weight: 700; }
.primary-btn { background: linear-gradient(90deg, #0058be, #00687a); color: #fff; }
.secondary-btn { background: #e2e8f0; color: #334155; }

@media (max-width: 1100px) {
}

@media (max-width: 800px) {
  .status-track { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .status-line { display: none; }
  .table-head, .ticket-row { grid-template-columns: 2fr 1.2fr 1.3fr 1fr; }
  .modal-form { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .tickets-shell { padding: 14px; }
  .table-head { display: none; }
  .ticket-row {
    grid-template-columns: 1fr;
    gap: 7px;
    padding: 12px;
  }
  .actions-col { justify-content: flex-end; }
}
</style>


