-- Phase 2: celular.al connector written (crawler/merchants/celular_al/) -
-- JSON-LD/schema.org based extraction, 7/7 tests passing against a synthetic
-- fixture (see crawler/tests/test_celular_al_connector.py docstring - the
-- fixture is a standard schema.org example, NOT captured from the real
-- site, since no session had real fetch access to celular.al when this
-- connector was written).
--
-- This does NOT flip allowed_by_robots/tos_reviewed/is_supported - those
-- still require someone (or a session with real browser/fetch access)
-- actually reading celular.al's robots.txt and ToS, the same way V10 did
-- for neptun.al. It just records connector-code status in tos_notes so the
-- next session (or whoever approves it in /admin) knows exactly what is and
-- isn't done yet:
--   1. robots.txt/ToS: NOT read yet.
--   2. Extraction logic (parse_offer + all extract_*): written and tested,
--      but only against a synthetic fixture.
--   3. discover_products() (category/listing URL enumeration): still
--      NotImplementedError - needs the real listing/pagination pattern
--      confirmed first, independent of (1).

UPDATE merchant_sources SET
  tos_notes = COALESCE(tos_notes, '') || E'\n\nConnector status (crawler/merchants/celular_al/): JSON-LD extraction ' ||
              'written and tested (7/7 tests, synthetic schema.org fixture only - not real site HTML). ' ||
              'discover_products() still NotImplementedError - listing/category URL pattern ' ||
              'not yet confirmed against the real site. robots.txt/ToS still not read. ' ||
              'is_supported must stay false until both are done.'
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'celular.al');
