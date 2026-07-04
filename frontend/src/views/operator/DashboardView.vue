<template>
  <AppShell
    title="مدیریت خودروها"
    subtitle="پذیرش، تخصیص و ترخیص خودروها"
    :hide-page-header="true"
    :show-search="true"
    search-placeholder="جستجوی پلاک یا نام..."
    :search-query="search"
    @update:search-query="search = $event"
  >
    <div class="dashboard-content">
        <div class="filters">
          <button class="primary-btn" @click="openVehicleModal">ثبت خودروی جدید</button>
          <button
            v-for="item in filterItems"
            :key="item.key"
            class="chip"
            :class="{ active: activeFilter === item.key }"
            @click="activeFilter = item.key"
          >
            {{ item.label }}
          </button>
        </div>
        

        <section class="cards-grid">
          <article
            v-for="car in filteredCars"
            :key="car.id"
            class="car-card"
            :class="{ 'card-released': car.statusKey === 'released' }"
            :style="{ borderRightColor: car.color }"
            @click="openVehicleDetails(car.id)"
          >
            <div class="card-head">
              <div class="status">
                <span class="dot" :style="{ backgroundColor: car.color }"></span>
                <span>{{ car.status }}</span>
              </div>
              <span class="time" :style="{ backgroundColor: car.badgeBg, color: car.badgeText }">{{ car.time }}</span>
            </div>

            <PlateBadge
              class="plate-box"
              :plate-number="car.plateDisplay"
              :plate-left="car.plateLeft"
              :plate-letter="car.plateLetter"
              :plate-mid="car.plateMid"
              :plate-right="car.plateRight"
              :plate-type="car.plateType"
            />

            <div class="car-info">
              <h3>{{ car.model }} - {{ car.colorName }}</h3>
              <p class="service-line">{{ car.service }}</p>
              <p>راننده: {{ car.driverName }} | {{ car.driverPhone }}</p>
              <p>نیرو: {{ car.workerName }}</p>
              <p class="customer-score-row">
                <span>امتیاز مشتری:</span>
                <span class="star-track">
                  <span class="star-bg">★★★★★</span>
                  <span class="star-fill" :style="{ width: `${customerScorePercent(car.customerScore)}%` }">★★★★★</span>
                </span>
              </p>
            </div>

            <button
              v-if="car.statusKey !== 'released'"
              class="card-action"
              :class="car.actionClass"
              @click.stop="handleCardAction(car)"
            >
              {{ car.action }}
            </button>
            <div v-else class="card-passive-state">ترخیص انجام شد</div>
          </article>
        </section>
    </div>
  </AppShell>

  <div v-if="showVehicleModal" class="modal-overlay" @click.self="closeVehicleModal">
      <section class="modal-panel" :class="{ 'step-one-modal-panel': modalStep === 1, 'step-two-modal-panel': modalStep === 2 }">
        <template v-if="modalStep === 1">
          <header class="modal-head">
            <div>
              <p class="modal-step">مرحله {{ modalStep }} از فرآیند پذیرش</p>
              <h2>ثبت ورود خودرو</h2>
            </div>
            <button class="close-btn" @click="closeVehicleModal">✕</button>
          </header>
          <div class="step-one-scroll-body">
            <VehicleEntryStepOne
              :vehicle-info="vehicleDraft"
              @continue="handleStepOneContinue"
              @refer="handleStepOneRefer"
            />
          </div>
        </template>

        <VehicleEntryStepTwo
          v-else
          :vehicle-info="vehicleDraft"
          @back="modalStep = 1"
          @close="closeVehicleModal"
          @assign="handleStepTwoAssign"
        />
      </section>
    </div>

    <VehicleDetailsModal
      :open="showVehicleDetailsModal"
      :vehicle="selectedVehicle"
      title="جزئیات کامل خودرو"
      @close="closeVehicleDetails"
      @cancel="cancelVehicle"
      @block-plate="blockSelectedVehiclePlate"
    />
    <div v-if="showReleaseModal" class="modal-overlay" @click.self="closeReleaseModal">
      <section class="modal-panel release-panel">
        <header class="modal-head release-modal-head">
          <div class="release-modal-copy">
            <p class="modal-step">ترخیص خودرو</p>
            <h2>اتمام کار و فروش محصولات</h2>
          </div>
          <div class="release-modal-tools">
            <button class="close-btn" @click="closeReleaseModal">✕</button>
          </div>
        </header>
        <div v-if="releaseCheckoutLoading" class="release-loading">
          <BaseSpinner size="66px" color="#1d4ed8" ball-color="#60a5fa" label="در حال بارگذاری اطلاعات ترخیص..." />
        </div>
        <div v-else class="release-modal-body">
          <div v-if="showReleaseServicePicker" class="service-picker-overlay" role="dialog" aria-modal="true">
            <section class="service-picker-panel">
              <header class="service-picker-head">
                <div>
                  <h4>ویرایش خدمات</h4>
                  <p>{{ tempReleaseServiceIds.length.toLocaleString('fa-IR') }} خدمت انتخاب شده</p>
                </div>
                <button type="button" class="icon-btn" aria-label="بستن" @click="closeReleaseServicePicker">
                  ✕
                </button>
              </header>

              <div class="service-picker-grid release-service-picker-grid">
                <button
                  v-for="service in releaseForm.availableServicesToAdd"
                  :key="service.id"
                  type="button"
                  class="service-bubble"
                  :class="{ selected: tempReleaseServiceIds.includes(Number(service.id)) }"
                  @click="toggleTempReleaseService(service.id)"
                >
                  {{ service.name }}
                </button>
              </div>

              <p v-if="!releaseForm.availableServicesToAdd.length" class="empty">خدمتی برای انتخاب وجود ندارد.</p>

              <footer class="service-picker-foot">
                <button type="button" class="secondary-foot-btn" @click="closeReleaseServicePicker">انصراف</button>
                <button type="button" class="primary-btn" @click="confirmReleaseServicePicker">ثبت خدمات</button>
              </footer>
            </section>
          </div>
          <div class="release-layout" :class="{ 'release-layout-no-products': !hasReleaseProducts }">
            <div class="release-col">
            <div class="release-title release-title-inline">
              <h3>خدمات</h3>
              <button type="button" class="secondary-btn small-btn" @click="openReleaseServicePicker">
                ویرایش
              </button>
            </div>
            <div class="release-list">
              <article v-for="(line, lineIndex) in visibleReleaseServiceLines" :key="line.id || `service-${line.service_id || lineIndex}`" class="service-check-item">
                <div>
                  <h4>{{ line.service_name }}</h4>
                </div>
                <div class="service-check-action">
                  <span>{{ formatMoney(line.line_total) }}</span>
                  <label>
                    <input
                      v-model="line.is_completed"
                      type="checkbox"
                    />
                    انجام شد
                  </label>
                </div>
              </article>
              <p v-if="!visibleReleaseServiceLines.length" class="empty-row">خدمتی برای این خودرو ثبت نشده است.</p>
            </div>
            
            </div>

            <div v-if="hasReleaseProducts" class="release-col release-products-col">
            <div class="release-title">
              <h3>محصولات جانبی</h3>
            </div>
            <div class="release-product-search">
              <input v-model="releaseForm.productSearch" type="text" placeholder="جستجوی محصول..." />
            </div>
            <div class="release-list products-scroll">
              <article
                v-for="product in filteredReleaseProducts"
                :key="product.id"
                class="product-item"
                :class="{ unavailable: Number(product.available_quantity || 0) <= 0 }"
              >
                <div>
                  <h4>{{ product.name }}</h4>
                  <p :class="{ 'stock-empty': Number(product.available_quantity || 0) <= 0 }">
                    موجودی: {{ Number(product.available_quantity || 0).toLocaleString('fa-IR') }}
                  </p>
                  <span>{{ formatMoney(product.sale_price) }}</span>
                </div>
                <div class="qty-controls">
                  <div class="qty-actions">
                    <button type="button" @click="decreaseReleaseProduct(product.id)">-</button>
                    <button
                      type="button"
                      @click="increaseReleaseProduct(product.id)"
                      :disabled="Number(product.available_quantity || 0) <= Number(getReleaseProductQty(product.id))"
                    >
                      +
                    </button>
                  </div>
                  <input
                    type="number"
                    min="0"
                    :max="Number(product.available_quantity || 0)"
                    :value="getReleaseProductQty(product.id)"
                    @input="setReleaseProductQty(product.id, $event.target.value)"
                  />
                </div>
              </article>
            </div>
            </div>

            <div class="release-col release-summary-col">
            <div class="release-title release-title-inline">
              <h3>خلاصه نهایی</h3>
              <button type="button" class="secondary-btn invoice-preview-btn" @click="openInvoicePreviewModal">
                فاکتور
              </button>
            </div>
            <div class="release-summary-hero">
              <div>
                <small>مبلغ قابل دریافت</small>
                <strong>{{ formatMoney(releaseSummary.finalTotal) }}</strong>
                <p>ترخیص، پرداخت و سهم پرسنل را از همین بخش نهایی کنید.</p>
              </div>
              <div class="release-summary-badge">{{ paymentMethodLabel(releaseForm.paymentMethod) }}</div>
            </div>
            <div class="summary-stat-grid">
              <article class="summary-stat-card">
                <span>جمع خدمات</span>
                <strong>{{ formatMoney(releaseSummary.servicesTotal) }}</strong>
              </article>
              <article class="summary-stat-card">
                <span>محصولات جانبی</span>
                <strong>{{ formatMoney(releaseSummary.productsTotal) }}</strong>
              </article>
              <article class="summary-stat-card">
                <span>تخفیف</span>
                <strong>{{ formatMoney(releaseSummary.discountAmount) }}</strong>
                <small>{{ formatPercent(releaseSummary.customerDiscountPercent) }}</small>
              </article>
              <article class="summary-stat-card accent-card">
                <span>انعام</span>
                <strong>{{ formatMoney(releaseSummary.tipAmount) }}</strong>
              </article>
            </div>
            <label class="tip-input-row modern-input-row">
              <span>انعام (هزار تومان)</span>
              <input v-model.number="releaseForm.tipAmount" type="number" min="0" step="1" />
            </label>
            <div class="worker-selection-panel">
              <div class="worker-selection-head">
                <div>
                  <h4>انتخاب نیروها</h4>
                  <p>هر نیرو را جداگانه فعال کنید. فقط نیروهای فعال در سهم این تسویه محاسبه می‌شوند.</p>
                </div>
                <button
                  v-if="releaseForm.assignedWorkers.length > 1 && selectedAssignedWorkers.length !== releaseForm.assignedWorkers.length"
                  type="button"
                  class="secondary-btn small-btn"
                  @click="activateAllReleaseWorkers"
                >
                  انتخاب همه
                </button>
              </div>
              <div v-if="releaseForm.assignedWorkers.length" class="worker-selection-grid">
                <button
                  v-for="(worker, index) in releaseForm.assignedWorkers"
                  :key="`worker-toggle-${worker.id || index}`"
                  type="button"
                  class="worker-select-card"
                  :class="{ selected: worker.isSelected !== false }"
                  @click="toggleReleaseWorkerSelection(index)"
                >
                  <span class="worker-select-check">{{ worker.isSelected !== false ? '✓' : '+' }}</span>
                  <strong>{{ worker.name || `نیروی ${Number(index + 1).toLocaleString('fa-IR')}` }}</strong>
                  <small>{{ worker.isSelected !== false ? 'فعال در این تسویه' : 'غیرفعال در این تسویه' }}</small>
                </button>
              </div>
              <p v-else class="empty-row">برای این سفارش نیرویی ثبت نشده است.</p>
            </div>
            <div class="summary-share">
              <p
                v-for="(worker, index) in releaseSummary.workerShares"
                :key="`${worker.name || 'worker'}-${index}`"
              >
                <span>
                  سهم {{ worker.name || `نیروی ${Number(index + 1).toLocaleString('fa-IR')}` }}
                  <small v-if="selectedAssignedWorkers.length > 1">({{ Number(worker.percent || 0).toLocaleString('fa-IR') }}٪)</small>
                </span>
                <strong>{{ formatMoney(worker.amount) }}</strong>
              </p>
              <p v-if="!releaseSummary.workerShares.length">
                <span>سهم نیرو</span>
                <strong>{{ formatMoney(0) }}</strong>
              </p>
              <p class="summary-share-total">
                <span>جمع سهم کارواش</span>
                <strong>{{ formatMoney(releaseSummary.carwashShare) }}</strong>
              </p>
            </div>
            <p class="summary-final"><span>جمع کل</span><strong>{{ formatMoney(releaseSummary.finalTotal) }}</strong></p>
            
            <div class="release-actions">
              <button type="button" class="back-btn" @click="closeReleaseModal">انصراف</button>
              <button type="button" class="confirm-release-btn" :disabled="releaseSubmitting" @click="confirmReleaseVehicle">
                {{ releaseSubmitting ? 'در حال ثبت...' : 'تایید و ترخیص خودرو' }}
              </button>
            </div>
          </div>
          </div>
          <section class="release-secondary-section">
            <div class="release-secondary-head">
              <div>
                <h4>پرداخت و ثبت‌های تکمیلی</h4>
                <small>روش پرداخت، چک، نسیه و پاداش یا جریمه را اینجا نهایی کنید.</small>
              </div>
              <div class="release-secondary-chip">{{ paymentMethodLabel(releaseForm.paymentMethod) }}</div>
            </div>
            <div class="release-secondary-grid">
              <label class="tip-input-row detail-field">
                <span>شیوه پرداخت</span>
                <select v-model="releaseForm.paymentMethod">
                  <option value="pos">دستگاه پوز</option>
                  <option value="cash">نقدی</option>
                  <option value="transfer">کارت به کارت</option>
                  <option value="cheque">چک</option>
                  <option value="credit">نسیه</option>
                  <option value="manual">اسنادی / ترکیبی</option>
                </select>
              </label>
              <div v-if="releaseForm.paymentMethod === 'manual'" class="detail-field detail-field-wide split-payment-grid">
                <label class="tip-input-row">
                  <span>مبلغ نقدی (هزار تومان)</span>
                  <input v-model.number="releaseForm.manualCashAmount" type="number" min="0" step="1" />
                </label>
                <label class="tip-input-row">
                  <span>روش بخش دوم</span>
                  <select v-model="releaseForm.manualSecondaryMethod">
                    <option value="transfer">کارت به کارت</option>
                    <option value="pos">دستگاه پوز</option>
                    <option value="cheque">چک</option>
                  </select>
                </label>
                <label class="tip-input-row">
                  <span>مبلغ بخش دوم (هزار تومان)</span>
                  <input v-model.number="releaseForm.manualSecondaryAmount" type="number" min="0" step="1" />
                </label>
                <div class="split-payment-summary">
                  <strong>جمع پرداخت ترکیبی</strong>
                  <span>{{ releasePaymentBreakdownLabel || 'هنوز بخشی ثبت نشده است.' }}</span>
                </div>
              </div>
              <div v-if="releaseForm.paymentMethod === 'cheque' || (releaseForm.paymentMethod === 'manual' && releaseForm.manualSecondaryMethod === 'cheque' && Number(releaseForm.manualSecondaryAmount || 0) > 0)" class="cheque-inline-card detail-field-wide">
                <div class="cheque-inline-head">
                <div>
                  <strong>جزئیات چک</strong>
                  <small>{{ chequeDetailsSummary }}</small>
                </div>
                <button type="button" class="secondary-btn" @click="openChequeDetailsModal">ثبت جزئیات چک</button>
              </div>
              </div>
              <label v-if="releaseForm.paymentMethod === 'credit'" class="tip-input-row detail-field">
                <span>تاریخ سررسید نسیه</span>
                <BaseDatePicker v-model="releaseForm.creditDueDate" placeholder="1405/01/30" />
              </label>
              <div class="detail-field detail-field-wide bonus-penalty-table">
                <div class="bonus-penalty-table-head">
                  <span>نیرو برای پاداش/جریمه</span>
                  <small>برای هر نیروی این سفارش، مبلغ جدا ثبت کنید.</small>
                </div>
                <div v-if="releaseForm.bonusPenaltyAdjustments.length" class="bonus-penalty-list">
                  <div v-for="(adjustment, index) in releaseForm.bonusPenaltyAdjustments" :key="`adjustment-${adjustment.worker_id || index}`" class="bonus-penalty-item">
                    <strong>{{ adjustment.worker_name || `نیروی ${Number(index + 1).toLocaleString('fa-IR')}` }}</strong>
                    <label class="tip-input-row">
                      <span>پاداش (هزار تومان)</span>
                      <input v-model.number="adjustment.bonus" type="number" min="0" step="1" />
                    </label>
                    <label class="tip-input-row">
                      <span>جریمه (هزار تومان)</span>
                      <input v-model.number="adjustment.penalty" type="number" min="0" step="1" />
                    </label>
                  </div>
                </div>
                <p v-else class="empty-row">برای این سفارش نیرویی ثبت نشده است.</p>
              </div>
              <label v-if="hasReleaseBonusOrPenalty" class="tip-input-row detail-field detail-field-wide">
                <span>توضیح پاداش/جریمه</span>
                <textarea v-model.trim="releaseForm.bonusPenaltyNote" rows="3" placeholder="دلیل ثبت پاداش یا جریمه را وارد کنید"></textarea>
              </label>
            </div>
          </section>
        </div>
      </section>
    </div>
    <div v-if="showChequeDetailsModal" class="modal-overlay" @click.self="closeChequeDetailsModal">
      <section class="modal-panel action-panel cheque-modal-panel">
        <header class="modal-head cheque-modal-head">
          <div>
            <p class="modal-step">پرداخت با چک</p>
            <h3>ثبت جزئیات چک</h3>
            <p class="cheque-modal-subtitle">اطلاعات چک را کامل وارد کنید تا در فاکتور و ثبت نهایی ذخیره شود.</p>
          </div>
          <button class="close-btn" @click="closeChequeDetailsModal">✕</button>
        </header>
        <div class="modal-body cheque-modal-body">
          <div class="cheque-modal-summary">
            <small>مبلغ چک</small>
            <strong>{{ formatMoney(Number(releaseForm.chequeAmount || 0) * 1000 || releaseSummary.finalTotal) }}</strong>
            <p>جمع قابل ثبت برای این سفارش</p>
            <span>{{ chequeDetailsSummary }}</span>
          </div>
          <div class="cheque-fields-grid">
            <label class="cheque-field">
              <span>تاریخ وصول</span>
              <BaseDatePicker v-model="releaseForm.creditDueDate" placeholder="1405/01/30" />
            </label>
            <label class="cheque-field">
              <span>شماره سریال</span>
              <input v-model.trim="releaseForm.chequeSerialNumber" type="text" />
            </label>
            <label class="cheque-field">
              <span>شماره صیادی</span>
              <input v-model.trim="releaseForm.chequeSayadiNumber" type="text" />
            </label>
            <label class="cheque-field">
              <span>بانک</span>
              <input v-model.trim="releaseForm.chequeBank" type="text" />
            </label>
            <label class="cheque-field cheque-field-wide">
              <span>شبا</span>
              <input v-model.trim="releaseForm.chequeShaba" type="text" />
            </label>
            <label class="cheque-field">
              <span>مبلغ (هزار تومان)</span>
              <input v-model.number="releaseForm.chequeAmount" type="number" min="1" step="1" />
            </label>
          </div>
          <div class="cheque-modal-actions">
            <button type="button" class="secondary-btn" @click="closeChequeDetailsModal">بستن</button>
            <button class="primary-btn" type="button" @click="closeChequeDetailsModal">تایید جزئیات چک</button>
          </div>
        </div>
      </section>
    </div>
    <div v-if="showInvoicePreviewModal" class="modal-overlay invoice-modal-overlay" @click.self="closeInvoicePreviewModal">
      <section class="modal-panel invoice-modal-panel">
        <header class="modal-head invoice-modal-head">
          <div>
            <h3>پیش‌نمایش فاکتور</h3>
            <p class="invoice-modal-subtitle">قالب چاپ را بین A4، A5 و فیش پرینتر عوض کنید و همان خروجی را برای PDF یا چاپ بگیرید.</p>
          </div>
          <button class="close-btn" @click="closeInvoicePreviewModal">✕</button>
        </header>
        <div class="invoice-modal-body">
          <div class="invoice-format-toolbar">
            <div class="invoice-format-presets">
              <button
                v-for="option in invoicePresetOptions"
                :key="option.key"
                type="button"
                class="invoice-format-chip"
                :class="{ active: invoiceLayout.preset === option.key }"
                @click="invoiceLayout.preset = option.key"
              >
                {{ option.label }}
              </button>
            </div>
            <div v-if="invoiceIsThermal" class="invoice-thermal-size-grid">
              <label>
                <span>عرض فیش (mm)</span>
                <input v-model.number="invoiceLayout.thermalWidthMm" type="number" min="48" max="120" step="1" />
              </label>
              <label>
                <span>طول فیش (mm)</span>
                <input v-model.number="invoiceLayout.thermalHeightMm" type="number" min="80" max="600" step="1" />
              </label>
            </div>
          </div>
          <div class="invoice-modal-actions">
            <button type="button" class="secondary-btn" :disabled="invoiceGenerating" @click="refreshInvoicePreview">
              {{ invoiceGenerating ? 'در حال ساخت...' : 'بروزرسانی فاکتور' }}
            </button>
            <button type="button" class="secondary-btn" :disabled="!invoicePdfUrl || invoiceGenerating" @click="downloadInvoicePdf">
              دانلود PDF
            </button>
            <button type="button" class="secondary-btn" :disabled="!invoicePdfUrl || invoiceGenerating" @click="printInvoicePdf">
              چاپ
            </button>
          </div>
          <div v-if="invoiceGenerating" class="invoice-preview-loading">
            <BaseSpinner size="56px" color="#1d4ed8" ball-color="#60a5fa" label="در حال ساخت فایل PDF فاکتور..." />
          </div>
          <div v-else-if="invoicePdfUrl" class="invoice-preview-frame-wrap">
            <iframe ref="invoicePreviewFrameRef" :src="invoicePreviewUrl" title="invoice-pdf-preview" class="invoice-preview-frame"></iframe>
          </div>
          <div v-else class="invoice-preview-empty">
            {{ invoiceErrorMessage || 'فاکتور هنوز ساخته نشده است.' }}
          </div>
        </div>
      </section>
    </div>
    <div class="invoice-print-stage" :style="invoiceStageStyle">
      <div ref="invoiceTemplateRef" class="invoice-template" :style="invoiceTemplateStyle">
        <div class="invoice-sheet" :class="invoiceSheetClass" :style="invoiceSheetStyle">
          <template v-if="invoiceIsThermal">
            <header class="thermal-sheet-head">
              <strong>کارنوواش</strong>
              <span>رسید سفارش #{{ Number(releaseCandidate?.id || 0).toLocaleString('fa-IR') }}</span>
              <small>{{ invoiceIssuedAt }}</small>
            </header>

            <section class="thermal-sheet-block">
              <p><span>مشتری</span><strong>{{ invoiceCustomerName }}</strong></p>
              <p><span>تلفن</span><strong>{{ invoiceCustomerPhone }}</strong></p>
              <p><span>خودرو</span><strong>{{ invoiceVehicleTitle }}</strong></p>
              <p><span>پلاک</span><strong>{{ invoicePlateLabel }}</strong></p>
              <p><span>پرداخت</span><strong>{{ paymentMethodLabel(releaseForm.paymentMethod) }}</strong></p>
            </section>

            <section class="thermal-sheet-block">
              <div class="thermal-lines-head">
                <strong>خدمات</strong>
                <span>{{ invoiceServiceLines.length.toLocaleString('fa-IR') }} ردیف</span>
              </div>
              <div v-for="(line, lineIndex) in invoiceServiceLines" :key="`thermal-service-${line.id || lineIndex}`" class="thermal-line-row">
                <div>
                  <strong>{{ line.service_name }}</strong>
                  <small>تعداد {{ Number(line.quantity || 1).toLocaleString('fa-IR') }}</small>
                </div>
                <span>{{ formatMoney(line.line_total) }}</span>
              </div>
              <div v-for="product in invoiceProductLines" :key="`thermal-product-${product.id}`" class="thermal-line-row thermal-line-row-product">
                <div>
                  <strong>{{ product.name }}</strong>
                  <small>محصول × {{ Number(product.quantity || 0).toLocaleString('fa-IR') }}</small>
                </div>
                <span>{{ formatMoney(product.total) }}</span>
              </div>
            </section>

            <section class="thermal-sheet-block thermal-total-block">
              <p><span>جمع خدمات</span><strong>{{ formatMoney(releaseSummary.servicesTotal) }}</strong></p>
              <p><span>محصولات</span><strong>{{ formatMoney(releaseSummary.productsTotal) }}</strong></p>
              <p><span>تخفیف</span><strong>{{ formatMoney(releaseSummary.discountAmount) }}</strong></p>
              <p><span>انعام</span><strong>{{ formatMoney(releaseSummary.tipAmount) }}</strong></p>
              <p class="thermal-grand-total"><span>مبلغ نهایی</span><strong>{{ formatMoney(releaseSummary.finalTotal) }}</strong></p>
            </section>

            <footer class="thermal-sheet-footer">
              <p v-if="releasePaymentBreakdownLabel">ترکیبی: {{ releasePaymentBreakdownLabel }}</p>
              <p v-if="invoiceDueDateLabel">سررسید: {{ invoiceDueDateLabel }}</p>
              <p v-if="releaseForm.receiptFooterNote">{{ releaseForm.receiptFooterNote }}</p>
              <p>CarnoWash</p>
            </footer>
          </template>

          <template v-else>
          <header class="invoice-sheet-head">
            <div>
              <small>CarnoWash</small>
              <strong>فاکتور نهایی سفارش</strong>
              <span>شماره فاکتور: {{ invoiceNumber }}</span>
            </div>
            <div class="invoice-sheet-meta">
              <strong>کارنوواش | CarnoWash</strong>
              <span>تاریخ صدور: {{ invoiceIssuedAt }}</span>
              <span>روش پرداخت: {{ paymentMethodLabel(releaseForm.paymentMethod) }}</span>
            </div>
          </header>

          <section class="invoice-identity-grid">
            <article>
              <small>اطلاعات مشتری</small>
              <p><span>نام</span><strong>{{ invoiceCustomerName }}</strong></p>
              <p><span>شماره تماس</span><strong>{{ invoiceCustomerPhone }}</strong></p>
              <p><span>امتیاز مشتری</span><strong>{{ formatCustomerScore(releaseForm.customerScore) }} | {{ releaseCustomerScoreStars }}</strong></p>
            </article>
            <article>
              <small>مشخصات خودرو</small>
              <p><span>خودرو</span><strong>{{ invoiceVehicleTitle }}</strong></p>
              <p><span>پلاک</span><strong>{{ invoicePlateLabel }}</strong></p>
              <p><span>نوع پذیرش</span><strong>{{ invoiceAdmissionLabel }}</strong></p>
            </article>
            <article>
              <small>اطلاعات سفارش</small>
              <p><span>شماره سفارش</span><strong>#{{ Number(releaseCandidate?.id || 0).toLocaleString('fa-IR') }}</strong></p>
              <p><span>وضعیت پرداخت</span><strong>{{ invoicePaymentStatusLabel }}</strong></p>
              <p><span>تاریخ ورود</span><strong>{{ invoiceCheckInLabel }}</strong></p>
            </article>
          </section>

          <section class="invoice-sheet-section">
            <div class="invoice-section-head">
              <strong>ریز خدمات انجام‌شده</strong>
            </div>
            <table class="invoice-table invoice-services-table">
              <thead>
                <tr>
                  <th>عنوان</th>
                  <th>تعداد</th>
                  <th>مبلغ</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(line, lineIndex) in invoiceServiceLines" :key="`invoice-service-${line.id || lineIndex}`">
                  <td>{{ line.service_name }}</td>
                  <td>{{ Number(line.quantity || 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ formatMoney(line.line_total) }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section class="invoice-sheet-section" v-if="invoiceProductLines.length">
            <div class="invoice-section-head">
              <strong>محصولات جانبی فروخته‌شده</strong>
            </div>
            <table class="invoice-table invoice-products-table">
              <thead>
                <tr>
                  <th>عنوان</th>
                  <th>تعداد</th>
                  <th>قیمت واحد</th>
                  <th>مبلغ</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="product in invoiceProductLines" :key="`invoice-product-${product.id}`">
                  <td>{{ product.name }}</td>
                  <td>{{ Number(product.quantity || 0).toLocaleString('fa-IR') }}</td>
                  <td>{{ formatMoney(product.unitPrice) }}</td>
                  <td>{{ formatMoney(product.total) }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section class="invoice-sheet-section invoice-payment-section">
            <div class="invoice-section-head">
              <strong>جزئیات پرداخت</strong>
            </div>
            <div class="invoice-payment-grid">
              <p><span>روش پرداخت</span><strong>{{ paymentMethodLabel(releaseForm.paymentMethod) }}</strong></p>
              <p><span>وضعیت</span><strong>{{ invoicePaymentStatusLabel }}</strong></p>
              <p v-if="releasePaymentBreakdownLabel"><span>پرداخت ترکیبی</span><strong>{{ releasePaymentBreakdownLabel }}</strong></p>
              <p v-if="invoiceDueDateLabel"><span>سررسید</span><strong>{{ invoiceDueDateLabel }}</strong></p>
              <p v-if="invoiceChequeLabel"><span>اطلاعات چک</span><strong>{{ invoiceChequeLabel }}</strong></p>
            </div>
          </section>

          <section class="invoice-sheet-section invoice-total-section">
            <div class="invoice-section-head">
              <strong>خلاصه مالی مشتری</strong>
            </div>
            <div class="invoice-totals">
              <p><span>جمع قبل از تخفیف</span><strong>{{ formatMoney(invoiceSubtotal) }}</strong></p>
              <p><span>جمع خدمات</span><strong>{{ formatMoney(releaseSummary.servicesTotal) }}</strong></p>
              <p><span>جمع محصولات</span><strong>{{ formatMoney(releaseSummary.productsTotal) }}</strong></p>
              <p v-if="releaseSummary.customerDiscountAmount > 0"><span>تخفیف امتیاز مشتری</span><strong>{{ formatMoney(releaseSummary.customerDiscountAmount) }}</strong></p>
              <p v-if="releaseSummary.manualDiscountAmount > 0"><span>تخفیف دستی</span><strong>{{ formatMoney(releaseSummary.manualDiscountAmount) }}</strong></p>
              <p><span>جمع تخفیف</span><strong>{{ formatMoney(releaseSummary.discountAmount) }}</strong></p>
              <p><span>انعام</span><strong>{{ formatMoney(releaseSummary.tipAmount) }}</strong></p>
              <p class="invoice-grand-total"><span>مبلغ نهایی</span><strong>{{ formatMoney(releaseSummary.finalTotal) }}</strong></p>
            </div>
          </section>

          <footer class="invoice-sheet-footer">
            <p v-if="invoiceCustomerNote">توضیحات سفارش: {{ invoiceCustomerNote }}</p>
            <p v-if="releaseForm.receiptFooterNote">{{ releaseForm.receiptFooterNote }}</p>
            <p>کارنوواش | CarnoWash</p>
          </footer>
          </template>
        </div>
      </div>
    </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import VehicleEntryStepOne from '../../components/operator/VehicleEntryStepOne.vue'
import VehicleEntryStepTwo from '../../components/operator/VehicleEntryStepTwo.vue'
import BaseSpinner from '../../components/base/BaseSpinner.vue'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import AppShell from '../../components/layout/AppShell.vue'
import PlateBadge from '../../components/vehicles/PlateBadge.vue'
import VehicleDetailsModal from '../../components/vehicles/VehicleDetailsModal.vue'
import { useVehicleStore } from '../../store/vehicle.store'
import api from '../../services/api'
import { formatThousandsToman } from '../../utils/money'
import { resolveApiErrorMessage } from '../../utils/apiError'
import { notifyError, notifyWarning } from '../../utils/notify'
import { buildPlateNumber, isAnonymousPlate, normalizeDigits, resolvePlateParts, splitPlate } from '../../utils/plate'

const search = ref('')
const activeFilter = ref('entered')
const showVehicleModal = ref(false)
const showVehicleDetailsModal = ref(false)
const showReleaseModal = ref(false)
const showChequeDetailsModal = ref(false)
const showInvoicePreviewModal = ref(false)
const showReleaseServicePicker = ref(false)
const releaseCheckoutLoading = ref(false)
const releaseSubmitting = ref(false)
const invoiceGenerating = ref(false)
const invoicePdfUrl = ref('')
const invoiceErrorMessage = ref('')
const modalStep = ref(1)
const vehicleDraft = ref(null)
const releaseCandidate = ref(null)
const invoiceTemplateRef = ref(null)
const invoicePreviewFrameRef = ref(null)
const tempReleaseServiceIds = ref([])
const invoiceRenderTimer = ref(null)
const invoiceLayout = ref({
  preset: 'a4',
  thermalWidthMm: 80,
  thermalHeightMm: 220
})
const releasePaymentMethods = ['pos', 'cash', 'transfer', 'cheque', 'credit', 'manual']
const releaseForm = ref({
  serviceLines: [],
  availableProducts: [],
  productLinesByProductId: {},
  productSearch: '',
  tipAmount: 0,
  assignedWorkers: [],
  workerShareAmount: 0,
  customerScore: 0,
  discountPercentPerHalfStar: 0,
  manualDiscountTotal: 0,
  paymentMethod: 'cash',
  manualCashAmount: 0,
  manualSecondaryMethod: 'transfer',
  manualSecondaryAmount: 0,
  chequeNumber: '',
  chequeSerialNumber: '',
  chequeSayadiNumber: '',
  chequeBank: '',
  chequeShaba: '',
  chequeAmount: 0,
  creditDueDate: '',
  receiptFooterNote: '',
  receiptPrinterPaperWidth: '80mm',
  receiptPrintCopies: 1,
  bonusPenaltyAdjustments: [],
  bonusPenaltyNote: '',
  newServiceLines: [],
  availableServicesToAdd: [],
  selectedServiceToAdd: 0
})
const vehicleStore = useVehicleStore()
const { vehicles, selectedVehicle } = storeToRefs(vehicleStore)
const hasOperatorModalOpen = computed(() => (
  showVehicleModal.value
  || showVehicleDetailsModal.value
  || showReleaseModal.value
  || showChequeDetailsModal.value
  || showInvoicePreviewModal.value
))

const openVehicleModal = () => {
  modalStep.value = 1
  vehicleDraft.value = null
  showVehicleModal.value = true
}
const closeVehicleModal = () => {
  showVehicleModal.value = false
  modalStep.value = 1
  vehicleDraft.value = null
}
const openVehicleDetails = async (vehicleId) => {
  try {
    const { data } = await api.get(`/vehicles/${vehicleId}/`)
    vehicleStore.selectedVehicle = data
    showVehicleDetailsModal.value = true
  } catch (error) {
    console.error('fetchVehicleDetail error:', error?.response?.data || error)
    notifyError('بارگذاری جزئیات خودرو ناموفق بود.', { title: 'جزئیات خودرو' })
  }
}
const closeVehicleDetails = () => {
  showVehicleDetailsModal.value = false
}
const lockBodyScrollForModal = () => {
  if (typeof document === 'undefined') return
  document.documentElement.classList.add('modal-open')
  document.body.classList.add('modal-open')
}
const unlockBodyScrollForModal = () => {
  if (typeof document === 'undefined') return
  document.documentElement.classList.remove('modal-open')
  document.body.classList.remove('modal-open')
}
const formatStatus = (value) => ({
  entered: 'وارد شده',
  assigned: 'تخصیص داده شده',
  in_progress: 'در حال انجام',
  ready_to_settle: 'آماده تسویه',
  released: 'تحویل شده',
  cancelled: 'لغو شده'
}[value] || '-')
const formatMoney = (value) => formatThousandsToman(value)
const formatPercent = (value) => `${Number(value || 0).toLocaleString('fa-IR')}٪`
const formatDateTime = (value) => {
  if (!value) return '-'
  return new Intl.DateTimeFormat('fa-IR', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}
const apiErrorText = (error, fallback = 'عملیات ناموفق بود.') => resolveApiErrorMessage(error, fallback)
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
const paymentMethodLabel = (value) => ({
  pos: 'دستگاه پوز',
  cash: 'نقدی',
  transfer: 'کارت به کارت',
  cheque: 'چک',
  credit: 'نسیه',
  manual: 'اسنادی / ترکیبی'
}[value] || 'نامشخص')
const paymentStatusLabel = (value) => ({
  unpaid: 'پرداخت نشده',
  partial: 'پرداخت ناقص',
  paid: 'پرداخت شده',
  refunded: 'مرجوع شده'
}[value] || 'در انتظار ثبت')
const customerScorePercent = (score) => {
  const normalized = Math.max(0, Math.min(5, Number(score || 0)))
  return (normalized / 5) * 100
}
const formatCustomerScore = (score) => `${Number(score || 0).toLocaleString('fa-IR')} / ۵`
const releaseCustomerScoreStars = computed(() => '★'.repeat(Math.round(Math.max(0, Math.min(5, Number(releaseForm.value.customerScore || 0))))) || '—')
const releaseVehicleSource = computed(() => releaseCandidate.value || selectedVehicle.value || {})
const releaseVehicleHeaderLabel = computed(() => {
  const source = releaseVehicleSource.value || {}
  const model = String(source.car_model || source.model || '').trim()
  const color = String(source.car_color || source.color || '').trim()
  return `${model} ${color}`.trim()
})
const releaseVehiclePlateLabel = computed(() => {
  const source = releaseVehicleSource.value || {}
  const rawPlate = String(source.plate_number || source.plate || '').trim()
  if (rawPlate) return rawPlate
  return buildPlateNumber(resolvePlateParts(source))
})
const mapVehicleToDraft = (source = {}) => ({
  id: source.id,
  plate: source.plate_number,
  plate_left: source.plate_left,
  plate_letter: source.plate_letter,
  plate_mid: source.plate_mid,
  plate_right: source.plate_right,
  plate_type: source.plate_type || 'car',
  plateType: source.plate_type || 'car',
  model: source.car_model,
  color: source.car_color,
  driver: source.driver_name,
  mobile: source.driver_phone,
  note: source.notes,
  tariffType: source.tariff_type || source.tariffType || 'type_1',
  isPieceWash: Boolean(source.is_piece_wash),
  pieceDetails: source.piece_details || '',
  pieceWashPrice: Number(source.job?.services_total || 0),
  isAnonymous: isAnonymousPlate(source),
  is_plate_blocked: Boolean(source.is_plate_blocked),
  serviceIds: Array.isArray(source.job?.service_lines) ? source.job.service_lines.map((s) => s.service) : [],
  staffId: source.job?.assigned_worker || null,
  staffMembers: Array.isArray(source.job?.assigned_workers_snapshot)
    ? source.job.assigned_workers_snapshot
      .map((item) => ({
        id: Number(item?.id || 0),
        name: String(item?.name || '').trim(),
        worker_share_percent: Math.max(0, Math.min(100, Number(item?.worker_share_percent || 0)))
      }))
      .filter((item) => item.id > 0)
    : [],
  staffIds: Array.isArray(source.job?.assigned_workers_snapshot)
    ? source.job.assigned_workers_snapshot
      .map((item) => Number(item?.id))
      .filter((id) => Number.isFinite(id) && id > 0)
    : []
})
const unassignedWorkerLabels = new Set(['تخصیص نشده', 'نیرو تخصیص نشده', 'بدون نیرو'])
const normalizeWorkerName = (value) => String(value || '').trim()
const isRealWorkerName = (value) => {
  const name = normalizeWorkerName(value)
  return name.length > 0 && !unassignedWorkerLabels.has(name)
}
const uniqueWorkerNames = (items) => (
  Array.isArray(items)
    ? items
      .map((item) => normalizeWorkerName(typeof item === 'string' ? item : item?.name || item?.worker_name))
      .filter((name, index, arr) => isRealWorkerName(name) && arr.indexOf(name) === index)
    : []
)
const assignedWorkersLabel = (job) => {
  if (!job) return 'تخصیص نشده'
  const names = uniqueWorkerNames(job.assigned_workers_names)
  if (names.length) return names.join('، ')
  const snapshotNames = uniqueWorkerNames(job.assigned_workers_snapshot)
  if (snapshotNames.length) return snapshotNames.join('، ')
  return isRealWorkerName(job.assigned_worker_name) ? job.assigned_worker_name : 'تخصیص نشده'
}
const hasCompletedStepOneData = (source = {}) => {
  const isPieceWash = Boolean(source.is_piece_wash)
  const isAnonymous = isAnonymousPlate(source)
  const hasPhone = normalizeDigits(source.driver_phone).length === 11
  if (isPieceWash) return hasPhone
  if (isAnonymous) {
    return hasPhone
  }
  return hasPhone
}
const handleCardAction = async (car) => {
  if (car.statusKey === 'released' || car.statusKey === 'cancelled') return
  if (car.statusKey === 'ready_to_settle') {
    await openReleaseModal(car)
    return
  }
  const source = vehicleStore.vehicles.find((item) => item.id === car.id)
  if (!source) return
  vehicleDraft.value = mapVehicleToDraft(source)
  modalStep.value = (car.statusKey === 'entered' && !hasCompletedStepOneData(source)) ? 1 : 2
  showVehicleModal.value = true
}
const closeReleaseModal = () => {
  showReleaseModal.value = false
  showReleaseServicePicker.value = false
  showChequeDetailsModal.value = false
  closeInvoicePreviewModal()
  releaseCandidate.value = null
  tempReleaseServiceIds.value = []
  releaseCheckoutLoading.value = false
  releaseSubmitting.value = false
  releaseForm.value = {
    serviceLines: [],
    availableProducts: [],
    productLinesByProductId: {},
    productSearch: '',
    tipAmount: 0,
      assignedWorkers: [],
      workerShareAmount: 0,
    customerScore: 0,
    discountPercentPerHalfStar: 0,
    manualDiscountTotal: 0,
    paymentMethod: defaultReleasePaymentMethod.value,
    manualCashAmount: 0,
    manualSecondaryMethod: 'transfer',
    manualSecondaryAmount: 0,
    chequeNumber: '',
    chequeSerialNumber: '',
    chequeSayadiNumber: '',
    chequeBank: '',
    chequeShaba: '',
    chequeAmount: 0,
    creditDueDate: '',
    receiptFooterNote: '',
    bonusPenaltyAdjustments: [],
    bonusPenaltyNote: '',
    newServiceLines: [],
    availableServicesToAdd: [],
      selectedServiceToAdd: 0
  }
}
const revokeInvoicePdfUrl = () => {
  if (invoicePdfUrl.value) URL.revokeObjectURL(invoicePdfUrl.value)
  invoicePdfUrl.value = ''
}
const closeInvoicePreviewModal = () => {
  showInvoicePreviewModal.value = false
  invoiceGenerating.value = false
  invoiceErrorMessage.value = ''
  if (invoiceRenderTimer.value) window.clearTimeout(invoiceRenderTimer.value)
  revokeInvoicePdfUrl()
}
const defaultReleasePaymentMethod = computed(() => {
  const counts = releasePaymentMethods.reduce((acc, method) => {
    acc[method] = 0
    return acc
  }, {})
  ;(Array.isArray(vehicleStore.vehicles) ? vehicleStore.vehicles : []).forEach((item) => {
    const method = String(item?.payment_method || '').trim().toLowerCase()
    if (method in counts) counts[method] += 1
  })
  let selected = 'cash'
  let maxCount = -1
  releasePaymentMethods.forEach((method) => {
    const count = counts[method] || 0
    if (count > maxCount) {
      selected = method
      maxCount = count
    }
  })
  return selected
})
const defaultWorkerSharePercents = (count) => {
  const workerCount = Math.max(0, Number(count || 0))
  if (!workerCount) return []
  const base = Math.floor(100 / workerCount)
  let remainder = 100 - (base * workerCount)
  return Array.from({ length: workerCount }, () => {
    const value = base + (remainder > 0 ? 1 : 0)
    if (remainder > 0) remainder -= 1
    return value
  })
}
const openChequeDetailsModal = () => {
  const preferredChequeAmount = releaseForm.value.paymentMethod === 'manual'
    && releaseForm.value.manualSecondaryMethod === 'cheque'
    && Number(releaseForm.value.manualSecondaryAmount || 0) > 0
    ? Number(releaseForm.value.manualSecondaryAmount || 0)
    : Math.round(Number(releaseSummary.value.finalTotal || 0) / 1000)
  if (Number(releaseForm.value.chequeAmount || 0) <= 0) {
    releaseForm.value.chequeAmount = Math.max(1, preferredChequeAmount)
  }
  showChequeDetailsModal.value = true
}
const closeChequeDetailsModal = () => {
  showChequeDetailsModal.value = false
}
const normalizeReleaseAssignedWorkers = (workers) => {
  const items = Array.isArray(workers)
    ? workers.filter((item) => String(item?.name || '').trim().length > 0)
    : []
  const fallbackPercents = defaultWorkerSharePercents(items.length)
  return items.map((item, index) => ({
    ...item,
    id: Number(item?.id || 0),
    worker_local_key: String(item?.worker_local_key || `worker-${index + 1}`),
    worker_share_percent: Number(item.worker_share_percent ?? fallbackPercents[index] ?? 0),
    isSelected: true
  }))
}
const releaseWorkersScore = (workers) => {
  const items = Array.isArray(workers) ? workers : []
  const activeCount = items.length
  const percentCount = items.filter((item) => Number(item?.worker_share_percent || 0) > 0).length
  const amountCount = items.filter((item) => Number(item?.worker_share_amount || 0) > 0).length
  return (activeCount * 10) + (percentCount * 4) + (amountCount * 4)
}
const pickBestReleaseAssignedWorkers = (...sources) => (
  sources
    .filter((items) => Array.isArray(items) && items.length)
    .sort((first, second) => releaseWorkersScore(second) - releaseWorkersScore(first))[0]
    || []
)
const selectedReleaseServiceIds = computed(() => (
  Array.isArray(releaseForm.value.serviceLines)
    ? releaseForm.value.serviceLines
      .filter((line) => line?.is_selected !== false && Number(line?.service_id || 0) > 0)
      .map((line) => Number(line.service_id))
    : []
))
const visibleReleaseServiceLines = computed(() => (
  Array.isArray(releaseForm.value.serviceLines)
    ? releaseForm.value.serviceLines.filter((line) => line?.is_selected !== false)
    : []
))
const extractReleaseAssignedWorkers = (payload) => {
  const assignedWorkers = Array.isArray(payload?.job?.assigned_workers)
    ? payload.job.assigned_workers
      .map((item, index) => ({
        id: Number(item?.id || 0),
        name: normalizeWorkerName(item?.name || item?.worker_name),
        tip_share_percent: Number(item?.tip_share_percent || 0),
        worker_share_percent: Number(item?.worker_share_percent || 0),
        worker_local_key: String(item?.worker_local_key || `assigned-worker-${index + 1}`)
      }))
      .filter((item) => isRealWorkerName(item.name))
    : []
  if (assignedWorkers.length) return assignedWorkers

  const snapshotWorkers = Array.isArray(payload?.job?.assigned_workers_snapshot)
    ? payload.job.assigned_workers_snapshot
      .map((item, index) => ({
        id: Number(item?.id || 0),
        name: normalizeWorkerName(item?.name || item?.worker_name),
        tip_share_percent: Number(item?.tip_share_percent || 0),
        worker_share_percent: Number(item?.worker_share_percent || 0),
        worker_local_key: String(item?.worker_local_key || `snapshot-worker-${index + 1}`)
      }))
      .filter((item) => isRealWorkerName(item.name))
    : []
  if (snapshotWorkers.length) return snapshotWorkers

  return Array.isArray(payload?.job?.assigned_workers_names)
    ? payload.job.assigned_workers_names
      .filter((item) => isRealWorkerName(item))
      .map((name, index) => ({
        id: 0,
        name: normalizeWorkerName(name),
        tip_share_percent: 0,
        worker_share_percent: 0,
        worker_local_key: `named-worker-${index + 1}`
      }))
    : (() => {
      const fallbackName = normalizeWorkerName(
        payload?.job?.assigned_worker_name
        || payload?.workerName
        || payload?.worker_name
        || ''
      )
      return isRealWorkerName(fallbackName)
        ? [{
          id: 0,
          name: fallbackName,
          tip_share_percent: 0,
          worker_share_percent: 100,
          worker_local_key: 'fallback-worker-1'
        }]
        : []
    })()
}
const openReleaseServicePicker = () => {
  tempReleaseServiceIds.value = [...selectedReleaseServiceIds.value]
  showReleaseServicePicker.value = true
}
const closeReleaseServicePicker = () => {
  showReleaseServicePicker.value = false
}
const toggleTempReleaseService = (rawServiceId) => {
  const serviceId = Number(rawServiceId || 0)
  if (!serviceId) return
  if (tempReleaseServiceIds.value.includes(serviceId)) {
    tempReleaseServiceIds.value = tempReleaseServiceIds.value.filter((item) => Number(item) !== serviceId)
    return
  }
  tempReleaseServiceIds.value = [...tempReleaseServiceIds.value, serviceId]
}
const confirmReleaseServicePicker = () => {
  const selectedIds = new Set(tempReleaseServiceIds.value.map((item) => Number(item)).filter((item) => item > 0))
  const currentLines = Array.isArray(releaseForm.value.serviceLines) ? [...releaseForm.value.serviceLines] : []
  const currentByServiceId = new Map(
    currentLines
      .filter((line) => Number(line?.service_id || 0) > 0)
      .map((line) => [Number(line.service_id), line])
  )

  currentLines.forEach((line) => {
    const serviceId = Number(line?.service_id || 0)
    if (!serviceId || !line?.id) return
    line.is_selected = selectedIds.has(serviceId)
    if (!selectedIds.has(serviceId)) line.is_completed = false
  })

  releaseForm.value.availableServicesToAdd.forEach((service) => {
    const serviceId = Number(service.id || 0)
    if (!serviceId || !selectedIds.has(serviceId) || currentByServiceId.has(serviceId)) return
    currentLines.push({
      id: null,
      service_id: serviceId,
      service_name: service.name,
      quantity: 1,
      line_total: Number(service.base_price || 0),
      is_completed: true,
      is_selected: true
    })
  })

  releaseForm.value.serviceLines = currentLines
    .map((line) => {
      const serviceId = Number(line?.service_id || 0)
      if (!serviceId) return line
      const isSelected = selectedIds.has(serviceId)
      return {
        ...line,
        is_selected: isSelected,
        is_completed: isSelected ? Boolean(line.is_completed ?? true) : false
      }
    })
    .filter((line) => line?.id || line?.is_selected !== false)

  releaseForm.value.newServiceLines = releaseForm.value.serviceLines
    .filter((line) => !line.id && line.is_selected !== false && Number(line.service_id || 0) > 0)
    .map((line) => ({ service_id: Number(line.service_id) }))

  closeReleaseServicePicker()
}
const getSelectedWorkerIndexes = (workers) => (
  Array.isArray(workers)
    ? workers
      .map((worker, index) => ((worker?.isSelected !== false && String(worker?.name || '').trim().length > 0) ? index : -1))
      .filter((index) => index >= 0)
    : []
)
const applyEqualDistributionToSelectedWorkers = (workers) => {
  const selectedIndexes = getSelectedWorkerIndexes(workers)
  if (!selectedIndexes.length) {
    return workers.map((worker) => ({ ...worker, worker_share_percent: 0 }))
  }
  const percents = defaultWorkerSharePercents(selectedIndexes.length)
  return workers.map((worker, index) => {
    const selectedPosition = selectedIndexes.indexOf(index)
    return {
      ...worker,
      worker_share_percent: selectedPosition >= 0 ? percents[selectedPosition] : 0
    }
  })
}
const selectedAssignedWorkers = computed(() => (
  Array.isArray(releaseForm.value.assignedWorkers)
    ? releaseForm.value.assignedWorkers
      .map((worker, index) => ({ ...worker, sourceIndex: index }))
      .filter((worker) => worker.isSelected !== false && String(worker.name || '').trim().length > 0)
    : []
))
const bonusPenaltyWorkers = computed(() => (
  Array.isArray(releaseForm.value.assignedWorkers)
    ? releaseForm.value.assignedWorkers
      .map((worker, index) => ({ ...worker, sourceIndex: index }))
      .filter((worker) => String(worker.name || '').trim().length > 0)
    : []
))
const syncBonusPenaltyAdjustments = () => {
  const workers = bonusPenaltyWorkers.value
  const current = Array.isArray(releaseForm.value.bonusPenaltyAdjustments) ? releaseForm.value.bonusPenaltyAdjustments : []
  const currentMap = new Map(
    current.map((item, index) => [String(item.worker_key || `adjustment-${Number(item.worker_id || 0)}-${index}`), item])
  )
  releaseForm.value.bonusPenaltyAdjustments = workers.map((worker) => {
    const workerKey = String(worker.worker_local_key || `worker-${worker.sourceIndex || 0}`)
    const existing = currentMap.get(workerKey)
    return {
      worker_id: Number(worker.id || 0),
      worker_key: workerKey,
      worker_name: worker.name || '',
      bonus: Number(existing?.bonus || 0),
      penalty: Number(existing?.penalty || 0)
    }
  })
}
const activateAllReleaseWorkers = () => {
  const workers = Array.isArray(releaseForm.value.assignedWorkers) ? [...releaseForm.value.assignedWorkers] : []
  if (!workers.length) return
  releaseForm.value.assignedWorkers = applyEqualDistributionToSelectedWorkers(
    workers.map((worker) => ({ ...worker, isSelected: true }))
  )
}
const toggleReleaseWorkerSelection = (index) => {
  const workers = Array.isArray(releaseForm.value.assignedWorkers) ? [...releaseForm.value.assignedWorkers] : []
  if (index < 0 || index >= workers.length) return
  const selectedIndexes = getSelectedWorkerIndexes(workers)
  const isSelected = workers[index]?.isSelected !== false
  if (isSelected && selectedIndexes.length <= 1) return

  workers[index] = {
    ...workers[index],
    isSelected: !isSelected,
    worker_share_percent: !isSelected ? Number(workers[index]?.worker_share_percent || 0) : 0
  }

  releaseForm.value.assignedWorkers = applyEqualDistributionToSelectedWorkers(workers)
  syncBonusPenaltyAdjustments()
}
const setReleaseWorkerSharePercent = (index, rawValue) => {
  const workers = Array.isArray(releaseForm.value.assignedWorkers) ? [...releaseForm.value.assignedWorkers] : []
  if (index < 0 || index >= workers.length) return
  if (workers[index]?.isSelected === false) return
  const selectedIndexes = getSelectedWorkerIndexes(workers)
  if (!selectedIndexes.includes(index)) return
  const parsed = Math.max(0, Math.min(100, Math.floor(Number(rawValue || 0))))
  if (selectedIndexes.length === 1) {
    workers[selectedIndexes[0]] = { ...workers[selectedIndexes[0]], worker_share_percent: 100 }
    releaseForm.value.assignedWorkers = workers
    return
  }

  const otherIndexes = selectedIndexes.filter((idx) => idx !== index)
  const remaining = Math.max(0, 100 - parsed)
  const base = otherIndexes.length ? Math.floor(remaining / otherIndexes.length) : 0
  let remainder = otherIndexes.length ? remaining - (base * otherIndexes.length) : 0

  workers[index] = { ...workers[index], worker_share_percent: parsed }
  otherIndexes.forEach((workerIndex) => {
    const nextValue = base + (remainder > 0 ? 1 : 0)
    if (remainder > 0) remainder -= 1
    workers[workerIndex] = { ...workers[workerIndex], worker_share_percent: nextValue }
  })
  releaseForm.value.assignedWorkers = workers
}
const getReleaseWorkerShareAmountInput = (index) => {
  const selectedIndex = getSelectedWorkerIndexes(releaseForm.value.assignedWorkers).indexOf(index)
  const worker = selectedIndex >= 0 ? releaseSummary.value.workerShares?.[selectedIndex] : null
  if (!worker) return 0
  return Math.round(Number(worker.baseAmount || 0) / 1000)
}
const setReleaseWorkerShareAmount = (index, rawValue) => {
  const workers = Array.isArray(releaseForm.value.assignedWorkers) ? [...releaseForm.value.assignedWorkers] : []
  if (index < 0 || index >= workers.length) return
  if (workers[index]?.isSelected === false) return
  const totalAmount = Math.max(0, Number(releaseSummary.value.workerShareBase || 0))
  const selectedIndexes = getSelectedWorkerIndexes(workers)
  if (!selectedIndexes.includes(index)) return
  if (selectedIndexes.length === 1 || totalAmount <= 0) {
    workers[selectedIndexes[0]] = { ...workers[selectedIndexes[0]], worker_share_percent: 100 }
    releaseForm.value.assignedWorkers = workers
    return
  }

  const inputAmount = Math.round(Math.max(0, Number(rawValue || 0)) * 1000)
  const assignedAmount = Math.max(0, Math.min(totalAmount, inputAmount))
  const otherIndexes = selectedIndexes.filter((idx) => idx !== index)
  const remaining = Math.max(0, totalAmount - assignedAmount)
  const base = otherIndexes.length ? Math.floor(remaining / otherIndexes.length) : 0
  let remainder = otherIndexes.length ? remaining - (base * otherIndexes.length) : 0

  const distributedAmounts = workers.map(() => 0)
  distributedAmounts[index] = assignedAmount
  otherIndexes.forEach((workerIndex) => {
    const nextValue = base + (remainder > 0 ? 1 : 0)
    if (remainder > 0) remainder -= 1
    distributedAmounts[workerIndex] = nextValue
  })

  let percentSum = 0
  selectedIndexes.forEach((workerIndex, selectedPosition) => {
    const percent = selectedPosition === selectedIndexes.length - 1
      ? Math.max(0, Number((100 - percentSum).toFixed(2)))
      : Number((((distributedAmounts[workerIndex] || 0) / totalAmount) * 100).toFixed(2))
    if (selectedPosition !== selectedIndexes.length - 1) percentSum = Number((percentSum + percent).toFixed(2))
    workers[workerIndex] = { ...workers[workerIndex], worker_share_percent: percent }
  })
  releaseForm.value.assignedWorkers = workers
}
const openReleaseModal = async (car) => {
  const sourceVehicle = vehicleStore.vehicles.find((item) => Number(item.id) === Number(car?.id || 0)) || null
  releaseCandidate.value = car
  showReleaseModal.value = true
  releaseCheckoutLoading.value = true
  try {
    const [releaseResponse, settingsResponse] = await Promise.all([
      api.get(`/vehicles/${car.id}/release/`),
      api.get('/services/general-settings/').catch(() => ({ data: { discount_percent_per_half_star: 0 } }))
    ])
    const data = releaseResponse.data
    const discountPercentPerHalfStar = Math.max(
      0,
      Number(
        settingsResponse?.data?.discount_percent_per_half_star
        ?? data?.job?.discount_percent_per_half_star
        ?? 0
      )
    )
    const serviceLines = Array.isArray(data?.job?.service_lines)
      ? data.job.service_lines.map((line) => ({
        id: line.id,
        service_id: Number(line.service_id || line.service || 0),
        service_name: line.service_name,
        quantity: Number(line.quantity || 0),
        line_total: Number(line.line_total || 0),
        is_completed: true,
        is_selected: true
      }))
      : []
    const resolvedAssignedWorkers = extractReleaseAssignedWorkers(data)
    const sourceSnapshotWorkers = Array.isArray(sourceVehicle?.job?.assigned_workers_snapshot)
      ? sourceVehicle.job.assigned_workers_snapshot
        .map((item, index) => ({
          id: Number(item?.id || 0),
          name: normalizeWorkerName(item?.name || item?.worker_name),
          tip_share_percent: Number(item?.tip_share_percent || 0),
          worker_share_percent: Number(item?.worker_share_percent || 0),
          worker_share_amount: Number(item?.worker_share_amount || 0),
          worker_local_key: String(item?.worker_local_key || `source-worker-${index + 1}`)
        }))
        .filter((item) => isRealWorkerName(item.name))
      : []
    const cardAssignedWorkers = extractReleaseAssignedWorkers({ workerName: car?.workerName || '' })
    const fallbackAssignedWorkers = sourceVehicle
      ? extractReleaseAssignedWorkers(sourceVehicle)
      : extractReleaseAssignedWorkers({ workerName: car?.workerName || '' })
    const preferredAssignedWorkers = pickBestReleaseAssignedWorkers(
      resolvedAssignedWorkers,
      sourceSnapshotWorkers,
      fallbackAssignedWorkers,
      cardAssignedWorkers
    )
    const availableProducts = Array.isArray(data?.job?.available_products)
      ? data.job.available_products.map((item) => ({
        id: item.id,
        name: item.name,
        sku: item.sku,
        sale_price: Number(item.sale_price || 0),
        available_quantity: Number(item.available_quantity || 0),
        selected_quantity: Number(item.selected_quantity || 0)
      }))
      : []
    const productLinesByProductId = {}
    availableProducts.forEach((item) => {
      if (item.selected_quantity > 0) productLinesByProductId[item.id] = item.selected_quantity
    })
    releaseForm.value = {
      serviceLines,
      availableProducts,
      productLinesByProductId,
      productSearch: '',
      tipAmount: Math.max(0, Number(data?.job?.tip_amount || 0) / 1000),
      assignedWorkers: normalizeReleaseAssignedWorkers(preferredAssignedWorkers),
      workerShareAmount: Number(data?.job?.worker_share_amount || 0),
      customerScore: Math.max(0, Number(data?.vehicle?.customer_score || releaseCandidate.value?.customerScore || 0)),
      discountPercentPerHalfStar,
      manualDiscountTotal: Math.max(0, Number(data?.job?.manual_discount_total || 0)),
      paymentMethod: defaultReleasePaymentMethod.value,
      manualCashAmount: 0,
      manualSecondaryMethod: 'transfer',
      manualSecondaryAmount: 0,
      chequeNumber: '',
      chequeSerialNumber: '',
      chequeSayadiNumber: '',
      chequeBank: '',
      chequeShaba: '',
      chequeAmount: 0,
      creditDueDate: '',
      receiptFooterNote: settingsResponse?.data?.receipt_footer_note || '',
      receiptPrinterPaperWidth: settingsResponse?.data?.receipt_printer_paper_width || '80mm',
      receiptPrintCopies: Math.max(1, Number(settingsResponse?.data?.receipt_print_copies || 1)),
      bonusPenaltyAdjustments: [],
      bonusPenaltyNote: '',
      newServiceLines: [],
      availableServicesToAdd: Array.isArray(data?.job?.available_services) ? data.job.available_services.map((item) => ({
        id: Number(item.id),
        name: item.name,
        base_price: Number(item.base_price || 0)
      })) : [],
      selectedServiceToAdd: 0
    }
    syncInvoiceLayoutFromPrinterSettings(releaseForm.value.receiptPrinterPaperWidth)
    tempReleaseServiceIds.value = [...selectedReleaseServiceIds.value]
    syncBonusPenaltyAdjustments()
  } catch (error) {
    console.error('openReleaseModal error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'بارگذاری اطلاعات ترخیص ناموفق بود.'), { title: 'خطا در بارگذاری ترخیص' })
    closeReleaseModal()
  } finally {
    releaseCheckoutLoading.value = false
  }
}
const invoiceServiceLines = computed(() => (
  Array.isArray(releaseForm.value.serviceLines)
    ? releaseForm.value.serviceLines.filter((line) => Boolean(line?.is_completed))
    : []
))
const sanitizeMillimeter = (value, fallback, min, max) => {
  const numeric = Number(value || 0)
  if (!Number.isFinite(numeric)) return fallback
  return Math.min(max, Math.max(min, numeric))
}
const invoicePresetOptions = [
  { key: 'a4', label: 'A4' },
  { key: 'a5', label: 'A5' },
  { key: 'thermal', label: 'فیش پرینتر' }
]
const invoiceIsThermal = computed(() => invoiceLayout.value.preset === 'thermal')
const invoiceThermalWidthMm = computed(() => sanitizeMillimeter(invoiceLayout.value.thermalWidthMm, 80, 48, 120))
const invoiceThermalHeightMm = computed(() => sanitizeMillimeter(invoiceLayout.value.thermalHeightMm, 220, 80, 600))
const invoicePageMetrics = computed(() => {
  if (invoiceLayout.value.preset === 'a5') {
    return { width: 148, minHeight: 210, padding: 4.5, gap: 6, margin: [5, 5, 5, 5], format: 'a5' }
  }
  if (invoiceLayout.value.preset === 'thermal') {
    return {
      width: invoiceThermalWidthMm.value,
      minHeight: invoiceThermalHeightMm.value,
      padding: 3.2,
      gap: 4,
      margin: [3, 3, 3, 3],
      format: [invoiceThermalWidthMm.value, invoiceThermalHeightMm.value]
    }
  }
  return { width: 210, minHeight: 297, padding: 5, gap: 7, margin: [6, 6, 6, 6], format: 'a4' }
})
const invoiceSheetStyle = computed(() => ({
  width: `${invoicePageMetrics.value.width}mm`,
  maxWidth: `${invoicePageMetrics.value.width}mm`,
  minHeight: `${invoicePageMetrics.value.minHeight}mm`,
  padding: `${invoicePageMetrics.value.padding}mm`,
  gap: `${invoicePageMetrics.value.gap}px`
}))
const invoiceTemplateStyle = computed(() => ({
  width: `${invoicePageMetrics.value.width}mm`,
  maxWidth: `${invoicePageMetrics.value.width}mm`
}))
const invoiceStageStyle = computed(() => ({
  width: `${invoicePageMetrics.value.width}mm`
}))
const invoiceSheetClass = computed(() => ({
  'invoice-sheet-a5': invoiceLayout.value.preset === 'a5',
  'invoice-sheet-thermal': invoiceLayout.value.preset === 'thermal'
}))
const invoiceFileLabel = computed(() => (
  invoiceLayout.value.preset === 'thermal'
    ? `receipt-${releaseCandidate.value?.id || 'carwash'}`
    : `invoice-${releaseCandidate.value?.id || 'carwash'}`
))
const invoicePreviewUrl = computed(() => (
  invoicePdfUrl.value
    ? `${invoicePdfUrl.value}#view=FitH&zoom=page-width`
    : ''
))
const invoiceProductLines = computed(() => (
  Array.isArray(releaseForm.value.availableProducts)
    ? releaseForm.value.availableProducts
      .map((product) => {
        const quantity = getReleaseProductQty(product.id)
        const unitPrice = Number(product.sale_price || 0)
        return quantity > 0
          ? {
            id: product.id,
            name: product.name,
            quantity,
            unitPrice,
            total: quantity * unitPrice
          }
          : null
      })
      .filter(Boolean)
    : []
))
const invoiceNumber = computed(() => `CW-${Number(releaseCandidate.value?.id || 0).toLocaleString('fa-IR')}`)
const invoiceCustomerName = computed(() => (
  String(releaseCandidate.value?.driverName || releaseCandidate.value?.driver_name || '').trim() || 'مشتری حضوری'
))
const invoiceCustomerPhone = computed(() => (
  String(releaseCandidate.value?.driverPhone || releaseCandidate.value?.driver_phone || '').trim() || '-'
))
const invoiceVehicleTitle = computed(() => {
  const model = String(releaseCandidate.value?.model || releaseCandidate.value?.car_model || '').trim()
  const color = String(releaseCandidate.value?.colorName || releaseCandidate.value?.car_color || '').trim()
  return `${model} ${color}`.trim() || 'قطعه‌شویی'
})
const invoicePlateLabel = computed(() => (
  String(releaseCandidate.value?.plateDisplay || releaseCandidate.value?.plate_number || '').trim() || 'قطعه‌شویی'
))
const invoiceAdmissionLabel = computed(() => (
  releaseCandidate.value?.isPieceWash || releaseCandidate.value?.is_piece_wash ? 'قطعه‌شویی' : 'خودرو'
))
const invoiceCheckInLabel = computed(() => {
  const rawDate = releaseCandidate.value?.checkInAt || releaseCandidate.value?.check_in_at || releaseCandidate.value?.created_at
  if (!rawDate) return '-'
  return new Intl.DateTimeFormat('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(rawDate))
})
const invoicePaymentStatusLabel = computed(() => (
  releaseSummary.value.finalTotal > 0 ? paymentStatusLabel(releaseCandidate.value?.payment_status) : 'تسویه شده'
))
const invoiceSubtotal = computed(() => Number((releaseSummary.value.servicesTotal + releaseSummary.value.productsTotal).toFixed(2)))
const invoiceDueDateLabel = computed(() => (
  releaseForm.value.creditDueDate && ['credit', 'cheque', 'manual'].includes(releaseForm.value.paymentMethod)
    ? releaseForm.value.creditDueDate
    : ''
))
const invoiceChequeLabel = computed(() => (
  chequeDetailsSummary.value !== 'جزئیات ثبت نشده' ? chequeDetailsSummary.value : ''
))
const invoiceCustomerNote = computed(() => (
  String(releaseCandidate.value?.note || releaseCandidate.value?.notes || '').trim()
))
const invoiceIssuedAt = computed(() => new Intl.DateTimeFormat('fa-IR', {
  dateStyle: 'medium',
  timeStyle: 'short'
}).format(new Date()))
const releasePaymentBreakdown = computed(() => {
  if (releaseForm.value.paymentMethod !== 'manual') return []
  const cashAmount = Math.max(0, Number(releaseForm.value.manualCashAmount || 0) * 1000)
  const secondaryAmount = Math.max(0, Number(releaseForm.value.manualSecondaryAmount || 0) * 1000)
  const secondaryMethod = String(releaseForm.value.manualSecondaryMethod || 'transfer').trim()
  return [
    cashAmount > 0 ? { method: 'cash', amount: cashAmount } : null,
    secondaryAmount > 0 ? { method: secondaryMethod, amount: secondaryAmount } : null
  ].filter(Boolean)
})
const releasePaymentBreakdownLabel = computed(() => (
  releasePaymentBreakdown.value
    .map((item) => `${paymentMethodLabel(item.method)}: ${formatMoney(item.amount)}`)
    .join(' | ')
))
const getReleaseProductQty = (productId) => Number(releaseForm.value.productLinesByProductId[productId] || 0)
const increaseReleaseProduct = (productId) => {
  const product = releaseForm.value.availableProducts.find((item) => item.id === productId)
  if (!product) return
  const current = getReleaseProductQty(productId)
  if (current >= Number(product.available_quantity || 0)) return
  releaseForm.value.productLinesByProductId[productId] = current + 1
}
const decreaseReleaseProduct = (productId) => {
  const current = getReleaseProductQty(productId)
  if (current <= 0) return
  const next = current - 1
  if (next === 0) {
    delete releaseForm.value.productLinesByProductId[productId]
    return
  }
  releaseForm.value.productLinesByProductId[productId] = next
}
const setReleaseProductQty = (productId, rawValue) => {
  const product = releaseForm.value.availableProducts.find((item) => item.id === productId)
  if (!product) return
  const maxQty = Math.max(0, Number(product.available_quantity || 0))
  const parsed = Math.floor(Number(rawValue || 0))
  const nextQty = Number.isFinite(parsed) ? Math.max(0, Math.min(maxQty, parsed)) : 0
  if (nextQty <= 0) {
    delete releaseForm.value.productLinesByProductId[productId]
    return
  }
  releaseForm.value.productLinesByProductId[productId] = nextQty
}
const syncInvoiceLayoutFromPrinterSettings = (paperWidth) => {
  const value = String(paperWidth || '').trim().toLowerCase()
  if (value === 'a4') {
    invoiceLayout.value.preset = 'a4'
    return
  }
  if (value === 'a5') {
    invoiceLayout.value.preset = 'a5'
    return
  }
  invoiceLayout.value.preset = 'thermal'
  if (value === '58mm') {
    invoiceLayout.value.thermalWidthMm = 58
  } else if (value === '80mm') {
    invoiceLayout.value.thermalWidthMm = 80
  }
}
const filteredReleaseProducts = computed(() => {
  const items = releaseForm.value.availableProducts || []
  const query = (releaseForm.value.productSearch || '').trim()
  if (!query) return items
  return items.filter((item) => `${item.name || ''} ${item.sku || ''}`.includes(query))
})
const hasReleaseProducts = computed(() => (
  Array.isArray(releaseForm.value.availableProducts) && releaseForm.value.availableProducts.length > 0
))
const addServiceFromSystem = (rawServiceId = null) => {
  const serviceId = Number(rawServiceId || releaseForm.value.selectedServiceToAdd || 0)
  if (!serviceId) return
  const service = releaseForm.value.availableServicesToAdd.find((item) => item.id === serviceId)
  if (!service) return
  const duplicate = releaseForm.value.serviceLines.some((line) => Number(line.service_id || 0) === service.id)
  if (duplicate) return
  releaseForm.value.serviceLines.push({
    id: null,
    service_id: service.id,
    service_name: service.name,
    quantity: 1,
    line_total: service.base_price,
    is_completed: true
  })
  releaseForm.value.newServiceLines.push({
    service_id: service.id
  })
  releaseForm.value.selectedServiceToAdd = 0
}
const releaseSummary = computed(() => {
  const servicesTotal = releaseForm.value.serviceLines.reduce((sum, line) => (
    line.is_completed ? sum + Number(line.line_total || 0) : sum
  ), 0)
  const productsTotal = releaseForm.value.availableProducts.reduce((sum, product) => {
    const qty = getReleaseProductQty(product.id)
    return sum + (qty * Number(product.sale_price || 0))
  }, 0)
  const tipAmount = Math.max(0, Number(releaseForm.value.tipAmount || 0) * 1000)
  const customerScore = Math.max(0, Math.min(5, Number(releaseForm.value.customerScore || 0)))
  const discountPercentPerHalfStar = Math.max(0, Number(releaseForm.value.discountPercentPerHalfStar || 0))
  const customerDiscountPercent = Math.max(0, Math.min(100, Number((discountPercentPerHalfStar * customerScore * 2).toFixed(2))))
  const discountBase = Math.max(0, servicesTotal + productsTotal)
  const customerDiscountAmount = Number((discountBase * customerDiscountPercent / 100).toFixed(2))
  const manualDiscountAmount = Math.max(0, Number(releaseForm.value.manualDiscountTotal || 0))
  const discountAmount = Math.min(discountBase, Number((customerDiscountAmount + manualDiscountAmount).toFixed(2)))
  const shareBaseTotal = Math.max(0, servicesTotal)
  const workerShareBase = Math.min(shareBaseTotal, Number(releaseForm.value.workerShareAmount || 0))
  const finalTotalWithProducts = Math.max(0, servicesTotal + productsTotal - discountAmount + tipAmount)
  const assignedWorkers = Array.isArray(releaseForm.value.assignedWorkers)
    ? releaseForm.value.assignedWorkers.filter((item) => item?.isSelected !== false && String(item?.name || '').trim().length > 0)
    : []
  const workerCount = assignedWorkers.length
  const distributionPercents = workerCount
    ? (() => {
      const raw = assignedWorkers.map((worker) => Math.max(0, Math.min(100, Number(worker?.worker_share_percent ?? 0))))
      const total = raw.reduce((sum, value) => sum + value, 0)
      if (total <= 0) return defaultWorkerSharePercents(workerCount)
      let normalizedSum = 0
      return raw.map((value, index) => {
        if (index === workerCount - 1) return Math.max(0, Number((100 - normalizedSum).toFixed(2)))
        const normalized = Number(((value * 100) / total).toFixed(2))
        normalizedSum = Number((normalizedSum + normalized).toFixed(2))
        return normalized
      })
    })()
    : []
  const baseAmountsByWorker = []
  if (workerCount > 0) {
    let distributed = 0
    for (let i = 0; i < workerCount; i += 1) {
      const amount = i === workerCount - 1
        ? Math.max(0, Number((workerShareBase - distributed).toFixed(2)))
        : Number(((workerShareBase * distributionPercents[i]) / 100).toFixed(2))
      baseAmountsByWorker.push(amount)
      distributed = Number((distributed + amount).toFixed(2))
    }
  }
  const percentByWorker = assignedWorkers.map((worker) => {
    const value = Number(worker?.tip_share_percent || 0)
    return Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0))
  })
  const totalPercent = percentByWorker.reduce((sum, value) => sum + value, 0)
  const tipAmountsByWorker = assignedWorkers.map(() => 0)
  let allocatedTipTotal = 0
  if (tipAmount > 0 && workerCount > 0 && totalPercent > 0) {
    let distributed = 0
    for (let i = 0; i < workerCount; i += 1) {
      const divisor = totalPercent > 100 ? totalPercent : 100
      const raw = totalPercent > 100
        ? (tipAmount * percentByWorker[i]) / divisor
        : (tipAmount * percentByWorker[i]) / 100
      const amount = i === workerCount - 1
        ? Math.max(0, Number((tipAmount - distributed).toFixed(2)))
        : Number(raw.toFixed(2))
      tipAmountsByWorker[i] = amount
      distributed = Number((distributed + amount).toFixed(2))
    }
    allocatedTipTotal = Math.min(tipAmount, Number(distributed.toFixed(2)))
  }

  const workerShares = []
  if (workerCount > 0) {
    for (let i = 0; i < workerCount; i += 1) {
      workerShares.push({
        name: assignedWorkers[i]?.name || 'نیرو',
        percent: Number(distributionPercents[i] || 0),
        baseAmount: Number(baseAmountsByWorker[i] || 0),
        tipAmount: Number(tipAmountsByWorker[i] || 0),
        amount: Number((Number(baseAmountsByWorker[i] || 0) + Number(tipAmountsByWorker[i] || 0)).toFixed(2))
      })
    }
  } else if (workerShareBase > 0) {
    workerShares.push({ name: 'نیرو', percent: 100, baseAmount: workerShareBase, tipAmount: 0, amount: workerShareBase })
  }
  const carwashShare = Math.max(
    0,
    Number((shareBaseTotal - workerShareBase + (tipAmount - allocatedTipTotal) - discountAmount).toFixed(2))
  )
  return {
    servicesTotal,
    productsTotal,
    customerScore,
    customerDiscountPercent,
    customerDiscountAmount,
    manualDiscountAmount,
    discountAmount,
    tipAmount,
    shareBaseTotal,
    workerShareBase,
    finalTotal: finalTotalWithProducts,
    workerShare: Number((workerShareBase + allocatedTipTotal).toFixed(2)),
    workerShares,
    carwashShare
  }
})
const hasReleaseBonusOrPenalty = computed(() => (
  Array.isArray(releaseForm.value.bonusPenaltyAdjustments)
    && releaseForm.value.bonusPenaltyAdjustments.some((item) => Number(item?.bonus || 0) > 0 || Number(item?.penalty || 0) > 0)
))
watch(bonusPenaltyWorkers, syncBonusPenaltyAdjustments, { deep: true })
const chequeDetailsSummary = computed(() => {
  if (releaseForm.value.paymentMethod !== 'cheque' && !(releaseForm.value.paymentMethod === 'manual' && releaseForm.value.manualSecondaryMethod === 'cheque')) return 'جزئیات ثبت نشده'
  const parts = []
  if (releaseForm.value.chequeSerialNumber) parts.push(`سریال ${releaseForm.value.chequeSerialNumber}`)
  if (releaseForm.value.chequeBank) parts.push(releaseForm.value.chequeBank)
  if (releaseForm.value.creditDueDate) parts.push(`وصول ${releaseForm.value.creditDueDate}`)
  if (Number(releaseForm.value.chequeAmount || 0) > 0) parts.push(`${Number(releaseForm.value.chequeAmount || 0).toLocaleString('fa-IR')} هزار`)
  return parts.length ? parts.join(' | ') : 'جزئیات ثبت نشده'
})
watch(() => releaseForm.value.paymentMethod, (value) => {
  if (value !== 'manual') return
  const finalTotal = Math.max(0, Number(releaseSummary.value.finalTotal || 0))
  if (Number(releaseForm.value.manualCashAmount || 0) <= 0 && Number(releaseForm.value.manualSecondaryAmount || 0) <= 0) {
    releaseForm.value.manualCashAmount = Math.round(finalTotal / 1000)
    releaseForm.value.manualSecondaryAmount = 0
  }
})
const buildInvoicePdf = async () => {
  if (!invoiceTemplateRef.value) return
  invoiceGenerating.value = true
  invoiceErrorMessage.value = ''
  revokeInvoicePdfUrl()
  try {
    await nextTick()
    const html2pdfModule = await import('html2pdf.js')
    const html2pdf = html2pdfModule.default || html2pdfModule
    const worker = html2pdf()
      .set({
        margin: invoicePageMetrics.value.margin,
        filename: `${invoiceFileLabel.value}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: invoiceIsThermal.value ? 2.2 : 2, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF: { unit: 'mm', format: invoicePageMetrics.value.format, orientation: 'portrait' },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      })
      .from(invoiceTemplateRef.value)
      .toPdf()
    const pdf = await worker.get('pdf')
    const blob = pdf.output('blob')
    invoicePdfUrl.value = URL.createObjectURL(blob)
  } catch (error) {
    console.error('buildInvoicePdf error:', error)
    invoiceErrorMessage.value = 'ساخت فایل فاکتور ناموفق بود.'
  } finally {
    invoiceGenerating.value = false
  }
}
const openInvoicePreviewModal = async () => {
  showInvoicePreviewModal.value = true
  await buildInvoicePdf()
}
const refreshInvoicePreview = async () => {
  await buildInvoicePdf()
}
const downloadInvoicePdf = () => {
  if (!invoicePdfUrl.value) return
  const anchor = document.createElement('a')
  anchor.href = invoicePdfUrl.value
  anchor.download = `${invoiceFileLabel.value}.pdf`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}
const printInvoicePdf = () => {
  const frame = invoicePreviewFrameRef.value
  if (frame?.contentWindow) {
    frame.contentWindow.focus()
    frame.contentWindow.print()
    return
  }
  if (!invoicePdfUrl.value) return
  const popup = window.open(invoicePdfUrl.value, '_blank', 'noopener,noreferrer')
  if (popup) {
    window.setTimeout(() => {
      popup.focus()
      popup.print()
    }, 400)
  }
}
const confirmReleaseVehicle = async () => {
  if (!releaseCandidate.value?.id) return
  if (releaseForm.value.assignedWorkers.length && !selectedAssignedWorkers.value.length) {
    notifyWarning('حداقل یک نیرو را برای این تسویه انتخاب کنید.', { title: 'اطلاعات ناقص تسویه' })
    return
  }
  const usesChequeDetails = releaseForm.value.paymentMethod === 'cheque'
    || (releaseForm.value.paymentMethod === 'manual' && releaseForm.value.manualSecondaryMethod === 'cheque' && Number(releaseForm.value.manualSecondaryAmount || 0) > 0)
  if (usesChequeDetails) {
    if (!releaseForm.value.creditDueDate || !releaseForm.value.chequeSerialNumber || !releaseForm.value.chequeSayadiNumber || !releaseForm.value.chequeBank || !releaseForm.value.chequeShaba || Number(releaseForm.value.chequeAmount || 0) <= 0) {
      notifyWarning('همه جزئیات چک را کامل کنید.', { title: 'اطلاعات ناقص چک' })
      showChequeDetailsModal.value = true
      return
    }
  }
  if (releaseForm.value.paymentMethod === 'manual') {
    const breakdownTotal = releasePaymentBreakdown.value.reduce((sum, item) => sum + Number(item.amount || 0), 0)
    const finalTotal = Math.max(0, Number(releaseSummary.value.finalTotal || 0))
    if (!releasePaymentBreakdown.value.length) {
      notifyWarning('حداقل یک بخش پرداخت برای حالت اسنادی / ترکیبی وارد کنید.', { title: 'اطلاعات پرداخت' })
      return
    }
    if (Math.abs(breakdownTotal - finalTotal) > 1) {
      notifyWarning('جمع بخش‌های پرداخت باید دقیقا با مبلغ نهایی برابر باشد.', { title: 'اطلاعات پرداخت' })
      return
    }
  }
  if (hasReleaseBonusOrPenalty.value && !String(releaseForm.value.bonusPenaltyNote || '').trim()) {
    notifyWarning('توضیح پاداش یا جریمه الزامی است.', { title: 'اطلاعات تعدیل' })
    return
  }
  try {
    releaseSubmitting.value = true
    const service_lines = releaseForm.value.serviceLines.map((line) => ({
      id: line.id,
      is_completed: Boolean(line.is_completed)
    })).filter((line) => line.id)
    const product_lines = releaseForm.value.availableProducts
      .map((product) => ({
        product_id: product.id,
        quantity: getReleaseProductQty(product.id)
      }))
    const { data } = await api.patch(`/vehicles/${releaseCandidate.value.id}/release/`, {
      service_lines,
      new_service_lines: releaseForm.value.newServiceLines
        .filter((line) => Number(line.service_id || 0) > 0)
        .map((line) => ({
          service_id: Number(line.service_id),
          is_completed: true
        })),
      product_lines,
      worker_share_distribution: (releaseForm.value.assignedWorkers || []).map((worker) => ({
        id: Number(worker.id || 0),
        worker_share_percent: Math.max(0, Math.min(100, Number(worker.worker_share_percent ?? 0)))
      })).filter((worker) => worker.id > 0),
      tip_amount: Math.max(0, Number(releaseForm.value.tipAmount || 0) * 1000),
      payment_method: releaseForm.value.paymentMethod,
      payment_breakdown: releasePaymentBreakdown.value.map((item) => ({
        method: item.method,
        amount: Number(item.amount || 0)
      })),
      cheque_number: usesChequeDetails ? (releaseForm.value.chequeSerialNumber || releaseForm.value.chequeNumber) : undefined,
      cheque_serial_number: usesChequeDetails ? releaseForm.value.chequeSerialNumber : undefined,
      cheque_sayadi_number: usesChequeDetails ? releaseForm.value.chequeSayadiNumber : undefined,
      cheque_bank: usesChequeDetails ? releaseForm.value.chequeBank : undefined,
      cheque_shaba: usesChequeDetails ? releaseForm.value.chequeShaba : undefined,
      cheque_amount: usesChequeDetails ? Number(releaseForm.value.chequeAmount || 0) * 1000 : undefined,
      credit_due_date: (['credit', 'cheque'].includes(releaseForm.value.paymentMethod) || usesChequeDetails) ? parseJalaliToIso(releaseForm.value.creditDueDate) || undefined : undefined,
      bonus_penalty_adjustments: (releaseForm.value.bonusPenaltyAdjustments || [])
        .map((item) => ({
          worker_id: Number(item.worker_id || 0),
          bonus: Math.max(0, Number(item.bonus || 0) * 1000),
          penalty: Math.max(0, Number(item.penalty || 0) * 1000)
        }))
        .filter((item) => item.worker_id > 0 && (item.bonus > 0 || item.penalty > 0)),
      bonus_penalty_note: String(releaseForm.value.bonusPenaltyNote || '').trim() || undefined
    })
    const idx = vehicleStore.vehicles.findIndex((item) => item.id === releaseCandidate.value.id)
    if (idx >= 0) vehicleStore.vehicles[idx] = data
    closeReleaseModal()
  } catch (error) {
    console.error('confirmReleaseVehicle error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ترخیص خودرو ناموفق بود.'), { title: 'خطا در ترخیص خودرو' })
  } finally {
    releaseSubmitting.value = false
  }
}
const handleStepOneContinue = async (payload) => {
  try {
    const plateStatus = await fetchPlateBlockedStatus(payload)
    if (plateStatus.is_blocked) {
      vehicleDraft.value = { ...payload, is_plate_blocked: true }
      modalStep.value = 2
      return
    }
    const savedVehicle = await saveVehicle({ vehicle: payload }, 'entered')
    vehicleDraft.value = {
      ...mapVehicleToDraft(savedVehicle),
      detectedPlate: payload.detectedPlate,
      detectedPlateLeft: payload.detectedPlateLeft,
      detectedPlateLetter: payload.detectedPlateLetter,
      detectedPlateMid: payload.detectedPlateMid,
      detectedPlateRight: payload.detectedPlateRight,
      detectedPlateType: payload.detectedPlateType,
      tariffType: payload.tariffType
    }
    modalStep.value = 2
  } catch (error) {
    console.error('continue step one error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ذخیره اطلاعات مرحله اول ناموفق بود.'), { title: 'خطا در ثبت خودرو' })
  }
}
const buildCreateOrUpdatePayload = (payload, status) => {
  const plateRaw = (payload?.vehicle?.plate || '').trim()
  const plateType = String(payload?.vehicle?.plateType || payload?.vehicle?.plate_type || 'car').trim() || 'car'
  const resolvedParts = resolvePlateParts({
    raw: plateRaw,
    plate_left: payload?.vehicle?.plateLeft || payload?.vehicle?.plate_left || '',
    plate_letter: payload?.vehicle?.plateLetter || payload?.vehicle?.plate_letter || '',
    plate_mid: payload?.vehicle?.plateMid || payload?.vehicle?.plate_mid || '',
    plate_right: payload?.vehicle?.plateRight || payload?.vehicle?.plate_right || '',
    plate_type: plateType,
  })
  const left = String(resolvedParts.left || '').trim()
  const letter = String(resolvedParts.letter || '').trim()
  const mid = String(resolvedParts.mid || '').trim()
  const right = String(resolvedParts.right || '').trim()
  const rebuiltPlate = buildPlateNumber({ left, letter, mid, right, plateType }) || plateRaw
  const isAnonymous = Boolean(payload?.vehicle?.isAnonymous)
  const isPieceWash = Boolean(payload?.vehicle?.isPieceWash)

  return {
    plate_number: isPieceWash ? '' : (isAnonymous ? '' : rebuiltPlate),
    plate_left: isPieceWash || isAnonymous || plateType === 'motorcycle' ? '' : left,
    plate_letter: isPieceWash || isAnonymous ? '' : letter,
    plate_mid: isPieceWash || isAnonymous ? '' : mid,
    plate_right: isPieceWash || isAnonymous || plateType === 'motorcycle' ? '' : right,
    plate_type: plateType,
    car_model: isPieceWash ? 'قطعه‌شویی' : (isAnonymous ? '1111' : String(payload?.vehicle?.model || '').trim()),
    car_color: isPieceWash ? '-' : (isAnonymous ? '1111' : String(payload?.vehicle?.color || '').trim()),
    driver_name: (payload?.vehicle?.driver || '').trim(),
    driver_phone: (payload?.vehicle?.mobile || '').trim(),
    notes: isPieceWash ? '' : (payload?.vehicle?.note || '').trim(),
    is_piece_wash: isPieceWash,
    piece_details: (payload?.vehicle?.pieceDetails || '').trim(),
    status,
    worker_id: payload?.staff?.id || null,
    worker_name: payload?.staff?.name || '',
    staff_members: Array.isArray(payload?.staffMembers)
      ? payload.staffMembers.map((item) => ({
        id: item?.id,
        name: item?.name || '',
        worker_share_percent: Math.max(0, Math.min(100, Number(item?.worker_share_percent || 0)))
      }))
      : [],
    services: payload?.services || [],
    manual_discount_total: Number(payload?.manual_discount_total || 0),
    share: payload?.share || {},
    blocked_plate_payment_confirmed: Boolean(payload?.blocked_plate_payment_confirmed)
  }
}

const fetchPlateBlockedStatus = async (payload) => {
  if (payload?.isAnonymous || payload?.vehicle?.isAnonymous) return { is_blocked: false }
  const plateType = String(payload?.plateType || payload?.vehicle?.plateType || payload?.vehicle?.plate_type || 'car').trim() || 'car'
  const plateRaw = (payload?.plate || payload?.vehicle?.plate || '').trim()
  const resolvedParts = resolvePlateParts({
    raw: plateRaw,
    plate_left: payload?.plateLeft || payload?.vehicle?.plateLeft || payload?.vehicle?.plate_left || '',
    plate_letter: payload?.plateLetter || payload?.vehicle?.plateLetter || payload?.vehicle?.plate_letter || '',
    plate_mid: payload?.plateMid || payload?.vehicle?.plateMid || payload?.vehicle?.plate_mid || '',
    plate_right: payload?.plateRight || payload?.vehicle?.plateRight || payload?.vehicle?.plate_right || '',
    plate_type: plateType,
  })
  const params = {
    plate_number: buildPlateNumber({ ...resolvedParts, plateType }) || plateRaw,
    plate_left: plateType === 'motorcycle' ? '' : String(resolvedParts.left || '').trim(),
    plate_letter: String(resolvedParts.letter || '').trim(),
    plate_mid: String(resolvedParts.mid || '').trim(),
    plate_right: plateType === 'motorcycle' ? '' : String(resolvedParts.right || '').trim()
  }
  const { data } = await api.get('/vehicles/plate-status/', { params })
  return data || { is_blocked: false }
}

const saveVehicle = async (payload, status) => {
  const body = buildCreateOrUpdatePayload(payload, status)
  const editingId = payload?.vehicle?.id || vehicleDraft.value?.id || null
  if (editingId) {
    const { data } = await api.patch(`/vehicles/${editingId}/`, body)
    const idx = vehicleStore.vehicles.findIndex((item) => item.id === editingId)
    if (idx >= 0) vehicleStore.vehicles[idx] = data
    return data
  }
  return vehicleStore.createVehicle(body)
}

const handleStepOneRefer = async (payload) => {
  try {
    const plateStatus = await fetchPlateBlockedStatus(payload)
    if (plateStatus.is_blocked) {
      vehicleDraft.value = { ...payload, is_plate_blocked: true }
      modalStep.value = 2
      return
    }
    await saveVehicle({ vehicle: payload }, 'entered')
    closeVehicleModal()
  } catch (error) {
    console.error('refer step one error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ثبت ارجاع ناموفق بود.'), { title: 'خطا در ثبت ارجاع' })
  }
}

const handleStepTwoAssign = async (payload) => {
  try {
    await saveVehicle(payload, 'ready_to_settle')
    closeVehicleModal()
  } catch (error) {
    console.error('assign step two error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ثبت تخصیص ناموفق بود.'), { title: 'خطا در ثبت تخصیص' })
  }
}
const cars = computed(() => vehicles.value.map((item) => ({
  id: item.id,
  statusKey: item.status,
  queueBucket: item.status === 'released' ? 'released' : item.status === 'cancelled' ? 'cancelled' : item.status === 'ready_to_settle' ? 'in_progress' : 'entered',
  status: item.status === 'cancelled' ? 'لغو' : item.status === 'released' ? 'ترخیص شده' : item.status === 'ready_to_settle' ? 'در حال انجام' : 'در انتظار تکمیل',
  color: item.status === 'cancelled' ? '#ef4444' : item.status === 'released' ? '#f59e0b' : item.status === 'in_progress' ? '#0058be' : '#16a34a',
  badgeBg: '#eef2ff',
  badgeText: '#334155',
  time: formatDateTime(item.check_in_at),
  sortTime: item.check_in_at,
  plateLeft: item.plate_left || '--',
  plateLetter: item.plate_letter || '-',
  plateMid: item.plate_mid || '---',
  plateRight: item.plate_right || '--',
  plateType: item.plate_type || 'car',
  model: item.car_model,
  colorName: item.car_color,
  plateDisplay: item.plate_number || '-',
  service: Array.isArray(item.job?.service_lines) && item.job.service_lines.length
    ? item.job.service_lines.map((line) => line.service_name || 'خدمت').join('، ')
    : 'خدمت ثبت نشده',
  driverName: item.driver_name,
  driverPhone: item.driver_phone,
  customerScore: Number(item.customer_score || 0),
  finalTotal: item.job?.final_total || item.job?.services_total || 0,
  carwashShare: item.job?.carwash_share_amount || 0,
  workerName: assignedWorkersLabel(item.job),
  action: item.status === 'released' ? 'ترخیص انجام شد' : item.status === 'ready_to_settle' ? 'ترخیص خودرو' : item.status === 'cancelled' ? 'لغو شده' : 'تکمیل اطلاعات',
  actionClass: item.status === 'ready_to_settle' ? 'action-release' : item.status === 'released' || item.status === 'cancelled' ? 'action-done' : 'action-complete'
})))

const counts = computed(() => {
  const data = { entered: 0, in_progress: 0, released: 0, cancelled: 0 }
  cars.value.forEach((item) => {
    if (Object.prototype.hasOwnProperty.call(data, item.queueBucket)) data[item.queueBucket] += 1
  })
  return data
})

const filterItems = computed(() => [
  { key: 'entered', label: `در انتظار تکمیل (${counts.value.entered})` },
  { key: 'in_progress', label: `در حال انجام (${counts.value.in_progress})` },
  { key: 'released', label: `ترخیص شده (${counts.value.released})` },
  { key: 'cancelled', label: `لغو (${counts.value.cancelled})` },
  { key: 'all', label: `کل (${cars.value.length})` }
])

const filteredCars = computed(() => {
  let items = cars.value
  if (activeFilter.value !== 'all') items = items.filter((item) => item.queueBucket === activeFilter.value)
  if (search.value.trim()) {
    const query = search.value.trim().toLowerCase()
    items = items.filter((item) => [
      item.plateLeft,
      item.plateLetter,
      item.plateMid,
      item.plateRight,
      item.plateDisplay,
      item.model,
      item.driverName,
      item.driverPhone,
      item.workerName
    ].join(' ').toLowerCase().includes(query))
  }
  return [...items].sort((first, second) => {
    const weightMap = { entered: 0, in_progress: 1, released: 3, cancelled: 4 }
    const weightDiff = (weightMap[first.queueBucket] ?? 9) - (weightMap[second.queueBucket] ?? 9)
    if (weightDiff !== 0) return weightDiff
    return new Date(first.sortTime).getTime() - new Date(second.sortTime).getTime()
  })
})
const cancelVehicle = async () => {
  if (!selectedVehicle.value?.id) return
  try {
    const { data } = await api.patch(`/vehicles/${selectedVehicle.value.id}/status/`, {
      status: 'cancelled',
      note: 'لغو توسط اپراتور'
    })
    vehicleStore.selectedVehicle = data
    const idx = vehicleStore.vehicles.findIndex((item) => item.id === data.id)
    if (idx >= 0) vehicleStore.vehicles[idx] = data
  } catch (error) {
    console.error('cancelVehicle error:', error?.response?.data || error)
    notifyError('لغو سفارش ناموفق بود.', { title: 'خطا در لغو سفارش' })
  }
}

const blockSelectedVehiclePlate = async () => {
  if (!selectedVehicle.value?.id) return
  try {
    const { data } = await api.post(`/vehicles/${selectedVehicle.value.id}/block-plate/`, {})
    selectedVehicle.value = {
      ...selectedVehicle.value,
      is_plate_blocked: Boolean(data?.is_blocked)
    }
    const idx = vehicleStore.vehicles.findIndex((item) => item.id === selectedVehicle.value.id)
    if (idx >= 0) {
      vehicleStore.vehicles[idx] = {
        ...vehicleStore.vehicles[idx],
        is_plate_blocked: true
      }
    }
  } catch (error) {
    console.error('blockSelectedVehiclePlate error:', error?.response?.data || error)
    notifyError('بلاک کردن پلاک ناموفق بود.', { title: 'خطا در بلاک پلاک' })
  }
}

onMounted(() => {
  vehicleStore.fetchVehicles()
})
watch(hasOperatorModalOpen, (isOpen) => {
  if (isOpen) lockBodyScrollForModal()
  else unlockBodyScrollForModal()
}, { immediate: true })
watch(
  () => [invoiceLayout.value.preset, invoiceLayout.value.thermalWidthMm, invoiceLayout.value.thermalHeightMm],
  () => {
    if (!showInvoicePreviewModal.value) return
    if (invoiceRenderTimer.value) window.clearTimeout(invoiceRenderTimer.value)
    invoiceRenderTimer.value = window.setTimeout(() => {
      buildInvoicePdf()
    }, 220)
  }
)
onBeforeUnmount(() => {
  unlockBodyScrollForModal()
  if (invoiceRenderTimer.value) window.clearTimeout(invoiceRenderTimer.value)
  revokeInvoicePdfUrl()
})
</script>

<style scoped>
.dashboard-content { min-width: 0; width: 100%; max-width: 100%; overflow-x: hidden; }
.primary-btn { height: 40px; border: none; border-radius: 12px; color: #fff; font-weight: 700; padding: 0 16px; background: linear-gradient(135deg, #0058be 0%, #57dffe 100%); cursor: pointer;margin-right: 3%; }
.filters { display: flex; gap: 10px; overflow-x: auto; overflow-y: hidden; padding-bottom: 8px; flex-wrap: nowrap; align-items: center; }
.filters > * { flex: 0 0 auto; }
.filters > .primary-btn { width: auto; margin-right: 0; }
.chip { border: none; border-radius: 999px; padding: 10px 16px; background: #e6e8ea; color: #4b5563;font-size:10px; font-weight: 500; white-space: nowrap; }
.chip.active { background: #0058be; color: #fff; }
.cards-grid { margin-top: 18px; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 20px; width: 100%; max-width: 100%; }
.car-card { min-width: 0; background: #fff; border-right: 4px solid #0058be; border-radius: 16px; padding: 16px; box-shadow: 0 14px 30px -10px rgba(15,23,42,.12); display: flex; flex-direction: column; gap: 12px; transition: transform .2s ease, box-shadow .2s ease; }
.car-card:hover { transform: translateY(-3px); box-shadow: 0 20px 34px -14px rgba(15,23,42,.16); }
.car-card.card-released { opacity: .58; filter: grayscale(.2); }
.car-card.card-released:hover { transform: none; box-shadow: 0 14px 30px -10px rgba(15,23,42,.12); }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.status { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: #475569; }
.dot { width: 8px; height: 8px; border-radius: 99px; }
.time { font-size: 10px; padding: 4px 9px; border-radius: 999px; font-weight: 700; }
.plate-box { width: 100%; max-width: 100%; min-width: 0; border-radius: 12px; padding: 10px; display: flex; align-items: stretch; justify-content: center; direction: ltr; overflow: hidden; }
.plate-white-wrap { min-width: 0; display: flex; align-items: center; gap: 10px; background: #6f59ef18; color: #111827; border-radius: 7px 0 0 7px; padding: 4px 12px; }
.plate-part { display: inline-flex; align-items: center; justify-content: center; line-height: 1; }
.plate-two, .plate-three { font-size: 10px; font-weight: 700; height: 16px; padding-top: 2px; padding-bottom: 1px; white-space: nowrap; }
.plate-letter { font-size: 10px; font-weight: 700; min-width: 8px; padding-top: 0; white-space: nowrap; }
.plate-blue { min-width: 18px; background: #2563eb; color: #ffffff; border-radius: 0 7px 7px 0; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 8px; line-height: 1; padding-top: 2px; padding-bottom: 1px; white-space: nowrap; }
.car-info h3 { margin: 0 0 6px; font-size: 15px; }
.car-info p { margin: 3px 0; font-size: 13px; color: #64748b; }
.customer-score-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.customer-score-row strong { color: #0f172a; font-weight: 700; font-size: 12px; }
.star-track { position: relative; display: inline-grid; line-height: 1; font-size: 14px; letter-spacing: 1px; width: max-content; direction: ltr; }
.star-bg { color: #d1d5db; grid-area: 1 / 1; }
.star-fill { position: absolute; top: 0; left: 0; height: 100%; overflow: hidden; white-space: nowrap; color: #f59e0b; direction: ltr; }
.card-action { margin-top: auto; height: 42px; border: none; border-radius: 12px; font-weight: 700; }
.card-action.action-complete { background: #d0fadf; color: #166534; }
.card-action.action-release { background: #fef3c7; color: #92850e; }
.card-action.action-done { background: #e5e7eb; color: #374151; }
.card-passive-state { margin-top: auto; height: 42px; border-radius: 12px; border: 1px dashed #cbd5e1; color: #64748b; background: #f8fafc; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.secondary-btn,.danger-btn{border:none;border-radius:10px;padding:8px 12px;cursor:pointer}
.secondary-btn{background:#e2e8f0;color:#334155}
.secondary-btn.blocked-btn{background:#fee2e2;color:#991b1b;cursor:default}
.danger-btn{background:#fee2e2;color:#b91c1c}
.danger-btn:disabled{background:#e5e7eb;color:#94a3b8;cursor:not-allowed}
.small-btn{padding:6px 10px}
.release-panel { width: min(1420px, 100%); max-width: 100%; height: calc(100vh - 40px); max-height: calc(100vh - 40px); display: flex; flex-direction: column; overflow-y: auto; overflow-x: hidden; -webkit-overflow-scrolling: touch; background: linear-gradient(180deg,#fdfefe,#f6fbff); }
.release-loading { min-height: 280px; display: flex; align-items: center; justify-content: center; color: #64748b; font-size: 14px; }
.release-modal-head{align-items:flex-start;gap:16px;padding:20px 24px;background:rgba(255,255,255,.9);backdrop-filter:blur(14px)}
.release-modal-copy{display:grid;gap:4px}
.release-modal-tools{display:flex;align-items:center;gap:12px;margin-inline-start:auto}
.release-modal-vehicle{display:grid;gap:4px;padding:10px 14px;border-radius:18px;border:1px solid #d7e5f8;background:linear-gradient(180deg,#ffffff,#f4f8ff);min-width:0}
.release-modal-vehicle strong{font-size:13px;color:#0f172a}
.release-modal-vehicle span{font-size:12px;color:#0058be;font-weight:800;line-height:1.6}
.release-modal-body{position:relative;flex:1;min-height:0;overflow:visible;display:grid;gap:14px;padding:16px 0 20px;background:
 radial-gradient(circle at top right, rgba(34,197,94,.08), transparent 18%),
 radial-gradient(circle at top left, rgba(14,165,233,.10), transparent 24%),
 linear-gradient(180deg,#edf7ff,#f5f9ff)}
.release-layout { padding: 0 24px; display: grid; gap: 20px; grid-template-columns: minmax(0,1.05fr) minmax(0,.95fr) minmax(0,1.08fr); background:
  radial-gradient(circle at top right, rgba(34,197,94,.10), transparent 24%),
  radial-gradient(circle at top left, rgba(14,165,233,.14), transparent 28%),
  linear-gradient(180deg,#edf7ff,#eef5ff); }
.release-layout.release-layout-no-products { grid-template-columns: minmax(0,1fr) minmax(0,1fr); }
.release-col { background: rgba(255,255,255,.88); border: 1px solid rgba(191,215,255,.9); border-radius: 24px; padding: 18px; display: flex; flex-direction: column; min-height: 620px; box-shadow: 0 22px 45px -32px rgba(15,23,42,.45); backdrop-filter: blur(10px); }
.release-products-col, .release-summary-col { border-right: 1px solid rgba(191,215,255,.85); }
.release-title-inline{display:flex;justify-content:space-between;align-items:center;gap:10px}
.service-picker-overlay{position:absolute;inset:0;z-index:8;display:flex;align-items:center;justify-content:center;padding:24px;background:rgba(15,23,42,.28);backdrop-filter:blur(6px)}
.service-picker-panel{width:min(920px,100%);max-height:min(720px,100%);display:grid;gap:18px;padding:22px;border-radius:28px;background:linear-gradient(180deg,#ffffff,#f5f9ff);border:1px solid #d8e6ff;box-shadow:0 28px 60px -34px rgba(15,23,42,.45);overflow:auto}
.service-picker-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.service-picker-head h4{margin:0;color:#0f172a;font-size:20px}
.service-picker-head p{margin:6px 0 0;color:#64748b;font-size:12px}
.service-picker-grid{display:flex;flex-wrap:wrap;gap:10px;align-content:flex-start}
.release-service-picker-grid{max-height:420px;overflow:auto;padding-inline-end:4px}
.service-bubble{border:1px solid #cfe1ff;border-radius:999px;padding:10px 16px;background:linear-gradient(180deg,#ffffff,#f3f8ff);color:#0f4c81;font-size:13px;font-weight:700;line-height:1.7;cursor:pointer;transition:.18s ease;white-space:nowrap}
.service-bubble.selected{border-color:#0ea5e9;background:linear-gradient(135deg,#0f4c81,#0ea5e9);color:#fff;box-shadow:0 18px 28px -22px rgba(14,165,233,.78)}
.service-picker-foot{display:flex;justify-content:flex-end;gap:10px}
.secondary-foot-btn{height:44px;padding:0 18px;border:1px solid #cbd5e1;border-radius:14px;background:#fff;color:#334155;font-weight:700;cursor:pointer}
.release-service-bubbles{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px;min-width:0}
.release-service-bubble{border:1px solid #cfe1ff;border-radius:999px;padding:9px 14px;background:linear-gradient(180deg,#ffffff,#f3f8ff);color:#0f4c81;font-size:12px;font-weight:700;line-height:1.6;cursor:pointer;transition:.18s ease;white-space:nowrap;box-shadow:0 10px 22px -20px rgba(15,76,129,.45)}
.release-service-bubble:hover{border-color:#8fc5ff;background:linear-gradient(180deg,#ffffff,#eaf5ff);transform:translateY(-1px)}
.release-service-bubble.active{border-color:#0ea5e9;background:linear-gradient(135deg,#0f4c81,#0ea5e9);color:#fff;box-shadow:0 18px 28px -22px rgba(14,165,233,.78)}
.add-service-row{display:flex;gap:8px;align-items:center}
.plus-btn{width:42px;height:42px;padding:0;display:inline-flex;align-items:center;justify-content:center;font-size:24px;font-weight:700;line-height:1}
.bonus-penalty-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px;align-items:end}
.bonus-penalty-row .tip-input-row{margin-top:0;min-width:0}
.bonus-penalty-table{display:grid;gap:12px}
.bonus-penalty-table-head{display:grid;gap:4px}
.bonus-penalty-table-head small{color:#64748b;font-size:12px}
.bonus-penalty-list{display:grid;gap:10px}
.bonus-penalty-item{display:grid;grid-template-columns:minmax(180px,.9fr) minmax(0,1fr) minmax(0,1fr);gap:10px;align-items:end;padding:12px;border:1px solid #d6e6ff;border-radius:16px;background:#fff}
.bonus-penalty-item strong{color:#0f172a;font-size:14px}
.add-service-row select,.tip-input-row select{height:46px;border:1px solid #cbd5e1;border-radius:14px;padding:0 12px;background:#fff}
.cheque-inline-card{margin-top:10px;padding:16px;border:1px solid #c7dcff;border-radius:18px;background:linear-gradient(180deg,#ffffff,#eef6ff);box-shadow:inset 0 1px 0 rgba(255,255,255,.7)}
.cheque-inline-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
.cheque-inline-head strong{display:block;color:#0f172a;font-size:14px}
.cheque-inline-head small{display:block;color:#64748b;font-size:12px;line-height:1.8}
.release-title { padding-bottom: 12px; border-bottom: 1px solid #dbe9ff; margin-bottom: 14px; }
.release-title h3 { margin: 0; font-size: 20px; color: #111827; }
.release-list { display: grid; gap: 10px; overflow: auto; }
.service-check-item { border: 1px solid #d4e4ff; border-radius: 18px; padding: 14px; display: flex; justify-content: space-between; gap: 12px; background: linear-gradient(180deg,#f9fcff,#eef5ff); }
.service-check-item h4 { margin: 0 0 4px; font-size: 15px; color: #0f172a; }
.service-check-item p { margin: 0; font-size: 12px; color: #64748b; }
.service-check-action { display: grid; justify-items: end; gap: 8px; align-content: center; }
.service-check-action span { font-size: 13px; font-weight: 700; color: #0058be; }
.service-check-action label { font-size: 12px; color: #475569; display: inline-flex; align-items: center; gap: 6px; }
.release-product-search { margin-bottom: 10px; }
.release-product-search input { width: 100%; height: 46px; border: 1px solid #bfd7ff; border-radius: 14px; padding: 0 14px; background: #f4f9ff; }
.products-scroll { max-height: 360px; padding-right: 4px; }
.product-item { border: 1px solid #d4e4ff; border-radius: 18px; padding: 10px 12px; display: grid; grid-template-columns: minmax(0,1fr) auto; gap: 10px; align-items: center; background:
 linear-gradient(180deg,#ffffff,#f8fbff);
 box-shadow: 0 18px 32px -28px rgba(15,23,42,.18); }
.product-item h4 { margin: 0 0 4px; font-size: 13px; color: #111827; line-height: 1.5; }
.product-item p { margin: 0; font-size: 11px; color: #64748b; }
.product-item span { display:inline-flex; margin-top:6px; padding:4px 8px; border-radius:999px; background:#ebf8ff; font-size: 11px; color: #00687a; font-weight: 800; }
.product-item.unavailable { opacity: .55; }
.product-item p.stock-empty { color: #ba1a1a; }
.qty-controls { display: grid; gap: 8px; min-width: 84px; }
.qty-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.qty-controls button { width: 100%; height: 28px; border: none; border-radius: 999px; background: transparent; color: #0f4c81; cursor: pointer; font-size: 20px; font-weight: 800; box-shadow: none; }
.qty-controls button:disabled { opacity: .45; cursor: not-allowed; }
.qty-controls input { width: 100%; height: 34px; border: 1px solid #bfd7ff; border-radius: 12px; text-align: center; background: #fff; }
.release-summary-hero{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:18px;border-radius:22px;background:
 linear-gradient(135deg,#082f49 0%,#0f4c81 40%,#0ea5e9 100%);color:#fff;box-shadow:0 22px 36px -24px rgba(8,47,73,.78)}
.release-summary-hero small{display:block;font-size:12px;color:rgba(255,255,255,.78);margin-bottom:6px}
.release-summary-hero strong{display:block;font-size:28px;line-height:1.1}
.release-summary-hero p{margin:8px 0 0;font-size:12px;line-height:1.9;color:rgba(255,255,255,.82)}
.release-summary-badge{padding:8px 12px;border-radius:999px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.22);font-size:12px;font-weight:700;white-space:nowrap}
.summary-stat-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:14px}
.summary-stat-card{padding:14px;border-radius:18px;border:1px solid #d9e8ff;background:linear-gradient(180deg,#ffffff,#f5faff);display:grid;gap:6px}
.summary-stat-card span{font-size:12px;color:#64748b}
.summary-stat-card strong{font-size:15px;color:#0f172a}
.summary-stat-card small{font-size:11px;color:#0f766e;font-weight:700}
.summary-stat-card.accent-card{background:linear-gradient(180deg,#f0fdf9,#ecfeff);border-color:#b8ece6}
.tip-input-row { margin-top: 10px; display: grid; gap: 6px; }
.tip-input-row span { color: #64748b; font-size: 12px; }
.tip-input-row input,.tip-input-row textarea { width:100%; max-width:100%; box-sizing:border-box; border: 1px solid #bfd7ff; border-radius: 14px; background: #f7fbff; }
.tip-input-row input { height: 46px; padding: 0 12px; }
.tip-input-row textarea { padding: 10px; resize: vertical; min-height: 84px; font-family: inherit; }
.modern-input-row{margin-top:14px;padding:12px 14px;border:1px solid #d6e7ff;border-radius:18px;background:linear-gradient(180deg,#ffffff,#f4f9ff)}
.cheque-modal-panel{width:min(780px,100%);overflow:hidden}
.cheque-modal-head{align-items:flex-start;background:linear-gradient(180deg,#f8fbff,#eef6ff)}
.cheque-modal-subtitle{margin:6px 0 0;color:#64748b;font-size:12px;line-height:1.8}
.cheque-modal-body{display:grid;gap:16px;padding:18px;background:
 radial-gradient(circle at top right, rgba(14,165,233,.12), transparent 26%),
 linear-gradient(180deg,#f9fcff,#edf5ff)}
.cheque-modal-summary{padding:18px;border-radius:22px;background:linear-gradient(135deg,#0f172a 0%,#0f4c81 58%,#38bdf8 100%);color:#fff;display:grid;gap:6px}
.cheque-modal-summary small{font-size:12px;color:rgba(255,255,255,.72)}
.cheque-modal-summary strong{font-size:24px}
.cheque-modal-summary p{margin:0;color:rgba(255,255,255,.84);font-size:12px}
.cheque-modal-summary span{font-size:12px;line-height:1.9;color:rgba(255,255,255,.8)}
.cheque-fields-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.cheque-field{display:grid;gap:6px;padding:14px;border:1px solid #d5e5ff;border-radius:18px;background:rgba(255,255,255,.85)}
.cheque-field span{font-size:12px;color:#475569}
.cheque-field-wide{grid-column:span 2}
.cheque-field :deep(input),.cheque-field input{width:100%;height:46px;border:1px solid #bfd7ff;border-radius:14px;padding:0 12px;background:#fff;box-sizing:border-box}
.cheque-modal-actions{display:flex;justify-content:flex-end;gap:10px}
.cheque-modal-actions .primary-btn{margin-right:0}
.worker-selection-panel{margin-top:14px;padding:14px;border:1px solid #d7e7ff;border-radius:20px;background:linear-gradient(180deg,#ffffff,#f4f9ff);display:grid;gap:12px}
.worker-selection-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.worker-selection-head h4{margin:0;font-size:15px;color:#0f172a}
.worker-selection-head p{margin:6px 0 0;font-size:12px;color:#64748b;line-height:1.8}
.worker-selection-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.worker-select-card{border:1px solid #d5e5ff;border-radius:18px;padding:14px;background:#fff;display:grid;justify-items:start;gap:8px;text-align:right;transition:.2s ease;cursor:pointer}
.worker-select-card.selected{background:linear-gradient(180deg,#eff8ff,#dcf2ff);border-color:#7dd3fc;box-shadow:0 14px 28px -24px rgba(14,165,233,.7)}
.worker-select-card strong{font-size:14px;color:#0f172a}
.worker-select-card small{font-size:12px;color:#64748b}
.worker-select-check{width:28px;height:28px;border-radius:10px;background:#e2e8f0;color:#334155;display:inline-flex;align-items:center;justify-content:center;font-weight:800}
.worker-select-card.selected .worker-select-check{background:#0ea5e9;color:#fff}
.summary-share { margin-top: 12px; border: 1px dashed #bfd7ff; border-radius: 20px; padding: 12px; background: linear-gradient(180deg,#f9fcff,#edf5ff); display: grid; gap: 10px; }
.worker-share-editor { display: grid; gap: 10px; padding-bottom: 8px; border-bottom: 1px dashed #bfd7ff; }
.modern-worker-share-editor{grid-template-columns:repeat(2,minmax(0,1fr))}
.worker-share-card{padding:12px;border-radius:18px;border:1px solid #d5e5ff;background:#fff;display:grid;gap:10px}
.worker-share-card-head{display:grid;gap:4px}
.worker-share-card-head small{font-size:11px;color:#64748b}
.worker-share-input { display: grid; grid-template-columns: minmax(120px, 1fr) minmax(0, 1.6fr); align-items: center; gap: 10px; font-size: 13px; color: #334155; }
.worker-share-name { font-weight: 700; color: #0f172a; }
.worker-share-controls { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, .8fr); gap: 8px; }
.modern-worker-share-controls{grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr)}
.worker-share-control { display: flex; align-items: center; gap: 6px; }
.worker-share-control input { width: 100%; height: 40px; border: 1px solid #bfd7ff; border-radius: 12px; padding: 0 10px; background: #fff; text-align: center; }
.worker-share-control small { color: #64748b; font-size: 12px; font-weight: 700; }
.summary-share p { margin: 0; display: flex; justify-content: space-between; font-size: 13px; color: #334155; }
.summary-share p span small { color: #64748b; font-size: 11px; margin-right: 4px; }
.summary-share .summary-share-total { border-top: 1px dashed #bfd7ff; padding-top: 8px; margin-top: 4px; font-weight: 700; }
.summary-final { margin: 14px 0 0; padding:16px 18px; border:1px solid #d7e8ff; border-radius:18px; background:linear-gradient(180deg,#ffffff,#f7fbff); display: flex; justify-content: space-between; font-size: 20px; font-weight: 800; color: #111827; }
.release-secondary-section{margin:0 24px;padding:18px;border:1px solid #d6e3f5;border-radius:24px;background:
 radial-gradient(circle at top left, rgba(34,197,94,.10), transparent 22%),
 linear-gradient(180deg,#ffffff,#f6f9fd);display:grid;gap:14px}
.release-secondary-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.release-secondary-head h4{margin:0;color:#0f172a;font-size:16px}
.release-secondary-head small{display:block;margin-top:4px;color:#64748b;font-size:12px}
.release-secondary-chip{padding:8px 12px;border-radius:999px;background:#eaf5ff;color:#0f4c81;font-size:12px;font-weight:700;border:1px solid #c7dcff}
.release-secondary-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.detail-field{margin-top:0;padding:14px;border:1px solid #d6e6ff;border-radius:18px;background:rgba(255,255,255,.8)}
.detail-field-wide{grid-column:span 2}
.split-payment-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;align-items:start}
.split-payment-summary{grid-column:1/-1;padding:14px 16px;border-radius:18px;background:linear-gradient(180deg,#f8fbff,#edf7ff);border:1px dashed #bcd8ff;display:grid;gap:6px}
.split-payment-summary strong{font-size:14px;color:#0f172a}
.split-payment-summary span{font-size:12px;color:#475569;line-height:1.8}
.payment-method-preview{padding:14px;border-radius:18px;border:1px dashed #bcd8ff;background:linear-gradient(180deg,#f5fbff,#edf7ff);display:grid;gap:6px}
.payment-method-preview strong{font-size:14px;color:#0f172a}
.payment-method-preview p{margin:0;font-size:12px;line-height:1.9;color:#475569}
.payment-method-preview p span{color:#0f4c81;font-weight:700}
.invoice-preview-btn{min-width:88px}
.mark-paid { margin-top: 12px; display: inline-flex; align-items: center; gap: 8px; color: #334155; font-size: 13px; }
.mark-paid.forced-paid { opacity: .85; }
.release-actions { margin-top: auto; padding-top: 16px; display: flex; gap: 8px; }
.back-btn { flex: 1; height: 44px; border: 1px solid #bfd7ff; border-radius: 12px; background: #fff; color: #334155; font-weight: 700; cursor: pointer; }
.confirm-release-btn { flex: 1; height: 44px; border: none; border-radius: 12px; font-weight: 700; color: #ffffff; background: linear-gradient(90deg,#0058be,#2170e4); cursor: pointer; box-shadow: 0 8px 20px rgba(0,88,190,.2); }
.confirm-release-btn:disabled { opacity: .65; cursor: not-allowed; }
.invoice-modal-overlay{z-index:75}
.invoice-modal-panel{width:min(1120px,100%);max-width:100%;height:calc(100vh - 40px);display:flex;flex-direction:column;overflow:hidden}
.invoice-modal-head{align-items:flex-start}
.invoice-modal-subtitle{margin:6px 0 0;color:#64748b;font-size:12px}
.invoice-modal-body{display:grid;grid-template-rows:auto minmax(0,1fr);gap:14px;padding:16px;min-height:0;min-width:0;flex:1;background:linear-gradient(180deg,#f8fbff,#edf5ff)}
.invoice-format-toolbar{display:grid;gap:12px;padding:14px;border-radius:18px;background:rgba(255,255,255,.88);border:1px solid #dbe7f5}
.invoice-format-presets{display:flex;gap:8px;flex-wrap:wrap}
.invoice-format-chip{border:none;border-radius:14px;padding:10px 14px;background:#eef4ff;color:#334155;font-weight:800;cursor:pointer}
.invoice-format-chip.active{background:linear-gradient(135deg,#c4b5fd,#e9d5ff);color:#4c1d95}
.invoice-thermal-size-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.invoice-thermal-size-grid label{display:grid;gap:6px}
.invoice-thermal-size-grid span{font-size:12px;color:#64748b}
.invoice-modal-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap}
.invoice-preview-loading,.invoice-preview-empty{min-height:380px;border:1px dashed #bfd7ff;border-radius:18px;background:#fff;display:flex;align-items:center;justify-content:center;color:#64748b;padding:20px}
.invoice-preview-frame-wrap{min-height:0;min-width:0;border-radius:18px;overflow:auto;border:1px solid #dbe7f5;background:#fff;box-shadow:0 16px 36px rgba(15,23,42,.08);height:100%}
.invoice-preview-frame{display:block;width:100%;height:100%;min-height:0;min-width:0;border:0;background:#fff}
.invoice-print-stage{position:fixed;left:-99999px;top:0;pointer-events:none}
.invoice-template{background:#fff;padding:0;box-sizing:border-box;overflow:hidden}
.invoice-sheet{direction:rtl;background:#fff;color:#0f172a;font-family:Tahoma,Arial,sans-serif;display:grid;box-sizing:border-box;overflow:hidden}
.invoice-sheet-a5{font-size:.9em}
.invoice-sheet-thermal{font-size:.82em}
.invoice-sheet-head{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);justify-content:space-between;gap:8px;padding:10px 12px;border-radius:10px;background:linear-gradient(135deg,#0f172a,#0f4c81 58%,#0ea5e9);color:#fff;min-width:0}
.invoice-sheet-head small{display:block;font-size:8px;color:rgba(255,255,255,.72);letter-spacing:0}
.invoice-sheet-head strong{display:block;font-size:15px;line-height:1.35;margin-top:2px;overflow-wrap:anywhere}
.invoice-sheet-head span{display:block;margin-top:3px;color:rgba(255,255,255,.78);font-size:8px;overflow-wrap:anywhere}
.invoice-sheet-meta{display:grid;gap:4px;justify-items:end;min-width:0;align-content:center}
.invoice-sheet-meta strong{font-size:10px;overflow-wrap:anywhere}
.invoice-sheet-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px}
.invoice-sheet-grid article{border:1px solid #dbe7f5;border-radius:8px;padding:6px 7px;background:linear-gradient(180deg,#ffffff,#f8fbff);display:grid;gap:2px;min-width:0}
.invoice-sheet-grid article span{font-size:8px;color:#64748b}
.invoice-sheet-grid article strong{font-size:9px;line-height:1.6;min-width:0;overflow-wrap:anywhere;word-break:break-word}
.invoice-identity-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
.invoice-identity-grid article{border:1px solid #dbe7f5;border-radius:8px;padding:7px;background:linear-gradient(180deg,#ffffff,#f8fbff);display:grid;gap:4px;min-width:0}
.invoice-identity-grid small{color:#0f4c81;font-size:9px;font-weight:800}
.invoice-identity-grid p{margin:0;display:grid;grid-template-columns:minmax(0,.62fr) minmax(0,1fr);gap:6px;align-items:start;color:#334155;font-size:8px;line-height:1.5;min-width:0}
.invoice-identity-grid p span{color:#64748b;min-width:0}
.invoice-identity-grid p strong{color:#0f172a;font-size:8px;font-weight:800;min-width:0;overflow-wrap:anywhere;word-break:break-word}
.invoice-sheet-section{display:grid;gap:6px}
.invoice-section-head strong{font-size:10px;color:#0f172a}
.invoice-table{width:100%;max-width:100%;table-layout:fixed;border-collapse:separate;border-spacing:0;border:1px solid #dbe7f5;border-radius:8px;overflow:hidden}
.invoice-table th,.invoice-table td{padding:4px 6px;border-bottom:1px solid #e2e8f0;text-align:right;font-size:9px;line-height:1.6;overflow-wrap:anywhere;word-break:break-word;min-width:0}
.invoice-table th{background:#eff6ff;color:#334155;font-weight:800}
.invoice-services-table th:first-child,.invoice-services-table td:first-child{width:58%}
.invoice-services-table th:nth-child(2),.invoice-services-table td:nth-child(2){width:14%;text-align:center}
.invoice-services-table th:nth-child(3),.invoice-services-table td:nth-child(3){width:28%}
.invoice-products-table th:first-child,.invoice-products-table td:first-child{width:48%}
.invoice-products-table th:nth-child(2),.invoice-products-table td:nth-child(2){width:12%;text-align:center}
.invoice-products-table th:nth-child(3),.invoice-products-table td:nth-child(3){width:20%}
.invoice-products-table th:nth-child(4),.invoice-products-table td:nth-child(4){width:20%}
.invoice-table tr:last-child td{border-bottom:0}
.invoice-payment-section{border:1px solid #dbe7f5;border-radius:10px;padding:7px 9px;background:#f8fbff}
.invoice-payment-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 8px}
.invoice-payment-grid p{margin:0;display:flex;justify-content:space-between;gap:8px;color:#334155;font-size:8px;line-height:1.6;min-width:0}
.invoice-payment-grid p span,.invoice-payment-grid p strong{min-width:0;overflow-wrap:anywhere;word-break:break-word}
.invoice-payment-grid p strong{color:#0f172a}
.invoice-total-section{border:1px solid #dbe7f5;border-radius:10px;padding:8px 10px;background:linear-gradient(180deg,#ffffff,#f8fbff)}
.invoice-totals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 8px}
.invoice-totals p{margin:0;display:flex;justify-content:space-between;gap:8px;color:#334155;font-size:9px;min-width:0}
.invoice-totals strong,.invoice-totals span{min-width:0;overflow-wrap:anywhere}
.invoice-grand-total{grid-column:1 / -1;padding-top:5px;border-top:1px dashed #bfd7ff;font-size:11px;font-weight:800;color:#0f172a}
.invoice-sheet-footer{padding-top:6px;border-top:1px dashed #cbd5e1;display:grid;gap:3px}
.invoice-sheet-footer p{margin:0;color:#475569;font-size:8px;line-height:1.6;overflow-wrap:anywhere;word-break:break-word}
.thermal-sheet-head{display:grid;justify-items:center;gap:3px;padding:10px 8px;border-bottom:1px dashed #cbd5e1}
.thermal-sheet-head strong{font-size:15px}
.thermal-sheet-head span,.thermal-sheet-head small{color:#475569;font-size:11px}
.thermal-sheet-block{display:grid;gap:8px;padding:8px 0;border-bottom:1px dashed #e2e8f0}
.thermal-sheet-block p{margin:0;display:flex;justify-content:space-between;gap:8px;font-size:11px;color:#334155}
.thermal-sheet-block p strong,.thermal-sheet-block p span{min-width:0;overflow-wrap:anywhere}
.thermal-lines-head{display:flex;justify-content:space-between;gap:8px}
.thermal-lines-head strong{font-size:12px}
.thermal-lines-head span{font-size:10px;color:#64748b}
.thermal-line-row{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;padding:6px 0;border-bottom:1px dashed #eef2f7}
.thermal-line-row:last-child{border-bottom:0}
.thermal-line-row div{display:grid;gap:2px}
.thermal-line-row strong{font-size:11px}
.thermal-line-row small{color:#64748b;font-size:10px}
.thermal-line-row span{font-size:11px;font-weight:800;color:#0f172a}
.thermal-line-row-product strong{color:#4c1d95}
.thermal-total-block{gap:6px}
.thermal-grand-total{padding-top:6px;border-top:1px dashed #cbd5e1;font-size:12px;font-weight:800;color:#0f172a}
.thermal-sheet-footer{display:grid;gap:4px;padding-top:6px}
.thermal-sheet-footer p{margin:0;text-align:center;color:#475569;font-size:10px;line-height:1.7}
.modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, .35); backdrop-filter: blur(3px); z-index: 60; display: flex; align-items: center; justify-content: center; padding: 20px; overflow-x: hidden; overflow-y: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; }
.modal-panel { width: min(1280px, 100%); max-width: 100%; max-height: calc(100vh - 40px); background: #fff; border-radius: 20px; overflow-y: auto; overflow-x: hidden; -webkit-overflow-scrolling: touch; display: flex; flex-direction: column; min-height: 0; box-shadow: 0 24px 60px -20px rgba(15,23,42,.4); }
.vehicle-entry-overlay { align-items: center; justify-content: center; }
.vehicle-entry-panel { width: min(980px, 100%); max-width: 100%; }
.vehicle-entry-head { background: rgba(255,255,255,.94); backdrop-filter: blur(12px); }
.step-one-modal-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: calc(100vh - 40px);
  max-height: calc(100vh - 40px);
  min-height: 0;
  background:
    radial-gradient(circle at top right, rgba(30,111,217,.06), transparent 24%),
    linear-gradient(180deg,#f7f9fb 0%,#eef5ff 100%);
}
.step-one-scroll-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
}
.step-two-modal-panel { width: min(1440px, 100%); max-width: 100%; height: calc(100vh - 40px); max-height: calc(100vh - 40px); overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column; min-height: 0; }
.modal-head { padding: 18px 22px; border-bottom: 1px solid #e3e6ed; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.modal-head h2 { margin: 0; font-size: 22px; }
.modal-step { margin: 0 0 6px; color: #64748b; font-size: 12px; }
.close-btn { width: 38px; height: 38px; border: 1px solid #dbe3ef; border-radius: 10px; background: #fff; cursor: pointer; }
.empty-row { margin: 0; color: #64748b; font-size: 13px; }
@media (max-width: 1400px) { .cards-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (max-width: 1100px) {
  .cards-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .release-layout { grid-template-columns: 1fr; }
  .release-col { min-height: auto; }
  .bonus-penalty-row { grid-template-columns: 1fr; }
  .release-secondary-grid,.cheque-fields-grid,.split-payment-grid { grid-template-columns: 1fr; }
  .detail-field-wide,.cheque-field-wide { grid-column: auto; }
  .release-secondary-section { margin: 14px 20px 20px; }
}
@media (max-width: 768px) {
  .cards-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
  .dashboard-content { padding-bottom: 8px; }
  .filters {
    display: flex;
    flex-wrap: nowrap;
    overflow-x: auto;
    overflow-y: hidden;
    gap: 8px;
    padding-bottom: 6px;
    margin-top: 2px;
  }
  .chip {
    padding: 8px 12px;
    font-size: 5px;
  }
  .primary-btn {
    height: 38px;
    padding: 0 12px;
    font-size: 13px;
    border-radius: 10px;
  }
  .car-card {
    padding: 10px;
    gap: 8px;
    border-radius: 14px;
  }
  .card-head {
    gap: 8px;
  }
  .status {
    font-size: 12px;
  }
  .time {
    font-size: 10px;
    padding: 4px 7px;
  }
  .modal-overlay {
    align-items: center;
    justify-content: center;
    padding: 8px;
    overflow-y: hidden;
    overflow-x: hidden;
  }
  .modal-panel {
    width: 100%;
    height: calc(100dvh - 16px);
    max-height: calc(100dvh - 16px);
    overflow-y: auto;
    overflow-x: hidden;
    border-radius: 18px;
  }
  .vehicle-entry-overlay {
    align-items: center !important;
    justify-content: center !important;
    padding: 12px !important;
  }
  .vehicle-entry-panel {
    width: min(860px, 100%) !important;
    max-width: calc(100vw - 24px) !important;
    border-radius: 24px !important;
  }
  .vehicle-entry-head {
    padding: 16px 16px 14px;
  }
  .step-one-modal-panel {
    height: calc(100dvh - 16px);
    max-height: calc(100dvh - 16px);
    overflow: hidden;
  }
  .step-two-modal-panel,
  .release-panel,
  .invoice-modal-panel { height: calc(100dvh - 16px); max-height: calc(100dvh - 16px); }
  .invoice-format-presets,
  .invoice-modal-actions { flex-direction: column; }
  .invoice-thermal-size-grid,
  .invoice-identity-grid,
  .invoice-payment-grid,
  .invoice-totals { grid-template-columns: 1fr; }
  .invoice-sheet-head { grid-template-columns: 1fr; }
  .primary-btn { margin-right: 0; }
  .card-head,
  .release-actions,
  .selected-worker-box,
  .summary-row,
  .summary-foot-actions,
  .worker-top,
  .worker-jobs,
  .worker-share-readonly {
    flex-direction: column;
    align-items: stretch;
  }
  .plate-box,
  .plate-white-wrap {
    width: 100%;
  }
  .plate-box {
    padding: 6px;
  }
  .plate-white-wrap {
    gap: 3px;
    padding: 2px 5px;
    flex-wrap: nowrap;
  }
  .plate-two, .plate-three { font-size: 10px; height: 15px; padding-top: 2px; padding-bottom: 1px; white-space: nowrap; }
  .plate-letter { font-size: 10px; min-width: 8px; padding-top: 0; white-space: nowrap; }
  .plate-blue { min-width: 18px; font-size: 8px; padding-top: 2px; padding-bottom: 1px; white-space: nowrap; }
  .car-info h3 {
    font-size: 13px;
    margin-bottom: 2px;
  }
  .car-info p,
  .customer-score-row strong {
    font-size: 11px;
    line-height: 1.55;
  }
  .star-track {
    font-size: 11px;
  }
  .service-line,
  .customer-score-row {
    display: none;
  }
  .card-action,
  .card-passive-state {
    height: 34px;
    font-size: 12px;
    border-radius: 10px;
  }
  .release-modal-head {
    padding: 14px 14px 12px;
    flex-direction: column;
    align-items: stretch;
  }
  .release-modal-tools {
    width: 100%;
    justify-content: space-between;
    margin-inline-start: 0;
  }
  .release-modal-vehicle {
    flex: 1;
    padding: 10px 12px;
    border-radius: 16px;
  }
  .release-modal-vehicle strong {
    font-size: 12px;
  }
  .release-modal-vehicle span {
    font-size: 11px;
  }
  .release-modal-body {
    gap: 10px;
    padding: 10px 0 12px;
  }
  .release-title-inline, .add-service-row { flex-direction: column; align-items: stretch; }
  .release-summary-hero,.worker-selection-head,.release-secondary-head,.cheque-inline-head,.cheque-modal-actions { flex-direction: column; align-items: stretch; }
  .release-layout {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 0 12px;
    background: transparent;
  }
  .release-col {
    min-height: auto;
    padding: 14px;
    border-radius: 22px;
  }
  .release-summary-col {
    order: 0;
    position: static;
    top: auto;
    z-index: auto;
    box-shadow: none;
  }
  .release-list { max-height: none; overflow: visible; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .products-scroll { max-height: 248px; overflow: auto; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .release-secondary-section {
    margin: 0 12px;
    padding: 14px;
    border-radius: 20px;
  }
  .plus-btn { width: 100%; }
  .worker-share-input, .worker-share-controls { grid-template-columns: 1fr; }
  .bonus-penalty-item { grid-template-columns: 1fr; }
  .service-discount-row input, .totals input { width: 100%; }
  .service-check-item,
  .product-item {
    border-radius: 16px;
    padding: 12px;
  }
  .service-check-item {
    display: grid;
    grid-template-columns: 1fr;
    align-items: start;
  }
  .product-item {
    grid-template-columns: 1fr;
    align-items: start;
    padding: 9px 10px;
  }
  .release-title h3 {
    font-size: 17px;
  }
  .release-summary-hero {
    padding: 16px;
    border-radius: 20px;
  }
  .release-summary-hero strong {
    font-size: 24px;
  }
  .summary-stat-grid {
    gap: 8px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .summary-stat-card {
    border-radius: 16px;
    padding: 12px;
  }
  .worker-selection-panel,
  .summary-share,
  .modern-input-row,
  .detail-field,
  .payment-method-preview,
  .cheque-inline-card {
    border-radius: 16px;
  }
  .release-actions {
    position: static;
    bottom: auto;
    margin-top: 12px;
    padding-top: 12px;
    background: none;
  }
  .worker-selection-grid,
  .modern-worker-share-editor {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .confirm-release-btn {
    min-height: 52px;
  }
  .empty-row {
    grid-column: 1 / -1;
  }
  .invoice-preview-loading,.invoice-preview-empty{min-height:220px}
  .invoice-modal-panel{height:calc(100vh - 16px)}
  .invoice-modal-actions{flex-direction:column}
}
@media (max-width: 480px) {
  .filters {
    display: flex;
    grid-template-columns: none;
  }
  .cards-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }
  .car-card {
    padding: 8px;
  }
  .plate-box {
    transform: none;
    transform-origin: center right;
    margin: 0;
  }
  .plate-white-wrap {
    gap: 4px;
    padding: 3px 6px;
  }
  .plate-two, .plate-three {
    font-size: 8px;
    height: 12px;
    padding-top: 1px;
    padding-bottom: 1px;
  }
  .plate-letter {
    font-size: 8px;
    min-width: 7px;
    padding-top: 0;
  }
  .plate-blue {
    min-width: 16px;
    font-size: 7px;
    padding-top: 1px;
    padding-bottom: 1px;
  }
  .car-info h3 {
    font-size: 12px;
  }
  .car-info p {
    font-size: 10px;
  }
  .chip {
    padding: 7px 10px;
    font-size: 10px;
  }
  .primary-btn {
    font-size: 12px;
    padding: 0 10px;
  }
  .vehicle-entry-overlay {
    padding: 10px !important;
  }
  .vehicle-entry-panel {
    max-width: calc(100vw - 20px) !important;
    border-radius: 20px !important;
  }
  .vehicle-entry-head {
    padding: 14px 14px 12px;
  }
  .step-one-modal-panel {
    height: calc(100dvh - 16px);
    max-height: calc(100dvh - 16px);
  }
  .release-layout {
    padding: 0 10px;
  }
  .release-secondary-section {
    margin: 0 10px;
    padding: 12px;
  }
  .release-list { max-height: none; }
  .products-scroll { max-height: 232px; }
  .release-list,
  .products-scroll,
  .summary-stat-grid,
  .worker-selection-grid,
  .modern-worker-share-editor {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .release-col {
    padding: 12px;
    border-radius: 18px;
  }
  .release-summary-hero {
    padding: 14px;
    border-radius: 18px;
  }
  .release-summary-hero strong {
    font-size: 21px;
  }
  .summary-final {
    font-size: 17px;
    padding: 14px;
  }
  .product-item h4 { font-size: 12px; }
  .product-item p,
  .product-item span { font-size: 10px; }
  .confirm-release-btn {
    min-height: 54px;
  }
}
</style>
