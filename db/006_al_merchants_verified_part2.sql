-- Phase 2 continued (part 2): live findings for the 4 merchants that
-- couldn't be checked in the previous session because their URLs arrived
-- concatenated without separators. Re-submitted individually and fetched
-- live in this session.

-- 1. neptun.al: CONFIRMED - this is the real, largest electronics chain in
-- Albania (per Wikipedia: Balfin Group, 31 stores in Albania). Live fetch
-- shows a very large category tree (elektroshtepiaket e medha, klima,
-- televizore, telefonia, informatike, gaming, foto/video, audio, etc.) and
-- an active promo/campaign-driven homepage. ToS link found in footer
-- ("Termat dhe Kushtet e Përgjithshme") but not yet opened and read.
-- Domain was already correct in 004 - just upgrading the note here.
UPDATE merchant_sources SET
  tos_notes = 'Confirmed largest Albanian electronics chain (Balfin Group) live. Extensive category tree confirmed. ToS link found in footer at what is presumably /termat-dhe-kushtet-e-pergjithshme (not yet opened/read - URL not confirmed exact). robots.txt not yet read by a human/tool.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'neptun.al');

-- 2. megateksa.com: this session's fetch tool itself returned
-- ROBOTS_DISALLOWED when attempting to fetch the homepage - i.e. the
-- site's own robots.txt explicitly disallows automated access (at least
-- for the path/user-agent this tool used). This is the first merchant in
-- the whole list with a DIRECTLY OBSERVED robots.txt signal, and it's a
-- negative one. Per spec section 3, this merchant must be treated as
-- explicitly disallowed, not just "pending review".
UPDATE merchant_sources SET
  allowed_by_robots = false,
  robots_txt_checked_at = now(),
  tos_notes = 'robots.txt DIRECTLY OBSERVED to disallow automated access - this session''s fetch tool refused the homepage fetch with a ROBOTS_DISALLOWED result. Do not crawl. Revisit only if the merchant later changes their robots.txt and explicitly permits it.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'megateksa.com');

-- 3. celular.al: CONFIRMED - Astro-based (server-rendered, NOT a client-side
-- SPA like globe.al/gjirafa50.com), which is good news for scraping: full
-- product catalog visible in the raw HTML this session's plain fetch tool
-- received, with clean canonical URLs at /products/<brand>/<slug>. ToS,
-- privacy policy, cookies policy, and FAQ all linked in the footer.
-- This is now, alongside shpresa.al, one of the two strongest structural
-- candidates for a first real connector.
UPDATE merchant_sources SET
  tos_notes = 'Astro (SSR) site - full product listing visible in plain HTML fetch, unlike the SPA sites. Clean URLs: /products/<brand>/<slug>. ToS at /kushtet-e-pergjithshme, privacy policy at /privacy-policy, cookies policy at /cookies-policy (links confirmed, content not yet read). robots.txt not yet read.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'celular.al');

-- 4. gjirafa50.com: CONFIRMED - real Kosovo electronics/general marketplace,
-- prices in EUR with VAT ("Përfshirë TVSH-në") shown inline. Like globe.al,
-- the homepage's raw HTML returned to this session's fetch tool was very
-- sparse (looks partly client-side rendered) - only a few price fragments
-- came through, not full product listings. Needs the Playwright connector
-- to properly inspect page structure, same caveat as globe.al.
UPDATE merchants SET status = 'UNSUPPORTED' WHERE domain = 'gjirafa50.com';
UPDATE merchant_sources SET
  tos_notes = 'Confirmed real Kosovo marketplace, EUR prices with VAT shown inline. Homepage HTML returned to this session''s plain fetch was sparse (partial JS rendering, similar to globe.al) - needs the Playwright connector for real structural inspection. robots.txt not yet read.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'gjirafa50.com');

-- Running tally after this migration:
--   Confirmed real + structurally promising for a first connector:
--     shpresa.al (WooCommerce), celular.al (Astro/SSR)
--   Confirmed real but needs Playwright (JS-rendered):
--     globe.al, gjirafa50.com
--   Confirmed real, large chain, not yet structurally inspected:
--     neptun.al, azaelectronics.com (OpenCart - already inspected, see 005)
--   Confirmed NOT crawlable:
--     megateksa.com (robots.txt disallows), ozone.al (bot-blocks fetches)
--   Removed from catalog (not an electronics retailer):
--     gotech.al
-- robots.txt has still only been DIRECTLY read for megateksa.com (via the
-- fetch tool's own refusal) - every other domain still needs either a human
-- reading robots.txt or the crawler's live ComplianceGate to confirm before
-- is_supported is ever set to true.
