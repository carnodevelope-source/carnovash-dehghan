export const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
  .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))

/** OCR latin token → default Persian plate letter (DTRB / light_plate_common). */
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

/**
 * Ambiguous OCR families: one latin token (or its Persian default) maps to several
 * look-alike plate letters. Unique letters (ب، م، ن، ک، …) are not listed → no bubbles.
 */
const OCR_AMBIGUOUS_BY_LATIN = {
  s: ['س', 'ص', 'ث'],
  c: ['ص', 'س', 'ث'],
  t: ['ط', 'ت']
}

const OCR_AMBIGUOUS_BY_PERSIAN = (() => {
  const map = Object.create(null)
  for (const options of Object.values(OCR_AMBIGUOUS_BY_LATIN)) {
    for (const letter of options) {
      if (!map[letter]) map[letter] = [...options]
    }
  }
  return map
})()

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

/** Extract OCR latin letter token from raw plate text like `67b34512`. */
export const extractOcrLatinLetter = (rawText) => {
  const cleaned = String(rawText || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '')
  if (!cleaned) return ''
  if (cleaned.length >= 8) {
    const ch = cleaned[2]
    return /[a-z]/.test(ch) ? ch : ''
  }
  const letter = cleaned.match(/[a-z]/)?.[0] || ''
  return letter
}

/**
 * Bubble options for operator when OCR letter is visually ambiguous.
 * Returns [] for unique letters (م، ب، ک، …) so UI hides the chip row.
 */
export const getAmbiguousLetterSuggestions = (letterOrLatin, rawOcrText = '') => {
  const latinFromRaw = extractOcrLatinLetter(rawOcrText)
  if (latinFromRaw && OCR_AMBIGUOUS_BY_LATIN[latinFromRaw]) {
    return [...OCR_AMBIGUOUS_BY_LATIN[latinFromRaw]]
  }

  const raw = String(letterOrLatin || '').replace(/\s+/g, '')
  if (!raw) return []

  const asLatin = raw.length === 1 && /[a-zA-Z]/.test(raw) ? raw.toLowerCase() : ''
  if (asLatin && OCR_AMBIGUOUS_BY_LATIN[asLatin]) {
    return [...OCR_AMBIGUOUS_BY_LATIN[asLatin]]
  }

  const persian = normalizePlateLetter(raw)
  if (!persian) return []
  return OCR_AMBIGUOUS_BY_PERSIAN[persian] ? [...OCR_AMBIGUOUS_BY_PERSIAN[persian]] : []
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
