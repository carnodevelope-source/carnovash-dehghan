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
      <article class="balance-strip">
        <div class="balance-strip-glow" aria-hidden="true"></div>
        <div class="balance-strip-main">
          <div class="balance-label-row">
            <span class="balance-icon-wrap">
              <IconlyIcon name="wallet" size="lg" tone="white" />
            </span>
            <div class="balance-label-text">
              <span class="balance-eyebrow">موجودی کل حساب</span>
              <span class="balance-status" :class="{ warn: regularLow || smsLow }">
                {{ regularLow || smsLow ? 'نیاز به شارژ' : 'وضعیت پایدار' }}
              </span>
            </div>
          </div>
          <h2 class="balance-amount">{{ moneyWithUnit(totalBalance) }}</h2>
          <p class="balance-hint">
            {{ selectedWalletId ? 'تراکنش‌های کیف پول انتخاب‌شده' : 'مجموع همه کیف‌پول‌ها' }}
          </p>
        </div>
        <div class="balance-actions">
          <button
            class="action-chip action-deposit"
            type="button"
            :disabled="!canDepositWalletAction || !hasDepositWallet"
            @click="openActionModal('deposit')"
          >
            <IconlyIcon name="plus" size="sm" tone="white" />
            <span>شارژ حساب</span>
          </button>
          <button
            class="action-chip action-withdraw"
            type="button"
            :disabled="withdrawButtonDisabled"
            @click="openActionModal('withdraw')"
          >
            <IconlyIcon name="arrowLeft" size="sm" tone="white" />
            <span>{{ withdrawButtonTitle }}</span>
          </button>
        </div>
      </article>

      <div class="stats-row">
        <article class="stat-chip stat-sms" :class="{ low: smsLow }">
          <div class="stat-chip-top">
            <span class="stat-chip-icon sms">
              <IconlyIcon name="message" size="sm" />
            </span>
            <div class="stat-chip-labels">
              <small>موجودی پیامک</small>
              <strong :class="{ danger: smsLow }">{{ moneyWithUnit(state.summary.sms_balance) }}</strong>
            </div>
            <span class="stat-badge" :class="{ warn: smsLow }">{{ smsBalanceStateLabel }}</span>
          </div>
          <div class="sms-topup-inline">
            <input
              :value="smsTopUpAmountText"
              type="text"
              inputmode="numeric"
              placeholder="مبلغ انتقال (تومان)"
              :disabled="smsTopUpSubmitting || !canWithdrawWalletAction"
              @input="onSmsTopUpAmountInput"
              @keydown.enter.prevent="submitSmsTopUpFromMain"
            />
            <button
              type="button"
              class="sms-topup-btn"
              :disabled="smsTopUpDisabled"
              @click="submitSmsTopUpFromMain"
            >
              {{ smsTopUpSubmitting ? 'در حال انتقال...' : 'انتقال' }}
            </button>
          </div>
          <p class="sms-topup-hint">
            <template v-if="!canWithdrawWalletAction">انتقال فقط برای مدیران فعال است.</template>
            <template v-else-if="primaryDepositWallet">
              از کیف پول اصلی ({{ moneyWithUnit(primaryWalletBalance) }}) به پیامک
            </template>
            <template v-else>کیف پول اصلی برای انتقال یافت نشد.</template>
          </p>
        </article>

        <article class="stat-chip">
          <span class="stat-chip-icon in">
            <IconlyIcon name="graph" size="sm" />
          </span>
          <div class="stat-chip-labels">
            <small>جمع واریزی‌ها</small>
            <strong>{{ moneyWithUnit(state.summary.deposits_total) }}</strong>
          </div>
        </article>

        <article class="stat-chip">
          <span class="stat-chip-icon out">
            <IconlyIcon name="chart" size="sm" />
          </span>
          <div class="stat-chip-labels">
            <small>جمع برداشت‌ها</small>
            <strong>{{ moneyWithUnit(state.summary.withdrawals_total) }}</strong>
          </div>
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

      <div class="options-grid options-grid-desktop">
        <article
          v-for="option in sortedWalletOptions"
          :key="`desktop-${option.feature_key}`"
          class="option-card"
          :class="{
            active: option.is_active,
            unavailable: option.is_available === false,
            locked: option.installment_is_locked,
            purchased: option.is_active && option.is_available !== false,
            'not-purchased': !option.is_active && option.is_available !== false
          }"
          :style="{ '--option-accent': option.accent || '#1976d2' }"
        >
          <div class="option-card-head">
            <div class="option-card-title-wrap">
              <span class="option-card-icon">
                <IconlyIcon :name="optionIconName(option.feature_key)" size="xl" />
              </span>
              <div>
                <span class="option-kicker">{{ option.subtitle || option.personalized_title }}</span>
                <h3>{{ option.title }}</h3>
              </div>
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
          <div v-if="option.is_available === false" class="option-unavailable-box">
            <strong>{{ option.status_label || 'در دسترس نمی‌باشد' }}</strong>
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
                  @click.stop="submitNextInstallmentPayment(option)"
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
              <span>{{ option.cash_only ? 'فقط نقدی' : `اقساط ${Number(option.installment_months || 0).toLocaleString('fa-IR')} ماهه` }}</span>
              <strong>{{ moneyWithUnit(option.monthly_installment_amount) }}</strong>
              <small>پیش‌پرداخت: {{ moneyWithUnit(option.installment_upfront_amount) }}</small>
            </div>
          </div>
          <div v-if="option.installment_is_locked" class="option-lock-note">
            <strong>این بخش قفل شده است</strong>
            <small>{{ option.installment_lock_notice || 'قسط سررسید این آپشن پرداخت نشده است. برای باز شدن دسترسی، قسط را پرداخت کنید.' }}</small>
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
            <small v-else>این قابلیت برای این کارواش فعال است.</small>
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

      <div class="options-grid options-grid-mobile">
        <button
          v-for="option in sortedWalletOptions"
          :key="`mobile-${option.feature_key}`"
          type="button"
          class="option-tile"
          :class="optionStatusClass(option)"
          :style="{ '--option-accent': option.accent || '#1976d2' }"
          @click="openOptionDetail(option)"
        >
          <span class="option-tile-icon">
            <IconlyIcon :name="optionIconName(option.feature_key)" size="xl" />
          </span>
          <span class="option-tile-body">
            <strong>{{ option.title }}</strong>
            <small>{{ optionTileCaption(option) }}</small>
          </span>
          <span class="option-tile-status" :class="optionStatusClass(option)">
            {{ optionStatusText(option) }}
          </span>
          <span class="option-tile-arrow" aria-hidden="true">
            <IconlyIcon name="arrowLeft" size="sm" />
          </span>
        </button>
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
      <section class="wallet-modal option-detail-modal" :style="{ '--option-accent': detailOption.accent || '#1976d2' }">
        <header class="wallet-modal-head option-detail-head">
          <div class="option-detail-title-wrap">
            <span class="option-detail-icon">
              <IconlyIcon :name="optionIconName(detailOption.feature_key)" size="2xl" />
            </span>
            <div class="wallet-modal-title-wrap">
              <p>{{ detailOption.subtitle || detailOption.personalized_title }}</p>
              <h3>{{ detailOption.title }}</h3>
            </div>
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
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../services/api'
import { LIVE_EVENT_NAME } from '../../services/live'
import BaseDatePicker from '../base/BaseDatePicker.vue'
import BaseSpinner from '../base/BaseSpinner.vue'
import IconlyIcon from '../base/IconlyIcon.vue'
import { formatJalaliDate, parseJalaliToIso } from '../../utils/date'
import { formatThousandsToman, formatThousandsTomanValue, fromThousandsTomanInput } from '../../utils/money'
import { resolveApiErrorMessage } from '../../utils/apiError'
import { useAuthStore } from '../../store/auth.store'

const props = defineProps({
  searchQuery: { type: String, default: '' }
})

const router = useRouter()
const authStore = useAuthStore()
let liveReloadTimer = null

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

const optionIconName = (featureKey) => ({
  core_software: 'shieldDone',
  attendance: 'calendar',
  sms_club: 'message',
  cloud_storage: 'discovery',
  accounting: 'chart',
  excel_import: 'document'
}[featureKey] || 'category')

const optionTileCaption = (option) => {
  if (!option) return ''
  if (option.is_available === false) return option.unavailable_message || 'به‌زودی'
  if (option.is_active) return `پرداخت‌شده ${moneyWithUnit(option.paid_amount)}`
  return `از ${moneyWithUnit(option.cash_amount || option.total_amount)}`
}

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

const SILENT_REQUEST_META = { trackLoading: false, showErrorToast: false }

const loadWalletDashboard = async ({ silent = false } = {}) => {
  if (!silent) state.loading = true
  state.error = ''
  try {
    const periodQuery = buildPeriodQuery()
    const { data } = await api.get('/payments/wallet/dashboard/', {
      params: {
        type: state.filterType,
        q: (props.searchQuery || '').trim() || undefined,
        start: periodQuery.start,
        end: periodQuery.end
      },
      ...(silent ? { meta: SILENT_REQUEST_META } : {})
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
    if (!silent) state.loading = false
  }
}

const loadWalletOptions = async ({ silent = false } = {}) => {
  if (!silent) state.optionsLoading = true
  try {
    const { data } = await api.get('/payments/wallet/options/', silent ? { meta: SILENT_REQUEST_META } : {})
    state.options = Array.isArray(data?.options) ? data.options : []
    state.optionsTenant = data?.tenant || null
    state.licenseStatus = data?.license_status || state.licenseStatus || {}
    if (!optionModal.walletId && optionWallets.value.length) {
      optionModal.walletId = Number(optionWallets.value[0].id)
    }
  } catch (error) {
    state.error = resolveApiErrorMessage(error, 'بارگذاری آپشن‌ها ناموفق بود.')
  } finally {
    if (!silent) state.optionsLoading = false
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

onMounted(() => {
  // Registered before any await: an unmount during the initial load would
  // otherwise run the cleanup first and leave this listener attached forever.
  window.addEventListener(LIVE_EVENT_NAME, onLiveEvent)
  applyGatewayResultMessage()
  void Promise.all([loadWalletDashboard(), loadWalletOptions()])
})

const onLiveEvent = (event) => {
  const type = String(event?.detail?.type || '')
  if (type.startsWith('payment.') || type.startsWith('subscription.') || type.startsWith('wallet.')) {
    if (liveReloadTimer) window.clearTimeout(liveReloadTimer)
    liveReloadTimer = window.setTimeout(() => {
      void Promise.all([
        loadWalletDashboard({ silent: true }),
        loadWalletOptions({ silent: true })
      ])
    }, 500)
  }
}

onBeforeUnmount(() => {
  if (liveReloadTimer) window.clearTimeout(liveReloadTimer)
  window.removeEventListener(LIVE_EVENT_NAME, onLiveEvent)
})
</script>

<style scoped>
.wallet-page{
  --wallet-border:rgba(25,118,210,.12);
  --wallet-panel:#ffffff;
  --wallet-panel-soft:#f7f9fd;
  --wallet-text:#0f2545;
  --wallet-muted:#647892;
  --wallet-primary:#1976d2;
  --wallet-primary-soft:#dbe9ff;
  --wallet-success:#16a34a;
  --wallet-danger:#dc2626;
  display:grid;
  gap:14px
}
.wallet-alert{border-radius:14px;padding:12px 14px;font-weight:700;font-size:13px;border:1px solid transparent}
.wallet-alert-error{background:#fef2f2;color:#991b1b;border-color:#fecaca}
.wallet-alert-success{background:#f0fdf4;color:#166534;border-color:#bbf7d0}
.license-lock-banner{display:grid;gap:4px;padding:12px 14px;border-radius:14px;border:1px solid #fed7aa;background:#fffbeb;color:#92400e;font-size:13px}
.license-lock-banner.locked{border-color:#fecaca;background:#fef2f2;color:#991b1b}
.license-lock-banner strong{font-size:14px}
.license-lock-banner p{margin:0;line-height:1.7}
.license-lock-banner span{font-size:11px;font-weight:800}
.wallet-overview{display:grid;gap:10px}
.balance-strip{position:relative;overflow:hidden;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:18px 20px;border-radius:18px;background:linear-gradient(135deg,#0c3d78 0%,#1976d2 52%,#42a5f5 100%);box-shadow:0 12px 32px rgba(25,118,210,.22);border:1px solid rgba(255,255,255,.12)}
.balance-strip-glow{position:absolute;inset:-40% auto auto -10%;width:280px;height:280px;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.14),transparent 70%);pointer-events:none}
.balance-strip-main{position:relative;z-index:1;min-width:0}
.balance-label-row{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.balance-icon-wrap{width:38px;height:38px;border-radius:12px;background:rgba(255,255,255,.16);display:inline-flex;align-items:center;justify-content:center;backdrop-filter:blur(8px)}
.balance-label-text{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.balance-eyebrow{color:rgba(255,255,255,.82);font-size:12px;font-weight:700}
.balance-status{height:24px;padding:0 10px;border-radius:999px;background:rgba(255,255,255,.14);color:#fff;font-size:10px;font-weight:800;display:inline-flex;align-items:center}
.balance-status.warn{background:rgba(220,38,38,.28);color:#fecaca}
.balance-amount{margin:0;color:#fff;font-size:clamp(1.5rem,3vw,2rem);font-weight:850;line-height:1.15;letter-spacing:-.02em}
.balance-hint{margin:4px 0 0;color:rgba(255,255,255,.72);font-size:11px}
.balance-actions{position:relative;z-index:1;display:flex;gap:8px;flex-shrink:0}
.action-chip{display:inline-flex;align-items:center;gap:7px;height:40px;padding:0 16px;border:0;border-radius:12px;font:inherit;font-size:13px;font-weight:800;cursor:pointer;transition:transform .18s ease,opacity .18s ease;white-space:nowrap}
.action-chip:hover:not(:disabled){transform:translateY(-1px)}
.action-chip:disabled{opacity:.5;cursor:not-allowed}
.action-deposit{background:#fff;color:#0c3d78;box-shadow:0 6px 16px rgba(0,0,0,.12)}
.action-withdraw{background:rgba(255,255,255,.14);color:#fff;border:1px solid rgba(255,255,255,.22);backdrop-filter:blur(8px)}
.stats-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.stat-chip{display:flex;flex-direction:column;gap:8px;padding:12px 14px;border-radius:14px;background:var(--wallet-panel);border:1px solid var(--wallet-border);box-shadow:0 4px 14px rgba(15,37,69,.04);min-width:0}
.stat-chip-top{display:flex;align-items:center;gap:10px}
.stat-chip-icon{width:34px;height:34px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;background:var(--wallet-primary-soft)}
.stat-chip-icon.sms{background:#f3e8ff}
.stat-chip-icon.in{background:#dcfce7}
.stat-chip-icon.out{background:#fee2e2}
.stat-chip-labels{display:grid;gap:2px;min-width:0;flex:1}
.stat-chip-labels small{color:var(--wallet-muted);font-size:11px;font-weight:700}
.stat-chip-labels strong{color:var(--wallet-text);font-size:15px;font-weight:800;line-height:1.2;font-variant-numeric:tabular-nums}
.stat-chip-labels strong.danger{color:var(--wallet-danger)}
.stat-badge{height:22px;padding:0 8px;border-radius:999px;background:#ecfdf5;color:#166534;font-size:10px;font-weight:800;display:inline-flex;align-items:center;flex-shrink:0}
.stat-badge.warn{background:#fff7ed;color:#c2410c}
.stat-sms.low{border-color:rgba(234,88,12,.25);background:linear-gradient(165deg,#fffaf5,#fff)}
.sms-topup-inline{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;margin-top:4px;padding-top:10px;border-top:1px solid var(--wallet-border)}
.sms-topup-inline input{height:36px;border:1px solid var(--wallet-border);border-radius:10px;padding:0 11px;font:inherit;font-size:12px;font-weight:700;min-width:0;background:#fff}
.sms-topup-inline input:disabled{opacity:.55;cursor:not-allowed}
.sms-topup-btn{height:36px;padding:0 14px;border:0;border-radius:10px;background:var(--wallet-primary);color:#fff;font:inherit;font-size:12px;font-weight:800;cursor:pointer;white-space:nowrap;transition:opacity .15s ease,transform .15s ease}
.sms-topup-btn:hover:not(:disabled){transform:translateY(-1px)}
.sms-topup-btn:disabled{opacity:.5;cursor:not-allowed}
.sms-topup-hint{margin:0;color:var(--wallet-muted);font-size:10px;line-height:1.5;font-weight:600}
.stat-sms.low .sms-topup-inline{border-top-color:rgba(234,88,12,.2)}
.warning-strip{display:flex;align-items:center;gap:10px;background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;padding:10px 14px;color:#c2410c;font-size:13px}
.warning-dot{width:8px;height:8px;border-radius:50%;background:#f97316;flex-shrink:0}
.options-panel{background:var(--wallet-panel);border:1px solid var(--wallet-border);border-radius:16px;padding:16px;box-shadow:0 4px 16px rgba(15,37,69,.04)}
.options-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}
.options-head p{margin:0 0 2px;color:var(--wallet-muted);font-size:11px;font-weight:700}
.options-head h2{margin:0;color:var(--wallet-text);font-size:17px;font-weight:800}
.options-grid{display:grid;gap:10px}
.options-grid-desktop{grid-template-columns:repeat(3,minmax(0,1fr))}
.options-grid-mobile{display:none;grid-template-columns:1fr;gap:8px}
.option-card{--option-accent:#1976d2;display:grid;gap:12px;padding:16px;border:1px solid var(--wallet-border);border-radius:16px;background:var(--wallet-panel-soft);box-shadow:0 4px 14px rgba(15,37,69,.04);position:relative;overflow:hidden}
.option-card::before{content:'';position:absolute;inset:0 0 auto 0;height:3px;background:var(--option-accent)}
.option-card.purchased,.option-card.active.purchased{background:linear-gradient(165deg,#f0fdf4,#fff);border-color:rgba(22,163,74,.22)}
.option-card.not-purchased{background:linear-gradient(165deg,#fffaf5,#fff);border-color:rgba(234,88,12,.18)}
.option-card.unavailable{opacity:.85;background:#f8fafc}
.option-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.option-card-title-wrap{display:flex;align-items:flex-start;gap:10px;min-width:0}
.option-card-icon{width:40px;height:40px;border-radius:11px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;background:color-mix(in srgb,var(--option-accent) 12%,#fff);border:1px solid color-mix(in srgb,var(--option-accent) 20%,transparent)}
.option-kicker{display:block;color:var(--option-accent);font-size:10px;font-weight:800;margin-bottom:3px}
.option-card h3{margin:0;color:var(--wallet-text);font-size:16px;font-weight:800;line-height:1.3}
.option-card-desc{margin:0;color:var(--wallet-muted);font-size:12px;line-height:1.75}
.option-status{display:inline-flex;align-items:center;height:26px;padding:0 10px;border-radius:999px;background:#f1f5f9;color:#64748b;font-size:10px;font-weight:800;white-space:nowrap;flex-shrink:0}
.option-status.enabled{background:#dcfce7;color:#166534}
.option-status.buyable{background:#ffedd5;color:#c2410c}
.option-card.locked .option-status{background:#fee2e2;color:#991b1b}
.option-card.unavailable .option-status{background:#e2e8f0;color:#475569}
.option-inline-pay-btn{height:26px;padding:0 10px;border:0;border-radius:999px;background:linear-gradient(135deg,var(--option-accent),color-mix(in srgb,var(--option-accent) 75%,#fff));color:#fff;font-size:10px;font-weight:800;cursor:pointer;white-space:nowrap;font:inherit}
.option-inline-pay-btn:disabled{opacity:.65;cursor:not-allowed}
.option-live-stat-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.option-buy-btn{height:40px;border:0;border-radius:12px;background:linear-gradient(135deg,var(--option-accent),color-mix(in srgb,var(--option-accent) 72%,#fff));color:#fff;font-weight:800;cursor:pointer;font:inherit;font-size:13px}
.option-buy-btn:disabled{background:#e2e8f0;color:#64748b;cursor:not-allowed}
.option-tile{--option-accent:#1976d2;display:grid;grid-template-columns:auto 1fr auto auto;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--wallet-border);border-radius:14px;background:var(--wallet-panel-soft);cursor:pointer;text-align:right;transition:border-color .18s ease,box-shadow .18s ease,transform .18s ease,background .18s ease;font:inherit;width:100%}
.option-tile:hover{border-color:rgba(25,118,210,.28);box-shadow:0 6px 18px rgba(25,118,210,.08);transform:translateY(-1px);background:#fff}
.option-tile.purchased{border-color:rgba(22,163,74,.22);background:linear-gradient(165deg,#f0fdf4,#fff)}
.option-tile.buyable{border-color:rgba(234,88,12,.18)}
.option-tile.locked{border-color:rgba(220,38,38,.2);background:#fef2f2}
.option-tile.unavailable{opacity:.72}
.option-tile-icon{width:38px;height:38px;border-radius:11px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;background:color-mix(in srgb,var(--option-accent) 12%,#fff);border:1px solid color-mix(in srgb,var(--option-accent) 20%,transparent)}
.option-tile-body{display:grid;gap:2px;min-width:0}
.option-tile-body strong{color:var(--wallet-text);font-size:13px;font-weight:800;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.option-tile-body small{color:var(--wallet-muted);font-size:10px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.option-tile-status{height:22px;padding:0 8px;border-radius:999px;font-size:9px;font-weight:800;display:inline-flex;align-items:center;flex-shrink:0;background:#f1f5f9;color:#64748b}
.option-tile-status.purchased{background:#dcfce7;color:#166534}
.option-tile-status.buyable{background:#ffedd5;color:#c2410c}
.option-tile-status.locked{background:#fee2e2;color:#991b1b}
.option-tile-status.unavailable{background:#e2e8f0;color:#475569}
.option-tile-arrow{opacity:.35;flex-shrink:0}
.option-detail-head{align-items:center}
.option-detail-title-wrap{display:flex;align-items:center;gap:12px;min-width:0}
.option-detail-icon{width:48px;height:48px;border-radius:14px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;background:color-mix(in srgb,var(--option-accent) 12%,#fff);border:1px solid color-mix(in srgb,var(--option-accent) 22%,transparent)}
.option-detail-status{display:inline-flex;align-items:center;height:28px;padding:0 11px;border-radius:999px;font-size:11px;font-weight:900;width:max-content}
.option-detail-status.purchased{background:#dcfce7;color:#166534}
.option-detail-status.buyable{background:#ffedd5;color:#c2410c}
.option-detail-status.locked{background:#fee2e2;color:#991b1b}
.option-detail-status.unavailable{background:#e2e8f0;color:#475569}
.option-detail-desc{margin:0;color:var(--wallet-muted);font-size:13px;line-height:1.85}
.option-unavailable-box{display:grid;gap:6px;padding:12px;border:1px dashed #cbd5e1;border-radius:12px;background:#f8fafc}
.option-unavailable-box strong{color:#334155;font-size:13px}
.option-unavailable-box small{color:#64748b;font-size:12px;line-height:1.8}
.option-lock-note{display:grid;gap:5px;padding:11px 12px;border:1px solid #fecaca;border-radius:12px;background:#fef2f2}
.option-lock-note strong{color:#991b1b;font-size:12px}
.option-lock-note small{color:#7f1d1d;font-size:11px;font-weight:700;line-height:1.7}
.option-price-row,.option-installment-row{display:grid;gap:4px;padding:11px 12px;border:1px solid var(--wallet-border);border-radius:12px;background:#fff}
.option-price-row span,.option-installment-row span,.option-installment-row small{color:var(--wallet-muted);font-size:11px}
.option-price-row strong,.option-installment-row strong{color:var(--wallet-text);font-size:15px;font-weight:800}
.option-price-stack{display:grid;gap:8px}
.option-live-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.option-live-stat{padding:10px 11px;border:1px solid var(--wallet-border);border-radius:12px;background:#fff;display:grid;gap:4px}
.option-live-stat span{color:var(--wallet-muted);font-size:11px;font-weight:700}
.option-live-stat strong{color:var(--wallet-text);font-size:14px;font-weight:800;line-height:1.5}
.option-progress-block{display:grid;gap:8px;padding:12px;border:1px solid var(--wallet-border);border-radius:12px;background:#f8fafc}
.option-progress-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.option-progress-head span{color:var(--wallet-muted);font-size:11px;font-weight:800}
.option-progress-head strong{color:#166534;font-size:12px}
.option-progress-bar{height:6px;border-radius:999px;background:#e2e8f0;overflow:hidden}
.option-progress-bar span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--option-accent),color-mix(in srgb,var(--option-accent) 60%,#fff))}
.option-progress-block small{color:#64748b;font-size:10px;line-height:1.7}
.history-panel{background:var(--wallet-panel);border:1px solid var(--wallet-border);border-radius:16px;padding:16px;box-shadow:0 4px 16px rgba(15,37,69,.04)}
.history-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap}
.history-title-wrap p{margin:0 0 2px;color:var(--wallet-muted);font-size:11px;font-weight:700}
.history-head h2{margin:0;color:var(--wallet-text);font-size:17px;font-weight:800}
.history-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.period-insight-row{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(120px,.7fr) minmax(160px,1fr);gap:8px;align-items:stretch;margin:0 0 12px}
.period-range-block{display:grid;gap:8px;padding:10px 12px;border:1px solid var(--wallet-border);border-radius:12px;background:var(--wallet-panel-soft);min-width:0}
.period-range-chips{display:flex;flex-wrap:wrap;gap:6px}
.period-chip{height:30px;padding:0 11px;border:1px solid var(--wallet-border);border-radius:999px;background:#fff;color:#475569;font:inherit;font-size:11px;font-weight:800;cursor:pointer;transition:background .15s ease,color .15s ease}
.period-chip.active{background:var(--wallet-primary);border-color:transparent;color:#fff}
.period-custom-dates{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
.period-stat-card{display:grid;align-content:center;gap:4px;padding:10px 12px;border:1px solid var(--wallet-border);border-radius:12px;background:#fff;min-width:0}
.period-stat-card span{color:var(--wallet-muted);font-size:11px;font-weight:700}
.period-stat-card strong{color:var(--wallet-text);font-size:15px;font-weight:800;line-height:1.2}
.period-flow-values{display:flex;flex-wrap:wrap;gap:6px 10px;font-style:normal}
.period-flow-values em{font-style:normal;font-size:13px;font-weight:800}
.period-flow-values .in{color:#16a34a}
.period-flow-values .out{color:var(--wallet-danger)}
.tx-list{display:grid;gap:6px}
.tx-item{display:grid;grid-template-columns:36px minmax(0,1fr) auto;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--wallet-border);border-radius:12px;background:#fff;transition:border-color .15s ease,box-shadow .15s ease}
.tx-item:hover{border-color:rgba(25,118,210,.2);box-shadow:0 4px 12px rgba(15,37,69,.04)}
.tx-title-row{display:flex;align-items:center;justify-content:space-between;gap:8px}
.tx-title-row h3{margin:0;color:var(--wallet-text);font-size:13px;font-weight:700;line-height:1.35;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
.tx-chip{display:inline-flex;align-items:center;height:22px;padding:0 8px;border-radius:999px;font-size:9px;font-weight:800;flex-shrink:0}
.tx-chip-in{background:#dcfce7;color:#166534}
.tx-chip-out{background:#fee2e2;color:#b91c1c}
.tx-meta{margin:3px 0 0;color:#94a3b8;font-size:10px;display:flex;gap:5px;flex-wrap:wrap;line-height:1.35}
.tx-meta .separate{opacity:.5}
.tx-value{font-size:13px;font-weight:800;white-space:nowrap;font-variant-numeric:tabular-nums}
.tx-value-in{color:#16a34a}
.tx-value-out{color:var(--wallet-danger)}
.tx-icon-box{width:36px;height:36px;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;font-size:16px;font-weight:800;flex-shrink:0}
.tx-icon-box-in{background:#dcfce7;color:#16a34a}
.tx-icon-box-out{background:#fee2e2;color:#dc2626}
.wallet-switch{height:36px;border:1px solid var(--wallet-border);border-radius:10px;padding:0 12px;background:#fff;color:var(--wallet-text);font:inherit;font-size:12px;font-weight:700}
.filter-pill{display:flex;gap:3px;padding:4px;background:#f1f5f9;border-radius:999px;border:1px solid var(--wallet-border)}
.filter-pill button,.refresh-btn,.close-btn,.submit-btn,.quick-amounts button{border:0;cursor:pointer;font:inherit}
.filter-pill button{height:32px;padding:0 12px;border-radius:999px;background:transparent;color:#64748b;font-size:11px;font-weight:800;transition:background .15s ease,color .15s ease}
.filter-pill button.active{background:#fff;color:var(--wallet-primary);box-shadow:0 2px 8px rgba(25,118,210,.1)}
.refresh-btn{height:36px;padding:0 14px;border-radius:10px;background:var(--wallet-panel-soft);color:var(--wallet-text);font-size:11px;font-weight:800;border:1px solid var(--wallet-border)}
.history-state{padding:32px 12px;text-align:center;color:var(--wallet-muted);font-size:13px}
.separate{color:#cbd5e1}
.wallet-modal-overlay{position:fixed;inset:0;background:rgba(15,37,69,.45);backdrop-filter:blur(10px);display:flex;align-items:flex-start;justify-content:center;z-index:120;padding:16px;overflow-y:auto;overscroll-behavior:contain}
.wallet-modal{width:min(540px,100%);max-height:calc(100dvh - 32px);background:#fff;border-radius:18px;overflow:hidden;box-shadow:0 20px 48px rgba(15,37,69,.16);display:flex;flex-direction:column;min-height:0;margin:auto 0}
.financial-action-modal{width:min(680px,100%)}
.wallet-modal-deposit{--wallet-modal-accent:#1976d2}
.wallet-modal-withdraw{--wallet-modal-accent:#dc2626}
.wallet-modal-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;padding:18px 20px 14px;border-bottom:1px solid var(--wallet-border);background:#fff}
.wallet-modal-title-row{display:flex;align-items:center;gap:12px;min-width:0}
.wallet-modal-symbol{width:44px;height:44px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;background:color-mix(in srgb,var(--wallet-modal-accent,#1976d2) 10%,#fff);color:var(--wallet-modal-accent,#1976d2);font-size:20px;font-weight:900;flex-shrink:0}
.wallet-modal-title-wrap p{margin:0 0 3px;color:var(--wallet-muted);font-size:11px;font-weight:700}
.wallet-modal-head h3{margin:0;font-size:18px;color:var(--wallet-text);font-weight:800}
.close-btn{width:36px;height:36px;border-radius:10px;background:#f1f5f9;color:#475569;font-size:20px;line-height:1;transition:background .15s ease}
.close-btn:hover{background:#e2e8f0;color:var(--wallet-text)}
.wallet-modal-body{padding:16px 20px 20px;display:grid;gap:12px;overflow-y:auto;min-height:0;background:#fafbfd}
.wallet-modal-highlight{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px;border-radius:14px;background:#fff;border:1px solid var(--wallet-border)}
.wallet-modal-highlight small{display:block;color:var(--wallet-muted);font-size:11px;margin-bottom:4px;font-weight:700}
.wallet-modal-highlight strong{display:block;font-size:22px;color:var(--wallet-text);line-height:1.15;font-weight:850}
.wallet-modal-highlight p{margin:4px 0 0;color:var(--wallet-muted);font-size:11px;font-weight:700}
.wallet-modal-section{display:grid;gap:10px;padding:14px;border:1px solid var(--wallet-border);border-radius:14px;background:#fff}
.wallet-modal-section-head{display:flex;align-items:flex-end;justify-content:space-between;gap:10px;flex-wrap:wrap}
.wallet-modal-section-head strong{color:var(--wallet-text);font-size:14px;font-weight:800}
.wallet-modal-section-head span{color:var(--wallet-muted);font-size:11px;font-weight:600}
.destination-toggle{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;padding:4px;border-radius:12px;background:#f1f5f9}
.destination-toggle button{border:none;border-radius:10px;background:transparent;padding:10px 12px;display:grid;gap:3px;text-align:right;cursor:pointer;font:inherit;transition:background .15s ease}
.destination-toggle button.active{background:#fff;box-shadow:0 2px 8px rgba(15,37,69,.06)}
.destination-toggle span{color:var(--wallet-text);font-size:13px;font-weight:800}
.destination-toggle small{color:var(--wallet-muted);font-size:10px;font-weight:700}
.bank-withdraw-fields{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
.bank-withdraw-fields label{display:grid;gap:5px}
.bank-withdraw-fields span{font-size:11px;font-weight:800;color:#334155}
.bank-withdraw-fields input{width:100%;border:1px solid var(--wallet-border);border-radius:10px;padding:10px 12px;background:#fff;color:var(--wallet-text);font-weight:700;font:inherit;font-size:13px}
.wallet-choice-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.wallet-choice-card{min-height:80px;border:1px solid var(--wallet-border);border-radius:12px;background:#fafbfd;padding:12px;display:grid;gap:4px;text-align:right;cursor:pointer;transition:border-color .15s ease,background .15s ease;font:inherit}
.wallet-choice-card:hover{border-color:rgba(25,118,210,.25);background:#fff}
.wallet-choice-card.active{background:var(--wallet-primary-soft);border-color:rgba(25,118,210,.35)}
.wallet-choice-card small{color:#94a3b8;font-size:10px;font-weight:800}
.wallet-choice-card strong{color:var(--wallet-text);font-size:13px;font-weight:800}
.wallet-choice-card span{color:var(--wallet-primary);font-size:14px;font-weight:900}
.wallet-modal-body label{display:grid;gap:6px;color:#334155;font-weight:700}
.wallet-modal-body label span{font-size:12px}
.wallet-modal-body input,.wallet-modal-body select{height:46px;border:1px solid var(--wallet-border);border-radius:12px;padding:0 14px;background:#fff;color:var(--wallet-text);font-size:13px;outline:none;font:inherit}
.wallet-modal-body input:focus,.wallet-modal-body select:focus{border-color:var(--wallet-primary);box-shadow:0 0 0 3px rgba(25,118,210,.12)}
.amount-field{display:grid;gap:6px}
.amount-input-shell{display:flex;align-items:center;gap:8px;min-height:46px;border:1px solid var(--wallet-border);border-radius:12px;padding:0 12px;background:#fff}
.amount-input-shell:focus-within{border-color:var(--wallet-primary);box-shadow:0 0 0 3px rgba(25,118,210,.12)}
.amount-input-shell input{flex:1;min-width:0;height:auto;border:0;padding:0;background:transparent;box-shadow:none;font-size:15px;font-weight:800;color:var(--wallet-text)}
.amount-input-unit{color:var(--wallet-muted);font-size:12px;font-weight:800}
.quick-amounts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
.quick-amounts button{min-height:54px;padding:8px 12px;border-radius:12px;background:#fafbfd;color:var(--wallet-text);font-weight:800;border:1px solid var(--wallet-border);display:grid;gap:3px;text-align:right;transition:border-color .15s ease,background .15s ease;font:inherit}
.quick-amounts button small{color:var(--wallet-muted);font-size:10px;font-weight:700}
.quick-amounts button strong{font-size:14px;line-height:1.3}
.quick-amounts button.active{background:var(--wallet-primary-soft);border-color:rgba(25,118,210,.3)}
.wallet-inline-warning{display:block;padding:10px 12px;border-radius:10px;background:#fef2f2;color:#991b1b;font-size:11px;font-weight:800;line-height:1.6;grid-column:1 / -1}
.wallet-balance-preview-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.wallet-balance-preview{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px;border-radius:12px;background:#f0fdf4;color:#166534}
.wallet-balance-preview.destination{background:#eff6ff;color:#1d4ed8}
.wallet-balance-preview.danger{background:#fef2f2;color:#991b1b}
.wallet-balance-preview span{font-size:11px;font-weight:800}
.wallet-balance-preview strong{font-size:14px;font-weight:850}
.deposit-method-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.deposit-method-card{min-height:72px;border:1px solid var(--wallet-border);border-radius:12px;background:#fafbfd;display:grid;gap:4px;text-align:right;padding:12px;cursor:pointer;font:inherit}
.deposit-method-card.active{background:var(--wallet-primary-soft);border-color:rgba(25,118,210,.3)}
.deposit-method-card.disabled{opacity:.5;cursor:not-allowed}
.deposit-method-card span{font-size:11px;color:var(--wallet-muted)}
.company-card-box{display:grid;gap:6px;padding:14px;border-radius:12px;background:#f5f3ff;border:1px solid #ddd6fe}
.company-card-box small{color:var(--wallet-muted);font-size:11px}
.company-card-box strong{font-size:20px;letter-spacing:.06em;color:#6d28d9;direction:ltr;text-align:left;font-weight:850}
.company-card-box span{color:#334155;font-weight:800;font-size:13px}
.card-payment-instruction{margin:0;color:#475569;line-height:1.8;font-size:12px}
.deposit-tax-rows{display:grid;gap:6px}
.deposit-tax-rows > div{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 10px;border-radius:10px;background:#f8fafc;border:1px solid var(--wallet-border)}
.deposit-tax-rows span{color:var(--wallet-muted);font-size:11px;font-weight:700}
.deposit-tax-rows strong{color:var(--wallet-text);font-size:12px;font-weight:800}
.deposit-tax-rows strong.tax{color:#c2410c}
.deposit-tax-rows .net{background:#f0fdf4;border-color:#bbf7d0}
.deposit-tax-rows .net strong{color:#166534}
.support-ticket-btn{min-height:44px;border:none;border-radius:12px;background:var(--wallet-primary);color:#fff;font-weight:800;cursor:pointer;font:inherit;font-size:13px}
.wallet-note{padding:12px;border-radius:12px;background:#f8fafc;color:#475569;border:1px solid var(--wallet-border);line-height:1.75;font-size:12px}
.submit-btn{height:46px;border-radius:12px;color:#fff;font-weight:800;transition:transform .15s ease,opacity .15s ease;font:inherit;font-size:14px}
.submit-btn:hover:not(:disabled){transform:translateY(-1px)}
.submit-btn:disabled{opacity:.6;cursor:not-allowed}
.submit-deposit{background:linear-gradient(135deg,#1976d2,#42a5f5)}
.submit-withdraw{background:linear-gradient(135deg,#dc2626,#f87171)}
.option-purchase-modal{--option-accent:#1976d2}
.option-purchase-hero{padding:14px;border-radius:14px;background:color-mix(in srgb,var(--option-accent) 8%,#fff);border:1px solid color-mix(in srgb,var(--option-accent) 18%,transparent)}
.option-purchase-hero small{display:block;color:var(--option-accent);font-size:11px;font-weight:800;margin-bottom:4px}
.option-purchase-hero strong{display:block;color:var(--wallet-text);font-size:20px;font-weight:850}
.option-purchase-hero p{margin:4px 0 0;color:var(--wallet-muted);font-size:11px;line-height:1.7}
.payment-plan-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.payment-plan-card{border:1px solid var(--wallet-border);border-radius:12px;background:#fff;padding:12px;display:grid;gap:5px;text-align:right;cursor:pointer;font:inherit}
.payment-plan-card.active{border-color:#16a34a;background:#f0fdf4}
.payment-plan-card strong{color:var(--wallet-text);font-size:14px;font-weight:800}
.payment-plan-card span{color:#166534;font-size:15px;font-weight:900}
.payment-plan-card small{color:var(--wallet-muted);font-size:11px;line-height:1.6}
.upfront-input-box small{color:var(--wallet-muted);font-size:11px;line-height:1.7;font-weight:700}
.installment-live-preview{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.installment-live-preview div{padding:11px;border:1px solid var(--wallet-border);border-radius:12px;background:#fff;display:grid;gap:4px}
.installment-live-preview span{color:var(--wallet-muted);font-size:11px;font-weight:800}
.installment-live-preview strong{color:var(--wallet-text);font-size:15px;font-weight:850}
@media (max-width:900px){
  .stats-row{grid-template-columns:1fr}
  .balance-strip{flex-direction:column;align-items:stretch}
  .balance-actions{width:100%}
  .action-chip{flex:1;justify-content:center}
  .history-head,.options-head{flex-direction:column;align-items:stretch}
  .period-insight-row{grid-template-columns:1fr}
  .options-grid-desktop{grid-template-columns:repeat(2,minmax(0,1fr))}
  .payment-plan-grid,.installment-live-preview,.option-live-grid,.bank-withdraw-fields,.wallet-balance-preview-grid{grid-template-columns:1fr}
  .deposit-method-grid,.wallet-choice-grid,.destination-toggle,.quick-amounts{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:640px){
  .wallet-page{gap:10px}
  .options-grid-desktop{display:none}
  .options-grid-mobile{display:grid}
  .option-tile{grid-template-columns:auto 1fr auto;gap:8px}
  .option-tile-status{display:none}
  .history-controls{flex-direction:column;align-items:stretch}
  .filter-pill{width:100%;justify-content:space-between}
  .tx-item{grid-template-columns:minmax(0,1fr) auto;gap:6px}
  .tx-icon-box{display:none}
  .tx-chip{display:none}
  .deposit-method-grid,.wallet-choice-grid,.destination-toggle,.quick-amounts{grid-template-columns:1fr}
  .wallet-modal-overlay{padding:10px}
  .wallet-modal{max-height:calc(100dvh - 20px)}
}
</style>
