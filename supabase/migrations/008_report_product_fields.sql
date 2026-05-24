ALTER TABLE reports
  ADD COLUMN IF NOT EXISTS product_name    TEXT,
  ADD COLUMN IF NOT EXISTS product_desc    TEXT,
  ADD COLUMN IF NOT EXISTS lead_count      INTEGER CHECK (lead_count IN (10, 20, 30)),
  ADD COLUMN IF NOT EXISTS moq             INTEGER,
  ADD COLUMN IF NOT EXISTS lead_time_days  INTEGER;
