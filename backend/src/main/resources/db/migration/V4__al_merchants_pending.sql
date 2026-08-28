-- Phase 2 (spec sections 3 & 38): register the merchants the user named so
-- the catalog/admin structure exists, WITHOUT enabling any crawling yet.
--
-- Per spec section 3: "Nese nje website nuk mund te crawl-ohet ne menyre te
-- lejueshme, sistemi duhet ta shenoje si unsupported" - and per section 38,
-- is_supported must be approved manually per merchant after a robots.txt/ToS
-- review. None of that review has happened yet (see chat notes on why: no
-- tool available in this session could reliably fetch robots.txt for these
-- specific domains or reach them from the crawler sandbox at all), so every
-- row here is inserted as PENDING_REVIEW / crawler_enabled = false and every
-- merchant_sources row has allowed_by_robots = NULL, tos_reviewed = false,
-- is_supported = false. Flipping any of this to enabled requires a human
-- (or a tool with real internet access) to actually open robots.txt and the
-- ToS and record the outcome - see the notes column for what's still open.

-- domain is NOT NULL on merchants, so ambiguous names get an obvious
-- placeholder ('pending-review.invalid') rather than a guessed real domain -
-- these must be corrected to the real domain before is_supported can ever
-- be considered, and the placeholder makes that obvious to anyone browsing
-- the merchants table.
--
-- `name` isn't unique by default (only `domain` is) - add that constraint
-- here, before the insert below relies on it for ON CONFLICT (name), since
-- later migrations correct placeholder domains to real ones and a merchant
-- re-seeded here must still be recognized as "the same merchant" by name,
-- not by a domain that's since changed.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_merchants_name') THEN
        ALTER TABLE merchants ADD CONSTRAINT uq_merchants_name UNIQUE (name);
    END IF;
END $$;

INSERT INTO merchants (name, domain, country, currency, status, crawler_enabled) VALUES
('Neptun',               'neptun.al',                      'AL', 'ALL', 'UNSUPPORTED', false),
('Globe',                'globe.pending-review.invalid',    'AL', 'ALL', 'UNSUPPORTED', false),
('Megatek',              'megateksa.com',                   'AL', 'ALL', 'UNSUPPORTED', false),
('Shpresa-Al',           'shpresa-al.pending-review.invalid','AL', 'ALL', 'UNSUPPORTED', false),
('Ozone',                'ozone.pending-review.invalid',    'AL', 'ALL', 'UNSUPPORTED', false),
('American Computers',   'american-computers.pending-review.invalid', 'AL', 'ALL', 'UNSUPPORTED', false),
('PC Store Albania',     'pc-store-albania.pending-review.invalid', 'AL', 'ALL', 'UNSUPPORTED', false),
('ElektroMarket',        'elektromarket.pending-review.invalid', 'AL', 'ALL', 'UNSUPPORTED', false),
('Celular.al',           'celular.al',                      'AL', 'ALL', 'UNSUPPORTED', false),
('Gjirafa50',            'gjirafa50.com',                   'AL', 'ALL', 'UNSUPPORTED', false),
('Xito Shop',            'xito-shop.pending-review.invalid', 'AL', 'ALL', 'UNSUPPORTED', false),
('BENALB Electronics',   'benalb.pending-review.invalid',   'AL', 'ALL', 'UNSUPPORTED', false),
('The Smartphone Shop',  'the-smartphone-shop.pending-review.invalid', 'AL', 'ALL', 'UNSUPPORTED', false),
('Aza Electronics',      'azaelectronics.com',              'AL', 'ALL', 'UNSUPPORTED', false),
('GoTech',               'gotech.pending-review.invalid',   'AL', 'ALL', 'UNSUPPORTED', false)
ON CONFLICT (name) DO NOTHING;

-- Domain notes (not columns on merchants - just for whoever reviews this
-- migration): "Globe", "Ozone", "GoTech", "American Computers", "PC Store
-- Albania", "ElektroMarket", "Xito Shop", "BENALB Electronics", "The
-- Smartphone Shop" are too generic/ambiguous to confidently resolve to one
-- real domain from search alone. "Shpresa-Al" specifically is NOT
-- shpresa.al (that domain is an unrelated community/education site, not an
-- electronics shop) - the real one needs to be identified separately.

-- merchant_sources: one PENDING row per merchant that has a confirmed domain
-- so far. Merchants with a NULL domain above (ambiguous names - "Globe",
-- "Ozone", "GoTech" etc. are too generic to identify with confidence, and
-- "Shpresa-Al" collides with an unrelated shpresa.al site) get no
-- merchant_sources row until their real domain is confirmed.
INSERT INTO merchant_sources (merchant_id, source_type, base_url, robots_txt_url, tos_reviewed, is_supported)
SELECT id, 'SCRAPER', 'https://www.' || domain || '/', 'https://www.' || domain || '/robots.txt', false, false
FROM merchants
WHERE domain IN ('neptun.al', 'megateksa.com', 'celular.al', 'gjirafa50.com', 'azaelectronics.com')
ON CONFLICT DO NOTHING;

COMMENT ON TABLE merchant_sources IS
  'is_supported stays false for every row until a human (or a tool with real '
  'internet access) confirms robots_txt/ToS - see db/004_al_merchants_pending.sql';
