export const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
  .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))

const ENGLISH_LETTER_MAP = {
  A: 'الف',
  B: 'ب',
  C: 'ص',
  D: 'د',
  E: 'ه',
  F: 'ف',
  G: 'گ',
  H: 'ح',
  I: 'ی',
  J: 'ج',
  K: 'ک',
  L: 'ل',
  M: 'م',
  N: 'ن',
  O: 'و',
  P: 'پ',
  Q: 'ق',
  R: 'ر',
  S: 'س',
  T: 'ط',
  U: 'ع',
  V: 'و',
  W: 'و',
  X: 'ش',
  Y: 'ی',
  Z: 'ز'
}

const PERSIAN_LETTER_MAP = {
  ا: 'الف',
  آ: 'الف',
  الف: 'الف',
  ب: 'ب',
  پ: 'پ',
  ت: 'ت',
  ث: 'ث',
  ج: 'ج',
  چ: 'چ',
  ح: 'ح',
  خ: 'خ',
  د: 'د',
  ذ: 'ذ',
  ر: 'ر',
  ز: 'ز',
  ژ: 'ژ',
  س: 'س',
  ش: 'ش',
  ص: 'ص',
  ض: 'ض',
  ط: 'ط',
  ظ: 'ظ',
  ع: 'ع',
  غ: 'غ',
  ف: 'ف',
  ق: 'ق',
  ک: 'ک',
  ك: 'ک',
  گ: 'گ',
  ل: 'ل',
  م: 'م',
  ن: 'ن',
  و: 'و',
  ه: 'ه',
  ی: 'ی',
  ي: 'ی'
}

export const normalizePlateLetter = (value) => {
  const raw = String(value || '').replace(/\s+/g, '')
  if (!raw) return ''
  const token = raw.slice(0, 3)
  if (PERSIAN_LETTER_MAP[token]) return PERSIAN_LETTER_MAP[token]
  const first = raw.slice(0, 1)
  const upper = first.toUpperCase()
  if (ENGLISH_LETTER_MAP[upper]) return ENGLISH_LETTER_MAP[upper]
  return PERSIAN_LETTER_MAP[first] || ''
}

export const splitPlate = (rawPlate) => String(rawPlate || '').trim().split(/\s+/).filter(Boolean)

export const resolvePlateParts = (source = {}) => {
  const plateType = String(source.plate_type || source.plateType || '').trim()
  const parts = splitPlate(source.raw || source.plate_number || source.plate || '')
  if (plateType === 'motorcycle') {
    const top = String(source.plate_mid || source.plateMid || parts[0] || '').trim()
    const bottom = String(
      source.plate_letter
      || source.plateLetter
      || parts[1]
      || `${source.plate_right || source.plateRight || ''}${source.plate_left || source.plateLeft || ''}${source.plate_letter || source.plateLetter || ''}`
    ).trim()
    return {
      left: '',
      letter: normalizeDigits(bottom).replace(/\D/g, '').slice(0, 5),
      mid: normalizeDigits(top).replace(/\D/g, '').slice(0, 3),
      right: ''
    }
  }
  return {
    left: String(source.plate_left || source.plateLeft || parts[0] || '').trim(),
    letter: normalizePlateLetter(String(source.plate_letter || source.plateLetter || parts[1] || '').trim()),
    mid: String(source.plate_mid || source.plateMid || parts[2] || '').trim(),
    right: String(source.plate_right || source.plateRight || parts[3] || '').trim()
  }
}

export const buildPlateNumber = (parts = {}) => {
  const plateType = String(parts.plate_type || parts.plateType || '').trim()
  const left = String(parts.left || '').trim()
  const letter = String(parts.letter || '').trim()
  const mid = String(parts.mid || '').trim()
  const right = String(parts.right || '').trim()
  if (plateType === 'motorcycle') {
    if (mid && letter) return `${mid} ${letter}`
    return ''
  }
  if (left && letter && mid && right) return `${left} ${letter} ${mid} ${right}`
  return ''
}

export const isAnonymousPlate = (vehicle = {}) => (
  String(vehicle?.plate_number || vehicle?.plate || '').trim() === '1111'
  && String(vehicle?.car_model || vehicle?.model || '').trim() === '1111'
  && String(vehicle?.car_color || vehicle?.color || '').trim() === '1111'
)

export const normalizePhone = (value) => normalizeDigits(value).replace(/\D/g, '').slice(0, 11)

export const isValidIranMobile = (value) => /^09\d{9}$/.test(normalizePhone(value))
