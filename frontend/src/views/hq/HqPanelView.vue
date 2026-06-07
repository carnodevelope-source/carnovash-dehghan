<template>
  <div class="hq-page" dir="rtl">
    <div class="hq-bg hq-bg-one"></div>
    <div class="hq-bg hq-bg-two"></div>

    <aside class="hq-sidebar">
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
          @click="activeTab = tab.key"
        >
          <span class="hq-nav-title">{{ tab.label }}</span>
          <span class="hq-nav-meta">{{ tab.meta }}</span>
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
      <header class="hq-header">
        <div>
          <p class="hq-kicker">مرکز کنترل پلتفرم</p>
          <h1>{{ currentTabTitle }}</h1>
        </div>
        <div class="hq-header-tools">
          <span class="hq-role-badge">{{ authStore.isHqAdmin ? 'HQ Admin' : 'HQ Support' }}</span>
          <button v-if="activeTab === 'overview'" type="button" class="primary-btn" @click="loadOverview">به‌روزرسانی</button>
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

      <section v-else-if="activeTab === 'carwashes'" class="workspace-grid">
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
                    <strong>{{ row.name }}</strong>
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

      <section v-else-if="activeTab === 'tickets'" class="ticket-center">
        <article class="ticket-list-shell">
          <div class="card-head">
            <h3>مرکز تیکت</h3>
            <span>{{ tickets.length.toLocaleString('fa-IR') }} گفتگو</span>
          </div>
          <div class="ticket-filter-grid ticket-filter-grid-wide">
            <input v-model.trim="ticketQuery" placeholder="جستجو در عنوان، متن، نام کارواش یا کاربر..." @input="loadTickets" />
            <select v-model="ticketStatus" @change="loadTickets">
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
            <select v-model="ticketTenantId" @change="loadTickets">
              <option value="">همه کارواش‌ها</option>
              <option v-for="item in carwashes" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
          </div>
          <div class="ticket-list">
            <button
              v-for="item in tickets"
              :key="item.id"
              type="button"
              class="ticket-thread"
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
            </button>
          </div>
        </article>

        <article class="ticket-chat-shell" v-if="selectedTicket">
          <div class="chat-head">
            <div>
              <h3>{{ selectedTicket.subject }}</h3>
              <p>{{ selectedTicket.tenant_name }} | {{ selectedTicket.created_by_name }}</p>
            </div>
            <div class="chat-head-badges">
              <span class="meta-chip">{{ categoryLabel(selectedTicket.category) }}</span>
              <span class="meta-chip">{{ priorityLabel(selectedTicket.priority) }}</span>
              <span class="ticket-mini-status" :class="`ticket-${selectedTicket.status}`">{{ statusLabel(selectedTicket.status) }}</span>
            </div>
          </div>

          <div class="chat-head-actions">
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

          <div class="chat-stream">
            <div
              v-for="message in selectedTicket.messages"
              :key="message.id"
              class="chat-bubble"
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

          <div class="chat-reply">
            <textarea v-model.trim="ticketReply.body" placeholder="پاسخ کامل، دقیق و حرفه‌ای بنویس..." />
            <div class="chat-tools">
              <label v-if="authStore.isHqAdmin" class="internal-toggle">
                <input v-model="ticketReply.is_internal" type="checkbox" />
                <span>یادداشت داخلی</span>
              </label>
              <button type="button" class="primary-btn" @click="sendTicketReply">ارسال پاسخ</button>
            </div>
          </div>
        </article>

        <article v-else class="ticket-placeholder">
          <strong>یک تیکت را انتخاب کن</strong>
          <span>گفتگو، ارجاع، وضعیت و تاریخچه کامل از اینجا مدیریت می‌شود.</span>
        </article>
      </section>

      <section v-else-if="activeTab === 'team'" class="workspace-grid">
        <article class="glass-card create-card">
          <div class="card-head">
            <h3>افزودن پشتیبان ساده</h3>
            <span>دسترسی: کارواش‌ها + تیکت‌ها</span>
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
              <input v-model="supportForm.password" type="password" required placeholder="حداقل 6 کاراکتر" />
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
              </div>
            </div>
          </div>
        </article>
      </section>

      <section v-else class="glass-card report-shell">
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../services/api'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import { useAuthStore } from '../../store/auth.store'
import { formatJalaliDate } from '../../utils/date'
import { formatThousandsToman } from '../../utils/money'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('overview')
const tabs = [
  { key: 'overview', label: 'داشبورد مرکزی', meta: 'نمای کل' },
  { key: 'carwashes', label: 'کارواش‌ها', meta: 'ثبت و نظارت' },
  { key: 'tickets', label: 'مرکز تیکت', meta: 'پاسخ چت‌محور' },
  { key: 'team', label: 'تیم مرکزی', meta: 'ساخت پشتیبان' },
  { key: 'reports', label: 'گزارشات', meta: 'تحلیل تاریخی و مالی' }
]

const visibleTabs = computed(() => tabs.filter((tab) => {
  if (tab.key === 'reports' || tab.key === 'team') return authStore.isHqAdmin
  return true
}))
const currentTabTitle = computed(() => visibleTabs.value.find((tab) => tab.key === activeTab.value)?.label || 'پنل مرکزی')

const overview = reactive({ summary: {}, recent_carwashes: [], recent_tickets: [] })

const carwashes = ref([])
const carwashQuery = ref('')
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
const ticketReply = reactive({
  body: '',
  status: '',
  assign_to_user_id: 0,
  is_internal: false
})

const reports = reactive({ summary: {}, rows: [], trends: [], highlights: {} })
const reportTab = ref('revenue')
const reportTabs = [
  { key: 'revenue', label: 'گزارش درآمد' },
  { key: 'wallet', label: 'گزارش کیف پول' }
]
const reportRangeOptions = [
  { key: 'day', label: 'روز' },
  { key: 'week', label: 'هفته' },
  { key: 'month', label: 'ماه' },
  { key: 'all', label: 'کل بازه تاریخی' }
]
const reportFilter = reactive({ rangeKey: 'month', start: '', end: '' })

const hqTeam = ref([])
const supportFormError = ref('')
const supportForm = reactive({
  first_name: '',
  last_name: '',
  username: '',
  phone: '',
  password: ''
})

const filteredCarwashes = computed(() => {
  const query = carwashQuery.value.trim().toLowerCase()
  if (!query) return carwashes.value
  return carwashes.value.filter((item) => {
    const haystack = `${item.name} ${item.address || ''} ${item.manager?.full_name || ''} ${item.manager?.phone || ''}`.toLowerCase()
    return haystack.includes(query)
  })
})

const teamAssignable = computed(() => hqTeam.value.filter((item) => ['hq_admin', 'hq_support'].includes(item.platform_role)))
const reportRows = computed(() => {
  const items = Array.isArray(reports.rows) ? [...reports.rows] : []
  if (reportTab.value === 'wallet') {
    return items.sort((a, b) => Number(b.wallet_balance || 0) - Number(a.wallet_balance || 0))
  }
  return items.sort((a, b) => Number(b.paid_amount || 0) - Number(a.paid_amount || 0))
})
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

const loadOverview = async () => {
  const { data } = await api.get('/auth/hq/overview/')
  overview.summary = data?.summary || {}
  overview.recent_carwashes = data?.recent_carwashes || []
  overview.recent_tickets = data?.recent_tickets || []
}

const loadCarwashes = async () => {
  const { data } = await api.get('/auth/hq/carwashes/')
  carwashes.value = Array.isArray(data) ? data : []
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
  await loadOverview()
}

const toggleCarwashState = async (row) => {
  await api.patch(`/auth/hq/carwashes/${row.id}/`, { is_active: !row.is_active })
  await loadCarwashes()
  await loadOverview()
}

const loadTickets = async () => {
  if (!carwashes.value.length) await loadCarwashes()
  const { data } = await api.get('/auth/hq/tickets/', {
    params: {
      q: ticketQuery.value || undefined,
      status: ticketStatus.value,
      priority: ticketPriority.value,
      tenant_id: ticketTenantId.value || undefined
    }
  })
  tickets.value = Array.isArray(data) ? data : []
  if (selectedTicket.value?.id) {
    const stillExists = tickets.value.some((item) => item.id === selectedTicket.value.id)
    if (stillExists) await selectTicket(selectedTicket.value.id)
    else selectedTicket.value = null
  }
}

const selectTicket = async (ticketId) => {
  const { data } = await api.get(`/auth/hq/tickets/${ticketId}/`)
  selectedTicket.value = data
  ticketReply.body = ''
  ticketReply.status = ''
  ticketReply.assign_to_user_id = Number(data?.assigned_to || 0)
  ticketReply.is_internal = false
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
}

const loadTeam = async () => {
  const { data } = await api.get('/auth/hq/team/')
  hqTeam.value = Array.isArray(data) ? data : []
}

const createSupportUser = async () => {
  supportFormError.value = ''
  try {
    await api.post('/auth/hq/team/', { ...supportForm })
    Object.assign(supportForm, {
      first_name: '',
      last_name: '',
      username: '',
      phone: '',
      password: ''
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

const logout = async () => {
  await authStore.logout()
  await router.push('/login')
}

watch(activeTab, async (tab) => {
  if ((tab === 'team' || tab === 'reports') && !authStore.isHqAdmin) {
    activeTab.value = 'overview'
    return
  }
  if (tab === 'overview') await loadOverview()
  if (tab === 'carwashes') await loadCarwashes()
  if (tab === 'tickets') await loadTickets()
  if (tab === 'team' && authStore.isHqAdmin) await loadTeam()
  if (tab === 'reports' && authStore.isHqAdmin) await loadReports()
})

watch(() => [reportFilter.start, reportFilter.end], async () => {
  if (activeTab.value === 'reports' && authStore.isHqAdmin) await loadReports()
})

onMounted(async () => {
  await loadOverview()
  await loadCarwashes()
  if (authStore.isHqAdmin) await loadTeam()
  setReportRange('month')
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
  --bg-card: rgba(255, 255, 255, 0.82);
  --bg-soft: rgba(255, 255, 255, 0.58);
  --line: rgba(148, 163, 184, 0.22);
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
  background: rgba(255, 255, 255, 0.74);
  backdrop-filter: blur(16px);
  border-left: 1px solid var(--line);
  z-index: 2;
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
  transition: 0.2s ease;
}

.hq-nav-item:hover,
.hq-nav-item.active {
  background: linear-gradient(135deg, rgba(15, 93, 215, 0.14), rgba(14, 165, 233, 0.1));
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
}

.hq-nav-title {
  font-weight: 700;
}

.hq-nav-meta {
  color: var(--muted);
  font-size: 12px;
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
  padding: 26px;
  display: grid;
  gap: 18px;
  position: relative;
  z-index: 1;
}

.hq-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
}

.hq-kicker {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--muted);
}

.hq-header h1 {
  margin: 0;
  font-size: 34px;
  font-weight: 800;
}

.hq-header-tools {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hq-role-badge,
.meta-chip {
  border-radius: 999px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
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
  border: 1px solid var(--line);
  border-radius: 26px;
  backdrop-filter: blur(18px);
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.06);
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
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 20px;
  padding: 14px 16px;
  display: grid;
  gap: 5px;
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

.create-card,
.table-card,
.report-shell {
  padding: 20px;
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
.ticket-filter-grid input,
.ticket-filter-grid select,
.table-search,
.chat-head-actions select,
.report-filters input,
.chat-reply textarea {
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(255, 255, 255, 0.82);
  border-radius: 14px;
  padding: 0 12px;
  font: inherit;
  color: var(--text);
}

.form-grid input,
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
}

.ticket-list-shell,
.ticket-chat-shell,
.ticket-placeholder {
  padding: 20px;
  min-height: 0;
}

.ticket-filter-grid {
  display: grid;
  gap: 10px;
  margin: 12px 0 14px;
}

.ticket-filter-grid-wide {
  grid-template-columns: 1.2fr 0.8fr 0.8fr 0.8fr;
}

.ticket-list {
  display: grid;
  gap: 10px;
  max-height: calc(100vh - 320px);
  overflow: auto;
}

.ticket-thread {
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.78);
  border-radius: 20px;
  padding: 14px;
  text-align: right;
  cursor: pointer;
  display: grid;
  gap: 8px;
}

.ticket-thread.active {
  border-color: rgba(15, 93, 215, 0.35);
  background: linear-gradient(135deg, rgba(15, 93, 215, 0.1), rgba(14, 165, 233, 0.08));
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
}

.ticket-thread p,
.chat-head p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.ticket-thread-meta {
  color: var(--muted);
  font-size: 12px;
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
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
}

.chat-head h3 {
  margin: 0 0 5px;
  font-size: 20px;
}

.chat-stream {
  min-height: 0;
  max-height: calc(100vh - 420px);
  overflow: auto;
  display: grid;
  gap: 12px;
  padding: 18px 0;
}

.chat-bubble {
  width: min(82%, 560px);
  border-radius: 22px 22px 8px 22px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.18);
  display: grid;
  gap: 8px;
}

.chat-bubble.mine {
  margin-right: auto;
  border-radius: 22px 22px 22px 8px;
  background: linear-gradient(135deg, rgba(15, 93, 215, 0.12), rgba(14, 165, 233, 0.08));
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
  font-size: 12px;
}

.chat-bubble p {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.9;
}

.chat-bubble small {
  color: var(--muted);
}

.chat-reply {
  border-top: 1px solid rgba(226, 232, 240, 0.9);
  padding-top: 14px;
  display: grid;
  gap: 12px;
}

.chat-reply textarea {
  min-height: 120px;
  padding: 12px;
  resize: vertical;
}

.internal-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
}

.ticket-placeholder {
  display: grid;
  place-items: center;
  text-align: center;
  gap: 8px;
  color: var(--muted);
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
  .report-top-grid,
  .report-body-grid {
    grid-template-columns: 1fr;
  }

  .report-kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .report-insight-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hq-main,
  .hq-sidebar {
    padding: 16px;
  }

  .hero-card,
  .form-grid,
  .ticket-filter-grid,
  .team-grid,
  .report-kpi-grid,
  .report-side-stats,
  .report-glance-strip {
    grid-template-columns: 1fr;
  }

  .team-metrics {
    grid-template-columns: 1fr;
  }

  .chat-head,
  .chat-head-actions,
  .chat-head-badges,
  .hq-header {
    flex-direction: column;
    align-items: stretch;
  }

  .chat-bubble {
    width: 100%;
  }
}
</style>
