<template>
  <main class="landing-page" dir="rtl">
    <div class="page-shell">
      <header class="header">
        <a class="brand" href="#home" aria-label="کارنوواش" @click.prevent="scrollTo('home')">
          <img :src="logoImg" alt="لوگو نرم افزار مدیریت کارواش کارنوواش" width="47" height="47" />
          <span>کارنوواش</span>
        </a>

        <nav class="nav" aria-label="منوی اصلی">
          <a
            v-for="item in navItems"
            :key="item.id"
            :href="item.href || `#${item.id}`"
            :class="{ active: !item.external && activeSection === item.id }"
            :target="item.external ? '_blank' : undefined"
            :rel="item.external ? 'noopener noreferrer' : undefined"
            @click="onNavClick($event, item)"
          >
            {{ item.label }}
          </a>
        </nav>

        <div class="header-actions">
          <RouterLink class="btn btn-primary" to="/login">ورود به پنل</RouterLink>
          <button
            class="menu-toggle"
            type="button"
            :aria-expanded="mobileOpen"
            aria-label="منو"
            @click="mobileOpen = !mobileOpen"
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </header>

      <Transition name="drawer">
        <div v-if="mobileOpen" class="mobile-drawer" @click.self="mobileOpen = false">
          <nav class="mobile-nav" aria-label="منوی موبایل">
            <a
              v-for="item in navItems"
              :key="`m-${item.id}`"
              :href="item.href || `#${item.id}`"
              :target="item.external ? '_blank' : undefined"
              :rel="item.external ? 'noopener noreferrer' : undefined"
              @click="onNavClick($event, item)"
            >
              <IconlyIcon :name="item.icon" size="sm" tone="brand" />
              {{ item.label }}
            </a>
            <div class="mobile-nav-actions">
              <RouterLink class="btn btn-primary" to="/login" @click="mobileOpen = false">ورود به پنل</RouterLink>
            </div>
          </nav>
        </div>
      </Transition>

      <section class="hero" id="home">
        <div class="hero-copy">
          <h1>
            نرم‌افزار مدیریت کارواش
            <strong>کارنوواش</strong>
          </h1>
          <p>
            کارنوواش (CarnoWash) سامانه یکپارچه مدیریت کارواش برای مالکان، مدیران و اپراتورهاست؛
            از پذیرش خودرو و پلاک‌خوان تا پرداخت، گزارش مالی، پیامک و باشگاه مشتریان.
          </p>
          <div class="hero-actions">
            <a class="btn btn-outline btn-lg" href="#features" @click.prevent="scrollTo('features')">
              <IconlyIcon name="play" size="lg" tone="brand" />
              مشاهده امکانات
            </a>
            <RouterLink class="btn btn-primary btn-lg" to="/login">
              ورود به پنل
              <IconlyIcon name="arrowLeft" size="md" tone="white" />
            </RouterLink>
          </div>
          <div class="social-proof">
            <div class="avatars" aria-hidden="true">
              <span>م</span><span>ع</span><span>ر</span><span>س</span>
            </div>
            <div>
              <b>با اعتماد کارواش‌داران</b>
              <small>بیش از ۲۴ کارواش در سراسر کشور</small>
            </div>
          </div>
        </div>

        <div class="hero-visual" aria-label="نمای سه بعدی داشبورد کارنوواش">
          <picture>
            <source media="(max-width: 820px)" srcset="/hero-3d-mobile.webp" type="image/webp" />
            <source srcset="/hero-3d.webp" type="image/webp" />
            <img
              src="/hero-3d.webp"
              alt="داشبورد مدیریت خودروها در نرم افزار کارنوواش"
              width="720"
              height="720"
              decoding="async"
              fetchpriority="high"
              loading="eager"
            />
          </picture>
        </div>
      </section>

      <section class="features-section" id="features">
        <div class="section-heading">
          <h2>همه چیز برای <em>مدیریت آسان</em> کارواش شما</h2>
          <p>کارنوواش با ابزارهای هوشمند و یکپارچه، تمام نیازهای مدیریت کارواش شما را پوشش می‌دهد.</p>
        </div>

        <div class="features-grid">
          <article
            v-for="(feature, index) in features"
            :key="feature.title"
            class="feature-card"
            :style="{ '--delay': `${index * 60}ms` }"
          >
            <div class="feature-icon">
              <IconlyIcon :name="feature.icon" size="2xl" tone="brand" />
            </div>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.text }}</p>
          </article>
        </div>

        <div class="stats">
          <div v-for="stat in stats" :key="stat.label">
            <span class="stat-icon">
              <IconlyIcon :name="stat.icon" size="3xl" tone="white" />
            </span>
            <b>{{ stat.value }}</b>
            <small>{{ stat.label }}</small>
          </div>
        </div>

        <section class="mobile-showcase" id="about">
          <div class="mobile-copy">
            <span class="eyebrow">همیشه و همیشه در دسترس</span>
            <h2>مدیریت از هر دستگاه، در هر زمان</h2>
            <p>
              با اپلیکیشن موبایل کارنوواش، کارواش خود را در هر زمان و مکان
              مدیریت کنید و به داده‌های کارواش خود دسترسی داشته باشید.
            </p>
            <div class="platforms">
              <button type="button" v-for="platform in platforms" :key="platform.label">
                <span class="platform-icon" :class="platform.tone">
                  <IconlyIcon :name="platform.icon" size="xl" :tone="platform.tone === 'android' ? 'brand' : 'muted'" />
                </span>
                <span>{{ platform.label }}</span>
              </button>
            </div>
          </div>

          <div class="mobile-visual" aria-label="اپلیکیشن موبایل کارنوواش">
            <img
              :src="mobileImg"
              alt="اپلیکیشن موبایل کارنوواش روی گوشی هوشمند"
              width="460"
              height="420"
              loading="lazy"
              decoding="async"
            />
          </div>
        </section>

        <section class="cta" id="signup">
          <div class="cta-art">
            <img
              :src="ctaImg"
              alt="ایستگاه هوشمند شستشوی خودکار خودرو"
              width="420"
              height="280"
              loading="lazy"
              decoding="async"
            />
          </div>
          <div class="cta-copy">
            <div>
              <h2>آماده ارتقای کسب‌وکار خود هستید؟</h2>
              <p>به خانواده کارنوواش بپیوندید و مدیریت کارواش خود را متحول کنید.</p>
              <RouterLink class="btn btn-primary" to="/login">
                همین حالا شروع کنید
                <IconlyIcon name="arrowLeft" size="sm" tone="white" />
              </RouterLink>
            </div>
          </div>
        </section>

        <section class="trusted">
          <h3>مورد اعتماد کارواش‌های برتر کشور</h3>
          <div class="trust-row">
            <span v-for="mark in trustMarks" :key="mark">
              <IconlyIcon name="shieldDone" size="sm" tone="muted" />
              {{ mark }}
            </span>
          </div>
        </section>
      </section>

      <section class="content-band" id="pain">
        <div class="content-panel">
          <div class="section-heading">
            <h2>کارواش‌های سنتی کجا <em>گیر می‌کنند؟</em></h2>
            <p>
              وقتی پذیرش با کاغذ، حافظه نیروها و پیام‌های پراکنده جلو می‌رود، خطای پلاک، فراموشی خدمات،
              ابهام در سهم نیرو و گزارش‌های ناقص طبیعی می‌شود. نتیجه معمولاً صف طولانی‌تر، اختلاف حساب و تجربه ضعیف برای مشتری است.
            </p>
          </div>
          <div class="pain-grid">
            <article v-for="item in painPoints" :key="item" class="pain-card">
              <IconlyIcon name="danger" size="md" tone="brand" />
              <p>{{ item }}</p>
            </article>
          </div>
          <p class="content-note">
            کارنوواش این پراکندگی را به یک جریان عملیاتی واحد تبدیل می‌کند: از ورود خودرو تا ترخیص و گزارش نهایی.
          </p>
        </div>
      </section>

      <section class="content-band" id="workflow">
        <div class="content-panel">
          <div class="section-heading">
            <h2>ساختار عملیاتی کارنوواش از <em>ورود تا ترخیص</em></h2>
            <p>سامانه حول یک مسیر واقعی کارواش طراحی شده است؛ نه فقط یک فرم ثبت، بلکه یک چرخه کامل عملیات، پرداخت و گزارش.</p>
          </div>
          <div class="workflow-grid">
            <article v-for="(step, index) in workflowSteps" :key="step.title" class="workflow-card">
              <span class="workflow-index">{{ toFaDigit(index + 1) }}</span>
              <h3>{{ step.title }}</h3>
              <ul>
                <li v-for="line in step.items" :key="line">{{ line }}</li>
              </ul>
            </article>
          </div>
          <p class="content-note">هر خودرو یک مسیر مشخص دارد؛ هر مبلغ یک منبع دارد؛ هر نیرو یک سهم شفاف دارد.</p>
        </div>
      </section>

      <section class="content-band" id="modules">
        <div class="content-panel">
          <div class="section-heading">
            <h2>همه آنچه برای <em>مدیریت واقعی</em> کارواش لازم دارید</h2>
            <p>کارنوواش فقط یک نرم‌افزار ثبت خودرو نیست. مجموعه‌ای از ماژول‌های به‌هم‌پیوسته برای عملیات روزانه، مالی، پرسنلی و ارتباط با مشتری.</p>
          </div>
          <div class="modules-grid">
            <article v-for="mod in modules" :key="mod.title" class="module-card">
              <div class="module-icon">
                <IconlyIcon :name="mod.icon" size="xl" tone="brand" />
              </div>
              <h3>{{ mod.title }}</h3>
              <p>{{ mod.text }}</p>
            </article>
          </div>
        </div>
      </section>

      <section class="content-band" id="roles">
        <div class="content-panel">
          <div class="section-heading">
            <h2>ارزش کارنوواش برای <em>هر نقش</em></h2>
            <p>از مالک تا اپراتور و نیرو؛ هر نفر مسیر شفاف خودش را دارد.</p>
          </div>
          <div class="roles-grid">
            <article v-for="role in roles" :key="role.title" class="role-card">
              <h3>{{ role.title }}</h3>
              <ul>
                <li v-for="line in role.items" :key="line">{{ line }}</li>
              </ul>
            </article>
          </div>
        </div>
      </section>

      <section class="content-band" id="compare">
        <div class="content-panel">
          <div class="section-heading">
            <h2>قبل و بعد از <em>کارنوواش</em></h2>
            <p>تفاوت عملیات سنتی با جریان یکپارچه سامانه را در یک نگاه ببینید.</p>
          </div>
          <div class="compare-table" role="table" aria-label="مقایسه قبل و بعد">
            <div class="compare-head" role="row">
              <span role="columnheader">قبل</span>
              <span role="columnheader">بعد با کارنوواش</span>
            </div>
            <div v-for="row in compareRows" :key="row.before" class="compare-row" role="row">
              <span role="cell">{{ row.before }}</span>
              <span role="cell">{{ row.after }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="content-band" id="why">
        <div class="content-panel">
          <div class="section-heading">
            <h2>چرا کارنوواش برای کارواش شما <em>منطقی</em> است؟</h2>
          </div>
          <div class="why-grid">
            <article v-for="(item, index) in whyItems" :key="item" class="why-card">
              <span>{{ toFaDigit(index + 1) }}</span>
              <p>{{ item }}</p>
            </article>
          </div>
        </div>
      </section>

      <section class="content-band" id="faq">
        <div class="content-panel">
          <div class="section-heading">
            <h2>سوالات <em>متداول</em></h2>
            <p>پاسخ‌های مستقیم برای تصمیم‌گیری سریع‌تر درباره نرم‌افزار مدیریت کارواش کارنوواش.</p>
          </div>
          <div class="faq-list">
            <details v-for="item in faqs" :key="item.q" class="faq-item">
              <summary>{{ item.q }}</summary>
              <p>{{ item.a }}</p>
            </details>
          </div>
        </div>
      </section>

      <footer class="landing-footer" id="footer">
        <div class="footer-inner">
          <div class="footer-brand">
            <img :src="logoImg" alt="لوگو کارنوواش" width="44" height="44" />
            <div>
              <strong>کارنوواش</strong>
              <span>CarnoWash</span>
            </div>
          </div>
          <p class="footer-copy">
            کارنوواش (CarnoWash) سامانه مدیریت کارواش برای پذیرش خودرو، پلاک‌خوان، خدمات، نیروها، پرداخت،
            گزارش مالی، کیف پول، حضور و غیاب و باشگاه مشتریان است. از لندینگ وارد پنل مدیریت شوید و عملیات کارواش خود را یکپارچه کنید.
          </p>
          <nav class="footer-links" aria-label="لینک‌های فوتر">
            <RouterLink to="/login">ورود به پنل</RouterLink>
            <a href="#features" @click.prevent="scrollTo('features')">نرم افزار مدیریت کارواش</a>
            <a href="#modules" @click.prevent="scrollTo('modules')">پلاک خوان</a>
            <a href="#modules" @click.prevent="scrollTo('modules')">گزارش و تسویه</a>
            <a href="#modules" @click.prevent="scrollTo('modules')">باشگاه مشتریان</a>
            <a href="#faq" @click.prevent="scrollTo('faq')">سوالات متداول</a>
            <a href="/about/">معرفی محصول</a>
            <a href="https://carnoco.ir" target="_blank" rel="noopener noreferrer">درباره ما</a>
          </nav>
          <div class="footer-bottom">
            <small>سامانه هوشمند مدیریت کارواش؛ پذیرش سریع‌تر، عملیات شفاف‌تر، درآمد دقیق‌تر.</small>
            <RouterLink class="btn btn-primary footer-cta" to="/login">ورود به پنل کارنوواش</RouterLink>
          </div>
          <div class="footer-credit">
            <p>تمامی حقوق محفوظ است</p>
            <span>Designed By DHS Development Team</span>
          </div>
        </div>
      </footer>
    </div>
  </main>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import IconlyIcon from '../../components/base/IconlyIcon.vue'
import logoImg from '../../assets/landing/logo.webp'
import mobileImg from '../../assets/landing/mobile-app-platform.webp'
import ctaImg from '../../assets/landing/automatic-carwash-station.webp'

const mobileOpen = ref(false)
const activeSection = ref('home')

const navItems = [
  { id: 'home', label: 'خانه', icon: 'home' },
  { id: 'features', label: 'امکانات', icon: 'category' },
  { id: 'workflow', label: 'گردش کار', icon: 'activity' },
  { id: 'about', label: 'درباره ما', icon: 'infoCircle', href: 'https://carnoco.ir', external: true },
  { id: 'faq', label: 'سوالات متداول', icon: 'message' }
]

const sectionIds = ['home', 'features', 'workflow', 'faq']

const features = [
  { icon: 'graph', title: 'گزارش‌های پیشرفته', text: 'گزارش‌های دقیق، قابل سفارشی‌سازی و مدیریت حرفه‌ای' },
  { icon: 'notification', title: 'اعلان‌ها و پیامک', text: 'ارسال خودکار پیامک و اطلاع‌رسانی هوشمند' },
  { icon: 'wallet', title: 'پرداخت و حسابداری', text: 'مدیریت پرداخت‌ها و گزارش‌های مالی دقیق' },
  { icon: 'calendar', title: 'نوبت‌دهی آنلاین', text: 'سیستم نوبت‌دهی و زمان‌بندی هوشمند' },
  { icon: 'users3', title: 'مدیریت مشتریان', text: 'ثبت مشتریان، دسته‌بندی و امتیازدهی' },
  { icon: 'category', title: 'داشبورد هوشمند', text: 'نمای کلی و لحظه‌ای از کارواش در یک نگاه' }
]

const stats = [
  { icon: 'timeCircle', value: '+۵۰٬۰۰۰', label: 'ساعت صرفه‌جویی' },
  { icon: 'activity', value: '+۱.۵M', label: 'درآمد کل ماهانه' },
  { icon: 'heart', value: '+۱۳۰', label: 'افزایش تکرار' },
  { icon: 'star', value: '۹۸٪', label: 'رضایت مشتریان' }
]

const platforms = [
  { label: 'iOS', icon: 'discovery', tone: '' },
  { label: 'اندروید', icon: 'tickSquare', tone: 'android' },
  { label: 'وب اپلیکیشن', icon: 'show', tone: '' }
]

const trustMarks = ['Power Shine', 'AQUA WASH', 'CLEAN CAR', 'EcoWash', 'WashTech', 'CAR DETAIL']

const painPoints = [
  'ثبت دستی و پراکنده پلاک و مشخصات خودرو',
  'نداشتن دید لحظه‌ای از وضعیت خودروهای داخل سالن',
  'محاسبه سخت سهم نیرو، انعام و درآمد کارواش',
  'نبود سابقه دقیق مشتری و مراجعه بعدی',
  'اطلاع‌رسانی دیر یا ناقص به مشتری',
  'گزارش‌های مالی غیرقابل‌اتکا برای تصمیم‌گیری'
]

const workflowSteps = [
  {
    title: 'پذیرش خودرو',
    items: ['ثبت پلاک به‌صورت دستی یا با پلاک‌خوان', 'ثبت مدل، رنگ، نام و شماره تماس مشتری', 'شروع پرونده سفارش در لحظه ورود']
  },
  {
    title: 'تخصیص خدمات و نیرو',
    items: ['انتخاب خدمات کارواش', 'تخصیص نیروی انجام‌دهنده', 'تعیین سهم نیرو و مشاهده خلاصه فاکتور']
  },
  {
    title: 'اجرای سفارش و پیگیری',
    items: ['داشبورد کارت‌محور خودروها', 'فیلتر وضعیت‌های عملیاتی', 'جست‌وجو بر اساس پلاک یا نام']
  },
  {
    title: 'فروش مکمل و ترخیص',
    items: ['فروش محصولات جانبی از انبار', 'تکمیل مبلغ نهایی قبل از تسویه']
  },
  {
    title: 'پرداخت، انعام و فاکتور',
    items: ['ثبت پرداخت دستی یا POS', 'محاسبه انعام', 'صدور فاکتور و آماده‌سازی پیامک']
  },
  {
    title: 'ترخیص و گزارش',
    items: ['نهایی‌سازی سفارش', 'ثبت در گزارش‌های مالی و عملیاتی', 'آماده‌سازی تسویه نیرو']
  }
]

const modules = [
  { icon: 'document', title: 'پذیرش سریع خودرو', text: 'ثبت پلاک، مشتری و سفارش در یک مسیر واحد' },
  { icon: 'scan', title: 'پلاک‌خوان هوشمند', text: 'کاهش خطای تایپ و سرعت بالاتر پذیرش' },
  { icon: 'category', title: 'داشبورد عملیاتی', text: 'همه خودروها و وضعیت‌ها جلوی چشم' },
  { icon: 'users3', title: 'تخصیص خدمات و نیرو', text: 'هر کار، یک مسئول و یک مبلغ مشخص' },
  { icon: 'wallet', title: 'پرداخت و فاکتور', text: 'تسویه شفاف با ثبت انعام و مبلغ نهایی' },
  { icon: 'graph', title: 'گزارش مالی', text: 'درآمد کارواش، سهم نیرو و انعام جداگانه' },
  { icon: 'profile', title: 'باشگاه مشتریان', text: 'سابقه مراجعه و بازگشت هدفمند' },
  { icon: 'message', title: 'پیامک اطلاع‌رسانی', text: 'مشتری در جریان وضعیت خودرو' },
  { icon: 'calendar', title: 'حضور و غیاب', text: 'کارکرد نیروها دقیق و قابل گزارش' },
  { icon: 'buy', title: 'کیف پول سامانه', text: 'مدیریت مالی و فعال‌سازی قابلیت‌ها' },
  { icon: 'work', title: 'انبار و فروش مکمل', text: 'افزایش درآمد هر پذیرش' },
  { icon: 'setting', title: 'پنل چندشعبه', text: 'کنترل متمرکز مجموعه‌های بزرگ‌تر' }
]

const roles = [
  {
    title: 'مالک / مدیر',
    items: ['شفافیت درآمد روزانه و دوره‌ای', 'کنترل سهم نیرو و انعام', 'تصمیم‌گیری بر اساس گزارش واقعی', 'امکان رشد به چندشعبه']
  },
  {
    title: 'اپراتور پذیرش',
    items: ['ثبت سریع‌تر خودرو', 'داشبورد واضح از وضعیت‌ها', 'کاهش رفت‌وبرگشت تلفنی و کاغذی', 'کاهش خطای پلاک و مبلغ']
  },
  {
    title: 'نیروی کار',
    items: ['شفافیت کارهای تخصیص‌یافته', 'مشخص بودن سهم و انعام', 'ثبت ساده حضور و غیاب']
  },
  {
    title: 'مشتری نهایی',
    items: ['اطلاع‌رسانی بهتر', 'تجربه حرفه‌ای‌تر تحویل', 'سابقه مراجعه و ارتباط هدفمند بعدی']
  }
]

const compareRows = [
  { before: 'ثبت پلاک با عجله و خطا', after: 'پذیرش کنترل‌شده + پلاک‌خوان' },
  { before: 'وضعیت خودرو در ذهن نیروها', after: 'داشبورد وضعیت لحظه‌ای' },
  { before: 'سهم نیرو روی کاغذ', after: 'محاسبه و تسویه سیستمی' },
  { before: 'پیام به مشتری نامنظم', after: 'پیامک ساختاریافته' },
  { before: 'گزارش مبهم پایان روز', after: 'گزارش‌های مالی و عملیاتی' },
  { before: 'رشد شعبه = پیچیدگی بیشتر', after: 'آمادگی برای مدیریت چندشعبه' }
]

const whyItems = [
  'طراحی‌شده برای عملیات واقعی کارواش؛ نه یک CRM عمومی که به زور به کارواش بچسبانید.',
  'پوشش end-to-end از پذیرش تا ترخیص، پرداخت، گزارش و ارتباط با مشتری.',
  'پلاک‌خوان و پذیرش سریع برای کاهش صف و خطا.',
  'شفافیت مالی برای مالک، نیرو و حسابداری.',
  'قابلیت رشد ماژولار؛ از نیازهای پایه تا باشگاه مشتریان، پیامک، حضور و غیاب و چندشعبه.',
  'مناسب بازار ایران؛ زبان فارسی، پلاک ایرانی، سناریوی واقعی کارواش داخلی.'
]

const faqs = [
  {
    q: 'کارنوواش چیست؟',
    a: 'کارنوواش (CarnoWash) یک سامانه مدیریت کارواش است که پذیرش خودرو، خدمات، نیروها، پرداخت، گزارش مالی، پیامک و باشگاه مشتریان را در یک پنل یکپارچه مدیریت می‌کند.'
  },
  {
    q: 'آیا کارنوواش برای مشتری نهایی (رزرو آنلاین عمومی) است؟',
    a: 'نسخه اصلی محصول، سامانه عملیاتی و مدیریتی داخل کارواش است. مشتری نهایی به‌صورت غیرمستقیم از پذیرش دقیق‌تر، اطلاع‌رسانی و تجربه بهتر بهره می‌برد.'
  },
  {
    q: 'پلاک‌خوان چگونه کمک می‌کند؟',
    a: 'با تشخیص پلاک از دوربین یا تصویر، سرعت پذیرش بالا می‌رود و خطای تایپ پلاک کم می‌شود. در صورت نیاز، نتیجه قابل اصلاح دستی است.'
  },
  {
    q: 'آیا سهم نیرو و انعام را هم حساب می‌کند؟',
    a: 'بله. می‌توانید سهم نیرو را درصدی یا مبلغی تعریف کنید، انعام را ثبت کنید و در گزارش‌ها تسویه را پیگیری کنید.'
  },
  {
    q: 'گزارش‌های مالی چه چیزهایی را پوشش می‌دهد؟',
    a: 'گزارش کل، حق کارواش، حق نیرو، انعام و گزارش‌های مرتبط با کارکرد؛ همراه با فیلتر تاریخ، جست‌وجو و جمع مبالغ.'
  },
  {
    q: 'باشگاه مشتریان و پیامک چه کاربردی دارد؟',
    a: 'برای نگهداری سابقه مشتری، ارسال پیامک وضعیت خودرو، گروه‌بندی مخاطبان و کمپین‌های بازگشت مشتری استفاده می‌شود.'
  },
  {
    q: 'آیا حضور و غیاب نیرو دارد؟',
    a: 'بله. هر نیرو می‌تواند با لینک اختصاصی ورود و خروج ثبت کند و گزارش کارکرد در دسترس مدیریت باشد.'
  },
  {
    q: 'برای چند شعبه مناسب است؟',
    a: 'بله. با پنل HQ می‌توانید مدیریت متمرکز شعب، کاربران و پشتیبانی را داشته باشید.'
  },
  {
    q: 'چطور وارد پنل شوم؟',
    a: 'از دکمه «ورود به پنل» در بالای لندینگ وارد صفحه لاگین شوید و با حساب کاربری کارواش خود وارد پنل مدیریت شوید.'
  },
  {
    q: 'چطور شروع کنم؟',
    a: 'از دکمه «ورود به پنل» وارد صفحه لاگین شوید. برای تهیه و فعال‌سازی سامانه، از مسیر ورود و ارتباط با تیم محصول اقدام کنید.'
  }
]

const toFaDigit = (value) => String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[digit])

let observer = null
let faqSchemaEl = null

const scrollTo = (id) => {
  mobileOpen.value = false
  activeSection.value = id
  const el = document.getElementById(id)
  if (!el) return
  const top = el.getBoundingClientRect().top + window.scrollY - 20
  window.scrollTo({ top, behavior: 'smooth' })
}

const onNavClick = (event, item) => {
  if (item.external) {
    mobileOpen.value = false
    return
  }
  event.preventDefault()
  scrollTo(item.id)
}

const onKeydown = (event) => {
  if (event.key === 'Escape') mobileOpen.value = false
}

const mountFaqSchema = () => {
  faqSchemaEl = document.createElement('script')
  faqSchemaEl.type = 'application/ld+json'
  faqSchemaEl.setAttribute('data-landing-faq', '1')
  faqSchemaEl.textContent = JSON.stringify({
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          {
            '@type': 'ListItem',
            position: 1,
            name: 'نرم افزار مدیریت کارواش کارنوواش',
            item: 'https://carnowash.ir/'
          }
        ]
      },
      {
        '@type': 'SoftwareApplication',
        name: 'کارنوواش',
        alternateName: ['کارنواش', 'کارنو واش', 'CarnoWash'],
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
        url: 'https://carnowash.ir/',
        description:
          'کارنوواش (CarnoWash) سامانه مدیریت کارواش برای پذیرش خودرو، پلاک‌خوان، خدمات، گزارش مالی، پیامک و باشگاه مشتریان.'
      },
      {
        '@type': 'FAQPage',
        mainEntity: faqs.map((item) => ({
          '@type': 'Question',
          name: item.q,
          acceptedAnswer: {
            '@type': 'Answer',
            text: item.a
          }
        }))
      }
    ]
  })
  document.head.appendChild(faqSchemaEl)
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  mountFaqSchema()

  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
      if (visible?.target?.id && sectionIds.includes(visible.target.id)) {
        activeSection.value = visible.target.id
      }
    },
    { rootMargin: '-25% 0px -55% 0px', threshold: [0.15, 0.35, 0.55] }
  )

  sectionIds.forEach((id) => {
    const el = document.getElementById(id)
    if (el) observer.observe(el)
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  observer?.disconnect()
  faqSchemaEl?.remove()
})
</script>

<style scoped>
.landing-page {
  --navy: #071b43;
  --blue: #0667f7;
  --muted: #566b8c;
  --line: #dbe7f5;
  min-height: 100vh;
  color: var(--navy);
  background:
    radial-gradient(circle at 92% 8%, rgba(76, 151, 255, 0.2), transparent 28%),
    radial-gradient(circle at 4% 28%, rgba(115, 201, 255, 0.14), transparent 25%),
    #f4f9ff;
  font-family: Vazirmatn, Tahoma, sans-serif;
}

.landing-page a {
  color: inherit;
  text-decoration: none;
}

.landing-page button {
  font: inherit;
}

.page-shell {
  width: min(100%, 1440px);
  margin: 0 auto;
  overflow: hidden;
  background:
    radial-gradient(circle at 30% 8%, rgba(255, 255, 255, 0.95), transparent 25%),
    radial-gradient(circle at 94% 20%, rgba(116, 179, 255, 0.18), transparent 30%),
    linear-gradient(180deg, #eff7ff 0%, #f9fcff 35%, #edf6ff 100%);
  box-shadow: 0 20px 80px rgba(12, 71, 154, 0.08);
}

.header {
  height: 108px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 40px;
  padding: 0 38px;
  position: sticky;
  top: 0;
  z-index: 30;
  backdrop-filter: blur(14px);
  background: rgba(239, 247, 255, 0.82);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-self: start;
  color: var(--blue);
  font-size: 29px;
  font-weight: 900;
}

.brand img {
  width: 47px;
  height: 47px;
  object-fit: contain;
  border-radius: 14px;
  background: transparent;
  box-shadow: 0 8px 18px rgba(6, 103, 247, 0.22);
}

.nav {
  display: flex;
  gap: 48px;
  font-size: 15px;
  font-weight: 650;
}

.nav a {
  transition: 0.25s ease;
  white-space: nowrap;
}

.nav a:hover,
.nav a.active {
  color: var(--blue);
}

.header-actions {
  display: flex;
  direction: ltr;
  justify-self: end;
  align-items: center;
  gap: 12px;
}

.menu-toggle {
  display: none;
  width: 42px;
  height: 42px;
  border: 1px solid #cbdff8;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.75);
  padding: 10px;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  cursor: pointer;
}

.menu-toggle span {
  display: block;
  height: 2px;
  border-radius: 999px;
  background: var(--blue);
}

.btn {
  min-height: 48px;
  padding: 0 27px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 1px solid transparent;
  font-weight: 750;
  font-size: 14px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
  cursor: pointer;
}

.btn:hover {
  transform: translateY(-2px);
}

.btn-primary {
  color: #fff;
  background: linear-gradient(135deg, #087cfa, #055ee9);
  box-shadow: 0 10px 24px rgba(5, 101, 244, 0.22);
}

.btn-primary:hover,
.btn-primary:focus,
.btn-primary:visited,
a.btn-primary,
a.btn-primary:hover,
a.btn-primary:focus,
a.btn-primary:visited {
  color: #fff;
}

.btn-primary:hover {
  box-shadow: 0 15px 30px rgba(5, 101, 244, 0.3);
}

.btn-outline {
  color: var(--blue);
  border-color: #cbdff8;
  background: rgba(255, 255, 255, 0.65);
}

.btn-lg {
  min-height: 60px;
  min-width: 182px;
  border-radius: 12px;
}

.hero {
  min-height: 825px;
  display: grid;
  grid-template-columns: 38% 62%;
  direction: rtl;
  align-items: center;
  position: relative;
  padding: 0 30px 70px;
}

.hero::after {
  content: '';
  position: absolute;
  inset: 10% 26% auto -15%;
  height: 630px;
  background: radial-gradient(ellipse at center, rgba(144, 199, 255, 0.22), transparent 63%);
  pointer-events: none;
}

.hero-visual {
  align-self: stretch;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
  margin-left: -40px;
  margin-right: 0;
  overflow: visible;
}

.hero-visual img {
  width: min(100%, 720px);
  max-width: none;
  height: auto;
  filter: drop-shadow(0 28px 48px rgba(8, 70, 170, 0.18));
  transform: translateY(8px);
}

.hero-copy {
  direction: rtl;
  text-align: right;
  position: relative;
  z-index: 2;
  padding: 20px 24px 0 8px;
  justify-self: stretch;
}

.hero-copy h1 {
  margin: 0;
  font-size: clamp(40px, 4vw, 62px);
  line-height: 1.45;
  letter-spacing: -2.4px;
  font-weight: 900;
}

.hero-copy h1 strong {
  display: block;
  color: var(--blue);
}

.hero-copy > p {
  color: var(--muted);
  font-size: 17px;
  line-height: 2.15;
  max-width: 470px;
  margin: 25px 0 38px;
  font-weight: 500;
}

.hero-actions {
  display: flex;
  gap: 14px;
}

.social-proof {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 80px;
}

.social-proof > div:last-child {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.social-proof b {
  font-size: 16px;
}

.social-proof small {
  color: var(--muted);
}

.avatars {
  display: flex;
  direction: ltr;
  padding-left: 14px;
}

.avatars span {
  width: 43px;
  height: 43px;
  margin-left: -12px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: white;
  border: 3px solid white;
  font-size: 13px;
  font-weight: 800;
  background: linear-gradient(145deg, #293750, #b27e62);
  box-shadow: 0 3px 8px rgba(4, 34, 77, 0.15);
}

.features-section {
  margin: 0 28px 28px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 30px;
  padding: 40px 34px 20px;
  box-shadow: 0 -20px 50px rgba(255, 255, 255, 0.8), 0 25px 70px rgba(22, 77, 145, 0.06);
}

.section-heading {
  text-align: center;
}

.section-heading h2 {
  font-size: 34px;
  margin: 0 0 14px;
  font-weight: 900;
}

.section-heading h2 em {
  font-style: normal;
  color: var(--blue);
}

.section-heading p {
  color: var(--muted);
  margin: 0;
  font-size: 15px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-top: 34px;
}

.feature-card {
  min-height: 225px;
  text-align: center;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: linear-gradient(180deg, #fff, #fbfdff);
  padding: 25px 14px 20px;
  box-shadow: 0 10px 25px rgba(24, 80, 150, 0.035);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  animation: rise 0.55s ease both;
  animation-delay: var(--delay, 0ms);
}

.feature-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 18px 36px rgba(24, 80, 150, 0.1);
}

.feature-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 22px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  background: linear-gradient(145deg, #f0f7ff, #dfeeff);
  box-shadow: inset 0 1px 0 white, 0 8px 20px rgba(45, 127, 235, 0.08);
}

.feature-card h3 {
  font-size: 16px;
  margin: 0 0 12px;
  font-weight: 900;
}

.feature-card p {
  color: var(--muted);
  font-size: 12px;
  line-height: 2;
  margin: 0;
}

.stats {
  min-height: 134px;
  margin: 48px 0 30px;
  border-radius: 18px;
  background: linear-gradient(100deg, #0785fd 0%, #0966ef 54%, #065cef 100%);
  color: white;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  align-items: center;
  box-shadow: 0 18px 38px rgba(0, 98, 242, 0.2);
}

.stats > div {
  display: grid;
  grid-template-columns: 60px auto;
  grid-template-rows: auto auto;
  align-items: center;
  justify-content: center;
  column-gap: 12px;
}

.stats > div + div {
  border-right: 1px solid rgba(255, 255, 255, 0.16);
}

.stat-icon {
  grid-row: 1 / 3;
  display: grid;
  place-items: center;
}

.stats b {
  font-size: 28px;
  font-weight: 500;
  line-height: 1;
  direction: ltr;
  text-align: right;
}

.stats small {
  opacity: 0.95;
  font-size: 14px;
  margin-top: 8px;
}

.mobile-showcase {
  min-height: 385px;
  display: grid;
  grid-template-columns: 1fr 1.05fr;
  align-items: center;
  direction: rtl;
  padding: 16px 65px 18px;
}

.mobile-copy {
  max-width: 530px;
}

.eyebrow {
  color: var(--blue);
  font-size: 16px;
  font-weight: 850;
}

.mobile-copy h2 {
  font-size: 34px;
  margin: 10px 0 13px;
  font-weight: 900;
}

.mobile-copy p {
  margin: 0;
  color: var(--muted);
  line-height: 2;
  font-size: 15px;
}

.platforms {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 25px;
}

.platforms button {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  min-height: 92px;
  color: var(--navy);
  display: grid;
  place-items: center;
  gap: 8px;
  padding: 10px;
  cursor: default;
}

.platform-icon {
  display: grid;
  place-items: center;
}

.platform-icon.android :deep(.iconly-shell) {
  --iconly-filter: brightness(0) saturate(100%) invert(48%) sepia(72%) saturate(467%) hue-rotate(121deg) brightness(95%) contrast(92%);
}

.platforms span {
  font-size: 13px;
}

.mobile-visual {
  position: relative;
  min-height: 360px;
  display: grid;
  place-items: center;
  direction: ltr;
}

.mobile-visual img {
  width: min(100%, 460px);
  height: auto;
  filter: drop-shadow(0 24px 40px rgba(8, 70, 170, 0.16));
}

.cta {
  min-height: 260px;
  border: 1px solid #d7e8fb;
  border-radius: 19px;
  background: linear-gradient(90deg, #e5f1ff, #f4f9ff 51%, #d8eaff);
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  align-items: center;
  overflow: hidden;
  margin: 0;
  box-shadow: 0 18px 35px rgba(20, 81, 153, 0.11);
}

.cta-copy {
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 35px 45px;
}

.cta-copy h2 {
  margin: 0 0 12px;
  font-size: 27px;
  font-weight: 900;
}

.cta-copy p {
  margin: 0 0 22px;
  color: var(--muted);
}

.cta-copy .btn {
  min-height: 48px;
}

.cta-art {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 240px;
  padding: 12px 18px 8px;
}

.cta-art img {
  width: min(100%, 420px);
  height: auto;
  filter: drop-shadow(0 18px 30px rgba(8, 70, 170, 0.18));
}

.trusted {
  text-align: center;
  padding: 40px 0 18px;
}

.trusted h3 {
  margin: 0 0 32px;
  font-size: 18px;
  font-weight: 800;
}

.trust-row {
  display: flex;
  direction: ltr;
  justify-content: space-between;
  align-items: center;
  color: #8ca3c4;
  font-weight: 800;
  padding: 0 24px;
  gap: 16px;
}

.trust-row span {
  white-space: nowrap;
  opacity: 0.9;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.content-band {
  margin: 0 28px 28px;
}

.content-panel {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 30px;
  padding: 42px 34px 34px;
  box-shadow: 0 25px 70px rgba(22, 77, 145, 0.06);
}

.content-note {
  margin: 28px 0 0;
  text-align: center;
  color: var(--muted);
  font-size: 15px;
  line-height: 2;
  max-width: 820px;
  margin-inline: auto;
}

.pain-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 30px;
}

.pain-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 92px;
  padding: 18px 16px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: linear-gradient(180deg, #fff, #f8fbff);
}

.pain-card p {
  margin: 0;
  color: var(--navy);
  font-size: 14px;
  line-height: 1.9;
  font-weight: 650;
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 30px;
}

.workflow-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #fff;
  padding: 22px 18px;
  min-height: 210px;
}

.workflow-index {
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(145deg, #f0f7ff, #dfeeff);
  color: var(--blue);
  font-weight: 900;
  margin-bottom: 14px;
}

.workflow-card h3 {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 900;
}

.workflow-card ul,
.role-card ul {
  margin: 0;
  padding: 0 18px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 2;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-top: 30px;
}

.module-card {
  text-align: center;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: linear-gradient(180deg, #fff, #fbfdff);
  padding: 22px 14px 18px;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 30px rgba(24, 80, 150, 0.08);
}

.module-icon {
  width: 52px;
  height: 52px;
  margin: 0 auto 14px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: linear-gradient(145deg, #f0f7ff, #dfeeff);
}

.module-card h3 {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 900;
}

.module-card p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.9;
}

.roles-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-top: 30px;
}

.role-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #fff;
  padding: 22px 18px;
}

.role-card h3 {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 900;
  color: var(--blue);
}

.compare-table {
  margin-top: 30px;
  border: 1px solid var(--line);
  border-radius: 18px;
  overflow: hidden;
  background: #fff;
}

.compare-head,
.compare-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.compare-head {
  background: linear-gradient(100deg, #0785fd 0%, #065cef 100%);
  color: #fff;
  font-weight: 800;
}

.compare-head span,
.compare-row span {
  padding: 16px 20px;
  font-size: 14px;
  line-height: 1.8;
}

.compare-row:nth-child(even) {
  background: #f7fbff;
}

.compare-row span + span {
  border-right: 1px solid var(--line);
  color: var(--navy);
  font-weight: 700;
}

.compare-row span:first-child {
  color: var(--muted);
}

.why-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-top: 30px;
}

.why-card {
  display: grid;
  grid-template-columns: 42px 1fr;
  gap: 14px;
  align-items: start;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #fff;
  padding: 18px 16px;
}

.why-card span {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: linear-gradient(145deg, #f0f7ff, #dfeeff);
  color: var(--blue);
  font-weight: 900;
}

.why-card p {
  margin: 0;
  color: var(--navy);
  font-size: 14px;
  line-height: 2;
  font-weight: 650;
}

.faq-list {
  display: grid;
  gap: 10px;
  margin-top: 30px;
  max-width: 920px;
  margin-inline: auto;
}

.faq-item {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  padding: 0 18px;
}

.faq-item summary {
  cursor: pointer;
  list-style: none;
  min-height: 58px;
  display: flex;
  align-items: center;
  font-weight: 800;
  font-size: 15px;
}

.faq-item summary::-webkit-details-marker {
  display: none;
}

.faq-item p {
  margin: 0 0 16px;
  color: var(--muted);
  font-size: 14px;
  line-height: 2;
}

.landing-footer {
  margin: 0 28px 28px;
  border-radius: 30px;
  background: linear-gradient(180deg, #071b43, #0a2a63);
  color: #dce9fb;
  padding: 42px 34px 28px;
}

.footer-inner {
  display: grid;
  gap: 22px;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.footer-brand img {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  object-fit: contain;
  background: #fff;
}

.footer-brand strong {
  display: block;
  color: #fff;
  font-size: 22px;
  font-weight: 900;
}

.footer-brand span {
  color: #8fb4ea;
  font-size: 13px;
}

.footer-copy {
  margin: 0;
  max-width: 920px;
  line-height: 2;
  font-size: 14px;
  color: #b7ccec;
}

.footer-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
}

.footer-links a {
  color: #e8f2ff;
  font-size: 13px;
  font-weight: 700;
  transition: color 0.2s ease;
}

.footer-links a:hover {
  color: #7cbcff;
}

.footer-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  padding-top: 18px;
}

.footer-bottom small {
  color: #9eb8dc;
  font-size: 13px;
  line-height: 1.8;
}

.footer-cta {
  flex: 0 0 auto;
}

.footer-credit {
  display: grid;
  gap: 4px;
  justify-items: center;
  text-align: center;
  padding-top: 8px;
}

.footer-credit p {
  margin: 0;
  color: #8fa8c9;
  font-size: 12px;
  font-weight: 600;
}

.footer-credit span {
  color: #6f87a8;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.mobile-drawer {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgba(7, 27, 67, 0.28);
  backdrop-filter: blur(4px);
}

.mobile-nav {
  position: absolute;
  top: 90px;
  left: 16px;
  right: 16px;
  background: #fff;
  border-radius: 18px;
  padding: 12px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
  box-shadow: 0 24px 50px rgba(12, 71, 154, 0.18);
}

.mobile-nav a {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 58px;
  padding: 8px 4px;
  border-radius: 12px;
  font-weight: 600;
  color: var(--navy);
  font-size: 11px;
  line-height: 1.3;
  text-align: center;
  white-space: nowrap;
}

.mobile-nav a:hover {
  background: #eff7ff;
  color: var(--blue);
}

.mobile-nav-actions {
  display: grid;
  gap: 10px;
  margin-top: 8px;
  grid-column: 1 / -1;
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.2s ease;
}

.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}

.drawer-enter-active .mobile-nav,
.drawer-leave-active .mobile-nav {
  transition: transform 0.22s ease, opacity 0.22s ease;
}

.drawer-enter-from .mobile-nav,
.drawer-leave-to .mobile-nav {
  opacity: 0;
  transform: translateY(-10px);
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 1100px) {
  .nav {
    gap: 22px;
  }

  .hero {
    grid-template-columns: 42% 58%;
    min-height: 680px;
  }

  .hero-visual {
    margin-left: -20px;
    margin-right: 0;
  }

  .hero-visual img {
    width: min(100%, 560px);
  }

  .features-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .feature-card {
    min-height: 200px;
  }

  .pain-grid,
  .workflow-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .modules-grid,
  .roles-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .nav {
    gap: 18px;
    font-size: 13px;
  }
}

@media (max-width: 820px) {
  .page-shell {
    width: 100%;
  }

  .header {
    height: 82px;
    grid-template-columns: auto 1fr;
    padding: 0 18px;
  }

  .brand {
    font-size: 22px;
  }

  .brand img {
    width: 40px;
    height: 40px;
  }

  .nav {
    display: none;
  }

  .header-actions {
    justify-self: end;
  }

  .header-actions .btn-primary {
    display: none;
  }

  .menu-toggle {
    display: inline-flex;
  }

  .hero {
    grid-template-columns: 1fr;
    padding: 25px 18px 50px;
    min-height: auto;
  }

  .hero-copy {
    grid-row: 2;
    padding: 20px 7px 0;
    text-align: center;
  }

  .hero-copy h1 {
    font-size: 39px;
    line-height: 1.5;
    letter-spacing: -1.5px;
  }

  .hero-copy > p {
    margin: 18px auto 25px;
    font-size: 15px;
    line-height: 2;
  }

  .hero-actions {
    justify-content: center;
    flex-wrap: wrap;
  }

  .btn-lg {
    min-height: 52px;
    min-width: 150px;
    padding: 0 18px;
  }

  .social-proof {
    justify-content: center;
    margin-top: 35px;
  }

  .hero-visual {
    grid-row: 1;
    margin: 10px 0 -5px;
  }

  .hero-visual img {
    width: min(100%, 420px);
    margin: auto;
    transform: none;
  }

  .features-section {
    margin: 0 10px 10px;
    padding: 32px 15px 15px;
    border-radius: 24px;
  }

  .section-heading h2 {
    font-size: 27px;
  }

  .section-heading p {
    line-height: 1.8;
  }

  .features-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .feature-card {
    min-height: 190px;
    padding: 18px 10px;
  }

  .feature-icon {
    width: 55px;
    height: 55px;
    margin-bottom: 15px;
  }

  .stats {
    grid-template-columns: 1fr 1fr;
    gap: 0;
    padding: 12px 0;
    margin-top: 28px;
  }

  .stats > div {
    min-height: 95px;
  }

  .stats > div + div {
    border-right: 0;
  }

  .stats > div:nth-child(odd) {
    border-left: 1px solid rgba(255, 255, 255, 0.15);
  }

  .stats b {
    font-size: 23px;
  }

  .mobile-showcase {
    grid-template-columns: 1fr;
    padding: 26px 15px;
  }

  .mobile-copy {
    text-align: center;
    margin: auto;
  }

  .mobile-copy h2 {
    font-size: 27px;
  }

  .mobile-visual {
    grid-row: 2;
    margin-top: 18px;
    min-height: auto;
  }

  .mobile-visual img {
    width: min(100%, 340px);
  }

  .platforms {
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .platforms button {
    min-height: 72px;
    padding: 8px 4px;
    border-radius: 12px;
    gap: 6px;
  }

  .platforms span {
    font-size: 11px;
  }

  .cta {
    grid-template-columns: 1fr;
  }

  .cta-copy {
    grid-row: 1;
    padding: 30px 20px;
    text-align: center;
    justify-content: center;
  }

  .cta-art {
    min-height: auto;
    padding: 0 16px 22px;
  }

  .cta-art img {
    width: min(100%, 320px);
  }

  .trust-row {
    flex-wrap: wrap;
    gap: 22px;
    justify-content: center;
  }

  .content-band,
  .landing-footer {
    margin: 0 10px 10px;
  }

  .content-panel,
  .landing-footer {
    padding: 28px 16px 20px;
    border-radius: 24px;
  }

  .pain-grid,
  .workflow-grid,
  .modules-grid,
  .roles-grid,
  .why-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .compare-head,
  .compare-row {
    grid-template-columns: 1fr 1fr;
  }

  .compare-row span + span {
    border-right: 1px solid var(--line);
    border-top: 0;
  }

  .footer-bottom {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }

  .footer-cta {
    width: 100%;
  }
}

@media (prefers-reduced-motion: no-preference) {
  .hero-visual {
    animation: reveal 0.7s ease both;
  }

  .mobile-visual img {
    animation: float 5s ease-in-out infinite;
  }

  .cta-art img {
    animation: float 5.5s ease-in-out infinite;
    animation-delay: -1.2s;
  }
}

@media (prefers-reduced-motion: reduce) {
  .feature-card,
  .hero-visual,
  .mobile-visual img,
  .cta-art img {
    animation: none;
  }

  .btn:hover,
  .feature-card:hover {
    transform: none;
  }
}

@keyframes reveal {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}
</style>
