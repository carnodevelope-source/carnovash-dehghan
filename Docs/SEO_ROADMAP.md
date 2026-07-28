# SEO roadmap — CarnoWash

Audited: 2026-07-26. Previous evidence: `Docs/seo-analyze.md`. Stack: Vue 3, Vite, Vue Router history mode, Nginx and a Django-backed API/admin. The public surface comprises `/` and the static `/about/`; the operational panels are intentionally private.

## Current score

**65/100 at audit baseline.** Metadata, canonical markup, static sitemap/robots and public HTML content are already strong. The audit’s critical issue was canonical-host duplication (`www` and non-`www`); the remaining score drag is performance and the small public content footprint.

## Implemented in this audit

- Improved social previews: Open Graph now uses the actual product hero rather than a favicon, adds accessible image text and uses `summary_large_image` plus a Twitter image.

## Critical / high priority

1. Configure a permanent edge redirect from `www.carnowash.ir` to `https://carnowash.ir`. The container accepts arbitrary hosts, so this must be implemented in the reverse proxy/CDN or deployment-specific server block. Expected impact: resolves the only critical issue in the source audit.
2. Validate the public `/about/` page has a self-canonical, unique title/description and remains listed in `sitemap.xml`. It is the primary supporting indexable page.
3. Use a real 1200×630 branded social card if the current hero is not that size. Verify its HTTP 200 response and dimensions with the social debuggers after deployment.

## Medium priority

- The build has a 983 kB `html2pdf` chunk. Keep it lazy-loaded and confirm it is never requested on `/` or `/about/`; protect public LCP from application-only code.
- Collect lab and field CWV after deploy. Target LCP ≤2.5s, INP ≤200ms and CLS ≤0.1. Avoid adding non-essential hero media or third-party scripts before these measurements.
- Add concise, original product/use-case pages only when the content can be materially different from the landing page. Link them from `/` and `/about/`, then add them to the sitemap.
- Preserve the existing noindex rules and Nginx `X-Robots-Tag` headers for `/login`, `/panel`, `/hq`, `/manager`, `/support` and `/attendance`.

## Long-term strategy

Develop a focused B2B content cluster: car-wash management software, plate recognition workflow, financial reporting and multi-branch operations. Use real screenshots, implementation outcomes and clearly attributed product expertise. Keep the product marketing layer statically rendered or prerendered; never expose operational data in crawled pages.

## Implementation order and expected impact

| Order | Work | Expected impact |
|---:|---|---|
| 1 | Enforce the non-`www` canonical host | Critical duplicate-content cleanup |
| 2 | Verify sitemap/about-page parity in production | Reliable public-page discovery |
| 3 | Confirm public routes exclude `html2pdf` and measure CWV | Better LCP and crawl efficiency |
| 4 | Replace or validate social card asset | Better share previews and click-through potential |
| 5 | Publish distinct B2B use-case pages | Longer-term qualified organic demand |

## Monitoring checklist

- Release check: test `/`, `/about/`, `/robots.txt`, `/sitemap.xml`, `/login` and `/panel`; confirm public/private robots behavior.
- Monthly: inspect Search Console canonical selection and mobile CWV; check sitemap submitted/processed counts.
- Content check: every new public page needs a unique title, description, H1, self-canonical, internal link, sitemap entry and truthful schema.
