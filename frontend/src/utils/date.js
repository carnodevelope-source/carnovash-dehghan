export const formatJalaliDate = (value) => {
  if (!value) return '-'
  return new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(new Date(value))
}

export const formatJalaliDateTime = (value) => {
  if (!value) return '-'
  const date = formatJalaliDate(value)
  const time = new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(value))
  return `${date} ${time}`
}
