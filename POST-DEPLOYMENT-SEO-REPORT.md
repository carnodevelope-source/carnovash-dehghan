# Post-Deployment Production SEO Report - CarnoWash

Audit date: 2026-07-15  
Production domain: `https://carnowash.ir`  
Local build compared: `frontend/dist` from the current workspace  
Business model detected: private B2B SaaS / operational SPA for carwash management in Iran

## Executive Summary

Production is not yet serving the current local SEO build. The live server returns the old SPA shell for crawler files, public pages, missing assets, and unknown URLs. This creates broken sitemap/robots behavior, soft-404 duplication, weak metadata, missing structured data, and no protection headers for private app routes.

Local source/build is substantially better than production. The safe code/config fixes now in the repo are designed to make the next deploy safer: stricter frontend healthcheck, explicit `/about/` static serving, HTTPS edge 410 guards for old Google snapshot files, and edge noindex headers for private route groups.

Production validation score: 42/100  
Local post-fix posture: 87/100 for a private app SEO baseline

## Verified Production Issues

| Area | Production Evidence | Severity |
|---|---|---|
| `robots.txt` | Returns `200 text/html` SPA shell, not text robots policy | Critical |
| `sitemap.xml` | Returns `200 text/html` SPA shell, not XML | Critical |
| `llms.txt` | Returns SPA shell, so GEO/AI guidance is not live | High |
| `/about/` | Returns SPA shell with old `CarWash` title, not static about page | High |
| `/login` metadata | Title is `CarWash`; no meta description, canonical, OG/Twitter, or JSON-LD | High |
| Private routes | `/manager/reports` and `/attendance/test-token` return `200` without `X-Robots-Tag` | High |
| Unknown URLs | `/does-not-exist-seo-test` returns `200` SPA shell | High |
| Old Google snapshot | `/Google%20Search.html` is still live with Google Search content | Critical |
| Missing assets | Optimized local assets return `text/html` shell instead of image/video content | High |
| Canonical host | `www.carnowash.ir` serves duplicate app instead of redirecting to non-www | High |
| Root redirect | `/` uses `302` to `/login`; local expected `301` | Medium |
| Security headers | HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy missing live | High |
| Caching | No visible `Cache-Control` on live HTML/assets | Medium |

## Local-Only Issues

- Local files are correct but not deployed live: `robots.txt`, `sitemap.xml`, `llms.txt`, `/about/index.html`, optimized image/video assets.
- Local nginx config is safer than production, but the live server reports `nginx/1.26.0 (Ubuntu)`, suggesting the public nginx/vhost is not the checked-in container edge config.
- Route-level SEO is still partly JS-applied for the SPA; public growth pages should remain static or server-rendered where possible.

## Requires Google Search Console Data

- Whether Google has indexed `/Google Search.html` or `/Google Search_files/`.
- Whether Google has indexed soft-404 unknown URLs.
- Whether private app routes were discovered or indexed.
- URL Inspection status for `/login`, `/about/`, `/robots.txt`, `/sitemap.xml`, and representative private routes.
- Sitemap submission and processing status after production serves valid XML.
- Real Core Web Vitals field data from CrUX/GSC.

## Requires Server Or DNS Access

- Point the public vhost to the checked-in production nginx behavior.
- Force `https://www.carnowash.ir/*` to `https://carnowash.ir/*`.
- Ensure `/robots.txt`, `/sitemap.xml`, `/llms.txt`, `/about/`, images, fonts, and assets are served before SPA fallback.
- Ensure missing assets return `404`, not SPA HTML.
- Ensure `/Google Search.html` and `/Google Search_files/` return `410`.
- Add HSTS/security/cache headers at the actual public edge if the Docker edge is not the public edge.

## Safe Fixes Implemented Locally

- Added HTTPS edge 410 guards for old Google Search snapshot paths.
- Added HTTPS edge `X-Robots-Tag` for private route groups.
- Added explicit frontend nginx static serving for `/about/`.
- Strengthened frontend Docker healthcheck so deployments fail if SEO static files and optimized login video are missing.

## Validation Commands Used

- `npm.cmd run build`
- `.venv\Scripts\python.exe codex-seo\scripts\analyze_technical.py https://carnowash.ir/login --json`
- `.venv\Scripts\python.exe codex-seo\scripts\analyze_schema.py https://carnowash.ir/login --json`
- `.venv\Scripts\python.exe codex-seo\scripts\analyze_performance.py https://carnowash.ir/login --json`
- `.venv\Scripts\python.exe codex-seo\scripts\analyze_geo.py https://carnowash.ir/login --json`

## Post-Deploy Verification Targets

- `/robots.txt`: `200`, `text/plain`, includes `Sitemap: https://carnowash.ir/sitemap.xml`
- `/sitemap.xml`: `200`, XML content type, includes `/about/` and `/login`
- `/llms.txt`: `200`, text content, not SPA HTML
- `/about/`: static HTML with H1, canonical, meta description, JSON-LD
- `/Google%20Search.html`: `410`
- `/manager/reports`: `X-Robots-Tag: noindex, nofollow, noarchive`
- `/does-not-exist-seo-test`: `404`
- `www.carnowash.ir/login`: `301` to `https://carnowash.ir/login`

