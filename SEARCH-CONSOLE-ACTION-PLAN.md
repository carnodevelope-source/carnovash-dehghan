# Search Console Action Plan - CarnoWash

## Priority 1: Fix Live Serving Before GSC Submission

Do not submit the current live sitemap yet. Production currently serves SPA HTML for `/sitemap.xml`, `/robots.txt`, and `/llms.txt`.

Required first:
- Deploy current local frontend build.
- Apply production nginx static-file and private-route noindex rules.
- Verify correct content types and status codes.

## Priority 2: URL Inspection

Use URL Inspection on:
- `https://carnowash.ir/login`
- `https://carnowash.ir/about/`
- `https://carnowash.ir/sitemap.xml`
- `https://carnowash.ir/robots.txt`
- `https://carnowash.ir/manager/reports`
- `https://carnowash.ir/Google%20Search.html`

Expected:
- `/login` and `/about/`: crawlable/indexable.
- private routes: blocked from indexing by `X-Robots-Tag`.
- Google snapshot: 410 removed.

## Priority 3: Sitemap Submission

Submit only after this passes:

```txt
https://carnowash.ir/sitemap.xml
```

The sitemap should include only public URLs:
- `https://carnowash.ir/about/`
- `https://carnowash.ir/login`

## Priority 4: Removals

If indexed, submit temporary removals for:
- `https://carnowash.ir/Google%20Search.html`
- `https://carnowash.ir/Google%20Search_files/*`
- any `/manager/`, `/hq`, `/support`, or `/attendance/` URLs.

## Priority 5: Performance And Enhancements

- Re-run PageSpeed Insights after deployment.
- Monitor Core Web Vitals once CrUX data exists.
- Check Enhancements for structured data after JSON-LD goes live.
- Track non-brand queries only after public product pages are added.

