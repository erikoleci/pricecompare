-- Real robots.txt compliance review for 7 merchants (spec section 3), based
-- on robots.txt content the user fetched directly and pasted into chat -
-- not assumed, not guessed. Follows the same pattern as
-- 008_neptun_compliance_review.sql: allowed_by_robots is set from what the
-- file actually says; tos_reviewed is NOT touched here because only
-- robots.txt content was provided this round, not ToS text - that stays a
-- separate step. is_supported is intentionally left untouched - only a
-- human clicking "Approve" in /admin (which requires allowedByRobots=true
-- AND tosReviewed=true - see AdminResource.updateCompliance) makes that
-- call, never a migration.

-- 1. shpresa.al (WooCommerce + Yoast SEO plugin):
--   Disallows only /wp-content/uploads/wc-logs/, .../woocommerce_transient_files/,
--   .../woocommerce_uploads/, add-to-cart query strings, and /wp-admin/
--   (with admin-ajax.php explicitly re-allowed - that's the standard
--   WooCommerce AJAX endpoint, not a real admin page). The Yoast block then
--   adds a SECOND "User-agent: *" group with an EMPTY Disallow (i.e. "allow
--   everything") and declares a sitemap. Product and category pages are not
--   disallowed anywhere. -> ALLOWED.
UPDATE merchant_sources SET
    allowed_by_robots = true,
    robots_txt_checked_at = now(),
    tos_notes = COALESCE(tos_notes || ' | ', '') ||
        'robots.txt (pasted by user ' || now()::date || '): WooCommerce+Yoast default - only /wp-admin/ and a few upload/cart paths disallowed (admin-ajax.php explicitly re-allowed), Yoast block explicitly clears Disallow for "*" and declares Sitemap: https://shpresa.al/sitemap_index.xml. Product/category pages fully allowed. ToS text itself not yet reviewed in this round (see earlier /term-conditions/ note from live fetch).'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'shpresa.al');

-- 2. celular.al: the user could not find a robots.txt at all - fetching
--   https://www.celular.al/robots.txt returns "404 | Faqja që kërkoni nuk
--   ekziston!" (the site's own custom 404 page, not a robots.txt). Per the
--   robots.txt spec that both Google and the standard (RFC 9309) follow: a
--   404/not-found response on /robots.txt means the site has published NO
--   restrictions, and crawlers may treat it as fully allowed - this is
--   different from a 5xx server error (which conventionally means "assume
--   fully disallowed until it's fixed"). -> ALLOWED (by absence of any
--   restriction, confirmed via a real fetch, not assumed).
UPDATE merchant_sources SET
    allowed_by_robots = true,
    robots_txt_checked_at = now(),
    tos_notes = COALESCE(tos_notes || ' | ', '') ||
        'robots.txt (checked by user ' || now()::date || '): does not exist - https://www.celular.al/robots.txt returns the site''s own custom 404 page. Per RFC 9309 / Google''s documented interpretation, a 404 on /robots.txt means no restrictions were published, so crawling is treated as fully allowed (unlike a 5xx error, which defaults to fully disallowed). Note this is still an Astro/JS-rendered site per the earlier live fetch - price/stock/SKU need the Playwright connector regardless of this robots.txt result. ToS text itself not yet reviewed (link found earlier at /kushtet-e-pergjithshme, not yet read).'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'celular.al');

-- 3. gjirafa50.com (nopCommerce): disallows a long list of DYNAMIC/
--   FUNCTIONAL routes only - cart, checkout, account/customer pages, forum
--   actions, wishlist, compare-list actions, /search? (the internal search
--   RESULTS page specifically), /admin, /install, etc. None of these are
--   product detail or category listing pages. -> ALLOWED for product/
--   category browsing; avoid the specific disallowed paths/params listed
--   (especially /search? - use a different discovery method, e.g. category
--   pages or the sitemap, not the site's own search results page).
UPDATE merchant_sources SET
    allowed_by_robots = true,
    robots_txt_checked_at = now(),
    tos_notes = COALESCE(tos_notes || ' | ', '') ||
        'robots.txt (pasted by user ' || now()::date || '): nopCommerce default - disallows only dynamic/functional routes (cart, checkout, account, admin, forum actions, wishlist, compare-list, /search? results page, etc.). Product/category pages are NOT in the disallow list. Sitemap declared at http://gjirafa50.com/sitemap.xml (note: http, not https - worth double-checking the live scheme). Discovery should avoid /search? specifically and use category pages or the sitemap instead. Still a partly JS-rendered homepage per the earlier live fetch - needs Playwright to confirm product-page structure. ToS text itself not yet reviewed.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'gjirafa50.com');

-- 4. globe.al: two things worth separating clearly.
--   (a) There's a malformed leading line "Disallow: globe.al/robots.txt"
--       under the first "User-agent: *" group - this value doesn't start
--       with "/", so per the robots.txt spec it's not a valid path and
--       compliant parsers ignore it (it doesn't block anything real).
--   (b) A second, well-formed "User-agent: *" group grants
--       "Content-Signal: search=yes,ai-train=no,use=reference" with
--       "Allow: /" - i.e. generic/unnamed crawlers (which is what this
--       project's own connector identifies as - see
--       crawler/merchants/_template/connector.py's User-Agent string) are
--       explicitly allowed for search/reference use, explicitly NOT for
--       AI training. A price-comparison index is a "reference" use, not
--       "ai-train" - compatible.
--   (c) Several NAMED bots are explicitly disallowed entirely (Disallow: /):
--       Amazonbot, Applebot-Extended, Bytespider, CCBot, ClaudeBot,
--       CloudflareBrowserRenderingCrawler, Google-Extended, GPTBot,
--       meta-externalagent. IMPORTANT: "ClaudeBot" (Anthropic's own web
--       crawler) is explicitly named and disallowed here. This does not
--       apply to this project's own crawler (which uses a distinct,
--       honestly-identified User-Agent, not "ClaudeBot" - see spec
--       section 3's requirement to never spoof identity), but it's a
--       directly relevant real-world data point given who's building this
--       project's tooling right now, so it's recorded here rather than
--       silently only acting on the generic "*" allowance.
--   -> ALLOWED for this project's own honestly-identified crawler bot,
--      under the generic "*" / Content-Signal rule; NOT allowed for a bot
--      literally identifying itself as "ClaudeBot" or any of the other
--      explicitly named bots above.
UPDATE merchant_sources SET
    allowed_by_robots = true,
    robots_txt_checked_at = now(),
    tos_notes = COALESCE(tos_notes || ' | ', '') ||
        'robots.txt (pasted by user ' || now()::date || '): generic "*" user-agent is allowed (Content-Signal: search=yes,ai-train=no,use=reference; Allow: /) - compatible with this project''s reference/comparison use case. A malformed early "Disallow: globe.al/robots.txt" line (missing leading slash) is not a valid path and blocks nothing. HOWEVER several NAMED bots are explicitly fully disallowed, including "ClaudeBot" specifically (also Amazonbot, Applebot-Extended, Bytespider, CCBot, CloudflareBrowserRenderingCrawler, Google-Extended, GPTBot, meta-externalagent) - this project''s connector must use its own distinct, honest User-Agent string (never "ClaudeBot" or any of these), which it already does per crawler/merchants/_template/connector.py. Still a JS-rendered SPA per the earlier live fetch - needs Playwright regardless. ToS text itself not yet reviewed.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'globe.al');

-- 5. gotech.al (WooCommerce, same boilerplate as shpresa.al): only
--   /wp-admin/ and upload/cart paths disallowed, admin-ajax.php
--   re-allowed, sitemap declared. Product/category pages allowed. -> ALLOWED.
UPDATE merchant_sources SET
    allowed_by_robots = true,
    robots_txt_checked_at = now(),
    tos_notes = COALESCE(tos_notes || ' | ', '') ||
        'robots.txt (pasted by user ' || now()::date || '): WooCommerce default, same shape as shpresa.al - only /wp-admin/ and a few upload/cart paths disallowed (admin-ajax.php re-allowed). Sitemap at https://gotech.al/sitemap_index.xml. Product/category pages fully allowed. ToS text itself not yet reviewed.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'gotech.al');

-- 6. azaelectronics.com (OpenCart): disallows a large set of QUERY-STRING
--   parameter combinations (limit, sort, order, price, brand_tabletpc,
--   color, filter_tag, mode, cat, dir, product_id-as-query-param, minprice,
--   maxprice, checkout/account/search routes) plus /admin/, /system/,
--   /catalog/. These are OpenCart's duplicate-content-prevention rules for
--   filtered/sorted listing URL variants, not a block on product pages
--   themselves - canonical SEO-slug product URLs (e.g. ending in
--   product-name.html, as seen in the earlier live category-listing fetch)
--   and plain category pages are NOT in this list. -> ALLOWED for canonical
--   product/category URLs; the crawler must avoid constructing URLs with
--   any of the listed disallowed query parameters (sort/filter/price-range
--   links on listing pages should not be followed - use pagination via
--   allowed parameters only, or the plain category URL).
UPDATE merchant_sources SET
    allowed_by_robots = true,
    robots_txt_checked_at = now(),
    tos_notes = COALESCE(tos_notes || ' | ', '') ||
        'robots.txt (pasted by user ' || now()::date || '): OpenCart default - disallows many query-string parameter combinations (sort/order/price/color/filter/mode/cat/dir/product_id-as-param/minprice/maxprice) plus /admin/, /system/, /catalog/. These target duplicate-content URL variants, not product pages themselves - canonical SEO-slug product URLs and plain category pages are allowed. Connector must not follow sort/filter query-links on listing pages; use canonical URLs only. ToS text itself not yet reviewed.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'azaelectronics.com');

-- 7. ozone.al (PrestaShop): disallows controller-based dynamic pages
--   (address, cart, checkout, my-account, order, login, registration,
--   search, password-recovery, etc.) and internal directories (/app/,
--   /cache/, /admin-equivalent dirs, /vendor/, etc.). Product/category
--   pages themselves are NOT in the disallow list -> robots.txt technically
--   ALLOWS crawling product/category pages.
--   BUT this is recorded alongside the earlier, separately-confirmed
--   finding (005_al_merchants_verified.sql) that ozone.al's server
--   actively returned an HTTP-level bot-detection block when this
--   project's own fetch tool tried to reach the site - i.e. even where
--   robots.txt permits it, the site is actively preventing automated
--   access through other means. robots.txt permission does not override or
--   excuse a live technical block; per spec section 3 this project does
--   not attempt to bypass/evade active anti-bot measures. -> allowed_by_robots
--   recorded as true (accurately reflecting the file), but this merchant
--   should stay OFF the crawl list regardless, and that reasoning is kept
--   explicit here rather than overwriting the earlier bot-blocking note.
UPDATE merchant_sources SET
    allowed_by_robots = true,
    robots_txt_checked_at = now(),
    tos_notes = COALESCE(tos_notes || ' | ', '') ||
        'robots.txt (pasted by user ' || now()::date || '): PrestaShop default - disallows controller/account/cart/checkout/admin-internals paths only; product/category pages are NOT disallowed, so the FILE technically permits crawling. Recorded as allowed_by_robots=true for accuracy. HOWEVER this does not change this merchant''s practical status: the earlier live-fetch finding stands - ozone.al''s server actively returned an HTTP-level bot-detection block against this project''s own fetch attempt, independent of robots.txt. A permissive robots.txt does not authorize working around an active technical block (spec section 3). Recommendation unchanged: do not approve this merchant unless the site''s bot-detection behavior is independently re-verified as no longer blocking, or the merchant grants access through another channel (API/feed).'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'ozone.al');
