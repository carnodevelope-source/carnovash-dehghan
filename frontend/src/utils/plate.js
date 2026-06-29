export const normalizeDigits = (value) => String(value || '')
  .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
  .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))

export const normalizePlateLetter = (value) => {
  const raw = String(value || '').replace(/\s+/g, '').slice(0, 1)
  const englishMap = { A: 'ا', B: 'ب', D: 'د', H: 'ه', J: 'ج', L: 'ل', M: 'م', N: 'ن', P: 'پ', S: 'س', T: 'ط', V: 'و', Y: 'ی' }
  const upper = raw.toUpperCase()
  if (englishMap[upper]) return englishMap[upper]
  return raw.replace(/[^آابپتثجچحخدذرزسشصضطظعغفقکگلمنوهی]/g, '')
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

export const isValidIranMobile = (value) => /^0\d{10}$/.test(normalizePhone(value))
