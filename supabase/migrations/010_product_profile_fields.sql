-- Migration 010: Product profile attributes for guided input flow (Step 1b)
-- Adds columns to reports that capture the richer product context needed
-- to make Apollo buyer searches precise rather than sector-broad.

ALTER TABLE reports
  ADD COLUMN IF NOT EXISTS product_phrase    TEXT,
  ADD COLUMN IF NOT EXISTS end_buyer_type    TEXT,
  ADD COLUMN IF NOT EXISTS price_tier        TEXT,
  ADD COLUMN IF NOT EXISTS packaging_format  TEXT[],
  ADD COLUMN IF NOT EXISTS material_subtype  TEXT,
  ADD COLUMN IF NOT EXISTS processing_level  TEXT;
