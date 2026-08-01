# CarnoWash Print Agent

ایجنت محلی ویندوز برای:
- خواندن لیست پرینترهای شناخته‌شده سیستم
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

## API

- `GET /health`
- `GET /printers`
- `POST /print` با بدنه JSON:
  - `printerName`
  - `pdfBase64`
  - `fileName` (اختیاری)

این سرویس فقط روی localhost گوش می‌دهد و برای چاپ بی‌صدا روی ویندوز به `pdf-to-printer` متکی است.
