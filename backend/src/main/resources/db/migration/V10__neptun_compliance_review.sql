-- Real compliance review for Neptun (spec section 3), based on content the
-- user fetched directly and pasted into chat - not assumed, not guessed.
--
-- robots.txt (fetched by the user from https://www.neptun.al/robots.txt):
--   User-agent: *
--   Disallow: /bin/ /datasource/ /index/ /logs/ /temp/ /Transformations/
--             /MasterPages/ /UserControls/
--   Sitemap: https://www.neptun.al/sitemap.xml
--   -> Only internal/technical (Sitefinity CMS) paths are disallowed.
--      Product and category pages are NOT disallowed. A sitemap is
--      published, which also helps with discovery.
--
-- ToS (fetched live from https://www.neptun.al/termat-dhe-kushtet-e-p-rgjithshme.nspx):
--   Titled "Termat dhe Kushtet e Përgjithshme" but its actual content is
--   entirely a personal-data-protection policy (GDPR-style: what customer
--   data is collected, how it's processed, retention, customer rights).
--   It does not mention scraping, crawling, bots, or automated access at
--   all - neither permitting nor prohibiting it. This is the ONLY page
--   under that title/URL; there is no separate general "terms of use"
--   document on the site.
--
-- Conclusion recorded here: allowed_by_robots = true (explicit, from the
-- file itself), tos_reviewed = true (the document was read in full; it
-- simply doesn't address this topic - recorded as-is, not spun as an
-- explicit permission it doesn't contain). is_supported is intentionally
-- LEFT false - per this project's established workflow, only a human
-- clicking "Approve" in /admin (which requires exactly these two fields to
-- already be true - see AdminResource.updateCompliance) makes that call,
-- not a migration.

UPDATE merchant_sources SET
    allowed_by_robots = true,
    robots_txt_checked_at = now(),
    tos_reviewed = true,
    tos_notes = 'robots.txt (fetched ' || now()::date || '): only disallows internal/technical paths (/bin/, /datasource/, /index/, /logs/, /temp/, /Transformations/, /MasterPages/, /UserControls/ - Sitefinity CMS internals). Product/category pages are allowed; sitemap published at /sitemap.xml. ToS (https://www.neptun.al/termat-dhe-kushtet-e-p-rgjithshme.nspx, read in full): the only document under that title is a personal-data-protection policy (GDPR-style) - it does not address scraping/crawling/bots/automated access at all, neither permitting nor prohibiting. No separate general terms-of-use document exists on the site. Ready for human approval in /admin.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'neptun.al');
