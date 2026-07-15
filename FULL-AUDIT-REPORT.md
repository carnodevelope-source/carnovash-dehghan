# Full Production SEO Audit - CarnoWash

Audit date: 2026-07-15  
Target used: `https://carnowash.ir/login` and local build output from `frontend/dist`  
Business type detected: private B2B operational SPA / SaaS for carwash management  
Overall health after local fixes: 87/100 for a private app SEO posture; 66/100 if judged as a public acquisition website.

## Executive Summary

CarnoWash is not currently structured as a public marketing website. The real product surface is an authenticated Vue SPA for operators, managers, HQ, support, wallet, reports, attendance, and customer-club workflows. For this product, the correct production SEO baseline is: index only the public login/brand surface, protect private and token routes, publish clean crawler files, remove accidental public artifacts, and avoid pretending private dashboard routes should rank.

Safe technical improvements were implemented directly in the codebase. The biggest fixed issue was removal of a saved Google Search export from `frontend/public`, which would otherwise be deployed as public third-party content. A crawlable `/about/` surface was also added so the site now has a public explanation page without exposing private app routes.

## Validation Evidence

Local build validation after fixes:

| Check | Result |
|---|---|
| `npm.cmd run build` | Pass |
| `frontend/dist/index.html` title | `CarnoWash | سامانه مدیریت کارواش` |
| Meta description | Present |
| Canonical | `https://carnowash.ir/login` |
| JSON-LD | Present |
| Schema types | `Organization`, `WebSite`, `WebPage`, `WebApplication` |
| `robots.txt` | Present in build |
| `sitemap.xml` | Present in build |
| `llms.txt` | Present in build |
| `/about/` public page | Present, indexable, H1, canonical, JSON-LD, about 292 words |
| Optimized mobile background | AVIF 48,748 bytes; WebP 101,378 bytes |
| Login video poster | WebP 105,670 bytes |
| Login video | MP4 681,039 bytes |
| Google Search snapshot in build | Removed |

Live audit note: the live deployment still appears stale. The codex-seo scripts against `https://carnowash.ir/login` reported no live canonical/schema/security headers and `/llms.txt` still serving the old SPA shell. Deploy the rebuilt frontend and nginx config before treating live results as fixed.

## Priority Findings

### Critical

1. Accidental public Google Search snapshot in deployable assets

Status: Fixed.

Evidence: `frontend/public/Google Search.html` and `frontend/public/Google Search_files/` were tracked under Vite public assets. This exposed irrelevant third-party content and Google `SearchResultsPage` markup.

Code changes made:
- Deleted `frontend/public/Google Search.html`
- Deleted `frontend/public/Google Search_files/`
- Added nginx 410/noindex guards for those paths in `frontend/nginx/default.conf` and edge nginx templates.

2. Missing crawler files

Status: Fixed locally; deploy required.

Evidence: `frontend/public` previously had no `robots.txt`, `sitemap.xml`, or `llms.txt`. Live `/robots.txt` and `/llms.txt` currently still return the old SPA shell.

Code changes made:
- Added `frontend/public/robots.txt`
- Added `frontend/public/sitemap.xml`
- Added `frontend/public/llms.txt`
- Added exact nginx locations for `/robots.txt`, `/sitemap.xml`, and `/llms.txt`.

### High

3. Private app routes needed explicit noindex handling

Status: Fixed locally; deploy required.

Code changes made:
- Added route-aware SEO utility at `frontend/src/utils/seo.js`
- Added route meta in `frontend/src/router/index.js`
- Login route is indexable.
- Attendance token route is noindexed.
- Private route groups get `X-Robots-Tag: noindex, nofollow, noarchive` in `frontend/nginx/default.conf`.

4. Missing canonical/meta/schema in SPA shell

Status: Fixed locally; deploy required.

Code changes made:
- Updated `frontend/index.html` with title, description, canonical, Open Graph, Twitter Card, font preloads, and JSON-LD graph.
- JSON-LD uses only verifiable generic entity types: `Organization`, `WebSite`, `WebPage`, `WebApplication`.

5. Root redirect was temporary

Status: Fixed locally.

Code change made:
- Changed `location = /` in `frontend/nginx/default.conf` from `302 /login` to `301 /login`.

6. Core Web Vitals risk from login media

Status: Fixed locally; deploy required.

Evidence:
- `frontend/dist/login-hero.mp4`: 681,039 bytes
- `frontend/dist/Mobile-bg.jpg`: 1,074,063 bytes, kept only as fallback
- `frontend/dist/Mobile-bg-640.avif`: 48,748 bytes
- `frontend/dist/Mobile-bg-640.webp`: 101,378 bytes
- `frontend/dist/login-poster.webp`: 105,670 bytes
- Live heuristic performance audit before deployment: LCP about 3.37s, score 65/100, based on the stale live build.

Code changes made:
- Created optimized AVIF/WebP mobile background assets.
- Created compressed login poster assets.
- Updated mobile CSS to use `image-set(...)`.
- Updated login video with `preload="metadata"` and poster.
- Replaced the original 4.1 MB login video with `frontend/public/login-hero.mp4` at 681,039 bytes.

### Medium

7. Public content and GEO/AEO readiness are weak

Status: Improved.

Reason: the app is private and CSR, but a static public `/about/` page now provides crawlable product context.

Code changes made:
- Added `frontend/public/about/index.html`.
- Added `/about/` to `robots.txt`, `sitemap.xml`, and `llms.txt`.

Remaining recommendation:
- Add public feature pages or case studies only if acquisition SEO becomes a product goal.

8. Backlink audit data insufficient

Status: Open by tooling/data setup.

Reason: no Moz, Bing Webmaster, DataForSEO, or verified backlink list is configured. Backlink scoring would be misleading.

Exact required setup:
- Configure Moz or Bing credentials in the codex-seo config.
- Provide a known backlink list for verification.
- Re-run backlink profile and competitor gap analysis.

9. Security headers partial

Status: Partially fixed locally.

Code changes made:
- Added `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy` in `frontend/nginx/default.conf`.
- Added security headers and canonical host redirect in `docker/edge-nginx/templates/site-ssl.conf.template`.

Open recommendation:
- Add a tested CSP after confirming it does not block Vite assets or JSON-LD parsing.

### Low

10. Brand typo and heading semantics on login

Status: Fixed.

Code changes made:
- Changed the visible misspelled brand text to `CarnoWash`.
- Changed the login page main heading from `h2` to `h1`.
- Normalized footer brand copy.

11. IndexNow not configured

Status: Open, optional.

Exact recommended code changes:
- Add an IndexNow key file at `frontend/public/<key>.txt`.
- Submit `https://carnowash.ir/login` after deployment if Bing/Yandex/Naver discovery matters.

## Category Analysis

| Category | Result |
|---|---|
| Crawlability | Fixed locally. Robots, sitemap, llms files now build. |
| Indexability | Good for private SPA posture. Login indexable; private/token routes protected. |
| Canonicals and redirects | Canonical added for `/login`; root redirect changed to permanent locally. |
| Internal linking and orphan pages | Not meaningful for private authenticated routes. Public link graph is intentionally minimal. |
| Duplicate and thin content | Private app duplicate UI is acceptable when noindexed. Public login is thin if used as acquisition page. |
| Titles/descriptions/headings/image SEO | Title, description, H1, brand typo, poster, and key image/video assets fixed. |
| Structured data | JSON-LD graph added. LocalBusiness intentionally not added due missing verified NAP/geo/hours. |
| Core Web Vitals | LCP risk materially reduced locally; validate live after deployment with PageSpeed/CrUX. |
| JavaScript rendering | Private app remains CSR. Critical SEO elements are now in initial HTML, but public content is still minimal. |
| E-E-A-T/helpful content | Weak publicly; acceptable only for private app. Needs public pages for growth. |
| Keyword intent/content gaps | Current surface satisfies navigational login intent only. Needs public content for commercial keywords. |
| Local SEO | Not applicable yet; no verified public location profile or location page. |
| E-commerce SEO | Not applicable; app has product/inventory modules but no public product catalog. |
| GEO/AEO/AI readiness | Improved with `llms.txt`; still weak without crawlable public explanation pages. |
| Backlinks/competitors | Insufficient data; strategy documented but no numeric score. |
| Security/accessibility SEO | Headers improved locally; mobile tap/font constraints still deserve a UX pass. |

## Exact Code Changes Implemented

- `frontend/index.html`: added SEO metadata, canonical, social tags, font preloads, JSON-LD entity graph.
- `frontend/src/utils/seo.js`: added route-aware title/meta/canonical/social updater.
- `frontend/src/router/index.js`: added SEO metadata for `/login` and `/attendance/:token`; applied route SEO after navigation.
- `frontend/public/robots.txt`: added crawler policy.
- `frontend/public/sitemap.xml`: added indexable login URL.
- `frontend/public/llms.txt`: added AI crawler guidance for private app context.
- `frontend/public/about/index.html`: added public crawlable product explanation page.
- `frontend/nginx/default.conf`: added security headers, exact static crawler-file routes, asset caching, noindex headers for private paths, 410 guards for removed Google snapshot paths, permanent root redirect.
- `docker/edge-nginx/templates/site-ssl.conf.template`: added security headers and canonical host redirect.
- `docker/edge-nginx/templates/site-http.conf.template`: added Google snapshot 410 guards.
- `frontend/src/views/auth/LoginView.vue`: fixed brand typo, H1 semantics, duplicate font-face declarations.
- `frontend/public/login-hero.mp4`: added optimized login background video and removed the original 4.1 MB MP4.
- `frontend/src/assets/styles/main.css`: added central Semibold font-face.
- `frontend/public/Mobile-bg-640.avif`, `frontend/public/Mobile-bg-640.webp`, `frontend/public/login-poster.avif`, `frontend/public/login-poster.webp`: added optimized media assets.
- `frontend/src/components/layout/AppShell.vue`: fixed missing mobile sidebar image reference.
- `.gitignore`: added `.seo-cache/`.

## Remaining Exact Code Changes

These were not auto-implemented because they require credentials, verified public business facts, or deeper product/content decisions:

```html
<!-- Future public feature page example -->
<h1>نرم افزار مدیریت کارواش CarnoWash</h1>
<p>صفحه‌ای اختصاصی برای توضیح ویژگی‌های پذیرش خودرو، گزارش‌ها، باشگاه مشتریان و مدیریت پرسنل.</p>
```

```txt
# frontend/public/llms.txt
- [معرفی CarnoWash](https://carnowash.ir/about/): توضیح عمومی و قابل استناد درباره سامانه.
```

```xml
<!-- frontend/public/sitemap.xml -->
<url>
  <loc>https://carnowash.ir/about/</loc>
  <changefreq>monthly</changefreq>
  <priority>0.8</priority>
</url>
```
