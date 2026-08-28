-- Bug found while testing db/004 and db/005 in this session: merchant_sources
-- had no uniqueness constraint at all, so re-running a migration (which
-- happened during iteration) silently duplicated rows instead of the
-- intended ON CONFLICT DO NOTHING no-op. Also cleans up any stale
-- placeholder-domain merchant rows left over from before db/004 started
-- enforcing uniqueness on `name` (see db/004's DO block).

-- merchant_sources: keep the earliest row per (merchant_id, source_type).
DELETE FROM merchant_sources a USING merchant_sources b
WHERE a.merchant_id = b.merchant_id
  AND a.source_type = b.source_type
  AND a.id > b.id;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_merchant_sources_merchant_source_type') THEN
        ALTER TABLE merchant_sources
            ADD CONSTRAINT uq_merchant_sources_merchant_source_type UNIQUE (merchant_id, source_type);
    END IF;
END $$;

-- merchants: drop any leftover placeholder-domain duplicate rows a merchant
-- may have picked up before uq_merchants_name existed (harmless no-op on a
-- fresh database, where this never happened).
DELETE FROM merchants
WHERE domain LIKE '%.pending-review.invalid'
  AND name IN (SELECT name FROM merchants WHERE domain NOT LIKE '%.pending-review.invalid' GROUP BY name);
