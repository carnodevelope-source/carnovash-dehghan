# سرویس نهایی پلاک و رنگ

این فولدر مستقل است و هیچ فایلی را از `ai` یا `ai_vehicle_agent` import نمی‌کند. قرارداد HTTP آن با سرویس قبلی سایت سازگار است و سه فیلد `color`، `color_confidence` و `color_reliable` را به پاسخ قبلی اضافه می‌کند.

## اجرای سایت (پیشنهادی)

```powershell
cd D:\Desktop\PRG\Cursor\carno\carvash\ai\final
$env:PLATE_AI_DEVICE="cuda"
python plate_http_service.py --host 127.0.0.1 --port 8765
```

یا از روت پروژه:

```powershell
.\scripts\run_dev_with_plate_ai.ps1
```

آدرس سایت بدون تغییر می‌ماند:

```text
PLATE_AI_SERVICE_URL=http://127.0.0.1:8765
```

مسیرها و payload قبلی بدون تغییرند:

- `GET /health`
- `POST /recognize`
- ورودی: `session_id`، `image_base64`، `timeout_sec` و `force_process`
- خروجی قبلی: `text`، `persian_text`، `confidence`، `bbox`، `stable` و ...
- خروجی جدید: `color`، `color_confidence`، `color_reliable` و `color_stable`

مدل‌ها فقط یک بار در شروع سرویس load و warm-up می‌شوند. فریم‌های تکراری از cache پاسخ می‌گیرند، OCR هر ۱۲ فریم و رنگ هر ۱۸ فریم refresh می‌شود و detector درخواست‌های همزمان را batch می‌کند.

## تست تک‌عکس

```powershell
python predict.py .\car1.jpg
```
