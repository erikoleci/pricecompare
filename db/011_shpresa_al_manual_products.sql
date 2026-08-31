-- Real products manually pulled from shpresa.al on the date of this
-- migration, via a direct fetch of https://shpresa.al/ (homepage "Zbulo
-- më të mirat" section) - NOT a live/automated crawler run (no scheduler
-- exists yet), and NOT synthetic/fabricated data (spec section 40
-- explicitly forbids fake products/prices). Every price, image URL, and
-- product URL below is copied exactly from what the site actually
-- returned. shpresa.al has a real, verified robots.txt review on file
-- (V12) with allowed_by_robots=true.
--
-- This is a manual one-time snapshot to prove the catalog pipeline works
-- end-to-end with real data, not the "system fetching it on its own" the
-- spec envisions for the real crawler (schedulers/priority_scheduler.py +
-- a merchant connector) - that still needs to be built and run somewhere
-- with real, continuous execution (see README's repeated notes on this).
--
-- 6 products across the 3 categories/brands already seeded in
-- 002_seed_categories_brands.sql (smartphones/Samsung, tvs/Samsung,
-- laptops/Apple).

DO $$
DECLARE
    v_merchant_id UUID;
    v_samsung_id UUID;
    v_apple_id UUID;
    v_smartphones_id UUID;
    v_tvs_id UUID;
    v_laptops_id UUID;
    v_product_id UUID;
    v_offer_id UUID;
BEGIN
    SELECT id INTO v_merchant_id FROM merchants WHERE domain = 'shpresa.al';
    SELECT id INTO v_samsung_id FROM brands WHERE slug = 'samsung';
    SELECT id INTO v_apple_id FROM brands WHERE slug = 'apple';
    SELECT id INTO v_smartphones_id FROM categories WHERE slug = 'smartphones';
    SELECT id INTO v_tvs_id FROM categories WHERE slug = 'tvs';
    SELECT id INTO v_laptops_id FROM categories WHERE slug = 'laptops';

    -- 1. Samsung Galaxy Z Fold8 Ultra 512GB - 149,990 L
    INSERT INTO products (brand_id, category_id, model, title, normalized_title, description)
    VALUES (v_samsung_id, v_smartphones_id, 'Galaxy Z Fold8 Ultra 512GB',
            'Samsung Galaxy Z Fold8 Ultra 512GB', 'samsung galaxy z fold8 ultra 512gb',
            '8.0" Foldable Amoled 2X (2256 x 2504px) 120Hz, Camera 200MP / Selfie 10MP, RAM 12GB/ROM 512GB, Battery 5000 mAh 45W, 4G/5G/WiFi')
    RETURNING id INTO v_product_id;
    INSERT INTO product_specifications (product_id, spec_key, spec_value) VALUES
        (v_product_id, 'display', '8.0" Foldable AMOLED 2X 120Hz'),
        (v_product_id, 'camera', '200MP / Selfie 10MP'),
        (v_product_id, 'ram', '12GB'), (v_product_id, 'storage', '512GB'),
        (v_product_id, 'battery', '5000 mAh, 45W');
    INSERT INTO product_images (product_id, url, position, source_merchant_id) VALUES
        (v_product_id, 'https://assets.shpresa.al/shop/2026/08/bc0249aa-cel2241-b-5.jpg', 0, v_merchant_id);
    INSERT INTO offers (product_id, merchant_id, merchant_product_id, price, currency, shipping_cost,
                         total_price, availability, url, image_url, source_type)
    VALUES (v_product_id, v_merchant_id, 'samsung-galaxy-z-fold8-ultra-512gb', 149990.00, 'ALL', NULL,
            149990.00, 'IN_STOCK', 'https://shpresa.al/product/samsung-galaxy-z-fold8-ultra-512gb/',
            'https://assets.shpresa.al/shop/2026/08/bc0249aa-cel2241-b-5.jpg', 'MANUAL')
    RETURNING id INTO v_offer_id;
    INSERT INTO price_history (product_id, offer_id, merchant_id, price, shipping_cost, total_price, currency, availability)
    VALUES (v_product_id, v_offer_id, v_merchant_id, 149990.00, NULL, 149990.00, 'ALL', 'IN_STOCK');

    -- 2. Samsung 55" Crystal UHD U8072F 4K Smart TV (2025) - 39,990 L
    INSERT INTO products (brand_id, category_id, model, title, normalized_title, description)
    VALUES (v_samsung_id, v_tvs_id, '55" Crystal UHD U8072F',
            'Samsung 55" Crystal UHD U8072F 4K Smart TV (2025)', 'samsung 55 crystal uhd u8072f 4k smart tv 2025',
            '55" LED 4K, Samsung Knox Security, Crystal 4K CPU, One UI Tizen')
    RETURNING id INTO v_product_id;
    INSERT INTO product_specifications (product_id, spec_key, spec_value) VALUES
        (v_product_id, 'size', '55"'), (v_product_id, 'panel', 'LED'), (v_product_id, 'resolution', '4K');
    INSERT INTO product_images (product_id, url, position, source_merchant_id) VALUES
        (v_product_id, 'https://assets.shpresa.al/shop/2026/05/2ebbe582-ue55u8072fuxxh-2.jpg', 0, v_merchant_id);
    INSERT INTO offers (product_id, merchant_id, merchant_product_id, price, currency, shipping_cost,
                         total_price, availability, url, image_url, source_type)
    VALUES (v_product_id, v_merchant_id, 'samsung-55-crystal-uhd-u8072f-4k-smart-tv-2025', 39990.00, 'ALL', NULL,
            39990.00, 'IN_STOCK', 'https://shpresa.al/product/samsung-55-crystal-uhd-u8072f-4k-smart-tv-2025/',
            'https://assets.shpresa.al/shop/2026/05/2ebbe582-ue55u8072fuxxh-2.jpg', 'MANUAL')
    RETURNING id INTO v_offer_id;
    INSERT INTO price_history (product_id, offer_id, merchant_id, price, shipping_cost, total_price, currency, availability)
    VALUES (v_product_id, v_offer_id, v_merchant_id, 39990.00, NULL, 39990.00, 'ALL', 'IN_STOCK');

    -- 3. Samsung 65" QLED Q7F 4K Smart TV (2025) - 69,990 L
    INSERT INTO products (brand_id, category_id, model, title, normalized_title, description)
    VALUES (v_samsung_id, v_tvs_id, '65" QLED Q7F',
            'Samsung 65" QLED Q7F 4K Samsung Vision AI Smart TV (2025)', 'samsung 65 qled q7f 4k samsung vision ai smart tv 2025',
            '65" QLED 4K, Samsung Vision AI, AI Q4 CPU, One UI Tizen, Quantum DOT')
    RETURNING id INTO v_product_id;
    INSERT INTO product_specifications (product_id, spec_key, spec_value) VALUES
        (v_product_id, 'size', '65"'), (v_product_id, 'panel', 'QLED'), (v_product_id, 'resolution', '4K');
    INSERT INTO product_images (product_id, url, position, source_merchant_id) VALUES
        (v_product_id, 'https://assets.shpresa.al/shop/2026/05/6284870c-qe65q7f2auxxh-3.jpg', 0, v_merchant_id);
    INSERT INTO offers (product_id, merchant_id, merchant_product_id, price, currency, shipping_cost,
                         total_price, availability, url, image_url, source_type)
    VALUES (v_product_id, v_merchant_id, 'samsung-65-qled-q7f-4k-samsung-vision-ai-smart-tv-2025', 69990.00, 'ALL', NULL,
            69990.00, 'IN_STOCK', 'https://shpresa.al/product/samsung-65-qled-q7f-4k-samsung-vision-ai-smart-tv-2025/',
            'https://assets.shpresa.al/shop/2026/05/6284870c-qe65q7f2auxxh-3.jpg', 'MANUAL')
    RETURNING id INTO v_offer_id;
    INSERT INTO price_history (product_id, offer_id, merchant_id, price, shipping_cost, total_price, currency, availability)
    VALUES (v_product_id, v_offer_id, v_merchant_id, 69990.00, NULL, 69990.00, 'ALL', 'IN_STOCK');

    -- 4. Apple MacBook Air 13.6" 16GB 512GB SSD M5 (2026) - 129,990 L (low end of shown range)
    INSERT INTO products (brand_id, category_id, model, title, normalized_title, description)
    VALUES (v_apple_id, v_laptops_id, 'MacBook Air 13.6" M5 16GB/512GB',
            'Apple MacBook Air 13.6", 16GB, 512GB SSD, M5 (2026)', 'apple macbook air 13 6 16gb 512gb ssd m5 2026',
            'Apple M5, 16GB RAM + 512GB SSD, 13.6" Liquid Retina Display, Apple 8-Core GPU')
    RETURNING id INTO v_product_id;
    INSERT INTO product_specifications (product_id, spec_key, spec_value) VALUES
        (v_product_id, 'cpu', 'Apple M5'), (v_product_id, 'ram', '16GB'), (v_product_id, 'ssd', '512GB'),
        (v_product_id, 'display_size', '13.6"');
    INSERT INTO product_images (product_id, url, position, source_merchant_id) VALUES
        (v_product_id, 'https://assets.shpresa.al/shop/2026/04/ff3f4220-dun2877-g-3.jpg', 0, v_merchant_id);
    INSERT INTO offers (product_id, merchant_id, merchant_product_id, price, currency, old_price, discount_percent,
                         shipping_cost, total_price, availability, url, image_url, source_type)
    VALUES (v_product_id, v_merchant_id, 'apple-macbook-air-13-6-16gb-512gb-ssd-m5-2026', 129990.00, 'ALL',
            139990.00, 7.14, NULL, 129990.00, 'IN_STOCK',
            'https://shpresa.al/product/apple-macbook-air-13-6-16gb-512gb-ssd-m5-2026/',
            'https://assets.shpresa.al/shop/2026/04/ff3f4220-dun2877-g-3.jpg', 'MANUAL')
    RETURNING id INTO v_offer_id;
    INSERT INTO price_history (product_id, offer_id, merchant_id, price, shipping_cost, total_price, currency, availability)
    VALUES (v_product_id, v_offer_id, v_merchant_id, 129990.00, NULL, 129990.00, 'ALL', 'IN_STOCK');

    -- 5. Apple MacBook Pro 14.2" 24GB 1TB SSD M5 Pro 2026 - 259,990 L
    INSERT INTO products (brand_id, category_id, model, title, normalized_title, description)
    VALUES (v_apple_id, v_laptops_id, 'MacBook Pro 14.2" M5 Pro 24GB/1TB',
            'Apple MacBook Pro 14.2", 24GB, 1TB SSD, M5 Pro, 2026', 'apple macbook pro 14 2 24gb 1tb ssd m5 pro 2026',
            'Apple M5 Pro, 24GB RAM + 1TB SSD, 14.2" Liquid Retina XDR display, Apple 16-Core GPU')
    RETURNING id INTO v_product_id;
    INSERT INTO product_specifications (product_id, spec_key, spec_value) VALUES
        (v_product_id, 'cpu', 'Apple M5 Pro'), (v_product_id, 'ram', '24GB'), (v_product_id, 'ssd', '1TB'),
        (v_product_id, 'display_size', '14.2"');
    INSERT INTO product_images (product_id, url, position, source_merchant_id) VALUES
        (v_product_id, 'https://assets.shpresa.al/shop/2026/04/6d18bbe3-dun2886-b-3.jpg', 0, v_merchant_id);
    INSERT INTO offers (product_id, merchant_id, merchant_product_id, price, currency, shipping_cost,
                         total_price, availability, url, image_url, source_type)
    VALUES (v_product_id, v_merchant_id, 'apple-macbook-pro-14-2-24gb-1tb-ssd-m5-pro-2026', 259990.00, 'ALL', NULL,
            259990.00, 'IN_STOCK', 'https://shpresa.al/product/apple-macbook-pro-14-2-24gb-1tb-ssd-m5-pro-2026/',
            'https://assets.shpresa.al/shop/2026/04/6d18bbe3-dun2886-b-3.jpg', 'MANUAL')
    RETURNING id INTO v_offer_id;
    INSERT INTO price_history (product_id, offer_id, merchant_id, price, shipping_cost, total_price, currency, availability)
    VALUES (v_product_id, v_offer_id, v_merchant_id, 259990.00, NULL, 259990.00, 'ALL', 'IN_STOCK');

    -- 6. Apple MacBook Pro 14.2" 24GB 2TB SSD M5 Pro 2026 - 279,990 L (discounted from 299,990)
    INSERT INTO products (brand_id, category_id, model, title, normalized_title, description)
    VALUES (v_apple_id, v_laptops_id, 'MacBook Pro 14.2" M5 Pro 24GB/2TB',
            'Apple MacBook Pro 14.2", 24GB, 2TB SSD, M5 Pro, 2026', 'apple macbook pro 14 2 24gb 2tb ssd m5 pro 2026',
            'Apple M5 Pro, 24GB RAM + 2TB SSD, 14.2" Liquid Retina XDR display, Apple 20-Core GPU')
    RETURNING id INTO v_product_id;
    INSERT INTO product_specifications (product_id, spec_key, spec_value) VALUES
        (v_product_id, 'cpu', 'Apple M5 Pro'), (v_product_id, 'ram', '24GB'), (v_product_id, 'ssd', '2TB'),
        (v_product_id, 'display_size', '14.2"');
    INSERT INTO product_images (product_id, url, position, source_merchant_id) VALUES
        (v_product_id, 'https://assets.shpresa.al/shop/2026/04/6d18bbe3-dun2886-b-3.jpg', 0, v_merchant_id);
    INSERT INTO offers (product_id, merchant_id, merchant_product_id, price, currency, old_price, discount_percent,
                         shipping_cost, total_price, availability, url, image_url, source_type)
    VALUES (v_product_id, v_merchant_id, 'apple-macbook-pro-14-2-24gb-2tb-ssd-m5-pro-2026', 279990.00, 'ALL',
            299990.00, 6.67, NULL, 279990.00, 'IN_STOCK',
            'https://shpresa.al/product/apple-macbook-pro-14-2-24gb-2tb-ssd-m5-pro-2026/',
            'https://assets.shpresa.al/shop/2026/04/6d18bbe3-dun2886-b-3.jpg', 'MANUAL')
    RETURNING id INTO v_offer_id;
    INSERT INTO price_history (product_id, offer_id, merchant_id, price, shipping_cost, total_price, currency, availability)
    VALUES (v_product_id, v_offer_id, v_merchant_id, 279990.00, NULL, 279990.00, 'ALL', 'IN_STOCK');
END $$;
