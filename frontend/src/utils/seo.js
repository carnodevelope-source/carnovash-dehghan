const SITE_URL = 'https://carnowash.ir'
const SITE_NAME = 'CarnoWash'

const DEFAULT_META = {
  title: 'CarnoWash | سامانه مدیریت کارواش',
  description: 'سامانه عملیاتی CarnoWash برای مدیریت پذیرش خودرو، خدمات، گزارش‌ها، کیف پول و ارتباط با مشتریان.',
  robots: 'noindex, nofollow',
  canonicalPath: '/login'
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

function routeMeta(route) {
  return {
    ...DEFAULT_META,
    ...(route.meta?.seo || {})
  }
}

export function applyRouteSeo(route) {
  if (typeof document === 'undefined') return

  const meta = routeMeta(route)
  const canonicalPath = meta.canonicalPath || route.path || '/login'
  const canonicalUrl = new URL(canonicalPath, SITE_URL).toString()

  document.title = meta.title
  upsertMeta('meta[name="description"]', { name: 'description', content: meta.description })
  upsertMeta('meta[name="robots"]', { name: 'robots', content: meta.robots })
  upsertCanonical(canonicalUrl)
  upsertMeta('meta[property="og:site_name"]', { property: 'og:site_name', content: SITE_NAME })
  upsertMeta('meta[property="og:title"]', { property: 'og:title', content: meta.title })
  upsertMeta('meta[property="og:description"]', { property: 'og:description', content: meta.description })
  upsertMeta('meta[property="og:url"]', { property: 'og:url', content: canonicalUrl })
  upsertMeta('meta[name="twitter:title"]', { name: 'twitter:title', content: meta.title })
  upsertMeta('meta[name="twitter:description"]', { name: 'twitter:description', content: meta.description })
}
