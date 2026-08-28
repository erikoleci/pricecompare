-- Correction: db/005_al_merchants_verified.sql (a different session) removed
-- GoTech from the catalog entirely, concluding gotech.al is "an IT-consulting
-- blog/company... NOT an electronics retailer". A direct re-fetch of
-- https://gotech.al/ in this session found that conclusion to be wrong:
--
--   Title: "GoTech Electronics | Elektroshtëpiake, Smartphone & Laptop"
--   - Real WordPress/WooCommerce/Elementor storefront, part of DUKA Group
--     (DUKA Group HQ, Rruga Dytësore, Autostrada Durrës-Tiranë, Vorë, Tiranë)
--   - Full category tree: appliances, computers, phones, TV/audio, gaming,
--     climate control
--   - Real products with real ALL prices and active discounts, e.g.
--     "TV SAMSUNG 65" QE65Q80DATXXH" at 99,990 ALL (from 209,990 ALL),
--     clean canonical URLs at /product/<slug>/
--   - 27 physical stores listed across Albania (Tiranë, Durrës, Shkodër,
--     Elbasan, Fier, Korçë, etc.)
--   - ToS at /termat-kushtet/, privacy policy at /politika-e-privatesise/
--
-- It's possible the other session fetched a stale cache, a different
-- "gotech" domain, or hit a transient error page - but this session's fetch
-- is unambiguous. Re-adding GoTech with the corrected findings, and using
-- ON CONFLICT (name) DO NOTHING so this migration is safe to re-run even
-- though a prior migration already (incorrectly) deleted the name once.

INSERT INTO merchants (name, domain, country, currency, status, crawler_enabled)
VALUES ('GoTech', 'gotech.al', 'AL', 'ALL', 'UNSUPPORTED', false)
ON CONFLICT (name) DO UPDATE SET domain = EXCLUDED.domain, status = EXCLUDED.status;

INSERT INTO merchant_sources (merchant_id, source_type, base_url, robots_txt_url, tos_reviewed, is_supported, tos_notes)
SELECT id, 'SCRAPER', 'https://gotech.al/', 'https://gotech.al/robots.txt', false, false,
       'CORRECTED: an earlier migration concluded this was an IT-consulting blog and removed it - that was wrong. Confirmed live: real WordPress/WooCommerce/Elementor electronics storefront (DUKA Group), real ALL prices, clean /product/<slug>/ URLs, 27 physical stores across Albania. ToS at /termat-kushtet/. robots.txt not yet read by a human/tool.'
FROM merchants WHERE domain = 'gotech.al'
ON CONFLICT (merchant_id, source_type) DO UPDATE SET tos_notes = EXCLUDED.tos_notes;
