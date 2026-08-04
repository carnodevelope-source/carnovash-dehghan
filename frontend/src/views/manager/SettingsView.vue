<template>
  <AppShell
    title="تنظیمات"
    subtitle="پیکربندی پرسنل، خدمات و موجودی"
    :show-search="true"
    search-placeholder="جستجو در تنظیمات..."
    :search-query="search"
    @update:search-query="search = $event"
  >
    <div class="settings-content">
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

      <section class="card">
        <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>

        <template v-if="activeTab === 'workers'">
          <div class="head-row">
            <h2>مدیریت پرسنل</h2>
            <button class="primary-btn btn-with-icon" @click="openWorkerModal()"><IconlyIcon name="plus" size="sm" />افزودن پرسنل</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>نام</th>
                  <th>نقش</th>
                  <th>نام کاربری</th>
                  <th>شماره</th>
                  <th>نوع پرداخت</th>
                  <th>مقدار پرداخت</th>
                  <th>حق بیمه</th>
                  <th>درصد انعام</th>
                  <th>تاریخ بروزرسانی</th>
                  <th>وضعیت</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in filteredWorkers" :key="item.id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ item.full_name }}</td>
                  <td>{{ workerRoleLabel(item.role_key || item.role) }}</td>
                  <td>{{ item.role_key === 'worker' ? '-' : (item.username || '-') }}</td>
                  <td>{{ item.phone || '-' }}</td>
                  <td>{{ item.payment_type === 'fixed' ? 'تومانی' : item.payment_type === 'hourly' ? 'ساعتی' : 'درصدی' }}</td>
                  <td>{{ formatWorkerPayment(item) }}</td>
                  <td>{{ money(item.insurance_amount || 0) }}</td>
                  <td>{{ Number(item.tip_share_percent || 0).toLocaleString('fa-IR') }}٪</td>
                  <td>{{ formatDate(item.updated_at) }}</td>
                  <td>{{ item.is_available ? 'فعال' : 'غیرفعال' }}</td>
                  <td>
                    <button class="table-btn" @click="openWorkerModal(item)">ویرایش</button>
                    <button
                      class="table-btn"
                      :class="item.is_available ? 'danger' : 'success'"
                      type="button"
                      @click="toggleWorkerAvailability(item)"
                      :title="item.is_available ? 'غیرفعال کردن پرسنل' : 'فعال کردن پرسنل'"
                    >
                      {{ item.is_available ? 'غیرفعال‌کردن' : 'فعال‌کردن' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else-if="activeTab === 'products'">
          <div class="head-row">
            <h2>مدیریت محصولات</h2>
            <div class="head-actions">
              <button class="secondary-btn btn-with-icon" @click="openProductPurchaseModal()"><IconlyIcon name="buy" size="sm" />ثبت خرید جدید</button>
              <button class="primary-btn btn-with-icon" @click="openProductModal()"><IconlyIcon name="plus" size="sm" />افزودن محصول</button>
            </div>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>نام</th>
                  <th>شرح</th>
                  <th>قیمت فروش</th>
                  <th>موجودی</th>
                  <th>تاریخ بروزرسانی</th>
                  <th>فعال</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in filteredProducts" :key="item.id" class="clickable-row" @click="openProductHistoryModal(item)">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ item.name }}</td>
                  <td>{{ item.description || '-' }}</td>
                  <td>{{ money(item.sale_price) }}</td>
                  <td>{{ Number(item.stock_qty || 0).toLocaleString('fa-IR') }}</td>
                  <td>{{ formatDate(item.updated_at) }}</td>
                  <td>{{ item.is_active ? 'بله' : 'خیر' }}</td>
                  <td>
                    <button class="table-btn" @click.stop="openProductModal(item)">ویرایش</button>
                    <button class="table-btn danger" @click.stop="deleteProduct(item)">حذف</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else-if="activeTab === 'expenses'">
          <div class="head-row">
            <h2>هزینه‌ها</h2>
            <button class="primary-btn btn-with-icon" @click="openExpenseModal()"><IconlyIcon name="plus" size="sm" />ثبت هزینه جدید</button>
          </div>
          <div class="expense-summary-strip">
            <article>
              <span>تعداد ردیف‌ها</span>
              <strong>{{ Number(filteredExpenses.length || 0).toLocaleString('fa-IR') }}</strong>
            </article>
            <article>
              <span>جمع هزینه‌ها</span>
              <strong>{{ money(expensesTotal) }}</strong>
            </article>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>شرح</th>
                  <th>مبلغ</th>
                  <th>نوع ثبت</th>
                  <th>جزئیات</th>
                  <th>پیوست</th>
                  <th>ثبت‌کننده</th>
                  <th>تاریخ</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in filteredExpenses" :key="item.row_id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ item.title }}</td>
                  <td>{{ money(item.amount) }}</td>
                  <td>
                    <span class="source-badge" :class="`source-${item.source_type}`">{{ item.source_label }}</span>
                  </td>
                  <td class="details-cell">{{ item.details || '-' }}</td>
                  <td>
                    <a v-if="item.attachment_url" class="table-link" :href="item.attachment_url" target="_blank" rel="noopener noreferrer">
                      {{ item.attachment_name || 'مشاهده فایل' }}
                    </a>
                    <span v-else>-</span>
                  </td>
                  <td>{{ item.created_by_name || '-' }}</td>
                  <td>{{ dateTime(item.spent_at || item.created_at) }}</td>
                  <td>
                    <button v-if="item.can_edit" class="table-btn" @click="openExpenseModal(item)">ویرایش</button>
                    <button v-if="item.can_delete" class="table-btn danger" @click="deleteExpense(item)">حذف</button>
                    <span v-if="!item.can_edit && !item.can_delete" class="table-meta-note">خودکار</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else-if="activeTab === 'services'">
          <div class="head-row">
            <h2>مدیریت خدمات</h2>
            <button class="primary-btn btn-with-icon" @click="openServiceModal()"><IconlyIcon name="paperPlus" size="sm" />افزودن خدمت</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>نام</th>
                  <th v-for="tier in carServiceTierOptions" :key="`head-${tier.key}`">فروش {{ tier.label }}</th>
                  <th>موتور سیکلت</th>
                  <th>تاریخ بروزرسانی</th>
                  <th>فعال</th>
                  <th>عملیات</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in filteredServices" :key="item.id" class="clickable-row" @click="openServiceHistoryModal(item)">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ item.name }}</td>
                  <td v-for="tier in carServiceTierOptions" :key="`${item.id}-${tier.key}`">
                    {{ money(item.pricing_tiers?.[tier.key]?.sale_price ?? item.base_price) }}
                  </td>
                  <td>{{ item.motorcycle_enabled ? 'دارد' : 'ندارد' }}</td>
                  <td>{{ formatDate(item.updated_at) }}</td>
                  <td>{{ item.is_active ? 'بله' : 'خیر' }}</td>
                  <td>
                    <button class="table-btn" @click.stop="openServiceModal(item)">ویرایش</button>
                    <button class="table-btn danger" @click.stop="deleteService(item)">حذف</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <template v-else>
          <section class="settings-hero">
            <div class="settings-hero-copy">
              <span class="settings-hero-kicker">کنترل مرکزی شعبه</span>
              <h2>تنظیمات عمومی</h2>
              <p>تخفیف مشتری، پرداخت، فیش پرینتر و قالب پیامک را از یک نمای مرتب، روشن و سریع مدیریت کنید.</p>
            </div>
            <div class="settings-hero-stats">
              <article>
                <span>تخفیف هر ستاره کامل</span>
                <strong>{{ fullStarDiscountLabel }}</strong>
              </article>
              <article>
                <span>بانک اصلی</span>
                <strong>{{ generalSettings.preferred_bank_name || 'ثبت نشده' }}</strong>
              </article>
              <article>
                <span>فیش پرینتر</span>
                <strong>{{ generalSettings.receipt_printer_enabled ? 'فعال' : 'غیرفعال' }}</strong>
              </article>
            </div>
          </section>
          <div class="general-settings-form">
            <section class="general-settings-card general-settings-card-accent">
              <div class="general-settings-head">
                <div>
                  <strong>تنظیمات تخفیف مشتری</strong>
                  <p class="helper-text">امتیاز و ستاره‌دهی ثابت می‌ماند؛ فقط مدل محاسبه تخفیف سفارش از اینجا کنترل می‌شود.</p>
                </div>
              </div>
              <div class="discount-mode-tabs">
                <button
                  type="button"
                  class="discount-mode-tab"
                  :class="{ active: generalSettings.discount_calculation_mode === 'step' }"
                  @click="generalSettings.discount_calculation_mode = 'step'"
                >
                  پلکانی
                </button>
                <button
                  type="button"
                  class="discount-mode-tab"
                  :class="{ active: generalSettings.discount_calculation_mode === 'fixed' }"
                  @click="generalSettings.discount_calculation_mode = 'fixed'"
                >
                  ثابت
                </button>
              </div>
              <div v-if="generalSettings.discount_calculation_mode === 'step'" class="discount-editor-grid">
                <label class="general-setting-label">
                  <span>درصد تخفیف به‌ازای هر نیم‌ستاره</span>
                  <input
                    v-model.number="generalSettings.discount_percent_per_half_star"
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                  />
                </label>
                <article class="discount-preview-card">
                  <small>پیش‌نمایش سریع</small>
                  <strong>{{ fullStarDiscountLabel }}</strong>
                  <p>در حالت پلکانی، مقدار تخفیف از امتیاز ستاره‌ای پلاک و درصد هر نیم‌ستاره محاسبه می‌شود.</p>
                </article>
              </div>
              <div v-else class="fixed-discount-grid">
                <label
                  v-for="item in fixedDiscountVisitItems"
                  :key="item.key"
                  class="general-setting-label fixed-discount-field"
                >
                  <span>{{ item.label }}</span>
                  <input
                    v-model.number="generalSettings.fixed_visit_discounts[item.key]"
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                  />
                </label>
                <article class="discount-preview-card fixed-preview-card">
                  <small>قوانین فعال</small>
                  <strong>{{ fixedDiscountPreviewLabel }}</strong>
                  <p>در مراجعه‌های ثبت‌شده، اگر شماره مراجعه پلاک با یکی از این ردیف‌ها برابر باشد همان درصد روی سفارش اعمال می‌شود.</p>
                </article>
              </div>
            </section>
            <section class="general-settings-card tax-settings-card">
              <div class="general-settings-head">
                <div>
                  <strong>مالیات سفارش</strong>
                  <p class="helper-text">اگر فعال باشد، درصد مالیات به جمع سفارش و فاکتور اضافه می‌شود.</p>
                </div>
                <label class="settings-toggle">
                  <input v-model="generalSettings.tax_enabled" type="checkbox" />
                  <span>{{ generalSettings.tax_enabled ? 'فعال' : 'غیرفعال' }}</span>
                </label>
              </div>
              <div class="discount-editor-grid">
                <label class="general-setting-label">
                  <span>درصد مالیات</span>
                  <input
                    v-model.number="generalSettings.tax_percent"
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    :disabled="!generalSettings.tax_enabled"
                  />
                </label>
                <article class="discount-preview-card">
                  <small>وضعیت فعلی</small>
                  <strong>{{ generalSettings.tax_enabled ? `${Number(generalSettings.tax_percent || 0).toLocaleString('fa-IR')}٪` : 'بدون مالیات' }}</strong>
                  <p>مالیات بعد از تخفیف‌ها و قبل از انعام روی مبلغ سفارش محاسبه می‌شود.</p>
                </article>
              </div>
            </section>
            <section class="general-settings-card payment-settings-card">
              <div class="general-settings-head">
                <div>
                  <strong>ویژگی‌های شیوه پرداخت</strong>
                  <p class="helper-text">اطلاعات بانکی، کارت‌خوان و توضیحات پرداخت کارواش را اینجا ثبت کنید.</p>
                </div>
              </div>
              <div class="payment-settings-grid">
                <label class="general-setting-label">
                  <span>بانک اصلی</span>
                  <input v-model.trim="generalSettings.preferred_bank_name" type="text" placeholder="مثلا بانک ملت" />
                </label>
                <label class="general-setting-label">
                  <span>نام صاحب حساب</span>
                  <input v-model.trim="generalSettings.bank_account_holder" type="text" placeholder="مثلا علی رضایی" />
                </label>
                <label class="general-setting-label">
                  <span>شماره کارت</span>
                  <input v-model.trim="generalSettings.bank_card_number" type="text" inputmode="numeric" placeholder="مثلا 6037991234567890" />
                </label>
                <label class="general-setting-label">
                  <span>شماره شبا</span>
                  <input v-model.trim="generalSettings.bank_account_iban" type="text" placeholder="IRxxxxxxxxxxxxxxxxxxxxxxxx" />
                </label>
                <label class="general-setting-label">
                  <span>نام دستگاه پوز</span>
                  <input v-model.trim="generalSettings.pos_device_name" type="text" placeholder="مثلا پوز صندوق ۱" />
                </label>
                <label class="general-setting-label">
                  <span>کد یا ترمینال پوز</span>
                  <input v-model.trim="generalSettings.pos_terminal_id" type="text" placeholder="مثلا TID-2048" />
                </label>
                <label class="general-setting-label full-width">
                  <span>توضیحات شیوه پرداخت</span>
                  <textarea v-model.trim="generalSettings.payment_methods_note" rows="4" placeholder="مثلا برای مبالغ بالا کارت به کارت فقط به همین حساب انجام شود یا توضیحات مربوط به پوز و تسویه را بنویسید." />
                </label>
              </div>
            </section>
            <section class="general-settings-card printer-settings-card">
              <div class="general-settings-head">
                <div>
                  <strong>تنظیمات فیش پرینتر</strong>
                  <p class="helper-text">نیازی به نصب نرم‌افزار نیست. با دکمه چاپ، پنجره چاپ سیستم (مثل Ctrl+P) باز می‌شود و پرینترهای همان سیستم قابل انتخاب هستند.</p>
                </div>
                <label class="settings-toggle">
                  <input v-model="generalSettings.receipt_printer_enabled" type="checkbox" />
                  <span>{{ generalSettings.receipt_printer_enabled ? 'فعال' : 'غیرفعال' }}</span>
                </label>
              </div>
              <div class="printer-settings-grid">
                <label class="general-setting-label">
                  <span>عرض کاغذ</span>
                  <select v-model="generalSettings.receipt_printer_paper_width">
                    <option value="58mm">58mm</option>
                    <option value="80mm">80mm</option>
                    <option value="a4">A4</option>
                  </select>
                </label>
                <label class="general-setting-label full-width">
                  <span>متن بالای فیش</span>
                  <textarea v-model.trim="generalSettings.receipt_header_note" rows="3" placeholder="متنی که زیر آدرس مجموعه در فیش چاپ می‌شود." />
                </label>
                <label class="general-setting-label full-width">
                  <span>متن پایین فیش</span>
                  <textarea v-model.trim="generalSettings.receipt_footer_note" rows="4" placeholder="متنی که قبل از «از اعتماد شما سپاسگزاریم» در فیش و فاکتور چاپ می‌شود." />
                </label>
              </div>
            </section>
            <section class="general-settings-card sms-settings-card">
              <div class="general-settings-head">
                <div>
                  <strong>تنظیمات سرویس پیامک</strong>
                  <p class="sms-cost-hint">هزینه بر اساس طول همان پیام قبل از ارسال: تا ۷۰ کاراکتر = ۱ پارت (۱۸۵ تومان)، پیام بلندتر با پارت‌های ۶۷ کاراکتری محاسبه می‌شود.</p>
                </div>
              </div>
              <div class="sms-auto-send-panel">
                <label class="row-check">
                  <input v-model="generalSettings.sms_vehicle_auto_send_enabled" type="checkbox" />
                  <span>ارسال خودکار پیامک تخصیص و ترخیص</span>
                </label>
              </div>
              <div class="sms-template-grid">
                <article class="sms-template-card">
                  <label class="general-setting-label sms-template-editor">
                    <span class="template-title-row">
                      <span>پیام تخصیص</span>
                      <label class="row-check inline-check">
                        <input v-model="generalSettings.sms_vehicle_assigned_enabled" type="checkbox" :disabled="!generalSettings.sms_vehicle_auto_send_enabled" />
                        <span>فعال</span>
                      </label>
                    </span>
                    <textarea v-model.trim="generalSettings.sms_vehicle_assigned_template" rows="14" />
                  </label>
                  <div class="sms-preview-panel">
                    <div class="sms-preview-head">
                      <small>نمونه خروجی</small>
                      <span>{{ `پیام پذیرش • ${smsAssignedEstimatedCostLabel}` }}</span>
                    </div>
                    <pre class="sms-preview-box">{{ smsAssignedPreview }}</pre>
                  </div>
                </article>
                <article class="sms-template-card">
                  <label class="general-setting-label sms-template-editor">
                    <span class="template-title-row">
                      <span>پیام بعد از ترخیص</span>
                      <label class="row-check inline-check">
                        <input v-model="generalSettings.sms_vehicle_released_enabled" type="checkbox" :disabled="!generalSettings.sms_vehicle_auto_send_enabled" />
                        <span>فعال</span>
                      </label>
                    </span>
                    <textarea v-model.trim="generalSettings.sms_vehicle_released_template" rows="7" />
                  </label>
                  <div class="sms-preview-panel">
                    <div class="sms-preview-head">
                      <small>نمونه خروجی</small>
                      <span>{{ `فاکتور ترخیص • ${smsReleasedEstimatedCostLabel}` }}</span>
                    </div>
                    <pre class="sms-preview-box">{{ smsReleasedPreview }}</pre>
                  </div>
                </article>
              </div>
              <div class="sms-token-panel">
                <strong>متغیرهای قابل استفاده</strong>
                <div class="sms-token-list">
                  <code v-for="token in smsTemplateTokens" :key="token">{{ token }}</code>
                </div>
              </div>
            </section>
            <div class="modal-actions">
              <button class="primary-btn" :disabled="generalSettingsSaving" @click="saveGeneralSettings">
                {{ generalSettingsSaving ? 'در حال ذخیره...' : 'ذخیره تنظیمات عمومی' }}
              </button>
            </div>
          </div>
        </template>
      </section>
    </div>

    <div v-if="modal.open" class="modal-overlay" @click.self="closeModal">
      <section class="modal-panel">
        <header class="modal-head">
          <h3>{{ modal.title }}</h3>
          <button class="close-btn" @click="closeModal">✕</button>
        </header>

        <form class="modal-form" @submit.prevent="submitModal">
          <template v-if="modal.type === 'workers'">
            <label><span>نام و نام خانوادگی</span><input v-model="forms.worker.full_name" required /></label>
            <label>
              <span>نقش پرسنل</span>
              <select v-model="forms.worker.role">
                <option value="worker">نیرو</option>
                <option value="operator">اپراتور</option>
              </select>
            </label>
            <p class="full helper-text modal-helper-text">تاریخ شروع همکاری این پرسنل به‌صورت خودکار از زمان ثبت در سامانه ذخیره می‌شود.</p>
            <template v-if="forms.worker.role !== 'worker'">
              <label><span>نام کاربری</span><input v-model.trim="forms.worker.username" required /></label>
              <label>
                <span>{{ modal.id ? 'رمز عبور جدید (اختیاری)' : 'رمز عبور' }}</span>
                <input v-model="forms.worker.password" type="text" :required="!modal.id" />
              </label>
            </template>
            <p v-else class="full helper-text modal-helper-text">نیرو نام کاربری و رمز عبور ندارد و فقط برای تخصیص کار و حضور و غیاب ثبت می‌شود.</p>
            <BasePhoneInput v-model="forms.worker.phone" label="شماره موبایل" :required="true" :force-show-error="workerPhoneTouched" />
            <label class="full"><span>آدرس</span><textarea v-model.trim="forms.worker.address" rows="3" placeholder="آدرس نیرو را وارد کنید" /></label>
            <label>
              <span>نوع پرداخت پرسنل</span>
              <select v-model="forms.worker.payment_type">
                <option value="percent">درصدی</option>
                <option value="fixed">تومانی</option>
                <option value="hourly">ساعتی</option>
              </select>
            </label>
            <label>
              <span>{{ forms.worker.payment_type === 'percent' ? 'درصد دریافتی' : forms.worker.payment_type === 'hourly' ? 'مبلغ ساعتی (تومان)' : 'مبلغ دریافتی (تومان)' }}</span>
              <input
                v-if="forms.worker.payment_type === 'percent'"
                type="number"
                min="0"
                max="100"
                v-model.number="forms.worker.payment_value"
                required
              />
              <input
                v-else
                :value="moneyInputValue(forms.worker.payment_value)"
                type="text"
                inputmode="numeric"
                @input="forms.worker.payment_value = fromThousandsInput($event.target.value)"
                required
              />
            </label>
            <label>
              <span>حق بیمه (تومان)</span>
              <input :value="moneyInputValue(forms.worker.insurance_amount)" type="text" inputmode="numeric" @input="forms.worker.insurance_amount = fromThousandsInput($event.target.value)" />
            </label>
            <label><span>درصد انعام</span><input type="number" min="0" max="100" v-model.number="forms.worker.tip_share_percent" required /></label>
            <label class="row-check"><input type="checkbox" v-model="forms.worker.is_available" /><span>فعال</span></label>
            <section class="full entrusted-card" :class="{ active: forms.worker.has_entrusted_item }">
              <div class="entrusted-head">
                <div>
                  <strong>امانات پرسنل</strong>
                  <small>اگر چیزی به این پرسنل امانت داده‌اید، این بخش را تکمیل کنید.</small>
                </div>
                <label class="row-check entrusted-toggle">
                  <input type="checkbox" v-model="forms.worker.has_entrusted_item" />
                  <span>ثبت امانت</span>
                </label>
              </div>
              <div v-if="forms.worker.has_entrusted_item" class="entrusted-grid">
                <div class="full entrusted-list-head">
                  <strong>لیست امانات</strong>
                  <button type="button" class="secondary-btn small-btn" @click="addEntrustedItem">افزودن ردیف</button>
                </div>
                <div
                  v-for="(entrustedItem, entrustedIndex) in forms.worker.entrusted_items"
                  :key="`entrusted-${entrustedIndex}`"
                  class="entrusted-item-row"
                >
                  <label class="full">
                    <span>شرح</span>
                    <textarea v-model.trim="entrustedItem.title" rows="2" placeholder="مثلا: کاردک، دستگاه، لباس کار یا هر مورد امانی" />
                  </label>
                  <label>
                    <span>تاریخ</span>
                    <BaseDatePicker v-model="entrustedItem.entrusted_at" placeholder="1405/01/01" />
                  </label>
                  <label>
                    <span>تعداد</span>
                    <input type="number" min="0" step="0.01" v-model.number="entrustedItem.quantity" />
                  </label>
                  <label>
                    <span>قیمت (تومان)</span>
                    <input :value="moneyInputValue(entrustedItem.price)" type="text" inputmode="numeric" @input="entrustedItem.price = fromThousandsInput($event.target.value)" />
                  </label>
                  <button
                    type="button"
                    class="table-btn danger entrusted-remove-btn"
                    @click="removeEntrustedItem(entrustedIndex)"
                  >
                    حذف
                  </button>
                </div>
              </div>
            </section>
          </template>

          <template v-else-if="modal.type === 'products'">
            <label><span>نام</span><input v-model="forms.product.name" required /></label>
            <label class="full"><span>شرح</span><textarea v-model="forms.product.description" rows="3" /></label>
            <label><span>قیمت فروش (تومان)</span><input :value="moneyInputValue(forms.product.sale_price)" type="text" inputmode="numeric" @input="forms.product.sale_price = fromThousandsInput($event.target.value)" required /></label>
            <label><span>قیمت خرید (تومان)</span><input :value="moneyInputValue(forms.product.cost_price)" type="text" inputmode="numeric" @input="forms.product.cost_price = fromThousandsInput($event.target.value)" required /></label>
            <label><span>واحد</span><input v-model="forms.product.unit" /></label>
            <label><span>حداقل موجودی</span><input type="number" min="0" v-model.number="forms.product.min_stock" /></label>
            <label class="row-check"><input type="checkbox" v-model="forms.product.is_active" /><span>فعال</span></label>
          </template>

          <template v-else-if="modal.type === 'product_purchase'">
            <label>
              <span>محصول</span>
              <select v-model.number="forms.purchase.product_id" required>
                <option :value="0" disabled>انتخاب محصول</option>
                <option v-for="item in products" :key="item.id" :value="item.id">{{ item.name }}</option>
              </select>
            </label>
            <label><span>تعداد خرید</span><input type="number" min="0.01" step="0.01" v-model.number="forms.purchase.quantity" required /></label>
            <label><span>قیمت خرید واحد (تومان)</span><input :value="moneyInputValue(forms.purchase.unit_cost)" type="text" inputmode="numeric" @input="forms.purchase.unit_cost = fromThousandsInput($event.target.value)" /></label>
            <label><span>قیمت فروش واحد (تومان)</span><input :value="moneyInputValue(forms.purchase.sale_price)" type="text" inputmode="numeric" @input="forms.purchase.sale_price = fromThousandsInput($event.target.value)" /></label>
            <label><span>توضیح</span><input v-model="forms.purchase.note" placeholder="اختیاری" /></label>
          </template>

          <template v-else-if="modal.type === 'expenses'">
            <label><span>شرح هزینه</span><input v-model.trim="forms.expense.title" required placeholder="مثلا تعمیر کولر" /></label>
            <label><span>مبلغ (تومان)</span><input :value="moneyInputValue(forms.expense.amount)" type="text" inputmode="numeric" @input="forms.expense.amount = fromThousandsInput($event.target.value)" required /></label>
            <label class="full"><span>تاریخ</span><BaseDatePicker v-model="forms.expense.spent_at_jalali" placeholder="1405/01/01" /></label>
            <label class="full">
              <span>پیوست</span>
              <input type="file" @change="handleExpenseAttachmentChange" />
              <small v-if="forms.expense.attachment_name" class="field-file-note">{{ forms.expense.attachment_name }}</small>
              <a v-if="forms.expense.attachment_url" class="table-link" :href="forms.expense.attachment_url" target="_blank" rel="noopener noreferrer">مشاهده پیوست فعلی</a>
            </label>
            <label class="full"><span>جزئیات</span><textarea v-model.trim="forms.expense.details" rows="4" placeholder="کجا، چرا و برای چه موردی هزینه شده است" /></label>
          </template>

          <template v-else>
            <label><span>نام خدمت</span><input v-model="forms.service.name" required /></label>
            <label class="full"><span>شرح</span><textarea v-model="forms.service.description" rows="3" /></label>
            <label class="row-check"><input type="checkbox" v-model="forms.service.is_active" /><span>فعال</span></label>
            <section class="full service-tier-panel">
              <div class="service-tier-panel-head">
                <div>
                  <strong>تیپ‌های خودرو</strong>
                  <p class="helper-text">برای هر تیپ، مبلغ نرخ نامه، مبلغ فروش و زمان انجام خدمت را به تومان و دقیقه ثبت کنید.</p>
                </div>
              </div>
              <div class="service-tier-grid">
                <article v-for="tier in carServiceTierOptions" :key="`car-${tier.key}`" class="service-tier-card">
                  <header>
                    <strong>{{ tier.label }}</strong>
                    <small>خودرو</small>
                  </header>
                  <label>
                    <span>مبلغ نرخ نامه</span>
                    <input :value="moneyInputValue(forms.service.pricing_tiers[tier.key].list_price)" type="text" inputmode="numeric" @input="forms.service.pricing_tiers[tier.key].list_price = fromThousandsInput($event.target.value)" required />
                  </label>
                  <label>
                    <span>مبلغ فروش</span>
                    <input :value="moneyInputValue(forms.service.pricing_tiers[tier.key].sale_price)" type="text" inputmode="numeric" @input="forms.service.pricing_tiers[tier.key].sale_price = fromThousandsInput($event.target.value)" required />
                  </label>
                  <label>
                    <span>زمان (دقیقه)</span>
                    <input type="number" min="1" v-model.number="forms.service.pricing_tiers[tier.key].duration_minutes" required />
                  </label>
                </article>
              </div>
            </section>
            <section class="full service-tier-panel" :class="{ active: forms.service.motorcycle_enabled }">
              <div class="service-tier-panel-head">
                <div>
                  <strong>تیپ‌های موتور سیکلت</strong>
                  <p class="helper-text">اگر این خدمت برای موتور سیکلت هم فعال است، تیپ‌های موتور را هم جداگانه تعریف کنید.</p>
                </div>
                <label class="row-check service-tier-toggle">
                  <input type="checkbox" v-model="forms.service.motorcycle_enabled" />
                  <span>این خدمت برای موتور سیکلت هم فعال باشد</span>
                </label>
              </div>
              <div v-if="forms.service.motorcycle_enabled" class="service-tier-grid motorcycle-tier-grid">
                <article v-for="tier in motorcycleServiceTierOptions" :key="`motor-${tier.key}`" class="service-tier-card motorcycle">
                  <header>
                    <strong>{{ tier.label }}</strong>
                    <small>موتور سیکلت</small>
                  </header>
                  <label>
                    <span>مبلغ نرخ نامه</span>
                    <input :value="moneyInputValue(forms.service.motorcycle_pricing_tiers[tier.key].list_price)" type="text" inputmode="numeric" @input="forms.service.motorcycle_pricing_tiers[tier.key].list_price = fromThousandsInput($event.target.value)" required />
                  </label>
                  <label>
                    <span>مبلغ فروش</span>
                    <input :value="moneyInputValue(forms.service.motorcycle_pricing_tiers[tier.key].sale_price)" type="text" inputmode="numeric" @input="forms.service.motorcycle_pricing_tiers[tier.key].sale_price = fromThousandsInput($event.target.value)" required />
                  </label>
                  <label>
                    <span>زمان (دقیقه)</span>
                    <input type="number" min="1" v-model.number="forms.service.motorcycle_pricing_tiers[tier.key].duration_minutes" required />
                  </label>
                </article>
              </div>
            </section>
          </template>

          <div class="modal-actions">
            <button type="button" class="secondary-btn" @click="closeModal">انصراف</button>
            <button class="primary-btn">ذخیره</button>
          </div>
        </form>
      </section>
    </div>

    <div v-if="productHistoryModal.open" class="modal-overlay" @click.self="closeProductHistoryModal">
      <section class="modal-panel history-panel">
        <header class="modal-head">
          <div>
            <h3>تاریخچه خرید {{ productHistoryModal.product?.name || '' }}</h3>
            <small class="modal-subtitle">همه خریدهای ثبت‌شده برای این محصول</small>
          </div>
          <button class="close-btn" @click="closeProductHistoryModal">✕</button>
        </header>
        <div v-if="productHistoryModal.loading" class="history-loading">در حال بارگذاری...</div>
        <div v-else class="history-body">
          <div class="history-summary" v-if="productHistoryModal.product">
            <article><span>قیمت فروش فعلی</span><strong>{{ money(productHistoryModal.product.sale_price) }}</strong></article>
            <article><span>قیمت خرید فعلی</span><strong>{{ money(productHistoryModal.product.cost_price) }}</strong></article>
            <article><span>تعداد خریدها</span><strong>{{ Number(productHistoryModal.history.length || 0).toLocaleString('fa-IR') }}</strong></article>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>تاریخ</th>
                  <th>تعداد</th>
                  <th>قیمت خرید</th>
                  <th>قیمت فروش</th>
                  <th>ثبت‌کننده</th>
                  <th>توضیح</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in productHistoryModal.history" :key="row.id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ dateTime(row.moved_at) }}</td>
                  <td>{{ Number(row.quantity || 0).toLocaleString('fa-IR') }}</td>
                  <td>{{ money(row.unit_cost) }}</td>
                  <td>{{ money(row.sale_price_snapshot) }}</td>
                  <td>{{ row.created_by_name || '-' }}</td>
                  <td>{{ row.note || '-' }}</td>
                </tr>
                <tr v-if="!productHistoryModal.history.length">
                  <td colspan="7">برای این محصول هنوز خریدی ثبت نشده است.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <div v-if="serviceHistoryModal.open" class="modal-overlay" @click.self="closeServiceHistoryModal">
      <section class="modal-panel history-panel">
        <header class="modal-head">
          <div>
            <h3>۵ تغییر آخر {{ serviceHistoryModal.service?.name || '' }}</h3>
            <small class="modal-subtitle">آخرین تغییرات قیمت، مدت و وضعیت این خدمت</small>
          </div>
          <button class="close-btn" @click="closeServiceHistoryModal">✕</button>
        </header>
        <div v-if="serviceHistoryModal.loading" class="history-loading">در حال بارگذاری...</div>
        <div v-else class="history-body">
          <div class="history-summary" v-if="serviceHistoryModal.service">
            <article><span>قیمت فعلی</span><strong>{{ money(serviceHistoryModal.service.base_price) }}</strong></article>
            <article><span>مدت فعلی</span><strong>{{ serviceHistoryModal.service.estimated_duration_minutes }} دقیقه</strong></article>
            <article><span>تعداد لاگ‌ها</span><strong>{{ Number(serviceHistoryModal.history.length || 0).toLocaleString('fa-IR') }}</strong></article>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ردیف</th>
                  <th>تاریخ</th>
                  <th>نوع تغییر</th>
                  <th>قیمت ثبت‌شده</th>
                  <th>مدت ثبت‌شده</th>
                  <th>وضعیت</th>
                  <th>ثبت‌کننده</th>
                  <th>جزئیات تغییر</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in serviceHistoryModal.history" :key="row.id">
                  <td>{{ Number(index + 1).toLocaleString('fa-IR') }}</td>
                  <td>{{ dateTime(row.created_at) }}</td>
                  <td>{{ serviceActionLabel(row.action_type) }}</td>
                  <td>{{ money(row.base_price_snapshot) }}</td>
                  <td>{{ row.estimated_duration_snapshot }} دقیقه</td>
                  <td>{{ row.is_active_snapshot ? 'فعال' : 'غیرفعال' }}</td>
                  <td>{{ row.changed_by_name || '-' }}</td>
                  <td>{{ serviceChangeSummaryText(row.change_summary) }}</td>
                </tr>
                <tr v-if="!serviceHistoryModal.history.length">
                  <td colspan="8">برای این خدمت هنوز تغییری ثبت نشده است.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.msg }}</div>
  </AppShell>
</template>
<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import api from '../../services/api'
import { useAuthStore } from '../../store/auth.store'
import AppShell from '../../components/layout/AppShell.vue'
import BaseDatePicker from '../../components/base/BaseDatePicker.vue'
import IconlyIcon from '../../components/base/IconlyIcon.vue'
import { formatJalaliDate } from '../../utils/date'
import { formatThousandsToman, formatThousandsTomanValue, fromThousandsTomanInput } from '../../utils/money'
import { resolveApiErrorMessage } from '../../utils/apiError'
import { carServiceTierOptions, motorcycleServiceTierOptions } from '../../utils/serviceTiers'
import { sectionHelpByPage } from '../../config/pageHelp'
import HelpTip from '../../components/base/HelpTip.vue'
import BasePhoneInput from '../../components/base/BasePhoneInput.vue'
import { iranMobileErrorMessage, normalizeIranMobile } from '../../utils/phone'
import { smsCharacterCount, smsCostForText, smsSegmentsForText } from '../../utils/smsCost'

const authStore = useAuthStore()
const search = ref('')
const activeTab = ref('workers')
const errorMessage = ref('')

const tabs = [
  { key: 'workers', label: 'پرسنل', icon: 'users3', help: sectionHelpByPage.settings.workers },
  { key: 'products', label: 'محصولات', icon: 'buy', help: sectionHelpByPage.settings.products },
  { key: 'expenses', label: 'هزینه‌ها', icon: 'wallet', help: sectionHelpByPage.settings.expenses },
  { key: 'services', label: 'خدمات', icon: 'paperPlus', help: sectionHelpByPage.settings.services },
  { key: 'general', label: 'تنظیمات عمومی', icon: 'setting', help: sectionHelpByPage.settings.general }
]

const workers = ref([])
const products = ref([])
const expenses = ref([])
const services = ref([])
const inventoryItems = ref([])
const generalSettings = reactive({
  discount_calculation_mode: 'step',
  discount_percent_per_half_star: 0,
  fixed_visit_discounts: { 2: 0, 5: 0, 10: 0 },
  tax_enabled: false,
  tax_percent: 0,
  preferred_bank_name: '',
  bank_account_holder: '',
  bank_card_number: '',
  bank_account_iban: '',
  pos_device_name: '',
  pos_terminal_id: '',
  payment_methods_note: '',
  receipt_printer_enabled: false,
  receipt_printer_name: '',
  receipt_printer_paper_width: '80mm',
  receipt_auto_print: false,
  receipt_show_logo: false,
  receipt_show_qr: false,
  receipt_header_note: '',
  receipt_footer_note: '',
  sms_provider_base_url: 'https://api.iranpayamak.com',
  sms_provider_line_number: '',
  sms_provider_api_key_configured: false,
  sms_provider_source: 'env',
  sms_vehicle_auto_send_enabled: true,
  sms_vehicle_assigned_enabled: true,
  sms_vehicle_assigned_invoice_enabled: true,
  sms_vehicle_released_enabled: true,
  sms_vehicle_assigned_template: '',
  sms_vehicle_assigned_invoice_template: '',
  sms_vehicle_released_template: ''
})
const generalSettingsSaving = ref(false)
const workerPhoneTouched = ref(false)
const fixedDiscountVisitItems = [
  { key: '2', label: 'مراجعه دوم' },
  { key: '5', label: 'مراجعه پنجم' },
  { key: '10', label: 'مراجعه دهم' }
]

const modal = reactive({ open: false, type: '', id: null, title: '' })
const productHistoryModal = reactive({ open: false, loading: false, product: null, history: [] })
const serviceHistoryModal = reactive({ open: false, loading: false, service: null, history: [] })
const forms = reactive({
  worker: {
    full_name: '',
    role: 'worker',
    started_at_jalali: '',
    username: '',
    password: '',
    phone: '',
    address: '',
    payment_type: 'percent',
    payment_value: 0,
    insurance_amount: 0,
    tip_share_percent: 0,
    is_available: true,
    has_entrusted_item: false,
    entrusted_items: [],
    entrusted_item_description: '',
    entrusted_item_quantity: 0,
    entrusted_item_price: 0
  },
  product: { name: '', description: '', sale_price: 0, cost_price: 0, unit: 'unit', min_stock: 0, is_active: true },
  purchase: { product_id: 0, quantity: 1, unit_cost: 0, sale_price: 0, note: '' },
  expense: { title: '', amount: 0, details: '', spent_at_jalali: '', attachment: null, attachment_name: '', attachment_url: '' },
  service: {
    name: '',
    description: '',
    base_price: 0,
    estimated_duration_minutes: 30,
    is_active: true,
    motorcycle_enabled: false,
    pricing_tiers: {},
    motorcycle_pricing_tiers: {}
  }
})

const toast = reactive({ show: false, type: 'success', msg: '' })
let timer = null

const t = (msg, type = 'success') => {
  toast.show = true
  toast.msg = msg
  toast.type = type
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => (toast.show = false), 2400)
}

const money = (v) => formatThousandsToman(v)
const moneyInputValue = (value) => formatThousandsTomanValue(value, { maximumFractionDigits: 0 })
const toThousandsDisplay = (value) => Math.round(Number(value || 0))
const fromThousandsInput = (value) => fromThousandsTomanInput(value)
const createEntrustedItem = () => ({ title: '', entrusted_at: '', quantity: 1, price: 0 })

const apiErrorText = (error) => resolveApiErrorMessage(error, 'ثبت ناموفق بود')

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

const toJalaliInput = (value) => {
  if (!value) return ''
  const formatted = String(formatJalaliDate(value) || '').trim()
  if (!formatted || formatted === '-') return ''
  return formatted.replace(/-/g, '/')
}

const workerRoleLabel = (value) => {
  if (value === 'worker' || value === 'Worker') return 'نیرو'
  if (value === 'operator' || value === 'Operator') return 'اپراتور'
  return value || '-'
}

const formatWorkerPayment = (worker) => {
  if (['fixed', 'hourly'].includes(worker?.payment_type || 'percent')) return money(worker?.payment_value || 0)
  return `${Number(worker?.payment_value || 0).toLocaleString('fa-IR')}٪`
}
const serviceActionLabel = (value) => ({
  created: 'ایجاد',
  updated: 'ویرایش',
  deactivated: 'غیرفعال‌سازی',
  deleted: 'حذف'
}[value] || 'ویرایش')
const serviceChangeSummaryText = (summary) => {
  const entries = Object.values(summary || {})
  if (!entries.length) return 'بدون جزئیات'
  return entries.map((item) => `${item.label}: ${item.from ?? '-'} ← ${item.to ?? '-'}`).join(' | ')
}
const createServiceTierState = (salePrice = 0, durationMinutes = 30) => ({
  list_price: salePrice,
  sale_price: salePrice,
  duration_minutes: durationMinutes
})
const normalizeServiceTierMap = (rawValue, tierOptions, fallbackSalePrice = 0, fallbackDurationMinutes = 30) => {
  const source = rawValue && typeof rawValue === 'object' ? rawValue : {}
  let previousSale = fallbackSalePrice
  let previousList = fallbackSalePrice
  let previousDuration = Number(fallbackDurationMinutes || 30) || 30
  return tierOptions.reduce((result, tier) => {
    const current = source?.[tier.key] && typeof source[tier.key] === 'object' ? source[tier.key] : {}
    const hasPrice = current && ('sale_price' in current || 'list_price' in current)
    const hasDuration = current && 'duration_minutes' in current
    const salePrice = hasPrice ? (current?.sale_price ?? current?.list_price ?? previousSale) : previousSale
    const listPrice = hasPrice ? (current?.list_price ?? current?.sale_price ?? previousList) : previousList
    const durationMinutes = hasDuration
      ? Number(current?.duration_minutes || previousDuration || 30)
      : previousDuration
    result[tier.key] = createServiceTierState(
      toThousandsDisplay(salePrice),
      durationMinutes
    )
    result[tier.key].list_price = toThousandsDisplay(listPrice)
    result[tier.key].sale_price = toThousandsDisplay(salePrice)
    previousSale = salePrice
    previousList = listPrice
    previousDuration = durationMinutes
    return result
  }, {})
}
const buildServiceTiersPayload = (tierMap, tierOptions) => tierOptions.reduce((result, tier) => {
  const current = tierMap?.[tier.key] || {}
  result[tier.key] = {
    list_price: fromThousandsInput(current?.list_price || 0),
    sale_price: fromThousandsInput(current?.sale_price || 0),
    duration_minutes: Math.max(1, Number(current?.duration_minutes || 30))
  }
  return result
}, {})

forms.service.pricing_tiers = normalizeServiceTierMap({}, carServiceTierOptions, 0, 30)
forms.service.motorcycle_pricing_tiers = normalizeServiceTierMap({}, motorcycleServiceTierOptions, 0, 30)

const stockByProductId = computed(() => {
  const map = {}
  for (const item of inventoryItems.value) {
    const pid = Number(item.product)
    if (!Number.isFinite(pid)) continue
    map[pid] = Number(item.available_quantity ?? item.quantity_on_hand ?? 0)
  }
  return map
})

const productsWithStock = computed(() => products.value.map((item) => ({
  ...item,
  stock_qty: stockByProductId.value[Number(item.id)] ?? 0
})))

const workerRoleOrder = (worker) => (worker?.role_key || worker?.role) === 'operator' ? 0 : 1
const filteredWorkers = computed(() => workers.value
  .filter((i) => (`${i.full_name} ${i.username || ''} ${i.phone || ''} ${i.role || ''}`).includes(search.value))
  .slice()
  .sort((a, b) => workerRoleOrder(a) - workerRoleOrder(b) || String(a.full_name || '').localeCompare(String(b.full_name || ''), 'fa'))
)
const filteredProducts = computed(() => productsWithStock.value.filter((i) => (`${i.name} ${i.description || ''} ${i.unit || ''}`).includes(search.value)))
const filteredExpenses = computed(() => expenses.value.filter((i) => (`${i.title || ''} ${i.details || ''} ${i.source_label || ''}`).includes(search.value)))
const filteredServices = computed(() => services.value.filter((i) => (`${i.name} ${i.description || ''}`).includes(search.value)))
const fullStarDiscountLabel = computed(() => `${Number((Number(generalSettings.discount_percent_per_half_star || 0) * 2).toFixed(2)).toLocaleString('fa-IR')}٪`)
const normalizeFixedVisitDiscounts = (value = {}) => {
  const source = value && typeof value === 'object' ? value : {}
  return fixedDiscountVisitItems.reduce((acc, item) => {
    const numericValue = Math.max(0, Math.min(100, Number(source[item.key] ?? source[Number(item.key)] ?? 0) || 0))
    acc[item.key] = Number(numericValue.toFixed(2))
    return acc
  }, {})
}
const fixedDiscountPreviewLabel = computed(() => fixedDiscountVisitItems
  .map((item) => `${item.label}: ${Number(generalSettings.fixed_visit_discounts?.[item.key] || 0).toLocaleString('fa-IR')}٪`)
  .join('، '))
const expensesTotal = computed(() => filteredExpenses.value.reduce((sum, item) => sum + Number(item.amount || 0), 0))
const smsTemplateTokens = [
  '[نام مشتری]',
  '[جنسیت مشتری]',
  '[نام کارواش]',
  '[شماره پذیرش]',
  '[پلاک]',
  '[ساعت تخصیص]',
  '[تاریخ تخصیص]',
  '[خلاصه خدمات]',
  '[جمع کل]',
  '[جمع نرخ نامه]',
  '[ساعت ترخیص]',
  '[تاریخ ترخیص]',
  '[امتیاز مشتری]',
  '[درصد تخفیف مراجعه بعد]',
  '[درصد تخفیف امتیاز مشتری]',
  '[تعداد مراجعات]',
  '[تعداد مراجعه]',
  '[انعام]',
  '[تخفیف مجموعه]',
  '[تخفیف امتیاز مشتری]',
  '[تخفیف دستی]',
  '[مالیات]',
  '[مبلغ نهایی]',
  '[جمع تخفیف]'
]
const SMS_CHARS_PER_SEGMENT = 70
const SMS_PRICE_PER_SEGMENT = 185

const toPersianDigits = (value) => String(value ?? '').replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)] || digit)

const toPersianMoney = (value) => toPersianDigits(Number(value || 0).toLocaleString('en-US'))

const smsEstimatedCostLabel = (text) => {
  const chars = smsCharacterCount(text)
  const segments = smsSegmentsForText(text, { charsPerSegment: SMS_CHARS_PER_SEGMENT })
  if (!segments) return 'بدون هزینه'
  const amount = smsCostForText(text, {
    pricePerSegment: SMS_PRICE_PER_SEGMENT,
    charsPerSegment: SMS_CHARS_PER_SEGMENT,
  })
  return `${toPersianDigits(chars)} کاراکتر • ${toPersianDigits(segments)} پارت • حدود ${toPersianMoney(amount)} تومان`
}

const ensureReleasedSmsTemplateDetails = (template) => {
  const text = String(template || '')
    .replaceAll('[خطاب مشتری]', '[نام مشتری]')
    .replaceAll('سفارش بعد', 'مراجعه بعد')
    .replaceAll('از کارواش', 'از مجموعه کارواش')
    .trim()
  if (!text) return text
  const lines = text.split('\n')
  const insertions = []
  if (!text.includes('[تعداد مراجعات]')) insertions.push('تعداد دفعات مراجعه: [تعداد مراجعات]')
  if (!text.includes('[انعام]')) insertions.push('انعام: [انعام]')
  if (!text.includes('[مالیات]')) insertions.push('مالیات: [مالیات]')
  if (!insertions.length) return orderAssignedFinancialLines(lines.join('\n'))
  const anchorIndex = lines.findIndex((line) => line.includes('[درصد تخفیف مراجعه بعد]') || line.includes('[درصد تخفیف سفارش بعد]'))
  const insertAt = anchorIndex >= 0 ? anchorIndex + 1 : Math.max(1, lines.length - 3)
  lines.splice(insertAt, 0, ...insertions)
  return lines.join('\n')
}
const orderAssignedFinancialLines = (template) => {
  const lines = String(template || '').split('\n')
  const servicesIndex = lines.findIndex((line) => line.includes('[خلاصه خدمات]'))
  if (servicesIndex < 0) return lines.join('\n')
  const financialLines = { total: null, discount: null, tax: null, final: null }
  const remaining = []
  lines.forEach((line) => {
    if (line.includes('[جمع کل]') || line.includes('[جمع نرخ نامه]')) financialLines.total = line
    else if (line.includes('[جمع تخفیف]')) financialLines.discount = line
    else if (line.includes('[مالیات]')) financialLines.tax = line
    else if (line.includes('[مبلغ نهایی]')) financialLines.final = line
    else remaining.push(line)
  })
  const nextServicesIndex = remaining.findIndex((line) => line.includes('[خلاصه خدمات]'))
  let insertAt = nextServicesIndex + 1
  if (remaining[insertAt]?.trim() === '---------------') insertAt += 1
  remaining.splice(insertAt, 0, ...[financialLines.total, financialLines.discount, financialLines.tax, financialLines.final].filter(Boolean))
  return remaining.join('\n')
}
const ensureAssignedSmsTemplateDetails = (template, { includeFinancials = true } = {}) => {
  const text = String(template || '')
    .replaceAll('[خطاب مشتری]', '[نام مشتری] عزیز')
    .replaceAll('شماره پذیرش: [شماره پذیرش]\nخودروی شما با پلاک [پلاک]،', 'خودروی شما با\nشماره پذیرش: [شماره پذیرش] با پلاک [پلاک]،')
    .replaceAll('شماره پذیرش: [شماره پذیرش]\nخودروی شما با پلاک [پلاک]', 'خودروی شما با\nشماره پذیرش: [شماره پذیرش] با پلاک [پلاک]')
    .replaceAll('با پلاک [پلاک] در ساعت', 'با پلاک [پلاک]، در ساعت')
    .replaceAll('[ساعت تخصیص] روز', '[ساعت تخصیص]، روز')
    .replaceAll('[تاریخ تخصیص]، در کارواش', '[تاریخ تخصیص] در مجموعه کارواش')
    .replaceAll('[تاریخ تخصیص] در کارواش', '[تاریخ تخصیص] در مجموعه کارواش')
    .replaceAll('برای انجام خدمات ثبت و تخصیص داده شد', 'برای انجام خدمات، پذیرش شد')
    .replaceAll('برای انجام خدمات، ثبت و تخصیص داده شد', 'برای انجام خدمات، پذیرش شد')
    .replaceAll('تخصیص داده شد', 'پذیرش شد')
    .replaceAll('پیش فاکتور خدمات:', 'خدمات:')
    .replaceAll('پیش‌فاکتور خدمات:', 'خدمات:')
    .replaceAll('مبلغ نهایی بعد از تخفیف:', 'مبلغ نهایی:')
    .replaceAll('1 ساعت کاری', '30 دقیقه')
    .trim()
  if (!text) return text
  const lines = text.split('\n')
  const insertions = []
  if (!text.includes('[شماره پذیرش]')) lines.splice(1, 0, 'شماره پذیرش: [شماره پذیرش]')
  if (includeFinancials && text.includes('[خلاصه خدمات]') && !text.includes('---------------')) {
    const servicesIndex = lines.findIndex((line) => line.includes('[خلاصه خدمات]'))
    if (servicesIndex >= 0) lines.splice(servicesIndex + 1, 0, '---------------')
  }
  if (includeFinancials && !text.includes('[خلاصه خدمات]')) {
    insertions.push('خدمات:')
    insertions.push('[خلاصه خدمات]')
    insertions.push('---------------')
  }
  if (includeFinancials && !text.includes('[جمع کل]') && !text.includes('[جمع نرخ نامه]')) insertions.push('جمع کل: [جمع کل]')
  if (includeFinancials && !text.includes('[جمع تخفیف]')) insertions.push('تخفیف این سفارش: [جمع تخفیف]')
  if (includeFinancials && !text.includes('[مالیات]')) insertions.push('مالیات: [مالیات]')
  if (includeFinancials && !text.includes('[مبلغ نهایی]')) insertions.push('مبلغ نهایی: [مبلغ نهایی]')
  if (!text.includes('آماده ترخیص')) insertions.push('خودروی شما حدود 30 دقیقه دیگر آماده ترخیص است.')
  if (!text.includes('از اعتماد شما سپاسگزاریم')) insertions.push('از اعتماد شما سپاسگزاریم')
  if (!insertions.length) return text
  const anchorIndex = lines.findIndex((line) => line.includes('[جمع کل]') || line.includes('[جمع نرخ نامه]'))
  const insertAt = anchorIndex >= 0 ? anchorIndex + 1 : lines.length
  lines.splice(insertAt, 0, ...insertions)
  return orderAssignedFinancialLines(lines.join('\n'))
}

const mergeAssignedSmsTemplate = (assignedTemplate, invoiceTemplate) => {
  const assignedText = String(assignedTemplate || '').trim()
  const invoiceText = String(invoiceTemplate || '').trim()
  if (!invoiceText || assignedText.includes('[خلاصه خدمات]')) return ensureAssignedSmsTemplateDetails(assignedText)
  return ensureAssignedSmsTemplateDetails([assignedText, invoiceText].filter(Boolean).join('\n'))
}
const smsPreviewContext = computed(() => {
  const isFixed = generalSettings.discount_calculation_mode === 'fixed'
  const nextDiscountPreview = isFixed ? 'درصد تخفیف مراجعه دوم : ۱۰٪' : '۱۰٪'
  return {
    '[خطاب مشتری]': 'آقای رضایی عزیز',
    '[نام مشتری]': 'آقای علی رضایی',
    '[جنسیت مشتری]': 'آقای',
    '[نام کارواش]': authStore.user?.tenant_name || authStore.user?.tenant?.name || 'سونامی',
    '[شماره پذیرش]': '۱۰۰۰',
    '[پلاک]': '67 - 345 ب 22',
    '[ساعت تخصیص]': '10:30',
    '[تاریخ تخصیص]': '1405/04/22',
    '[خلاصه خدمات]': 'روشویی : ۷۰،۰۰۰ تومان\nواکس بدنه : ۱۲۰،۰۰۰ تومان',
    '[جمع کل]': '350،000 تومان',
    '[جمع نرخ نامه]': '350،000 تومان',
    '[ساعت ترخیص]': '12:15',
    '[تاریخ ترخیص]': '1405/04/22',
    '[امتیاز مشتری]': '2.5',
    '[درصد تخفیف مراجعه بعد]': nextDiscountPreview,
    '[درصد تخفیف سفارش بعد]': nextDiscountPreview,
    '[درصد تخفیف امتیاز مشتری]': '۱۰٪',
    '[تعداد مراجعات]': '۵',
    '[تعداد مراجعه]': '۵',
    '[انعام]': '50،000 تومان',
    '[تخفیف مجموعه]': '80،000 تومان',
    '[تخفیف امتیاز مشتری]': '35،000 تومان',
    '[تخفیف دستی]': '20،000 تومان',
    '[جمع تخفیف]': '135،000 تومان',
    '[مالیات]': '26،500 تومان',
    '[مبلغ نهایی]': '291،500 تومان'
  }
})
const prepareReleasedDiscountPreviewTemplate = (template) => {
  const isFixed = generalSettings.discount_calculation_mode === 'fixed'
  return String(template || '')
    .split('\n')
    .map((line) => {
      const hasToken = line.includes('[درصد تخفیف مراجعه بعد]') || line.includes('[درصد تخفیف سفارش بعد]')
      if (!hasToken) return line
      return isFixed ? '[درصد تخفیف مراجعه بعد]' : line
    })
    .join('\n')
}
const renderSmsPreview = (template) => {
  let message = String(template || '').trim()
  Object.entries(smsPreviewContext.value).forEach(([token, value]) => {
    message = message.replaceAll(token, value)
  })
  return message
}
const smsAssignedPreview = computed(() => renderSmsPreview(ensureAssignedSmsTemplateDetails(generalSettings.sms_vehicle_assigned_template)))
const smsReleasedPreview = computed(() => renderSmsPreview(
  prepareReleasedDiscountPreviewTemplate(ensureReleasedSmsTemplateDetails(generalSettings.sms_vehicle_released_template))
))
const smsAssignedEstimatedCostLabel = computed(() => smsEstimatedCostLabel(smsAssignedPreview.value))
const smsReleasedEstimatedCostLabel = computed(() => smsEstimatedCostLabel(smsReleasedPreview.value))

watch(() => forms.purchase.product_id, (newProductId) => {
  const selected = products.value.find((item) => Number(item.id) === Number(newProductId))
  if (!selected) return
  forms.purchase.unit_cost = toThousandsDisplay(selected.cost_price || 0)
  forms.purchase.sale_price = toThousandsDisplay(selected.sale_price || 0)
})

watch(() => forms.worker.has_entrusted_item, (enabled) => {
  if (enabled && !forms.worker.entrusted_items.length) {
    forms.worker.entrusted_items = [createEntrustedItem()]
    return
  }
  if (!enabled) forms.worker.entrusted_items = []
})

watch(() => forms.worker.role, (role) => {
  if (role === 'worker') {
    forms.worker.username = ''
    forms.worker.password = ''
  }
})

const loadAll = async () => {
  try {
    const [w, p, e, s, inv] = await Promise.all([
      api.get('/workers/', { params: { include_inactive: 1 } }),
      api.get('/products/'),
      api.get('/inventory/expenses/'),
      api.get('/services/'),
      api.get('/inventory/')
    ])
    workers.value = Array.isArray(w.data) ? w.data : []
    products.value = Array.isArray(p.data) ? p.data : []
    expenses.value = Array.isArray(e.data) ? e.data : []
    services.value = Array.isArray(s.data) ? s.data : []
    inventoryItems.value = Array.isArray(inv.data) ? inv.data : []
    try {
      const gs = await api.get('/services/general-settings/')
      generalSettings.discount_calculation_mode = gs.data?.discount_calculation_mode === 'fixed' ? 'fixed' : 'step'
      generalSettings.discount_percent_per_half_star = Number(gs.data?.discount_percent_per_half_star || 0)
      generalSettings.fixed_visit_discounts = normalizeFixedVisitDiscounts(gs.data?.fixed_visit_discounts)
      generalSettings.tax_enabled = Boolean(gs.data?.tax_enabled)
      generalSettings.tax_percent = Number(gs.data?.tax_percent || 0)
      generalSettings.preferred_bank_name = gs.data?.preferred_bank_name || ''
      generalSettings.bank_account_holder = gs.data?.bank_account_holder || ''
      generalSettings.bank_card_number = gs.data?.bank_card_number || ''
      generalSettings.bank_account_iban = gs.data?.bank_account_iban || ''
      generalSettings.pos_device_name = gs.data?.pos_device_name || ''
      generalSettings.pos_terminal_id = gs.data?.pos_terminal_id || ''
      generalSettings.payment_methods_note = gs.data?.payment_methods_note || ''
      generalSettings.receipt_printer_enabled = Boolean(gs.data?.receipt_printer_enabled)
      generalSettings.receipt_printer_name = gs.data?.receipt_printer_name || ''
      generalSettings.receipt_printer_paper_width = gs.data?.receipt_printer_paper_width || '80mm'
      generalSettings.receipt_auto_print = Boolean(gs.data?.receipt_auto_print)
      generalSettings.receipt_show_logo = Boolean(gs.data?.receipt_show_logo)
      generalSettings.receipt_show_qr = Boolean(gs.data?.receipt_show_qr)
      generalSettings.receipt_header_note = gs.data?.receipt_header_note || ''
      generalSettings.receipt_footer_note = gs.data?.receipt_footer_note || ''
      generalSettings.sms_provider_base_url = gs.data?.sms_provider_base_url || 'https://api.iranpayamak.com'
      generalSettings.sms_provider_line_number = gs.data?.sms_provider_line_number || ''
      generalSettings.sms_provider_api_key_configured = Boolean(gs.data?.sms_provider_api_key_configured)
      generalSettings.sms_provider_source = gs.data?.sms_provider_source || 'env'
      generalSettings.sms_vehicle_auto_send_enabled = gs.data?.sms_vehicle_auto_send_enabled !== false
      generalSettings.sms_vehicle_assigned_enabled = gs.data?.sms_vehicle_assigned_enabled !== false
      generalSettings.sms_vehicle_assigned_invoice_enabled = gs.data?.sms_vehicle_assigned_invoice_enabled !== false
      generalSettings.sms_vehicle_released_enabled = gs.data?.sms_vehicle_released_enabled !== false
      generalSettings.sms_vehicle_assigned_template = mergeAssignedSmsTemplate(
        gs.data?.sms_vehicle_assigned_template || '',
        gs.data?.sms_vehicle_assigned_invoice_template || ''
      )
      generalSettings.sms_vehicle_assigned_invoice_template = ''
      generalSettings.sms_vehicle_released_template = ensureReleasedSmsTemplateDetails(gs.data?.sms_vehicle_released_template || '')
    } catch {
      generalSettings.discount_calculation_mode = 'step'
      generalSettings.discount_percent_per_half_star = 0
      generalSettings.fixed_visit_discounts = normalizeFixedVisitDiscounts()
      generalSettings.tax_enabled = false
      generalSettings.tax_percent = 0
      generalSettings.preferred_bank_name = ''
      generalSettings.bank_account_holder = ''
      generalSettings.bank_card_number = ''
      generalSettings.bank_account_iban = ''
      generalSettings.pos_device_name = ''
      generalSettings.pos_terminal_id = ''
      generalSettings.payment_methods_note = ''
      generalSettings.receipt_printer_enabled = false
      generalSettings.receipt_printer_name = ''
      generalSettings.receipt_printer_paper_width = '80mm'
      generalSettings.receipt_auto_print = false
      generalSettings.receipt_show_logo = false
      generalSettings.receipt_show_qr = false
      generalSettings.receipt_header_note = ''
      generalSettings.receipt_footer_note = ''
      generalSettings.sms_provider_base_url = 'https://api.iranpayamak.com'
      generalSettings.sms_provider_line_number = ''
      generalSettings.sms_provider_api_key_configured = false
      generalSettings.sms_provider_source = 'env'
      generalSettings.sms_vehicle_auto_send_enabled = true
      generalSettings.sms_vehicle_assigned_enabled = true
      generalSettings.sms_vehicle_assigned_invoice_enabled = true
      generalSettings.sms_vehicle_released_enabled = true
      generalSettings.sms_vehicle_assigned_template = ''
      generalSettings.sms_vehicle_assigned_invoice_template = ''
      generalSettings.sms_vehicle_released_template = ''
    }
  } catch (e) {
    errorMessage.value = resolveApiErrorMessage(e, 'خطا در بارگذاری داده‌ها')
  }
}

const saveGeneralSettings = async () => {
  generalSettingsSaving.value = true
  try {
    const payload = {
      discount_calculation_mode: generalSettings.discount_calculation_mode === 'fixed' ? 'fixed' : 'step',
      discount_percent_per_half_star: Number(generalSettings.discount_percent_per_half_star || 0),
      fixed_visit_discounts: normalizeFixedVisitDiscounts(generalSettings.fixed_visit_discounts),
      tax_enabled: Boolean(generalSettings.tax_enabled),
      tax_percent: Number(generalSettings.tax_percent || 0),
      preferred_bank_name: generalSettings.preferred_bank_name || '',
      bank_account_holder: generalSettings.bank_account_holder || '',
      bank_card_number: generalSettings.bank_card_number || '',
      bank_account_iban: generalSettings.bank_account_iban || '',
      pos_device_name: generalSettings.pos_device_name || '',
      pos_terminal_id: generalSettings.pos_terminal_id || '',
      payment_methods_note: generalSettings.payment_methods_note || '',
      receipt_printer_enabled: Boolean(generalSettings.receipt_printer_enabled),
      receipt_printer_name: generalSettings.receipt_printer_name || '',
      receipt_printer_paper_width: generalSettings.receipt_printer_paper_width || '80mm',
      receipt_print_copies: 1,
      receipt_auto_print: Boolean(generalSettings.receipt_auto_print),
      receipt_show_logo: Boolean(generalSettings.receipt_show_logo),
      receipt_show_qr: Boolean(generalSettings.receipt_show_qr),
      receipt_header_note: generalSettings.receipt_header_note || '',
      receipt_footer_note: generalSettings.receipt_footer_note || '',
      sms_vehicle_assigned_enabled: Boolean(generalSettings.sms_vehicle_assigned_enabled),
      sms_vehicle_assigned_invoice_enabled: false,
      sms_vehicle_released_enabled: Boolean(generalSettings.sms_vehicle_released_enabled),
      sms_vehicle_assigned_template: ensureAssignedSmsTemplateDetails(generalSettings.sms_vehicle_assigned_template || ''),
      sms_vehicle_assigned_invoice_template: '',
      sms_vehicle_auto_send_enabled: Boolean(generalSettings.sms_vehicle_auto_send_enabled),
      sms_vehicle_released_template: ensureReleasedSmsTemplateDetails(generalSettings.sms_vehicle_released_template || '')
    }
    const response = await api.patch('/services/general-settings/', payload)
    generalSettings.discount_calculation_mode = response.data?.discount_calculation_mode === 'fixed' ? 'fixed' : 'step'
    generalSettings.discount_percent_per_half_star = Number(response.data?.discount_percent_per_half_star || 0)
    generalSettings.fixed_visit_discounts = normalizeFixedVisitDiscounts(response.data?.fixed_visit_discounts)
    generalSettings.tax_enabled = Boolean(response.data?.tax_enabled)
    generalSettings.tax_percent = Number(response.data?.tax_percent || 0)
    generalSettings.preferred_bank_name = response.data?.preferred_bank_name || ''
    generalSettings.bank_account_holder = response.data?.bank_account_holder || ''
    generalSettings.bank_card_number = response.data?.bank_card_number || ''
    generalSettings.bank_account_iban = response.data?.bank_account_iban || ''
    generalSettings.pos_device_name = response.data?.pos_device_name || ''
    generalSettings.pos_terminal_id = response.data?.pos_terminal_id || ''
    generalSettings.payment_methods_note = response.data?.payment_methods_note || ''
    generalSettings.receipt_printer_enabled = Boolean(response.data?.receipt_printer_enabled)
    generalSettings.receipt_printer_name = response.data?.receipt_printer_name || ''
    generalSettings.receipt_printer_paper_width = response.data?.receipt_printer_paper_width || '80mm'
    generalSettings.receipt_auto_print = Boolean(response.data?.receipt_auto_print)
    generalSettings.receipt_show_logo = Boolean(response.data?.receipt_show_logo)
    generalSettings.receipt_show_qr = Boolean(response.data?.receipt_show_qr)
    generalSettings.receipt_header_note = response.data?.receipt_header_note || ''
    generalSettings.receipt_footer_note = response.data?.receipt_footer_note || ''
    generalSettings.sms_provider_base_url = response.data?.sms_provider_base_url || 'https://api.iranpayamak.com'
    generalSettings.sms_provider_line_number = response.data?.sms_provider_line_number || ''
    generalSettings.sms_provider_api_key_configured = Boolean(response.data?.sms_provider_api_key_configured)
    generalSettings.sms_provider_source = response.data?.sms_provider_source || 'env'
    generalSettings.sms_vehicle_auto_send_enabled = response.data?.sms_vehicle_auto_send_enabled !== false
    generalSettings.sms_vehicle_assigned_enabled = response.data?.sms_vehicle_assigned_enabled !== false
    generalSettings.sms_vehicle_assigned_invoice_enabled = response.data?.sms_vehicle_assigned_invoice_enabled !== false
    generalSettings.sms_vehicle_released_enabled = response.data?.sms_vehicle_released_enabled !== false
    generalSettings.sms_vehicle_assigned_template = ensureAssignedSmsTemplateDetails(response.data?.sms_vehicle_assigned_template || '')
    generalSettings.sms_vehicle_assigned_invoice_template = ''
    generalSettings.sms_vehicle_released_template = ensureReleasedSmsTemplateDetails(response.data?.sms_vehicle_released_template || '')
    t('تنظیمات عمومی ذخیره شد')
  } catch (e) {
    t(apiErrorText(e), 'error')
  } finally {
    generalSettingsSaving.value = false
  }
}

const addEntrustedItem = () => {
  forms.worker.entrusted_items.push(createEntrustedItem())
}

const removeEntrustedItem = (index) => {
  forms.worker.entrusted_items.splice(index, 1)
  if (!forms.worker.entrusted_items.length) forms.worker.has_entrusted_item = false
}

const openWorkerModal = (item = null) => {
  modal.open = true
  modal.type = 'workers'
  modal.id = item?.id || null
  modal.title = modal.id ? 'ویرایش پرسنل' : 'افزودن پرسنل'
  forms.worker.full_name = item?.full_name || ''
  forms.worker.role = item?.role_key || 'worker'
  forms.worker.username = (item?.role_key || 'worker') === 'worker' ? '' : (item?.username || '')
  forms.worker.password = ''
  forms.worker.phone = normalizeIranMobile(item?.phone || '')
  workerPhoneTouched.value = false
  forms.worker.address = item?.address || ''
  forms.worker.payment_type = item?.payment_type || 'percent'
  forms.worker.payment_value = ['fixed', 'hourly'].includes(forms.worker.payment_type)
    ? toThousandsDisplay(item?.payment_value || 0)
    : Number(item?.payment_value || 0)
  forms.worker.insurance_amount = toThousandsDisplay(item?.insurance_amount || 0)
  forms.worker.tip_share_percent = Number(item?.tip_share_percent || 0)
  forms.worker.is_available = item?.is_available ?? true
  forms.worker.has_entrusted_item = Boolean(item?.has_entrusted_item)
  forms.worker.entrusted_items = Array.isArray(item?.entrusted_items) && item.entrusted_items.length
    ? item.entrusted_items.map((entrustedItem) => ({
        title: entrustedItem?.title || '',
        entrusted_at: entrustedItem?.entrusted_at || '',
        quantity: Number(entrustedItem?.quantity || 0),
        price: toThousandsDisplay(entrustedItem?.price || 0)
      }))
    : (forms.worker.has_entrusted_item
        ? [{
            title: item?.entrusted_item_description || '',
            quantity: Number(item?.entrusted_item_quantity || 0),
            price: toThousandsDisplay(item?.entrusted_item_price || 0)
          }]
        : [])
  forms.worker.entrusted_item_description = item?.entrusted_item_description || ''
  forms.worker.entrusted_item_quantity = Number(item?.entrusted_item_quantity || 0)
  forms.worker.entrusted_item_price = toThousandsDisplay(item?.entrusted_item_price || 0)
  if (forms.worker.has_entrusted_item && !forms.worker.entrusted_items.length) forms.worker.entrusted_items = [createEntrustedItem()]
}

const openProductModal = (item = null) => {
  modal.open = true
  modal.type = 'products'
  modal.id = item?.id || null
  modal.title = modal.id ? 'ویرایش محصول' : 'افزودن محصول'
  Object.assign(forms.product, {
    name: item?.name || '',
    description: item?.description || '',
    sale_price: toThousandsDisplay(item?.sale_price),
    cost_price: toThousandsDisplay(item?.cost_price),
    unit: item?.unit || 'unit',
    min_stock: Number(item?.min_stock || 0),
    is_active: item?.is_active ?? true
  })
}

const openProductPurchaseModal = (item = null) => {
  modal.open = true
  modal.type = 'product_purchase'
  modal.id = null
  modal.title = 'ثبت خرید جدید'
  Object.assign(forms.purchase, {
    product_id: Number(item?.id || 0),
    quantity: 1,
    unit_cost: toThousandsDisplay(item?.cost_price || 0),
    sale_price: toThousandsDisplay(item?.sale_price || 0),
    note: ''
  })
}

const openExpenseModal = (item = null) => {
  modal.open = true
  modal.type = 'expenses'
  modal.id = item?.can_edit ? item.id : null
  modal.title = modal.id ? 'ویرایش هزینه' : 'ثبت هزینه جدید'
  Object.assign(forms.expense, {
    title: item?.title || '',
    amount: toThousandsDisplay(item?.amount || 0),
    details: item?.details || '',
    spent_at_jalali: toJalaliInput(item?.spent_at || item?.created_at),
    attachment: null,
    attachment_name: item?.attachment_name || '',
    attachment_url: item?.attachment_url || ''
  })
}

const handleExpenseAttachmentChange = (event) => {
  const file = event?.target?.files?.[0] || null
  forms.expense.attachment = file
  forms.expense.attachment_name = file?.name || forms.expense.attachment_name || ''
}

const openProductHistoryModal = async (item) => {
  if (!item?.id) return
  productHistoryModal.open = true
  productHistoryModal.loading = true
  productHistoryModal.product = item
  productHistoryModal.history = []
  try {
    const { data } = await api.get(`/inventory/product-history/${item.id}/`)
    productHistoryModal.product = data?.product || item
    productHistoryModal.history = Array.isArray(data?.history) ? data.history : []
  } catch (e) {
    t(apiErrorText(e), 'error')
    closeProductHistoryModal()
  } finally {
    productHistoryModal.loading = false
  }
}

const closeProductHistoryModal = () => {
  productHistoryModal.open = false
  productHistoryModal.loading = false
  productHistoryModal.product = null
  productHistoryModal.history = []
}

const openServiceHistoryModal = async (item) => {
  if (!item?.id) return
  serviceHistoryModal.open = true
  serviceHistoryModal.loading = true
  serviceHistoryModal.service = item
  serviceHistoryModal.history = []
  try {
    const { data } = await api.get(`/services/${item.id}/history/`)
    serviceHistoryModal.service = data?.service || item
    serviceHistoryModal.history = Array.isArray(data?.history) ? data.history : []
  } catch (e) {
    t(apiErrorText(e), 'error')
    closeServiceHistoryModal()
  } finally {
    serviceHistoryModal.loading = false
  }
}

const closeServiceHistoryModal = () => {
  serviceHistoryModal.open = false
  serviceHistoryModal.loading = false
  serviceHistoryModal.service = null
  serviceHistoryModal.history = []
}

const openServiceModal = (item = null) => {
  modal.open = true
  modal.type = 'services'
  modal.id = item?.id || null
  modal.title = modal.id ? 'ویرایش خدمت' : 'افزودن خدمت'
  const fallbackSalePrice = item?.pricing_tiers?.type_1?.sale_price ?? item?.base_price ?? 0
  const fallbackDuration = Number((item?.pricing_tiers?.type_1?.duration_minutes ?? item?.estimated_duration_minutes) || 30)
  Object.assign(forms.service, {
    name: item?.name || '',
    description: item?.description || '',
    base_price: toThousandsDisplay(fallbackSalePrice),
    estimated_duration_minutes: fallbackDuration,
    is_active: item?.is_active ?? true,
    motorcycle_enabled: Boolean(item?.motorcycle_enabled),
    pricing_tiers: normalizeServiceTierMap(item?.pricing_tiers, carServiceTierOptions, fallbackSalePrice, fallbackDuration),
    motorcycle_pricing_tiers: normalizeServiceTierMap(item?.motorcycle_pricing_tiers, motorcycleServiceTierOptions, fallbackSalePrice, fallbackDuration)
  })
}

const closeModal = () => {
  modal.open = false
  modal.type = ''
  modal.id = null
}

const formatDate = (value) => formatJalaliDate(value)
const dateTime = (value) => formatJalaliDate(value)

const submitModal = async () => {
  try {
    if (modal.type === 'workers') {
      workerPhoneTouched.value = true
      forms.worker.phone = normalizeIranMobile(forms.worker.phone)
      const phoneError = iranMobileErrorMessage(forms.worker.phone, { label: 'شماره موبایل' })
      if (phoneError) {
        t(phoneError, 'error')
        return
      }
      const paymentValueNormalized = ['fixed', 'hourly'].includes(forms.worker.payment_type)
        ? fromThousandsInput(forms.worker.payment_value)
        : Number(forms.worker.payment_value || 0)
      const entrustedItemsPayload = forms.worker.has_entrusted_item
        ? forms.worker.entrusted_items.map((item) => ({
            title: (item?.title || '').trim(),
            entrusted_at: item?.entrusted_at || '',
            quantity: Number(item?.quantity || 0),
            price: fromThousandsInput(item?.price || 0)
          }))
        : []
      const primaryEntrustedItem = entrustedItemsPayload[0] || null
      const workerPayload = {
        full_name: forms.worker.full_name,
        role: forms.worker.role || 'worker',
        username: forms.worker.role === 'worker' ? '' : forms.worker.username,
        password: forms.worker.role === 'worker' ? '' : forms.worker.password,
        phone: forms.worker.phone,
        address: forms.worker.address || '',
        is_available: forms.worker.is_available,
        payment_type: forms.worker.payment_type,
        payment_value: Number.isFinite(Number(paymentValueNormalized)) ? Number(paymentValueNormalized) : 0,
        insurance_amount: fromThousandsInput(forms.worker.insurance_amount || 0),
        tip_share_percent: Number(forms.worker.tip_share_percent || 0),
        has_entrusted_item: Boolean(forms.worker.has_entrusted_item),
        entrusted_items: entrustedItemsPayload,
        entrusted_item_description: primaryEntrustedItem?.title || '',
        entrusted_item_quantity: Number(primaryEntrustedItem?.quantity || 0),
        entrusted_item_price: Number(primaryEntrustedItem?.price || 0)
      }
      if (modal.id) await api.patch(`/workers/${modal.id}/`, workerPayload)
      else await api.post('/workers/', workerPayload)
      t('پرسنل ذخیره شد')
    } else if (modal.type === 'products') {
      const payload = {
        ...forms.product,
        sale_price: fromThousandsInput(forms.product.sale_price),
        cost_price: fromThousandsInput(forms.product.cost_price)
      }
      if (modal.id) await api.patch(`/products/${modal.id}/`, payload)
      else await api.post('/products/', payload)
      t('محصول ذخیره شد')
    } else if (modal.type === 'product_purchase') {
      const payload = {
        product_id: Number(forms.purchase.product_id || 0),
        quantity: Number(forms.purchase.quantity || 0),
        unit_cost: fromThousandsInput(forms.purchase.unit_cost || 0),
        sale_price: fromThousandsInput(forms.purchase.sale_price || 0),
        note: forms.purchase.note || ''
      }
      await api.post('/inventory/purchase/', payload)
      t('خرید محصول ثبت شد')
    } else if (modal.type === 'expenses') {
      const payload = new FormData()
      payload.append('title', forms.expense.title || '')
      payload.append('amount', String(fromThousandsInput(forms.expense.amount || 0)))
      payload.append('details', forms.expense.details || '')
      const spentAt = parseJalaliToIso(forms.expense.spent_at_jalali)
      if (spentAt) payload.append('spent_at', spentAt)
      if (forms.expense.attachment) payload.append('attachment', forms.expense.attachment)
      if (modal.id) await api.patch(`/inventory/expenses/${modal.id}/`, payload)
      else await api.post('/inventory/expenses/', payload)
      t(modal.id ? 'هزینه ویرایش شد' : 'هزینه ثبت شد')
    } else {
      const pricingTiers = buildServiceTiersPayload(forms.service.pricing_tiers, carServiceTierOptions)
      const motorcyclePricingTiers = forms.service.motorcycle_enabled
        ? buildServiceTiersPayload(forms.service.motorcycle_pricing_tiers, motorcycleServiceTierOptions)
        : {}
      const primaryCarTier = pricingTiers.type_1 || { sale_price: 0, duration_minutes: 30 }
      const payload = {
        ...forms.service,
        base_price: Number(primaryCarTier.sale_price || 0),
        estimated_duration_minutes: Number(primaryCarTier.duration_minutes || 30),
        motorcycle_enabled: Boolean(forms.service.motorcycle_enabled),
        pricing_tiers: pricingTiers,
        motorcycle_pricing_tiers: motorcyclePricingTiers
      }
      if (modal.id) await api.patch(`/services/${modal.id}/`, payload)
      else await api.post('/services/', payload)
      t('خدمت ذخیره شد')
    }

    closeModal()
    await loadAll()
  } catch (e) {
    t(apiErrorText(e), 'error')
  }
}

const toggleWorkerAvailability = async (item) => {
  if (!item?.id) return
  const nextAvailability = !item.is_available
  if (!confirm(`پرسنل «${item.full_name}» ${nextAvailability ? 'فعال' : 'غیرفعال'} شود؟`)) return
  await api.patch(`/workers/${item.id}/`, {
    full_name: item.full_name,
    role: item.role_key || item.role,
    username: item.role_key === 'worker' ? '' : (item.username || ''),
    phone: item.phone || '',
    address: item.address || '',
    is_available: nextAvailability,
    payment_type: item.payment_type || 'percent',
    payment_value: Number(item.payment_value || 0),
    insurance_amount: Number(item.insurance_amount || 0),
    tip_share_percent: Number(item.tip_share_percent || 0),
    has_entrusted_item: Boolean(item.has_entrusted_item),
    entrusted_items: Array.isArray(item.entrusted_items) ? item.entrusted_items : [],
    entrusted_item_description: item.entrusted_item_description || '',
    entrusted_item_quantity: Number(item.entrusted_item_quantity || 0),
    entrusted_item_price: Number(item.entrusted_item_price || 0)
  })
  t(nextAvailability ? 'پرسنل فعال شد' : 'پرسنل غیرفعال شد')
  await loadAll()
}
const deleteProduct = async (item) => { if (!confirm('حذف شود؟')) return; await api.delete(`/products/${item.id}/`); t('حذف شد'); await loadAll() }
const deleteExpense = async (item) => { if (!confirm('حذف شود؟')) return; await api.delete(`/inventory/expenses/${item.id}/`); t('حذف شد'); await loadAll() }
const deleteService = async (item) => { if (!confirm('حذف شود؟')) return; await api.delete(`/services/${item.id}/`); t('حذف شد'); await loadAll() }

onMounted(async () => {
  await authStore.fetchMe()
  await loadAll()
})
</script>

<style scoped>
.settings-content { min-width: 0; }
.tabs-bar { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.chip { border: 0; background: #e2e8f0; color: #334155; padding: 8px 14px; border-radius: 999px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }
.chip.active { background: #2563eb; color: #fff; }
.chip.active :deep(.iconly-shell),
.primary-btn :deep(.iconly-shell) { --iconly-filter: brightness(0) saturate(100%) invert(100%); }
.card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px; }
.head-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 10px; }
.head-actions { display: flex; gap: 8px; }
h2 { margin: 0; font-size: 20px; }
.expense-summary-strip { display: grid; grid-template-columns: repeat(2, minmax(0, 220px)); gap: 10px; margin-bottom: 14px; }
.expense-summary-strip article { border: 1px solid #dbe7f5; border-radius: 14px; padding: 12px 14px; background: linear-gradient(180deg, #fbfdff 0%, #f3f8ff 100%); display: grid; gap: 6px; }
.expense-summary-strip span { color: #64748b; font-size: 12px; }
.expense-summary-strip strong { color: #0f172a; font-size: 16px; }
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right; white-space: nowrap; }
.details-cell { white-space: normal; min-width: 240px; line-height: 1.8; }
.primary-btn, .secondary-btn { border: 0; border-radius: 10px; padding: 8px 12px; cursor: pointer; }
.primary-btn { background: linear-gradient(90deg,#2563eb,#0891b2); color: #fff; }
.secondary-btn { background: #e2e8f0; }
.btn-with-icon { display: inline-flex; align-items: center; gap: 8px; }
.table-btn { border: 0; background: #e2e8f0; padding: 6px 10px; border-radius: 8px; cursor: pointer; margin-left: 6px; }
.table-btn.danger { background: #fee2e2; color: #991b1b; }
.table-btn.success { background: #dcfce7; color: #166534; }
.table-meta-note { color: #64748b; font-size: 12px; font-weight: 700; }
.source-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 84px; padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; }
.source-manual { background: #dbeafe; color: #1d4ed8; }
.source-purchase { background: #dcfce7; color: #166534; }
.clickable-row { cursor: pointer; }
.clickable-row:hover td { background: #f8fbff; }
.modal-overlay { position: fixed; inset: 0; background: rgba(15,23,42,.45); display: flex; align-items: center; justify-content: center; padding: 18px; z-index: 99; }
.modal-panel { width: min(980px,100%); max-height: calc(100vh - 36px); background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; overflow: auto; }
.history-panel { width: min(1100px,100%); }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; border-bottom: 1px solid #e2e8f0; }
.modal-subtitle { display: block; margin-top: 4px; color: #64748b; font-size: 12px; }
.close-btn { border: 0; background: #f1f5f9; border-radius: 8px; width: 30px; height: 30px; cursor: pointer; }
.modal-form { padding: 14px; display: grid; gap: 10px; grid-template-columns: repeat(3, minmax(0, 1fr)); align-items: end; }
.modal-form label { display: grid; gap: 5px; }
.modal-form input, .modal-form select { height: 42px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 0 10px; background: #fff; }
.modal-form textarea { border: 1px solid #cbd5e1; border-radius: 10px; padding: 10px; background: #fff; font: inherit; resize: vertical; }
.sms-settings-card { gap: 18px; }
.sms-cost-hint {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.7;
  font-weight: 500;
}
.sms-auto-send-panel {
  display: flex;
  padding: 12px 14px;
  border: 1px solid #dbe5f0;
  border-radius: 16px;
  background: #f8fbff;
}
.sms-template-grid { display: grid; gap: 14px; }
.sms-template-card {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(320px, .92fr);
  gap: 14px;
  align-items: stretch;
  padding: 14px;
  border-radius: 22px;
  border: 1px solid #dbe7f5;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, .08), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 16px 42px rgba(15, 23, 42, .06);
}
.sms-template-editor { align-content: start; min-width: 0; }
.sms-template-editor textarea {
  min-height: 150px;
  background: #ffffff;
  color: #0f172a;
  line-height: 1.85;
}
.sms-preview-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
  min-width: 0;
  padding: 13px;
  border-radius: 18px;
  border: 1px solid #99f6e4;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, .96), rgba(14, 116, 144, .94)),
    radial-gradient(circle at top left, rgba(255, 255, 255, .28), transparent 32%);
  color: #ecfeff;
}
.sms-preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.sms-preview-head small {
  color: #ffffff;
  font-size: 12px;
  font-weight: 900;
}
.sms-preview-head span {
  color: rgba(236, 254, 255, .76);
  font-size: 11px;
  font-weight: 700;
}
.sms-preview-box {
  margin: 0;
  min-height: 132px;
  max-height: 280px;
  overflow: auto;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, .24);
  background: rgba(7, 27, 35, .42);
  color: #ffffff;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.95;
  font-family: inherit;
  font-size: 13px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .08);
}
.sms-token-panel {
  display: grid;
  gap: 10px;
  padding: 14px;
  border-radius: 20px;
  border: 1px dashed #b7c9e5;
  background: linear-gradient(180deg, #ffffff, #f3f8ff);
}
.sms-token-panel strong { color: #0f172a; font-size: 13px; }
.sms-token-list { display: flex; flex-wrap: wrap; gap: 8px; }
.sms-token-list code {
  padding: 7px 10px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #075985;
  border: 1px solid #bae6fd;
  font-family: inherit;
  font-size: 12px;
  font-weight: 800;
}
.row-check { display: flex !important; align-items: center; gap: 8px; }
.full { grid-column: 1 / -1; }
.entrusted-card {
  grid-column: 1 / -1;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid #dbe7f5;
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
  display: grid;
  gap: 12px;
}
.entrusted-card.active {
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.12);
  border-color: #bfd7ff;
}
.entrusted-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.entrusted-head strong { color: #0f172a; font-size: 15px; }
.entrusted-head small { display: block; margin-top: 4px; color: #64748b; }
.entrusted-toggle { white-space: nowrap; }
.entrusted-grid {
  display: grid;
  gap: 10px;
}
.entrusted-list-head {
  display: flex !important;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.small-btn {
  padding: 6px 10px;
  border-radius: 10px;
}
.entrusted-item-row {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) repeat(2, minmax(0, 1fr)) auto;
  gap: 10px;
  align-items: end;
  padding: 12px;
  border: 1px solid #dbe7f5;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.75);
}
.entrusted-remove-btn {
  height: 42px;
  margin-left: 0;
}
.service-tier-panel {
  grid-column: 1 / -1;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #dbe7f5;
  background: linear-gradient(180deg, #f8fbff 0%, #eef6ff 100%);
  display: grid;
  gap: 14px;
}
.service-tier-panel.active {
  border-color: #bfd7ff;
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.1);
}
.service-tier-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.service-tier-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.motorcycle-tier-grid {
  grid-template-columns: repeat(3, minmax(0, min(320px, 1fr)));
}
.service-tier-card {
  padding: 14px;
  border: 1px solid #dbe7f5;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.85);
  display: grid;
  gap: 10px;
}
.service-tier-card.motorcycle {
  border-color: #cbe7da;
  background: linear-gradient(180deg, #ffffff 0%, #f2fbf6 100%);
}
.service-tier-card header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.service-tier-card strong { color: #0f172a; }
.service-tier-card small { color: #64748b; }
.service-tier-toggle { white-space: nowrap; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; grid-column: 1 / -1; }
.history-loading, .history-body { padding: 14px; }
.history-summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }
.history-summary article { border: 1px solid #e2e8f0; border-radius: 12px; padding: 10px; background: #f8fbff; display: grid; gap: 6px; }
.history-summary span { color: #64748b; font-size: 12px; }
.history-summary strong { color: #0f172a; font-size: 14px; }
.settings-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, .9fr);
  gap: 18px;
  margin-bottom: 16px;
  padding: 22px;
  border-radius: 28px;
  background:
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.10), transparent 28%),
    radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.14), transparent 24%),
    linear-gradient(135deg, #f8fcff 0%, #f5fbfa 54%, #ffffff 100%);
  border: 1px solid #d8e9ef;
}
.settings-hero-copy { display: grid; gap: 10px; align-content: center; }
.settings-hero-kicker { color: #0f766e; font-size: 12px; font-weight: 800; letter-spacing: .08em; }
.settings-hero-copy h2 { font-size: 28px; }
.settings-hero-copy p { margin: 0; color: #4b5d72; line-height: 2; }
.settings-hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.settings-hero-stats article {
  border-radius: 22px;
  padding: 16px;
  background: rgba(255,255,255,.88);
  border: 1px solid #e2edf2;
  display: grid;
  gap: 8px;
}
.settings-hero-stats span { color: #64748b; font-size: 12px; }
.settings-hero-stats strong { color: #0f172a; font-size: 17px; line-height: 1.5; }
.general-settings-form { display: grid; gap: 16px; }
.general-settings-card {
  border: 1px solid #d8e6ee;
  border-radius: 26px;
  padding: 20px;
  background: linear-gradient(180deg, rgba(255,255,255,.98) 0%, rgba(248,252,255,.98) 100%);
  display: grid;
  gap: 14px;
}
.general-settings-card-accent { background: linear-gradient(135deg, #f7fffc 0%, #f8fbff 48%, #ffffff 100%); }
.general-settings-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.general-settings-head strong { color: #0f172a; font-size: 16px; }
.settings-toggle {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 40px;
  padding: 0 13px;
  border: 1px solid #cfe0f7;
  border-radius: 999px;
  background: #fff;
  color: #315f9f;
  font-weight: 900;
  white-space: nowrap;
}
.settings-toggle input { width: 17px; height: 17px; }
.general-setting-label { display: grid; gap: 6px; }
.general-setting-label input,
.general-setting-label textarea,
.general-setting-label select {
  border: 1px solid #d9e3ea;
  border-radius: 18px;
  padding: 10px 14px;
  background: #f9fbfc;
  font: inherit;
  box-shadow: none !important;
  outline: none;
  transition: border-color .2s ease, background .2s ease;
}
.general-setting-label input { height: 48px; }
.general-setting-label input:focus,
.general-setting-label textarea:focus,
.general-setting-label select:focus {
  border-color: #8dd3c7;
  background: #fff;
  box-shadow: none !important;
}
.discount-editor-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, .8fr);
  gap: 14px;
  align-items: stretch;
}
.discount-mode-tabs {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(120px, 1fr));
  gap: 6px;
  padding: 5px;
  border: 1px solid #d8e6ee;
  border-radius: 14px;
  background: #f8fbff;
  width: min(360px, 100%);
}
.discount-mode-tab {
  height: 38px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #475569;
  font: inherit;
  font-weight: 900;
  cursor: pointer;
}
.discount-mode-tab.active {
  background: #0f766e;
  color: #ffffff;
}
.fixed-discount-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(260px, .9fr);
  gap: 14px;
  align-items: stretch;
}
.fixed-discount-field input {
  direction: ltr;
}
.discount-preview-card {
  border-radius: 22px;
  padding: 18px;
  background: linear-gradient(135deg, #0f766e 0%, #0f5cc0 100%);
  color: #fff;
  display: grid;
  gap: 10px;
}
.discount-preview-card small { font-size: 12px; opacity: .82; }
.discount-preview-card strong { font-size: 28px; line-height: 1.2; }
.discount-preview-card p { margin: 0; line-height: 1.9; font-size: 13px; color: rgba(255,255,255,.86); }
.fixed-preview-card { background: linear-gradient(135deg, #0f4c81 0%, #0f766e 100%); }
.payment-settings-card {
  background: linear-gradient(180deg, #f9fcff 0%, #f3f8fd 100%);
}
.payment-settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.printer-settings-card {
  background: linear-gradient(180deg, #fffefb 0%, #fff8ef 100%);
}
.printer-settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.printer-settings-grid select {
  height: 48px;
  font: inherit;
}
.printer-toggle {
  grid-column: 1 / -1;
  padding: 14px 16px;
  border: 1px solid #fde2ba;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.94);
}
.printer-checks {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.full-width { grid-column: 1 / -1; }
.template-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.inline-check { width: auto; white-space: nowrap; font-size: 12px; }
.helper-text { margin: 0; color: #475569; font-size: 13px; }
.modal-helper-text { padding: 10px 12px; border-radius: 12px; background: #eff6ff; color: #1d4ed8; }
.field-file-note { display: block; margin-top: 8px; color: #475569; font-size: 12px; }
.table-link { color: #2563eb; text-decoration: none; }
.table-link:hover { text-decoration: underline; }
.error-box { margin-bottom: 10px; padding: 10px; background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; border-radius: 10px; }
.toast { position: fixed; left: 20px; bottom: 20px; padding: 10px 14px; border-radius: 10px; color: #fff; z-index: 120; }
.toast.success { background: #16a34a; }
.toast.error { background: #dc2626; }
@media (max-width: 960px) {
  .settings-hero,
  .head-row,
  .head-actions,
  .modal-actions,
  .general-settings-head {
    flex-direction: column;
    align-items: stretch;
  }

  .tabs-bar {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .tabs-bar .chip {
    width: 100%;
    justify-content: center;
    min-height: 42px;
    border-radius: 12px;
  }

  .modal-form, .history-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .entrusted-head, .entrusted-grid { grid-template-columns: 1fr; display: grid; }
  .entrusted-item-row { grid-template-columns: 1fr; }
  .service-tier-panel-head { flex-direction: column; align-items: stretch; }
  .service-tier-grid,
  .motorcycle-tier-grid { grid-template-columns: 1fr; }
  .entrusted-list-head { align-items: stretch; }
  .expense-summary-strip { grid-template-columns: 1fr; }
  .sms-template-card { grid-template-columns: 1fr; }
  .sms-preview-panel { min-height: 220px; }
  .discount-editor-grid,
  .fixed-discount-grid,
  .settings-hero-stats,
  .payment-settings-grid, .printer-settings-grid, .printer-checks { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .settings-hero { display: none; }
  .template-title-row { align-items: flex-start; }
  .fixed-discount-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
