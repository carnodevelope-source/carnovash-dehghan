# سند اجرایی بازطراحی UI/UX پنل HQ

> نسخه آماده توسعه برای Cursor — گزارشات مرکزی و سرویس‌ها

## 0) دستور اصلی برای Cursor

این سند را به‌عنوان **مرجع قطعی پیاده‌سازی فرانت‌اند** در نظر بگیر. ابتدا کامپوننت‌ها، APIها، enumها، permissionها و استایل‌های موجود پروژه را بررسی کن؛ سپس بازطراحی را مرحله‌ای انجام بده. هیچ API، فیلد، عدد یا وضعیت ساختگی نساز و هیچ منطق بک‌اند را حدس نزن. در صورت نبود یک فیلد، حالت خالی استاندارد نشان بده و آن را با مقدار جعلی پر نکن.

الزامات غیرقابل مذاکره:

- همه رابط‌ها RTL و فارسی باشند؛ اعداد مالی با جداکننده هزارگان و واحد «تومان» نمایش داده شوند.
- تاریخ در UI جلالی باشد و فقط در لایه API به ISO تبدیل شود.
- وضعیت فیلتر، تب، مرتب‌سازی، صفحه جدول و کلاینت انتخابی در URL query ذخیره شود.
- داده‌های مالی یا اکشن‌های غیرمجاز حتی برای لحظه‌ای به نقش فاقد دسترسی render نشوند.
- همه نمودارها، KPIها، جدول‌ها و جزئیات از یک snapshot/response هم‌زمان تغذیه شوند.
- هر عملیات موفق، داده‌های Summary، جدول، جزئیات و Alertهای وابسته را invalidate و دوباره دریافت کند.
- طراحی باید از تم فعلی سایت استفاده کند و ظاهر یک محصول SaaS مدیریتی مدرن، روشن و حرفه‌ای داشته باشد.
- از کارت‌سازی افراطی، رنگ‌های زیاد، سایه سنگین، گرادیان نمایشی، انیمیشن طولانی و جدول‌های بدون اولویت‌بندی خودداری شود.

---

# 1) هدف محصول و منطق معماری اطلاعات

پنل باید در کمتر از ۵ ثانیه پاسخ این سؤال‌ها را بدهد:

1. امروز/این بازه، وضعیت مالی و عملیاتی کل شبکه چگونه است؟
2. سهم کارنو و آراکار دقیقاً از کجا ایجاد شده است؟
3. کدام کارواش درآمد، بدهی، افت عملکرد یا مشکل کیف پول دارد؟
4. کدام سرویس نزدیک انقضا، بدهکار، مسدود یا نیازمند اقدام است؟
5. کاربر بر اساس نقش خود اکنون باید روی کدام مورد اقدام کند؟

اصل ساختاری:

- **نمای کلی** برای تصمیم‌گیری سریع.
- **تحلیل** برای مقایسه و کشف علت.
- **جدول** برای حسابرسی و عملیات.
- **Drawer/Modal** برای جزئیات و اقدام، بدون خارج‌شدن از context.

هیچ صفحه‌ای نباید تمام داده‌ها را هم‌زمان در یک سطح نمایش دهد. ترتیب ثابت اطلاعات در همه بخش‌ها:

`عنوان و وضعیت → فیلترها → KPIهای اصلی → روند/هشدار → جدول → جزئیات → اقدام`

---

# 2) Design System پنل HQ

## 2.1 رنگ‌ها

از توکن‌های زیر استفاده شود و در صورت وجود tokenهای فعلی پروژه، به همان‌ها map شوند:

| کاربرد | مقدار | توضیح |
|---|---:|---|
| Page background | `#EDF3FB` | پس‌زمینه اصلی روشن |
| Surface | `#F7F9FD` | کارت و پنل فرعی |
| Surface strong | `#FFFFFF` | جدول، Drawer و مودال |
| Primary | `#1976D2` | CTA، تب فعال، لینک |
| Primary hover | `#0F62B3` | hover و active |
| Primary text | `#0F3B72` | تیترهای اصلی |
| Accent/Success | `#4CAF50` | موفق، فعال، وصول کامل |
| Border | `#D8E3F5` | مرز کنترل‌ها و کارت‌ها |
| Text | `#0F2545` | متن اصلی |
| Text muted | `#64748B` | توضیحات و metadata |
| Warning | `#D97706` | نزدیک انقضا، پرداخت ناقص |
| Danger | `#DC2626` | مسدود، overdue، ریسک |
| Info | `#0284C7` | اطلاعات و وضعیت خنثی |

قاعده رنگ:

- رنگ باید «معنا» داشته باشد، نه تزئین.
- تمام وضعیت‌ها علاوه بر رنگ، متن و icon داشته باشند.
- سبز فقط برای وضعیت مثبت، قرمز فقط برای خطا/ریسک، نارنجی برای نیاز به توجه و آبی برای اطلاعات استفاده شود.
- سهم کارنو با آبی و سهم آراکار با بنفش ملایم نمایش داده شود؛ این دو رنگ در همه صفحات ثابت بمانند.

## 2.2 تایپوگرافی و اعداد

- فونت: فونت فعلی پروژه؛ fallback پیشنهادی `Dana, IRANSansX, Vazirmatn, sans-serif`.
- عنوان صفحه: 24px/700 دسکتاپ، 20px/700 موبایل.
- عنوان بخش: 18px/700.
- عنوان کارت: 13px/500 با رنگ muted.
- مقدار KPI: 24–28px/800 و `font-variant-numeric: tabular-nums`.
- متن جدول: 13px/500؛ header جدول 12px/700.
- توضیح ثانویه: 12px/400.
- مبلغ در تمام جدول‌ها nowrap و هم‌تراز باشد.

## 2.3 فاصله، شعاع و ارتفاع

| مورد | مقدار پیشنهادی |
|---|---:|
| Page gutter | 24px دسکتاپ، 16px تبلت، 12px موبایل |
| فاصله Section | 24px |
| فاصله داخلی Card | 16–20px |
| Radius کارت/جدول | 14px |
| Radius کنترل | 10px |
| ارتفاع input/button | 40px |
| ارتفاع ردیف جدول | 56px؛ حالت compact برابر 44px |

سایه فقط روی Drawer/Modal و header چسبان استفاده شود. کارت‌های عادی با border ظریف از پس‌زمینه جدا شوند.

## 2.4 الگوی ثابت کامپوننت‌ها

### `PageHeader`

- breadcrumb کوچک: `پنل HQ / گزارشات` یا `پنل HQ / سرویس‌ها`
- عنوان، توضیح یک‌خطی و badge «آخرین بروزرسانی».
- سمت مقابل: Refresh و اکشن‌های سطح صفحه.
- در موبایل اکشن‌های فرعی داخل menu قرار گیرند.

### `KpiCard`

شامل label، مقدار، واحد، icon، مقایسه دوره قبل و tooltip تعریف شاخص. در هر view حداکثر ۴ KPI اصلی در ردیف اول نمایش داده شود. KPIهای مکمل داخل بخش «جزئیات بیشتر» یا ردیف دوم کم‌تأکید قرار گیرند.

### `StatusBadge`

- ارتفاع 24px، متن کوتاه، dot یا icon، پس‌زمینه بسیار ملایم.
- map وضعیت‌ها از یک فایل مرکزی باشد؛ از تعریف رنگ و label داخل هر صفحه جلوگیری شود.

### `DataTableShell`

- toolbar مستقل شامل نتیجه، ستون‌ها، تراکم، خروجی و refresh.
- header چسبان، pagination سروری، مرتب‌سازی سروری و empty/loading/error داخلی.
- ستون اصلی و ستون عملیات sticky باشند.
- tooltip برای headerهای تخصصی و مقادیر truncate‌شده.
- column visibility و density برای هر کاربر در local storage ذخیره شود.

### `FilterBar`

- فیلترهای اصلی همیشه دیده شوند؛ فیلترهای ثانویه داخل popover «فیلترهای بیشتر».
- بعد از اعمال، chip فعال با امکان حذف سریع نمایش داده شود.
- دکمه «پاک‌کردن همه» فقط وقتی فیلتر فعال وجود دارد.
- تغییر فیلتر با debounce 350ms برای search و immediate برای select انجام شود.

### `DetailDrawer`

- دسکتاپ: عرض 520 تا 640px؛ موبایل: تمام‌صفحه.
- header و footer چسبان.
- بستن با Esc، دکمه مشخص و کلیک backdrop؛ هنگام فرم dirty برای بستن confirmation لازم است.

### `ConfirmActionModal`

- برای اکشن‌های اثرگذار استفاده شود.
- قبل از تأیید: هدف، تغییر مورد انتظار، اثر روی دسترسی/مالی، reason اجباری و خلاصه داده نمایش داده شود.
- CTA destructive قرمز و متن آن دقیق باشد؛ از «تأیید» مبهم استفاده نشود.

---

# 3) پوسته مشترک دو صفحه

## 3.1 ناوبری سطح اول HQ

دو آیتم اصلی در navigation پنل:

- **گزارشات مرکزی**: فقط `hq_admin`, `hq_finance`
- **سرویس‌ها و اشتراک‌ها**: همه نقش‌های مجاز، با محدودیت جزئیات بر اساس capability

این دو صفحه نباید به شکل دو tab کوچک در میان محتوای شلوغ دیده شوند؛ آن‌ها دو مقصد اصلی پنل هستند و باید در navigation یا tab سطح اول، واضح و پایدار باشند.

## 3.2 نوار زمان و freshness

در صفحه گزارشات یک `ReportControlBar` چسبان زیر header قرار گیرد:

- segmented control: روز، هفته، ماه، کل تاریخ.
- date range سفارشی.
- switch «مقایسه با دوره قبل» فقط برای بازه دارای start/end.
- متن `داده‌ها تا ساعت ...`.
- refresh دستی با spinner کوچک.

رفتار:

- پیش‌فرض `month`.
- با تغییر بازه، تمام بخش‌های view فعال skeleton می‌شوند، ولی layout جابه‌جا نمی‌شود.
- هنگام refresh، داده قبلی حفظ و روی خود دکمه loading نشان داده شود.
- اگر دریافت بخشی شکست خورد، کل صفحه سفید نشود؛ همان section error با retry داشته باشد.

---

# 4) صفحه گزارشات مرکزی

## 4.1 Workspace navigation

پس از کنترل بازه، ۴ workspace به‌صورت tab card فشرده نمایش داده شوند:

| تب | سؤال اصلی | محتوای شاخص |
|---|---|---|
| گزارش داخلی HQ | سهم کارنو/آراکار و مطالبات چقدر است؟ | سهم‌ها، قابلیت‌ها، هزینه عملیاتی |
| گزارش کارواش‌ها | یک شعبه مشخص چگونه عمل کرده؟ | انتخاب کارواش و گزارش کامل |
| ریز کیف پول | پول چگونه وارد و خارج شده؟ | موجودی، واریز، برداشت، لجر |
| نمای شبکه | رتبه و سلامت شعب چگونه است؟ | روند و مقایسه per-tenant |

هر tab دارای icon، عنوان، توضیح بسیار کوتاه و badge تعداد موارد نیازمند توجه باشد. در موبایل horizontal scroll با snap فعال شود.

---

## 4.2 Workspace «گزارش داخلی HQ»

### ساختار صفحه

1. ردیف ۳ KPI اصلی.
2. نمودار روند سهم‌ها و breakdown منبع درآمد.
3. segmented tab سهم کارنو.
4. جدول مربوط به tab فعال.
5. بخش مستقل سهم آراکار و عملیات شعب.

### KPIهای اصلی

| کارت | فیلد | رفتار |
|---|---|---|
| سهم کارنو | `hq_share_total` | آبی؛ tooltip: فقط wallet OUT گروه hq |
| سهم آراکار | `rah_share_total` | بنفش؛ tooltip: فقط wallet OUT گروه rah |
| مانده اقساط آپشن‌ها | `feature_remaining_total` | نارنجی در صورت بیشتر از صفر |

زیر مقدار هر کارت یک breakdown کوتاه نمایش داده شود، نه یک KPI جدید. نمونه: `پیامک ۴۲٪ · حضور و غیاب ۳۱٪`.

### ناحیه تحلیل

چیدمان دسکتاپ 8/4:

- **نمودار اصلی:** line/area برای `hq_share_total` و `rah_share_total` از `trends[]`.
- **ترکیب سهم کارنو:** فهرست افقی/Donut از `feature_summary[]` و هزینه SMS؛ همراه مبلغ و درصد.

نمودار باید tooltip تاریخ جلالی و مبلغ کامل داشته باشد. legend قابل کلیک و رنگ سهم‌ها ثابت باشد. اگر trends خالی است، empty state توضیحی نشان داده شود.

### ساب‌تب سهم کارنو

ترتیب:

1. کیف پول پیامک.
2. باشگاه مشتریان پیشرفته.
3. ورود اکسل.
4. ورود و خروج.

هر tab badge مبلغ/تعداد داشته باشد. tabهای بدون داده حذف نشوند؛ با مقدار صفر و empty state نمایش داده شوند تا ساختار صفحه پایدار بماند.

#### جدول پیامک

ستون‌های پیش‌فرض:

`کارواش | کیف پول | نوع | مبلغ | شرح | زمان | سهم`

- ردیف و index فقط در export یا حالت حسابرسی نمایش داده شود؛ در UI روزمره ارزش بصری کمی دارد.
- «کارواش» لینک آبی و بازکننده Drawer ریز همان tenant باشد.
- نوع IN/OUT با badge و icon جهت نمایش داده شود.
- شرح حداکثر دو خط و متن کامل در tooltip.
- footer جدول جمع `share_amount || amount` را بر اساس ردیف‌های response جاری نشان دهد و label دقیق «جمع ردیف‌های نمایش‌داده‌شده» داشته باشد.

#### جدول قابلیت‌ها

ستون‌ها:

`کارواش | قابلیت | پلن پرداخت | پرداخت‌شده | مانده | اقساط | سهم`

- مانده صفر: «تسویه‌شده» سبز.
- مانده مثبت: مبلغ نارنجی + badge تعداد ماه.
- ردیف مجازی `customer_import_excel` با icon و tooltip «ایجادشده از تراکنش کیف پول» از خرید واقعی قابلیت تفکیک شود.

### بخش سهم آراکار و عملیات

Header بخش:

- عنوان «سهم آراکار و عملکرد عملیاتی شعب».
- توضیح: «فقط شعب دارای سهم آراکار در بازه انتخابی».
- quick filter برای وضعیت health.

قبل از جدول، دو insight کوچک نشان داده شود: بیشترین سهم آراکار و بیشترین مطالبات؛ از `highlights` در صورت وجود.

ستون‌ها:

`رتبه | کارواش و آخرین فعالیت | درآمد وصولی | هزینه | سهم آراکار | مطالبات | خودرو | سلامت`

- ردیف‌ها بر اساس `rah_share_total` پیش‌فرض نزولی.
- `last_activity_at` زیر نام کارواش با متن نسبی و tooltip تاریخ کامل.
- health همیشه از helper مرکزی و طبق الگوریتم backend نمایش داده شود؛ frontend آن را دوباره محاسبه نکند.

---

## 4.3 Workspace «گزارشات کارواش‌ها»

### چیدمان

دسکتاپ از grid با ستون انتخاب کارواش 300–340px و ناحیه گزارش منعطف استفاده کند. Sidebar و header گزارش sticky باشند. در نمایشگر زیر 1024px انتخاب کارواش به combobox قابل جستجو تبدیل شود.

### پنل انتخاب کارواش

- search با نام کارواش.
- filter وضعیت: همه، فعال در بازه، بدون فعالیت.
- هر آیتم: نام، آخرین فعالیت، تعداد خودرو، سلامت.
- selected state واضح با border آبی و check icon.
- virtual list اگر تعداد بالا است.

### header کارواش انتخابی

- نام کارواش، وضعیت health، آخرین فعالیت.
- بازه گزارش فعال.
- اکشن «بازکردن پروفایل کارواش» فقط اگر route معتبر وجود دارد.
- loading مستقل هنگام تعویض tenant.

### KPIها با گروه‌بندی معنایی

ردیف اول، ۴ KPI اصلی:

`مبلغ نهایی | حق کارواش | حق نیرو | تعداد خودرو`

ردیف مکمل collapsible:

`قبل تخفیف | تخفیف | انعام | پرداختنی نیرو | بیمه`

این تفکیک مانع نمایش ۹ کارت هم‌وزن و گیج‌کننده می‌شود.

### ساب‌تب‌های گزارش کارواش

| تب | خلاصه در tab | ستون‌های اصلی |
|---|---|---|
| گزارش کل | تعداد مراجعه | راننده، پلاک، وضعیت، مبلغ نهایی، سهم‌ها، تخفیف، مالیات، انعام، نیرو، خدمات، تاریخ |
| حق کارواش | جمع سهم | راننده، پلاک، حق کارواش، نیرو، تاریخ |
| حق نیرو | جمع سهم | راننده، پلاک، حق نیرو، نیرو، تاریخ |
| انعام و کالا | جمع انعام | راننده، پلاک، انعام، نیرو، کالا، تاریخ |
| درآمد و پرداخت | وصول/مانده | تاریخ، راننده، روش/وضعیت پرداخت، خدمت، کالا، مالیات، نهایی، دریافتی، مانده |
| ورود و خروج | تعداد رویداد | نیرو، نوع رویداد، منبع، زمان |
| لیست سیاه | تعداد پلاک | پلاک، نوع، یادداشت، ثبت‌کننده، تاریخ |

قواعد جدول گزارش کل:

- ستون‌های کم‌اولویت مثل gender، phone، tax و services به‌صورت پیش‌فرض مخفی ولی از selector ستون قابل فعال‌سازی باشند.
- کلیک ردیف یک Drawer جزئیات مراجعه باز کند، نه modal کوچک.
- پلاک در یک کامپوننت plate خوانا نمایش داده شود.
- serviceها به‌صورت حداکثر دو chip و `+N` نمایش داده شوند.

Empty state اولیه: «برای مشاهده گزارش، یک کارواش را انتخاب کنید.»

---

## 4.4 Workspace «ریز کیف پول»

### ساختار

1. گروه KPI «موجودی و جریان».
2. نمودار جریان روزانه.
3. گروه KPI «پیامک».
4. فیلتر و لجر تراکنش‌ها.
5. Drawer ریز کارواش.

### KPIها

ردیف اول:

- کل موجودی: `wallet_balance_total`
- کل واریزی: `wallet_deposit_total`
- کل برداشت: `wallet_withdraw_total`
- خالص جریان: `deposit - withdraw` یا `wallet_net_flow` موجود در API

ردیف دوم فشرده:

- شارژ درگاه.
- شارژ دستی.
- موجودی پیامک.
- SMS ارسال‌شده و هزینه SMS در یک کارت ترکیبی.

### نمودار

Bar مثبت/منفی روزانه برای واریز و برداشت از `trends[]` و line خالص جریان. در tooltip سه مقدار کامل نمایش داده شود. نمودار صرفاً از response دریافت‌شده ساخته شود.

### فیلتر اختصاصی لجر

- search کارواش/شرح.
- نوع کیف پول: همه، عادی، پیامک.
- جهت: همه، واریز، برداشت.
- گروه سهم: کارنو، آراکار، بدون سهم.
- منبع/ref type.

ستون‌ها:

`کارواش | کیف پول | نوع کیف | جهت | مبلغ | شرح/مرجع | ثبت‌کننده | زمان | سهم`

قواعد:

- مبلغ واریز با `+` و برداشت با `−`، ولی رنگ تنها نشانه نباشد.
- عبارت «حداکثر ۲۵۰ تراکنش اخیر» بالای جدول واضح باشد تا کاربر آن را با کل داده اشتباه نگیرد.
- اگر pagination بک‌اند وجود ندارد، pagination مصنوعی برای القای کل داده نساز.

### Drawer ریز کارواش

header: نام کارواش + سلامت شارژ + بازه.

چهار KPI: کل موجودی، عادی، پیامک، خالص جریان.

سپس tabهای `همه | واریزها | برداشت‌ها | پیامک` و جدول تراکنش‌های همان tenant. داده باید از snapshot فعلی فیلتر شود؛ اگر endpoint مستقل اضافه شد، source آن صریح و loading جدا باشد.

---

## 4.5 Workspace «نمای شبکه»

دو subtab سطح دوم: `گزارش درآمد` و `گزارش کیف پول`.

### گزارش درآمد

KPI اصلی:

`درآمد وصولی | خالص | تعداد خودرو | نرخ وصول`

KPI مکمل:

`قبل تخفیف | تخفیف | میانگین فاکتور | مطالبات`

هر KPI در صورت وجود فیلد `*_change_percent` badge روند داشته باشد. برای null عبارت «بدون داده مقایسه» نمایش داده شود؛ صفر جایگزین null نشود.

ناحیه تحلیل:

- نمودار trend درآمد/خالص.
- کارت highlight شامل `top_revenue`, `top_volume`, `top_margin` و watchlist.

جدول:

`رتبه | کارواش | سلامت | درآمد | قبل تخفیف | تخفیف | خالص | میانگین فاکتور | مطالبات | تعداد پرداخت`

- default sort: paid_amount desc.
- کارواش‌های risk یک خط accent قرمز بسیار ظریف در سمت راست ردیف داشته باشند.
- رتبه با medal فقط برای ۳ ردیف اول؛ سایر رتبه‌ها متن ساده.

### گزارش کیف پول

KPI: کل موجودی، عادی، پیامک، شارژ درگاه، شارژ دستی.

جدول:

`کارواش | سلامت شارژ | کل موجودی | عادی | پیامک | واریز | برداشت | درگاه | دستی`

Status mapping:

| API | label | tone |
|---|---|---|
| `empty` | موجودی خالی | danger |
| `sms_heavy` | تمرکز روی پیامک | info |
| `gateway` | شارژ عمدتاً درگاه | success |
| `healthy` | سالم | success |
| `idle` | بدون فعالیت | neutral |

بالای جدول quick filter «نیازمند توجه» شامل empty و idle قرار گیرد.

---

# 5) صفحه سرویس‌ها و اشتراک‌ها

## 5.1 ساختار کلی صفحه

ترتیب دقیق:

1. `PageHeader` و اکشن‌های سطح صفحه.
2. نوار Alertهای مهم.
3. KPIهای متناسب با نقش.
4. navigation هشت report.
5. FilterBar متناسب با report فعال.
6. client context در صورت انتخاب tenant.
7. جدول/ماتریس.
8. bulk action bar در صورت selection.
9. Detail Drawer.
10. Action Drawer/Modal.

### اکشن‌های Header

- Refresh برای همه.
- Export فقط capability `export`.
- «همگام‌سازی کاتالوگ» فقط admin، داخل menu فرعی و با confirmation؛ CTA اصلی صفحه نباشد.

## 5.2 Alert Center

Alertها به‌جای یک strip شلوغ، در یک نوار خلاصه نمایش داده شوند:

- critical count قرمز.
- warning count نارنجی.
- info count آبی.
- دکمه «مشاهده هشدارها» Drawer جدا باز کند.

در Drawer هشدارها:

- گروه‌بندی بر اساس severity.
- هر ردیف: title، client، product، message و CTA «مشاهده اشتراک».
- کلیک CTA، Drawer هشدار را می‌بندد و Detail Drawer اشتراک را باز می‌کند.

## 5.3 KPIهای نقش‌محور

برای همه نقش‌ها:

`کلاینت فعال | سرویس فعال | نزدیک انقضا | مسدود/در انتظار اقدام`

برای role دارای `see_financial`:

`فروش کل | وصول‌شده | مطالبات`

برای role دارای `see_holding_profit`:

یک کارت تقسیم‌شده «سهم وصولی هلدینگ‌ها» با `carno_paid` و `arakar_paid`.

قاعده: support نباید placeholder یا کارت قفل‌شده مالی ببیند؛ layout باید بدون gap بازچینش شود.

## 5.4 Report navigation

۸ تب:

`همه سرویس‌ها | لایسنس | کیف پول | ورود و خروج | فضای ابری | باشگاه مشتریان | پیامک | ماتریس درآمد`

- icon و badge count.
- tab درآمد فقط برای `see_financial`.
- tab فعال در query `report=`.
- در موبایل horizontal scroll؛ dropdown مبهم جایگزین tab نشود.

## 5.5 FilterBar سرویس‌ها

فیلترهای همیشه‌نمایان:

- جستجو.
- پروژه.
- سرویس، مگر tab خودش سرویس را ثابت کرده باشد.
- وضعیت.
- وضعیت پرداخت فقط برای `see_financial`.

فیلترهای بیشتر:

- کلاینت.
- بدهکار.
- نزدیک انقضا.
- تاریخ خرید از/تا.
- مرتب‌سازی.

اگر tab مثل لایسنس `product_key=core_software` را ثابت می‌کند، select سرویس مخفی شود و chip قفل‌شده «لایسنس اصلی» نشان داده شود.

## 5.6 پنل ۳۶۰ درجه کلاینت

وقتی `tenant_id` انتخاب شد، یک context card بالای جدول نمایش داده شود:

- نام کلاینت و تعداد سرویس‌های فعال.
- خلاصه مالی فقط برای نقش مجاز.
- سرویس‌های خریداری‌شده به‌صورت chip status.
- فرصت‌های فروش از `not_purchased[]` در بخش collapsible «سرویس‌های خریداری‌نشده».
- دکمه بستن context برای حذف tenant filter.

این بخش جایگزین جدول نیست؛ جدول همچنان اشتراک‌های همان tenant را نشان می‌دهد.

## 5.7 جدول اصلی اشتراک‌ها

ستون‌های پایه:

`انتخاب | کلاینت | سرویس و مالک سهم | پلن | وضعیت | تاریخ خرید | انقضا | عملیات`

ستون‌های مالی فقط با `see_financial`:

`مبلغ فروش | وصول | مانده`

بهبود نمایش:

- سهم به‌جای ستون پررنگ مستقل، زیر نام سرویس با badge کوچک کارنو/آراکار نمایش داده شود؛ قابلیت sort/filter آن حفظ شود.
- تاریخ انقضا علاوه بر تاریخ، label نسبی داشته باشد: «۸ روز مانده»، «۳ روز گذشته».
- مانده صفر با «تسویه‌شده» و مانده مثبت با مبلغ نمایش داده شود.
- row tint کامل برای share ممنوع؛ یک accent bar 3px و badge کافی است.
- کلیک هر جای ردیف Detail Drawer را باز کند؛ کلیک checkbox و action menu propagation نداشته باشد.

### Action menu ردیف

اکشن‌ها بر اساس وضعیت و capability گروه‌بندی شوند:

- دسترسی: فعال‌سازی، غیرفعال‌سازی، تعلیق، رفع تعلیق، مسدودسازی، بازگردانی.
- قرارداد: تمدید روز، تمدید رسمی، تغییر پلن.
- مالی: ثبت پرداخت، تخفیف، بخشش بدهی.
- ویژه: فعال‌سازی رایگان.

اکشن نامعتبر برای وضعیت فعلی render نشود؛ disabled کردن ده‌ها گزینه تجربه بدی ایجاد می‌کند.

## 5.8 ماتریس درآمد

بالای جدول:

- KPI فروش، وصول، مانده، نرخ وصول.
- segmented grouping: «بر اساس سرویس» و در صورت پشتیبانی API «بر اساس مالک سهم».

ستون‌ها:

`سرویس | مالک سهم | تعداد اشتراک | فروش | وصول‌شده | مانده | نرخ وصول`

`نرخ وصول = paid / sales × 100` فقط اگر از داده response قابل محاسبه و sales > 0 باشد. footer جدول جمع ستون‌های مالی را نشان دهد.

---

# 6) Detail Drawer اشتراک

## 6.1 Header

- عنوان سرویس.
- نام کلاینت.
- StatusBadge.
- منوی عملیات مجاز.
- شناسه/کد قرارداد در متن کم‌رنگ، اگر وجود دارد.

## 6.2 خلاصه اولیه

دو بخش مجزا:

### وضعیت قرارداد

`تاریخ خرید | فعال‌سازی | شروع | انقضا | پلن | مصرف/سقف`

برای usage یک progress bar با متن `usage_used از usage_cap` نمایش داده شود. اگر سقف null است، progress bar ساخته نشود.

### وضعیت مالی

فقط برای `see_financial`:

`مبلغ نهایی | پرداخت‌شده | مانده | وضعیت پرداخت`

## 6.3 Tabهای Drawer

1. **نمای کلی**: summary و توضیحات.
2. **دوره‌ها**: timeline از `periods[]`.
3. **پرداخت‌ها**: ledger از `payments[]`، فقط نقش مالی.
4. **تاریخچه تغییرات**: timeline از `audit_logs[]`.

Timelineها جدیدترین مورد را بالا نشان دهند. actor، action، reason/note و تاریخ کامل مشخص باشد. وقتی reason وجود ندارد، «بدون توضیح» با tone خنثی نمایش داده شود؛ متن جعلی ساخته نشود.

---

# 7) طراحی دقیق عملیات و مودال‌ها

تمام اکشن‌ها از یک موتور فرم schema-based استفاده کنند تا validation، loading، error و audit note یکسان باشد.

## 7.1 فرم مشترک

هر action شامل:

- خلاصه target: کلاینت، سرویس، وضعیت فعلی.
- شرح تغییر: وضعیت فعلی → وضعیت جدید.
- فیلدهای مخصوص action.
- `reason` اجباری برای اکشن‌های دسترسی/بدهی.
- `note` اختیاری برای پرداخت/تمدید در صورت اجازه API.
- خلاصه نهایی قبل از CTA.

## 7.2 قرارداد UI اکشن‌ها

| Action | کنترل‌های لازم | متن CTA | نوع |
|---|---|---|---|
| activate | reason | فعال‌کردن سرویس | primary |
| deactivate | reason + هشدار قطع gate | غیرفعال‌کردن سرویس | danger |
| suspend | reason | تعلیق سرویس | warning |
| unsuspend | reason | رفع تعلیق | primary |
| block | reason + هشدار مسدودی | مسدودکردن سرویس | danger |
| restore | reason | بازگردانی سرویس | primary |
| extend_days | عدد روز مثبت + reason | افزودن روز | primary |
| renew | پلن/دوره، تاریخ، مبلغ‌های برگشتی API، reason | ثبت تمدید | primary |
| change_plan | plan جدید + preview تغییر | تغییر پلن | primary |
| register_payment | مبلغ، روش، تاریخ پرداخت، reference/note | ثبت پرداخت | success |
| apply_discount | نوع/مقدار تخفیف + reason + preview مبلغ | اعمال تخفیف | warning |
| forgive_debt | مبلغ بدهی + reason اجباری + checkbox تأیید | بخشش بدهی | danger |
| free_activate | تعداد روز + reason | فعال‌سازی رایگان | warning |

قواعد validation:

- مبلغ پرداخت بیشتر از مانده فقط در صورت پشتیبانی صریح API مجاز باشد.
- عدد روز و مبلغ منفی/صفر پذیرفته نشود.
- تغییر plan به plan فعلی ممنوع.
- اکشن مالی هنگام submit دوباره با capability بررسی شود.
- خطای field-level کنار فیلد و خطای عمومی بالای footer نمایش داده شود.
- modal تا پایان request بسته نشود و submit دوباره غیرفعال باشد.

## 7.3 عملیات گروهی

با انتخاب اولین ردیف، یک BulkBar چسبان پایین صفحه نمایش داده شود:

- تعداد انتخاب.
- پاک‌کردن انتخاب.
- اکشن‌های مشترک و مجاز بین همه selectedها.
- activate، deactivate، ارسال پیامک انقضا.

پیش از اجرا modal خلاصه نشان دهد:

- تعداد کل.
- موارد قابل اجرا.
- موارد ردشده و دلیل.
- reason/note.

نتیجه bulk به شکل summary `موفق / ناموفق / ردشده` و امکان دیدن جزئیات هر ردیف نمایش داده شود. پس از موفقیت selection پاک و لیست refetch شود.

---

# 8) Permission و امنیت نمایشی

| قابلیت | admin | finance | project manager | support |
|---|---:|---:|---:|---:|
| مشاهده مالی | بله | بله | بله | خیر |
| مشاهده سهم/هزینه هلدینگ | بله | بله | خیر | خیر |
| تغییر وضعیت | بله | خیر | بله | خیر |
| ثبت پرداخت | بله | بله | خیر | خیر |
| خروجی | بله | بله | بله | خیر |
| عملیات گروهی | بله | خیر | بله | خیر |

قواعد پیاده‌سازی:

- یک `useHqCapabilities()` مرکزی داشته باش.
- route guard، tab visibility، column visibility، action visibility و request initiation همگی از همین capability map استفاده کنند.
- صرفاً مخفی‌کردن button کافی نیست؛ handler و مسیر فراخوانی API نیز guard شود.
- support هیچ total، tooltip، export payload یا computed مالی در DOM دریافت نکند.
- پاسخ 403 با پیام «دسترسی این عملیات برای نقش شما فعال نیست» نمایش داده شود و UI refetch شود.

---

# 9) قرارداد داده و همگام‌سازی واقعی

## 9.1 Single source of truth

- Reports store: snapshot گزارش HQ برای range فعال.
- Carwash report cache: کلید `tenantId + start + end`.
- Services store: `reportKey + filters + pagination + ordering`.
- Subscription detail cache: کلید subscription id.

KPIها و جداول یک view نباید با requestهای دارای فیلتر متفاوت ساخته شوند. timestamp response در store نگهداری و در header نمایش داده شود.

## 9.2 URL state

نمونه گزارش:

```text
/hq/reports?workspace=network&networkTab=revenue&range=month&compare=1&health=risk&page=1
```

نمونه سرویس:

```text
/hq/services?report=license&status=near_expiry&payment=partial&tenant=42&ordering=ends_at&page=1
```

Back/forward مرورگر باید دقیقاً view قبلی را برگرداند.

## 9.3 Refresh پس از mutation

| عملیات | داده‌های invalidate‌شونده |
|---|---|
| تغییر وضعیت سرویس | subscription list، detail، summary، alerts، client services |
| ثبت پرداخت/تخفیف/بخشش | موارد بالا + revenue report |
| renew/change plan | list، detail periods، summary، reports، client services |
| bulk | تمام queryهای report فعال + summary + alerts |
| seed catalog | catalog، filter options، تمام reportهای وابسته |

Optimistic update فقط برای فیلدهای کم‌ریسک و برگشت‌پذیر مجاز است. عملیات مالی و وضعیت دسترسی تا پاسخ موفق server optimistic نشوند.

## 9.4 Formatters مرکزی

فقط helperهای مرکزی استفاده شوند:

- `formatMoney(value)` با مدیریت null و صفر.
- `formatFaNumber(value)`.
- `formatJalaliDate(value)`.
- `formatJalaliDateTime(value)`.
- `formatPercent(value)`؛ null برابر «—».
- `formatRelativeDate(value)`.
- `getStatusMeta(status)`.
- `getHealthMeta(health)`.
- `getShareOwnerMeta(owner)`.

هیچ formatter تکراری در componentهای صفحه تعریف نشود.

---

# 10) Loading، Empty، Error و Success states

## Loading

- اولین بار: skeleton متناسب با layout واقعی.
- refetch: داده قبلی باقی بماند و indicator کوچک نمایش داده شود.
- table: ۸ ردیف skeleton؛ spinner وسط صفحه ممنوع.
- Drawer: skeleton header و sectionها.

## Empty

Empty state باید دلیل را تشخیص دهد:

- بدون داده در بازه: «در این بازه داده‌ای ثبت نشده است.»
- بدون نتیجه فیلتر: «نتیجه‌ای با این فیلترها پیدا نشد.» + پاک‌کردن فیلتر.
- بدون انتخاب کارواش: راهنمای انتخاب.
- بدون alert: پیام مثبت «هشدار فعالی وجود ندارد.»
- بدون سابقه پرداخت/دوره/audit: متن همان بخش.

## Error

- خطای section با retry همان section.
- خطای کل صفحه فقط وقتی endpoint پایه شکست خورده باشد.
- error message فنی backend مستقیم به کاربر نشان داده نشود؛ متن قابل فهم + کد پیگیری در صورت وجود.
- toast برای success کوتاه و دقیق: «پرداخت با موفقیت ثبت شد.»

---

# 11) Responsive behavior

| عرض | رفتار |
|---|---|
| `≥1280` | layout کامل، ۴ KPI در ردیف، split view کارواش |
| `1024–1279` | ۲ یا ۳ KPI، sidebar باریک‌تر، جدول scroll افقی |
| `768–1023` | KPI دو ستونه، انتخاب کارواش combobox، Drawer حدود 80vw |
| `<768` | KPI تک/دو ستونه، toolbar چندردیفی، Drawer تمام‌صفحه، tab افقی |

در موبایل:

- جدول مالی به card list تبدیل نشود مگر برای عرض بسیار کم و فقط در viewهای ساده؛ حفظ header و scroll افقی برای حسابرسی بهتر است.
- ستون sticky اصلی و عملیات حفظ شود.
- modal عملیات تمام‌صفحه با footer ثابت باشد.
- chart حداقل ارتفاع 260px و tooltip لمسی داشته باشد.

---

# 12) Accessibility و تعامل

- تمام inputها label واقعی داشته باشند.
- tabها با semantics صحیح `tablist/tab/tabpanel`.
- Drawer و Modal focus trap و بازگشت focus به trigger.
- tooltip تنها منبع یک اطلاعات حیاتی نباشد.
- contrast متن و status حداقل WCAG AA.
- checkbox انتخاب گروهی label قابل دسترس داشته باشد.
- نمودارها summary متنی کوتاه و legend قابل keyboard داشته باشند.
- target لمسی حداقل 40×40px.
- حرکت‌ها 150–220ms و با `prefers-reduced-motion` قابل حذف باشند.

---

# 13) ساختار پیشنهادی فرانت‌اند Vue

نام‌ها با معماری فعلی پروژه تطبیق داده شوند؛ ساختار پیشنهادی:

```text
src/
  modules/hq/
    components/
      shared/
        HqPageHeader.vue
        HqKpiCard.vue
        HqStatusBadge.vue
        HqFilterBar.vue
        HqDataTable.vue
        HqEmptyState.vue
        HqErrorState.vue
        HqDetailDrawer.vue
      reports/
        ReportControlBar.vue
        InternalReportView.vue
        CarwashReportView.vue
        WalletLedgerView.vue
        NetworkReportView.vue
        TenantWalletDrawer.vue
      services/
        ServicesSummary.vue
        ServicesReportTabs.vue
        ServicesTable.vue
        RevenueMatrix.vue
        ClientContextPanel.vue
        ServiceAlertsDrawer.vue
        SubscriptionDetailDrawer.vue
        SubscriptionActionForm.vue
        BulkActionBar.vue
    composables/
      useHqCapabilities.ts
      useHqReportFilters.ts
      useHqReports.ts
      useHqServices.ts
      useSubscriptionActions.ts
    constants/
      hq-status-meta.ts
      hq-table-columns.ts
      hq-report-tabs.ts
    utils/
      formatters.ts
      query-state.ts
```

از یک component غول‌آسا برای همه tabها استفاده نشود. هر workspace request/state مشخص داشته باشد و shared componentها صرفاً presentation مشترک را پوشش دهند.

---

# 14) نگاشت API به صفحه

## گزارشات

| API | مصرف |
|---|---|
| `GET /auth/hq/reports/?start=&end=` | summary، rows، trends، feature_summary، wallet_transactions، highlights |
| `GET /auth/hq/carwashes/{id}/reports/?start=&end=` | گزارش کامل کارواش انتخابی و ساب‌تب‌ها |

## سرویس‌ها

| API | مصرف |
|---|---|
| `GET /subscriptions/hq/catalog/` | گزینه پروژه، محصول و plan |
| `GET /subscriptions/hq/summary/` | KPIهای نقش‌محور |
| `GET /subscriptions/hq/subscriptions/` | جدول همه سرویس‌ها |
| `GET /subscriptions/hq/subscriptions/{id}/` | Detail Drawer |
| `POST /subscriptions/hq/subscriptions/{id}/actions/` | عملیات تکی |
| `GET /subscriptions/hq/clients/{tenant_id}/services/` | Client context و فرصت فروش |
| `GET /subscriptions/hq/alerts/` | Alert Center |
| `GET /subscriptions/hq/reports/{report_key}/` | گزارش تخصصی هر tab |
| `GET /subscriptions/hq/revenue/` | ماتریس درآمد |
| `GET /subscriptions/hq/export/` | خروجی مطابق فیلتر فعال |
| `POST /subscriptions/hq/bulk/` | عملیات گروهی |
| `POST /subscriptions/hq/seed/` | sync/seed کاتالوگ فقط admin |
| `POST /subscriptions/hq/orders/` | سفارش خرید/تمدید |

Export باید دقیقاً query فعال، ترتیب و permission کاربر را رعایت کند؛ export داده مالی برای support نباید امکان‌پذیر باشد.

---

# 15) پیوست قرارداد قطعی داده و محاسبات

این بخش برای جلوگیری از تغییر ناخواسته مفهوم شاخص‌هاست. Frontend نباید این قواعد را با برداشت بصری یا محاسبه متفاوت جایگزین کند.

## 15.1 دامنه داده گزارشات HQ

فقط کارواش‌هایی وارد گزارش می‌شوند که هم‌زمان شرایط زیر را داشته باشند:

```text
is_active = true
exclude_from_hq_reports = false
is_sample = false
```

بازه‌های استاندارد:

| UI | `rangeKey` | قرارداد |
|---|---|---|
| روز | `day` | امروز |
| هفته | `week` | ۷ روز اخیر |
| ماه | `month` | ماه جاری و پیش‌فرض |
| کل تاریخ | `all` | بدون start/end |

مقایسه دوره قبل فقط وقتی start و end وجود دارد انجام می‌شود و باید همان طول بازه قبلی را مقایسه کند.

## 15.2 منطق قطعی سهم کارنو و آراکار در گزارشات

| API | label | مفهوم |
|---|---|---|
| `hq` | کارنو | SMS، باشگاه، ورود اکسل، حضور و غیاب |
| `rah` | آراکار | لایسنس، فضای ابری و برداشت‌های عملیاتی غیرکارنو |
| `none` | بدون سهم | تمام واریزها؛ شارژ کیف پول سهم محسوب نمی‌شود |

```text
direction = in
  => none

wallet_type = sms
or reference_type in (
  customer_import_excel,
  sms_campaign_send,
  vehicle_assigned_sms,
  vehicle_released_sms,
  system_sms
)
  => hq

reference_type = feature_option_*
  => share group همان feature

سایر برداشت‌ها
  => rah
```

`hq_share_total` و `rah_share_total` از برداشت‌های کیف پول محاسبه می‌شوند، نه از مبلغ فاکتور سفارش کارواش. این دو مفهوم هرگز با سهم مالک محصول در صفحه سرویس‌ها ادغام نشوند.

## 15.3 قابلیت‌ها در گزارش داخلی

| `feature_key` | label | share |
|---|---|---|
| `sms_club` | پنل باشگاه مشتریان پیشرفته | `hq` |
| `excel_import` | وارد کردن مشتریان با اکسل | `hq` |
| `attendance` | ورود و خروج | `hq` |
| `core_software` | لایسنس اصلی نرم‌افزار | `rah` |
| `cloud_storage` | فضای ابری | `rah` |

## 15.4 Data dictionary گزارش HQ

### `summary`

| فیلد | تعریف | محل نمایش اصلی |
|---|---|---|
| `tenants_count` | تعداد کارواش‌های visible | metadata/overview |
| `active_tenants_count` | tenant دارای فعالیت مالی یا عملیاتی | overview |
| `vehicles_count` | تعداد `VehicleEntry` | شبکه/کارواش |
| `released_count` | خودروهای RELEASED | جزئیات عملکرد |
| `cancelled_count` | خودروهای CANCELLED | جزئیات عملکرد |
| `paid_amount` | مجموع Payment موفق | درآمد شبکه |
| `final_total` | مبلغ نهایی snapshot | درآمد |
| `before_discount_total` | مبلغ + تخفیف | شبکه/کارواش |
| `expense_total` | خرید انبار + هزینه دستی | تحلیل خالص |
| `net_total` | paid − expense | KPI شبکه |
| `pending_amount` | Payment در وضعیت PENDING | مطالبات |
| `payments_count` | تعداد پرداخت موفق | جدول شبکه |
| `tips_total` | مجموع انعام | گزارش کارواش |
| `discount_total` | مجموع تخفیف | گزارش شبکه/کارواش |
| `services_total` | فروش خدمات | جزئیات درآمد |
| `products_total` | فروش کالا | جزئیات درآمد |
| `average_ticket` | paid / vehicles | تحلیل شبکه |
| `completion_rate` | released / vehicles × 100 | جزئیات عملکرد |
| `collection_rate` | paid / (paid + pending) × 100 | KPI شبکه |
| `wallet_balance_total` | مجموع موجودی کیف فعال | کیف پول |
| `wallet_deposit_total` | مجموع IN بازه | کیف پول |
| `wallet_withdraw_total` | مجموع OUT بازه | کیف پول |
| `wallet_gateway_charge_total` | IN مرجع درگاه | کیف پول |
| `wallet_manual_charge_total` | سایر INها | کیف پول |
| `wallet_sms_balance_total` | موجودی کیف SMS | کیف پول |
| `hq_share_total` | سهم کارنو از برداشت‌ها | داخلی HQ |
| `rah_share_total` | سهم آراکار از برداشت‌ها | داخلی HQ |
| `unallocated_wallet_total` | تراکنش‌های `none` | جزئیات/حسابرسی |
| `sms_sent_count` | تعداد NotificationLog SENT | کیف/SMS |
| `sms_cost_total` | OUT کیف SMS | کیف/SMS |
| `feature_income_total` | مبلغ قابلیت‌ها | جزئیات قابلیت |
| `feature_paid_total` | وصول قابلیت‌ها | جزئیات قابلیت |
| `feature_remaining_total` | مانده خرید قابلیت‌ها | KPI داخلی |
| `revenue_change_percent` و مشابه | تغییر نسبت به دوره قبل | badge KPI |
| `date_start`, `date_end` | echo بازه API | کنترل صحت/نمایش بازه |

### `rows[]` هر tenant

علاوه بر مقادیر summary همان tenant:

```text
feature_breakdown[]
share_breakdown { hq, rah, none }
rank
health
wallet_charge_health
wallet_gateway_charge_count
active_queue_count
refunded_total
last_activity_at
```

### `feature_summary[]`

```text
key, label, tab_label, description,
total_amount, paid_amount, remaining_amount,
active_count, purchase_count
```

### `wallet_transactions[]`

حداکثر ۲۵۰ ردیف اخیر:

```text
tenant_name, wallet_name, wallet_type,
direction, amount, description, reference_type,
transacted_at, created_by_name, share_group,
share_amount, hq_share_amount, rah_share_amount
```

### `trends[]`

```text
date, vehicles_count, paid_amount, expense_total,
wallet_deposit_total, wallet_withdraw_total,
hq_share_total, rah_share_total, sms_cost_total,
net_amount, wallet_net_flow
```

### `highlights`

```text
top_revenue, top_volume, top_margin,
top_wallet_balance, top_wallet_deposit,
wallet_watchlist, watchlist
```

## 15.5 الگوریتم‌های سلامت

Frontend فقط label و style را map کند و نتیجه را دوباره محاسبه نکند.

### `health`

- `risk`: خالص منفی یا مطالبات حداقل ۳۵٪ درآمد.
- `strong`: نرخ تکمیل حداقل ۸۰٪ و خالص مثبت.
- `stable`: فعالیت وجود دارد ولی strong/risk نیست.
- `idle`: بدون فعالیت.

### `wallet_charge_health`

- `empty`: موجودی ≤ ۰ ولی تراکنش وجود دارد.
- `sms_heavy`: موجودی SMS بیشتر از عادی.
- `gateway`: شارژ درگاه حداقل شارژ دستی.
- `healthy`: موجودی مثبت.
- `idle`: بدون داده.

## 15.6 کاتالوگ سرویس و مالک سهم

| `product_key` | عنوان | `share_owner` |
|---|---|---|
| `core_software` | لایسنس اصلی نرم‌افزار | `arakar` |
| `cloud_storage` | فضای ابری | `arakar` |
| `wallet` | کیف پول | `carno` |
| `attendance` | ورود و خروج | `carno` |
| `sms_club` | پنل پیشرفته مشتریان | `carno` |
| `sms_panel` | پنل پیامک | `carno` |
| `sms_credit` | بسته/اعتبار پیامک | `carno` |
| `excel_import` | ورود اکسل | `carno` |
| `accounting` | حسابداری | `none` |
| `custom_addon` | افزونه اختصاصی | `none` |

محاسبه مبلغ پلن:

```text
base → discount percent → taxable amount → tax percent → final amount
```

مالیات پیش‌فرض فعلی ۱۰٪ است، اما UI باید مقدار واقعی API/پلن را نمایش دهد و آن را hardcode نکند.

ثابت فعلی SMS در سرویس: هزینه ۱۴۵ + سود ۴۰ = صورتحساب ۱۸۵ به ازای ۱۰۰ پیامک. نمایش این breakdown فقط وقتی endpoint همان اعداد را برمی‌گرداند انجام شود.

## 15.7 Status dictionary سرویس‌ها

### وضعیت اشتراک

```text
active, inactive, expired, near_expiry,
blocked, suspended, pending_payment,
pending_activation, cancelled, trial, not_renewed
```

### وضعیت پرداخت

```text
settled, partial, unpaid, overdue, early
```

Label فارسی، tone و icon تمام این enumها باید در فایل metadata مرکزی تعریف شود. مقدار ناشناخته با badge خنثی و خود مقدار API نمایش داده و در monitoring ثبت شود؛ صفحه نباید crash کند.

## 15.8 ساختار جزئیات اشتراک

```text
Subscription detail
  product_title
  client_name
  status
  purchased_at
  activated_at
  starts_at / ends_at
  final_amount / paid_amount / remaining_amount
  usage_used / usage_cap
  periods[]: kind, starts, ends, final_amount
  payments[]: amount, method, paid_at
  audit_logs[]: action, actor, reason, note, created_at
```

تاریخچه دوره‌ها append-only است و نباید در UI به‌عنوان یک رکورد قابل ویرایش مستقیم نمایش داده شود.

---

# 16) معیارهای پذیرش نهایی

## تجربه کاربری

- [ ] کاربر در نگاه اول تفاوت گزارش شبکه، کیف پول و سرویس‌ها را درک می‌کند.
- [ ] در هر view حداکثر ۴ KPI اصلی با وزن بصری بالا وجود دارد.
- [ ] هر جدول فیلتر، sort، loading، empty، error و pagination صحیح دارد.
- [ ] هیچ modal شلوغی برای نمایش جزئیات طولانی استفاده نشده و جزئیات در Drawer است.
- [ ] اکشن‌ها فقط در context معتبر و برای نقش مجاز نمایش داده می‌شوند.
- [ ] بازگشت مرورگر فیلتر و tab قبلی را حفظ می‌کند.

## صحت داده

- [ ] هیچ مبلغ یا درصد ساختگی وجود ندارد.
- [ ] سهم گزارشات از wallet OUT و سهم سرویس‌ها از product owner تفکیک شده است.
- [ ] null با صفر اشتباه گرفته نمی‌شود.
- [ ] KPI و جدول یک view بازه و فیلتر مشترک دارند.
- [ ] بعد از عملیات، تمام داده‌های وابسته refetch می‌شوند.
- [ ] متن محدودیت ۲۵۰ تراکنش لجر نمایش داده می‌شود.

## نقش‌ها

- [ ] support هیچ داده مالی در DOM یا export نمی‌بیند.
- [ ] finance عملیات وضعیت یا bulk غیرمجاز ندارد.
- [ ] project manager سهم/هزینه هلدینگ را نمی‌بیند.
- [ ] admin تمام امکانات مجاز را دارد.

## کیفیت فنی

- [ ] تمام statusها و formatterها مرکزی هستند.
- [ ] requestهای search debounce و request قبلی cancel می‌شوند.
- [ ] loading باعث layout shift شدید نمی‌شود.
- [ ] table و listهای بزرگ performance قابل قبول دارند.
- [ ] همه Drawer/Modalها keyboard accessible هستند.
- [ ] در desktop، tablet و mobile تست شده است.

---

# 17) ترتیب پیشنهادی توسعه

1. استخراج tokenها، formatterها، status meta و capability map.
2. ساخت shell مشترک: PageHeader، FilterBar، KPI، Table، Drawer و stateها.
3. بازطراحی Workspace navigation و URL state گزارشات.
4. پیاده‌سازی Internal، Wallet، Network و سپس Carwash report.
5. بازطراحی Services summary، tabs، filter و table.
6. Detail Drawer و Alert Drawer.
7. Action forms و Bulk flow با invalidation کامل.
8. responsive، accessibility، performance و تست نقش‌ها.

در پایان هر مرحله، صفحه با داده واقعی API و حداقل این سناریوها تست شود: داده زیاد، داده خالی، null، صفر، خطای API، پاسخ کند، role محدود، بازه کل تاریخ و mutation موفق/ناموفق.

---

# نتیجه مورد انتظار

خروجی نهایی باید پنلی باشد که در آن «اطلاعات زیاد» همچنان کامل باقی می‌ماند، اما بر اساس اهمیت و هدف کاربر لایه‌بندی می‌شود. مدیر HQ ابتدا وضعیت را می‌بیند، سپس علت را تحلیل می‌کند و در نهایت بدون گم‌کردن context وارد جزئیات یا عملیات می‌شود.
