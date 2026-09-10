const pxToMm = (px) => (Number(px) || 0) * 25.4 / 96

const normalizePageOptions = (page = {}) => {
  const widthMm = Math.max(40, Number(page.widthMm) || 80)
  const marginMm = Math.max(0, Number(page.marginMm ?? (page.thermal ? 1.5 : 6)))
  const marginTopMm = Math.max(0, Number(page.marginTopMm ?? 0))
  const marginRightMm = Math.max(0, Number(page.marginRightMm ?? marginMm))
  const marginBottomMm = Math.max(0, Number(page.marginBottomMm ?? marginMm))
  const marginLeftMm = Math.max(0, Number(page.marginLeftMm ?? marginMm))
  const minHeightMm = Math.max(20, Number(page.minHeightMm) || (page.thermal ? 40 : 100))
  const fixedHeightMm = Number(page.heightMm) > 0 ? Number(page.heightMm) : null
  return {
    widthMm,
    marginMm,
    marginTopMm,
    marginRightMm,
    marginBottomMm,
    marginLeftMm,
    minHeightMm,
    fixedHeightMm,
    thermal: Boolean(page.thermal),
    formatLabel: String(page.formatLabel || '').trim()
  }
}

const THERMAL_PRINT_CSS = `
  html, body {
    margin: 0 !important;
    padding: 0 !important;
    background: #fff !important;
    color: #000 !important;
    height: auto !important;
    min-height: 0 !important;
    max-height: none !important;
    display: block !important;
    position: static !important;
    top: 0 !important;
    inset: auto !important;
    transform: none !important;
    font-family: Tahoma, Arial, sans-serif !important;
  }
  body > * {
    margin: 0 !important;
    margin-top: 0 !important;
    margin-block-start: 0 !important;
    padding-top: 0 !important;
    padding-block-start: 0 !important;
    position: static !important;
    top: auto !important;
    transform: none !important;
    min-height: 0 !important;
    height: auto !important;
    box-shadow: none !important;
    border: 0 !important;
  }
`

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

  const contentWidthMm = Math.max(
    30,
    page.widthMm - page.marginLeftMm - page.marginRightMm
  )

  // Thermal / receipt prints must stay isolated from app CSS (nav offsets, 100vh, flex centering).
  // Paper invoices keep page styles for branded layout fidelity.
  const pageStyles = page.thermal
    ? ''
    : Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'))
      .map((node) => node.outerHTML)
      .join('\n')

  const cloned = element.cloneNode(true)
  if (cloned instanceof HTMLElement) {
    cloned.style.margin = '0'
    cloned.style.marginTop = '0'
    cloned.style.paddingTop = cloned.style.paddingTop || ''
    cloned.style.minHeight = '0'
    cloned.style.height = 'auto'
    cloned.style.position = 'static'
    cloned.style.top = 'auto'
    cloned.style.transform = 'none'
    cloned.querySelectorAll('.invoice-sheet, .worker-receipt-pdf').forEach((node) => {
      if (!(node instanceof HTMLElement)) return
      node.style.minHeight = '0'
      node.style.height = 'auto'
      node.style.marginTop = '0'
    })
  }

  frameDoc.open()
  frameDoc.write(`<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
  <meta charset="utf-8" />
  <title>چاپ فاکتور</title>
  ${pageStyles}
  <style id="carnowash-print-page-style">
    ${THERMAL_PRINT_CSS}
    html, body {
      width: ${contentWidthMm}mm;
      max-width: ${contentWidthMm}mm;
    }
    body > .invoice-template,
    body > .invoice-sheet,
    body > .worker-receipt-pdf,
    body > * {
      width: ${contentWidthMm}mm !important;
      max-width: ${contentWidthMm}mm !important;
      overflow: visible !important;
      align-self: flex-start !important;
      vertical-align: top !important;
    }
    body > * .invoice-sheet,
    body > * .worker-receipt-pdf {
      min-height: 0 !important;
      height: auto !important;
      margin-top: 0 !important;
      align-content: start !important;
      align-items: start !important;
    }
  </style>
</head>
<body></body>
</html>`)
  frameDoc.close()
  frameDoc.body.appendChild(cloned)

  await new Promise((resolve) => {
    const done = () => resolve()
    if (frameDoc.readyState === 'complete') {
      window.setTimeout(done, 120)
      return
    }
    iframe.onload = () => window.setTimeout(done, 120)
    window.setTimeout(done, 700)
  })

  const root = frameDoc.body.firstElementChild || frameDoc.body
  root.style.minHeight = '0'
  root.style.height = 'auto'
  root.querySelectorAll('.invoice-sheet, .worker-receipt-pdf').forEach((node) => {
    node.style.minHeight = '0'
    node.style.height = 'auto'
  })

  const measuredHeightMm = Math.ceil(pxToMm(root.scrollHeight || frameDoc.body.scrollHeight || 0))
  // Hug content tightly — do not inflate thermal pages with unused blank height.
  const heightMm = page.fixedHeightMm
    || Math.max(
      page.thermal ? Math.max(30, measuredHeightMm) : page.minHeightMm,
      measuredHeightMm + (page.thermal ? 0 : (page.marginTopMm + page.marginBottomMm))
    )

  const pageStyleNode = frameDoc.getElementById('carnowash-print-page-style')
  if (pageStyleNode) {
    pageStyleNode.textContent += `
      @page {
        size: ${page.widthMm}mm ${heightMm}mm;
        margin: ${page.marginTopMm}mm ${page.marginRightMm}mm ${page.marginBottomMm}mm ${page.marginLeftMm}mm;
      }
      @media print {
        html, body {
          width: ${contentWidthMm}mm !important;
          max-width: ${contentWidthMm}mm !important;
          margin: 0 !important;
          padding: 0 !important;
          height: auto !important;
          min-height: 0 !important;
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
