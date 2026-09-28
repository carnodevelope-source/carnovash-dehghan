<template>
  <AppShell title="گزارشات" subtitle="تحلیل مالی و عملیاتی">
    <div class="reports-content">
      <section class="range-bar">
        <button
          v-for="option in rangeOptions"
          :key="option.key"
          class="range-chip"
          :class="{ active: filters.rangeKey === option.key }"
          @click="setRange(option.key)"
        >
          <IconlyIcon :name="option.icon" size="sm" />
          {{ option.label }}
        </button>
      </section>

      <section class="filters-card">
        <div class="filters-top-row">
          <div class="field search-field">
            <span><IconlyIcon name="search" size="xs" />جستجو</span>
            <input v-model="filters.q" type="text" placeholder="راننده، شماره، نیرو، مدل یا پلاک..." />
          </div>
          <div class="field">
            <span><IconlyIcon name="calendar" size="xs" />شروع بازه (شمسی)</span>
            <BaseDatePicker v-model="filters.startJalali" placeholder="1405/01/01" />
          </div>
          <div class="field">
            <span><IconlyIcon name="calendar" size="xs" />پایان بازه (شمسی)</span>
            <BaseDatePicker v-model="filters.endJalali" placeholder="1405/01/30" />
          </div>
          <div class="field">
            <span><IconlyIcon name="users3" size="xs" />نیرو</span>
            <select v-model="filters.workerId">
              <option value="">همه نیروها</option>
              <option v-for="worker in workers" :key="worker.id" :value="String(worker.id)">{{ worker.full_name }}</option>
            </select>
          </div>
          <div class="field">
            <span><IconlyIcon name="calendar" size="xs" />ماه بیمه</span>
            <select v-model="filters.insuranceMonthJalali">
              <option v-for="item in insuranceMonthOptions" :key="`filter-${item.value}`" :value="item.value">{{ item.label }}</option>
            </select>
          </div>
        </div>

        <div class="plate-filter-bar">
          <span class="plate-filter-label"><IconlyIcon name="filter" size="xs" />پلاک</span>
          <select v-model="filters.plateType" class="plate-type-inline" aria-label="نوع وسیله">
            <option value="">همه</option>
            <option value="car">خودرو</option>
            <option value="motorcycle">موتور سیکلت</option>
          </select>
          <PlateEditor
            class="plate-filter-editor"
            dense
            :plate-left="filters.plateLeft"
            :plate-letter="filters.plateLetter"
            :plate-mid="filters.plateMid"
            :plate-right="filters.plateRight"
            :plate-type="filters.plateType || 'car'"
            :show-type-switch="false"
            :show-anonymous-toggle="false"
            :show-piece-wash-toggle="false"
            @update:plateLeft="filters.plateLeft = $event"
            @update:plateLetter="filters.plateLetter = $event"
            @update:plateMid="filters.plateMid = $event"
            @update:plateRight="filters.plateRight = $event"
            @update:plateType="filters.plateType = $event"
          />
          <button
            type="button"
            class="plate-clear-btn"
            :disabled="!hasPlateFilter"
            @click="clearPlateFilter"
          >
            پاک کردن
          </button>
          <div class="filters-actions">
            <button class="secondary-btn clear-btn btn-with-icon" @click="resetFilters"><IconlyIcon name="filter" size="sm" />حذف فیلتر</button>
            <section class="export-studio-actions">
              <button class="export-action-btn csv" :disabled="exportState.csvLoading" @click="exportCsv">
                <IconlyIcon name="document" size="sm" />
                {{ exportState.csvLoading ? 'در حال آماده‌سازی CSV...' : 'خروجی CSV' }}
              </button>
              <button class="export-action-btn pdf" :disabled="exportState.pdfLoading" @click="exportPdf">
                <IconlyIcon name="download" size="sm" />
                {{ exportState.pdfLoading ? (activeTab === 'worker' ? 'در حال آماده‌سازی...' : 'در حال ساخت PDF...') : (activeTab === 'worker' ? 'خروجی / چاپ' : 'خروجی PDF') }}
              </button>
            </section>
          </div>
        </div>
      </section>

      <section v-if="visibleSummaryCards.length" class="summary-grid">
        <article v-for="card in visibleSummaryCards" :key="card.key" class="kpi-card">
          <p>{{ card.label }}</p>
          <strong>{{ card.value }}</strong>
          <small v-if="card.hint" class="kpi-hint">{{ card.hint }}</small>
        </article>
      </section>

      <section class="tabs-bar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="chip"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <IconlyIcon :name="tab.icon" size="sm" />
          <span>{{ tab.label }}</span>
          <HelpTip v-if="tab.help" :text="tab.help" />
        </button>
      </section>

      <section ref="reportExportRef" class="table-card">
        <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>
        <p v-if="syncNotice" class="sync-notice">{{ syncNotice }}</p>

        <template v-if="activeTab === 'overall'">
          <h3>گزارش کل</h3>
          <div class="table-wrap">
            <table>
              <thead><tr><th>ردیف</th><th>نام راننده</th><th>جنسیت</th><th>شماره</th><th>مدل</th><th>رنگ</th><th class="col-plate">پلاک</th><th>وضعیت</th><th>حق کارواش</th><th>حق نیرو</th><th>تخفیف</th><th>مالیات</th><th>انعام</th><th>نام نیرو</th><th>خدمات</th><th>تاریخ</th></tr></thead>
              <tbody>
                <template v-for="row in pagedTables.overall.rows" :key="`o-${serviceRowKey(row)}`">
                  <tr class="clickable-row" :class="{ expanded: isServicesExpanded(row) }" @click="openVehicleDetail(row.vehicle_id)">
                    <td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ formatGender(row.driver_gender) }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.car_color || '-' }}</td><td class="col-plate"><span class="report-plate-cell"><IranPlateMark
                      :plate-number="row.plate_number"
                      :plate-left="row.plate_left"
                      :plate-letter="row.plate_letter"
                      :plate-mid="row.plate_mid"
                      :plate-right="row.plate_right"
                      :plate-type="row.plate_type || 'car'"
                      compact
                    /></span></td><td>{{ formatStatus(row.status) }}</td><td>{{ money(row.carwash_share) }}</td><td>{{ money(row.worker_share) }}</td><td>{{ money(row.discount_total) }}</td><td>{{ money(row.tax_total) }}</td><td>{{ money(row.tip_amount) }}</td><td>{{ row.worker_name }}</td><td><div class="services-preview-cell"><span class="services-preview-text">{{ servicesPreview(row.services) }}</span><button v-if="hasExpandableServices(row.services)" type="button" class="services-toggle-btn" :class="{ active: isServicesExpanded(row) }" @click.stop="toggleServicesRow(row)"><span class="services-toggle-dots">•••</span></button></div></td><td>{{ dateTime(row.created_at) }}</td>
                  </tr>
                  <tr v-if="isServicesExpanded(row)" class="services-expanded-row">
                    <td colspan="16">
                      <div class="services-expanded-box">
                        <strong>همه خدمات انجام‌شده</strong>
                        <p>{{ normalizeServicesValue(row.services) }}</p>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
          <ReportPager
            v-if="!exportAllRows"
            :page="pagedTables.overall.page"
            :pages="pagedTables.overall.pages"
            :total="pagedTables.overall.total"
            :from="pagedTables.overall.from"
            :to="pagedTables.overall.to"
            @update:page="setTablePage('overall', $event)"
          />
        </template>

        <template v-else-if="activeTab === 'carwash'">
          <h3>گزارش حق کارواش</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>رنگ</th><th class="col-plate">پلاک</th><th>حق کارواش</th><th>نام نیرو</th><th>تاریخ</th></tr></thead><tbody>
            <tr v-for="row in pagedTables.carwash.rows" :key="`c-${row.row}`" class="clickable-row" @click="openVehicleDetail(row.vehicle_id)"><td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.car_color || '-' }}</td><td class="col-plate"><span class="report-plate-cell"><IranPlateMark
                      :plate-number="row.plate_number"
                      :plate-left="row.plate_left"
                      :plate-letter="row.plate_letter"
                      :plate-mid="row.plate_mid"
                      :plate-right="row.plate_right"
                      :plate-type="row.plate_type || 'car'"
                      compact
                    /></span></td><td>{{ money(row.carwash_share) }}</td><td>{{ row.worker_name }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
          </tbody></table></div>
          <ReportPager
            v-if="!exportAllRows"
            :page="pagedTables.carwash.page"
            :pages="pagedTables.carwash.pages"
            :total="pagedTables.carwash.total"
            :from="pagedTables.carwash.from"
            :to="pagedTables.carwash.to"
            @update:page="setTablePage('carwash', $event)"
          />
        </template>

        <template v-else-if="activeTab === 'worker'">
          <div class="worker-head">
            <h3>گزارش حق نیرو</h3>
            <div v-if="selectedWorkerSummary" class="action-row">
              <button class="primary-btn btn-with-icon" @click="openPayoutModal('wage')"><IconlyIcon name="wallet" size="sm" />{{ payoutButtonLabel }}</button>
              <button class="primary-btn btn-with-icon" @click="openPayoutModal('advance')"><IconlyIcon name="wallet" size="sm" />{{ advancePayoutButtonLabel }}</button>
              <button class="primary-btn btn-with-icon" @click="openPayoutModal('insurance')"><IconlyIcon name="wallet" size="sm" />{{ insurancePayoutButtonLabel }}</button>
            </div>
          </div>
          <div v-if="selectedWorkerSummary" class="worker-summary-grid">
            <article class="payout-card"><p>نوع پرداخت</p><strong>{{ workerPaymentTypeLabel(selectedWorkerSummary.payment_type) }}</strong></article>
            <article v-if="selectedWorkerSummary.payment_type === 'hourly'" class="payout-card"><p>ساعت کاری</p><strong>{{ workHoursLabel(selectedWorkerSummary.attendance_hours) }}</strong></article>
            <article v-if="selectedWorkerSummary.payment_type === 'hourly'" class="payout-card"><p>نرخ ساعتی</p><strong>{{ money(selectedWorkerSummary.hourly_wage) }}</strong></article>
            <article class="payout-card"><p>جمع حق نیرو (دوره)</p><strong>{{ money(selectedWorkerSummary.wage_total) }}</strong></article>
            <article class="payout-card"><p>پاداش</p><strong>{{ money(selectedWorkerSummary.bonus_total) }}</strong></article>
            <article class="payout-card"><p>جریمه</p><strong>{{ money(selectedWorkerSummary.penalty_total) }}</strong></article>
            <article class="payout-card"><p>حقوق پرداخت‌شده</p><strong>{{ money(selectedWorkerSummary.wage_paid_total) }}</strong></article>
            <article class="payout-card"><p>مساعده پرداخت‌شده</p><strong>{{ money(selectedWorkerSummary.advance_paid_total) }}</strong></article>
            <article class="payout-card"><p>مانده قابل پرداخت حقوق</p><strong>{{ money(selectedWorkerSummary.payable_total) }}</strong></article>
            <article class="payout-card"><p>حق بیمه هر ماه</p><strong>{{ money(selectedWorkerSummary.insurance_monthly_amount) }}</strong></article>
            <article class="payout-card"><p>پرداخت بیمه این ماه</p><strong>{{ money(selectedWorkerSummary.insurance_selected_month_paid_total) }}</strong></article>
            <article class="payout-card"><p>مانده بیمه این ماه</p><strong>{{ money(selectedWorkerSummary.insurance_selected_month_balance) }}</strong></article>
            <article class="payout-card"><p>جمع انعام (دوره)</p><strong>{{ money(selectedWorkerSummary.tip_total) }}</strong></article>
            <article class="payout-card"><p>انعام پرداخت‌شده</p><strong>{{ money(selectedWorkerSummary.tip_paid_total) }}</strong></article>
            <article class="payout-card"><p>مانده انعام قابل پرداخت</p><strong>{{ money(selectedWorkerSummary.tip_balance) }}</strong></article>
          </div>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>مدل</th><th>رنگ</th><th class="col-plate">پلاک</th><th>جمع خدمات</th><th>محصولات</th><th>انعام</th><th>حق نیرو</th><th>نام نیرو</th><th>تاریخ</th></tr></thead><tbody>
            <tr v-for="row in pagedTables.worker.rows" :key="`w-${row.row}`" class="clickable-row" @click="openVehicleDetail(row.vehicle_id)"><td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.car_model }}</td><td>{{ row.car_color || '-' }}</td><td class="col-plate"><span class="report-plate-cell"><IranPlateMark
                      :plate-number="row.plate_number"
                      :plate-left="row.plate_left"
                      :plate-letter="row.plate_letter"
                      :plate-mid="row.plate_mid"
                      :plate-right="row.plate_right"
                      :plate-type="row.plate_type || 'car'"
                      compact
                    /></span></td><td>{{ money(row.service_total) }}</td><td>{{ money(row.products_total) }}</td><td>{{ money(row.tip_amount) }}</td><td>{{ money(row.worker_share) }}</td><td>{{ row.worker_name }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
          </tbody></table></div>
          <ReportPager
            v-if="!exportAllRows"
            :page="pagedTables.worker.page"
            :pages="pagedTables.worker.pages"
            :total="pagedTables.worker.total"
            :from="pagedTables.worker.from"
            :to="pagedTables.worker.to"
            @update:page="setTablePage('worker', $event)"
          />
          <div v-if="selectedWorkerSummary" class="transactions-shell">
            <div class="worker-head">
              <h3>تراکنش‌های مالی {{ selectedWorkerSummary.worker_name }}</h3>
              <div class="action-row">
                <button class="secondary-btn btn-with-icon" @click="openAdjustmentModal('bonus')"><IconlyIcon name="plus" size="sm" />ثبت پاداش</button>
                <button class="secondary-btn danger-soft btn-with-icon" @click="openAdjustmentModal('penalty')"><IconlyIcon name="trash" size="sm" />ثبت جریمه</button>
              </div>
            </div>
            <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نوع</th><th>مبلغ</th><th>ماه بیمه</th><th>سفارش</th><th>توضیح</th><th>زمان</th><th>عملیات</th></tr></thead><tbody>
              <tr v-for="row in pagedTables.workerTx.rows" :key="row.id">
                <td>{{ faNumber(row._pageRow) }}</td>
                <td>{{ payoutKindLabel(row.kind) }}</td>
                <td>{{ money(row.amount) }}</td>
                <td>{{ row.reference_month || '-' }}</td>
                <td>{{ row.vehicle_job_id || '-' }}</td>
                <td>{{ row.note || '-' }}</td>
                <td>{{ dateTime(row.created_at) }}</td>
                <td>
                  <button type="button" class="secondary-btn table-edit-btn" @click.stop="openEditTransaction(row)">ویرایش</button>
                </td>
              </tr>
              <tr v-if="!selectedWorkerTransactions.length"><td colspan="8">تراکنشی ثبت نشده است.</td></tr>
            </tbody></table></div>
            <ReportPager
              v-if="!exportAllRows"
              :page="pagedTables.workerTx.page"
              :pages="pagedTables.workerTx.pages"
              :total="pagedTables.workerTx.total"
              :from="pagedTables.workerTx.from"
              :to="pagedTables.workerTx.to"
              @update:page="setTablePage('workerTx', $event)"
            />
          </div>
        </template>

        <template v-else-if="activeTab === 'tips'">
          <h3>گزارش انعام</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>رنگ</th><th class="col-plate">پلاک</th><th>انعام</th><th>نام نیرو</th><th>کالا</th><th>تاریخ</th></tr></thead><tbody>
            <tr v-for="row in pagedTables.tips.rows" :key="`t-${row.row}`" class="clickable-row" @click="openVehicleDetail(row.vehicle_id)"><td>{{ row.row }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.car_color || '-' }}</td><td class="col-plate"><span class="report-plate-cell"><IranPlateMark
                      :plate-number="row.plate_number"
                      :plate-left="row.plate_left"
                      :plate-letter="row.plate_letter"
                      :plate-mid="row.plate_mid"
                      :plate-right="row.plate_right"
                      :plate-type="row.plate_type || 'car'"
                      compact
                    /></span></td><td>{{ money(row.tip_amount) }}</td><td>{{ row.worker_name }}</td><td>{{ row.products || '-' }}</td><td>{{ dateTime(row.created_at) }}</td></tr>
          </tbody></table></div>
          <ReportPager
            v-if="!exportAllRows"
            :page="pagedTables.tips.page"
            :pages="pagedTables.tips.pages"
            :total="pagedTables.tips.total"
            :from="pagedTables.tips.from"
            :to="pagedTables.tips.to"
            @update:page="setTablePage('tips', $event)"
          />
        </template>

        <template v-else-if="activeTab === 'products'">
          <h3>گزارش محصولات</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>محصول</th><th>تعداد</th><th>فی فروش</th><th>مبلغ فروش</th><th>بهای تمام‌شده</th><th>سود</th><th>راننده</th><th class="col-plate">پلاک</th><th>نام نیرو</th><th>تاریخ</th></tr></thead><tbody>
            <tr v-for="row in pagedTables.products.rows" :key="`p-${row.row}-${row.product_id || 0}`" class="clickable-row" @click="openVehicleDetail(row.vehicle_id)">
              <td>{{ row.row }}</td>
              <td>{{ row.product_name }}</td>
              <td>{{ faNumber(row.quantity) }}</td>
              <td>{{ money(row.unit_price) }}</td>
              <td>{{ money(row.sale_amount) }}</td>
              <td>{{ money(row.cost_amount) }}</td>
              <td>{{ money(row.profit_amount) }}</td>
              <td>{{ row.driver_name }}</td>
              <td class="col-plate"><span class="report-plate-cell"><IranPlateMark
                      :plate-number="row.plate_number"
                      :plate-left="row.plate_left"
                      :plate-letter="row.plate_letter"
                      :plate-mid="row.plate_mid"
                      :plate-right="row.plate_right"
                      :plate-type="row.plate_type || 'car'"
                      compact
                    /></span></td>
              <td>{{ row.worker_name || '-' }}</td>
              <td>{{ dateTime(row.created_at) }}</td>
            </tr>
            <tr v-if="!pagedTables.products.rows.length"><td colspan="11">در این بازه فروش محصولی ثبت نشده است.</td></tr>
          </tbody></table></div>
          <ReportPager
            v-if="!exportAllRows"
            :page="pagedTables.products.page"
            :pages="pagedTables.products.pages"
            :total="pagedTables.products.total"
            :from="pagedTables.products.from"
            :to="pagedTables.products.to"
            @update:page="setTablePage('products', $event)"
          />
        </template>

        <template v-else-if="activeTab === 'discount'">
          <h3>گزارش تخفیف</h3>
          <p class="discount-tab-note">
            تخفیف امتیاز مشتری همان تخفیف باشگاه مشتریان است که بر اساس امتیاز و دفعات مراجعه پلاک در بازه انتخابی ثبت شده است.
          </p>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام راننده</th><th>شماره</th><th>مدل</th><th>رنگ</th><th class="col-plate">پلاک</th><th>تخفیف امتیاز / مراجعه</th><th>تخفیف مجموعه</th><th>تخفیف دستی</th><th>جمع تخفیف</th><th>تاریخ</th></tr></thead><tbody>
            <tr v-for="row in pagedTables.discount.rows" :key="`d-${row.row}`" class="clickable-row" @click="openVehicleDetail(row.vehicle_id)">
              <td>{{ row.row }}</td>
              <td>{{ row.driver_name }}</td>
              <td>{{ row.driver_phone }}</td>
              <td>{{ row.car_model }}</td>
              <td>{{ row.car_color || '-' }}</td>
              <td class="col-plate"><span class="report-plate-cell"><IranPlateMark
                :plate-number="row.plate_number"
                :plate-left="row.plate_left"
                :plate-letter="row.plate_letter"
                :plate-mid="row.plate_mid"
                :plate-right="row.plate_right"
                :plate-type="row.plate_type || 'car'"
                compact
              /></span></td>
              <td>{{ money(row.loyalty_discount_total) }}</td>
              <td>{{ money(row.facility_discount_total) }}</td>
              <td>{{ money(row.manual_discount_total) }}</td>
              <td>{{ money(row.discount_total) }}</td>
              <td>{{ dateTime(row.created_at) }}</td>
            </tr>
            <tr v-if="!data.discount_report.length"><td colspan="11">در این بازه تخفیفی ثبت نشده است.</td></tr>
          </tbody></table></div>
          <ReportPager
            v-if="!exportAllRows"
            :page="pagedTables.discount.page"
            :pages="pagedTables.discount.pages"
            :total="pagedTables.discount.total"
            :from="pagedTables.discount.from"
            :to="pagedTables.discount.to"
            @update:page="setTablePage('discount', $event)"
          />
        </template>

        <template v-else-if="activeTab === 'revenue'">
          <h3>گزارش درآمد</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>تاریخ</th><th>راننده</th><th>شماره</th><th>مدل خودرو</th><th>رنگ</th><th class="col-plate">پلاک</th><th>روش پرداخت</th><th>وضعیت پرداخت</th><th>خدمات</th><th>محصولات</th><th>تخفیف</th><th>انعام</th><th>مالیات</th><th>مبلغ نهایی</th><th>وصول شده</th><th>مانده</th><th>شماره چک</th><th>سررسید</th></tr></thead><tbody>
            <tr v-for="row in pagedTables.revenue.rows" :key="`r-${row.row}`" class="clickable-row" @click="openVehicleDetail(row.vehicle_id)"><td>{{ row.row }}</td><td>{{ dateTime(row.created_at) }}</td><td>{{ row.driver_name }}</td><td>{{ row.driver_phone }}</td><td>{{ row.car_model }}</td><td>{{ row.car_color || '-' }}</td><td class="col-plate"><span class="report-plate-cell"><IranPlateMark
                      :plate-number="row.plate_number"
                      :plate-left="row.plate_left"
                      :plate-letter="row.plate_letter"
                      :plate-mid="row.plate_mid"
                      :plate-right="row.plate_right"
                      :plate-type="row.plate_type || 'car'"
                      compact
                    /></span></td><td>{{ paymentMethodLabel(row.payment_method) }}</td><td>{{ paymentStateLabel(row.payment_status) }}</td><td>{{ money(row.service_amount) }}</td><td>{{ money(row.product_amount) }}</td><td>{{ money(row.discount_amount) }}</td><td>{{ money(row.tip_amount) }}</td><td>{{ money(row.tax_amount) }}</td><td>{{ money(row.final_total) }}</td><td>{{ money(row.received_amount) }}</td><td>{{ money(row.outstanding_amount) }}</td><td>{{ row.cheque_number || '-' }}</td><td>{{ dateOnly(row.reminder_due_at) }}</td></tr>
          </tbody></table></div>
          <ReportPager
            v-if="!exportAllRows"
            :page="pagedTables.revenue.page"
            :pages="pagedTables.revenue.pages"
            :total="pagedTables.revenue.total"
            :from="pagedTables.revenue.from"
            :to="pagedTables.revenue.to"
            @update:page="setTablePage('revenue', $event)"
          />
        </template>

        <template v-else-if="activeTab === 'attendance'">
          <h3>گزارش ورود و خروج</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th>نام پرسنل</th><th>نوع رویداد</th><th>منبع ثبت</th><th>زمان</th></tr></thead><tbody>
            <tr v-for="row in pagedTables.attendance.rows" :key="`a-${row.row}`"><td>{{ row.row }}</td><td>{{ row.worker_name }}</td><td>{{ row.event_type === 'in' ? 'ورود' : 'خروج' }}</td><td>{{ row.source === 'manager' ? 'مدیر' : row.source === 'link' ? 'لینک پرسنل' : (row.source || '-') }}</td><td>{{ dateTime(row.event_at) }}</td></tr>
            <tr v-if="!data.attendance_report.length"><td colspan="5">رکوردی برای این بازه پیدا نشد.</td></tr>
          </tbody></table></div>
          <ReportPager
            v-if="!exportAllRows"
            :page="pagedTables.attendance.page"
            :pages="pagedTables.attendance.pages"
            :total="pagedTables.attendance.total"
            :from="pagedTables.attendance.from"
            :to="pagedTables.attendance.to"
            @update:page="setTablePage('attendance', $event)"
          />
        </template>

        <template v-else-if="activeTab === 'blacklist'">
          <h3>گزارش لیست سیاه</h3>
          <div class="table-wrap"><table><thead><tr><th>ردیف</th><th class="col-plate">پلاک</th><th>نوع وسیله</th><th>توضیح</th><th>ثبت کننده</th><th>تاریخ ثبت</th></tr></thead><tbody>
            <tr
              v-for="row in pagedTables.blacklist.rows"
              :key="`b-${row.id || row.row}`"
              class="clickable-row"
              @click="openBlacklistRow(row)"
            >
              <td>{{ row.row }}</td>
              <td class="col-plate"><span class="report-plate-cell"><IranPlateMark
                      :plate-number="row.plate_number"
                      :plate-left="row.plate_left"
                      :plate-letter="row.plate_letter"
                      :plate-mid="row.plate_mid"
                      :plate-right="row.plate_right"
                      :plate-type="row.plate_type || 'car'"
                      compact
                    /></span></td>
              <td>{{ row.plate_type === 'motorcycle' ? 'موتور سیکلت' : 'خودرو' }}</td>
              <td>{{ row.note || '-' }}</td>
              <td>{{ row.blocked_by_name || '-' }}</td>
              <td>{{ dateTime(row.created_at) }}</td>
            </tr>
            <tr v-if="!data.blacklist_report.length"><td colspan="6">پلاکی در لیست سیاه برای این بازه پیدا نشد.</td></tr>
          </tbody></table></div>
          <ReportPager
            v-if="!exportAllRows"
            :page="pagedTables.blacklist.page"
            :pages="pagedTables.blacklist.pages"
            :total="pagedTables.blacklist.total"
            :from="pagedTables.blacklist.from"
            :to="pagedTables.blacklist.to"
            @update:page="setTablePage('blacklist', $event)"
          />
        </template>

      </section>
    </div>
  </AppShell>

  <VehicleDetailsModal
    :open="vehicleModal.open"
    :loading="vehicleModal.loading"
    :vehicle="vehicleModal.data"
    title="جزئیات کامل خودرو"
    @close="closeVehicleModal"
    @cancel="cancelVehicle"
    @block-plate="blockVehiclePlate"
    @unblock-plate="unblockVehiclePlate"
  />

  <div v-if="payoutModal.open" class="modal-overlay" @click.self="closePayoutModal">
    <section class="modal-panel action-panel">
      <header class="modal-head">
        <h3>
          {{
            payoutModal.replaceId
              ? (
                payoutModal.target === 'advance'
                  ? 'ویرایش مساعده'
                  : payoutModal.target === 'insurance'
                    ? 'ویرایش حق بیمه'
                    : payoutModal.target === 'tip'
                      ? 'ویرایش انعام'
                      : 'ویرایش پرداخت حقوق'
              )
              : (
                payoutModal.target === 'advance'
                  ? 'پرداخت مساعده'
                  : payoutModal.target === 'insurance'
                    ? 'پرداخت حق بیمه'
                    : 'پرداخت حقوق'
              )
          }}
          {{ selectedWorkerSummary?.worker_name || '' }}
        </h3>
        <button class="close-btn" @click="closePayoutModal">✕</button>
      </header>
      <div class="modal-body">
        <template v-if="payoutModal.target === 'advance'">
          <label><span>مبلغ مساعده (تومان)</span><input :value="moneyInputValue(payoutModal.amount)" type="text" inputmode="numeric" @input="payoutModal.amount = parseMoneyInput($event.target.value)" /></label>
          <p class="helper-note">مساعده در تراکنش‌های مالی ثبت می‌شود و از مانده قابل پرداخت حقوق کم می‌شود.</p>
        </template>
        <template v-else>
          <label><span>نوع پرداخت</span><select v-model="payoutModal.mode"><option value="full">{{ payoutModal.target === 'insurance' ? 'کل حق بیمه' : payoutModal.target === 'tip' ? 'کل انعام' : 'کل حقوق' }}</option><option value="partial">{{ payoutModal.target === 'insurance' ? 'بخشی از حق بیمه' : payoutModal.target === 'tip' ? 'بخشی از انعام' : 'بخشی از حقوق' }}</option></select></label>
          <label v-if="payoutModal.target === 'insurance'">
            <span>ماه بیمه (شمسی)</span>
            <select v-model="payoutModal.insuranceMonth">
              <option value="" disabled>انتخاب ماه</option>
              <option v-for="item in insuranceMonthOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
          <label v-if="payoutModal.mode === 'partial'"><span>مبلغ (تومان)</span><input :value="moneyInputValue(payoutModal.amount)" type="text" inputmode="numeric" @input="payoutModal.amount = parseMoneyInput($event.target.value)" /></label>
          <p v-if="payoutModal.mode === 'partial'" class="helper-note" :class="{ error: payoutValidationMessage }">
            {{ payoutValidationMessage || `مانده قابل پرداخت: ${money(payoutModalMaxAmount)}. ${payoutModal.replaceId ? 'مبلغ می‌تواند تا سقف مانده باشد.' : 'مبلغ باید کمتر از مانده باشد.'}` }}
          </p>
          <label v-if="payoutModal.target === 'wage' && !payoutModal.replaceId" class="checkbox-row">
            <input v-model="payoutModal.includeTip" type="checkbox" />
            <span>پرداخت انعام هم انجام شود (مانده انعام: {{ money(selectedWorkerSummary?.tip_balance || 0) }})</span>
          </label>
        </template>
        <p v-if="payoutSubmitError" class="helper-note error">
          {{ payoutSubmitError }}
        </p>
        <label><span>توضیح</span><input v-model="payoutModal.note" type="text" /></label>
        <button class="primary-btn" :disabled="payoutModal.submitting || !canSubmitPayout" @click="submitPayout">{{ payoutModal.submitting ? 'در حال ثبت...' : (payoutModal.replaceId ? 'ثبت ویرایش' : 'ثبت پرداخت') }}</button>
      </div>
    </section>
  </div>

  <div v-if="adjustmentModal.open" class="modal-overlay" @click.self="closeAdjustmentModal">
    <section class="modal-panel action-panel">
      <header class="modal-head">
        <h3>{{ adjustmentModal.replaceId ? 'ویرایش' : 'ثبت' }} {{ adjustmentModal.kind === 'bonus' ? 'پاداش' : 'جریمه' }} برای {{ selectedWorkerSummary?.worker_name || '' }}</h3>
        <button class="close-btn" @click="closeAdjustmentModal">✕</button>
      </header>
      <div class="modal-body">
        <label><span>مبلغ (تومان)</span><input :value="moneyInputValue(adjustmentModal.amount)" type="text" inputmode="numeric" @input="adjustmentModal.amount = parseMoneyInput($event.target.value)" /></label>
        <label><span>توضیح</span><input v-model.trim="adjustmentModal.note" type="text" placeholder="ثبت دلیل پاداش یا جریمه" /></label>
        <button class="primary-btn" :disabled="adjustmentModal.submitting" @click="submitAdjustment">{{ adjustmentModal.submitting ? 'در حال ثبت...' : (adjustmentModal.replaceId ? 'ثبت ویرایش' : 'ثبت') }}</button>
      </div>
    </section>
  </div>

  <div v-if="pdfFormatModal.open" class="modal-overlay" @click.self="closePdfFormatModal">
    <section class="modal-panel pdf-format-panel">
      <header class="modal-head">
        <h3>{{ activeTab === 'worker' ? 'انتخاب قالب خروجی' : 'انتخاب قالب PDF' }}</h3>
        <button class="close-btn" @click="closePdfFormatModal">✕</button>
      </header>
      <div class="pdf-format-body">
        <button class="pdf-format-option" @click="selectPdfFormat('a4')">
          <strong>A4</strong>
          <span>خروجی گزارش افقی</span>
        </button>
        <button class="pdf-format-option" @click="selectPdfFormat('a5')">
          <strong>A5</strong>
          <span>خروجی فشرده‌تر</span>
        </button>
        <button
          v-if="activeTab === 'worker'"
          class="pdf-format-option receipt"
          :disabled="!selectedWorkerSummary?.worker_id"
          @click="selectPdfFormat('receipt')"
        >
          <strong>فیش</strong>
          <span>{{ selectedWorkerSummary?.worker_id ? 'چاپ مستقیم مثل فاکتور' : 'اول نیرو را انتخاب کنید' }}</span>
        </button>
      </div>
    </section>
  </div>

  <div v-if="blacklistModal.open" class="modal-overlay" @click.self="closeBlacklistModal">
    <section class="modal-panel action-panel">
      <header class="modal-head">
        <h3>جزئیات پلاک بلاک‌شده</h3>
        <button class="close-btn" @click="closeBlacklistModal">✕</button>
      </header>
      <div class="modal-body blacklist-modal-body">
        <div class="blacklist-plate-preview">
          <PlateBadge
            :plate-number="blacklistModal.row?.plate_number"
            :plate-left="blacklistModal.row?.plate_left"
            :plate-letter="blacklistModal.row?.plate_letter"
            :plate-mid="blacklistModal.row?.plate_mid"
            :plate-right="blacklistModal.row?.plate_right"
            :plate-type="blacklistModal.row?.plate_type || 'car'"
            compact
          />
        </div>
        <p><span>نوع وسیله</span><strong>{{ blacklistModal.row?.plate_type === 'motorcycle' ? 'موتور سیکلت' : 'خودرو' }}</strong></p>
        <p><span>توضیح</span><strong>{{ blacklistModal.row?.note || '-' }}</strong></p>
        <p><span>ثبت‌کننده</span><strong>{{ blacklistModal.row?.blocked_by_name || '-' }}</strong></p>
        <p><span>تاریخ ثبت</span><strong>{{ dateTime(blacklistModal.row?.created_at) }}</strong></p>
        <p v-if="blacklistModal.error" class="helper-note error">{{ blacklistModal.error }}</p>
        <button class="primary-btn" :disabled="blacklistModal.submitting || !blacklistModal.row?.id" @click="unblockBlacklistPlate">
          {{ blacklistModal.submitting ? 'در حال خارج کردن...' : 'خارج کردن از لیست سیاه' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import api from '../../services/api'
import { LIVE_EVENT_NAME } from '../../services/live'
import { useAuthStore } from '../../store/auth.store'
import AppShell from '../../components/layout/AppShell.vue'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import IconlyIcon from '../../components/base/IconlyIcon.vue'
import PlateBadge from '../../components/vehicles/PlateBadge.vue'
import IranPlateMark from '../../components/vehicles/IranPlateMark.vue'
import PlateEditor from '../../components/vehicles/PlateEditor.vue'
import VehicleDetailsModal from '../../components/vehicles/VehicleDetailsModal.vue'
import { formatJalaliDate, formatJalaliMonthDay } from '../../utils/date'
import { formatThousandsToman, formatThousandsTomanValue, fromThousandsTomanInput } from '../../utils/money'
import { normalizeDigits, normalizePlateLetter as normalizePlateLetterUtil } from '../../utils/plate'
import { resolveApiErrorMessage } from '../../utils/apiError'
import { printHtmlElement, resolvePrintErrorMessage } from '../../utils/receiptPrinter'
import { sectionHelpByPage } from '../../config/pageHelp'
import HelpTip from '../../components/base/HelpTip.vue'
import ReportPager from '../../components/reports/ReportPager.vue'

const activeTab = ref('overall')
let liveReloadTimer = null
const authStore = useAuthStore()
const workers = ref([])
const errorMessage = ref('')
const rangeOptions = [
  { key: 'today', label: 'امروز', icon: 'calendar' },
  { key: 'week', label: 'این هفته', icon: 'graph' },
  { key: 'month', label: 'این ماه', icon: 'document' },
  { key: 'all', label: 'کل', icon: 'category' }
]

const currentJalaliMonthValue = () => {
  const parts = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    month: '2-digit'
  }).formatToParts(new Date())
  return parts.find((item) => item.type === 'month')?.value || '01'
}

const filters = reactive({
  rangeKey: 'today',
  startJalali: '',
  endJalali: '',
  q: '',
  workerId: '',
  insuranceMonthJalali: currentJalaliMonthValue(),
  plateType: '',
  plateLeft: '',
  plateLetter: '',
  plateMid: '',
  plateRight: ''
})
const summary = reactive({
  vehicles_count: 0,
  carwash_total: 0,
  worker_total: 0,
  tips_total: 0,
  discount_total: 0,
  facility_discount_total: 0,
  loyalty_discount_total: 0,
  manual_discount_total: 0,
  loyalty_discount_count: 0,
  tax_total: 0,
  final_total: 0,
  before_discount_total: 0,
  payable_worker_total: 0,
  bonus_total: 0,
  penalty_total: 0
})
const sectionTotals = reactive({ overall: {}, carwash: {}, worker: {}, tips: {}, products: {}, discount: {}, revenue: {}, attendance: {}, blacklist: {} })
const data = reactive({
  overall_report: [],
  carwash_report: [],
  worker_report: [],
  tips_report: [],
  products_report: [],
  discount_report: [],
  attendance_report: [],
  blacklist_report: [],
  revenue_report: []
})
const expandedServiceRows = ref({})
const selectedWorkerSummary = ref(null)
const selectedWorkerTransactions = ref([])
const REPORT_PAGE_SIZE = 50
const exportAllRows = ref(false)
const lastWorkerSyncSignature = ref('')
let workerSyncTimer = null
let workerSyncInFlight = false
let workerSyncRequestToken = 0
const tablePage = reactive({
  overall: 1,
  carwash: 1,
  worker: 1,
  workerTx: 1,
  tips: 1,
  products: 1,
  discount: 1,
  revenue: 1,
  attendance: 1,
  blacklist: 1
})
const sectionMeta = reactive({
  overall: { total: 0, pages: 1, page: 1 },
  carwash: { total: 0, pages: 1, page: 1 },
  worker: { total: 0, pages: 1, page: 1 },
  tips: { total: 0, pages: 1, page: 1 },
  products: { total: 0, pages: 1, page: 1 },
  discount: { total: 0, pages: 1, page: 1 },
  revenue: { total: 0, pages: 1, page: 1 },
  attendance: { total: 0, pages: 1, page: 1 },
  blacklist: { total: 0, pages: 1, page: 1 }
})
const vehicleModal = reactive({ open: false, loading: false, data: null })
const blacklistModal = reactive({ open: false, submitting: false, row: null, error: '' })
const payoutModal = reactive({ open: false, submitting: false, target: 'wage', mode: 'full', amount: 0, note: '', insuranceMonth: '', includeTip: false, replaceId: null, replaceAmount: 0 })
const payoutSubmitError = ref('')
const adjustmentModal = reactive({ open: false, submitting: false, kind: 'bonus', amount: 0, note: '', replaceId: null })
const pdfFormatModal = reactive({ open: false })
const reportExportRef = ref(null)
const exportState = reactive({ csvLoading: false, pdfLoading: false })

const tabs = [
  { key: 'overall', label: 'گزارش کل', icon: 'document', help: sectionHelpByPage.reports.overall },
  { key: 'carwash', label: 'حق کارواش', icon: 'wallet', help: sectionHelpByPage.reports.carwash },
  { key: 'worker', label: 'حق نیرو', icon: 'users3', help: sectionHelpByPage.reports.worker },
  { key: 'tips', label: 'انعام', icon: 'message', help: sectionHelpByPage.reports.tips },
  { key: 'products', label: 'محصولات', icon: 'buy', help: sectionHelpByPage.reports.products || 'گزارش فروش محصولات و سود هر ردیف' },
  { key: 'discount', label: 'تخفیف', icon: 'star', help: sectionHelpByPage.reports.discount },
  { key: 'revenue', label: 'گزارش درآمد', icon: 'graph', help: sectionHelpByPage.reports.revenue },
  { key: 'attendance', label: 'ورود و خروج', icon: 'calendar', help: sectionHelpByPage.reports.attendance },
  { key: 'blacklist', label: 'لیست سیاه', icon: 'danger', help: sectionHelpByPage.reports.blacklist }
]
const moneyInputValue = (value) => formatThousandsTomanValue(value, { maximumFractionDigits: 0 })
const parseMoneyInput = (value) => fromThousandsTomanInput(normalizeDigits(value))

const paginateList = (rows, key, { numbered = false } = {}) => {
  const list = Array.isArray(rows) ? rows : []
  const meta = sectionMeta[key] || {}
  const total = Number(meta.total ?? list.length) || 0
  const pages = Math.max(1, Number(meta.pages) || Math.ceil(total / REPORT_PAGE_SIZE) || 1)
  const safePage = Math.min(Math.max(1, Number(tablePage[key]) || 1), pages)
  if (exportAllRows.value) {
    const mapped = numbered
      ? list.map((row, index) => ({ ...row, _pageRow: index + 1 }))
      : list
    return { rows: mapped, total, pages: 1, page: 1, from: total ? 1 : 0, to: total, pageSize: REPORT_PAGE_SIZE }
  }
  // Server already returns the current page slice for report tabs.
  const start = (safePage - 1) * REPORT_PAGE_SIZE
  const mapped = numbered
    ? list.map((row, index) => ({ ...row, _pageRow: start + index + 1 }))
    : list
  return {
    rows: mapped,
    total,
    pages,
    page: safePage,
    from: total ? start + 1 : 0,
    to: Math.min(start + list.length, total),
    pageSize: REPORT_PAGE_SIZE
  }
}

const pagedTables = computed(() => ({
  overall: paginateList(data.overall_report, 'overall'),
  carwash: paginateList(data.carwash_report, 'carwash'),
  worker: paginateList(data.worker_report, 'worker'),
  workerTx: (() => {
    const list = Array.isArray(selectedWorkerTransactions.value) ? selectedWorkerTransactions.value : []
    const total = list.length
    const pages = Math.max(1, Math.ceil(total / REPORT_PAGE_SIZE) || 1)
    const safePage = Math.min(Math.max(1, Number(tablePage.workerTx) || 1), pages)
    const start = (safePage - 1) * REPORT_PAGE_SIZE
    const slice = exportAllRows.value ? list : list.slice(start, start + REPORT_PAGE_SIZE)
    return {
      rows: slice.map((row, index) => ({ ...row, _pageRow: (exportAllRows.value ? 0 : start) + index + 1 })),
      total,
      pages,
      page: exportAllRows.value ? 1 : safePage,
      from: total ? (exportAllRows.value ? 1 : start + 1) : 0,
      to: exportAllRows.value ? total : Math.min(start + REPORT_PAGE_SIZE, total),
      pageSize: REPORT_PAGE_SIZE
    }
  })(),
  tips: paginateList(data.tips_report, 'tips'),
  products: paginateList(data.products_report, 'products'),
  discount: paginateList(data.discount_report, 'discount'),
  revenue: paginateList(data.revenue_report, 'revenue'),
  attendance: paginateList(data.attendance_report, 'attendance'),
  blacklist: paginateList(data.blacklist_report, 'blacklist')
}))

const resetTablePages = () => {
  Object.keys(tablePage).forEach((key) => { tablePage[key] = 1 })
}

const linkedVehicleTabs = ['overall', 'carwash', 'worker', 'tips']

const setTablePage = (key, page) => {
  const meta = pagedTables.value[key]
  const pages = Math.max(1, Number(meta?.pages) || 1)
  const nextPage = Math.min(Math.max(1, Number(page) || 1), pages)
  if (linkedVehicleTabs.includes(key)) {
    linkedVehicleTabs.forEach((tabKey) => { tablePage[tabKey] = nextPage })
  } else {
    tablePage[key] = nextPage
  }
  if (key !== 'workerTx') {
    void fetchReports({ page: nextPage, skipWorkerAutoSync: true })
  }
  nextTick(() => {
    reportExportRef.value?.querySelector('.table-wrap')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  })
}

const insuranceMonthOptions = [
  { value: '01', label: 'فروردین' },
  { value: '02', label: 'اردیبهشت' },
  { value: '03', label: 'خرداد' },
  { value: '04', label: 'تیر' },
  { value: '05', label: 'مرداد' },
  { value: '06', label: 'شهریور' },
  { value: '07', label: 'مهر' },
  { value: '08', label: 'آبان' },
  { value: '09', label: 'آذر' },
  { value: '10', label: 'دی' },
  { value: '11', label: 'بهمن' },
  { value: '12', label: 'اسفند' }
]

const money = (v) => formatThousandsToman(v)
const faNumber = (value) => Number(value || 0).toLocaleString('fa-IR')
const dateTime = (v) => formatJalaliDate(v)
const dateOnly = (v) => formatJalaliDate(v)
const receiptDateShort = (v) => formatJalaliMonthDay(v)
const faNumberLatin = (value) => Number(value || 0).toLocaleString('en-US')
const moneyLatin = (value) => Number(value || 0).toLocaleString('en-US')
const receiptMoney = (value) => `${moneyLatin(value)}`
const formatStatus = (value) => ({ entered: 'در انتظار تکمیل', assigned: 'در انتظار تکمیل', in_progress: 'در حال انجام', ready_to_settle: 'در انتظار تکمیل', released: 'ترخیص شده', cancelled: 'لغو' }[value] || '-')
const formatGender = (value) => ({ male: 'آقا', female: 'خانم' }[value] || '-')
const workerPaymentTypeLabel = (value) => ({ hourly: 'ساعتی', fixed: 'ثابت', percent: 'درصدی' }[value] || '-')
const workHoursLabel = (value) => `${Number(value || 0).toLocaleString('fa-IR', { maximumFractionDigits: 2 })} ساعت`
const payoutKindLabel = (value) => ({ wage_payment: 'پرداخت حقوق', tip_payment: 'پرداخت انعام', insurance_payment: 'پرداخت حق بیمه', advance_payment: 'پرداخت مساعده', bonus: 'پاداش', penalty: 'جریمه' }[value] || value)
const paymentMethodLabel = (value) => ({ cash: 'نقدی', transfer: 'کارت به کارت', cheque: 'چک', credit: 'نسیه', pos: 'کارت‌خوان', manual: 'دستی' }[value] || value || '-')
const paymentStateLabel = (value) => ({ success: 'تسویه شده', pending: 'در انتظار', failed: 'ناموفق', refunded: 'مرجوعی' }[value] || value || '-')
const normalizeServicesValue = (value) => {
  const text = String(value || '').trim()
  return text || '-'
}
const hasExpandableServices = (value) => normalizeServicesValue(value).length > 24
const servicesPreview = (value) => {
  const text = normalizeServicesValue(value)
  if (text === '-' || text.length <= 24) return text
  return `${text.slice(0, 24).trim()}...`
}
const serviceRowKey = (row) => String(row?.vehicle_id || row?.row || '')
const isServicesExpanded = (row) => Boolean(expandedServiceRows.value[serviceRowKey(row)])
const toggleServicesRow = (row) => {
  const key = serviceRowKey(row)
  if (!key) return
  expandedServiceRows.value = {
    ...expandedServiceRows.value,
    [key]: !expandedServiceRows.value[key]
  }
}
const overallAmount = (key) => Number(sectionTotals.overall?.[key] ?? summary?.[key] ?? 0)
const overallFinalAmount = () => {
  const explicitTotal = overallAmount('final_total')
  if (explicitTotal > 0) return explicitTotal
  return (
  overallAmount('carwash_total') +
  overallAmount('products_total') +
  overallAmount('worker_total') +
  overallAmount('tips_total')
)
}
const overallFinalAmountWithoutTip = () => (
  Math.max(0, Math.round(overallFinalAmount()) - Math.round(overallAmount('tips_total')))
)
const overallBeforeDiscountAmount = () => (
  Math.round(overallFinalAmount()) + Math.round(overallAmount('discount_total'))
)
const visibleSummaryCards = computed(() => {
  if (activeTab.value === 'overall') {
    return [
      { key: 'visits_count', label: 'کل مراجعات', value: Number(overallAmount('vehicles_count')).toLocaleString('fa-IR') },
      { key: 'final_total', label: 'مبلغ نهایی', value: money(overallFinalAmount()) },
      { key: 'final_total_without_tip', label: 'مبلغ نهایی بدون انعام', value: money(overallFinalAmountWithoutTip()) },
      { key: 'carwash_total', label: 'حق کارواش', value: money(overallAmount('carwash_total')) },
      { key: 'worker_total', label: 'حق نیرو', value: money(overallAmount('worker_total')) },
      { key: 'products_total', label: 'فروش محصولات', value: money(overallAmount('products_total')) },
      { key: 'tips_total', label: 'انعام', value: money(overallAmount('tips_total')) },
      { key: 'discount_total', label: 'جمع تخفیف', value: money(overallAmount('discount_total')) },
      { key: 'tax_total', label: 'مالیات', value: money(overallAmount('tax_total')) },
      { key: 'before_discount_total', label: 'قبل از تخفیف', value: money(overallBeforeDiscountAmount()) }
    ]
  }
  if (activeTab.value === 'carwash') {
    return [
      { key: 'carwash_total', label: 'حق کارواش', value: money(summary.carwash_total) }
    ]
  }
  if (activeTab.value === 'worker') {
    return [
      { key: 'worker_total', label: selectedWorkerSummary.value ? 'جمع حق نیرو (دوره)' : 'جمع حق نیرو', value: money(summary.worker_total) },
      { key: 'payable_worker_total', label: selectedWorkerSummary.value ? 'مانده قابل پرداخت حقوق' : 'مانده حق نیرو', value: money(summary.payable_worker_total) },
      { key: 'advance_paid_total', label: 'مساعده پرداخت‌شده', value: money(selectedWorkerSummary.value?.advance_paid_total || 0) },
      { key: 'tip_balance', label: 'مانده انعام', value: money(selectedWorkerSummary.value?.tip_balance || summary.payable_tip_total || 0) },
      { key: 'insurance_total', label: 'مانده بیمه این ماه', value: money(summary.insurance_total) },
      { key: 'bonus_total', label: 'پاداش', value: money(summary.bonus_total) },
      { key: 'penalty_total', label: 'جریمه', value: money(summary.penalty_total) }
    ]
  }
  if (activeTab.value === 'tips') {
    return [
      { key: 'tips_total', label: 'انعام', value: money(summary.tips_total) }
    ]
  }
  if (activeTab.value === 'products') {
    return [
      { key: 'products_count', label: 'تعداد ردیف‌ها', value: Number(sectionTotals.products?.count || 0).toLocaleString('fa-IR') },
      { key: 'quantity_total', label: 'جمع تعداد', value: Number(sectionTotals.products?.quantity_total || 0).toLocaleString('fa-IR') },
      { key: 'sale_total', label: 'جمع فروش', value: money(sectionTotals.products?.sale_total || 0) },
      { key: 'cost_total', label: 'جمع بهای تمام‌شده', value: money(sectionTotals.products?.cost_total || 0) },
      { key: 'profit_total', label: 'جمع سود', value: money(sectionTotals.products?.profit_total || 0) }
    ]
  }
  if (activeTab.value === 'discount') {
    const loyaltyTotal = Number(sectionTotals.discount?.loyalty_discount_total ?? summary.loyalty_discount_total ?? 0)
    const loyaltyCount = Number(sectionTotals.discount?.loyalty_discount_count ?? summary.loyalty_discount_count ?? 0)
    return [
      { key: 'discount_total', label: 'جمع کل تخفیف', value: money(sectionTotals.discount?.discount_total ?? summary.discount_total) },
      { key: 'loyalty_discount_total', label: 'تخفیف امتیاز مشتری', value: money(loyaltyTotal) },
      {
        key: 'loyalty_visit_discount',
        label: 'تخفیف دفعات مراجعه',
        value: money(loyaltyTotal),
        hint: loyaltyCount
          ? `${Number(loyaltyCount).toLocaleString('fa-IR')} مراجعه با تخفیف امتیاز`
          : 'در این بازه تخفیف امتیاز ثبت نشده'
      },
      { key: 'facility_discount_total', label: 'تخفیف مجموعه', value: money(sectionTotals.discount?.facility_discount_total ?? summary.facility_discount_total) },
      { key: 'manual_discount_total', label: 'تخفیف دستی', value: money(sectionTotals.discount?.manual_discount_total ?? summary.manual_discount_total) },
      {
        key: 'discount_rows_count',
        label: 'تعداد سفارش‌های دارای تخفیف',
        value: Number(sectionTotals.discount?.count || data.discount_report.length || 0).toLocaleString('fa-IR')
      }
    ]
  }
  if (activeTab.value === 'revenue') {
    return [
      { key: 'revenue_total', label: 'درآمد وصول‌شده', value: money(sectionTotals.revenue.revenue_total) }
    ]
  }
  if (activeTab.value === 'attendance') {
    const checkins = data.attendance_report.filter((item) => item.event_type === 'in').length
    const checkouts = data.attendance_report.filter((item) => item.event_type === 'out').length
    return [
      { key: 'attendance_count', label: 'کل رویدادها', value: Number(sectionTotals.attendance.count || 0).toLocaleString('fa-IR') },
      { key: 'attendance_checkins', label: 'ورودها', value: Number(checkins || 0).toLocaleString('fa-IR') },
      { key: 'attendance_checkouts', label: 'خروج‌ها', value: Number(checkouts || 0).toLocaleString('fa-IR') },
    ]
  }
  if (activeTab.value === 'blacklist') {
    return [
      { key: 'blacklist_count', label: 'تعداد پلاک‌های مسدود', value: Number(sectionTotals.blacklist.count || 0).toLocaleString('fa-IR') }
    ]
  }
  return []
})

const toIsoDate = (value) => {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const resolveRangeDates = (rangeKey) => {
  if (rangeKey === 'all') return { start: '', end: '' }
  const now = new Date()
  const end = new Date(now)
  let start = new Date(now)
  if (rangeKey === 'today') {
    return { start: toIsoDate(start), end: toIsoDate(end) }
  }
  if (rangeKey === 'week') {
    const day = now.getDay()
    const offset = day === 0 ? 6 : day - 1
    start.setDate(now.getDate() - offset)
    return { start: toIsoDate(start), end: toIsoDate(end) }
  }
  if (rangeKey === 'month') {
    start = new Date(now.getFullYear(), now.getMonth(), 1)
    return { start: toIsoDate(start), end: toIsoDate(end) }
  }
  return { start: '', end: '' }
}

const setRange = (rangeKey) => {
  filters.rangeKey = rangeKey
}

const reportPeriodLabel = computed(() => {
  if (filters.startJalali && filters.endJalali) return `از ${filters.startJalali} تا ${filters.endJalali}`
  const params = buildReportParams()
  const start = params.start ? formatJalaliDate(params.start) : ''
  const end = params.end ? formatJalaliDate(params.end) : ''
  if (start && end) return `از ${start} تا ${end}`
  if (start) return `از ${start}`
  if (end) return `تا ${end}`
  return 'کل دوره'
})

const buildReportParams = ({ page = null, exportAll = false } = {}) => {
  const manualStart = parseJalaliToIso(filters.startJalali)
  const manualEnd = parseJalaliToIso(filters.endJalali)
  const quickRange = resolveRangeDates(filters.rangeKey)
  let start = manualStart || quickRange.start
  let end = manualEnd || quickRange.end
  if (start && end && start > end) {
    const temp = start
    start = end
    end = temp
  }
  const workerId = Number.parseInt(filters.workerId, 10)
  const activePageKey = linkedVehicleTabs.includes(activeTab.value) ? 'overall' : activeTab.value
  return {
    start: start || undefined,
    end: end || undefined,
    q: (filters.q || '').trim() || undefined,
    worker_id: Number.isInteger(workerId) && workerId > 0 ? workerId : undefined,
    insurance_month: normalizeInsuranceMonth(filters.insuranceMonthJalali),
    plate_type: filters.plateType || undefined,
    plate_left: filters.plateLeft || undefined,
    plate_letter: filters.plateLetter || undefined,
    plate_mid: filters.plateMid || undefined,
    plate_right: filters.plateRight || undefined,
    page: exportAll ? 1 : (page || tablePage[activePageKey] || 1),
    page_size: REPORT_PAGE_SIZE,
    ...(exportAll ? { export_all: 1 } : {})
  }
}

const buildWorkerSyncSignature = () => JSON.stringify({
  tab: activeTab.value,
  workerId: filters.workerId || '',
  rangeKey: filters.rangeKey,
  startJalali: filters.startJalali || '',
  endJalali: filters.endJalali || '',
  q: (filters.q || '').trim(),
  insuranceMonthJalali: filters.insuranceMonthJalali || '',
  plateType: filters.plateType || '',
  plateLeft: filters.plateLeft || '',
  plateLetter: filters.plateLetter || '',
  plateMid: filters.plateMid || '',
  plateRight: filters.plateRight || ''
})

const payoutButtonLabel = computed(() => `پرداخت حقوق ${selectedWorkerSummary.value?.worker_name || ''}`)
const insurancePayoutButtonLabel = computed(() => `پرداخت حق بیمه ${selectedWorkerSummary.value?.worker_name || ''}`)
const advancePayoutButtonLabel = computed(() => `پرداخت مساعده ${selectedWorkerSummary.value?.worker_name || ''}`)
const selectedInsuranceMonthKey = computed(() => normalizeInsuranceMonth(payoutModal.insuranceMonth) || selectedWorkerSummary.value?.insurance_month || '')
const selectedInsuranceMonthPaidAmount = computed(() => {
  if (!selectedInsuranceMonthKey.value) return 0
  return selectedWorkerTransactions.value
    .filter((item) => item.kind === 'insurance_payment' && item.reference_month === selectedInsuranceMonthKey.value)
    .reduce((sum, item) => sum + Number(item.amount || 0), 0)
})
const selectedInsuranceMonthBalance = computed(() => {
  const monthlyAmount = Number(selectedWorkerSummary.value?.insurance_monthly_amount || 0)
  const dueStartMonth = normalizeInsuranceMonth(selectedWorkerSummary.value?.insurance_due_start_month)
  if (!isJalaliMonthOnOrAfter(selectedInsuranceMonthKey.value, dueStartMonth)) return 0
  return Math.max(0, monthlyAmount - selectedInsuranceMonthPaidAmount.value)
})
const payoutModalMaxAmount = computed(() => {
  const freed = payoutModal.replaceId ? Number(payoutModal.replaceAmount || 0) : 0
  if (payoutModal.target === 'insurance') {
    return selectedInsuranceMonthBalance.value + freed
  }
  if (payoutModal.target === 'tip') {
    return Number(selectedWorkerSummary.value?.tip_balance || 0) + freed
  }
  if (payoutModal.target === 'advance') {
    return Number.POSITIVE_INFINITY
  }
  return Number(selectedWorkerSummary.value?.payable_total || 0) + freed
})
const payoutValidationMessage = computed(() => {
  if (payoutModal.target === 'advance') {
    const amount = Number(fromThousandsTomanInput(payoutModal.amount || 0))
    if (amount <= 0) return 'مبلغ مساعده باید بیشتر از صفر باشد.'
    return ''
  }
  if (payoutModal.mode !== 'partial') return ''
  const amount = Number(fromThousandsTomanInput(payoutModal.amount || 0))
  if (amount <= 0) return 'مبلغ پرداخت باید بیشتر از صفر باشد.'
  if (payoutModal.replaceId) {
    if (amount > payoutModalMaxAmount.value) return `مبلغ واردشده از مانده بیشتر است. سقف مجاز: ${money(payoutModalMaxAmount.value)}`
    return ''
  }
  if (amount >= payoutModalMaxAmount.value) return `مبلغ واردشده از مانده بیشتر است. مبلغ باید کمتر از مانده باشد: ${money(payoutModalMaxAmount.value)}`
  return ''
})
const isPayoutAmountValid = computed(() => {
  if (payoutModal.target === 'advance') {
    return Number(fromThousandsTomanInput(payoutModal.amount || 0)) > 0
  }
  if (payoutModal.target === 'wage' && payoutModal.includeTip && !payoutModal.replaceId && Number(selectedWorkerSummary.value?.tip_balance || 0) > 0) {
    if (payoutModal.mode === 'full') return true
  }
  if (payoutModal.mode !== 'partial') return payoutModalMaxAmount.value > 0
  const amount = Number(fromThousandsTomanInput(payoutModal.amount || 0))
  if (payoutModal.replaceId) return amount > 0 && amount <= payoutModalMaxAmount.value
  return amount > 0 && amount < payoutModalMaxAmount.value
})
const canSubmitPayout = computed(() => isPayoutAmountValid.value)

const hasPlateFilter = computed(() => Boolean(
  filters.plateLeft
  || filters.plateLetter
  || filters.plateMid
  || filters.plateRight
  || filters.plateType
))

const clearPlateFilter = () => {
  filters.plateType = ''
  filters.plateLeft = ''
  filters.plateLetter = ''
  filters.plateMid = ''
  filters.plateRight = ''
}

const normalizePlateFilters = () => {
  if (filters.plateType !== 'motorcycle' && filters.plateType !== 'car') filters.plateType = ''
  filters.plateLeft = normalizeDigits(filters.plateLeft).replace(/\D/g, '').slice(0, 2)
  filters.plateRight = normalizeDigits(filters.plateRight).replace(/\D/g, '').slice(0, 2)
  filters.plateMid = normalizeDigits(filters.plateMid).replace(/\D/g, '').slice(0, 3)
  const letterRaw = String(filters.plateLetter || '')
  const letterLooksMotor = /^\d+$/.test(normalizeDigits(letterRaw).replace(/\D/g, '')) && normalizeDigits(letterRaw).replace(/\D/g, '').length > 1
  if (filters.plateType === 'motorcycle' || (!filters.plateType && letterLooksMotor)) {
    filters.plateLetter = normalizeDigits(filters.plateLetter).replace(/\D/g, '').slice(0, 5)
  } else {
    filters.plateLetter = normalizePlateLetterUtil(filters.plateLetter)
  }
  if (filters.plateType === 'motorcycle') {
    filters.plateLeft = ''
    filters.plateRight = ''
  }
}
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

const normalizeInsuranceMonth = (value) => {
  const normalized = String(value || '').trim().replace(/-/g, '/')
  const parts = normalized.split('/')
  if (parts.length === 1) {
    const monthOnly = normalizeDigits(parts[0]).replace(/\D/g, '').slice(0, 2).padStart(2, '0')
    const year = resolveInsuranceYear()
    const monthNumber = Number(monthOnly)
    return monthNumber >= 1 && monthNumber <= 12 && year ? `${year}/${monthOnly}` : ''
  }
  if (parts.length < 2) return ''
  const year = normalizeDigits(parts[0]).replace(/\D/g, '').slice(0, 4)
  const month = normalizeDigits(parts[1]).replace(/\D/g, '').slice(0, 2).padStart(2, '0')
  const monthNumber = Number(month)
  if (!year || monthNumber < 1 || monthNumber > 12) return ''
  return `${year}/${month}`
}

const jalaliMonthIndex = (value) => {
  const monthValue = normalizeInsuranceMonth(value)
  if (!monthValue) return null
  const [year, month] = monthValue.split('/').map((item) => Number(item))
  if (!Number.isFinite(year) || !Number.isFinite(month)) return null
  return (year * 12) + month
}

const isJalaliMonthAfter = (left, right) => {
  const leftIndex = jalaliMonthIndex(left)
  const rightIndex = jalaliMonthIndex(right)
  return leftIndex !== null && rightIndex !== null && leftIndex > rightIndex
}

const isJalaliMonthOnOrAfter = (left, right) => {
  const leftIndex = jalaliMonthIndex(left)
  const rightIndex = jalaliMonthIndex(right)
  return leftIndex !== null && rightIndex !== null && leftIndex >= rightIndex
}

const insuranceMonthToFilterDate = (value) => {
  const monthValue = normalizeInsuranceMonth(value)
  return monthValue ? monthValue.split('/')[1] : ''
}

const getCurrentJalaliYear = () => {
  const formatter = new Intl.DateTimeFormat('fa-IR-u-ca-persian', { year: 'numeric' })
  const yearPart = formatter.formatToParts(new Date()).find((item) => item.type === 'year')
  return normalizeDigits(yearPart?.value || '').replace(/\D/g, '').slice(0, 4)
}

const resolveInsuranceYear = () => {
  const candidates = [
    selectedWorkerSummary.value?.insurance_month,
    filters.insuranceMonthJalali,
  ]
  for (const item of candidates) {
    const match = normalizeDigits(String(item || '')).match(/(\d{4})/)
    if (match?.[1]) return match[1]
  }
  return getCurrentJalaliYear()
}

const SILENT_REQUEST_META = { trackLoading: false, showErrorToast: false }

const fetchWorkers = async ({ silent = false } = {}) => {
  try {
    const { data } = await api.get('/workers/', {
      params: { include_inactive: 1 },
      ...(silent ? { meta: SILENT_REQUEST_META } : {})
    })
    workers.value = Array.isArray(data) ? data : []
  } catch (_error) {
    workers.value = []
  }
}

let fetchToken = 0
const applySectionMeta = (payload = {}) => {
  const sections = payload?.pagination?.sections || {}
  const fallbackTotal = Number(payload?.pagination?.total || payload?.summary?.vehicles_count || 0)
  const fallbackPages = Math.max(1, Number(payload?.pagination?.pages) || Math.ceil(fallbackTotal / REPORT_PAGE_SIZE) || 1)
  const fallbackPage = Math.max(1, Number(payload?.pagination?.page) || 1)
  const keys = Object.keys(sectionMeta)
  keys.forEach((key) => {
    const section = sections[key] || {}
    sectionMeta[key] = {
      total: Number(section.total ?? fallbackTotal) || 0,
      pages: Math.max(1, Number(section.pages) || fallbackPages),
      page: Math.max(1, Number(section.page) || fallbackPage)
    }
    if (key !== 'workerTx') {
      tablePage[key] = sectionMeta[key].page
    }
  })
}

const fetchReports = async ({
  withSync = false,
  syncLimit = null,
  skipWorkerAutoSync = false,
  silent = false,
  page = null,
  exportAll = false,
  resetPages = false
} = {}) => {
  const token = ++fetchToken
  errorMessage.value = ''
  if (resetPages) resetTablePages()
  try {
    const params = {
      ...buildReportParams({ page, exportAll }),
      ...(withSync ? { sync: 1 } : {}),
      ...(withSync && syncLimit != null ? { sync_limit: syncLimit } : {})
    }
    const { data: payload } = await api.get('/reports/dashboard/', {
      params,
      meta: {
        ...(silent ? SILENT_REQUEST_META : {}),
        timeoutMs: exportAll || filters.rangeKey === 'all' ? 60000 : 45000,
        loadingKey: 'reports:dashboard'
      }
    })
    if (token !== fetchToken) return
    Object.assign(summary, payload.summary || {})
    Object.assign(sectionTotals.overall, payload.section_totals?.overall || {})
    Object.assign(sectionTotals.carwash, payload.section_totals?.carwash || {})
    Object.assign(sectionTotals.worker, payload.section_totals?.worker || {})
    Object.assign(sectionTotals.tips, payload.section_totals?.tips || {})
    Object.assign(sectionTotals.products, payload.section_totals?.products || {})
    Object.assign(sectionTotals.discount, payload.section_totals?.discount || {})
    Object.assign(sectionTotals.attendance, payload.section_totals?.attendance || {})
    Object.assign(sectionTotals.blacklist, payload.section_totals?.blacklist || {})
    Object.assign(sectionTotals.revenue, payload.section_totals?.revenue || {})
    expandedServiceRows.value = {}
    data.overall_report = payload.overall_report || []
    data.carwash_report = payload.carwash_report || []
    data.worker_report = payload.worker_report || []
    data.tips_report = payload.tips_report || []
    data.products_report = payload.products_report || []
    data.discount_report = payload.discount_report || []
    data.attendance_report = payload.attendance_report || []
    data.blacklist_report = payload.blacklist_report || []
    data.revenue_report = payload.revenue_report || []
    selectedWorkerSummary.value = payload.selected_worker_summary || null
    selectedWorkerTransactions.value = payload.selected_worker_transactions || []
    applySectionMeta(payload)
    if (!skipWorkerAutoSync && !withSync && activeTab.value === 'worker') {
      scheduleWorkerReportSync()
    }
  } catch (error) {
    if (token !== fetchToken) return
    errorMessage.value = resolveApiErrorMessage(error, 'بارگذاری گزارشات ناموفق بود.')
  }
}

const syncWorkerReportRows = async ({ full = false } = {}) => {
  if (activeTab.value !== 'worker') return
  if (workerSyncInFlight) return
  const signature = buildWorkerSyncSignature()
  if (!full && signature === lastWorkerSyncSignature.value) return

  workerSyncInFlight = true
  const token = ++workerSyncRequestToken
  try {
    await fetchReports({
      withSync: true,
      syncLimit: full ? null : REPORT_PAGE_SIZE,
      skipWorkerAutoSync: true
    })
    if (token === workerSyncRequestToken) {
      lastWorkerSyncSignature.value = signature
    }
  } finally {
    if (token === workerSyncRequestToken) {
      workerSyncInFlight = false
    }
  }
}

const scheduleWorkerReportSync = ({ full = false, delayMs = 120 } = {}) => {
  if (activeTab.value !== 'worker') return
  if (workerSyncTimer) clearTimeout(workerSyncTimer)
  workerSyncTimer = setTimeout(() => {
    syncWorkerReportRows({ full })
  }, delayMs)
}

const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

const escapeHtml = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#039;')

const workerReceiptOrderPrice = (row) => {
  // Services-only share base (after post-sale discounts). Products never enter worker share math.
  if (row?.service_total !== undefined && row?.service_total !== null) {
    return Math.max(0, Number(row.service_total || 0))
  }
  if (row?.final_total_without_tip !== undefined && row?.final_total_without_tip !== null) {
    const products = Math.max(0, Number(row.products_total || 0))
    return Math.max(0, Number(row.final_total_without_tip || 0) - products)
  }
  if (row?.final_total !== undefined && row?.final_total !== null) {
    return Math.max(0, Number(row.final_total || 0) - Number(row.tip_amount || 0) - Number(row.products_total || 0))
  }
  return 0
}

const workerReceiptRows = computed(() => (
  Array.isArray(data.worker_report) ? data.worker_report : []
).map((row, index) => ({
  row: index + 1,
  date: receiptDateShort(row.created_at),
  car: String(row.car_model || '-').trim() || '-',
  price: workerReceiptOrderPrice(row),
  tip: Number(row.tip_amount || 0),
  share: Number(row.worker_share || 0)
})))

const workerReceiptTotalServices = computed(() => workerReceiptRows.value.reduce((sum, row) => sum + row.price, 0))
const workerReceiptTotalTip = computed(() => {
  if (selectedWorkerSummary.value) {
    return Number(selectedWorkerSummary.value.tip_total || 0)
  }
  return workerReceiptRows.value.reduce((sum, row) => sum + row.tip, 0)
})
const workerReceiptStaffShare = computed(() => {
  if (selectedWorkerSummary.value) {
    return Number(selectedWorkerSummary.value.wage_total || 0)
  }
  return workerReceiptRows.value.reduce((sum, row) => sum + row.share, 0)
})
const workerReceiptGrandTotal = computed(() => workerReceiptStaffShare.value + workerReceiptTotalTip.value)

const buildWorkerReceiptElement = () => {
  const workerName = selectedWorkerSummary.value?.worker_name || '-'
  const paymentType = workerPaymentTypeLabel(selectedWorkerSummary.value?.payment_type)
  const rowsHtml = workerReceiptRows.value.map((row) => `
    <tr>
      <td class="col-idx">${escapeHtml(faNumberLatin(row.row))}</td>
      <td class="col-date">${escapeHtml(row.date)}</td>
      <td class="col-car">${escapeHtml(row.car)}</td>
      <td class="col-num">${escapeHtml(receiptMoney(row.price))}</td>
      <td class="col-num">${escapeHtml(receiptMoney(row.tip))}</td>
    </tr>
  `).join('')
  const emptyRow = '<tr><td colspan="5" class="empty-row">سفارشی در این بازه نیست</td></tr>'

  // Styles must live INSIDE the printable node — thermal print clones only this element.
  const element = document.createElement('div')
  element.innerHTML = `
    <article class="worker-receipt-pdf" dir="rtl" lang="fa">
      <style>
        .worker-receipt-pdf, .worker-receipt-pdf * {
          box-sizing: border-box !important;
          color: #000 !important;
          background: #fff !important;
          box-shadow: none !important;
          text-shadow: none !important;
          font-family: Tahoma, "IRANSans", "Segoe UI", Arial, sans-serif !important;
          letter-spacing: 0 !important;
          -webkit-font-smoothing: none !important;
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
        }
        .worker-receipt-pdf {
          width: 74mm;
          max-width: 74mm;
          margin: 0;
          padding: 2mm 1.5mm 2.5mm;
          direction: rtl;
          line-height: 1.45;
          font-size: 13px;
          font-weight: 700;
          overflow: visible;
          page-break-inside: auto;
          break-inside: auto;
        }
        .worker-receipt-pdf .head {
          display: grid;
          gap: 4px;
          text-align: center;
          padding: 0 0 8px;
          margin: 0 0 8px;
          border-bottom: 2px solid #000;
        }
        .worker-receipt-pdf .head .title {
          margin: 0;
          font-size: 18px;
          font-weight: 800;
          line-height: 1.3;
        }
        .worker-receipt-pdf .head .name {
          margin: 0;
          font-size: 15px;
          font-weight: 700;
          line-height: 1.35;
        }
        .worker-receipt-pdf .meta {
          display: grid;
          gap: 4px;
          margin: 0 0 8px;
          padding: 0 0 8px;
          border-bottom: 1px dashed #000;
          font-size: 12px;
          font-weight: 700;
          line-height: 1.45;
        }
        .worker-receipt-pdf .meta p {
          margin: 0;
          display: flex;
          justify-content: space-between;
          gap: 8px;
          align-items: baseline;
        }
        .worker-receipt-pdf .meta span { font-weight: 700; white-space: nowrap; }
        .worker-receipt-pdf .meta strong {
          font-weight: 700;
          text-align: left;
          direction: ltr;
          unicode-bidi: plaintext;
          overflow-wrap: anywhere;
        }
        .worker-receipt-pdf table {
          width: 100%;
          border-collapse: collapse;
          table-layout: fixed;
          margin: 0;
          border: 1.5px solid #000;
        }
        .worker-receipt-pdf th,
        .worker-receipt-pdf td {
          border: 1px solid #000;
          padding: 5px 3px;
          text-align: center;
          vertical-align: middle;
          font-size: 11px;
          line-height: 1.35;
          font-weight: 700;
        }
        .worker-receipt-pdf th {
          font-size: 11px;
          font-weight: 800;
          padding: 6px 3px;
        }
        .worker-receipt-pdf .col-idx {
          width: 10%;
          white-space: nowrap;
          overflow: hidden;
        }
        .worker-receipt-pdf .col-date {
          width: 16%;
          white-space: nowrap;
          overflow: hidden;
          direction: ltr;
          unicode-bidi: isolate;
        }
        .worker-receipt-pdf .col-car {
          width: 30%;
          overflow-wrap: anywhere;
          word-break: break-word;
          font-size: 11px;
        }
        .worker-receipt-pdf .col-num {
          width: 22%;
          white-space: nowrap;
          direction: ltr;
          unicode-bidi: plaintext;
          font-size: 11px;
          font-weight: 800;
        }
        .worker-receipt-pdf .empty-row {
          padding: 10px 4px;
          font-size: 12px;
          font-weight: 700;
        }
        .worker-receipt-pdf .totals {
          display: grid;
          gap: 5px;
          margin: 8px 0 0;
          padding: 8px 0 0;
          border-top: 2px solid #000;
        }
        .worker-receipt-pdf .totals p {
          margin: 0;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          line-height: 1.4;
          font-weight: 700;
        }
        .worker-receipt-pdf .totals span { white-space: nowrap; }
        .worker-receipt-pdf .totals strong {
          white-space: nowrap;
          direction: ltr;
          unicode-bidi: plaintext;
          font-weight: 800;
          font-size: 13px;
        }
        .worker-receipt-pdf .totals .grand {
          margin-top: 3px;
          padding-top: 6px;
          border-top: 2px solid #000;
          border-bottom: 3px double #000;
          padding-bottom: 6px;
          font-size: 14px;
          font-weight: 800;
        }
        .worker-receipt-pdf .totals .grand strong { font-size: 15px; font-weight: 800; }
        .worker-receipt-pdf .foot-note {
          margin: 8px 0 0;
          text-align: center;
          font-size: 11px;
          font-weight: 700;
          line-height: 1.4;
        }
      </style>
      <header class="head">
        <p class="title">فیش حق نیرو</p>
        <p class="name">${escapeHtml(workerName)}</p>
      </header>
      <section class="meta">
        <p><span>دوره</span><strong>${escapeHtml(reportPeriodLabel.value || '-')}</strong></p>
        <p><span>نوع پرداخت</span><strong>${escapeHtml(paymentType)}</strong></p>
        <p><span>تعداد سفارش</span><strong>${escapeHtml(faNumberLatin(workerReceiptRows.value.length))}</strong></p>
      </section>
      <table>
        <thead>
          <tr>
            <th class="col-idx">#</th>
            <th class="col-date">تاریخ</th>
            <th class="col-car">خودرو</th>
            <th class="col-num">خدمات</th>
            <th class="col-num">انعام</th>
          </tr>
        </thead>
        <tbody>${rowsHtml || emptyRow}</tbody>
      </table>
      <section class="totals">
        <p><span>جمع خدمات</span><strong>${escapeHtml(receiptMoney(workerReceiptTotalServices.value))}</strong></p>
        <p><span>جمع حق نیرو</span><strong>${escapeHtml(receiptMoney(workerReceiptStaffShare.value))}</strong></p>
        <p><span>جمع انعام</span><strong>${escapeHtml(receiptMoney(workerReceiptTotalTip.value))}</strong></p>
        <p class="grand"><span>قابل پرداخت</span><strong>${escapeHtml(receiptMoney(workerReceiptGrandTotal.value))}</strong></p>
      </section>
      <p class="foot-note">مبالغ به تومان — محصولات جزو سهم نیست</p>
    </article>
  `

  const wrapper = document.createElement('div')
  wrapper.style.cssText = 'position:fixed;top:0;left:0;width:74mm;max-width:74mm;background:#fff;z-index:-1;pointer-events:none;opacity:0;'
  wrapper.appendChild(element.firstElementChild)
  document.body.appendChild(wrapper)
  return wrapper
}

const exportPdfAsPaper = async (paper = 'a4') => {
  if (!reportExportRef.value) return
  await fetchReports({ exportAll: true, skipWorkerAutoSync: true })
  exportAllRows.value = true
  await nextTick()
  try {
    const html2pdfModule = await import('html2pdf.js')
    const html2pdf = html2pdfModule.default || html2pdfModule
    const format = paper === 'a5' ? 'a5' : 'a4'
    const worker = html2pdf()
      .set({
        margin: format === 'a5' ? 6 : 8,
        filename: `reports-${activeTab.value}-${format}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF: { unit: 'mm', format, orientation: 'landscape' },
        pagebreak: { mode: ['css', 'legacy'] }
      })
      .from(reportExportRef.value)
      .toPdf()
    const pdf = await worker.get('pdf')
    downloadBlob(pdf.output('blob'), `reports-${activeTab.value}-${format}.pdf`)
  } finally {
    exportAllRows.value = false
    await fetchReports({ skipWorkerAutoSync: true })
  }
}

const exportWorkerReceiptPdf = async () => {
  if (activeTab.value !== 'worker' || !selectedWorkerSummary.value?.worker_id) {
    errorMessage.value = 'برای چاپ فیش، اول یک نیرو را از فیلتر انتخاب کنید.'
    return
  }
  await fetchReports({ exportAll: true, skipWorkerAutoSync: true })
  await nextTick()
  const receiptElement = buildWorkerReceiptElement()
  try {
    const receiptNode = receiptElement.querySelector('.worker-receipt-pdf')
    if (!receiptNode) throw new Error('محتوای فیش پیدا نشد.')
    await printHtmlElement(receiptNode, {
      widthMm: 80,
      marginMm: 2,
      marginTopMm: 1,
      marginRightMm: 2,
      marginBottomMm: 2,
      marginLeftMm: 2,
      minHeightMm: 30,
      thermal: true,
      formatLabel: 'فیش حق نیرو'
    })
  } finally {
    receiptElement.remove()
    await fetchReports({ skipWorkerAutoSync: true })
  }
}

const closePdfFormatModal = () => {
  pdfFormatModal.open = false
}

const selectPdfFormat = async (format) => {
  closePdfFormatModal()
  exportState.pdfLoading = true
  errorMessage.value = ''
  try {
    if (format === 'receipt') await exportWorkerReceiptPdf()
    else await exportPdfAsPaper(format)
  } catch (error) {
    console.error('exportPdf error:', error)
    errorMessage.value = format === 'receipt'
      ? resolvePrintErrorMessage(error)
      : 'ساخت خروجی PDF ناموفق بود.'
  } finally {
    exportState.pdfLoading = false
  }
}

const exportCsv = async () => {
  exportState.csvLoading = true
  errorMessage.value = ''
  try {
    const response = await api.get('/reports/export/', {
      params: {
        tab: activeTab.value,
        ...buildReportParams()
      },
      responseType: 'blob',
      meta: { trackLoading: false }
    })
    downloadBlob(response.data, `reports-${activeTab.value}.csv`)
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'دریافت خروجی CSV ناموفق بود.')
  } finally {
    exportState.csvLoading = false
  }
}

const exportPdf = async () => {
  pdfFormatModal.open = true
}

const resetFilters = () => {
  filters.rangeKey = 'today'
  filters.startJalali = ''
  filters.endJalali = ''
  filters.q = ''
  filters.workerId = ''
  filters.insuranceMonthJalali = currentJalaliMonthValue()
  filters.plateType = ''
  filters.plateLeft = ''
  filters.plateLetter = ''
  filters.plateMid = ''
  filters.plateRight = ''
  expandedServiceRows.value = {}
}

const openVehicleDetail = async (vehicleId) => {
  if (!vehicleId) return
  vehicleModal.open = true
  vehicleModal.loading = true
  vehicleModal.data = null
  try {
    const { data } = await api.get(`/vehicles/${vehicleId}/`)
    vehicleModal.data = data
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بارگذاری جزئیات سفارش ناموفق بود.')
    closeVehicleModal()
  } finally {
    vehicleModal.loading = false
  }
}
const closeVehicleModal = () => {
  vehicleModal.open = false
  vehicleModal.loading = false
  vehicleModal.data = null
}

const reloadVehicleDetail = async () => {
  const vehicleId = vehicleModal.data?.id
  if (!vehicleId) return
  vehicleModal.loading = true
  try {
    const { data } = await api.get(`/vehicles/${vehicleId}/`)
    vehicleModal.data = data
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بارگذاری جزئیات سفارش ناموفق بود.')
    closeVehicleModal()
  } finally {
    vehicleModal.loading = false
  }
}

const cancelVehicle = async () => {
  if (!vehicleModal.data?.id) return
  try {
    await api.patch(`/vehicles/${vehicleModal.data.id}/status/`, { status: 'cancelled' })
    await Promise.all([reloadVehicleDetail(), fetchReports()])
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'لغو سفارش ناموفق بود.')
  }
}

const blockVehiclePlate = async (payload = {}) => {
  if (!vehicleModal.data?.id) return
  const note = String(payload?.note || '').trim()
  if (!note) {
    errorMessage.value = 'دلیل بلاک را بنویسید.'
    return
  }
  try {
    const { data } = await api.post(`/vehicles/${vehicleModal.data.id}/block-plate/`, { note })
    if (data?.vehicle) {
      vehicleModal.data = {
        ...data.vehicle,
        is_plate_blocked: true,
        blocked_plate_id: data?.id || data.vehicle.blocked_plate_id || null
      }
    } else {
      await reloadVehicleDetail()
    }
    await fetchReports()
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بلاک کردن پلاک ناموفق بود.')
  }
}

const unblockVehiclePlate = async () => {
  if (!vehicleModal.data) return
  try {
    const vehicle = vehicleModal.data
    const params = {
      plate_number: vehicle.plate_number || '',
      plate_left: vehicle.plate_left || '',
      plate_letter: vehicle.plate_letter || '',
      plate_mid: vehicle.plate_mid || '',
      plate_right: vehicle.plate_right || ''
    }
    const { data } = await api.get('/vehicles/plate-status/', {
      params,
      meta: { trackLoading: false, showErrorToast: false }
    })
    const blockedId = data?.id || vehicle.blocked_plate_id
    if (!blockedId) {
      errorMessage.value = 'رکورد بلاک برای این پلاک پیدا نشد.'
      return
    }
    closeVehicleModal()
    openBlacklistRow({
      id: blockedId,
      plate_number: data?.plate_number || vehicle.plate_number,
      plate_left: data?.plate_left || vehicle.plate_left,
      plate_letter: data?.plate_letter || vehicle.plate_letter,
      plate_mid: data?.plate_mid || vehicle.plate_mid,
      plate_right: data?.plate_right || vehicle.plate_right,
      plate_type: data?.plate_type || vehicle.plate_type || 'car',
      note: data?.note || '',
      blocked_by_name: data?.blocked_by_name || '-',
      created_at: data?.created_at || data?.blocked_at
    })
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'بارگذاری جزئیات بلاک ناموفق بود.')
  }
}

const openBlacklistRow = (row) => {
  if (!row) return
  blacklistModal.open = true
  blacklistModal.submitting = false
  blacklistModal.error = ''
  blacklistModal.row = { ...row }
}

const closeBlacklistModal = () => {
  blacklistModal.open = false
  blacklistModal.submitting = false
  blacklistModal.error = ''
  blacklistModal.row = null
}

const unblockBlacklistPlate = async () => {
  if (!blacklistModal.row?.id) return
  blacklistModal.submitting = true
  blacklistModal.error = ''
  try {
    await api.post(`/vehicles/blocked-plates/${blacklistModal.row.id}/unblock/`, {})
    closeBlacklistModal()
    await fetchReports()
  } catch (error) {
    blacklistModal.error = resolveApiErrorMessage(error, 'خارج کردن پلاک از لیست سیاه ناموفق بود.')
  } finally {
    blacklistModal.submitting = false
  }
}

const openPayoutModal = (target = 'wage') => {
  payoutModal.open = true
  payoutSubmitError.value = ''
  payoutModal.target = target
  payoutModal.mode = 'full'
  payoutModal.note = ''
  payoutModal.includeTip = false
  payoutModal.replaceId = null
  payoutModal.replaceAmount = 0
  payoutModal.insuranceMonth = String(selectedWorkerSummary.value?.insurance_month || '').split('/')[1] || '01'
  payoutModal.amount = Math.max(0, Math.round(
    target === 'insurance'
      ? selectedInsuranceMonthBalance.value || 0
      : target === 'advance'
        ? 0
        : selectedWorkerSummary.value?.payable_total || 0
  ))
}

const openEditTransaction = (row) => {
  if (!row?.id || !selectedWorkerSummary.value?.worker_id) return
  const kind = String(row.kind || '')
  if (kind === 'bonus' || kind === 'penalty') {
    adjustmentModal.open = true
    adjustmentModal.kind = kind
    adjustmentModal.amount = Math.max(0, Math.round(Number(row.amount || 0)))
    adjustmentModal.note = String(row.note || '')
    adjustmentModal.replaceId = row.id
    return
  }
  const targetMap = {
    wage_payment: 'wage',
    tip_payment: 'tip',
    insurance_payment: 'insurance',
    advance_payment: 'advance'
  }
  const target = targetMap[kind]
  if (!target) return
  payoutModal.open = true
  payoutSubmitError.value = ''
  payoutModal.target = target
  payoutModal.replaceId = row.id
  payoutModal.replaceAmount = Math.max(0, Number(row.amount || 0))
  payoutModal.includeTip = false
  payoutModal.note = String(row.note || '')
  if (target === 'advance') {
    payoutModal.mode = 'partial'
    payoutModal.amount = Math.max(0, Math.round(Number(row.amount || 0)))
    payoutModal.insuranceMonth = ''
    return
  }
  payoutModal.mode = 'partial'
  payoutModal.amount = Math.max(0, Math.round(Number(row.amount || 0)))
  if (target === 'insurance') {
    const month = normalizeInsuranceMonth(row.reference_month) || selectedWorkerSummary.value?.insurance_month || ''
    payoutModal.insuranceMonth = String(month).split('/')[1] || String(month).slice(-2) || '01'
  } else {
    payoutModal.insuranceMonth = String(selectedWorkerSummary.value?.insurance_month || '').split('/')[1] || '01'
  }
}

const closePayoutModal = () => {
  payoutModal.open = false
  payoutModal.submitting = false
  payoutModal.target = 'wage'
  payoutModal.insuranceMonth = ''
  payoutModal.includeTip = false
  payoutModal.replaceId = null
  payoutModal.replaceAmount = 0
  payoutSubmitError.value = ''
}
const submitPayout = async () => {
  if (!selectedWorkerSummary.value?.worker_id) return
  payoutSubmitError.value = ''
  const normalizedInsuranceMonth = payoutModal.target === 'insurance'
    ? normalizeInsuranceMonth(payoutModal.insuranceMonth)
    : ''
  if (payoutModal.target === 'insurance' && !normalizedInsuranceMonth) {
    payoutSubmitError.value = 'الان نمی‌توانید ثبت کنید، چون ماه بیمه به‌صورت معتبر انتخاب نشده است.'
    errorMessage.value = payoutSubmitError.value
    return
  }
  if (payoutModal.target === 'insurance' && payoutModalMaxAmount.value <= 0) {
    payoutSubmitError.value = `الان نمی‌توانید ثبت کنید، چون ماه ${normalizedInsuranceMonth} قبلا تسویه شده است.`
    errorMessage.value = payoutSubmitError.value
    return
  }
  if (!isPayoutAmountValid.value) {
    payoutSubmitError.value = payoutModal.target === 'advance'
      ? 'مبلغ مساعده باید بیشتر از صفر باشد.'
      : 'الان نمی‌توانید ثبت کنید، چون مبلغ باید بیشتر از صفر و در محدوده مانده مجاز باشد.'
    errorMessage.value = payoutSubmitError.value
    return
  }
  payoutModal.submitting = true
  try {
    const payload = {
      worker_id: selectedWorkerSummary.value.worker_id,
      payout_target: payoutModal.target,
      mode: payoutModal.target === 'advance' ? 'partial' : payoutModal.mode,
      insurance_month: normalizedInsuranceMonth || undefined,
      note: payoutModal.note || undefined,
      include_tip: payoutModal.target === 'wage' && !payoutModal.replaceId ? Boolean(payoutModal.includeTip) : undefined,
      replace_transaction_id: payoutModal.replaceId || undefined
    }
    if (payoutModal.target === 'advance' || payoutModal.mode === 'partial') {
      payload.amount = fromThousandsTomanInput(payoutModal.amount || 0)
    }
    await api.post('/reports/workers/payouts/', payload)
    if (payoutModal.target === 'insurance' && normalizedInsuranceMonth) {
      filters.insuranceMonthJalali = insuranceMonthToFilterDate(normalizedInsuranceMonth)
    }
    closePayoutModal()
    await fetchReports()
  } catch (error) {
    const fallback = payoutModal.replaceId
      ? 'الان نمی‌توانید ویرایش پرداخت را ثبت کنید.'
      : payoutModal.target === 'advance'
        ? 'الان نمی‌توانید پرداخت مساعده را ثبت کنید.'
        : payoutModal.target === 'insurance'
          ? 'الان نمی‌توانید پرداخت حق بیمه را ثبت کنید.'
          : 'الان نمی‌توانید پرداخت را ثبت کنید.'
    const reason = resolveApiErrorMessage(error, fallback)
    payoutSubmitError.value = reason.startsWith('الان نمی‌توانید')
      ? reason
      : `${fallback} ${reason}`
    errorMessage.value = payoutSubmitError.value
  } finally {
    payoutModal.submitting = false
  }
}

const openAdjustmentModal = (kind) => {
  adjustmentModal.open = true
  adjustmentModal.kind = kind
  adjustmentModal.amount = 0
  adjustmentModal.note = ''
  adjustmentModal.replaceId = null
}
const closeAdjustmentModal = () => {
  adjustmentModal.open = false
  adjustmentModal.submitting = false
  adjustmentModal.replaceId = null
}
const submitAdjustment = async () => {
  if (!selectedWorkerSummary.value?.worker_id) return
  if (!adjustmentModal.note.trim()) {
    errorMessage.value = 'توضیح پاداش یا جریمه الزامی است.'
    return
  }
  adjustmentModal.submitting = true
  try {
    await api.post('/reports/workers/adjustments/', {
      worker_id: selectedWorkerSummary.value.worker_id,
      kind: adjustmentModal.kind,
      amount: Number(adjustmentModal.amount || 0),
      note: adjustmentModal.note.trim(),
      replace_transaction_id: adjustmentModal.replaceId || undefined
    })
    closeAdjustmentModal()
    await fetchReports()
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, 'ثبت تعدیل ناموفق بود.')
  } finally {
    adjustmentModal.submitting = false
  }
}

let filterTimer = null
watch(() => [filters.q, filters.rangeKey, filters.startJalali, filters.endJalali, filters.workerId, filters.insuranceMonthJalali, filters.plateType, filters.plateLeft, filters.plateLetter, filters.plateMid, filters.plateRight], () => {
  normalizePlateFilters()
  if (filterTimer) clearTimeout(filterTimer)
  filterTimer = setTimeout(() => {
    lastWorkerSyncSignature.value = ''
    fetchReports({ withSync: true, skipWorkerAutoSync: true, resetPages: true })
  }, 280)
})

watch(activeTab, (tab) => {
  if (tab !== 'worker') return
  scheduleWorkerReportSync()
})

watch(() => [payoutModal.target, payoutModal.mode, payoutModal.insuranceMonth], () => {
  if (payoutModal.target !== 'insurance' || payoutModal.mode !== 'full') return
  payoutModal.amount = Math.max(0, Math.round(selectedInsuranceMonthBalance.value || 0))
})

onMounted(() => {
  // Registered before any await: an unmount during the initial load would
  // otherwise run the cleanup first and leave this listener attached forever.
  window.addEventListener(LIVE_EVENT_NAME, onLiveEvent)
  void Promise.all([fetchWorkers(), fetchReports()])
})

const onLiveEvent = (event) => {
  const type = String(event?.detail?.type || '')
  if (
    type.startsWith('vehicle.')
    || type.startsWith('worker.')
    || type.startsWith('payment.')
    || type.startsWith('inventory.')
    || type.startsWith('expense.')
    || type.startsWith('service.')
    || type === 'settings.updated'
    || type === 'system.full_resync_required'
  ) {
    if (liveReloadTimer) window.clearTimeout(liveReloadTimer)
    liveReloadTimer = window.setTimeout(() => {
      void fetchReports({ silent: true })
      if (type.startsWith('worker.')) void fetchWorkers({ silent: true })
    }, 700)
  }
}

onBeforeUnmount(() => {
  if (liveReloadTimer) window.clearTimeout(liveReloadTimer)
  if (filterTimer) clearTimeout(filterTimer)
  if (workerSyncTimer) clearTimeout(workerSyncTimer)
  window.removeEventListener(LIVE_EVENT_NAME, onLiveEvent)
})
</script>

<style scoped>
.reports-content{font-size:13px}
.range-bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.range-chip{border:1px solid #cbd5e1;background:#fff;color:#334155;padding:9px 16px;border-radius:999px;cursor:pointer;font-size:12px;font-weight:700;display:inline-flex;align-items:center;gap:8px}
.range-chip.active{background:#2563eb;border-color:#2563eb;color:#fff}
.filters-card{display:grid;gap:10px;padding:14px;border:1px solid #e2e8f0;border-radius:16px;margin-bottom:10px;background:linear-gradient(180deg,#fff,#f8fbff)}
.filters-top-row{display:grid;grid-template-columns:minmax(180px,1.4fr) repeat(4,minmax(120px,1fr));gap:10px;align-items:end}
.field{display:grid;gap:5px;font-size:12px;min-width:0}
.field span{display:inline-flex;align-items:center;gap:6px}
.field input,.field select{height:38px;border:1px solid #cbd5e1;border-radius:10px;padding:0 10px;font-size:12px;background:#fff}
.search-field{min-width:0}
.plate-filter-bar{
  display:flex;
  align-items:center;
  gap:10px;
  flex-wrap:nowrap;
  min-width:0;
  padding:8px 10px;
  border:1px solid #dbe5f0;
  border-radius:14px;
  background:linear-gradient(180deg,#fdfefe,#f3f7fb);
}
.plate-filter-label{display:inline-flex;align-items:center;gap:6px;color:#334155;font-size:12px;font-weight:700;white-space:nowrap;flex:0 0 auto}
.plate-type-inline{height:38px;min-width:110px;flex:0 0 auto;border:1px solid #cbd5e1;border-radius:10px;padding:0 10px;background:#fff;font-size:12px}
.plate-filter-editor{flex:0 1 auto;min-width:0;max-width:340px}
.plate-filter-bar :deep(.plate-editor){gap:0}
.plate-clear-btn{flex:0 0 auto;height:38px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#475569;padding:0 14px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
.plate-clear-btn:disabled{opacity:.45;cursor:not-allowed}
.filters-actions{margin-right:auto;display:flex;align-items:center;justify-content:flex-end;gap:12px;flex-wrap:nowrap}
.summary-grid{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:8px;margin-bottom:10px}
.kpi-card{border:1px solid #e2e8f0;border-radius:12px;padding:10px;background:#f8fbff;min-width:0}
.kpi-card p{margin:0;color:#64748b;font-size:12px}
.kpi-card strong{display:block;margin-top:6px;font-size:15px;color:#0f172a;word-break:break-word}
.kpi-hint{display:block;margin-top:6px;color:#64748b;font-size:11px;line-height:1.6}
.discount-tab-note{margin:0 0 12px;padding:10px 12px;border-radius:12px;background:#f8fafc;border:1px solid #e2e8f0;color:#475569;font-size:12px;line-height:1.8}
.tabs-bar{
  display:flex;
  flex-wrap:nowrap;
  align-items:stretch;
  gap:6px;
  overflow-x:auto;
  overflow-y:hidden;
  -webkit-overflow-scrolling:touch;
  scrollbar-width:thin;
  padding-bottom:2px;
}
.tabs-bar .chip{
  flex:1 1 0;
  min-width:max-content;
  width:auto;
  white-space:nowrap;
  padding:6px 10px;
}
.export-studio-actions{display:grid;grid-template-columns:repeat(2,minmax(180px,220px));justify-content:start;gap:12px}
.export-action-btn{border:0;border-radius:18px;padding:14px 16px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px;font-size:13px;font-weight:700;transition:transform .18s ease, box-shadow .18s ease, opacity .18s ease}
.export-action-btn:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 14px 30px rgba(15,23,42,.14)}
.export-action-btn:disabled{opacity:.7;cursor:not-allowed}
.export-action-btn.csv{background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff}
.export-action-btn.pdf{background:#fff;border:1px solid #cbd5e1;color:#0f172a}
.chip{border:0;background:#e2e8f0;color:#334155;padding:6px 12px;border-radius:14px;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;justify-content:center;gap:8px;width:100%;min-height:40px}
.chip.active,.primary-btn{background:#2563eb;color:#fff}
.primary-btn,.secondary-btn,.close-btn{border:0;border-radius:10px;padding:8px 12px;cursor:pointer}
.secondary-btn{background:#e2e8f0}
.btn-with-icon{display:inline-flex;align-items:center;gap:8px}
.danger-soft{background:#fee2e2;color:#991b1b}
.range-chip.active :deep(.iconly-shell),
.chip.active :deep(.iconly-shell),
.primary-btn :deep(.iconly-shell) { --iconly-filter: brightness(0) saturate(100%) invert(100%); }
.danger-soft :deep(.iconly-shell) { --iconly-filter: brightness(0) saturate(100%) invert(20%) sepia(78%) saturate(2280%) hue-rotate(345deg) brightness(97%) contrast(92%); }
.table-card{border:1px solid #e2e8f0;border-radius:12px;padding:10px}
.table-card h3{margin:0 0 8px;font-size:15px}
.table-wrap{
  width:100%;
  max-width:100%;
  overflow-x:auto;
  overflow-y:hidden;
  -webkit-overflow-scrolling:touch;
}
.table-card table{
  width:max-content;
  min-width:100%;
  border-collapse:separate;
  border-spacing:0;
  table-layout:auto;
  font-size:12px;
}
.table-card th,
.table-card td{
  padding:8px 10px;
  border-bottom:1px solid #e2e8f0;
  text-align:right;
  white-space:nowrap;
  vertical-align:middle;
  line-height:1.45;
  word-break:normal;
  overflow-wrap:normal;
  box-sizing:border-box;
}
.table-card th.col-plate,
.table-card td.col-plate{
  width:132px;
  min-width:132px;
  max-width:132px;
  padding:8px 8px;
  text-align:center;
  overflow:hidden;
}
.report-plate-cell{
  display:flex;
  align-items:center;
  justify-content:center;
  width:100%;
  max-width:116px;
  margin:0 auto;
  overflow:hidden;
}
.report-plate-cell :deep(.iran-plate){
  width:116px;
  max-width:116px;
  min-width:116px;
  height:28px;
  flex-shrink:0;
}
.report-plate-cell :deep(.iran-plate-motorcycle){
  height:36px;
}
.report-plate-cell :deep(.iran-plate-body),
.report-plate-cell :deep(.iran-plate-motor-body){
  gap:4px;
  padding:2px 6px;
  min-width:0;
  flex:1 1 auto;
}
.report-plate-cell :deep(.iran-plate-body strong),
.report-plate-cell :deep(.iran-plate-motor-top){
  font-size:11px;
  letter-spacing:0;
}
.report-plate-cell :deep(.iran-plate-body em),
.report-plate-cell :deep(.iran-plate-motor-bottom){
  font-size:10px;
  min-width:0;
}
.report-plate-cell :deep(.iran-plate-city){
  min-width:26px;
  padding:1px 4px;
  flex:0 0 auto;
}
.report-plate-cell :deep(.iran-plate-city small){font-size:5px}
.report-plate-cell :deep(.iran-plate-city strong){font-size:10px}
.report-plate-cell :deep(.iran-plate-ir){
  min-width:22px;
  padding:2px 3px;
  font-size:5px;
  flex:0 0 auto;
}
.error-box{margin-bottom:10px;padding:10px;background:#fee2e2;color:#991b1b;border:1px solid #fecaca;border-radius:10px}
.clickable-row{cursor:pointer}
.clickable-row.expanded{background:#f8fbff}
.services-preview-cell{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;min-width:140px}
.services-preview-text{flex:1;min-width:0;white-space:normal;word-break:break-word}
.table-card td:has(.services-preview-cell){white-space:normal;min-width:160px;max-width:220px}
.services-toggle-btn{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#475569;cursor:pointer;flex-shrink:0;transition:.18s ease}
.services-toggle-btn:hover,.services-toggle-btn.active{border-color:#2563eb;background:#eff6ff;color:#1d4ed8}
.services-toggle-dots{font-size:15px;line-height:1;transform:translateY(-1px)}
.services-expanded-row td{padding:0 6px 10px;background:#f8fbff}
.services-expanded-box{margin:0 0 0 auto;padding:12px 14px;border:1px dashed #bfdbfe;border-radius:14px;background:linear-gradient(180deg,#ffffff,#eff6ff)}
.services-expanded-box strong{display:block;margin-bottom:6px;color:#0f172a;font-size:12px}
.services-expanded-box p{margin:0;color:#334155;line-height:1.8}
.worker-head,.action-row{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}
.table-edit-btn{padding:5px 10px;font-size:11px;white-space:nowrap}
.worker-summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
.payout-card{border:1px solid #dbeafe;background:#f8fbff;border-radius:12px;padding:8px 10px}
.payout-card p{margin:0;color:#64748b;font-size:11px}
.payout-card strong{display:block;margin-top:6px;color:#0f172a;font-size:13px}
.checkbox-row{display:flex;align-items:center;gap:8px;margin:8px 0;font-size:13px;color:#334155}
.checkbox-row input{width:16px;height:16px;accent-color:#0f4c81}
.transactions-shell{margin-top:14px}
.modal-overlay{position:fixed;inset:0;background:rgba(15,23,42,.48);display:flex;align-items:center;justify-content:center;z-index:90;padding:18px}
.modal-panel{width:min(720px,100%);background:#fff;border-radius:16px;overflow:hidden}
.modal-head{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;border-bottom:1px solid #e2e8f0}
.modal-step{margin:0;color:#64748b;font-size:12px}
.modal-body{padding:16px}
.modal-body{display:grid;gap:12px;grid-template-columns:repeat(2,minmax(0,1fr))}
.modal-body label{display:grid;gap:6px}
.helper-note{grid-column:1 / -1;margin:-4px 0 0;color:#475569;font-size:12px}
.helper-note.error{color:#b91c1c}
.blacklist-modal-body{grid-template-columns:1fr}
.blacklist-modal-body p{margin:0;display:flex;justify-content:space-between;gap:12px;align-items:center;padding:10px 12px;border:1px solid #e2e8f0;border-radius:12px;background:#f8fafc}
.blacklist-modal-body p span{color:#64748b;font-size:12px}
.blacklist-modal-body p strong{color:#0f172a;font-size:13px;text-align:left}
.blacklist-plate-preview{display:flex;justify-content:center;padding:8px 0 4px}
.blacklist-modal-body .primary-btn{width:100%}

.modal-body input,.modal-body select{height:42px;border:1px solid #cbd5e1;border-radius:10px;padding:0 10px}
.pdf-format-panel{width:min(560px,100%)}
.pdf-format-body{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding:16px}
.pdf-format-option{border:1px solid #cbd5e1;border-radius:14px;background:#fff;color:#0f172a;padding:16px;display:grid;gap:6px;text-align:right;cursor:pointer}
.pdf-format-option strong{font-size:18px}
.pdf-format-option span{font-size:12px;color:#475569}
.pdf-format-option.receipt{border-color:#0f172a;background:#f8fafc}
.pdf-format-option:disabled{opacity:.56;cursor:not-allowed}
@media (max-width:1400px){.summary-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media (max-width:1200px){.filters-top-row{grid-template-columns:repeat(3,minmax(0,1fr))}.plate-filter-bar{flex-wrap:wrap}.filters-actions{margin-right:0;width:100%;justify-content:flex-start;flex-wrap:wrap}.worker-summary-grid{grid-template-columns:repeat(2,1fr)}.export-studio-actions{grid-template-columns:repeat(2,minmax(0,1fr));justify-content:stretch}}
@media (max-width:900px){.summary-grid,.worker-summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:768px){.reports-content{font-size:11px}.range-chip,.chip,.field,.field input,.field select,.modal-step{font-size:10px}.table-wrap{display:block;max-width:100%;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch}.table-wrap table{width:max-content;min-width:100%;table-layout:auto}.table-wrap th,.table-wrap td{white-space:nowrap;word-break:normal;overflow-wrap:normal}.primary-btn,.secondary-btn,.close-btn{font-size:10px;padding:7px 10px}.filters-top-row{grid-template-columns:repeat(2,minmax(0,1fr))}.summary-grid,.worker-summary-grid{grid-template-columns:repeat(2,minmax(0,1fr)) !important;gap:8px}.kpi-card{padding:10px 8px;border-radius:10px}.worker-head,.action-row,.services-preview-cell,.filters-actions{flex-direction:column;align-items:stretch}.kpi-card p,.services-expanded-box strong,.payout-card p{font-size:10px}.kpi-card strong,.payout-card strong,.table-card h3{font-size:12px}.field input,.field select,.modal-body input,.modal-body select{height:34px}.range-bar{gap:5px}.tabs-bar{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.tabs-bar .chip{width:100%;justify-content:center;min-height:40px;border-radius:12px}.modal-overlay{padding:10px}.modal-panel{max-height:calc(100vh - 20px);overflow:auto}.modal-body{grid-template-columns:repeat(2,minmax(0,1fr))}.export-studio-actions{grid-template-columns:1fr}.export-action-btn,.clear-btn{width:100%}}
@media (max-width:480px){.reports-content{font-size:10px}.range-chip,.chip,.field,.field input,.field select{font-size:9px}.primary-btn,.secondary-btn,.close-btn{font-size:9px;padding:6px 9px}.summary-grid,.worker-summary-grid{grid-template-columns:repeat(2,minmax(0,1fr)) !important;gap:6px}.kpi-card{padding:8px}.kpi-card p,.services-expanded-box strong,.services-expanded-box p,.payout-card p,.modal-step{font-size:9px}.kpi-card strong,.payout-card strong,.table-card h3{font-size:11px}.field input,.field select,.modal-body input,.modal-body select{height:32px}.plate-filter-bar,.table-card,.modal-body{padding:8px}.worker-head,.action-row{gap:6px}.filters-top-row{grid-template-columns:repeat(2,minmax(0,1fr))}.plate-type-inline,.plate-clear-btn,.plate-filter-editor{width:100%;max-width:none}}
</style>
