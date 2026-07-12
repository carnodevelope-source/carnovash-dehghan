const normalizeNumericInput = (value) => String(value ?? '')
  .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
  .replace(/[^\d.-]/g, '')

export const toThousandsToman = (value) => Number(value || 0)

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
  const numeric = Number(value || 0)
  return formatFaNumber(numeric, options)
}

export const formatThousandsToman = (value, options = {}) => `${formatThousandsTomanValue(value, options)} تومان`

export const fromThousandsTomanInput = (value) => Math.round(Number(normalizeNumericInput(value) || 0))
