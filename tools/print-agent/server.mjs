import cors from 'cors'
import express from 'express'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import pdfToPrinter from 'pdf-to-printer'

const { getPrinters, print } = pdfToPrinter

const PORT = Number(process.env.CARNOWASH_PRINT_AGENT_PORT || 17321)
const HOST = process.env.CARNOWASH_PRINT_AGENT_HOST || '127.0.0.1'

const app = express()
app.use(cors({ origin: true }))
app.use(express.json({ limit: '25mb' }))

const ok = (res, data = {}) => res.json({ ok: true, ...data })
const fail = (res, status, message) => res.status(status).json({ ok: false, message })

app.get('/health', (_req, res) => {
  ok(res, {
    service: 'carnowash-print-agent',
    platform: process.platform,
    host: HOST,
    port: PORT
  })
})

app.get('/printers', async (_req, res) => {
  try {
    const printers = await getPrinters()
    const list = (Array.isArray(printers) ? printers : [])
      .map((item) => ({
        name: String(item?.name || item?.deviceId || '').trim(),
        isDefault: Boolean(item?.isDefault)
      }))
      .filter((item) => item.name)
      .sort((a, b) => Number(b.isDefault) - Number(a.isDefault) || a.name.localeCompare(b.name, 'fa'))
    return ok(res, { printers: list })
  } catch (error) {
    console.error('list printers failed:', error)
    return fail(res, 500, 'خواندن لیست پرینترهای سیستم ناموفق بود.')
  }
})

app.post('/print', async (req, res) => {
  const printerName = String(req.body?.printerName || '').trim()
  const pdfBase64 = String(req.body?.pdfBase64 || '').trim()
  const fileName = String(req.body?.fileName || 'carnowash-receipt.pdf').replace(/[^\w.\-آ-ی]+/g, '_') || 'carnowash-receipt.pdf'

  if (!printerName) {
    return fail(res, 400, 'نام پرینتر مشخص نشده است.')
  }
  if (!pdfBase64) {
    return fail(res, 400, 'فایل PDF برای چاپ ارسال نشده است.')
  }

  const pureBase64 = pdfBase64.includes(',') ? pdfBase64.split(',').pop() : pdfBase64
  let tempFile = ''
  try {
    const buffer = Buffer.from(pureBase64, 'base64')
    if (!buffer.length) {
      return fail(res, 400, 'فایل PDF نامعتبر است.')
    }
    tempFile = path.join(os.tmpdir(), `carnowash-print-${Date.now()}-${fileName.endsWith('.pdf') ? fileName : `${fileName}.pdf`}`)
    await fs.writeFile(tempFile, buffer)
    await print(tempFile, {
      printer: printerName,
      silent: true,
      scale: 'noscale',
      monochrome: true
    })
    return ok(res, { printerName })
  } catch (error) {
    console.error('silent print failed:', error)
    return fail(res, 500, error?.message || 'چاپ مستقیم روی پرینتر انتخاب‌شده ناموفق بود.')
  } finally {
    if (tempFile) {
      fs.unlink(tempFile).catch(() => {})
    }
  }
})

app.listen(PORT, HOST, () => {
  console.log(`[CarnoWash Print Agent] listening on http://${HOST}:${PORT}`)
  console.log('Endpoints: GET /health | GET /printers | POST /print')
})
