export const HQ_STATUS_META = {
  active: { label: 'فعال', tone: 'success' },
  inactive: { label: 'غیرفعال', tone: 'neutral' },
  expired: { label: 'منقضی', tone: 'danger' },
  near_expiry: { label: 'نزدیک انقضا', tone: 'warning' },
  blocked: { label: 'مسدود', tone: 'danger' },
  suspended: { label: 'تعلیق', tone: 'warning' },
  pending_payment: { label: 'در انتظار پرداخت', tone: 'warning' },
  pending_activation: { label: 'در انتظار فعالسازی', tone: 'info' },
  cancelled: { label: 'لغو', tone: 'neutral' },
  trial: { label: 'آزمایشی', tone: 'info' },
  not_renewed: { label: 'تمدیدنشده', tone: 'warning' }
}

export const HQ_PAYMENT_STATUS_META = {
  settled: { label: 'تسویه', tone: 'success' },
  partial: { label: 'جزئی', tone: 'warning' },
  unpaid: { label: 'پرداخت‌نشده', tone: 'danger' },
  overdue: { label: 'معوق', tone: 'danger' },
  early: { label: 'زودتر از موعد', tone: 'info' }
}

export const HQ_HEALTH_META = {
  strong: { label: 'عالی', tone: 'success' },
  stable: { label: 'باثبات', tone: 'info' },
  risk: { label: 'نیازمند توجه', tone: 'danger' },
  idle: { label: 'بدون فعالیت', tone: 'neutral' }
}

export const HQ_WALLET_HEALTH_META = {
  healthy: { label: 'سالم', tone: 'success' },
  gateway: { label: 'شارژ درگاه', tone: 'success' },
  sms_heavy: { label: 'تمرکز پیامک', tone: 'info' },
  empty: { label: 'موجودی خالی', tone: 'danger' },
  idle: { label: 'بدون فعالیت', tone: 'neutral' }
}

export const HQ_SHARE_META = {
  hq: { label: 'سهم کارنو', tone: 'carno', short: 'کارنو' },
  rah: { label: 'سهم آراکار', tone: 'arakar', short: 'آراکار' },
  none: { label: 'بدون سهم', tone: 'neutral', short: '—' },
  carno: { label: 'کارنو', tone: 'carno', short: 'کارنو' },
  arakar: { label: 'آراکار', tone: 'arakar', short: 'آراکار' }
}

export const HQ_DIRECTION_META = {
  in: { label: 'واریز', tone: 'success', sign: '+' },
  out: { label: 'برداشت', tone: 'danger', sign: '−' }
}

export function getStatusMeta(status) {
  return HQ_STATUS_META[status] || { label: status || '—', tone: 'neutral' }
}

export function getPaymentStatusMeta(status) {
  return HQ_PAYMENT_STATUS_META[status] || { label: status || '—', tone: 'neutral' }
}

export function getHealthMeta(health) {
  return HQ_HEALTH_META[health] || { label: health || '—', tone: 'neutral' }
}

export function getWalletHealthMeta(health) {
  return HQ_WALLET_HEALTH_META[health] || { label: health || '—', tone: 'neutral' }
}

export function getShareOwnerMeta(owner) {
  return HQ_SHARE_META[owner] || { label: owner || 'بدون سهم', tone: 'neutral', short: '—' }
}

export function getDirectionMeta(direction) {
  return HQ_DIRECTION_META[direction] || { label: direction || 'تراکنش', tone: 'neutral', sign: '' }
}
