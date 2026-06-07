<template>
  <section class="wallet-page" dir="rtl">
    <div v-if="state.error" class="wallet-alert wallet-alert-error">{{ state.error }}</div>
    <div v-if="state.successMessage" class="wallet-alert wallet-alert-success">{{ state.successMessage }}</div>

    <section class="wallet-hero-shell">
      <aside class="wallet-shortcuts">
        <div class="shortcut-head">
          <h3>دسترسی سریع</h3>
          <p>مدیریت سریع عملیات مالی</p>
        </div>
        <div class="shortcut-grid">
          <button class="shortcut-card shortcut-primary" type="button" @click="openActionModal('deposit')">
            <span class="shortcut-icon">+</span>
            <strong>شارژ حساب</strong>
            <small>ورود به درگاه پرداخت</small>
          </button>
          <button v-if="!activeWalletIsSms" class="shortcut-card" type="button" @click="openActionModal('withdraw')">
            <span class="shortcut-icon">↗</span>
            <strong>برداشت وجه</strong>
            <small>ثبت برداشت داخلی</small>
          </button>
          <button class="shortcut-card" type="button" @click="setFilter('deposit')">
            <span class="shortcut-icon">↓</span>
            <strong>واریزی‌ها</strong>
            <small>{{ moneyWithUnit(state.summary.deposits_total) }}</small>
          </button>
          <button class="shortcut-card" type="button" @click="setFilter('withdraw')">
            <span class="shortcut-icon">↑</span>
            <strong>برداشت‌ها</strong>
            <small>{{ moneyWithUnit(state.summary.withdrawals_total) }}</small>
          </button>
        </div>
      </aside>

      <section class="wallet-hero">
        <div class="hero-top">
          <div class="hero-badge">
            <span class="hero-icon">◫</span>
            <span>کیف پول هوشمند</span>
          </div>
          <div class="hero-status" :class="{ danger: regularLow || smsLow }">
            {{ regularLow || smsLow ? 'نیاز به شارژ' : 'وضعیت پایدار' }}
          </div>
        </div>

        <div class="hero-main">
          <div>
            <p class="hero-label">موجودی کل حساب</p>
            <h2>{{ money(totalBalance) }} <span>هزار تومان</span></h2>
            <p class="hero-sub">
              {{ selectedWalletId ? 'نمایش تراکنش‌های کیف پول انتخاب‌شده' : 'نمایش تجمیعی همه کیف‌پول‌ها' }}
            </p>
          </div>
          <div class="hero-orb"></div>
        </div>

        <div class="hero-actions">
          <button class="hero-action hero-action-light" type="button" @click="openActionModal('deposit')">
            شارژ حساب / واریز
          </button>
          <button
            v-if="!activeWalletIsSms"
            class="hero-action hero-action-ghost"
            type="button"
            @click="openActionModal('withdraw')"
          >
            برداشت وجه
          </button>
        </div>
      </section>
    </section>

    <section class="wallet-summary-board">
      <article class="summary-tile">
        <small>موجودی عادی</small>
        <strong :class="{ danger: regularLow }">{{ money(state.summary.regular_balance) }}</strong>
        <span>هزار تومان</span>
      </article>
      <article class="summary-tile sms-tile">
        <small>موجودی پیامک</small>
        <strong :class="{ danger: smsLow }">{{ money(state.summary.sms_balance) }}</strong>
        <span>هزار تومان</span>
      </article>
      <article class="summary-tile accent-tile">
        <small>جمع واریزی‌ها</small>
        <strong>{{ money(state.summary.deposits_total) }}</strong>
        <span>هزار تومان</span>
      </article>
      <article class="summary-tile soft-tile">
        <small>جمع برداشت‌ها</small>
        <strong>{{ money(state.summary.withdrawals_total) }}</strong>
        <span>هزار تومان</span>
      </article>
    </section>

    <section v-if="regularLow || smsLow" class="warning-strip">
      <span class="warning-dot"></span>
      <strong>{{ regularLow && smsLow ? 'موجودی عادی و شارژ پیامک کم است.' : regularLow ? 'موجودی عادی کم است.' : 'شارژ پیامک کم است.' }}</strong>
    </section>

    <section class="history-panel">
      <header class="history-head">
        <div class="history-title-wrap">
          <p>گردش مالی</p>
          <h2>تاریخچه تراکنش‌ها</h2>
        </div>
        <div class="history-controls">
          <div class="filter-pill" role="tablist" aria-label="فیلتر تراکنش">
            <button type="button" :class="{ active: state.filterType === 'all' }" @click="setFilter('all')">همه</button>
            <button type="button" :class="{ active: state.filterType === 'deposit' }" @click="setFilter('deposit')">واریزی‌ها</button>
            <button type="button" :class="{ active: state.filterType === 'withdraw' }" @click="setFilter('withdraw')">برداشت‌ها</button>
          </div>
          <select v-model.number="selectedWalletId" class="wallet-switch">
            <option :value="0">همه کیف‌پول‌ها</option>
            <option v-for="wallet in state.wallets" :key="wallet.id" :value="wallet.id">{{ wallet.name }}</option>
          </select>
          <button class="refresh-btn" type="button" :disabled="state.loading" @click="loadWalletDashboard">
            {{ state.loading ? 'در حال بروزرسانی...' : 'بروزرسانی' }}
          </button>
        </div>
      </header>

      <div v-if="state.loading" class="history-state">
        <BaseSpinner size="62px" color="#0f5cc0" ball-color="#5fb7ff" label="در حال بارگذاری اطلاعات کیف پول..." />
      </div>
      <div v-else-if="!filteredTransactions.length" class="history-state">تراکنشی برای نمایش وجود ندارد.</div>

      <div v-else class="tx-list">
        <article v-for="tx in filteredTransactions" :key="tx.id" class="tx-item">
          <button class="tx-expand" type="button">‹</button>

          <div class="tx-main">
            <div class="tx-title-row">
              <h3>{{ txTitle(tx) }}</h3>
              <span class="tx-chip" :class="tx.direction === 'in' ? 'tx-chip-in' : 'tx-chip-out'">
                {{ tx.direction === 'in' ? 'موفقیت‌آمیز' : 'ثبت‌شده' }}
              </span>
            </div>
            <p class="tx-meta">
              <span>{{ formatDateTime(tx.transacted_at) }}</span>
              <span class="separate">•</span>
              <span>{{ tx.wallet_name || 'کیف پول اصلی' }}</span>
              <span v-if="tx.reference_id" class="separate">•</span>
              <span v-if="tx.reference_id">کد پیگیری #{{ tx.reference_id }}</span>
            </p>
          </div>

          <div class="tx-value-col">
            <strong class="tx-value" :class="tx.direction === 'in' ? 'tx-value-in' : 'tx-value-out'">
              {{ tx.direction === 'in' ? '+' : '-' }}{{ money(tx.amount) }} هزار تومان
            </strong>
            <div class="tx-icon-box" :class="tx.direction === 'in' ? 'tx-icon-box-in' : 'tx-icon-box-out'">
              {{ tx.direction === 'in' ? '↓' : '↑' }}
            </div>
          </div>
        </article>
      </div>
    </section>

    <div v-if="actionModal.open" class="wallet-modal-overlay" @click.self="closeActionModal">
      <section class="wallet-modal" :class="actionModal.type === 'deposit' ? 'wallet-modal-deposit' : 'wallet-modal-withdraw'">
        <header class="wallet-modal-head">
          <div class="wallet-modal-title-wrap">
            <p>{{ actionModal.type === 'deposit' ? 'افزایش موجودی از طریق درگاه' : 'ثبت برداشت داخلی' }}</p>
            <h3>{{ actionModalTitle }}</h3>
          </div>
          <button class="close-btn" type="button" @click="closeActionModal">×</button>
        </header>

        <div class="wallet-modal-body">
          <div class="wallet-modal-highlight" v-if="activeWallet">
            <div>
              <small>موجودی فعلی</small>
              <strong>{{ money(activeWallet.balance) }} هزار تومان</strong>
            </div>
            <span class="wallet-modal-highlight-badge">
              {{ actionModal.type === 'deposit' ? 'شارژ' : 'برداشت' }}
            </span>
          </div>

          <label>
            <span>انتخاب کیف پول</span>
            <select v-model.number="actionModal.walletId">
              <option
                v-for="wallet in selectableWallets"
                :key="wallet.id"
                :value="wallet.id"
              >
                {{ wallet.name }} ({{ money(wallet.balance) }} هزار تومان)
              </option>
            </select>
          </label>

          <label>
            <span>{{ actionModal.type === 'deposit' ? 'مبلغ واریز (هزار تومان)' : 'مبلغ (هزار تومان)' }}</span>
            <input
              v-if="actionModal.type === 'withdraw'"
              v-model="actionModal.amountText"
              type="text"
              inputmode="numeric"
              placeholder="مثلاً 500"
            />
            <div v-else class="gateway-amounts">
              <button type="button" :class="{ active: selectedDepositAmount === 1000000 }" @click="setQuickAmount(1000000)">
                <strong>1,000</strong>
                <span>هزار تومان</span>
              </button>
              <button type="button" :class="{ active: selectedDepositAmount === 2000000 }" @click="setQuickAmount(2000000)">
                <strong>2,000</strong>
                <span>هزار تومان</span>
              </button>
              <button type="button" :class="{ active: selectedDepositAmount === 3000000 }" @click="setQuickAmount(3000000)">
                <strong>3,000</strong>
                <span>هزار تومان</span>
              </button>
            </div>
          </label>

          <div v-if="actionModal.type === 'withdraw'" class="quick-amounts">
            <button type="button" @click="setQuickAmount(100000)">100 هزار تومان</button>
            <button type="button" @click="setQuickAmount(500000)">500 هزار تومان</button>
            <button type="button" @click="setQuickAmount(1000000)">1,000 هزار تومان</button>
          </div>

          <label>
            <span>شرح</span>
            <input v-model="actionModal.description" type="text" :placeholder="actionModal.type === 'deposit' ? 'مثلاً شارژ صندوق' : 'مثلاً هزینه جاری'" />
          </label>

          <div class="wallet-note">
            {{ actionModal.type === 'deposit' ? 'بعد از انتخاب مبلغ، به درگاه پرداخت منتقل می‌شوید.' : 'برداشت بلافاصله از موجودی کیف پول کسر می‌شود.' }}
          </div>

          <button class="submit-btn" :class="actionModal.type === 'deposit' ? 'submit-deposit' : 'submit-withdraw'" type="button" :disabled="actionModal.submitting" @click="submitAction">
            {{ actionModal.submitting ? 'در حال ثبت...' : actionModalSubmitLabel }}
          </button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import api from '../../services/api'
import BaseSpinner from '../base/BaseSpinner.vue'
import { formatThousandsToman, formatThousandsTomanValue, fromThousandsTomanInput } from '../../utils/money'

const props = defineProps({
  searchQuery: { type: String, default: '' }
})

const state = reactive({
  loading: false,
  error: '',
  successMessage: '',
  filterType: 'all',
  summary: {
    total_balance: 0,
    regular_balance: 0,
    sms_balance: 0,
    deposits_total: 0,
    withdrawals_total: 0
  },
  wallets: [],
  transactions: []
})

const actionModal = reactive({
  open: false,
  type: 'deposit',
  walletId: null,
  amountText: '',
  description: '',
  submitting: false
})

const selectedWalletId = ref(0)
const selectedDepositAmount = ref(1000000)

const money = (value) => formatThousandsTomanValue(value)
const moneyWithUnit = (value) => formatThousandsToman(value)
const formatDateTime = (value) => value ? new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '-'
const txTitle = (tx) => tx?.description || (tx?.direction === 'in' ? 'واریز به کیف پول' : 'برداشت از کیف پول')
const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
  .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
  .replace(/[^\d]/g, '')
const parseAmount = (text) => fromThousandsTomanInput(normalizeDigits(text))

const regularLow = computed(() => Number(state.summary.regular_balance || 0) <= 100000)
const smsLow = computed(() => Number(state.summary.sms_balance || 0) <= 50000)
const totalBalance = computed(() => Number(state.summary.total_balance || 0))
const activeWallet = computed(() => state.wallets.find((wallet) => Number(wallet.id) === Number(actionModal.walletId)) || null)
const activeWalletIsSms = computed(() => activeWallet.value?.wallet_type === 'sms')
const selectableWallets = computed(() => (
  actionModal.type === 'withdraw'
    ? state.wallets.filter((wallet) => wallet.wallet_type !== 'sms')
    : state.wallets
))
const filteredTransactions = computed(() => {
  const walletId = Number(selectedWalletId.value || 0)
  if (!walletId) return state.transactions
  return state.transactions.filter((tx) => Number(tx.wallet) === walletId)
})
const actionModalTitle = computed(() => actionModal.type === 'deposit' ? 'ثبت واریز به کیف پول' : 'ثبت برداشت از کیف پول')
const actionModalSubmitLabel = computed(() => actionModal.type === 'deposit' ? 'تایید و ثبت واریز' : 'تایید و ثبت برداشت')

const resolveErrorMessage = (error, fallback) => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) return String(detail[0])
  return fallback
}

const clearMessages = () => {
  state.error = ''
  state.successMessage = ''
}

const applyGatewayResultMessage = () => {
  const params = new URLSearchParams(window.location.search)
  const gatewayState = params.get('gateway')
  if (!gatewayState) return
  if (gatewayState === 'success') state.successMessage = 'شارژ کیف پول با موفقیت انجام شد.'
  else if (gatewayState === 'cancelled') state.error = 'پرداخت شارژ کیف پول لغو شد.'
  else if (gatewayState === 'already-processed') state.error = 'این درخواست پرداخت قبلاً پردازش شده است.'
  params.delete('gateway')
  const nextQuery = params.toString()
  const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ''}${window.location.hash || ''}`
  window.history.replaceState({}, '', nextUrl)
}

const loadWalletDashboard = async () => {
  state.loading = true
  state.error = ''
  try {
    const { data } = await api.get('/payments/wallet/dashboard/', {
      params: { type: state.filterType, q: (props.searchQuery || '').trim() || undefined }
    })
    state.summary = {
      total_balance: Number(data?.summary?.total_balance || 0),
      regular_balance: Number(data?.summary?.regular_balance || 0),
      sms_balance: Number(data?.summary?.sms_balance || 0),
      deposits_total: Number(data?.summary?.deposits_total || 0),
      withdrawals_total: Number(data?.summary?.withdrawals_total ?? data?.summary?.payments_total ?? 0)
    }
    state.wallets = Array.isArray(data?.wallets) ? data.wallets : []
    state.transactions = Array.isArray(data?.transactions) ? data.transactions : []
    if ((!actionModal.walletId || !selectableWallets.value.some((wallet) => Number(wallet.id) === Number(actionModal.walletId))) && selectableWallets.value.length) {
      actionModal.walletId = Number(selectableWallets.value[0].id)
    }
  } catch (error) {
    state.error = resolveErrorMessage(error, 'بارگذاری کیف پول ناموفق بود.')
  } finally {
    state.loading = false
  }
}

const setFilter = async (type) => {
  if (state.filterType === type && !state.error) return
  state.filterType = type
  await loadWalletDashboard()
}

const openActionModal = (type) => {
  clearMessages()
  actionModal.open = true
  actionModal.type = type
  actionModal.amountText = ''
  actionModal.description = ''
  actionModal.submitting = false
  selectedDepositAmount.value = 1000000
  const wallets = type === 'withdraw' ? state.wallets.filter((wallet) => wallet.wallet_type !== 'sms') : state.wallets
  actionModal.walletId = wallets.length ? Number(wallets[0].id) : null
}

const closeActionModal = () => {
  actionModal.open = false
  actionModal.amountText = ''
  actionModal.description = ''
  actionModal.submitting = false
}

const setQuickAmount = (amount) => {
  if (actionModal.type === 'deposit') {
    selectedDepositAmount.value = Number(amount || 0)
    return
  }
  actionModal.amountText = money(amount)
}

const submitAction = async () => {
  clearMessages()
  if (!actionModal.walletId) {
    state.error = 'ابتدا یک کیف پول انتخاب کنید.'
    return
  }
  const amount = actionModal.type === 'deposit'
    ? Number(selectedDepositAmount.value || 0)
    : parseAmount(actionModal.amountText)
  if (amount <= 0) {
    state.error = 'مبلغ باید بزرگ‌تر از صفر باشد.'
    return
  }

  actionModal.submitting = true
  try {
    const endpoint = actionModal.type === 'deposit' ? '/payments/wallet/deposit/start/' : '/payments/wallet/withdraw/'
    const payload = {
      wallet_id: actionModal.walletId,
      amount,
      description: (actionModal.description || '').trim() || undefined
    }
    if (actionModal.type === 'deposit') payload.return_url = `${window.location.origin}/manager/wallet`
    const { data } = await api.post(endpoint, payload)
    if (actionModal.type === 'deposit' && data?.payment_url) {
      window.location.href = data.payment_url
      return
    }
    state.successMessage = data?.detail || (actionModal.type === 'deposit' ? 'واریز ثبت شد.' : 'برداشت ثبت شد.')
    closeActionModal()
    await loadWalletDashboard()
  } catch (error) {
    state.error = resolveErrorMessage(error, 'ثبت تراکنش ناموفق بود.')
  } finally {
    actionModal.submitting = false
  }
}

watch(() => props.searchQuery, async () => {
  await loadWalletDashboard()
})

onMounted(async () => {
  applyGatewayResultMessage()
  await loadWalletDashboard()
})
</script>

<style scoped>
.wallet-page{
  --wallet-border:#d8e4f1;
  --wallet-panel:#ffffff;
  --wallet-panel-soft:#f6fbff;
  --wallet-text:#0f172a;
  --wallet-muted:#64748b;
  --wallet-primary:#0f5cc0;
  --wallet-primary-2:#16a3b7;
  --wallet-success:#0f766e;
  --wallet-danger:#dc2626;
  display:grid;
  gap:18px
}
.wallet-alert{border-radius:18px;padding:14px 16px;font-weight:700;border:1px solid transparent;box-shadow:0 16px 34px rgba(15,23,42,.05)}
.wallet-alert-error{background:#fff1f2;color:#9f1239;border-color:#fecdd3}
.wallet-alert-success{background:#ecfdf5;color:#166534;border-color:#bbf7d0}
.wallet-hero-shell{display:grid;grid-template-columns:370px minmax(0,1fr);gap:22px;align-items:stretch}
.wallet-shortcuts{background:linear-gradient(180deg,#ffffff 0%,#f7fbff 100%);border:1px solid var(--wallet-border);border-radius:34px;padding:24px;box-shadow:0 22px 56px rgba(15,23,42,.07);position:relative;overflow:hidden}
.wallet-shortcuts::before{content:'';position:absolute;inset:-90px auto auto -80px;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,rgba(59,130,246,.12),rgba(59,130,246,0) 70%)}
.shortcut-head{position:relative;z-index:1}
.shortcut-head h3{margin:0;color:var(--wallet-text);font-size:20px}
.shortcut-head p{margin:8px 0 0;color:var(--wallet-muted);font-size:13px}
.shortcut-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:22px}
.shortcut-card{border:1px solid #e2e8f0;border-radius:24px;padding:18px 16px;background:linear-gradient(180deg,#fbfdff,#f1f6fb);display:grid;gap:10px;text-align:right;cursor:pointer;transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease;position:relative;z-index:1}
.shortcut-card:hover{transform:translateY(-3px);box-shadow:0 18px 38px rgba(15,23,42,.08);border-color:#bfd7ff}
.shortcut-primary{background:linear-gradient(135deg,#0d5ec6,#1485d6 60%,#16a3b7);color:#fff;border-color:transparent}
.shortcut-primary strong,.shortcut-primary small,.shortcut-primary .shortcut-icon{color:#fff}
.shortcut-icon{width:46px;height:46px;border-radius:16px;background:#eef5ff;color:#0f5cc0;display:inline-flex;align-items:center;justify-content:center;font-size:24px;font-weight:900;box-shadow:inset 0 1px 0 rgba(255,255,255,.7)}
.shortcut-card strong{font-size:18px;color:var(--wallet-text)}
.shortcut-card small{color:var(--wallet-muted);font-size:12px}
.wallet-hero{position:relative;overflow:hidden;border-radius:38px;padding:28px 34px;background:linear-gradient(135deg,#0c63bf 0%,#116abf 38%,#138fb0 100%);box-shadow:0 28px 70px rgba(15,92,192,.24);display:grid;gap:28px;min-height:320px;border:1px solid rgba(255,255,255,.18)}
.wallet-hero::before{content:'';position:absolute;inset:auto auto -120px -80px;width:280px;height:280px;border-radius:50%;background:rgba(255,255,255,.08);filter:blur(8px)}
.wallet-hero::after{content:'';position:absolute;top:-70px;left:22%;width:240px;height:240px;border-radius:50%;background:rgba(255,255,255,.06)}
.hero-top,.hero-main,.hero-actions{position:relative;z-index:1}
.hero-top{display:flex;justify-content:space-between;align-items:center;gap:16px}
.hero-badge{display:inline-flex;align-items:center;gap:10px;color:#e0f2fe;font-weight:700}
.hero-icon{width:48px;height:48px;border-radius:18px;background:rgba(255,255,255,.14);display:inline-flex;align-items:center;justify-content:center;font-size:26px}
.hero-status{padding:8px 14px;border-radius:999px;background:rgba(255,255,255,.14);color:#eff6ff;font-weight:800;font-size:12px}
.hero-status.danger{background:rgba(127,29,29,.22);color:#fee2e2}
.hero-main{display:flex;justify-content:space-between;align-items:flex-start;gap:20px}
.hero-label{margin:0;color:#dbeafe;font-size:16px}
.hero-main h2{margin:12px 0 10px;color:#fff;font-size:58px;line-height:1;font-weight:900}
.hero-main h2 span{font-size:28px;font-weight:800}
.hero-sub{margin:0;color:#d9efff;font-size:14px}
.hero-orb{width:180px;height:180px;border-radius:50%;background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.52),rgba(255,255,255,.05) 58%,rgba(255,255,255,0) 72%)}
.hero-actions{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin-top:auto}
.hero-action{height:72px;min-width:280px;border-radius:26px;border:0;font-size:28px;font-weight:900;cursor:pointer;padding:0 28px;transition:transform .2s ease,box-shadow .2s ease,background .2s ease}
.hero-action:hover{transform:translateY(-2px)}
.hero-action-light{background:#fff;color:#0f5cc0;box-shadow:0 18px 40px rgba(15,23,42,.18)}
.hero-action-ghost{background:rgba(255,255,255,.08);color:#fff;border:1px solid rgba(255,255,255,.2);backdrop-filter:blur(10px)}
.wallet-summary-board{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.summary-tile{background:linear-gradient(180deg,#ffffff,#f8fbff);border:1px solid var(--wallet-border);border-radius:24px;padding:18px 20px;box-shadow:0 14px 34px rgba(15,23,42,.05);position:relative;overflow:hidden}
.summary-tile::before{content:'';position:absolute;top:0;right:0;left:0;height:4px;background:linear-gradient(90deg,#60a5fa,#38bdf8)}
.summary-tile small{display:block;color:#64748b;font-size:12px}
.summary-tile strong{display:block;margin-top:12px;color:#0f172a;font-size:30px;line-height:1.15}
.summary-tile strong.danger{color:#b91c1c}
.summary-tile span{display:block;margin-top:6px;color:#94a3b8;font-size:12px}
.accent-tile{background:linear-gradient(135deg,#eff6ff,#e0f2fe)}
.soft-tile{background:linear-gradient(135deg,#fff7ed,#fff1f2)}
.sms-tile{background:linear-gradient(135deg,#f8fafc,#eef6ff)}
.warning-strip{display:flex;align-items:center;gap:12px;background:#fff7ed;border:1px solid #fdba74;border-radius:18px;padding:14px 16px;color:#c2410c}
.warning-dot{width:10px;height:10px;border-radius:50%;background:#f97316;box-shadow:0 0 0 6px rgba(249,115,22,.14)}
.history-panel{background:linear-gradient(180deg,#ffffff,#fbfdff);border:1px solid var(--wallet-border);border-radius:34px;padding:24px;box-shadow:0 18px 46px rgba(15,23,42,.06)}
.history-head{display:flex;justify-content:space-between;align-items:flex-end;gap:18px;margin-bottom:18px}
.history-title-wrap p{margin:0 0 8px;color:#94a3b8;font-size:13px;font-weight:700}
.history-head h2{margin:0;color:#0f172a;font-size:38px;line-height:1}
.history-controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.wallet-switch{height:44px;border:1px solid var(--wallet-border);border-radius:16px;padding:0 14px;background:#fff;color:#0f172a;box-shadow:inset 0 1px 2px rgba(15,23,42,.03)}
.filter-pill{display:flex;gap:4px;padding:5px;background:#eef3f8;border-radius:999px;border:1px solid #dde7f3}
.filter-pill button,.refresh-btn,.close-btn,.submit-btn,.quick-amounts button{border:0;cursor:pointer}
.filter-pill button{height:40px;padding:0 16px;border-radius:999px;background:transparent;color:#475569;font-weight:800}
.filter-pill button.active{background:#fff;color:#0f4aa8;box-shadow:0 10px 20px rgba(148,163,184,.16)}
.refresh-btn{height:44px;padding:0 18px;border-radius:16px;background:#eff6ff;color:#0f4aa8;font-weight:800;box-shadow:inset 0 1px 0 rgba(255,255,255,.65)}
.history-state{padding:42px 12px;text-align:center;color:#64748b}
.tx-list{display:grid;gap:16px}
.tx-item{display:grid;grid-template-columns:46px minmax(0,1fr) auto;align-items:center;gap:18px;padding:20px 22px;border:1px solid #e2e8f0;border-radius:28px;background:linear-gradient(180deg,#fff,#fcfdff);box-shadow:0 16px 34px rgba(15,23,42,.05);transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease}
.tx-item:hover{transform:translateY(-2px);box-shadow:0 22px 44px rgba(15,23,42,.08);border-color:#cdddf1}
.tx-expand{width:38px;height:38px;border:0;border-radius:50%;background:#f8fafc;color:#1e293b;font-size:34px;line-height:1;cursor:pointer}
.tx-title-row{display:flex;align-items:center;justify-content:space-between;gap:12px}
.tx-title-row h3{margin:0;color:#0f172a;font-size:17px}
.tx-chip{display:inline-flex;align-items:center;height:28px;padding:0 12px;border-radius:999px;font-size:11px;font-weight:800}
.tx-chip-in{background:#dcfce7;color:#166534}
.tx-chip-out{background:#fee2e2;color:#b91c1c}
.tx-meta{margin:10px 0 0;color:#94a3b8;font-size:13px;display:flex;gap:8px;flex-wrap:wrap}
.separate{color:#cbd5e1}
.tx-value-col{display:flex;align-items:center;gap:16px}
.tx-value{font-size:20px;font-weight:900;white-space:nowrap}
.tx-value-in{color:#0f766e}
.tx-value-out{color:#dc2626}
.tx-icon-box{width:68px;height:68px;border-radius:22px;display:inline-flex;align-items:center;justify-content:center;font-size:34px;font-weight:900}
.tx-icon-box-in{background:#dff2f0;color:#0f766e}
.tx-icon-box-out{background:#fde8e8;color:#dc2626}
.wallet-modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.52);backdrop-filter:blur(10px);display:flex;align-items:center;justify-content:center;z-index:120;padding:20px}
.wallet-modal{width:min(580px,100%);background:linear-gradient(180deg,#ffffff,#fdfefe);border-radius:30px;overflow:hidden;box-shadow:0 30px 80px rgba(15,23,42,.34);border:1px solid rgba(255,255,255,.8)}
.wallet-modal-deposit{--wallet-modal-accent:#0f766e;--wallet-modal-accent-soft:#ccfbf1;--wallet-modal-accent-bg:linear-gradient(135deg,#ecfeff,#f0fdfa)}
.wallet-modal-withdraw{--wallet-modal-accent:#dc2626;--wallet-modal-accent-soft:#fee2e2;--wallet-modal-accent-bg:linear-gradient(135deg,#fff7ed,#fff1f2)}
.wallet-modal-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding:22px 22px 18px;border-bottom:1px solid #e5edf6;background:linear-gradient(180deg,#ffffff,#f9fcff)}
.wallet-modal-title-wrap p{margin:0 0 6px;color:#64748b;font-size:12px;font-weight:800}
.wallet-modal-head h3{margin:0;font-size:21px;color:#0f172a}
.close-btn{width:42px;height:42px;border-radius:14px;background:#f1f5f9;color:#334155;font-size:22px;line-height:1;transition:background .2s ease,color .2s ease,transform .2s ease}
.close-btn:hover{background:#e2e8f0;color:#0f172a;transform:translateY(-1px)}
.wallet-modal-body{padding:22px;display:grid;gap:16px}
.wallet-modal-highlight{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:16px 18px;border-radius:22px;background:var(--wallet-modal-accent-bg);border:1px solid var(--wallet-modal-accent-soft)}
.wallet-modal-highlight small{display:block;color:#64748b;font-size:12px;margin-bottom:6px}
.wallet-modal-highlight strong{font-size:24px;color:#0f172a}
.wallet-modal-highlight-badge{display:inline-flex;align-items:center;justify-content:center;height:36px;padding:0 14px;border-radius:999px;background:#fff;color:var(--wallet-modal-accent);font-weight:900;border:1px solid rgba(15,23,42,.06)}
.wallet-modal-body label{display:grid;gap:8px;color:#334155;font-weight:700}
.wallet-modal-body label span{font-size:13px}
.wallet-modal-body input,.wallet-modal-body select{height:50px;border:1px solid #d7e3f0;border-radius:16px;padding:0 14px;background:#fbfdff;color:#0f172a;font-size:14px;outline:none;transition:border-color .2s ease,box-shadow .2s ease,background .2s ease}
.wallet-modal-body input:focus,.wallet-modal-body select:focus{border-color:color-mix(in srgb, var(--wallet-modal-accent) 55%, white);box-shadow:0 0 0 4px color-mix(in srgb, var(--wallet-modal-accent) 14%, white);background:#fff}
.quick-amounts{display:flex;gap:8px;flex-wrap:wrap}
.quick-amounts button{height:42px;padding:0 14px;border-radius:14px;background:#f8fafc;color:#0f4aa8;font-weight:800;border:1px solid #dbe5f0}
.quick-amounts button:hover{background:#eff6ff;border-color:#bfdbfe}
.gateway-amounts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.gateway-amounts button{min-height:84px;border:1px solid #dbe5f0;border-radius:18px;background:#fff;color:#0f172a;font-weight:900;cursor:pointer;padding:14px 12px;display:grid;gap:8px;justify-items:start;text-align:right;transition:border-color .2s ease,box-shadow .2s ease,transform .2s ease}
.gateway-amounts button strong{font-size:20px;line-height:1;color:#0f172a}
.gateway-amounts button span{font-size:12px;color:#64748b}
.gateway-amounts button:hover{transform:translateY(-2px);box-shadow:0 14px 28px rgba(15,23,42,.08);border-color:#bfdbfe}
.gateway-amounts button.active{background:var(--wallet-modal-accent-bg);border-color:color-mix(in srgb, var(--wallet-modal-accent) 42%, white)}
.gateway-amounts button.active strong,.gateway-amounts button.active span{color:var(--wallet-modal-accent)}
.wallet-note{padding:14px 16px;border-radius:16px;background:#f8fafc;color:#334155;border:1px solid #dbe5f0;line-height:1.8}
.submit-btn{height:54px;border-radius:18px;color:#fff;font-weight:900;box-shadow:0 18px 34px rgba(15,23,42,.14);transition:transform .2s ease,box-shadow .2s ease,opacity .2s ease}
.submit-btn:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 22px 40px rgba(15,23,42,.18)}
.submit-btn:disabled{opacity:.7;cursor:not-allowed}
.submit-deposit{background:linear-gradient(135deg,#0f766e,#14b8a6)}
.submit-withdraw{background:linear-gradient(135deg,#b91c1c,#ef4444)}
@media (max-width:1200px){.wallet-hero-shell{grid-template-columns:1fr}.wallet-summary-board{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:900px){.history-head{flex-direction:column;align-items:stretch}.history-head h2{font-size:28px}.hero-main{flex-direction:column}.hero-main h2{font-size:44px}.hero-action{min-width:0;width:100%;font-size:22px;height:60px}.gateway-amounts{grid-template-columns:1fr}}
@media (max-width:640px){.shortcut-grid,.wallet-summary-board{grid-template-columns:1fr}.tx-item{grid-template-columns:1fr;justify-items:start}.tx-value-col{width:100%;justify-content:space-between}.history-controls,.hero-actions{flex-direction:column;align-items:stretch}.filter-pill{width:100%;justify-content:space-between}.wallet-modal-overlay{padding:12px}.wallet-modal-head,.wallet-modal-body{padding:16px}.wallet-modal-highlight{align-items:flex-start;flex-direction:column}.wallet-modal-highlight strong{font-size:21px}}
</style>
