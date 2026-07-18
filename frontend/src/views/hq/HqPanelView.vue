<template>
  <div class="hq-page" :class="{ 'support-only': !authStore.isHqAdmin }" dir="rtl">
    <div class="hq-bg hq-bg-one"></div>
    <div class="hq-bg hq-bg-two"></div>

    <div
      v-if="authStore.isHqAdmin && isMobileSidebarOpen"
      class="hq-mobile-overlay"
      @click="closeMobileSidebar"
    ></div>

    <aside
      v-if="authStore.isHqAdmin"
      class="hq-sidebar"
      :class="{ 'hq-sidebar-mobile-open': isMobileSidebarOpen }"
    >
      <div class="hq-brand">
        <span class="hq-brand-badge">HQ</span>
        <div>
          <strong>پنل مرکزی</strong>
          <small>مدیریت یکپارچه کارواش‌ها، پشتیبانی و گزارشات</small>
        </div>
      </div>

      <nav class="hq-nav">
        <button
          v-for="tab in visibleTabs"
          :key="tab.key"
          type="button"
          class="hq-nav-item"
          :class="{ active: activeTab === tab.key }"
          @click="selectTab(tab.key)"
        >
          <span class="hq-nav-title">{{ tab.label }}</span>
          <span class="hq-nav-meta">{{ tab.meta }}</span>
          <span v-if="tab.key === 'tickets' && openTicketCount > 0" class="hq-nav-count">{{ toFa(openTicketCount) }}</span>
        </button>
      </nav>

      <div class="hq-profile">
        <div>
          <strong>{{ authStore.user?.full_name || authStore.user?.username }}</strong>
          <small>{{ authStore.isHqAdmin ? 'مدیرکل مجموعه' : 'پشتیبان مرکزی' }}</small>
        </div>
        <button type="button" class="ghost-btn" @click="logout">خروج</button>
      </div>
    </aside>

    <main class="hq-main">
      <header class="hq-header" :class="{ 'hq-header-compact': !authStore.isHqAdmin }">
        <div>
          <p class="hq-kicker">{{ authStore.isHqAdmin ? 'مرکز کنترل پلتفرم' : 'Ticket Desk' }}</p>
          <h1>{{ currentTabTitle }}</h1>
        </div>
        <div class="hq-header-tools">
          <button
            v-if="authStore.isHqAdmin"
            type="button"
            class="hq-mobile-menu-btn"
            :aria-expanded="isMobileSidebarOpen"
            aria-label="باز کردن منوی پنل مرکزی"
            @click="toggleMobileSidebar"
          >
            ☰
          </button>
          <span class="hq-role-badge">{{ authStore.isHqAdmin ? 'HQ Admin' : 'HQ Support' }}</span>
          <button v-if="activeTab === 'overview'" type="button" class="primary-btn" @click="loadOverview">به‌روزرسانی</button>
          <button v-if="!authStore.isHqAdmin" type="button" class="ghost-btn" @click="logout">خروج</button>
        </div>
      </header>

      <section v-if="activeTab === 'overview'" class="overview-grid">
        <article class="hero-card">
          <div class="hero-stats">
            <div class="metric-box">
              <small>کارواش فعال</small>
              <strong>{{ overview.summary.active_carwashes || 0 }}</strong>
            </div>
            <div class="metric-box">
              <small>تیکت باز</small>
              <strong>{{ overview.summary.open_tickets || 0 }}</strong>
            </div>
            <div class="metric-box">
              <small>خودروهای امروز</small>
              <strong>{{ overview.summary.today_vehicles || 0 }}</strong>
            </div>
          </div>
        </article>

        <article class="summary-card">
          <div class="summary-head">
            <h3>خلاصه سریع</h3>
            <span>شاخص‌های کلیدی امروز</span>
          </div>
          <div class="summary-items">
            <div class="summary-item">
              <span>کل کارواش‌ها</span>
              <strong>{{ overview.summary.total_carwashes || 0 }}</strong>
            </div>
            <div class="summary-item warn">
              <span>تیکت فوری</span>
              <strong>{{ overview.summary.urgent_tickets || 0 }}</strong>
            </div>
            <div class="summary-item">
              <span>پشتیبان فعال</span>
              <strong>{{ overview.summary.hq_support_users || 0 }}</strong>
            </div>
          </div>
        </article>

        <article class="list-card">
          <div class="card-head">
            <h3>کارواش‌های تازه</h3>
            <button type="button" class="link-btn" @click="activeTab = 'carwashes'">مدیریت</button>
          </div>
          <div class="compact-list">
            <div v-for="item in overview.recent_carwashes" :key="item.id" class="compact-row">
              <div>
                <strong>{{ item.name }}</strong>
                <small>{{ item.manager?.full_name || 'بدون مدیر' }}</small>
              </div>
              <span class="status-dot" :class="{ off: !item.is_active }">{{ item.is_active ? 'فعال' : 'غیرفعال' }}</span>
            </div>
          </div>
        </article>

        <article class="list-card">
          <div class="card-head">
            <h3>آخرین تیکت‌ها</h3>
            <button type="button" class="link-btn" @click="activeTab = 'tickets'">ورود به مرکز تیکت</button>
          </div>
          <div class="compact-list">
            <div v-for="item in overview.recent_tickets" :key="item.id" class="compact-row">
              <div>
                <strong>{{ item.subject }}</strong>
                <small>{{ item.tenant_name }}</small>
              </div>
              <span class="ticket-mini-status" :class="`ticket-${item.status}`">{{ statusLabel(item.status) }}</span>
            </div>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'carwashes'" class="workspace-grid carwash-ops-grid">
        <article class="glass-card create-card">
          <div class="card-head">
            <h3>ثبت کارواش و مدیر</h3>
            <span>ساخت پنل جدید برای مشتری با مدیر اختصاصی</span>
          </div>
          <form class="form-grid" @submit.prevent="createCarwash">
            <label>
              <span>نام کارواش</span>
              <input v-model.trim="createForm.carwash_name" required placeholder="مثلا کارواش امیران" />
            </label>
            <label>
              <span>آدرس کارواش</span>
              <input v-model.trim="createForm.carwash_address" placeholder="آدرس کامل کارواش" />
            </label>
            <label>
              <span>نام مدیر</span>
              <input v-model.trim="createForm.manager_first_name" required placeholder="علی" />
            </label>
            <label>
              <span>نام خانوادگی مدیر</span>
              <input v-model.trim="createForm.manager_last_name" required placeholder="محمدی" />
            </label>
            <label>
              <span>نام کاربری مدیر</span>
              <input v-model.trim="createForm.manager_username" required placeholder="manager.amiran" />
            </label>
            <label>
              <span>موبایل مدیر</span>
              <input v-model.trim="createForm.manager_phone" required placeholder="09xxxxxxxxx" />
            </label>
            <label class="wide">
              <span>رمز عبور اولیه</span>
              <input v-model="createForm.manager_password" type="password" required placeholder="حداقل 6 کاراکتر" />
            </label>
            <div class="wide form-actions">
              <button class="primary-btn" type="submit">ثبت کارواش</button>
            </div>
          </form>
        </article>

        <article class="glass-card tenant-command-card" :class="{ loading: carwashInsight.loading }">
          <div class="tenant-command-empty" v-if="carwashInsight.error && !carwashInsight.loading">
            <span class="tenant-command-mark error">!</span>
            <h3>دریافت اطلاعات ناموفق بود</h3>
            <p>{{ carwashInsight.error }}</p>
          </div>

          <div class="tenant-command-empty" v-else-if="!selectedCarwashInsight && !carwashInsight.loading">
            <span class="tenant-command-mark">HQ</span>
            <h3>مرکز نظارت کارواش</h3>
            <p>روی نام هر کارواش کلیک کنید تا وضعیت کیف پول، اقساط آپشن‌ها و ورود و خروج همان مجموعه یکجا نمایش داده شود.</p>
          </div>

          <div v-else-if="carwashInsight.loading" class="tenant-command-empty">
            <span class="tenant-command-mark pulse">...</span>
            <h3>در حال بارگذاری داده‌ها</h3>
            <p>اطلاعات مالی و عملیاتی کارواش انتخاب‌شده در حال دریافت است.</p>
          </div>

          <div v-else class="tenant-command-content">
            <header class="tenant-command-head">
              <div>
                <small>نمای ۳۶۰ درجه</small>
                <h3>{{ selectedCarwashInsight.tenant.name }}</h3>
                <p>{{ selectedCarwashInsight.tenant.address || 'آدرس ثبت نشده' }}</p>
              </div>
              <button type="button" class="refresh-btn" @click="loadCarwashInsight(selectedCarwashInsight.tenant.id)">
                بروزرسانی
              </button>
            </header>

            <div class="tenant-kpi-grid">
              <div class="tenant-kpi-card primary">
                <small>موجودی کل</small>
                <strong>{{ money(selectedCarwashInsight.wallet.summary.total_balance) }}</strong>
                <span>اصلی {{ money(selectedCarwashInsight.wallet.summary.regular_balance) }}</span>
              </div>
              <div class="tenant-kpi-card">
                <small>اقساط فعال</small>
                <strong>{{ toFa(selectedCarwashInsight.options.summary.installment_count) }}</strong>
                <span>مانده {{ money(selectedCarwashInsight.options.summary.remaining_total) }}</span>
              </div>
              <div class="tenant-kpi-card">
                <small>حاضر امروز</small>
                <strong>{{ toFa(selectedCarwashInsight.attendance.summary.present_count) }}</strong>
                <span>از {{ toFa(selectedCarwashInsight.attendance.summary.worker_count) }} نیرو</span>
              </div>
              <div class="tenant-kpi-card">
                <small>خودروهای امروز</small>
                <strong>{{ toFa(selectedCarwashInsight.attendance.summary.today_vehicle_count) }}</strong>
                <span>{{ toFa(selectedCarwashInsight.attendance.summary.today_active_vehicle_count) }} فعال</span>
              </div>
            </div>

            <div class="tenant-monitor-grid">
              <section class="tenant-monitor-panel">
                <div class="tenant-panel-head">
                  <h4>کیف پول</h4>
                  <span>امروز: +{{ money(selectedCarwashInsight.wallet.summary.today_deposit_total) }} / -{{ money(selectedCarwashInsight.wallet.summary.today_withdraw_total) }}</span>
                </div>
                <div class="wallet-monitor-list">
                  <div v-for="wallet in selectedCarwashInsight.wallet.wallets" :key="wallet.id" class="wallet-monitor-row">
                    <div>
                      <strong>{{ wallet.name }}</strong>
                      <small>{{ wallet.wallet_type === 'sms' ? 'پیامک' : 'اصلی' }}</small>
                    </div>
                    <span>{{ money(wallet.balance) }}</span>
                  </div>
                </div>
              </section>

              <section class="tenant-monitor-panel">
                <div class="tenant-panel-head">
                  <h4>آپشن‌ها و اقساط</h4>
                  <span>ماهیانه {{ money(selectedCarwashInsight.options.summary.monthly_total) }}</span>
                </div>
                <div class="option-monitor-list">
                  <div v-for="option in selectedCarwashInsight.options.purchases" :key="option.id" class="option-monitor-row" :class="{ active: option.is_active }">
                    <div>
                      <strong>{{ option.title }}</strong>
                      <small>{{ paymentPlanLabel(option.payment_plan) }}</small>
                    </div>
                    <span>{{ option.remaining_amount > 0 ? money(option.remaining_amount) : 'تسویه' }}</span>
                  </div>
                  <div v-if="!selectedCarwashInsight.options.purchases.length" class="empty-note">آپشنی برای این کارواش ثبت نشده است.</div>
                </div>
              </section>
            </div>

            <section class="tenant-monitor-panel wide-panel">
              <div class="tenant-panel-head">
                <h4>ورود و خروج امروز</h4>
                <span>{{ toFa(selectedCarwashInsight.attendance.summary.present_count) }} نفر داخل صف کاری</span>
              </div>
              <div class="attendance-monitor-list">
                <div v-for="worker in selectedCarwashInsight.attendance.workers" :key="worker.worker_id" class="attendance-monitor-row" :class="worker.current_status">
                  <span class="attendance-dot"></span>
                  <div>
                    <strong>{{ worker.name }}</strong>
                    <small>{{ worker.first_in_at ? `ورود: ${dateTime(worker.first_in_at)}` : 'ورودی امروز ندارد' }}</small>
                  </div>
                  <em>{{ worker.current_status === 'in' ? 'حاضر' : 'خارج' }}</em>
                </div>
                <div v-if="!selectedCarwashInsight.attendance.workers.length" class="empty-note">نیرویی برای این کارواش ثبت نشده است.</div>
              </div>
            </section>

            <section class="tenant-monitor-panel wide-panel">
              <div class="tenant-panel-head">
                <h4>آخرین تراکنش‌های کیف پول</h4>
                <span>{{ toFa(selectedCarwashInsight.wallet.recent_transactions.length) }} تراکنش</span>
              </div>
              <div class="transaction-monitor-list">
                <div v-for="tx in selectedCarwashInsight.wallet.recent_transactions" :key="tx.id" class="transaction-monitor-row" :class="tx.direction">
                  <div>
                    <strong>{{ tx.description || tx.wallet_name }}</strong>
                    <small>{{ dateTime(tx.transacted_at) }}</small>
                  </div>
                  <span>{{ tx.direction === 'in' ? '+' : '-' }}{{ money(tx.amount) }}</span>
                </div>
                <div v-if="!selectedCarwashInsight.wallet.recent_transactions.length" class="empty-note">تراکنشی برای نمایش وجود ندارد.</div>
              </div>
            </section>
          </div>
        </article>

        <article class="glass-card table-card">
          <div class="card-head">
            <h3>نظارت بر کارواش‌ها</h3>
            <span>{{ carwashes.length.toLocaleString('fa-IR') }} مورد</span>
          </div>
          <div class="table-toolbar">
            <input v-model.trim="carwashQuery" class="table-search" placeholder="جستجو در نام کارواش، مدیر یا آدرس..." />
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>کارواش</th>
                  <th>مدیر</th>
                  <th>موبایل مدیر</th>
                  <th>تیکت باز</th>
                  <th>تاریخ بروزرسانی</th>
                  <th>وضعیت</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in filteredCarwashes" :key="row.id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>
                    <button type="button" class="tenant-name-btn" :class="{ active: selectedCarwashInsight?.tenant?.id === row.id }" @click="loadCarwashInsight(row.id)">
                      {{ row.name }}
                    </button>
                    <small class="row-sub">{{ row.address || '-' }}</small>
                  </td>
                  <td>{{ row.manager?.full_name || '-' }}</td>
                  <td>{{ row.manager?.phone || '-' }}</td>
                  <td>{{ Number(row.tickets_open_count || 0).toLocaleString('fa-IR') }}</td>
                  <td>{{ formatDate(row.updated_at) }}</td>
                  <td>
                    <button type="button" class="status-pill status-toggle" :class="{ off: !row.is_active }" @click="toggleCarwashState(row)">
                      {{ row.is_active ? 'فعال' : 'غیرفعال' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'tickets'" class="ticket-command-center" :class="{ 'support-ticket-mode': !authStore.isHqAdmin }">
        <article class="ticket-modern-shell ticket-workspace-head">
          <div class="ticket-workspace-copy">
            <span class="desk-kicker">{{ authStore.isHqAdmin ? 'HQ Ticket Center' : 'Assigned Support Desk' }}</span>
            <h3>{{ authStore.isHqAdmin ? 'مرکز پاسخ‌گویی تیکت‌ها' : 'صف پاسخ‌گویی تیکت‌های شما' }}</h3>
            <p>{{ visibleTickets.length.toLocaleString('fa-IR') }} تیکت در نمای فعلی. نمای فعال: {{ activeTicketScopeLabel }}</p>
          </div>
          <div class="ticket-workspace-actions">
            <div class="ticket-workspace-stat">
              <small>باز</small>
              <strong>{{ toFa(ticketSummaryCards.find((item) => item.key === 'open')?.value || 0) }}</strong>
            </div>
            <div class="ticket-workspace-stat">
              <small>فوری</small>
              <strong>{{ toFa(ticketSummaryCards.find((item) => item.key === 'urgent')?.value || 0) }}</strong>
            </div>
            <button type="button" class="link-btn desk-refresh-btn" @click="loadTickets">بروزرسانی</button>
          </div>
        </article>

        <div class="command-body-grid command-body-grid-simple" :class="{ compact: !authStore.isHqAdmin }">
          <article class="ticket-list-shell ticket-inbox-shell ticket-modern-shell command-inbox-card">
            <div class="card-head ticket-inbox-head">
              <div>
                <h3>اینباکس و صف تیکت‌ها</h3>
                <span>{{ visibleTickets.length.toLocaleString('fa-IR') }} مورد در نمای فعلی</span>
              </div>
            </div>

            <div class="ticket-filter-grid ticket-filter-grid-wide ticket-filter-grid-desk" :class="{ compact: !authStore.isHqAdmin }">
              <input v-model.trim="ticketQuery" placeholder="جستجو در عنوان، متن، نام کارواش یا کاربر..." @input="loadTickets" />
              <select v-if="authStore.isHqAdmin" v-model="ticketStatus" @change="loadTickets">
                <option value="all">همه وضعیت‌ها</option>
                <option value="open">باز</option>
                <option value="pending">در انتظار پیگیری</option>
                <option value="answered">پاسخ داده شده</option>
                <option value="closed">بسته شده</option>
              </select>
              <select v-model="ticketPriority" @change="loadTickets">
                <option value="all">همه اولویت‌ها</option>
                <option value="low">کم</option>
                <option value="medium">متوسط</option>
                <option value="high">بالا</option>
                <option value="urgent">فوری</option>
              </select>
              <select v-if="authStore.isHqAdmin" v-model="ticketTenantId" @change="loadTickets">
                <option value="">همه کارواش‌ها</option>
                <option v-for="item in carwashes" :key="item.id" :value="item.id">{{ item.name }}</option>
              </select>
            </div>

            <div class="hq-ticket-scope-row">
              <button
                v-for="scope in ticketScopeOptions"
                :key="scope.key"
                type="button"
                class="scope-chip"
                :class="{ active: ticketScope === scope.key }"
                @click="ticketScope = scope.key"
              >
                {{ scope.label }}
              </button>
            </div>

            <div class="ticket-list ticket-list-modern">
              <button
                v-for="item in visibleTickets"
                :key="item.id"
                type="button"
                class="ticket-thread ticket-thread-rich desk-ticket-thread"
                :class="{ active: selectedTicket?.id === item.id }"
                @click="selectTicket(item.id)"
              >
                <div class="ticket-thread-top">
                  <strong>{{ item.subject }}</strong>
                  <span class="ticket-mini-status" :class="`ticket-${item.status}`">{{ statusLabel(item.status) }}</span>
                </div>
                <div class="ticket-thread-meta">
                  <span>{{ item.tenant_name }}</span>
                  <span>{{ priorityLabel(item.priority) }}</span>
                </div>
                <p>{{ item.last_message_preview || item.message }}</p>
                <div class="ticket-thread-foot">
                  <small>#{{ item.id }}</small>
                  <small>{{ ticketSlaShortLabel(item) }}</small>
                </div>
              </button>
              <div v-if="!visibleTickets.length" class="ticket-list-empty desk-empty">
                <strong>تیکتی در این نما پیدا نشد</strong>
                <span>فیلترها را تغییر دهید یا دوباره بروزرسانی کنید.</span>
              </div>
            </div>
          </article>

          <article v-if="selectedTicket" class="ticket-chat-shell ticket-chat-shell-rich ticket-modern-shell command-chat-card">
            <div class="desk-detail-head">
              <div class="chat-head ticket-chat-head desk-ticket-chat-head">
                <div>
                  <div class="ticket-chat-title">
                    <h3>{{ selectedTicket.subject }}</h3>
                    <span class="ticket-mini-status" :class="`ticket-${selectedTicket.status}`">{{ statusLabel(selectedTicket.status) }}</span>
                  </div>
                  <p>{{ selectedTicket.tenant_name }}</p>
                </div>
                <div class="chat-head-badges">
                  <span class="meta-chip">{{ categoryLabel(selectedTicket.category) }}</span>
                  <span class="meta-chip">{{ priorityLabel(selectedTicket.priority) }}</span>
                  <span class="meta-chip">#{{ selectedTicket.id }}</span>
                </div>
              </div>

            </div>

            <div class="chat-head-actions ticket-chat-actions desk-ticket-actions">
              <select v-model="ticketReply.status">
                <option value="">بدون تغییر وضعیت</option>
                <option value="answered">پاسخ داده شده</option>
                <option value="pending">در انتظار پیگیری</option>
                <option value="closed">بستن تیکت</option>
              </select>
              <select v-if="authStore.isHqAdmin" v-model="ticketReply.assign_to_user_id">
                <option :value="0">بدون ارجاع</option>
                <option v-for="member in teamAssignable" :key="member.id" :value="member.id">
                  {{ member.full_name || member.username }}
                </option>
              </select>
            </div>

            <section v-if="canApproveRegistration" class="registration-approval-card">
              <div>
                <span>تایید ثبت‌نام کارواش</span>
                <strong>مدارک بارگذاری‌شده را بررسی کنید و بعد حساب را فعال کنید.</strong>
                <p>بعد از تایید، لاگین مدیر باز می‌شود و پیامک فعال‌سازی برای شماره ثبت‌شده ارسال خواهد شد.</p>
              </div>
              <button type="button" class="primary-btn" :disabled="registrationApproval.submitting" @click="approveRegistrationTicket">
                {{ registrationApproval.submitting ? 'در حال تایید...' : 'تایید ثبت‌نام و فعال‌سازی' }}
              </button>
              <small v-if="registrationApproval.message" class="transfer-feedback success">{{ registrationApproval.message }}</small>
              <small v-if="registrationApproval.error" class="transfer-feedback error">{{ registrationApproval.error }}</small>
            </section>

            <section v-if="isWalletOperationTicket(selectedTicket)" class="wallet-ticket-transfer-card">
              <div>
                <span>عملیات تیکت پرداخت</span>
                <strong>انتقال پول به کیف پول مقصد</strong>
                <p>بعد از بررسی رسید، مبلغ تایید شده را وارد کنید تا مستقیم به کیف پول صاحب تیکت اضافه شود.</p>
              </div>
              <label>
                <span>مبلغ انتقال (تومان)</span>
                <input v-model="walletTransfer.amountText" inputmode="numeric" placeholder="مثلا ۲۵۰۰۰۰" />
              </label>
              <button type="button" class="primary-btn wallet-transfer-btn" :disabled="walletTransfer.submitting" @click="submitWalletTransfer">
                {{ walletTransfer.submitting ? walletOperationSubmittingLabel : walletOperationButtonLabel }}
              </button>
              <small v-if="walletTransfer.error" class="transfer-feedback error">{{ walletTransfer.error }}</small>
              <small v-if="walletTransfer.success" class="transfer-feedback success">{{ walletTransfer.success }}</small>
            </section>

            <section v-if="selectedTicket.attachments?.length" class="hq-ticket-attachments">
              <div class="reply-head">
                <strong>رسیدها و فایل‌های پیوست</strong>
                <small>{{ toFa(selectedTicket.attachments.length) }} فایل</small>
              </div>
              <div class="hq-ticket-attachments-list">
                <a
                  v-for="attachment in selectedTicket.attachments"
                  :key="attachment.id"
                  class="hq-ticket-attachment-item"
                  :href="attachment.file_url"
                  target="_blank"
                  rel="noreferrer"
                >
                  <strong>{{ attachment.original_name || 'فایل پیوست' }}</strong>
                  <span>باز کردن فایل</span>
                </a>
              </div>
            </section>

            <div class="chat-stream ticket-chat-stream desk-ticket-stream">
              <div
                v-for="message in selectedTicket.messages"
                :key="message.id"
                class="chat-bubble ticket-chat-bubble desk-ticket-bubble"
                :class="{ mine: message.sender === authStore.user?.id, internal: message.is_internal }"
              >
                <div class="chat-meta">
                  <strong>{{ message.sender_name }}</strong>
                  <span>{{ roleLabel(message) }}</span>
                </div>
                <p>{{ message.body }}</p>
                <small>{{ dateTime(message.created_at) }}</small>
              </div>
            </div>

            <div class="chat-reply ticket-chat-reply desk-ticket-reply">
              <div class="template-chip-row" :class="{ compact: !authStore.isHqAdmin }">
                <button
                  v-for="template in ticketResponseTemplates"
                  :key="template.id"
                  type="button"
                  class="template-chip"
                  @click="applyTicketTemplate(template.body)"
                >
                  {{ template.title }}
                </button>
              </div>
              <textarea v-model.trim="ticketReply.body" placeholder="پاسخ کامل، ساختاریافته و حرفه‌ای برای کارواش بنویس..." />
              <div class="chat-tools">
                <label v-if="authStore.isHqAdmin" class="internal-toggle">
                  <input v-model="ticketReply.is_internal" type="checkbox" />
                  <span>یادداشت داخلی</span>
                </label>
                <button type="button" class="primary-btn" @click="sendTicketReply">ارسال پاسخ</button>
              </div>
            </div>
          </article>

          <article v-else class="ticket-placeholder ticket-placeholder-rich ticket-modern-shell desk-placeholder command-chat-card">
            <strong>یک تیکت را از اینباکس انتخاب کنید</strong>
            <span>جزئیات کامل، گفتگو، ارجاع، وضعیت و پاسخ‌گویی از همین بخش انجام می‌شود.</span>
          </article>
        </div>
      </section>

      <section v-else-if="activeTab === 'team'" class="workspace-grid">
        <article class="glass-card create-card">
          <div class="card-head">
            <h3>افزودن پشتیبان ساده</h3>
            <span>دسترسی: فقط مرکز تیکت</span>
          </div>
          <form class="form-grid" @submit.prevent="createSupportUser">
            <label>
              <span>نام</span>
              <input v-model.trim="supportForm.first_name" required placeholder="میلاد" />
            </label>
            <label>
              <span>نام خانوادگی</span>
              <input v-model.trim="supportForm.last_name" required placeholder="دهستانی" />
            </label>
            <label>
              <span>نام کاربری</span>
              <input v-model.trim="supportForm.username" required placeholder="milad.dehestani" />
            </label>
            <label>
              <span>موبایل</span>
              <input v-model.trim="supportForm.phone" required placeholder="09xxxxxxxxx" />
            </label>
            <label class="wide">
              <span>رمز عبور</span>
              <input v-model="supportForm.password" type="password" minlength="6" required placeholder="حداقل 6 کاراکتر" />
            </label>
            <p v-if="supportFormError" class="form-error wide">{{ supportFormError }}</p>
            <div class="wide form-actions">
              <button type="submit" class="primary-btn">ثبت پشتیبان</button>
            </div>
          </form>
        </article>

        <article class="glass-card table-card">
          <div class="card-head">
            <h3>تیم مرکزی</h3>
            <span>{{ hqTeam.length.toLocaleString('fa-IR') }} کاربر</span>
          </div>
          <div class="team-grid">
            <div v-for="member in hqTeam" :key="member.id" class="team-card">
              <div class="team-avatar">{{ initials(member.full_name || member.username) }}</div>
              <div class="team-card-body">
                <strong>{{ member.full_name || member.username }}</strong>
                <p>{{ member.platform_role === 'hq_admin' ? 'مدیرکل' : 'پشتیبان مرکزی' }}</p>
                <small>{{ member.phone }}</small>
                <small v-if="member.platform_role === 'hq_support'">{{ member.tenant_name || 'همه کارواش‌ها' }}</small>
                <div v-if="member.platform_role === 'hq_support'" class="team-rating">
                  <div class="team-stars" :title="`امتیاز ${formatSupportScore(member.support_star_rating)} از 5`">
                    <span class="team-stars-base">★★★★★</span>
                    <span class="team-stars-fill" :style="{ width: `${supportScorePercent(member.support_star_rating)}%` }">★★★★★</span>
                  </div>
                  <span class="team-rating-score">{{ formatSupportScore(member.support_star_rating) }}</span>
                </div>
                <div v-if="member.platform_role === 'hq_support'" class="team-metrics">
                  <small>رضایت: {{ formatSupportScore(member.support_customer_satisfaction_avg) }} / ۵</small>
                  <small>کیفیت پاسخ: {{ formatSupportScore(member.support_response_quality_avg) }} / ۵</small>
                  <small>پاسخ‌ اول: {{ formatResponseMinutes(member.support_first_response_minutes_avg) }}</small>
                  <small>تعداد رضایت: {{ toFa(member.support_rating_count || 0) }}</small>
                </div>
                <div v-if="member.platform_role === 'hq_support'" class="team-actions">
                  <button type="button" class="ghost-btn" @click="openEditSupportUser(member)">ویرایش</button>
                  <button type="button" class="danger-btn" @click="deleteSupportUser(member)">حذف</button>
                </div>
              </div>
            </div>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'reports'" class="glass-card report-shell hq-report-pro">
        <div class="report-command-hero">
          <div class="report-command-copy">
            <span class="report-eyebrow">HQ Financial Intelligence</span>
            <h2>گزارشات مرکزی کارنوواش</h2>
            <p>مرکز گزارشات HQ با تفکیک سهم کارنو، سهم آراکار، ریز واریزی‌های کیف پول و گزارش کامل هر کارواش داخل مجموعه.</p>
          </div>
          <div class="report-command-metrics">
            <article>
              <small>سهم کارنو</small>
              <strong>{{ money(reports.summary.hq_share_total || 0) }}</strong>
              <span>کیف پول پیامک و ورود مشتریان با اکسل</span>
            </article>
            <article>
              <small>سهم آراکار</small>
              <strong>{{ money(reports.summary.rah_share_total || 0) }}</strong>
              <span>عملیات، درآمد و هزینه‌های شعب</span>
            </article>
            <article>
              <small>درآمد نهایی</small>
              <strong>{{ money(hqFinalAmount()) }}</strong>
              <span>قبل از تخفیف: {{ money(hqBeforeDiscountAmount()) }}</span>
            </article>
          </div>
        </div>

        <div class="report-workspace-tabs" role="tablist" aria-label="تب‌های گزارشات HQ">
          <button type="button" :class="{ active: reportWorkspaceTab === 'internal' }" @click="reportWorkspaceTab = 'internal'">گزارش داخلی HQ</button>
          <button type="button" :class="{ active: reportWorkspaceTab === 'carwash' }" @click="reportWorkspaceTab = 'carwash'">گزارشات کارواش‌ها</button>
          <button type="button" :class="{ active: reportWorkspaceTab === 'wallet' }" @click="reportWorkspaceTab = 'wallet'">ریز کیف پول</button>
          <button type="button" :class="{ active: reportWorkspaceTab === 'network' }" @click="reportWorkspaceTab = 'network'">نمای شبکه</button>
        </div>

        <div class="report-control-deck">
          <div>
            <span class="report-control-label">بازه زمانی</span>
            <div class="report-range-chips">
              <button
                v-for="option in reportRangeOptions"
                :key="option.key"
                type="button"
                class="report-range-chip"
                :class="{ active: reportFilter.rangeKey === option.key }"
                @click="setReportRange(option.key)"
              >
                {{ option.label }}
              </button>
            </div>
          </div>
          <div class="report-filters compact">
            <BaseDatePicker v-model="reportFilter.start" placeholder="1405/01/01" />
            <BaseDatePicker v-model="reportFilter.end" placeholder="1405/01/30" />
          </div>
          <div class="report-period-card compact">
            <small>بازه انتخابی</small>
            <strong>{{ reportPeriodLabel }}</strong>
          </div>
        </div>

        <template v-if="reportWorkspaceTab === 'internal'">
          <div class="share-split-grid">
            <article class="share-card hq">
              <small>سهم کارنو</small>
              <strong>{{ money(reports.summary.hq_share_total || 0) }}</strong>
              <p>شارژ کیف پول پیامک و هزینه وارد کردن مشتریان با اکسل.</p>
            </article>
            <article class="share-card rah">
              <small>سهم آراکار</small>
              <strong>{{ money(reports.summary.rah_share_total || 0) }}</strong>
              <p>درآمد عملیاتی، پرداخت‌ها، هزینه‌ها، فروش خدمات و گزارش‌های اجرایی کارواش‌ها.</p>
            </article>
            <article class="share-card neutral">
              <small>مانده اقساط آپشن‌ها</small>
              <strong>{{ money(reports.summary.feature_remaining_total || 0) }}</strong>
              <p>مانده پرداخت نشده قابلیت‌های خریداری‌شده در کل مجموعه.</p>
            </article>
          </div>

          <div class="hq-share-tabs" role="tablist" aria-label="تب‌های سهم کارنو">
            <button
              v-for="tab in hqShareTabs"
              :key="tab.key"
              type="button"
              :class="{ active: hqShareTab === tab.key }"
              @click="hqShareTab = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>

          <div class="report-detail-grid">
            <article class="report-focus-card">
              <small>{{ hqShareTab === 'sms_wallet' ? 'کیف پول پیامک' : selectedHqFeature?.label || 'سهم کارنو' }}</small>
              <strong>{{ money(hqShareFeatureTotal) }}</strong>
              <p>{{ hqShareTab === 'sms_wallet' ? 'شارژهای ثبت‌شده روی کیف پول پیامک که سهم کارنو هستند.' : selectedHqFeature?.description || 'ریز پرداختی‌های این قابلیت در مجموعه.' }}</p>
            </article>
            <article class="report-focus-card">
              <small>تعداد ردیف</small>
              <strong>{{ toFa(selectedHqFeatureRows.length) }}</strong>
              <p>همه موارد مرتبط با تب انتخابی، بدون مخفی شدن در جدول‌های عمومی.</p>
            </article>
          </div>

          <div class="table-wrap report-table-wrap rich-table">
            <table>
              <thead>
                <tr v-if="hqShareTab === 'sms_wallet'">
                  <th>ردیف</th><th>کارواش</th><th>کیف پول</th><th>نوع</th><th>مبلغ</th><th>شرح</th><th>زمان</th><th>سهم</th>
                </tr>
                <tr v-else>
                  <th>ردیف</th><th>کارواش</th><th>قابلیت</th><th>پلن پرداخت</th><th>پرداخت شده</th><th>مانده</th><th>اقساط</th><th>سهم</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in selectedHqFeatureRows" :key="`${hqShareTab}-${row.id || row.tenant_id || index}`">
                  <template v-if="hqShareTab === 'sms_wallet'">
                    <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                    <td>{{ row.tenant_name }}</td>
                    <td>{{ row.wallet_name }}</td>
                    <td><span class="direction-pill" :class="row.direction">{{ walletDirectionLabel(row.direction) }}</span></td>
                    <td>{{ money(row.amount) }}</td>
                    <td>{{ row.description || row.reference_type || '-' }}</td>
                    <td>{{ dateTime(row.transacted_at) }}</td>
                    <td>{{ shareGroupLabel(row.share_group) }}</td>
                  </template>
                  <template v-else>
                    <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                    <td>{{ row.tenant_name }}</td>
                    <td>{{ row.feature?.label }}</td>
                    <td>{{ paymentPlanLabel(row.feature?.payment_plan) }}</td>
                    <td>{{ money(row.feature?.paid_amount) }}</td>
                    <td>{{ money(row.feature?.remaining_amount) }}</td>
                    <td>{{ row.feature?.installment_months ? `${toFa(row.feature.installment_months)} قسط` : '-' }}</td>
                    <td>{{ shareGroupLabel(row.feature?.share_group) }}</td>
                  </template>
                </tr>
                <tr v-if="!selectedHqFeatureRows.length">
                  <td colspan="8">برای این تب هنوز ردیفی در بازه انتخابی ثبت نشده است.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="table-wrap report-table-wrap rich-table">
            <div class="table-section-title">
              <h3>سهم آراکار، درآمد و هزینه‌های عملیاتی</h3>
              <span>{{ toFa(rahShareRows.length) }} کارواش</span>
            </div>
            <table>
              <thead><tr><th>رتبه</th><th>کارواش</th><th>درآمد وصولی</th><th>هزینه</th><th>خالص راه</th><th>مطالبات</th><th>خودرو</th><th>وضعیت</th></tr></thead>
              <tbody>
                <tr v-for="(row, index) in rahShareRows" :key="`rah-${row.tenant_id}`">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td><strong>{{ row.tenant_name }}</strong><small class="row-sub">{{ formatDate(row.last_activity_at) }}</small></td>
                  <td>{{ money(row.paid_amount) }}</td>
                  <td>{{ money(row.expense_total) }}</td>
                  <td>{{ money(row.rah_share_total) }}</td>
                  <td>{{ money(row.pending_amount) }}</td>
                  <td>{{ toFa(row.vehicles_count || 0) }}</td>
                  <td><span class="health-pill" :class="row.health">{{ healthLabel(row.health) }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else-if="reportWorkspaceTab === 'carwash'">
          <div class="tenant-report-layout">
            <aside class="tenant-report-list">
              <div class="table-toolbar">
                <input v-model.trim="carwashQuery" class="table-search" placeholder="جستجو در کارواش‌ها..." />
              </div>
              <button
                v-for="item in filteredCarwashes"
                :key="item.id"
                type="button"
                class="tenant-report-item"
                :class="{ active: String(item.id) === String(selectedReportTenantId) }"
                @click="selectedReportTenantId = String(item.id)"
              >
                <strong>{{ item.name }}</strong>
                <span>{{ item.manager?.full_name || 'بدون مدیر' }}</span>
              </button>
            </aside>

            <div class="tenant-report-main">
              <div class="tenant-report-head">
                <div>
                  <span class="report-eyebrow">گزارش کامل کارواش</span>
                  <h3>{{ selectedTenantReport.tenant?.name || 'یک کارواش را انتخاب کنید' }}</h3>
                </div>
                <button type="button" class="refresh-btn" :disabled="tenantReport.loading || !selectedReportTenantId" @click="loadTenantReports">به‌روزرسانی</button>
              </div>

              <div v-if="tenantReport.error" class="error-box" role="alert">{{ tenantReport.error }}</div>
              <div v-else-if="tenantReport.loading" class="empty-note">در حال دریافت گزارش کارواش انتخابی...</div>
              <template v-else>
                <div class="report-kpi-grid tenant-kpis finance-kpi-grid">
                  <article class="report-kpi-card spotlight"><small>مبلغ نهایی</small><strong>{{ money(tenantFinalAmount()) }}</strong><span>بعد از تخفیف، شامل انعام</span></article>
                  <article class="report-kpi-card"><small>قبل از تخفیف</small><strong>{{ money(tenantBeforeDiscountAmount()) }}</strong><span>مبلغ نهایی + جمع تخفیف</span></article>
                  <article class="report-kpi-card"><small>جمع تخفیف</small><strong>{{ money(tenantSummaryAmount('discount_total')) }}</strong><span>تخفیف مجموعه، امتیاز و دستی</span></article>
                  <article class="report-kpi-card"><small>حق کارواش</small><strong>{{ money(tenantSummaryAmount('carwash_total')) }}</strong><span>سهم شعبه بعد از تسویه سهم‌ها</span></article>
                  <article class="report-kpi-card"><small>حق نیرو</small><strong>{{ money(tenantSummaryAmount('worker_total')) }}</strong><span>سهم اجرای خدمات</span></article>
                  <article class="report-kpi-card"><small>انعام</small><strong>{{ money(tenantSummaryAmount('tips_total')) }}</strong><span>انعام ثبت‌شده روی سفارش‌ها</span></article>
                  <article class="report-kpi-card"><small>پرداختنی نیرو</small><strong>{{ money(tenantSummaryAmount('payable_worker_total')) }}</strong><span>مانده حقوق محاسبه‌شده</span></article>
                  <article class="report-kpi-card"><small>بیمه</small><strong>{{ money(tenantSummaryAmount('insurance_total')) }}</strong><span>مانده حق بیمه</span></article>
                  <article class="report-kpi-card"><small>تعداد خودرو</small><strong>{{ toFa(tenantSummaryAmount('vehicles_count')) }}</strong><span>کل مراجعات بازه</span></article>
                </div>

                <div class="hq-share-tabs compact" role="tablist" aria-label="تب‌های گزارش کارواش">
                  <button
                    v-for="tab in tenantReportTabs"
                    :key="tab.key"
                    type="button"
                    :class="{ active: tenantReportTab === tab.key }"
                    @click="tenantReportTab = tab.key"
                  >
                    {{ tab.label }}
                  </button>
                </div>

                <div class="table-wrap report-table-wrap rich-table">
                  <table>
                    <thead>
                      <tr>
                        <th v-for="column in tenantReportColumns" :key="column[0]">{{ column[1] }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, index) in tenantReportRows" :key="`${tenantReportTab}-${row.id || row.vehicle_id || index}`">
                        <td v-for="column in tenantReportColumns" :key="column[0]">{{ tenantCellValue(row, column) }}</td>
                      </tr>
                      <tr v-if="!tenantReportRows.length">
                        <td :colspan="tenantReportColumns.length || 1">در این تب برای بازه انتخابی رکوردی پیدا نشد.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
            </div>
          </div>
        </template>

        <template v-else-if="reportWorkspaceTab === 'wallet'">
          <div class="report-kpi-grid">
            <article class="report-kpi-card spotlight"><small>کل موجودی کیف پول</small><strong>{{ money(reports.summary.wallet_balance_total || 0) }}</strong></article>
            <article class="report-kpi-card"><small>کل واریزی‌ها</small><strong>{{ money(reports.summary.wallet_deposit_total || 0) }}</strong></article>
            <article class="report-kpi-card"><small>کل برداشت‌ها</small><strong>{{ money(reports.summary.wallet_withdraw_total || 0) }}</strong></article>
            <article class="report-kpi-card"><small>شارژ درگاه</small><strong>{{ money(reports.summary.wallet_gateway_charge_total || 0) }}</strong></article>
            <article class="report-kpi-card"><small>شارژ دستی</small><strong>{{ money(reports.summary.wallet_manual_charge_total || 0) }}</strong></article>
            <article class="report-kpi-card"><small>کیف پول پیامک</small><strong>{{ money(reports.summary.wallet_sms_balance_total || 0) }}</strong></article>
          </div>
          <div class="table-wrap report-table-wrap rich-table">
            <table>
              <thead><tr><th>ردیف</th><th>کارواش</th><th>کیف پول</th><th>نوع کیف پول</th><th>ورودی/خروجی</th><th>مبلغ</th><th>شرح</th><th>مرجع</th><th>ثبت‌کننده</th><th>زمان</th><th>سهم</th></tr></thead>
              <tbody>
                <tr v-for="(row, index) in walletLedgerRows" :key="row.id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ row.tenant_name }}</td>
                  <td>{{ row.wallet_name }}</td>
                  <td>{{ row.wallet_type === 'sms' ? 'پیامک' : 'عادی' }}</td>
                  <td><span class="direction-pill" :class="row.direction">{{ walletDirectionLabel(row.direction) }}</span></td>
                  <td>{{ money(row.amount) }}</td>
                  <td>{{ row.description || '-' }}</td>
                  <td>{{ row.reference_type || '-' }}</td>
                  <td>{{ row.created_by_name || '-' }}</td>
                  <td>{{ dateTime(row.transacted_at) }}</td>
                  <td>{{ shareGroupLabel(row.share_group) }}</td>
                </tr>
                <tr v-if="!walletLedgerRows.length"><td colspan="11">تراکنشی برای بازه انتخابی وجود ندارد.</td></tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else>
          <div class="report-tabs network-tabs">
            <button v-for="tab in reportTabs" :key="tab.key" type="button" class="report-tab-btn" :class="{ active: reportTab === tab.key }" @click="reportTab = tab.key">{{ tab.label }}</button>
          </div>
          <div class="report-kpi-grid report-money-kpis">
            <article v-if="reportTab === 'revenue'" class="report-kpi-card spotlight"><small>درآمد وصول‌شده</small><strong>{{ money(reports.summary.paid_amount || 0) }}</strong><span class="delta-badge" :class="deltaClass(reports.summary.revenue_change_percent)">{{ formatPercentChange(reports.summary.revenue_change_percent) }}</span></article>
            <article v-if="reportTab === 'revenue'" class="report-kpi-card"><small>قبل از تخفیف</small><strong>{{ money(hqBeforeDiscountAmount()) }}</strong><span>درآمد وصول‌شده + تخفیف</span></article>
            <article v-if="reportTab === 'revenue'" class="report-kpi-card"><small>جمع تخفیف</small><strong>{{ money(hqSummaryAmount('discount_total')) }}</strong><span>تخفیف ثبت‌شده پرداخت‌های موفق</span></article>
            <article v-if="reportTab === 'revenue'" class="report-kpi-card"><small>خالص شبکه</small><strong>{{ money(reports.summary.net_total || 0) }}</strong><span class="delta-badge" :class="deltaClass(reports.summary.net_change_percent)">{{ formatPercentChange(reports.summary.net_change_percent) }}</span></article>
            <article v-if="reportTab === 'revenue'" class="report-kpi-card"><small>تعداد خودرو</small><strong>{{ toFa(reports.summary.vehicles_count || 0) }}</strong></article>
            <article v-if="reportTab === 'wallet'" class="report-kpi-card spotlight"><small>موجودی کل کیف پول‌ها</small><strong>{{ money(reports.summary.wallet_balance_total || 0) }}</strong></article>
            <article v-if="reportTab === 'wallet'" class="report-kpi-card"><small>واریز کل</small><strong>{{ money(reports.summary.wallet_deposit_total || 0) }}</strong></article>
            <article v-if="reportTab === 'wallet'" class="report-kpi-card"><small>برداشت کل</small><strong>{{ money(reports.summary.wallet_withdraw_total || 0) }}</strong></article>
          </div>
          <div class="table-wrap report-table-wrap rich-table">
            <table v-if="reportTab === 'revenue'">
              <thead><tr><th>رتبه</th><th>کارواش</th><th>وضعیت</th><th>درآمد وصولی</th><th>قبل از تخفیف</th><th>تخفیف</th><th>خالص</th><th>میانگین فاکتور</th><th>مطالبات</th><th>پرداخت موفق</th></tr></thead>
              <tbody>
                <tr v-for="(row, index) in reportRows" :key="row.tenant_id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td><td><strong>{{ row.tenant_name }}</strong><small class="row-sub">{{ formatDate(row.last_activity_at) }}</small></td><td><span class="health-pill" :class="row.health">{{ healthLabel(row.health) }}</span></td><td>{{ money(row.paid_amount) }}</td><td>{{ money(rowBeforeDiscountAmount(row)) }}</td><td>{{ money(row.discount_total) }}</td><td>{{ money(row.net_amount) }}</td><td>{{ money(row.average_ticket) }}</td><td>{{ money(row.pending_amount) }}</td><td>{{ toFa(row.payments_count || 0) }}</td>
                </tr>
              </tbody>
            </table>
            <table v-else>
              <thead><tr><th>رتبه</th><th>کارواش</th><th>وضعیت شارژ</th><th>موجودی کل</th><th>موجودی عادی</th><th>موجودی پیامک</th><th>واریز</th><th>برداشت</th><th>شارژ درگاه</th><th>شارژ دستی</th></tr></thead>
              <tbody>
                <tr v-for="(row, index) in reportRows" :key="row.tenant_id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td><td><strong>{{ row.tenant_name }}</strong><small class="row-sub">{{ formatDate(row.last_activity_at) }}</small></td><td><span class="health-pill" :class="row.wallet_charge_health">{{ walletHealthLabel(row.wallet_charge_health) }}</span></td><td>{{ money(row.wallet_balance) }}</td><td>{{ money(row.wallet_regular_balance) }}</td><td>{{ money(row.wallet_sms_balance) }}</td><td>{{ money(row.wallet_deposit_total) }}</td><td>{{ money(row.wallet_withdraw_total) }}</td><td>{{ money(row.wallet_gateway_charge_total) }}</td><td>{{ money(row.wallet_manual_charge_total) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </section>

      <section v-else-if="false" class="glass-card report-shell">
        <div class="report-top-grid">
          <div class="report-hero">
            <div class="report-hero-copy">
              <span class="report-eyebrow">گزارش زنده همه کارواش‌ها</span>
              <h3>{{ reportTab === 'wallet' ? 'وضعیت کیف پول و شارژ پنل همه کارواش‌ها' : 'عملکرد واقعی شبکه بر اساس سفارش، پرداخت و خرید انبار' }}</h3>
              <p>{{ reportTab === 'wallet' ? 'در این نما برای هر کارواش مانده کیف پول، مجموع واریز، برداشت، شارژ درگاه و وضعیت شارژ پنل از روی دیتابیس واقعی نمایش داده می‌شود.' : 'این بخش از داده‌های واقعی دیتابیس همه شعبه‌ها ساخته می‌شود و وضعیت مالی، عملیاتی و بازدهی هر کارواش را در یک نمای واحد نشان می‌دهد.' }}</p>
            </div>
            <div class="report-glance-strip">
              <article class="glance-chip">
                <small>{{ reportTab === 'wallet' ? 'کارواش دارای تراکنش' : 'کارواش فعال' }}</small>
                <strong>{{ toFa(reports.summary.active_tenants_count || 0) }}</strong>
              </article>
              <article class="glance-chip">
                <small>{{ reportTab === 'wallet' ? 'کل تراکنش کیف پول' : 'کل پرداخت موفق' }}</small>
                <strong>{{ toFa(reportTab === 'wallet' ? reports.summary.wallet_transactions_count || 0 : reports.summary.payments_count || 0) }}</strong>
              </article>
              <article class="glance-chip">
                <small>{{ reportTab === 'wallet' ? 'بازه فعال' : 'نرخ وصول' }}</small>
                <strong>{{ reportTab === 'wallet' ? reportPeriodLabel : `${toFa(reports.summary.collection_rate || 0)}٪` }}</strong>
              </article>
            </div>
          </div>

          <aside class="report-control-rail">
            <div class="report-control-block">
              <span class="report-control-label">نوع گزارش</span>
              <div class="report-tabs">
                <button
                  v-for="tab in reportTabs"
                  :key="tab.key"
                  type="button"
                  class="report-tab-btn"
                  :class="{ active: reportTab === tab.key }"
                  @click="reportTab = tab.key"
                >
                  {{ tab.label }}
                </button>
              </div>
            </div>
            <div class="report-control-block">
              <span class="report-control-label">بازه زمانی</span>
              <div class="report-range-chips">
                <button
                  v-for="option in reportRangeOptions"
                  :key="option.key"
                  type="button"
                  class="report-range-chip"
                  :class="{ active: reportFilter.rangeKey === option.key }"
                  @click="setReportRange(option.key)"
                >
                  {{ option.label }}
                </button>
              </div>
            </div>
            <div class="report-filters">
              <BaseDatePicker v-model="reportFilter.start" placeholder="1405/01/01" />
              <BaseDatePicker v-model="reportFilter.end" placeholder="1405/01/30" />
            </div>
            <div class="report-period-card">
              <small>بازه انتخابی</small>
              <strong>{{ reportPeriodLabel }}</strong>
            </div>
          </aside>
        </div>

        <div class="report-body-grid">
          <div class="report-main-col">
            <div class="report-kpi-grid">
              <article v-if="reportTab === 'revenue'" class="report-kpi-card spotlight">
                <small>درآمد وصول‌شده</small>
                <strong>{{ money(reports.summary.paid_amount || 0) }}</strong>
                <span class="delta-badge" :class="deltaClass(reports.summary.revenue_change_percent)">
                  {{ formatPercentChange(reports.summary.revenue_change_percent) }}
                </span>
              </article>
              <article v-if="reportTab === 'revenue'" class="report-kpi-card">
                <small>خالص شبکه</small>
                <strong>{{ money(reports.summary.net_total || 0) }}</strong>
                <span class="delta-badge" :class="deltaClass(reports.summary.net_change_percent)">
                  {{ formatPercentChange(reports.summary.net_change_percent) }}
                </span>
              </article>
              <article v-if="reportTab === 'revenue'" class="report-kpi-card">
                <small>تعداد خودرو</small>
                <strong>{{ toFa(reports.summary.vehicles_count || 0) }}</strong>
                <span class="delta-badge" :class="deltaClass(reports.summary.vehicles_change_percent)">
                  {{ formatPercentChange(reports.summary.vehicles_change_percent) }}
                </span>
              </article>
              <article v-if="reportTab === 'revenue'" class="report-kpi-card">
                <small>هزینه خریدها</small>
                <strong>{{ money(reports.summary.expense_total || 0) }}</strong>
                <span>از انبار و خریدهای ثبت‌شده</span>
              </article>
              <article v-if="reportTab === 'revenue'" class="report-kpi-card">
                <small>میانگین فاکتور</small>
                <strong>{{ money(reports.summary.average_ticket || 0) }}</strong>
                <span>{{ toFa(reports.summary.payments_count || 0) }} پرداخت موفق</span>
              </article>
              <article v-if="reportTab === 'revenue'" class="report-kpi-card">
                <small>نرخ تکمیل</small>
                <strong>{{ toFa(reports.summary.completion_rate || 0) }}٪</strong>
                <span>{{ toFa(reports.summary.active_tenants_count || 0) }} کارواش فعال از {{ toFa(reports.summary.tenants_count || 0) }}</span>
              </article>

              <article v-if="reportTab === 'wallet'" class="report-kpi-card spotlight">
                <small>موجودی کل کیف پول‌ها</small>
                <strong>{{ money(reports.summary.wallet_balance_total || 0) }}</strong>
                <span>مانده واقعی همه کارواش‌ها</span>
              </article>
              <article v-if="reportTab === 'wallet'" class="report-kpi-card">
                <small>واریز کل</small>
                <strong>{{ money(reports.summary.wallet_deposit_total || 0) }}</strong>
                <span>{{ toFa(reports.summary.wallet_transactions_count || 0) }} تراکنش</span>
              </article>
              <article v-if="reportTab === 'wallet'" class="report-kpi-card">
                <small>برداشت کل</small>
                <strong>{{ money(reports.summary.wallet_withdraw_total || 0) }}</strong>
                <span>خروجی ثبت‌شده کیف پول</span>
              </article>
              <article v-if="reportTab === 'wallet'" class="report-kpi-card">
                <small>شارژ از درگاه</small>
                <strong>{{ money(reports.summary.wallet_gateway_charge_total || 0) }}</strong>
                <span>شارژ آنلاین پنل</span>
              </article>
              <article v-if="reportTab === 'wallet'" class="report-kpi-card">
                <small>شارژ دستی</small>
                <strong>{{ money(reports.summary.wallet_manual_charge_total || 0) }}</strong>
                <span>واریز داخلی/دستی</span>
              </article>
              <article v-if="reportTab === 'wallet'" class="report-kpi-card">
                <small>موجودی پیامک</small>
                <strong>{{ money(reports.summary.wallet_sms_balance_total || 0) }}</strong>
                <span>از کل {{ money(reports.summary.wallet_regular_balance_total || 0) }} موجودی عادی</span>
              </article>
            </div>

            <article class="report-trend-card report-trend-surface">
              <div class="card-head">
                <h3>روند {{ reportTabs.find((item) => item.key === reportTab)?.label }}</h3>
                <span>۱۲ بازه آخر</span>
              </div>
              <div class="trend-bars" v-if="reportTrendItems.length">
                <div v-for="item in reportTrendItems" :key="item.date" class="trend-bar-item">
                  <small>{{ formatDate(item.date) }}</small>
                  <div class="trend-bar-shell">
                    <div class="trend-bar-fill" :style="trendBarStyle(item)"></div>
                  </div>
                  <strong>{{ money(trendValue(item)) }}</strong>
                </div>
              </div>
              <div v-else class="empty-note">در این بازه داده‌ای برای روند وجود ندارد.</div>
            </article>

            <div class="table-wrap report-table-wrap">
              <table v-if="reportTab === 'revenue'">
                <thead>
                  <tr>
                    <th>رتبه</th>
                    <th>کارواش</th>
                    <th>وضعیت</th>
                    <th>درآمد وصولی</th>
                    <th>خالص</th>
                    <th>میانگین فاکتور</th>
                    <th>مطالبات</th>
                    <th>پرداخت موفق</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in reportRows" :key="row.tenant_id">
                    <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                    <td>
                      <strong>{{ row.tenant_name }}</strong>
                      <small class="row-sub">{{ formatDate(row.last_activity_at) }}</small>
                    </td>
                    <td><span class="health-pill" :class="row.health">{{ healthLabel(row.health) }}</span></td>
                    <td>{{ money(row.paid_amount) }}</td>
                    <td>{{ money(row.net_amount) }}</td>
                    <td>{{ money(row.average_ticket) }}</td>
                    <td>{{ money(row.pending_amount) }}</td>
                    <td>{{ toFa(row.payments_count || 0) }}</td>
                  </tr>
                </tbody>
              </table>
              <table v-else>
                <thead>
                  <tr>
                    <th>رتبه</th>
                    <th>کارواش</th>
                    <th>وضعیت شارژ</th>
                    <th>موجودی کل</th>
                    <th>موجودی عادی</th>
                    <th>موجودی پیامک</th>
                    <th>واریز</th>
                    <th>برداشت</th>
                    <th>شارژ درگاه</th>
                    <th>شارژ دستی</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in reportRows" :key="row.tenant_id">
                    <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                    <td>
                      <strong>{{ row.tenant_name }}</strong>
                      <small class="row-sub">{{ formatDate(row.last_activity_at) }}</small>
                    </td>
                    <td><span class="health-pill" :class="row.wallet_charge_health">{{ walletHealthLabel(row.wallet_charge_health) }}</span></td>
                    <td>{{ money(row.wallet_balance) }}</td>
                    <td>{{ money(row.wallet_regular_balance) }}</td>
                    <td>{{ money(row.wallet_sms_balance) }}</td>
                    <td>{{ money(row.wallet_deposit_total) }}</td>
                    <td>{{ money(row.wallet_withdraw_total) }}</td>
                    <td>{{ money(row.wallet_gateway_charge_total) }}</td>
                    <td>{{ money(row.wallet_manual_charge_total) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <aside class="report-side-col">
            <div class="report-insight-grid">
              <article v-if="reportTab === 'revenue' && highlightRow('top_revenue')" class="report-highlight-card success">
                <small>بیشترین درآمد</small>
                <strong>{{ highlightRow('top_revenue').tenant_name }}</strong>
                <p>{{ money(highlightRow('top_revenue').paid_amount) }}</p>
                <span>{{ toFa(highlightRow('top_revenue').vehicles_count || 0) }} خودرو</span>
              </article>
              <article v-if="reportTab === 'revenue' && highlightRow('top_volume')" class="report-highlight-card info">
                <small>بیشترین حجم کار</small>
                <strong>{{ highlightRow('top_volume').tenant_name }}</strong>
                <p>{{ toFa(highlightRow('top_volume').vehicles_count || 0) }} خودرو</p>
                <span>نرخ تکمیل {{ toFa(highlightRow('top_volume').completion_rate || 0) }}٪</span>
              </article>
              <article v-if="reportTab === 'revenue' && highlightRow('watchlist')" class="report-highlight-card warn">
                <small>نیازمند توجه</small>
                <strong>{{ highlightRow('watchlist').tenant_name }}</strong>
                <p>خالص {{ money(highlightRow('watchlist').net_amount) }}</p>
                <span>مطالبات {{ money(highlightRow('watchlist').pending_amount) }}</span>
              </article>

              <article v-if="reportTab === 'wallet' && highlightRow('top_wallet_balance')" class="report-highlight-card success">
                <small>بیشترین موجودی</small>
                <strong>{{ highlightRow('top_wallet_balance').tenant_name }}</strong>
                <p>{{ money(highlightRow('top_wallet_balance').wallet_balance) }}</p>
                <span>موجودی عادی {{ money(highlightRow('top_wallet_balance').wallet_regular_balance) }}</span>
              </article>
              <article v-if="reportTab === 'wallet' && highlightRow('top_wallet_deposit')" class="report-highlight-card info">
                <small>بیشترین شارژ</small>
                <strong>{{ highlightRow('top_wallet_deposit').tenant_name }}</strong>
                <p>{{ money(highlightRow('top_wallet_deposit').wallet_deposit_total) }}</p>
                <span>درگاه {{ money(highlightRow('top_wallet_deposit').wallet_gateway_charge_total) }}</span>
              </article>
              <article v-if="reportTab === 'wallet' && highlightRow('wallet_watchlist')" class="report-highlight-card warn">
                <small>نیازمند شارژ</small>
                <strong>{{ highlightRow('wallet_watchlist').tenant_name }}</strong>
                <p>موجودی {{ money(highlightRow('wallet_watchlist').wallet_balance) }}</p>
                <span>برداشت {{ money(highlightRow('wallet_watchlist').wallet_withdraw_total) }}</span>
              </article>
            </div>

            <article class="report-side-stats">
              <div v-if="reportTab === 'revenue'" class="mini-stat">
                <small>مطالبات باز</small>
                <strong>{{ money(reports.summary.pending_amount || 0) }}</strong>
              </div>
              <div v-if="reportTab === 'revenue'" class="mini-stat">
                <small>مبلغ خدمات</small>
                <strong>{{ money(reports.summary.services_total || 0) }}</strong>
              </div>
              <div v-if="reportTab === 'revenue'" class="mini-stat">
                <small>مبلغ محصولات</small>
                <strong>{{ money(reports.summary.products_total || 0) }}</strong>
              </div>
              <div v-if="reportTab === 'revenue'" class="mini-stat">
                <small>انعام ثبت‌شده</small>
                <strong>{{ money(reports.summary.tips_total || 0) }}</strong>
              </div>
              <div v-if="reportTab === 'revenue'" class="mini-stat">
                <small>تخفیف ثبت‌شده</small>
                <strong>{{ money(reports.summary.discount_total || 0) }}</strong>
              </div>
              <div v-if="reportTab === 'revenue'" class="mini-stat">
                <small>نرخ وصول</small>
                <strong>{{ toFa(reports.summary.collection_rate || 0) }}٪</strong>
              </div>

              <div v-if="reportTab === 'wallet'" class="mini-stat">
                <small>موجودی عادی</small>
                <strong>{{ money(reports.summary.wallet_regular_balance_total || 0) }}</strong>
              </div>
              <div v-if="reportTab === 'wallet'" class="mini-stat">
                <small>موجودی پیامک</small>
                <strong>{{ money(reports.summary.wallet_sms_balance_total || 0) }}</strong>
              </div>
              <div v-if="reportTab === 'wallet'" class="mini-stat">
                <small>شارژ از درگاه</small>
                <strong>{{ money(reports.summary.wallet_gateway_charge_total || 0) }}</strong>
              </div>
              <div v-if="reportTab === 'wallet'" class="mini-stat">
                <small>شارژ دستی</small>
                <strong>{{ money(reports.summary.wallet_manual_charge_total || 0) }}</strong>
              </div>
              <div v-if="reportTab === 'wallet'" class="mini-stat">
                <small>واریز کل</small>
                <strong>{{ money(reports.summary.wallet_deposit_total || 0) }}</strong>
              </div>
              <div v-if="reportTab === 'wallet'" class="mini-stat">
                <small>برداشت کل</small>
                <strong>{{ money(reports.summary.wallet_withdraw_total || 0) }}</strong>
              </div>
            </article>
          </aside>
        </div>
      </section>
    </main>

    <div v-if="editSupportModal.open" class="modal-overlay" @click.self="closeEditSupportModal">
      <div class="modal-card" dir="rtl">
        <div class="card-head">
          <h3>ویرایش پشتیبان</h3>
          <button type="button" class="ghost-btn" @click="closeEditSupportModal">بستن</button>
        </div>
        <form class="form-grid" @submit.prevent="updateSupportUser">
          <label>
            <span>نام</span>
            <input v-model.trim="editSupportModal.first_name" required />
          </label>
          <label>
            <span>نام خانوادگی</span>
            <input v-model.trim="editSupportModal.last_name" required />
          </label>
          <label>
            <span>نام کاربری</span>
            <input v-model.trim="editSupportModal.username" required />
          </label>
          <label>
            <span>موبایل</span>
            <input v-model.trim="editSupportModal.phone" required />
          </label>
          <div class="wide support-scope-note">
            <span>حوزه پوشش</span>
            <strong>همه کارواش‌ها</strong>
          </div>
          <label class="wide">
            <span>رمز عبور جدید</span>
            <input v-model="editSupportModal.password" type="password" minlength="6" placeholder="خالی بماند یعنی بدون تغییر" />
          </label>
          <label class="wide inline-toggle">
            <input v-model="editSupportModal.is_active" type="checkbox" />
            <span>پشتیبان فعال باشد</span>
          </label>
          <p v-if="editSupportModal.error" class="form-error wide">{{ editSupportModal.error }}</p>
          <div class="wide form-actions">
            <button type="submit" class="primary-btn">ذخیره تغییرات</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../services/api'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import { useAuthStore } from '../../store/auth.store'
import { formatJalaliDate } from '../../utils/date'
import { formatThousandsToman } from '../../utils/money'

const router = useRouter()
const authStore = useAuthStore()

const allTabs = [
  { key: 'overview', label: 'داشبورد مرکزی', meta: 'نمای کل' },
  { key: 'carwashes', label: 'کارواش‌ها', meta: 'ثبت و نظارت' },
  { key: 'tickets', label: 'مرکز تیکت', meta: 'پاسخ چت‌محور' },
  { key: 'team', label: 'تیم مرکزی', meta: 'ساخت پشتیبان' },
  { key: 'reports', label: 'گزارشات', meta: 'تحلیل تاریخی و مالی' }
]
const activeTab = ref(authStore.isHqAdmin ? 'overview' : 'tickets')
const isMobileSidebarOpen = ref(false)
let hqTicketPollingTimer = null
let hqTicketPollingInFlight = false
let knownTicketIds = new Set()
let knownTicketActivity = new Map()
let notificationAudioContext = null
let notificationAudioUnlocked = false
const visibleTabs = computed(() => {
  if (!authStore.isHqAdmin) return allTabs.filter((tab) => tab.key === 'tickets')
  return allTabs.filter((tab) => {
    if (tab.key === 'reports' || tab.key === 'team') return authStore.isHqAdmin
    return true
  })
})
const currentTabTitle = computed(() => visibleTabs.value.find((tab) => tab.key === activeTab.value)?.label || 'پنل مرکزی')

const selectTab = (tabKey) => {
  activeTab.value = tabKey
  isMobileSidebarOpen.value = false
}

const toggleMobileSidebar = () => {
  isMobileSidebarOpen.value = !isMobileSidebarOpen.value
}

const closeMobileSidebar = () => {
  isMobileSidebarOpen.value = false
}

const overview = reactive({ summary: {}, recent_carwashes: [], recent_tickets: [] })

const carwashes = ref([])
const carwashQuery = ref('')
const carwashInsight = reactive({
  loading: false,
  error: '',
  data: null
})
const createForm = reactive({
  carwash_name: '',
  carwash_address: '',
  manager_first_name: '',
  manager_last_name: '',
  manager_username: '',
  manager_phone: '',
  manager_password: ''
})

const tickets = ref([])
const selectedTicket = ref(null)
const ticketQuery = ref('')
const ticketStatus = ref('all')
const ticketPriority = ref('all')
const ticketTenantId = ref('')
const ticketScope = ref('all')
const ticketReply = reactive({
  body: '',
  status: '',
  assign_to_user_id: 0,
  is_internal: false
})
const walletTransfer = reactive({
  amountText: '',
  submitting: false,
  error: '',
  success: '',
  skipNextSuggestedAmount: false
})
const registrationApproval = reactive({
  submitting: false,
  error: '',
  message: ''
})

const reports = reactive({ summary: {}, rows: [], trends: [], highlights: {}, feature_summary: [], wallet_transactions: [] })
const reportWorkspaceTab = ref('internal')
const reportTab = ref('revenue')
const reportTabs = [
  { key: 'revenue', label: 'گزارش درآمد' },
  { key: 'wallet', label: 'گزارش کیف پول' }
]
const hqShareTab = ref('sms_wallet')
const hqShareTabs = [
  { key: 'sms_wallet', label: 'کیف پول پیامک' },
  { key: 'excel_import', label: 'وارد کردن مشتریان با اکسل' },
]
const selectedReportTenantId = ref('')
const tenantReportTab = ref('overall')
const tenantReportTabs = [
  { key: 'overall', label: 'گزارش کل' },
  { key: 'carwash', label: 'حق کارواش' },
  { key: 'worker', label: 'حق نیرو' },
  { key: 'tips', label: 'انعام' },
  { key: 'revenue', label: 'درآمد و پرداخت' },
  { key: 'attendance', label: 'ورود و خروج' },
  { key: 'blacklist', label: 'لیست سیاه' }
]
const reportRangeOptions = [
  { key: 'day', label: 'روز' },
  { key: 'week', label: 'هفته' },
  { key: 'month', label: 'ماه' },
  { key: 'all', label: 'کل بازه تاریخی' }
]
const reportFilter = reactive({ rangeKey: 'month', start: '', end: '' })
const tenantReport = reactive({ loading: false, error: '', data: null })

const hqTeam = ref([])
const supportFormError = ref('')
const supportForm = reactive({
  first_name: '',
  last_name: '',
  username: '',
  phone: '',
  password: '',
  tenant_id: 0
})
const editSupportModal = reactive({
  open: false,
  id: 0,
  first_name: '',
  last_name: '',
  username: '',
  phone: '',
  password: '',
  tenant_id: 0,
  is_active: true,
  error: ''
})

const filteredCarwashes = computed(() => {
  const query = carwashQuery.value.trim().toLowerCase()
  if (!query) return carwashes.value
  return carwashes.value.filter((item) => {
    const haystack = `${item.name} ${item.address || ''} ${item.manager?.full_name || ''} ${item.manager?.phone || ''}`.toLowerCase()
    return haystack.includes(query)
  })
})
const selectedCarwashInsight = computed(() => carwashInsight.data)

const teamAssignable = computed(() => hqTeam.value.filter((item) => ['hq_admin', 'hq_support'].includes(item.platform_role)))
const ticketScopeOptions = computed(() => (authStore.isHqAdmin
  ? [
    { key: 'all', label: 'همه تیکت‌ها' },
    { key: 'mine', label: 'ارجاع‌شده به من' },
    { key: 'unassigned', label: 'بدون مسئول' },
    { key: 'urgent', label: 'فوری و حساس' }
  ]
  : [
    { key: 'all', label: 'صف فعال' },
    { key: 'answered', label: 'پاسخ داده شده' },
    { key: 'urgent', label: 'فوری و حساس' }
  ]))
const ticketSummaryCards = computed(() => {
  const items = Array.isArray(tickets.value) ? tickets.value : []
  const counts = items.reduce((acc, item) => {
    acc.total += 1
    if (item.status === 'open') acc.open += 1
    if (item.status === 'pending') acc.pending += 1
    if (item.status === 'answered') acc.answered += 1
    if (item.status === 'closed') acc.closed += 1
    if (!item.assigned_to) acc.unassigned += 1
    if (Number(item.assigned_to || 0) === Number(authStore.user?.id || 0)) acc.mine += 1
    if (['urgent', 'high'].includes(item.priority)) acc.urgent += 1
    return acc
  }, { total: 0, open: 0, pending: 0, answered: 0, closed: 0, unassigned: 0, mine: 0, urgent: 0 })
  const activeCount = counts.open + counts.pending + counts.answered
  if (!authStore.isHqAdmin) {
    return [
      { key: 'open', label: 'جدید / باز', value: activeCount, tone: 'open' },
      { key: 'pending', label: 'در حال پیگیری', value: counts.pending, tone: 'pending' },
      { key: 'answered', label: 'پاسخ داده شده', value: counts.answered, tone: 'mine' },
      { key: 'urgent', label: 'فوری', value: counts.urgent, tone: 'urgent' }
    ]
  }
  return [
    { key: 'open', label: 'باز', value: activeCount, tone: 'open' },
    { key: 'pending', label: 'در انتظار', value: counts.pending, tone: 'pending' },
    { key: 'mine', label: 'ارجاع به من', value: counts.mine, tone: 'mine' },
    { key: 'urgent', label: 'فوری', value: counts.urgent, tone: 'urgent' }
  ]
})
const openTicketCount = computed(() => ticketSummaryCards.value.find((item) => item.key === 'open')?.value || 0)
const activeTicketScopeLabel = computed(() => {
  const match = ticketScopeOptions.value.find((item) => item.key === ticketScope.value)
  return match?.label || 'همه تیکت‌ها'
})
const visibleTickets = computed(() => {
  const items = Array.isArray(tickets.value) ? tickets.value : []
  return items.filter((item) => {
    if (!authStore.isHqAdmin && item.status === 'closed') return false
    if (!authStore.isHqAdmin && ticketScope.value === 'answered') return item.status === 'answered'
    if (ticketScope.value === 'mine') return Number(item.assigned_to || 0) === Number(authStore.user?.id || 0)
    if (ticketScope.value === 'urgent') return ['urgent', 'high'].includes(item.priority)
    if (ticketScope.value === 'unassigned') return !item.assigned_to
    return true
  })
})
const selectedTicketLastResponder = computed(() => {
  if (!selectedTicket.value?.messages?.length) return 'بدون پاسخ'
  const lastMessage = selectedTicket.value.messages[selectedTicket.value.messages.length - 1]
  return roleLabel(lastMessage)
})
const ticketResponseTemplates = [
  { id: 'need-info', title: 'درخواست اطلاعات بیشتر', body: 'برای بررسی دقیق‌تر، لطفا جزئیات تکمیلی، زمان رخداد و در صورت نیاز شماره سفارش یا تراکنش را ارسال کنید.' },
  { id: 'under-review', title: 'در حال بررسی', body: 'موضوع شما دریافت شد و در حال بررسی توسط تیم مربوطه است. نتیجه بررسی به‌محض جمع‌بندی از همین تیکت اعلام می‌شود.' },
  { id: 'resolved', title: 'جمع‌بندی و حل', body: 'بررسی انجام شد و مورد از سمت ما رفع شده است. لطفا یک‌بار مجدد بررسی کنید و اگر هنوز مشکل باقی بود همین تیکت را ادامه دهید.' }
]
const ticketSlaRules = {
  low: { firstResponseMinutes: 24 * 60 },
  medium: { firstResponseMinutes: 12 * 60 },
  high: { firstResponseMinutes: 4 * 60 },
  urgent: { firstResponseMinutes: 30 }
}
const ticketDeadlineAt = (ticket) => {
  if (!ticket?.created_at) return null
  const minutes = ticketSlaRules[ticket.priority]?.firstResponseMinutes || ticketSlaRules.medium.firstResponseMinutes
  return new Date(new Date(ticket.created_at).getTime() + minutes * 60 * 1000)
}
const ticketSlaMeta = (ticket) => {
  if (!ticket?.created_at) return { state: 'neutral', label: 'بدون داده', description: 'زمان‌بندی این تیکت قابل محاسبه نیست.' }
  if (ticket.first_response_at) {
    return {
      state: 'resolved',
      label: 'پاسخ ثبت شده',
      description: `پاسخ اول در ${dateTime(ticket.first_response_at)} ثبت شده است.`
    }
  }
  const deadline = ticketDeadlineAt(ticket)
  const remainingMs = deadline ? deadline.getTime() - Date.now() : 0
  if (remainingMs <= 0) {
    return {
      state: 'breached',
      label: 'نقض شده',
      description: 'زمان پاسخ اولیه از SLA عبور کرده است.'
    }
  }
  const remainingMinutes = Math.ceil(remainingMs / 60000)
  if (remainingMinutes <= 60) {
    return {
      state: 'risk',
      label: `${toFa(remainingMinutes)} دقیقه مانده`,
      description: 'زمان پاسخ اولیه نزدیک به پایان است.'
    }
  }
  const remainingHours = Math.ceil(remainingMinutes / 60)
  return {
    state: 'safe',
    label: `${toFa(remainingHours)} ساعت مانده`,
    description: 'این تیکت هنوز داخل بازه مجاز پاسخ اولیه است.'
  }
}
const selectedTicketSla = computed(() => ticketSlaMeta(selectedTicket.value))
const selectedTicketInternalNotesCount = computed(() => {
  const items = selectedTicket.value?.messages || []
  return items.filter((item) => item.is_internal).length
})
const canApproveRegistration = computed(() => (
  Boolean(selectedTicket.value?.is_registration_request)
  && selectedTicket.value?.registration_status === 'pending'
))
const selectedTicketActivityFeed = computed(() => {
  const ticket = selectedTicket.value
  if (!ticket) return []
  const events = [
    {
      id: `created-${ticket.id}`,
      created_at: ticket.created_at,
      tone: 'primary',
      title: 'تیکت ایجاد شد',
      description: `پرونده با عنوان «${ticket.subject}» برای ${ticket.tenant_name} ثبت شد.`
    }
  ]
  if (ticket.assigned_to_name && ticket.assigned_to_name !== '-') {
    events.push({
      id: `assigned-${ticket.id}`,
      created_at: ticket.updated_at,
      tone: 'info',
      title: 'ارجاع فعال',
      description: `مسئول فعلی رسیدگی: ${ticket.assigned_to_name}`
    })
  }
  ;(ticket.messages || []).forEach((message) => {
    events.push({
      id: `message-${message.id}`,
      created_at: message.created_at,
      tone: message.is_internal ? 'muted' : message.sender_platform_role ? 'success' : 'neutral',
      title: message.is_internal ? 'یادداشت داخلی' : roleLabel(message),
      description: String(message.body || '').slice(0, 120)
    })
  })
  if (ticket.closed_at) {
    events.push({
      id: `closed-${ticket.id}`,
      created_at: ticket.closed_at,
      tone: 'muted',
      title: 'تیکت بسته شد',
      description: 'پرونده از سمت تیم پشتیبانی بسته شده است.'
    })
  }
  return events.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
})
const priorityQueue = computed(() => {
  const items = [...visibleTickets.value]
  return items
    .sort((a, b) => {
      const aUrgent = ['urgent', 'high'].includes(a.priority) ? 1 : 0
      const bUrgent = ['urgent', 'high'].includes(b.priority) ? 1 : 0
      if (bUrgent !== aUrgent) return bUrgent - aUrgent
      const aDeadline = ticketDeadlineAt(a)?.getTime() || Number.MAX_SAFE_INTEGER
      const bDeadline = ticketDeadlineAt(b)?.getTime() || Number.MAX_SAFE_INTEGER
      return aDeadline - bDeadline
    })
})
const ticketSlaSummary = computed(() => {
  const items = Array.isArray(tickets.value) ? tickets.value : []
  const openItems = items.filter((item) => item.status !== 'closed')
  const breached = openItems.filter((item) => ticketSlaMeta(item).state === 'breached').length
  const compliant = Math.max(openItems.length - breached, 0)
  const compliance = openItems.length ? Math.round((compliant / openItems.length) * 100) : 100
  const responded = items.filter((item) => item.first_response_at)
  const avgMinutes = responded.length
    ? Math.round(responded.reduce((sum, item) => {
      const minutes = Math.max((new Date(item.first_response_at).getTime() - new Date(item.created_at).getTime()) / 60000, 0)
      return sum + minutes
    }, 0) / responded.length)
    : 0
  return {
    compliance,
    breached,
    unassigned: items.filter((item) => !item.assigned_to).length,
    firstResponseLabel: avgMinutes ? `${toFa(avgMinutes)} دقیقه` : 'بدون داده'
  }
})
const ticketTrendBars = computed(() => {
  const days = Array.from({ length: 6 }).map((_, index) => {
    const date = new Date()
    date.setDate(date.getDate() - (5 - index))
    const label = new Intl.DateTimeFormat('fa-IR', { month: 'numeric', day: 'numeric' }).format(date)
    return { key: date.toISOString().slice(0, 10), label, count: 0 }
  })
  const map = new Map(days.map((item) => [item.key, item]))
  ;(tickets.value || []).forEach((ticket) => {
    const key = String(ticket.created_at || '').slice(0, 10)
    if (map.has(key)) map.get(key).count += 1
  })
  const max = Math.max(...days.map((item) => item.count), 1)
  return days.map((item) => ({ ...item, height: Math.max(18, Math.round((item.count / max) * 100)) }))
})
const reportRows = computed(() => {
  const items = Array.isArray(reports.rows) ? [...reports.rows] : []
  if (reportTab.value === 'wallet') {
    return items.sort((a, b) => Number(b.wallet_balance || 0) - Number(a.wallet_balance || 0))
  }
  return items.sort((a, b) => Number(b.paid_amount || 0) - Number(a.paid_amount || 0))
})
const hqFeatureSummary = computed(() => (Array.isArray(reports.feature_summary) ? reports.feature_summary : []))
const selectedHqFeature = computed(() => hqFeatureSummary.value.find((item) => item.key === hqShareTab.value) || null)
const selectedHqFeatureRows = computed(() => {
  if (hqShareTab.value === 'sms_wallet') {
    return (Array.isArray(reports.wallet_transactions) ? reports.wallet_transactions : [])
      .filter((item) => item.wallet_type === 'sms' && item.share_group === 'hq')
  }
  if (hqShareTab.value === 'excel_import') {
    const featureRows = reportRows.value
      .map((row) => ({
        ...row,
        feature: (Array.isArray(row.feature_breakdown) ? row.feature_breakdown : [])
          .find((item) => item.feature_key === hqShareTab.value)
      }))
      .filter((row) => row.feature)
    const transactionRows = (Array.isArray(reports.wallet_transactions) ? reports.wallet_transactions : [])
      .filter((item) => item.reference_type === 'customer_import_excel' && item.share_group === 'hq')
      .map((item) => ({
        ...item,
        feature: {
          label: 'وارد کردن مشتریان با اکسل',
          payment_plan: 'wallet',
          paid_amount: item.share_amount || item.amount || 0,
          remaining_amount: 0,
          installment_months: 0,
          share_group: item.share_group
        }
      }))
    return [...featureRows, ...transactionRows]
  }
  return reportRows.value
    .map((row) => ({
      ...row,
      feature: (Array.isArray(row.feature_breakdown) ? row.feature_breakdown : [])
        .find((item) => item.feature_key === hqShareTab.value)
    }))
    .filter((row) => row.feature)
})
const hqShareFeatureTotal = computed(() => selectedHqFeatureRows.value.reduce((sum, item) => {
  if (hqShareTab.value === 'sms_wallet') return sum + Number(item.share_amount || item.amount || 0)
  return sum + Number(item.feature?.paid_amount || 0)
}, 0))
const rahShareRows = computed(() => reportRows.value.filter((row) => Number(row.rah_share_total || 0) || Number(row.net_amount || 0)))
const walletLedgerRows = computed(() => (Array.isArray(reports.wallet_transactions) ? [...reports.wallet_transactions] : [])
  .sort((a, b) => new Date(b.transacted_at || 0) - new Date(a.transacted_at || 0)))
const selectedTenantReport = computed(() => tenantReport.data || {})
const selectedTenantReportSummary = computed(() => selectedTenantReport.value.summary || {})
const tenantReportRows = computed(() => {
  const data = selectedTenantReport.value
  const map = {
    overall: data.overall_report,
    carwash: data.carwash_report,
    worker: data.worker_report,
    tips: data.tips_report,
    revenue: data.revenue_report,
    attendance: data.attendance_report,
    blacklist: data.blacklist_report
  }
  return Array.isArray(map[tenantReportTab.value]) ? map[tenantReportTab.value] : []
})
const tenantReportColumns = computed(() => ({
  overall: [
    ['row', 'ردیف'], ['driver_name', 'راننده'], ['driver_phone', 'شماره'], ['plate_number', 'پلاک'], ['status', 'وضعیت'], ['final_total', 'مبلغ نهایی', 'money'], ['before_discount_total', 'قبل از تخفیف', 'money'], ['carwash_share', 'حق کارواش', 'money'], ['worker_share', 'حق نیرو', 'money'], ['discount_total', 'جمع تخفیف', 'money'], ['tip_amount', 'انعام', 'money'], ['worker_name', 'نیرو'], ['services', 'خدمات'], ['created_at', 'تاریخ', 'date']
  ],
  carwash: [
    ['row', 'ردیف'], ['driver_name', 'راننده'], ['plate_number', 'پلاک'], ['carwash_share', 'حق کارواش', 'money'], ['worker_name', 'نیرو'], ['created_at', 'تاریخ', 'date']
  ],
  worker: [
    ['row', 'ردیف'], ['driver_name', 'راننده'], ['plate_number', 'پلاک'], ['worker_share', 'حق نیرو', 'money'], ['worker_name', 'نیرو'], ['created_at', 'تاریخ', 'date']
  ],
  tips: [
    ['row', 'ردیف'], ['driver_name', 'راننده'], ['plate_number', 'پلاک'], ['tip_amount', 'انعام', 'money'], ['worker_name', 'نیرو'], ['products', 'کالا'], ['created_at', 'تاریخ', 'date']
  ],
  revenue: [
    ['row', 'ردیف'], ['created_at', 'تاریخ', 'date'], ['driver_name', 'راننده'], ['payment_method', 'روش پرداخت'], ['payment_status', 'وضعیت'], ['service_amount', 'خدمات', 'money'], ['product_amount', 'محصولات', 'money'], ['final_total', 'مبلغ نهایی', 'money'], ['received_amount', 'وصول شده', 'money'], ['outstanding_amount', 'مانده', 'money']
  ],
  attendance: [
    ['row', 'ردیف'], ['worker_name', 'پرسنل'], ['event_type', 'رویداد'], ['source', 'منبع'], ['event_at', 'زمان', 'date']
  ],
  blacklist: [
    ['row', 'ردیف'], ['plate_number', 'پلاک'], ['plate_type', 'نوع وسیله'], ['note', 'توضیح'], ['blocked_by_name', 'ثبت کننده'], ['created_at', 'تاریخ', 'date']
  ]
}[tenantReportTab.value] || []))
const reportHighlights = computed(() => reports.highlights || {})
const reportTrendMetricKey = computed(() => {
  if (reportTab.value === 'wallet') return 'wallet_deposit_total'
  return 'paid_amount'
})
const reportTrendItems = computed(() => (Array.isArray(reports.trends) ? reports.trends.slice(-12) : []))
const reportTrendMax = computed(() => {
  const values = reportTrendItems.value.map((item) => Number(item?.[reportTrendMetricKey.value] || 0))
  return Math.max(...values, 1)
})
const reportPeriodLabel = computed(() => {
  if (reportFilter.start && reportFilter.end) return `${reportFilter.start} تا ${reportFilter.end}`
  if (reportFilter.start) return `از ${reportFilter.start}`
  if (reportFilter.end) return `تا ${reportFilter.end}`
  return 'کل بازه تاریخی'
})

const money = (value) => formatThousandsToman(value)
const toFa = (value) => Number(value || 0).toLocaleString('fa-IR')
const roundedMoneySum = (...values) => values.reduce((sum, value) => sum + Math.round(Number(value || 0)), 0)
const hqSummaryAmount = (key) => Number(reports.summary?.[key] || 0)
const hqFinalAmount = () => hqSummaryAmount('final_total') || hqSummaryAmount('paid_amount')
const hqBeforeDiscountAmount = () => roundedMoneySum(hqFinalAmount(), hqSummaryAmount('discount_total'))
const tenantSummaryAmount = (key) => Number(selectedTenantReportSummary.value?.[key] || 0)
const tenantFinalAmount = () => {
  const explicitTotal = tenantSummaryAmount('final_total')
  if (explicitTotal > 0) return explicitTotal
  return tenantSummaryAmount('carwash_total') + tenantSummaryAmount('worker_total') + tenantSummaryAmount('tips_total')
}
const tenantBeforeDiscountAmount = () => roundedMoneySum(tenantFinalAmount(), tenantSummaryAmount('discount_total'))
const rowBeforeDiscountAmount = (row) => {
  return roundedMoneySum(row?.paid_amount || row?.final_total || 0, row?.discount_total || 0)
}
const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'.indexOf(digit))
  .replace(/[٠-٩]/g, (digit) => '٠١٢٣٤٥٦٧٨٩'.indexOf(digit))
const parseTransferAmount = (value) => Number(normalizeDigits(value).replace(/[,\s٬،]/g, ''))
const extractWalletTransferAmount = (ticket) => {
  const messageText = [
    ticket?.message || '',
    ...(Array.isArray(ticket?.messages) ? ticket.messages.map((item) => item?.body || '') : [])
  ].join('\n')
  const normalized = normalizeDigits(messageText)
  const withdrawMatch = normalized.match(/withdraw_amount\s*[:：]?\s*([\d,.\s]+)/i)
  if (withdrawMatch) {
    const withdrawAmount = parseTransferAmount(withdrawMatch[1])
    if (withdrawAmount > 0) return withdrawAmount
  }
  const patterns = [
    /مبلغ\s*پرداخت\s*[:：]?\s*([\d,\s٬،]+)/i,
    /مبلغ\s*واریز\s*[:：]?\s*([\d,\s٬،]+)/i,
    /مبلغ\s*شارژ\s*[:：]?\s*([\d,\s٬،]+)/i,
    /amount\s*[:：]?\s*([\d,\s٬،]+)/i
  ]
  for (const pattern of patterns) {
    const match = normalized.match(pattern)
    const amount = match ? parseTransferAmount(match[1]) : 0
    if (amount > 0) return amount
  }
  return 0
}
const isWalletCardPaymentTicket = (ticket) => {
  const text = `${ticket?.subject || ''}\n${ticket?.message || ''}`.toLowerCase()
  return text.includes('wallet-card-payment') || (text.includes('کارت به کارت') && text.includes('کیف پول'))
}
const isWalletBankWithdrawalTicket = (ticket) => {
  const text = `${ticket?.subject || ''}\n${ticket?.message || ''}`.toLowerCase()
  return text.includes('wallet-bank-withdrawal')
}
const isWalletOperationTicket = (ticket) => isWalletCardPaymentTicket(ticket) || isWalletBankWithdrawalTicket(ticket)
const walletOperationButtonLabel = computed(() => isWalletBankWithdrawalTicket(selectedTicket.value) ? 'برداشت' : 'انتقال پول')
const walletOperationSubmittingLabel = computed(() => isWalletBankWithdrawalTicket(selectedTicket.value) ? 'در حال برداشت...' : 'در حال انتقال...')
const initials = (value) => {
  const parts = String(value || '').trim().split(' ').filter(Boolean)
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`
  return String(value || '--').slice(0, 2)
}
const formatSupportScore = (value) => Number(value || 0).toLocaleString('fa-IR', { minimumFractionDigits: 1, maximumFractionDigits: 2 })
const supportScorePercent = (value) => Math.max(0, Math.min(100, (Number(value || 0) / 5) * 100))
const formatResponseMinutes = (value) => {
  const minutes = Number(value || 0)
  if (!minutes) return 'بدون داده'
  if (minutes < 60) return `${toFa(minutes.toFixed(0))} دقیقه`
  const hours = minutes / 60
  return `${Number(hours).toLocaleString('fa-IR', { maximumFractionDigits: 1 })} ساعت`
}
const formatPercentChange = (value) => {
  if (value === null || value === undefined) return 'بدون مبنا'
  const numeric = Number(value || 0)
  const sign = numeric > 0 ? '+' : ''
  return `${sign}${numeric.toLocaleString('fa-IR', { maximumFractionDigits: 1 })}٪`
}
const deltaClass = (value) => {
  if (value === null || value === undefined || Number(value || 0) === 0) return 'neutral'
  return Number(value) > 0 ? 'up' : 'down'
}
const healthLabel = (value) => ({
  strong: 'عالی',
  stable: 'باثبات',
  risk: 'نیازمند توجه',
  idle: 'بدون فعالیت'
}[value] || 'باثبات')
const walletHealthLabel = (value) => ({
  healthy: 'سالم',
  gateway: 'شارژ درگاه',
  sms_heavy: 'تمرکز پیامک',
  empty: 'خالی',
  idle: 'بدون تراکنش'
}[value] || 'سالم')
const shareGroupLabel = (value) => ({
  hq: 'سهم کارنو',
  rah: 'سهم آراکار'
}[value] || 'سهم آراکار')
const walletDirectionLabel = (value) => ({
  in: 'واریز',
  out: 'برداشت'
}[value] || 'تراکنش')
const paymentMethodLabel = (value) => ({
  pos: 'کارتخوان',
  cash: 'نقدی',
  transfer: 'انتقال',
  cheque: 'چک',
  credit: 'اعتباری',
  manual: 'دستی'
}[value] || value || '-')
const paymentStatusLabel = (value) => ({
  pending: 'در انتظار',
  success: 'موفق',
  failed: 'ناموفق',
  refunded: 'مرجوع'
}[value] || value || '-')
const attendanceEventLabel = (value) => ({
  in: 'ورود',
  out: 'خروج'
}[value] || value || '-')
const plateTypeLabel = (value) => ({
  car: 'خودرو',
  motorcycle: 'موتور سیکلت'
}[value] || value || '-')
const tenantCellValue = (row, column) => {
  const [key, _label, type] = column
  if (key === 'before_discount_total') {
    return money(roundedMoneySum(row?.final_total || 0, row?.discount_total || 0))
  }
  const value = row?.[key]
  if (type === 'money') return money(value || 0)
  if (type === 'date') return dateTime(value)
  if (key === 'payment_method') return paymentMethodLabel(value)
  if (key === 'payment_status') return paymentStatusLabel(value)
  if (key === 'event_type') return attendanceEventLabel(value)
  if (key === 'plate_type') return plateTypeLabel(value)
  if (key === 'status') return statusLabel(value)
  return value || '-'
}
const paymentPlanLabel = (value) => ({
  cash: 'نقدی',
  installment: 'قسطی',
  manual: 'دستی',
  wallet: 'کیف پول'
}[value] || 'نامشخص')
const trendValue = (item) => Number(item?.[reportTrendMetricKey.value] || 0)
const trendBarStyle = (item) => {
  const ratio = trendValue(item) / reportTrendMax.value
  return { height: `${Math.max(18, Math.round(ratio * 120))}px` }
}
const highlightRow = (key) => reportHighlights.value?.[key] || null
const toJalaliDate = (date) => {
  const parts = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).formatToParts(date)
  const year = parts.find((item) => item.type === 'year')?.value || '1405'
  const month = parts.find((item) => item.type === 'month')?.value || '01'
  const day = parts.find((item) => item.type === 'day')?.value || '01'
  return `${year}/${month}/${day}`
}
const statusLabel = (value) => ({
  open: 'باز',
  pending: 'در انتظار پیگیری',
  answered: 'پاسخ داده شده',
  closed: 'بسته شده'
}[value] || 'باز')
const priorityLabel = (value) => ({
  low: 'کم',
  medium: 'متوسط',
  high: 'بالا',
  urgent: 'فوری'
}[value] || 'متوسط')
const categoryLabel = (value) => ({
  technical: 'فنی',
  financial: 'مالی',
  operations: 'عملیاتی',
  account: 'حساب',
  other: 'سایر'
}[value] || 'سایر')
const ticketSummaryHint = (key) => ({
  open: 'تیکت‌های تازه یا دوباره بازشده',
  pending: 'در حال پیگیری توسط پشتیبانی',
  answered: 'منتظر واکنش کاربر',
  mine: 'در صف پاسخ شما',
  urgent: 'پرونده‌های حساس و فوری'
}[key] || '')
const ticketSlaShortLabel = (ticket) => {
  const meta = ticketSlaMeta(ticket)
  return meta.label
}
const applyTicketTemplate = (body) => {
  const tenantName = selectedTicket.value?.tenant_name || 'کارواش'
  ticketReply.body = String(body || '').replaceAll('{{tenant_name}}', tenantName)
}
const unlockNotificationAudio = () => {
  if (notificationAudioUnlocked || typeof window === 'undefined') return
  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  if (!AudioContextClass) return
  notificationAudioContext = notificationAudioContext || new AudioContextClass()
  notificationAudioContext.resume?.()
  notificationAudioUnlocked = true
}

const playTicketDing = () => {
  if (typeof window === 'undefined') return
  try {
    unlockNotificationAudio()
    const context = notificationAudioContext
    if (!context) return
    const startedAt = context.currentTime
    const gain = context.createGain()
    gain.gain.setValueAtTime(0.0001, startedAt)
    gain.gain.exponentialRampToValueAtTime(0.16, startedAt + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, startedAt + 0.36)
    gain.connect(context.destination)

    const firstTone = context.createOscillator()
    firstTone.type = 'sine'
    firstTone.frequency.setValueAtTime(880, startedAt)
    firstTone.connect(gain)
    firstTone.start(startedAt)
    firstTone.stop(startedAt + 0.16)

    const secondTone = context.createOscillator()
    secondTone.type = 'sine'
    secondTone.frequency.setValueAtTime(1175, startedAt + 0.12)
    secondTone.connect(gain)
    secondTone.start(startedAt + 0.12)
    secondTone.stop(startedAt + 0.34)
  } catch (_error) {
    // Browser autoplay policies can block sound until the first user interaction.
  }
}

const roleLabel = (message) => {
  if (message.sender_platform_role === 'hq_admin') return 'مدیرکل'
  if (message.sender_platform_role === 'hq_support') return 'پشتیبان مرکزی'
  return message.sender_role || 'کاربر'
}
const formatDate = (value) => formatJalaliDate(value)
const dateTime = (value) => formatJalaliDate(value)
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
const resolveReportRange = (rangeKey) => {
  if (rangeKey === 'all') return { start: '', end: '' }
  const now = new Date()
  const start = new Date(now)
  if (rangeKey === 'day') return { start: toJalaliDate(start), end: toJalaliDate(now) }
  if (rangeKey === 'week') {
    const day = now.getDay()
    const offset = day === 0 ? 6 : day - 1
    start.setDate(now.getDate() - offset)
    return { start: toJalaliDate(start), end: toJalaliDate(now) }
  }
  start.setDate(1)
  return { start: toJalaliDate(start), end: toJalaliDate(now) }
}
const setReportRange = (rangeKey) => {
  reportFilter.rangeKey = rangeKey
  const range = resolveReportRange(rangeKey)
  reportFilter.start = range.start
  reportFilter.end = range.end
}

const loadOverview = async (options = {}) => {
  const { data } = await api.get('/auth/hq/overview/', {
    meta: options.silent ? { trackLoading: false, showErrorToast: false } : undefined
  })
  overview.summary = data?.summary || {}
  overview.recent_carwashes = data?.recent_carwashes || []
  overview.recent_tickets = data?.recent_tickets || []
}

const loadCarwashes = async () => {
  const { data } = await api.get('/auth/hq/carwashes/')
  carwashes.value = Array.isArray(data) ? data : []
}

const loadCarwashInsight = async (tenantId) => {
  const id = Number(tenantId || 0)
  if (!id || carwashInsight.loading) return
  carwashInsight.loading = true
  carwashInsight.error = ''
  try {
    const { data } = await api.get(`/auth/hq/carwashes/${id}/insights/`)
    carwashInsight.data = data
  } catch (error) {
    carwashInsight.error = error?.response?.data?.detail || 'دریافت اطلاعات نظارتی کارواش ناموفق بود.'
  } finally {
    carwashInsight.loading = false
  }
}

const createCarwash = async () => {
  await api.post('/auth/hq/carwashes/', createForm)
  Object.assign(createForm, {
    carwash_name: '',
    carwash_address: '',
    manager_first_name: '',
    manager_last_name: '',
    manager_username: '',
    manager_phone: '',
    manager_password: ''
  })
  await loadCarwashes()
  if (carwashes.value[0]?.id) await loadCarwashInsight(carwashes.value[0].id)
  await loadOverview()
}

const toggleCarwashState = async (row) => {
  await api.patch(`/auth/hq/carwashes/${row.id}/`, { is_active: !row.is_active })
  await loadCarwashes()
  if (selectedCarwashInsight.value?.tenant?.id === row.id) await loadCarwashInsight(row.id)
  await loadOverview()
}

const ticketActivitySignature = (ticket) => [
  ticket?.last_message_at || '',
  ticket?.messages_count || 0,
  ticket?.status || ''
].join('|')

const loadTickets = async (options = {}) => {
  if (authStore.isHqAdmin && !carwashes.value.length && !options.silent) await loadCarwashes()
  const { data } = await api.get('/auth/hq/tickets/', {
    params: {
      q: ticketQuery.value || undefined,
      status: ticketStatus.value,
      priority: ticketPriority.value,
      tenant_id: authStore.isHqAdmin ? (ticketTenantId.value || undefined) : undefined
    },
    meta: options.silent ? { trackLoading: false, showErrorToast: false } : undefined
  })
  const nextTickets = Array.isArray(data) ? data : []
  if (knownTicketIds.size && options.notifyNew) {
    const hasUserActivity = nextTickets.some((item) => {
      if (item.status === 'closed') return false
      const id = Number(item.id)
      if (!knownTicketIds.has(id)) return true
      return knownTicketActivity.get(id) !== ticketActivitySignature(item)
    })
    if (hasUserActivity) playTicketDing()
  }
  knownTicketIds = new Set(nextTickets.map((item) => Number(item.id)))
  knownTicketActivity = new Map(nextTickets.map((item) => [Number(item.id), ticketActivitySignature(item)]))
  tickets.value = nextTickets
  if (!options.skipSelection) await ensureSelectedTicket(options)
}

const ensureSelectedTicket = async (options = {}) => {
  if (!visibleTickets.value.length) {
    if (!options.keepReply) selectedTicket.value = null
    return
  }
  if (selectedTicket.value?.id && visibleTickets.value.some((item) => item.id === selectedTicket.value.id)) {
    const stillExists = tickets.value.some((item) => item.id === selectedTicket.value.id)
    if (stillExists) {
      await selectTicket(selectedTicket.value.id, {
        keepReply: Boolean(options.keepReply),
        silent: Boolean(options.silent)
      })
      return
    }
  }
  await selectTicket(visibleTickets.value[0].id)
}

const selectTicket = async (ticketId, options = {}) => {
  const { data } = await api.get(`/auth/hq/tickets/${ticketId}/`, {
    meta: options.silent ? { trackLoading: false, showErrorToast: false } : undefined
  })
  selectedTicket.value = data
  if (!options.keepReply) {
    ticketReply.body = ''
    ticketReply.status = ''
  }
  if (!options.keepReply) {
    ticketReply.assign_to_user_id = Number(data?.assigned_to || 0)
    ticketReply.is_internal = false
    const suggestedTransferAmount = isWalletOperationTicket(data) && !walletTransfer.skipNextSuggestedAmount
      ? extractWalletTransferAmount(data)
      : 0
    walletTransfer.amountText = suggestedTransferAmount > 0 ? String(suggestedTransferAmount) : ''
    walletTransfer.skipNextSuggestedAmount = false
    walletTransfer.error = ''
    walletTransfer.success = ''
    registrationApproval.error = ''
    registrationApproval.message = ''
  }
}

const refreshTicketsQuietly = async () => {
  if (hqTicketPollingInFlight) return
  hqTicketPollingInFlight = true
  try {
    await loadTickets({
      keepReply: true,
      notifyNew: true,
      silent: true,
      skipSelection: true
    })
  } finally {
    hqTicketPollingInFlight = false
  }
}

const sendTicketReply = async () => {
  const body = String(ticketReply.body || '').trim()
  if (!selectedTicket.value?.id || !body) return
  await api.post(`/auth/hq/tickets/${selectedTicket.value.id}/messages/`, {
    body,
    status: ticketReply.status || undefined,
    assign_to_user_id: Number(ticketReply.assign_to_user_id || 0) || undefined,
    is_internal: ticketReply.is_internal
  })
  await selectTicket(selectedTicket.value.id)
  await loadTickets()
  await loadOverview()
}

const submitWalletTransfer = async () => {
  walletTransfer.error = ''
  walletTransfer.success = ''
  if (!selectedTicket.value?.id || walletTransfer.submitting) return
  const amount = parseTransferAmount(walletTransfer.amountText)
  if (!amount || amount <= 0) {
    walletTransfer.error = 'مبلغ انتقال را به تومان وارد کنید.'
    return
  }
  walletTransfer.submitting = true
  try {
    const endpoint = isWalletBankWithdrawalTicket(selectedTicket.value)
      ? `/auth/hq/tickets/${selectedTicket.value.id}/wallet-withdraw/`
      : `/auth/hq/tickets/${selectedTicket.value.id}/wallet-transfer/`
    await api.post(endpoint, { amount })
    walletTransfer.amountText = ''
    walletTransfer.success = 'انتقال وجه ثبت شد و کیف پول مقصد شارژ شد.'
    walletTransfer.skipNextSuggestedAmount = true
    if (isWalletBankWithdrawalTicket(selectedTicket.value)) {
      walletTransfer.success = 'برداشت ثبت شد و مبلغ از کیف پول کم شد.'
    }
    await selectTicket(selectedTicket.value.id)
    await loadTickets()
    await loadOverview()
  } catch (error) {
    const { data } = error?.response || {}
    walletTransfer.error = data?.detail || 'انتقال وجه ثبت نشد. اطلاعات تیکت یا کیف پول را بررسی کنید.'
  } finally {
    walletTransfer.submitting = false
  }
}

const approveRegistrationTicket = async () => {
  registrationApproval.error = ''
  registrationApproval.message = ''
  if (!selectedTicket.value?.id || registrationApproval.submitting || !canApproveRegistration.value) return
  registrationApproval.submitting = true
  try {
    const { data } = await api.post(`/auth/hq/tickets/${selectedTicket.value.id}/approve-registration/`, {})
    registrationApproval.message = data?.sms?.ok
      ? 'ثبت‌نام تایید شد و پیامک فعال‌سازی هم ارسال شد.'
      : (data?.sms?.message || data?.detail || 'ثبت‌نام تایید شد.')
    await selectTicket(selectedTicket.value.id)
    await loadTickets()
    await loadOverview()
    if (authStore.isHqAdmin) await loadCarwashes()
  } catch (error) {
    registrationApproval.error = error?.response?.data?.detail || 'تایید ثبت‌نام انجام نشد.'
  } finally {
    registrationApproval.submitting = false
  }
}

const loadReports = async () => {
  const start = parseJalaliToIso(reportFilter.start)
  const end = parseJalaliToIso(reportFilter.end)
  const { data } = await api.get('/auth/hq/reports/', {
    params: {
      start: start || undefined,
      end: end || undefined
    }
  })
  reports.summary = data?.summary || {}
  reports.rows = data?.rows || []
  reports.trends = data?.trends || []
  reports.highlights = data?.highlights || {}
  reports.feature_summary = data?.feature_summary || []
  reports.wallet_transactions = data?.wallet_transactions || []
}

const loadTenantReports = async () => {
  const tenantId = Number(selectedReportTenantId.value || 0)
  if (!tenantId || tenantReport.loading) return
  tenantReport.loading = true
  tenantReport.error = ''
  try {
    const start = parseJalaliToIso(reportFilter.start)
    const end = parseJalaliToIso(reportFilter.end)
    const { data } = await api.get(`/auth/hq/carwashes/${tenantId}/reports/`, {
      params: {
        start: start || undefined,
        end: end || undefined
      }
    })
    tenantReport.data = data || null
  } catch (error) {
    tenantReport.error = error?.response?.data?.detail || 'دریافت گزارش کارواش انتخابی ناموفق بود.'
    tenantReport.data = null
  } finally {
    tenantReport.loading = false
  }
}

const loadTeam = async () => {
  const { data } = await api.get('/auth/hq/team/')
  hqTeam.value = Array.isArray(data) ? data : []
}

const createSupportUser = async () => {
  supportFormError.value = ''
  try {
    await api.post('/auth/hq/team/', {
      first_name: supportForm.first_name,
      last_name: supportForm.last_name,
      username: supportForm.username,
      phone: supportForm.phone,
      password: supportForm.password
    })
    Object.assign(supportForm, {
      first_name: '',
      last_name: '',
      username: '',
      phone: '',
      password: '',
      tenant_id: 0
    })
    await loadTeam()
    await loadOverview()
  } catch (error) {
    const data = error?.response?.data
    if (typeof data?.detail === 'string' && data.detail) {
      supportFormError.value = data.detail
      return
    }
    if (data && typeof data === 'object') {
      const firstFieldError = Object.values(data).flat().find(Boolean)
      supportFormError.value = String(firstFieldError || 'ثبت پشتیبان انجام نشد. دوباره تلاش کنید.')
      return
    }
    supportFormError.value = 'ثبت پشتیبان انجام نشد. دوباره تلاش کنید.'
  }
}

const openEditSupportUser = async (member) => {
  editSupportModal.open = true
  editSupportModal.id = Number(member.id || 0)
  editSupportModal.first_name = member.first_name || ''
  editSupportModal.last_name = member.last_name || ''
  editSupportModal.username = member.username || ''
  editSupportModal.phone = member.phone || ''
  editSupportModal.password = ''
  editSupportModal.tenant_id = Number(member.tenant || 0)
  editSupportModal.is_active = Boolean(member.is_active)
  editSupportModal.error = ''
}

const closeEditSupportModal = () => {
  editSupportModal.open = false
  editSupportModal.id = 0
  editSupportModal.first_name = ''
  editSupportModal.last_name = ''
  editSupportModal.username = ''
  editSupportModal.phone = ''
  editSupportModal.password = ''
  editSupportModal.tenant_id = 0
  editSupportModal.is_active = true
  editSupportModal.error = ''
}

const updateSupportUser = async () => {
  editSupportModal.error = ''
  try {
    await api.patch(`/auth/hq/team/${editSupportModal.id}/`, {
      first_name: editSupportModal.first_name,
      last_name: editSupportModal.last_name,
      username: editSupportModal.username,
      phone: editSupportModal.phone,
      password: editSupportModal.password || undefined,
      tenant_id: null,
      is_active: editSupportModal.is_active
    })
    closeEditSupportModal()
    await loadTeam()
    await loadOverview()
  } catch (error) {
    const data = error?.response?.data
    if (typeof data?.detail === 'string' && data.detail) {
      editSupportModal.error = data.detail
      return
    }
    if (data && typeof data === 'object') {
      const firstFieldError = Object.values(data).flat().find(Boolean)
      editSupportModal.error = String(firstFieldError || 'ویرایش پشتیبان انجام نشد. دوباره تلاش کنید.')
      return
    }
    editSupportModal.error = 'ویرایش پشتیبان انجام نشد. دوباره تلاش کنید.'
  }
}

const deleteSupportUser = async (member) => {
  if (!window.confirm(`پشتیبان «${member.full_name || member.username}» حذف شود؟`)) return
  await api.delete(`/auth/hq/team/${member.id}/`)
  await loadTeam()
  await loadTickets()
  await loadOverview()
}

const logout = async () => {
  await authStore.logout()
  await router.push('/login')
}

watch(activeTab, async (tab) => {
  closeMobileSidebar()
  if (!visibleTabs.value.some((item) => item.key === tab)) {
    activeTab.value = visibleTabs.value[0]?.key || 'tickets'
    return
  }
  if (tab === 'overview') await loadOverview()
  if (tab === 'carwashes') await loadCarwashes()
  if (tab === 'tickets') await loadTickets()
  if (tab === 'team' && authStore.isHqAdmin) await loadTeam()
  if (tab === 'reports' && authStore.isHqAdmin) {
    if (!carwashes.value.length) await loadCarwashes()
    if (!selectedReportTenantId.value && carwashes.value[0]?.id) selectedReportTenantId.value = String(carwashes.value[0].id)
    await Promise.all([loadReports(), selectedReportTenantId.value ? loadTenantReports() : Promise.resolve()])
  }
})

watch(() => [reportFilter.start, reportFilter.end], async () => {
  if (activeTab.value === 'reports' && authStore.isHqAdmin) {
    await Promise.all([loadReports(), selectedReportTenantId.value ? loadTenantReports() : Promise.resolve()])
  }
})

watch(selectedReportTenantId, async () => {
  if (activeTab.value === 'reports' && authStore.isHqAdmin) await loadTenantReports()
})

watch(ticketScope, async () => {
  await ensureSelectedTicket()
})

onMounted(async () => {
  window.addEventListener('pointerdown', unlockNotificationAudio, { once: true })
  window.addEventListener('keydown', unlockNotificationAudio, { once: true })
  if (authStore.isHqAdmin) {
    await loadOverview()
    await loadCarwashes()
    await loadTeam()
  } else {
    activeTab.value = 'tickets'
  }
  setReportRange('month')
  if (activeTab.value === 'tickets') await loadTickets()
  hqTicketPollingTimer = window.setInterval(async () => {
    await refreshTicketsQuietly()
  }, 10000)
})

onBeforeUnmount(() => {
  if (hqTicketPollingTimer) window.clearInterval(hqTicketPollingTimer)
  window.removeEventListener('pointerdown', unlockNotificationAudio)
  window.removeEventListener('keydown', unlockNotificationAudio)
})
</script>

<style scoped>
:global(body) {
  background:
    radial-gradient(circle at top left, rgba(13, 110, 253, 0.12), transparent 32%),
    radial-gradient(circle at bottom right, rgba(2, 132, 199, 0.12), transparent 28%),
    #f3f7fb;
}

.hq-page {
  --bg-card: rgba(255, 255, 255, 0.9);
  --bg-soft: rgba(255, 255, 255, 0.7);
  --line: rgba(148, 163, 184, 0.14);
  --text: #0f172a;
  --muted: #64748b;
  --primary: #0f5dd7;
  --primary-soft: rgba(15, 93, 215, 0.12);
  --success-soft: rgba(22, 163, 74, 0.14);
  --warn-soft: rgba(245, 158, 11, 0.14);
  min-height: 100vh;
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  position: relative;
  color: var(--text);
}

.hq-page.support-only {
  grid-template-columns: minmax(0, 1fr);
}

.hq-bg {
  position: fixed;
  border-radius: 999px;
  filter: blur(90px);
  opacity: 0.55;
  pointer-events: none;
}

.hq-bg-one {
  width: 360px;
  height: 360px;
  top: -110px;
  right: -80px;
  background: rgba(59, 130, 246, 0.26);
}

.hq-bg-two {
  width: 420px;
  height: 420px;
  bottom: -160px;
  left: -100px;
  background: rgba(14, 165, 233, 0.18);
}

.hq-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 26px 20px;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 18px;
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(16px);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.06);
  z-index: 2;
}

.hq-mobile-overlay,
.hq-mobile-menu-btn {
  display: none;
}

.hq-brand,
.hq-profile {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.hq-brand-badge {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: inline-grid;
  place-items: center;
  background: linear-gradient(135deg, #0f5dd7, #0ea5e9);
  color: #fff;
  font-weight: 800;
}

.hq-brand strong,
.hq-profile strong {
  display: block;
  font-size: 16px;
}

.hq-brand small,
.hq-profile small {
  color: var(--muted);
  font-size: 12px;
}

.hq-nav {
  display: grid;
  gap: 8px;
  align-content: start;
}

.hq-nav-item {
  border: 0;
  text-align: right;
  border-radius: 18px;
  padding: 14px 16px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  display: grid;
  gap: 4px;
  position: relative;
  transition: 0.2s ease;
}

.hq-nav-item:hover,
.hq-nav-item.active {
  background: linear-gradient(135deg, rgba(15, 93, 215, 0.1), rgba(14, 165, 233, 0.08));
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.06);
}

.hq-nav-title {
  font-weight: 700;
}

.hq-nav-meta {
  color: var(--muted);
  font-size: 12px;
}

.hq-nav-count {
  position: absolute;
  left: 12px;
  top: 12px;
  min-width: 24px;
  height: 24px;
  padding: 0 7px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #ef4444;
  color: #fff;
  font-size: 11px;
  font-weight: 900;
}

.ghost-btn,
.link-btn,
.primary-btn,
.status-pill {
  border: 0;
  cursor: pointer;
  font: inherit;
}

.ghost-btn {
  background: rgba(239, 68, 68, 0.08);
  color: #b91c1c;
  border-radius: 12px;
  padding: 9px 12px;
}

.hq-main {
  padding: 28px;
  display: grid;
  gap: 18px;
  position: relative;
  z-index: 1;
}

.hq-page.support-only .hq-main {
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  min-height: 100vh;
  height: auto;
  grid-template-rows: auto auto;
  overflow: visible;
}

.hq-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
}

.hq-header-compact {
  align-items: center;
  padding: 4px 2px 0;
}

.hq-kicker {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--muted);
}

.hq-header h1 {
  margin: 0;
  font-size: 30px;
  font-weight: 800;
}

.hq-header-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.hq-role-badge,
.meta-chip {
  border-radius: 999px;
  background: var(--bg-soft);
  color: var(--muted);
  padding: 8px 12px;
  font-size: 12px;
}

.primary-btn {
  height: 44px;
  padding: 0 18px;
  border-radius: 14px;
  background: linear-gradient(135deg, #0f5dd7, #0ea5e9);
  color: #fff;
  box-shadow: 0 18px 38px rgba(15, 93, 215, 0.18);
}

.glass-card,
.hero-card,
.summary-card,
.list-card,
.ticket-list-shell,
.ticket-chat-shell,
.ticket-placeholder {
  background: var(--bg-card);
  border-radius: 30px;
  backdrop-filter: blur(18px);
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.07);
}

.overview-grid {
  display: grid;
  grid-template-columns: 1.3fr 0.7fr;
  gap: 16px;
}

.hero-card {
  padding: 24px;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 18px;
}

.hero-copy p,
.hero-copy span {
  margin: 0;
  color: var(--muted);
}

.hero-copy h2 {
  margin: 10px 0 12px;
  font-size: 28px;
  line-height: 1.5;
}

.hero-stats,
.report-metrics {
  display: grid;
  gap: 10px;
}

.metric-box {
  background: rgba(255, 255, 255, 0.84);
  border-radius: 22px;
  padding: 14px 16px;
  display: grid;
  gap: 5px;
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.8);
}

.metric-box small {
  color: var(--muted);
}

.metric-box strong {
  font-size: 28px;
}

.summary-card,
.list-card {
  padding: 20px;
  display: grid;
  gap: 14px;
}

.summary-head,
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.summary-head h3,
.card-head h3 {
  margin: 0;
  font-size: 18px;
}

.summary-head span,
.card-head span {
  color: var(--muted);
  font-size: 12px;
}

.summary-items {
  display: grid;
  gap: 10px;
}

.summary-item {
  background: rgba(15, 23, 42, 0.03);
  border-radius: 18px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-item.warn {
  background: var(--warn-soft);
}

.compact-list {
  display: grid;
  gap: 10px;
}

.compact-row {
  border-radius: 16px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.72);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.compact-row strong,
.row-sub,
.team-card strong {
  display: block;
}

.row-sub {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}

.status-dot,
.ticket-mini-status {
  border-radius: 999px;
  padding: 7px 11px;
  font-size: 11px;
  font-weight: 700;
}

.status-dot {
  background: var(--success-soft);
  color: #166534;
}

.status-dot.off,
.status-pill.off {
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
}

.link-btn {
  background: transparent;
  color: var(--primary);
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(340px, 430px) minmax(0, 1fr);
  gap: 16px;
}

.carwash-ops-grid .table-card {
  grid-column: 1 / -1;
}

.create-card,
.table-card,
.report-shell,
.tenant-command-card {
  padding: 20px;
}

.tenant-command-card {
  min-height: 430px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background:
    linear-gradient(135deg, rgba(255,255,255,.92), rgba(245,248,252,.82)),
    radial-gradient(circle at top right, rgba(14, 165, 233, .12), transparent 42%);
  overflow: hidden;
}

.tenant-command-empty {
  min-height: 390px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  text-align: center;
  color: var(--muted);
}

.tenant-command-empty h3 {
  margin: 0;
  color: var(--text);
  font-size: 24px;
}

.tenant-command-empty p {
  margin: 0;
  max-width: 46ch;
  line-height: 1.9;
}

.tenant-command-mark {
  width: 62px;
  height: 62px;
  border-radius: 22px;
  display: inline-grid;
  place-items: center;
  color: #fff;
  font-weight: 900;
  background: linear-gradient(135deg, #0f5dd7, #0ea5e9);
  box-shadow: 0 18px 34px rgba(15, 93, 215, .22);
}

.tenant-command-mark.error {
  background: linear-gradient(135deg, #dc2626, #fb7185);
}

.tenant-command-mark.pulse {
  animation: hqPulse 1.1s ease-in-out infinite;
}

.tenant-command-content {
  display: grid;
  gap: 16px;
}

.tenant-command-head,
.tenant-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}

.tenant-command-head small,
.tenant-panel-head span,
.tenant-kpi-card small,
.wallet-monitor-row small,
.option-monitor-row small,
.attendance-monitor-row small,
.transaction-monitor-row small {
  color: var(--muted);
  font-size: 12px;
}

.tenant-command-head h3 {
  margin: 6px 0 4px;
  font-size: 26px;
  color: var(--text);
}

.tenant-command-head p {
  margin: 0;
  color: var(--muted);
  line-height: 1.8;
}

.refresh-btn {
  border: 0;
  height: 40px;
  padding: 0 14px;
  border-radius: 14px;
  background: rgba(15, 93, 215, .1);
  color: var(--primary);
  cursor: pointer;
  font-weight: 800;
}

.tenant-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.tenant-kpi-card {
  border: 1px solid rgba(148, 163, 184, .14);
  border-radius: 20px;
  padding: 14px;
  background: rgba(255, 255, 255, .78);
  display: grid;
  gap: 7px;
}

.tenant-kpi-card.primary {
  background: linear-gradient(135deg, rgba(15, 93, 215, .14), rgba(14, 165, 233, .08));
}

.tenant-kpi-card strong {
  font-size: 20px;
  color: var(--text);
  line-height: 1.35;
  word-break: break-word;
}

.tenant-kpi-card span {
  color: var(--muted);
  font-size: 11px;
}

.tenant-monitor-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.tenant-monitor-panel {
  border: 1px solid rgba(148, 163, 184, .14);
  border-radius: 22px;
  padding: 14px;
  background: rgba(255, 255, 255, .72);
  display: grid;
  gap: 12px;
}

.tenant-monitor-panel.wide-panel {
  width: 100%;
}

.tenant-panel-head h4 {
  margin: 0;
  color: var(--text);
  font-size: 16px;
}

.wallet-monitor-list,
.option-monitor-list,
.attendance-monitor-list,
.transaction-monitor-list {
  display: grid;
  gap: 8px;
}

.wallet-monitor-row,
.option-monitor-row,
.attendance-monitor-row,
.transaction-monitor-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 12px;
  border-radius: 16px;
  background: rgba(248, 250, 252, .86);
}

.wallet-monitor-row strong,
.option-monitor-row strong,
.attendance-monitor-row strong,
.transaction-monitor-row strong {
  color: var(--text);
}

.wallet-monitor-row span,
.option-monitor-row span,
.transaction-monitor-row span {
  color: var(--primary);
  font-weight: 900;
}

.option-monitor-row.active {
  background: rgba(220, 252, 231, .62);
}

.attendance-monitor-row {
  justify-content: start;
}

.attendance-monitor-row em {
  margin-right: auto;
  font-style: normal;
  font-size: 12px;
  font-weight: 900;
  color: #64748b;
}

.attendance-monitor-row.in em {
  color: #166534;
}

.attendance-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #94a3b8;
  box-shadow: 0 0 0 5px rgba(148, 163, 184, .14);
}

.attendance-monitor-row.in .attendance-dot {
  background: #16a34a;
  box-shadow: 0 0 0 5px rgba(22, 163, 74, .14);
}

.transaction-monitor-row.out span {
  color: #dc2626;
}

.tenant-name-btn {
  border: 0;
  background: transparent;
  color: var(--text);
  padding: 0;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
  text-align: right;
}

.tenant-name-btn:hover,
.tenant-name-btn.active {
  color: var(--primary);
}

@keyframes hqPulse {
  0%, 100% { transform: scale(1); opacity: .72; }
  50% { transform: scale(1.06); opacity: 1; }
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid label {
  display: grid;
  gap: 6px;
}

.form-grid label span {
  color: var(--muted);
  font-size: 12px;
}

.form-grid input,
.form-grid select,
.ticket-filter-grid input,
.ticket-filter-grid select,
.table-search,
.chat-head-actions select,
.report-filters input,
.chat-reply textarea {
  border: 1px solid rgba(203, 213, 225, 0.72);
  background: rgba(248, 251, 255, 0.94);
  border-radius: 16px;
  padding: 0 12px;
  font: inherit;
  color: var(--text);
}

.form-grid input:focus,
.form-grid select:focus,
.ticket-filter-grid input:focus,
.ticket-filter-grid select:focus,
.table-search:focus,
.chat-head-actions select:focus,
.report-filters input:focus,
.chat-reply textarea:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.35);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.08);
}

.form-grid input,
.form-grid select,
.ticket-filter-grid input,
.ticket-filter-grid select,
.table-search,
.chat-head-actions select,
.report-filters input {
  height: 44px;
}

.wide {
  grid-column: 1 / -1;
}

.support-scope-note {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid rgba(203, 213, 225, 0.72);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.92);
}

.support-scope-note span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}

.support-scope-note strong {
  color: var(--text);
  font-size: 14px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.form-error {
  margin: 0;
  padding: 11px 14px;
  border-radius: 14px;
  background: rgba(254, 226, 226, 0.9);
  color: #b91c1c;
  font-size: 13px;
  font-weight: 700;
}

.table-toolbar {
  margin: 4px 0 12px;
}

.table-search {
  width: 100%;
}

.table-wrap {
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 12px 10px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  text-align: right;
  vertical-align: top;
  white-space: nowrap;
}

td strong {
  display: block;
}

.status-toggle {
  background: var(--primary-soft);
  color: var(--primary);
}

.ticket-center {
  display: grid;
  grid-template-columns: 390px minmax(0, 1fr);
  gap: 16px;
  min-height: calc(100vh - 170px);
  min-width: 0;
}

.ticket-command-center {
  display: grid;
  gap: 14px;
  min-height: calc(100vh - 170px);
}

.hq-page.support-only .ticket-center {
  min-height: 0;
  height: 100%;
}

.ticket-desk {
  grid-template-columns: minmax(340px, 420px) minmax(0, 1fr);
}

.ticket-list-shell,
.ticket-chat-shell,
.ticket-placeholder {
  padding: 20px;
  min-height: 0;
  min-width: 0;
}

.ticket-modern-shell {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 30px;
  background:
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 251, 255, 0.96));
  box-shadow: 0 24px 56px rgba(15, 23, 42, 0.06);
}

.command-top-grid,
.command-body-grid,
.command-health-grid,
.priority-queue-list,
.ticket-side-detail-list,
.ticket-activity-list,
.template-chip-row {
  display: grid;
  gap: 14px;
}

.command-top-grid {
  grid-template-columns: minmax(0, 1.25fr) 420px;
}

.command-top-grid.compact {
  grid-template-columns: 1fr;
}

.command-body-grid {
  grid-template-columns: 390px minmax(0, 1fr) 320px;
  align-items: start;
}

.command-body-grid.compact {
  grid-template-columns: 320px minmax(0, 1fr);
}

.command-body-grid-simple {
  grid-template-columns: minmax(320px, 380px) minmax(0, 1fr);
}

.command-body-grid-simple.compact {
  grid-template-columns: minmax(300px, 360px) minmax(0, 1fr);
}

.ticket-workspace-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
}

.ticket-workspace-copy {
  display: grid;
  gap: 8px;
}

.ticket-workspace-copy h3 {
  margin: 0;
  color: var(--text);
  font-size: 22px;
}

.ticket-workspace-copy p {
  margin: 0;
  color: var(--muted);
  line-height: 1.8;
  font-size: 13px;
}

.ticket-workspace-actions {
  display: flex;
  align-items: stretch;
  gap: 10px;
  flex-wrap: wrap;
}

.ticket-workspace-stat {
  min-width: 88px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.9);
  display: grid;
  gap: 4px;
}

.ticket-workspace-stat small {
  color: var(--muted);
  font-size: 11px;
}

.ticket-workspace-stat strong {
  color: var(--text);
  font-size: 16px;
}

.command-focus-card,
.command-health-card,
.command-inbox-card,
.command-chat-card,
.ticket-side-rail {
  padding: 20px;
}

.command-focus-card {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) 220px;
  gap: 16px;
}

.support-ticket-mode .command-focus-card {
  grid-template-columns: minmax(0, 1fr) 200px;
}

.command-focus-copy {
  display: grid;
  gap: 10px;
}

.command-focus-copy h3,
.command-health-card h3,
.ticket-side-rail h3 {
  margin: 0;
  color: var(--text);
}

.command-focus-copy p,
.priority-queue-item p,
.priority-queue-item small,
.ticket-activity-row p,
.ticket-activity-row small {
  margin: 0;
  color: var(--muted);
  line-height: 1.85;
}

.command-focus-side {
  display: grid;
  align-content: start;
  gap: 10px;
}

.command-health-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.health-tile {
  padding: 16px;
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(255, 255, 255, 0.84);
  display: grid;
  gap: 8px;
}

.health-tile.spotlight {
  background: linear-gradient(135deg, rgba(15, 93, 215, 0.14), rgba(14, 165, 233, 0.08));
  box-shadow: 0 18px 38px rgba(15, 93, 215, 0.12);
}

.health-tile small,
.priority-queue-item small,
.trend-bar-item small,
.ticket-activity-row small,
.ticket-side-detail-list .detail-row span {
  color: var(--muted);
  font-size: 11px;
}

.health-tile strong,
.trend-bar-item strong,
.ticket-side-detail-list .detail-row strong {
  color: var(--text);
  font-size: 18px;
}

.hq-page.support-only .ticket-list-shell,
.hq-page.support-only .ticket-chat-shell,
.hq-page.support-only .ticket-placeholder {
  height: 100%;
  overflow: hidden;
}

.ticket-inbox-shell {
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
  gap: 12px;
}

.desk-hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) 220px;
  gap: 14px;
  padding: 18px;
  border-radius: 26px;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.14), transparent 28%),
    linear-gradient(135deg, rgba(15, 93, 215, 0.08), rgba(255, 255, 255, 0.94));
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.desk-kicker {
  display: inline-flex;
  width: fit-content;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(15, 93, 215, 0.1);
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
}

.desk-hero-copy {
  display: grid;
  gap: 10px;
}

.desk-hero-copy h3,
.desk-focus-box strong,
.desk-placeholder strong {
  margin: 0;
  color: var(--text);
}

.desk-hero-copy p,
.desk-focus-box small,
.desk-focus-box strong,
.desk-summary-card small,
.desk-placeholder span {
  line-height: 1.85;
}

.desk-hero-actions {
  display: grid;
  align-content: start;
  gap: 10px;
}

.desk-refresh-btn {
  justify-self: stretch;
  text-align: center;
}

.desk-focus-box {
  padding: 16px;
  border-radius: 22px;
  background: rgba(15, 23, 42, 0.92);
  color: #fff;
  display: grid;
  gap: 8px;
}

.desk-focus-box small {
  color: rgba(255, 255, 255, 0.7);
}

.desk-focus-box strong {
  color: #fff;
  font-size: 18px;
}

.ticket-inbox-head {
  margin-bottom: 0;
}

.ticket-inbox-head h3 {
  margin: 0;
  font-size: 18px;
}

.ticket-filter-grid {
  display: grid;
  gap: 8px;
  margin: 6px 0 10px;
}

.ticket-filter-grid-wide {
  grid-template-columns: 1.2fr 0.8fr 0.8fr 0.8fr;
}

.ticket-filter-grid-wide.compact {
  grid-template-columns: 1.3fr 0.7fr;
}

.ticket-filter-grid input,
.ticket-filter-grid select {
  min-width: 0;
}

.ticket-list {
  display: grid;
  gap: 8px;
  max-height: calc(100vh - 270px);
  overflow: auto;
  padding: 2px;
}

.hq-page.support-only .ticket-list {
  max-height: calc(100vh - 290px);
  min-height: 0;
  overflow: auto;
}

.hq-ticket-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.desk-summary-grid {
  gap: 12px;
}

.hq-ticket-summary-card,
.hq-ticket-meta-card {
  padding: 12px 13px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(148, 163, 184, 0.18);
  display: grid;
  gap: 4px;
  min-width: 0;
}

.desk-summary-card {
  gap: 6px;
  min-height: 104px;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.04);
}

.desk-summary-card small {
  color: var(--muted);
  font-size: 11px;
}

.priority-queue-item {
  padding: 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(226, 232, 240, 0.84);
  display: grid;
  gap: 6px;
}

.hq-ticket-summary-card span,
.hq-ticket-meta-card span {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.45;
}

.hq-ticket-summary-card strong,
.hq-ticket-meta-card strong {
  font-size: 14px;
  line-height: 1.1;
  color: var(--text);
}

.hq-ticket-summary-card.open { background: rgba(219, 234, 254, 0.58); }
.hq-ticket-summary-card.pending { background: rgba(254, 243, 199, 0.6); }
.hq-ticket-summary-card.mine { background: rgba(220, 252, 231, 0.62); }
.hq-ticket-summary-card.urgent { background: rgba(254, 226, 226, 0.68); }

.hq-ticket-scope-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.scope-chip {
  border: 0;
  border-radius: 999px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--muted);
  cursor: pointer;
  font: inherit;
  font-size: 10px;
  font-weight: 700;
}

.scope-chip.active {
  background: linear-gradient(135deg, rgba(15, 93, 215, 0.14), rgba(14, 165, 233, 0.16));
  color: var(--primary);
  border-color: rgba(15, 93, 215, 0.22);
}

.ticket-thread {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 24px;
  padding: 14px;
  text-align: right;
  cursor: pointer;
  display: grid;
  gap: 8px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.04);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.ticket-thread:hover {
  transform: translateY(-1px);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.06);
}

.ticket-thread.active {
  background: linear-gradient(135deg, rgba(15, 93, 215, 0.1), rgba(14, 165, 233, 0.08));
  box-shadow:
    0 18px 40px rgba(15, 93, 215, 0.12),
    inset 0 0 0 1px rgba(59, 130, 246, 0.18);
}

.desk-ticket-thread {
  border: 1px solid rgba(226, 232, 240, 0.84);
}

.ticket-thread-rich {
  gap: 8px;
  border-radius: 22px;
}

.ticket-thread-top,
.ticket-thread-meta,
.chat-head,
.chat-head-actions,
.chat-tools,
.chat-head-badges {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
}

.ticket-thread p,
.chat-head p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
  font-size: 12px;
}

.ticket-thread-top strong,
.chat-head h3,
.chat-head p {
  min-width: 0;
}

.ticket-thread-top strong {
  font-size: 14px;
}

.ticket-thread p {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ticket-thread-meta {
  color: var(--muted);
  font-size: 10px;
}

.ticket-thread-foot {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: var(--muted);
  font-size: 10px;
  flex-wrap: wrap;
}

.ticket-list-empty {
  min-height: 220px;
  display: grid;
  place-items: center;
  text-align: center;
  gap: 8px;
  color: var(--muted);
  padding: 18px;
}

.desk-empty {
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px dashed rgba(148, 163, 184, 0.4);
}

.ticket-mini-status.ticket-open {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.ticket-mini-status.ticket-pending {
  background: rgba(245, 158, 11, 0.16);
  color: #b45309;
}

.ticket-mini-status.ticket-answered {
  background: rgba(22, 163, 74, 0.14);
  color: #15803d;
}

.ticket-mini-status.ticket-closed {
  background: rgba(100, 116, 139, 0.14);
  color: #475569;
}

.chat-head {
  padding: 2px 0 12px;
}

.ticket-chat-shell-rich {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 10px;
  max-height: calc(100dvh - 184px);
  overflow: hidden;
}

.desk-detail-head {
  display: grid;
  gap: 8px;
}

.hq-page.support-only .ticket-chat-shell-rich {
  height: 100%;
}

.ticket-chat-head {
  padding: 0 0 14px;
  margin: 0;
}

.ticket-chat-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.ticket-chat-actions {
  padding: 0;
  border: 0;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 8px;
}

.ticket-chat-actions select {
  min-width: 0;
  flex: 1 1 220px;
}

.hq-ticket-meta-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.desk-ticket-chat-head {
  padding: 0;
}

.hq-ticket-meta-card.safe {
  background: rgba(219, 234, 254, 0.58);
}

.hq-ticket-meta-card.risk {
  background: rgba(254, 243, 199, 0.72);
}

.hq-ticket-meta-card.breached {
  background: rgba(254, 226, 226, 0.76);
}

.hq-ticket-meta-card.resolved {
  background: rgba(220, 252, 231, 0.72);
}

.hq-ticket-meta-card small {
  color: var(--muted);
  font-size: 11px;
}

.chat-head h3 {
  margin: 0 0 5px;
  font-size: 17px;
}

.chat-stream {
  min-height: 0;
  overflow: auto;
  display: grid;
  gap: 12px;
  padding: 18px;
  border-radius: 26px;
  background: linear-gradient(180deg, rgba(247, 250, 255, 0.94), rgba(255, 255, 255, 0.98));
}

.hq-page.support-only .chat-stream {
  min-height: 0;
  overflow: auto;
}

.ticket-chat-stream {
  padding: 18px;
}

.desk-ticket-stream {
  border: 1px solid rgba(226, 232, 240, 0.8);
}

.chat-bubble {
  width: min(82%, 560px);
  border-radius: 22px 22px 8px 22px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.88);
  display: grid;
  gap: 8px;
}

.ticket-chat-bubble {
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.05);
}

.chat-bubble.mine {
  margin-right: auto;
  border-radius: 22px 22px 22px 8px;
  background: linear-gradient(135deg, rgba(15, 93, 215, 0.14), rgba(14, 165, 233, 0.09));
}

.chat-bubble.internal {
  border-style: dashed;
  background: rgba(248, 250, 252, 0.92);
}

.chat-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--muted);
  font-size: 11px;
}

.chat-bubble p {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.9;
  font-size: 13px;
}

.chat-bubble small {
  color: var(--muted);
  font-size: 11px;
}

.chat-reply {
  padding: 12px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  display: grid;
  gap: 8px;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.05);
}

.ticket-chat-reply {
  padding: 12px;
  position: sticky;
  bottom: 0;
  z-index: 2;
}

.desk-ticket-reply {
  border: 1px solid rgba(226, 232, 240, 0.86);
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(8px);
}

.template-chip-row {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.template-chip-row.compact {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.template-chip {
  border: 0;
  border-radius: 12px;
  padding: 7px 9px;
  background: rgba(219, 234, 254, 0.84);
  color: var(--primary);
  font: inherit;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.desk-ticket-reply textarea {
  min-height: 58px;
  max-height: 96px;
  resize: none;
}

.quick-status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.support-ticket-mode .desk-summary-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.support-ticket-mode .command-inbox-card,
.support-ticket-mode .command-chat-card {
  align-self: stretch;
}

.danger-chip {
  background: rgba(254, 226, 226, 0.82);
  color: #b91c1c;
}

.chat-reply textarea {
  min-height: 58px;
  max-height: 96px;
  padding: 12px;
  resize: none;
  min-width: 0;
  width: 100%;
  box-sizing: border-box;
  font-size: 13px;
}

.internal-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
}

.chat-head-badges,
.chat-tools,
.ticket-thread-meta {
  flex-wrap: wrap;
}

.ticket-chat-shell-rich > * {
  min-width: 0;
}

.command-body-grid-simple,
.command-body-grid-simple.compact,
.command-chat-card,
.ticket-chat-shell-rich {
  min-width: 0;
}

.ticket-chat-shell-rich {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ticket-chat-shell-rich .chat-stream {
  flex: 1 1 auto;
  min-height: 0;
}

.ticket-chat-reply {
  flex: 0 0 auto;
  max-width: 100%;
  min-width: 0;
}

.chat-tools {
  min-width: 0;
}

.chat-tools .primary-btn {
  max-width: 100%;
  white-space: nowrap;
}

.ticket-placeholder {
  display: grid;
  place-items: center;
  text-align: center;
  gap: 8px;
  color: var(--muted);
}

.ticket-placeholder-rich {
  min-height: 100%;
}

.desk-placeholder {
  border-style: dashed;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.1), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.96));
}

.ticket-side-rail {
  display: grid;
  align-content: start;
  gap: 14px;
}

.rail-block {
  display: grid;
  gap: 12px;
}

.ticket-side-detail-list .detail-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.92);
}

.trend-bars {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
  align-items: end;
}

.trend-bar-item {
  display: grid;
  gap: 8px;
  text-align: center;
}

.trend-bar-shell {
  height: 116px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(226, 232, 240, 0.28), rgba(241, 245, 249, 0.76));
  display: flex;
  align-items: end;
  padding: 8px;
}

.trend-bar-fill {
  width: 100%;
  border-radius: 14px;
  background: linear-gradient(180deg, #38bdf8, #0f5dd7);
  box-shadow: 0 16px 30px rgba(15, 93, 215, 0.16);
}

.ticket-activity-row {
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr);
  gap: 12px;
}

.ticket-activity-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
}

.ticket-activity-dot.primary,
.ticket-activity-dot.info {
  background: #2563eb;
}

.ticket-activity-dot.success {
  background: #16a34a;
}

.ticket-activity-dot.neutral,
.ticket-activity-dot.muted {
  background: #94a3b8;
}

.team-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.team-card {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.78);
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.team-card-body {
  display: grid;
  gap: 4px;
}

.team-avatar {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #0f5dd7, #38bdf8);
  color: #fff;
  font-weight: 800;
}

.team-card p,
.team-card small {
  margin: 4px 0 0;
  color: var(--muted);
}

.team-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  display: grid;
  place-items: center;
  padding: 20px;
  z-index: 40;
}

.modal-card {
  width: min(680px, 100%);
  max-height: calc(100vh - 40px);
  overflow: auto;
  padding: 20px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
}

.inline-toggle {
  display: flex !important;
  align-items: center;
  gap: 10px;
}

.team-rating {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.team-stars {
  position: relative;
  display: inline-grid;
  line-height: 1;
  font-size: 16px;
  letter-spacing: 1px;
  width: max-content;
  direction: ltr;
}

.team-stars-base {
  color: #cbd5e1;
  grid-area: 1 / 1;
}

.team-stars-fill {
  position: absolute;
  top: 0;
  left: 0;
  overflow: hidden;
  white-space: nowrap;
  color: #f59e0b;
}

.team-rating-score {
  color: #0f172a;
  font-weight: 800;
  font-size: 13px;
}

.team-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 12px;
  margin-top: 6px;
}

.team-metrics small {
  margin: 0;
}

.report-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.report-shell {
  display: grid;
  gap: 18px;
}

.report-top-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) 360px;
  gap: 16px;
}

.report-hero {
  display: grid;
  gap: 18px;
  min-height: 100%;
  padding: 24px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 30px;
  background:
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.16), transparent 28%),
    linear-gradient(135deg, rgba(15, 93, 215, 0.08), rgba(255, 255, 255, 0.94));
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.07);
}

.report-hero-copy {
  padding: 0;
}

.report-eyebrow {
  display: inline-flex;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(15, 93, 215, 0.1);
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
}

.report-hero-copy h3 {
  margin: 14px 0 12px;
  font-size: 32px;
  line-height: 1.45;
  max-width: 13ch;
}

.report-hero-copy p,
.report-period {
  margin: 0;
  color: var(--muted);
  line-height: 1.95;
}

.report-glance-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.glance-chip {
  border-radius: 22px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.14);
  display: grid;
  gap: 8px;
}

.glance-chip small {
  color: var(--muted);
}

.glance-chip strong {
  font-size: 20px;
  line-height: 1.4;
  word-break: break-word;
}

.report-control-rail {
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(241, 245, 249, 0.9));
  border-radius: 30px;
  padding: 18px;
  display: grid;
  align-content: start;
  gap: 14px;
  box-shadow: 0 22px 52px rgba(15, 23, 42, 0.06);
}

.report-control-block {
  display: grid;
  gap: 10px;
}

.report-control-label {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}

.report-period-card {
  border-radius: 22px;
  padding: 14px 16px;
  background: rgba(15, 23, 42, 0.03);
  display: grid;
  gap: 8px;
}

.report-period-card small {
  color: var(--muted);
}

.report-period-card strong {
  font-size: 15px;
  line-height: 1.8;
}

.report-body-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) 320px;
  gap: 16px;
  align-items: start;
}

.report-main-col,
.report-side-col {
  display: grid;
  gap: 16px;
}

.report-kpi-grid,
.report-insight-grid,
.report-analytics-grid {
  display: grid;
  gap: 14px;
}

.report-kpi-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.report-money-kpis {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.finance-kpi-grid {
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
}

.report-kpi-card,
.report-highlight-card,
.report-trend-card,
.report-side-stats {
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.8);
  border-radius: 24px;
  padding: 16px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.05);
}

.report-kpi-card {
  display: grid;
  gap: 8px;
  min-height: 138px;
  align-content: start;
}

.report-kpi-card.spotlight {
  background: linear-gradient(135deg, rgba(15, 93, 215, 0.16), rgba(14, 165, 233, 0.1));
  box-shadow: 0 24px 50px rgba(15, 93, 215, 0.12);
}

.report-kpi-card small,
.report-highlight-card small,
.mini-stat small {
  color: var(--muted);
}

.report-kpi-card strong,
.report-highlight-card strong,
.mini-stat strong {
  font-size: 24px;
}

.report-kpi-card span,
.report-highlight-card span {
  color: var(--muted);
  font-size: 12px;
}

.delta-badge {
  width: fit-content;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
}

.delta-badge.up {
  background: rgba(22, 163, 74, 0.12);
  color: #166534;
}

.delta-badge.down {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.report-insight-grid {
  grid-template-columns: 1fr;
}

.report-highlight-card {
  display: grid;
  gap: 8px;
}

.report-highlight-card p {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
}

.report-highlight-card.success {
  background: linear-gradient(135deg, rgba(22, 163, 74, 0.12), rgba(255, 255, 255, 0.86));
}

.report-highlight-card.info {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(255, 255, 255, 0.86));
}

.report-highlight-card.warn {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.14), rgba(255, 255, 255, 0.86));
}

.report-trend-card {
  display: grid;
  gap: 14px;
}

.report-trend-surface {
  min-height: 100%;
}

.trend-bars {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
  gap: 10px;
  align-items: end;
}

.trend-bar-item {
  display: grid;
  gap: 8px;
  text-align: center;
}

.trend-bar-item small,
.empty-note {
  color: var(--muted);
}

.trend-bar-shell {
  height: 132px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(226, 232, 240, 0.24), rgba(241, 245, 249, 0.72));
  display: flex;
  align-items: end;
  padding: 10px;
}

.trend-bar-fill {
  width: 100%;
  border-radius: 14px;
  background: linear-gradient(180deg, #38bdf8, #0f5dd7);
  box-shadow: 0 16px 32px rgba(15, 93, 215, 0.18);
}

.report-side-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  align-content: start;
}

.mini-stat {
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.92);
  padding: 14px;
  display: grid;
  gap: 8px;
}

.report-table-wrap {
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.05);
}

.report-table-wrap table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: rgba(248, 250, 252, 0.94);
  backdrop-filter: blur(8px);
}

.report-table-wrap tbody tr:hover td {
  background: rgba(248, 250, 252, 0.9);
}

.health-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 7px 12px;
  font-size: 11px;
  font-weight: 800;
}

.health-pill.strong {
  background: rgba(22, 163, 74, 0.12);
  color: #166534;
}

.health-pill.stable {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.health-pill.healthy,
.health-pill.gateway {
  background: rgba(22, 163, 74, 0.12);
  color: #166534;
}

.health-pill.risk {
  background: rgba(245, 158, 11, 0.16);
  color: #b45309;
}

.health-pill.sms_heavy {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.health-pill.idle {
  background: rgba(148, 163, 184, 0.14);
  color: #475569;
}

.health-pill.empty {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.report-tabs,
.report-range-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.report-tab-btn,
.report-range-chip {
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.78);
  color: var(--muted);
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
  font-weight: 700;
  font-size: 12px;
}

.report-tab-btn.active,
.report-range-chip.active {
  background: rgba(15, 93, 215, 0.12);
  border-color: rgba(15, 93, 215, 0.24);
  color: var(--primary);
}

.wallet-ticket-transfer-card {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(180px, 0.8fr) auto;
  gap: 14px;
  align-items: end;
  margin: 12px 0 18px;
  padding: 18px;
  border-radius: 28px;
  background: linear-gradient(135deg, rgba(246, 240, 255, 0.96), rgba(255, 255, 255, 0.96));
  box-shadow: 0 18px 48px rgba(121, 92, 168, 0.14);
}

.registration-approval-card {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) auto;
  gap: 14px;
  align-items: end;
  margin: 12px 0 18px;
  padding: 18px;
  border-radius: 28px;
  background: linear-gradient(135deg, rgba(236, 253, 245, 0.96), rgba(255, 255, 255, 0.96));
  box-shadow: 0 18px 48px rgba(21, 128, 61, 0.12);
}

.registration-approval-card strong {
  display: block;
  margin-top: 4px;
  color: #14532d;
}

.registration-approval-card p,
.registration-approval-card span {
  margin: 0;
  color: #3f6b53;
}

.wallet-ticket-transfer-card strong {
  display: block;
  margin-top: 4px;
  color: #33224f;
}

.wallet-ticket-transfer-card p,
.wallet-ticket-transfer-card span {
  margin: 0;
  color: #7a6c91;
}

.wallet-ticket-transfer-card label {
  display: grid;
  gap: 8px;
}

.wallet-ticket-transfer-card input {
  min-height: 46px;
  border: 0;
  border-radius: 18px;
  padding: 0 14px;
  background: rgba(255, 255, 255, 0.86);
  color: #33224f;
  outline: none;
}

.wallet-transfer-btn {
  min-height: 46px;
  white-space: nowrap;
}

.transfer-feedback {
  grid-column: 1 / -1;
  padding: 8px 12px;
  border-radius: 14px;
}

.transfer-feedback.error {
  color: #a33030;
  background: rgba(255, 229, 229, 0.74);
}

.transfer-feedback.success {
  color: #23744a;
  background: rgba(225, 249, 235, 0.8);
}

.hq-ticket-attachments {
  display: grid;
  gap: 12px;
  margin: 8px 0 18px;
  padding: 18px;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(245, 243, 255, 0.96));
  box-shadow: 0 16px 40px rgba(51, 34, 79, 0.08);
}

.hq-ticket-attachments-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.hq-ticket-attachment-item {
  display: grid;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 18px;
  text-decoration: none;
  background: rgba(255, 255, 255, 0.92);
}

.hq-ticket-attachment-item strong {
  color: #33224f;
}

.hq-ticket-attachment-item span {
  color: #7c3aed;
  font-size: 12px;
  font-weight: 700;
}

@media (max-width: 1280px) {
  .hq-page {
    grid-template-columns: 1fr;
  }

  .hq-sidebar {
    position: static;
    height: auto;
    grid-template-rows: auto auto auto;
  }

  .overview-grid,
  .workspace-grid,
  .ticket-center,
  .command-top-grid,
  .command-body-grid,
  .report-top-grid,
  .report-body-grid {
    grid-template-columns: 1fr;
  }

  .report-kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .tenant-kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .tenant-monitor-grid {
    grid-template-columns: 1fr;
  }

  .report-insight-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 1560px) {
  .ticket-workspace-head {
    align-items: flex-start;
  }

  .ticket-filter-grid-wide {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .hq-main,
  .hq-sidebar {
    padding: 16px;
  }

  .hq-mobile-menu-btn {
    display: inline-grid;
    place-items: center;
    width: 40px;
    height: 40px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.92);
    color: var(--text);
    font: inherit;
    font-size: 18px;
  }

  .hq-mobile-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.32);
    z-index: 30;
  }

  .hq-sidebar {
    position: fixed;
    top: 0;
    right: 0;
    width: min(320px, calc(100vw - 24px));
    max-width: 100%;
    height: 100vh;
    transform: translateX(110%);
    opacity: 0;
    pointer-events: none;
    transition: transform .22s ease, opacity .22s ease;
    z-index: 35;
    overflow: auto;
  }

  .hq-sidebar.hq-sidebar-mobile-open {
    transform: translateX(0);
    opacity: 1;
    pointer-events: auto;
  }

  .hq-nav {
    display: grid;
    gap: 10px;
    overflow: visible;
    padding-bottom: 0;
  }

  .hq-nav-item {
    flex: unset;
  }

  .hero-card,
  .form-grid,
  .ticket-filter-grid,
  .team-grid,
  .tenant-kpi-grid,
  .report-kpi-grid,
  .report-side-stats,
  .report-glance-strip,
  .trend-bars,
  .tenant-monitor-grid {
    grid-template-columns: 1fr;
  }

  .tenant-command-head,
  .tenant-panel-head,
  .wallet-monitor-row,
  .option-monitor-row,
  .transaction-monitor-row {
    flex-direction: column;
    align-items: stretch;
  }

  .attendance-monitor-row {
    align-items: flex-start;
  }

  .team-metrics {
    grid-template-columns: 1fr;
  }

  .chat-head,
  .chat-head-actions,
  .chat-head-badges,
  .ticket-workspace-head,
  .ticket-workspace-actions,
  .hq-header,
  .hq-header-tools,
  .hq-profile,
  .card-head {
    flex-direction: column;
    align-items: stretch;
  }

  .ticket-filter-grid-wide {
    grid-template-columns: 1fr;
  }

  .command-body-grid-simple,
  .command-body-grid-simple.compact {
    grid-template-columns: 1fr;
  }

  .hq-ticket-summary-grid {
    grid-template-columns: 1fr;
  }

  .hq-ticket-meta-grid {
    grid-template-columns: 1fr;
  }

  .wallet-ticket-transfer-card {
    grid-template-columns: 1fr;
  }

  .registration-approval-card {
    grid-template-columns: 1fr;
  }

  .chat-bubble {
    width: 100%;
  }
}

/* HQ and support desk operational UX refresh */
.hq-page {
  --ops-primary: #1e3a5f;
  --ops-blue: #2563eb;
  --ops-green: #16a34a;
  --ops-bg: #f8fafc;
  --ops-surface: #ffffff;
  --ops-border: #d8e2ee;
  --ops-text: #0f172a;
  --ops-muted: #64748b;
}

.hq-main {
  gap: 16px;
}

.hq-sidebar {
  border-left: 1px solid rgba(203, 213, 225, 0.78);
}

.hq-nav-item,
.primary-btn,
.ghost-btn,
.link-btn,
.scope-chip,
.template-chip,
.ticket-thread,
.hq-mobile-menu-btn {
  touch-action: manipulation;
}

.hq-nav-item:focus-visible,
.primary-btn:focus-visible,
.ghost-btn:focus-visible,
.link-btn:focus-visible,
.scope-chip:focus-visible,
.template-chip:focus-visible,
.ticket-thread:focus-visible,
.hq-mobile-menu-btn:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.28);
  outline-offset: 3px;
}

.ticket-command-center {
  gap: 12px;
}

.ticket-modern-shell {
  border-radius: 22px;
  border-color: rgba(203, 213, 225, 0.86);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.055);
}

.ticket-workspace-head {
  padding: 16px 18px;
  align-items: flex-start;
}

.ticket-workspace-copy h3 {
  font-size: 21px;
  line-height: 1.5;
}

.ticket-workspace-actions {
  align-items: stretch;
}

.ticket-workspace-stat {
  border-radius: 16px;
  min-width: 96px;
}

.command-body-grid-simple,
.command-body-grid-simple.compact {
  grid-template-columns: minmax(320px, 390px) minmax(0, 1fr);
  gap: 14px;
  align-items: stretch;
}

.command-inbox-card,
.command-chat-card {
  padding: 18px;
}

.ticket-inbox-shell {
  position: sticky;
  top: 16px;
  max-height: calc(100dvh - 118px);
}

.ticket-filter-grid {
  gap: 10px;
}

.ticket-filter-grid input,
.ticket-filter-grid select,
.chat-head-actions select {
  min-height: 46px;
  border-radius: 14px;
}

.hq-ticket-scope-row {
  gap: 8px;
  overflow-x: auto;
  flex-wrap: nowrap;
  padding-bottom: 2px;
  scrollbar-width: none;
}

.hq-ticket-scope-row::-webkit-scrollbar {
  display: none;
}

.scope-chip {
  min-height: 38px;
  flex: 0 0 auto;
  border: 1px solid rgba(203, 213, 225, 0.62);
}

.quick-status-row {
  padding: 10px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.82);
  border: 1px solid rgba(226, 232, 240, 0.86);
}

.quick-status-row .scope-chip {
  min-height: 42px;
  font-size: 11px;
}

.ticket-list {
  gap: 10px;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.ticket-thread {
  border-radius: 18px;
  padding: 14px;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.ticket-thread.active {
  border-color: rgba(37, 99, 235, 0.38);
}

.ticket-thread-top strong,
.ticket-chat-title h3 {
  line-height: 1.55;
}

.ticket-chat-shell-rich {
  max-height: calc(100dvh - 118px);
  position: sticky;
  top: 16px;
}

.desk-detail-head {
  padding-bottom: 4px;
}

.hq-ticket-meta-grid {
  gap: 8px;
}

.hq-ticket-meta-card {
  border-radius: 15px;
  padding: 11px 12px;
}

.ticket-chat-actions {
  padding: 10px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.82);
  border: 1px solid rgba(226, 232, 240, 0.86);
}

.registration-approval-card,
.wallet-ticket-transfer-card,
.hq-ticket-attachments {
  border-radius: 18px;
}

.chat-stream {
  border-radius: 20px;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.chat-bubble {
  border-radius: 18px 18px 6px 18px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.chat-bubble.mine {
  border-radius: 18px 18px 18px 6px;
}

.ticket-chat-reply {
  border-radius: 20px;
}

.template-chip-row {
  gap: 8px;
}

.template-chip {
  min-height: 42px;
}

.chat-tools {
  align-items: stretch;
}

.chat-tools .primary-btn {
  min-height: 46px;
}

@media (max-width: 1280px) {
  .ticket-inbox-shell,
  .ticket-chat-shell-rich {
    position: static;
    max-height: none;
  }
}

@media (max-width: 760px) {
  .hq-page {
    background: linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
  }

  .hq-main {
    padding: 12px;
    gap: 12px;
  }

  .hq-header {
    position: sticky;
    top: 0;
    z-index: 20;
    margin: -12px -12px 0;
    padding: 12px;
    background: rgba(248, 250, 252, 0.94);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(226, 232, 240, 0.82);
  }

  .hq-header h1 {
    font-size: 22px;
    line-height: 1.45;
  }

  .hq-role-badge {
    width: fit-content;
  }

  .ticket-workspace-head,
  .command-inbox-card,
  .command-chat-card {
    padding: 14px;
    border-radius: 20px;
  }

  .ticket-workspace-copy h3 {
    font-size: 18px;
  }

  .ticket-workspace-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .ticket-workspace-actions .desk-refresh-btn {
    grid-column: 1 / -1;
    min-height: 44px;
  }

  .ticket-workspace-stat {
    min-width: 0;
  }

  .ticket-filter-grid-wide,
  .ticket-filter-grid-wide.compact {
    grid-template-columns: 1fr;
  }

  .ticket-filter-grid input,
  .ticket-filter-grid select,
  .chat-head-actions select,
  .chat-reply textarea {
    font-size: 16px;
  }

  .ticket-list {
    max-height: none;
    overflow: visible;
  }

  .ticket-thread {
    min-height: 130px;
    border-radius: 18px;
  }

  .ticket-chat-shell-rich,
  .support-ticket-mode .ticket-chat-shell-rich {
    display: grid;
    grid-template-rows: auto auto auto auto auto;
    gap: 12px;
    max-height: none;
  }

  .ticket-chat-head,
  .desk-ticket-chat-head {
    padding-bottom: 8px;
  }

  .hq-ticket-meta-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ticket-chat-actions,
  .quick-status-row {
    padding: 8px;
  }

  .quick-status-row {
    display: grid;
    grid-template-columns: 1fr;
  }

  .chat-stream,
  .hq-page.support-only .chat-stream {
    max-height: none;
    min-height: 220px;
    padding: 12px;
  }

  .chat-bubble {
    width: 100%;
    padding: 13px 14px;
  }

  .ticket-chat-reply {
    position: sticky;
    bottom: 0;
    margin: 0 -2px;
    padding: 12px;
    border-radius: 18px;
  }

  .template-chip-row,
  .template-chip-row.compact {
    display: flex;
    overflow-x: auto;
    gap: 8px;
    scrollbar-width: none;
  }

  .template-chip-row::-webkit-scrollbar,
  .template-chip-row.compact::-webkit-scrollbar {
    display: none;
  }

  .template-chip {
    flex: 0 0 auto;
    white-space: nowrap;
  }

  .chat-tools {
    display: grid;
    grid-template-columns: 1fr;
  }

  .internal-toggle {
    min-height: 44px;
  }
}

@media (max-width: 420px) {
  .hq-ticket-meta-grid,
  .ticket-workspace-actions {
    grid-template-columns: 1fr;
  }
}

/* HQ reports pro workspace */
.hq-report-pro {
  --report-ink: #0f172a;
  --report-muted: #64748b;
  --report-blue: #1e40af;
  --report-cyan: #0891b2;
  --report-amber: #d97706;
  --report-green: #15803d;
  --report-soft: rgba(248, 250, 252, 0.88);
  gap: 16px;
}

.report-command-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
  gap: 16px;
  padding: 22px;
  border-radius: 32px;
  background:
    radial-gradient(circle at 12% 10%, rgba(8, 145, 178, 0.18), transparent 28%),
    radial-gradient(circle at 90% 20%, rgba(217, 119, 6, 0.16), transparent 28%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 64, 175, 0.9));
  color: #fff;
  box-shadow: 0 28px 70px rgba(15, 23, 42, 0.18);
}

.report-command-copy h2 {
  margin: 10px 0;
  font-size: clamp(28px, 4vw, 46px);
  line-height: 1.35;
}

.report-command-copy p {
  max-width: 720px;
  margin: 0;
  color: rgba(255, 255, 255, 0.78);
  line-height: 2;
}

.report-command-metrics,
.share-split-grid,
.report-detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.report-command-metrics article {
  display: grid;
  gap: 8px;
  padding: 16px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

.report-command-metrics small,
.report-command-metrics span {
  color: rgba(255, 255, 255, 0.72);
}

.report-command-metrics strong {
  font-size: 24px;
  color: #fff;
}

.report-workspace-tabs,
.hq-share-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px;
  border-radius: 24px;
  background: rgba(226, 232, 240, 0.58);
}

.report-workspace-tabs button,
.hq-share-tabs button {
  min-height: 44px;
  border: 0;
  border-radius: 18px;
  padding: 10px 16px;
  background: transparent;
  color: var(--report-muted);
  cursor: pointer;
  font-weight: 800;
  transition: background .2s ease, color .2s ease, box-shadow .2s ease, transform .2s ease;
}

.report-workspace-tabs button.active,
.hq-share-tabs button.active {
  background: #fff;
  color: var(--report-blue);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}

.report-workspace-tabs button:hover,
.hq-share-tabs button:hover {
  transform: translateY(-1px);
}

.report-workspace-tabs button:focus-visible,
.hq-share-tabs button:focus-visible,
.tenant-report-item:focus-visible {
  outline: 3px solid rgba(30, 64, 175, 0.24);
  outline-offset: 3px;
}

.report-control-deck {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 0.6fr) minmax(220px, 0.4fr);
  gap: 12px;
  align-items: end;
  padding: 14px;
  border-radius: 28px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(241, 245, 249, 0.92));
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.055);
}

.report-filters.compact {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
}

.report-period-card.compact {
  height: 100%;
  margin: 0;
}

.share-card,
.report-focus-card {
  display: grid;
  gap: 10px;
  padding: 18px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.06);
}

.share-card small,
.report-focus-card small {
  color: var(--report-muted);
  font-weight: 800;
}

.share-card strong,
.report-focus-card strong {
  font-size: 26px;
  color: var(--report-ink);
}

.share-card p,
.report-focus-card p {
  margin: 0;
  color: var(--report-muted);
  line-height: 1.9;
}

.share-card.hq {
  background: linear-gradient(135deg, rgba(219, 234, 254, 0.9), rgba(255, 255, 255, 0.92));
}

.share-card.rah {
  background: linear-gradient(135deg, rgba(220, 252, 231, 0.9), rgba(255, 255, 255, 0.92));
}

.share-card.neutral {
  background: linear-gradient(135deg, rgba(254, 243, 199, 0.9), rgba(255, 255, 255, 0.92));
}

.report-detail-grid {
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.5fr);
}

.table-section-title,
.tenant-report-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
}

.table-section-title h3,
.tenant-report-head h3 {
  margin: 0;
}

.rich-table {
  overflow: auto;
  border: 0;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.86);
}

.rich-table table {
  min-width: 920px;
}

.rich-table th {
  color: #334155;
  font-weight: 900;
}

.rich-table td,
.rich-table th {
  padding: 12px 14px;
}

.direction-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 70px;
  border-radius: 999px;
  padding: 7px 10px;
  font-weight: 900;
  font-size: 11px;
}

.direction-pill.in {
  background: rgba(21, 128, 61, 0.12);
  color: #166534;
}

.direction-pill.out {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}

.tenant-report-layout {
  display: grid;
  grid-template-columns: 310px minmax(0, 1fr);
  gap: 16px;
}

.tenant-report-list {
  position: sticky;
  top: 16px;
  align-self: start;
  display: grid;
  gap: 10px;
  max-height: calc(100dvh - 150px);
  overflow: auto;
  padding: 12px;
  border-radius: 28px;
  background: rgba(241, 245, 249, 0.86);
}

.tenant-report-item {
  display: grid;
  gap: 6px;
  width: 100%;
  min-height: 66px;
  border: 0;
  border-radius: 20px;
  padding: 13px 14px;
  background: rgba(255, 255, 255, 0.76);
  color: var(--report-ink);
  text-align: right;
  cursor: pointer;
  transition: background .2s ease, box-shadow .2s ease, transform .2s ease;
}

.tenant-report-item span {
  color: var(--report-muted);
  font-size: 12px;
}

.tenant-report-item.active {
  background: linear-gradient(135deg, #1e40af, #0891b2);
  color: #fff;
  box-shadow: 0 18px 42px rgba(30, 64, 175, 0.22);
}

.tenant-report-item.active span {
  color: rgba(255, 255, 255, 0.78);
}

.tenant-report-main {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.tenant-kpis {
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
}

.hq-share-tabs.compact {
  background: rgba(241, 245, 249, 0.82);
}

.network-tabs {
  margin: 0;
}

@media (prefers-reduced-motion: reduce) {
  .report-workspace-tabs button,
  .hq-share-tabs button,
  .tenant-report-item {
    transition: none;
  }

  .report-workspace-tabs button:hover,
  .hq-share-tabs button:hover {
    transform: none;
  }
}

@media (max-width: 1280px) {
  .report-command-hero,
  .report-control-deck,
  .tenant-report-layout {
    grid-template-columns: 1fr;
  }

  .tenant-report-list {
    position: static;
    max-height: none;
  }

  .tenant-kpis {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .report-command-hero {
    padding: 16px;
    border-radius: 24px;
  }

  .report-command-metrics,
  .share-split-grid,
  .report-detail-grid,
  .tenant-kpis {
    grid-template-columns: 1fr;
  }

  .report-workspace-tabs,
  .hq-share-tabs {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .report-workspace-tabs::-webkit-scrollbar,
  .hq-share-tabs::-webkit-scrollbar {
    display: none;
  }

  .report-workspace-tabs button,
  .hq-share-tabs button {
    flex: 0 0 auto;
    white-space: nowrap;
  }

  .report-filters.compact {
    grid-template-columns: 1fr;
  }

  .table-section-title,
  .tenant-report-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
