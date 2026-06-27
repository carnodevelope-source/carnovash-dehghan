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
          <button
            v-for="item in filterItems"
            :key="item.key"
            class="chip"
            :class="{ active: activeFilter === item.key }"
            @click="activeFilter = item.key"
          >
            {{ item.label }}
          </button>
          <button class="primary-btn" @click="openVehicleModal">ثبت خودروی جدید</button>
        
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

            <div class="plate-box">
              <div class="plate-white-wrap">
                <span class="plate-part plate-two">{{ car.plateTwoDigit }}</span>
                <span class="plate-part plate-letter">{{ car.plateLetter }}</span>
                <span class="plate-part plate-three">{{ car.plateThreeDigit }}</span>
              </div>
              <span class="plate-blue">{{ car.plateBlue }}</span>
            </div>

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
            <div v-if="releaseVehiclePlateLabel || releaseVehicleHeaderLabel" class="release-modal-vehicle">
              <strong v-if="releaseVehicleHeaderLabel">{{ releaseVehicleHeaderLabel }}</strong>
              <span v-if="releaseVehiclePlateLabel">{{ releaseVehiclePlateLabel }}</span>
            </div>
            <button class="close-btn" @click="closeReleaseModal">✕</button>
          </div>
        </header>
        <div v-if="releaseCheckoutLoading" class="release-loading">
          <BaseSpinner size="66px" color="#1d4ed8" ball-color="#60a5fa" label="در حال بارگذاری اطلاعات ترخیص..." />
        </div>
        <div v-else class="release-modal-body">
          <div class="release-layout">
            <div class="release-col">
            <div class="release-title release-title-inline">
              <h3>تایید خدمات</h3>
              <div class="add-service-row">
                <select v-model.number="releaseForm.selectedServiceToAdd">
                  <option :value="0">انتخاب خدمت</option>
                  <option v-for="service in releaseForm.availableServicesToAdd" :key="service.id" :value="service.id">{{ service.name }}</option>
                </select>
                <button type="button" class="secondary-btn plus-btn" @click="addServiceFromSystem">+</button>
              </div>
            </div>
            <div class="release-list">
              <article v-for="(line, lineIndex) in releaseForm.serviceLines" :key="line.id || `service-${line.service_id || lineIndex}`" class="service-check-item">
                <div>
                  <h4>{{ line.service_name }}</h4>
                  <p>تعداد: {{ Number(line.quantity || 0).toLocaleString('fa-IR') }}</p>
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
              <p v-if="!releaseForm.serviceLines.length" class="empty-row">خدمتی برای این خودرو ثبت نشده است.</p>
            </div>
            
            </div>

            <div class="release-col release-products-col">
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
                  <button type="button" @click="decreaseReleaseProduct(product.id)">-</button>
                  <input
                    type="number"
                    min="0"
                    :max="Number(product.available_quantity || 0)"
                    :value="getReleaseProductQty(product.id)"
                    @input="setReleaseProductQty(product.id, $event.target.value)"
                  />
                  <button
                    type="button"
                    @click="increaseReleaseProduct(product.id)"
                    :disabled="Number(product.available_quantity || 0) <= Number(getReleaseProductQty(product.id))"
                  >
                    +
                  </button>
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
                <span>تخفیف مشتری</span>
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
              <div v-if="selectedAssignedWorkers.length" class="worker-share-editor modern-worker-share-editor">
                <article
                  v-for="worker in selectedAssignedWorkers"
                  :key="`share-${worker.id || worker.sourceIndex}`"
                  class="worker-share-card"
                >
                  <div class="worker-share-card-head">
                    <span class="worker-share-name">{{ worker.name || `نیروی ${Number(worker.sourceIndex + 1).toLocaleString('fa-IR')}` }}</span>
                    <small>سهم پایه و درصد این نیرو</small>
                  </div>
                  <div class="worker-share-controls modern-worker-share-controls">
                    <div class="worker-share-control amount-control">
                      <input
                        :value="getReleaseWorkerShareAmountInput(worker.sourceIndex)"
                        type="number"
                        min="0"
                        step="1"
                        @input="setReleaseWorkerShareAmount(worker.sourceIndex, $event.target.value)"
                      />
                      <small>هزار تومان</small>
                    </div>
                    <div class="worker-share-control">
                      <input
                        :value="worker.worker_share_percent ?? 0"
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        @input="setReleaseWorkerSharePercent(worker.sourceIndex, $event.target.value)"
                      />
                      <small>٪</small>
                    </div>
                  </div>
                </article>
              </div>
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
                </select>
              </label>
              <div class="payment-method-preview">
                <strong>ثبت پرداخت</strong>
                <p>پرداخت فعلی با روش <span>{{ paymentMethodLabel(releaseForm.paymentMethod) }}</span> نهایی می‌شود.</p>
              </div>
              <div v-if="releaseForm.paymentMethod === 'cheque'" class="cheque-inline-card detail-field-wide">
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
            <p class="invoice-modal-subtitle">فاکتور سفارش را به‌صورت PDF ببینید و در صورت نیاز دانلود کنید.</p>
          </div>
          <button class="close-btn" @click="closeInvoicePreviewModal">✕</button>
        </header>
        <div class="invoice-modal-body">
          <div class="invoice-modal-actions">
            <button type="button" class="secondary-btn" :disabled="invoiceGenerating" @click="refreshInvoicePreview">
              {{ invoiceGenerating ? 'در حال ساخت...' : 'بروزرسانی فاکتور' }}
            </button>
            <button type="button" class="secondary-btn" :disabled="!invoicePdfUrl || invoiceGenerating" @click="downloadInvoicePdf">
              دانلود PDF
            </button>
          </div>
          <div v-if="invoiceGenerating" class="invoice-preview-loading">
            <BaseSpinner size="56px" color="#1d4ed8" ball-color="#60a5fa" label="در حال ساخت فایل PDF فاکتور..." />
          </div>
          <div v-else-if="invoicePdfUrl" class="invoice-preview-frame-wrap">
            <iframe :src="invoicePreviewUrl" title="invoice-pdf-preview" class="invoice-preview-frame"></iframe>
          </div>
          <div v-else class="invoice-preview-empty">
            {{ invoiceErrorMessage || 'فاکتور هنوز ساخته نشده است.' }}
          </div>
        </div>
      </section>
    </div>
    <div class="invoice-print-stage">
      <div ref="invoiceTemplateRef" class="invoice-template">
        <div class="invoice-sheet">
          <header class="invoice-sheet-head">
            <div>
              <strong>فاکتور ترخیص خودرو</strong>
              <span>شماره سفارش: #{{ Number(releaseCandidate?.id || 0).toLocaleString('fa-IR') }}</span>
            </div>
            <div class="invoice-sheet-meta">
              <span>تاریخ صدور: {{ invoiceIssuedAt }}</span>
              <span>روش پرداخت: {{ paymentMethodLabel(releaseForm.paymentMethod) }}</span>
            </div>
          </header>
          <section class="invoice-sheet-grid">
            <article>
              <span>مشتری</span>
              <strong>{{ releaseCandidate?.driverName || releaseCandidate?.driver_name || '-' }}</strong>
            </article>
            <article>
              <span>شماره تماس</span>
              <strong>{{ releaseCandidate?.driverPhone || releaseCandidate?.driver_phone || '-' }}</strong>
            </article>
            <article>
              <span>خودرو</span>
              <strong>{{ releaseCandidate?.model || releaseCandidate?.car_model || '-' }}</strong>
            </article>
            <article>
              <span>پلاک</span>
              <strong>{{ releaseCandidate?.plateDisplay || releaseCandidate?.plate_number || 'قطعه‌شویی' }}</strong>
            </article>
          </section>

          <section class="invoice-sheet-section">
            <div class="invoice-section-head">
              <strong>خدمات</strong>
            </div>
            <table class="invoice-table">
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
                  <td>{{ Number(line.quantity || 0).toLocaleString('fa-IR') }}</td>
                  <td>{{ formatMoney(line.line_total) }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section class="invoice-sheet-section" v-if="invoiceProductLines.length">
            <div class="invoice-section-head">
              <strong>محصولات جانبی</strong>
            </div>
            <table class="invoice-table">
              <thead>
                <tr>
                  <th>عنوان</th>
                  <th>تعداد</th>
                  <th>مبلغ</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="product in invoiceProductLines" :key="`invoice-product-${product.id}`">
                  <td>{{ product.name }}</td>
                  <td>{{ Number(product.quantity || 0).toLocaleString('fa-IR') }}</td>
                  <td>{{ formatMoney(product.total) }}</td>
                </tr>
              </tbody>
            </table>
          </section>

          <section class="invoice-sheet-section invoice-total-section">
            <div class="invoice-totals">
              <p><span>جمع خدمات</span><strong>{{ formatMoney(releaseSummary.servicesTotal) }}</strong></p>
              <p><span>جمع محصولات</span><strong>{{ formatMoney(releaseSummary.productsTotal) }}</strong></p>
              <p><span>تخفیف مشتری</span><strong>{{ formatMoney(releaseSummary.discountAmount) }}</strong></p>
              <p><span>انعام</span><strong>{{ formatMoney(releaseSummary.tipAmount) }}</strong></p>
              <p class="invoice-grand-total"><span>مبلغ نهایی</span><strong>{{ formatMoney(releaseSummary.finalTotal) }}</strong></p>
            </div>
          </section>

          <section class="invoice-sheet-section">
            <div class="invoice-section-head">
              <strong>سهم پرسنل</strong>
            </div>
            <div class="invoice-workers">
              <p v-for="(worker, index) in releaseSummary.workerShares" :key="`invoice-worker-${index}`">
                <span>{{ worker.name }} ({{ Number(worker.percent || 0).toLocaleString('fa-IR') }}٪)</span>
                <strong>{{ formatMoney(worker.amount) }}</strong>
              </p>
              <p>
                <span>سهم کارواش</span>
                <strong>{{ formatMoney(releaseSummary.carwashShare) }}</strong>
              </p>
            </div>
          </section>

          <footer class="invoice-sheet-footer">
            <p v-if="releaseForm.creditDueDate && ['credit', 'cheque'].includes(releaseForm.paymentMethod)">
              سررسید پرداخت: {{ releaseForm.creditDueDate }}
            </p>
            <p v-if="releaseForm.paymentMethod === 'cheque' && chequeDetailsSummary !== 'جزئیات ثبت نشده'">
              {{ chequeDetailsSummary }}
            </p>
            <p v-if="releaseForm.receiptFooterNote">{{ releaseForm.receiptFooterNote }}</p>
          </footer>
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
import VehicleDetailsModal from '../../components/vehicles/VehicleDetailsModal.vue'
import { useVehicleStore } from '../../store/vehicle.store'
import api from '../../services/api'
import { formatThousandsToman } from '../../utils/money'
import { resolveApiErrorMessage } from '../../utils/apiError'

const search = ref('')
const activeFilter = ref('all')
const showVehicleModal = ref(false)
const showVehicleDetailsModal = ref(false)
const showReleaseModal = ref(false)
const showChequeDetailsModal = ref(false)
const showInvoicePreviewModal = ref(false)
const releaseCheckoutLoading = ref(false)
const releaseSubmitting = ref(false)
const invoiceGenerating = ref(false)
const invoicePdfUrl = ref('')
const invoiceErrorMessage = ref('')
const modalStep = ref(1)
const vehicleDraft = ref(null)
const releaseCandidate = ref(null)
const invoiceTemplateRef = ref(null)
const releasePaymentMethods = ['pos', 'cash', 'transfer', 'cheque', 'credit']
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
  paymentMethod: 'cash',
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
    alert('بارگذاری جزئیات خودرو ناموفق بود.')
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
  manual: 'دستی'
}[value] || 'نامشخص')
const customerScorePercent = (score) => {
  const normalized = Math.max(0, Math.min(5, Number(score || 0)))
  return (normalized / 5) * 100
}
const formatCustomerScore = (score) => `${Number(score || 0).toLocaleString('fa-IR')} / ۵`
const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (d) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
  .replace(/\D/g, '')
const splitPlate = (rawPlate) => String(rawPlate || '').trim().split(/\s+/).filter(Boolean)
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
  return [
    source.plate_left,
    source.plate_letter,
    source.plate_mid,
    source.plate_right
  ].map((value) => String(value || '').trim()).filter(Boolean).join(' ')
})
const mapVehicleToDraft = (source = {}) => ({
  id: source.id,
  plate: source.plate_number,
  plate_left: source.plate_left,
  plate_letter: source.plate_letter,
  plate_mid: source.plate_mid,
  plate_right: source.plate_right,
  model: source.car_model,
  color: source.car_color,
  driver: source.driver_name,
  mobile: source.driver_phone,
  note: source.notes,
  isPieceWash: Boolean(source.is_piece_wash),
  pieceDetails: source.piece_details || '',
  pieceWashPrice: Number(source.job?.services_total || 0),
  isAnonymous: source.plate_number === '1111' && source.car_model === '1111' && source.car_color === '1111',
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
const assignedWorkersLabel = (job) => {
  if (!job) return 'تخصیص نشده'
  const names = Array.isArray(job.assigned_workers_names)
    ? job.assigned_workers_names.filter((item) => String(item || '').trim().length > 0)
    : []
  if (names.length) return names.join('، ')
  return job.assigned_worker_name || 'تخصیص نشده'
}
const hasCompletedStepOneData = (source = {}) => {
  const isPieceWash = Boolean(source.is_piece_wash)
  const isAnonymous = source.plate_number === '1111' && source.car_model === '1111' && source.car_color === '1111'
  const hasPhone = normalizeDigits(source.driver_phone).length > 0
  if (isPieceWash) {
    return String(source.driver_name || '').trim().length > 0 && hasPhone
  }
  if (isAnonymous) {
    return hasPhone
  }
  const plateParts = splitPlate(source.plate_number)
  const left = String(source.plate_left || plateParts[0] || '').trim()
  const letter = String(source.plate_letter || plateParts[1] || '').trim()
  const mid = String(source.plate_mid || plateParts[2] || '').trim()
  const right = String(source.plate_right || plateParts[3] || '').trim()
  const hasPlate = left.length === 2 && letter.length === 1 && mid.length === 3 && right.length === 2
  const hasModel = String(source.car_model || '').trim().length > 0
  const hasColor = String(source.car_color || '').trim().length > 0
  return hasPlate && hasModel && hasColor && hasPhone
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
  showChequeDetailsModal.value = false
  closeInvoicePreviewModal()
  releaseCandidate.value = null
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
    paymentMethod: defaultReleasePaymentMethod.value,
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
  if (Number(releaseForm.value.chequeAmount || 0) <= 0) {
    releaseForm.value.chequeAmount = Math.max(1, Math.round(Number(releaseSummary.value.finalTotal || 0) / 1000))
  }
  showChequeDetailsModal.value = true
}
const closeChequeDetailsModal = () => {
  showChequeDetailsModal.value = false
}
const normalizeReleaseAssignedWorkers = (workers) => {
  const items = Array.isArray(workers) ? workers.filter((item) => item.id > 0 && item.name.length > 0) : []
  const fallbackPercents = defaultWorkerSharePercents(items.length)
  return items.map((item, index) => ({
    ...item,
    worker_share_percent: Number(item.worker_share_percent ?? fallbackPercents[index] ?? 0),
    isSelected: true
  }))
}
const extractReleaseAssignedWorkers = (payload) => {
  const assignedWorkers = Array.isArray(payload?.job?.assigned_workers)
    ? payload.job.assigned_workers
      .map((item) => ({
        id: Number(item?.id || 0),
        name: String(item?.name || '').trim(),
        tip_share_percent: Number(item?.tip_share_percent || 0),
        worker_share_percent: Number(item?.worker_share_percent || 0)
      }))
      .filter((item) => item.id > 0 && item.name.length > 0)
    : []
  if (assignedWorkers.length) return assignedWorkers

  const snapshotWorkers = Array.isArray(payload?.job?.assigned_workers_snapshot)
    ? payload.job.assigned_workers_snapshot
      .map((item, index) => ({
        id: Number(item?.id || index + 1),
        name: String(item?.name || '').trim(),
        tip_share_percent: Number(item?.tip_share_percent || 0),
        worker_share_percent: Number(item?.worker_share_percent || 0)
      }))
      .filter((item) => item.id > 0 && item.name.length > 0)
    : []
  if (snapshotWorkers.length) return snapshotWorkers

  return Array.isArray(payload?.job?.assigned_workers_names)
    ? payload.job.assigned_workers_names
      .filter((item) => String(item || '').trim().length > 0)
      .map((name, index) => ({
        id: index + 1,
        name: String(name || '').trim(),
        tip_share_percent: 0,
        worker_share_percent: 0
      }))
    : []
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
      .filter((worker) => Number(worker.id || 0) > 0 && String(worker.name || '').trim().length > 0)
    : []
))
const syncBonusPenaltyAdjustments = () => {
  const workers = bonusPenaltyWorkers.value
  const current = Array.isArray(releaseForm.value.bonusPenaltyAdjustments) ? releaseForm.value.bonusPenaltyAdjustments : []
  const currentMap = new Map(current.map((item) => [Number(item.worker_id || 0), item]))
  releaseForm.value.bonusPenaltyAdjustments = workers.map((worker) => {
    const existing = currentMap.get(Number(worker.id || 0))
    return {
      worker_id: Number(worker.id || 0),
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
        is_completed: Boolean(line.is_completed)
      }))
      : []
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
      assignedWorkers: normalizeReleaseAssignedWorkers(extractReleaseAssignedWorkers(data)),
      workerShareAmount: Number(data?.job?.worker_share_amount || 0),
      customerScore: Math.max(0, Number(data?.vehicle?.customer_score || releaseCandidate.value?.customerScore || 0)),
      discountPercentPerHalfStar,
      paymentMethod: defaultReleasePaymentMethod.value,
      chequeNumber: '',
      chequeSerialNumber: '',
      chequeSayadiNumber: '',
      chequeBank: '',
      chequeShaba: '',
      chequeAmount: 0,
      creditDueDate: '',
      receiptFooterNote: settingsResponse?.data?.receipt_footer_note || '',
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
    syncBonusPenaltyAdjustments()
  } catch (error) {
    console.error('openReleaseModal error:', error?.response?.data || error)
    alert(apiErrorText(error, 'بارگذاری اطلاعات ترخیص ناموفق بود.'))
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
        return quantity > 0
          ? {
            id: product.id,
            name: product.name,
            quantity,
            total: quantity * Number(product.sale_price || 0)
          }
          : null
      })
      .filter(Boolean)
    : []
))
const invoiceIssuedAt = computed(() => new Intl.DateTimeFormat('fa-IR', {
  dateStyle: 'medium',
  timeStyle: 'short'
}).format(new Date()))
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
const filteredReleaseProducts = computed(() => {
  const items = releaseForm.value.availableProducts || []
  const query = (releaseForm.value.productSearch || '').trim()
  if (!query) return items
  return items.filter((item) => `${item.name || ''} ${item.sku || ''}`.includes(query))
})
const addServiceFromSystem = () => {
  const serviceId = Number(releaseForm.value.selectedServiceToAdd || 0)
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
  const discountAmount = Number((discountBase * customerDiscountPercent / 100).toFixed(2))
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
  if (releaseForm.value.paymentMethod !== 'cheque') return 'جزئیات ثبت نشده'
  const parts = []
  if (releaseForm.value.chequeSerialNumber) parts.push(`سریال ${releaseForm.value.chequeSerialNumber}`)
  if (releaseForm.value.chequeBank) parts.push(releaseForm.value.chequeBank)
  if (releaseForm.value.creditDueDate) parts.push(`وصول ${releaseForm.value.creditDueDate}`)
  if (Number(releaseForm.value.chequeAmount || 0) > 0) parts.push(`${Number(releaseForm.value.chequeAmount || 0).toLocaleString('fa-IR')} هزار`)
  return parts.length ? parts.join(' | ') : 'جزئیات ثبت نشده'
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
        margin: [8, 8, 8, 8],
        filename: `invoice-${releaseCandidate.value?.id || 'carwash'}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
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
  anchor.download = `invoice-${releaseCandidate.value?.id || 'carwash'}.pdf`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}
const confirmReleaseVehicle = async () => {
  if (!releaseCandidate.value?.id) return
  if (releaseForm.value.assignedWorkers.length && !selectedAssignedWorkers.value.length) {
    alert('حداقل یک نیرو را برای این تسویه انتخاب کنید.')
    return
  }
  if (releaseForm.value.paymentMethod === 'cheque') {
    if (!releaseForm.value.creditDueDate || !releaseForm.value.chequeSerialNumber || !releaseForm.value.chequeSayadiNumber || !releaseForm.value.chequeBank || !releaseForm.value.chequeShaba || Number(releaseForm.value.chequeAmount || 0) <= 0) {
      alert('همه جزئیات چک را کامل کنید.')
      showChequeDetailsModal.value = true
      return
    }
  }
  if (hasReleaseBonusOrPenalty.value && !String(releaseForm.value.bonusPenaltyNote || '').trim()) {
    alert('توضیح پاداش یا جریمه الزامی است.')
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
      cheque_number: releaseForm.value.paymentMethod === 'cheque' ? (releaseForm.value.chequeSerialNumber || releaseForm.value.chequeNumber) : undefined,
      cheque_serial_number: releaseForm.value.paymentMethod === 'cheque' ? releaseForm.value.chequeSerialNumber : undefined,
      cheque_sayadi_number: releaseForm.value.paymentMethod === 'cheque' ? releaseForm.value.chequeSayadiNumber : undefined,
      cheque_bank: releaseForm.value.paymentMethod === 'cheque' ? releaseForm.value.chequeBank : undefined,
      cheque_shaba: releaseForm.value.paymentMethod === 'cheque' ? releaseForm.value.chequeShaba : undefined,
      cheque_amount: releaseForm.value.paymentMethod === 'cheque' ? Number(releaseForm.value.chequeAmount || 0) * 1000 : undefined,
      credit_due_date: ['credit', 'cheque'].includes(releaseForm.value.paymentMethod) ? parseJalaliToIso(releaseForm.value.creditDueDate) || undefined : undefined,
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
    alert(apiErrorText(error, 'ترخیص خودرو ناموفق بود.'))
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
    vehicleDraft.value = mapVehicleToDraft(savedVehicle)
    modalStep.value = 2
  } catch (error) {
    console.error('continue step one error:', error?.response?.data || error)
    alert(apiErrorText(error, 'ذخیره اطلاعات مرحله اول ناموفق بود.'))
  }
}
const buildCreateOrUpdatePayload = (payload, status) => {
  const plateRaw = (payload?.vehicle?.plate || '').trim()
  const [leftPart = '', letterPart = '', midPart = '', rightPart = ''] = plateRaw.split(/\s+/).filter(Boolean)
  const left = String(payload?.vehicle?.plateLeft || payload?.vehicle?.plate_left || leftPart || '').trim()
  const letter = String(payload?.vehicle?.plateLetter || payload?.vehicle?.plate_letter || letterPart || '').trim()
  const mid = String(payload?.vehicle?.plateMid || payload?.vehicle?.plate_mid || midPart || '').trim()
  const right = String(payload?.vehicle?.plateRight || payload?.vehicle?.plate_right || rightPart || '').trim()
  const rebuiltPlate = [left, letter, mid, right].every(Boolean)
    ? `${left} ${letter} ${mid} ${right}`
    : plateRaw
  const isAnonymous = Boolean(payload?.vehicle?.isAnonymous)
  const isPieceWash = Boolean(payload?.vehicle?.isPieceWash)

  return {
    plate_number: isPieceWash ? '' : (isAnonymous ? '1111' : rebuiltPlate),
    plate_left: isPieceWash || isAnonymous ? '' : left,
    plate_letter: isPieceWash || isAnonymous ? '' : letter,
    plate_mid: isPieceWash || isAnonymous ? '' : mid,
    plate_right: isPieceWash || isAnonymous ? '' : right,
    car_model: isPieceWash ? 'قطعه‌شویی' : (isAnonymous ? '1111' : (payload?.vehicle?.model || '').trim()),
    car_color: isPieceWash ? '-' : (isAnonymous ? '1111' : (payload?.vehicle?.color || '').trim()),
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
  const plateRaw = (payload?.plate || payload?.vehicle?.plate || '').trim()
  const params = {
    plate_number: plateRaw,
    plate_left: String(payload?.plateLeft || payload?.vehicle?.plateLeft || payload?.vehicle?.plate_left || '').trim(),
    plate_letter: String(payload?.plateLetter || payload?.vehicle?.plateLetter || payload?.vehicle?.plate_letter || '').trim(),
    plate_mid: String(payload?.plateMid || payload?.vehicle?.plateMid || payload?.vehicle?.plate_mid || '').trim(),
    plate_right: String(payload?.plateRight || payload?.vehicle?.plateRight || payload?.vehicle?.plate_right || '').trim()
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
    alert(apiErrorText(error, 'ثبت ارجاع ناموفق بود.'))
  }
}

const handleStepTwoAssign = async (payload) => {
  try {
    await saveVehicle(payload, 'ready_to_settle')
    closeVehicleModal()
  } catch (error) {
    console.error('assign step two error:', error?.response?.data || error)
    alert(apiErrorText(error, 'ثبت تخصیص ناموفق بود.'))
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
  plateTwoDigit: item.plate_left || '--',
  plateLetter: item.plate_letter || '-',
  plateThreeDigit: item.plate_mid || '---',
  plateBlue: item.plate_right || '--',
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
  { key: 'all', label: `کل (${cars.value.length})` },
  { key: 'entered', label: `در انتظار تکمیل (${counts.value.entered})` },
  { key: 'in_progress', label: `در حال انجام (${counts.value.in_progress})` },
  { key: 'released', label: `ترخیص شده (${counts.value.released})` },
  { key: 'cancelled', label: `لغو (${counts.value.cancelled})` }
])

const filteredCars = computed(() => {
  let items = cars.value
  if (activeFilter.value !== 'all') items = items.filter((item) => item.queueBucket === activeFilter.value)
  if (search.value.trim()) {
    const query = search.value.trim()
    items = items.filter((item) => [item.plateTwoDigit, item.plateLetter, item.plateThreeDigit, item.plateBlue, item.model, item.driverName, item.driverPhone].join(' ').includes(query))
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
    alert('لغو سفارش ناموفق بود.')
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
    alert('بلاک کردن پلاک ناموفق بود.')
  }
}

onMounted(() => {
  vehicleStore.fetchVehicles()
})
watch(hasOperatorModalOpen, (isOpen) => {
  if (isOpen) lockBodyScrollForModal()
  else unlockBodyScrollForModal()
}, { immediate: true })
onBeforeUnmount(() => {
  unlockBodyScrollForModal()
  revokeInvoicePdfUrl()
})
</script>

<style scoped>
.dashboard-content { min-width: 0; width: 100%; max-width: 100%; overflow-x: hidden; }
.primary-btn { height: 40px; border: none; border-radius: 12px; color: #fff; font-weight: 700; padding: 0 16px; background: linear-gradient(135deg, #0058be 0%, #57dffe 100%); cursor: pointer;margin-right: 3%; }
.filters { display: flex; gap: 10px; overflow-x: auto; overflow-y: hidden; padding-bottom: 8px; flex-wrap: nowrap; align-items: center; }
.filters > * { flex: 0 0 auto; }
.filters > .primary-btn { width: auto; margin-right: 0; }
.chip { border: none; border-radius: 999px; padding: 10px 16px; background: #e6e8ea; color: #4b5563;font-size:13px; font-weight: 500; white-space: nowrap; }
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
.plate-two, .plate-three { font-size: 24px; font-weight: 700; height: 40px; padding-top: 12px; padding-bottom: 8px; }
.plate-letter { font-size: 24px; font-weight: 700; min-width: 20px; padding-top: 2px; }
.plate-blue { min-width: 52px; background: #2563eb; color: #ffffff; border-radius: 0 7px 7px 0; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 24px; line-height: 1; padding-top: 12px; padding-bottom: 8px; }
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
.release-modal-body{flex:1;min-height:0;overflow:visible;display:grid;gap:14px;padding:16px 0 20px;background:
 radial-gradient(circle at top right, rgba(34,197,94,.08), transparent 18%),
 radial-gradient(circle at top left, rgba(14,165,233,.10), transparent 24%),
 linear-gradient(180deg,#edf7ff,#f5f9ff)}
.release-layout { padding: 0 24px; display: grid; gap: 20px; grid-template-columns: minmax(0,1.05fr) minmax(0,.95fr) minmax(0,1.08fr); background:
  radial-gradient(circle at top right, rgba(34,197,94,.10), transparent 24%),
  radial-gradient(circle at top left, rgba(14,165,233,.14), transparent 28%),
  linear-gradient(180deg,#edf7ff,#eef5ff); }
.release-col { background: rgba(255,255,255,.88); border: 1px solid rgba(191,215,255,.9); border-radius: 24px; padding: 18px; display: flex; flex-direction: column; min-height: 620px; box-shadow: 0 22px 45px -32px rgba(15,23,42,.45); backdrop-filter: blur(10px); }
.release-products-col, .release-summary-col { border-right: 1px solid rgba(191,215,255,.85); }
.release-title-inline{display:flex;justify-content:space-between;align-items:center;gap:10px}
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
.products-scroll { max-height: 520px; padding-right: 4px; }
.product-item { border: 1px solid #d4e4ff; border-radius: 18px; padding: 14px; display: flex; justify-content: space-between; align-items: center; background: linear-gradient(180deg,#ffffff,#f7fbff); }
.product-item h4 { margin: 0 0 4px; font-size: 14px; color: #111827; }
.product-item p { margin: 0; font-size: 12px; color: #64748b; }
.product-item span { font-size: 13px; color: #00687a; font-weight: 700; }
.product-item.unavailable { opacity: .55; }
.product-item p.stock-empty { color: #ba1a1a; }
.qty-controls { display: inline-flex; align-items: center; gap: 10px; border: 1px solid #d4e4ff; border-radius: 14px; padding: 6px 8px; background: #edf5ff; }
.qty-controls button { width: 28px; height: 28px; border: 1px solid #bfd7ff; border-radius: 8px; background: #fff; cursor: pointer; }
.qty-controls button:disabled { opacity: .45; cursor: not-allowed; }
.qty-controls input { width: 72px; height: 28px; border: 1px solid #bfd7ff; border-radius: 8px; text-align: center; background: #fff; }
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
.invoice-modal-actions{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap}
.invoice-preview-loading,.invoice-preview-empty{min-height:380px;border:1px dashed #bfd7ff;border-radius:18px;background:#fff;display:flex;align-items:center;justify-content:center;color:#64748b;padding:20px}
.invoice-preview-frame-wrap{min-height:0;min-width:0;border-radius:18px;overflow:auto;border:1px solid #dbe7f5;background:#fff;box-shadow:0 16px 36px rgba(15,23,42,.08);height:100%}
.invoice-preview-frame{display:block;width:100%;height:100%;min-height:0;min-width:0;border:0;background:#fff}
.invoice-print-stage{position:fixed;left:-99999px;top:0;width:794px;pointer-events:none}
.invoice-template{width:794px;max-width:794px;background:#fff;padding:0}
.invoice-sheet{direction:rtl;background:#fff;color:#0f172a;padding:28px;font-family:Tahoma,Arial,sans-serif;display:grid;gap:18px;width:100%;max-width:100%;box-sizing:border-box}
.invoice-sheet-head{display:flex;justify-content:space-between;gap:18px;padding-bottom:14px;border-bottom:2px solid #dbe7f5}
.invoice-sheet-head strong{display:block;font-size:22px}
.invoice-sheet-head span{display:block;margin-top:6px;color:#475569;font-size:13px}
.invoice-sheet-meta{display:grid;gap:8px;justify-items:end;min-width:0}
.invoice-sheet-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.invoice-sheet-grid article{border:1px solid #dbe7f5;border-radius:16px;padding:14px;background:#f8fbff;display:grid;gap:6px;min-width:0}
.invoice-sheet-grid article span{font-size:12px;color:#64748b}
.invoice-sheet-grid article strong{font-size:14px;min-width:0;overflow-wrap:anywhere}
.invoice-sheet-section{display:grid;gap:10px}
.invoice-section-head strong{font-size:15px}
.invoice-table{width:100%;max-width:100%;table-layout:fixed;border-collapse:collapse;border:1px solid #dbe7f5;border-radius:16px;overflow:hidden}
.invoice-table th,.invoice-table td{padding:12px 14px;border-bottom:1px solid #e2e8f0;text-align:right;font-size:13px;overflow-wrap:anywhere;word-break:break-word}
.invoice-table th{background:#eff6ff;color:#334155}
.invoice-table tr:last-child td{border-bottom:0}
.invoice-total-section{border:1px solid #dbe7f5;border-radius:18px;padding:14px;background:linear-gradient(180deg,#ffffff,#f8fbff)}
.invoice-totals{display:grid;gap:10px}
.invoice-totals p{margin:0;display:flex;justify-content:space-between;gap:12px;color:#334155;font-size:13px}
.invoice-grand-total{padding-top:10px;border-top:1px dashed #bfd7ff;font-size:16px;font-weight:800;color:#0f172a}
.invoice-workers{display:grid;gap:8px}
.invoice-workers p{margin:0;display:flex;justify-content:space-between;gap:12px;padding:10px 12px;border-radius:14px;background:#f8fbff;border:1px solid #dbe7f5;font-size:13px}
.invoice-sheet-footer{padding-top:10px;border-top:1px dashed #cbd5e1;display:grid;gap:6px}
.invoice-sheet-footer p{margin:0;color:#475569;font-size:12px;line-height:1.9;overflow-wrap:anywhere}
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
  .summary-stat-grid,.worker-selection-grid,.modern-worker-share-editor,.release-secondary-grid,.cheque-fields-grid { grid-template-columns: 1fr; }
  .detail-field-wide,.cheque-field-wide { grid-column: auto; }
  .release-secondary-section { margin: 14px 20px 20px; }
  .invoice-sheet-head,.invoice-sheet-grid{grid-template-columns:1fr;display:grid}
  .invoice-sheet-meta{justify-items:start}
  .invoice-totals p,.invoice-workers p{align-items:flex-start}
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
    font-size: 12px;
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
  .primary-btn { margin-right: 0; }
  .card-head,
  .release-actions,
  .selected-worker-box,
  .service-check-item,
  .product-item,
  .summary-row,
  .summary-foot-actions,
  .worker-top,
  .worker-jobs,
  .worker-share-readonly,
  .qty-controls {
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
    gap: 6px;
    padding: 4px 8px;
  }
  .plate-two, .plate-three { font-size: 15px; height: 24px; padding-top: 5px; padding-bottom: 3px; }
  .plate-letter { font-size: 15px; min-width: 12px; padding-top: 0; }
  .plate-blue { min-width: 32px; font-size: 13px; padding-top: 5px; padding-bottom: 3px; }
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
  .release-list,
  .products-scroll {
    max-height: none;
    overflow: visible;
  }
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
  .invoice-preview-loading,.invoice-preview-empty{min-height:220px}
  .invoice-modal-panel{height:calc(100vh - 16px)}
  .invoice-modal-actions{flex-direction:column}
  .invoice-totals p,.invoice-workers p{flex-direction:column}
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
  .car-info h3 {
    font-size: 12px;
  }
  .car-info p {
    font-size: 10px;
  }
  .chip {
    padding: 7px 10px;
    font-size: 11px;
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
  .release-list,
  .products-scroll {
    max-height: none;
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
}
</style>
