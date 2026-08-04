/** Print an HTML element via the browser print dialog (same as Ctrl+P), without popup windows. */
export const printHtmlElement = async (element) => {
  if (!(element instanceof Element)) {
    throw new Error('محتوای چاپ پیدا نشد.')
  }

  const iframe = document.createElement('iframe')
  iframe.setAttribute('title', 'carnowash-print')
  iframe.setAttribute('aria-hidden', 'true')
  iframe.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;opacity:0;pointer-events:none;'
  document.body.appendChild(iframe)

  const frameDoc = iframe.contentDocument || iframe.contentWindow?.document
  const frameWindow = iframe.contentWindow
  if (!frameDoc || !frameWindow) {
    iframe.remove()
    throw new Error('پنجره چاپ در دسترس نیست.')
  }

  const pageStyles = Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'))
    .map((node) => node.outerHTML)
    .join('\n')

  frameDoc.open()
  frameDoc.write(`<!DOCTYPE html>
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
  frameDoc.close()

  await new Promise((resolve) => {
    const done = () => resolve()
    if (frameDoc.readyState === 'complete') {
      window.setTimeout(done, 150)
      return
    }
    iframe.onload = () => window.setTimeout(done, 150)
    window.setTimeout(done, 800)
  })

  try {
    frameWindow.focus()
    frameWindow.print()
  } finally {
    window.setTimeout(() => {
      try { iframe.remove() } catch (_error) { /* ignore */ }
    }, 60_000)
  }

  return { ok: true }
}

export const resolvePrintErrorMessage = (error) => (
  error?.message || 'چاپ ناموفق بود.'
)
