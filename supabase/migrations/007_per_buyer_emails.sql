-- Per-buyer personalised outreach emails (replaces single first_contact_email)
ALTER TABLE reports
  ADD COLUMN IF NOT EXISTS per_buyer_emails JSONB DEFAULT '[]'::jsonb;
