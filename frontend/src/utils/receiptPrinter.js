const PRINT_AGENT_BASE_URL = String(import.meta.env.VITE_PRINT_AGENT_URL || 'http://127.0.0.1:17321').replace(/\/$/, '')

const requestJson = async (path, options = {}) => {
  const response = await fetch(`${PRINT_AGENT_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.headers || {})
    }
  })
  let data = null
  try {
    data = await response.json()
  } catch (_error) {
    data = null
  }
  if (!response.ok || data?.ok === false) {
    const error = new Error(data?.message || `خطای پرینت‌ایجنت (${response.status})`)
    error.status = response.status
    error.data = data
    throw error
  }
  return data || {}
}

export const getPrintAgentBaseUrl = () => PRINT_AGENT_BASE_URL

export const checkPrintAgentHealth = async () => {
  try {
    const data = await requestJson('/health', { method: 'GET', signal: AbortSignal.timeout(2500) })
    return { online: true, data }
  } catch (_error) {
    return { online: false, data: null }
  }
}

export const fetchSystemPrinters = async () => {
  const data = await requestJson('/printers', { method: 'GET', signal: AbortSignal.timeout(5000) })
  return Array.isArray(data.printers) ? data.printers : []
}

const blobToBase64 = (blob) => new Promise((resolve, reject) => {
  const reader = new FileReader()
  reader.onload = () => resolve(String(reader.result || ''))
  reader.onerror = () => reject(new Error('خواندن فایل PDF برای چاپ ناموفق بود.'))
  reader.readAsDataURL(blob)
})

export const printPdfBlobSilent = async (blob, printerName, fileName = 'carnowash-receipt.pdf') => {
  const normalizedPrinter = String(printerName || '').trim()
  if (!normalizedPrinter) {
    throw new Error('ابتدا در تنظیمات، پرینتر سیستم را انتخاب و ثبت کنید.')
  }
  if (!(blob instanceof Blob)) {
    throw new Error('فایل چاپ نامعتبر است.')
  }
  const pdfBase64 = await blobToBase64(blob)
  return requestJson('/print', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      printerName: normalizedPrinter,
      pdfBase64,
      fileName
    })
  })
}

export const resolveSilentPrintErrorMessage = (error) => {
  if (error?.status === 0 || error?.name === 'TypeError' || error?.name === 'TimeoutError' || error?.name === 'AbortError') {
    return 'پرینت‌ایجنت روشن نیست. فایل tools/print-agent/start-print-agent.bat را روی همین سیستم اجرا کنید.'
  }
  return error?.message || 'چاپ مستقیم ناموفق بود.'
}
