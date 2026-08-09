<template>
  <AppShell
    title="مدیریت خودروها"
    subtitle="پذیرش، تخصیص و ترخیص خودروها"
    :hide-page-header="true"
    :show-search="true"
    search-placeholder="جستجوی پلاک یا نام..."
    :search-query="search"
    :search-active="hasPlateFilter"
    @update:search-query="search = $event"
  >
    <template #search-extra>
      <div class="plate-search-bar">
        <select v-model="plateFilter.plateType" class="plate-type-inline" aria-label="نوع وسیله">
          <option value="">همه</option>
          <option value="car">خودرو</option>
          <option value="motorcycle">موتور</option>
        </select>
        <PlateEditor
          class="plate-search-editor"
          dense
          :plate-left="plateFilter.plateLeft"
          :plate-letter="plateFilter.plateLetter"
          :plate-mid="plateFilter.plateMid"
          :plate-right="plateFilter.plateRight"
          :plate-type="plateFilter.plateType || 'car'"
          :show-type-switch="false"
          :show-anonymous-toggle="false"
          :show-piece-wash-toggle="false"
          @update:plateLeft="plateFilter.plateLeft = $event"
          @update:plateLetter="plateFilter.plateLetter = $event"
          @update:plateMid="plateFilter.plateMid = $event"
          @update:plateRight="plateFilter.plateRight = $event"
          @update:plateType="plateFilter.plateType = $event"
        />
        <button
          type="button"
          class="plate-clear-btn"
          :disabled="!hasPlateFilter"
          aria-label="پاک کردن پلاک"
          @click="clearPlateFilter"
        >
          ✕
        </button>
      </div>
    </template>
    <div class="dashboard-content">
        <div class="vehicle-toolbar">
          <button class="primary-btn" @click="openVehicleModal">ثبت خودروی جدید</button>
          <div class="date-range-chips" aria-label="فیلتر بازه خودروها">
            <button
              v-for="item in datePresetItems"
              :key="item.key"
              type="button"
              class="date-chip"
              :class="{ active: dateRangeMode === item.key }"
              @click="selectDatePreset(item.key)"
            >
              {{ item.label }}
            </button>
            <button
              type="button"
              class="date-chip custom-range-chip"
              :class="{ active: dateRangeMode === 'custom' }"
              @click="openDateRangeModal"
            >
              بازه تاریخی
            </button>
          </div>
          <span class="active-range-label">{{ activeDateRangeLabel }}</span>
        </div>
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
              <div class="card-head-badges">
                <span v-if="car.isPlateBlocked" class="blocked-chip">بلاک شده</span>
                <span class="time" :style="{ backgroundColor: car.badgeBg, color: car.badgeText }">{{ car.time }}</span>
              </div>
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
                <strong>{{ Number(car.customerLoyaltyDiscountPercent || 0).toLocaleString('fa-IR') }}٪ تخفیف</strong>
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

  <div v-if="showDateRangeModal" class="modal-overlay date-range-overlay" @click.self="closeDateRangeModal">
    <section class="modal-panel date-range-panel">
      <header class="modal-head">
        <div>
          <p class="modal-step">بازه تاریخی</p>
          <h2>انتخاب تاریخ خودروها</h2>
        </div>
        <button class="close-btn" type="button" @click="closeDateRangeModal">✕</button>
      </header>
      <div class="date-range-modal-body">
        <label class="date-range-field">
          <span>شروع بازه</span>
          <BaseDatePicker v-model="dateRangeDraft.startJalali" placeholder="1405/01/01" :clearable="false" />
        </label>
        <label class="date-range-field">
          <span>پایان بازه</span>
          <BaseDatePicker v-model="dateRangeDraft.endJalali" placeholder="1405/01/30" :clearable="false" />
        </label>
      </div>
      <footer class="date-range-actions">
        <button type="button" class="secondary-btn" @click="closeDateRangeModal">انصراف</button>
        <button type="button" class="primary-btn" @click="applyCustomDateRange">اعمال بازه</button>
      </footer>
    </section>
  </div>

  <div v-if="showVehicleModal" class="modal-overlay" @click.self="closeVehicleModal">
      <section class="modal-panel" :class="{ 'step-one-modal-panel': modalStep === 1, 'step-two-modal-panel': modalStep === 2 }">
        <div v-if="stepTransitionLoading || stepSubmitting" class="step-transition-overlay">
          <BaseSpinner size="52px" color="#1d4ed8" ball-color="#60a5fa" label="در حال پردازش..." />
        </div>
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
              :submitting="stepSubmitting"
              @continue="handleStepOneContinue"
              @refer="handleStepOneRefer"
            />
          </div>
        </template>

        <VehicleEntryStepTwo
          v-else
          :vehicle-info="vehicleDraft"
          :submitting="stepSubmitting"
          :submit-label="stepTwoSubmitLabel"
          @back="handleStepTwoBack"
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
      @unblock-plate="unblockSelectedVehiclePlate"
      @edit-vehicle="editSelectedVehicleVisit"
    />
    <div v-if="showPlateEditModal" class="modal-overlay plate-edit-overlay" @click.self="closePlateEditModal">
      <section class="modal-panel plate-edit-panel">
        <header class="modal-head plate-edit-head">
          <div>
            <p class="modal-step">ویرایش پلاک</p>
            <h2>اصلاح پلاک خودرو</h2>
          </div>
          <button class="close-btn" type="button" :disabled="plateEditSubmitting" @click="closePlateEditModal">✕</button>
        </header>
        <div class="plate-edit-body">
          <PlateEditor
            v-model:plate-left="plateEditForm.plateLeft"
            v-model:plate-letter="plateEditForm.plateLetter"
            v-model:plate-mid="plateEditForm.plateMid"
            v-model:plate-right="plateEditForm.plateRight"
            v-model:plate-type="plateEditForm.plateType"
            :disabled="plateEditSubmitting"
          />
          <div class="plate-edit-preview">
            <span>نمای نهایی</span>
            <PlateBadge
              :plate-number="plateEditPreview"
              :plate-left="plateEditForm.plateLeft"
              :plate-letter="plateEditForm.plateLetter"
              :plate-mid="plateEditForm.plateMid"
              :plate-right="plateEditForm.plateRight"
              :plate-type="plateEditForm.plateType"
            />
          </div>
        </div>
        <footer class="plate-edit-actions">
          <button type="button" class="secondary-btn" :disabled="plateEditSubmitting" @click="closePlateEditModal">انصراف</button>
          <button type="button" class="primary-btn plate-edit-submit" :disabled="plateEditSubmitting" @click="submitPlateEdit">
            {{ plateEditSubmitting ? 'در حال ثبت...' : 'ثبت پلاک' }}
          </button>
        </footer>
      </section>
    </div>
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
                  <span class="service-bubble-name">{{ service.name }}</span>
                  <span class="service-bubble-price">{{ formatMoney(service.base_price) }}</span>
                </button>
              </div>

              <p v-if="!releaseForm.availableServicesToAdd.length" class="empty">خدمتی برای انتخاب وجود ندارد.</p>

              <footer class="service-picker-foot">
                <button type="button" class="secondary-foot-btn" @click="closeReleaseServicePicker">انصراف</button>
                <button type="button" class="primary-btn" @click="confirmReleaseServicePicker">ثبت خدمات</button>
              </footer>
            </section>
          </div>
          <div v-if="showReleaseWorkerEditor" class="service-picker-overlay" role="dialog" aria-modal="true">
            <section class="service-picker-panel worker-editor-panel">
              <header class="service-picker-head worker-editor-head">
                <div>
                  <h4>ویرایش پرسنل ترخیص</h4>
                  <p>{{ tempReleaseWorkerRows.filter((worker) => worker.isSelected).length.toLocaleString('fa-IR') }} نفر فعال در این تسویه</p>
                </div>
                <button type="button" class="icon-btn" aria-label="بستن" @click="closeReleaseWorkerEditor">
                  ✕
                </button>
              </header>

              <div class="worker-editor-summary">
                <article>
                  <span>جمع سهم قابل تقسیم</span>
                  <strong>{{ formatMoney(releaseSummary.workerShareBase) }}</strong>
                </article>
                <article>
                  <span>جمع درصد فعال</span>
                  <strong>{{ Number(tempReleaseWorkerPercentTotal).toLocaleString('fa-IR') }}٪</strong>
                </article>
              </div>

              <label v-if="tempReleaseWorkerRows.length" class="worker-editor-search">
                <span>جستجوی پرسنل</span>
                <input v-model="releaseWorkerSearch" type="text" placeholder="نام نیرو را بنویسید..." />
              </label>

              <div v-if="filteredTempReleaseWorkerRows.length" class="worker-editor-grid">
                <article
                  v-for="worker in filteredTempReleaseWorkerRows"
                  :key="`release-worker-editor-${worker.id || worker.sourceIndex}`"
                  class="worker-editor-card"
                  :class="{ selected: worker.isSelected }"
                >
                  <button type="button" class="worker-editor-toggle" @click="toggleTempReleaseWorker(worker.sourceIndex)">
                    <span>{{ worker.isSelected ? '✓' : '+' }}</span>
                    <strong>{{ worker.name }}</strong>
                    <small>{{ worker.isSelected ? 'در تسویه فعال است' : 'افزودن به تسویه' }}</small>
                  </button>
                  <label class="worker-percent-field">
                    <span>درصد سهم</span>
                    <input
                      :value="Math.round(Number(worker.worker_share_percent || 0))"
                      type="number"
                      inputmode="numeric"
                      min="0"
                      max="100"
                      :disabled="!worker.isSelected"
                      @input="setTempReleaseWorkerShare(worker.sourceIndex, $event.target.value)"
                    />
                    <small>{{ formatMoney(tempReleaseWorkerShareAmount(worker)) }}</small>
                  </label>
                </article>
              </div>
              <p v-else class="empty">{{ tempReleaseWorkerRows.length ? 'نیرویی با این جستجو پیدا نشد.' : 'نیرویی برای انتخاب پیدا نشد.' }}</p>

              <footer class="service-picker-foot worker-editor-foot">
                <button type="button" class="secondary-foot-btn" @click="closeReleaseWorkerEditor">انصراف</button>
                <button type="button" class="secondary-foot-btn" @click="equalizeTempReleaseWorkers">تقسیم مساوی</button>
                <button type="button" class="primary-btn" @click="confirmReleaseWorkerEditor">ثبت پرسنل</button>
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
                <div class="summary-stat-value">
                  <strong>{{ formatMoney(releaseSummary.discountAmount) }}</strong>
                  <small>{{ formatPercent(releaseSummary.customerDiscountPercent) }}</small>
                </div>
              </article>
              <article class="summary-stat-card accent-card">
                <span>انعام</span>
                <strong>{{ formatMoney(releaseSummary.tipAmount) }}</strong>
              </article>
              <article class="summary-stat-card">
                <span>مالیات</span>
                <div class="summary-stat-value">
                  <strong>{{ formatMoney(releaseSummary.taxAmount) }}</strong>
                  <small>{{ formatPercent(releaseSummary.taxPercent) }}</small>
                </div>
              </article>
            </div>
            <div class="summary-input-grid">
              <label class="tip-input-row modern-input-row">
                <span>انعام (تومان)</span>
                <input :value="moneyInputValue(releaseForm.tipAmount)" type="text" inputmode="numeric" @input="releaseForm.tipAmount = parseMoneyInput($event.target.value)" />
              </label>
              <label class="tip-input-row modern-input-row">
                <span>تخفیف دستی (تومان)</span>
                <input :value="moneyInputValue(releaseForm.manualDiscountTotal)" type="text" inputmode="numeric" @input="releaseForm.manualDiscountTotal = parseMoneyInput($event.target.value)" />
              </label>
            </div>
            <div class="worker-selection-panel">
              <div class="worker-selection-head">
                <div>
                  <h4>پرسنل</h4>
                  <p>پرسنل این تسویه را مثل خدمات ویرایش کنید؛ نیروها و درصد سهم از همین بخش نهایی می‌شوند.</p>
                </div>
                <div class="worker-selection-actions">
                  <button
                    v-if="releaseForm.assignedWorkers.length > 1 && selectedAssignedWorkers.length !== releaseForm.assignedWorkers.length"
                    type="button"
                    class="secondary-btn small-btn"
                    @click="activateAllReleaseWorkers"
                  >
                    انتخاب همه
                  </button>
                  <button type="button" class="secondary-btn small-btn" @click="openReleaseWorkerEditor">
                    ویرایش
                  </button>
                </div>
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
              <p v-else class="empty-row">برای این سفارش نیرویی ثبت نشده است. از گزینه ویرایش، پرسنل را اضافه کنید.</p>
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
            <p class="summary-final"><span>مبلغ نهایی</span><strong>{{ formatMoney(releaseSummary.finalTotal) }}</strong></p>
            
            <div class="release-actions">
              <button type="button" class="back-btn" @click="closeReleaseModal">انصراف</button>
              <button type="button" class="confirm-release-btn" :disabled="releaseSubmitting" @click="confirmReleaseVehicle">
                {{ releaseSubmitting ? 'در حال ثبت...' : (jobEditMode ? 'ثبت تغییرات' : 'تایید و ترخیص خودرو') }}
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
            <div class="release-secondary-grid release-secondary-grid-accordion">
              <section class="release-mobile-section">
                <button
                  v-if="isReleaseMobile"
                  type="button"
                  class="release-mobile-toggle"
                  @click="toggleReleaseSection('payment')"
                >
                  <span>پرداخت</span>
                  <small>{{ paymentMethodLabel(releaseForm.paymentMethod) }}</small>
                  <strong>{{ isReleaseSectionOpen('payment') ? '▾' : '▸' }}</strong>
                </button>
                <div v-show="isReleaseSectionOpen('payment')" class="release-mobile-content">
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
                      <span>مبلغ نقدی (تومان)</span>
                      <input :value="moneyInputValue(releaseForm.manualCashAmount)" type="text" inputmode="numeric" @input="releaseForm.manualCashAmount = parseMoneyInput($event.target.value)" />
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
                      <span>مبلغ بخش دوم (تومان)</span>
                      <input :value="moneyInputValue(releaseForm.manualSecondaryAmount)" type="text" inputmode="numeric" @input="releaseForm.manualSecondaryAmount = parseMoneyInput($event.target.value)" />
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
                </div>
              </section>

              <section class="release-mobile-section">
                <button
                  v-if="isReleaseMobile"
                  type="button"
                  class="release-mobile-toggle"
                  @click="toggleReleaseSection('bonus')"
                >
                  <span>پاداش / جریمه</span>
                  <small>ثبت برای پرسنل سفارش</small>
                  <strong>{{ isReleaseSectionOpen('bonus') ? '▾' : '▸' }}</strong>
                </button>
                <div v-show="isReleaseSectionOpen('bonus')" class="release-mobile-content">
                  <div class="detail-field detail-field-wide bonus-penalty-table">
                    <div class="bonus-penalty-table-head">
                      <span>نیرو برای پاداش/جریمه</span>
                      <small>برای هر نیروی این سفارش، مبلغ جدا ثبت کنید.</small>
                    </div>
                    <div v-if="releaseForm.bonusPenaltyAdjustments.length" class="bonus-penalty-list">
                      <div v-for="(adjustment, index) in releaseForm.bonusPenaltyAdjustments" :key="`adjustment-${adjustment.worker_id || index}`" class="bonus-penalty-item">
                        <strong>{{ adjustment.worker_name || `نیروی ${Number(index + 1).toLocaleString('fa-IR')}` }}</strong>
                        <label class="tip-input-row">
                          <span>پاداش (تومان)</span>
                          <input :value="moneyInputValue(adjustment.bonus)" type="text" inputmode="numeric" @input="adjustment.bonus = parseMoneyInput($event.target.value)" />
                        </label>
                        <label class="tip-input-row">
                          <span>جریمه (تومان)</span>
                          <input :value="moneyInputValue(adjustment.penalty)" type="text" inputmode="numeric" @input="adjustment.penalty = parseMoneyInput($event.target.value)" />
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

              <section class="release-mobile-section">
                <button
                  v-if="isReleaseMobile"
                  type="button"
                  class="release-mobile-toggle"
                  @click="toggleReleaseSection('sms')"
                >
                  <span>SMS</span>
                  <small>ارسال پیامک ترخیص</small>
                  <strong>{{ isReleaseSectionOpen('sms') ? '▾' : '▸' }}</strong>
                </button>
                <div v-show="isReleaseSectionOpen('sms')" class="release-mobile-content">
                  <label class="release-sms-check detail-field detail-field-wide" :class="{ disabled: !releaseForm.smsAutoSendEnabled }">
                    <input v-model="releaseForm.smsNotificationsEnabled" type="checkbox" :disabled="!releaseForm.smsAutoSendEnabled" />
                    <span>
                      <strong>SMS</strong>
                      <small>{{ releaseForm.smsAutoSendEnabled ? 'ارسال پیامک ترخیص برای همین سفارش' : 'ارسال خودکار پیامک در تنظیمات غیرفعال است' }}</small>
                    </span>
                  </label>
                </div>
              </section>
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
            <strong>{{ formatMoney(Number(releaseForm.chequeAmount || 0) || releaseSummary.finalTotal) }}</strong>
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
              <span>مبلغ (تومان)</span>
              <input :value="moneyInputValue(releaseForm.chequeAmount)" type="text" inputmode="numeric" @input="releaseForm.chequeAmount = parseMoneyInput($event.target.value)" />
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
                <strong>{{ option.label }}</strong>
                <span>{{ option.hint }}</span>
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
            <div class="invoice-modal-actions">
              <button type="button" class="secondary-btn" :disabled="invoiceGenerating" @click="downloadInvoicePdf">
                {{ invoiceGenerating ? 'در حال ساخت PDF...' : 'دانلود PDF' }}
              </button>
              <button type="button" class="secondary-btn" :disabled="invoiceGenerating" @click="printInvoiceHtml">
                {{ invoiceGenerating ? 'در حال چاپ...' : 'چاپ' }}
              </button>
            </div>
          </div>
          <div class="invoice-preview-frame-wrap">
            <div class="invoice-live-preview" :style="invoiceStageStyle">
              <div ref="invoiceTemplateRef" class="invoice-template" :style="invoiceTemplateStyle">
                <div class="invoice-sheet" :class="invoiceSheetClass" :style="invoiceSheetStyle">
          <template v-if="invoiceIsThermal">
            <header class="thermal-sheet-head">
              <strong>{{ invoiceCarwashTitle }}</strong>
              <small v-if="invoiceReceiptHeaderNote" class="receipt-custom-note">{{ invoiceReceiptHeaderNote }}</small>
            </header>

            <section class="thermal-info-grid">
              <p><span>شماره پذیرش:</span><strong>{{ invoiceAdmissionNumber }}</strong></p>
              <p><span>تاریخ:</span><strong>{{ invoiceIssuedAt }}</strong></p>
              <p><span>تعداد مراجعه:</span><strong>{{ Number(releaseForm.customerLoyaltyVisitCount || 0).toLocaleString('fa-IR') }}</strong></p>
              <p><span>امتیاز:</span><strong>{{ invoiceCustomerScoreLabel }}</strong></p>
              <p><span>تیپ نرخنامه:</span><strong>{{ invoiceTariffTypeNumber }}</strong></p>
              <p><span>مدل خودرو:</span><strong>{{ invoiceVehicleTitle }}</strong></p>
              <p><span>پلاک:</span><strong>{{ invoicePlateLabel }}</strong></p>
              <p><span>مشتری:</span><strong>{{ invoiceCustomerDisplayName }}</strong></p>
            </section>

            <section class="thermal-items-section">
              <table class="thermal-items-table">
                <thead>
                  <tr>
                    <th>شرح خدمات / کالا</th>
                    <th>مبلغ<br />(تومان)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(line, lineIndex) in invoiceServiceLines" :key="`thermal-service-${line.id || lineIndex}`">
                    <td>{{ Number(lineIndex + 1).toLocaleString('fa-IR') }}. {{ line.service_name }}</td>
                    <td>{{ moneyInputValue(invoiceServiceLineListTotal(line)) }}</td>
                  </tr>
                  <tr v-for="(product, productIndex) in invoiceProductLines" :key="`thermal-product-${product.id}`">
                    <td>{{ Number(invoiceServiceLines.length + productIndex + 1).toLocaleString('fa-IR') }}. {{ product.name }}</td>
                    <td>{{ moneyInputValue(product.total) }}</td>
                  </tr>
                </tbody>
              </table>
            </section>

            <section class="thermal-total-block">
              <p><span>جمع کل</span><strong>{{ formatMoney(invoiceSubtotal) }}</strong></p>
              <p><span>جمع تخفیف</span><strong>{{ formatMoney(releaseSummary.discountAmount) }}</strong></p>
              <p><span>انعام</span><strong>{{ formatMoney(releaseSummary.tipAmount) }}</strong></p>
              <p><span>مالیات</span><strong>{{ formatMoney(releaseSummary.taxAmount) }}</strong></p>
              <p class="thermal-payable-total"><span>قیمت نهایی</span><strong>{{ formatMoney(releaseSummary.finalTotal) }}</strong></p>
            </section>

            <footer class="thermal-sheet-footer">
              <p v-if="releasePaymentBreakdownLabel">ترکیبی: {{ releasePaymentBreakdownLabel }}</p>
              <p v-if="invoiceDueDateLabel">سررسید: {{ invoiceDueDateLabel }}</p>
              <p v-if="releaseForm.receiptFooterNote" class="receipt-custom-note">{{ releaseForm.receiptFooterNote }}</p>
              <strong>از اعتماد شما سپاسگزاریم</strong>
            </footer>
          </template>

          <template v-else>
          <header class="invoice-sheet-head">
            <div class="invoice-sheet-brand">
              <small>{{ invoiceCarwashContactLine || invoiceCarwashName }}</small>
              <strong>فاکتور نهایی سفارش</strong>
              <span>شماره فاکتور: {{ invoiceNumber }}</span>
            </div>
            <div class="invoice-sheet-meta">
              <strong>{{ invoiceCarwashTitle }}</strong>
              <span>تاریخ صدور: {{ invoiceIssuedAt }}</span>
              <span>تیپ نرخنامه: {{ invoiceTariffTypeNumber }}</span>
            </div>
            <small v-if="invoiceReceiptHeaderNote" class="receipt-custom-note invoice-header-note">{{ invoiceReceiptHeaderNote }}</small>
          </header>

          <section class="invoice-identity-grid">
            <article>
              <small>اطلاعات مشتری</small>
              <p><span>نام</span><strong>{{ invoiceCustomerDisplayName }}</strong></p>
              <p><span>شماره تماس</span><strong>{{ invoiceCustomerPhone }}</strong></p>
              <p><span>امتیاز مشتری</span><strong>{{ formatCustomerScore(releaseForm.customerScore) }} | {{ releaseCustomerScoreStars }}</strong></p>
              <p><span>درصد تخفیف امتیاز</span><strong>{{ Number(releaseForm.customerLoyaltyDiscountPercent || 0).toLocaleString('fa-IR') }}٪</strong></p>
              <p><span>تعداد مراجعات</span><strong>{{ Number(releaseForm.customerLoyaltyVisitCount || 0).toLocaleString('fa-IR') }}</strong></p>
            </article>
            <article>
              <small>مشخصات خودرو</small>
              <p><span>خودرو</span><strong>{{ invoiceVehicleTitle }}</strong></p>
              <p><span>پلاک</span><strong>{{ invoicePlateLabel }}</strong></p>
              <p><span>نوع پذیرش</span><strong>{{ invoiceAdmissionLabel }}</strong></p>
            </article>
            <article>
              <small>اطلاعات سفارش</small>
              <p><span>شماره پذیرش</span><strong>#{{ invoiceAdmissionNumber }}</strong></p>
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
                  <td>{{ formatMoney(invoiceServiceLineListTotal(line)) }}</td>
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
              <p><span>تیپ نرخنامه</span><strong>{{ invoiceTariffTypeNumber }}</strong></p>
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
              <p><span>جمع کل</span><strong>{{ formatMoney(invoiceSubtotal) }}</strong></p>
              <p v-if="releaseSummary.facilityDiscountAmount > 0"><span>تخفیف مجموعه</span><strong>{{ formatMoney(releaseSummary.facilityDiscountAmount) }}</strong></p>
              <p v-if="releaseSummary.customerDiscountAmount > 0"><span>تخفیف امتیاز مشتری</span><strong>{{ formatMoney(releaseSummary.customerDiscountAmount) }}</strong></p>
              <p v-if="releaseSummary.manualDiscountAmount > 0"><span>تخفیف دستی</span><strong>{{ formatMoney(releaseSummary.manualDiscountAmount) }}</strong></p>
              <p><span>جمع تخفیف</span><strong>{{ formatMoney(releaseSummary.discountAmount) }}</strong></p>
              <p><span>انعام</span><strong>{{ formatMoney(releaseSummary.tipAmount) }}</strong></p>
              <p><span>مالیات</span><strong>{{ formatMoney(releaseSummary.taxAmount) }}</strong></p>
              <p class="invoice-grand-total"><span>قیمت نهایی</span><strong>{{ formatMoney(releaseSummary.finalTotal) }}</strong></p>
            </div>
          </section>

          <footer class="invoice-sheet-footer">
            <p v-if="invoiceCustomerNote">توضیحات سفارش: {{ invoiceCustomerNote }}</p>
            <p v-if="releaseForm.receiptFooterNote" class="receipt-custom-note">{{ releaseForm.receiptFooterNote }}</p>
            <p>از اعتماد شما سپاسگزاریم</p>
          </footer>
          </template>
                </div>
              </div>
            </div>
          </div>
          <p v-if="invoiceErrorMessage" class="invoice-preview-error">{{ invoiceErrorMessage }}</p>
        </div>
      </section>
    </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import VehicleEntryStepOne from '../../components/operator/VehicleEntryStepOne.vue'
import VehicleEntryStepTwo from '../../components/operator/VehicleEntryStepTwo.vue'
import BaseSpinner from '../../components/base/BaseSpinner.vue'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import AppShell from '../../components/layout/AppShell.vue'
import PlateBadge from '../../components/vehicles/PlateBadge.vue'
import PlateEditor from '../../components/vehicles/PlateEditor.vue'
import VehicleDetailsModal from '../../components/vehicles/VehicleDetailsModal.vue'
import { useAuthStore } from '../../store/auth.store'
import { useVehicleStore } from '../../store/vehicle.store'
import api from '../../services/api'
import { formatThousandsToman, formatThousandsTomanValue, fromThousandsTomanInput } from '../../utils/money'
import { resolveApiErrorMessage } from '../../utils/apiError'
import { notifyError, notifySuccess, notifyWarning } from '../../utils/notify'
import { buildPlateNumber, isAnonymousPlate, isValidIranMobile, normalizeDigits, normalizePlateLetter, resolvePlateParts, splitPlate } from '../../utils/plate'
import { printHtmlElement, resolvePrintErrorMessage } from '../../utils/receiptPrinter'

const search = ref('')
const debouncedSearch = ref('')
const plateFilter = reactive({
  plateType: '',
  plateLeft: '',
  plateLetter: '',
  plateMid: '',
  plateRight: ''
})
const debouncedPlateFilter = ref({
  plateType: '',
  plateLeft: '',
  plateLetter: '',
  plateMid: '',
  plateRight: ''
})
const activeFilter = ref('entered')
const dateRangeMode = ref('today')
const customDateRange = ref({
  startJalali: getTodayJalaliString(),
  endJalali: getTodayJalaliString()
})
const dateRangeDraft = ref({
  startJalali: getTodayJalaliString(),
  endJalali: getTodayJalaliString()
})
const showVehicleModal = ref(false)
const showVehicleDetailsModal = ref(false)
const showPlateEditModal = ref(false)
const showReleaseModal = ref(false)
const showDateRangeModal = ref(false)
const showChequeDetailsModal = ref(false)
const showInvoicePreviewModal = ref(false)
const showReleaseServicePicker = ref(false)
const showReleaseWorkerEditor = ref(false)
const releaseCheckoutLoading = ref(false)
const releaseSubmitting = ref(false)
const plateEditSubmitting = ref(false)
const stepSubmitting = ref(false)
const stepTransitionLoading = ref(false)
const invoiceGenerating = ref(false)
const invoicePdfUrl = ref('')
const invoiceErrorMessage = ref('')
const modalStep = ref(1)
const vehicleDraft = ref(null)
const vehicleEditFlow = ref('')
const releaseCandidate = ref(null)
const plateEditForm = ref({
  id: null,
  plateLeft: '',
  plateLetter: '',
  plateMid: '',
  plateRight: '',
  plateType: 'car'
})
const invoiceTemplateRef = ref(null)
const tempReleaseServiceIds = ref([])
const tempReleaseWorkerRows = ref([])
const releaseWorkerSearch = ref('')
const invoiceRenderTimer = ref(null)
const vehicleAutoSmsEnabled = ref(true)
const jobEditMode = ref('')
const isReleaseMobile = ref(false)
const releaseSectionOpen = ref({
  payment: false,
  bonus: false,
  sms: false
})
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
  availableWorkers: [],
  workerShareAmount: 0,
  customerScore: 0,
  applyLoyaltyDiscount: true,
  discountPercentPerHalfStar: 0,
  taxEnabled: false,
  taxPercent: 0,
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
  receiptHeaderNote: '',
  receiptFooterNote: '',
  carwashAddress: '',
  managerPhone: '',
  receiptPrinterPaperWidth: '80mm',
  receiptPrinterName: '',
  receiptPrinterEnabled: false,
  bonusPenaltyAdjustments: [],
  bonusPenaltyNote: '',
  smsNotificationsEnabled: true,
  smsAutoSendEnabled: true,
  newServiceLines: [],
  availableServicesToAdd: [],
  selectedServiceToAdd: 0
})
const vehicleStore = useVehicleStore()
const authStore = useAuthStore()
const { vehicles, selectedVehicle } = storeToRefs(vehicleStore)
const vehicleCardsRefreshTimer = ref(null)
const vehicleCardsRefreshInFlight = ref(false)
const hasOperatorModalOpen = computed(() => (
  showVehicleModal.value
  || showVehicleDetailsModal.value
  || showPlateEditModal.value
  || showReleaseModal.value
  || showChequeDetailsModal.value
  || showInvoicePreviewModal.value
  || showReleaseWorkerEditor.value
  || showDateRangeModal.value
))
const stepTwoSubmitLabel = computed(() => {
  if (vehicleEditFlow.value === 'released') return 'ادامه'
  const currentStatus = vehicleDraft.value?.status || selectedVehicle.value?.status || ''
  // Referred / incomplete entries still need a real assign action.
  if (vehicleEditFlow.value && ['entered', 'assigned', 'in_progress'].includes(currentStatus)) {
    return 'تایید و تخصیص کار'
  }
  if (vehicleEditFlow.value) return 'ثبت'
  return 'تایید و تخصیص کار'
})
const syncReleaseMobileState = () => {
  const mobile = window.innerWidth <= 768
  if (mobile === isReleaseMobile.value) return
  isReleaseMobile.value = mobile
  if (!mobile) {
    releaseSectionOpen.value = { payment: true, bonus: true, sms: true }
  } else {
    releaseSectionOpen.value = { payment: false, bonus: false, sms: false }
  }
}
const isReleaseSectionOpen = (key) => (
  !isReleaseMobile.value || Boolean(releaseSectionOpen.value?.[key])
)
const toggleReleaseSection = (key) => {
  if (!isReleaseMobile.value) return
  releaseSectionOpen.value = {
    ...releaseSectionOpen.value,
    [key]: !releaseSectionOpen.value?.[key],
  }
}

const openVehicleModal = () => {
  modalStep.value = 1
  vehicleEditFlow.value = ''
  vehicleDraft.value = {
    smsNotificationsEnabled: vehicleAutoSmsEnabled.value,
    smsAutoSendEnabled: vehicleAutoSmsEnabled.value
  }
  showVehicleModal.value = true
}
const closeVehicleModal = (options = {}) => {
  const force = options?.force === true
  if (stepSubmitting.value && !force) return
  showVehicleModal.value = false
  modalStep.value = 1
  vehicleDraft.value = null
  vehicleEditFlow.value = ''
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
const editSelectedVehicleVisit = async () => {
  if (!selectedVehicle.value?.id) return
  try {
    const { data } = await api.get(`/vehicles/${selectedVehicle.value.id}/`)
    vehicleStore.selectedVehicle = data
    vehicleDraft.value = mapVehicleToDraft(data)
    vehicleEditFlow.value = data.status === 'released' ? 'released' : 'active'
    modalStep.value = 1
    showVehicleDetailsModal.value = false
    showVehicleModal.value = true
  } catch (error) {
    console.error('editSelectedVehicleVisit error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'بارگذاری اطلاعات ویرایش ناموفق بود.'), { title: 'ویرایش مراجعه' })
  }
}
const emptyPlateEditForm = () => ({
  id: null,
  plateLeft: '',
  plateLetter: '',
  plateMid: '',
  plateRight: '',
  plateType: 'car'
})
const plateDigits = (value, limit) => normalizeDigits(value).replace(/\D/g, '').slice(0, limit)
const normalizedPlateEditParts = () => {
  const plateType = plateEditForm.value.plateType === 'motorcycle' ? 'motorcycle' : 'car'
  const resolved = resolvePlateParts({
    plate_left: plateEditForm.value.plateLeft,
    plate_letter: plateEditForm.value.plateLetter,
    plate_mid: plateEditForm.value.plateMid,
    plate_right: plateEditForm.value.plateRight,
    plate_type: plateType
  })
  if (plateType === 'motorcycle') {
    return {
      left: '',
      letter: plateDigits(resolved.letter, 5),
      mid: plateDigits(resolved.mid, 3),
      right: ''
    }
  }
  return {
    left: plateDigits(resolved.left, 2),
    letter: String(resolved.letter || '').trim(),
    mid: plateDigits(resolved.mid, 3),
    right: plateDigits(resolved.right, 2)
  }
}
const plateEditPreview = computed(() => buildPlateNumber({
  ...normalizedPlateEditParts(),
  plateType: plateEditForm.value.plateType
}))
const syncVehicleSnapshot = (vehicle) => {
  if (!vehicle?.id) return
  const idx = vehicleStore.vehicles.findIndex((item) => Number(item.id) === Number(vehicle.id))
  if (idx >= 0) vehicleStore.vehicles[idx] = vehicle
  if (Number(selectedVehicle.value?.id || 0) === Number(vehicle.id)) {
    vehicleStore.selectedVehicle = vehicle
  }
}
const openPlateEditModal = () => {
  const source = selectedVehicle.value
  if (!source?.id || source.is_piece_wash) return
  const plateType = source.plate_type === 'motorcycle' ? 'motorcycle' : 'car'
  const parts = isAnonymousPlate(source)
    ? { left: '', letter: '', mid: '', right: '' }
    : resolvePlateParts({
      raw: source.plate_number || '',
      plate_left: source.plate_left || '',
      plate_letter: source.plate_letter || '',
      plate_mid: source.plate_mid || '',
      plate_right: source.plate_right || '',
      plate_type: plateType
    })
  plateEditForm.value = {
    id: source.id,
    plateLeft: plateType === 'motorcycle' ? '' : plateDigits(parts.left, 2),
    plateLetter: plateType === 'motorcycle' ? plateDigits(parts.letter, 5) : String(parts.letter || ''),
    plateMid: plateDigits(parts.mid, 3),
    plateRight: plateType === 'motorcycle' ? '' : plateDigits(parts.right, 2),
    plateType
  }
  showPlateEditModal.value = true
}
const closePlateEditModal = (options = {}) => {
  const force = options?.force === true
  if (plateEditSubmitting.value && !force) return
  showPlateEditModal.value = false
  plateEditForm.value = emptyPlateEditForm()
}
const submitPlateEdit = async () => {
  if (!plateEditForm.value.id || plateEditSubmitting.value) return
  const plateType = plateEditForm.value.plateType === 'motorcycle' ? 'motorcycle' : 'car'
  const parts = normalizedPlateEditParts()
  const isComplete = plateType === 'motorcycle'
    ? parts.mid.length === 3 && parts.letter.length === 5
    : parts.left.length === 2 && parts.mid.length === 3 && parts.right.length === 2 && Boolean(parts.letter)
  if (!isComplete) {
    notifyWarning('پلاک را کامل وارد کنید.', { title: 'ویرایش پلاک' })
    return
  }
  const plateNumber = buildPlateNumber({ ...parts, plateType })
  try {
    plateEditSubmitting.value = true
    const { data } = await api.patch(`/vehicles/${plateEditForm.value.id}/`, {
      plate_number: plateNumber,
      plate_left: plateType === 'motorcycle' ? '' : parts.left,
      plate_letter: parts.letter,
      plate_mid: parts.mid,
      plate_right: plateType === 'motorcycle' ? '' : parts.right,
      plate_type: plateType
    }, { meta: { trackLoading: false } })
    syncVehicleSnapshot(data)
    closePlateEditModal({ force: true })
    notifySuccess('پلاک خودرو به‌روزرسانی شد.', { title: 'ویرایش پلاک' })
  } catch (error) {
    console.error('submitPlateEdit error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ویرایش پلاک ناموفق بود.'), { title: 'خطا در ویرایش پلاک' })
  } finally {
    plateEditSubmitting.value = false
  }
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
const moneyInputValue = (value) => formatThousandsTomanValue(value, { maximumFractionDigits: 0 })
const parseMoneyInput = (value) => fromThousandsTomanInput(normalizeDigits(value))
const formatPercent = (value) => `${Number(value || 0).toLocaleString('fa-IR')}٪`
const normalizeAiConfidence = (value) => {
  if (value === null || value === undefined || value === '') return null
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return null
  return Math.round(Math.min(999.99, Math.max(0, numericValue)) * 100) / 100
}
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
function localDateOnly(date = new Date()) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}
function shiftLocalDate(date, days) {
  const next = localDateOnly(date)
  next.setDate(next.getDate() + days)
  return next
}
function formatIsoDate(date) {
  const localDate = localDateOnly(date)
  return `${localDate.getFullYear()}-${String(localDate.getMonth() + 1).padStart(2, '0')}-${String(localDate.getDate()).padStart(2, '0')}`
}
function getJalaliParts(date = new Date()) {
  const parts = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric'
  }).formatToParts(date)
  return {
    y: Number(parts.find((item) => item.type === 'year')?.value || 1400),
    m: Number(parts.find((item) => item.type === 'month')?.value || 1),
    d: Number(parts.find((item) => item.type === 'day')?.value || 1)
  }
}
function formatJalaliParts(parts) {
  return `${parts.y}/${String(parts.m).padStart(2, '0')}/${String(parts.d).padStart(2, '0')}`
}
function getTodayJalaliString() {
  return formatJalaliParts(getJalaliParts(new Date()))
}
function isoDateToLocalDate(isoDate) {
  const match = String(isoDate || '').match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!match) return null
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}
function jalaliToLocalDate(jalaliDate) {
  const isoDate = parseJalaliToIso(jalaliDate)
  return isoDateToLocalDate(isoDate)
}
function presetDateRange(mode) {
  const today = localDateOnly(new Date())
  if (mode === 'yesterday') {
    const yesterday = shiftLocalDate(today, -1)
    const jalali = formatJalaliParts(getJalaliParts(yesterday))
    return { startJalali: jalali, endJalali: jalali }
  }
  if (mode === 'week') {
    const saturdayOffset = (today.getDay() + 1) % 7
    const weekStart = shiftLocalDate(today, -saturdayOffset)
    return {
      startJalali: formatJalaliParts(getJalaliParts(weekStart)),
      endJalali: formatJalaliParts(getJalaliParts(today))
    }
  }
  if (mode === 'month') {
    const todayJalali = getJalaliParts(today)
    return {
      startJalali: formatJalaliParts({ y: todayJalali.y, m: todayJalali.m, d: 1 }),
      endJalali: formatJalaliParts(todayJalali)
    }
  }
  const jalali = formatJalaliParts(getJalaliParts(today))
  return { startJalali: jalali, endJalali: jalali }
}
const datePresetItems = [
  { key: 'today', label: 'امروز' },
  { key: 'yesterday', label: 'دیروز' },
  { key: 'week', label: 'این هفته' },
  { key: 'month', label: 'این ماه' }
]
const activeDateRange = computed(() => (
  dateRangeMode.value === 'custom' ? customDateRange.value : presetDateRange(dateRangeMode.value)
))
const activeDateRangeLabel = computed(() => {
  const range = activeDateRange.value
  if (!range.startJalali || !range.endJalali) return ''
  if (range.startJalali === range.endJalali) return range.startJalali
  return `${range.startJalali} تا ${range.endJalali}`
})
const activeDateRangeParams = computed(() => {
  const range = activeDateRange.value
  const start = parseJalaliToIso(range.startJalali)
  const end = parseJalaliToIso(range.endJalali)
  return {
    date_start: start || undefined,
    date_end: end || undefined
  }
})
const fetchVehiclesForActiveRange = (options = {}) => vehicleStore.fetchVehicles(activeDateRangeParams.value, {
  trackLoading: false,
  ...options
})
const refreshVehicleCardsFromDatabase = async () => {
  if (vehicleCardsRefreshInFlight.value) return
  vehicleCardsRefreshInFlight.value = true
  try {
    await fetchVehiclesForActiveRange({ showErrorToast: false })
  } catch (error) {
    console.error('vehicle cards auto refresh error:', error?.response?.data || error)
  } finally {
    vehicleCardsRefreshInFlight.value = false
  }
}
const startVehicleCardsAutoRefresh = () => {
  if (vehicleCardsRefreshTimer.value) window.clearInterval(vehicleCardsRefreshTimer.value)
  vehicleCardsRefreshTimer.value = window.setInterval(refreshVehicleCardsFromDatabase, 10000)
}
const selectDatePreset = (mode) => {
  dateRangeMode.value = mode
}
const openDateRangeModal = () => {
  const range = activeDateRange.value
  dateRangeDraft.value = {
    startJalali: range.startJalali || getTodayJalaliString(),
    endJalali: range.endJalali || getTodayJalaliString()
  }
  showDateRangeModal.value = true
}
const closeDateRangeModal = () => {
  showDateRangeModal.value = false
}
const applyCustomDateRange = () => {
  const startDate = jalaliToLocalDate(dateRangeDraft.value.startJalali)
  const endDate = jalaliToLocalDate(dateRangeDraft.value.endJalali)
  if (!startDate || !endDate) {
    notifyWarning('تاریخ شروع و پایان را کامل انتخاب کنید.', { title: 'بازه تاریخی' })
    return
  }
  if (startDate.getTime() > endDate.getTime()) {
    notifyWarning('تاریخ شروع نباید بعد از تاریخ پایان باشد.', { title: 'بازه تاریخی' })
    return
  }
  customDateRange.value = {
    startJalali: dateRangeDraft.value.startJalali,
    endJalali: dateRangeDraft.value.endJalali
  }
  dateRangeMode.value = 'custom'
  closeDateRangeModal()
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
const isAnonymousVisitFromDatabase = (source = {}) => {
  if (Boolean(source.is_piece_wash || source.isPieceWash)) return false
  const model = String(source.car_model || source.model || '').trim()
  const color = String(source.car_color || source.color || '').trim()
  const plateNumber = String(source.plate_number || source.plate || '').trim()
  return Boolean(source.is_anonymous || source.isAnonymous) || isAnonymousPlate(source) || (model === '1111' && color === '1111') || (plateNumber === '1111')
}
const mapVehicleToDraft = (source = {}) => ({
  id: source.id,
  status: source.status,
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
  driverGender: source.driver_gender || 'male',
  mobile: source.driver_phone,
  smsNotificationsEnabled: source.sms_notifications_enabled !== false,
  smsAutoSendEnabled: source.smsAutoSendEnabled ?? source.sms_auto_send_enabled ?? source.sms_vehicle_auto_send_enabled ?? vehicleAutoSmsEnabled.value,
  customerScore: Number(source.customer_score || source.customerScore || 0),
  customerLoyaltyVisitCount: Math.max(
    source.is_piece_wash || source.isPieceWash ? 0 : 1,
    Number(source.customer_loyalty_visit_count || source.customerLoyaltyVisitCount || 0)
  ),
  customerLoyaltyDiscountPercent: Number(source.customer_loyalty_discount_percent || source.customerLoyaltyDiscountPercent || 0),
  applyLoyaltyDiscount: source.job?.apply_loyalty_discount !== false,
  apply_loyalty_discount: source.job?.apply_loyalty_discount !== false,
  manualDiscountTotal: Number(source.job?.manual_discount_total || 0),
  manual_discount_total: Number(source.job?.manual_discount_total || 0),
  note: source.notes,
  tariffType: source.tariff_type || source.tariffType || 'type_1',
  detectedPlate: source.ai_converted_plate || source.plate_number || '',
  detectedPlateLeft: source.ai_converted_plate_left || source.plate_left || '',
  detectedPlateLetter: source.ai_converted_plate_letter || source.plate_letter || '',
  detectedPlateMid: source.ai_converted_plate_mid || source.plate_mid || '',
  detectedPlateRight: source.ai_converted_plate_right || source.plate_right || '',
  detectedPlateType: source.ai_converted_plate_type || source.plate_type || 'car',
  aiSessionId: source.ai_session_id || '',
  aiRawText: source.ai_raw_text || '',
  aiPersianText: source.ai_persian_text || '',
  aiConvertedPlate: source.ai_converted_plate || '',
  aiConvertedPlateLeft: source.ai_converted_plate_left || '',
  aiConvertedPlateLetter: source.ai_converted_plate_letter || '',
  aiConvertedPlateMid: source.ai_converted_plate_mid || '',
  aiConvertedPlateRight: source.ai_converted_plate_right || '',
  aiConvertedPlateType: source.ai_converted_plate_type || source.plate_type || 'car',
  aiImageBase64: source.ai_image_base64 || '',
  aiConfidence: source.ai_confidence ?? null,
  aiLatencyMs: source.ai_latency_ms ?? null,
  isPieceWash: Boolean(source.is_piece_wash),
  pieceDetails: source.piece_details || '',
  pieceWashPrice: Number(source.job?.services_total || 0),
  isAnonymous: isAnonymousVisitFromDatabase(source),
  is_plate_blocked: Boolean(source.is_plate_blocked),
  blocked_plate_id: source.blocked_plate_id || null,
  serviceIds: Array.isArray(source.job?.service_lines) ? source.job.service_lines.map((s) => s.service).filter(Boolean) : [],
  services: Array.isArray(source.job?.service_lines)
    ? source.job.service_lines.map((line) => ({
      id: line.service,
      service_id: line.service,
      title: line.service_name,
      name: line.service_name,
      price: Number(line.line_total || line.unit_price || 0),
      base_price: Number(line.unit_price || line.line_total || 0),
      list_price: Number(line.list_unit_price || line.line_total || line.unit_price || 0),
      unit_price: Number(line.unit_price || line.line_total || 0),
      adjusted_price: Number(line.line_total || line.unit_price || 0),
      discount_amount: Number(line.discount_amount || 0)
    }))
    : [],
  products: Array.isArray(source.job?.product_lines)
    ? source.job.product_lines.map((line) => ({
      id: line.product,
      product_id: line.product,
      name: line.product_name,
      quantity: Number(line.quantity || 0),
      sale_price: Number(line.unit_price || 0),
      lineTotal: Number(line.line_total || 0)
    }))
    : [],
  productLines: Array.isArray(source.job?.product_lines)
    ? source.job.product_lines.map((line) => ({
      id: line.product,
      product_id: line.product,
      name: line.product_name,
      quantity: Number(line.quantity || 0),
      sale_price: Number(line.unit_price || 0),
      lineTotal: Number(line.line_total || 0)
    }))
    : [],
  staffId: source.job?.assigned_worker || null,
  staffMembers: Array.isArray(source.job?.assigned_workers_snapshot) && source.job.assigned_workers_snapshot.length
    ? source.job.assigned_workers_snapshot
      .map((item) => ({
        id: Number(item?.id || 0),
        name: String(item?.name || '').trim(),
        worker_share_percent: Math.max(0, Math.min(100, Number(item?.worker_share_percent || 0)))
      }))
      .filter((item) => item.id > 0)
    : (
      source.job?.assigned_worker
        ? [{
            id: Number(source.job.assigned_worker),
            name: String(source.job?.assigned_worker_name || '').trim(),
            worker_share_percent: Math.max(0, Math.min(100, Number(source.job?.worker_share_percent || 100)))
          }]
        : []
    ),
  staffIds: Array.isArray(source.job?.assigned_workers_snapshot) && source.job.assigned_workers_snapshot.length
    ? source.job.assigned_workers_snapshot
      .map((item) => Number(item?.id))
      .filter((id) => Number.isFinite(id) && id > 0)
    : (
      source.job?.assigned_worker
        ? [Number(source.job.assigned_worker)].filter((id) => Number.isFinite(id) && id > 0)
        : []
    ),
  job: source.job || null
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
  const hasPhone = isValidIranMobile(source.driver_phone)
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
  try {
    const { data } = await api.get(`/vehicles/${car.id}/`)
    vehicleStore.selectedVehicle = data
    vehicleDraft.value = mapVehicleToDraft(data)
    vehicleEditFlow.value = data.status === 'released' ? 'released' : 'active'
    modalStep.value = (data.status === 'entered' && !hasCompletedStepOneData(data)) ? 1 : 2
    showVehicleModal.value = true
  } catch (error) {
    console.error('handleCardAction error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'بارگذاری اطلاعات مراجعه ناموفق بود.'), { title: 'ویرایش مراجعه' })
  }
}
const closeReleaseModal = (options = {}) => {
  const force = options?.force === true
  if (releaseSubmitting.value && !force) return
  showReleaseModal.value = false
  showReleaseServicePicker.value = false
  showReleaseWorkerEditor.value = false
  showChequeDetailsModal.value = false
  closeInvoicePreviewModal()
  releaseCandidate.value = null
  tempReleaseServiceIds.value = []
  tempReleaseWorkerRows.value = []
  releaseCheckoutLoading.value = false
  releaseSubmitting.value = false
  jobEditMode.value = ''
  releaseForm.value = {
    serviceLines: [],
    availableProducts: [],
    productLinesByProductId: {},
    productSearch: '',
    tipAmount: 0,
      assignedWorkers: [],
      availableWorkers: [],
      workerShareAmount: 0,
      customerScore: 0,
      applyLoyaltyDiscount: true,
    discountPercentPerHalfStar: 0,
    taxEnabled: false,
    taxPercent: 0,
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
      receiptHeaderNote: '',
      receiptFooterNote: '',
    carwashAddress: '',
    managerPhone: '',
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
    : Math.round(Number(releaseSummary.value.finalTotal || 0))
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
const isReleaseAssignableWorker = (worker) => {
  const roleKey = String(worker?.role_key || worker?.user?.role || '').trim().toLowerCase()
  if (roleKey) return roleKey === 'worker'
  const roleLabel = String(worker?.role || '').trim().toLowerCase()
  return roleLabel.includes('worker') || roleLabel.includes('نیرو') || roleLabel.includes('پرسنل')
}
const normalizeAvailableReleaseWorkers = (workers) => (
  (Array.isArray(workers) ? workers : [])
    .filter(isReleaseAssignableWorker)
    .map((item) => ({
      id: Number(item?.id || 0),
      name: normalizeWorkerName(item?.full_name || item?.name || item?.user?.full_name || item?.username || ''),
      tip_share_percent: Number(item?.tip_share_percent || 0),
      worker_share_percent: Number(item?.worker_share_percent || 0),
      worker_local_key: `available-worker-${Number(item?.id || 0)}`
    }))
    .filter((item) => item.id > 0 && isRealWorkerName(item.name))
)
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
  return Math.round(Number(worker.baseAmount || 0))
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

  const inputAmount = Math.round(Math.max(0, Number(rawValue || 0)))
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
const tempReleaseWorkerPercentTotal = computed(() => (
  tempReleaseWorkerRows.value
    .filter((worker) => worker.isSelected)
    .reduce((sum, worker) => sum + Math.max(0, Math.min(100, Number(worker.worker_share_percent || 0))), 0)
))
const filteredTempReleaseWorkerRows = computed(() => {
  const query = String(releaseWorkerSearch.value || '').trim()
  return tempReleaseWorkerRows.value
    .map((worker, index) => ({ ...worker, sourceIndex: index }))
    .filter((worker) => !query || String(worker.name || '').includes(query))
})
const buildReleaseWorkerEditorRows = () => {
  const selectedMap = new Map(
    (releaseForm.value.assignedWorkers || [])
      .filter((worker) => Number(worker?.id || 0) > 0)
      .map((worker) => [Number(worker.id), worker])
  )
  const rowsById = new Map()
  ;(releaseForm.value.availableWorkers || []).forEach((worker) => {
    rowsById.set(Number(worker.id), {
      ...worker,
      isSelected: selectedMap.has(Number(worker.id)),
      worker_share_percent: Number(selectedMap.get(Number(worker.id))?.worker_share_percent ?? worker.worker_share_percent ?? 0),
      worker_local_key: String(selectedMap.get(Number(worker.id))?.worker_local_key || worker.worker_local_key || `available-worker-${worker.id}`)
    })
  })
  selectedMap.forEach((worker, workerId) => {
    if (rowsById.has(workerId)) return
    rowsById.set(workerId, {
      ...worker,
      id: workerId,
      name: normalizeWorkerName(worker.name) || `نیرو ${workerId}`,
      isSelected: true,
      worker_share_percent: Number(worker.worker_share_percent || 0),
      worker_local_key: String(worker.worker_local_key || `selected-worker-${workerId}`)
    })
  })
  const rows = [...rowsById.values()]
  const selectedPercentTotal = rows
    .filter((worker) => worker.isSelected)
    .reduce((sum, worker) => sum + Math.max(0, Number(worker.worker_share_percent || 0)), 0)
  tempReleaseWorkerRows.value = selectedPercentTotal > 0
    ? rows
    : applyEqualDistributionToSelectedWorkers(rows)
}
const openReleaseWorkerEditor = () => {
  releaseWorkerSearch.value = ''
  buildReleaseWorkerEditorRows()
  showReleaseWorkerEditor.value = true
}
const closeReleaseWorkerEditor = () => {
  showReleaseWorkerEditor.value = false
  tempReleaseWorkerRows.value = []
  releaseWorkerSearch.value = ''
}
const toggleTempReleaseWorker = (index) => {
  const rows = [...tempReleaseWorkerRows.value]
  if (index < 0 || index >= rows.length) return
  const selectedCount = rows.filter((worker) => worker.isSelected).length
  const isSelected = Boolean(rows[index].isSelected)
  if (isSelected && selectedCount <= 1) {
    notifyWarning('حداقل یک پرسنل باید در تسویه فعال باشد.', { title: 'ویرایش پرسنل' })
    return
  }
  rows[index] = {
    ...rows[index],
    isSelected: !isSelected,
    worker_share_percent: isSelected ? 0 : Number(rows[index].worker_share_percent || 0)
  }
  tempReleaseWorkerRows.value = applyEqualDistributionToSelectedWorkers(rows)
}
const setTempReleaseWorkerShare = (index, rawValue) => {
  const rows = [...tempReleaseWorkerRows.value]
  if (index < 0 || index >= rows.length || !rows[index].isSelected) return
  const selectedIndexes = getSelectedWorkerIndexes(rows)
  if (!selectedIndexes.includes(index)) return
  const parsed = Math.max(0, Math.min(100, Math.floor(Number(rawValue || 0))))
  if (selectedIndexes.length === 1) {
    rows[index] = { ...rows[index], worker_share_percent: 100 }
    tempReleaseWorkerRows.value = rows
    return
  }
  const otherIndexes = selectedIndexes.filter((item) => item !== index)
  const remaining = Math.max(0, 100 - parsed)
  const base = otherIndexes.length ? Math.floor(remaining / otherIndexes.length) : 0
  let remainder = otherIndexes.length ? remaining - (base * otherIndexes.length) : 0
  rows[index] = { ...rows[index], worker_share_percent: parsed }
  otherIndexes.forEach((workerIndex) => {
    const nextValue = base + (remainder > 0 ? 1 : 0)
    if (remainder > 0) remainder -= 1
    rows[workerIndex] = { ...rows[workerIndex], worker_share_percent: nextValue }
  })
  tempReleaseWorkerRows.value = rows
}
const equalizeTempReleaseWorkers = () => {
  tempReleaseWorkerRows.value = applyEqualDistributionToSelectedWorkers(tempReleaseWorkerRows.value)
}
const tempReleaseWorkerShareAmount = (worker) => {
  if (!worker?.isSelected) return 0
  const percent = Math.max(0, Math.min(100, Number(worker.worker_share_percent || 0)))
  return Math.round((Number(releaseSummary.value.workerShareBase || 0) * percent) / 100)
}
const confirmReleaseWorkerEditor = () => {
  const selectedPercentTotal = tempReleaseWorkerRows.value
    .filter((worker) => worker.isSelected)
    .reduce((sum, worker) => sum + Math.max(0, Number(worker.worker_share_percent || 0)), 0)
  const rows = selectedPercentTotal > 0
    ? [...tempReleaseWorkerRows.value]
    : applyEqualDistributionToSelectedWorkers(tempReleaseWorkerRows.value)
  const selectedRows = rows.filter((worker) => worker.isSelected && Number(worker.id || 0) > 0)
  if (!selectedRows.length) {
    notifyWarning('حداقل یک پرسنل معتبر انتخاب کنید.', { title: 'ویرایش پرسنل' })
    return
  }
  releaseForm.value.assignedWorkers = selectedRows.map((worker, index) => ({
    id: Number(worker.id),
    name: normalizeWorkerName(worker.name) || `نیرو ${Number(index + 1).toLocaleString('fa-IR')}`,
    tip_share_percent: Number(worker.tip_share_percent || 0),
    worker_share_percent: Math.max(0, Math.min(100, Number(worker.worker_share_percent || 0))),
    worker_local_key: String(worker.worker_local_key || `release-worker-${worker.id}`),
    isSelected: true
  }))
  syncBonusPenaltyAdjustments()
  closeReleaseWorkerEditor()
}
const openReleaseModal = async (car) => {
  const sourceVehicle = vehicleStore.vehicles.find((item) => Number(item.id) === Number(car?.id || 0)) || null
  releaseCandidate.value = car
  showReleaseModal.value = true
  releaseCheckoutLoading.value = true
  try {
    const [releaseResponse, settingsResponse, workersResponse] = await Promise.all([
      api.get(`/vehicles/${car.id}/release/`),
      api.get('/services/general-settings/').catch(() => ({ data: { discount_percent_per_half_star: 0 } })),
      api.get('/workers/').catch(() => ({ data: [] }))
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
        list_unit_price: Number(line.list_unit_price || 0),
        unit_price: Number(line.unit_price || 0),
        discount_amount: Number(line.discount_amount || 0),
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
      tipAmount: Math.max(0, Number(data?.job?.tip_amount || 0)),
      assignedWorkers: normalizeReleaseAssignedWorkers(preferredAssignedWorkers),
      availableWorkers: normalizeAvailableReleaseWorkers(workersResponse?.data),
      workerShareAmount: Number(data?.job?.worker_share_amount || 0),
      customerScore: Math.max(0, Number(data?.vehicle?.customer_score || releaseCandidate.value?.customerScore || 0)),
      customerLoyaltyVisitCount: Math.max(0, Number(data?.vehicle?.customer_loyalty_visit_count || 0)),
      customerLoyaltyDiscountPercent: Math.max(0, Number(data?.vehicle?.customer_loyalty_discount_percent || 0)),
      applyLoyaltyDiscount: data?.job?.apply_loyalty_discount !== false,
      discountPercentPerHalfStar,
      facilityDiscountTotal: Math.max(0, Number(data?.job?.facility_discount_total || 0)),
      loyaltyDiscountTotal: Math.max(0, Number(data?.job?.loyalty_discount_total || 0)),
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
      receiptHeaderNote: settingsResponse?.data?.receipt_header_note || '',
      receiptFooterNote: settingsResponse?.data?.receipt_footer_note || '',
      carwashAddress: data?.vehicle?.tenant_address || authStore.user?.tenant?.address || '',
      managerPhone: data?.vehicle?.manager_phone || authStore.user?.phone || '',
      receiptPrinterPaperWidth: settingsResponse?.data?.receipt_printer_paper_width || '80mm',
      receiptPrinterName: settingsResponse?.data?.receipt_printer_name || '',
      receiptPrinterEnabled: Boolean(settingsResponse?.data?.receipt_printer_enabled),
      taxEnabled: Boolean(settingsResponse?.data?.tax_enabled),
      taxPercent: Number(settingsResponse?.data?.tax_percent || 0),
      bonusPenaltyAdjustments: [],
      bonusPenaltyNote: '',
      smsNotificationsEnabled: settingsResponse?.data?.sms_vehicle_auto_send_enabled !== false && data?.vehicle?.sms_notifications_enabled !== false,
      smsAutoSendEnabled: settingsResponse?.data?.sms_vehicle_auto_send_enabled !== false,
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
    closeReleaseModal({ force: true })
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
  { key: 'a4', label: 'A4', hint: 'فاکتور کامل' },
  { key: 'a5', label: 'A5', hint: 'جمع‌وجور' },
  { key: 'thermal', label: 'فیش', hint: 'پرینتر حرارتی' }
]
const invoiceIsThermal = computed(() => invoiceLayout.value.preset === 'thermal')
const invoiceThermalWidthMm = computed(() => sanitizeMillimeter(invoiceLayout.value.thermalWidthMm, 80, 48, 120))
const invoiceThermalHeightMm = computed(() => sanitizeMillimeter(invoiceLayout.value.thermalHeightMm, 220, 80, 600))
const invoicePageMetrics = computed(() => {
  if (invoiceLayout.value.preset === 'a5') {
    return {
      width: 138,
      minHeight: 200,
      padding: 4.5,
      gap: 6,
      margin: [5, 5, 5, 5],
      format: 'a5',
      printWidthMm: 148,
      printHeightMm: 210,
      printMarginMm: 5,
      thermal: false
    }
  }
  if (invoiceLayout.value.preset === 'thermal') {
    const paperWidth = invoiceThermalWidthMm.value
    const paperHeight = invoiceThermalHeightMm.value
    return {
      width: paperWidth,
      minHeight: Math.max(80, Math.min(paperHeight, 160)),
      padding: paperWidth <= 58 ? 1.6 : 2.2,
      gap: 4,
      margin: [1, 1, 1, 1],
      format: [paperWidth, paperHeight],
      printWidthMm: paperWidth,
      printHeightMm: null,
      printMarginMm: paperWidth <= 58 ? 1 : 1.5,
      printMinHeightMm: 80,
      thermal: true
    }
  }
  return {
    width: 198,
    minHeight: 285,
    padding: 5,
    gap: 7,
    margin: [6, 6, 6, 6],
    format: 'a4',
    printWidthMm: 210,
    printHeightMm: 297,
    printMarginMm: 6,
    thermal: false
  }
})
const invoicePrintPageOptions = computed(() => ({
  widthMm: invoicePageMetrics.value.printWidthMm,
  heightMm: invoicePageMetrics.value.printHeightMm,
  minHeightMm: invoicePageMetrics.value.printMinHeightMm || invoicePageMetrics.value.minHeight,
  marginMm: invoicePageMetrics.value.printMarginMm,
  thermal: Boolean(invoicePageMetrics.value.thermal)
}))
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
const invoiceCarwashName = computed(() => (
  String(authStore.user?.tenant_name || '').trim() || 'کارواش'
))
const invoiceCarwashTitle = computed(() => {
  const name = invoiceCarwashName.value
  return name.startsWith('کارواش') ? name : `کارواش ${name}`
})
const invoiceCarwashContactLine = computed(() => {
  const parts = [
    String(releaseForm.value.carwashAddress || '').trim(),
    String(releaseForm.value.managerPhone || '').trim()
  ].filter(Boolean)
  return parts.join(' | ')
})
const invoiceReceiptHeaderNote = computed(() => String(releaseForm.value.receiptHeaderNote || '').trim())
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
const invoiceAdmissionNumber = computed(() => Number(
  releaseCandidate.value?.admission_number || releaseCandidate.value?.admissionNumber || releaseCandidate.value?.id || 0
).toLocaleString('fa-IR'))
const invoiceNumber = computed(() => `CW-${invoiceAdmissionNumber.value}`)
const invoiceTariffTypeNumber = computed(() => {
  const raw = String(
    releaseCandidate.value?.tariff_type || releaseCandidate.value?.tariffType || 'type_1'
  ).trim()
  const match = raw.match(/(\d+)/)
  return Number(match ? match[1] : 1).toLocaleString('fa-IR')
})
const invoiceCustomerName = computed(() => (
  String(releaseCandidate.value?.driverName || releaseCandidate.value?.driver_name || '').trim() || 'مشتری حضوری'
))
const invoiceCustomerDisplayName = computed(() => {
  const name = invoiceCustomerName.value
  const gender = String(
    releaseCandidate.value?.driverGender || releaseCandidate.value?.driver_gender || ''
  ).trim().toLowerCase()
  if (!name || name === 'مشتری حضوری') return name
  if (gender === 'male' && !/^(آقای|اقای)\s+/.test(name)) return `اقای ${name}`
  if (gender === 'female' && !/^خانم\s+/.test(name)) return `خانم ${name}`
  return name
})
const invoiceCustomerPhone = computed(() => (
  String(releaseCandidate.value?.driverPhone || releaseCandidate.value?.driver_phone || '').trim() || '-'
))
const invoiceCustomerScoreLabel = computed(() => `${Number(releaseForm.value.customerScore || 0).toLocaleString('fa-IR')} از ۵`)
const invoiceVehicleTitle = computed(() => {
  const model = String(releaseCandidate.value?.model || releaseCandidate.value?.car_model || '').trim()
  const color = String(releaseCandidate.value?.colorName || releaseCandidate.value?.car_color || '').trim()
  return `${model} ${color}`.trim() || 'قطعه‌شویی'
})
const invoicePlateLabel = computed(() => {
  const source = releaseCandidate.value || {}
  const plateType = String(source.plateType || source.plate_type || '').trim()
  if (plateType === 'motorcycle') {
    return buildPlateNumber({
      plateType,
      mid: source.plateMid || source.plate_mid || '',
      letter: source.plateLetter || source.plate_letter || ''
    }) || String(source.plateDisplay || source.plate_number || '').trim() || 'قطعه‌شویی'
  }
  const right = String(source.plateRight || source.plate_right || '').trim()
  const letter = String(source.plateLetter || source.plate_letter || '').trim()
  const mid = String(source.plateMid || source.plate_mid || '').trim()
  const left = String(source.plateLeft || source.plate_left || '').trim()
  if (right && letter && mid && left) return `${right} ${letter} ${mid} - ${left}`
  return String(source.plateDisplay || source.plate_number || '').trim() || 'قطعه‌شویی'
})
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
const invoiceServiceLineListTotal = (line) => {
  return Number(line?.line_total || 0) + Number(line?.discount_amount || 0)
}
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
  const cashAmount = Math.max(0, Number(releaseForm.value.manualCashAmount || 0))
  const secondaryAmount = Math.max(0, Number(releaseForm.value.manualSecondaryAmount || 0))
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
  const mmMatch = value.match(/(\d+(?:\.\d+)?)\s*mm/)
  if (mmMatch) {
    invoiceLayout.value.thermalWidthMm = sanitizeMillimeter(Number(mmMatch[1]), 80, 48, 120)
  } else if (value === '58mm') {
    invoiceLayout.value.thermalWidthMm = 58
  } else {
    invoiceLayout.value.thermalWidthMm = 80
  }
}
const filteredReleaseProducts = computed(() => {
  const items = releaseForm.value.availableProducts || []
  const query = (releaseForm.value.productSearch || '').trim()
  if (!query) return items
  return items.filter((item) => `${item.name || ''} ${item.sku || ''}`.includes(query))
})
let searchDebounceTimer = null
let plateDebounceTimer = null
watch(search, (value) => {
  if (searchDebounceTimer) window.clearTimeout(searchDebounceTimer)
  searchDebounceTimer = window.setTimeout(() => {
    debouncedSearch.value = String(value || '')
  }, 180)
}, { immediate: true })

const hasPlateFilter = computed(() => Boolean(
  plateFilter.plateLeft
  || plateFilter.plateLetter
  || plateFilter.plateMid
  || plateFilter.plateRight
  || plateFilter.plateType
))

const hasDebouncedPlateFilter = computed(() => Boolean(
  debouncedPlateFilter.value.plateLeft
  || debouncedPlateFilter.value.plateLetter
  || debouncedPlateFilter.value.plateMid
  || debouncedPlateFilter.value.plateRight
  || debouncedPlateFilter.value.plateType
))

const clearPlateFilter = () => {
  if (plateDebounceTimer) window.clearTimeout(plateDebounceTimer)
  plateFilter.plateType = ''
  plateFilter.plateLeft = ''
  plateFilter.plateLetter = ''
  plateFilter.plateMid = ''
  plateFilter.plateRight = ''
  debouncedPlateFilter.value = {
    plateType: '',
    plateLeft: '',
    plateLetter: '',
    plateMid: '',
    plateRight: ''
  }
}

const normalizePlateFilterSnapshot = (source = {}) => {
  let plateType = source.plateType === 'motorcycle' || source.plateType === 'car' ? source.plateType : ''
  let plateLeft = normalizeDigits(source.plateLeft).replace(/\D/g, '').slice(0, 2)
  let plateRight = normalizeDigits(source.plateRight).replace(/\D/g, '').slice(0, 2)
  let plateMid = normalizeDigits(source.plateMid).replace(/\D/g, '').slice(0, 3)
  const letterRaw = String(source.plateLetter || '')
  const letterLooksMotor = /^\d+$/.test(normalizeDigits(letterRaw).replace(/\D/g, '')) && letterRaw.length > 1
  let plateLetter = ''
  if (plateType === 'motorcycle' || (!plateType && letterLooksMotor)) {
    plateLetter = normalizeDigits(letterRaw).replace(/\D/g, '').slice(0, 5)
  } else {
    plateLetter = normalizePlateLetter(letterRaw)
  }
  if (plateType === 'motorcycle') {
    plateLeft = ''
    plateRight = ''
  }
  return { plateType, plateLeft, plateLetter, plateMid, plateRight }
}

watch(
  () => [
    plateFilter.plateType,
    plateFilter.plateLeft,
    plateFilter.plateLetter,
    plateFilter.plateMid,
    plateFilter.plateRight
  ],
  () => {
    if (plateDebounceTimer) window.clearTimeout(plateDebounceTimer)
    plateDebounceTimer = window.setTimeout(() => {
      debouncedPlateFilter.value = normalizePlateFilterSnapshot(plateFilter)
    }, 180)
  },
  { immediate: true }
)

const matchesPlateFilter = (item, plate) => {
  if (!plate) return true
  const itemType = String(item.plateType || 'car').toLowerCase() === 'motorcycle' ? 'motorcycle' : 'car'
  if (plate.plateType && itemType !== plate.plateType) return false

  const left = String(item.plateLeftKey || '')
  const letter = String(item.plateLetterKey || '')
  const mid = String(item.plateMidKey || '')
  const right = String(item.plateRightKey || '')
  const display = String(item.plateDisplay || '')

  if (plate.plateLeft && !left.includes(plate.plateLeft) && !display.includes(plate.plateLeft)) return false
  if (plate.plateMid && !mid.includes(plate.plateMid) && !display.includes(plate.plateMid)) return false
  if (plate.plateRight && !right.includes(plate.plateRight) && !display.includes(plate.plateRight)) return false
  if (plate.plateLetter) {
    const needle = String(plate.plateLetter).toLowerCase()
    if (!letter.toLowerCase().includes(needle) && !display.toLowerCase().includes(needle)) return false
  }
  return true
}
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
  const rawServiceListSubtotal = releaseForm.value.serviceLines.reduce((sum, line) => (
    line.is_completed ? sum + invoiceServiceLineListTotal(line) : sum
  ), 0)
  const productsTotal = releaseForm.value.availableProducts.reduce((sum, product) => {
    const qty = getReleaseProductQty(product.id)
    return sum + (qty * Number(product.sale_price || 0))
  }, 0)
  const tipAmount = Math.max(0, Number(releaseForm.value.tipAmount || 0))
  const customerScore = Math.max(0, Math.min(5, Number(releaseForm.value.customerScore || 0)))
  const discountPercentPerHalfStar = Math.max(0, Number(releaseForm.value.discountPercentPerHalfStar || 0))
  const serviceListSubtotal = rawServiceListSubtotal > 0
    ? rawServiceListSubtotal
    : servicesTotal + Math.max(0, Number(releaseForm.value.facilityDiscountTotal || 0))
  const computedFacilityDiscountAmount = Math.max(0, Number((serviceListSubtotal - servicesTotal).toFixed(2)))
  const facilityDiscountAmount = computedFacilityDiscountAmount || Math.max(0, Number(releaseForm.value.facilityDiscountTotal || 0))
  const customerDiscountPercent = Math.max(
    0,
    Number(
      releaseForm.value.customerLoyaltyDiscountPercent
      ?? Number((discountPercentPerHalfStar * customerScore * 2).toFixed(2))
      ?? 0
    )
  )
  const customerDiscountAmount = Number(
    (
      releaseForm.value.applyLoyaltyDiscount === false
        ? 0
        : (releaseForm.value.loyaltyDiscountTotal || ((serviceListSubtotal * customerDiscountPercent) / 100))
    ).toFixed(2)
  )
  const manualDiscountAmount = Math.max(0, Number(releaseForm.value.manualDiscountTotal || 0))
  const discountAmount = Math.min(
    Math.max(0, serviceListSubtotal),
    Number((facilityDiscountAmount + customerDiscountAmount + manualDiscountAmount).toFixed(2))
  )
  const shareBaseTotal = Math.max(0, servicesTotal)
  const workerShareBase = Math.min(shareBaseTotal, Number(releaseForm.value.workerShareAmount || 0))
  const taxableTotal = Math.max(0, serviceListSubtotal + productsTotal - discountAmount)
  const taxPercent = releaseForm.value.taxEnabled ? Math.max(0, Math.min(100, Number(releaseForm.value.taxPercent || 0))) : 0
  const taxAmount = Number(((taxableTotal * taxPercent) / 100).toFixed(2))
  const finalTotalWithProducts = Math.max(0, taxableTotal + taxAmount + tipAmount)
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
    Number((shareBaseTotal - workerShareBase + (tipAmount - allocatedTipTotal) - Math.min(servicesTotal, customerDiscountAmount + manualDiscountAmount)).toFixed(2))
  )
  return {
    serviceListSubtotal,
    servicesTotal,
    productsTotal,
    customerScore,
    customerDiscountPercent,
    facilityDiscountAmount,
    customerDiscountAmount,
    manualDiscountAmount,
    discountAmount,
    taxPercent,
    taxAmount,
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
  if (Number(releaseForm.value.chequeAmount || 0) > 0) parts.push(`${Number(releaseForm.value.chequeAmount || 0).toLocaleString('fa-IR')} تومان`)
  return parts.length ? parts.join(' | ') : 'جزئیات ثبت نشده'
})
watch(() => releaseForm.value.paymentMethod, (value) => {
  if (value !== 'manual') return
  const finalTotal = Math.max(0, Number(releaseSummary.value.finalTotal || 0))
  if (Number(releaseForm.value.manualCashAmount || 0) <= 0 && Number(releaseForm.value.manualSecondaryAmount || 0) <= 0) {
    releaseForm.value.manualCashAmount = Math.round(finalTotal)
    releaseForm.value.manualSecondaryAmount = 0
  }
})
const buildInvoicePdf = async () => {
  if (!invoiceTemplateRef.value) return false
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
        image: { type: 'png', quality: 1 },
        html2canvas: {
          scale: invoiceIsThermal.value ? 4 : 3,
          useCORS: true,
          backgroundColor: '#ffffff',
          logging: false,
          scrollX: 0,
          scrollY: 0,
          windowWidth: invoiceTemplateRef.value.scrollWidth,
          windowHeight: invoiceTemplateRef.value.scrollHeight
        },
        jsPDF: { unit: 'mm', format: invoicePageMetrics.value.format, orientation: 'portrait' },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      })
      .from(invoiceTemplateRef.value)
      .toPdf()
    const pdf = await worker.get('pdf')
    const blob = pdf.output('blob')
    invoicePdfUrl.value = URL.createObjectURL(blob)
    return true
  } catch (error) {
    console.error('buildInvoicePdf error:', error)
    invoiceErrorMessage.value = 'ساخت فایل فاکتور ناموفق بود.'
    return false
  } finally {
    invoiceGenerating.value = false
  }
}
const openInvoicePreviewModal = async () => {
  showInvoicePreviewModal.value = true
  await nextTick()
}
const downloadInvoicePdf = async () => {
  const ready = invoicePdfUrl.value ? true : await buildInvoicePdf()
  if (!ready || !invoicePdfUrl.value) return
  const anchor = document.createElement('a')
  anchor.href = invoicePdfUrl.value
  anchor.download = `${invoiceFileLabel.value}.pdf`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}
const printInvoiceHtml = async () => {
  invoiceErrorMessage.value = ''
  if (!invoiceTemplateRef.value) {
    invoiceErrorMessage.value = 'محتوای فاکتور برای چاپ آماده نیست.'
    notifyError(invoiceErrorMessage.value, { title: 'چاپ ناموفق' })
    return
  }
  try {
    invoiceGenerating.value = true
    await nextTick()
    await printHtmlElement(invoiceTemplateRef.value, invoicePrintPageOptions.value)
  } catch (error) {
    console.error('printInvoiceHtml error:', error)
    invoiceErrorMessage.value = resolvePrintErrorMessage(error)
    notifyError(invoiceErrorMessage.value, { title: 'چاپ ناموفق' })
  } finally {
    invoiceGenerating.value = false
  }
}
const confirmReleaseVehicle = async () => {
  if (!releaseCandidate.value?.id) return
  if (jobEditMode.value) {
    await persistJobAdjust()
    return
  }
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
      assigned_workers: selectedAssignedWorkers.value.map((worker) => ({
        id: Number(worker.id || 0),
        name: String(worker.name || '').trim(),
        worker_share_percent: Math.max(0, Math.min(100, Number(worker.worker_share_percent ?? 0)))
      })).filter((worker) => worker.id > 0),
      tip_amount: Math.max(0, Number(releaseForm.value.tipAmount || 0)),
      manual_discount_total: Math.max(0, Number(releaseForm.value.manualDiscountTotal || 0)),
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
      cheque_amount: usesChequeDetails ? Number(releaseForm.value.chequeAmount || 0) : undefined,
      credit_due_date: (['credit', 'cheque'].includes(releaseForm.value.paymentMethod) || usesChequeDetails) ? parseJalaliToIso(releaseForm.value.creditDueDate) || undefined : undefined,
      bonus_penalty_adjustments: (releaseForm.value.bonusPenaltyAdjustments || [])
        .map((item) => ({
          worker_id: Number(item.worker_id || 0),
          bonus: Math.max(0, Number(item.bonus || 0)),
          penalty: Math.max(0, Number(item.penalty || 0))
        }))
        .filter((item) => item.worker_id > 0 && (item.bonus > 0 || item.penalty > 0)),
      bonus_penalty_note: String(releaseForm.value.bonusPenaltyNote || '').trim() || undefined,
      sms_notifications_enabled: Boolean(releaseForm.value.smsNotificationsEnabled)
    })
    const idx = vehicleStore.vehicles.findIndex((item) => item.id === releaseCandidate.value.id)
    if (idx >= 0) vehicleStore.vehicles[idx] = data
    closeReleaseModal({ force: true })
  } catch (error) {
    console.error('confirmReleaseVehicle error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ترخیص خودرو ناموفق بود.'), { title: 'خطا در ترخیص خودرو' })
  } finally {
    releaseSubmitting.value = false
  }
}

const buildJobAdjustPayload = () => ({
  assigned_workers: selectedAssignedWorkers.value.map((worker) => ({
    id: Number(worker.id || 0),
    name: String(worker.name || '').trim(),
    worker_share_percent: Math.max(0, Math.min(100, Number(worker.worker_share_percent ?? 0)))
  })).filter((worker) => worker.id > 0),
  worker_share_distribution: (releaseForm.value.assignedWorkers || []).map((worker) => ({
    id: Number(worker.id || 0),
    worker_share_percent: Math.max(0, Math.min(100, Number(worker.worker_share_percent ?? 0)))
  })).filter((worker) => worker.id > 0),
  tip_amount: Math.max(0, Number(releaseForm.value.tipAmount || 0))
})

const persistJobAdjust = async () => {
  if (!releaseCandidate.value?.id || releaseSubmitting.value) return
  if (releaseForm.value.assignedWorkers.length && !selectedAssignedWorkers.value.length) {
    notifyWarning('حداقل یک نیرو انتخاب کنید.', { title: 'ویرایش نیرو' })
    return
  }
  try {
    releaseSubmitting.value = true
    const { data } = await api.patch(`/vehicles/${releaseCandidate.value.id}/job-adjust/`, buildJobAdjustPayload())
    const idx = vehicleStore.vehicles.findIndex((item) => Number(item.id) === Number(data?.id))
    if (idx >= 0) vehicleStore.vehicles[idx] = data
    vehicleStore.selectedVehicle = data
    closeReleaseModal({ force: true })
    showVehicleDetailsModal.value = false
  } catch (error) {
    console.error('persistJobAdjust error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ویرایش سفارش ناموفق بود.'), { title: 'خطا در ویرایش سفارش' })
  } finally {
    releaseSubmitting.value = false
  }
}

const editSelectedVehicleWorkers = async () => {
  if (!selectedVehicle.value?.id) return
  jobEditMode.value = 'workers'
  await openReleaseModal({
    ...selectedVehicle.value,
    statusKey: selectedVehicle.value.status,
    plateDisplay: selectedVehicle.value.plate_number,
    plateLeft: selectedVehicle.value.plate_left,
    plateLetter: selectedVehicle.value.plate_letter,
    plateMid: selectedVehicle.value.plate_mid,
    plateRight: selectedVehicle.value.plate_right,
    plateType: selectedVehicle.value.plate_type
  })
  openReleaseWorkerEditor()
}

const editSelectedVehicleTip = async () => {
  const vehicle = selectedVehicle.value
  if (!vehicle?.id) return
  const currentTip = Number(vehicle.job?.tip_amount || 0)
  const rawValue = window.prompt('مبلغ انعام جدید را وارد کنید', String(Math.round(currentTip)))
  if (rawValue === null) return
  const nextTip = Math.max(0, parseMoneyInput(rawValue))
  try {
    const { data } = await api.patch(`/vehicles/${vehicle.id}/job-adjust/`, { tip_amount: nextTip })
    const idx = vehicleStore.vehicles.findIndex((item) => Number(item.id) === Number(data?.id))
    if (idx >= 0) vehicleStore.vehicles[idx] = data
    vehicleStore.selectedVehicle = data
  } catch (error) {
    console.error('editSelectedVehicleTip error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ویرایش انعام ناموفق بود.'), { title: 'خطا در ویرایش انعام' })
  }
}
const handleStepOneContinue = async (payload) => {
  if (stepSubmitting.value) return
  stepSubmitting.value = true
  stepTransitionLoading.value = true
  try {
    const payloadWithSmsDefault = {
      ...payload,
      smsNotificationsEnabled: payload?.smsNotificationsEnabled ?? payload?.sms_notifications_enabled ?? vehicleAutoSmsEnabled.value,
      smsAutoSendEnabled: vehicleAutoSmsEnabled.value
    }
    if (vehicleEditFlow.value) {
      const currentStatus = vehicleDraft.value?.status || selectedVehicle.value?.status || 'ready_to_settle'
      const savedVehicle = await saveVehicle({ vehicle: { ...payloadWithSmsDefault, id: vehicleDraft.value?.id } }, currentStatus)
      vehicleDraft.value = {
        ...mapVehicleToDraft(savedVehicle),
        aiSessionId: payload.aiSessionId,
        aiRawText: payload.aiRawText,
        aiPersianText: payload.aiPersianText,
        aiConvertedPlate: payload.aiConvertedPlate,
        aiConvertedPlateLeft: payload.aiConvertedPlateLeft,
        aiConvertedPlateLetter: payload.aiConvertedPlateLetter,
        aiConvertedPlateMid: payload.aiConvertedPlateMid,
        aiConvertedPlateRight: payload.aiConvertedPlateRight,
        aiConvertedPlateType: payload.aiConvertedPlateType,
        aiImageBase64: payload.aiImageBase64,
        aiConfidence: payload.aiConfidence,
        aiLatencyMs: payload.aiLatencyMs,
        tariffType: payload.tariffType
      }
      modalStep.value = 2
      return
    }
    const plateStatus = await fetchPlateBlockedStatus(payload)
    if (plateStatus.is_blocked) {
      vehicleDraft.value = { ...payloadWithSmsDefault, is_plate_blocked: true }
      modalStep.value = 2
      return
    }
    const savedVehicle = await saveVehicle({ vehicle: payload }, 'entered')
    vehicleDraft.value = {
      ...mapVehicleToDraft(savedVehicle),
      smsNotificationsEnabled: savedVehicle?.sms_notifications_enabled ?? payloadWithSmsDefault.smsNotificationsEnabled,
      smsAutoSendEnabled: vehicleAutoSmsEnabled.value,
      detectedPlate: payload.detectedPlate,
      detectedPlateLeft: payload.detectedPlateLeft,
      detectedPlateLetter: payload.detectedPlateLetter,
      detectedPlateMid: payload.detectedPlateMid,
      detectedPlateRight: payload.detectedPlateRight,
      detectedPlateType: payload.detectedPlateType,
      aiSessionId: payload.aiSessionId,
      aiRawText: payload.aiRawText,
      aiPersianText: payload.aiPersianText,
      aiConvertedPlate: payload.aiConvertedPlate,
      aiConvertedPlateLeft: payload.aiConvertedPlateLeft,
      aiConvertedPlateLetter: payload.aiConvertedPlateLetter,
      aiConvertedPlateMid: payload.aiConvertedPlateMid,
      aiConvertedPlateRight: payload.aiConvertedPlateRight,
      aiConvertedPlateType: payload.aiConvertedPlateType,
      aiImageBase64: payload.aiImageBase64,
      aiConfidence: payload.aiConfidence,
      aiLatencyMs: payload.aiLatencyMs,
      tariffType: payload.tariffType,
      customerScore: Number(savedVehicle?.customer_score ?? payload.customerScore ?? 0),
      customerLoyaltyVisitCount: Number(savedVehicle?.customer_loyalty_visit_count ?? payload.customerLoyaltyVisitCount ?? 0),
      customerLoyaltyDiscountPercent: Number(savedVehicle?.customer_loyalty_discount_percent ?? payload.customerLoyaltyDiscountPercent ?? 0)
    }
    modalStep.value = 2
  } catch (error) {
    console.error('continue step one error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ذخیره اطلاعات مرحله اول ناموفق بود.'), { title: 'خطا در ثبت خودرو' })
  } finally {
    stepSubmitting.value = false
    window.setTimeout(() => { stepTransitionLoading.value = false }, 120)
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
    || (
      !Boolean(payload?.vehicle?.isPieceWash)
      && (
        (
          String(payload?.vehicle?.model || '').trim() === '1111'
          && String(payload?.vehicle?.color || '').trim() === '1111'
        )
        || String(payload?.vehicle?.plate || payload?.vehicle?.plate_number || '').trim() === '1111'
      )
    )
  const isPieceWash = Boolean(payload?.vehicle?.isPieceWash)
  const aiConfidence = normalizeAiConfidence(payload?.vehicle?.aiConfidence)

  return {
    plate_number: isPieceWash ? '' : (isAnonymous ? '' : rebuiltPlate),
    plate_left: isPieceWash || isAnonymous || plateType === 'motorcycle' ? '' : left,
    plate_letter: isPieceWash || isAnonymous ? '' : letter,
    plate_mid: isPieceWash || isAnonymous ? '' : mid,
    plate_right: isPieceWash || isAnonymous || plateType === 'motorcycle' ? '' : right,
    plate_type: plateType,
    tariff_type: String(payload?.vehicle?.tariffType || payload?.vehicle?.tariff_type || 'type_1').trim() || 'type_1',
    car_model: isPieceWash ? 'قطعه‌شویی' : (isAnonymous ? '1111' : String(payload?.vehicle?.model || '').trim()),
    car_color: isPieceWash ? '-' : (isAnonymous ? '1111' : String(payload?.vehicle?.color || '').trim()),
    driver_name: (payload?.vehicle?.driver || '').trim(),
    driver_gender: ['male', 'female'].includes(String(payload?.vehicle?.driverGender || payload?.vehicle?.driver_gender || '').trim())
      ? String(payload?.vehicle?.driverGender || payload?.vehicle?.driver_gender).trim()
      : '',
    driver_phone: (payload?.vehicle?.mobile || '').trim(),
    sms_notifications_enabled: (
      payload?.vehicle?.smsAutoSendEnabled !== false
      && payload?.vehicle?.sms_auto_send_enabled !== false
      && payload?.vehicle?.sms_vehicle_auto_send_enabled !== false
      && payload?.vehicle?.smsNotificationsEnabled !== false
    ),
    notes: isPieceWash ? '' : (payload?.vehicle?.note || '').trim(),
    is_piece_wash: isPieceWash,
    piece_details: (payload?.vehicle?.pieceDetails || '').trim(),
    status,
    ...(payload?.staff || Array.isArray(payload?.staffMembers)
      ? {
          worker_id: payload?.staff?.id || null,
          worker_name: payload?.staff?.name || ''
        }
      : {}),
    staff_members: Array.isArray(payload?.staffMembers)
      ? payload.staffMembers.map((item) => ({
        id: item?.id,
        name: item?.name || '',
        worker_share_percent: Math.max(0, Math.min(100, Number(item?.worker_share_percent || 0)))
      }))
      : undefined,
    services: Array.isArray(payload?.services) ? payload.services : undefined,
    products: Array.isArray(payload?.products) ? payload.products : undefined,
    manual_discount_total: (payload?.manual_discount_total != null || payload?.manualDiscountTotal != null)
      ? Number((payload?.manual_discount_total ?? payload?.manualDiscountTotal) || 0)
      : undefined,
    apply_loyalty_discount: (payload?.apply_loyalty_discount != null || payload?.applyLoyaltyDiscount != null)
      ? ((payload?.apply_loyalty_discount ?? payload?.applyLoyaltyDiscount) !== false)
      : undefined,
    share: payload?.share || undefined,
    intake_source: payload?.vehicle?.aiImageBase64 ? 'ai' : undefined,
    ai_confidence: payload?.vehicle?.aiImageBase64 ? aiConfidence : undefined,
    ai_session_id: payload?.vehicle?.aiImageBase64 ? (payload?.vehicle?.aiSessionId || '') : undefined,
    ai_raw_text: payload?.vehicle?.aiImageBase64 ? (payload?.vehicle?.aiRawText || '') : undefined,
    ai_persian_text: payload?.vehicle?.aiImageBase64 ? (payload?.vehicle?.aiPersianText || '') : undefined,
    ai_converted_plate: payload?.vehicle?.aiImageBase64 ? rebuiltPlate : undefined,
    ai_converted_plate_left: payload?.vehicle?.aiImageBase64 ? (plateType === 'motorcycle' ? '' : left) : undefined,
    ai_converted_plate_letter: payload?.vehicle?.aiImageBase64 ? letter : undefined,
    ai_converted_plate_mid: payload?.vehicle?.aiImageBase64 ? mid : undefined,
    ai_converted_plate_right: payload?.vehicle?.aiImageBase64 ? (plateType === 'motorcycle' ? '' : right) : undefined,
    ai_converted_plate_type: payload?.vehicle?.aiImageBase64 ? (payload?.vehicle?.aiConvertedPlateType || plateType) : undefined,
    ai_image_base64: payload?.vehicle?.aiImageBase64 || undefined,
    ai_latency_ms: payload?.vehicle?.aiImageBase64 ? (payload?.vehicle?.aiLatencyMs ?? null) : undefined,
    blocked_plate_payment_confirmed: Boolean(payload?.blocked_plate_payment_confirmed)
  }
}

const compactVehiclePayload = (body) => Object.fromEntries(
  Object.entries(body).filter(([, value]) => value !== undefined)
)

const fetchPlateBlockedStatus = async (payload) => {
  const isAnonymous = Boolean(payload?.isAnonymous || payload?.vehicle?.isAnonymous)
    || (
      String(payload?.model || payload?.vehicle?.model || '').trim() === '1111'
      && String(payload?.color || payload?.vehicle?.color || '').trim() === '1111'
    )
  if (isAnonymous || payload?.isPieceWash || payload?.vehicle?.isPieceWash) return { is_blocked: false }
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
  const { data } = await api.get('/vehicles/plate-status/', { params, meta: { trackLoading: false } })
  return data || { is_blocked: false }
}

const saveVehicle = async (payload, status) => {
  const body = compactVehiclePayload(buildCreateOrUpdatePayload(payload, status))
  const editingId = payload?.vehicle?.id || vehicleDraft.value?.id || null
  if (editingId) {
    // Image/OCR audit already ran on create; re-uploading slows assign/refer a lot.
    delete body.ai_image_base64
    delete body.ai_raw_text
    delete body.ai_persian_text
    delete body.ai_converted_plate
    delete body.ai_converted_plate_left
    delete body.ai_converted_plate_letter
    delete body.ai_converted_plate_mid
    delete body.ai_converted_plate_right
    delete body.ai_converted_plate_type
    delete body.ai_session_id
    delete body.ai_confidence
    delete body.ai_latency_ms
    delete body.intake_source
    const { data } = await api.patch(`/vehicles/${editingId}/`, body, { meta: { trackLoading: false } })
    vehicleStore.upsertVehicle(data)
    return data
  }
  const { data } = await api.post('/vehicles/', body, { meta: { trackLoading: false } })
  vehicleStore.upsertVehicle(data)
  return data
}

const refreshVehicleBoard = async () => {
  await fetchVehiclesForActiveRange()
  if (selectedVehicle.value?.id) {
    await vehicleStore.fetchVehicleDetail(selectedVehicle.value.id)
  }
}

const handleStepOneRefer = async (payload) => {
  if (stepSubmitting.value) return
  stepSubmitting.value = true
  stepTransitionLoading.value = true
  try {
    const plateStatus = await fetchPlateBlockedStatus(payload)
    if (plateStatus.is_blocked) {
      vehicleDraft.value = { ...payload, is_plate_blocked: true }
      modalStep.value = 2
      return
    }
    await saveVehicle({ vehicle: payload }, 'entered')
    closeVehicleModal({ force: true })
    void refreshVehicleCardsFromDatabase()
  } catch (error) {
    console.error('refer step one error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ثبت ارجاع ناموفق بود.'), { title: 'خطا در ثبت ارجاع' })
  } finally {
    stepSubmitting.value = false
    window.setTimeout(() => { stepTransitionLoading.value = false }, 120)
  }
}

const handleStepTwoBack = async () => {
  if (stepSubmitting.value) return
  stepTransitionLoading.value = true
  await nextTick()
  modalStep.value = 1
  window.setTimeout(() => { stepTransitionLoading.value = false }, 120)
}

const resolveAssignStatus = () => {
  const currentStatus = vehicleDraft.value?.status || selectedVehicle.value?.status || 'ready_to_settle'
  // Editing a released visit must keep released; completing a referred/incomplete
  // entry (entered/assigned/in_progress) must advance to ready_to_settle so the
  // board moves it from «در انتظار تکمیل» to «در حال انجام».
  if (vehicleEditFlow.value === 'released') return currentStatus
  if (['entered', 'assigned', 'in_progress'].includes(currentStatus)) return 'ready_to_settle'
  return currentStatus || 'ready_to_settle'
}

const handleStepTwoAssign = async (payload) => {
  if (stepSubmitting.value) return
  stepSubmitting.value = true
  stepTransitionLoading.value = true
  try {
    if (vehicleEditFlow.value) {
      const nextStatus = resolveAssignStatus()
      const savedVehicle = await saveVehicle(payload, nextStatus)
      if (vehicleEditFlow.value === 'released') {
        closeVehicleModal({ force: true })
        await openReleaseModal({
          ...savedVehicle,
          statusKey: savedVehicle.status,
          plateDisplay: savedVehicle.plate_number,
          plateLeft: savedVehicle.plate_left,
          plateLetter: savedVehicle.plate_letter,
          plateMid: savedVehicle.plate_mid,
          plateRight: savedVehicle.plate_right,
          plateType: savedVehicle.plate_type
        })
      } else {
        closeVehicleModal({ force: true })
        void refreshVehicleCardsFromDatabase()
      }
      return
    }
    await saveVehicle(payload, 'ready_to_settle')
    closeVehicleModal({ force: true })
    void refreshVehicleCardsFromDatabase()
  } catch (error) {
    console.error('assign step two error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'ثبت تخصیص ناموفق بود.'), { title: 'خطا در ثبت تخصیص' })
  } finally {
    stepSubmitting.value = false
    window.setTimeout(() => { stepTransitionLoading.value = false }, 120)
  }
}
const cars = computed(() => vehicles.value.map((item) => {
  const plateLeftKey = String(item.plate_left || '').trim()
  const plateLetterKey = String(item.plate_letter || '').trim()
  const plateMidKey = String(item.plate_mid || '').trim()
  const plateRightKey = String(item.plate_right || '').trim()
  const plateDisplay = String(item.plate_number || '').trim() || '-'
  const sortTime = item.status === 'released'
    ? (item.released_at || item.check_in_at)
    : item.check_in_at
  const driverName = item.driver_name || ''
  const driverPhone = item.driver_phone || ''
  const model = item.car_model || ''
  const workerName = assignedWorkersLabel(item.job)
  const searchText = [
    plateLeftKey,
    plateLetterKey,
    plateMidKey,
    plateRightKey,
    plateDisplay,
    model,
    driverName,
    driverPhone,
    workerName
  ].join(' ').toLowerCase()
  return {
    id: item.id,
    admission_number: item.admission_number,
    admissionNumber: item.admission_number,
    statusKey: item.status,
    queueBucket: item.status === 'released' ? 'released' : item.status === 'cancelled' ? 'cancelled' : item.status === 'ready_to_settle' ? 'in_progress' : 'entered',
    status: item.status === 'cancelled' ? 'لغو' : item.status === 'released' ? 'ترخیص شده' : item.status === 'ready_to_settle' ? 'در حال انجام' : 'در انتظار تکمیل',
    color: item.status === 'cancelled' ? '#ef4444' : item.status === 'released' ? '#f59e0b' : item.status === 'in_progress' ? '#0058be' : '#16a34a',
    badgeBg: '#eef2ff',
    badgeText: '#334155',
    time: formatDateTime(item.check_in_at),
    sortTime,
    sortMs: Date.parse(sortTime) || 0,
    plateLeft: plateLeftKey || '--',
    plateLetter: plateLetterKey || '-',
    plateMid: plateMidKey || '---',
    plateRight: plateRightKey || '--',
    plateLeftKey,
    plateLetterKey,
    plateMidKey,
    plateRightKey,
    plateType: item.plate_type || 'car',
    tariff_type: item.tariff_type || 'type_1',
    tariffType: item.tariff_type || 'type_1',
    model,
    colorName: item.car_color,
    plateDisplay,
    searchText,
    service: Array.isArray(item.job?.service_lines) && item.job.service_lines.length
      ? item.job.service_lines.map((line) => line.service_name || 'خدمت').join('، ')
      : 'خدمت ثبت نشده',
    driverName,
    driver_gender: item.driver_gender,
    driverGender: item.driver_gender,
    driverPhone,
    isPlateBlocked: Boolean(item.is_plate_blocked),
    customerScore: Number(item.customer_score || 0),
    customerLoyaltyDiscountPercent: Number(item.customer_loyalty_discount_percent || 0),
    finalTotal: item.job?.final_total || item.job?.services_total || 0,
    carwashShare: item.job?.carwash_share_amount || 0,
    workerName,
    action: item.status === 'released' ? 'ترخیص انجام شد' : item.status === 'ready_to_settle' ? 'ترخیص خودرو' : item.status === 'cancelled' ? 'لغو شده' : 'تکمیل اطلاعات',
    actionClass: item.status === 'ready_to_settle' ? 'action-release' : item.status === 'released' || item.status === 'cancelled' ? 'action-done' : 'action-complete'
  }
}))

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
  const weightMap = { entered: 0, in_progress: 1, released: 3, cancelled: 4 }
  const query = debouncedSearch.value.trim().toLowerCase()
  const plate = hasDebouncedPlateFilter.value ? debouncedPlateFilter.value : null
  const bucket = activeFilter.value
  const items = []
  for (const item of cars.value) {
    if (bucket !== 'all' && item.queueBucket !== bucket) continue
    if (query && !item.searchText.includes(query)) continue
    if (plate && !matchesPlateFilter(item, plate)) continue
    items.push(item)
  }
  items.sort((first, second) => {
    const weightDiff = (weightMap[first.queueBucket] ?? 9) - (weightMap[second.queueBucket] ?? 9)
    if (weightDiff !== 0) return weightDiff
    return first.sortMs - second.sortMs
  })
  return items
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
  const plateNumber = String(selectedVehicle.value.plate_number || '').trim()
  const hasParts = [
    selectedVehicle.value.plate_left,
    selectedVehicle.value.plate_letter,
    selectedVehicle.value.plate_mid,
    selectedVehicle.value.plate_right
  ].some((part) => String(part || '').trim())
  const model = String(selectedVehicle.value.car_model || '').trim()
  const color = String(selectedVehicle.value.car_color || '').trim()
  const isAnonymous = (model === '1111' && color === '1111') || selectedVehicle.value.is_piece_wash
  if (isAnonymous || (!plateNumber && !hasParts)) {
    notifyError('مراجعه ناشناس یا بدون پلاک قابل بلاک نیست. یک خودرو با پلاک واقعی ثبت کنید.', {
      title: 'خطا در بلاک پلاک'
    })
    return
  }
  try {
    const { data } = await api.post(`/vehicles/${selectedVehicle.value.id}/block-plate/`, {})
    const vehiclePayload = data?.vehicle
    if (vehiclePayload?.id) {
      syncVehicleSnapshot({
        ...vehiclePayload,
        is_plate_blocked: true,
        blocked_plate_id: data?.id || vehiclePayload.blocked_plate_id || null
      })
    } else {
      selectedVehicle.value = {
        ...selectedVehicle.value,
        is_plate_blocked: Boolean(data?.is_blocked),
        blocked_plate_id: data?.id || selectedVehicle.value.blocked_plate_id || null
      }
      const idx = vehicleStore.vehicles.findIndex((item) => item.id === selectedVehicle.value.id)
      if (idx >= 0) {
        vehicleStore.vehicles[idx] = {
          ...vehicleStore.vehicles[idx],
          is_plate_blocked: true,
          blocked_plate_id: data?.id || vehicleStore.vehicles[idx].blocked_plate_id || null
        }
      }
    }
    await refreshVehicleBoard()
    if (selectedVehicle.value?.id) {
      await vehicleStore.fetchVehicleDetail(selectedVehicle.value.id)
    }
  } catch (error) {
    console.error('blockSelectedVehiclePlate error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'بلاک کردن پلاک ناموفق بود.'), { title: 'خطا در بلاک پلاک' })
  }
}

const resolveBlockedPlateId = async (vehicle) => {
  if (vehicle?.blocked_plate_id) return vehicle.blocked_plate_id
  if (!vehicle) return null
  try {
    const { data } = await api.get('/vehicles/plate-status/', {
      params: {
        plate_number: vehicle.plate_number || '',
        plate_left: vehicle.plate_left || '',
        plate_letter: vehicle.plate_letter || '',
        plate_mid: vehicle.plate_mid || '',
        plate_right: vehicle.plate_right || ''
      },
      meta: { trackLoading: false, showErrorToast: false }
    })
    return data?.id || null
  } catch {
    return null
  }
}

const unblockSelectedVehiclePlate = async () => {
  if (!selectedVehicle.value?.id) return
  try {
    const blockedId = await resolveBlockedPlateId(selectedVehicle.value)
    if (!blockedId) {
      notifyError('رکورد بلاک برای این پلاک پیدا نشد.', { title: 'خطا در خارج کردن از بلاک' })
      return
    }
    await api.post(`/vehicles/blocked-plates/${blockedId}/unblock/`, {})
    syncVehicleSnapshot({
      ...selectedVehicle.value,
      is_plate_blocked: false,
      blocked_plate_id: null
    })
    await refreshVehicleBoard()
    if (selectedVehicle.value?.id) {
      await vehicleStore.fetchVehicleDetail(selectedVehicle.value.id)
    }
  } catch (error) {
    console.error('unblockSelectedVehiclePlate error:', error?.response?.data || error)
    notifyError(apiErrorText(error, 'خارج کردن پلاک از لیست سیاه ناموفق بود.'), { title: 'خطا در خارج کردن از بلاک' })
  }
}

const loadVehicleSmsSettings = async () => {
  try {
    const { data } = await api.get('/services/general-settings/', {
      meta: { trackLoading: false, showErrorToast: false }
    })
    vehicleAutoSmsEnabled.value = data?.sms_vehicle_auto_send_enabled !== false
  } catch {
    vehicleAutoSmsEnabled.value = true
  }
}

onMounted(() => {
  fetchVehiclesForActiveRange()
  startVehicleCardsAutoRefresh()
  loadVehicleSmsSettings()
  syncReleaseMobileState()
  window.addEventListener('resize', syncReleaseMobileState)
})
watch(
  () => [dateRangeMode.value, customDateRange.value.startJalali, customDateRange.value.endJalali],
  () => {
    fetchVehiclesForActiveRange()
  }
)
watch(hasOperatorModalOpen, (isOpen) => {
  if (isOpen) lockBodyScrollForModal()
  else unlockBodyScrollForModal()
}, { immediate: true })
watch(
  () => [invoiceLayout.value.preset, invoiceLayout.value.thermalWidthMm, invoiceLayout.value.thermalHeightMm],
  () => {
    if (!showInvoicePreviewModal.value) return
    revokeInvoicePdfUrl()
  }
)
onBeforeUnmount(() => {
  unlockBodyScrollForModal()
  if (vehicleCardsRefreshTimer.value) window.clearInterval(vehicleCardsRefreshTimer.value)
  if (searchDebounceTimer) window.clearTimeout(searchDebounceTimer)
  if (plateDebounceTimer) window.clearTimeout(plateDebounceTimer)
  if (invoiceRenderTimer.value) window.clearTimeout(invoiceRenderTimer.value)
  revokeInvoicePdfUrl()
  window.removeEventListener('resize', syncReleaseMobileState)
})
</script>

<style scoped>
.dashboard-content { min-width: 0; width: 100%; max-width: 100%; overflow-x: hidden; }
.plate-search-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 4px 6px;
  border: 1px solid #dbe5f0;
  border-radius: 12px;
  background: linear-gradient(180deg, #fdfefe, #f3f7fb);
}
.plate-type-inline {
  height: 34px;
  min-width: 72px;
  flex: 0 0 auto;
  border: 1px solid #cbd5e1;
  border-radius: 9px;
  padding: 0 8px;
  background: #fff;
  font-size: 11px;
  color: #334155;
}
.plate-search-editor {
  flex: 0 1 auto;
  min-width: 0;
  max-width: 280px;
}
.plate-search-bar :deep(.plate-editor) { gap: 0; }
.plate-search-bar :deep(.manual-plate-badge) { max-width: 250px; }
.plate-search-bar :deep(.plate-editor-dense .plate-input) { height: 28px; font-size: 14px; }
.plate-search-bar :deep(.plate-editor-dense .manual-plate-car .plate-input.right),
.plate-search-bar :deep(.plate-editor-dense .manual-plate-car .plate-input.left) { width: 36px; }
.plate-search-bar :deep(.plate-editor-dense .manual-plate-car .plate-input.mid) { width: 48px; }
.plate-search-bar :deep(.plate-editor-dense .manual-plate-car .plate-input.letter) { width: 48px; min-width: 44px; }
.plate-search-bar :deep(.plate-editor-dense .blue-input) { width: 34px !important; font-size: 13px; }
.plate-search-bar :deep(.plate-editor-dense .manual-plate-blue) { min-width: 34px; font-size: 13px; padding: 4px 0; }
.plate-clear-btn {
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  border: 1px solid #cbd5e1;
  border-radius: 9px;
  background: #fff;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  line-height: 1;
}
.plate-clear-btn:disabled { opacity: .4; cursor: not-allowed; }
.primary-btn { height: 40px; border: none; border-radius: 12px; color: #fff; font-weight: 700; padding: 0 16px; background: linear-gradient(135deg, #0058be 0%, #57dffe 100%); cursor: pointer;margin-right: 3%; }
.vehicle-toolbar { display: flex; align-items: center; gap: 10px; min-width: 0; max-width: 100%; overflow-x: auto; overflow-y: hidden; padding-bottom: 8px; }
.vehicle-toolbar > * { flex: 0 0 auto; }
.vehicle-toolbar > .primary-btn { margin-right: 0; }
.date-range-chips { display: flex; align-items: center; gap: 8px; flex: 0 0 auto; }
.date-chip { height: 36px; border: 1px solid #d8e2ee; border-radius: 999px; padding: 0 14px; background: #f8fafc; color: #64748b; font-size: 12px; font-weight: 900; white-space: nowrap; cursor: pointer; }
.date-chip.active { border-color: #0ea5e9; background: #e0f2fe; color: #075985; }
.custom-range-chip { background: #fff; color: #334155; }
.active-range-label { height: 30px; display: inline-flex; align-items: center; padding: 0 10px; border-radius: 999px; background: #eef2f7; color: #475569; font-size: 11px; font-weight: 800; white-space: nowrap; }
.filters { display: flex; gap: 10px; overflow-x: auto; overflow-y: hidden; padding-bottom: 8px; flex-wrap: nowrap; align-items: center; }
.filters > * { flex: 0 0 auto; }
.filters > .primary-btn { width: auto; margin-right: 0; }
.chip { border: none; border-radius: 999px; padding: 11px 18px; background: #e6e8ea; color: #4b5563;font-size:13px; font-weight: 800; white-space: nowrap; }
.chip.active { background: #0058be; color: #fff; }
.date-range-overlay { align-items: flex-start; padding-top: 88px; }
.date-range-panel { width: min(440px, 100%); overflow: visible; }
.date-range-modal-body { display: grid; gap: 12px; padding: 18px; background: #f8fbff; }
.date-range-field { display: grid; gap: 7px; padding: 12px; border: 1px solid #d8e6f7; border-radius: 16px; background: #fff; }
.date-range-field span { color: #475569; font-size: 12px; font-weight: 900; }
.date-range-field :deep(.base-date-picker) { width: 100%; }
.date-range-field :deep(.picker-input) { width: 100%; justify-content: space-between; }
.date-range-actions { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 18px 18px; background: #fff; }
.date-range-actions .primary-btn { margin-right: 0; }
.cards-grid { margin-top: 18px; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 16px; width: 100%; max-width: 100%; }
.car-card { min-width: 0; background: #fff; border-right: 4px solid #0058be; border-radius: 16px; padding: 14px; box-shadow: 0 6px 18px -14px rgba(15,23,42,.28); display: flex; flex-direction: column; gap: 10px; transition: border-color .12s ease; contain: content; content-visibility: auto; contain-intrinsic-size: 220px; }
.car-card:hover { box-shadow: 0 8px 20px -16px rgba(15,23,42,.32); }
.car-card.card-released { opacity: .7; }
.car-card.card-released:hover { box-shadow: 0 6px 18px -14px rgba(15,23,42,.28); }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.status { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: #475569; }
.dot { width: 8px; height: 8px; border-radius: 99px; }
.card-head-badges { display: inline-flex; align-items: center; gap: 6px; }
.blocked-chip { font-size: 10px; padding: 4px 9px; border-radius: 999px; font-weight: 800; background: #fee2e2; color: #991b1b; }
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
.release-panel { width: min(1420px, 100%); max-width: 100%; height: calc(100vh - 40px); max-height: calc(100vh - 40px); display: flex; flex-direction: column; overflow-y: auto; overflow-x: hidden; -webkit-overflow-scrolling: touch; background: #f7fbff; contain: content; }
.release-loading { min-height: 280px; display: flex; align-items: center; justify-content: center; color: #64748b; font-size: 14px; }
.release-modal-head{align-items:flex-start;gap:16px;padding:20px 24px;background:#fff}
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
.release-col { background: #fff; border: 1px solid rgba(191,215,255,.9); border-radius: 24px; padding: 18px; display: flex; flex-direction: column; min-height: 620px; box-shadow: 0 10px 24px -22px rgba(15,23,42,.45); contain: content; }
.release-products-col, .release-summary-col { border-right: 1px solid rgba(191,215,255,.85); }
.release-title-inline{display:flex;justify-content:space-between;align-items:center;gap:10px}
.service-picker-overlay{position:absolute;inset:0;z-index:8;display:flex;align-items:center;justify-content:center;padding:24px;background:rgba(15,23,42,.28)}
.service-picker-panel{width:min(920px,100%);max-height:min(720px,100%);display:grid;gap:18px;padding:22px;border-radius:28px;background:linear-gradient(180deg,#ffffff,#f5f9ff);border:1px solid #d8e6ff;box-shadow:0 28px 60px -34px rgba(15,23,42,.45);overflow:auto}
.service-picker-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}
.service-picker-head h4{margin:0;color:#0f172a;font-size:20px}
.service-picker-head p{margin:6px 0 0;color:#64748b;font-size:12px}
.service-picker-grid{display:flex;flex-wrap:wrap;gap:10px;align-content:flex-start}
.release-service-picker-grid{max-height:420px;overflow:auto;padding-inline-end:4px}
.service-bubble{display:grid;place-items:center;gap:1px;min-height:48px;border:1px solid #cfe1ff;border-radius:999px;padding:8px 16px;background:linear-gradient(180deg,#ffffff,#f3f8ff);color:#0f4c81;font-size:13px;font-weight:700;line-height:1.35;cursor:pointer;transition:.18s ease;white-space:normal}
.service-bubble-name,.service-bubble-price{display:block;max-width:100%;overflow-wrap:anywhere;text-align:center}
.service-bubble-price{color:#64748b;font-size:10px;font-weight:800;line-height:1.2}
.service-bubble.selected{border-color:#0ea5e9;background:linear-gradient(135deg,#0f4c81,#0ea5e9);color:#fff;box-shadow:0 18px 28px -22px rgba(14,165,233,.78)}
.service-bubble.selected .service-bubble-price{color:rgba(255,255,255,.82)}
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
.summary-stat-card{padding:14px;border-radius:18px;border:1px solid #d9e8ff;background:linear-gradient(180deg,#ffffff,#f5faff);display:flex;align-items:center;justify-content:space-between;gap:10px;min-width:0}
.summary-stat-card span{font-size:12px;color:#64748b;flex:0 1 auto;min-width:0}
.summary-stat-card strong{font-size:15px;color:#0f172a;text-align:left;flex:0 1 auto;min-width:0;overflow-wrap:anywhere}
.summary-stat-value{display:flex;flex-direction:column;align-items:flex-end;gap:2px;min-width:0}
.summary-stat-value strong{font-size:15px;color:#0f172a;text-align:left}
.summary-stat-card small,.summary-stat-value small{font-size:11px;color:#0f766e;font-weight:700}
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
.worker-selection-actions{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap}
.worker-selection-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.worker-select-card{border:1px solid #d5e5ff;border-radius:18px;padding:14px;background:#fff;display:grid;justify-items:start;gap:8px;text-align:right;transition:.2s ease;cursor:pointer}
.worker-select-card.selected{background:linear-gradient(180deg,#eff8ff,#dcf2ff);border-color:#7dd3fc;box-shadow:0 14px 28px -24px rgba(14,165,233,.7)}
.worker-select-card strong{font-size:14px;color:#0f172a}
.worker-select-card small{font-size:12px;color:#64748b}
.worker-select-check{width:28px;height:28px;border-radius:10px;background:#e2e8f0;color:#334155;display:inline-flex;align-items:center;justify-content:center;font-weight:800}
.worker-select-card.selected .worker-select-check{background:#0ea5e9;color:#fff}
.worker-editor-panel{width:min(980px,100%);border-radius:30px;background:linear-gradient(180deg,#ffffff 0%,#f6fbff 100%)}
.worker-editor-head h4{font-size:21px}
.worker-editor-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.worker-editor-summary article{border:1px solid #d9e8ff;border-radius:18px;padding:14px 16px;background:#fff;display:grid;gap:6px}
.worker-editor-summary span{font-size:12px;color:#64748b}
.worker-editor-summary strong{font-size:17px;color:#0f172a}
.worker-editor-search{display:grid;gap:7px;border:1px solid #d9e8ff;border-radius:18px;background:#fff;padding:12px 14px}
.worker-editor-search span{font-size:12px;color:#64748b;font-weight:900}
.worker-editor-search input{height:42px;border:1px solid #dbe7f5;border-radius:14px;background:#f8fbff;color:#0f172a;padding:0 12px;font:inherit;font-size:13px;font-weight:800}
.worker-editor-search input:focus{outline:none;border-color:#38bdf8;box-shadow:0 0 0 3px rgba(56,189,248,.16);background:#fff}
.worker-editor-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;max-height:430px;overflow:auto;padding-inline-end:4px}
.worker-editor-card{border:1px solid #dbe7f5;border-radius:22px;padding:12px;background:#fff;display:grid;gap:12px;box-shadow:0 18px 38px -34px rgba(15,23,42,.45)}
.worker-editor-card.selected{border-color:#38bdf8;background:linear-gradient(180deg,#f0f9ff,#ffffff)}
.worker-editor-toggle{border:0;background:transparent;padding:0;display:grid;grid-template-columns:34px minmax(0,1fr);grid-template-areas:"check name" "check hint";gap:2px 10px;text-align:right;align-items:center;cursor:pointer}
.worker-editor-toggle span{grid-area:check;width:34px;height:34px;border-radius:12px;background:#e2e8f0;color:#334155;display:inline-flex;align-items:center;justify-content:center;font-weight:900}
.worker-editor-card.selected .worker-editor-toggle span{background:#0284c7;color:#fff}
.worker-editor-toggle strong{grid-area:name;color:#0f172a;font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.worker-editor-toggle small{grid-area:hint;color:#64748b;font-size:12px}
.worker-percent-field{display:grid;grid-template-columns:auto 88px minmax(0,1fr);gap:8px;align-items:center;border:1px solid #e2e8f0;border-radius:16px;padding:10px;background:#f8fbff}
.worker-percent-field span,.worker-percent-field small{font-size:12px;color:#64748b}
.worker-percent-field input{width:100%;height:36px;border:1px solid #cbd5e1;border-radius:12px;background:#fff;text-align:center;font-weight:800;color:#0f172a}
.worker-percent-field input:disabled{background:#eef2f7;color:#94a3b8}
.worker-editor-foot{position:sticky;bottom:0;background:linear-gradient(180deg,rgba(246,251,255,.7),#f6fbff);padding-top:10px}
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
.summary-input-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.release-secondary-grid-accordion{grid-template-columns:1fr}
.release-mobile-section{border:1px solid #dbe7f5;border-radius:14px;background:#fff;padding:10px}
.release-mobile-content{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.release-mobile-toggle{display:none}
.detail-field{margin-top:0;padding:14px;border:1px solid #d6e6ff;border-radius:18px;background:rgba(255,255,255,.8)}
.detail-field-wide{grid-column:span 2}
.release-sms-check{display:flex;align-items:center;gap:12px}
.release-sms-check.disabled{opacity:.62}
.release-sms-check input{width:18px;height:18px;accent-color:#2563eb}
.release-sms-check span{display:grid;gap:2px}
.release-sms-check small{color:#64748b;font-size:12px}
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
.invoice-modal-body{display:grid;grid-template-rows:auto minmax(0,1fr);gap:10px;padding:12px;min-height:0;min-width:0;flex:1;background:linear-gradient(180deg,#f8fbff,#edf5ff)}
.invoice-format-toolbar{display:grid;grid-template-columns:minmax(260px,1fr) auto auto;align-items:center;gap:10px;padding:10px;border-radius:18px;background:rgba(255,255,255,.9);border:1px solid #dbe7f5;box-shadow:0 10px 26px rgba(15,23,42,.06)}
.invoice-format-presets{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.invoice-format-chip{border:1px solid #dbe7f5;border-radius:14px;padding:8px 12px;background:linear-gradient(180deg,#fff,#eef6ff);color:#334155;font-weight:800;cursor:pointer;display:grid;gap:2px;text-align:right;min-width:0;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease,background .18s ease}
.invoice-format-chip:hover{transform:translateY(-1px);box-shadow:0 10px 22px rgba(15,23,42,.1)}
.invoice-format-chip strong{font-size:14px;line-height:1.25;overflow-wrap:anywhere}
.invoice-format-chip span{font-size:10px;color:#64748b;line-height:1.45;overflow-wrap:anywhere}
.invoice-format-chip.active{background:linear-gradient(135deg,#0f172a,#0f4c81 58%,#0ea5e9);border-color:#0f4c81;color:#fff;box-shadow:0 14px 28px rgba(14,116,144,.22)}
.invoice-format-chip.active span{color:rgba(255,255,255,.78)}
.invoice-thermal-size-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.invoice-thermal-size-grid label{display:grid;gap:6px}
.invoice-thermal-size-grid span{font-size:12px;color:#64748b}
.invoice-thermal-size-grid input{width:100%;min-width:0;border:1px solid #dbe7f5;border-radius:12px;padding:7px 9px;background:#fff;color:#0f172a;font-weight:800;box-sizing:border-box}
.invoice-modal-actions{display:flex;justify-content:flex-end;gap:6px;flex-wrap:nowrap;align-items:center}
.invoice-modal-actions .secondary-btn{border-radius:12px;min-height:36px;padding:0 11px;background:linear-gradient(180deg,#fff,#f1f7ff);border:1px solid #d7e5f8;box-shadow:0 6px 14px rgba(15,23,42,.05);white-space:nowrap}
.invoice-preview-loading,.invoice-preview-empty{min-height:380px;border:1px dashed #bfd7ff;border-radius:18px;background:#fff;display:flex;align-items:center;justify-content:center;color:#64748b;padding:20px}
.invoice-preview-error{margin:10px 2px 0;color:#b91c1c;font-size:13px}
.invoice-preview-frame-wrap{min-height:0;min-width:0;border-radius:18px;overflow:auto;border:1px solid #dbe7f5;background:#eef3f8;box-shadow:0 16px 36px rgba(15,23,42,.08);height:100%;padding:18px;display:flex;justify-content:center;align-items:flex-start}
.invoice-live-preview{margin:0 auto;background:#fff;box-shadow:0 10px 28px rgba(15,23,42,.12)}
.invoice-preview-frame{display:block;width:100%;height:100%;min-height:0;min-width:0;border:0;background:#fff}
.invoice-template{background:#fff;padding:0;box-sizing:border-box;overflow:hidden}
.invoice-template *,.invoice-template *::before,.invoice-template *::after{box-sizing:border-box}
.invoice-sheet{direction:rtl;background:#fff;color:#0f172a;font-family:Tahoma,Arial,sans-serif;display:grid;box-sizing:border-box;overflow:hidden;max-width:100%;contain:layout paint}
.invoice-sheet-a5{font-size:1em}
.invoice-sheet-thermal{font-size:1em;direction:rtl;background:#fff!important;color:#000!important;font-family:Tahoma,Arial,sans-serif;line-height:1.35}
.invoice-sheet-thermal,
.invoice-sheet-thermal *{color:#000!important;background:#fff!important;background-color:#fff!important;box-shadow:none!important;text-shadow:none!important}
.invoice-sheet-thermal{border-radius:0!important}
.invoice-sheet-thermal *{border-color:#000!important}
.invoice-sheet-head{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);justify-content:space-between;gap:8px;padding:10px 12px;border-radius:10px;background:linear-gradient(135deg,#0f172a,#0f4c81 58%,#0ea5e9);color:#fff;min-width:0;max-width:100%}
.invoice-sheet-head > *{min-width:0}
.invoice-sheet-head .invoice-header-note{grid-column:1/-1;text-align:center;justify-self:center;width:100%;max-width:100%;margin-top:2px}
.invoice-sheet-head small{display:block;font-size:10px;color:rgba(255,255,255,.72);letter-spacing:0}
.receipt-custom-note{white-space:pre-line;overflow-wrap:anywhere;word-break:break-word;text-align:center;line-height:1.7}
.invoice-sheet-head strong{display:block;font-size:18px;line-height:1.35;margin-top:2px;overflow-wrap:anywhere}
.invoice-sheet-head span{display:block;margin-top:3px;color:rgba(255,255,255,.78);font-size:10px;overflow-wrap:anywhere}
.invoice-sheet-meta{display:grid;gap:4px;justify-items:end;min-width:0;align-content:center}
.invoice-sheet-meta strong{font-size:12px;overflow-wrap:anywhere}
.invoice-sheet-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px}
.invoice-sheet-grid article{border:1px solid #dbe7f5;border-radius:8px;padding:6px 7px;background:linear-gradient(180deg,#ffffff,#f8fbff);display:grid;gap:2px;min-width:0}
.invoice-sheet-grid article span{font-size:8px;color:#64748b}
.invoice-sheet-grid article strong{font-size:9px;line-height:1.6;min-width:0;overflow-wrap:anywhere;word-break:break-word}
.invoice-identity-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
.invoice-identity-grid article{border:1px solid #dbe7f5;border-radius:8px;padding:7px;background:linear-gradient(180deg,#ffffff,#f8fbff);display:grid;gap:4px;min-width:0}
.invoice-identity-grid small{color:#0f4c81;font-size:11px;font-weight:800}
.invoice-identity-grid p{margin:0;display:grid;grid-template-columns:minmax(0,.62fr) minmax(0,1fr);gap:6px;align-items:start;color:#334155;font-size:10px;line-height:1.55;min-width:0}
.invoice-identity-grid p span{color:#64748b;min-width:0}
.invoice-identity-grid p strong{color:#0f172a;font-size:10px;font-weight:800;min-width:0;overflow-wrap:anywhere;word-break:break-word}
.invoice-sheet-section{display:grid;gap:6px;min-width:0;max-width:100%}
.invoice-section-head strong{font-size:12px;color:#0f172a}
.invoice-table{width:100%;max-width:100%;table-layout:fixed;border-collapse:separate;border-spacing:0;border:1px solid #dbe7f5;border-radius:8px;overflow:hidden}
.invoice-table th,.invoice-table td{padding:5px 7px;border-bottom:1px solid #e2e8f0;text-align:right;font-size:11px;line-height:1.6;overflow-wrap:anywhere;word-break:break-word;min-width:0;vertical-align:middle}
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
.invoice-payment-grid p{margin:0;display:grid;grid-template-columns:minmax(0,.65fr) minmax(0,1fr);gap:8px;color:#334155;font-size:10px;line-height:1.6;min-width:0}
.invoice-payment-grid p span,.invoice-payment-grid p strong{min-width:0;overflow-wrap:anywhere;word-break:break-word}
.invoice-payment-grid p strong{color:#0f172a}
.invoice-total-section{border:1px solid #dbe7f5;border-radius:10px;padding:8px 10px;background:linear-gradient(180deg,#ffffff,#f8fbff)}
.invoice-totals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 8px}
.invoice-totals p{margin:0;display:grid;grid-template-columns:minmax(0,.75fr) minmax(0,1fr);gap:8px;color:#334155;font-size:11px;min-width:0}
.invoice-totals strong,.invoice-totals span{min-width:0;overflow-wrap:anywhere}
.invoice-grand-total{grid-column:1 / -1;padding-top:6px;border-top:1px dashed #bfd7ff;font-size:14px;font-weight:900;color:#0f172a}
.invoice-sheet-footer{padding-top:6px;border-top:1px dashed #cbd5e1;display:grid;gap:3px}
.invoice-sheet-footer p{margin:0;color:#475569;font-size:10px;line-height:1.7;overflow-wrap:anywhere;word-break:break-word;white-space:pre-line}
.thermal-sheet-head{display:grid;justify-items:center;gap:5px;padding:3px 0 8px;border-bottom:2px solid #000;text-align:center}
.thermal-sheet-head strong{font-size:26px;font-weight:900;line-height:1.22}
.thermal-sheet-head span{font-size:13px;font-weight:800;line-height:1.5;max-width:100%;overflow-wrap:anywhere}
.thermal-sheet-head small{font-size:11px;font-weight:800;line-height:1.65;max-width:100%;overflow-wrap:anywhere;white-space:pre-line;text-align:center}
.thermal-info-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px 10px;padding:8px 0;border-bottom:2px solid #000}
.thermal-info-grid p{margin:0;display:flex;align-items:center;gap:4px;font-size:12px;line-height:1.55;min-width:0}
.thermal-info-grid span{flex:0 0 auto;font-weight:700}
.thermal-info-grid strong{min-width:0;font-weight:700;overflow-wrap:anywhere;word-break:break-word}
.thermal-items-section{padding:8px 0}
.thermal-items-table{width:100%;border-collapse:collapse;table-layout:fixed;border:1.5px solid #000}
.thermal-items-table th,.thermal-items-table td{border:1px solid #000;padding:7px 5px;text-align:center;vertical-align:middle;font-size:12px;line-height:1.35;overflow-wrap:anywhere;word-break:break-word}
.thermal-items-table th{font-weight:900;font-size:12px;line-height:1.35}
.thermal-items-table th:first-child,.thermal-items-table td:first-child{width:62%;text-align:center}
.thermal-items-table th:nth-child(2),.thermal-items-table td:nth-child(2){width:38%}
.thermal-total-block{display:grid;gap:4px;padding:6px 0 0}
.thermal-total-block p{margin:0;display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:13px;line-height:1.6}
.thermal-total-block span{font-weight:800}
.thermal-total-block strong{font-weight:900;text-align:left;white-space:nowrap}
.thermal-payable-total{margin-top:4px!important;padding:8px 0!important;border-top:2px solid #000;border-bottom:4px double #000;font-size:16px!important;font-weight:900}
.thermal-payable-total strong{font-size:17px}
.thermal-sheet-footer{display:grid;gap:3px;padding-top:8px}
.thermal-sheet-footer p{margin:0;text-align:center;font-size:11px;line-height:1.65;font-weight:800;white-space:pre-line;overflow-wrap:anywhere;word-break:break-word}
.thermal-sheet-footer .receipt-custom-note{padding-top:6px;border-top:1px dashed #000}
.thermal-sheet-footer strong{display:block;margin-top:8px;text-align:center;font-size:14px;font-weight:900;line-height:1.7}
.modal-overlay { position: fixed; inset: 0; background: rgba(15, 23, 42, .35); z-index: 60; display: flex; align-items: center; justify-content: center; padding: 20px; overflow-x: hidden; overflow-y: auto; overscroll-behavior: contain; -webkit-overflow-scrolling: touch; }
.modal-panel { position: relative; width: min(1280px, 100%); max-width: 100%; max-height: calc(100vh - 40px); background: #fff; border-radius: 20px; overflow-y: auto; overflow-x: hidden; -webkit-overflow-scrolling: touch; display: flex; flex-direction: column; min-height: 0; box-shadow: 0 16px 42px -24px rgba(15,23,42,.45); contain: content; }
.plate-edit-overlay { z-index: 120; }
.plate-edit-panel { width: min(720px, 100%); overflow: hidden; background: linear-gradient(180deg,#ffffff,#f5f9ff); }
.plate-edit-head { background: #fff; }
.plate-edit-body { display: grid; gap: 16px; padding: 20px; }
.plate-edit-preview { display: grid; gap: 10px; padding: 14px; border: 1px solid #d6e6ff; border-radius: 18px; background: rgba(255,255,255,.82); }
.plate-edit-preview > span { color: #64748b; font-size: 12px; font-weight: 800; }
.plate-edit-actions { display: flex; justify-content: flex-end; gap: 10px; padding: 0 20px 20px; }
.plate-edit-submit { margin-right: 0; min-width: 130px; }
.vehicle-entry-overlay { align-items: center; justify-content: center; }
.vehicle-entry-panel { width: min(980px, 100%); max-width: 100%; }
.vehicle-entry-head { background: #fff; }
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
.step-transition-overlay{position:absolute;inset:0;z-index:25;background:rgba(255,255,255,.78);backdrop-filter:blur(1px);display:flex;align-items:center;justify-content:center}
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
  .release-mobile-content { grid-template-columns: 1fr; }
  .detail-field-wide,.cheque-field-wide { grid-column: auto; }
  .release-secondary-section { margin: 14px 20px 20px; }
}
@media (max-width: 768px) {
  .cards-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
  .dashboard-content { padding-bottom: 8px; }
  .plate-search-bar {
    width: 100%;
    flex-wrap: wrap;
    padding: 8px;
    gap: 8px;
  }
  .plate-type-inline {
    min-width: 88px;
    height: 36px;
  }
  .plate-search-editor {
    max-width: none;
    flex: 1 1 180px;
  }
  .plate-clear-btn {
    width: 36px;
    height: 36px;
  }
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
    padding: 9px 12px;
    font-size: 12px;
    flex: 0 0 auto;
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
  .plate-edit-overlay {
    align-items: center;
    overflow-y: auto;
  }
  .plate-edit-panel {
    height: auto;
    max-height: calc(100dvh - 16px);
  }
  .plate-edit-body {
    padding: 14px;
  }
  .plate-edit-actions {
    padding: 0 14px 14px;
    flex-direction: column;
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
  .invoice-format-toolbar { grid-template-columns: 1fr; align-items: stretch; }
  .invoice-format-presets { grid-template-columns: 1fr; }
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
  .worker-selection-actions { justify-content: stretch; }
  .worker-selection-actions .small-btn { width: 100%; }
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
  .summary-input-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .release-mobile-section{padding:0;border:none;background:transparent}
  .release-mobile-toggle{width:100%;border:1px solid #dbe7f5;border-radius:14px;background:#f8fbff;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:3px 8px;padding:10px 12px;text-align:right;align-items:center}
  .release-mobile-toggle span{font-weight:800;color:#0f172a}
  .release-mobile-toggle small{grid-column:1/2;color:#64748b;font-size:11px}
  .release-mobile-toggle strong{grid-row:1/3;grid-column:2/3;font-size:15px;color:#0f4c81}
  .release-mobile-content{margin-top:8px;grid-template-columns:1fr}
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
    border-radius: 14px;
    padding: 10px 12px;
    gap: 8px;
  }
  .summary-stat-card span {
    font-size: 11px;
    font-weight: 700;
  }
  .summary-stat-card strong,
  .summary-stat-value strong {
    font-size: 12px;
    line-height: 1.35;
  }
  .summary-stat-card small,
  .summary-stat-value small {
    font-size: 10px;
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
  .worker-editor-grid,
  .worker-editor-summary {
    grid-template-columns: 1fr;
  }
  .worker-editor-panel { border-radius: 22px; padding: 16px; }
  .worker-percent-field { grid-template-columns: 1fr 76px; }
  .worker-percent-field small { grid-column: 1 / -1; }
  .confirm-release-btn {
    min-height: 52px;
  }
  .empty-row {
    grid-column: 1 / -1;
  }
  .invoice-preview-loading,.invoice-preview-empty{min-height:220px}
  .invoice-modal-panel{height:calc(100vh - 16px)}
  .invoice-modal-actions{flex-direction:column;align-items:stretch}
  .invoice-modal-actions .secondary-btn{width:100%}
}
@media (max-width: 480px) {
  .filters {
    display: flex;
    grid-template-columns: none;
    flex-wrap: nowrap;
    overflow-x: auto;
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
    padding: 8px 10px;
    font-size: 11px;
    flex: 0 0 auto;
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
  .summary-stat-card {
    padding: 9px 10px;
  }
  .summary-stat-card span {
    font-size: 10px;
  }
  .summary-stat-card strong,
  .summary-stat-value strong {
    font-size: 11px;
  }
  .worker-editor-grid,
  .worker-editor-summary {
    grid-template-columns: 1fr;
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
