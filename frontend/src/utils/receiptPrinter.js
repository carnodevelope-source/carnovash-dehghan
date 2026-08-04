const pxToMm = (px) => (Number(px) || 0) * 25.4 / 96

const normalizePageOptions = (page = {}) => {
  const widthMm = Math.max(40, Number(page.widthMm) || 80)
  const marginMm = Math.max(0, Number(page.marginMm ?? (page.thermal ? 1.5 : 6)))
  const minHeightMm = Math.max(40, Number(page.minHeightMm) || (page.thermal ? 80 : 100))
  const fixedHeightMm = Number(page.heightMm) > 0 ? Number(page.heightMm) : null
  return {
    widthMm,
    marginMm,
    minHeightMm,
    fixedHeightMm,
    thermal: Boolean(page.thermal),
    formatLabel: String(page.formatLabel || '').trim()
  }
}

/** Print an HTML element via the browser print dialog (same as Ctrl+P), without popup windows. */
export const printHtmlElement = async (element, pageOptions = {}) => {
  if (!(element instanceof Element)) {
    throw new Error('محتوای چاپ پیدا نشد.')
  }

  const page = normalizePageOptions(pageOptions)
  const iframe = document.createElement('iframe')
  iframe.setAttribute('title', 'carnowash-print')
  iframe.setAttribute('aria-hidden', 'true')
  // Keep iframe large enough off-screen so layout/height measurement is accurate.
  iframe.style.cssText = [
    'position:fixed',
    'left:-10000px',
    'top:0',
    `width:${Math.ceil(page.widthMm * 3.78)}px`,
    'height:1200px',
    'border:0',
    'opacity:0',
    'pointer-events:none'
  ].join(';')
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

  const contentWidthMm = Math.max(30, page.widthMm - page.marginMm * 2)

  frameDoc.open()
  frameDoc.write(`<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
  <meta charset="utf-8" />
  <title>چاپ فاکتور</title>
  ${pageStyles}
  <style id="carnowash-print-page-style">
    html, body {
      margin: 0;
      padding: 0;
      background: #fff;
      color: #111;
      width: ${contentWidthMm}mm;
      max-width: ${contentWidthMm}mm;
    }
    body {
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    body > .invoice-template,
    body > * {
      width: ${contentWidthMm}mm !important;
      max-width: ${contentWidthMm}mm !important;
      min-height: auto !important;
      margin: 0 !important;
      box-shadow: none !important;
      border: 0 !important;
      overflow: visible !important;
    }
  </style>
</head>
<body>${element.outerHTML}</body>
</html>`)
  frameDoc.close()

  await new Promise((resolve) => {
    const done = () => resolve()
    if (frameDoc.readyState === 'complete') {
      window.setTimeout(done, 180)
      return
    }
    iframe.onload = () => window.setTimeout(done, 180)
    window.setTimeout(done, 900)
  })

  const root = frameDoc.body.firstElementChild || frameDoc.body
  const measuredHeightMm = Math.ceil(pxToMm(root.scrollHeight || frameDoc.body.scrollHeight || 0))
  const heightMm = page.fixedHeightMm
    || Math.max(page.minHeightMm, measuredHeightMm + page.marginMm * 2)

  const pageStyleNode = frameDoc.getElementById('carnowash-print-page-style')
  if (pageStyleNode) {
    pageStyleNode.textContent += `
      @page {
        size: ${page.widthMm}mm ${heightMm}mm;
        margin: ${page.marginMm}mm;
      }
      @media print {
        html, body {
          width: ${contentWidthMm}mm !important;
          max-width: ${contentWidthMm}mm !important;
        }
      }
    `
  }

  try {
    frameWindow.focus()
    frameWindow.print()
  } finally {
    window.setTimeout(() => {
      try { iframe.remove() } catch (_error) { /* ignore */ }
    }, 60_000)
  }

  return { ok: true, widthMm: page.widthMm, heightMm }
}

export const resolvePrintErrorMessage = (error) => (
  error?.message || 'چاپ ناموفق بود.'
)
