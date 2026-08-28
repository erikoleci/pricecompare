-- Phase 5 (spec sections 23-24): search + dynamic filters.
--
-- Search needs to handle:
--   "iphone 17 pro", "ps5 pro", "samsung 65 oled", "gaming laptop rtx 5070"
-- with typo tolerance, brand/model/category detection, and EAN/SKU lookup
-- (section 23). We start on Postgres FTS + pg_trgm (already enabled in
-- 001_init_schema.sql) rather than standing up OpenSearch for the MVP, per
-- the note in spec section 33.

-- ------------------------------------------------------------
-- Full-text search vector, generated from the fields a shopper actually
-- searches by: title, brand name, model, category name, and any spec
-- values (so "rtx 5070" or "oled" match even though they live in
-- product_specifications, not the title).
-- ------------------------------------------------------------
ALTER TABLE products ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE OR REPLACE FUNCTION products_search_vector_refresh(p_product_id UUID) RETURNS void AS $$
DECLARE
    v_brand TEXT;
    v_category TEXT;
    v_specs TEXT;
BEGIN
    SELECT b.name INTO v_brand FROM products p LEFT JOIN brands b ON b.id = p.brand_id WHERE p.id = p_product_id;
    SELECT c.name INTO v_category FROM products p LEFT JOIN categories c ON c.id = p.category_id WHERE p.id = p_product_id;
    SELECT string_agg(spec_value, ' ') INTO v_specs FROM product_specifications WHERE product_id = p_product_id;

    UPDATE products p SET search_vector =
        setweight(to_tsvector('simple', coalesce(p.title, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(v_brand, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(p.model, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(v_category, '')), 'C') ||
        setweight(to_tsvector('simple', coalesce(v_specs, '')), 'B')
    WHERE p.id = p_product_id;
END;
$$ LANGUAGE plpgsql;

-- Keep search_vector current whenever a product's own core fields change.
-- Spec/brand/category changes are refreshed by the storage layer explicitly
-- (see crawler/storage/offer_storage.py) since those live in other tables
-- and a trigger on products alone can't see them change.
CREATE OR REPLACE FUNCTION products_search_vector_trigger() RETURNS trigger AS $$
BEGIN
    PERFORM products_search_vector_refresh(NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_products_search_vector ON products;
CREATE TRIGGER trg_products_search_vector
    AFTER INSERT OR UPDATE OF title, model, brand_id, category_id ON products
    FOR EACH ROW EXECUTE FUNCTION products_search_vector_trigger();

CREATE INDEX IF NOT EXISTS idx_products_search_vector ON products USING gin (search_vector);

-- Backfill existing rows (no-op on a fresh DB, matters when re-running on
-- data seeded before this migration).
DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN SELECT id FROM products LOOP
        PERFORM products_search_vector_refresh(r.id);
    END LOOP;
END $$;

-- ------------------------------------------------------------
-- Dynamic filters per category (spec section 24). filter_schema was already
-- a JSONB column on categories (001_init_schema.sql); this seeds the MVP
-- categories with the exact filter sets the spec lists.
-- ------------------------------------------------------------
UPDATE categories SET filter_schema = '{
  "filters": [
    {"key": "brand", "label": "Brand", "type": "multi_select", "source": "facet"},
    {"key": "model", "label": "Model", "type": "multi_select", "source": "facet"},
    {"key": "storage", "label": "Storage", "type": "multi_select", "source": "spec:storage"},
    {"key": "ram", "label": "RAM", "type": "multi_select", "source": "spec:ram"},
    {"key": "display", "label": "Display", "type": "multi_select", "source": "spec:display"},
    {"key": "camera", "label": "Camera", "type": "multi_select", "source": "spec:camera"},
    {"key": "5g", "label": "5G", "type": "boolean", "source": "spec:5g"},
    {"key": "price", "label": "Price", "type": "range", "source": "price"}
  ]
}'::jsonb WHERE slug = 'smartphones';

UPDATE categories SET filter_schema = '{
  "filters": [
    {"key": "brand", "label": "Brand", "type": "multi_select", "source": "facet"},
    {"key": "cpu", "label": "CPU", "type": "multi_select", "source": "spec:cpu"},
    {"key": "gpu", "label": "GPU", "type": "multi_select", "source": "spec:gpu"},
    {"key": "ram", "label": "RAM", "type": "multi_select", "source": "spec:ram"},
    {"key": "ssd", "label": "SSD", "type": "multi_select", "source": "spec:ssd"},
    {"key": "display_size", "label": "Display size", "type": "multi_select", "source": "spec:display_size"},
    {"key": "resolution", "label": "Resolution", "type": "multi_select", "source": "spec:resolution"},
    {"key": "refresh_rate", "label": "Refresh rate", "type": "multi_select", "source": "spec:refresh_rate"},
    {"key": "price", "label": "Price", "type": "range", "source": "price"}
  ]
}'::jsonb WHERE slug = 'laptops';

UPDATE categories SET filter_schema = '{
  "filters": [
    {"key": "brand", "label": "Brand", "type": "multi_select", "source": "facet"},
    {"key": "size", "label": "Size", "type": "multi_select", "source": "spec:size"},
    {"key": "panel", "label": "Panel", "type": "multi_select", "source": "spec:panel", "options": ["OLED", "QLED", "LED"]},
    {"key": "resolution", "label": "Resolution", "type": "multi_select", "source": "spec:resolution"},
    {"key": "refresh_rate", "label": "Refresh rate", "type": "multi_select", "source": "spec:refresh_rate"},
    {"key": "hdr", "label": "HDR", "type": "boolean", "source": "spec:hdr"},
    {"key": "smart_tv", "label": "Smart TV", "type": "boolean", "source": "spec:smart_tv"},
    {"key": "price", "label": "Price", "type": "range", "source": "price"}
  ]
}'::jsonb WHERE slug = 'tvs';

UPDATE categories SET filter_schema = '{
  "filters": [
    {"key": "platform", "label": "Platform", "type": "multi_select", "source": "facet"},
    {"key": "model", "label": "Model", "type": "multi_select", "source": "facet"},
    {"key": "storage", "label": "Storage", "type": "multi_select", "source": "spec:storage"},
    {"key": "edition", "label": "Edition", "type": "multi_select", "source": "spec:edition"},
    {"key": "bundle", "label": "Bundle", "type": "multi_select", "source": "spec:bundle"},
    {"key": "price", "label": "Price", "type": "range", "source": "price"}
  ]
}'::jsonb WHERE slug = 'gaming';
