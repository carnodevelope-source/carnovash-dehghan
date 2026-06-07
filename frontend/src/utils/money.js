export const toThousandsToman = (value) => Number(value || 0) / 1000

export const formatThousandsTomanValue = (value, options = {}) => {
  const numeric = toThousandsToman(value)
  const {
    minimumFractionDigits = 0,
    maximumFractionDigits = Number.isInteger(numeric) ? 0 : 1
  } = options
  return numeric.toLocaleString('fa-IR', {
    minimumFractionDigits,
    maximumFractionDigits
  })
}

export const formatThousandsToman = (value, options = {}) => `${formatThousandsTomanValue(value, options)} هزار تومان`

export const fromThousandsTomanInput = (value) => Math.round(Number(value || 0) * 1000)
