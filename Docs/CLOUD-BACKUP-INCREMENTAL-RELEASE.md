# وضعیت توسعه بکاپ افزایشی carvash — ۲۷ اکتبر ۲۰۲۶

فقط شاخه `feature/cloud-backup-incremental-10d` در مسیر
`/home/shivamouj/carvash-releases/cloud-backup-incremental-work` تغییر کرده است.
هیچ Push، Deploy، اجرای migration عملیاتی، فعال‌سازی زمان‌بند یا حذف بکاپ واقعی انجام نشده است.

## تغییرات

- قفل هر tenant اکنون برنامه‌ریزی، ایجاد فایل و ثبت نهایی رکورد را پوشش می‌دهد.
- پیش از انتشار اتمیک، نام آرشیو در رکورد running ثبت می‌شود؛ فایل منتشرشده در خطای DB گم‌نام نیست.
- رکوردهای اجرای قطع‌شده زیر قفل failed می‌شوند؛ فایل ناقص موفق محسوب نمی‌شود.
- `scheduled_for` روز تهران را مستقل از زمان پایان کار ذخیره می‌کند (migration 0003).
- زمان‌بند opt-in: `run_cloud_backup_chains` پیش‌فرض dry run است؛ `--execute --loop`
  در شروع، نوبت عقب‌افتاده را بررسی می‌کند و در نیمه‌شب Asia/Tehran بیدار می‌شود.
  تصمیم روز و backoff در DB پایدار است؛ تکرار روزانه و اجرای هم‌زمان رد می‌شوند.
- زنجیره با اندازه، SHA256، مجوز 0600، مالکیت و بازیابی کامل بررسی می‌شود.
  پایه گم‌شده یا خراب موجب Full جدید می‌شود؛ Full قدیمی خودکار prune نمی‌شود.
- تغییر هویت/محتوای رسانه نسبت به collect باعث شکست می‌شود؛ ترتیب لیست fixture
  با digest استاندارد مقایسه می‌شود، نه ترتیب وابسته به شناسه رشته‌ای.
- staging بازیابی فقط روی tmpfs در `/dev/shm` با مجوز 0700 است؛ پس از خطا پاک می‌شود
  و بقایای worker کشته‌شده در اجرای بعدی همان tenant، زیر قفل، جمع می‌شوند.
- CRC و پایان gzip افزایشی نیز بررسی می‌شود. مرجع فایل گم‌شده در fixture بازیابی رد می‌شود.
- خواندن کلید با FD بدون دنبال‌کردن symlink، بررسی فایل معمولی، hardlink و مجوز محدود انجام می‌شود.
- retention واقعی: `retain_cloud_backup_chains --tenant ID` فقط گزارش و token می‌دهد.
  حذف نیازمند `--execute --reviewed-token TOKEN` و ثابت‌ماندن همان طرح است.
  تمام زنجیره‌ها پیش از حذف بازیابی می‌شوند؛ حذف از آخرین delta به سمت پایه انجام می‌شود.
  وضعیت deleting قبل از unlink پایدار است و قطع حذف قابل ادامه است.
  فایل ناشناخته، خرابی، زنجیره مبهم یا قطع دیسک حذف را متوقف می‌کند.
- Compose آزمون مستقل با MySQL 8.4.11، شبکه internal، DB روی tmpfs، بدون پورت میزبان،
  بدون شبکه/Volume/Secret عملیاتی و محدودیت CPU/RAM اضافه شده است.
- override افزایشی فقط یک فایل آماده‌سازی است و اعمال نشده است.

## جلوگیری از Downgrade

ایمیج backend در حال اجرای سرور `carwash-backend:3e6f2bc` است؛ مسیر source-master
روی `2ed6f8b` بود و معرف دقیق نسخه اجراشده نیست. شاخه بکاپ با 3e6f2bc واگرا بود.
کامیت `3e6f2bc` در شاخه توسعه ادغام شد؛ حفاظت tenant، migrationها و آزمون‌های آن حفظ شدند.
هیچ فایل عملیاتی برای این ادغام تغییر نکرد.
در انتشار آینده باید ancestry نسخه اجراشده دوباره بررسی شود؛ این بررسی جایگزین تأیید انتشار نیست.

## آزمایش‌های انجام‌شده

- قبل از ادغام: MySQL مستقل ۷۵/۷۵ موفق؛ SQLite امنیتی ۷۷ اجرا، ۷۶ موفق و ۱ Skip مخصوص MySQL.
- پس از ادغام: MySQL مستقل ۸۵/۸۵ موفق، بدون Skip.
- بازیابی واقعی در DB recovery مستقل: افزودن/ویرایش/حذف ردیف، افزودن/ویرایش/حذف رسانه،
  سه delta متوالی، مقایسه تمام ردیف‌های fixture با ORM، رد داده tenant دیگر.
- شبیه‌سازی ۴۰ روز: Full در روزهای ۰،۱۰،۲۰،۳۰،۴۰؛ حفظ و بازیابی تک‌تک نقاط روزهای ۱۰ تا ۴۰
  بعد از حذف صرفاً داده آزمایشی زنجیره منقضی‌شده.
- خرابی پایه، فقدان پایه، تغییر رسانه، رقابت flock، خطای DB پیش/پس از انتشار، قطع worker،
  قطع حذف، خطای mount و تغییر طرح حذف آزمایش شدند.
- `makemigrations --check --dry-run`: بدون تغییر تشخیص‌داده‌شده.
- تقویم systemd برای `00:00:00 Asia/Tehran` فقط خواندنی بررسی شد؛ هیچ unit نصب یا فعال نشد.

## حدود اعتبار و دروازه انتشار

- قطع دیسک واقعی و قطع برق روی سرور انجام نشد. آزمون قطع mount در این اجرا تزریق خطاست؛
  آزمون خصوصی ext4 قدیمی جزو ادعای نتایج فعلی نیست.
- Snapshot دیتابیس از MVCC و رسانه از fingerprint+SHA256 استفاده می‌کند. این به‌معنای
  transaction اتمیک مشترک بین MySQL و فایل‌سیستم نیست. برای تضمین دقیق در حضور
  بازنویسی هم‌زمان فایل با همان نام، قرارداد immutable media یا هماهنگی نویسندگان برنامه
  باید در rehearsal بار هم‌زمان تأیید شود؛ قفل بکاپ، نویسندگان سایت را قفل نمی‌کند.
- برای جلوگیری از انتقال tmpfs به swap، worker به cgroup با memory.swap.max=0 یا میزبان بدون swap نیاز دارد؛
  در غیر این صورت fail-closed متوقف می‌شود. override با memswap_limit برابر mem_limit این محدودیت را
  فراهم می‌کند؛ مقدار 0 داخل کانتینر مستقل همین سرور بررسی شد. حافظه staging محدود است و کمبود جا شکست امن است.
- plaintext staging بعد از SIGKILL تا اجرای بعدی همان tenant می‌ماند؛ reboot آن را پاک می‌کند.
- آرشیو مربوط به failed/running با نام ثبت‌شده نگه داشته می‌شود؛ فایل مشکوک خودکار حذف نمی‌شود
  و در retention نیازمند بررسی اپراتور است.
- پاک‌سازی واقعی روی بکاپ‌های موجود فقط پس از dry run و بازبینی token مجاز است.
- در آینده، migration 0002 و 0003 و دسترسی حساب محدود باید فقط با تأیید انتشار اعمال شوند.
- پاک‌سازی قدیمی از writer حذف شد؛ حتی فراخوانی فرمان قدیمی نیز پایه زنجیره را حذف نمی‌کند.
  اجرای هم‌زمان worker قدیمی و جدید در انتشار مجاز نیست؛ فقط یک زمان‌بند باید فعال باشد.
- وضعیت انتشار: آماده بازبینی کد است؛ آمادگی قطعی Production تأیید نشده است.
  تضمین هم‌زمانی DB/Media و ۱۴ خطای موجود کل پروژه هنوز دروازه باز انتشار هستند.


## فایل‌های اصلی این مرحله

| فایل | مسئولیت |
|---|---|
| service.py، scheduled_chain.py، chain_service.py | قفل سراسری هر tenant، ثبت پایدار، انتشار و اجرای روزانه |
| chain_history.py، planner.py | اعتبار ترتیب/پایه/نام یکتا، بررسی واقعی سلامت و رد تاریخ آینده |
| snapshot.py | digest و هویت رسانه در Snapshot |
| archive.py، incremental_archive.py، chain_recovery.py | کلید امن، CRC و کنترل مرجع رسانه پس از بازیابی |
| staging.py | tmpfs خصوصی و منع Swap |
| models.py، migrations/0003_backuprun_scheduled_for.py | روز تقویمی اجرای زمان‌بندی |
| retention_service.py | preview، token و حذف وابستگی‌محور قابل ادامه |
| management/commands/run_cloud_backup_chains.py | worker صریح opt-in با backoff و بازیابی بعد از restart |
| management/commands/retain_cloud_backup_chains.py | بازبینی و اجرای retention |
| test_chain_lifecycle.py، test_incremental_archive.py، tests.py | آزمون‌های مرزی و integration |
| docker-compose.cloud-backup-incremental-test.yml | MySQL مستقل با منابع محدود |
| docker-compose.cloud-backup-incremental.yml | override آماده، اعمال‌نشده |

## شکست‌های قبلی مجموعه کامل پروژه

نسخه توسعه اولیه: ۳۷۶ تست، ۳۲۴ موفق، ۱۲ Failure، ۲ Error و ۳۸ Skip.
نسخه پایه دست‌نخورده 3e6f2bc: ۳۲۶ تست، ۲۷۴ موفق، همان ۱۲ Failure و همان ۲ Error و ۳۸ Skip.
نام و علت هر ۱۴ مورد در اجرای کامل یکسان بود؛ اجرای تکی ۳ مورد به ترتیب/وضعیت آزمون وابسته بود.
این فایل‌ها نسبت به 3e6f2bc هیچ تغییری ندارند. برای حفظ محدوده توسعه بکاپ، رفتار مالی/اشتراک/
پیامک/حضور کارکنان تغییر داده نشد. این شکست‌ها برای تأیید سلامت کل محصول همچنان باز هستند.

| بخش | مورد ناموفق |
|---|---|
| payments/test_wallet_api.py | trial_access_unlocks_core_and_options_until_expiry؛ نبود trial_active در اجرای کامل |
| realtime/tests.py | sync_and_sse_replay_are_tenant_scoped؛ پاسخ 402 به‌جای 200 |
| services/test_general_settings_read_only.py | get_returns_defaults_without_creating_or_normalizing_a_row؛ 402 |
| vehicles/test_plate_ai_parsing.py | lookup_resolves_letter_candidates_in_one_request؛ found=False |
| vehicles/test_vehicle_status_sms.py | release_checkout_counts_facility_discount_once_from_list_price؛ اختلاف تخفیف |
| workers/test_attendance_api.py | worker_list_frees_stale_holds_from_previous_days؛ active_jobs_count=1 |
| auth/test_wallet_card_deposit_tax.py | tax_percent_is_ten و two_million_deposit_credits_net_after_ten_percent_tax؛ مالیات صفر |
| notifications/test_sms_cost.py | existing_cancel_footer_is_not_duplicated و long_persian_style_message_matches_five_parts؛ کاراکترهای جهت متن |
| notifications/test_vehicle_sms_templates.py | assignment_sms_renders_customer_and_services و assignment_invoice_sms_shows_tariff_discount_and_final_total؛ قالب پلاک |
| vehicles/test_loyalty_fixed_sms.py | fixed_mode_writes_milestone_line و step_mode_keeps_generic_percent؛ query در SimpleTestCase |


## نتیجه نهایی این نوبت

| بررسی | تعداد | موفق | ناموفق | Skip |
|---|---:|---:|---:|---:|
| بکاپ روی MySQL مستقل، آخرین کد | ۸۹ | ۸۹ | ۰ | ۰ |
| مجموعه کامل پروژه روی SQLite، آخرین کد | ۳۸۰ | ۳۲۸ | ۱۴ | ۳۸ |
| مجموعه کامل نسخه پایه 3e6f2bc روی SQLite | ۳۲۶ | ۲۷۴ | ۱۴ | ۳۸ |

هر ۱۴ مورد ناموفق مجموعه کامل، نام و علت یکسان در نسخه پایه داشتند.
آزمون‌ها تغییر داده نشده‌اند تا این شکست‌ها پنهان شوند. ۵۴ آزمون اضافه نسبت به نسخه پایه موفق‌اند.

- Git diff --check موفق؛ تغییر بیرون از محدوده cloud_backup و Compose/Docs مرتبط نسبت به 3e6f2bc نیست.
- بررسی markerهای کلید خصوصی و توکن در فایل‌های تغییرکرده: صفر مورد؛ این یک اسکن کامل تاریخچه Git نیست.
- Compose پایه + fixture + تنظیمات بکاپ + override افزایشی با مقادیر ساختگی و بدون env واقعی معتبر شد.
- image آزمایشی `carvash-cloud-backup-review:90116c2` فقط از فایل‌های tracked و وابستگی‌های موجود ساخته شد؛
  Django check در کانتینر بدون شبکه و با فایل‌سیستم فقط‌خواندنی موفق بود. این image Deploy نشده است.
- backend عملیاتی در پایان همان `carwash-backend:3e6f2bc` با زمان شروع قبلی و پاسخ سایت HTTP 200 بود.
- کامیت‌های محلی این نوبت: `6ce97d4` (اجرای امن و retention)، `ef2e8c4` (ادغام نسخه عملیاتی)،
  `90116c2` (منع Swap، حذف pruning قدیمی و رد تاریخچه مبهم).
- هیچ Push، Deploy، فعال‌سازی زمان‌بند، حذف آرشیو واقعی یا تغییر دیتابیس عملیاتی انجام نشد.

مرحله بعد: rehearsal هم‌زمانی نویسندگان DB/Media در محیط مستقل و تعیین تکلیف خطاهای قبلی
مجموعه کامل؛ سپس بازبینی plan واقعی retention و اخذ تأیید صریح انتشار. برآورد باقی‌مانده
بخش بکاپ تا آمادگی قطعی انتشار حدود ۱۰ تا ۱۵ درصد است؛ رفع مشکلات سایر ماژول‌ها جداگانه است.
