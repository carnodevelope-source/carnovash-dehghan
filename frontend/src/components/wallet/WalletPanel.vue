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
          <button class="shortcut-card shortcut-primary" type="button" :disabled="!hasDepositWallet" @click="openActionModal('deposit')">
            <span class="shortcut-icon">+</span>
            <strong>شارژ حساب</strong>
            <small>{{ depositShortcutCaption }}</small>
          </button>
          <button class="shortcut-card" type="button" :disabled="withdrawButtonDisabled" @click="openActionModal('withdraw')">
            <span class="shortcut-icon">↗</span>
            <strong>{{ withdrawButtonTitle }}</strong>
            <small>{{ withdrawButtonCaption }}</small>
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
            <h2>{{ moneyWithUnit(totalBalance) }}</h2>
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
            class="hero-action hero-action-ghost"
            type="button"
            :disabled="withdrawButtonDisabled"
            @click="openActionModal('withdraw')"
          >
            {{ withdrawButtonTitle }}
          </button>
        </div>
      </section>
    </section>

    <section class="wallet-summary-board">
      <article class="summary-tile">
        <small>موجودی عادی</small>
        <strong :class="{ danger: regularLow }">{{ moneyWithUnit(state.summary.regular_balance) }}</strong>
      </article>
      <article class="summary-tile sms-tile" :class="{ low: smsLow }">
        <div class="sms-tile-head">
          <small>موجودی پیامک</small>
          <span class="sms-state-pill" :class="{ low: smsLow }">{{ smsBalanceStateLabel }}</span>
        </div>
        <strong :class="{ danger: smsLow }">{{ moneyWithUnit(state.summary.sms_balance) }}</strong>
        <p class="sms-balance-caption">{{ smsBalanceHint }}</p>
        <span class="sms-topup-chip">{{ suggestedSmsTopUpLabel }}</span>
      </article>
      <article class="summary-tile accent-tile">
        <small>جمع واریزی‌ها</small>
        <strong>{{ moneyWithUnit(state.summary.deposits_total) }}</strong>
      </article>
      <article class="summary-tile soft-tile">
        <small>جمع برداشت‌ها</small>
        <strong>{{ moneyWithUnit(state.summary.withdrawals_total) }}</strong>
      </article>
    </section>

    <section v-if="regularLow || smsLow" class="warning-strip">
      <span class="warning-dot"></span>
      <strong>{{ regularLow && smsLow ? 'موجودی عادی و شارژ پیامک کم است.' : regularLow ? 'موجودی عادی کم است.' : 'شارژ پیامک کم است.' }}</strong>
    </section>

    <section class="options-panel">
      <header class="options-head">
        <div>
          <p>آپشن‌ها</p>
          <h2>قابلیت‌های اختصاصی {{ optionsTenantName }}</h2>
        </div>
        <button class="refresh-btn" type="button" :disabled="state.optionsLoading" @click="loadWalletOptions">
          {{ state.optionsLoading ? 'در حال بروزرسانی...' : 'بروزرسانی آپشن‌ها' }}
        </button>
      </header>

      <div class="options-grid">
        <article
          v-for="option in state.options"
          :key="option.feature_key"
          class="option-card"
          :class="{ active: option.is_active, unavailable: option.is_available === false }"
          :style="{ '--option-accent': option.accent || '#315f9f' }"
        >
          <div class="option-card-head">
            <div>
              <span class="option-kicker">{{ option.personalized_title }}</span>
              <h3>{{ option.title }}</h3>
            </div>
            <span class="option-status" :class="{ enabled: option.is_active }">
              {{ option.status_label || (option.is_active ? 'فعال' : 'قابل خرید') }}
            </span>
          </div>
          <p>{{ option.description }}</p>
          <div v-if="option.is_available === false" class="option-unavailable-box">
            <strong>در دسترس نمی‌باشد</strong>
            <small>{{ option.unavailable_message || 'این آپشن هنوز ارائه نمی‌شود.' }}</small>
          </div>
          <div v-if="option.is_active && option.is_available !== false" class="option-live-grid">
            <article class="option-live-stat">
              <span>شیوه پرداخت</span>
              <strong>{{ option.payment_plan_label || 'ثبت نشده' }}</strong>
            </article>
            <article class="option-live-stat">
              <span>پرداخت‌شده</span>
              <strong>{{ moneyWithUnit(option.paid_amount) }}</strong>
            </article>
            <article class="option-live-stat">
              <span>مانده</span>
              <strong>{{ moneyWithUnit(option.remaining_amount) }}</strong>
            </article>
            <article class="option-live-stat">
              <div class="option-live-stat-head">
                <span>{{ option.next_installment_due_at ? 'سررسید بعدی' : 'فعال‌سازی' }}</span>
                <button
                  v-if="option.can_pay_next_installment"
                  type="button"
                  class="option-inline-pay-btn"
                  :disabled="payingInstallmentFeatureKey === option.feature_key"
                  @click="submitNextInstallmentPayment(option)"
                >
                  {{ payingInstallmentFeatureKey === option.feature_key ? 'در حال پرداخت...' : 'پرداخت' }}
                </button>
              </div>
              <strong>{{ option.next_installment_due_at ? formatShortDate(option.next_installment_due_at) : formatShortDate(option.purchased_at) }}</strong>
            </article>
          </div>
          <div v-else-if="option.is_available !== false" class="option-price-stack">
            <div class="option-price-row">
              <span>قیمت نقدی</span>
              <strong>{{ moneyWithUnit(option.cash_amount) }}</strong>
            </div>
            <div class="option-installment-row">
              <span>اقساط ۱۲ ماهه</span>
              <strong>{{ moneyWithUnit(option.monthly_installment_amount) }}</strong>
              <small>پیش‌پرداخت: {{ moneyWithUnit(option.installment_upfront_amount) }}</small>
            </div>
          </div>
          <div v-if="option.is_active && option.is_available !== false" class="option-progress-block">
            <div class="option-progress-head">
              <span>پیشرفت پرداخت</span>
              <strong>{{ toFaPercent(option.progress_percent) }}</strong>
            </div>
            <div class="option-progress-bar">
              <span :style="{ width: `${option.progress_percent || 0}%` }"></span>
            </div>
            <small v-if="option.auto_charge_enabled">
              برداشت خودکار ماهانه {{ moneyWithUnit(option.next_installment_amount || option.live_monthly_installment_amount) }}
              <template v-if="option.next_installment_due_at"> در {{ formatShortDate(option.next_installment_due_at) }}</template>
              از کیف پول اصلی انجام می‌شود.
            </small>
            <small v-else>این قابلیت برای این کارواش فعال است و از روی دیتابیس همین شعبه خوانده می‌شود.</small>
          </div>
          <button
            class="option-buy-btn"
            type="button"
            :disabled="option.is_active || option.is_available === false"
            @click="openOptionModal(option)"
          >
            {{ option.is_available === false ? 'فعلا ارائه نمی‌شود' : option.is_active ? 'فعال شده' : 'انتخاب و خرید' }}
          </button>
        </article>
      </div>
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
              {{ tx.direction === 'in' ? '+' : '-' }}{{ moneyWithUnit(tx.amount) }}
            </strong>
            <div class="tx-icon-box" :class="tx.direction === 'in' ? 'tx-icon-box-in' : 'tx-icon-box-out'">
              {{ tx.direction === 'in' ? '↓' : '↑' }}
            </div>
          </div>
        </article>
      </div>
    </section>

    <div v-if="actionModal.open" class="wallet-modal-overlay" @click.self="closeActionModal">
      <section class="wallet-modal financial-action-modal" :class="actionModal.type === 'deposit' ? 'wallet-modal-deposit' : 'wallet-modal-withdraw'">
        <header class="wallet-modal-head">
          <div class="wallet-modal-title-row">
            <div class="wallet-modal-symbol">
              {{ actionModal.type === 'deposit' ? '↓' : '↑' }}
            </div>
            <div class="wallet-modal-title-wrap">
              <p>{{ actionModal.type === 'deposit' ? 'افزایش موجودی از طریق درگاه' : 'ثبت برداشت داخلی' }}</p>
              <h3>{{ actionModalTitle }}</h3>
            </div>
          </div>
          <button class="close-btn" type="button" @click="closeActionModal">×</button>
        </header>

        <div class="wallet-modal-body">
          <div class="wallet-modal-highlight" v-if="activeWallet">
            <div>
              <small>{{ activeWallet.name }}</small>
              <strong>{{ moneyWithUnit(activeWallet.balance) }}</strong>
              <p>موجودی فعلی کیف پول انتخاب‌شده</p>
            </div>
            <span class="wallet-modal-highlight-badge">
              {{ actionModal.type === 'deposit' ? 'شارژ' : 'برداشت' }}
            </span>
          </div>

          <div class="wallet-modal-section">
            <div class="wallet-modal-section-head">
              <strong>{{ actionModal.type === 'withdraw' ? 'کیف پول مبدا' : 'کیف پول مقصد شارژ' }}</strong>
              <span>{{ actionModal.type === 'withdraw' ? 'از هر کیف پول دارای موجودی می‌توانید برداشت یا انتقال ثبت کنید' : 'کیف پولی که شارژ به آن اضافه می‌شود' }}</span>
            </div>

            <div class="wallet-choice-grid">
              <button
                v-for="wallet in actionSourceWallets"
                :key="`action-wallet-${wallet.id}`"
                type="button"
                class="wallet-choice-card"
                :class="{ active: Number(actionModal.walletId) === Number(wallet.id) }"
                @click="actionModal.walletId = Number(wallet.id)"
              >
                <small>کیف پول</small>
                <span>{{ wallet.name }}</span>
                <strong>{{ moneyWithUnit(wallet.balance) }}</strong>
              </button>
            </div>
          </div>

          <div v-if="actionModal.type === 'deposit'" class="wallet-modal-section deposit-method-section">
            <div class="wallet-modal-section-head">
              <strong>روش واریز</strong>
              <span>فعلا فقط کارت به کارت فعال است</span>
            </div>

            <div class="deposit-method-grid">
              <button
                v-for="method in depositMethods"
                :key="method.key"
                type="button"
                class="deposit-method-card"
                :class="{ active: actionModal.paymentMethod === method.key, disabled: method.disabled }"
                :disabled="method.disabled"
                @click="actionModal.paymentMethod = method.key"
              >
                <strong>{{ method.title }}</strong>
                <span>{{ method.caption }}</span>
              </button>
            </div>
          </div>

          <div class="wallet-modal-section">
            <div class="wallet-modal-section-head">
              <strong>{{ actionModal.type === 'deposit' ? 'انتخاب مبلغ واریز' : 'ثبت مبلغ برداشت' }}</strong>
              <span>{{ actionModal.type === 'deposit' ? 'یکی از مبالغ پیشنهادی را انتخاب کنید' : 'می‌توانید مبلغ را دستی یا سریع وارد کنید' }}</span>
            </div>

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
                <button
                  v-for="amount in dynamicDepositAmounts"
                  :key="`deposit-${amount.value}`"
                  type="button"
                  :class="{ active: selectedDepositAmount === amount.value }"
                  @click="setQuickAmount(amount.value)"
                >
                  <strong>{{ moneyWithUnit(amount.value) }}</strong>
                  <span>{{ amount.caption }}</span>
                </button>
              </div>
            </label>

            <div v-if="actionModal.type === 'withdraw'" class="quick-amounts">
              <button
                v-for="amount in dynamicWithdrawAmounts"
                :key="`withdraw-${amount.value}`"
                type="button"
                @click="setQuickAmount(amount.value)"
              >
                <small>{{ amount.label }}</small>
                <strong>{{ moneyWithUnit(amount.value) }}</strong>
              </button>
              <span v-if="!dynamicWithdrawAmounts.length" class="wallet-inline-warning">موجودی قابل برداشت برای این کیف پول وجود ندارد.</span>
            </div>
          </div>

          <div v-if="actionModal.type === 'deposit' && actionModal.paymentMethod === 'card'" class="wallet-modal-section card-payment-section">
            <div class="wallet-modal-section-head">
              <strong>اطلاعات کارت به کارت</strong>
              <span>پس از واریز، رسید را از مسیر پشتیبانی ثبت کنید</span>
            </div>
            <div class="company-card-box">
              <small>شماره کارت شرکت</small>
              <strong>{{ companyCardNumber }}</strong>
              <span>{{ companyCardHolder }}</span>
            </div>
            <p class="card-payment-instruction">
              بعد از پرداخت وجه روی این دکمه کلیک کنید. فرم تیکت پرداخت به صورت خودکار باز می‌شود؛ شماره و کد تراکنش یا مشخصات رسید واریز را وارد کنید و تیکت را ارجاع دهید.
            </p>
            <button class="support-ticket-btn" type="button" @click="openPaymentSupportTicket">
              ثبت تیکت رسید واریز
            </button>
          </div>

          <div v-if="actionModal.type === 'withdraw'" class="wallet-modal-section wallet-destination-section">
            <div class="wallet-modal-section-head">
              <strong>مقصد برداشت</strong>
              <span>مبلغ را به حساب بانکی یا کیف پول دیگر منتقل کنید</span>
            </div>

            <div class="destination-toggle" role="group" aria-label="مقصد برداشت">
              <button
                type="button"
                :class="{ active: actionModal.destinationType === 'bank' }"
                @click="actionModal.destinationType = 'bank'"
              >
                <span>حساب بانکی</span>
                <small>ثبت خروج از کیف پول</small>
              </button>
              <button
                type="button"
                :class="{ active: actionModal.destinationType === 'wallet' }"
                @click="actionModal.destinationType = 'wallet'"
              >
                <span>کیف پول دیگر</span>
                <small>انتقال داخلی فوری</small>
              </button>
            </div>

            <div v-if="actionModal.destinationType === 'wallet'" class="wallet-choice-grid">
              <button
                v-for="wallet in transferDestinationWallets"
                :key="`destination-wallet-${wallet.id}`"
                type="button"
                class="wallet-choice-card destination-card"
                :class="{ active: Number(actionModal.destinationWalletId) === Number(wallet.id) }"
                @click="actionModal.destinationWalletId = Number(wallet.id)"
              >
                <small>مقصد</small>
                <span>{{ wallet.name }}</span>
                <strong>{{ moneyWithUnit(wallet.balance) }}</strong>
              </button>
            </div>
          </div>

          <div v-if="selectedActionAmount > 0" class="wallet-balance-preview-grid">
            <div class="wallet-balance-preview" :class="{ danger: balanceAfterAction < 0 }">
              <span>{{ actionModal.type === 'deposit' ? 'موجودی بعد از واریز' : 'مانده مبدا' }}</span>
              <strong>{{ moneyWithUnit(Math.max(0, balanceAfterAction)) }}</strong>
            </div>
            <div v-if="actionModal.type === 'withdraw' && actionModal.destinationType === 'wallet' && selectedDestinationWallet" class="wallet-balance-preview destination">
              <span>موجودی مقصد</span>
              <strong>{{ moneyWithUnit(destinationBalanceAfterAction) }}</strong>
            </div>
          </div>
          <div v-if="actionAmountError" class="wallet-inline-warning">{{ actionAmountError }}</div>

          <div class="wallet-modal-section wallet-modal-section-soft">
            <div class="wallet-modal-section-head">
              <strong>جزئیات ثبت</strong>
              <span>شرح کوتاه برای پیگیری مالی بهتر</span>
            </div>
            <label>
              <span>شرح</span>
              <input v-model="actionModal.description" type="text" :placeholder="actionModal.type === 'deposit' ? 'مثلاً شارژ صندوق' : 'مثلاً هزینه جاری'" />
            </label>
          </div>

          <div class="wallet-note">
            {{ actionModal.type === 'deposit' ? 'واریز کارت به کارت بعد از بررسی رسید توسط پشتیبانی به کیف پول اضافه می‌شود.' : 'برداشت بلافاصله از موجودی کیف پول کسر می‌شود.' }}
          </div>

          <button v-if="actionModal.type !== 'deposit' || actionModal.paymentMethod !== 'card'" class="submit-btn" :class="actionModal.type === 'deposit' ? 'submit-deposit' : 'submit-withdraw'" type="button" :disabled="!canSubmitAction" @click="submitAction">
            {{ actionModal.submitting ? 'در حال ثبت...' : actionModalSubmitLabel }}
          </button>
        </div>
      </section>
    </div>

    <div v-if="optionModal.open" class="wallet-modal-overlay" @click.self="closeOptionModal">
      <section class="wallet-modal option-purchase-modal">
        <header class="wallet-modal-head">
          <div class="wallet-modal-title-wrap">
            <p>خرید آپشن اختصاصی</p>
            <h3>{{ selectedOption?.personalized_title || 'آپشن' }}</h3>
          </div>
          <button class="close-btn" type="button" @click="closeOptionModal">×</button>
        </header>

        <div class="wallet-modal-body">
          <div class="option-purchase-hero" v-if="selectedOption" :style="{ '--option-accent': selectedOption.accent || '#315f9f' }">
            <div>
              <small>{{ selectedOption.subtitle }}</small>
              <strong>{{ moneyWithUnit(selectedOption.total_amount) }}</strong>
              <p>{{ selectedOption.description }}</p>
            </div>
          </div>

          <label>
            <span>کیف پول پرداخت</span>
            <select v-model.number="optionModal.walletId">
              <option v-for="wallet in optionWallets" :key="wallet.id" :value="wallet.id">
                {{ wallet.name }} ({{ moneyWithUnit(wallet.balance) }})
              </option>
            </select>
          </label>

          <div class="payment-plan-grid">
            <button
              type="button"
              class="payment-plan-card"
              :class="{ active: optionModal.paymentPlan === 'cash' }"
              @click="optionModal.paymentPlan = 'cash'"
            >
              <strong>نقدی</strong>
              <span>{{ moneyWithUnit(selectedOption?.cash_amount) }}</span>
              <small>کل مبلغ همین حالا از کیف پول کم می‌شود.</small>
            </button>
            <button
              type="button"
              class="payment-plan-card"
              :class="{ active: optionModal.paymentPlan === 'installment' }"
              @click="optionModal.paymentPlan = 'installment'"
            >
              <strong>قسطی</strong>
              <span>{{ moneyWithUnit(selectedOption?.installment_upfront_amount) }}</span>
              <small>باقی‌مانده ۱۲ ماهه، ماهی {{ moneyWithUnit(selectedOption?.monthly_installment_amount) }}</small>
            </button>
          </div>

          <label v-if="optionModal.paymentPlan === 'installment'" class="upfront-input-box">
            <span>مبلغ نقدی اولیه (هزار تومان)</span>
            <input
              v-model="optionModal.upfrontAmountText"
              type="text"
              inputmode="numeric"
              placeholder="مثلا 800"
            />
            <small>باقی‌مانده به صورت خودکار در ۱۲ قسط مساوی محاسبه می‌شود.</small>
          </label>

          <div v-if="optionModal.paymentPlan === 'installment'" class="installment-live-preview">
            <div>
              <span>باقی‌مانده</span>
              <strong>{{ moneyWithUnit(optionRemainingAmount) }}</strong>
            </div>
            <div>
              <span>قسط ماهانه</span>
              <strong>{{ moneyWithUnit(optionMonthlyAmount) }}</strong>
            </div>
          </div>
          <div v-if="optionModal.paymentPlan === 'installment'" class="wallet-note">
            برداشت اقساط ماهانه به صورت خودکار از کیف پول اصلی همین کارواش انجام می‌شود و سررسیدهای عقب‌افتاده نیز در اولین اجرای API یا job زمان‌بندی‌شده تسویه می‌شوند.
          </div>

          <div class="wallet-balance-preview" :class="{ danger: optionBalanceAfter < 0 }">
            <span>موجودی بعد از خرید</span>
            <strong>{{ moneyWithUnit(Math.max(0, optionBalanceAfter)) }}</strong>
          </div>
          <div v-if="optionPurchaseError" class="wallet-inline-warning">{{ optionPurchaseError }}</div>

          <button class="submit-btn submit-deposit" type="button" :disabled="!canSubmitOptionPurchase" @click="submitOptionPurchase">
            {{ optionModal.submitting ? 'در حال فعال‌سازی...' : 'تایید و فعال‌سازی آپشن' }}
          </button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../services/api'
import BaseSpinner from '../base/BaseSpinner.vue'
import { formatThousandsToman, formatThousandsTomanValue, fromThousandsTomanInput } from '../../utils/money'
import { resolveApiErrorMessage } from '../../utils/apiError'

const props = defineProps({
  searchQuery: { type: String, default: '' }
})

const router = useRouter()

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
  transactions: [],
  options: [],
  optionsTenant: null,
  optionsLoading: false
})

const actionModal = reactive({
  open: false,
  type: 'deposit',
  walletId: null,
  destinationType: 'bank',
  destinationWalletId: null,
  paymentMethod: 'card',
  amountText: '',
  description: '',
  submitting: false
})

const optionModal = reactive({
  open: false,
  featureKey: '',
  walletId: null,
  paymentPlan: 'cash',
  upfrontAmountText: '',
  submitting: false
})

const selectedWalletId = ref(0)
const selectedDepositAmount = ref(1000000)
const payingInstallmentFeatureKey = ref('')
const companyCardNumber = '6037991719847703'
const companyCardHolder = 'میلاد دهستانی'
const depositMethods = [
  { key: 'gateway', title: 'درگاه پرداخت', caption: 'به‌زودی فعال می‌شود', disabled: true },
  { key: 'up', title: 'اپلیکیشن آپ', caption: 'به‌زودی فعال می‌شود', disabled: true },
  { key: 'card', title: 'کارت به کارت', caption: 'فعال', disabled: false }
]

const money = (value) => formatThousandsTomanValue(value)
const moneyWithUnit = (value) => formatThousandsToman(value)
const formatDateTime = (value) => value ? new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '-'
const formatShortDate = (value) => value ? new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium' }).format(new Date(value)) : '-'
const txTitle = (tx) => tx?.description || (tx?.direction === 'in' ? 'واریز به کیف پول' : 'برداشت از کیف پول')
const toFaPercent = (value) => `${new Intl.NumberFormat('fa-IR').format(Number(value || 0))}٪`
const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
  .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
  .replace(/[^\d]/g, '')
const parseAmount = (text) => fromThousandsTomanInput(normalizeDigits(text))

const regularLow = computed(() => Number(state.summary.regular_balance || 0) <= 100000)
const smsLow = computed(() => Number(state.summary.sms_balance || 0) <= 50000)
const totalBalance = computed(() => Number(state.summary.total_balance || 0))
const smsBalanceStateLabel = computed(() => {
  if (Number(state.summary.sms_balance || 0) <= 0) return 'بدون شارژ'
  if (smsLow.value) return 'رو به اتمام'
  return 'آماده ارسال'
})
const smsBalanceHint = computed(() => {
  if (Number(state.summary.sms_balance || 0) <= 0) return 'فعلا هیچ اعتبار پیامکی ثبت نشده و ارسال کمپین متوقف می‌ماند.'
  if (smsLow.value) return 'برای جلوگیری از توقف ارسال، بهتر است همین حالا کیف پول پیامک را شارژ کنید.'
  return 'این اعتبار برای پیامک‌های تکی و گروهی همین شعبه استفاده می‌شود.'
})
const suggestedSmsTopUpLabel = computed(() => {
  if (Number(state.summary.sms_balance || 0) <= 0) return 'شارژ پیشنهادی: ۱۰۰ هزار تومان'
  if (smsLow.value) return 'پیشنهاد: یک شارژ سبک انجام بده'
  return 'وضعیت شارژ: مناسب'
})
const selectedWallet = computed(() => state.wallets.find((wallet) => Number(wallet.id) === Number(selectedWalletId.value)) || null)
const activeWallet = computed(() => state.wallets.find((wallet) => Number(wallet.id) === Number(actionModal.walletId)) || null)
const activeWalletIsSms = computed(() => activeWallet.value?.wallet_type === 'sms')
const activeWalletBalance = computed(() => Math.max(0, Number(activeWallet.value?.balance || 0)))
const selectedWalletIsSms = computed(() => selectedWallet.value?.wallet_type === 'sms')
const selectedWalletBalance = computed(() => Math.max(0, Number(selectedWallet.value?.balance || 0)))
const hasDepositWallet = computed(() => state.wallets.length > 0)
const hasWithdrawableBalance = computed(() => state.wallets.some((wallet) => Number(wallet.balance || 0) > 0))
const withdrawButtonDisabled = computed(() => {
  if (!hasWithdrawableBalance.value) return true
  if (!selectedWallet.value) return false
  return selectedWalletBalance.value <= 0
})
const withdrawButtonTitle = computed(() => withdrawButtonDisabled.value ? 'برداشت غیرفعال' : 'برداشت وجه')
const withdrawButtonCaption = computed(() => {
  if (selectedWallet.value && selectedWalletBalance.value <= 0) return 'موجودی این کیف پول صفر است'
  if (!hasWithdrawableBalance.value) return 'موجودی قابل برداشت ندارید'
  const balance = selectedWallet.value ? selectedWalletBalance.value : Number(state.summary.regular_balance || 0)
  return `قابل برداشت: ${moneyWithUnit(balance)}`
})
const depositShortcutCaption = computed(() => {
  if (!hasDepositWallet.value) return 'کیف پولی برای شارژ وجود ندارد'
  const wallet = selectedWallet.value || state.wallets[0]
  return `${wallet.name}: ${moneyWithUnit(wallet.balance)}`
})
const selectableWallets = computed(() => (
  actionModal.type === 'withdraw'
    ? state.wallets
    : state.wallets
))
const withdrawSourceWallets = computed(() => state.wallets.filter((wallet) => Number(wallet.balance || 0) > 0))
const actionSourceWallets = computed(() => actionModal.type === 'withdraw' ? withdrawSourceWallets.value : selectableWallets.value)
const transferDestinationWallets = computed(() => state.wallets.filter((wallet) => Number(wallet.id) !== Number(actionModal.walletId)))
const selectedDestinationWallet = computed(() => transferDestinationWallets.value.find((wallet) => Number(wallet.id) === Number(actionModal.destinationWalletId)) || null)
const filteredTransactions = computed(() => {
  const walletId = Number(selectedWalletId.value || 0)
  if (!walletId) return state.transactions
  return state.transactions.filter((tx) => Number(tx.wallet) === walletId)
})
const actionModalTitle = computed(() => actionModal.type === 'deposit' ? 'ثبت واریز به کیف پول' : 'ثبت برداشت از کیف پول')
const actionModalSubmitLabel = computed(() => actionModal.type === 'deposit' ? 'تایید و ثبت واریز' : 'تایید و ثبت برداشت')
const optionsTenantName = computed(() => state.optionsTenant?.name || 'کارواش شما')
const selectedOption = computed(() => state.options.find((option) => option.feature_key === optionModal.featureKey) || null)
const optionWallets = computed(() => state.wallets.filter((wallet) => wallet.wallet_type !== 'sms'))
const selectedOptionWallet = computed(() => optionWallets.value.find((wallet) => Number(wallet.id) === Number(optionModal.walletId)) || null)
const optionUpfrontAmount = computed(() => parseAmount(optionModal.upfrontAmountText))
const selectedOptionDebitAmount = computed(() => {
  const option = selectedOption.value
  if (!option) return 0
  return optionModal.paymentPlan === 'installment'
    ? optionUpfrontAmount.value
    : Number(option.cash_amount || option.total_amount || 0)
})
const optionRemainingAmount = computed(() => Math.max(0, Number(selectedOption.value?.total_amount || 0) - selectedOptionDebitAmount.value))
const optionMonthlyAmount = computed(() => optionModal.paymentPlan === 'installment' ? Math.round(optionRemainingAmount.value / 12) : 0)
const optionBalanceAfter = computed(() => Number(selectedOptionWallet.value?.balance || 0) - selectedOptionDebitAmount.value)
const optionPurchaseError = computed(() => {
  if (!optionModal.open) return ''
  if (!selectedOption.value) return 'آپشن انتخاب‌شده معتبر نیست.'
  if (selectedOption.value.is_active) return 'این آپشن قبلا فعال شده است.'
  if (!selectedOptionWallet.value) return 'برای خرید، یک کیف پول عادی انتخاب کنید.'
  if (optionModal.paymentPlan === 'installment' && selectedOptionDebitAmount.value <= 0) return 'مبلغ نقدی اولیه را وارد کنید.'
  if (optionModal.paymentPlan === 'installment' && selectedOptionDebitAmount.value >= Number(selectedOption.value.total_amount || 0)) return 'برای پرداخت قسطی، مبلغ نقدی باید کمتر از کل مبلغ باشد.'
  if (optionBalanceAfter.value < 0) return 'موجودی کیف پول برای این شیوه پرداخت کافی نیست.'
  return ''
})
const canSubmitOptionPurchase = computed(() => !optionModal.submitting && !optionPurchaseError.value)
const roundUpToStep = (value, step = 50000) => Math.ceil(Math.max(0, Number(value || 0)) / step) * step
const roundDownToStep = (value, step = 1000) => Math.floor(Math.max(0, Number(value || 0)) / step) * step
const uniquePositiveAmounts = (items) => {
  const seen = new Set()
  return items
    .map((item) => ({ ...item, value: Math.round(Number(item.value || 0)) }))
    .filter((item) => item.value > 0 && !seen.has(item.value) && seen.add(item.value))
}
const dynamicDepositAmounts = computed(() => {
  const wallet = activeWallet.value
  const balance = activeWalletBalance.value
  if (!wallet) return []
  if (wallet.wallet_type === 'sms') {
    return uniquePositiveAmounts([
      { value: roundUpToStep(Math.max(50000, 50000 - balance), 10000), caption: 'حداقل شارژ پیامک' },
      { value: roundUpToStep(Math.max(100000, 100000 - balance), 10000), caption: 'شارژ پیشنهادی پیامک' },
      { value: 200000, caption: 'شارژ مطمئن پیامک' }
    ])
  }
  return uniquePositiveAmounts([
    { value: roundUpToStep(Math.max(100000, 500000 - balance)), caption: 'رسیدن به حد امن' },
    { value: roundUpToStep(Math.max(500000, 1000000 - balance)), caption: 'شارژ پیشنهادی' },
    { value: roundUpToStep(Math.max(1000000, Math.min(5000000, balance * 0.5 || 2000000))), caption: 'شارژ عملیاتی' }
  ])
})
const dynamicWithdrawAmounts = computed(() => {
  const balance = activeWalletBalance.value
  if (actionModal.type !== 'withdraw' || !activeWallet.value || balance <= 0) return []
  return uniquePositiveAmounts([
    { value: Math.min(100000, balance), label: 'سریع' },
    { value: roundDownToStep(balance * 0.25), label: '۲۵٪ موجودی' },
    { value: roundDownToStep(balance * 0.5), label: '۵۰٪ موجودی' },
    { value: roundDownToStep(balance), label: 'کل موجودی' }
  ]).filter((item) => item.value <= balance)
})
const selectedActionAmount = computed(() => (
  actionModal.type === 'deposit'
    ? Number(selectedDepositAmount.value || 0)
    : parseAmount(actionModal.amountText)
))
const balanceAfterAction = computed(() => (
  actionModal.type === 'deposit'
    ? activeWalletBalance.value + selectedActionAmount.value
    : activeWalletBalance.value - selectedActionAmount.value
))
const destinationBalanceAfterAction = computed(() => (
  actionModal.type === 'withdraw' && actionModal.destinationType === 'wallet' && selectedDestinationWallet.value
    ? Number(selectedDestinationWallet.value.balance || 0) + selectedActionAmount.value
    : 0
))
const actionAmountError = computed(() => {
  if (!actionModal.open) return ''
  if (!actionModal.walletId) return 'ابتدا یک کیف پول انتخاب کنید.'
  if (selectedActionAmount.value <= 0) return 'مبلغ باید بزرگ‌تر از صفر باشد.'
  if (actionModal.type === 'withdraw') {
    if (selectedActionAmount.value > activeWalletBalance.value) return 'مبلغ برداشت از موجودی کیف پول بیشتر است.'
    if (actionModal.destinationType === 'wallet') {
      if (!actionModal.destinationWalletId) return 'کیف پول مقصد را انتخاب کنید.'
      if (Number(actionModal.destinationWalletId) === Number(actionModal.walletId)) return 'کیف پول مقصد نمی‌تواند با مبدا یکی باشد.'
    }
  }
  return ''
})
const canSubmitAction = computed(() => !actionModal.submitting && !actionAmountError.value)

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
    state.error = resolveApiErrorMessage(error, 'بارگذاری کیف پول ناموفق بود.')
  } finally {
    state.loading = false
  }
}

const loadWalletOptions = async () => {
  state.optionsLoading = true
  try {
    const { data } = await api.get('/payments/wallet/options/')
    state.options = Array.isArray(data?.options) ? data.options : []
    state.optionsTenant = data?.tenant || null
    if (!optionModal.walletId && optionWallets.value.length) {
      optionModal.walletId = Number(optionWallets.value[0].id)
    }
  } catch (error) {
    state.error = resolveApiErrorMessage(error, 'بارگذاری آپشن‌ها ناموفق بود.')
  } finally {
    state.optionsLoading = false
  }
}

const setFilter = async (type) => {
  if (state.filterType === type && !state.error) return
  state.filterType = type
  await loadWalletDashboard()
}

const openActionModal = (type) => {
  clearMessages()
  if (type === 'withdraw' && withdrawButtonDisabled.value) {
    state.error = withdrawButtonCaption.value
    return
  }
  actionModal.open = true
  actionModal.type = type
  actionModal.destinationType = 'bank'
  actionModal.destinationWalletId = null
  actionModal.paymentMethod = 'card'
  actionModal.amountText = ''
  actionModal.description = ''
  actionModal.submitting = false
  const preferredWallet = selectedWallet.value
  const wallets = type === 'withdraw'
    ? state.wallets.filter((wallet) => Number(wallet.balance || 0) > 0)
    : state.wallets
  const fallbackWallet = (
    preferredWallet
    && wallets.some((wallet) => Number(wallet.id) === Number(preferredWallet.id))
  )
    ? preferredWallet
    : wallets[0]
  actionModal.walletId = fallbackWallet ? Number(fallbackWallet.id) : null
  actionModal.destinationWalletId = transferDestinationWallets.value[0]?.id ? Number(transferDestinationWallets.value[0].id) : null
  if (type === 'deposit') {
    selectedDepositAmount.value = dynamicDepositAmounts.value[0]?.value || 0
  } else if (dynamicWithdrawAmounts.value.length) {
    actionModal.amountText = money(dynamicWithdrawAmounts.value[0].value)
  }
}

const openOptionModal = (option) => {
  clearMessages()
  optionModal.open = true
  optionModal.featureKey = option?.feature_key || ''
  optionModal.paymentPlan = 'cash'
  optionModal.upfrontAmountText = money(option?.installment_upfront_amount || 0)
  optionModal.submitting = false
  const preferredWallet = selectedWallet.value
  const wallet = (
    preferredWallet
    && preferredWallet.wallet_type !== 'sms'
    && optionWallets.value.some((item) => Number(item.id) === Number(preferredWallet.id))
  )
    ? preferredWallet
    : optionWallets.value[0]
  optionModal.walletId = wallet ? Number(wallet.id) : null
}

const closeOptionModal = () => {
  optionModal.open = false
  optionModal.featureKey = ''
  optionModal.paymentPlan = 'cash'
  optionModal.upfrontAmountText = ''
  optionModal.submitting = false
}

const closeActionModal = () => {
  actionModal.open = false
  actionModal.destinationType = 'bank'
  actionModal.destinationWalletId = null
  actionModal.paymentMethod = 'card'
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

const openPaymentSupportTicket = () => {
  const amount = selectedActionAmount.value
  router.push({
    path: '/support',
    query: {
      prefill: 'wallet-card-payment',
      amount: amount > 0 ? String(amount) : '',
      wallet_id: actionModal.walletId ? String(actionModal.walletId) : '',
      wallet_name: activeWallet.value?.name || ''
    }
  })
}

const submitAction = async () => {
  clearMessages()
  if (actionAmountError.value) {
    state.error = actionAmountError.value
    return
  }
  const amount = selectedActionAmount.value

  actionModal.submitting = true
  try {
    const endpoint = actionModal.type === 'deposit' ? '/payments/wallet/deposit/start/' : '/payments/wallet/withdraw/'
    const payload = {
      wallet_id: actionModal.walletId,
      source_wallet_id: actionModal.walletId,
      destination_type: actionModal.type === 'withdraw' ? actionModal.destinationType : undefined,
      destination_wallet_id: actionModal.type === 'withdraw' && actionModal.destinationType === 'wallet'
        ? actionModal.destinationWalletId
        : undefined,
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
    state.error = resolveApiErrorMessage(error, 'ثبت تراکنش ناموفق بود.')
  } finally {
    actionModal.submitting = false
  }
}

const submitOptionPurchase = async () => {
  clearMessages()
  if (optionPurchaseError.value) {
    state.error = optionPurchaseError.value
    return
  }
  optionModal.submitting = true
  try {
    const { data } = await api.post('/payments/wallet/options/', {
      feature_key: optionModal.featureKey,
      wallet_id: optionModal.walletId,
      payment_plan: optionModal.paymentPlan,
      upfront_amount: optionModal.paymentPlan === 'installment' ? selectedOptionDebitAmount.value : undefined
    })
    state.successMessage = data?.detail || 'آپشن با موفقیت فعال شد.'
    if (data?.wallet) {
      const index = state.wallets.findIndex((wallet) => Number(wallet.id) === Number(data.wallet.id))
      if (index >= 0) state.wallets[index] = data.wallet
    }
    closeOptionModal()
    await Promise.all([loadWalletDashboard(), loadWalletOptions()])
  } catch (error) {
    state.error = resolveApiErrorMessage(error, 'خرید آپشن ناموفق بود.')
  } finally {
    optionModal.submitting = false
  }
}

const submitNextInstallmentPayment = async (option) => {
  clearMessages()
  if (!option?.feature_key || !option?.can_pay_next_installment) return
  payingInstallmentFeatureKey.value = option.feature_key
  try {
    const { data } = await api.post('/payments/wallet/options/', {
      action: 'pay_installment',
      feature_key: option.feature_key
    })
    state.successMessage = data?.detail || 'قسط بعدی با موفقیت پرداخت شد.'
    if (data?.wallet) {
      const index = state.wallets.findIndex((wallet) => Number(wallet.id) === Number(data.wallet.id))
      if (index >= 0) state.wallets[index] = data.wallet
    }
    await Promise.all([loadWalletDashboard(), loadWalletOptions()])
  } catch (error) {
    state.error = resolveApiErrorMessage(error, 'پرداخت قسط بعدی ناموفق بود.')
  } finally {
    payingInstallmentFeatureKey.value = ''
  }
}

watch(() => props.searchQuery, async () => {
  await loadWalletDashboard()
})

watch(() => [actionModal.walletId, actionModal.type, actionModal.destinationType], () => {
  if (!actionModal.open) return
  if (actionModal.type === 'deposit') {
    const exists = dynamicDepositAmounts.value.some((item) => item.value === Number(selectedDepositAmount.value))
    if (!exists) selectedDepositAmount.value = dynamicDepositAmounts.value[0]?.value || 0
    return
  }
  if (actionModal.destinationType === 'wallet') {
    const exists = transferDestinationWallets.value.some((wallet) => Number(wallet.id) === Number(actionModal.destinationWalletId))
    if (!exists) actionModal.destinationWalletId = transferDestinationWallets.value[0]?.id ? Number(transferDestinationWallets.value[0].id) : null
  }
  const currentAmount = parseAmount(actionModal.amountText)
  if (currentAmount <= 0 || currentAmount > activeWalletBalance.value) {
    actionModal.amountText = dynamicWithdrawAmounts.value.length ? money(dynamicWithdrawAmounts.value[0].value) : ''
  }
})

onMounted(async () => {
  applyGatewayResultMessage()
  await Promise.all([loadWalletDashboard(), loadWalletOptions()])
})
</script>

<style scoped>
.wallet-page{
  --wallet-border:#dde6f0;
  --wallet-panel:#ffffff;
  --wallet-panel-soft:#f8fafc;
  --wallet-text:#0f172a;
  --wallet-muted:#64748b;
  --wallet-primary:#315f9f;
  --wallet-primary-2:#5d8bb8;
  --wallet-success:#2f7d6b;
  --wallet-danger:#c85b5b;
  display:grid;
  gap:18px
}
.wallet-alert{border-radius:18px;padding:14px 16px;font-weight:700;border:1px solid transparent;box-shadow:0 16px 34px rgba(15,23,42,.05)}
.wallet-alert-error{background:#fff1f2;color:#9f1239;border-color:#fecdd3}
.wallet-alert-success{background:#ecfdf5;color:#166534;border-color:#bbf7d0}
.wallet-hero-shell{display:grid;grid-template-columns:370px minmax(0,1fr);gap:22px;align-items:stretch}
.wallet-shortcuts{background:linear-gradient(180deg,#ffffff 0%,#f8fbfe 60%,#f3f7fb 100%);border:1px solid var(--wallet-border);border-radius:30px;padding:22px;box-shadow:0 18px 42px rgba(15,23,42,.05);position:relative;overflow:hidden}
.wallet-shortcuts::before{content:'';position:absolute;inset:-90px auto auto -80px;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,rgba(99,132,171,.10),rgba(99,132,171,0) 70%)}
.wallet-shortcuts::after{content:'';position:absolute;left:18px;bottom:-48px;width:170px;height:170px;border-radius:50%;background:radial-gradient(circle,rgba(148,163,184,.09),rgba(148,163,184,0) 72%)}
.shortcut-head{position:relative;z-index:1}
.shortcut-head h3{margin:0;color:var(--wallet-text);font-size:18px;font-weight:800}
.shortcut-head p{margin:8px 0 0;color:var(--wallet-muted);font-size:12px}
.shortcut-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:22px}
.shortcut-card{border:1px solid #e1e8f0;border-radius:20px;padding:16px 15px;background:linear-gradient(180deg,#fdfefe,#f4f7fb);display:grid;gap:9px;text-align:right;cursor:pointer;transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease,background .2s ease;position:relative;z-index:1}
.shortcut-card:hover{transform:translateY(-2px);box-shadow:0 14px 28px rgba(15,23,42,.06);border-color:#c8d5e2;background:linear-gradient(180deg,#ffffff,#f6f9fc)}
.shortcut-card:disabled,.hero-action:disabled{opacity:.55;cursor:not-allowed;filter:saturate(.72)}
.shortcut-card:disabled:hover,.hero-action:disabled:hover{transform:none;box-shadow:none}
.shortcut-primary{background:linear-gradient(135deg,#466b9f,#5d8bb8 58%,#7ca7bf);color:#fff;border-color:transparent}
.shortcut-primary strong,.shortcut-primary small,.shortcut-primary .shortcut-icon{color:#fff}
.shortcut-icon{width:42px;height:42px;border-radius:14px;background:linear-gradient(180deg,#edf3f8,#e2e8f0);color:#315f9f;display:inline-flex;align-items:center;justify-content:center;font-size:21px;font-weight:800;box-shadow:inset 0 1px 0 rgba(255,255,255,.7)}
.shortcut-card strong{font-size:16px;color:var(--wallet-text);font-weight:800}
.shortcut-card small{color:var(--wallet-muted);font-size:12px}
.wallet-hero{position:relative;overflow:hidden;border-radius:30px;padding:24px 28px;background:linear-gradient(135deg,#415a77 0%,#557a95 38%,#6b96a8 100%);box-shadow:0 20px 46px rgba(65,90,119,.18);display:grid;gap:22px;min-height:290px;border:1px solid rgba(255,255,255,.14)}
.wallet-hero::before{content:'';position:absolute;inset:auto auto -120px -80px;width:280px;height:280px;border-radius:50%;background:rgba(255,255,255,.08);filter:blur(8px)}
.wallet-hero::after{content:'';position:absolute;top:-70px;left:22%;width:240px;height:240px;border-radius:50%;background:rgba(255,255,255,.06)}
.hero-top,.hero-main,.hero-actions{position:relative;z-index:1}
.hero-top{display:flex;justify-content:space-between;align-items:center;gap:16px}
.hero-badge{display:inline-flex;align-items:center;gap:10px;color:#eff6ff;font-weight:700;font-size:13px}
.hero-icon{width:42px;height:42px;border-radius:14px;background:rgba(255,255,255,.14);display:inline-flex;align-items:center;justify-content:center;font-size:22px}
.hero-status{padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.14);color:#f8fafc;font-weight:700;font-size:11px;box-shadow:inset 0 1px 0 rgba(255,255,255,.12)}
.hero-status.danger{background:rgba(127,29,29,.22);color:#fee2e2}
.hero-main{display:flex;justify-content:space-between;align-items:flex-start;gap:20px}
.hero-label{margin:0;color:#dbe7f1;font-size:14px}
.hero-main h2{margin:10px 0 8px;color:#fff;font-size:42px;line-height:1.05;font-weight:850}
.hero-main h2 span{font-size:20px;font-weight:700}
.hero-sub{margin:0;color:#e5edf5;font-size:13px;max-width:540px}
.hero-orb{width:140px;height:140px;border-radius:50%;background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.34),rgba(255,255,255,.04) 58%,rgba(255,255,255,0) 72%)}
.hero-actions{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin-top:auto}
.hero-action{height:54px;min-width:210px;border-radius:18px;border:0;font-size:17px;font-weight:800;cursor:pointer;padding:0 22px;transition:transform .2s ease,box-shadow .2s ease,background .2s ease}
.hero-action:hover{transform:translateY(-2px)}
.hero-action-light{background:linear-gradient(180deg,#ffffff,#eef2f7);color:#35506b;box-shadow:0 14px 28px rgba(15,23,42,.12)}
.hero-action-ghost{background:rgba(255,255,255,.1);color:#fff;border:1px solid rgba(255,255,255,.2);backdrop-filter:blur(10px)}
.wallet-summary-board{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.summary-tile{background:linear-gradient(180deg,#ffffff,#f8fafc);border:1px solid var(--wallet-border);border-radius:20px;padding:16px 18px;box-shadow:0 10px 24px rgba(15,23,42,.04);position:relative;overflow:hidden;min-height:132px}
.summary-tile::before{content:'';position:absolute;top:0;right:0;left:0;height:3px;background:linear-gradient(90deg,#7aa2c7,#8db6a9)}
.summary-tile small{display:block;color:#64748b;font-size:12px}
.summary-tile strong{display:block;margin-top:10px;color:#0f172a;font-size:24px;line-height:1.15}
.summary-tile strong.danger{color:#b91c1c}
.summary-tile span{display:block;margin-top:6px;color:#94a3b8;font-size:12px}
.accent-tile{background:linear-gradient(135deg,#f3f8fd,#edf7f2)}
.soft-tile{background:linear-gradient(135deg,#fcfaf7,#f8f4f4)}
.sms-tile{background:radial-gradient(circle at top left,rgba(59,130,246,.16),transparent 34%),linear-gradient(135deg,#f8fbff,#eef6ff);border-color:#cfe0f7}
.sms-tile.low{background:radial-gradient(circle at top left,rgba(249,115,22,.18),transparent 34%),linear-gradient(135deg,#fff8f1,#fff2e8);border-color:#fdc48b}
.sms-tile strong{font-size:30px;margin-top:14px}
.sms-tile-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.sms-balance-caption{margin:10px 0 0;color:#516072;font-size:12px;line-height:1.9;max-width:28ch}
.sms-state-pill,.sms-topup-chip{display:inline-flex;align-items:center;justify-content:center;width:max-content}
.sms-state-pill{height:28px;padding:0 10px;border-radius:999px;background:rgba(15,92,192,.1);color:#0f5cc0;font-size:11px;font-weight:900}
.sms-state-pill.low{background:rgba(234,88,12,.12);color:#c2410c}
.sms-topup-chip{margin-top:12px;padding:7px 11px;border-radius:999px;background:rgba(255,255,255,.86);border:1px solid rgba(148,163,184,.22);color:#35506b;font-size:11px;font-weight:800}
.warning-strip{display:flex;align-items:center;gap:12px;background:#fff7ed;border:1px solid #fdba74;border-radius:18px;padding:14px 16px;color:#c2410c}
.warning-dot{width:10px;height:10px;border-radius:50%;background:#f97316;box-shadow:0 0 0 6px rgba(249,115,22,.14)}
.options-panel{background:linear-gradient(180deg,#ffffff,#f8fbfc);border:1px solid var(--wallet-border);border-radius:28px;padding:22px;box-shadow:0 14px 34px rgba(15,23,42,.05)}
.options-head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:18px}
.options-head p{margin:0 0 8px;color:#94a3b8;font-size:12px;font-weight:800}
.options-head h2{margin:0;color:#0f172a;font-size:28px}
.options-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
.option-card{--option-accent:#315f9f;display:grid;gap:14px;padding:18px;border:1px solid #dbe5f0;border-radius:22px;background:linear-gradient(180deg,#fff,#f8fafc);box-shadow:0 12px 26px rgba(15,23,42,.04);position:relative;overflow:hidden}
.option-card::before{content:'';position:absolute;inset:0 0 auto 0;height:4px;background:var(--option-accent)}
.option-card.active{background:linear-gradient(180deg,#f7fffb,#f2fbf8);border-color:color-mix(in srgb,var(--option-accent) 35%,#dbe5f0)}
.option-card.unavailable{background:linear-gradient(180deg,#fcfcfd,#f5f7fa);border-color:#d8e0ea}
.option-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.option-kicker{display:block;color:var(--option-accent);font-size:11px;font-weight:900;margin-bottom:6px}
.option-card h3{margin:0;color:#0f172a;font-size:20px}
.option-card p{margin:0;color:#64748b;font-size:12px;line-height:1.9}
.option-status{display:inline-flex;align-items:center;height:30px;padding:0 11px;border-radius:999px;background:#eef2f7;color:#475569;font-size:11px;font-weight:900;white-space:nowrap}
.option-status.enabled{background:#dcfce7;color:#166534}
.option-card.unavailable .option-status{background:#e2e8f0;color:#475569}
.option-unavailable-box{display:grid;gap:7px;padding:13px 14px;border:1px dashed #cbd5e1;border-radius:16px;background:linear-gradient(180deg,#ffffff,#f8fafc)}
.option-unavailable-box strong{color:#334155;font-size:14px}
.option-unavailable-box small{color:#64748b;font-size:12px;line-height:1.9}
.option-price-row,.option-installment-row{display:grid;gap:5px;padding:12px 13px;border:1px solid #e1e8f0;border-radius:16px;background:#fff}
.option-price-row span,.option-installment-row span,.option-installment-row small{color:#64748b;font-size:12px}
.option-price-row strong,.option-installment-row strong{color:#0f172a;font-size:17px}
.option-price-stack{display:grid;gap:10px}
.option-live-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.option-live-stat{padding:12px 13px;border:1px solid #d9e7df;border-radius:16px;background:linear-gradient(180deg,#ffffff,#f6fbf8);display:grid;gap:5px}
.option-live-stat-head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.option-live-stat span{color:#64748b;font-size:12px}
.option-live-stat strong{color:#0f172a;font-size:15px;line-height:1.7}
.option-inline-pay-btn{height:28px;padding:0 11px;border:0;border-radius:999px;background:linear-gradient(135deg,var(--option-accent),color-mix(in srgb,var(--option-accent) 75%,#ffffff));color:#fff;font-size:11px;font-weight:900;cursor:pointer;white-space:nowrap}
.option-inline-pay-btn:disabled{opacity:.65;cursor:not-allowed}
.option-progress-block{display:grid;gap:9px;padding:14px;border:1px solid #d9e7df;border-radius:18px;background:linear-gradient(180deg,#fcfffd,#f4fbf7)}
.option-progress-head{display:flex;align-items:center;justify-content:space-between;gap:10px}
.option-progress-head span{color:#64748b;font-size:12px;font-weight:800}
.option-progress-head strong{color:#166534;font-size:13px}
.option-progress-bar{height:9px;border-radius:999px;background:#dbe7df;overflow:hidden}
.option-progress-bar span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--option-accent),color-mix(in srgb,var(--option-accent) 58%,#ffffff))}
.option-progress-block small{color:#527066;font-size:11px;line-height:1.9}
.option-buy-btn{height:46px;border:0;border-radius:15px;background:linear-gradient(135deg,var(--option-accent),color-mix(in srgb,var(--option-accent) 72%,#ffffff));color:#fff;font-weight:900;cursor:pointer}
.option-buy-btn:disabled{background:#e2e8f0;color:#64748b;cursor:not-allowed}
.option-purchase-modal{--option-accent:#315f9f}
.option-purchase-hero{padding:18px;border-radius:22px;background:linear-gradient(135deg,color-mix(in srgb,var(--option-accent) 12%,#ffffff),#ffffff);border:1px solid color-mix(in srgb,var(--option-accent) 24%,#dbe5f0)}
.option-purchase-hero small{display:block;color:var(--option-accent);font-size:12px;font-weight:900;margin-bottom:8px}
.option-purchase-hero strong{display:block;color:#0f172a;font-size:24px}
.option-purchase-hero p{margin:8px 0 0;color:#475569;font-size:12px;line-height:1.8}
.payment-plan-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.payment-plan-card{border:1px solid #dbe5f0;border-radius:18px;background:#fff;padding:15px;display:grid;gap:7px;text-align:right;cursor:pointer}
.payment-plan-card.active{border-color:var(--wallet-success);background:#f0fdf4;box-shadow:0 14px 28px rgba(22,101,52,.08)}
.payment-plan-card strong{color:#0f172a;font-size:15px}
.payment-plan-card span{color:#166534;font-size:16px;font-weight:900}
.payment-plan-card small{color:#64748b;font-size:12px;line-height:1.7}
.upfront-input-box small{color:#64748b;font-size:12px;line-height:1.8;font-weight:700}
.installment-live-preview{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.installment-live-preview div{padding:13px 14px;border:1px solid #e1e8f0;border-radius:16px;background:linear-gradient(180deg,#fff,#f8fafc);display:grid;gap:6px}
.installment-live-preview span{color:#64748b;font-size:12px;font-weight:800}
.installment-live-preview strong{color:#0f172a;font-size:17px}
.history-panel{background:linear-gradient(180deg,#ffffff,#f9fbfc);border:1px solid var(--wallet-border);border-radius:28px;padding:22px;box-shadow:0 14px 34px rgba(15,23,42,.05)}
.history-head{display:flex;justify-content:space-between;align-items:flex-end;gap:18px;margin-bottom:18px}
.history-title-wrap p{margin:0 0 8px;color:#94a3b8;font-size:12px;font-weight:700}
.history-head h2{margin:0;color:#0f172a;font-size:30px;line-height:1}
.history-controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.wallet-switch{height:42px;border:1px solid var(--wallet-border);border-radius:14px;padding:0 14px;background:#fff;color:#0f172a;box-shadow:inset 0 1px 2px rgba(15,23,42,.03)}
.filter-pill{display:flex;gap:4px;padding:5px;background:linear-gradient(180deg,#f1f5f9,#eaf0f5);border-radius:999px;border:1px solid #dde7f3}
.filter-pill button,.refresh-btn,.close-btn,.submit-btn,.quick-amounts button{border:0;cursor:pointer}
.filter-pill button{height:38px;padding:0 15px;border-radius:999px;background:transparent;color:#475569;font-weight:700}
.filter-pill button.active{background:linear-gradient(180deg,#ffffff,#f8fafc);color:#35506b;box-shadow:0 8px 18px rgba(148,163,184,.12)}
.refresh-btn{height:42px;padding:0 18px;border-radius:14px;background:linear-gradient(180deg,#f1f5f9,#e2e8f0);color:#35506b;font-weight:800;box-shadow:inset 0 1px 0 rgba(255,255,255,.65)}
.history-state{padding:42px 12px;text-align:center;color:#64748b}
.tx-list{display:grid;gap:16px}
.tx-item{display:grid;grid-template-columns:46px minmax(0,1fr) auto;align-items:center;gap:18px;padding:18px 20px;border:1px solid #e2e8f0;border-radius:22px;background:linear-gradient(180deg,#fff,#fafcfd);box-shadow:0 12px 24px rgba(15,23,42,.04);transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease}
.tx-item:hover{transform:translateY(-1px);box-shadow:0 16px 28px rgba(15,23,42,.06);border-color:#d4dee8}
.tx-expand{width:36px;height:36px;border:0;border-radius:50%;background:linear-gradient(180deg,#f8fafc,#eef2f6);color:#1e293b;font-size:30px;line-height:1;cursor:pointer}
.tx-title-row{display:flex;align-items:center;justify-content:space-between;gap:12px}
.tx-title-row h3{margin:0;color:#0f172a;font-size:15px}
.tx-chip{display:inline-flex;align-items:center;height:28px;padding:0 12px;border-radius:999px;font-size:11px;font-weight:800}
.tx-chip-in{background:#dcfce7;color:#166534}
.tx-chip-out{background:#fee2e2;color:#b91c1c}
.tx-meta{margin:10px 0 0;color:#94a3b8;font-size:12px;display:flex;gap:8px;flex-wrap:wrap}
.separate{color:#cbd5e1}
.tx-value-col{display:flex;align-items:center;gap:16px}
.tx-value{font-size:17px;font-weight:800;white-space:nowrap}
.tx-value-in{color:#0f766e}
.tx-value-out{color:#dc2626}
.tx-icon-box{width:58px;height:58px;border-radius:18px;display:inline-flex;align-items:center;justify-content:center;font-size:28px;font-weight:800}
.tx-icon-box-in{background:linear-gradient(180deg,#e7f7f1,#d9f1ea);color:#2f7d6b}
.tx-icon-box-out{background:linear-gradient(180deg,#fce8e8,#f9dddd);color:#c85b5b}
.wallet-modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.44);backdrop-filter:blur(12px);display:flex;align-items:flex-start;justify-content:center;z-index:120;padding:20px;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;-webkit-overflow-scrolling:touch}
.wallet-modal{width:min(560px,100%);max-height:calc(100dvh - 40px);background:#fff;border-radius:24px;overflow:hidden;box-shadow:0 18px 34px rgba(15,23,42,.10);border:none;display:flex;flex-direction:column;min-height:0;margin:auto 0}
.financial-action-modal{width:min(720px,100%)}
.wallet-modal-deposit{--wallet-modal-accent:#9d6cff;--wallet-modal-accent-soft:#efe4ff;--wallet-modal-accent-bg:linear-gradient(135deg,#fbf8ff,#f4edff)}
.wallet-modal-withdraw{--wallet-modal-accent:#c85b5b;--wallet-modal-accent-soft:#f4d7d7;--wallet-modal-accent-bg:linear-gradient(135deg,#fdf8f8,#fbf1f1)}
.wallet-modal-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding:22px 24px 18px;border-bottom:none;background:linear-gradient(135deg,#f8fbff,#ffffff 52%,color-mix(in srgb,var(--wallet-modal-accent,#315f9f) 10%,#ffffff))}
.wallet-modal-title-row{display:flex;align-items:center;gap:14px;min-width:0}
.wallet-modal-symbol{width:50px;height:50px;border-radius:16px;display:inline-flex;align-items:center;justify-content:center;background:color-mix(in srgb,var(--wallet-modal-accent) 12%,#ffffff);border:none;color:var(--wallet-modal-accent);font-size:24px;font-weight:900}
.wallet-modal-title-wrap p{margin:0 0 6px;color:#64748b;font-size:12px;font-weight:800}
.wallet-modal-head h3{margin:0;font-size:22px;color:#0f172a}
.close-btn{width:42px;height:42px;border-radius:14px;background:#fff;color:#334155;font-size:22px;line-height:1;transition:background .2s ease,color .2s ease,transform .2s ease,border-color .2s ease;border:none}
.close-btn:hover{background:#ffffff;color:#0f172a;transform:translateY(-1px);border-color:transparent}
.wallet-modal-body{padding:22px;display:grid;gap:14px;overflow-y:auto;overflow-x:hidden;min-height:0;-webkit-overflow-scrolling:touch;background:linear-gradient(180deg,#f7f1ff,#ffffff 28%)}
.wallet-modal-highlight{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:18px;border-radius:20px;background:#fff;border:1px solid #efe4ff;box-shadow:0 14px 30px rgba(157,108,255,.08)}
.wallet-modal-highlight small{display:block;color:#64748b;font-size:12px;margin-bottom:6px}
.wallet-modal-highlight strong{display:block;font-size:30px;color:#0f172a;line-height:1.15}
.wallet-modal-highlight p{margin:8px 0 0;color:#475569;font-size:12px;font-weight:800}
.wallet-modal-highlight-badge{display:inline-flex;align-items:center;justify-content:center;height:38px;padding:0 15px;border-radius:999px;background:#f4edff;color:var(--wallet-modal-accent);font-weight:900;border:none;box-shadow:none}
.wallet-modal-section{display:grid;gap:14px;padding:16px;border:1px solid #efe4ff;border-radius:20px;background:#fff;box-shadow:0 12px 28px rgba(157,108,255,.06)}
.wallet-modal-section-soft{background:#fff}
.wallet-modal-section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap}
.wallet-modal-section-head strong{color:#0f172a;font-size:15px}
.wallet-modal-section-head span{color:#64748b;font-size:12px;font-weight:700}
.wallet-destination-section{background:#fff}
.destination-toggle{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;padding:5px;border:none;border-radius:18px;background:#f8fafc}
.destination-toggle button{border:none;border-radius:14px;background:transparent;padding:12px 14px;display:grid;gap:5px;text-align:right;cursor:pointer;transition:background .2s ease,border-color .2s ease,transform .2s ease}
.destination-toggle button:hover{background:#fff;transform:translateY(-1px)}
.destination-toggle button.active{background:#fff;border-color:transparent}
.destination-toggle span{color:#0f172a;font-size:14px;font-weight:900}
.destination-toggle small{color:#64748b;font-size:11px;font-weight:800}
.wallet-choice-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.wallet-choice-card{min-height:92px;border:1px solid #efe4ff;border-radius:16px;background:#fbf8ff;padding:14px 15px;display:grid;gap:6px;text-align:right;cursor:pointer;transition:border-color .2s ease,transform .2s ease,background .2s ease}
.wallet-choice-card:hover{transform:translateY(-1px);border-color:#dbc8ff;background:#fff}
.wallet-choice-card.active{background:#f1e8ff;border-color:#c9adff}
.destination-card.active{background:color-mix(in srgb,#315f9f 8%,#ffffff);border-color:transparent}
.wallet-choice-card small{color:#94a3b8;font-size:11px;font-weight:800}
.wallet-choice-card strong{color:#0f172a;font-size:14px}
.wallet-choice-card span{color:var(--wallet-modal-accent);font-size:16px;font-weight:900}
.wallet-modal-body label{display:grid;gap:8px;color:#334155;font-weight:700}
.wallet-modal-body label span{font-size:13px}
.wallet-inline-select{margin-top:-4px}
.wallet-modal-body input,.wallet-modal-body select{height:52px;border:1px solid #efe4ff;border-radius:16px;padding:0 16px;background:#fbf8ff;color:#0f172a;font-size:14px;outline:none;transition:border-color .2s ease,box-shadow .2s ease,background .2s ease}
.wallet-modal-body input:focus,.wallet-modal-body select:focus{border-color:#c9adff;box-shadow:0 0 0 4px rgba(201,173,255,.18);background:#fff}
.quick-amounts{display:flex;gap:8px;flex-wrap:wrap}
.quick-amounts button{min-width:132px;min-height:60px;padding:10px 14px;border-radius:16px;background:#fff;color:#0f4aa8;font-weight:800;border:none;display:grid;gap:4px;text-align:right;justify-items:start;transition:border-color .2s ease,transform .2s ease,background .2s ease}
.quick-amounts button small{color:#64748b;font-size:11px;font-weight:800}
.quick-amounts button strong{color:#0f172a;font-size:15px;line-height:1.4}
.quick-amounts button:hover{background:#eff6ff;border-color:transparent;transform:translateY(-1px)}
.wallet-inline-warning{display:block;padding:11px 13px;border:none;border-radius:14px;background:#fff1f2;color:#9f1239;font-size:12px;font-weight:800;line-height:1.7}
.wallet-balance-preview-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.wallet-balance-preview{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:15px 16px;border:none;border-radius:16px;background:#f0fdf4;color:#166534}
.wallet-balance-preview.destination{border-color:transparent;background:#eff6ff;color:#1d4ed8}
.wallet-balance-preview.danger{border-color:transparent;background:#fff1f2;color:#9f1239}
.wallet-balance-preview span{font-size:12px;font-weight:800}
.wallet-balance-preview strong{font-size:16px}
.gateway-amounts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.gateway-amounts button{min-height:86px;border:1px solid #efe4ff;border-radius:16px;background:#fbf8ff;color:#0f172a;font-weight:800;cursor:pointer;padding:15px 14px;display:grid;gap:8px;justify-items:start;text-align:right;transition:border-color .2s ease,transform .2s ease,background .2s ease}
.gateway-amounts button strong{font-size:18px;line-height:1;color:#0f172a}
.gateway-amounts button span{font-size:12px;color:#64748b}
.gateway-amounts button:hover{transform:translateY(-1px);border-color:#dbc8ff;background:#fff}
.gateway-amounts button.active{background:#f1e8ff;border-color:#c9adff}
.gateway-amounts button.active strong,.gateway-amounts button.active span{color:var(--wallet-modal-accent)}
.deposit-method-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.deposit-method-card{min-height:82px;border:1px solid #efe4ff;border-radius:16px;background:#fbf8ff;color:#0f172a;display:grid;gap:6px;text-align:right;padding:14px;cursor:pointer}
.deposit-method-card.active{background:#f1e8ff;border-color:#c9adff}
.deposit-method-card.disabled{opacity:.54;cursor:not-allowed;background:#f8fafc;color:#94a3b8}
.deposit-method-card span{font-size:12px;color:#64748b}
.company-card-box{display:grid;gap:8px;padding:18px;border-radius:18px;background:linear-gradient(135deg,#ffffff,#f4edff);border:1px solid #dbc8ff}
.company-card-box small{color:#64748b;font-size:12px}
.company-card-box strong{font-size:23px;letter-spacing:.08em;color:#7c3aed;direction:ltr;text-align:left}
.company-card-box span{color:#334155;font-weight:800}
.card-payment-instruction{margin:0;color:#475569;line-height:1.9;font-size:13px}
.support-ticket-btn{min-height:52px;border:none;border-radius:16px;background:#9d6cff;color:#fff;font-weight:900;cursor:pointer}
.wallet-note{padding:15px 16px;border-radius:18px;background:#fbf8ff;color:#334155;border:1px solid #efe4ff;line-height:1.8}
.submit-btn{height:54px;border-radius:16px;color:#fff;font-weight:800;box-shadow:none;transition:transform .2s ease,filter .2s ease,opacity .2s ease}
.submit-btn:hover:not(:disabled){transform:translateY(-1px);filter:saturate(1.06)}
.submit-btn:disabled{opacity:.7;cursor:not-allowed}
.submit-deposit{background:linear-gradient(135deg,#3b7f71,#6ca69a)}
.submit-withdraw{background:linear-gradient(135deg,#b85b5b,#d98383)}
@media (max-width:1200px){.wallet-hero-shell{grid-template-columns:1fr}.wallet-summary-board{grid-template-columns:repeat(2,minmax(0,1fr))}.options-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:900px){.history-head,.options-head,.wallet-modal-section-head{flex-direction:column;align-items:stretch}.history-head h2,.options-head h2{font-size:28px}.hero-main{flex-direction:column}.hero-main h2{font-size:44px}.hero-action{min-width:0;width:100%;font-size:22px;height:60px}.gateway-amounts,.deposit-method-grid,.payment-plan-grid,.wallet-choice-grid,.installment-live-preview,.option-live-grid,.destination-toggle,.wallet-balance-preview-grid{grid-template-columns:1fr}}
@media (max-width:640px){.shortcut-grid,.wallet-summary-board,.options-grid{grid-template-columns:1fr}.tx-item{grid-template-columns:1fr;justify-items:start}.tx-value-col{width:100%;justify-content:space-between}.history-controls,.hero-actions,.hero-top,.tx-title-row,.wallet-modal-title-row{flex-direction:column;align-items:stretch}.filter-pill{width:100%;justify-content:space-between;flex-wrap:wrap}.wallet-modal-overlay{padding:12px}.wallet-modal{max-height:calc(100dvh - 24px)}.wallet-modal-head,.wallet-modal-body{padding:16px}.wallet-modal-highlight{align-items:flex-start;flex-direction:column}.wallet-modal-highlight strong{font-size:21px}.wallet-modal-symbol{width:46px;height:46px;border-radius:15px;font-size:20px}.wallet-modal-section{padding:14px;border-radius:20px}.quick-amounts button{width:100%}.tx-value{white-space:normal}.hero-main h2{font-size:34px}.wallet-shortcuts,.wallet-hero,.history-panel,.options-panel{padding:16px}.option-progress-head{align-items:flex-start;flex-direction:column}}
</style>
