# پلی‌بوک رفع کندی سیستم‌های Django + Vue

تاریخ: ۳۱ مرداد ۱۴۰۵ (۲۱ آگوست ۲۰۲۶)  
منبع موردی: پروژه‌ی کارنوواش  
مخاطب: خودتان، وقتی روی پروژه‌ی دیگری همین علائم را می‌بینید

`PERFORMANCE.md` گزارش حادثه‌ی همین سایت است. این فایل **روش کار** است: چه چیزی را چک کنید، چرا خطرناک است، چطور عوضش کنید بدون اینکه دیتا یا الگوریتم خراب شود، چه تستی بنویسید، و چه نتیجه‌ای باید ببینید.

قانون طلایی: **اول ظرفیت و نشت را درست کنید، بعد کوئری، بعد رندر.** اگر سرور قفل است بهینه‌کردن ORM فایده ندارد. اگر ORM خطی رشد می‌کند، ریزکردن CSS فایده ندارد.

---

## ۱. چطور از این سند روی پروژه‌ی دیگر استفاده کنید

1. علائم را با جدول بخش ۲ تطبیق دهید. معمولاً چند علت هم‌زمان‌اند.
2. برای هر علت، بخش ۳ را با grepهای همان لایه روی ریپوی جدید اجرا کنید.
3. قبل از تغییر محاسبه‌ای، **الگوریتم قدیمی را در تست به‌صورت مرجع نگه دارید** (بخش ۵).
4. هر تغییر را با سه قفل ببندید: تست بودجه، تست هم‌ارزی خروجی، و تست «GET ننویسد».
5. دیپلوی را با چک‌لیست بخش ۷ انجام دهید.

اگر پروژه‌ی جدید Django + DRF + Vue + axios + gunicorn + docker compose باشد، تقریباً همه‌ی الگوها مستقیم کپی می‌شوند. اگر استک فرق دارد، اصل را نگه دارید و ابزار را عوض کنید:

| اصل | معادل در استک دیگر |
|---|---|
| کارگر sync + استریم طولانی = قفل کل API | uvicorn تک‌ورکر، PHP-FPM با `pm.max_children` کم، Node تک‌ترد بدون cluster |
| N+1 سریالایزر | GraphQL resolver بدون dataloader، Laravel resource بدون `with()` |
| لیسنر بعد از `await` در `onMounted` | React `useEffect` async بدون cleanup، Angular `ngOnInit` با subscribe بعد از await |
| GET که می‌نویسد | serializer `create` داخل `to_representation`، cache warm در مسیر خواندن |
| لاگ داکر بدون سقف | journald بدون vacuum، nginx access log بدون rotate |

---

## ۲. علائم → علت محتمل

| علامت کاربر | علت محتمل | لایه‌ی اول جست‌وجو |
|---|---|---|
| لودینگ چند دقیقه تا نیم ساعت، بعد ناگهان جواب می‌آید | کارگر sync اشغال‌شده با SSE/WebSocket/long-poll؛ یا axios بدون timeout | gunicorn CMD، `EventSource`، nginx buffering |
| با ۲ تب سایت می‌خوابد، بقیه‌ی سایت‌های همین سرور سالم‌اند | تمام workerهای این سرویس اشغال شده‌اند، نه کل ماشین | تعداد اتصال زنده × نوع worker |
| هرچه داده بیشتر می‌شود لیست کندتر می‌شود | N+1 در serializer / نبود ایندکس tenant-first | `CaptureQueriesContext` روی داغ‌ترین GET |
| ذخیره کردن مشتری وفادار کندتر از مشتری جدید است | بازپخش تاریخچه با UPDATE به‌ازای هر ردیف | توابع `rebuild` / `sync` / `recalculate` |
| بعد از چند بار عوض کردن صفحه، تب خودش کند می‌شود و فقط با رفرش درست می‌شود | نشت listener/timer | `onMounted(async` + `addEventListener` بعد از await |
| وسط فرم، صفحه تار و قفل می‌شود بدون اینکه خود کاربر چیزی زده باشد | رفرش لایو با overlay سراسری | `trackLoading` روی handler رویداد |
| یک درخواست گیر می‌کند و کل UI تا ابد اسپینر می‌ماند | axios timeout=0 + overlay بدون watchdog | `axios.create` |
| دیسک پر می‌شود / کل VPS به مرور کند می‌شود | لاگ json-file بدون rotate | `docker inspect` → `LogConfig` |
| پیامک زمان‌بندی‌شده روی سرور نمی‌رود ولی در dev می‌رود | scheduler فقط زیر `runserver` | `sys.argv` داخل `ready()` |

در کارنوواش هر سه ردیف اول **با هم** بودند. رفع یکی کافی نبود.

---

## ۳. چک‌لیست کشف (grep و بازرسی)

روی پروژه‌ی جدید این‌ها را اجرا کنید. هر hit یعنی یک سناریوی مشخص در بخش ۴.

### ۳.۱ زیرساخت و gunicorn

```bash
# نوع worker را پیدا کنید. اگر --worker-class نیست، sync است.
rg -n "gunicorn|worker.class|worker_class|sync|gthread|gevent" Dockerfile docker-compose.yml gunicorn.conf.py

# استریم طولانی که worker را نگه می‌دارد
rg -n "StreamingHttpResponse|EventSource|text/event-stream|websocket" --type py --type vue --type js
```

چک دستی:

- تعداد worker × (اگر sync: ۱ درخواست، اگر gthread: threads) باید از «تعداد تب باز × اتصال SSE در هر تب» بزرگ‌تر باشد.
- اگر SSE دارید و nginx جلویش است، `proxy_buffering` برای آن path باید `off` باشد و `proxy_read_timeout` چند ده دقیقه.

### ۳.۲ ORM و سریالایزر

```bash
# N+1 کلاسیک
rg -n "SerializerMethodField|for .+ in .+:" apps --glob "*serializers*"
rg -n "select_related|prefetch_related" apps --glob "*views*"

# GET که می‌نویسد — خطرناک‌ترین کلاس باگ
rg -n "\.save\(|get_or_create|update_or_create|objects\.create" apps --glob "*serializers*"

# بازپخش تاریخچه
rg -n "for .+ in .+:\n.*\.save\(" --multiline
rg -n "rebuild_|recalculate_|sync_.+history" --type py

# ایندکس وارونه: ستون کم‌تنوع اول (status, type, is_active)
rg -n "models.Index\(fields=\['(status|type|is_active)" --type py
```

تست سریع در شِل Django:

```python
from django.test.utils import CaptureQueriesContext
from django.db import connection
with CaptureQueriesContext(connection) as q:
    # داغ‌ترین GET را صدا بزنید
    ...
print(len(q), [x['sql'][:80] for x in q])
```

اگر با ۲ برابر کردن تعداد ردیف، تعداد کوئری تقریباً ۲ برابر شد، N+1 دارید.

### ۳.۳ فرانت‌اند Vue

```bash
# لیسنر / SSE / setInterval بعد از await
rg -n "onMounted\(async" src --glob "*.vue"

# overlay روی رفرش پس‌زمینه
rg -n "LIVE_EVENT|addEventListener\(|setInterval\(|createLiveEventSource" src --glob "*.vue"

# axios بدون سقف
rg -n "axios.create|timeout:" src/services

# آبشار mount
rg -n "await load|await fetch|await authStore" src --glob "*.vue"

# Intl گران در حلقه
rg -n "new Intl.DateTimeFormat" src
```

قانون: در هر `onMounted(async () => {` باید `addEventListener` / `setInterval` / `createLiveEventSource` **قبل از اولین await** باشد، و جفت `remove`/`clear`/`close` در `onBeforeUnmount` وجود داشته باشد. تایمر debounce هم باید clear شود.

### ۳.۴ Docker و سشن

```bash
# لاگ بدون سقف
rg -n "logging:|max-size|json-file" docker-compose.yml

# سشن دیتابیسی بدون clearsessions
rg -n "SESSION_ENGINE|clearsessions|CONN_MAX_AGE" --type py --type sh

# scheduler که فقط در dev زنده است
rg -n "runserver|CARWASH_INTERNAL_SCHEDULER|start_internal_scheduler" --type py
```

---

## ۴. کاتالوگ تغییرات

هر مورد این ساختار را دارد: **هدف → سناریو → کار انجام‌شده → چرا دیتا خراب نمی‌شود → تست → نتیجه.**  
اعداد «قبل/بعد» مال کارنوواش است؛ در پروژه‌ی دیگر همان تست را با اعداد خودتان پر کنید.

### ۴.۱ کارگر gunicorn: sync → gthread

**هدف:** استریم طولانی یک پروسه‌ی کامل را اشغال نکند.  
**سناریو:** SSE / فایل بزرگ / گزارش طولانی + `gunicorn --workers N` بدون `--worker-class`. هر تب یک worker می‌خورد؛ با N تب API می‌میرد. gunicorn هر `timeout` ثانیه worker را می‌کشد؛ کاربر «نیم ساعت لودینگ بعد ناگهان جواب» می‌بیند.

**کار:**

```python
# gunicorn.conf.py
worker_class = 'gthread'
workers = 3          # تقریباً CPU+1
threads = 24         # ظرفیت اتصال، نه CPU
timeout = 120
```

CMD را از آرگومان خط فرمان به `-c gunicorn.conf.py` ببرید تا env قابل تنظیم بماند.

**دیتا:** هیچ. فقط مدل همزمانی عوض می‌شود.  
**چک:** چند تب هم‌زمان باز کنید؛ درخواست‌های عادی API نباید صف بکشند. لاگ `WORKER TIMEOUT` برای استریم زنده نباید بیاید.  
**نتیجه‌ی کارنوواش:** ۳ worker × ۲۴ thread = ۷۲ اتصال هم‌زمان به‌جای ۳.

اگر CPU-bound خالص دارید (بدون I/O طولانی) `gthread` انتخاب غلط است؛ آنجا `sync` با worker بیشتر یا `gevent` با کد سازگار معنی دارد. کارنوواش I/O-bound بود.

### ۴.۲ یک اتصال SSE برای کل تب + سقف سرور + Redis pub/sub

**هدف:** تعداد اتصال زنده را از «تعداد کامپوننت» به «تعداد تب» برسانید، و رویداد بین پروسه‌ها گم نشود.

**سناریو:** چند کامپوننت هرکدام `new EventSource(url)` می‌زنند. با ۳ worker sync، ۲ تب داشبورد کل ظرفیت را می‌خورد. رویداد در `set()` حافظه‌ی همان پروسه است، پس ۲/۳ کلاینت‌ها رویداد را نمی‌بینند.

**کار:**

1. کلاینت: `createLiveEventSource()` یک اتصال مشترک با ref-count برمی‌گرداند. تب مخفی بعد از ۲ دقیقه قطع می‌شود.
2. سرور: سقف `LIVE_MAX_SUBSCRIBERS`، ثبت subscriber داخل ژنراتور (نه قبل از شروع استریم)، `connections.close_all()` در شروع استریم.
3. nginx: `location = /api/live/events/` با `proxy_buffering off`.
4. Redis pub/sub بین workerها. اگر Redis نباشد، fallback محلی بدون exception.
5. `transaction.on_commit` قبل از publish تا کلاینت ردیف rollbackشده را نبیند.

**دیتا:** هیچ. ترتیب رویداد ممکن است چند میلی‌ثانیه جابه‌جا شود؛ محتوای رویداد همان است.  
**چک:** دو تب، دو worker؛ یک save در تب A باید در تب B دیده شود. قطع تب باید اتصال را ببندد (`ss -tn` یا لاگ).  
**نتیجه:** سرور دیگر با چند کاربر قفل نمی‌شود؛ رویدادها به همه‌ی پروسه‌ها می‌رسند.

### ۴.۳ بودجه‌ی کوئری برای داغ‌ترین لیست

**هدف:** تعداد کوئری لیست با تعداد ردیف رشد نکند، و GET ننویسد.

**سناریو:** `SerializerMethodField` برای هر ردیف `GeneralSettings` / پروفایل / tenant را جدا می‌خواند. DRF برای `many=True` **یک** نمونه‌ی سریالایزر می‌سازد؛ پس کش روی `self` برای مدت همان پاسخ معتبر است. `select_related` ناقص (`tenant` جا افتاده) N+1 پنهان می‌سازد.

**کار، به ترتیب امنی:**

1. `select_related` / `prefetch_related` در queryset ویو.
2. کش روی `self` برای تنظیمات مشترک کل لیست.
3. یک متد خروجی به‌جای سه `SerializerMethodField` که همان کار را تکرار می‌کنند.
4. اگر اسنپ‌شات منجمد دارید، پروفایل زنده را در GET لمس نکنید.
5. `EXISTS` یک‌باره برای مجموعه‌های خلوت (مثلاً پلاک مسدود).

**دیتا:** خروجی JSON باید با قبل یکی باشد؛ فقط منبع خواندن عوض می‌شود. نوشتن در GET را حذف کنید، چون قفل می‌گیرد و گزارش را خراب می‌کند.  
**تست الگو:** بخش ۵.۱.  
**نتیجه‌ی کارنوواش:** ۱۸.۶ کوئری/ردیف → ۰ رشد؛ ۱۹۵ کوئری برای ۱۰ ردیف → ۷؛ ۱۱ نوشتن در GET → ۰.

### ۴.۴ بازسازی تاریخچه: حلقه‌ی UPDATE → یک فرمول + یک SAVE

**هدف:** ذخیره‌ی رکورد مشتری پرتکرار با ذخیره‌ی مشتری جدید هم‌هزینه شود.

**سناریو:** `rebuild(profile)` صفر می‌کند، بعد برای هر رویداد تاریخی `apply_one()` می‌زند که `save()` دارد. هزینه‌اش O(تاریخچه) است و داخل تراکنش قفل نگه می‌دارد.

**کار:**

1. الگوریتم قدیمی را **عیناً** در تست به‌صورت تابع خالص پیاده کنید. این مرجع است، نه کد پروداکشن.
2. ثابت کنید وضعیت نهایی فقط به «تعداد / ترتیب رویدادها» وابسته است.
3. در پروداکشن یک SELECT سبک (`values_list` ستون لازم) + یک محاسبه + یک `save`.
4. مرز چرخه را تست کنید (مثلاً ۹، ۱۰، ۱۱ اگر چرخه ۱۰تایی است).

**دیتا:** اگر تست هم‌ارزی سبز باشد، خروجی پروفایل با قبل یکی است. اگر فرمول را حدس بزنید بدون تست مرجع، این خطرناک‌ترین تغییر کاتالوگ است.  
**تست الگو:** بخش ۵.۲.  
**نتیجه‌ی کارنوواش:** ۶۱ کوئری برای ۶۰ ویزیت → ۳؛ رشد خطی → ثابت.

### ۴.۵ گزارش بازه‌ای که کل تاریخچه را می‌خواند

**هدف:** هزینه‌ی «گزارش این ماه» با سن سیستم رشد نکند.

**سناریو:** برای ساعت کارکرد بین `start` و `end`، همه‌ی رویدادهای از روز اول خوانده می‌شود و در پایتون clip می‌شود. گزارش فروردین و اسفند یک حجم دارند.

**کار:** رویدادهای داخل بازه + **یک** ردیف بلافاصله قبل از `start` برای شیفت باز. `values_list` به‌جای مدل کامل.

**دیتا:** شیفتی که قبل از بازه شروع شده و داخل بازه ادامه دارد نباید صفر شود. بدون آن `LIMIT 1` خروجی عوض می‌شود.  
**چک:** کارگری که دیروز IN کرده و امروز OUT نکرده؛ گزارش «امروز» باید از نیمه‌شب تا الان دقیقه بشمارد، نه صفر.  
**نتیجه:** حجم خواندن = رویدادهای بازه، نه کل عمر کارگر.

### ۴.۶ نشت listener / timer در Vue

**هدف:** تب با استفاده‌ی عادی کند نشود.

**سناریو:**

```js
onMounted(async () => {
  await load()
  window.addEventListener(NAME, handler) // خیلی دیر
})
onBeforeUnmount(() => {
  window.removeEventListener(NAME, handler)
})
```

اگر کاربر وسط `load` صفحه را عوض کند، cleanup اول اجرا می‌شود (هنوز لیسنری نیست)، بعد لیسنر روی کامپوننت مرده ثبت می‌شود و تا رفرش تب می‌ماند. هر نشت یک refetch اضافه روی هر رویداد لایو است.

**کار:** ثبت لیسنر/تایمر/SSE **همزمان و قبل از await**. `isUnmounted` اگر بعد از await چیزی set می‌کنید. همه‌ی `setTimeout` دیبانس را در unmount پاک کنید.

**دیتا:** هیچ.  
**چک:** سریع بین دو صفحه که هردو لیسنر دارند جابه‌جا شوید؛ در DevTools → Event Listeners تعداد `carvash-live-event` (یا معادل) نباید رشد کند.  
**نتیجه:** کندی تدریجی مرورگر قطع می‌شود.

### ۴.۷ overlay سراسری فقط برای کار کاربر

**هدف:** رفرش پس‌زمینه UI را قفل نکند، و یک درخواست گیرکرده تا ابد قفل نکند.

**کار:**

- `axios.create({ timeout: 20000..45000 })`
- `meta.trackLoading === false` روی poll / live refresh / پیش‌بارگذاری
- watchdog روی شمارنده‌ی overlay (اگر response interceptor نیاید)
- debounce نمایش overlay (~300ms) تا درخواست سریع چشمک نزند
- درخواست لغوشده توست خطا ندهد
- فلگ معکوس را چک کنید: `trackLoading: !showLoading` تقریباً همیشه غلط است

**دیتا:** هیچ.  
**چک:** در صفحه‌ی فرم، از تب دیگر یک رکورد ذخیره کنید؛ فرم نباید تار شود. یک endpoint را عمداً آهسته کنید؛ overlay باید قبل از ۲ دقیقه آزاد شود.

### ۴.۸ آبشار `await` در mount → `Promise.all`

**هدف:** مدت اسپینر ورود به صفحه = کندترین درخواست، نه جمع آن‌ها.

**کار:** فقط درخواست‌هایی را موازی کنید که به خروجی هم وابسته نیستند. `fetchMe` را اگر گارد روتر همین حالا زده، تکرار نکنید. دو watcher که هردو با تعویض تب همان GET را می‌زنند یکی شوند.

**دیتا:** هیچ، مگر اینکه ترتیب پاسخ در UI فرض شده باشد (مثلاً id از درخواست اول برای دومی لازم باشد). آن‌ها را موازی نکنید.  
**نتیجه‌ی کارنوواش:** ورود HQ از ۴ round-trip پشت هم به یک round-trip رسید.

### ۴.۹ کوئری تکراری روی مسیر داغ هر درخواست

**هدف:** middleware و `/me/` برای کارهایی که لازم نیست هزینه ندهند.

**سناریو:** `/me/` دو بار `locked_features()` می‌زند چون map دسترسی دوباره همان را صدا می‌زند. middleware روی **هر** API قفل فیچر را چک می‌کند، در حالی که فقط دو prefix قابل قفل‌اند.

**کار:** نتیجه‌ی یک lookup را به توابع پایین‌دست پاس بدهید. در middleware اول path، بعد کوئری گران.

**دیتا:** اگر trial / قفل لایسنس را با همان توابع محاسبه می‌کنید، خروجی `/me/` نباید عوض شود. تست دسترسی منو را نگه دارید.  
**نتیجه:** ۳ کوئری ثابت از هر API معمولی حذف شد؛ `/me/` نصف شد.

### ۴.۱۰ ایندکس tenant-first

**هدف:** MySQL فیلتر اصلی را با index covering بزند، نه filesort روی status.

**سناریو:** ایندکس `(status, check_in_at)` برای کوئری `WHERE tenant_id=? ORDER BY check_in_at` تقریباً بی‌فایده است. `status` کم‌تنوع است.

**کار:** ایندکس را از روی کوئری واقعی بسازید، نه از روی «ستون‌هایی که زیاد فیلتر می‌شوند»:

```
WHERE tenant_id = ? AND check_in_at BETWEEN ? AND ?     → (tenant, check_in_at)
WHERE tenant_id = ? AND status = ? ORDER BY check_in_at  → (tenant, status, check_in_at)
WHERE tenant_id = ? AND plate_number IN (...)            → (tenant, plate_number)
```

مایگریشن روی جدول بزرگ ممکن است چند دقیقه طول بکشد؛ یک‌بار است و دیتا را عوض نمی‌کند.

**دیتا:** هیچ. فقط فایل ایندکس.  
**چک:** `EXPLAIN` قبل و بعد؛ `type` باید `ref`/`range` باشد نه `ALL`.

### ۴.۱۱ سشن، کانکشن DB، لاگ داکر

**هدف:** هزینه‌ی ثابت هر درخواست و رشد دیسک را ببندید.

| مورد | کار | دیتا |
|---|---|---|
| سشن | `cached_db` + Redis. دیتابیس منبع حقیقت می‌ماند | اگر Redis برود کاربر بیرون نمی‌افتد؛ فقط یک SELECT اضافه می‌شود |
| سشن منقضی | `clearsessions` در entrypoint دیپلوی | ردیف‌های مرده پاک می‌شوند، سشن فعال نه |
| کانکشن | `CONN_MAX_AGE=60` + `CONN_HEALTH_CHECKS` | هیچ؛ فقط هندشیک کمتر |
| لاگ داکر | `max-size: 10m`, `max-file: 3` روی همه‌ی سرویس‌ها | هیچ؛ لاگ قدیمی روی دیسک می‌ماند تا truncate دستی |

لاگ rotate از این به بعد اثر دارد. برای آزاد کردن فضای قبلی باید فایل json.log را truncate کنید.

### ۴.۱۲ زمان‌بند داخل‌پروسه‌ای زیر gunicorn

**هدف:** جاب‌های دوره‌ای روی پروداکشن واقعاً اجرا شوند، ولی نه N بار به‌ازای N worker.

**سناریو:** `if 'runserver' not in sys.argv: return`. در Docker هیچ‌وقت اجرا نمی‌شود. اگر فقط env را روشن کنید، هر worker یک ترد جدا می‌سازد و پیامک سه‌بار می‌رود.

**کار:** `SET key NX EX ttl` روی Redis برای انتخاب یک runner در هر چرخه. اگر Redis نباشد، اجرا شود (از دست رفتن جاب بدتر از تکرار گاه‌به‌گاه است). env را در compose پیش‌فرض روشن کنید.

**دیتا / رفتار:** این **تنها تغییر رفتاری واقعی کاتالوگ** است: کارهایی که قبلاً روی سرور نمی‌دویدند حالا می‌دوند. اگر جای دیگری cron برای همان جاب دارید، یکی را خاموش کنید.

### ۴.۱۳ رندر و باندل (اولویت پایین، بعد از بقیه)

- `Intl.DateTimeFormat` را یک بار در سطح ماژول بسازید.
- کلید sort را قبل از comparator محاسبه کنید؛ داخل comparator رشته‌ی بزرگ نسازید.
- `backdrop-filter` تمام‌صفحه را روی تبلت ضعیف بردارید.
- `manualChunks` برای `vue`/`vue-router`/`pinia`/`axios`.
- وابستگی پروداکشن استفاده‌نشده را حذف کنید.

**دیتا:** هیچ.  
**نتیجه‌ی کارنوواش:** چانک ورودی ۱۷۷KB → ۲۳KB کد اپ + ۱۵۴KB vendor قابل کش.

---

## ۵. الگوهای تست که باید در هر پروژه کپی شوند

بدون این سه تست، بهینه‌سازی محاسبه‌ای را merge نکنید.

### ۵.۱ بودجه‌ی کوئری لیست (رشد صفر + GET بدون نوشتن)

```python
def test_query_count_does_not_grow_with_row_count(self):
    self._create(5)
    small, _ = self._count_list_queries()
    self._create(25)
    large, rows = self._count_list_queries()
    self.assertEqual(rows, 30)
    self.assertLessEqual(large - small, 2)  # سقف کوچک، نه صفر سخت‌گیر اگر cache گرم شود

def test_list_get_does_not_write(self):
    self._create(10)
    with CaptureQueriesContext(connection) as q:
        self.client.get('/api/…/')
    writes = [x['sql'] for x in q if x['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))]
    self.assertEqual(writes, [])
```

اگر `large - small` با تعداد ردیف جدید تقریباً برابر شد، N+1 برگشته.

### ۵.۲ هم‌ارزی الگوریتم قدیمی و جدید

```python
def replay_old(events):
    # عیناً حلقه‌ی پروداکشن قبلی، بدون I/O
    ...

def test_matches_visit_by_visit_replay(self):
    for count in [0, 1, 2, cycle-1, cycle, cycle+1, 2*cycle-1, 2*cycle, 2*cycle+1]:
        events = self._make_events(count)
        new = rebuild_fast(events)
        old = replay_old(events)
        self.assertEqual(new, old)
```

مرز چرخه را از قلم نیندازید. در کارنوواش بدون ۹/۱۰/۱۱ تست سبزِ دروغین ممکن بود.

### ۵.۳ بودجه‌ی بازسازی (رشد صفر نسبت به تاریخچه)

```python
self._make_events(3)
with CaptureQueriesContext(connection) as short: rebuild(short_profile)
self._make_events(60)
with CaptureQueriesContext(connection) as long: rebuild(long_profile)
self.assertEqual(len(short), len(long))
self.assertLessEqual(len(long), 3)
```

### ۵.۴ تست دسترسی / منو اگر `/me/` را دست زدید

خروجی `menu_access` و `locked_feature_keys` را برای کاربر trial، کاربر قفل‌شده، و HQ جدا assert کنید. بهینه‌کردن lookup نباید permission را عوض کند.

### ۵.۵ تست‌های از قبل قرمز

قبل از شروع کار یک بار کل سوئیت را بگیرید و failهای موجود را ثبت کنید. در کارنوواش دو تست `SimpleTestCase` که به DB می‌زدند از قبل قرمز بودند؛ به این تغییرات ربط نداشتند. اگر ثبت نکنید، بعداً گمان می‌کنید خودتان شکسته‌اید.

---

## ۶. قوانینی که جلوی باگ دیتا را می‌گیرند

1. **GET نباید بنویسد.** همگام‌سازی پروفایل مال POST/وضعیت است، مال لیست نیست.
2. **فرمول جایگزین حلقه فقط با تست مرجع.** اگر نمی‌توانید الگوریتم قدیمی را در ۲۰ خط خالص بازپخش کنید، هنوز آماده‌ی بازنویسی نیستید.
3. **clip بازه باید شیفت باز را ببیند.** یک `LIMIT 1` قبل از start، نه حدس.
4. **موازی‌سازی فقط برای درخواست مستقل.** اگر B به A وابسته است، `Promise.all` نکنید.
5. **publish بعد از commit.** وگرنه UI ردیفی را نشان می‌دهد که rollback شده.
6. **cache روی `self` سریالایزر فقط برای مدت همان request.** روی `lru_cache` ماژول برای داده‌ی tenantدار نگذارید مگر کلید tenant داشته باشد.
7. **ایندکس دیتا را عوض نمی‌کند؛ rebuild تاریخچه ممکن است عوض کند.** اولی را آزادانه بزنید، دومی را با تست.
8. **روشن کردن scheduler رفتار محصول را عوض می‌کند.** این را در نوت دیپلوی بنویسید.
9. **fallback Redis باید بی‌صدا کار کند، نه exception در save.** save کاربر به خاطر pub/sub نباید بترکد.
10. **قبل از دیپلوی بکاپ.** این تغییرات migration دیتایی ندارند، ولی عادت درست است.

---

## ۷. چک‌لیست دیپلوی و صحت‌سنجی

```text
[ ] بکاپ دیتابیس
[ ] env: REDIS_URL, GUNICORN_WORKERS, GUNICORN_THREADS, DB_CONN_MAX_AGE,
        LIVE_MAX_SUBSCRIBERS, CARWASH_INTERNAL_SCHEDULER, DOCKER_LOG_MAX_*
[ ] docker compose up بدون نام سرویس تا redis ساخته شود
[ ] مایگریشن ایندکس تمام شود (روی جدول بزرگ چند دقیقه طبیعی است)
[ ] تست بودجه + تست هم‌ارزی داخل کانتینر
[ ] دو تب هم‌زمان: API نایستد
[ ] ذخیره در تب A در تب B دیده شود (pub/sub)
[ ] جابه‌جایی سریع بین صفحات: overlay گیر نکند، listener در DevTools رشد نکند
[ ] یک save مشتری پرتکرار در حد مشتری جدید باشد
[ ] اگر cron جدا برای جاب‌های scheduler دارید، یکی خاموش شود
[ ] در صورت پر بودن دیسک: truncate لاگ‌های json قبلی
```

دستورهای کارنوواش:

```bash
docker compose exec backend python manage.py test \
  apps.vehicles.tests.test_vehicle_list_query_budget \
  apps.vehicles.tests.test_loyalty_rebuild

docker compose logs -f backend | grep "live:"   # خالی = Redis سالم
```

---

## ۸. نقشه‌ی فایل‌های کارنوواش (برای کپی مسیر، نه کپی کور)

| موضوع | فایل‌ها |
|---|---|
| gunicorn gthread | `backend/gunicorn.conf.py`, `backend/Dockerfile` |
| SSE + Redis + سقف | `backend/apps/live.py`, `frontend/src/services/live.js` |
| nginx استریم | `frontend/nginx/default.conf`, `docker/edge-nginx/templates/site-ssl.conf.template` |
| redis سرویس | `docker-compose.yml`, `.env.production.example` |
| N+1 لیست خودرو | `backend/apps/vehicles/serializers.py`, `views.py` |
| تست بودجه | `backend/apps/vehicles/tests/test_vehicle_list_query_budget.py` |
| لویالتی O(1) | `backend/apps/vehicles/loyalty.py`, `tests/test_loyalty_rebuild.py` |
| حضور و غیاب بازه‌ای | `backend/apps/reports/views.py` |
| `/me/` و middleware | `backend/apps/auth/views.py`, `feature_access.py`, `middleware.py` |
| ایندکس | `backend/apps/vehicles/models.py`, `migrations/0022_*.py` |
| سشن/کش/کانکشن | `backend/config/settings.py`, `backend/docker/entrypoint.sh` |
| scheduler | `backend/apps/auth/scheduler.py` |
| overlay و timeout | `frontend/src/services/api.js`, `frontend/src/App.vue` |
| نشت لیسنر | `ReportsView`, `SettingsView`, `CustomerClubView`, `WalletPanel`, `SupportView`, `HqPanelView` |
| باندل | `frontend/vite.config.js`, `frontend/package.json` |
| گزارش حادثه | `Docs/PERFORMANCE.md` |

---

## ۹. ترتیب پیشنهادی روی پروژه‌ی بعدی

زمان تقریبی برای یک سیستم هم‌اندازه:

| اولویت | کار | چرا اول |
|---|---|---|
| P0 | نوع worker + یکی کردن استریم + timeout axios + سقف اتصال | سایت ممکن است کلاً قفل باشد |
| P0 | ثبت لیسنر قبل از await | کندی تدریجی مرورگر |
| P1 | بودجه‌ی کوئری داغ‌ترین GET + حذف نوشتن از GET | کندی با رشد داده |
| P1 | overlay فقط برای کار کاربر | حس «هر کلیک چند ثانیه لودینگ» |
| P2 | فرمول به‌جای بازپخش، گزارش بازه‌ای | کندی روی مشتری/کارگر قدیمی |
| P2 | ایندکس tenant-first | بعد از ثابت شدن تعداد کوئری، خود کوئری باید سریع باشد |
| P3 | سشن/لاگ/CONN_MAX_AGE/scheduler/chunk | هزینه‌ی ثابت و بهداشت سرور |
| بعداً | صفحه‌بندی، حذف relation سنگین از لیست، virtualize گرید | وقتی P0–P2 تمام شد |

کارهایی که در کارنوواش عمداً نماند:

- صفحه‌بندی لیست خودرو (نیاز به هماهنگی فرانت)
- حذف `status_logs` از پاسخ لیست
- جدول واسط job↔worker به‌جای JSON snapshot
- مجازی‌سازی کارت‌های داشبورد
- جابه‌جایی PNG منبع از `public/` (اسکریپت بهینه‌سازی به آن‌ها وابسته است)

---

## ۱۰. جمع‌بندی یک‌خطی

کندی کارنوواش سه موتور جدا داشت: **کارگر sync + SSE** (قفل کامل)، **N+1 و بازپخش تاریخچه** (کندی با رشد داده)، **نشت لیسنر Vue** (کندی با عمر تب). هیچ‌کدام دیتا را عوض نمی‌کنند اگر با تست بودجه و تست هم‌ارزی قفل شوند. تنها استثنا روشن شدن scheduler است که جاب‌های خوابیده را زنده می‌کند.

برای پروژه‌ی بعد: grep بخش ۳، کاتالوگ بخش ۴، تست بخش ۵، قوانین بخش ۶، دیپلوی بخش ۷.
