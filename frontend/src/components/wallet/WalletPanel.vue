<template>
  <section class="wallet-page" dir="rtl">
    <div v-if="state.error" class="wallet-alert wallet-alert-error">{{ state.error }}</div>
    <div v-if="state.successMessage" class="wallet-alert wallet-alert-success">{{ state.successMessage }}</div>
    <section v-if="state.licenseStatus?.notice" class="license-lock-banner" :class="{ locked: state.licenseStatus.is_locked }">
      <strong>{{ state.licenseStatus.is_locked ? 'نرم‌افزار قفل است' : 'یادآوری پرداخت نرم‌افزار' }}</strong>
      <p>{{ state.licenseStatus.notice }}</p>
      <span v-if="state.licenseStatus.amount_due">مبلغ سررسید: {{ moneyWithUnit(state.licenseStatus.amount_due) }}</span>
    </section>

    <section class="wallet-overview">
      <aside class="wallet-shortcuts">
        <div class="shortcut-head">
          <h3>دسترسی سریع</h3>
          <p>مدیریت سریع عملیات مالی</p>
        </div>
        <div class="shortcut-grid">
          <button class="shortcut-card shortcut-primary" type="button" :disabled="!canDepositWalletAction || !hasDepositWallet" @click="openActionModal('deposit')">
            <span class="shortcut-icon">+</span>
            <strong>شارژ حساب</strong>
            <small>{{ depositShortcutCaption }}</small>
          </button>
          <button class="shortcut-card" type="button" :disabled="withdrawButtonDisabled" @click="openActionModal('withdraw')">
            <span class="shortcut-icon">↗</span>
            <strong>{{ withdrawButtonTitle }}</strong>
            <small>{{ withdrawButtonCaption }}</small>
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
      </section>

      <article class="summary-tile sms-tile" :class="{ low: smsLow }">
        <div class="sms-tile-head">
          <small><span class="sms-tile-mark">✉</span> موجودی پیامک</small>
          <span class="sms-state-pill" :class="{ low: smsLow }">{{ smsBalanceStateLabel }}</span>
        </div>
        <strong :class="{ danger: smsLow }">{{ moneyWithUnit(state.summary.sms_balance) }}</strong>
        <p class="sms-balance-caption">{{ smsBalanceHint }}</p>
        <span class="sms-topup-chip">{{ suggestedSmsTopUpLabel }}</span>
        <div class="sms-quick-topup">
          <input
            :value="smsTopUpAmountText"
            type="text"
            inputmode="numeric"
            placeholder="مبلغ (تومان)"
            :disabled="smsTopUpSubmitting || !canWithdrawWalletAction"
            @input="onSmsTopUpAmountInput"
          />
          <button
            type="button"
            class="sms-quick-topup-btn"
            :disabled="smsTopUpDisabled"
            @click="submitSmsTopUpFromMain"
          >
            {{ smsTopUpSubmitting ? 'در حال انتقال...' : 'برداشت از کیف پول اصلی' }}
          </button>
        </div>
      </article>

      <div class="summary-money-row">
        <article class="summary-tile accent-tile">
          <small>جمع واریزی‌ها</small>
          <strong>{{ moneyWithUnit(state.summary.deposits_total) }}</strong>
        </article>
        <article class="summary-tile soft-tile">
          <small>جمع برداشت‌ها</small>
          <strong>{{ moneyWithUnit(state.summary.withdrawals_total) }}</strong>
        </article>
      </div>
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
          v-for="option in sortedWalletOptions"
          :key="option.feature_key"
          class="option-card"
          :class="{
            active: option.is_active,
            unavailable: option.is_available === false,
            locked: option.installment_is_locked,
            purchased: option.is_active && option.is_available !== false,
            'not-purchased': !option.is_active && option.is_available !== false
          }"
          :style="{ '--option-accent': option.accent || '#315f9f' }"
          role="button"
          tabindex="0"
          @click="onOptionCardActivate(option)"
          @keydown.enter.prevent="onOptionCardActivate(option)"
        >
          <div class="option-card-head">
            <div>
              <span class="option-kicker">{{ option.personalized_title }}</span>
              <h3>{{ option.title }}</h3>
            </div>
            <span
              class="option-status"
              :class="{
                enabled: option.is_active && option.is_available !== false,
                locked: option.installment_is_locked,
                buyable: !option.is_active && option.is_available !== false
              }"
            >
              {{ optionStatusText(option) }}
            </span>
          </div>
          <p class="option-card-desc">{{ option.description }}</p>
          <div class="option-card-compact-meta">
            <span v-if="option.is_active && option.is_available !== false">
              پرداخت‌شده {{ moneyWithUnit(option.paid_amount) }}
            </span>
            <span v-else-if="option.is_available !== false">
              از {{ moneyWithUnit(option.cash_amount || option.total_amount) }}
            </span>
            <span v-else>{{ option.unavailable_message || 'فعلا ارائه نمی‌شود' }}</span>
          </div>
          <div v-if="option.is_available === false" class="option-unavailable-box option-card-details">
            <strong>{{ option.status_label || 'در دسترس نمی‌باشد' }}</strong>
            <small>{{ option.unavailable_message || 'این آپشن هنوز ارائه نمی‌شود.' }}</small>
          </div>
          <div v-if="option.is_active && option.is_available !== false" class="option-live-grid option-card-details">
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
                  @click.stop="submitNextInstallmentPayment(option)"
                >
                  {{ payingInstallmentFeatureKey === option.feature_key ? 'در حال پرداخت...' : 'پرداخت' }}
                </button>
              </div>
              <strong>{{ option.next_installment_due_at ? formatShortDate(option.next_installment_due_at) : formatShortDate(option.purchased_at) }}</strong>
            </article>
          </div>
          <div v-else-if="option.is_available !== false" class="option-price-stack option-card-details">
            <div class="option-price-row">
              <span>قیمت نقدی</span>
              <strong>{{ moneyWithUnit(option.cash_amount) }}</strong>
            </div>
            <div class="option-installment-row">
              <span>{{ option.cash_only ? 'فقط نقدی' : `اقساط ${Number(option.installment_months || 0).toLocaleString('fa-IR')} ماهه` }}</span>
              <strong>{{ moneyWithUnit(option.monthly_installment_amount) }}</strong>
              <small>پیش‌پرداخت: {{ moneyWithUnit(option.installment_upfront_amount) }}</small>
            </div>
          </div>
          <div v-if="option.installment_is_locked" class="option-lock-note option-card-details">
            <strong>این بخش قفل شده است</strong>
            <small>{{ option.installment_lock_notice || 'قسط سررسید این آپشن پرداخت نشده است. برای باز شدن دسترسی، قسط را پرداخت کنید.' }}</small>
          </div>
          <div v-if="option.is_active && option.is_available !== false" class="option-progress-block option-card-details">
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
            class="option-buy-btn option-card-details"
            type="button"
            :disabled="option.is_active || option.is_available === false"
            @click.stop="openOptionModal(option)"
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

      <div class="period-insight-row">
        <div class="period-range-block">
          <div class="period-range-chips" role="tablist" aria-label="بازه زمانی">
            <button
              v-for="option in periodRangeOptions"
              :key="option.key"
              type="button"
              class="period-chip"
              :class="{ active: periodFilters.rangeKey === option.key }"
              @click="setPeriodRange(option.key)"
            >
              {{ option.label }}
            </button>
          </div>
          <div v-if="periodFilters.rangeKey === 'custom'" class="period-custom-dates">
            <BaseDatePicker v-model="periodFilters.startJalali" placeholder="شروع شمسی" />
            <BaseDatePicker v-model="periodFilters.endJalali" placeholder="پایان شمسی" />
          </div>
        </div>
        <article class="period-stat-card">
          <span>پیامک ارسال‌شده</span>
          <strong>{{ Number(state.periodSummary.sms_sent_count || 0).toLocaleString('fa-IR') }}</strong>
        </article>
        <article class="period-stat-card">
          <span>واریز / برداشت بازه</span>
          <strong class="period-flow-values">
            <em class="in">+{{ money(state.periodSummary.deposits_total) }}</em>
            <em class="out">-{{ money(state.periodSummary.withdrawals_total) }}</em>
          </strong>
        </article>
      </div>

      <div v-if="state.loading" class="history-state">
        <BaseSpinner size="62px" color="#0f5cc0" ball-color="#5fb7ff" label="در حال بارگذاری اطلاعات کیف پول..." />
      </div>
      <div v-else-if="!filteredTransactions.length" class="history-state">تراکنشی برای نمایش وجود ندارد.</div>

      <div v-else class="tx-list">
        <article v-for="tx in filteredTransactions" :key="tx.id" class="tx-item">
          <div class="tx-icon-box" :class="tx.direction === 'in' ? 'tx-icon-box-in' : 'tx-icon-box-out'">
            {{ tx.direction === 'in' ? '↓' : '↑' }}
          </div>

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

          <strong class="tx-value" :class="tx.direction === 'in' ? 'tx-value-in' : 'tx-value-out'">
            {{ tx.direction === 'in' ? '+' : '-' }}{{ moneyWithUnit(tx.amount) }}
          </strong>
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
          </div>

          <div v-if="actionModal.type === 'withdraw'" class="wallet-modal-section">
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
              <span>ابتدا مبلغ دلخواه را وارد کنید، سپس در صورت نیاز از مبالغ سریع استفاده کنید</span>
            </div>

            <label class="amount-field">
              <span>مبلغ دلخواه</span>
              <div class="amount-input-shell">
                <input
                  :value="actionModal.amountText"
                  type="text"
                  inputmode="numeric"
                  placeholder="مثلاً ۱٬۵۴۰٬۰۰۰"
                  @input="onActionAmountInput"
                />
                <span class="amount-input-unit">تومان</span>
              </div>
            </label>

            <div class="quick-amounts">
              <button
                v-for="amount in actionQuickAmounts"
                :key="`quick-${actionModal.type}-${amount.value}`"
                type="button"
                :class="{ active: selectedActionAmount === amount.value }"
                @click="setQuickAmount(amount.value)"
              >
                <small>{{ amount.label || amount.caption }}</small>
                <strong>{{ moneyWithUnit(amount.value) }}</strong>
              </button>
              <span v-if="actionModal.type === 'withdraw' && !actionQuickAmounts.length" class="wallet-inline-warning">موجودی قابل برداشت برای این کیف پول وجود ندارد.</span>
            </div>
          </div>

          <div v-if="actionModal.type === 'deposit' && actionModal.paymentMethod === 'card' && selectedActionAmount > 0" class="wallet-modal-section deposit-tax-preview">
            <div class="wallet-modal-section-head">
              <strong>محاسبه واریز به کیف پول</strong>
              <span>پس از تایید پشتیبانی، مالیات از مبلغ خام کسر می‌شود</span>
            </div>
            <div class="deposit-tax-rows">
              <div><span>مبلغ خام واریزی</span><strong>{{ moneyWithUnit(selectedActionAmount) }}</strong></div>
              <div><span>کسر مالیات ۱۰٪</span><strong class="tax">− {{ moneyWithUnit(depositTaxAmount) }}</strong></div>
              <div class="net"><span>مبلغ نهایی اضافه‌شده به کیف پول</span><strong>{{ moneyWithUnit(depositNetAmount) }}</strong></div>
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
              مبلغ خام را کارت به کارت کنید. بعد از تایید پشتیبانی، ۱۰٪ مالیات کسر و باقی‌مانده به کیف پول اضافه می‌شود.
              برای مثال اگر ۲٬۰۰۰٬۰۰۰ تومان واریز کنید، ۲۰۰٬۰۰۰ تومان مالیات و ۱٬۸۰۰٬۰۰۰ تومان به کیف پول می‌نشیند.
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

            <div v-if="actionModal.destinationType === 'bank'" class="bank-withdraw-fields">
              <label>
                <span>شماره شبا</span>
                <input v-model="actionModal.bankAccountIban" dir="ltr" inputmode="text" placeholder="IR..." />
              </label>
              <label>
                <span>نام صاحب حساب</span>
                <input v-model="actionModal.bankAccountHolder" type="text" placeholder="اختیاری" />
              </label>
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
              <span>{{ actionModal.type === 'deposit' ? 'موجودی بعد از واریز خالص' : 'مانده مبدا' }}</span>
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

          <div v-if="actionModal.type === 'withdraw' && actionModal.destinationType === 'bank'" class="wallet-note">
            با ثبت برداشت فقط تیکت برای پشتیبانی ساخته می‌شود. مبلغ هنوز کم نمی‌شود؛ بعد از واریز بانکی و تایید پشتیبانی از کیف پول کسر خواهد شد.
          </div>

          <div v-else class="wallet-note">
            {{ actionModal.type === 'deposit' ? 'واریز کارت به کارت بعد از تایید پشتیبانی با کسر ۱۰٪ مالیات به کیف پول اضافه می‌شود.' : 'انتقال بین کیف‌پول‌ها بلافاصله انجام می‌شود.' }}
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
              v-if="!selectedOption?.cash_only"
              type="button"
              class="payment-plan-card"
              :class="{ active: optionModal.paymentPlan === 'installment' }"
              @click="optionModal.paymentPlan = 'installment'"
            >
              <strong>قسطی</strong>
              <span>{{ moneyWithUnit(selectedOption?.installment_upfront_amount) }}</span>
              <small>باقی‌مانده {{ Number(selectedOption?.installment_months || 0).toLocaleString('fa-IR') }} ماهه، ماهی {{ moneyWithUnit(selectedOption?.monthly_installment_amount) }}</small>
            </button>
          </div>

          <label v-if="optionModal.paymentPlan === 'installment'" class="upfront-input-box">
            <span>مبلغ نقدی اولیه (تومان)</span>
            <input
              v-model="optionModal.upfrontAmountText"
              type="text"
              inputmode="numeric"
              placeholder="مثلا 800,000"
            />
            <small>مبلغ پیش‌پرداخت طبق پلن همین محصول ثابت است و اقساط در سررسیدهای جداگانه ثبت می‌شوند.</small>
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
            برداشت اقساط در سررسیدها از کیف پول اصلی انجام می‌شود. اگر تا ۷ روز بعد از سررسید پرداخت نشود، دسترسی نرم‌افزار قفل می‌شود.
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

    <div v-if="optionDetailModal.open && detailOption" class="wallet-modal-overlay" @click.self="closeOptionDetail">
      <section class="wallet-modal option-detail-modal" :style="{ '--option-accent': detailOption.accent || '#315f9f' }">
        <header class="wallet-modal-head">
          <div class="wallet-modal-title-wrap">
            <p>{{ detailOption.personalized_title }}</p>
            <h3>{{ detailOption.title }}</h3>
          </div>
          <button class="close-btn" type="button" @click="closeOptionDetail">×</button>
        </header>
        <div class="wallet-modal-body">
          <div class="option-detail-status" :class="optionStatusClass(detailOption)">
            {{ optionStatusText(detailOption) }}
          </div>
          <p class="option-detail-desc">{{ detailOption.description }}</p>
          <div v-if="detailOption.is_available === false" class="option-unavailable-box">
            <strong>{{ detailOption.status_label || 'در دسترس نمی‌باشد' }}</strong>
            <small>{{ detailOption.unavailable_message || 'این آپشن هنوز ارائه نمی‌شود.' }}</small>
          </div>
          <div v-else-if="detailOption.is_active" class="option-live-grid">
            <article class="option-live-stat">
              <span>شیوه پرداخت</span>
              <strong>{{ detailOption.payment_plan_label || 'ثبت نشده' }}</strong>
            </article>
            <article class="option-live-stat">
              <span>پرداخت‌شده</span>
              <strong>{{ moneyWithUnit(detailOption.paid_amount) }}</strong>
            </article>
            <article class="option-live-stat">
              <span>مانده</span>
              <strong>{{ moneyWithUnit(detailOption.remaining_amount) }}</strong>
            </article>
            <article class="option-live-stat">
              <span>{{ detailOption.next_installment_due_at ? 'سررسید بعدی' : 'فعال‌سازی' }}</span>
              <strong>{{ detailOption.next_installment_due_at ? formatShortDate(detailOption.next_installment_due_at) : formatShortDate(detailOption.purchased_at) }}</strong>
            </article>
          </div>
          <div v-else class="option-price-stack">
            <div class="option-price-row">
              <span>قیمت نقدی</span>
              <strong>{{ moneyWithUnit(detailOption.cash_amount) }}</strong>
            </div>
            <div class="option-installment-row">
              <span>{{ detailOption.cash_only ? 'فقط نقدی' : `اقساط ${Number(detailOption.installment_months || 0).toLocaleString('fa-IR')} ماهه` }}</span>
              <strong>{{ moneyWithUnit(detailOption.monthly_installment_amount) }}</strong>
              <small>پیش‌پرداخت: {{ moneyWithUnit(detailOption.installment_upfront_amount) }}</small>
            </div>
          </div>
          <div v-if="detailOption.installment_is_locked" class="option-lock-note">
            <strong>این بخش قفل شده است</strong>
            <small>{{ detailOption.installment_lock_notice || 'قسط سررسید این آپشن پرداخت نشده است.' }}</small>
          </div>
          <div v-if="detailOption.is_active && detailOption.is_available !== false" class="option-progress-block">
            <div class="option-progress-head">
              <span>پیشرفت پرداخت</span>
              <strong>{{ toFaPercent(detailOption.progress_percent) }}</strong>
            </div>
            <div class="option-progress-bar">
              <span :style="{ width: `${detailOption.progress_percent || 0}%` }"></span>
            </div>
          </div>
          <button
            v-if="detailOption.can_pay_next_installment"
            class="submit-btn submit-deposit"
            type="button"
            :disabled="payingInstallmentFeatureKey === detailOption.feature_key"
            @click="submitNextInstallmentPayment(detailOption)"
          >
            {{ payingInstallmentFeatureKey === detailOption.feature_key ? 'در حال پرداخت...' : 'پرداخت قسط بعدی' }}
          </button>
          <button
            v-else-if="!detailOption.is_active && detailOption.is_available !== false"
            class="submit-btn submit-deposit"
            type="button"
            @click="openPurchaseFromDetail"
          >
            انتخاب و خرید
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
import BaseDatePicker from '../base/BaseDatePicker.vue'
import BaseSpinner from '../base/BaseSpinner.vue'
import { formatJalaliDate, parseJalaliToIso } from '../../utils/date'
import { formatThousandsToman, formatThousandsTomanValue, fromThousandsTomanInput } from '../../utils/money'
import { resolveApiErrorMessage } from '../../utils/apiError'
import { useAuthStore } from '../../store/auth.store'

const props = defineProps({
  searchQuery: { type: String, default: '' }
})

const router = useRouter()
const authStore = useAuthStore()

const reloadAfterOptionChange = () => {
  window.setTimeout(() => {
    window.location.reload()
  }, 120)
}

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
  periodSummary: {
    start: '',
    end: '',
    sms_sent_count: 0,
    deposits_total: 0,
    withdrawals_total: 0
  },
  wallets: [],
  transactions: [],
  options: [],
  optionsTenant: null,
  licenseStatus: {},
  optionsLoading: false
})

const periodRangeOptions = [
  { key: 'today', label: 'امروز' },
  { key: 'yesterday', label: 'دیروز' },
  { key: 'month', label: 'این ماه' },
  { key: 'custom', label: 'بازه دلخواه' }
]

const periodFilters = reactive({
  rangeKey: 'today',
  startJalali: '',
  endJalali: ''
})

const toIsoDate = (value) => {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const resolvePeriodRangeDates = (rangeKey) => {
  const now = new Date()
  if (rangeKey === 'today') {
    const iso = toIsoDate(now)
    return { start: iso, end: iso }
  }
  if (rangeKey === 'yesterday') {
    const yesterday = new Date(now)
    yesterday.setDate(now.getDate() - 1)
    const iso = toIsoDate(yesterday)
    return { start: iso, end: iso }
  }
  if (rangeKey === 'month') {
    const start = new Date(now.getFullYear(), now.getMonth(), 1)
    return { start: toIsoDate(start), end: toIsoDate(now) }
  }
  return { start: '', end: '' }
}

const buildPeriodQuery = () => {
  if (periodFilters.rangeKey === 'custom') {
    let start = parseJalaliToIso(periodFilters.startJalali)
    let end = parseJalaliToIso(periodFilters.endJalali)
    if (start && end && start > end) {
      const temp = start
      start = end
      end = temp
    }
    return { start: start || undefined, end: end || undefined }
  }
  const quick = resolvePeriodRangeDates(periodFilters.rangeKey)
  return { start: quick.start || undefined, end: quick.end || undefined }
}

const setPeriodRange = (rangeKey) => {
  periodFilters.rangeKey = rangeKey
  if (rangeKey !== 'custom') {
    periodFilters.startJalali = ''
    periodFilters.endJalali = ''
  } else if (!periodFilters.startJalali || !periodFilters.endJalali) {
    const todayIso = toIsoDate(new Date())
    periodFilters.startJalali = formatJalaliDate(todayIso).replace(/-/g, '/')
    periodFilters.endJalali = periodFilters.startJalali
  }
}

const actionModal = reactive({
  open: false,
  type: 'deposit',
  walletId: null,
  destinationType: 'bank',
  destinationWalletId: null,
  bankAccountIban: '',
  bankAccountHolder: '',
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

const optionDetailModal = reactive({
  open: false,
  featureKey: ''
})

const selectedWalletId = ref(0)
const smsTopUpAmountText = ref('')
const smsTopUpSubmitting = ref(false)
const payingInstallmentFeatureKey = ref('')
const companyCardNumber = '6274121774209571'
const companyCardHolder = 'امید کریمی'
const depositMethods = [
  { key: 'gateway', title: 'درگاه پرداخت', caption: 'به‌زودی فعال می‌شود', disabled: true },
  { key: 'up', title: 'اپلیکیشن آپ', caption: 'به‌زودی فعال می‌شود', disabled: true },
  { key: 'card', title: 'کارت به کارت', caption: 'فعال', disabled: false }
]

const money = (value) => formatThousandsTomanValue(value)
const moneyWithUnit = (value) => formatThousandsToman(value)
const formatDateTime = (value) => value ? new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '-'
const formatShortDate = (value) => value ? new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium' }).format(new Date(value)) : '-'
const txTitle = (tx) => {
  const description = String(tx?.description || '').trim()
  const referenceType = String(tx?.reference_type || '').trim()
  if (referenceType === 'vehicle_assigned_sms' || description.includes('پذیرش')) {
    return description || 'ارسال پیامک پذیرش خودرو'
  }
  if (referenceType === 'vehicle_released_sms' || description.includes('ترخیص')) {
    return description || 'ارسال پیامک ترخیص خودرو'
  }
  return description || (tx?.direction === 'in' ? 'واریز به کیف پول' : 'برداشت از کیف پول')
}
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
  if (Number(state.summary.sms_balance || 0) <= 0) return 'شارژ پیشنهادی: ۱۰۰,۰۰۰ تومان'
  if (smsLow.value) return 'پیشنهاد: یک شارژ سبک انجام بده'
  return 'وضعیت شارژ: مناسب'
})
const selectedWallet = computed(() => state.wallets.find((wallet) => Number(wallet.id) === Number(selectedWalletId.value)) || null)
const activeWallet = computed(() => state.wallets.find((wallet) => Number(wallet.id) === Number(actionModal.walletId)) || null)
const activeWalletIsSms = computed(() => activeWallet.value?.wallet_type === 'sms')
const activeWalletBalance = computed(() => Math.max(0, Number(activeWallet.value?.balance || 0)))
const selectedWalletIsSms = computed(() => selectedWallet.value?.wallet_type === 'sms')
const selectedWalletBalance = computed(() => Math.max(0, Number(selectedWallet.value?.balance || 0)))
const walletUserRole = computed(() => authStore.role || authStore.user?.role || '')
const canDepositWalletAction = computed(() => ['accountant', 'admin', 'owner', 'manager', 'operator'].includes(walletUserRole.value))
const canWithdrawWalletAction = computed(() => ['admin', 'owner', 'manager'].includes(walletUserRole.value))
const hasDepositWallet = computed(() => state.wallets.length > 0)
const hasWithdrawableBalance = computed(() => state.wallets.some((wallet) => Number(wallet.balance || 0) > 0))
const withdrawButtonDisabled = computed(() => {
  if (!canWithdrawWalletAction.value) return true
  if (!hasWithdrawableBalance.value) return true
  if (!selectedWallet.value) return false
  return selectedWalletBalance.value <= 0
})
const withdrawButtonTitle = computed(() => {
  if (!canWithdrawWalletAction.value) return 'برداشت فقط برای مدیر'
  return withdrawButtonDisabled.value ? 'برداشت غیرفعال' : 'برداشت وجه'
})
const withdrawButtonCaption = computed(() => {
  if (!canWithdrawWalletAction.value) return 'واریز فعال است، برداشت فقط برای مدیران است'
  if (selectedWallet.value && selectedWalletBalance.value <= 0) return 'موجودی این کیف پول صفر است'
  if (!hasWithdrawableBalance.value) return 'موجودی قابل برداشت ندارید'
  const balance = selectedWallet.value ? selectedWalletBalance.value : Number(state.summary.regular_balance || 0)
  return `قابل برداشت: ${moneyWithUnit(balance)}`
})
const depositShortcutCaption = computed(() => {
  if (!primaryDepositWallet.value) return 'کیف پولی برای شارژ وجود ندارد'
  return `کیف پول اصلی: ${moneyWithUnit(state.summary.regular_balance)}`
})
const primaryDepositWallet = computed(() => (
  state.wallets.find((wallet) => wallet.wallet_type !== 'sms')
  || state.wallets[0]
  || null
))
const smsWallet = computed(() => state.wallets.find((wallet) => wallet.wallet_type === 'sms') || null)
const primaryWalletBalance = computed(() => Math.max(0, Number(primaryDepositWallet.value?.balance || 0)))
const smsTopUpAmount = computed(() => parseAmount(smsTopUpAmountText.value))
const smsTopUpDisabled = computed(() => {
  if (smsTopUpSubmitting.value) return true
  if (!canWithdrawWalletAction.value) return true
  if (!primaryDepositWallet.value || !smsWallet.value) return true
  if (smsTopUpAmount.value <= 0) return true
  if (smsTopUpAmount.value > primaryWalletBalance.value) return true
  return false
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
const sortedWalletOptions = computed(() => (
  [...state.options].sort((a, b) => {
    const aUnavailable = a?.is_available === false ? 1 : 0
    const bUnavailable = b?.is_available === false ? 1 : 0
    return aUnavailable - bUnavailable
  })
))
const selectedOption = computed(() => state.options.find((option) => option.feature_key === optionModal.featureKey) || null)
const detailOption = computed(() => state.options.find((option) => option.feature_key === optionDetailModal.featureKey) || null)
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
const optionMonthlyAmount = computed(() => optionModal.paymentPlan === 'installment' ? Number(selectedOption.value?.monthly_installment_amount || 0) : 0)
const optionBalanceAfter = computed(() => Number(selectedOptionWallet.value?.balance || 0) - selectedOptionDebitAmount.value)
const optionPurchaseError = computed(() => {
  if (!optionModal.open) return ''
  if (!selectedOption.value) return 'آپشن انتخاب‌شده معتبر نیست.'
  if (selectedOption.value.is_active) return 'این آپشن قبلا فعال شده است.'
  if (selectedOption.value.cash_only && optionModal.paymentPlan === 'installment') return 'این مورد فقط نقدی قابل پرداخت است.'
  if (!selectedOptionWallet.value) return 'برای خرید، یک کیف پول عادی انتخاب کنید.'
  if (optionModal.paymentPlan === 'installment' && selectedOptionDebitAmount.value <= 0) return 'مبلغ نقدی اولیه را وارد کنید.'
  if (optionModal.paymentPlan === 'installment' && selectedOptionDebitAmount.value !== Number(selectedOption.value.installment_upfront_amount || 0)) return 'مبلغ نقدی اولیه باید مطابق پلن محصول باشد.'
  if (optionBalanceAfter.value < 0) return 'موجودی کیف پول برای این شیوه پرداخت کافی نیست.'
  return ''
})
const canSubmitOptionPurchase = computed(() => !optionModal.submitting && !optionPurchaseError.value)

const optionStatusText = (option) => {
  if (!option) return ''
  if (option.is_available === false) return option.status_label || 'غیرفعال'
  if (option.installment_is_locked) return 'قفل‌شده'
  if (option.is_active) return option.status_label || 'خریداری‌شده'
  return option.status_label || 'قابل خرید'
}

const optionStatusClass = (option) => {
  if (!option) return ''
  if (option.is_available === false) return 'unavailable'
  if (option.installment_is_locked) return 'locked'
  if (option.is_active) return 'purchased'
  return 'buyable'
}

const isMobileWalletViewport = () => window.matchMedia('(max-width: 768px)').matches

const onOptionCardActivate = (option) => {
  if (!option) return
  if (isMobileWalletViewport()) {
    openOptionDetail(option)
    return
  }
  if (!option.is_active && option.is_available !== false) openOptionModal(option)
}

const openOptionDetail = (option) => {
  optionDetailModal.open = true
  optionDetailModal.featureKey = option?.feature_key || ''
}

const closeOptionDetail = () => {
  optionDetailModal.open = false
  optionDetailModal.featureKey = ''
}

const openPurchaseFromDetail = () => {
  const option = detailOption.value
  closeOptionDetail()
  if (option) openOptionModal(option)
}
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
    { value: roundDownToStep(balance * 0.25), label: '۲۵٪ موجودی' },
    { value: roundDownToStep(balance * 0.5), label: '۵۰٪ موجودی' },
    { value: roundDownToStep(balance), label: 'کل موجودی' }
  ]).filter((item) => item.value <= balance)
})
const actionQuickAmounts = computed(() => (
  actionModal.type === 'deposit' ? dynamicDepositAmounts.value : dynamicWithdrawAmounts.value
))
const selectedActionAmount = computed(() => parseAmount(actionModal.amountText))
const WALLET_DEPOSIT_TAX_PERCENT = 10
const depositTaxAmount = computed(() => {
  if (actionModal.type !== 'deposit' || actionModal.paymentMethod !== 'card') return 0
  const gross = Math.max(0, Number(selectedActionAmount.value || 0))
  return Math.round((gross * WALLET_DEPOSIT_TAX_PERCENT) / 100)
})
const depositNetAmount = computed(() => Math.max(0, Number(selectedActionAmount.value || 0) - depositTaxAmount.value))
const balanceAfterAction = computed(() => (
  actionModal.type === 'deposit'
    ? activeWalletBalance.value + (actionModal.paymentMethod === 'card' ? depositNetAmount.value : selectedActionAmount.value)
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
  if (actionModal.type === 'withdraw' && actionModal.destinationType === 'bank') {
    const iban = String(actionModal.bankAccountIban || '').replace(/[\s-]/g, '')
    if (!iban) return 'شماره شبا را برای برداشت بانکی وارد کنید.'
    if (iban.length < 10) return 'شماره شبا معتبر نیست.'
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
    const periodQuery = buildPeriodQuery()
    const { data } = await api.get('/payments/wallet/dashboard/', {
      params: {
        type: state.filterType,
        q: (props.searchQuery || '').trim() || undefined,
        start: periodQuery.start,
        end: periodQuery.end
      }
    })
    state.summary = {
      total_balance: Number(data?.summary?.total_balance || 0),
      regular_balance: Number(data?.summary?.regular_balance || 0),
      sms_balance: Number(data?.summary?.sms_balance || 0),
      deposits_total: Number(data?.summary?.deposits_total || 0),
      withdrawals_total: Number(data?.summary?.withdrawals_total ?? data?.summary?.payments_total ?? 0)
    }
    state.periodSummary = {
      start: data?.period_summary?.start || periodQuery.start || '',
      end: data?.period_summary?.end || periodQuery.end || '',
      sms_sent_count: Number(data?.period_summary?.sms_sent_count || 0),
      deposits_total: Number(data?.period_summary?.deposits_total || 0),
      withdrawals_total: Number(data?.period_summary?.withdrawals_total || 0)
    }
    state.wallets = Array.isArray(data?.wallets) ? data.wallets : []
    state.transactions = Array.isArray(data?.transactions) ? data.transactions : []
    state.licenseStatus = data?.license_status || state.licenseStatus || {}
    const defaultActionWallet = actionModal.type === 'deposit'
      ? primaryDepositWallet.value
      : selectableWallets.value[0]
    if ((!actionModal.walletId || !selectableWallets.value.some((wallet) => Number(wallet.id) === Number(actionModal.walletId))) && defaultActionWallet) {
      actionModal.walletId = Number(defaultActionWallet.id)
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
    state.licenseStatus = data?.license_status || state.licenseStatus || {}
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

const openActionModal = async (type) => {
  clearMessages()
  if (type === 'deposit' && !canDepositWalletAction.value) {
    state.error = 'شما دسترسی ثبت واریز کیف پول را ندارید.'
    return
  }
  if (type === 'withdraw' && !canWithdrawWalletAction.value) {
    state.error = 'برداشت از کیف پول فقط برای مدیران مجاز است.'
    return
  }
  if (type === 'withdraw' && withdrawButtonDisabled.value) {
    state.error = withdrawButtonCaption.value
    return
  }
  actionModal.open = true
  actionModal.type = type
  actionModal.destinationType = 'bank'
  actionModal.destinationWalletId = null
  actionModal.bankAccountIban = ''
  actionModal.bankAccountHolder = ''
  actionModal.paymentMethod = 'card'
  actionModal.amountText = ''
  actionModal.description = ''
  actionModal.submitting = false
  const preferredWallet = selectedWallet.value
  const wallets = type === 'withdraw'
    ? state.wallets.filter((wallet) => Number(wallet.balance || 0) > 0)
    : (primaryDepositWallet.value ? [primaryDepositWallet.value] : [])
  const fallbackWallet = (
    preferredWallet
    && wallets.some((wallet) => Number(wallet.id) === Number(preferredWallet.id))
  )
    ? preferredWallet
    : wallets[0]
  actionModal.walletId = fallbackWallet ? Number(fallbackWallet.id) : null
  actionModal.destinationWalletId = transferDestinationWallets.value[0]?.id ? Number(transferDestinationWallets.value[0].id) : null
  if (type === 'deposit') {
    actionModal.amountText = dynamicDepositAmounts.value[0]?.value ? money(dynamicDepositAmounts.value[0].value) : ''
  } else if (dynamicWithdrawAmounts.value.length) {
    actionModal.amountText = money(dynamicWithdrawAmounts.value[0].value)
  }
  if (type === 'withdraw') {
    try {
      const { data } = await api.get('/services/general-settings/', { meta: { trackLoading: false, showErrorToast: false } })
      if (data?.bank_account_iban) actionModal.bankAccountIban = String(data.bank_account_iban)
      if (data?.bank_account_holder) actionModal.bankAccountHolder = String(data.bank_account_holder)
    } catch (_error) {
      // optional prefill
    }
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
  actionModal.bankAccountIban = ''
  actionModal.bankAccountHolder = ''
  actionModal.paymentMethod = 'card'
  actionModal.amountText = ''
  actionModal.description = ''
  actionModal.submitting = false
}

const setQuickAmount = (amount) => {
  actionModal.amountText = money(amount)
}

const onActionAmountInput = (event) => {
  const digits = normalizeDigits(event?.target?.value)
  actionModal.amountText = digits ? money(parseAmount(digits)) : ''
}

const onSmsTopUpAmountInput = (event) => {
  const digits = normalizeDigits(event?.target?.value)
  smsTopUpAmountText.value = digits ? money(parseAmount(digits)) : ''
}

const submitSmsTopUpFromMain = async () => {
  clearMessages()
  if (!canWithdrawWalletAction.value) {
    state.error = 'برداشت از کیف پول فقط برای مدیران مجاز است.'
    return
  }
  const sourceWallet = primaryDepositWallet.value
  const destinationWallet = smsWallet.value
  const amount = smsTopUpAmount.value
  if (!sourceWallet || !destinationWallet) {
    state.error = 'کیف پول اصلی یا پیامک پیدا نشد.'
    return
  }
  if (amount <= 0) {
    state.error = 'مبلغ باید بزرگ‌تر از صفر باشد.'
    return
  }
  if (amount > Number(sourceWallet.balance || 0)) {
    state.error = 'مبلغ از موجودی کیف پول اصلی بیشتر است.'
    return
  }
  if (Number(sourceWallet.id) === Number(destinationWallet.id)) {
    state.error = 'کیف پول مقصد نمی‌تواند با مبدا یکی باشد.'
    return
  }

  smsTopUpSubmitting.value = true
  try {
    const { data } = await api.post('/payments/wallet/withdraw/', {
      wallet_id: sourceWallet.id,
      source_wallet_id: sourceWallet.id,
      destination_type: 'wallet',
      destination_wallet_id: destinationWallet.id,
      amount,
      description: 'شارژ موجودی پیامک از کیف پول اصلی'
    })
    state.successMessage = data?.detail || 'موجودی پیامک با موفقیت شارژ شد.'
    smsTopUpAmountText.value = ''
    await loadWalletDashboard()
  } catch (error) {
    state.error = resolveApiErrorMessage(error, 'انتقال به موجودی پیامک ناموفق بود.')
  } finally {
    smsTopUpSubmitting.value = false
  }
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
  if (actionModal.type === 'deposit' && !canDepositWalletAction.value) {
    state.error = 'شما دسترسی ثبت واریز کیف پول را ندارید.'
    return
  }
  if (actionModal.type === 'withdraw' && !canWithdrawWalletAction.value) {
    state.error = 'برداشت از کیف پول فقط برای مدیران مجاز است.'
    return
  }
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
      bank_account_iban: actionModal.type === 'withdraw' && actionModal.destinationType === 'bank'
        ? String(actionModal.bankAccountIban || '').trim()
        : undefined,
      bank_account_holder: actionModal.type === 'withdraw' && actionModal.destinationType === 'bank'
        ? String(actionModal.bankAccountHolder || '').trim()
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
    const isBankWithdraw = actionModal.type === 'withdraw' && actionModal.destinationType === 'bank'
    const ticketId = data?.ticket?.id
    state.successMessage = data?.detail || (actionModal.type === 'deposit' ? 'واریز ثبت شد.' : 'برداشت ثبت شد.')
    closeActionModal()
    await loadWalletDashboard()
    if (isBankWithdraw) {
      router.push({
        path: '/support',
        query: ticketId ? { ticket: String(ticketId) } : undefined
      })
    }
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
    await authStore.fetchMe()
    reloadAfterOptionChange()
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
    await authStore.fetchMe()
    reloadAfterOptionChange()
  } catch (error) {
    state.error = resolveApiErrorMessage(error, 'پرداخت قسط بعدی ناموفق بود.')
  } finally {
    payingInstallmentFeatureKey.value = ''
  }
}

watch(() => props.searchQuery, async () => {
  await loadWalletDashboard()
})

watch(
  () => [periodFilters.rangeKey, periodFilters.startJalali, periodFilters.endJalali],
  async () => {
    if (periodFilters.rangeKey === 'custom' && (!periodFilters.startJalali || !periodFilters.endJalali)) return
    await loadWalletDashboard()
  }
)

watch(() => [actionModal.walletId, actionModal.type, actionModal.destinationType], () => {
  if (!actionModal.open) return
  if (actionModal.destinationType === 'wallet') {
    const exists = transferDestinationWallets.value.some((wallet) => Number(wallet.id) === Number(actionModal.destinationWalletId))
    if (!exists) actionModal.destinationWalletId = transferDestinationWallets.value[0]?.id ? Number(transferDestinationWallets.value[0].id) : null
  }
  const currentAmount = parseAmount(actionModal.amountText)
  if (actionModal.type === 'deposit') {
    const firstDeposit = dynamicDepositAmounts.value[0]?.value
    if (currentAmount <= 0 && firstDeposit) actionModal.amountText = money(firstDeposit)
    return
  }
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
.license-lock-banner{display:grid;gap:6px;padding:16px 18px;border-radius:22px;border:1px solid #fed7aa;background:linear-gradient(135deg,#fff7ed,#fffdf7);color:#9a3412;box-shadow:0 16px 34px rgba(154,52,18,.08)}
.license-lock-banner.locked{border-color:#fecaca;background:linear-gradient(135deg,#fff1f2,#fff7ed);color:#991b1b}
.license-lock-banner strong{font-size:16px;color:inherit}
.license-lock-banner p{margin:0;line-height:1.8;color:inherit}
.license-lock-banner span{font-size:12px;font-weight:900;color:inherit}
.wallet-overview{
  display:grid;
  grid-template-columns:370px minmax(0,1fr) minmax(0,1fr);
  grid-template-areas:
    "shortcuts hero hero"
    "sms money money";
  gap:14px;
  align-items:stretch
}
.wallet-shortcuts{grid-area:shortcuts;background:linear-gradient(180deg,#ffffff 0%,#f8fbfe 60%,#f3f7fb 100%);border:1px solid var(--wallet-border);border-radius:30px;padding:22px;box-shadow:0 18px 42px rgba(15,23,42,.05);position:relative;overflow:hidden}
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
.shortcut-primary{background:linear-gradient(145deg,#e7faf4 0%,#e8f6ff 55%,#f0fbff 100%);color:#0f766e;border-color:#b7e4d6;box-shadow:0 10px 22px rgba(45,158,133,.10)}
.shortcut-primary:hover{background:linear-gradient(145deg,#dff7ef,#e2f3ff 55%,#eef9ff);border-color:#9fd8c6;box-shadow:0 14px 26px rgba(45,158,133,.14)}
.shortcut-primary strong{color:#0f5c52}
.shortcut-primary small{color:#3d8f82}
.shortcut-primary .shortcut-icon{background:linear-gradient(180deg,#ffffff,#e8faf4);color:#14b8a6;box-shadow:0 4px 10px rgba(20,184,166,.18)}
.shortcut-icon{width:42px;height:42px;border-radius:14px;background:linear-gradient(180deg,#edf3f8,#e2e8f0);color:#315f9f;display:inline-flex;align-items:center;justify-content:center;font-size:21px;font-weight:800;box-shadow:inset 0 1px 0 rgba(255,255,255,.7)}
.shortcut-card strong{font-size:16px;color:var(--wallet-text);font-weight:800}
.shortcut-card small{color:var(--wallet-muted);font-size:12px}
.wallet-hero{grid-area:hero;position:relative;overflow:hidden;border-radius:30px;padding:24px 28px;background:linear-gradient(135deg,#415a77 0%,#557a95 38%,#6b96a8 100%);box-shadow:0 20px 46px rgba(65,90,119,.18);display:grid;gap:22px;min-height:290px;border:1px solid rgba(255,255,255,.14)}
.sms-tile{grid-area:sms}
.summary-money-row{grid-area:money;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
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
.summary-tile{background:linear-gradient(180deg,#ffffff,#f8fafc);border:1px solid var(--wallet-border);border-radius:20px;padding:16px 18px;box-shadow:0 10px 24px rgba(15,23,42,.04);position:relative;overflow:hidden;min-height:0}
.option-card-compact-meta{display:none}
.option-status.buyable{background:#fff7ed;color:#c2410c}
.option-status.locked{background:#fee2e2;color:#991b1b}
.option-card.purchased{background:linear-gradient(180deg,#f3fdf7,#ecfdf3);border-color:#86efac}
.option-card.not-purchased{background:linear-gradient(180deg,#fffaf5,#fff7ed);border-color:#fdba74}
.option-detail-status{display:inline-flex;align-items:center;height:32px;padding:0 12px;border-radius:999px;font-size:12px;font-weight:900;width:max-content}
.option-detail-status.purchased{background:#dcfce7;color:#166534}
.option-detail-status.buyable{background:#ffedd5;color:#c2410c}
.option-detail-status.locked{background:#fee2e2;color:#991b1b}
.option-detail-status.unavailable{background:#e2e8f0;color:#475569}
.option-detail-desc{margin:0;color:#64748b;font-size:13px;line-height:1.9}
.tx-list{display:grid;gap:10px}
.tx-item{display:grid;grid-template-columns:40px minmax(0,1fr) auto;align-items:center;gap:12px;padding:12px 14px;border:1px solid #e2e8f0;border-radius:16px;background:linear-gradient(180deg,#fff,#fafcfd);box-shadow:0 8px 18px rgba(15,23,42,.03);transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease}
.tx-item:hover{transform:translateY(-1px);box-shadow:0 12px 22px rgba(15,23,42,.05);border-color:#d4dee8}
.tx-title-row{display:flex;align-items:center;justify-content:space-between;gap:10px}
.tx-title-row h3{margin:0;color:#0f172a;font-size:13px;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.tx-chip{display:inline-flex;align-items:center;height:24px;padding:0 10px;border-radius:999px;font-size:10px;font-weight:800;flex-shrink:0}
.tx-chip-in{background:#dcfce7;color:#166534}
.tx-chip-out{background:#fee2e2;color:#b91c1c}
.tx-meta{margin:6px 0 0;color:#94a3b8;font-size:11px;display:flex;gap:6px;flex-wrap:wrap;line-height:1.4}
.tx-meta .separate{opacity:.55}
.tx-value{font-size:14px;font-weight:800;white-space:nowrap}
.tx-value-in{color:#0f766e}
.tx-value-out{color:#dc2626}
.tx-icon-box{width:40px;height:40px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;font-weight:800;flex-shrink:0}
.tx-icon-box-in{background:linear-gradient(180deg,#e7f7f1,#d9f1ea);color:#2f7d6b}
.tx-icon-box-out{background:linear-gradient(180deg,#fce8e8,#f9dddd);color:#c85b5b}
.summary-tile::before{content:'';position:absolute;top:0;right:0;left:0;height:3px;background:linear-gradient(90deg,#7aa2c7,#8db6a9)}
.summary-tile small{display:block;color:#64748b;font-size:12px}
.summary-tile strong{display:block;margin-top:10px;color:#0f172a;font-size:24px;line-height:1.15}
.summary-tile strong.danger{color:#b91c1c}
.summary-tile span{display:block;margin-top:6px;color:#94a3b8;font-size:12px}
.accent-tile{background:linear-gradient(135deg,#f3f8fd,#edf7f2)}
.soft-tile{background:linear-gradient(135deg,#fcfaf7,#f8f4f4)}
.sms-tile{background:
  radial-gradient(circle at 12% 0%,rgba(139,92,246,.22),transparent 42%),
  radial-gradient(circle at 88% 100%,rgba(45,212,191,.18),transparent 40%),
  linear-gradient(145deg,#f7f3ff 0%,#eef6ff 48%,#eafaf6 100%);
  border:1.5px solid #c4b5fd;
  box-shadow:0 14px 30px rgba(124,58,237,.10)
}
.sms-tile::before{height:4px;background:linear-gradient(90deg,#8b5cf6,#38bdf8,#2dd4bf)}
.sms-tile.low{background:
  radial-gradient(circle at 12% 0%,rgba(249,115,22,.22),transparent 42%),
  radial-gradient(circle at 88% 100%,rgba(251,191,36,.16),transparent 40%),
  linear-gradient(145deg,#fff8f1,#fff3e8 55%,#fff7ed);
  border-color:#fdba74;
  box-shadow:0 14px 30px rgba(234,88,12,.10)
}
.sms-tile.low::before{background:linear-gradient(90deg,#f97316,#fb923c,#fbbf24)}
.sms-tile strong{font-size:30px;margin-top:14px;color:#5b21b6}
.sms-tile.low strong,.sms-tile strong.danger{color:#c2410c}
.sms-tile-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.sms-tile-head small{color:#6d28d9;font-weight:800;display:inline-flex;align-items:center;gap:6px}
.sms-tile-mark{width:22px;height:22px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#8b5cf6,#6366f1);color:#fff;font-size:11px;box-shadow:0 6px 12px rgba(99,102,241,.25)}
.sms-tile.low .sms-tile-head small{color:#c2410c}
.sms-tile.low .sms-tile-mark{background:linear-gradient(135deg,#f97316,#fb923c);box-shadow:0 6px 12px rgba(249,115,22,.22)}
.sms-balance-caption{margin:10px 0 0;color:#516072;font-size:12px;line-height:1.9;max-width:28ch}
.sms-state-pill,.sms-topup-chip{display:inline-flex;align-items:center;justify-content:center;width:max-content}
.sms-state-pill{height:28px;padding:0 10px;border-radius:999px;background:rgba(139,92,246,.14);color:#6d28d9;font-size:11px;font-weight:900}
.sms-state-pill.low{background:rgba(234,88,12,.12);color:#c2410c}
.sms-topup-chip{margin-top:12px;padding:7px 11px;border-radius:999px;background:rgba(255,255,255,.9);border:1px solid rgba(167,139,250,.35);color:#5b21b6;font-size:11px;font-weight:800}
.sms-quick-topup{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;margin-top:14px;position:relative;z-index:1}
.sms-quick-topup input{height:40px;border:1px solid #d8b4fe;border-radius:12px;padding:0 12px;background:#fff;color:#0f172a;font:inherit;font-size:13px;font-weight:700;min-width:0}
.sms-quick-topup input:disabled{opacity:.6;cursor:not-allowed}
.sms-quick-topup-btn{height:40px;border:0;border-radius:12px;padding:0 12px;background:linear-gradient(135deg,#8b5cf6,#6366f1);color:#fff;font:inherit;font-size:12px;font-weight:800;cursor:pointer;white-space:nowrap;box-shadow:0 8px 16px rgba(99,102,241,.22)}
.sms-quick-topup-btn:disabled{opacity:.55;cursor:not-allowed}
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
.option-card.purchased,.option-card.active.purchased{background:linear-gradient(180deg,#f3fdf7,#ecfdf3);border-color:#86efac}
.option-card.not-purchased{background:linear-gradient(180deg,#fffaf5,#fff7ed);border-color:#fdba74}
.option-card.unavailable{background:linear-gradient(180deg,#fcfcfd,#f5f7fa);border-color:#d8e0ea}
.option-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.option-kicker{display:block;color:var(--option-accent);font-size:11px;font-weight:900;margin-bottom:6px}
.option-card h3{margin:0;color:#0f172a;font-size:20px}
.option-card p{margin:0;color:#64748b;font-size:12px;line-height:1.9}
.option-status{display:inline-flex;align-items:center;height:30px;padding:0 11px;border-radius:999px;background:#eef2f7;color:#475569;font-size:11px;font-weight:900;white-space:nowrap}
.option-status.enabled{background:#dcfce7;color:#166534}
.option-card.locked .option-status{background:#fee2e2;color:#991b1b}
.option-card.unavailable .option-status{background:#e2e8f0;color:#475569}
.option-unavailable-box{display:grid;gap:7px;padding:13px 14px;border:1px dashed #cbd5e1;border-radius:16px;background:linear-gradient(180deg,#ffffff,#f8fafc)}
.option-unavailable-box strong{color:#334155;font-size:14px}
.option-unavailable-box small{color:#64748b;font-size:12px;line-height:1.9}
.option-lock-note{display:grid;gap:6px;padding:12px 13px;border:1px solid #fecaca;border-radius:16px;background:linear-gradient(180deg,#fff7f7,#fff1f2)}
.option-lock-note strong{color:#991b1b;font-size:13px}
.option-lock-note small{color:#7f1d1d;font-size:12px;font-weight:800;line-height:1.8}
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
.period-insight-row{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(140px,0.7fr) minmax(180px,1fr);gap:12px;align-items:stretch;margin:0 0 16px}
.period-range-block{display:grid;gap:10px;padding:12px 14px;border:1px solid #dbe7f5;border-radius:18px;background:linear-gradient(180deg,#fff,#f7fbff);min-width:0}
.period-range-chips{display:flex;flex-wrap:wrap;gap:8px}
.period-chip{height:34px;padding:0 12px;border:1px solid #d7e5f8;border-radius:999px;background:#fff;color:#334155;font:inherit;font-size:12px;font-weight:800;cursor:pointer}
.period-chip.active{background:linear-gradient(135deg,#0f4c81,#0ea5e9);border-color:transparent;color:#fff}
.period-custom-dates{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.period-stat-card{display:grid;align-content:center;gap:6px;padding:12px 14px;border:1px solid #dbe7f5;border-radius:18px;background:linear-gradient(180deg,#fff,#f8fafc);min-width:0}
.period-stat-card span{color:#64748b;font-size:12px;font-weight:700}
.period-stat-card strong{color:#0f172a;font-size:18px;line-height:1.2}
.period-flow-values{display:flex;flex-wrap:wrap;gap:8px 12px;font-style:normal}
.period-flow-values em{font-style:normal;font-size:14px;font-weight:800}
.period-flow-values .in{color:#0f766e}
.period-flow-values .out{color:#dc2626}
.wallet-switch{height:42px;border:1px solid var(--wallet-border);border-radius:14px;padding:0 14px;background:#fff;color:#0f172a;box-shadow:inset 0 1px 2px rgba(15,23,42,.03)}
.filter-pill{display:flex;gap:4px;padding:5px;background:linear-gradient(180deg,#f1f5f9,#eaf0f5);border-radius:999px;border:1px solid #dde7f3}
.filter-pill button,.refresh-btn,.close-btn,.submit-btn,.quick-amounts button{border:0;cursor:pointer}
.filter-pill button{height:38px;padding:0 15px;border-radius:999px;background:transparent;color:#475569;font-weight:700}
.filter-pill button.active{background:linear-gradient(180deg,#ffffff,#f8fafc);color:#35506b;box-shadow:0 8px 18px rgba(148,163,184,.12)}
.refresh-btn{height:42px;padding:0 18px;border-radius:14px;background:linear-gradient(180deg,#f1f5f9,#e2e8f0);color:#35506b;font-weight:800;box-shadow:inset 0 1px 0 rgba(255,255,255,.65)}
.history-state{padding:42px 12px;text-align:center;color:#64748b}
.separate{color:#cbd5e1}
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
.bank-withdraw-fields{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
.bank-withdraw-fields label{display:grid;gap:6px}
.bank-withdraw-fields span{font-size:12px;font-weight:900;color:#334155}
.bank-withdraw-fields input{width:100%;border:1px solid #e2e8f0;border-radius:14px;padding:12px;background:#fff;color:#0f172a;font-weight:800}
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
.amount-field{display:grid;gap:8px}
.amount-input-shell{display:flex;align-items:center;gap:10px;min-height:52px;border:1px solid #efe4ff;border-radius:16px;padding:0 14px;background:#fbf8ff;transition:border-color .2s ease,box-shadow .2s ease,background .2s ease}
.amount-input-shell:focus-within{border-color:#c9adff;box-shadow:0 0 0 4px rgba(201,173,255,.18);background:#fff}
.amount-input-shell input{flex:1;min-width:0;height:auto;border:0;padding:0;background:transparent;box-shadow:none;font-size:16px;font-weight:800;color:#0f172a}
.amount-input-shell input:focus{border:0;box-shadow:none;background:transparent}
.amount-input-unit{flex:0 0 auto;color:#64748b;font-size:13px;font-weight:900}
.quick-amounts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.quick-amounts button{min-width:0;min-height:60px;width:100%;padding:10px 14px;border-radius:16px;background:#fff;color:#0f4aa8;font-weight:800;border:1px solid #efe4ff;display:grid;gap:4px;text-align:right;justify-items:start;transition:border-color .2s ease,transform .2s ease,background .2s ease}
.quick-amounts button small{color:#64748b;font-size:11px;font-weight:800}
.quick-amounts button strong{color:#0f172a;font-size:15px;line-height:1.4}
.quick-amounts button:hover{background:#eff6ff;border-color:transparent;transform:translateY(-1px)}
.quick-amounts button.active{background:#f1e8ff;border-color:#c9adff}
.quick-amounts button.active small,.quick-amounts button.active strong{color:var(--wallet-modal-accent)}
.wallet-inline-warning{display:block;padding:11px 13px;border:none;border-radius:14px;background:#fff1f2;color:#9f1239;font-size:12px;font-weight:800;line-height:1.7;grid-column:1 / -1}
.wallet-balance-preview-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.wallet-balance-preview{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:15px 16px;border:none;border-radius:16px;background:#f0fdf4;color:#166534}
.wallet-balance-preview.destination{border-color:transparent;background:#eff6ff;color:#1d4ed8}
.wallet-balance-preview.danger{border-color:transparent;background:#fff1f2;color:#9f1239}
.wallet-balance-preview span{font-size:12px;font-weight:800}
.wallet-balance-preview strong{font-size:16px}
.gateway-amounts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.deposit-amount-block{display:grid;gap:10px;width:100%}
.deposit-custom-amount-btn{border-style:dashed}
.deposit-custom-amount-input{height:44px;border:1px solid #dbe5f0;border-radius:14px;padding:0 14px;background:#fff;color:#0f172a;font:inherit;font-size:14px;font-weight:700}
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
.deposit-tax-rows{display:grid;gap:8px}
.deposit-tax-rows > div{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 12px;border-radius:12px;background:#f8fafc;border:1px solid #e8eef5}
.deposit-tax-rows span{color:#64748b;font-size:12px;font-weight:700}
.deposit-tax-rows strong{color:#0f172a;font-size:13px}
.deposit-tax-rows strong.tax{color:#c2410c}
.deposit-tax-rows .net{background:linear-gradient(135deg,#ecfdf5,#f0fdf4);border-color:#bbf7d0}
.deposit-tax-rows .net strong{color:#166534}
.support-ticket-btn{min-height:52px;border:none;border-radius:16px;background:#9d6cff;color:#fff;font-weight:900;cursor:pointer}
.wallet-note{padding:15px 16px;border-radius:18px;background:#fbf8ff;color:#334155;border:1px solid #efe4ff;line-height:1.8}
.submit-btn{height:54px;border-radius:16px;color:#fff;font-weight:800;box-shadow:none;transition:transform .2s ease,filter .2s ease,opacity .2s ease}
.submit-btn:hover:not(:disabled){transform:translateY(-1px);filter:saturate(1.06)}
.submit-btn:disabled{opacity:.7;cursor:not-allowed}
.submit-deposit{background:linear-gradient(135deg,#3b7f71,#6ca69a)}
.submit-withdraw{background:linear-gradient(135deg,#b85b5b,#d98383)}
@media (max-width:1200px){
  .wallet-overview{
    grid-template-columns:1fr 1fr;
    grid-template-areas:
      "hero hero"
      "sms sms"
      "shortcuts shortcuts"
      "money money";
    gap:12px
  }
  .summary-money-row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
  .options-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:900px){
  .history-head,.options-head,.wallet-modal-section-head{flex-direction:column;align-items:stretch}
  .history-head h2,.options-head h2{font-size:24px}
  .hero-main{flex-direction:column}
  .hero-main h2{font-size:36px}
  .hero-orb{display:none}
  .wallet-hero{min-height:0;padding:18px;gap:14px}
  .payment-plan-grid,.installment-live-preview,.option-live-grid,.bank-withdraw-fields,.wallet-balance-preview-grid{grid-template-columns:1fr}
  .deposit-method-grid,.wallet-choice-grid,.destination-toggle,.quick-amounts{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:768px){
  .wallet-page{gap:8px;font-size:11px}
  .wallet-alert{padding:10px 12px;border-radius:14px;font-size:11px;font-weight:700}
  .shortcut-head{display:none}
  .shortcut-grid{margin-top:0;gap:8px;grid-template-columns:repeat(2,minmax(0,1fr))}
  .wallet-shortcuts{padding:8px;border-radius:14px;box-shadow:0 8px 18px rgba(15,23,42,.04)}
  .shortcut-card{padding:9px 9px;gap:3px;border-radius:12px}
  .shortcut-icon{width:24px;height:24px;border-radius:8px;font-size:13px}
  .shortcut-card strong{font-size:11px;font-weight:700}
  .shortcut-card small{font-size:8px;line-height:1.3;font-weight:600;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
  .wallet-hero{min-height:0;padding:10px 12px;border-radius:14px;gap:0;box-shadow:0 10px 24px rgba(65,90,119,.12)}
  .hero-top{display:none}
  .hero-label{font-size:9px;letter-spacing:.02em;opacity:.9}
  .hero-main{gap:0}
  .hero-main h2{margin:3px 0 2px;font-size:17px !important;line-height:1.15;font-weight:700}
  .hero-sub{font-size:9px;line-height:1.35;max-width:none;opacity:.88}
  .hero-orb{display:none}
  .wallet-overview{
    grid-template-columns:1fr;
    grid-template-areas:
      "hero"
      "sms"
      "shortcuts"
      "money";
    gap:8px
  }
  .summary-money-row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .summary-tile{padding:9px 10px;border-radius:12px;box-shadow:0 6px 14px rgba(15,23,42,.03)}
  .summary-tile::before{height:2px}
  .summary-tile small{font-size:9px;font-weight:700}
  .summary-tile strong{margin-top:3px;font-size:12px;font-weight:700}
  .sms-tile{padding:11px 12px;border-radius:14px;border-width:1.5px}
  .sms-tile strong{font-size:15px !important;margin-top:4px;font-weight:700}
  .sms-tile-head small{font-size:9px}
  .sms-tile-mark{width:18px;height:18px;border-radius:6px;font-size:9px}
  .sms-state-pill{height:20px;padding:0 7px;font-size:8px}
  .sms-balance-caption{margin-top:4px;font-size:9px;line-height:1.45;max-width:none}
  .sms-topup-chip{margin-top:6px;padding:4px 8px;font-size:8px;border-radius:999px}
  .sms-quick-topup{margin-top:8px;grid-template-columns:1fr;gap:6px}
  .sms-quick-topup-btn{width:100%;height:32px;font-size:10px;border-radius:10px;box-shadow:0 6px 12px rgba(99,102,241,.18)}
  .sms-quick-topup input{height:32px;font-size:11px;border-radius:10px}
  .warning-strip{padding:10px 12px;border-radius:12px;gap:8px;font-size:10px}
  .warning-strip strong{font-size:10px;font-weight:700}
  .options-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
  .option-card{gap:5px;padding:9px;border-radius:12px;cursor:pointer;box-shadow:0 6px 14px rgba(15,23,42,.03)}
  .option-card::before{height:2px}
  .option-card h3{font-size:11px !important;line-height:1.3;font-weight:700;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .option-kicker{font-size:8px;margin-bottom:1px;font-weight:800}
  .option-status{height:18px;padding:0 6px;font-size:8px;font-weight:800}
  .option-card-desc,.option-card-details{display:none}
  .option-card-compact-meta{display:block;color:#64748b;font-size:9px;line-height:1.35}
  .options-panel,.history-panel{padding:10px;border-radius:14px;box-shadow:0 8px 18px rgba(15,23,42,.04)}
  .options-head{margin-bottom:10px;gap:8px}
  .options-head p,.history-title-wrap p{margin:0 0 4px;font-size:9px;font-weight:700}
  .options-head h2,.history-head h2{font-size:14px !important;font-weight:700;line-height:1.25}
  .history-head{margin-bottom:10px}
  .history-controls{flex-direction:column;align-items:stretch;gap:8px}
  .period-insight-row{grid-template-columns:1fr;gap:8px;margin-bottom:10px}
  .period-range-block,.period-stat-card{padding:10px 12px;border-radius:14px}
  .period-custom-dates{grid-template-columns:1fr}
  .filter-pill{width:100%;justify-content:space-between;flex-wrap:wrap;padding:3px;gap:2px}
  .filter-pill button{height:30px;padding:0 10px;font-size:10px;font-weight:700}
  .wallet-switch,.refresh-btn{height:32px;font-size:10px;border-radius:10px;padding:0 12px}
  .tx-list{gap:5px}
  .tx-item{grid-template-columns:minmax(0,1fr) auto;gap:4px 8px;padding:7px 9px;border-radius:10px;align-items:center;box-shadow:none}
  .tx-icon-box{display:none}
  .tx-title-row{gap:4px}
  .tx-title-row h3{font-size:10px !important;line-height:1.3;font-weight:700;-webkit-line-clamp:1}
  .tx-chip{display:none}
  .tx-meta{margin:1px 0 0;font-size:8px;gap:3px;line-height:1.3}
  .tx-meta span:nth-child(n+4){display:none}
  .tx-value{font-size:10px;font-weight:700;white-space:nowrap}
  .history-state{padding:28px 10px;font-size:11px}
  .deposit-method-grid,.wallet-choice-grid,.destination-toggle,.quick-amounts{grid-template-columns:repeat(2,minmax(0,1fr))}
  .wallet-modal-overlay{padding:12px}
  .wallet-modal{max-height:calc(100dvh - 24px)}
  .wallet-modal-head,.wallet-modal-body{padding:14px}
  .wallet-modal-head h3{font-size:15px !important}
  .wallet-modal-title-wrap p{font-size:10px}
  .wallet-modal-highlight{align-items:flex-start;flex-direction:column;padding:12px;border-radius:14px}
  .wallet-modal-highlight strong{font-size:16px !important}
  .wallet-modal-highlight small,.wallet-modal-highlight p{font-size:10px}
  .wallet-modal-symbol{width:40px;height:40px;border-radius:12px;font-size:18px}
  .wallet-modal-section{padding:12px;border-radius:14px;gap:10px}
  .wallet-modal-section-head strong{font-size:12px}
  .wallet-modal-section-head span{font-size:10px}
  .wallet-modal-title-row{flex-direction:column;align-items:stretch}
  .submit-btn{height:44px;font-size:12px;border-radius:12px}
}
@media (max-width:480px){
  .wallet-page{gap:7px;font-size:10px}
  .shortcut-card{padding:8px}
  .shortcut-card strong{font-size:10px}
  .shortcut-card small{font-size:7.5px}
  .wallet-hero{padding:9px 11px}
  .hero-main h2{font-size:15px !important}
  .hero-label,.hero-sub{font-size:8px}
  .summary-tile strong{font-size:11px}
  .sms-tile strong{font-size:13px !important}
  .sms-balance-caption,.sms-topup-chip,.sms-tile-head small{font-size:8px}
  .option-card{padding:8px;gap:4px}
  .option-card h3{font-size:10px !important}
  .option-card-compact-meta,.option-status,.option-kicker{font-size:8px}
  .options-head h2,.history-head h2{font-size:13px !important}
  .tx-item{padding:6px 8px}
  .tx-title-row h3,.tx-value{font-size:9px !important}
  .tx-meta{font-size:7.5px}
}
</style>
