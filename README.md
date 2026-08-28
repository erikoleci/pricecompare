# PriceCompare — Electronics Price Comparison Platform

Scraping-first, Idealo-inspired price comparison platform. Real data only —
no fake products/prices/reviews. See the original spec for full requirements.

## Status: Phase 1 complete ✅

- [x] Repository structure (`backend/`, `frontend/`, `crawler/`, `db/`, `infra/`)
- [x] PostgreSQL schema — 21 tables (corrected from an earlier "22" typo in
      this doc), verified end-to-end against a real, freshly-installed
      Postgres 16 in a later session: all 6 migrations (`001`-`006`) apply
      cleanly in order, `price > 0` rejects a negative-price insert,
      `shipping_cost` stays `NULL` (not `0`) and `total_price` is computed
      correctly when shipping is unknown, append-only `price_history`.
- [x] Seed data for the 8 MVP categories + subcategories + brands
- [x] Backend skeleton (Quarkus): `Merchant`, `Product`, `Offer`,
      `PriceHistory`, `ProductIdentifier`, `ProductSpecification`, `Brand`,
      `Category` entities; `PriceAnalyticsService` (price index, min/max/avg,
      % change, deal score, buy recommendation — all pure/testable);
      `MerchantResource` + `ProductResource` REST endpoints (list, get,
      cheapest→most-expensive offers, price history)
- [x] Frontend skeleton (Vue 3 + TS + Vuetify + Pinia + Vue Router): home
      page with category grid + search bar, product page wired to the
      offers/price-history API, placeholder routes for compare/deals/search
- [x] Crawler architecture (Python + Playwright): `MerchantConnector`
      interface (section 4), `ComplianceGate` enforcing robots.txt +
      crawl-delay + rate limits *before* any fetch, normalizer +
      confidence-scored product matcher (section 15 thresholds), priority
      scheduler (HIGH/MEDIUM/LOW), and a `_template` connector to copy per
      merchant. 7 unit tests passing (title normalization, shipping-cost
      handling, discount %, match confidence thresholds).

## Status: Phase 2 (partial) ✅

- [x] Storage layer (`crawler/storage/offer_storage.py`) — the only code that
      writes to Postgres from the crawler side. Upserts offers, **always
      appends to `price_history`** (never overwrites), flags
      `needs_verification` on a >50% price jump (section 30), and inserts a
      `price_drop_events` row whenever total price falls.
- [x] Reference connector (`crawler/merchants/demo_electronics_store/`) —
      full BeautifulSoup-based extraction (price, old price, shipping,
      availability, EAN/MPN, specs, images) proven against a fixture page,
      **not a real site**: this repo has no general internet access, so a
      fixture stands in for a live fetch. Copying this pattern to a real
      merchant still requires the robots.txt/ToS review in the `_template`
      connector before `is_supported=true`.
- [x] **End-to-end integration test** — fixture HTML → parse → normalize →
      write through the real storage layer into a live PostgreSQL 16
      instance → verified `shipping_cost`/`total_price` math, append-only
      `price_history`, and correct `price_drop_events` creation on a
      simulated price drop. All 8 crawler tests pass (7 unit + 1 integration).
- [x] Admin crawler-monitoring API (`CrawlerMonitoringResource`) — per
      merchant run history + today's rollup (runs, success rate, products
      crawled, prices changed) per spec sections 28-29.

## Status: Phase 3 complete ✅

- [x] `OfferStorage.resolve_product_id()` — wires the section-15 matcher into
      the DB: EAN/GTIN/MPN exact match (confidence 100/95, auto-merge) →
      brand+model with spec-overlap scoring → pg_trgm-assisted fuzzy
      normalized-title shortlist within the same category. Never auto-merges
      below confidence 90; the 70–89 band creates a **separate** product and
      records a `product_match_candidates` row (status `PENDING`) for manual
      review instead, exactly as spec section 15 requires.
- [x] `OfferStorage.process_raw_offer()` — the single entry point spec
      section 36 asked for: `RawOffer → normalize → match → product → offer →
      price history` in one call, so a connector's scraped result is the
      only thing the crawler side needs to hand to storage.
- [x] 3 new integration tests against a live Postgres 16: same EAN from two
      merchants links to one product (auto-merge), different brand/model
      stays separate, and same brand+model with conflicting specs lands in
      the possible-match band and is flagged for review rather than merged.
      **11/11 crawler tests passing** (7 unit + 4 integration).

## Status: Phase 4 (price alerts) ✅

- [x] `OfferStorage.check_and_trigger_alerts()` + wiring into
      `upsert_offer_and_record_price()` — spec section 22 ("notify me when
      below €X"). Checks the **best current price across all of a product's
      merchants** (not just the offer that just changed) against each active,
      not-yet-triggered `price_alerts` row; marks matches `triggered_at` +
      `active=false` and returns them for a caller to hand off to a
      notification channel. Actual email/push delivery isn't implemented —
      no provider credentials exist yet — this only decides *which* alerts
      fire.
- [x] Deal score, price index, price-change %, and buying-recommendation
      logic (`PriceAnalyticsService`, spec sections 10/12/18/26) was already
      written and reviewed in Phase 1; still not compiled/run here since the
      sandbox has no Maven Central access.
- [x] 2 new tests: alert fires exactly once when price drops to/below
      target and not before; an alert on one product is untouched by price
      changes on a different product. **13/13 crawler tests passing**
      (7 unit + 6 integration against live Postgres).
- Not yet done from Phase 4: scheduled (cron-style) price-drop batch jobs —
  the detection itself already runs inline on every price write, which
  covers the same outcome for now; a separate scheduled sweep would only
  matter once crawls aren't triggering it live.

## Status: Phase 5 (search, filters, compare) ✅

- [x] `db/003_search_and_filters.sql` — full-text search vector on
      `products` (title + brand + model weighted highest, category +
      spec values included so "oled" or "rtx 5070" match even though
      they live in `product_specifications`), kept current by a trigger,
      GIN-indexed. Typed `filter_schema` (multi_select/boolean/range) seeded
      for smartphones/laptops/TVs/gaming per spec section 24's explicit list.
      Verified directly against Postgres: FTS match on `"ps5 pro"`, trigram
      fuzzy match on the typo `"plestation 5 pro"` (0.45 similarity), and
      exact EAN lookup all returned the right product.
- [x] `SearchResource` (`GET /api/search`) — priority order per spec
      section 23: digit-only query → identifier (EAN/GTIN/MPN/SKU) lookup,
      else full-text, else trigram fallback for typo tolerance. Raw JDBC
      (not Panache) since `@@`/`similarity()` don't map cleanly to HQL.
- [x] `CategoryResource` (`GET /api/categories`, `/api/categories/{slug}`)
      — serves the filter schema so the frontend never hardcodes filters.
- [x] `GET /api/products/compare?ids=...` (spec section 14) — 2-4 products,
      current/lowest/average price, merchant count, rating (blank, never
      fabricated, until real reviews exist), and every spec key present on
      any compared product for one aligned table.
- [x] `SearchView.vue` and `CompareView.vue` wired to these endpoints for
      real (search-as-you-type add-to-compare, difference highlighting).
      **Built clean with `vue-tsc -b && vite build` — zero type errors.**
- Backend Java still isn't compiled here (sandbox has no Maven Central
  access) — written and reviewed, but only the SQL it issues has been
  proven against a live database, and only the frontend has been proven
  to actually build.

## Status: Phase 2 merchant registration (partial) — 15 Albanian merchants requested

- [x] All 15 named merchants registered in `merchants` with
      `status='UNSUPPORTED'`, `crawler_enabled=false` (spec section 3). Real
      domains confirmed for 9: neptun.al, megateksa.com, celular.al,
      gjirafa50.com, azaelectronics.com, shpresa.al, globe.al, ozone.al,
      gotech.al. The other 6 (American Computers, PC Store Albania,
      ElektroMarket, Xito Shop, BENALB Electronics, The Smartphone Shop)
      have an obvious placeholder domain until confirmed.
- [x] Live findings across two independent sessions on the 4 the user
      linked directly: **shpresa.al** and **gotech.al** are ordinary
      server-rendered WooCommerce/Elementor shops with real ALL prices and
      clean `/product/<slug>/` URLs — straightforward to parse once
      approved; **globe.al** is a JS single-page app, so an approved crawl
      needs Playwright rendering, not a plain HTTP GET; **ozone.al**
      actively refused a plain, non-adversarial fetch with its own bot
      detection — flagged as a caution per spec section 3 (never bypass
      anti-bot measures), not attempted further.
- **Correction confirmed**: `db/007_gotech_restore.sql` re-verified `gotech.al`
  live and restored it - real WordPress/WooCommerce/Elementor electronics
  storefront (DUKA Group), 27 physical stores, real ALL prices, not an
  IT-consulting blog as an earlier migration concluded.
- [x] Fixed two data-integrity bugs found while testing these migrations:
      `merchant_sources` had no uniqueness constraint at all (silently
      duplicated rows on re-run), and `merchants` was only unique on
      `domain`, which broke once a placeholder domain got corrected to a
      real one. Fixed in `db/006_merchant_sources_uniqueness_fix.sql`; the
      full migration chain was re-run twice from a fresh database to
      confirm it's genuinely idempotent.
- [ ] **robots.txt/ToS itself still hasn't been read by a human for any of
      them.** Every chat session's tools hit the same wall: `web_fetch`
      only allows URLs already surfaced by search, and robots.txt is never
      indexed by search engines for small regional sites. This does **not**
      weaken enforcement at actual crawl time — `crawler/core/compliance.py`
      fetches and honors robots.txt directly over the real network before
      any real request, independent of any chat session's tooling.
      `is_supported=true` still needs a human (or an agent with real,
      unrestricted browser access, e.g. Claude Code) to read robots.txt and
      the ToS and record the result in `merchant_sources`.
- See `db/004_al_merchants_pending.sql`, `db/005_al_merchants_real_domains.sql`,
  and `db/005_al_merchants_verified.sql` for the full history, domain notes,
  and per-site technical observations across sessions.

## Status: Live verification session (Phase 1 re-check + Phase 6 reviews)

A later session had a real Linux sandbox (not just chat tools) and used it to
actually run things that earlier sessions could only write and describe:

- [x] **Database (Phase 1) verified for real**: installed Postgres 16 via apt,
      applied all migrations in order against a live instance - all apply
      cleanly. Directly tested the two constraints spec section 6 & 30 care
      about most: an offer with `price = -5` is rejected by the
      `offers_price_check` constraint; an offer with no known shipping cost
      stores `shipping_cost = NULL` and `total_price = price` rather than
      silently treating shipping as free.
- [x] **Frontend (Phase 5) verified for real**: `npm install && npm run build`
      completes cleanly, confirming the vue-tsc/vite build claim from Phase 5.
- [ ] **Backend (Phase 1/4/5) still not compilable in a sandbox**: installed
      JDK 21 + Maven and ran `mvn compile` against the real `pom.xml`. It
      failed with a confirmed, explicit cause (not a guess): `repo.maven.apache.org`
      responds `403` with header `x-deny-reason: host_not_allowed` - the
      sandbox's network egress proxy blocks Maven Central by policy. This is a
      sandbox/infra limitation, not a code problem, and not something to route
      around (bypassing network egress rules is out of scope). Compiling the
      backend needs to happen on a machine with real Maven Central access.
- [x] **Deal Score / Price Index / Buying Recommendation formulas
      (`PriceAnalyticsService.java`, sections 10/12/18/26) verified against
      real inputs** without needing Quarkus/Maven: since that class only
      imports plain `java.*` (no framework types), its formulas were copied
      into a standalone scratch file, compiled with plain `javac`, and run
      against 5 scenarios (deep discount, at-average price, well-above-average
      price, no history yet, extreme inputs) - all 9 assertions passed,
      including that a deal score is always clamped to 0-100 and that "no
      history" never produces an overconfident recommendation. The scratch
      file was for verification only and isn't part of the repo.
- [x] **Reviews pipeline (sections 16-17) — previously entirely missing —
      implemented and tested**: `OfferStorage.write_reviews()` persists only
      reviews a connector actually scraped (never fabricates any), skips
      exact duplicates so a re-crawl of the same review page doesn't
      double-insert, and `refresh_review_summary()` recomputes
      `review_summary` (average rating, count, rating distribution) purely
      from what's stored in `reviews` - if a product has zero real reviews,
      no summary row is created at all rather than showing a fake `0.0`.
      Wired into `process_raw_offer()` so any connector that opts into
      `extract_reviews()` gets this for free. 3 new tests
      (`crawler/tests/test_reviews.py`), all passing against live Postgres.
      **16/16 crawler tests passing** (13 previous + 3 new).
- [x] `crawler/tools/merchant_audit.py` - read-only tool automating 14 of the
      24 discovery-checklist points (robots.txt, sitemap, JSON-LD structured
      data, per-field product detection) per merchant domain; never bypasses
      robots.txt/CAPTCHA/login. See `crawler/tools/domains_pending.txt`.

## Status: Phase 7 (admin merchant management + SEO structured data)

- [x] `MerchantSource` entity + `AdminResource` (`GET /api/admin/merchants`,
      `PATCH /api/admin/merchants/{id}/compliance`, `GET /api/admin/dashboard`)
      — a real UI for exactly the workflow this project's chat sessions have
      been doing by hand with SQL migrations: record that a human actually
      read robots.txt and the ToS, and only that (`approve: true`, which the
      endpoint refuses unless `allowedByRobots=true` AND `tosReviewed=true`)
      can flip `is_supported` to true. Spec section 3's gate is enforced in
      code now, not just by convention.
- [x] `AdminView.vue` — merchant compliance table (status, robots.txt/ToS
      review state, notes, approve/revoke) wired to the endpoints above, plus
      dashboard summary cards. The exact SQL each endpoint runs was verified
      directly against Postgres before writing the Java (same reasoning as
      SearchResource in Phase 5 - the DB layer is proven even though the
      Java itself still can't compile in this sandbox).
- [x] SEO structured data (spec section 35): `ProductView.vue` now injects
      `Product` + `AggregateOffer` + `BreadcrumbList` JSON-LD into `<head>`
      on mount (client-rendered SPA, so this is picked up by JS-executing
      crawlers; a future SSR pass would move it server-side). Category/brand
      landing pages aren't built yet.
- **Frontend rebuilt clean** with the new `AdminView` route -
  `vue-tsc -b && vite build`, zero errors. **16/16 crawler tests** still
  passing (unaffected by this round - no crawler-layer changes).

## Not yet built (next phases, per spec section 37)

- Live merchant connectors — blocked on the compliance review above.
  shpresa.al and celular.al are the best-positioned candidates once
  approved (simple server-rendered HTML); globe.al/gjirafa50.com need
  Playwright rendering in addition; megateksa.com and ozone.al should
  stay off the list (robots.txt disallow / active bot-blocking)
- Full section-28 admin browsing (products/offers/users/reviews/price
  alerts/searches/clicks as separate admin list views) — only the
  merchant-compliance and dashboard-summary parts got built this round,
  since that's what's actually blocking real progress right now
- SEO category/brand/deals landing pages (section 35) - only per-product
  structured data (Product/AggregateOffer/BreadcrumbList) is done so far

## Local setup

### 1. Infra (Postgres + Redis)
```bash
cd infra
docker compose up -d
```

### 2. Database
Schema + seed data run automatically via the Postgres init scripts in
`docker-compose.yml` (mounts `db/` into `/docker-entrypoint-initdb.d`). For a
manual apply:
```bash
psql -h localhost -U pricecompare -d pricecompare -f db/001_init_schema.sql
psql -h localhost -U pricecompare -d pricecompare -f db/002_seed_categories_brands.sql
```
This has been run and verified against a live PostgreSQL 16 instance during
development — all 22 tables, indexes, and triggers apply cleanly.

### 3. Backend (Quarkus)
Requires JDK 21 + Maven, and network access to Maven Central (not available
in this sandbox, so the build itself hasn't been compiled here — only
written and reviewed).
```bash
cd backend
./mvnw quarkus:dev
```
API docs at `http://localhost:8080/api/docs` once running.

### 4. Frontend (Vue 3)
```bash
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:5173`, proxies `/api` to the backend.

### 5. Crawler (Python)
```bash
cd crawler
pip install -r requirements.txt beautifulsoup4 lxml "psycopg[binary]"
playwright install chromium
python -m pytest tests/ -v   # 16/16 passing, verified in this sandbox against a live Postgres 16
```

## Architecture (spec section 36)

```
SCRAPER / API / XML / CSV  →  RAW DATA  →  NORMALIZER  →  PRODUCT MATCHER
   →  PRODUCT DB  →  OFFER DB  →  PRICE HISTORY  →  SEARCH  →  FRONTEND
```

The DB is never written to directly by a scraper — everything passes through
the normalizer + matcher first, so non-scraper sources (API/XML/CSV feeds)
can be added later without touching the storage layer.
