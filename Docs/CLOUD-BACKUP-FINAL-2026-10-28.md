> به‌روزرسانی: دو مانع با مجوز بعدی رفع و نسخه منتشر شد. وضعیت جاری در [گزارش انتشار](CLOUD-BACKUP-PRODUCTION-2026-10-28.md) است؛ متن زیر تاریخچه پیش از انتشار است.

# گزارش نهایی بررسی Carvash — ۲۸ اکتبر ۲۰۲۶

وضعیت: **نیازمند اصلاح**. انتشار جدید و فعال‌سازی worker به علت موانع داده واقعی متوقف شد.
هیچ فایل، Volume، دیتابیس یا آرشیو عملیاتی حذف نشد و پروژه Carwasheman دست‌کاری نشد.

## وضعیت واقعی اولیه

- source-master: شاخه server، کامیت 2ed6f8b؛ ai/Dockerfile تغییرکرده و فایل‌های private/Compose ثبت‌نشده داشت. حفظ شدند.
- شاخه توسعه: feature/cloud-backup-incremental-10d در f88169d، همراه تغییرات و اسکریپت‌های ثبت‌نشده قبلی.
- Backend از قبل با carwash-backend:f88169d اجرا می‌شد؛ source-master نماینده دقیق کد runtime نبود.
- هر پنج کانتینر Production healthy بودند. worker دائمی cloud-backup وجود نداشت.
- cloud_storage برای tenantهای 3،11،12 فعال بود. اشتراک‌ها تغییر نکردند.
- /mnt/extra-storage روی /dev/sdb1، ext4، متصل و دارای حدود 434GiB فضای آزاد بود.

## اصلاحات این نوبت در شاخه توسعه

- Signalهای post_save در auth، vehicles، subscriptions، inventory، workers، payments، services، products، notifications اکنون raw fixture را بدون ایجاد event/SMS/cache side effect رد می‌کنند.
- archive.py: روشن‌سازی استفاده از DeserializedObject.save(using=using) که خود Model.save_base(raw=True) را فراخوانی می‌کند. تغییر نام متغیر قبلی به‌تنهایی اصلاح رفتار نبود.
- production_drill.py: زمان‌ها با لحظه دقیق و دقت میکروثانیه مقایسه می‌شوند؛ .000 و نبودن اعشار صفر، زمان متفاوت محسوب نمی‌شوند. هش سایر فیلدها و همه هویت‌ها همچنان دقیق بررسی می‌شود.
- snapshot.py و scheduled_chain.py: فایل رسانه‌ای مفقود به‌صورت missing_media ثبت می‌شود و نادیده گرفته نمی‌شود.
- test_restore_safety.py: آزمون حفظ تاریخ قدیمی، عدم ایجاد event/SMS/cache mutation و رد رسانه گم‌شده.
- docker-compose.cloud-backup-full-test.yml: افزودن آزمون‌های جدید به مجموعه کامل.
- تغییر tmpfs در incremental Compose و اسکریپت‌های انتشار از قبل وجود داشتند؛ روی Production اعمال نشدند.

## آزمایش‌های واقعی این نوبت

| آزمایش | نتیجه |
|---|---|
| مجموعه نهایی MySQL مستقل | 397 تست؛ 389 موفق، 8 Skip، بدون شکست؛ 241.182 ثانیه |
| قطع واقعی tmpfs خصوصی، lazy detach، remount RO، device اشتباه | 2 آزمون جداگانه موفق؛ دیسک واقعی سرور جدا نشد |
| Full و سه Incremental پس از افزودن/ویرایش/حذف داده و رسانه | بازیابی واقعی ORM و bytes در دیتابیس‌های موقت موفق |
| رمزنگاری، دستکاری/ناقص بودن فایل و فقدان حلقه زنجیره | در مجموعه نهایی موفق؛ فایل نامعتبر پذیرفته نشد |
| قفل هم‌زمانی، SIGKILL worker، retry، کمبود فضا و خطای persistence | در مجموعه نهایی موفق |
| چرخه 40روزه و حفظ نقاط بازیابی پنجره 30روزه | در مجموعه نهایی موفق |
| مجموعه غیرفعال | در مجموعه نهایی بدون ساخت فایل یا BackupRun؛ اشتراک Production برای آزمون تغییر نکرد |
| makemigrations --check --dry-run | No changes detected؛ هیچ Migration جدیدی لازم نیست |
| بررسی Migrationهای Production | هیچ Migration معوقی وجود نداشت؛ این نوبت Migration عملیاتی اجرا نشد |
| preflight runtime، ancestry، policy و inode رسانه | موفق؛ این موفقیت موانع داده را نادیده نمی‌گیرد |

### بازیابی آرشیو واقعی Production، فقط در MySQL ایزوله

آخرین اجرای کد اصلاح‌شده: restore-drill-20261028T085620Z.log، Exit 0.
شبکه internal، بدون پورت میزبان، بدون اتصال یا credential دیتابیس Production.

- میلان tenant=3، run=4: **64350 رکورد در 33 مدل**؛ تطبیق همه هویت‌ها، فیلدها، روابط و زمان‌های موجود در fixture؛ فقط tenant=3 در recovery.
- tenant=11، run=5: **15191 رکورد در 26 مدل**؛ همان کنترل‌ها موفق.
- هر دو آرشیو Full و دارای صفر فایل رسانه‌ای‌اند؛ این آزمایش اثبات بازیابی رسانه Production نیست. رسانه با داده آزمایشی واقعی در آزمون زنجیره بررسی شد.
- Incremental از داده زنده Production هنوز ساخته نشده است؛ موفقیت Incremental مربوط به دیتابیس مستقل و تغییرات کنترل‌شده آزمایشی است.

## دو مانع واقعی باقی‌مانده

1. tenant=12 فعال و غیرنمونه است. SupportTicketAttachment با pk=5 به فایل مفقود اشاره دارد. بررسی فعلی collect به FileNotFoundError رسید؛ کد جدید آن را missing_media می‌کند. جست‌وجوی قبلی در منابع Carvash نیز candidate نداشت. فایل اصلی باید از منبع معتبر بازیابی شود؛ حذف مرجع یا ساخت تصویر جایگزین، رفع سالم این مشکل نیست.
2. tenant=3 یک آرشیو قدیمی بدون موفقیت ثبت‌شده دارد:
   20261027T104429-798af5968dff42c3a6f39e8b7128380e.cvb
   ممیزی تازه با کلید تنظیم‌شده: authentication_failed_or_wrong_key. علت قطعی میان خرابی و کلید نامتناسب معلوم نیست. فایل حفظ شد. وجود این آرشیو unmanaged، retention عملیاتی میلان را fail-closed متوقف می‌کند. کلید اصلی/نسخه سالم یا سیاست حفاظت استثنایی بازبینی‌شده لازم است.

## بکاپ‌ها و Rollback

- Full معتبر میلان: /mnt/extra-storage/cloud-backups/tenant-3/20261027T165251-a0efecd3d8a54c26a4b65e749047efee.cvb
  اندازه 4938488 bytes؛ رمزگشایی، احراز اصالت و بازیابی واقعی موفق.
- بکاپ مستقل تازه از دیتابیس اصلی و رسانه در:
  /mnt/extra-storage/cloud-backups/deployment-rollback/20261028T085352Z/
  database.sql.gz.aesgcm و media.tar.gz.aesgcm.
  SQL برابر 97704535 bytes و tar برابر 71680 bytes پیش از فشرده‌سازی؛ هر دو با رمزگشایی کامل و SHA256 تطبیق داده شدند. SQL مستقل به دیتابیس وارد نشد؛ این بررسی سلامت بایت‌هاست.
- manifest خصوصی: /mnt/extra-storage/carwash-rehearsal-artifacts/cloud-backup-checkpoint-20261028T085352Z.json
- فایل rollback ایمیج قبلی و تنظیمات محفوظ از انتشار قبلی وجود دارد؛ چون این نوبت انتشار نشد، rollback اجرا نشد.

## انتشار و زمان‌بندی

هیچ ایمیج Production بازسازی/تعویض نشد؛ اصلاحات این نوبت فقط در شاخه توسعه هستند.
worker فعال نشد. هیچ Cron کاربر یا timer با نام Carvash backup یافت نشد؛ worker دائمی نیز وجود ندارد.
کد برنامه‌ریزی Asia/Tehran، Full هر 10 روز و Incremental بین آن‌ها و retention 30روزه در تست‌ها موفق است.
موعد تقویمی بعدی 29 اکتبر 2026 ساعت 00:00 تهران (28 اکتبر 20:30 UTC) است؛ **اجرای عملیاتی برای آن فعال نیست**.
اجرای نیمه‌شب، کارایی تحت بار واقعی و Production Incremental بعد از رفع موانع و انتشار هنوز تأیید نشده‌اند.

گزارش‌های خصوصی آزمون در /mnt/extra-storage/carwash-rehearsal-artifacts/cloud-backup-release-f88169d/ حفظ شدند.

## کنترل نهایی

- آزمون واقعی Production برای tenant=20 فاقد cloud_storage فعال: execute_tenant مقدار None برگرداند؛ شمار BackupRun قبل و بعد صفر بود.
- هر پنج کانتینر Production در بررسی پایانی healthy و running بودند؛ / و /api/health/ روی پورت 18086 پاسخ 200 دادند.
- دو کانتینر دیتابیس موقت تست پس از پایان آزمون متوقف شدند؛ هیچ کانتینر Production متوقف نشد.
