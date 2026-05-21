-- Add certifications and capacity_units columns to reports table
ALTER TABLE reports
  ADD COLUMN IF NOT EXISTS certifications TEXT[] NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS capacity_units  TEXT   NOT NULL DEFAULT '<100/mo'
    CHECK (capacity_units IN ('<100/mo', '100-500/mo', '500+/mo'));
