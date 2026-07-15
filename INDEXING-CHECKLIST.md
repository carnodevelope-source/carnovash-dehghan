# Indexing Checklist - CarnoWash

## Before Submitting To Search Console

- [ ] Deploy the current frontend build and nginx configs.
- [ ] Confirm `https://carnowash.ir/robots.txt` returns real robots text.
- [ ] Confirm `https://carnowash.ir/sitemap.xml` returns valid XML.
- [ ] Confirm `https://carnowash.ir/llms.txt` returns plain text.
- [ ] Confirm `https://carnowash.ir/about/` returns the static about page.
- [ ] Confirm `/Google%20Search.html` returns `410`.
- [ ] Confirm private routes return `X-Robots-Tag: noindex, nofollow, noarchive`.
- [ ] Confirm unknown public paths return `404`.
- [ ] Confirm `www` redirects to non-www.
- [ ] Confirm `/` redirects with `301` to `/login`.

## URLs To Inspect

- `https://carnowash.ir/login`
- `https://carnowash.ir/about/`
- `https://carnowash.ir/robots.txt`
- `https://carnowash.ir/sitemap.xml`
- `https://carnowash.ir/Google%20Search.html`
- `https://carnowash.ir/manager/reports`
- `https://www.carnowash.ir/login`

## Desired Indexing State

| URL Pattern | Desired State |
|---|---|
| `/login` | Indexable brand/login page |
| `/about/` | Indexable public product explanation |
| `/manager/*` | Not indexed |
| `/hq*` | Not indexed |
| `/support*` | Not indexed |
| `/attendance/*` | Not indexed |
| `/Google Search.html` | Removed / 410 |
| Unknown URLs | 404, not indexed |

## Search Console Actions

- [ ] Add and verify domain property for `carnowash.ir`.
- [ ] Submit `https://carnowash.ir/sitemap.xml` only after it serves XML.
- [ ] Request indexing for `/about/` and `/login`.
- [ ] Request removal for any indexed Google snapshot URLs.
- [ ] Check Coverage/Pages report for soft 404s.
- [ ] Check Crawled - currently not indexed for private route leakage.
- [ ] Review Page Experience/Core Web Vitals after enough field data is available.

