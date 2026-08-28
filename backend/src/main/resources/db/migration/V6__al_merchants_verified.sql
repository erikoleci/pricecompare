-- Phase 2 continued: real findings from LIVE web fetches (this session had
-- actual internet access via web_search/web_fetch, unlike the session that
-- wrote 004_al_merchants_pending.sql). This does NOT set is_supported=true
-- for anyone - that still requires a full robots.txt read, which this
-- session's web_fetch tool could not retrieve for ANY of these domains
-- (robots.txt paths are never surfaced in search-engine results for small
-- regional sites, and the fetch tool refuses URLs that were not returned by
-- a prior search/fetch). The crawler's own ComplianceGate
-- (crawler/core/compliance.py) fetches robots.txt directly over the real
-- network at run time and is NOT subject to that restriction - so robots.txt
-- compliance is still fully enforced before any real crawl, just not
-- pre-verified by a human/assistant reading it in this chat session.
--
-- What WAS verified live in this session: real domain, storefront platform,
-- and whether the site is reachable/bot-blocked at all.

-- 1. shpresa.al: the domain guessed as unresolvable in 004 was WRONG.
-- The real site is shpresa.al itself (not "shpresa-al.al" or similar) -
-- confirmed by fetching https://shpresa.al/ live. It's a WooCommerce store
-- with clean, well-structured product pages (SKU, price, stock status,
-- full spec tables, brand taxonomy pages) at /product/<slug>/ and
-- /product-category/<path>/. Terms of Service found at
-- https://shpresa.al/term-conditions/ (covers the customer purchase
-- process; does not itself state a scraping/robots policy - that's what
-- robots.txt is for). This is currently the most promising first-connector
-- candidate structurally.
UPDATE merchants SET domain = 'shpresa.al', status = 'UNSUPPORTED'
WHERE domain = 'shpresa-al.pending-review.invalid';

DELETE FROM merchant_sources WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'shpresa.al') ;
INSERT INTO merchant_sources (merchant_id, source_type, base_url, robots_txt_url, tos_reviewed, tos_notes, is_supported)
SELECT id, 'SCRAPER', 'https://shpresa.al/', 'https://shpresa.al/robots.txt', false,
       'ToS at /term-conditions/ reviewed for customer-purchase terms only; does not address scraping. robots.txt not yet read by a human/tool - see comment above.',
       false
FROM merchants WHERE domain = 'shpresa.al';

-- 2. azaelectronics.com: domain confirmed live (was already correct in 004).
-- OpenCart-based storefront (index.php?route=product/product URLs and
-- also SEO-friendly slugs like /smartphone-xiaomi-...html). Prices in Lek
-- (ALL), full category tree, product listing pages show old/new price and
-- discount % inline.
UPDATE merchant_sources SET
  tos_notes = 'OpenCart storefront confirmed live; product URLs both as index.php?route=product/product&product_id=N and SEO slugs ending in N.html. robots.txt not yet read - see comment at top of this file.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'azaelectronics.com');

-- 3. ozone.al: the "Ozone" merchant in 004 was left domain-less as
-- ambiguous. It resolves to ozone.al, BUT that domain's server actively
-- blocked this session's fetch request with bot detection (HTTP-level
-- block, not a robots.txt directive). Recorded here as an explicit
-- negative signal - even after robots.txt is eventually read, this
-- merchant is unlikely to be crawlable without triggering the same block,
-- which would count as circumventing an access control and is out of
-- scope per spec section 3.
UPDATE merchants SET domain = 'ozone.al', status = 'UNSUPPORTED'
WHERE name = 'Ozone';

INSERT INTO merchant_sources (merchant_id, source_type, base_url, tos_reviewed, tos_notes, is_supported)
SELECT id, 'SCRAPER', 'https://ozone.al/', false,
       'Server actively blocked this session''s fetch with bot detection (HTTP-level, not robots.txt). Treat as NOT crawlable until/unless the merchant explicitly authorizes access via another channel (API, feed).',
       false
FROM merchants WHERE domain = 'ozone.al'
ON CONFLICT DO NOTHING;

-- 4. gotech.al: the "GoTech" merchant in 004 was left domain-less as
-- ambiguous. It resolves to gotech.al, but that site is a tech
-- blog/IT-consulting company (web development, IT consulting, articles) -
-- NOT an electronics retailer with a product catalog. It has nothing to
-- scrape for this platform's purpose. Remove it from the merchant catalog
-- entirely rather than leave it marked UNSUPPORTED (which would incorrectly
-- imply it's an in-scope retailer pending review).
DELETE FROM merchant_sources WHERE merchant_id = (SELECT id FROM merchants WHERE name = 'GoTech');
DELETE FROM merchants WHERE name = 'GoTech';

-- 5. globe.al: the "Globe" merchant in 004 was left domain-less as
-- ambiguous (there's an unrelated travel-blog "Globe.al" per earlier
-- ahrefs search results). Live fetch of https://globe.al/ this session
-- shows it IS an electronics storefront ("Cilësia është kursim!" tagline),
-- but it's a client-side rendered SPA - the raw HTML this session's fetch
-- tool received was just a JS app shell with no product data. A real
-- crawl will need the Playwright-based connector (which renders JS) rather
-- than a plain HTTP fetch; this session's simple fetch tool can't confirm
-- product-page structure for that reason.
UPDATE merchants SET domain = 'globe.al', status = 'UNSUPPORTED'
WHERE name = 'Globe';

INSERT INTO merchant_sources (merchant_id, source_type, base_url, tos_reviewed, tos_notes, is_supported)
SELECT id, 'SCRAPER', 'https://globe.al/', false,
       'Confirmed real electronics storefront but is a client-side rendered SPA - plain HTTP fetch returns only an empty JS app shell. Needs the Playwright connector (renders JS) to inspect actual product-page structure. robots.txt not yet read.',
       false
FROM merchants WHERE domain = 'globe.al'
ON CONFLICT DO NOTHING;

-- Still unresolved after this session (URLs were provided by the user but
-- arrived concatenated without separators in chat, so this session's
-- fetch tool could not isolate them as distinct URLs to fetch):
--   neptun.al, megateksa.com, celular.al, gjirafa50.com
-- These remain exactly as inserted in 004 (UNSUPPORTED, is_supported=false).
-- Re-fetching them individually (one URL per message, or with whitespace/
-- newlines between them) in a future session would resolve this.

COMMENT ON TABLE merchant_sources IS
  'is_supported stays false for every row until robots.txt itself is read '
  '(the crawler''s own ComplianceGate does this live at run time - see '
  'crawler/core/compliance.py) and a human reviews the ToS. See '
  'db/004_al_merchants_pending.sql and db/005_al_merchants_verified.sql for '
  'what has and has not been checked so far.';
