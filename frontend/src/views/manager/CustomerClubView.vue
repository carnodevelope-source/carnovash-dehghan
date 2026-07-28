<template>
  <AppShell
    title="باشگاه مشتریان"
    subtitle="مدیریت مشتریان، گروه‌بندی هوشمند و ارتباط هدفمند"
    :show-search="true"
    search-placeholder="جستجو با نام، موبایل یا پلاک..."
    :search-query="searchQuery"
    @update:search-query="searchQuery = $event"
  >
    <template #header-actions>
      <button type="button" class="club-ghost-btn btn-with-icon" @click="exportCustomers"><IconlyIcon name="document" size="sm" />خروجی اکسل</button>
      <button type="button" class="club-ghost-btn btn-with-icon" @click="openCustomerImportModal"><IconlyIcon name="paperPlus" size="sm" />وارد کردن مشتریان</button>
      <button type="button" class="club-primary-btn btn-with-icon" @click="openGroupBuilder"><IconlyIcon name="plus" size="sm" />ساخت گروه جدید</button>
    </template>

    <div class="club-page">
      <section class="club-hero">
        <div class="club-hero-copy">
          <span class="club-kicker">CRM Suite</span>
          <h2>باشگاه مشتریان {{ authStore.user?.tenant_name || 'کارواش' }}</h2>
          <p>
            نمای ساده برای دیدن و گروه‌بندی مشتری‌ها، و نمای پیشرفته برای ارسال پیامک‌های هدفمند،
            پایش اعتبار و ذخیره گزارش کامل ارسال‌ها.
          </p>
        </div>

        <div class="club-hero-actions">
          <div class="mode-switch">
            <button type="button" :class="{ active: activePlan === 'simple' }" @click="activePlan = 'simple'">
              <span>ساده</span>
              <HelpTip :text="sectionHelpByPage.customerClub.simple" />
            </button>
            <button type="button" :class="{ active: activePlan === 'advanced' }" @click="openAdvancedPlan">
              <span>پیشرفته</span>
              <HelpTip :text="sectionHelpByPage.customerClub.advanced" />
            </button>
          </div>

          <button
            v-if="activePlan === 'advanced'"
            type="button"
            class="club-secondary-btn btn-with-icon"
            :disabled="!filteredCustomers.length"
            @click="openPrimaryGroupSmsComposer"
          >
            <IconlyIcon name="message" size="sm" />
            ارسال پیامک گروهی
          </button>
        </div>
      </section>

      <section class="club-stats-grid">
        <article class="club-stat-card tone-blue">
          <small>کل مشتریان</small>
          <strong>{{ toFa(customers.length) }}</strong>
          <span>{{ activeCarwashCountLabel }}</span>
        </article>
        <article class="club-stat-card tone-teal">
          <small>مشتریان فعال</small>
          <strong>{{ toFa(activeCustomersCount) }}</strong>
          <span>دارای حداقل ۲ سفارش</span>
        </article>
        <article class="club-stat-card tone-violet">
          <small>گروه‌های سفارشی</small>
          <strong>{{ toFa(customGroups.length) }}</strong>
          <span>گروه پیش‌فرض کارواش همیشه فعال است</span>
        </article>
        <article class="club-stat-card tone-amber">
          <small>{{ activePlan === 'advanced' ? 'اعتبار پیامک' : 'میانگین امتیاز' }}</small>
          <strong>{{ activePlan === 'advanced' ? money(smsCreditBalance) : toFaDecimal(averageScore) }}</strong>
          <span>
            {{ activePlan === 'advanced' ? smsCreditStateLabel : 'بر اساس امتیاز مشتری‌ها' }}
          </span>
        </article>
      </section>

      <section class="club-filter-shell">
        <div class="club-filter-grid">
          <label class="filter-field">
            <span>گروه‌بندی</span>
            <select v-model="filters.groupId">
              <option value="">همه مشتریان</option>
              <option v-for="group in availableGroups" :key="group.id" :value="String(group.id)">{{ group.name }}</option>
            </select>
          </label>

          <label class="filter-field">
            <span>حداقل سفارش</span>
            <input v-model.number="filters.minOrders" type="number" min="0" placeholder="مثلا ۵" />
          </label>

          <label class="filter-field">
            <span>حداقل جمع خرید</span>
            <input :value="moneyInputValue(filters.minSpent)" type="text" inputmode="numeric" placeholder="تومان" @input="filters.minSpent = parseMoneyInput($event.target.value)" />
          </label>

          <label class="filter-field">
            <span>حداقل امتیاز</span>
            <input v-model.number="filters.minScore" type="number" min="0" max="5" step="0.1" placeholder="از ۵" />
          </label>

          <label class="filter-field">
            <span>مرتب‌سازی</span>
            <select v-model="filters.sortBy">
              <option value="spent">جمع مبلغ خرید</option>
              <option value="orders">تعداد سفارش</option>
              <option value="score">امتیاز</option>
              <option value="recent">آخرین سفارش</option>
              <option value="name">نام مشتری</option>
            </select>
          </label>
        </div>

        <div class="grouping-toolbar">
          <div class="grouping-mode">
            <button type="button" :class="{ active: groupingMode === 'tenant' }" @click="groupingMode = 'tenant'">گروه‌بندی بر اساس کارواش</button>
            <button type="button" :class="{ active: groupingMode === 'custom' }" @click="groupingMode = 'custom'">گروه‌های سفارشی</button>
          </div>

          <div class="grouping-chips">
            <button
              v-for="group in customGroups"
              :key="group.id"
              type="button"
              class="group-chip"
              @click="highlightGroup(group.id)"
            >
              {{ group.name }}
              <small>{{ toFa(resolveGroupMembers(group).length) }}</small>
            </button>
          </div>
        </div>
      </section>

      <div class="club-body" :class="{ advanced: activePlan === 'advanced' }">
        <section class="club-main-col">
          <article
            v-for="section in visibleSections"
            :key="section.key"
            class="customer-section"
            :class="{ highlighted: highlightedGroupId === section.sourceGroupId }"
          >
            <header class="customer-section-head">
              <div>
                <h3>{{ section.title }}</h3>
                <p>{{ section.description }}</p>
              </div>

              <div class="customer-section-actions">
                <span class="section-count">{{ toFa(section.customers.length) }} مشتری</span>
                <button
                  v-if="activePlan === 'advanced' && section.customers.length"
                  type="button"
                  class="club-inline-btn"
                  @click="openSmsComposer(section.sourceGroupId ? { type: 'group', group: groupById(section.sourceGroupId) } : { type: 'section', section })"
                >
                  ارسال پیامک
                </button>
              </div>
            </header>

            <div v-if="section.customers.length" class="customer-table-wrap">
              <table class="customer-table">
                <thead>
                  <tr>
                    <th>نام مشتری</th>
                    <th>شماره موبایل</th>
                    <th>نام کارواش</th>
                    <th>جمع مبلغ خرید</th>
                    <th>امتیاز</th>
                    <th>عملیات</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="customer in section.customers" :key="customer.key">
                    <td>
                      <div class="customer-name-cell">
                        <span class="avatar-badge">{{ initials(customer.name) }}</span>
                        <div>
                          <strong>{{ customer.name }}</strong>
                          <PlateBadge
                            v-if="customer.primary_plate"
                            :plate-number="customer.primary_plate"
                            :plate-left="customer.primary_plate_left"
                            :plate-letter="customer.primary_plate_letter"
                            :plate-mid="customer.primary_plate_mid"
                            :plate-right="customer.primary_plate_right"
                            :plate-type="customer.primary_plate_type || 'car'"
                            compact
                          />
                          <small v-else>بدون پلاک ثبت‌شده</small>
                        </div>
                      </div>
                    </td>
                    <td class="mono-cell">{{ customer.phone || '-' }}</td>
                    <td>{{ customer.carwash_name }}</td>
                    <td>{{ money(customer.total_spent) }}</td>
                    <td>
                      <span class="score-pill">
                        {{ toFaDecimal(customer.score) }}
                        <span>★</span>
                      </span>
                    </td>
                    <td>
                      <div class="table-actions">
                        <button type="button" class="icon-action icon-only-action" title="مشاهده" aria-label="مشاهده" @click="openCustomerDetail(customer)">
                          <img :src="actionIcons.view" alt="" class="action-icon-image" />
                        </button>
                        <button
                          type="button"
                          class="icon-action icon-only-action"
                          title="گروه"
                          aria-label="گروه"
                          @click="handleGroupAction(customer)"
                        >
                          <img :src="actionIcons.group" alt="" class="action-icon-image" />
                        </button>
                        <button
                          v-if="activePlan === 'advanced'"
                          type="button"
                          class="icon-action primary icon-only-action"
                          title="پیامک"
                          aria-label="پیامک"
                          @click="openSmsComposer({ type: 'customer', customer })"
                        >
                          <img :src="actionIcons.sms" alt="" class="action-icon-image" />
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-else class="empty-state">
              <strong>مشتری‌ای در این گروه دیده نشد</strong>
              <span>فیلترها را تغییر دهید یا گروه تازه‌ای بسازید.</span>
            </div>
          </article>
        </section>

        <aside v-if="activePlan === 'advanced'" class="club-side-col">
          <article class="side-card hero-side-card">
            <div class="side-card-head">
              <h4>مرکز پیامک</h4>
              <span>{{ smsCreditStateLabel }}</span>
            </div>
            <div class="sms-credit-panel">
              <strong>{{ money(smsCreditBalance) }}</strong>
              <p>اعتبار کیف پول پیامک برای ارسال کمپین‌های تکی و گروهی.</p>
            </div>
            <div class="side-metrics">
              <div>
                <small>موفق</small>
                <strong>{{ toFa(smsStatusCount.success) }}</strong>
              </div>
              <div>
                <small>در انتظار</small>
                <strong>{{ toFa(smsStatusCount.pending) }}</strong>
              </div>
              <div>
                <small>ناموفق</small>
                <strong>{{ toFa(smsStatusCount.failed) }}</strong>
              </div>
            </div>
          </article>

          <article class="side-card">
            <div class="side-card-head">
              <h4>پیشنهاد هوشمند</h4>
              <span>AI Hint</span>
            </div>
            <div class="suggestion-list">
              <button type="button" class="suggestion-item" @click="applySuggestedRule('vip')">
                <strong>مشتریان وفادار</strong>
                <small>بالای ۵ سفارش و امتیاز بیشتر از ۴</small>
              </button>
              <button type="button" class="suggestion-item" @click="applySuggestedRule('at-risk')">
                <strong>مشتریان در معرض ریزش</strong>
                <small>کمتر از ۲ سفارش در بازه اخیر و خرید پایین</small>
              </button>
            </div>
          </article>

          <article class="side-card">
            <div class="side-card-head">
              <h4>قالب‌های سریع</h4>
              <button type="button" class="club-inline-btn" @click="openTemplateEditor()">مدیریت</button>
            </div>
            <div class="template-list">
              <button v-for="template in smsTemplates" :key="template.id" type="button" class="template-item template-preview-item" @click="openTemplateEditor(template)">
                <strong>{{ template.title }}</strong>
                <small>{{ previewTemplateBody(template.body) }}</small>
              </button>
            </div>
          </article>

          <article class="side-card log-card">
            <div class="side-card-head">
              <h4>گزارش پیامک‌ها</h4>
              <span>{{ toFa(smsLogs.length) }} رکورد</span>
            </div>
            <div v-if="smsLogs.length" class="sms-log-list sms-log-scroll">
              <div v-for="log in smsLogs" :key="log.id" class="sms-log-row">
                <div class="sms-log-main">
                  <div class="sms-log-head">
                    <strong>{{ log.recipient_name || log.phone || 'گیرنده نامشخص' }}</strong>
                    <small>{{ log.target_label || log.phone || 'بدون برچسب' }}</small>
                  </div>
                  <p class="sms-log-message">{{ logMessageText(log) }}</p>
                  <div class="sms-log-meta">
                    <span>{{ log.phone || 'بدون شماره' }}</span>
                    <span>{{ date(log.created_at) }}</span>
                  </div>
                  <p v-if="log.provider_response" class="sms-log-response">{{ log.provider_response }}</p>
                </div>
                <span class="status-badge" :class="log.status">{{ smsStatusLabel(log.status) }}</span>
              </div>
            </div>
            <p v-else class="empty-inline">هنوز گزارشی ثبت نشده است.</p>
          </article>
        </aside>
      </div>
    </div>

    <div v-if="customerImport.open" class="overlay" @click.self="closeCustomerImportModal">
      <section class="modal-card customer-import-modal">
        <header class="modal-head">
          <div>
            <p class="modal-kicker">وارد کردن مشتریان</p>
            <h3>{{ customerImport.confirming ? 'تایید هزینه واردات' : 'بارگذاری فایل اکسل مشتریان' }}</h3>
          </div>
          <button type="button" class="icon-close" @click="closeCustomerImportModal">×</button>
        </header>

        <div v-if="!customerImport.confirming" class="customer-import-layout">
          <section class="import-guide-panel">
            <h4>ساختار فایل</h4>
            <p>ابتدا فایل نمونه را دانلود کنید و اطلاعات مشتریان را با همین ستون‌ها وارد کنید. ستون شماره تلفن الزامی است و باید با 09 شروع شود.</p>
            <div class="import-columns">
              <span>نام مشتری</span>
              <span>شماره تلفن</span>
              <span>پلاک</span>
              <span>مدل خودرو</span>
              <span>رنگ خودرو</span>
              <span>توضیحات</span>
            </div>
            <button type="button" class="club-secondary-btn btn-with-icon" :disabled="customerImport.downloadingTemplate" @click="downloadCustomerImportTemplate">
              <IconlyIcon name="document" size="sm" />
              {{ customerImport.downloadingTemplate ? 'در حال دریافت...' : 'دانلود تمپلیت اکسل' }}
            </button>
          </section>

          <section class="import-upload-panel">
            <label class="import-dropzone">
              <input ref="customerImportFileRef" type="file" accept=".xlsx" @change="handleCustomerImportFile" />
              <strong>{{ customerImport.fileName || 'فایل اکسل را انتخاب کنید' }}</strong>
              <span>بعد از انتخاب فایل، ۵ ردیف اول برای بررسی نمایش داده می‌شود.</span>
              <span>هزینه فقط هنگام تایید نهایی از کیف پول اصلی کسر می‌شود.</span>
            </label>
            <button type="button" class="club-primary-btn" :disabled="!customerImport.file || customerImport.previewing" @click="previewCustomerImport">
              {{ customerImport.previewing ? 'در حال بررسی...' : 'نمایش پیش‌نمایش' }}
            </button>
          </section>
        </div>

        <div v-if="!customerImport.confirming && customerImport.preview.length" class="import-preview-panel">
          <div class="side-card-head">
            <h4>پیش‌نمایش ۵ ردیف اول</h4>
            <span>{{ toFa(customerImport.validCount) }} ردیف معتبر</span>
          </div>
          <div class="customer-table-wrap import-preview-table-wrap">
            <table class="customer-table import-preview-table">
              <thead>
                <tr>
                  <th>نام</th>
                  <th>شماره تلفن</th>
                  <th>پلاک</th>
                  <th>مدل خودرو</th>
                  <th>رنگ</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in customerImport.preview" :key="`${row.row}-${row.phone}`">
                  <td>{{ row.full_name }}</td>
                  <td class="mono-cell">{{ row.phone }}</td>
                  <td>{{ row.plate_number || '-' }}</td>
                  <td>{{ row.car_model || '-' }}</td>
                  <td>{{ row.car_color || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="customerImport.errors.length" class="import-errors">
            <strong>{{ toFa(customerImport.errorCount) }} خطا در فایل پیدا شد</strong>
            <p v-for="error in customerImport.errors" :key="`${error.row}-${error.message}`">ردیف {{ toFa(error.row) }}: {{ error.message }}</p>
          </div>
        </div>

        <div v-if="customerImport.confirming" class="import-payment-panel">
          <strong>{{ money(customerImport.price) }}</strong>
          <p>هزینه هر تبدیل اکسل {{ money(customerImport.price) }} است و فقط هنگام تایید نهایی از کیف پول اصلی کسر می‌شود. بعد از کسر هزینه، {{ toFa(customerImport.validCount) }} مشتری در باشگاه مشتریان اضافه یا به‌روزرسانی می‌شود.</p>
        </div>

        <footer class="modal-foot">
          <button type="button" class="club-ghost-btn" @click="closeCustomerImportModal">انصراف</button>
          <button
            v-if="customerImport.preview.length && !customerImport.confirming"
            type="button"
            class="club-primary-btn"
            :disabled="customerImport.errorCount > 0 || customerImport.validCount <= 0"
            @click="customerImport.confirming = true"
          >
            تایید پیش‌نمایش
          </button>
          <button
            v-if="customerImport.confirming"
            type="button"
            class="club-primary-btn"
            :disabled="customerImport.submitting"
            @click="confirmCustomerImport"
          >
            {{ customerImport.submitting ? 'در حال ثبت...' : 'تایید و کسر از کیف پول' }}
          </button>
        </footer>
      </section>
    </div>

    <div v-if="groupBuilder.open" class="overlay" @click.self="closeGroupBuilder">
      <section class="modal-card group-builder-modal">
        <header class="modal-head">
          <div>
            <p class="modal-kicker">ساخت گروه جدید</p>
            <h3>دسته‌بندی دستی یا هوشمند مشتری‌ها</h3>
          </div>
          <button type="button" class="icon-close" @click="closeGroupBuilder">×</button>
        </header>

        <div class="group-builder-layout">
          <div class="group-builder-form">
            <label class="filter-field">
              <span>نام گروه</span>
              <input v-model.trim="groupBuilder.name" type="text" placeholder="مثلا مشتریان وفادار VIP" />
            </label>

            <label class="filter-field">
              <span>توضیح</span>
              <textarea v-model.trim="groupBuilder.description" rows="3" placeholder="کاربرد این گروه را بنویسید"></textarea>
            </label>

            <div class="builder-switch">
              <button type="button" :class="{ active: groupBuilder.mode === 'manual' }" @click="groupBuilder.mode = 'manual'">دستی</button>
              <button type="button" :class="{ active: groupBuilder.mode === 'smart' }" @click="groupBuilder.mode = 'smart'">هوشمند</button>
            </div>

            <div v-if="groupBuilder.mode === 'smart'" class="smart-rule-grid">
              <label class="filter-field">
                <span>حداقل سفارش</span>
                <input v-model.number="groupBuilder.rules.minOrders" type="number" min="0" />
              </label>
              <label class="filter-field">
                <span>حداقل خرید</span>
                <input :value="moneyInputValue(groupBuilder.rules.minSpent)" type="text" inputmode="numeric" placeholder="مثلا 1,000,000" @input="groupBuilder.rules.minSpent = parseMoneyInput($event.target.value)" />
              </label>
              <label class="filter-field">
                <span>حداقل امتیاز</span>
                <input v-model.number="groupBuilder.rules.minScore" type="number" min="0" max="5" step="0.1" />
              </label>
              <label class="filter-field">
                <span>کارواش</span>
                <select v-model="groupBuilder.rules.carwash">
                  <option value="">همه کارواش‌ها</option>
                  <option v-for="carwash in availableCarwashes" :key="carwash" :value="carwash">{{ carwash }}</option>
                </select>
              </label>
            </div>

            <div v-else class="manual-picker">
              <div class="manual-picker-head">
                <strong>انتخاب مشتری</strong>
                <input v-model.trim="groupBuilder.manualSearch" type="text" placeholder="جستجوی مشتری..." />
              </div>
              <div class="manual-picker-list">
                <label v-for="customer in manualSelectableCustomers" :key="customer.key" class="manual-picker-item">
                  <input v-model="groupBuilder.manualKeys" type="checkbox" :value="customer.key" />
                  <div>
                    <strong>{{ customer.name }}</strong>
                    <small>{{ customer.phone || 'بدون موبایل' }} · {{ customer.carwash_name }}</small>
                  </div>
                </label>
              </div>
            </div>
          </div>

          <aside class="group-preview-card">
            <div class="preview-bubble">
              <strong>{{ toFa(groupBuilderPreview.length) }}</strong>
              <span>عضو در پیش‌نمایش</span>
            </div>
            <p>این گروه با تنظیمات فعلی روی همین تعداد مشتری اعمال می‌شود.</p>
            <div class="preview-list">
              <div v-for="customer in groupBuilderPreview.slice(0, 6)" :key="customer.key" class="preview-list-item">
                <span>{{ customer.name }}</span>
                <small>{{ money(customer.total_spent) }}</small>
              </div>
            </div>
          </aside>
        </div>

        <footer class="modal-foot">
          <button type="button" class="club-ghost-btn" @click="closeGroupBuilder">انصراف</button>
          <button type="button" class="club-primary-btn" @click="saveCustomGroup">ذخیره گروه</button>
        </footer>
      </section>
    </div>

    <div v-if="assignGroupModal.open" class="overlay" @click.self="closeAssignGroupModal">
      <section class="modal-card assign-modal">
        <header class="modal-head">
          <div>
            <p class="modal-kicker">افزودن به گروه</p>
            <h3>{{ assignGroupModal.customer?.name }}</h3>
          </div>
          <button type="button" class="icon-close" @click="closeAssignGroupModal">×</button>
        </header>

        <div class="assign-list">
          <label v-for="group in customGroups" :key="group.id" class="assign-item">
            <input v-model="assignGroupModal.selectedGroupIds" type="checkbox" :value="group.id" />
            <div>
              <strong>{{ group.name }}</strong>
              <small>{{ group.mode === 'smart' ? 'هوشمند' : 'دستی' }}</small>
            </div>
          </label>
        </div>

        <footer class="modal-foot">
          <button type="button" class="club-ghost-btn" @click="closeAssignGroupModal">بستن</button>
          <button type="button" class="club-primary-btn" @click="saveCustomerGroupAssignment">ذخیره</button>
        </footer>
      </section>
    </div>

    <div v-if="customerDetail.open" class="overlay" @click.self="closeCustomerDetail">
      <section class="modal-card customer-detail-modal">
        <header class="modal-head">
          <div>
            <p class="modal-kicker">پروفایل مشتری</p>
            <h3>{{ customerDetail.customer?.name }}</h3>
          </div>
          <button type="button" class="icon-close" @click="closeCustomerDetail">×</button>
        </header>

        <div v-if="false && customerDetail.customer" class="detail-grid">
          <article class="detail-metric">
            <small>شماره موبایل</small>
            <strong>{{ customerDetail.customer.phone || '-' }}</strong>
          </article>
          <article class="detail-metric">
            <small>کارواش</small>
            <strong>{{ customerDetail.customer.carwash_name }}</strong>
          </article>
          <article class="detail-metric">
            <small>سفارش‌ها</small>
            <strong>{{ toFa(customerDetail.customer.orders_count) }}</strong>
          </article>
          <article class="detail-metric">
            <small>جمع خرید</small>
            <strong>{{ money(customerDetail.customer.total_spent) }}</strong>
          </article>

          <article class="detail-panel">
            <h4>گروه‌های عضو</h4>
            <div class="tag-row">
              <span class="tag">کارواش {{ customerDetail.customer.carwash_name }}</span>
              <span v-for="group in customerMembershipGroups(customerDetail.customer)" :key="group.id" class="tag custom">
                {{ group.name }}
              </span>
            </div>
          </article>

          <article class="detail-panel">
            <h4>پلاک‌های ثبت‌شده</h4>
            <div class="tag-row">
              <PlateBadge
                v-for="plate in customerDetail.customer.plates"
                :key="plate.plate_number"
                :plate-number="plate.plate_number"
                :plate-left="plate.plate_left"
                :plate-letter="plate.plate_letter"
                :plate-mid="plate.plate_mid"
                :plate-right="plate.plate_right"
                :plate-type="plate.plate_type || 'car'"
                compact
              />
            </div>
          </article>
        </div>

        <div v-if="customerDetail.customer" class="customer-profile-shell">
          <section class="customer-profile-hero">
            <div class="customer-profile-title">
              <span class="avatar-badge large">{{ initials(customerDetail.customer.name) }}</span>
              <div>
                <strong>{{ customerDetail.customer.name }}</strong>
                <small>{{ customerDetail.customer.phone || '-' }}</small>
              </div>
            </div>
            <div class="customer-profile-score">
              <span>امتیاز فعلی</span>
              <strong>{{ toFaDecimal(customerDetail.customer.score) }}</strong>
            </div>
          </section>

          <div class="detail-grid profile-metrics-grid">
            <article class="detail-metric">
              <small>کارواش</small>
              <strong>{{ customerDetail.customer.carwash_name }}</strong>
            </article>
            <article class="detail-metric">
              <small>سفارش‌ها</small>
              <strong>{{ toFa(customerDetail.customer.orders_count) }}</strong>
            </article>
            <article class="detail-metric">
              <small>جمع خرید</small>
              <strong>{{ money(customerDetail.customer.total_spent) }}</strong>
            </article>
            <article class="detail-metric">
              <small>میانگین هر سفارش</small>
              <strong>{{ money(customerDetail.customer.average_ticket) }}</strong>
            </article>
            <article class="detail-metric">
              <small>آخرین مراجعه</small>
              <strong>{{ date(customerDetail.customer.last_order_at) }}</strong>
            </article>
            <article class="detail-metric">
              <small>اولین ثبت</small>
              <strong>{{ date(customerDetail.customer.first_order_at) }}</strong>
            </article>
          </div>

          <div class="profile-panel-grid">
            <article class="detail-panel profile-panel">
              <h4>گروه‌های عضو</h4>
              <div class="tag-row">
                <span class="tag">کارواش {{ customerDetail.customer.carwash_name }}</span>
                <span v-for="group in customerMembershipGroups(customerDetail.customer)" :key="group.id" class="tag custom">
                  {{ group.name }}
                </span>
              </div>
            </article>

            <article class="detail-panel profile-panel">
              <h4>پلاک‌های ثبت‌شده</h4>
              <div class="tag-row plate-tag-row">
                <PlateBadge
                  v-for="plate in customerDetail.customer.plates"
                  :key="plate.plate_number"
                  :plate-number="plate.plate_number"
                  :plate-left="plate.plate_left"
                  :plate-letter="plate.plate_letter"
                  :plate-mid="plate.plate_mid"
                  :plate-right="plate.plate_right"
                  :plate-type="plate.plate_type || 'car'"
                  compact
                />
                <span v-if="!customerDetail.customer.plates?.length" class="tag">بدون پلاک ثبت‌شده</span>
              </div>
            </article>
          </div>
        </div>

        <footer class="modal-foot">
          <button type="button" class="club-ghost-btn" @click="openAssignGroupModal(customerDetail.customer)">افزودن به گروه</button>
          <button
            v-if="activePlan === 'advanced' && customerDetail.customer"
            type="button"
            class="club-primary-btn"
            @click="openSmsComposer({ type: 'customer', customer: customerDetail.customer })"
          >
            ارسال پیامک
          </button>
        </footer>
      </section>
    </div>

    <div v-if="smsComposer.open" class="overlay" @click.self="closeSmsComposer">
      <section class="modal-card sms-modal">
        <header class="modal-head">
          <div>
            <p class="modal-kicker">ارسال پیامک هوشمند</p>
            <h3>{{ smsComposer.targetLabel }}</h3>
          </div>
          <button type="button" class="icon-close" @click="closeSmsComposer">×</button>
        </header>

        <div class="sms-layout">
          <div class="sms-form-col">
            <div class="sms-target-card">
              <div>
                <small>تعداد گیرنده</small>
                <strong>{{ toFa(smsRecipients.length) }} نفر</strong>
              </div>
              <div>
                <small>وضعیت اعتبار</small>
                <strong :class="{ danger: !hasEnoughSmsCredit }">{{ hasEnoughSmsCredit ? 'کافی' : 'ناکافی' }}</strong>
              </div>
            </div>

            <div class="template-list horizontal">
              <button v-for="template in smsTemplates" :key="template.id" type="button" class="template-item" @click="useSmsTemplate(template.body)">
                {{ template.title }}
              </button>
            </div>

            <label class="filter-field">
              <span>متن پیامک</span>
              <textarea v-model.trim="smsComposer.message" rows="7" placeholder="متن پیامک را اینجا بنویسید..."></textarea>
            </label>

            <label class="filter-field">
              <span>یادداشت گزارش</span>
              <textarea v-model.trim="smsComposer.note" rows="3" placeholder="مثلا کمپین مشتریان وفادار تیرماه"></textarea>
            </label>

            <div class="sms-meta-grid">
              <article class="detail-metric">
                <small>کاراکتر</small>
                <strong>{{ toFa(smsCharacterCount) }}</strong>
              </article>
              <article class="detail-metric">
                <small>تعداد گیرنده</small>
                <strong>{{ toFa(smsRecipients.length) }}</strong>
              </article>
              <article class="detail-metric">
                <small>هزینه تخمینی</small>
                <strong>{{ money(estimatedSmsCost) }}</strong>
              </article>
            </div>
          </div>

          <aside class="sms-preview-col">
            <div class="phone-preview">
              <div class="phone-notch"></div>
              <div class="phone-screen">
                <div class="phone-head">
                  <strong>{{ authStore.user?.tenant_name || 'CarWash' }}</strong>
                  <small>Text Message</small>
                </div>
                <div class="phone-chat">
                  <div class="bubble">
                    <p>{{ smsPreviewText }}</p>
                    <small>{{ smsRecipients[0]?.name || 'گیرنده نمونه' }}</small>
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>

        <footer class="modal-foot">
          <button type="button" class="club-ghost-btn" @click="closeSmsComposer">انصراف</button>
          <button type="button" class="club-primary-btn" :disabled="!canSendSms || smsSending" @click="sendSmsCampaign">
            {{ smsSending ? 'در حال ارسال...' : 'تایید و ارسال' }}
          </button>
        </footer>
      </section>
    </div>

    <div v-if="templateEditor.open" class="overlay" @click.self="closeTemplateEditor">
      <section class="modal-card template-editor-modal">
        <header class="modal-head">
          <div>
            <p class="modal-kicker">قالب پیامک</p>
            <h3>{{ templateEditor.id ? 'ویرایش قالب' : 'ساخت قالب جدید' }}</h3>
          </div>
          <button type="button" class="icon-close" @click="closeTemplateEditor">×</button>
        </header>

        <div class="template-editor-layout">
          <div class="template-editor-form">
            <label class="filter-field">
              <span>عنوان</span>
              <input v-model.trim="templateEditor.title" type="text" placeholder="مثلا تخفیف وفاداری" />
            </label>
            <label class="filter-field">
              <span>کد قالب</span>
              <input v-model.trim="templateEditor.code" type="text" placeholder="discount-loyal" />
            </label>
            <label class="filter-field">
              <span>متن قالب</span>
              <textarea v-model.trim="templateEditor.body" rows="8" placeholder="[نام مشتری] عزیز ..."></textarea>
            </label>
            <div class="template-token-row">
              <button v-for="token in smsVariableTokens" :key="token" type="button" class="group-chip" @click="appendTemplateToken(token)">{{ token }}</button>
            </div>
          </div>

          <aside class="template-editor-preview">
            <div class="side-card-head">
              <h4>پیش‌نمایش</h4>
              <span>{{ toFa(templateEditor.body.length) }} کاراکتر</span>
            </div>
            <div class="template-preview-box">
              <p>{{ templatePreviewText }}</p>
            </div>
            <button
              v-if="templateEditor.body.trim()"
              type="button"
              class="club-secondary-btn"
              @click="useTemplateInComposer"
            >
              استفاده در ارسال پیامک
            </button>
          </aside>
        </div>

        <footer class="modal-foot template-editor-foot">
          <button v-if="templateEditor.id" type="button" class="club-ghost-btn danger-btn" @click="deleteTemplate">حذف</button>
          <button type="button" class="club-ghost-btn" @click="closeTemplateEditor">انصراف</button>
          <button type="button" class="club-primary-btn" :disabled="templateSaving" @click="saveTemplate">
            {{ templateSaving ? 'در حال ذخیره...' : 'ذخیره قالب' }}
          </button>
        </footer>
      </section>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppShell from '../../components/layout/AppShell.vue'
import IconlyIcon from '../../components/base/IconlyIcon.vue'
import HelpTip from '../../components/base/HelpTip.vue'
import PlateBadge from '../../components/vehicles/PlateBadge.vue'
import api from '../../services/api'
import { useAuthStore } from '../../store/auth.store'
import { formatJalaliDate } from '../../utils/date'
import { formatThousandsToman, formatThousandsTomanValue, fromThousandsTomanInput } from '../../utils/money'
import { resolveApiErrorMessage } from '../../utils/apiError'
import { notifyError, notifySuccess, notifyWarning } from '../../utils/notify'
import { hasFeatureAccess } from '../../utils/attendanceAccess'
import { sectionHelpByPage } from '../../config/pageHelp'
import actionViewIcon from '../../assets/iconly/show.svg'
import actionGroupIcon from '../../assets/iconly/category.svg'
import actionSmsIcon from '../../assets/iconly/message.svg'

const authStore = useAuthStore()
const actionIcons = {
  view: actionViewIcon,
  group: actionGroupIcon,
  sms: actionSmsIcon
}

const activePlan = ref('simple')
const searchQuery = ref('')
const loading = ref(false)
const smsSending = ref(false)
const templateSaving = ref(false)
const customers = ref([])
const smsCreditBalance = ref(0)
const smsPricePerSegment = ref(185)
const smsCharsPerSegment = ref(100)
const highlightedGroupId = ref('')
const customerImportFileRef = ref(null)
const CUSTOMER_IMPORT_PRICE = 500000

const customerImport = reactive({
  open: false,
  file: null,
  fileName: '',
  preview: [],
  errors: [],
  validCount: 0,
  errorCount: 0,
  price: CUSTOMER_IMPORT_PRICE,
  confirming: false,
  previewing: false,
  submitting: false,
  downloadingTemplate: false
})

const filters = reactive({
  groupId: '',
  minOrders: 0,
  minSpent: 0,
  minScore: 0,
  sortBy: 'spent'
})

const groupingMode = ref('tenant')
const customGroups = ref([])
const smsLogs = ref([])

const groupBuilder = reactive({
  open: false,
  id: '',
  name: '',
  description: '',
  mode: 'manual',
  manualSearch: '',
  manualKeys: [],
  rules: {
    minOrders: 0,
    minSpent: 0,
    minScore: 0,
    carwash: ''
  }
})

const assignGroupModal = reactive({
  open: false,
  customer: null,
  selectedGroupIds: []
})

const customerDetail = reactive({
  open: false,
  customer: null
})

const smsComposer = reactive({
  open: false,
  targetType: '',
  targetLabel: '',
  recipients: [],
  message: '',
  note: ''
})

const smsTemplates = ref([])
const smsVariableTokens = ['[نام مشتری]', '[نام کارواش]', '[تعداد سفارش]', '[جمع خرید]', '[امتیاز]', '[پلاک]']

const templateEditor = reactive({
  open: false,
  id: '',
  code: '',
  title: '',
  body: '',
  displayOrder: 0
})

const availableCarwashes = computed(() => {
  const set = new Set(customers.value.map((item) => item.carwash_name).filter(Boolean))
  return [...set]
})
const availableGroups = computed(() => customGroups.value.filter((group) => group?.id))

const activeCustomersCount = computed(() => customers.value.filter((item) => item.orders_count >= 2).length)
const averageScore = computed(() => {
  if (!customers.value.length) return 0
  const total = customers.value.reduce((sum, item) => sum + Number(item.score || 0), 0)
  return Number((total / customers.value.length).toFixed(1))
})
const activeCarwashCountLabel = computed(() => `داده در کارواش فعلی`)
const canAccessAdvancedSmsClub = computed(() => hasFeatureAccess(authStore.user, 'sms_club'))
const smsCreditStateLabel = computed(() => {
  if (smsCreditBalance.value <= 0) return 'بدون اعتبار'
  if (smsCreditBalance.value < 500000) return 'اعتبار رو به اتمام'
  return 'اعتبار مناسب'
})

const filteredCustomers = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  const minSpentValue = Number(filters.minSpent || 0)
  const activeGroup = customGroups.value.find((group) => String(group.id) === String(filters.groupId || ''))
  const items = customers.value.filter((customer) => {
    if (activeGroup && !resolveGroupMembers(activeGroup).some((item) => item.key === customer.key)) return false
    if (Number(customer.orders_count || 0) < Number(filters.minOrders || 0)) return false
    if (Number(customer.total_spent || 0) < minSpentValue) return false
    if (Number(customer.score || 0) < Number(filters.minScore || 0)) return false
    if (!query) return true
    const haystack = `${customer.name} ${customer.phone} ${customer.primary_plate} ${customer.carwash_name}`.toLowerCase()
    return haystack.includes(query)
  })

  const sorted = [...items]
  sorted.sort((a, b) => {
    if (filters.sortBy === 'orders') return Number(b.orders_count || 0) - Number(a.orders_count || 0)
    if (filters.sortBy === 'score') return Number(b.score || 0) - Number(a.score || 0)
    if (filters.sortBy === 'recent') return new Date(b.last_order_at || 0) - new Date(a.last_order_at || 0)
    if (filters.sortBy === 'name') return String(a.name || '').localeCompare(String(b.name || ''), 'fa')
    return Number(b.total_spent || 0) - Number(a.total_spent || 0)
  })
  return sorted
})

const visibleSections = computed(() => {
  if (groupingMode.value === 'custom') {
    return customGroups.value.map((group) => {
      const members = resolveGroupMembers(group).filter((customer) => filteredCustomerKeys.value.has(customer.key))
      return {
        key: `group-${group.id}`,
        sourceGroupId: group.id,
        title: group.name,
        description: group.description || (group.mode === 'smart' ? 'گروه هوشمند با قوانین پویا' : 'گروه دستی با انتخاب مستقیم مشتری‌ها'),
        customers: members
      }
    })
  }

  const grouped = new Map()
  filteredCustomers.value.forEach((customer) => {
    const key = customer.carwash_name || 'بدون کارواش'
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key).push(customer)
  })
  return [...grouped.entries()].map(([carwashName, members]) => ({
    key: `tenant-${carwashName}`,
    sourceGroupId: '',
    title: `کارواش ${carwashName}`,
    description: 'گروه‌بندی پیش‌فرض بر اساس نام کارواش',
    customers: members
  }))
})

const filteredCustomerKeys = computed(() => new Set(filteredCustomers.value.map((item) => item.key)))

const manualSelectableCustomers = computed(() => {
  const query = groupBuilder.manualSearch.trim().toLowerCase()
  if (!query) return filteredCustomers.value
  return filteredCustomers.value.filter((customer) => {
    const haystack = `${customer.name} ${customer.phone} ${customer.primary_plate}`.toLowerCase()
    return haystack.includes(query)
  })
})

const groupBuilderPreview = computed(() => {
  if (groupBuilder.mode === 'manual') {
    const selected = new Set(groupBuilder.manualKeys)
    return filteredCustomers.value.filter((customer) => selected.has(customer.key))
  }
  return filteredCustomers.value.filter((customer) => customerMatchesRules(customer, groupBuilder.rules))
})

const smsRecipients = computed(() => smsComposer.recipients || [])
const smsCharacterCount = computed(() => String(smsComposer.message || '').trim().length)
const smsSegmentCount = computed(() => {
  const length = smsCharacterCount.value
  const perSegment = Math.max(1, Number(smsCharsPerSegment.value || 100))
  if (length <= 0) return 0
  return Math.ceil(length / perSegment)
})
const estimatedSmsCost = computed(() => (
  smsRecipients.value.length
  * smsSegmentCount.value
  * Number(smsPricePerSegment.value || 0)
))
const hasEnoughSmsCredit = computed(() => smsCreditBalance.value >= estimatedSmsCost.value)
const canSendSms = computed(() => smsRecipients.value.length > 0 && String(smsComposer.message || '').trim().length > 0 && hasEnoughSmsCredit.value)
const smsPreviewText = computed(() => {
  const sampleCustomer = smsRecipients.value[0]
  const message = String(smsComposer.message || '').trim()
  if (!message) return 'متن پیام شما اینجا نمایش داده می‌شود.'
  return renderSmsVariables(message, sampleCustomer)
})
const templatePreviewText = computed(() => {
  const sampleCustomer = customers.value[0]
  const message = String(templateEditor.body || '').trim()
  if (!message) return 'پیش‌نمایش قالب اینجا نمایش داده می‌شود.'
  return renderSmsVariables(message, sampleCustomer)
})

const smsStatusCount = computed(() => smsLogs.value.reduce((acc, item) => {
  acc[item.status] = (acc[item.status] || 0) + 1
  return acc
}, { success: 0, failed: 0, pending: 0 }))

const money = (value) => formatThousandsToman(value)
const moneyInputValue = (value) => formatThousandsTomanValue(value, { maximumFractionDigits: 0 })
const parseMoneyInput = (value) => fromThousandsTomanInput(value)
const date = (value) => formatJalaliDate(value)
const logMessageText = (log) => {
  const message = String(log?.message || '').trim()
  if (message) return message
  const response = String(log?.provider_response || '').trim()
  if (response) return `متن پیام ثبت نشده است. پاسخ سرویس: ${response}`
  return 'متن پیام در این لاگ ذخیره نشده است.'
}
const toFa = (value) => Number(value || 0).toLocaleString('fa-IR')
const toFaDecimal = (value) => Number(value || 0).toLocaleString('fa-IR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const initials = (value) => {
  const parts = String(value || '').trim().split(' ').filter(Boolean)
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`
  return String(value || '--').slice(0, 2)
}

const resetCustomerImport = () => {
  customerImport.file = null
  customerImport.fileName = ''
  customerImport.preview = []
  customerImport.errors = []
  customerImport.validCount = 0
  customerImport.errorCount = 0
  customerImport.price = CUSTOMER_IMPORT_PRICE
  customerImport.confirming = false
  customerImport.previewing = false
  customerImport.submitting = false
  customerImport.downloadingTemplate = false
  if (customerImportFileRef.value) customerImportFileRef.value.value = ''
}

const openCustomerImportModal = () => {
  resetCustomerImport()
  customerImport.open = true
}

const closeCustomerImportModal = () => {
  customerImport.open = false
  resetCustomerImport()
}

const downloadCustomerImportTemplate = async () => {
  customerImport.downloadingTemplate = true
  try {
    const { data } = await api.get('/notifications/customer-club/import/template/', {
      responseType: 'blob'
    })
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = 'customer-import-template.xlsx'
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    notifyError(resolveApiErrorMessage(error, 'دریافت تمپلیت اکسل ناموفق بود.'), { title: 'وارد کردن مشتریان' })
  } finally {
    customerImport.downloadingTemplate = false
  }
}

const handleCustomerImportFile = (event) => {
  const file = event.target.files?.[0] || null
  customerImport.file = file
  customerImport.fileName = file?.name || ''
  customerImport.preview = []
  customerImport.errors = []
  customerImport.validCount = 0
  customerImport.errorCount = 0
  customerImport.confirming = false
}

const customerImportFormData = () => {
  const form = new FormData()
  form.append('file', customerImport.file)
  return form
}

const previewCustomerImport = async () => {
  if (!customerImport.file) {
    notifyWarning('فایل اکسل مشتریان را انتخاب کنید.', { title: 'وارد کردن مشتریان' })
    return
  }
  customerImport.previewing = true
  customerImport.confirming = false
  try {
    const { data } = await api.post('/notifications/customer-club/import/preview/', customerImportFormData(), {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    customerImport.preview = Array.isArray(data?.preview) ? data.preview : []
    customerImport.errors = Array.isArray(data?.errors) ? data.errors : []
    customerImport.validCount = Number(data?.valid_count || 0)
    customerImport.errorCount = Number(data?.error_count || 0)
    customerImport.price = Number(data?.price || CUSTOMER_IMPORT_PRICE)
    if (!customerImport.preview.length && !customerImport.errorCount) {
      notifyWarning('هیچ ردیف معتبری در فایل پیدا نشد.', { title: 'وارد کردن مشتریان' })
    }
  } catch (error) {
    notifyError(resolveApiErrorMessage(error, 'بررسی فایل اکسل ناموفق بود.'), { title: 'وارد کردن مشتریان' })
  } finally {
    customerImport.previewing = false
  }
}

const confirmCustomerImport = async () => {
  if (!customerImport.file) return
  customerImport.submitting = true
  try {
    const { data } = await api.post('/notifications/customer-club/import/confirm/', customerImportFormData(), {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    notifySuccess(`${toFa(data?.imported_count || 0)} مشتری وارد باشگاه مشتریان شد.`, { title: 'وارد کردن مشتریان' })
    closeCustomerImportModal()
    await loadCustomerClubData({ showLoading: false })
  } catch (error) {
    notifyError(resolveApiErrorMessage(error, 'ثبت نهایی مشتریان ناموفق بود.'), { title: 'وارد کردن مشتریان' })
  } finally {
    customerImport.submitting = false
  }
}

const normalizePhone = (value) => String(value || '')
  .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
  .replace(/[^\d+]/g, '')

const unique = (items) => [...new Set(items.filter(Boolean))]

const buildCustomersFromVehicles = (rows) => {
  const map = new Map()
  rows
    .filter((item) => item?.status !== 'cancelled')
    .forEach((item) => {
      const normalizedPhone = normalizePhone(item?.driver_phone)
      const fallbackKey = `${normalizedPhone || 'no-phone'}:${String(item?.driver_name || '').trim() || item.id}`
      const key = fallbackKey
      const record = map.get(key) || {
        key,
        name: String(item?.driver_name || 'مشتری بدون نام').trim() || 'مشتری بدون نام',
        phone: normalizedPhone,
        carwash_name: authStore.user?.tenant_name || 'کارواش اصلی',
        orders_count: 0,
        total_spent: 0,
        score: 0,
        last_order_at: item?.created_at || item?.check_in_at || null,
        plates: [],
        primary_plate: '',
        primary_plate_left: '',
        primary_plate_letter: '',
        primary_plate_mid: '',
        primary_plate_right: '',
        primary_plate_type: 'car'
      }
      record.orders_count += 1
      record.total_spent += Number(item?.job?.final_total || item?.job?.services_total || 0)
      record.score = Math.max(record.score, Number(item?.customer_score || 0))
      const eventDate = item?.released_at || item?.updated_at || item?.check_in_at || item?.created_at
      if (!record.last_order_at || new Date(eventDate) > new Date(record.last_order_at)) {
        record.last_order_at = eventDate
      }
      const plate = String(item?.plate_number || '').trim()
      if (plate && plate !== '1111' && !record.plates.find((entry) => entry.plate_number === plate)) {
        record.plates.push({
          plate_number: plate,
          plate_left: String(item?.plate_left || '').trim(),
          plate_letter: String(item?.plate_letter || '').trim(),
          plate_mid: String(item?.plate_mid || '').trim(),
          plate_right: String(item?.plate_right || '').trim(),
          plate_type: String(item?.plate_type || 'car').trim() || 'car'
        })
      }
      const primaryPlate = record.plates[0]
      record.primary_plate = primaryPlate?.plate_number || record.primary_plate || ''
      record.primary_plate_left = primaryPlate?.plate_left || ''
      record.primary_plate_letter = primaryPlate?.plate_letter || ''
      record.primary_plate_mid = primaryPlate?.plate_mid || ''
      record.primary_plate_right = primaryPlate?.plate_right || ''
      record.primary_plate_type = primaryPlate?.plate_type || 'car'
      map.set(key, record)
    })
  return [...map.values()]
}

const customerMatchesRules = (customer, rules) => {
  if (rules.carwash && customer.carwash_name !== rules.carwash) return false
  if (Number(customer.orders_count || 0) < Number(rules.minOrders || 0)) return false
  if (Number(customer.total_spent || 0) < Number(rules.minSpent || 0)) return false
  if (Number(customer.score || 0) < Number(rules.minScore || 0)) return false
  return true
}

const resolveGroupMembers = (group) => {
  if (!group) return []
  if (group.mode === 'smart') {
    return customers.value.filter((customer) => customerMatchesRules(customer, group.rules || {}))
  }
  const memberKeys = new Set(group.member_keys || group.memberKeys || [])
  return customers.value.filter((customer) => memberKeys.has(customer.key))
}

const groupById = (groupId) => customGroups.value.find((group) => group.id === groupId) || null

const customerMembershipGroups = (customer) => customGroups.value.filter((group) => {
  if (!customer) return false
  if (group.mode === 'smart') return customerMatchesRules(customer, group.rules || {})
  return (group.member_keys || group.memberKeys || []).includes(customer.key)
})

const highlightGroup = (groupId) => {
  groupingMode.value = 'custom'
  highlightedGroupId.value = groupId
}

const openAdvancedPlan = () => {
  if (!canAccessAdvancedSmsClub.value) {
    notifyWarning('پنل پیشرفته باشگاه مشتریان باید از کیف پول خریداری شود.', { title: 'پنل پیشرفته فعال نیست' })
    activePlan.value = 'simple'
    return
  }
  activePlan.value = 'advanced'
}

const resetGroupBuilder = () => {
  groupBuilder.open = false
  groupBuilder.id = ''
  groupBuilder.name = ''
  groupBuilder.description = ''
  groupBuilder.mode = 'manual'
  groupBuilder.manualSearch = ''
  groupBuilder.manualKeys = []
  groupBuilder.rules.minOrders = 0
  groupBuilder.rules.minSpent = 0
  groupBuilder.rules.minScore = 0
  groupBuilder.rules.carwash = ''
}

const openGroupBuilder = () => {
  resetGroupBuilder()
  groupBuilder.open = true
}

const closeGroupBuilder = () => {
  resetGroupBuilder()
}

const buildGroupPayload = () => ({
  name: String(groupBuilder.name || '').trim(),
  description: String(groupBuilder.description || '').trim(),
  mode: groupBuilder.mode,
  member_keys: groupBuilder.mode === 'manual' ? [...groupBuilder.manualKeys] : [],
  rules: groupBuilder.mode === 'smart'
    ? {
      minOrders: Number(groupBuilder.rules.minOrders || 0),
      minSpent: Number(groupBuilder.rules.minSpent || 0),
      minScore: Number(groupBuilder.rules.minScore || 0),
      carwash: groupBuilder.rules.carwash || ''
    }
    : {}
})

const loadCustomerClubData = async ({ showLoading = true } = {}) => {
  if (showLoading) loading.value = true
  try {
    const { data } = await api.get('/notifications/customer-club/', {
      meta: { trackLoading: !showLoading }
    })
    customers.value = Array.isArray(data?.customers) ? data.customers : []
    customGroups.value = Array.isArray(data?.groups) ? data.groups : []
    smsTemplates.value = Array.isArray(data?.templates) ? data.templates : []
    smsLogs.value = Array.isArray(data?.logs) ? data.logs : []
    smsCreditBalance.value = Number(data?.summary?.sms_balance || 0)
    smsPricePerSegment.value = Number(data?.summary?.sms_price_per_segment || 185)
    smsCharsPerSegment.value = Number(data?.summary?.sms_chars_per_segment || 100)
  } catch (_error) {
    customers.value = []
    customGroups.value = []
    smsTemplates.value = []
    smsLogs.value = []
    smsCreditBalance.value = 0
    smsPricePerSegment.value = 185
    smsCharsPerSegment.value = 100
  } finally {
    if (showLoading) loading.value = false
  }
}

const saveCustomGroup = async () => {
  const name = String(groupBuilder.name || '').trim()
  if (!name) {
    notifyWarning('نام گروه را وارد کنید.', { title: 'اطلاعات ناقص' })
    return
  }

  try {
    const payload = buildGroupPayload()
    if (groupBuilder.id) {
      await api.put(`/notifications/customer-groups/${groupBuilder.id}/`, payload)
    } else {
      await api.post('/notifications/customer-groups/', payload)
    }
    await loadCustomerClubData({ showLoading: false })
    const latestGroup = customGroups.value.find((group) => group.name === payload.name) || customGroups.value[0]
    closeGroupBuilder()
    groupingMode.value = 'custom'
    highlightedGroupId.value = latestGroup?.id || ''
  } catch (error) {
    notifyError(resolveApiErrorMessage(error, 'ذخیره گروه ناموفق بود.'), { title: 'خطا در ذخیره گروه' })
  }
}

const openAssignGroupModal = (customer) => {
  if (!customer) return
  assignGroupModal.open = true
  assignGroupModal.customer = customer
  assignGroupModal.selectedGroupIds = customGroups.value
    .filter((group) => group.mode === 'manual' && (group.member_keys || group.memberKeys || []).includes(customer.key))
    .map((group) => group.id)
}

const prefillGroupBuilderForCustomer = (customer) => {
  openGroupBuilder()
  if (!customer) return
  groupBuilder.mode = 'manual'
  groupBuilder.name = `گروه ${customer.name || 'مشتری'}`
  groupBuilder.description = `گروه ساخته‌شده برای ${customer.name || 'این مشتری'}`
  groupBuilder.manualKeys = customer.key ? [customer.key] : []
}

const handleGroupAction = (customer) => {
  if (customGroups.value.length) {
    openAssignGroupModal(customer)
    return
  }
  prefillGroupBuilderForCustomer(customer)
}

const closeAssignGroupModal = () => {
  assignGroupModal.open = false
  assignGroupModal.customer = null
  assignGroupModal.selectedGroupIds = []
}

const saveCustomerGroupAssignment = async () => {
  const customer = assignGroupModal.customer
  if (!customer) return
  const selected = new Set(assignGroupModal.selectedGroupIds)

  try {
    const requests = customGroups.value
      .filter((group) => group.mode === 'manual')
      .map((group) => {
        const memberKeys = new Set(group.member_keys || group.memberKeys || [])
        if (selected.has(group.id)) memberKeys.add(customer.key)
        else memberKeys.delete(customer.key)
        return api.put(`/notifications/customer-groups/${group.id}/`, {
          name: group.name,
          description: group.description || '',
          mode: group.mode,
          member_keys: [...memberKeys],
          rules: group.rules || {}
        }, {
          meta: { trackLoading: false }
        })
      })

    await Promise.all(requests)
    await loadCustomerClubData({ showLoading: false })
    closeAssignGroupModal()
  } catch (error) {
    notifyError(resolveApiErrorMessage(error, 'بروزرسانی گروه‌ها ناموفق بود.'), { title: 'خطا در بروزرسانی گروه‌ها' })
  }
}

const openCustomerDetail = (customer) => {
  customerDetail.open = true
  customerDetail.customer = customer
}

const closeCustomerDetail = () => {
  customerDetail.open = false
  customerDetail.customer = null
}

const replaceSmsVariables = (message, customer) => String(message || '')
  .replaceAll('[نام مشتری]', customer?.name || 'مشتری')
  .replaceAll('[نام کارواش]', customer?.carwash_name || authStore.user?.tenant_name || 'کارواش')

const previewTemplateBody = (body) => {
  const text = String(body || '').replace(/\s+/g, ' ').trim()
  if (!text) return 'قالب خالی است'
  return text.length > 84 ? `${text.slice(0, 84)}...` : text
}

const renderSmsVariables = (message, customer) => String(message || '')
  .replaceAll('[نام مشتری]', customer?.name || 'مشتری')
  .replaceAll('[نام کارواش]', customer?.carwash_name || authStore.user?.tenant_name || 'کارواش')
  .replaceAll('[تعداد سفارش]', toFa(customer?.orders_count || 0))
  .replaceAll('[جمع خرید]', money(customer?.total_spent || 0))
  .replaceAll('[امتیاز]', toFaDecimal(customer?.score || 0))
  .replaceAll('[پلاک]', customer?.primary_plate || '-')

const resetTemplateEditor = () => {
  templateEditor.open = false
  templateEditor.id = ''
  templateEditor.code = ''
  templateEditor.title = ''
  templateEditor.body = ''
  templateEditor.displayOrder = smsTemplates.value.length + 10
}

const openTemplateEditor = (template = null) => {
  resetTemplateEditor()
  templateEditor.open = true
  if (!template) return
  templateEditor.id = template.id
  templateEditor.code = template.code || ''
  templateEditor.title = template.title || ''
  templateEditor.body = template.body || ''
  templateEditor.displayOrder = Number(template.display_order || 0)
}

const closeTemplateEditor = () => {
  resetTemplateEditor()
}

const appendTemplateToken = (token) => {
  templateEditor.body = `${templateEditor.body || ''}${templateEditor.body ? ' ' : ''}${token}`
}

const useTemplateInComposer = () => {
  if (!smsComposer.open) {
    const fallbackTarget = customGroups.value[0]
    if (fallbackTarget) openSmsComposer({ type: 'group', group: fallbackTarget })
  }
  useSmsTemplate(templateEditor.body)
}

const saveTemplate = async () => {
  const title = String(templateEditor.title || '').trim()
  const body = String(templateEditor.body || '').trim()
  const code = String(templateEditor.code || '').trim()
  if (!title || !body) {
    notifyWarning('عنوان و متن قالب الزامی است.', { title: 'اطلاعات ناقص' })
    return
  }

  templateSaving.value = true
  try {
    const payload = {
      title,
      body,
      code: code || `custom-${Date.now()}`,
      display_order: Number(templateEditor.displayOrder || smsTemplates.value.length + 10),
      is_active: true
    }
    if (templateEditor.id) {
      await api.put(`/notifications/sms/templates/${templateEditor.id}/`, payload, { meta: { trackLoading: false } })
    } else {
      await api.post('/notifications/sms/templates/', payload, { meta: { trackLoading: false } })
    }
    await loadCustomerClubData({ showLoading: false })
    closeTemplateEditor()
  } catch (error) {
    notifyError(resolveApiErrorMessage(error, 'ذخیره قالب ناموفق بود.'), { title: 'خطا در ذخیره قالب' })
  } finally {
    templateSaving.value = false
  }
}

const deleteTemplate = async () => {
  if (!templateEditor.id) return
  templateSaving.value = true
  try {
    await api.delete(`/notifications/sms/templates/${templateEditor.id}/`, { meta: { trackLoading: false } })
    await loadCustomerClubData({ showLoading: false })
    closeTemplateEditor()
  } catch (error) {
    notifyError(resolveApiErrorMessage(error, 'حذف قالب ناموفق بود.'), { title: 'خطا در حذف قالب' })
  } finally {
    templateSaving.value = false
  }
}

const openPrimaryGroupSmsComposer = () => {
  if (customGroups.value.length) {
    openSmsComposer({ type: 'group', group: customGroups.value[0] })
    return
  }

  const primarySection = visibleSections.value.find((section) => Array.isArray(section.customers) && section.customers.length)
  if (primarySection) {
    openSmsComposer({ type: 'section', section: primarySection })
    return
  }

  if (filteredCustomers.value.length) {
    openSmsComposer({
      type: 'section',
      section: {
        title: 'مشتری‌های فیلترشده',
        customers: filteredCustomers.value
      }
    })
  }
}

const openSmsComposer = (payload) => {
  let recipients = []
  let targetLabel = ''
  let targetType = ''

  if (payload?.type === 'customer' && payload.customer) {
    recipients = [payload.customer]
    targetLabel = `پیامک تکی برای ${payload.customer.name}`
    targetType = 'customer'
  } else if (payload?.type === 'group' && payload.group) {
    recipients = resolveGroupMembers(payload.group)
    targetLabel = `پیامک گروهی برای ${payload.group.name}`
    targetType = 'group'
  } else if (payload?.type === 'section' && payload.section) {
    recipients = payload.section.customers || []
    targetLabel = `پیامک برای ${payload.section.title}`
    targetType = 'section'
  }

  const normalizedRecipients = recipients
    .map((recipient) => ({ ...recipient, phone: normalizePhone(recipient.phone) }))
    .filter((recipient) => recipient.phone)

  if (!normalizedRecipients.length) {
    notifyWarning('شماره موبایل معتبری برای ارسال پیامک وجود ندارد.', { title: 'ارسال پیامک' })
    return
  }

  smsComposer.open = true
  smsComposer.targetType = targetType
  smsComposer.targetLabel = targetLabel
  smsComposer.recipients = normalizedRecipients
  smsComposer.message = ''
  smsComposer.note = ''
}

const closeSmsComposer = () => {
  smsComposer.open = false
  smsComposer.targetType = ''
  smsComposer.targetLabel = ''
  smsComposer.recipients = []
  smsComposer.message = ''
  smsComposer.note = ''
}

const useSmsTemplate = (templateBody) => {
  smsComposer.message = templateBody || ''
}

const smsStatusLabel = (status) => ({
  success: 'موفق',
  failed: 'ناموفق',
  pending: 'در انتظار'
}[status] || 'در انتظار')

const sendSmsCampaign = async () => {
  if (!canSendSms.value || smsSending.value) return

  smsSending.value = true
  try {
    const activeTemplate = smsTemplates.value.find((template) => template.body === smsComposer.message)
    const { data } = await api.post('/notifications/sms/send/', {
      template_code: activeTemplate?.code || '',
      template_text: smsComposer.message,
      recipients: smsRecipients.value.map((recipient) => ({
        key: recipient.key,
        name: recipient.name,
        phone: recipient.phone,
        carwash_name: recipient.carwash_name,
        orders_count: recipient.orders_count,
        total_spent: recipient.total_spent,
        score: recipient.score,
        last_order_at: recipient.last_order_at,
        primary_plate: recipient.primary_plate
      })),
      note: smsComposer.note,
      target_label: smsComposer.targetLabel
    }, {
      meta: { trackLoading: false }
    })

    await loadCustomerClubData({ showLoading: false })

    const successCount = Number(data?.success_count || 0)
    const failedCount = Number(data?.failed_count || 0)

    if (successCount === 0) {
      notifyWarning(data?.detail || 'هیچ پیامکی ارسال نشد. جزئیات خطا را در گزارش پیامک بررسی کنید.', { title: 'ارسال پیامک' })
      return
    }

    closeSmsComposer()
    if (failedCount > 0) {
      notifyWarning(`${toFa(successCount)} پیامک ارسال شد و ${toFa(failedCount)} پیامک ناموفق بود.`, { title: 'ارسال پیامک' })
      return
    }

    notifySuccess(`${toFa(successCount)} پیامک با موفقیت در صف ارسال قرار گرفت.`, { title: 'ارسال پیامک' })
  } catch (error) {
    const detail = resolveApiErrorMessage(error, 'ارسال پیامک ناموفق بود.')
    notifyError(detail, { title: 'خطا در ارسال پیامک' })
    await loadCustomerClubData({ showLoading: false })
  } finally {
    smsSending.value = false
  }
}

const applySuggestedRule = (type) => {
  openGroupBuilder()
  groupBuilder.mode = 'smart'
  if (type === 'vip') {
    groupBuilder.name = 'مشتریان وفادار'
    groupBuilder.description = 'مشتریان با سفارش بالا و امتیاز عالی'
    groupBuilder.rules.minOrders = 5
    groupBuilder.rules.minSpent = 10000000
    groupBuilder.rules.minScore = 4
  } else {
    groupBuilder.name = 'مشتریان در معرض ریزش'
    groupBuilder.description = 'مشتریان با خرید پایین و امتیاز متوسط'
    groupBuilder.rules.minOrders = 1
    groupBuilder.rules.minSpent = 0
    groupBuilder.rules.minScore = 2
  }
}

const exportCustomers = () => {
  if (!filteredCustomers.value.length) {
    notifyWarning('برای خروجی گرفتن، حداقل یک مشتری باید در لیست باشد.', { title: 'خروجی اکسل' })
    return
  }
  const rows = [
    ['نام مشتری', 'شماره موبایل', 'کارواش', 'تعداد سفارش', 'جمع مبلغ خرید', 'امتیاز', 'آخرین سفارش'],
    ...filteredCustomers.value.map((customer) => [
      customer.name,
      customer.phone,
      customer.carwash_name,
      customer.orders_count,
      customer.total_spent,
      customer.score,
      customer.last_order_at
    ])
  ]
  const csv = rows.map((row) => row.join(',')).join('\n')
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'customer-club-export.csv'
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await loadCustomerClubData()
})
</script>

<style scoped>
.club-page {
  display: grid;
  gap: 20px;
}

.club-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) 320px;
  gap: 18px;
  padding: 28px;
  border-radius: 32px;
  border: 1px solid rgba(191, 219, 254, 0.8);
  background:
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.18), transparent 26%),
    radial-gradient(circle at left bottom, rgba(99, 102, 241, 0.12), transparent 22%),
    linear-gradient(135deg, #ffffff 0%, #f2f8ff 54%, #eef6ff 100%);
  box-shadow: 0 22px 50px rgba(15, 23, 42, 0.06);
}

.club-kicker {
  display: inline-flex;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(0, 88, 190, 0.1);
  color: #0058be;
  font-size: 12px;
  font-weight: 800;
}

.club-hero-copy h2 {
  margin: 14px 0 10px;
  font-size: 40px;
  line-height: 1.3;
  color: #0f172a;
}

.club-hero-copy p {
  margin: 0;
  max-width: 62ch;
  color: #475569;
  line-height: 2;
}

.club-hero-actions {
  display: grid;
  align-content: start;
  gap: 12px;
}

.mode-switch,
.builder-switch,
.grouping-mode {
  display: inline-flex;
  gap: 6px;
  padding: 6px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(203, 213, 225, 0.8);
}

.mode-switch button,
.builder-switch button,
.grouping-mode button {
  border: 0;
  background: transparent;
  color: #64748b;
  font: inherit;
  font-weight: 700;
  border-radius: 14px;
  padding: 12px 18px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.mode-switch button.active,
.builder-switch button.active,
.grouping-mode button.active {
  background: linear-gradient(135deg, #0058be, #2170e4);
  color: #fff;
  box-shadow: 0 12px 22px rgba(0, 88, 190, 0.18);
}

.club-primary-btn,
.club-ghost-btn,
.club-secondary-btn,
.club-inline-btn,
.icon-action {
  border: 0;
  border-radius: 16px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  transition: 0.18s ease;
}

.btn-with-icon {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.club-primary-btn {
  padding: 13px 18px;
  color: #fff;
  background: linear-gradient(135deg, #0058be, #0ea5e9);
  box-shadow: 0 18px 30px rgba(0, 88, 190, 0.2);
}

.club-primary-btn :deep(.iconly-shell) {
  --iconly-filter: brightness(0) saturate(100%) invert(100%);
}

.club-primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.club-ghost-btn,
.club-secondary-btn {
  padding: 13px 18px;
  color: #0058be;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.28);
}

.club-inline-btn {
  padding: 10px 14px;
  color: #0f4c81;
  background: rgba(219, 234, 254, 0.9);
}

.club-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.club-stat-card {
  position: relative;
  overflow: hidden;
  padding: 22px;
  border-radius: 26px;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
  display: grid;
  gap: 8px;
}

.club-stat-card::after {
  content: '';
  position: absolute;
  inset-inline-end: -24px;
  inset-block-end: -24px;
  width: 96px;
  height: 96px;
  border-radius: 28px;
  opacity: 0.09;
  background: currentColor;
}

.club-stat-card small,
.detail-metric small {
  color: #64748b;
  font-size: 12px;
}

.club-stat-card strong,
.detail-metric strong {
  font-size: 30px;
  color: #0f172a;
}

.club-stat-card span {
  color: #475569;
  font-size: 12px;
}

.tone-blue { color: #0058be; }
.tone-teal { color: #00687a; }
.tone-violet { color: #6b38d4; }
.tone-amber { color: #c38100; }

.club-filter-shell {
  padding: 22px;
  border-radius: 28px;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 20px 46px rgba(15, 23, 42, 0.05);
  display: grid;
  gap: 16px;
}

.club-filter-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.filter-field {
  display: grid;
  gap: 8px;
}

.filter-field span {
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.filter-field input,
.filter-field select,
.filter-field textarea,
.manual-picker-head input {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  border: 1px solid rgba(203, 213, 225, 0.92);
  background: #f8fbff;
  border-radius: 16px;
  padding: 0 14px;
  min-height: 46px;
  font: inherit;
  color: #0f172a;
}

.filter-field textarea {
  min-height: 110px;
  padding-top: 12px;
  resize: vertical;
}

.filter-field input:focus,
.filter-field select:focus,
.filter-field textarea:focus,
.manual-picker-head input:focus {
  outline: none;
  border-color: rgba(0, 88, 190, 0.35);
  box-shadow: 0 0 0 4px rgba(0, 88, 190, 0.08);
}

.grouping-toolbar,
.customer-section-head,
.side-card-head,
.sms-target-card,
.manual-picker-head,
.modal-head,
.modal-foot,
.table-actions,
.detail-grid,
.side-metrics {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.grouping-toolbar {
  flex-wrap: wrap;
}

.grouping-chips,
.tag-row,
.template-list.horizontal {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.group-chip,
.tag {
  border-radius: 999px;
  padding: 8px 12px;
  background: rgba(219, 234, 254, 0.78);
  color: #0f4c81;
  font-size: 12px;
  font-weight: 700;
}

.group-chip {
  border: 0;
  cursor: pointer;
}

.group-chip small {
  margin-inline-start: 8px;
  opacity: 0.72;
}

.tag.custom {
  background: rgba(237, 233, 254, 0.88);
  color: #6b38d4;
}

.club-body {
  display: grid;
  gap: 18px;
}

.club-body.advanced {
  grid-template-columns: minmax(0, 1.12fr) 340px;
}

.club-main-col,
.club-side-col {
  display: grid;
  gap: 16px;
  align-content: start;
}

.customer-section,
.side-card,
.modal-card {
  border-radius: 28px;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 20px 46px rgba(15, 23, 42, 0.05);
}

.customer-section {
  padding: 20px;
}

.customer-section.highlighted {
  box-shadow:
    0 22px 56px rgba(0, 88, 190, 0.14),
    inset 0 0 0 1px rgba(37, 99, 235, 0.16);
}

.customer-section-head h3,
.modal-head h3,
.side-card-head h4 {
  margin: 0;
  color: #0f172a;
}

.customer-section-head p,
.side-card p,
.modal-kicker,
.empty-inline {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.8;
}

.section-count {
  color: #0f4c81;
  font-size: 12px;
  font-weight: 800;
}

.customer-table-wrap {
  overflow: hidden;
  margin-top: 14px;
}

.customer-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.customer-table th,
.customer-table td {
  padding: 10px 8px;
  text-align: right;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  vertical-align: top;
  white-space: normal;
  font-size: 11px;
  line-height: 1.6;
  word-break: break-word;
}

.customer-table th {
  color: #64748b;
  font-size: 12px;
}

.customer-name-cell {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  min-width: 0;
}

.customer-name-cell > div {
  min-width: 0;
}

.customer-name-cell strong {
  display: block;
  color: #0f172a;
  font-size: 12px;
}

.customer-name-cell small {
  color: #64748b;
  font-size: 11px;
}

.customer-name-cell :deep(.plate-badge) {
  max-width: 100%;
}

.customer-name-cell :deep(.plate-badge.compact) {
  transform: scale(.82);
  transform-origin: right top;
  margin-top: 2px;
  margin-bottom: -8px;
}

.avatar-badge {
  width: 42px;
  height: 42px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #dbeafe, #e0f2fe);
  color: #0058be;
  font-weight: 800;
}

.avatar-badge.large {
  width: 56px;
  height: 56px;
  border-radius: 20px;
  font-size: 18px;
}

.mono-cell {
  font-variant-numeric: tabular-nums;
}

.score-pill,
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.score-pill {
  background: #fff4ce;
  color: #a16207;
}

.icon-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 12px;
  color: #475569;
  background: #eff6ff;
  white-space: nowrap;
  word-break: keep-all;
  flex: 0 0 auto;
}

.icon-action.primary {
  color: #fff;
  background: linear-gradient(135deg, #0058be, #2170e4);
}

.icon-only-action {
  width: 40px;
  height: 40px;
  min-width: 40px;
  padding: 0;
  border-radius: 999px;
}

.action-icon-image {
  width: 18px;
  height: 18px;
  display: block;
  object-fit: contain;
}

.icon-action.primary .action-icon-image {
  filter: brightness(0) invert(1);
}

.table-actions {
  flex-wrap: nowrap;
  justify-content: flex-start;
  gap: 8px;
}

.empty-state {
  min-height: 180px;
  display: grid;
  place-items: center;
  text-align: center;
  gap: 8px;
  color: #64748b;
}

.side-card {
  padding: 18px;
  display: grid;
  gap: 14px;
}

.hero-side-card {
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.12), transparent 24%),
    linear-gradient(180deg, #ffffff, #f5faff);
}

.sms-credit-panel {
  padding: 16px;
  border-radius: 22px;
  background: linear-gradient(135deg, #0f4c81, #0ea5e9);
  color: #fff;
}

.sms-credit-panel strong {
  display: block;
  font-size: 28px;
}

.sms-credit-panel p {
  color: rgba(255, 255, 255, 0.84);
}

.side-metrics {
  align-items: stretch;
}

.side-metrics > div {
  flex: 1;
  padding: 12px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  display: grid;
  gap: 6px;
}

.side-metrics strong {
  font-size: 22px;
}

.suggestion-list,
.template-list,
.sms-log-list,
.assign-list,
.preview-list,
.manual-picker-list {
  display: grid;
  gap: 10px;
}

.suggestion-item,
.template-item,
.manual-picker-item,
.assign-item {
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: #f8fbff;
  border-radius: 18px;
  padding: 14px;
  text-align: right;
  font: inherit;
  cursor: pointer;
}

.template-item {
  border: 0;
}

.sms-log-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
}

.sms-log-main {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.sms-log-head {
  display: grid;
  gap: 3px;
}

.sms-log-head strong {
  color: #0f172a;
}

.sms-log-head small,
.sms-log-meta {
  color: #64748b;
  font-size: 12px;
}

.sms-log-message,
.sms-log-response {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.9;
  font-size: 13px;
}

.sms-log-message {
  color: #1e293b;
}

.sms-log-response {
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(226, 232, 240, 0.9);
  color: #475569;
}

.sms-log-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.template-preview-item {
  display: grid;
  gap: 6px;
}

.template-preview-item strong {
  color: #0f172a;
}

.template-preview-item small {
  color: #64748b;
  line-height: 1.8;
}

.sms-log-row:last-child {
  border-bottom: 0;
}

.sms-log-scroll {
  max-height: 560px;
  overflow-y: auto;
  padding-left: 4px;
}

.status-badge.success {
  background: rgba(34, 197, 94, 0.12);
  color: #166534;
}

.status-badge.pending {
  background: rgba(245, 158, 11, 0.15);
  color: #92400e;
}

.status-badge.failed {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(8px);
  display: grid;
  place-items: center;
  padding: 24px;
}

.modal-card {
  width: min(1180px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
  padding: 24px;
}

.group-builder-modal {
  width: min(1160px, 100%);
}

.customer-import-modal {
  width: min(1040px, 100%);
}

.customer-import-layout {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1fr);
  gap: 16px;
}

.import-guide-panel,
.import-upload-panel,
.import-preview-panel,
.import-payment-panel {
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(248, 250, 252, 0.88);
  padding: 18px;
  display: grid;
  gap: 14px;
}

.import-guide-panel h4,
.import-preview-panel h4 {
  margin: 0;
}

.import-guide-panel p,
.import-payment-panel p {
  margin: 0;
  color: #64748b;
  line-height: 1.9;
}

.import-columns {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.import-columns span {
  padding: 7px 10px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #075985;
  font-size: 12px;
  font-weight: 800;
}

.import-dropzone {
  min-height: 166px;
  border: 1px dashed rgba(0, 88, 190, 0.38);
  background: #ffffff;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  padding: 18px;
  cursor: pointer;
  text-align: center;
}

.import-dropzone input {
  display: none;
}

.import-dropzone strong {
  color: #0f172a;
}

.import-dropzone span {
  color: #64748b;
  font-size: 12px;
}

.import-preview-panel,
.import-payment-panel {
  margin-top: 16px;
}

.import-preview-table-wrap {
  max-height: 280px;
}

.import-errors {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid rgba(239, 68, 68, 0.18);
  background: rgba(254, 242, 242, 0.95);
  color: #991b1b;
}

.import-errors p {
  margin: 0;
  font-size: 12px;
}

.import-payment-panel {
  justify-items: start;
}

.import-payment-panel strong {
  font-size: 28px;
  color: #0058be;
}

.modal-kicker {
  margin: 0 0 8px;
  font-weight: 800;
}

.icon-close {
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 14px;
  background: #eff6ff;
  color: #0f4c81;
  font-size: 28px;
  cursor: pointer;
}

.group-builder-layout,
.sms-layout {
  display: grid;
  gap: 16px;
  margin-top: 18px;
}

.group-builder-layout {
  grid-template-columns: minmax(0, 1.25fr) 320px;
}

.group-builder-form,
.group-preview-card,
.sms-form-col,
.sms-preview-col {
  display: grid;
  gap: 14px;
}

.smart-rule-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.manual-picker {
  display: grid;
  gap: 12px;
}

.manual-picker-list {
  max-height: 360px;
  overflow: auto;
}

.manual-picker-item,
.assign-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.group-preview-card {
  padding: 18px;
  border-radius: 24px;
  background: linear-gradient(180deg, #f5faff, #ffffff);
  border: 1px solid rgba(191, 219, 254, 0.86);
}

.preview-bubble {
  width: 146px;
  aspect-ratio: 1;
  border-radius: 50%;
  margin: 0 auto;
  display: grid;
  place-items: center;
  text-align: center;
  background: radial-gradient(circle at top, #ffffff, #dbeafe);
  box-shadow: inset 0 0 0 8px rgba(255, 255, 255, 0.75);
}

.preview-bubble strong {
  display: block;
  font-size: 32px;
  color: #0058be;
}

.preview-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.95);
}

.assign-modal {
  width: min(620px, 100%);
}

.customer-detail-modal {
  width: min(760px, 100%);
}

.customer-profile-shell {
  display: grid;
  gap: 16px;
  margin-top: 16px;
}

.customer-profile-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px;
  border-radius: 24px;
  background: linear-gradient(135deg, #0f172a, #0f4c81 62%, #38bdf8);
  color: #fff;
}

.customer-profile-title {
  display: flex;
  align-items: center;
  gap: 14px;
}

.customer-profile-title strong,
.customer-profile-score strong {
  display: block;
  font-size: 19px;
}

.customer-profile-title small,
.customer-profile-score span {
  color: rgba(255, 255, 255, 0.84);
  font-size: 11px;
}

.profile-metrics-grid {
  justify-content: flex-start;
  flex-wrap: wrap;
}

.profile-panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.profile-panel {
  min-height: 100%;
}

.plate-tag-row {
  align-items: center;
}

.detail-grid {
  margin-top: 16px;
  flex-wrap: wrap;
  justify-content: flex-start;
}

.detail-metric,
.detail-panel {
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: #f8fbff;
}

.detail-metric {
  min-width: 180px;
  padding: 14px;
  display: grid;
  gap: 6px;
}

.customer-profile-shell .detail-metric small {
  font-size: 10px;
}

.customer-profile-shell .detail-metric strong {
  font-size: 17px;
}

.detail-panel {
  width: 100%;
  padding: 18px;
}

.detail-panel h4 {
  margin: 0 0 10px;
  font-size: 14px;
}

.customer-profile-shell .tag,
.customer-profile-shell .tag.custom {
  font-size: 10px;
  padding: 7px 10px;
}

.sms-modal {
  width: min(1200px, 100%);
}

.template-editor-modal {
  width: min(980px, 100%);
}

.template-editor-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) 320px;
  gap: 16px;
  margin-top: 18px;
}

.template-editor-form,
.template-editor-preview {
  display: grid;
  gap: 14px;
}

.template-token-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.template-preview-box {
  min-height: 220px;
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(191, 219, 254, 0.86);
  background: linear-gradient(180deg, #f8fbff, #ffffff);
}

.template-preview-box p {
  margin: 0;
  color: #0f172a;
  line-height: 2;
}

.danger-btn {
  color: #b91c1c;
  border-color: rgba(239, 68, 68, 0.28);
}

.sms-layout {
  grid-template-columns: minmax(0, 1.1fr) 320px;
}

.sms-target-card,
.sms-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.sms-target-card > div,
.phone-preview,
.bubble {
  border-radius: 20px;
}

.sms-target-card > div {
  padding: 16px;
  background: #f8fbff;
  border: 1px solid rgba(191, 219, 254, 0.9);
}

.danger {
  color: #b91c1c !important;
}

.phone-preview {
  margin-inline: auto;
  width: 290px;
  height: 590px;
  padding: 14px;
  background: #111827;
  border: 8px solid #1f2937;
  position: relative;
  box-shadow: 0 30px 70px rgba(15, 23, 42, 0.35);
}

.phone-notch {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 126px;
  height: 24px;
  background: #1f2937;
  border-radius: 0 0 16px 16px;
}

.phone-screen {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 28px;
  background: #ffffff;
  display: grid;
  grid-template-rows: auto 1fr;
}

.phone-head {
  padding: 38px 16px 14px;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
  display: grid;
  gap: 4px;
}

.phone-chat {
  padding: 18px;
  background: #e7f0ff;
  display: flex;
  align-items: flex-end;
}

.bubble {
  max-width: 90%;
  padding: 14px 16px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
  display: grid;
  gap: 8px;
}

.bubble p,
.bubble small {
  margin: 0;
}

.bubble p {
  line-height: 1.9;
  color: #0f172a;
}

.modal-foot {
  margin-top: 18px;
  justify-content: flex-end;
}

@media (max-width: 1280px) {
  .club-hero,
  .club-body.advanced,
  .group-builder-layout,
  .customer-import-layout,
  .sms-layout,
  .template-editor-layout,
  .profile-panel-grid {
    grid-template-columns: 1fr;
  }

  .club-stats-grid,
  .club-filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .club-hero,
  .club-filter-shell,
  .customer-section,
  .modal-card {
    padding: 16px;
  }

  .club-hero-copy h2 {
    font-size: 22px;
  }

  .club-hero-copy p,
  .hero-kicker,
  .section-count,
  .customer-table th,
  .customer-table td,
  .group-chip,
  .group-chip small,
  .score-pill,
  .status-badge,
  .customer-name-cell small {
    font-size: 10px;
  }

  .customer-section-head h3,
  .modal-head h3,
  .side-card-head h3,
  .hero-side-card strong,
  .sms-credit-panel strong {
    font-size: 18px;
  }

  .club-stats-grid article strong,
  .side-metrics strong {
    font-size: 16px;
  }

  .club-hero-actions button,
  .customer-section-actions button,
  .table-actions button,
  .icon-action,
  .group-chip {
    font-size: 10px;
    padding: 7px 9px;
  }

  .icon-action {
    min-width: max-content;
  }

  .club-stats-grid,
  .club-filter-grid,
  .smart-rule-grid,
  .sms-target-card,
  .sms-meta-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .grouping-toolbar,
  .customer-section-head,
  .modal-head,
  .modal-foot {
    flex-direction: column;
    align-items: stretch;
  }

  .customer-section-actions,
  .club-hero-actions,
  .side-card-head,
  .sms-log-row,
  .preview-list-item,
  .manual-picker-item,
  .assign-item {
    flex-direction: column;
    align-items: stretch;
  }

  .customer-table th,
  .customer-table td {
    padding-inline: 8px;
    padding-block: 10px;
    font-size: 10px;
  }

  .table-actions {
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    flex-wrap: nowrap;
    gap: 6px;
  }

  .phone-preview {
    width: min(280px, 100%);
    height: 560px;
  }
}

@media (max-width: 480px) {
  .club-hero,
  .club-filter-shell,
  .customer-section,
  .modal-card,
  .side-card {
    padding: 12px;
  }

  .club-hero-copy h2 {
    font-size: 18px;
  }

  .club-hero-copy p,
  .hero-kicker,
  .section-count,
  .customer-table th,
  .customer-table td,
  .group-chip,
  .group-chip small,
  .score-pill,
  .status-badge,
  .customer-name-cell small,
  .sms-log-row,
  .preview-list-item,
  .assign-item,
  .manual-picker-item {
    font-size: 9px;
  }

  .customer-section-head h3,
  .modal-head h3,
  .side-card-head h3,
  .hero-side-card strong,
  .sms-credit-panel strong {
    font-size: 15px;
  }

  .club-stats-grid article strong,
  .side-metrics strong,
  .customer-name-cell strong {
    font-size: 13px;
  }

  .club-hero-actions button,
  .customer-section-actions button,
  .table-actions button,
  .icon-action,
  .group-chip {
    font-size: 9px;
    padding: 6px 8px;
  }

  .icon-action {
    min-width: max-content;
  }

  .customer-table th,
  .customer-table td {
    padding-inline: 6px;
    padding-block: 8px;
    font-size: 9px;
  }

  .club-stats-grid,
  .club-filter-grid,
  .smart-rule-grid,
  .sms-target-card,
  .sms-meta-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .avatar-badge {
    width: 34px;
    height: 34px;
    border-radius: 12px;
    font-size: 10px;
  }

  .customer-profile-hero {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
