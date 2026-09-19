// Constructing an Intl.DateTimeFormat is expensive, and these run once per row
// of every list, so the formatters are built once and reused.
const jalaliDateFormatter = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit'
})

const jalaliTimeFormatter = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
  hour: '2-digit',
  minute: '2-digit'
})

const jalaliMonthDayFormatter = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
  month: '2-digit',
  day: '2-digit'
})

export const formatJalaliDate = (value) => {
  if (!value) return '-'
  return jalaliDateFormatter.format(new Date(value))
}

export const formatJalaliMonthDay = (value) => {
  if (!value) return '-'
  return jalaliMonthDayFormatter.format(new Date(value))
}

export const formatJalaliDateTime = (value) => {
  if (!value) return '-'
  return `${jalaliDateFormatter.format(new Date(value))} ${jalaliTimeFormatter.format(new Date(value))}`
}

/** Convert Jalali date string YYYY/MM/DD to Gregorian ISO YYYY-MM-DD for API filters. */
export const parseJalaliToIso = (input) => {
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
    gy += Math.floor((gDayNo - 1) / 365)
    gDayNo = (gDayNo - 1) % 365
  }
  const gDaysInMonth = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  let gm = 0
  while (gm < 12 && gDayNo >= gDaysInMonth[gm]) {
    gDayNo -= gDaysInMonth[gm]
    gm += 1
  }
  const gd = gDayNo + 1
  const month = String(gm + 1).padStart(2, '0')
  const day = String(gd).padStart(2, '0')
  return `${gy}-${month}-${day}`
}
