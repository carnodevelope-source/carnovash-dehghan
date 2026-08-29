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
 * look-alike plate letters. Unique letters (م، ن، ل، …) are not listed → no bubbles.
 */
const OCR_AMBIGUOUS_BY_LATIN = {
  s: ['س', 'ص', 'ث'],
  c: ['ص', 'س', 'ث'],
  t: ['ط', 'ت'],
  b: ['ب', 'پ'],
  p: ['پ', 'ب'],
  r: ['ر', 'ز'],
  z: ['ز', 'ر'],
  k: ['ک', 'گ'],
  g: ['گ', 'ک'],
  f: ['ف', 'ق'],
  q: ['ق', 'ف'],
  h: ['ح', 'ج'],
  j: ['ج', 'ح'],
  u: ['ع', 'غ']
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

/** OCR often swaps look-alike digits. Hamming-1 variants only — never a full grid. */
const OCR_DIGIT_CONFUSIONS = {
  0: ['6', '8'],
  1: ['7'],
  2: ['7'],
  3: ['8'],
  4: ['9'],
  5: ['6', '3'],
  6: ['0', '8', '5'],
  7: ['1', '2'],
  8: ['0', '6', '3'],
  9: ['4', '0']
}

export const getOcrDigitConfusionVariants = (left, mid, right) => {
  const digits = `${left}${mid}${right}`
  if (!/^\d{7}$/.test(digits)) return []
  const seen = new Set()
  const variants = []
  for (let index = 0; index < digits.length; index += 1) {
    const options = OCR_DIGIT_CONFUSIONS[digits[index]] || []
    for (const alt of options) {
      if (alt === digits[index]) continue
      const next = `${digits.slice(0, index)}${alt}${digits.slice(index + 1)}`
      if (seen.has(next)) continue
      seen.add(next)
      variants.push({
        left: next.slice(0, 2),
        mid: next.slice(2, 5),
        right: next.slice(5, 7)
      })
    }
  }
  return variants
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
 * Returns [] for unique letters (م، ن، ل، …) so UI hides the chip row.
 */
export const getAmbiguousLetterSuggestions = (letterOrLatin, rawOcrText = '') => {
  const latinFromRaw = extractOcrLatinLetter(rawOcrText)
  if (latinFromRaw && OCR_AMBIGUOUS_BY_LATIN[latinFromRaw]) {
    const family = OCR_AMBIGUOUS_BY_LATIN[latinFromRaw]
    const preferred = normalizePlateLetter(letterOrLatin)
    if (preferred && family.includes(preferred)) {
      return [preferred, ...family.filter((item) => item !== preferred)]
    }
    return [...family]
  }

  const raw = String(letterOrLatin || '').replace(/\s+/g, '')
  if (!raw) return []

  const asLatin = raw.length === 1 && /[a-zA-Z]/.test(raw) ? raw.toLowerCase() : ''
  if (asLatin && OCR_AMBIGUOUS_BY_LATIN[asLatin]) {
    return [...OCR_AMBIGUOUS_BY_LATIN[asLatin]]
  }

  const persian = normalizePlateLetter(raw)
  if (!persian) return []
  const family = OCR_AMBIGUOUS_BY_PERSIAN[persian]
  if (!family) return []
  return [persian, ...family.filter((item) => item !== persian)]
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

export { normalizeIranMobile, isValidIranMobile, iranMobileErrorMessage, assertIranMobile } from './phone'
export { normalizeIranMobile as normalizePhone } from './phone'
