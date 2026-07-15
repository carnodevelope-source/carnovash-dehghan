# SEO Action Plan - CarnoWash

## Critical

1. Deploy current frontend and nginx changes.
   - Live audit still shows the old shell for `/llms.txt`, no canonical, no schema, and missing visible security headers.
   - After deployment, `https://carnowash.ir/robots.txt`, `/sitemap.xml`, and `/llms.txt` must return real text/XML files, not SPA HTML.

2. Keep removed Google Search artifacts out of `frontend/public`.
   - Implemented: deleted tracked snapshot files and added 410 guards.
   - After deployment, `/Google%20Search.html` should return 410.

## High

1. Optimize login LCP media.
   - Implemented: `Mobile-bg-640.avif`, `Mobile-bg-640.webp`, `login-poster.avif`, and `login-poster.webp`.
   - Implemented: login video now uses `preload="metadata"` and a compressed poster.
   - Implemented: replaced the 4.1 MB login MP4 with `login-hero.mp4` at 681,039 bytes.

2. Create a public crawlable explanation page if SEO acquisition matters.
   - Implemented: `frontend/public/about/index.html`.
   - Implemented: added `/about/` to `sitemap.xml`, `robots.txt`, and `llms.txt`.
   - Keep `/manager`, `/hq`, `/support`, and `/attendance` private/noindexed.

3. Re-run live audits after deployment.
   - `.venv\Scripts\python.exe codex-seo\scripts\analyze_technical.py https://carnowash.ir/login --json`
   - `.venv\Scripts\python.exe codex-seo\scripts\analyze_schema.py https://carnowash.ir/login --json`
   - `.venv\Scripts\python.exe codex-seo\scripts\analyze_geo.py https://carnowash.ir/login --json`
   - `.venv\Scripts\python.exe codex-seo\scripts\analyze_performance.py https://carnowash.ir/login --json`

## Medium

1. Add a tested CSP at the edge.
   - Start in report-only mode.
   - Confirm Vue assets, API calls, fonts, media, and JSON-LD remain valid.

2. Configure backlink data sources.
   - Add Moz or Bing Webmaster credentials.
   - Provide known backlinks for verification.
   - Re-run backlink and competitor gap analysis.

3. Improve mobile UX/accessibility constraints.
   - Raise mobile base text and control sizes where practical.
   - Preserve compact operational layout, but keep tap targets near 44-48px.

4. Continue media cleanup.
   - Implemented: broken mobile sidebar art now points to `Mobile-bg-640.webp`.
   - Remaining: remove or replace the original `Mobile-bg.jpg` once legacy image fallbacks can be dropped.

## Low

1. Consider IndexNow.
   - Add key file and submit login/about URLs after deployment.

2. Add richer Organization data later.
   - Add logo, contact, and `sameAs` only after verified public URLs exist.

3. Add local SEO only if CarnoWash should market a physical office/location.
   - Requires verified address, phone, opening hours, geo coordinates, and GBP/NAP strategy.
