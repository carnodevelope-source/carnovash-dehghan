/** Open the OS print dialog (same printers as Ctrl+P). No local agent/install required. */
export const printPdfBlobViaBrowser = (blob) => new Promise((resolve, reject) => {
  if (!(blob instanceof Blob)) {
    reject(new Error('فایل چاپ نامعتبر است.'))
    return
  }

  const url = URL.createObjectURL(blob)
  const iframe = document.createElement('iframe')
  iframe.setAttribute('title', 'carnowash-print')
  iframe.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;opacity:0;pointer-events:none;'

  let settled = false
  const cleanup = () => {
    try { URL.revokeObjectURL(url) } catch (_error) { /* ignore */ }
    try { iframe.remove() } catch (_error) { /* ignore */ }
  }

  const fail = (message) => {
    if (settled) return
    settled = true
    cleanup()
    reject(new Error(message || 'باز کردن پنجره چاپ ناموفق بود.'))
  }

  const succeed = () => {
    if (settled) return
    settled = true
    // Keep iframe briefly so the print dialog can finish loading the PDF.
    window.setTimeout(cleanup, 60_000)
    resolve({ ok: true })
  }

  iframe.onload = () => {
    window.setTimeout(() => {
      try {
        const frameWindow = iframe.contentWindow
        if (!frameWindow) {
          fail('پنجره چاپ در دسترس نیست.')
          return
        }
        frameWindow.focus()
        frameWindow.print()
        succeed()
      } catch (_error) {
        fail('مرورگر اجازه چاپ نداد. پنجره پاپ‌آپ را بررسی کنید.')
      }
    }, 250)
  }

  iframe.onerror = () => fail('بارگذاری فایل چاپ ناموفق بود.')
  document.body.appendChild(iframe)
  iframe.src = url
})

export const resolvePrintErrorMessage = (error) => (
  error?.message || 'چاپ ناموفق بود.'
)
