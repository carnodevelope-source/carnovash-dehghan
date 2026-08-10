export const REPORT_WORKSPACES = [
  {
    key: 'internal',
    label: 'گزارش داخلی HQ',
    hint: 'سهم کارنو و آراکار',
    icon: 'graph'
  },
  {
    key: 'carwash',
    label: 'گزارش کارواش‌ها',
    hint: 'عملکرد یک شعبه',
    icon: 'home'
  },
  {
    key: 'wallet',
    label: 'ریز کیف پول',
    hint: 'واریز و برداشت',
    icon: 'wallet'
  },
  {
    key: 'network',
    label: 'نمای شبکه',
    hint: 'رتبه و سلامت شعب',
    icon: 'chart'
  }
]

export const REPORT_RANGE_OPTIONS = [
  { key: 'day', label: 'روز' },
  { key: 'week', label: 'هفته' },
  { key: 'month', label: 'ماه' },
  { key: 'all', label: 'کل تاریخ' }
]

export const HQ_SHARE_FEATURE_ORDER = ['sms_wallet', 'sms_club', 'excel_import', 'attendance']

export const HQ_SHARE_FEATURE_LABELS = {
  sms_wallet: 'کیف پول پیامک',
  sms_club: 'باشگاه مشتریان',
  excel_import: 'ورود اکسل',
  attendance: 'ورود و خروج'
}

export const TENANT_REPORT_TABS = [
  { key: 'overall', label: 'گزارش کل', rowsKey: 'overall_report', summaryKey: 'vehicles_count' },
  { key: 'carwash', label: 'حق کارواش', rowsKey: 'carwash_report', moneyKey: 'carwash_total' },
  { key: 'worker', label: 'حق نیرو', rowsKey: 'worker_report', moneyKey: 'worker_total' },
  { key: 'tips', label: 'انعام و کالا', rowsKey: 'tips_report', moneyKey: 'tips_total' },
  { key: 'revenue', label: 'درآمد و پرداخت', rowsKey: 'revenue_report' },
  { key: 'attendance', label: 'ورود و خروج', rowsKey: 'attendance_report' },
  { key: 'blacklist', label: 'لیست سیاه', rowsKey: 'blacklist_report' }
]

export const SERVICE_REPORT_TABS = [
  { key: 'all', label: 'همه سرویس‌ها', productKey: '' },
  { key: 'license', label: 'لایسنس', productKey: 'core_software', lockedLabel: 'لایسنس اصلی' },
  { key: 'wallet', label: 'کیف پول', productKey: 'wallet', lockedLabel: 'کیف پول' },
  { key: 'attendance', label: 'ورود و خروج', productKey: 'attendance', lockedLabel: 'ورود و خروج' },
  { key: 'cloud', label: 'فضای ابری', productKey: 'cloud_storage', lockedLabel: 'فضای ابری' },
  { key: 'sms_club', label: 'باشگاه مشتریان', productKey: 'sms_club', lockedLabel: 'باشگاه مشتریان' },
  { key: 'sms', label: 'پیامک', productKey: 'sms_panel', lockedLabel: 'پنل پیامک' },
  { key: 'revenue', label: 'ماتریس درآمد', productKey: '', financialOnly: true }
]

export const SERVICE_STATUS_OPTIONS = [
  { value: '', label: 'همه وضعیت‌ها' },
  { value: 'active', label: 'فعال' },
  { value: 'inactive', label: 'غیرفعال' },
  { value: 'expired', label: 'منقضی' },
  { value: 'near_expiry', label: 'نزدیک انقضا' },
  { value: 'blocked', label: 'مسدود' },
  { value: 'suspended', label: 'تعلیق' },
  { value: 'pending_payment', label: 'در انتظار پرداخت' },
  { value: 'pending_activation', label: 'در انتظار فعالسازی' },
  { value: 'cancelled', label: 'لغو' },
  { value: 'not_renewed', label: 'تمدیدنشده' }
]

export const SERVICE_PAYMENT_OPTIONS = [
  { value: '', label: 'همه پرداخت‌ها' },
  { value: 'settled', label: 'تسویه' },
  { value: 'partial', label: 'جزئی' },
  { value: 'unpaid', label: 'پرداخت‌نشده' },
  { value: 'overdue', label: 'معوق' }
]

export const SERVICE_ORDERING_OPTIONS = [
  { value: '-updated_at', label: 'جدیدترین تغییر' },
  { value: '-purchased_at', label: 'تاریخ خرید' },
  { value: 'ends_at', label: 'نزدیک‌ترین انقضا' },
  { value: '-final_amount', label: 'بیشترین مبلغ' },
  { value: '-remaining_amount', label: 'بیشترین بدهی' },
  { value: 'client_name', label: 'نام کلاینت' }
]
