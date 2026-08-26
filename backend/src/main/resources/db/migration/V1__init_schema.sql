-- ==============================================================
-- PriceCompare Platform - Phase 1 Core Schema
-- PostgreSQL 15+
-- ==============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- fuzzy / typo-tolerant search later

-- ------------------------------------------------------------
-- USERS
-- ------------------------------------------------------------
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(120),
    role            VARCHAR(20) NOT NULL DEFAULT 'USER', -- USER, ADMIN
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- MERCHANTS
-- ------------------------------------------------------------
CREATE TABLE merchants (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                    VARCHAR(150) NOT NULL,
    domain                  VARCHAR(255) NOT NULL UNIQUE,
    logo_url                VARCHAR(500),
    country                 VARCHAR(2),
    currency                VARCHAR(3) NOT NULL DEFAULT 'EUR',
    rating                  NUMERIC(3,2),
    review_count            INTEGER DEFAULT 0,
    status                  VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, PAUSED, DISABLED, UNSUPPORTED
    crawler_enabled         BOOLEAN NOT NULL DEFAULT false,
    last_successful_crawl   TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Legal/technical access notes per merchant source (robots.txt, ToS, rate limits)
CREATE TABLE merchant_sources (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id         UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    source_type         VARCHAR(20) NOT NULL DEFAULT 'SCRAPER', -- SCRAPER, API, XML_FEED, CSV_FEED
    base_url            VARCHAR(500) NOT NULL,
    robots_txt_url      VARCHAR(500),
    robots_txt_checked_at TIMESTAMPTZ,
    allowed_by_robots   BOOLEAN,
    tos_reviewed        BOOLEAN NOT NULL DEFAULT false,
    tos_notes           TEXT,
    crawl_delay_seconds NUMERIC(6,2) DEFAULT 2,
    max_requests_per_min INTEGER DEFAULT 20,
    is_supported        BOOLEAN NOT NULL DEFAULT false, -- false = "unsupported" per spec section 3
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- CATEGORIES / BRANDS
-- ------------------------------------------------------------
CREATE TABLE categories (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id       UUID REFERENCES categories(id),
    slug            VARCHAR(150) NOT NULL UNIQUE,
    name            VARCHAR(150) NOT NULL,
    filter_schema   JSONB, -- dynamic filters per category (section 24)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE brands (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug            VARCHAR(150) NOT NULL UNIQUE,
    name            VARCHAR(150) NOT NULL,
    logo_url        VARCHAR(500),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- PRODUCTS
-- ------------------------------------------------------------
CREATE TABLE products (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id            UUID REFERENCES brands(id),
    category_id         UUID REFERENCES categories(id),
    subcategory_id      UUID REFERENCES categories(id),
    model               VARCHAR(255),
    title               VARCHAR(500) NOT NULL,
    normalized_title     VARCHAR(500) NOT NULL,
    description          TEXT,
    match_confidence_avg NUMERIC(5,2), -- rollup from product_match_candidates
    status               VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, MERGED, NEEDS_REVIEW, REMOVED
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_products_normalized_title_trgm ON products USING gin (normalized_title gin_trgm_ops);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_brand ON products(brand_id);

-- EAN/GTIN/SKU/MPN identifiers (a product can have several, and identifiers drive matching priority)
CREATE TABLE product_identifiers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    id_type         VARCHAR(20) NOT NULL, -- EAN, GTIN, SKU, MPN
    id_value        VARCHAR(120) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (id_type, id_value)
);
CREATE INDEX idx_product_identifiers_product ON product_identifiers(product_id);

CREATE TABLE product_specifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    spec_key        VARCHAR(100) NOT NULL, -- e.g. "storage", "ram", "display_size"
    spec_value      VARCHAR(255) NOT NULL,
    spec_unit       VARCHAR(30),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_product_specifications_product ON product_specifications(product_id);
CREATE INDEX idx_product_specifications_key_value ON product_specifications(spec_key, spec_value);

CREATE TABLE product_images (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    url             VARCHAR(700) NOT NULL,
    position        INTEGER NOT NULL DEFAULT 0,
    source_merchant_id UUID REFERENCES merchants(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- OFFERS (a product can have many offers, one per merchant listing)
-- ------------------------------------------------------------
CREATE TABLE offers (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id              UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    merchant_id             UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    merchant_product_id     VARCHAR(255), -- merchant's own SKU/id for this listing
    price                   NUMERIC(12,2) NOT NULL CHECK (price > 0),
    currency                VARCHAR(3) NOT NULL DEFAULT 'EUR',
    old_price               NUMERIC(12,2),
    discount_percent        NUMERIC(5,2),
    shipping_cost           NUMERIC(12,2), -- NULL = unknown, never assume free (section 6)
    total_price             NUMERIC(12,2) NOT NULL, -- price + shipping_cost (0 if shipping known-free)
    availability            VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN', -- IN_STOCK, OUT_OF_STOCK, PREORDER, UNKNOWN
    condition               VARCHAR(20) NOT NULL DEFAULT 'NEW', -- NEW, REFURBISHED, USED
    warranty                VARCHAR(255),
    url                     VARCHAR(700) NOT NULL,
    image_url               VARCHAR(700),
    -- provenance (section 39)
    source_type             VARCHAR(20) NOT NULL DEFAULT 'SCRAPER',
    scraped_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_price_change_at    TIMESTAMPTZ,
    needs_verification      BOOLEAN NOT NULL DEFAULT false, -- flagged when price jumps >50% (section 30)
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (merchant_id, merchant_product_id)
);
CREATE INDEX idx_offers_product ON offers(product_id);
CREATE INDEX idx_offers_merchant ON offers(merchant_id);
CREATE INDEX idx_offers_total_price ON offers(product_id, total_price);

-- ------------------------------------------------------------
-- PRICE HISTORY (append-only; never overwrite, section 8)
-- ------------------------------------------------------------
CREATE TABLE price_history (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    offer_id            UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    merchant_id         UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    price               NUMERIC(12,2) NOT NULL,
    shipping_cost       NUMERIC(12,2),
    total_price         NUMERIC(12,2) NOT NULL,
    currency            VARCHAR(3) NOT NULL DEFAULT 'EUR',
    availability        VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN',
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_price_history_product_time ON price_history(product_id, recorded_at);
CREATE INDEX idx_price_history_offer_time ON price_history(offer_id, recorded_at);

CREATE TABLE price_drop_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id          UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    offer_id            UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    merchant_id         UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    old_price           NUMERIC(12,2) NOT NULL,
    new_price           NUMERIC(12,2) NOT NULL,
    drop_percent        NUMERIC(5,2) NOT NULL,
    drop_amount         NUMERIC(12,2) NOT NULL,
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_price_drop_events_product ON price_drop_events(product_id, detected_at);

-- ------------------------------------------------------------
-- REVIEWS
-- ------------------------------------------------------------
CREATE TABLE reviews (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    merchant_id     UUID REFERENCES merchants(id),
    source          VARCHAR(100) NOT NULL, -- where the review was permissibly obtained from
    author_name     VARCHAR(150),
    rating          NUMERIC(2,1) NOT NULL CHECK (rating BETWEEN 0 AND 5),
    title           VARCHAR(255),
    text            TEXT,
    review_date     DATE,
    verified        BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_reviews_product ON reviews(product_id);

CREATE TABLE review_summary (
    product_id          UUID PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    average_rating      NUMERIC(3,2),
    review_count        INTEGER NOT NULL DEFAULT 0,
    rating_distribution JSONB, -- {"5": 72, "4": 18, "3": 6, "2": 2, "1": 2} (percentages)
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- PRICE ALERTS
-- ------------------------------------------------------------
CREATE TABLE price_alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    target_price    NUMERIC(12,2) NOT NULL,
    active          BOOLEAN NOT NULL DEFAULT true,
    triggered_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_price_alerts_product ON price_alerts(product_id) WHERE active = true;

-- ------------------------------------------------------------
-- SEARCH / CLICK ANALYTICS
-- ------------------------------------------------------------
CREATE TABLE search_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id),
    query           VARCHAR(500) NOT NULL,
    result_count    INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE click_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id),
    product_id      UUID REFERENCES products(id),
    offer_id        UUID REFERENCES offers(id),
    event_type      VARCHAR(30) NOT NULL DEFAULT 'OFFER_CLICK', -- OFFER_CLICK, PRODUCT_VIEW, SEARCH_RESULT_CLICK
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_click_events_product ON click_events(product_id, created_at);

-- ------------------------------------------------------------
-- CRAWLER MONITORING
-- ------------------------------------------------------------
CREATE TABLE crawler_jobs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    merchant_id     UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    job_type        VARCHAR(30) NOT NULL DEFAULT 'FULL_CRAWL', -- DISCOVER, FULL_CRAWL, PRICE_REFRESH
    priority        VARCHAR(10) NOT NULL DEFAULT 'MEDIUM', -- HIGH, MEDIUM, LOW (section 31)
    schedule_cron   VARCHAR(100),
    enabled         BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE crawler_runs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crawler_job_id      UUID NOT NULL REFERENCES crawler_jobs(id) ON DELETE CASCADE,
    merchant_id         UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    status              VARCHAR(20) NOT NULL DEFAULT 'RUNNING', -- RUNNING, SUCCESS, FAILED, PARTIAL
    products_found      INTEGER DEFAULT 0,
    products_updated    INTEGER DEFAULT 0,
    prices_changed      INTEGER DEFAULT 0,
    new_products        INTEGER DEFAULT 0,
    out_of_stock        INTEGER DEFAULT 0,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ,
    duration_ms         INTEGER
);
CREATE INDEX idx_crawler_runs_merchant_time ON crawler_runs(merchant_id, started_at);

CREATE TABLE crawler_errors (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crawler_run_id  UUID NOT NULL REFERENCES crawler_runs(id) ON DELETE CASCADE,
    merchant_id     UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
    url             VARCHAR(700),
    error_type      VARCHAR(100),
    error_message   TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_crawler_errors_run ON crawler_errors(crawler_run_id);

-- ------------------------------------------------------------
-- PRODUCT MATCHING (section 15)
-- ------------------------------------------------------------
CREATE TABLE product_match_candidates (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    offer_id            UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    candidate_product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    match_method        VARCHAR(30) NOT NULL, -- EAN, GTIN, MPN, BRAND_MODEL, SPEC, NORMALIZED_TITLE, FUZZY
    confidence          NUMERIC(5,2) NOT NULL, -- 0-100, see thresholds in spec section 15
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING, AUTO_MERGED, MANUAL_REVIEW, REJECTED
    reviewed_by         UUID REFERENCES users(id),
    reviewed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_match_candidates_offer ON product_match_candidates(offer_id);
CREATE INDEX idx_match_candidates_status ON product_match_candidates(status);

-- ------------------------------------------------------------
-- updated_at trigger helper
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_products_updated_at BEFORE UPDATE ON products
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_offers_updated_at BEFORE UPDATE ON offers
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_merchants_updated_at BEFORE UPDATE ON merchants
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_merchant_sources_updated_at BEFORE UPDATE ON merchant_sources
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
