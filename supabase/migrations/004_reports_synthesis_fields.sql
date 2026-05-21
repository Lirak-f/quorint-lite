-- Add synthesis output columns to reports table
ALTER TABLE reports
  ADD COLUMN IF NOT EXISTS full_report_markdown          TEXT,
  ADD COLUMN IF NOT EXISTS first_contact_email           TEXT,
  ADD COLUMN IF NOT EXISTS first_contact_subject_lines   TEXT[]  DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS action_plan_markdown           TEXT,
  ADD COLUMN IF NOT EXISTS risk_flags_markdown            TEXT,
  ADD COLUMN IF NOT EXISTS current_worker                SMALLINT DEFAULT 0;
