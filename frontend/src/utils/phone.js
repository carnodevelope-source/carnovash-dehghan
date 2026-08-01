const PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
const ARABIC_DIGITS = '٠١٢٣٤٥٦٧٨٩'

const toEnglishDigits = (value) => String(value ?? '').replace(/[۰-۹٠-٩]/g, (digit) => {
  const persianIndex = PERSIAN_DIGITS.indexOf(digit)
  if (persianIndex >= 0) return String(persianIndex)
  const arabicIndex = ARABIC_DIGITS.indexOf(digit)
  if (arabicIndex >= 0) return String(arabicIndex)
  return digit
})

export const IRAN_MOBILE_LENGTH = 11
export const IRAN_MOBILE_PREFIX = '09'
export const IRAN_MOBILE_PATTERN = /^09\d{9}$/
export const IRAN_MOBILE_PLACEHOLDER = '09121234567'

/** Keep only digits and cap at 11 for Iranian mobile fields. */
export const normalizeIranMobile = (value) => toEnglishDigits(value).replace(/\D/g, '').slice(0, IRAN_MOBILE_LENGTH)

export const isValidIranMobile = (value) => IRAN_MOBILE_PATTERN.test(normalizeIranMobile(value))

/**
 * Friendly Persian validation message for mobile fields.
 * Returns empty string when valid (or empty if allowEmpty and blank).
 */
export const iranMobileErrorMessage = (value, { allowEmpty = false, label = 'شماره موبایل' } = {}) => {
  const digits = normalizeIranMobile(value)
  if (!digits) {
    return allowEmpty ? '' : `${label} را وارد کنید.`
  }
  if (!digits.startsWith(IRAN_MOBILE_PREFIX)) {
    return `${label} باید با ۰۹ شروع شود.`
  }
  if (digits.length < IRAN_MOBILE_LENGTH) {
    return `${label} باید ۱۱ رقم باشد (${digits.length.toLocaleString('fa-IR')} رقم وارد شده).`
  }
  if (!isValidIranMobile(digits)) {
    return `${label} معتبر نیست. مثال: ۰۹۱۲۱۲۳۴۵۶۷`
  }
  return ''
}

export const assertIranMobile = (value, options = {}) => {
  const message = iranMobileErrorMessage(value, options)
  if (message) {
    const error = new Error(message)
    error.code = 'INVALID_IRAN_MOBILE'
    throw error
  }
  return normalizeIranMobile(value)
}
