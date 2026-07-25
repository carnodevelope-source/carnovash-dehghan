const SITE_URL = 'https://carnowash.ir'
const SITE_NAME = 'CarnoWash'

const DEFAULT_META = {
  title: 'نرم افزار مدیریت کارواش | کارنوواش CarnoWash',
  description:
    'کارنوواش (CarnoWash) سامانه مدیریت کارواش برای پذیرش خودرو، پلاک‌خوان، تخصیص خدمات و نیرو، پرداخت، گزارش مالی، کیف پول، حضور و غیاب و باشگاه مشتریان.',
  robots: 'noindex, nofollow',
  canonicalPath: '/'
}

function upsertMeta(selector, attrs) {
  let element = document.head.querySelector(selector)
  if (!element) {
    element = document.createElement('meta')
    document.head.appendChild(element)
  }
  Object.entries(attrs).forEach(([key, value]) => {
    element.setAttribute(key, value)
  })
}

function upsertCanonical(href) {
  let element = document.head.querySelector('link[rel="canonical"]')
  if (!element) {
    element = document.createElement('link')
    element.setAttribute('rel', 'canonical')
    document.head.appendChild(element)
  }
  element.setAttribute('href', href)
}

function upsertLink(rel, href, attrs = {}) {
  const selector = Object.entries(attrs).reduce(
    (acc, [key, value]) => `${acc}[${key}="${value}"]`,
    `link[rel="${rel}"]`
  )
  let element = document.head.querySelector(selector)
  if (!element) {
    element = document.createElement('link')
    element.setAttribute('rel', rel)
    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value))
    document.head.appendChild(element)
  }
  element.setAttribute('href', href)
}

function routeMeta(route) {
  return {
    ...DEFAULT_META,
    ...(route.meta?.seo || {})
  }
}

export function applyRouteSeo(route) {
  if (typeof document === 'undefined') return

  const meta = routeMeta(route)
  const canonicalPath = meta.canonicalPath || route.path || '/'
  const canonicalUrl = new URL(canonicalPath, SITE_URL).toString()

  document.title = meta.title
  document.documentElement.lang = 'fa'
  document.documentElement.dir = 'rtl'

  upsertMeta('meta[name="description"]', { name: 'description', content: meta.description })
  upsertMeta('meta[name="robots"]', { name: 'robots', content: meta.robots })
  upsertCanonical(canonicalUrl)
  upsertLink('icon', `${SITE_URL}/favicon.webp`, { type: 'image/webp' })
  upsertLink('icon', `${SITE_URL}/favicon.png`, { type: 'image/png' })
  upsertLink('apple-touch-icon', `${SITE_URL}/apple-touch-icon.png`)

  upsertMeta('meta[property="og:site_name"]', { property: 'og:site_name', content: SITE_NAME })
  upsertMeta('meta[property="og:type"]', { property: 'og:type', content: 'website' })
  upsertMeta('meta[property="og:locale"]', { property: 'og:locale', content: 'fa_IR' })
  upsertMeta('meta[property="og:title"]', { property: 'og:title', content: meta.title })
  upsertMeta('meta[property="og:description"]', { property: 'og:description', content: meta.description })
  upsertMeta('meta[property="og:url"]', { property: 'og:url', content: canonicalUrl })
  upsertMeta('meta[property="og:image"]', { property: 'og:image', content: `${SITE_URL}/logo/blue.webp` })
  upsertMeta('meta[name="twitter:card"]', { name: 'twitter:card', content: 'summary' })
  upsertMeta('meta[name="twitter:title"]', { name: 'twitter:title', content: meta.title })
  upsertMeta('meta[name="twitter:description"]', { name: 'twitter:description', content: meta.description })
}
