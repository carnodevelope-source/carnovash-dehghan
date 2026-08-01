import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import cors from 'cors'
import express from 'express'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import pdfToPrinter from 'pdf-to-printer'

const { getPrinters, getDefaultPrinter, print } = pdfToPrinter
const execFileAsync = promisify(execFile)

const PORT = Number(process.env.CARNOWASH_PRINT_AGENT_PORT || 17321)
const HOST = process.env.CARNOWASH_PRINT_AGENT_HOST || '127.0.0.1'

const app = express()

// HTTPS public sites (e.g. carnowash.ir) need Private Network Access headers
// to call this local HTTP agent from the browser.
app.use((req, res, next) => {
  const origin = req.headers.origin
  if (origin) res.setHeader('Access-Control-Allow-Origin', origin)
  else res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Vary', 'Origin')
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
  res.setHeader(
    'Access-Control-Allow-Headers',
    req.headers['access-control-request-headers'] || 'Content-Type, Accept'
  )
  res.setHeader('Access-Control-Allow-Private-Network', 'true')

  if (req.method === 'OPTIONS') {
    return res.status(204).end()
  }
  return next()
})

app.use(cors({ origin: true }))
app.use(express.json({ limit: '25mb' }))

const ok = (res, data = {}) => res.json({ ok: true, ...data })
const fail = (res, status, message) => res.status(status).json({ ok: false, message })

const normalizePrinterList = (items) => {
  const seen = new Set()
  return (Array.isArray(items) ? items : [])
    .map((item) => ({
      name: String(item?.name || item?.Name || item?.deviceId || '').trim(),
      isDefault: Boolean(item?.isDefault ?? item?.Default),
      workOffline: Boolean(item?.workOffline ?? item?.WorkOffline)
    }))
    .filter((item) => {
      if (!item.name || seen.has(item.name)) return false
      seen.add(item.name)
      return true
    })
    .sort((a, b) => Number(b.isDefault) - Number(a.isDefault) || a.name.localeCompare(b.name, 'fa'))
}

const listPrintersViaPowerShell = async () => {
  if (process.platform !== 'win32') return null
  const script = [
    "$ErrorActionPreference = 'Stop'",
    'Get-CimInstance -ClassName Win32_Printer |',
    '  Select-Object Name, Default, WorkOffline |',
    '  ConvertTo-Json -Compress'
  ].join(' ')

  const { stdout } = await execFileAsync(
    'powershell.exe',
    ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', script],
    { windowsHide: true, maxBuffer: 2 * 1024 * 1024 }
  )
  const raw = String(stdout || '').trim()
  if (!raw) return []
  const parsed = JSON.parse(raw)
  return normalizePrinterList(Array.isArray(parsed) ? parsed : [parsed])
}

const listPrintersViaPdfToPrinter = async () => {
  const [printers, defaultPrinter] = await Promise.all([
    getPrinters(),
    getDefaultPrinter().catch(() => null)
  ])
  const defaultName = String(defaultPrinter?.name || defaultPrinter?.deviceId || '').trim()
  return normalizePrinterList(
    (Array.isArray(printers) ? printers : []).map((item) => ({
      name: String(item?.name || item?.deviceId || '').trim(),
      isDefault: Boolean(
        item?.isDefault
        || (defaultName && (item?.name === defaultName || item?.deviceId === defaultName))
      )
    }))
  )
}

const listSystemPrinters = async () => {
  try {
    const viaPs = await listPrintersViaPowerShell()
    if (Array.isArray(viaPs) && viaPs.length) return viaPs
  } catch (error) {
    console.warn('PowerShell printer list failed, falling back:', error?.message || error)
  }
  return listPrintersViaPdfToPrinter()
}

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
    const printers = await listSystemPrinters()
    return ok(res, { printers })
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
