/** Print an HTML element via the browser print dialog (same as Ctrl+P). */
export const printHtmlElement = async (element) => {
  if (!(element instanceof Element)) {
    throw new Error('محتوای چاپ پیدا نشد.')
  }

  const printWindow = window.open('', '_blank', 'noopener,noreferrer,width=900,height=700')
  if (!printWindow) {
    throw new Error('پنجره چاپ مسدود شد. اجازه پاپ‌آپ را برای این سایت فعال کنید.')
  }

  const pageStyles = Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'))
    .map((node) => node.outerHTML)
    .join('\n')

  printWindow.document.open()
  printWindow.document.write(`<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
  <meta charset="utf-8" />
  <title>چاپ فاکتور</title>
  ${pageStyles}
  <style>
    @page { margin: 8mm; }
    html, body {
      margin: 0;
      padding: 0;
      background: #fff;
      color: #111;
    }
    body {
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
  </style>
</head>
<body>${element.outerHTML}</body>
</html>`)
  printWindow.document.close()

  await new Promise((resolve) => {
    const done = () => resolve()
    if (printWindow.document.readyState === 'complete') {
      window.setTimeout(done, 150)
      return
    }
    printWindow.onload = () => window.setTimeout(done, 150)
    window.setTimeout(done, 800)
  })

  try {
    printWindow.focus()
    printWindow.print()
  } finally {
    window.setTimeout(() => {
      try { printWindow.close() } catch (_error) { /* ignore */ }
    }, 400)
  }

  return { ok: true }
}

export const resolvePrintErrorMessage = (error) => (
  error?.message || 'چاپ ناموفق بود.'
)
