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

/**
 * Self-contained invoice/receipt layout for the print iframe.
 * App Vue styles are scoped (data-v-*) and thermal mode previously skipped
 * copying them, so tables/grids collapsed into plain jumbled text.
 */
const INVOICE_PRINT_LAYOUT_CSS = `
  *, *::before, *::after { box-sizing: border-box !important; }

  .invoice-template,
  .invoice-sheet,
  .worker-receipt-pdf {
    direction: rtl !important;
    background: #fff !important;
    color: #0f172a !important;
    font-family: Tahoma, "Segoe UI", Arial, sans-serif !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    overflow: visible !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    min-height: 0 !important;
    height: auto !important;
    position: static !important;
    transform: none !important;
    contain: none !important;
  }

  .invoice-template {
    display: block !important;
    padding: 0 !important;
  }

  .invoice-sheet {
    display: grid !important;
    gap: 7px !important;
    color: #0f172a !important;
  }

  .worker-receipt-pdf {
    display: block !important;
  }

  .invoice-sheet-thermal {
    color: #000 !important;
    line-height: 1.35 !important;
    gap: 4px !important;
  }

  .invoice-sheet-thermal,
  .invoice-sheet-thermal * {
    color: #000 !important;
    background: #fff !important;
    background-color: #fff !important;
    box-shadow: none !important;
    text-shadow: none !important;
  }

  .invoice-sheet-thermal * { border-color: #000 !important; }

  .invoice-sheet-head {
    display: grid !important;
    grid-template-columns: minmax(0, 1.2fr) minmax(0, .8fr) !important;
    justify-content: space-between !important;
    gap: 8px !important;
    padding: 10px 12px !important;
    border-radius: 10px !important;
    background: linear-gradient(135deg, #0f172a, #0f4c81 58%, #0ea5e9) !important;
    color: #fff !important;
    min-width: 0 !important;
    max-width: 100% !important;
  }

  .invoice-sheet-head > * { min-width: 0 !important; }

  .invoice-sheet-head .invoice-header-note {
    grid-column: 1 / -1 !important;
    text-align: center !important;
    justify-self: center !important;
    width: 100% !important;
    margin-top: 2px !important;
  }

  .invoice-sheet-head small {
    display: block !important;
    font-size: 10px !important;
    color: rgba(255, 255, 255, .72) !important;
  }

  .invoice-sheet-head strong {
    display: block !important;
    font-size: 18px !important;
    line-height: 1.35 !important;
    margin-top: 2px !important;
    color: #fff !important;
    overflow-wrap: anywhere !important;
  }

  .invoice-sheet-head span {
    display: block !important;
    margin-top: 3px !important;
    color: rgba(255, 255, 255, .78) !important;
    font-size: 10px !important;
    overflow-wrap: anywhere !important;
  }

  .invoice-sheet-meta {
    display: grid !important;
    gap: 4px !important;
    justify-items: end !important;
    min-width: 0 !important;
    align-content: center !important;
  }

  .invoice-sheet-meta strong {
    font-size: 12px !important;
    color: #fff !important;
    overflow-wrap: anywhere !important;
  }

  .receipt-custom-note {
    white-space: pre-line !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
    text-align: center !important;
    line-height: 1.7 !important;
  }

  .invoice-identity-grid {
    display: grid !important;
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
    gap: 6px !important;
  }

  .invoice-identity-grid article {
    border: 1px solid #dbe7f5 !important;
    border-radius: 8px !important;
    padding: 7px !important;
    background: linear-gradient(180deg, #ffffff, #f8fbff) !important;
    display: grid !important;
    gap: 4px !important;
    min-width: 0 !important;
  }

  .invoice-identity-grid small {
    color: #0f4c81 !important;
    font-size: 11px !important;
    font-weight: 800 !important;
  }

  .invoice-identity-grid p {
    margin: 0 !important;
    display: grid !important;
    grid-template-columns: minmax(0, .62fr) minmax(0, 1fr) !important;
    gap: 6px !important;
    align-items: start !important;
    color: #334155 !important;
    font-size: 10px !important;
    line-height: 1.55 !important;
    min-width: 0 !important;
  }

  .invoice-identity-grid p span { color: #64748b !important; min-width: 0 !important; }
  .invoice-identity-grid p strong {
    color: #0f172a !important;
    font-size: 10px !important;
    font-weight: 800 !important;
    min-width: 0 !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
  }

  .invoice-sheet-section {
    display: grid !important;
    gap: 6px !important;
    min-width: 0 !important;
    max-width: 100% !important;
  }

  .invoice-section-head strong {
    font-size: 12px !important;
    color: #0f172a !important;
  }

  table.invoice-table,
  table.thermal-items-table {
    display: table !important;
    width: 100% !important;
    max-width: 100% !important;
    table-layout: fixed !important;
    border-collapse: collapse !important;
    border-spacing: 0 !important;
    empty-cells: show !important;
  }

  table.invoice-table {
    border: 1px solid #dbe7f5 !important;
    border-radius: 8px !important;
    overflow: hidden !important;
  }

  table.invoice-table thead { display: table-header-group !important; }
  table.invoice-table tbody { display: table-row-group !important; }
  table.invoice-table tr { display: table-row !important; }
  table.invoice-table th,
  table.invoice-table td {
    display: table-cell !important;
    padding: 5px 7px !important;
    border: 0 !important;
    border-bottom: 1px solid #e2e8f0 !important;
    text-align: right !important;
    font-size: 11px !important;
    line-height: 1.6 !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
    min-width: 0 !important;
    vertical-align: middle !important;
  }

  table.invoice-table th {
    background: #eff6ff !important;
    color: #334155 !important;
    font-weight: 800 !important;
  }

  table.invoice-table tr:last-child td { border-bottom: 0 !important; }

  .invoice-services-table th:first-child,
  .invoice-services-table td:first-child { width: 58% !important; }
  .invoice-services-table th:nth-child(2),
  .invoice-services-table td:nth-child(2) { width: 14% !important; text-align: center !important; }
  .invoice-services-table th:nth-child(3),
  .invoice-services-table td:nth-child(3) { width: 28% !important; }

  .invoice-products-table th:first-child,
  .invoice-products-table td:first-child { width: 48% !important; }
  .invoice-products-table th:nth-child(2),
  .invoice-products-table td:nth-child(2) { width: 12% !important; text-align: center !important; }
  .invoice-products-table th:nth-child(3),
  .invoice-products-table td:nth-child(3) { width: 20% !important; }
  .invoice-products-table th:nth-child(4),
  .invoice-products-table td:nth-child(4) { width: 20% !important; }

  .invoice-payment-section {
    border: 1px solid #dbe7f5 !important;
    border-radius: 10px !important;
    padding: 7px 9px !important;
    background: #f8fbff !important;
  }

  .invoice-payment-grid {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 4px 8px !important;
  }

  .invoice-payment-grid p {
    margin: 0 !important;
    display: grid !important;
    grid-template-columns: minmax(0, .65fr) minmax(0, 1fr) !important;
    gap: 8px !important;
    color: #334155 !important;
    font-size: 10px !important;
    line-height: 1.6 !important;
    min-width: 0 !important;
  }

  .invoice-payment-grid p strong { color: #0f172a !important; }

  .invoice-total-section {
    border: 1px solid #dbe7f5 !important;
    border-radius: 10px !important;
    padding: 8px 10px !important;
    background: linear-gradient(180deg, #ffffff, #f8fbff) !important;
  }

  .invoice-totals {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 4px 8px !important;
  }

  .invoice-totals p {
    margin: 0 !important;
    display: grid !important;
    grid-template-columns: minmax(0, .75fr) minmax(0, 1fr) !important;
    gap: 8px !important;
    color: #334155 !important;
    font-size: 11px !important;
    min-width: 0 !important;
  }

  .invoice-grand-total {
    grid-column: 1 / -1 !important;
    padding-top: 6px !important;
    border-top: 1px dashed #bfd7ff !important;
    font-size: 14px !important;
    font-weight: 900 !important;
    color: #0f172a !important;
  }

  .invoice-sheet-footer {
    padding-top: 6px !important;
    border-top: 1px dashed #cbd5e1 !important;
    display: grid !important;
    gap: 3px !important;
  }

  .invoice-sheet-footer p {
    margin: 0 !important;
    color: #475569 !important;
    font-size: 10px !important;
    line-height: 1.7 !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
    white-space: pre-line !important;
  }

  .thermal-sheet-head {
    display: grid !important;
    justify-items: center !important;
    gap: 5px !important;
    padding: 3px 0 8px !important;
    border-bottom: 2px solid #000 !important;
    text-align: center !important;
  }

  .thermal-sheet-head strong {
    font-size: 22px !important;
    font-weight: 900 !important;
    line-height: 1.22 !important;
  }

  .thermal-sheet-head span {
    font-size: 13px !important;
    font-weight: 800 !important;
    line-height: 1.5 !important;
    max-width: 100% !important;
    overflow-wrap: anywhere !important;
  }

  .thermal-sheet-head small {
    font-size: 11px !important;
    font-weight: 800 !important;
    line-height: 1.65 !important;
    max-width: 100% !important;
    overflow-wrap: anywhere !important;
    white-space: pre-line !important;
    text-align: center !important;
  }

  .thermal-info-grid {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 5px 10px !important;
    padding: 8px 0 !important;
    border-bottom: 2px solid #000 !important;
  }

  .thermal-info-grid p {
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
    font-size: 12px !important;
    line-height: 1.55 !important;
    min-width: 0 !important;
  }

  .thermal-info-grid span { flex: 0 0 auto !important; font-weight: 700 !important; }
  .thermal-info-grid strong {
    min-width: 0 !important;
    font-weight: 700 !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
  }

  .thermal-items-section { padding: 8px 0 !important; display: block !important; }

  table.thermal-items-table {
    border: 1.5px solid #000 !important;
  }

  table.thermal-items-table thead { display: table-header-group !important; }
  table.thermal-items-table tbody { display: table-row-group !important; }
  table.thermal-items-table tr { display: table-row !important; }
  table.thermal-items-table th,
  table.thermal-items-table td {
    display: table-cell !important;
    border: 1px solid #000 !important;
    padding: 7px 5px !important;
    text-align: center !important;
    vertical-align: middle !important;
    font-size: 12px !important;
    line-height: 1.35 !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
  }

  table.thermal-items-table th { font-weight: 900 !important; }
  table.thermal-items-table th:first-child,
  table.thermal-items-table td:first-child { width: 62% !important; text-align: center !important; }
  table.thermal-items-table th:nth-child(2),
  table.thermal-items-table td:nth-child(2) { width: 38% !important; }

  .thermal-total-block {
    display: grid !important;
    gap: 4px !important;
    padding: 6px 0 0 !important;
  }

  .thermal-total-block p {
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 10px !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
  }

  .thermal-total-block span { font-weight: 800 !important; }
  .thermal-total-block strong {
    font-weight: 900 !important;
    text-align: left !important;
    white-space: nowrap !important;
  }

  .thermal-payable-total {
    margin-top: 4px !important;
    padding: 8px 0 !important;
    border-top: 2px solid #000 !important;
    border-bottom: 4px double #000 !important;
    font-size: 16px !important;
    font-weight: 900 !important;
  }

  .thermal-payable-total strong { font-size: 17px !important; }

  .thermal-sheet-footer {
    display: grid !important;
    gap: 3px !important;
    padding-top: 8px !important;
  }

  .thermal-sheet-footer p {
    margin: 0 !important;
    text-align: center !important;
    font-size: 11px !important;
    line-height: 1.65 !important;
    font-weight: 800 !important;
    white-space: pre-line !important;
    overflow-wrap: anywhere !important;
    word-break: break-word !important;
  }

  .thermal-sheet-footer .receipt-custom-note {
    padding-top: 6px !important;
    border-top: 1px dashed #000 !important;
  }

  .thermal-sheet-footer strong {
    display: block !important;
    margin-top: 8px !important;
    text-align: center !important;
    font-size: 14px !important;
    font-weight: 900 !important;
    line-height: 1.7 !important;
  }

  @media print {
    table.invoice-table,
    table.thermal-items-table {
      page-break-inside: auto !important;
      break-inside: auto !important;
    }
    table.invoice-table tr,
    table.thermal-items-table tr {
      page-break-inside: avoid !important;
      break-inside: avoid !important;
    }
  }
`

const PRINT_BASE_CSS = `
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
    font-family: Tahoma, "Segoe UI", Arial, sans-serif !important;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
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

  // Never rely on Vue scoped app styles in the print iframe — they either
  // miss thermal mode entirely or pull in page chrome that breaks tables.
  const cloned = element.cloneNode(true)
  if (cloned instanceof HTMLElement) {
    cloned.style.margin = '0'
    cloned.style.marginTop = '0'
    cloned.style.minHeight = '0'
    cloned.style.height = 'auto'
    cloned.style.position = 'static'
    cloned.style.top = 'auto'
    cloned.style.transform = 'none'
    cloned.style.width = `${contentWidthMm}mm`
    cloned.style.maxWidth = `${contentWidthMm}mm`
    cloned.querySelectorAll('.invoice-sheet, .worker-receipt-pdf, .invoice-template').forEach((node) => {
      if (!(node instanceof HTMLElement)) return
      node.style.minHeight = '0'
      node.style.height = 'auto'
      node.style.marginTop = '0'
      node.style.width = '100%'
      node.style.maxWidth = '100%'
      node.style.contain = 'none'
    })
  }

  frameDoc.open()
  frameDoc.write(`<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
  <meta charset="utf-8" />
  <title>چاپ فاکتور</title>
  <style id="carnowash-print-page-style">
    ${PRINT_BASE_CSS}
    ${INVOICE_PRINT_LAYOUT_CSS}
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
    }
    body > * .invoice-sheet,
    body > * .worker-receipt-pdf,
    body > * .invoice-template {
      min-height: 0 !important;
      height: auto !important;
      margin-top: 0 !important;
      width: 100% !important;
      max-width: 100% !important;
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
  root.querySelectorAll('.invoice-sheet, .worker-receipt-pdf, .invoice-template').forEach((node) => {
    node.style.minHeight = '0'
    node.style.height = 'auto'
    node.style.contain = 'none'
  })

  const measuredHeightMm = Math.ceil(pxToMm(root.scrollHeight || frameDoc.body.scrollHeight || 0))
  // Hug content tightly — do not inflate thermal pages with unused blank height.
  // Small buffer keeps the last line from spilling onto a blank second page.
  const heightMm = page.fixedHeightMm
    || Math.max(
      page.thermal ? Math.max(30, measuredHeightMm + 3) : page.minHeightMm,
      measuredHeightMm + (page.thermal ? 3 : (page.marginTopMm + page.marginBottomMm))
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
          overflow: visible !important;
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
