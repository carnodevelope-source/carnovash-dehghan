

# 🏗️ Frontend Architecture — Vue 3 + Django

## 📁 ساختار کلی پروژه

CarWash/
├── frontend/                          # Vue 3 Application
│   ├── public/
│   │   ├── favicon.ico
│   │   └── index.html
│   │
│   ├── src/
│   │   ├── main.js                    # Entry point
│   │   ├── App.vue                    # Root component
│   │   │
│   │   ├── assets/                    # استاتیک‌ها
│   │   │   ├── styles/
│   │   │   │   ├── main.css           # Global styles
│   │   │   │   ├── variables.css      # Design tokens
│   │   │   │   ├── typography.css     # فونت‌ها
│   │   │   │   ├── animations.css     # انیمیشن‌ها
│   │   │   │   └── utilities.css      # Helper classes
│   │   │   ├── fonts/
│   │   │   │   ├── Vazirmatn/
│   │   │   │   └── Inter/
│   │   │   └── images/
│   │   │       ├── logo.svg
│   │   │       └── icons/
│   │   │
│   │   ├── components/                # کامپوننت‌های مشترک
│   │   │   ├── base/                  # کامپوننت‌های پایه
│   │   │   │   ├── BaseButton.vue
│   │   │   │   ├── BaseInput.vue
│   │   │   │   ├── BaseCard.vue
│   │   │   │   ├── BaseModal.vue
│   │   │   │   ├── BaseBadge.vue
│   │   │   │   ├── BaseTable.vue
│   │   │   │   ├── BaseSelect.vue
│   │   │   │   ├── BaseCheckbox.vue
│   │   │   │   ├── BaseRadio.vue
│   │   │   │   ├── BaseTextarea.vue
│   │   │   │   ├── BaseSpinner.vue
│   │   │   │   ├── BaseToast.vue
│   │   │   │   └── BaseDatePicker.vue
│   │   │   │
│   │   │   ├── layout/                # لایوت‌ها
│   │   │   │   ├── AppHeader.vue
│   │   │   │   ├── AppSidebar.vue
│   │   │   │   ├── AppFooter.vue
│   │   │   │   └── AppLayout.vue
│   │   │   │
│   │   │   ├── common/                # کامپوننت‌های مشترک
│   │   │   │   ├── LoadingOverlay.vue
│   │   │   │   ├── EmptyState.vue
│   │   │   │   ├── ErrorBoundary.vue
│   │   │   │   ├── ConfirmDialog.vue
│   │   │   │   ├── SearchBar.vue
│   │   │   │   ├── FilterPanel.vue
│   │   │   │   ├── Pagination.vue
│   │   │   │   ├── StatusBadge.vue
│   │   │   │   └── PriceDisplay.vue
│   │   │   │
│   │   │   └── features/              # کامپوننت‌های ویژه
│   │   │       ├── vehicle/
│   │   │       │   ├── VehicleCard.vue
│   │   │       │   ├── VehicleForm.vue
│   │   │       │   ├── VehicleList.vue
│   │   │       │   ├── PlateDisplay.vue
│   │   │       │   └── CameraCapture.vue
│   │   │       │
│   │   │       ├── service/
│   │   │       │   ├── ServiceSelector.vue
│   │   │       │   ├── ServiceItem.vue
│   │   │       │   └── ServiceSummary.vue
│   │   │       │
│   │   │       ├── worker/
│   │   │       │   ├── WorkerSelector.vue
│   │   │       │   ├── WorkerCard.vue
│   │   │       │   └── WorkerStatus.vue
│   │   │       │
│   │   │       ├── payment/
│   │   │       │   ├── PaymentModal.vue
│   │   │       │   ├── POSIntegration.vue
│   │   │       │   ├── TipCalculator.vue
│   │   │       │   └── InvoicePreview.vue
│   │   │       │
│   │   │       ├── product/
│   │   │       │   ├── ProductSelector.vue
│   │   │       │   ├── ProductCard.vue
│   │   │       │   └── ProductCart.vue
│   │   │       │
│   │   │       └── reports/
│   │   │           ├── ReportTable.vue
│   │   │           ├── ReportFilters.vue
│   │   │           ├── ReportSummary.vue
│   │   │           ├── KPICard.vue
│   │   │           └── ExportButton.vue
│   │   │
│   │   ├── views/                     # صفحات اصلی
│   │   │   ├── auth/
│   │   │   │   ├── LoginView.vue
│   │   │   │   └── ForgotPasswordView.vue
│   │   │   │
│   │   │   ├── operator/              # پنل 
│   │   │   │   ├── DashboardView.vue
│   │   │   │   ├── IntakeView.vue
│   │   │   │   ├── VehiclesView.vue
│   │   │   │   └── ReleaseView.vue
│   │   │   │
│   │   │   ├── manager/               # پنل مدیر
│   │   │   │   ├── ReportsView.vue
│   │   │   │   ├── WorkersReportView.vue
│   │   │   │   ├── TipsReportView.vue
│   │   │   │   ├── RevenueReportView.vue
│   │   │   │   └── AttendanceView.vue
│   │   │   │
│   │   │   └── NotFound.vue
│   │   │
│   │   ├── router/
│   │   │   └── index.js
│   │   │
│   │   ├── store/                     # Pinia
│   │   │   ├── index.js
│   │   │   ├── auth.store.js
│   │   │   ├── vehicle.store.js
│   │   │   ├── worker.store.js
│   │   │   ├── service.store.js
│   │   │   ├── payment.store.js
│   │   │   ├── product.store.js
│   │   │   └── report.store.js
│   │   │
│   │   ├── services/                  # API Layer
│   │   │   ├── api.js                 # Axios instance
│   │   │   ├── auth.api.js
│   │   │   ├── vehicle.api.js
│   │   │   ├── worker.api.js
│   │   │   ├── service.api.js
│   │   │   ├── payment.api.js
│   │   │   ├── product.api.js
│   │   │   └── report.api.js
│   │   │
│   │   ├── composables/               # Vue Composables
│   │   │   ├── useModal.js
│   │   │   ├── usePagination.js
│   │   │   ├── useFilters.js
│   │   │   ├── useCurrency.js
│   │   │   ├── useToast.js
│   │   │   ├── usePOS.js
│   │   │   └── useAIPlate.js
│   │   │
│   │   ├── utils/
│   │   │   ├── formatters.js
│   │   │   ├── constants.js
│   │   │   ├── validators.js
│   │   │   └── permissions.js
│   │   │
│   │   └── config/
│   │       ├── env.js
│   │       └── roles.js
│   │
│   └── package.json

---

# 🧠 معماری منطقی (Layered Architecture)

## 1️⃣ Presentation Layer
- Views
- Feature Components
- Base Components

فقط UI + interaction  
هیچ API مستقیم اینجا زده نمی‌شود.

---

## 2️⃣ State Layer (Pinia)
هر domain یک store مستقل دارد.

### مثال:
js
vehicle.store.js

وظایف:
- نگهداری لیست خودروها
- وضعیت‌ها (entered, assigned, completed…)
- loading state
- selected vehicle
- async actions

---

## 3️⃣ Service Layer (API abstraction)
تمام ارتباط با Django فقط اینجاست.

js
vehicle.api.js

مثال:
js
export const fetchVehicles = () => api.get('/vehicles/')
export const createVehicle = (data) => api.post('/vehicles/',
عالی ✅  
الان یک **ساختار حرفه‌ای و Production‑Ready برای فرانت Vue 3** برات طراحی می‌کنم که:

- با Django REST هماهنگ باشه  
- ماژولار باشه  
- قابل توسعه باشه  
- Design System قبلی داخلش پیاده بشه  
- برای چند نقش (اپراتور / مدیر) آماده باشه  
- تمیز و مقیاس‌پذیر باشه  

---

# ✅ Tech Stack پیشنهادی

- Vue 3 (Composition API)
- Vite
- Pinia (State Management)
- Vue Router
- Axios
- Tailwind (با Design
ساختار کامل فرانت را بدون فرمت سنگین و کاملاً قابل استفاده برای پیاده‌سازی Vue 3 می‌دهم. این ساختار با بک‌اند Django و دیتابیس MySQL هماهنگ است و بر اساس جریان‌ها، فیچرها و دیزاین‌سیستمی است که تا الان تعریف کرده‌ایم.

----------------------------------------------------------------

ساختار اصلی پروژه (Vue 3 + Vite)

frontend/
  public/
    index.html
    favicon.ico

  src/
    main.js
    App.vue

    assets/
      styles/
        variables.css
        main.css
        typography.css
        animations.css
        utilities.css
      images/
      fonts/

    router/
      index.js
      guards.js   (چک نقش اپراتور، مدیر، لاگین)

    store/        (Pinia)
      auth.store.js
      vehicle.store.js
      service.store.js
      worker.store.js
      payment.store.js
      product.store.js
      report.store.js
      ui.store.js

    services/     (Axios API Layer)
      api.js
      auth.api.js
      vehicle.api.js
      service.api.js
      worker.api.js
      payment.api.js
      product.api.js
      report.api.js
      pos.api.js   (ارتباط با دستگاه کارت‌خوان)
      ai.api.js    (تشخیص پلاک و مدل)

    utils/
      formatters.js
      validators.js
      constants.js
      permissions.js
      helpers.js

    composables/
      useModal.js
      useToast.js
      usePagination.js
      useFilters.js
      useCurrency.js
      usePOS.js
      useAIPlate.js

    components/
      base/
        BaseButton.vue
        BaseInput.vue
        BaseSelect.vue
        BaseCheckbox.vue
        BaseRadio.vue
        BaseCard.vue
        BaseTable.vue
        BaseModal.vue
        BaseToast.vue
        BaseSpinner.vue
        BaseBadge.vue
        BaseDatePicker.vue

      layout/
        AppHeader.vue
        AppSidebar.vue
        AppFooter.vue
        AppLayout.vue

      common/
        LoadingOverlay.vue
        SearchBar.vue
        FilterPanel.vue
        EmptyState.vue
        ConfirmDialog.vue
        Pagination.vue
        StatusBadge.vue
        PriceDisplay.vue

      features/

        vehicle/
          VehicleCard.vue
          VehicleForm.vue
          VehicleList.vue
          CameraCapture.vue
          PlateDisplay.vue

        service/
          ServiceSelector.vue
          ServiceItem.vue
          ServiceSummary.vue

        worker/
          WorkerSelector.vue
          WorkerCard.vue
          WorkerStatus.vue

        payment/
          PaymentModal.vue
          POSIntegration.vue
          TipCalculator.vue
          InvoicePreview.vue

        product/
          ProductSelector.vue
          ProductCard.vue
          ProductCart.vue

        reports/
          ReportTable.vue
          ReportFilters.vue
          ReportSummary.vue
          KPICard.vue
          ExportButton.vue

    views/

      auth/
        LoginView.vue

      operator/
        DashboardView.vue
        IntakeView.vue
        VehiclesView.vue
        ServiceAssignmentView.vue
        ReleaseView.vue

      manager/
        ReportsView.vue
        TipsReportView.vue
        RevenueReportView.vue
        WorkerReportView.vue
        AttendanceView.vue

      NotFound.vue

----------------------------------------------------------------

منطق معماری

Presentation Layer
  شامل صفحات (Views)، لایوت‌ها و کامپوننت‌ها.

State Layer (Pinia)
  هر بخش یک store مستقل دارد.
  state فقط از store خوانده می‌شود.
  API فقط از service layer صدا زده می‌شود نه مستقیم در کامپوننت.

Service Layer
  فقط نقش ارتباط با Django دارد.
  همه درخواست‌ها از این لایه عبور می‌کنند.

Composable Layer
  توابع قابل استفاده مجدد مثل:
  useModal
  useAIPlate
  usePOS
  usePagination

Design System Layer
  همه استایل‌ها از variables.css می‌آیند تا یکپارچگی کامل باشد.

----------------------------------------------------------------

ماژول‌بندی دقیق بر اساس PRD

ماژول Intake (ثبت ورود)
  CameraCapture
  AIPlate Detection
  VehicleForm
  VehicleCard

ماژول Service Assignment (تحویل به نیرو)
  ServiceSelector
  WorkerSelector
  ServiceSummary
  InvoicePreview

ماژول Release/Payment (ترخیص)
  PaymentModal
  POSIntegration
  TipCalculator
  ProductSelector

ماژول Reports (مدیر)
  ReportTable
  ReportFilters
  KPICard
  ExportButton

----------------------------------------------------------------

چیدمان مسیرهای Vue Router

/
  /login
  /operator/dashboard
  /operator/intake
  /operator/vehicles
  /operator/release
  /manager/reports
  /manager/revenue
  /manager/tips
  /manager/workers
  /manager/attendance

ACL:
  اپراتور فقط مسیرهای operator را می‌بیند.
  مدیر فقط مسیرهای manager.

----------------------------------------------------------------

ساختار استیت‌ها (مثال)

vehicle.store.js
  state:
    list
    selectedVehicle
    statusFilters
    loading

  actions:
    fetchVehicles
    createVehicle
    updateStatus
    assignWorker
    releaseVehicle

payment.store.js
  state:
    invoice
    posStatus
    tipAmount

  actions:
    startPOS
    verifyPOS
    submitPayment

report.store.js
  state:
    data
    filters
    summary

  actions:
    fetchReport
    exportReport

----------------------------------------------------------------

ارتباط کامل با Django

تمام درخواست‌ها:
  با Axios instance واحد ساخته می‌شوند.
  کلید JWT در هدر تزریق می‌شود.
  Refresh/Access Token مدیریت می‌شود.
  ارورها استانداردسازی شده.

----------------------------------------------------------------
