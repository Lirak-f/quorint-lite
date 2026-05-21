-- Migrate from Stripe to Paddle
-- Run via: supabase db push

ALTER TABLE reports
  DROP COLUMN IF EXISTS stripe_id,
  ADD COLUMN IF NOT EXISTS paddle_transaction_id TEXT,
  ADD COLUMN IF NOT EXISTS paddle_subscription_id TEXT;

ALTER TABLE manufacturers
  ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'none',
  ADD COLUMN IF NOT EXISTS paddle_subscription_id TEXT;
