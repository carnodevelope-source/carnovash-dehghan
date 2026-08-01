# CarnoWash Print Agent

ایجنت محلی ویندوز برای:
- خواندن لیست پرینترهای شناخته‌شده سیستم (مثل همان‌هایی که در Ctrl+P دیده می‌شوند)
- چاپ مستقیم فیش/فاکتور روی پرینتر انتخاب‌شده بدون دیالوگ مرورگر

## اجرا

روی سیستم کارواش:

```bat
tools\print-agent\start-print-agent.bat
```

یا:

```bash
cd tools/print-agent
npm install
npm start
```

آدرس پیش‌فرض: `http://127.0.0.1:17321`

این پنجره را باز بگذارید. در تنظیمات پنل، «بروزرسانی لیست» را بزنید تا پرینترهای ویندوز ظاهر شوند.

اگر سایت روی HTTPS باز است، ایجنت هدر Private Network Access را برمی‌گرداند تا مرورگر اجازه دسترسی به localhost را بدهد.

## API

- `GET /health`
- `GET /printers`
- `POST /print` با بدنه JSON:
  - `printerName`
  - `pdfBase64`
  - `fileName` (اختیاری)

لیست پرینترها اول از طریق PowerShell/`Win32_Printer` خوانده می‌شود و در صورت نیاز به `pdf-to-printer` برمی‌گردد.
