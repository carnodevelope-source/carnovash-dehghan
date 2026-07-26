# Current technical SEO audit — CarnoWash

**Audited:** 2026-07-26
**Status:** Audit complete; implementation and post-change verification pending.
**Evidence scope:** Current repository, live robots/sitemap HTTP checks, `Docs/seo-analyze.md` (historical single-page report), and source inspection. No Search Console, CrUX, analytics, or production-secret access was available.

## 1. Executive summary

CarnoWash is a Vue/Vite history-mode application backed by Django and delivered through frontend and edge Nginx. The indexable public surface is intentionally narrow: `/` and `/about/`. Operational panels, login, attendance, support, manager, and HQ routes must remain noindex.

Unlike the other two projects, production robots and sitemap endpoints are currently valid and return the expected document types. The source still has meaningful technical risks: an apparent credential in an example environment file, a two-hop `http://www` canonical redirect, soft 404 behavior for arbitrary URLs, header inheritance gaps on private-route locations, duplicate SoftwareApplication entity data, and a client-rendered public landing page.

## 2. Current architecture

| Area | Current implementation |
|---|---|
| Frontend | Vue 3 + Vite + Vue Router history mode |
| Backend | Django API/admin |
| Delivery | Static Nginx frontend + TLS edge Nginx |
| Indexable routes | `/`, `/about/` |
| Alias | `/landing` redirects/canonicalizes to `/` |
| Noindex/private routes | `/login`, `/attendance/:token`, `/hq`, `/panel`, `/manager/*`, `/support` |
| SEO implementation | Frontend entry documents, static about document, router metadata, robots/sitemap, both Nginx layers |

SEO maturity is **good for a compact product site**, but the SPA fallback and server header issues should be resolved before publishing more pages.

## 3. Prioritized findings

| Severity | Issue | Evidence and affected route/file | Why it matters | Proposed fix | Risk | Verification |
|---|---|---|---|---|---|---|
| Critical | Apparent API credential in tracked example files | `/.env.production.example`, `/.env.docker.example`, and `/.env.xampp.example` contained non-placeholder IranPayamak API-key-like values. Values are intentionally not copied into this report. | A leaked provider credential can be abused and may have been captured in history. | Revoke/rotate it, replace it with empty documented placeholders, and run repository/history secret scanning. | Requires provider action; source change is safe. | Provider shows old key invalid; secret scanner finds no active value. |
| High | `http://www` has a redirect chain | `docker/edge-nginx/templates/site-ssl.conf.template` first redirects HTTP to `https://$host`, then HTTPS redirects `www` to apex. | Avoidable redirect hop slows crawling/navigation and weakens canonical consistency. | Make HTTP `www` redirect straight to `https://carnowash.ir$request_uri`. | Low if ACME handling is preserved. | `curl -IL http://www.carnowash.ir/` has one 301. |
| High | Unknown URLs are soft 404s | `frontend/nginx/default.conf` sends arbitrary paths to `index.html`; `frontend/src/router/index.js` only handles NotFound client-side. | Crawlers receive 200 plus an initially indexable shell rather than a clear 404. | Restrict SPA fallbacks to known route families and return 404 for all others. | Valid deep links must be enumerated. | `/does-not-exist` returns 404; all declared app routes still work. |
| High | Security headers are lost in private Nginx locations | Route-level `add_header X-Robots-Tag` in `frontend/nginx/default.conf` and edge template supersedes inherited header sets. | Private responses can lose HSTS/CSP/XFO/nosniff/referrer protections. | Repeat the complete header policy in overriding locations or extract a tested shared include. | Header/CSP changes can affect embeds; stage first. | Compare `curl -I` headers for public and every private route family. |
| Medium | Public content and FAQ schema are CSR-dependent | `frontend/index.html` hides its marketing fallback, while `frontend/src/views/landing/LandingView.vue` renders content and FAQ JSON-LD after Vue starts. | Rendering dependency can delay indexing and structured-data processing. | Prerender/SSR `/`, or deliver the relevant visible semantic content and JSON-LD in initial HTML. | Architecture work; avoid duplicating conflicting text/schema. | Raw vs rendered HTML and Rich Results Test after deployment. |
| Medium | SoftwareApplication entity conflicts across pages | `frontend/index.html` and `frontend/public/about/index.html` use the same `@id` `https://carnowash.ir/#software` but inconsistent `url` values. | Search engines may merge contradictory entity statements. | Keep one consistent homepage URL for that entity, or remove it from the about page. | Low. | Parse both JSON-LD blocks and compare entity values. |
| Medium | Excess preloads can compete with LCP | `frontend/index.html` preloads four fonts plus login/mobile assets that are not needed for every homepage visit. | Unneeded high-priority resources contend with hero/LCP assets. | Retain only above-fold font/hero preloads; load login/mobile-only assets on demand. | Font timing needs visual QA. | Browser waterfall and Lighthouse lab run. |
| Low | IndexNow is absent | No key, endpoint, or publish hook found. | Bing-family discovery is slower when public content becomes dynamic. | Add only when public content updates regularly. | Low; not urgent for two static URLs. | Key file and URL-submission hook when implemented. |

## 4. Route indexability matrix

| Route family | Classification | Required directive |
|---|---|---|
| `/` | Index | 200, self-canonical, sitemap, public JSON-LD |
| `/about/` | Index | 200, unique self-canonical, sitemap |
| `/landing` | Redirect | One-hop 301 to `/` |
| `/login`, `/attendance/:token`, `/hq`, `/panel`, `/manager/*`, `/support` | Noindex | HTTP response noindex plus no sitemap |
| `/api/`, admin/data endpoints | Block from crawling / noindex | Not content, never sitemap |
| Unknown paths | Remove | HTTP 404 |

## 5. Metadata matrix

| Indexable route | Title/description | Canonical | Robots/social | Status |
|---|---|---|---|---|
| `/` | Unique Persian product title and description | Self-canonical | index/follow; OG/Twitter present | Good source implementation |
| `/about/` | Unique document metadata | Self-canonical | Public metadata present | Validate after schema URL correction |
| Private routes | Route-specific noindex configuration | No sitemap | Nginx header must be complete | Header inheritance needs correction |

## 6. Structured data status

Source contains Organization, WebSite, WebPage, and SoftwareApplication JSON-LD appropriate to the public product pages. Syntax is valid on source inspection. The duplicate SoftwareApplication entity needs consistent `url` data. FAQ markup should reflect visible FAQ content, but FAQ rich results are restricted by Google to authoritative government/health sites; do not treat it as a Google rich-result enhancement for this commercial product site.

## 7. Performance and Core Web Vitals

No field data was available. Source shows strong foundations: responsive WebP hero handling, image dimensions, high-priority LCP treatment, lazy loading for noncritical images, `font-display: swap`, and suitable mobile touch target sizing. The known risks are unnecessary initial preloads and the public CSR dependency. Measure lab performance after the changes and field CWV in CrUX/Search Console afterward; do not infer INP from TBT.

## 8. Content, internal links, images, accessibility, and AI visibility

- The public page meets the previous report’s metadata/H1 baseline and has a small, intentional content footprint. Publish only distinct feature/use-case pages with original evidence.
- Robots permits public-page access to major AI search crawlers while excluding operational paths. This supports AI-search visibility without exposing private pages.
- Sitemap correctly lists only `/` and `/about/`. No sitemap changes are currently justified.
- Semantic headings, alt text, responsive images, and mobile touch targets are strong in source. Avoid importing operational screenshots/data into public content.

## 9. Recommended implementation order

1. Revoke/rotate the apparent credential and remove it from source/history as appropriate.
2. Fix direct canonical redirect and route 404 behavior.
3. Make header policy consistent across edge and frontend route locations.
4. Correct structured-data identity and trim noncritical preloads.
5. Plan prerendering before expanding the public content surface.

## 10. Files requiring modification

- `.env.production.example`
- `docker/edge-nginx/templates/site-ssl.conf.template`
- `frontend/nginx/default.conf`
- `frontend/public/about/index.html`
- `frontend/index.html`
- potentially the public landing build strategy

## 11. Risks and verification checklist

Never include active provider secrets in example files or reports. Preserve ACME challenge routing while changing HTTP redirects. Do not use robots.txt as a privacy boundary; use authentication and response-level noindex.

- [ ] The old provider key is revoked and not present in source/history scans.
- [ ] HTTP `www` goes directly to HTTPS apex; HTTPS `www` also canonicalizes in one hop.
- [ ] Unknown routes return 404 and declared routes still render correctly.
- [ ] Public/private route headers retain HSTS, CSP, framing, nosniff, referrer, and robots protections.
- [ ] `/` and `/about/` have consistent JSON-LD entity IDs and URLs.
- [ ] Live robots/sitemap remain valid after deployment.
- [ ] Authorized operator checks sitemap, canonical selection, and CWV in Search Console.

## Completion status — 2026-07-26

**Implemented locally:** removed the provider key from all tracked environment example files; made the certificate-enabled HTTP redirect target the canonical apex directly; return real 404s for unknown frontend paths while retaining declared application routes; restored complete security headers in Nginx locations that set response-specific headers; aligned client-updated social metadata with the server hero image; removed noncritical landing preloads; removed the one-item breadcrumb and duplicate client SoftwareApplication markup; prevented tokenized attendance URLs from declaring the login page canonical; and removed ignored sitemap priority/changefreq hints.

**Still requires production/business action:** revoke/rotate the removed provider key and scan repository history; deploy and test Nginx behavior; select one authoritative Persian brand spelling and reconcile the remaining duplicate SoftwareApplication entity in the static about document; decide whether the commercial FAQ schema is retained for AI parsing; and collect post-deploy CWV/Search Console data.
