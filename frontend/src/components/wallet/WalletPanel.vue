<template>
  <section class="wallet-page" dir="rtl">
    <div v-if="state.error" class="wallet-alert wallet-alert-error">{{ state.error }}</div>
    <div v-if="state.successMessage" class="wallet-alert wallet-alert-success">{{ state.successMessage }}</div>

    <section class="wallet-hero">
      <div class="hero-glow hero-glow-a"></div>
      <div class="hero-glow hero-glow-b"></div>
      <div class="hero-content">
        <div class="hero-balance">
          <p class="hero-label">موجودی کل کیف پول</p>
          <h1>
            {{ money(state.summary.total_balance) }}
            <small>تومان</small>
          </h1>
        </div>

        <div class="hero-actions">
          <button class="hero-btn hero-btn-deposit" type="button" @click="openActionModal('deposit')">
            واریز
          </button>
          <button class="hero-btn hero-btn-withdraw" type="button" @click="openActionModal('withdraw')">
            برداشت
          </button>
        </div>
      </div>

      <div class="stats-grid">
        <article class="stat-card">
          <p>کل واریزی</p>
          <strong>{{ money(state.summary.deposits_total) }} <span>تومان</span></strong>
        </article>
        <article class="stat-card">
          <p>کل برداشت</p>
          <strong>{{ money(state.summary.withdrawals_total) }} <span>تومان</span></strong>
        </article>
        <article class="stat-card">
          <p>تعداد تراکنش</p>
          <strong>{{ money(state.transactions.length) }} <span>مورد</span></strong>
        </article>
      </div>
    </section>

    <section class="history-panel">
      <header class="history-head">
        <h2>تاریخچه تراکنش‌ها</h2>
        <div class="history-controls">
          <div class="filter-pill" role="tablist" aria-label="فیلتر تراکنش">
            <button
              type="button"
              :class="{ active: state.filterType === 'all' }"
              @click="setFilter('all')"
            >
              کل
            </button>
            <button
              type="button"
              :class="{ active: state.filterType === 'deposit' }"
              @click="setFilter('deposit')"
            >
              واریز
            </button>
            <button
              type="button"
              :class="{ active: state.filterType === 'withdraw' }"
              @click="setFilter('withdraw')"
            >
              برداشت
            </button>
          </div>

          <button class="refresh-btn" type="button" :disabled="state.loading" @click="loadWalletDashboard">
            {{ state.loading ? 'در حال بروزرسانی...' : 'بروزرسانی' }}
          </button>
        </div>
      </header>

      <div v-if="state.loading" class="history-state">
        <BaseSpinner size="62px" color="#1d4ed8" ball-color="#60a5fa" label="در حال بارگذاری اطلاعات کیف پول..." />
      </div>
      <div v-else-if="!state.transactions.length" class="history-state">تراکنشی برای نمایش وجود ندارد.</div>

      <div v-else class="tx-list">
        <article v-for="tx in state.transactions" :key="tx.id" class="tx-item">
          <div class="tx-main">
            <div class="tx-dot" :class="tx.direction === 'in' ? 'tx-dot-in' : 'tx-dot-out'"></div>
            <div>
              <h3>{{ txTitle(tx) }}</h3>
              <p>
                {{ formatDateTime(tx.transacted_at) }}
                <span class="separate">•</span>
                {{ tx.wallet_name || 'کیف پول اصلی' }}
              </p>
            </div>
          </div>

          <div class="tx-value" :class="tx.direction === 'in' ? 'tx-value-in' : 'tx-value-out'">
            <strong>{{ tx.direction === 'in' ? '+' : '-' }}{{ money(tx.amount) }}</strong>
            <span>تومان</span>
          </div>
        </article>
      </div>
    </section>

    <div v-if="actionModal.open" class="wallet-modal-overlay" @click.self="closeActionModal">
      <section class="wallet-modal">
        <header class="wallet-modal-head">
          <h3>{{ actionModalTitle }}</h3>
          <button class="close-btn" type="button" @click="closeActionModal">×</button>
        </header>

        <div class="wallet-modal-body">
          <label>
            <span>انتخاب کیف پول</span>
            <select v-model.number="actionModal.walletId">
              <option v-for="wallet in state.wallets" :key="wallet.id" :value="wallet.id">
                {{ wallet.name }} ({{ money(wallet.balance) }} تومان)
              </option>
            </select>
          </label>

          <label>
            <span>مبلغ (تومان)</span>
            <input
              v-model="actionModal.amountText"
              type="text"
              inputmode="numeric"
              :placeholder="actionModal.type === 'deposit' ? 'مثلا ۵۰۰,۰۰۰' : 'مثلا ۲۰۰,۰۰۰'"
            />
          </label>

          <div class="quick-amounts">
            <button type="button" @click="setQuickAmount(100000)">۱۰۰,۰۰۰</button>
            <button type="button" @click="setQuickAmount(500000)">۵۰۰,۰۰۰</button>
            <button type="button" @click="setQuickAmount(1000000)">۱,۰۰۰,۰۰۰</button>
          </div>

          <label>
            <span>شرح</span>
            <input
              v-model="actionModal.description"
              type="text"
              :placeholder="actionModal.type === 'deposit' ? 'واریز از صندوق' : 'برداشت برای هزینه‌ها'"
            />
          </label>

          <div class="wallet-note" v-if="activeWallet">
            موجودی کیف پول انتخابی: <strong>{{ money(activeWallet.balance) }} تومان</strong>
          </div>

          <button
            class="submit-btn"
            :class="actionModal.type === 'deposit' ? 'submit-deposit' : 'submit-withdraw'"
            type="button"
            :disabled="actionModal.submitting"
            @click="submitAction"
          >
            {{ actionModal.submitting ? 'در حال ثبت...' : actionModalSubmitLabel }}
          </button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, watch } from 'vue'
import api from '../../services/api'
import BaseSpinner from '../base/BaseSpinner.vue'

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

const money = (value) => Number(value || 0).toLocaleString('fa-IR')

const formatDateTime = (value) => {
  if (!value) return '-'
  return new Intl.DateTimeFormat('fa-IR', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

const txTitle = (tx) => {
  if (tx?.description) return tx.description
  return tx?.direction === 'in' ? 'واریز به کیف پول' : 'برداشت از کیف پول'
}

const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
  .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
  .replace(/[^\d]/g, '')

const parseAmount = (text) => Number(normalizeDigits(text) || 0)

const activeWallet = computed(() => state.wallets.find((wallet) => Number(wallet.id) === Number(actionModal.walletId)) || null)

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

const loadWalletDashboard = async () => {
  state.loading = true
  state.error = ''

  try {
    const { data } = await api.get('/payments/wallet/dashboard/', {
      params: {
        type: state.filterType,
        q: (props.searchQuery || '').trim() || undefined
      }
    })

    state.summary = {
      total_balance: Number(data?.summary?.total_balance || 0),
      deposits_total: Number(data?.summary?.deposits_total || 0),
      withdrawals_total: Number(data?.summary?.withdrawals_total ?? data?.summary?.payments_total ?? 0)
    }

    state.wallets = Array.isArray(data?.wallets) ? data.wallets : []
    state.transactions = Array.isArray(data?.transactions) ? data.transactions : []

    if (!actionModal.walletId && state.wallets.length) {
      actionModal.walletId = Number(state.wallets[0].id)
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
  if (!actionModal.walletId && state.wallets.length) {
    actionModal.walletId = Number(state.wallets[0].id)
  }
}

const closeActionModal = () => {
  actionModal.open = false
  actionModal.amountText = ''
  actionModal.description = ''
  actionModal.submitting = false
}

const setQuickAmount = (amount) => {
  actionModal.amountText = Number(amount || 0).toLocaleString('fa-IR')
}

const submitAction = async () => {
  clearMessages()

  if (!actionModal.walletId) {
    state.error = 'ابتدا یک کیف پول انتخاب کنید.'
    return
  }

  const amount = parseAmount(actionModal.amountText)
  if (amount <= 0) {
    state.error = 'مبلغ باید بزرگ‌تر از صفر باشد.'
    return
  }

  actionModal.submitting = true

  try {
    const endpoint = actionModal.type === 'deposit'
      ? '/payments/wallet/deposit/'
      : '/payments/wallet/withdraw/'

    const { data } = await api.post(endpoint, {
      wallet_id: actionModal.walletId,
      amount,
      description: (actionModal.description || '').trim() || undefined
    })

    state.successMessage = data?.detail || (actionModal.type === 'deposit' ? 'واریز با موفقیت ثبت شد.' : 'برداشت با موفقیت ثبت شد.')
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
  await loadWalletDashboard()
})
</script>

<style scoped>
.wallet-page {
  --wallet-ink: #0f172a;
  --wallet-muted: #64748b;
  --wallet-border: #dbe5f0;
  --wallet-surface: #ffffff;
  --wallet-soft: #f4f8fc;
  --wallet-positive: #059669;
  --wallet-negative: #dc2626;

  display: grid;
  gap: 22px;
}

.wallet-alert {
  border-radius: 14px;
  padding: 12px 14px;
  font-weight: 600;
  border: 1px solid transparent;
}

.wallet-alert-error {
  background: #fef2f2;
  color: #991b1b;
  border-color: #fecaca;
}

.wallet-alert-success {
  background: #ecfdf5;
  color: #166534;
  border-color: #bbf7d0;
}

.wallet-hero {
  position: relative;
  overflow: hidden;
  border-radius: 26px;
  padding: 24px;
  background: radial-gradient(circle at 15% 10%, #5eead4 0, rgba(94, 234, 212, 0) 40%),
    linear-gradient(135deg, #0f4aa8 0%, #0e7490 58%, #0f766e 100%);
  color: #fff;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.24);
}

.hero-glow {
  position: absolute;
  border-radius: 999px;
  filter: blur(46px);
  opacity: 0.35;
}

.hero-glow-a {
  width: 220px;
  height: 220px;
  top: -80px;
  left: -40px;
  background: #ffffff;
}

.hero-glow-b {
  width: 260px;
  height: 260px;
  right: -90px;
  bottom: -120px;
  background: #99f6e4;
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}

.hero-label {
  margin: 0 0 8px;
  opacity: 0.88;
  font-size: 14px;
}

.hero-balance h1 {
  margin: 0;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  font-size: clamp(30px, 4vw, 42px);
  line-height: 1;
}

.hero-balance small {
  font-size: 17px;
  opacity: 0.9;
}

.hero-actions {
  display: flex;
  gap: 10px;
}

.hero-btn {
  border: 0;
  border-radius: 14px;
  min-width: 118px;
  height: 48px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.hero-btn:hover {
  transform: translateY(-1px);
}

.hero-btn-deposit {
  color: #0f4aa8;
  background: #fff;
  box-shadow: 0 10px 24px rgba(255, 255, 255, 0.25);
}

.hero-btn-withdraw {
  color: #fff;
  background: rgba(15, 23, 42, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.38);
}

.stats-grid {
  position: relative;
  z-index: 1;
  margin-top: 20px;
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.stat-card {
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 16px;
  padding: 12px;
  backdrop-filter: blur(4px);
}

.stat-card p {
  margin: 0;
  font-size: 13px;
  opacity: 0.86;
}

.stat-card strong {
  display: block;
  margin-top: 8px;
  font-size: 20px;
}

.stat-card span {
  font-size: 13px;
  opacity: 0.9;
}

.history-panel {
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border-radius: 24px;
  border: 1px solid var(--wallet-border);
  padding: 18px;
  display: grid;
  gap: 14px;
}

.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.history-head h2 {
  margin: 0;
  color: var(--wallet-ink);
  font-size: 22px;
}

.history-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.filter-pill {
  background: #e7edf5;
  border-radius: 999px;
  padding: 4px;
  display: flex;
  gap: 4px;
}

.filter-pill button {
  border: 0;
  background: transparent;
  color: #334155;
  border-radius: 999px;
  padding: 7px 14px;
  font-weight: 700;
  cursor: pointer;
}

.filter-pill button.active {
  background: #fff;
  color: #0f4aa8;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.15);
}

.refresh-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #0f172a;
  border-radius: 12px;
  height: 38px;
  padding: 0 14px;
  font-weight: 700;
  cursor: pointer;
}

.refresh-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.history-state {
  min-height: 130px;
  border: 1px dashed #cbd5e1;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--wallet-muted);
  background: #fff;
}

.tx-list {
  display: grid;
  gap: 9px;
}

.tx-item {
  background: var(--wallet-surface);
  border: 1px solid var(--wallet-border);
  border-radius: 16px;
  padding: 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.tx-main {
  display: flex;
  gap: 10px;
  align-items: center;
}

.tx-dot {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  flex: 0 0 auto;
}

.tx-dot-in {
  background: #34d399;
  box-shadow: 0 0 0 6px rgba(52, 211, 153, 0.15);
}

.tx-dot-out {
  background: #f87171;
  box-shadow: 0 0 0 6px rgba(248, 113, 113, 0.14);
}

.tx-main h3 {
  margin: 0;
  font-size: 15px;
  color: var(--wallet-ink);
}

.tx-main p {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--wallet-muted);
}

.separate {
  margin: 0 6px;
}

.tx-value {
  text-align: left;
}

.tx-value strong {
  font-size: 17px;
}

.tx-value span {
  display: block;
  color: var(--wallet-muted);
  font-size: 12px;
}

.tx-value-in strong {
  color: var(--wallet-positive);
}

.tx-value-out strong {
  color: var(--wallet-negative);
}

.wallet-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.52);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 120;
}

.wallet-modal {
  width: min(540px, 100%);
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid var(--wallet-border);
  background: #fff;
}

.wallet-modal-head {
  background: #f0f7ff;
  border-bottom: 1px solid var(--wallet-border);
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.wallet-modal-head h3 {
  margin: 0;
  color: #0f4aa8;
  font-size: 18px;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 10px;
  background: #e2e8f0;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
}

.wallet-modal-body {
  padding: 16px;
  display: grid;
  gap: 11px;
}

.wallet-modal-body label {
  display: grid;
  gap: 6px;
}

.wallet-modal-body span {
  font-size: 13px;
  color: #334155;
  font-weight: 700;
}

.wallet-modal-body input,
.wallet-modal-body select {
  height: 44px;
  border: 1px solid #cbd5e1;
  border-radius: 11px;
  padding: 0 10px;
  font: inherit;
}

.quick-amounts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.quick-amounts button {
  border: 1px solid #dbe5f0;
  border-radius: 10px;
  background: #f8fbff;
  height: 40px;
  cursor: pointer;
  font-weight: 700;
}

.wallet-note {
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  padding: 9px 10px;
  color: #334155;
  font-size: 13px;
}

.submit-btn {
  height: 48px;
  border: 0;
  border-radius: 12px;
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.submit-deposit {
  background: linear-gradient(90deg, #0f4aa8, #0f766e);
}

.submit-withdraw {
  background: linear-gradient(90deg, #b45309, #dc2626);
}

@media (max-width: 980px) {
  .hero-content {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .history-controls {
    width: 100%;
    justify-content: space-between;
  }
}

@media (max-width: 640px) {
  .wallet-hero {
    padding: 18px;
    border-radius: 20px;
  }

  .hero-btn {
    flex: 1;
  }

  .filter-pill {
    width: 100%;
  }

  .filter-pill button {
    flex: 1;
    text-align: center;
  }

  .history-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .refresh-btn {
    width: 100%;
  }

  .tx-item {
    align-items: flex-start;
    flex-direction: column;
  }

  .tx-value {
    width: 100%;
    text-align: right;
  }
}
</style>
