# PriceCompare — Electronics Price Comparison Platform

Scraping-first, Idealo-inspired price comparison platform. Real data only —
no fake products/prices/reviews. See the original spec for full requirements.

## Status: Phase 1 complete ✅

- [x] Repository structure (`backend/`, `frontend/`, `crawler/`, `db/`, `infra/`)
- [x] PostgreSQL schema — 22 tables, tested end-to-end (schema applies cleanly,
      constraints verified: `price > 0`, `shipping_cost` stays `NULL` instead of
      defaulting to free, append-only `price_history`)
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

## Not yet built (next phases, per spec section 37)

- Rest of Phase 2: onboard 3–5 *real* merchants — each needs a manual
  robots.txt/ToS review recorded in `merchant_sources` before
  `is_supported` is set to `true`, then Playwright-based live fetching
  wired to the connector pattern already proven above
- Phase 4: scheduled price-drop detection jobs (the detection logic itself
  is done and tested), deal score persisted per product, price alert
  notifications (section 22)
- Phase 5: search (Postgres FTS → OpenSearch later), dynamic filters, `/compare`
- Phase 6: reviews pipeline, price alerts + notifications
- Phase 7: admin dashboard, crawler monitoring UI, SEO pages

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
python -m pytest tests/ -v   # 8/8 passing, verified in this sandbox against a live Postgres 16
```

## Architecture (spec section 36)

```
SCRAPER / API / XML / CSV  →  RAW DATA  →  NORMALIZER  →  PRODUCT MATCHER
   →  PRODUCT DB  →  OFFER DB  →  PRICE HISTORY  →  SEARCH  →  FRONTEND
```

The DB is never written to directly by a scraper — everything passes through
the normalizer + matcher first, so non-scraper sources (API/XML/CSV feeds)
can be added later without touching the storage layer.
