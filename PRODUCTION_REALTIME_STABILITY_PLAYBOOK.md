# Production Realtime & Performance Stability Playbook

**نسخه:** 2.0 — Production Safety Edition  
**تاریخ:** 2026-08-25  
**استک هدف:** Django + DRF + Vue 3 + Axios + MySQL + Redis + Nginx + Docker + Gunicorn/ASGI  
**هدف:** لایو‌سینک بدون نیاز به Refresh، لودینگ صحیح برای اکشن‌های کاربر، حذف کندی تدریجی مرورگر/سرور، و دیپلوی مرحله‌ای با امکان Rollback.

---

## 0) دستور اجرای این سند برای Cursor

این سند «پیشنهاد کلی» نیست. آن را به‌عنوان قرارداد اجرای تغییرات روی ریپو استفاده کن.

### قواعد غیرقابل مذاکره

1. **هیچ تغییر معماری را یک‌باره روی Production اعمال نکن.** تغییرات باید به فازهای P0/P1/P2 تقسیم شوند.
2. **قبل از هر تغییر، baseline ثبت کن:** تست‌ها، latency، query count، تعداد SSE connection، memory، CPU، DB connection و log size.
3. **Database منبع حقیقت است.** SSE/Redis فقط transport/invalidation است؛ هیچ state حیاتی فقط در Redis Pub/Sub نگهداری نشود.
4. **Live event فقط بعد از commit منتشر شود.** رویداد مربوط به تراکنش rollback‌شده نباید به UI برسد.
5. **هر mutation کاربر باید loading محلی و duplicate-submit protection داشته باشد.** Background sync نباید global overlay باز کند.
6. **هر listener/timer/watcher/connection باید lifecycle مشخص و cleanup قطعی داشته باشد.** هیچ side effect بعد از `await` بدون guard ایجاد نشود.
7. **GET نباید write کند.** اگر GET باعث `INSERT/UPDATE/DELETE` می‌شود، آن رفتار باید از read path خارج شود.
8. **هر endpoint داغ query budget دارد.** افزایش تعداد row نباید query count را خطی زیاد کند.
9. **هیچ timeout نامحدود برای Axios/HTTP request مجاز نیست.** POST timeout نباید باعث duplicate write شود؛ retry باید idempotent باشد.
10. **Multi-tenant isolation در live event اجباری است.** event مربوط به tenant/user دیگر هرگز نباید به client اشتباه برسد.
11. **Rollback path قبل از deploy نوشته شود.** Feature flag و config قبلی باید قابل بازگشت باشد.
12. **Cursor حق ندارد برای “بهینه‌سازی” business logic را حدس بزند.** هر بازنویسی محاسباتی فقط با equivalence test.

### خروجی‌هایی که Cursor باید در پایان بسازد

- `Docs/REALTIME_PERFORMANCE_AUDIT.md`
- `Docs/REALTIME_PERFORMANCE_CHANGES.md`
- `Docs/PRODUCTION_ROLLOUT_CHECKLIST.md`
- تست‌های backend و frontend مربوط به این سند
- benchmark قبل/بعد
- فهرست فایل‌های تغییرکرده با علت تغییر
- rollback command/config

---

# 1) مسئله‌ای که باید حل شود

سیستم قبلاً live-update داشته، اما سه کلاس مشکل دیده شده است:

1. **کندی تدریجی:** با گذشت ساعت/روز یا جابه‌جایی بین صفحات، تعداد listener/request بالا می‌رود و تب یا backend کندتر می‌شود.
2. **Loading UX خراب:** بعضی mutationها مثل ثبت درخواست داخل modal یا Start کردن task زمان می‌برند، اما کاربر feedback نمی‌بیند و ممکن است دوباره کلیک کند.
3. **Live sync ناقص:** بعد از بهینه‌سازی، eventها دیگر روی client دیگر اعمال نمی‌شوند و برای دیدن تغییرات باید Refresh دستی انجام شود.

هدف نهایی این است:

- mutation در client A ثبت شود؛
- همان client بلافاصله نتیجه‌ی معتبر خودش را ببیند؛
- client B بدون Refresh دستی تغییر را ببیند؛
- اگر SSE/Redis برای چند ثانیه قطع شد، بعد از reconnect خودکار catch-up شود؛
- هیچ background refresh باعث global loading/blur نشود؛
- تعداد connection/listener/request با عمر تب رشد نکند؛
- رشد data باعث رشد خطی queryها نشود؛
- سرویس بعد از روزها uptime همان رفتار روز اول را داشته باشد.

---

# 2) معماری هدف — اصل کلیدی

```text
User Mutation
   |
   v
Vue action state (local loading + duplicate guard)
   |
   v
Django transaction
   |---- business data write
   |---- optional durable LiveOutbox row
   |
 COMMIT
   |
 transaction.on_commit(...)
   |
   +----> Redis publish (low latency signal)
   |
   v
SSE service
   |
   v
ONE live connection per browser tab
   |
   v
Client event router
   |
   +---- targeted cache/store patch
   +---- targeted silent revalidate
   +---- dedupe/coalesce repeated events
   |
   v
UI updated without global overlay
```

### Source of truth

- MySQL = source of truth.
- Redis Pub/Sub = fast broadcast only.
- SSE = transport to browser only.
- Vue store/cache = derived client state.

**هیچ business state نباید فقط با رسیدن SSE معتبر شود.** اگر event از دست رفت، client باید بتواند از DB reconcile شود.

---

# 3) طراحی Live Sync که Refresh دستی را حذف می‌کند

## 3.1 Event envelope استاندارد

تمام eventها یک schema ثابت داشته باشند:

```json
{
  "event_id": "123456",
  "event_type": "task.updated",
  "entity": "task",
  "entity_id": "TSK-123",
  "action": "updated",
  "tenant_id": "42",
  "actor_user_id": "7",
  "version": "2026-08-25T06:30:21.123456Z",
  "occurred_at": "2026-08-25T06:30:21.130Z",
  "payload": {
    "changed_fields": ["status", "started_at"]
  }
}
```

قواعد:

- payload کوچک باشد.
- اطلاعات حساس کامل در event قرار نگیرد.
- frontend برای داده‌ی حساس/detail از API authorized fetch کند.
- event type نام‌گذاری domain-based داشته باشد: `task.created`, `request.updated`, `expense.deleted`.
- هر event `event_id` قابل dedupe داشته باشد.
- tenant/user scope اجباری باشد.

---

## 3.2 Publish فقط بعد از commit

نمونه‌ی backend:

```python
from functools import partial
from django.db import transaction


def publish_after_commit(event):
    transaction.on_commit(partial(live_bus.publish, event))
```

**ممنوع:** publish داخل `save()` قبل از commit، به‌خصوص در `atomic()`.

اگر transaction rollback شود، client نباید event phantom بگیرد.

---

## 3.3 Redis Pub/Sub به‌تنهایی کافی نیست

Redis Pub/Sub delivery از نوع **at-most-once** است. اگر subscriber لحظه‌ی publish offline باشد، event از بین می‌رود.

بنابراین یکی از دو مدل زیر اجباری است:

### مدل پیشنهادی A — Pub/Sub + Durable Cursor/Reconcile

برای اکثر SaaSهای CRUD بهترین تعادل پیچیدگی/پایداری:

- Redis Pub/Sub برای live latency.
- DB برای state.
- `event_id`/revision برای تشخیص gap.
- reconnect → catch-up از DB/outbox.
- safety revision check سبک هر 60–120 ثانیه فقط وقتی tab visible است.

### مدل B — Redis Streams

اگر **replay دقیق eventها**، audit event stream یا at-least-once لازم است، Redis Streams مناسب‌تر است.

**Cursor نباید Pub/Sub را به‌عنوان queue durable فرض کند.**

---

## 3.4 پیشنهاد مقاوم‌تر: LiveOutbox سبک

اگر سیستم باید حتی بعد از قطع کوتاه Redis بدون Refresh دستی recover شود، یک outbox کوچک بساز:

```python
class LiveOutbox(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.BigIntegerField(db_index=True)
    event_type = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=40)
    entity_id = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant_id", "id"]),
        ]
```

Outbox row باید **داخل همان transaction business mutation** نوشته شود.

سپس بعد از commit همان event به Redis publish شود.

مزایا:

- `id` cursor پایدار و monotonic است.
- reconnect می‌تواند `id > last_event_id` را replay کند.
- Redis restart باعث از دست رفتن منبع حقیقت event gap نمی‌شود.
- event history می‌تواند با retention محدود (مثلاً 24–72h) پاک شود.

**نکته:** outbox قرار نیست audit log دائمی باشد؛ retention کنترل‌شده داشته باشد.

---

## 3.5 Reconnect و Catch-up

Native `EventSource` هنگام reconnect از `Last-Event-ID` پشتیبانی می‌کند، به شرط اینکه سرور `id:` برای event بفرستد.

SSE frame:

```text
id: 123456
event: task.updated
data: {"entity":"task","entity_id":"TSK-123"}

```

در reconnect:

1. server `Last-Event-ID` را بخواند.
2. eventهای missed را با tenant scope replay کند.
3. سپس live stream ادامه یابد.
4. اگر cursor خیلی قدیمی و خارج retention بود، event `system.full_resync_required` بدهد.
5. client silent full-resync صفحه/Store مرتبط را انجام دهد، بدون reload کل سایت.

### جلوگیری از race بین replay و subscription

ترتیب امن:

1. Redis subscription را برقرار کن.
2. high-watermark/outbox backlog را بخوان.
3. backlog را ارسال کن.
4. eventهای queue شده با `id <= high-watermark` را dedupe کن.
5. سپس live queue را ادامه بده.

---

## 3.6 Heartbeat

SSE باید heartbeat داشته باشد تا proxy idle connection را نبندد:

```text
: heartbeat 2026-08-25T06:30:00Z

```

پیشنهاد شروع:

- heartbeat: 15–25s
- nginx `proxy_read_timeout`: حداقل 3× heartbeat
- retry hint: 2–5s با jitter سمت client/service در صورت custom reconnect

Heartbeat نباید DB query بزند.

---

# 4) یک connection لایو برای هر Tab — نه هر Component

## 4.1 ممنوع

```js
// داخل چندین component مختلف
onMounted(() => {
  source = new EventSource('/api/live/events/')
})
```

این الگو connection count را با تعداد component بالا می‌برد.

## 4.2 ساختار صحیح

یک singleton/composable مرکزی:

```text
src/services/live/
  liveConnection.js
  liveEventRouter.js
  liveSubscriptions.js
```

ویژگی‌های `liveConnection`:

- حداکثر یک EventSource active در هر tab.
- ref-count subscriberها.
- reconnect state.
- lastEventId.
- dedupe LRU برای event_idهای اخیر.
- visibility handling.
- explicit `close()`.
- health status: CONNECTING / OPEN / DEGRADED / CLOSED.

کامپوننت‌ها EventSource نمی‌سازند؛ فقط subscribe می‌کنند:

```js
const unsubscribe = liveBus.subscribe('task.*', onTaskEvent)

onUnmounted(() => unsubscribe())
```

---

# 5) حذف قطعی Listener/Timer/Watcher Leak در Vue

## 5.1 قانون lifecycle

Side effect باید synchronously ثبت شود و cleanup آن همان لحظه قابل تعریف باشد.

### الگوی خطرناک

```js
onMounted(async () => {
  await loadData()
  window.addEventListener('live-event', handler)
})
```

اگر component قبل از تمام شدن `await` unmount شود، listener بعداً روی component مرده ثبت می‌شود.

### الگوی صحیح

```js
let disposed = false

onMounted(() => {
  window.addEventListener('live-event', handler)

  void loadData().then((data) => {
    if (disposed) return
    applyData(data)
  })
})

onUnmounted(() => {
  disposed = true
  window.removeEventListener('live-event', handler)
})
```

بهتر از آن: listener را داخل composable مرکزی abstraction کن.

---

## 5.2 Watcher async

اگر Vue >= 3.5 است از `onWatcherCleanup()` یا `onCleanup` برای abort کردن request stale استفاده کن.

```js
watch(taskId, (id, _old, onCleanup) => {
  const controller = new AbortController()

  api.get(`/tasks/${id}/`, {
    signal: controller.signal,
    meta: { mode: 'background' }
  }).then(applyTask)

  onCleanup(() => controller.abort())
})
```

**ممنوع:** watcher async را بعد از timer/await بساز و انتظار auto-cleanup داشته باش.

---

## 5.3 Timer policy

- `setInterval` پراکنده در صفحه‌ها ممنوع.
- polling فقط fallback باشد.
- timer id در unmount پاک شود.
- debounce timeout هم cleanup شود.
- background polling وقتی `document.hidden === true` متوقف شود.
- اگر live سالم است full list polling نکن.

---

# 6) Live Event نباید Full Page Refetch ایجاد کند

یکی از منابع کندی این است:

```text
1 event
 -> 6 component listeners
 -> 6 API list calls
 -> هر call global loading
 -> render بزرگ
```

مدل صحیح:

```text
1 event
 -> central router
 -> dedupe
 -> determine impacted resource
 -> one targeted request OR local patch
 -> store update
 -> components reactively render
```

### Event coalescing

اگر در 100–300ms چند event برای یک resource آمد:

```js
scheduleRefresh('tasks:list', 150)
```

فقط یک GET بزن.

### عدم refetch غیرضروری

- `task.updated` در صفحه task detail → fetch همان task.
- `task.updated` در list → patch row اگر payload کافی است، در غیر این صورت فقط list query همان filter.
- `wallet.updated` نباید Reports/Settings/User دوباره fetch شوند.
- event route table مستند باشد.

---

# 7) سیستم Loading حرفه‌ای — User Action و Background Sync را جدا کن

## 7.1 چهار نوع request

```text
1. mutation-user    -> button/row/modal local loading
2. navigation       -> page skeleton یا route loader
3. background-sync  -> silent, بدون overlay
4. prefetch         -> silent و cancellable
```

Global overlay نباید default همه requestها باشد.

---

## 7.2 قرارداد Axios meta

نمونه:

```js
api.post('/requests/', body, {
  meta: {
    mode: 'mutation-user',
    loadingKey: 'request:create',
    timeoutMs: 30000,
    idempotencyKey: requestId,
  }
})
```

Background:

```js
api.get('/tasks/', {
  meta: {
    mode: 'background-sync',
    dedupeKey: 'tasks:list:active'
  }
})
```

### اصل

- interceptor فقط request registry را مدیریت کند.
- component می‌تواند loading مخصوص خودش را از `loadingKey` بخواند.
- global overlay فقط برای `navigation` یا عملیات واقعاً blocking.

---

## 7.3 مثال ثبت Request در Modal

رفتار مورد انتظار:

1. کاربر Submit می‌زند.
2. فقط دکمه Submit disable می‌شود.
3. spinner + متن «در حال ثبت…» نمایش داده می‌شود.
4. modal بی‌دلیل بسته نشود.
5. submit دوم نادیده گرفته شود.
6. POST success → local state فوراً update شود.
7. modal success state/close مطابق UX فعلی.
8. event live برای clientهای دیگر ارسال شود.
9. background refetch اگر لازم است silent باشد.
10. error → button آزاد + پیام دقیق؛ داده‌های فرم حفظ شوند.

Vue pattern:

```js
const submitting = ref(false)

async function submitRequest() {
  if (submitting.value) return
  submitting.value = true

  const key = crypto.randomUUID()

  try {
    const { data } = await api.post('/requests/', form.value, {
      timeout: 30000,
      headers: { 'Idempotency-Key': key },
      meta: { mode: 'mutation-user', loadingKey: 'request:create' }
    })

    requestStore.upsert(data)
  } finally {
    submitting.value = false
  }
}
```

---

## 7.4 مثال Start Task

Loading باید per-row باشد، نه کل صفحه:

```js
const pendingTaskActions = reactive(new Set())

async function startTask(taskId) {
  if (pendingTaskActions.has(taskId)) return
  pendingTaskActions.add(taskId)

  try {
    const { data } = await api.post(`/tasks/${taskId}/start/`, null, {
      meta: { mode: 'mutation-user', loadingKey: `task:start:${taskId}` }
    })
    taskStore.upsert(data)
  } finally {
    pendingTaskActions.delete(taskId)
  }
}
```

فقط دکمه‌ی همان task spinner بگیرد.

---

# 8) Duplicate Submit فقط Frontend Problem نیست — Idempotency لازم است

Disable button کافی نیست؛ retry شبکه، double tap، reverse proxy retry یا timeout مبهم ممکن است duplicate mutation بسازد.

## 8.1 Idempotency-Key

برای mutationهای حساس مثل:

- create request
- create expense
- payment
- start/finish task
- approval
- wallet transaction

header:

```http
Idempotency-Key: <uuid>
```

Backend باید tenant + user + endpoint + key را unique در نظر بگیرد و برای تکرار همان key همان نتیجه‌ی قبلی را برگرداند.

### حداقل implementation

```text
IdempotencyRecord
- tenant_id
- user_id
- key
- method
- path
- request_hash
- status_code
- response_json
- created_at

UNIQUE(tenant_id, user_id, key)
```

Retention محدود مثلاً 24h–7d بر اساس نوع عملیات.

**اگر request body با همان key عوض شد → 409 Conflict.**

---

# 9) Axios Timeout، Cancellation و Stale Request

Axios default timeout برابر صفر است؛ یعنی timeout نامحدود.

## 9.1 Default پیشنهادی

- normal GET: 15–20s
- mutation: 20–30s
- report سنگین: endpoint-specific، نه global infinite
- upload: endpoint-specific

این‌ها starting point هستند؛ از metrics تنظیم شوند.

```js
const api = axios.create({
  baseURL: '/api',
  timeout: 20000,
})
```

## 9.2 AbortController

در route change، filter change، watcher invalidation و unmount، GETهای stale را abort کن.

**برای POST timeout کورکورانه retry نکن.** اگر idempotency دارد، همان key را retry کن؛ اگر ندارد ابتدا status را verify کن.

## 9.3 Loading cleanup

هر request باید دقیقاً یک finalize داشته باشد:

```text
request -> registry.add(id)
response/error/cancel -> registry.remove(id)
watchdog -> remove stale id + log anomaly
```

boolean سراسری `isLoading=true/false` در concurrent requests ممنوع.

---

# 10) جلوگیری از کندشدن مرورگر با گذر زمان

Cursor باید audit کند:

```bash
rg -n "onMounted\(async|addEventListener|removeEventListener|setInterval|clearInterval|setTimeout|clearTimeout|EventSource|watch\(|watchEffect\(" frontend/src
```

برای هر hit جدول بساز:

```text
file | side effect | created where | cleanup where | can create multiple? | fixed?
```

### Acceptance

بعد از 100 بار route navigation:

- تعداد live EventSource = 1 per tab.
- listener count ثابت.
- timer count ثابت.
- request/minute در حالت idle ثابت.
- heap بعد از GC روند صعودی واضح نداشته باشد.
- یک live event فقط یک logical refresh ایجاد کند.

---

# 11) Backend Query Stability

## 11.1 N+1

برای ListAPIView/ModelViewSet، relationهای serializer را audit کن.

- FK / OneToOne → `select_related`
- reverse / M2M → `prefetch_related`
- `SerializerMethodField` داخل row loop بررسی شود.

### Query budget test

```python
def test_task_list_queries_do_not_scale_with_rows(self):
    self.make_tasks(5)
    small = self.query_count()

    self.make_tasks(50)
    large = self.query_count()

    self.assertLessEqual(large - small, 3)
```

عدد سقف بر اساس endpoint تنظیم شود، اما growth باید تقریباً ثابت باشد.

---

## 11.2 GET نباید write کند

تست عمومی endpointهای داغ:

```python
writes = [
    q['sql'] for q in captured
    if q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))
]
assert writes == []
```

هر sync/rebuild که هنگام GET اجرا می‌شود باید به mutation/job مناسب منتقل شود.

---

## 11.3 History rebuild

هر الگوی زیر خطر است:

```python
for event in historical_events:
    profile.apply(event)
    profile.save()
```

باید با equivalence test به:

```text
1 bounded SELECT + pure calculation + 1 save
```

تبدیل شود.

Cursor حق ندارد formula را حدس بزند.

---

# 12) MySQL Indexing بر اساس Query واقعی

Composite index از leftmost prefix استفاده می‌کند. ترتیب index باید از WHERE/ORDER BY واقعی بیاید.

مثال:

```text
WHERE tenant_id=? AND status=? ORDER BY created_at DESC
=> INDEX(tenant_id, status, created_at)

WHERE tenant_id=? AND updated_at>?
=> INDEX(tenant_id, updated_at)

LiveOutbox replay:
WHERE tenant_id=? AND id>?
=> INDEX(tenant_id, id)
```

برای endpointهای داغ:

1. query واقعی را capture کن.
2. `EXPLAIN` قبل.
3. migration index.
4. `EXPLAIN` بعد.
5. latency با data مشابه production.

هدف معمولاً `ref/range` به‌جای `ALL` برای lookupهای selective است.

**Index اضافه‌ی کورکورانه ممنوع**؛ write cost و disk را زیاد می‌کند.

---

# 13) مدل همزمانی Server — P0 کم‌ریسک

اگر اکنون Django زیر WSGI + Gunicorn و SSE با `StreamingHttpResponse` است، stream یک worker/thread را برای مدت اتصال نگه می‌دارد.

### فاز P0: قبل از مهاجرت ASGI

- یک SSE per tab.
- Gunicorn `gthread` به‌جای `sync` اگر workload I/O-bound است.
- threads را از capacity واقعی تعیین کن، نه عدد تصادفی.
- subscriber cap.
- SSE heartbeat.
- DB connection را قبل از loop طولانی آزاد کن.
- Nginx buffering off فقط روی live route.

نمونه‌ی config اولیه، فقط پس از اندازه‌گیری منابع:

```python
# gunicorn.conf.py
import os

workers = int(os.getenv('GUNICORN_WORKERS', '3'))
threads = int(os.getenv('GUNICORN_THREADS', '8'))
worker_class = 'gthread'

timeout = int(os.getenv('GUNICORN_TIMEOUT', '60'))
graceful_timeout = 30
keepalive = 5

# Safety net, not a substitute for fixing leaks
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '2000'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '200'))
```

**اعداد بالا benchmark default هستند، نه قانون.**

### DB connection budget

با gthread هر thread می‌تواند DB connection خودش را داشته باشد.

تقریب ظرفیت:

```text
api_ceiling = gunicorn_workers * threads
+ celery/worker DB concurrency
+ scheduler
+ admin/maintenance reserve
```

این عدد باید با `max_connections` MySQL سازگار باشد و reserve امن باقی بماند.

SSE loop نباید DB connection را idle نگه دارد.

---

# 14) معماری نهایی توصیه‌شده — ASGI برای Realtime

Django برای long-lived streaming/SSE زیر ASGI مناسب‌تر است؛ WSGI برای short-lived request طراحی شده است.

## 14.1 Rollout امن ASGI

Cursor نباید مستقیم Production را عوض کند.

### Stage A

- `asgi.py` فعلی را audit کن.
- middleware sync-only را لیست کن.
- SSE endpoint را async-compatible کن.
- staging test.

### Stage B

Canary با درصد کم traffic یا سرویس جداگانه realtime.

Current production command پیشنهادی مطابق مستندات جدید:

```bash
python -m pip install uvicorn uvicorn-worker gunicorn
python -m gunicorn config.asgi:application -k uvicorn_worker.UvicornWorker -w 3
```

**از `uvicorn.workers.UvicornWorker` قدیمی استفاده نکن اگر نسخه‌ی نصب‌شده آن را deprecated اعلام می‌کند.**

### Stage C

بعد از soak test، traffic کامل.

## 14.2 نکته DB در ASGI

در ASGI، `CONN_MAX_AGE` را کورکورانه مثل WSGI بالا نبر. نسخه‌ی Django نصب‌شده را بررسی کن و مطابق docs همان نسخه تنظیم کن. در مستندات جدید Django، persistent connection برای ASGI توصیه نمی‌شود.

## 14.3 Async safety

اگر transaction business logic sync است، آن را sync نگه دار و از boundary امن استفاده کن. transaction پیچیده را فقط برای async شدن بازنویسی نکن.

---

# 15) Nginx برای SSE

روی route live buffering باید خاموش باشد:

```nginx
location /api/live/events/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_buffering off;
    proxy_cache off;

    proxy_read_timeout 90s;
    proxy_send_timeout 90s;

    gzip off;
}
```

Backend response:

```http
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

`proxy_read_timeout` فاصله بین readهاست؛ heartbeat باید قبل از آن برسد.

**برای کل API `proxy_buffering off` نکن. فقط مسیر SSE.**

---

# 16) Hidden Tab Policy

وقتی tab hidden است دو انتخاب امن وجود دارد:

### حالت ساده

Connection را باز نگه دار؛ فقط render/refetch سنگین را کاهش بده.

### حالت resource-saving

بعد از مثلاً 1–2 دقیقه hidden:

- SSE را close کن.
- `lastEventId` را نگه دار.
- هنگام visible شدن reconnect کن.
- replay/catch-up انجام بده.

اگر replay نداری، **hidden tab را disconnect نکن** چون data gap ایجاد می‌شود.

---

# 17) Client Reconcile — Safety Net بدون Polling سنگین

حتی با SSE سالم، یک check بسیار سبک برای self-healing داشته باش:

```http
GET /api/live/revision/
```

Response:

```json
{
  "latest_event_id": "123456"
}
```

فقط وقتی tab visible است، هر 60–120 ثانیه:

- اگر `latest_event_id === lastAppliedEventId` → هیچ کاری نکن.
- اگر gap هست → `/api/live/sync/?after=<id>`.
- full page list refresh نکن.

این fallback جای SSE نیست؛ فقط self-healing است.

---

# 18) Store Update Strategy

برای هر mutation:

### Client initiator

بعد از success response، store خودش را فوراً update کند. منتظر event خودش نماند.

### Other clients

از event update شوند.

### Self event dedupe

اگر همان client event خودش را دوباره دریافت کرد:

- event_id dedupe یا version compare.
- fetch دوباره غیرضروری نزن.

### Version guard

اگر response/event قدیمی‌تر از state فعلی است، apply نکن.

مثال:

```js
if (incoming.updated_at < current.updated_at) return
```

برای داده‌های حساس‌تر version integer server-side بهتر از timestamp است.

---

# 19) جلوگیری از Request Storm

Event storm را کنترل کن:

- dedupe by `event_id`.
- coalesce by resource key.
- debounce 100–300ms برای list refresh.
- max one in-flight GET per dedupe key.
- اگر request جدیدتر آمد، قبلی abort شود.
- event queue bounded باشد.
- اگر queue overflow شد → `full_resync_required`، نه هزار fetch.

---

# 20) Session / DB Connection / Redis hygiene

## WSGI

اگر workload مناسب است:

```python
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
```

فقط بعد از محاسبه DB connection capacity.

## Long-running SSE thread/process

بعد از auth/snapshot اولیه، DB connection را آزاد کن و در heartbeat loop DB را لمس نکن.

## Redis

- pub/sub subscriber connection از command connection جدا باشد.
- pool exhaustion monitor شود.
- reconnect/backoff داشته باشد.
- failure Redis نباید business save را fail کند، مگر business requirement صریحاً خلاف آن باشد.

---

# 21) Docker Log Rotation

`json-file` بدون rotation می‌تواند disk را پر کند.

Compose/service config:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

یا daemon-level policy مناسب.

بعد از تغییر daemon config، containerهای موجود خودکار config جدید نمی‌گیرند؛ recreate لازم است.

**فایل log Docker را با ابزار خارجی دست‌کاری نکن مگر recovery اضطراری و با آگاهی کامل.**

---

# 22) Worker Recycling — فقط Safety Net

Gunicorn `max_requests` + `max_requests_jitter` می‌تواند اثر memory leak کوچک را محدود کند، ولی جای fix کردن leak نیست.

استفاده:

- بعد از measurement RSS growth.
- با jitter تا workerها هم‌زمان restart نشوند.
- graceful restart test با SSE active.

اگر memory ثابت است، restart بسیار تهاجمی نگذار.

---

# 23) Observability اجباری قبل از Production

حداقل metrics:

### HTTP

- request count
- error rate
- p50/p95/p99 latency
- timeout count
- cancelled request count
- endpoint latency top N

### Live

- active SSE connections
- reconnect count
- events published/sec
- events delivered/sec
- replayed events
- client gap detections
- full resync count
- average event-to-UI lag
- Redis disconnect count

### DB

- active connections
- query p95
- slow query count
- per-hot-endpoint query count
- lock wait / transaction duration

### Process

- CPU
- RSS per worker
- open file descriptors
- thread count
- container restart count

### Browser

در dev/diagnostic mode:

- active live connection count
- registered live subscribers
- pending request registry size
- duplicate event drops
- last event id

---

# 24) Logging استاندارد برای تشخیص حادثه

هر request مهم:

```json
{
  "request_id": "...",
  "path": "/api/tasks/1/start/",
  "method": "POST",
  "status": 200,
  "duration_ms": 184,
  "user_id": 7,
  "tenant_id": 42
}
```

Live event log sample:

```json
{
  "event_id": 123456,
  "event_type": "task.updated",
  "tenant_id": 42,
  "publish_ms": 3,
  "source": "task.start"
}
```

Sensitive payload را log نکن.

---

# 25) تست‌های Backend اجباری

## 25.1 Publish after commit

- commit → publish called.
- rollback → publish not called.

## 25.2 Tenant isolation

- user tenant A هیچ event tenant B را receive نکند.

## 25.3 Replay

- last id = N
- events N+1..N+5 وجود دارد
- reconnect دقیقاً missed eventها را می‌گیرد.

## 25.4 Dedupe

- event duplicate دوبار apply نشود.

## 25.5 Query budget

- 5 row vs 50 row رشد query نزدیک صفر.

## 25.6 GET no write

- list/detail GET write query نداشته باشد.

## 25.7 Idempotency

- همان key + همان body → همان response، یک mutation.
- همان key + body متفاوت → 409.

## 25.8 Outbox

- business write و outbox row atomic باشند.
- rollback هر دو را حذف کند.

---

# 26) تست‌های Frontend اجباری

## 26.1 Listener lifecycle

mount/unmount 100 بار → subscriber count baseline برگردد.

## 26.2 One connection

چند component هم‌زمان live subscription داشته باشند → فقط یک EventSource.

## 26.3 Silent background

live event → background fetch → global overlay باز نشود.

## 26.4 Mutation loading

Submit request:

- spinner فوری.
- button disabled.
- second click → POST دوم ندارد.
- success/error → loading cleanup.

## 26.5 Abort stale GET

filter سریع عوض شود → response قدیمی state جدید را overwrite نکند.

## 26.6 Reconnect

SSE قطع → reconnect → missed events apply → بدون manual reload.

## 26.7 Own-event dedupe

POST success local update + دریافت SSE همان event → duplicate refresh ایجاد نشود.

---

# 27) Soak Test — شرط اصلی برای مشکل «به مرور زمان کند می‌شود»

تست کوتاه 30 ثانیه‌ای کافی نیست.

### Staging soak

حداقل سناریو:

- چند browser/client هم‌زمان.
- route navigation تکراری.
- create/update/start/finish.
- live events پیوسته.
- tab hide/show.
- Redis restart شبیه‌سازی‌شده.
- backend worker graceful restart.

در ابتدا و انتها مقایسه:

```text
browser heap
listener count
EventSource count
requests/min idle
backend RSS
threads
DB connections
p95 API latency
live event lag
```

**Acceptance:** هیچ metric نباید روند رشد بدون سقف نشان دهد.

---

# 28) Load Test سناریوها

## Scenario A — SSE fanout

- 20/50/100 concurrent live clients بر اساس ظرفیت واقعی.
- هر 1–5s یک event.
- API عادی هم‌زمان.
- p95 API نباید به‌خاطر SSE collapse کند.

## Scenario B — Burst

- 50 event در چند ثانیه.
- frontend باید coalesce کند.
- backend نباید N×component request ببیند.

## Scenario C — Redis outage

- Redis قطع.
- business POST باید طبق policy موفق بماند.
- reconnect Redis.
- reconcile gap.

## Scenario D — Slow endpoint

- GET عمداً کند.
- timeout/cancel درست.
- loading گیر نکند.

---

# 29) Feature Flags برای Rollout

حداقل:

```env
LIVE_V2_ENABLED=false
LIVE_REPLAY_ENABLED=false
LIVE_OUTBOX_ENABLED=false
LIVE_ASGI_ENABLED=false
LIVE_REVISION_SAFETY_CHECK=true
```

Rollout:

```text
1. code deploy flags off
2. smoke test
3. enable live v2 internal users
4. monitor
5. enable replay
6. monitor
7. ASGI canary separately
8. full rollout
```

Rollback = flag off + previous container image، بدون data rollback خطرناک.

---

# 30) ترتیب اجرای پیشنهادی Cursor

## P0 — قبل از هر چیز

1. baseline و audit.
2. listener/timer leakها.
3. Axios timeout + cancellation.
4. loading mode separation.
5. mutation local loading + duplicate guard.
6. one live connection per tab.
7. Nginx SSE buffering off + heartbeat.
8. gthread capacity اگر هنوز WSGI/sync است.
9. live event dedupe/coalescing.

**بعد از P0 deploy staging و soak.**

## P1 — Sync correctness

1. استاندارد event envelope.
2. `transaction.on_commit`.
3. tenant scoping.
4. `event_id`.
5. replay/reconcile path.
6. revision safety endpoint.
7. local-store update after mutation success.
8. own-event dedupe.
9. backend idempotency برای mutationهای حساس.

## P2 — Backend growth prevention

1. query budget.
2. N+1 fixes.
3. GET no write.
4. history rebuild equivalence optimization.
5. indexes.
6. DB connection budget.
7. log rotation.
8. metrics.

## P3 — Architecture finalization

1. ASGI canary.
2. sync middleware audit.
3. realtime endpoint migration.
4. WSGI/gthread legacy path removal only after success.
5. optional Redis Streams if business نیاز durable stream دارد.

---

# 31) Grep/Audit Commands

## Frontend

```bash
rg -n "onMounted\(async|onUnmounted|onBeforeUnmount|EventSource|addEventListener|removeEventListener|setInterval|clearInterval|setTimeout|clearTimeout|watch\(|watchEffect\(" frontend/src

rg -n "axios.create|timeout:|interceptors|trackLoading|showLoading|loading" frontend/src

rg -n "await .*fetch|await .*load" frontend/src --glob "*.vue"
```

## Backend

```bash
rg -n "StreamingHttpResponse|text/event-stream|EventSource|pubsub|publish|subscribe|redis" backend

rg -n "transaction.on_commit|atomic\(" backend

rg -n "SerializerMethodField|select_related|prefetch_related" backend

rg -n "\.save\(|get_or_create|update_or_create|objects.create" backend --glob "*serializers*"

rg -n "for .* in .*" backend --glob "*.py"
```

## Infra

```bash
rg -n "gunicorn|worker_class|threads|max_requests|timeout" .
rg -n "proxy_buffering|proxy_read_timeout|text/event-stream" .
rg -n "logging:|max-size|max-file" docker-compose*.yml
```

---

# 32) Production Preflight Checklist

```text
[ ] DB backup verified
[ ] current image/tag recorded for rollback
[ ] baseline p95/p99 saved
[ ] baseline DB connections saved
[ ] baseline RSS saved
[ ] baseline SSE connections saved
[ ] full test suite baseline recorded
[ ] P0 tests green
[ ] no listener/timer growth after navigation stress
[ ] one SSE per tab
[ ] background live refresh opens no global overlay
[ ] request create shows local loading
[ ] task start shows per-task loading
[ ] duplicate click produces one mutation
[ ] Axios requests have finite timeout
[ ] stale GET can be aborted
[ ] Redis event published only after commit
[ ] tenant isolation test green
[ ] reconnect catches up without manual refresh
[ ] Redis temporary outage self-heals
[ ] hot GET query budget is stable
[ ] GET routes perform no writes
[ ] EXPLAIN checked for new indexes
[ ] MySQL max_connections budget checked against worker/thread count
[ ] Docker logs rotate
[ ] nginx SSE buffering disabled only on SSE route
[ ] heartbeat interval < proxy_read_timeout
[ ] graceful deploy with active SSE tested
[ ] feature flags default safe
[ ] rollback tested
```

---

# 33) Production Post-Deploy Validation

در 5–15 دقیقه اول:

```text
- 5xx rate
- timeout count
- p95 latency
- DB connection count
- Redis errors
- active SSE count
- reconnect storm
- worker RSS/thread count
```

سپس:

- client A mutation → client B update بدون reload.
- network offline client B → mutation A → network online B → catch-up.
- 20 بار route switch → listener ثابت.
- modal submit slow endpoint → spinner صحیح، بدون duplicate.
- task start slow endpoint → فقط همان row loading.
- event background → هیچ full-screen overlay.

در 1–24 ساعت:

- RSS trend.
- requests/min idle.
- DB connection trend.
- event lag.
- log disk size.
- reconnect rate.

اگر trend رشد مداوم دارد rollout متوقف و rollback کن.

---

# 34) مواردی که Cursor نباید انجام دهد

1. `timeout: 0` را نگه ندارد.
2. برای حل loading، global overlay را روی همه requestها برنگرداند.
3. برای حل sync، polling کامل همه‌ی صفحه‌ها را هر چند ثانیه فعال نکند.
4. برای حل SSE، تعداد worker را بی‌حساب زیاد نکند.
5. Redis Pub/Sub را durable فرض نکند.
6. event را قبل از DB commit publish نکند.
7. داخل هر component EventSource جدید نسازد.
8. listener را بعد از `await` بدون lifecycle guard نسازد.
9. POST timeout را با key جدید retry نکند.
10. full store/page را برای هر live event refetch نکند.
11. query optimization را بدون query-budget test merge نکند.
12. history calculation را بدون equivalence test عوض نکند.
13. ASGI migration را بدون middleware audit و staging soak deploy نکند.
14. DB `CONN_MAX_AGE` و Gunicorn threads را بدون connection-capacity calculation بالا نبرد.
15. indexهای زیاد فقط «برای احتیاط» اضافه نکند.

---

# 35) Definition of Done

کار فقط وقتی تمام است که همه‌ی موارد زیر برقرار باشد:

### UX

- تمام mutationهای قابل‌توجه feedback فوری دارند.
- هیچ double submit قابل تولید نیست.
- background sync UI را قفل نمی‌کند.

### Realtime

- یک connection per tab.
- clientهای دیگر بدون refresh update می‌شوند.
- reconnect gap را خودکار جبران می‌کند.
- own-event duplicate ایجاد نمی‌کند.

### Stability

- navigation stress باعث رشد listener/timer نمی‌شود.
- soak test memory/request growth ندارد.
- SSE باعث starvation API نمی‌شود.

### Backend

- hot lists N+1 ندارند.
- GET write ندارد.
- query budget با row count رشد خطی ندارد.
- indexها با EXPLAIN تأیید شده‌اند.

### Infra

- timeoutها محدودند.
- log rotation فعال است.
- DB connections ظرفیت امن دارند.
- metrics و rollback آماده‌اند.

---

# 36) تصمیم معماری پیشنهادی نهایی

برای این پروژه، مسیر کم‌ریسک و حرفه‌ای این است:

```text
NOW:
WSGI/Gunicorn gthread (اگر فعلاً معماری همین است)
+ one SSE/tab
+ Redis Pub/Sub
+ transaction.on_commit
+ event_id/dedupe
+ local action loading
+ silent background sync
+ timeout/cancel
+ leak cleanup
+ query budgets

NEXT:
Durable cursor/outbox + reconnect replay

THEN:
ASGI canary for realtime/whole Django after compatibility audit
```

این ترتیب عمداً محافظه‌کارانه است: اول bugهای فعلی را بدون rewrite پرریسک برطرف می‌کند، سپس reliability را اضافه می‌کند، و در آخر مدل deployment را به معماری مناسب long-lived connection ارتقا می‌دهد.

---

# 37) منابع رسمی که این تصمیم‌ها با آن‌ها تطبیق داده شده‌اند

- Django — `StreamingHttpResponse`: زیر WSGI، streaming worker را برای تمام مدت response درگیر می‌کند؛ زیر ASGI long-lived streaming مناسب‌تر است.  
  https://docs.djangoproject.com/en/6.1/ref/request-response/#streaminghttpresponse-objects

- Django — ASGI deployment / Uvicorn.  
  https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/uvicorn/

- Django — `transaction.on_commit()`.  
  https://docs.djangoproject.com/en/dev/topics/db/transactions/#performing-actions-after-commit

- Django REST Framework — جلوگیری از N+1 با `select_related()` و `prefetch_related()`.  
  https://www.django-rest-framework.org/api-guide/generic-views/#avoiding-n1-queries

- Gunicorn 23 — worker design, gthread, threads, `max_requests`, jitter و timeout.  
  https://docs.gunicorn.org/en/stable/design.html  
  https://docs.gunicorn.org/en/stable/settings.html

- Vue — cleanup side effects در `onUnmounted()` و synchronous watcher lifecycle.  
  https://vuejs.org/api/composition-api-lifecycle  
  https://vuejs.org/guide/essentials/watchers

- Axios — timeout پیش‌فرض 0 و AbortController cancellation.  
  https://axios-http.com/docs/req_config  
  https://axios-http.com/docs/cancellation

- Redis — Pub/Sub دارای at-most-once delivery است؛ برای replay/durability باید state durable/reconcile یا Streams داشته باشید.  
  https://redis.io/docs/latest/develop/pubsub/

- WHATWG HTML — SSE `id`, `retry`, auto reconnect و `Last-Event-ID`.  
  https://html.spec.whatwg.org/dev/server-sent-events.html

- Nginx — `proxy_buffering` و `proxy_read_timeout`.  
  https://nginx.org/en/docs/http/ngx_http_proxy_module.html

- MySQL — composite index و leftmost prefix؛ EXPLAIN برای تأیید plan.  
  https://dev.mysql.com/doc/refman/8.0/en/multiple-column-indexes.html  
  https://dev.mysql.com/doc/refman/8.4/en/explain.html

- Docker — `json-file` rotation با `max-size` و `max-file`.  
  https://docs.docker.com/engine/logging/drivers/json-file/

---

# 38) جمله‌ی نهایی برای Cursor

**هدف این تغییرات “سریع‌تر شدن یک صفحه” نیست؛ هدف ساختن یک سیستم self-healing است که live update را بدون Refresh دستی حفظ کند، loading فقط جایی نمایش داده شود که کاربر واقعاً منتظر عملیات خودش است، هیچ listener/request/connection با عمر تب تکثیر نشود، و هیچ failure موقت Redis/SSE یا request کند باعث گیرکردن UI یا از دست رفتن دائمی sync نشود. هر تغییر باید با test + metric + rollback اثبات شود.**
