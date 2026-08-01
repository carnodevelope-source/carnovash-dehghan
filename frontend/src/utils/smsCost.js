/**
 * Melipayamak / IranPayamak Persian (UCS-2) SMS billing helpers.
 * Single part: up to 70 chars. Multipart: 67 chars per part.
 * Provider may append an unsubscribe footer (لغو11) — include it in billable length.
 */

export const SMS_CHARS_PER_SEGMENT_DEFAULT = 70
export const SMS_PRICE_PER_SEGMENT_DEFAULT = 185
export const SMS_PROVIDER_FOOTER_DEFAULT = '\nلغو11'

export function smsBillableText(text, { footer = SMS_PROVIDER_FOOTER_DEFAULT } = {}) {
  const body = String(text || '')
  if (!body.trim()) return ''
  if (!footer) return body
  if (body.includes('لغو')) return body
  return `${body}${footer}`
}

export function smsSegmentsForText(
  text,
  {
    charsPerSegment = SMS_CHARS_PER_SEGMENT_DEFAULT,
    footer = SMS_PROVIDER_FOOTER_DEFAULT,
  } = {},
) {
  const length = smsBillableText(text, { footer }).length
  if (length <= 0) return 0
  const singleLimit = Math.max(1, Number(charsPerSegment) || SMS_CHARS_PER_SEGMENT_DEFAULT)
  if (length <= singleLimit) return 1
  const multiLimit = Math.max(1, singleLimit - 3)
  return Math.ceil(length / multiLimit)
}

export function smsCostForText(
  text,
  {
    pricePerSegment = SMS_PRICE_PER_SEGMENT_DEFAULT,
    charsPerSegment = SMS_CHARS_PER_SEGMENT_DEFAULT,
    footer = SMS_PROVIDER_FOOTER_DEFAULT,
  } = {},
) {
  const segments = smsSegmentsForText(text, { charsPerSegment, footer })
  if (!segments) return 0
  return segments * Number(pricePerSegment || 0)
}

export function smsCharacterCount(text, options = {}) {
  return smsBillableText(text, options).length
}
