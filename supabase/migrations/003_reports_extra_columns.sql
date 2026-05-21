-- Add columns missing from initial schema
ALTER TABLE reports
  ADD COLUMN IF NOT EXISTS capacity_units TEXT DEFAULT '<100/mo',
  ADD COLUMN IF NOT EXISTS certifications JSONB DEFAULT '[]';
