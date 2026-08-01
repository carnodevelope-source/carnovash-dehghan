const PRINT_AGENT_CANDIDATES = Array.from(new Set([
  String(import.meta.env.VITE_PRINT_AGENT_URL || '').replace(/\/$/, ''),
  'http://127.0.0.1:17321',
  'http://localhost:17321'
].filter(Boolean)))

let resolvedPrintAgentBaseUrl = PRINT_AGENT_CANDIDATES[0] || 'http://127.0.0.1:17321'

const requestJsonAt = async (baseUrl, path, options = {}) => {
  const response = await fetch(`${baseUrl}${path}`, {
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

const requestJson = async (path, options = {}) => {
  let lastError = null
  const bases = Array.from(new Set([resolvedPrintAgentBaseUrl, ...PRINT_AGENT_CANDIDATES]))
  for (const baseUrl of bases) {
    try {
      const data = await requestJsonAt(baseUrl, path, options)
      resolvedPrintAgentBaseUrl = baseUrl
      return data
    } catch (error) {
      lastError = error
      // Keep trying other loopback URLs only for connectivity failures.
      if (error?.status && error.status !== 0) throw error
    }
  }
  throw lastError || new Error('پرینت‌ایجنت در دسترس نیست.')
}

export const getPrintAgentBaseUrl = () => resolvedPrintAgentBaseUrl

export const checkPrintAgentHealth = async () => {
  try {
    const data = await requestJson('/health', { method: 'GET', signal: AbortSignal.timeout(2500) })
    return { online: true, data }
  } catch (_error) {
    return { online: false, data: null }
  }
}

export const fetchSystemPrinters = async () => {
  const data = await requestJson('/printers', { method: 'GET', signal: AbortSignal.timeout(8000) })
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
    if (typeof window !== 'undefined' && window.isSecureContext && window.location?.protocol === 'https:') {
      return 'مرورگر به پرینت‌ایجنت محلی وصل نشد. start-print-agent.bat را اجرا کنید و اگر باز هم لیست خالی بود، یک‌بار صفحه را رفرش کنید.'
    }
    return 'پرینت‌ایجنت روشن نیست. فایل tools/print-agent/start-print-agent.bat را روی همین سیستم اجرا کنید.'
  }
  return error?.message || 'چاپ مستقیم ناموفق بود.'
}
