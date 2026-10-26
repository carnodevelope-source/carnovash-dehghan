# گزارش اصلاح Cloud Backup

اصلاحات روی سورس محلی انجام شد. هیچ اتصال، migration، دیپلوی، بازیابی یا تغییر
مجوز روی سرور اصلی انجام نشد. آرشیوها و اطلاعات فعلی مشتریان جابه‌جا یا حذف
نشدند. تغییرات جدید هنوز Commit یا Push نشده‌اند.

## نتیجه بررسی و اصلاح

- Media از مسیر اشتباه bind به Volume موجود `carwash_carvash_media` تغییر کرد؛
  فقط‌خواندنی و external است و Volume خالی جایگزین ساخته نمی‌شود.
- ریشه هارد دوم فقط‌خواندنی است؛ تنها `cloud-backups` قابلیت نوشتن دارد.
  پوشه باید از قبل با مالک سرویس و مجوز 0700 آماده شده باشد؛ تغییر مالکیت کل
  هارد یا Media لازم نیست. کنترل mount از کنترل پوشه مقصد جدا شد.
- Directory FD برای ریشه و هر tenant، بازکردن بدون دنبال‌کردن symlink، کنترل
  مالکیت و مجوزها، قفل واقعی و کدهای خطای EIO/EROFS/ENOSPC اضافه یا تقویت شد.
- تمام مدل‌های فعلی طبقه‌بندی صریح دارند؛ مدل جدید بدون بازبینی وارد بکاپ
  نمی‌شود. ارتباطات tenant و فایل‌ها بررسی می‌شوند. تغییر فایل پس از Snapshot
  نیز از انتشار آرشیو جلوگیری می‌کند. خواندن JSON تصاویر سایر tenantها حذف شد.
- سقف ردیف/JSON/فایل و بررسی اندازه فیلد پیش از بارگیری، مصرف حافظه را محدود
  می‌کند. فاصله تلاش مجدد افزایشی است و زمان‌بندی دوباره داخل قفل کنترل می‌شود.
- آرشیو v2 شناسه کلید احراز‌شده و keyring اختیاری دارد؛ v1 قابل خواندن باقی
  مانده است. آزمون چرخش کلید، قطع آرشیو، دستکاری، trailer gzip و مسیر نامعتبر
  اضافه شد. در بکاپ فایل موقت plaintext ساخته نمی‌شود.
- بازیابی به alias مجاز و دیتابیس مجزا، پوشه جدید و تأیید صریح اپراتور محدود
  شد. محتوای رکوردهای بازیابی‌شده و فایل‌ها واقعاً مقایسه می‌شود.
- فرمان تولید SQL دسترسی‌های جدول‌به‌جدول هیچ Grant یا حسابی را اجرا/ایجاد
  نمی‌کند. حساب محدود در MySQL آزمایشی توانست بکاپ بگیرد؛ نوشتن در جدول اصلی،
  DELETE تاریخچه و DDL برای آن رد شد.
- build اختصاصی، نسخه‌های Python dependencies ثابت، preflight خواندنی میزبان،
  محیط Compose تست مستقل و راهنمای کامل آماده‌سازی/توقف/rollback تهیه شد.

## فایل‌های تغییرکرده و جدید

| فایل | تغییر |
| --- | --- |
| `backend/config/settings.py` | تنظیمات mount، مقصد، کلید، سقف منابع و recovery |
| `backend/apps/cloud_backup/service.py` | کنترل دیسک/مجوز، FD، قفل، backoff و خطا |
| `backend/apps/cloud_backup/snapshot.py` | طبقه‌بندی، سقف منابع، ایمنی و هویت فایل‌ها |
| `backend/apps/cloud_backup/archive.py` | v2/keyring، سازگاری v1، صحت و بازیابی امن |
| `backend/apps/cloud_backup/management/commands/run_cloud_backups.py` | اجرای زمان‌بندی با backoff |
| `backend/apps/cloud_backup/management/commands/recover_cloud_backup.py` | منبع ثابت، مقصد جدید و تأیید بازیابی |
| `backend/apps/cloud_backup/management/commands/cloud_backup_status.py` | وضعیت دیسک، قدیمی‌شدن موفقیت و نوبت اجرا |
| `backend/apps/cloud_backup/management/commands/check_cloud_backup.py` | preflight فقط‌خواندنی داخل سرویس |
| `backend/apps/cloud_backup/management/commands/cloud_backup_grants.py` | تولید SQL حداقل دسترسی بدون اجرا |
| `backend/apps/cloud_backup/tests.py` | تست Snapshot، رمزگذاری، بازیابی و مجوز MySQL |
| `backend/apps/cloud_backup/tests_linux.py` | شش تست واقعی ext4/UID/FD/flock در namespace موقت |
| `backend/apps/cloud_backup/test_settings.py` | allowlist دیتابیس بازیابی تست |
| `backend/apps/cloud_backup/test_settings_mysql.py` | تنظیمات MySQL کاملاً آزمایشی و opt-in |
| `backend/apps/cloud_backup/fixtures/server-compose.fixture.yml` | نمونه توپولوژی اعلام‌شده، فقط برای config تست |
| `backend/Dockerfile.cloud-backup` | build مستقل با base digest ثابت و کاربر محدود |
| `backend/cloud-backup-requirements.lock` | نسخه‌های آزموده‌شده وابستگی‌های Python |
| `docker-compose.cloud-backup.yml` | Volume واقعی، RW محدود و build مستقل |
| `docker-compose.cloud-backup-test.yml` | MySQL موقت و اجرای تست با UID 10001 و root فقط‌خواندنی |
| `scripts/cloud-backup-preflight.sh` | بررسی خواندنی UUID، دستگاه، مقصد و Volume روی میزبان |
| `Docs/CLOUD-BACKUP.md` | راهنمای میزبان، حساب محدود، کلید، دیپلوی و بازیابی |
| `Docs/CLOUD-BACKUP-REVIEW.md` | همین گزارش و فهرست فایل‌ها |

مدل و migration اولیه BackupRun تغییر نکردند. هیچ migration جدید یا تغییری
در قابلیت‌های دیگر پروژه ایجاد نشد.

## اعتبارسنجی انجام‌شده

| بررسی | موفق | ناموفق | صرف‌نظر |
| --- | ---: | ---: | ---: |
| SQLite / Windows، ۲۹ تست | ۲۸ | ۰ | ۱، تست مخصوص MySQL |
| MySQL 8.4، ۲۹ تست در Docker مستقل | ۲۹ | ۰ | ۰ |
| Linux/ext4 در namespace جدا، ۶ تست | ۶ | ۰ | ۰ |

تست MySQL نهایی با Dockerfile اختصاصی، وابستگی‌های ثابت، کاربر `10001:10001`،
root فقط‌خواندنی و دیتابیس tmpfs انجام شد؛ Exit Code صفر بود. تست محدودیت حساب
دیتابیس هم در همین مجموعه اجرا شد. تست Linux از loop imageهای تازه در `/tmp`
استفاده کرد؛ هارد واقعی Production در هیچ تستی استفاده نشد. خطاهای EIO و
ENOSPC در تست انتقال تزریق شده‌اند و معادل آزمون خرابی فیزیکی سخت‌افزار نیستند.

Build اختصاصی موفق بود. Django check بدون ایراد و بررسی migration بدون تغییر
بود. سینتکس شل preflight و config دو Compose هم معتبر بودند. در config با fixture:

- Volume مربوط به backend و بکاپ هر دو `carwash_carvash_media` شدند.
- Volume بکاپ external و اتصال Media فقط‌خواندنی بود.
- mount ریشه RO و فقط پوشه مقصد RW بود؛ ساخت خودکار host path غیرفعال ماند.
- وابستگی به `db` و شبکه مشترک `default` حفظ شد.

## محدودیت‌ها و کارهای مانده پیش از Production

۱. فایل واقعی `docker-compose.usb-local.yml` در سورس محلی موجود نیست؛ اعتبارسنجی
ترکیب دقیق سرور و بررسی شبکه/Volume باید روی همان سرور، خواندنی، تکرار شود.
fixture به‌هیچ‌وجه جایگزین فایل سرور نیست.

۲. حساب MySQL، پوشه خصوصی و Secret هنوز روی سرور آماده نشده‌اند. دستورهای
پیشنهادی در بخش‌های «Proposed HOST preparation»، «Proposed MySQL account
preparation» و «Proposed deployment and rollback» در
[راهنمای اجرا](CLOUD-BACKUP.md) جداگانه آمده‌اند؛ اجرا نشده‌اند.

۳. UUID در preflight میزبان کنترل می‌شود؛ runtime بدون دسترسی raw-device از
mountinfo و major:minor استفاده می‌کند. تغییر شماره دستگاه نیازمند بازبینی
دوباره UUID است، نه تغییر خودکار تنظیمات.

۴. حفظ هفت روز بر هدف ۱۴ نسخه مقدم است؛ هر شش ساعت بکاپ می‌تواند حدود ۲۸ نسخه
جوان ایجاد کند. سقف سخت ۱۴ با این دو شرط هم‌زمان سازگار نیست.

۵. مجموعه‌های بزرگ‌تر از سقف‌ها ایمن متوقف می‌شوند و به اندازه‌گیری حافظه یا
پیاده‌سازی streaming fixture گسترده‌تر نیاز دارند. همان سقف‌ها در تأیید آرشیو
قدیمی هم اعمال می‌شوند؛ برای بازیابی بزرگ در محیط جدا می‌توان آن‌ها را پس از
تأمین منابع افزایش داد. کشف تصاویر هنوز نام فایل‌ها را در درخت audit می‌گردد؛
برای آرشیو بسیار بزرگ، نمایه مالکیت فایل در آینده مفید است.

۶. صحت نسخه با drill عملیاتی همان نسخه متفاوت است؛ گزارش
`integrity_verified` ادعای restore drill برای تک‌تک آرشیوها نیست. تنظیم هشدار
عملیاتی، کنترل رشد دیسک و بکاپ خارج از سرور همچنان مسئولیت بهره‌برداری است.

سورس آماده بازبینی و Commit است. برای تغییرات این مرحله Push انجام نشده است.
