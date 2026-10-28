# گزارش انتشار نهایی بکاپ Carvash — ۲۸ اکتبر ۲۰۲۶

**وضعیت: منتشرشده با موارد در انتظار تأیید**

انتشار و آزمون‌های ضروری موفق شدند. تنها تأیید زمان‌دار باقی‌مانده، اجرای واقعی نیمه‌شب است.
این گزارش جایگزین وضعیت عملیاتی گزارش پیشین CLOUD-BACKUP-FINAL-2026-10-28.md است؛ گزارش پیشین تاریخچه بررسی قبل از اجازه پاک‌سازی را نگه می‌دارد.

## حذف دقیق و قابل بازگشت موارد مجاز

- پیوست SupportTicketAttachment با pk=5 متعلق به tenant=12 بود؛ تاریخ 6 اوت 2026، تیکت بسته‌شده، فایل مفقود و بدون reverse dependency. فقط همان یک رکورد حذف شد؛ خود تیکت حفظ شد. مرجع دیگری از کاربران حذف نشد.
- قبل از حذف، بکاپ SQL/رسانه مستقل و نسخه رمزنگاری‌شده JSON همان رکورد ساخته و با رمزگشایی/هش بررسی شد.
- آرشیو ثبت‌نشده میلان با نام 20261027T104429-798af5968dff42c3a6f39e8b7128380e.cvb هیچ عضو تاریخچه یا زنجیره معتبر نبود. زنجیره سالم قبل از حذف از مسیر فعال تأیید شد.
- بایت‌های آرشیو نامعتبر در نسخه محافظت‌شده با SHA256 یکسان حفظ و سپس فقط فایل مسیر فعال unlink شد. فایل نامعتبر تعمیرشده یا قابل رمزگشایی اعلام نشده است.
- مسیر برگشت: /mnt/extra-storage/cloud-backups/deployment-rollback/approved-cleanup-20261028T090542Z/
  شامل attachment-5.json.aesgcm، legacy-original.cvb.protected و production-config.tar.aesgcm.
- journal خصوصی: /mnt/extra-storage/carwash-rehearsal-artifacts/approved-cleanup-20261028T090542Z.json

## اصلاحات و فایل‌ها

کد برنامه در کامیت e11b825 و گزارش قبلی در d17317e ثبت شد؛ Backend و worker با carwash-backend:d17317e اجرا می‌شوند.
فایل‌های Backend این ایمیج همان فایل‌های backend در شاخه نهایی‌اند؛ کامیت‌های بعدی ابزار انتشار و گزارش را اضافه می‌کنند.

- backend/apps/cloud_backup/archive.py: فراخوانی DeserializedObject.save(using=using) با توضیح صحیح raw=True داخلی؛ حفظ زمان‌های آرشیو.
- backend/apps/cloud_backup/snapshot.py و scheduled_chain.py: missing_media به‌صورت روشن و بدون افشای نام فایل/داده ثبت می‌شود؛ رسانه گم‌شده نادیده گرفته نمی‌شود.
- backend/apps/cloud_backup/production_drill.py و test_restore_safety.py: مقایسه دقیق زمان‌ها مستقل از اعشار صفر و آزمون عدم side effect بازیابی.
- signals.py در auth، vehicles، subscriptions، inventory، workers، payments، services، products، notifications: raw fixture هیچ رویداد، پیامک یا تغییر کش زنده ایجاد نمی‌کند.
- docker-compose.cloud-backup-full-test.yml: آزمون‌های جدید؛ docker-compose.cloud-backup-incremental.yml: tmpfs محدود /tmp.
- scripts/remove-approved-backup-blockers.py: پاک‌سازی دقیق همین موارد با پیش‌شرط، نسخه رمزنگاری‌شده، کنترل وابستگی و journal.
- scripts/release-cloud-backup-backend.py: حفظ محیط/رسانه، Canary، انتشار بدون بازسازی وابستگی‌ها و rollback ایمیج.
- scripts/prepare-cloud-backup-runtime.py: پیکربندی خصوصی worker از runtime واقعی با رسانه RO و create_host_path=false.
- scripts/run-approved-cloud-restore-drill.py: image/runtime صریح و بازیابی فقط روی شبکه internal خصوصی.

## آزمون‌های پیش از انتشار

- ایمیج جدید فقط از فایل‌های tracked و پایه محلی f88169d، بدون شبکه و بدون دریافت dependency تازه ساخته شد.
- روی خود ایمیج d17317e، بدون bind کد میزبان: 397 تست MySQL، 389 موفق و 8 Skip، بدون شکست؛ 244.608 ثانیه.
- مجموعه شامل Full، سه Incremental بعد از افزودن/ویرایش/حذف داده و رسانه، بازیابی ORM و bytes، خرابی/قطع فایل، زنجیره ناقص، جداسازی tenant، قفل، SIGKILL worker، retry، کمبود فضا و چرخه 40روزه retention بود.
- دو آزمون mount/unmount، lazy detach، remount RO و device اشتباه در کانتینر خصوصی قبلاً در همین جلسه موفق شدند؛ دیسک Production جدا نشد.
- makemigrations --check --dry-run بدون تغییر؛ Migration plan عملیاتی خالی بود و Migration جدیدی روی Production لازم نشد.
- preflight ancestry، schema، ذخیره‌ساز immutable و هویت inode رسانه موفق بود.

## بکاپ مستقل و مسیر بازگشت انتشار

قبل از انتشار، SQL و رسانه در این مسیر ساخته و با رمزگشایی کامل و SHA256 تأیید شدند:
/mnt/extra-storage/cloud-backups/deployment-rollback/20261028T091005Z/

SQL پیش از فشرده‌سازی 97760874 bytes و tar رسانه 71680 bytes بود. این مرحله صحت بایت‌های بکاپ مستقل را بررسی کرد؛ SQL کامل به دیتابیس وارد نشد. بازیابی tenant واقعی جداگانه در MySQL آزمایش شد.
تنظیمات حساس، Docker inspect، Git state و تغییرات محلی نیز داخل production-config.tar.aesgcm حفظ شدند؛ کلید و رمز در Git یا گزارش چاپ نشدند.

rollback عملیاتی آماده است:
/mnt/extra-storage/carwash-rehearsal-artifacts/cloud-backup-release-d17317e/backend-rollback.private.yml
این فایل ایمیج f88169d و محیط/رسانه قبلی را حفظ می‌کند. rollback لازم نشد؛ هیچ restore عملیاتی اجرا نشد.

## انتشار

- source-master از 2ed6f8b به نسخه تأییدشده fast-forward شد. هش فایل‌های private، ai/Dockerfile و فایل‌های محلی پیش و پس از انتقال برابر بود.
- Canary جدید ابتدا سالم شد؛ Frontend موقتاً به آن رفت، Backend بدون بازسازی DB/Redis/Frontend تعویض شد و مسیر اصلی برگشت.
- Backend اکنون d17317e است. Canaryهای موقت و DBهای موقت تست پس از اتمام متوقف شدند؛ هیچ Volume عملیاتی حذف نشد.
- هیچ‌یک از فایل‌ها، کانتینرها یا دیتابیس‌های پروژه Carwasheman دست‌کاری نشد.

## بکاپ واقعی Production پس از انتشار

| tenant | Run | نوع | bytes | بکاپ | retention |
|---|---|---|---:|---|---|
| 3، میلان | 7 | Incremental، پایه 4 | 40877 | success | success |
| 11 | 8 | Incremental، پایه 5 | 2039 | success | success |
| 12 | 9 | Full | 13581 | success | success |

مسیرها:
- /mnt/extra-storage/cloud-backups/tenant-3/20261028T091319-b050620c8fff4ca09b1ce466aebd5df7.delta.cvb
- /mnt/extra-storage/cloud-backups/tenant-11/20261028T091455-3754e6da7ce54d948e661e4a9d480641.delta.cvb
- /mnt/extra-storage/cloud-backups/tenant-12/20261028T091511-fdc2e04c3ea84e36a0be6d72806b829f.cvb

پایه معتبر میلان حفظ شد:
/mnt/extra-storage/cloud-backups/tenant-3/20261027T165251-a0efecd3d8a54c26a4b65e749047efee.cvb

تمام فایل‌های زنجیره از نظر اندازه، SHA256، مالک UID و مجوز 0600 و رمزگشایی/احراز اصالت بررسی شدند.
retention پس از بازسازی و تأیید زنجیره‌ها موفق شد؛ طرح حذف هر سه tenant خالی بود و هیچ بکاپ معتبر منقضی‌شده واقعی در این اجرا حذف نشد.
خطاهای تاریخی BackupRunهای 1،2،3،6 برای audit باقی ماندند؛ اجرای جدید ناموفق وجود ندارد.

## بازیابی واقعی پس از انتشار

سه آرشیو/زنجیره تازه از Production فقط در MySQL روی شبکه internal بدون اتصال یا credential دیتابیس اصلی بازیابی شدند:

| tenant | Full + Incremental | رکورد | مدل | تطبیق کامل و جداسازی |
|---|---|---:|---:|---|
| 3 | Full پایه + 1 Incremental | 64718 | 33 | موفق |
| 11 | Full پایه + 1 Incremental | 15192 | 26 | موفق |
| 12 | Full | 123 | 31 | موفق |

تمام هویت‌ها، فیلدها، روابط و زمان‌های fixture با رکوردهای بازیابی مقایسه شدند. تغییرات واقعی میلان از 64350 رکورد پایه به 64718 رکورد در زنجیره افزایشی بازیابی شد.
این سه زنجیره در محدوده snapshot خود صفر فایل رسانه‌ای دارند؛ بازیابی تصاویر Production از این آرشیوها ادعا نمی‌شود. پوشش رسانه و تغییر/حذف فایل در آزمون‌های مستقل با فایل واقعی بررسی شد.

## فعال‌سازی و آزمون زمان‌بند

- کار اصلی: run_cloud_backup_chains --execute --loop --retention؛ زمان‌بند داخل worker مستقل Django است، نه Cron یا Celery.
- کانتینر دائمی carwash-cloud-backup-1 با restart=unless-stopped و healthcheck فعال و سالم است.
- برنامه ساعت 00:00 Asia/Tehran را محاسبه می‌کند، نوبت ازدست‌رفته را پس از راه‌اندازی جبران و هویت روز/موفقیت را در DB نگه می‌دارد.
- Full هر 10 روز و Incremental بین آن‌ها؛ retention پنجره 30روزه با حفظ کل زنجیره و حداقل پایه‌های لازم.
- اجرای کنترل‌شده اول بکاپ‌های 7،8،9 را ساخت؛ اجرای مجدد همان چرخه هیچ رکوردی اضافه نکرد. پس از شروع worker دائمی نیز شمار رکوردها 9 ماند.
- tenant=20 فاقد cloud_storage فعال در Production آزموده شد: نتیجه None، صفر بکاپ جدید. اشتراک هیچ مجموعه‌ای تغییر نکرد.
- فقط tenantهای دارای cloud_storage.is_active=true انتخاب می‌شوند؛ اکنون 3،11،12.
- موعد بعدی: **29 اکتبر 2026 ساعت 00:00 تهران**، معادل 28 اکتبر 20:30 UTC.
- Full تقویمی بعدی میلان و 11: 6 نوامبر؛ tenant=12: 7 نوامبر، مشروط به سالم بودن زنجیره که در خرابی Full زودتر ساخته می‌شود.
- **اجرای واقعی نیمه‌شب در انتظار تأیید است**؛ اجرای کنترل‌شده جای آن اعلام نشده است.

## پایداری و سلامت نهایی

- محدودیت worker: 0.5 CPU، RAM و memswap برابر 3GiB، staging RAM برابر 1GiB، swap.max=0، فایل‌سیستم container فقط‌خواندنی و cap_drop=ALL.
- رسانه دقیقاً همان bind زنده Backend و فقط‌خواندنی است. ریشه دیسک فقط‌خواندنی و تنها پوشه cloud-backups قابل نوشتن است.
- سقف 100هزار ردیف و JSON برابر 256MiB، field برابر 1MiB و 50هزار فایل؛ شکست ظرفیت به‌صورت امن ثبت می‌شود، نه افزایش نامحدود مصرف.
- /mnt/extra-storage روی ext4 دیسک ثانویه متصل است. mount/device، مجوزها و حداقل فضای آزاد کنترل می‌شوند.
- Backend، Frontend، MySQL، Redis، Plate AI و worker همگی running و healthy، بدون restart غیرمنتظره‌اند.
- سایت و API سلامت در پورت 18086 پاسخ 200 دادند؛ حین بکاپ نیز 200 بودند. نمونه‌های API در پایان حدود 2.8 تا 3.0ms بودند؛ این بررسی سلامت سبک است، نه آزمون بار کامل.
- worker خطای چرخه ثبت نکرده و هیچ BackupRun در وضعیت running باقی نمانده است.
- قطع برق یا جداکردن فیزیکی دیسک Production آزمایش نشد؛ این رفتارها در Mount خصوصی و آزمون فرآیند مستقل بررسی شدند.

## شواهد محفوظ

/mnt/extra-storage/carwash-rehearsal-artifacts/cloud-backup-release-d17317e/
- release-state.json و فایل‌های release/rollback خصوصی
- worker-runtime.private.json
- production-backup-receipts.json
- production-chain-restore-20261028.log
- scheduler-controlled-check.json
- final-production-health.json

لاگ آزمون 397تایی ایمیج در cloud-backup-release-f88169d/image-d17317e-final-tests.log باقی است.

**منتشرشده با موارد در انتظار تأیید** — تنها تأیید زمان‌دار باز، اجرای واقعی نیمه‌شب است.
