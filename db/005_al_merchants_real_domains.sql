-- User provided the real URLs for 4 more merchants directly (globe.al,
-- shpresa.al, ozone.al, gotech.al) plus reconfirmed azaelectronics.com.
-- Fetching each (now permitted since the URLs were given directly) gave
-- real, useful signal even without a robots.txt answer:
--
--   shpresa.al  - real electronics shop ("Shpresa AL Computers"), server-
--                 rendered HTML with real prices in Lek, clean product
--                 URLs (shpresa.al/product/<slug>/) - straightforward to
--                 parse once compliance is confirmed.
--   gotech.al   - real electronics shop ("GoTech Electronics", part of
--                 DUKA Group), WooCommerce-style server-rendered HTML,
--                 real prices, clean product URLs - same as above.
--   globe.al    - real shop but a JS single-page app: a plain fetch
--                 returns only "You need to enable JavaScript to run this
--                 app." - a compliant crawler would need real browser
--                 rendering (Playwright, already in the architecture),
--                 not just an HTTP GET.
--   ozone.al    - a plain fetch was refused outright by the site's own bot
--                 detection. This is a real caution signal, not a tooling
--                 gap: spec section 3 explicitly forbids anti-bot bypass,
--                 so this merchant should stay unsupported unless the
--                 owner's ToS/API offers a sanctioned way in.
--
-- None of this is a robots.txt/ToS review - that still hasn't happened for
-- any of them, for the same reason as before (no tool in this session can
-- reliably fetch a robots.txt that wasn't already surfaced by search).
-- is_supported / crawler_enabled stay false across the board.

UPDATE merchants SET domain = 'shpresa.al' WHERE name = 'Shpresa-Al';
UPDATE merchants SET domain = 'globe.al' WHERE name = 'Globe';
UPDATE merchants SET domain = 'ozone.al' WHERE name = 'Ozone';
UPDATE merchants SET domain = 'gotech.al' WHERE name = 'GoTech';

INSERT INTO merchant_sources (merchant_id, source_type, base_url, robots_txt_url, tos_reviewed, is_supported, tos_notes)
SELECT m.id, 'SCRAPER', 'https://' || m.domain || '/', 'https://' || m.domain || '/robots.txt', false, false, notes
FROM merchants m
JOIN (VALUES
  ('shpresa.al', 'Server-rendered WooCommerce-style HTML, real ALL prices, clean /product/<slug>/ URLs. Technically straightforward once robots.txt/ToS confirmed.'),
  ('gotech.al',  'Server-rendered WooCommerce-style HTML (DUKA Group), real ALL prices, clean /product/<slug>/ URLs. Technically straightforward once robots.txt/ToS confirmed.'),
  ('globe.al',   'JS single-page app - static fetch returns no content. Would need Playwright rendering (already planned), not a simple HTTP GET, even after compliance is confirmed.'),
  ('ozone.al',   'CAUTION: a plain, non-adversarial fetch was refused by the site''s own bot detection. Per spec section 3 (no anti-bot bypass), do not attempt to work around this - only proceed if the merchant offers a sanctioned API/feed.')
) AS notes_by_domain(domain, notes) ON notes_by_domain.domain = m.domain
WHERE m.id NOT IN (SELECT merchant_id FROM merchant_sources)
ON CONFLICT DO NOTHING;
