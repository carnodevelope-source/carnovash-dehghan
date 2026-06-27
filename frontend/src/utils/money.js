export const toThousandsToman = (value) => Number(value || 0) / 1000

const formatFaNumber = (numeric, options = {}) => {
  const {
    minimumFractionDigits = 0,
    maximumFractionDigits = Number.isInteger(numeric) ? 0 : 1
  } = options
  return numeric.toLocaleString('fa-IR', {
    minimumFractionDigits,
    maximumFractionDigits
  })
}

export const formatThousandsTomanValue = (value, options = {}) => {
  const numeric = toThousandsToman(value)
  return formatFaNumber(numeric, options)
}

export const formatThousandsToman = (value, options = {}) => {
  const numeric = Number(value || 0)
  if (Math.abs(numeric) >= 1000000) {
    return `${formatFaNumber(numeric / 1000000, options)} میلیون تومان`
  }
  return `${formatThousandsTomanValue(value, options)} هزار تومان`
}

export const fromThousandsTomanInput = (value) => Math.round(Number(value || 0) * 1000)
