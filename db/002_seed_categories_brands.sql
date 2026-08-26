-- ==============================================================
-- Seed: MVP categories (section 2) and brands
-- ==============================================================

INSERT INTO categories (slug, name, filter_schema) VALUES
('smartphones', 'Smartphones', '{"filters":["brand","model","storage","ram","display","camera","5g","price"]}'),
('laptops', 'Laptops', '{"filters":["brand","cpu","gpu","ram","ssd","display_size","resolution","refresh_rate","price"]}'),
('tvs', 'TVs', '{"filters":["brand","size","panel_type","resolution","refresh_rate","hdr","smart_tv","price"]}'),
('gaming', 'Gaming', '{"filters":["platform","model","storage","edition","bundle","price"]}'),
('smartwatch', 'Smartwatch', '{"filters":["brand","model","case_size","connectivity","price"]}'),
('monitors', 'Monitors', '{"filters":["brand","size","resolution","refresh_rate","panel_type","price"]}'),
('audio', 'Audio', '{"filters":["brand","type","noise_cancelling","battery_life","price"]}'),
('pc-components', 'PC Components', '{"filters":["brand","component_type","socket","memory_size","price"]}');

-- Subcategories for PC Components
INSERT INTO categories (parent_id, slug, name) VALUES
((SELECT id FROM categories WHERE slug='pc-components'), 'gpu-nvidia', 'NVIDIA GPU'),
((SELECT id FROM categories WHERE slug='pc-components'), 'gpu-amd', 'AMD GPU'),
((SELECT id FROM categories WHERE slug='pc-components'), 'cpu-intel', 'Intel CPU'),
((SELECT id FROM categories WHERE slug='pc-components'), 'cpu-amd', 'AMD CPU'),
((SELECT id FROM categories WHERE slug='pc-components'), 'ram', 'RAM'),
((SELECT id FROM categories WHERE slug='pc-components'), 'ssd', 'SSD');

INSERT INTO brands (slug, name) VALUES
('apple', 'Apple'),
('samsung', 'Samsung'),
('xiaomi', 'Xiaomi'),
('lenovo', 'Lenovo'),
('asus', 'ASUS'),
('acer', 'Acer'),
('hp', 'HP'),
('dell', 'Dell'),
('msi', 'MSI'),
('lg', 'LG'),
('sony', 'Sony'),
('tcl', 'TCL'),
('hisense', 'Hisense'),
('playstation', 'PlayStation'),
('xbox', 'Xbox'),
('nintendo', 'Nintendo'),
('garmin', 'Garmin'),
('aoc', 'AOC'),
('jbl', 'JBL'),
('bose', 'Bose'),
('nvidia', 'NVIDIA'),
('amd', 'AMD'),
('intel', 'Intel')
ON CONFLICT (slug) DO NOTHING;
