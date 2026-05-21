-- Quorint initial schema
-- Run via: supabase db push

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ─────────────────────────────────────────
-- Core tables
-- ─────────────────────────────────────────

CREATE TABLE manufacturers (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES auth.users(id),
  company     TEXT,
  origin_iso2 CHAR(2),
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE reports (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manufacturer_id UUID REFERENCES manufacturers(id),
  hs_code         TEXT        NOT NULL,
  origin_iso2     CHAR(2)     NOT NULL,
  target_iso2     CHAR(2)     NOT NULL,
  unit_cost_eur   NUMERIC(10,2),
  tier            TEXT        NOT NULL CHECK (tier IN ('starter','full')),
  status          TEXT        NOT NULL DEFAULT 'queued'
                  CHECK (status IN ('queued','running','complete','failed')),
  is_test         BOOLEAN     NOT NULL DEFAULT false,
  stripe_id       TEXT,
  pdf_url         TEXT,
  error_message   TEXT,
  created_at      TIMESTAMPTZ DEFAULT now(),
  completed_at    TIMESTAMPTZ
);

CREATE TABLE report_demand (
  report_id           UUID PRIMARY KEY REFERENCES reports(id),
  import_value_usd    BIGINT,
  cagr_5yr            NUMERIC(6,4),
  top_suppliers       JSONB,
  tariff_mfn          NUMERIC(5,4),
  tariff_preferential NUMERIC(5,4),
  trade_agreement     TEXT,
  rca_score           NUMERIC(6,3),
  retail_p25_eur      NUMERIC(10,2),
  retail_median_eur   NUMERIC(10,2),
  retail_p75_eur      NUMERIC(10,2),
  wholesale_low_eur   NUMERIC(10,2),
  wholesale_high_eur  NUMERIC(10,2),
  freight_low_eur     INTEGER,
  freight_high_eur    INTEGER,
  dap_per_unit_eur    NUMERIC(10,2),
  margin              NUMERIC(5,4),
  margin_verdict      TEXT CHECK (margin_verdict IN ('viable','tight','not_viable')),
  competitor_summary  TEXT,
  fx_volatility_90d   NUMERIC(6,4)
);

CREATE TABLE report_compliance (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id       UUID REFERENCES reports(id),
  cert_id         TEXT,
  cert_name       TEXT,
  cert_type       TEXT CHECK (cert_type IN ('mandatory','commercial_expected','recommended')),
  critical        BOOLEAN DEFAULT false,
  cost_low_eur    INTEGER,
  cost_high_eur   INTEGER,
  lead_time_min   INTEGER,
  lead_time_max   INTEGER,
  providers       TEXT[],
  note            TEXT
);

CREATE TABLE report_buyers (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id             UUID REFERENCES reports(id),
  company_name          TEXT,
  company_domain        TEXT,
  city                  TEXT,
  country_iso2          CHAR(2),
  buyer_type            TEXT,
  contact_name          TEXT,
  contact_title         TEXT,
  contact_email         TEXT,
  linkedin_url          TEXT,
  enrichment_source     TEXT CHECK (enrichment_source IN ('apollo','pdl','perplexity')),
  receptiveness_score   INTEGER CHECK (receptiveness_score BETWEEN 0 AND 100),
  receptiveness_signals JSONB,
  tier                  TEXT CHECK (tier IN ('warm','cold','skip')),
  created_at            TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE report_embeddings (
  report_id UUID PRIMARY KEY REFERENCES reports(id),
  embedding vector(1536)
);

CREATE TABLE retention_triggers (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id    UUID REFERENCES reports(id),
  trigger_type TEXT CHECK (trigger_type IN ('tariff_change','new_buyer','day30')),
  fired_at     TIMESTAMPTZ DEFAULT now(),
  email_sent   BOOLEAN DEFAULT false,
  opened       BOOLEAN DEFAULT false
);

-- ─────────────────────────────────────────
-- Freight benchmarks
-- Road freight only. FTL rates, validated quarterly.
-- ─────────────────────────────────────────

CREATE TABLE freight_benchmarks (
  origin_iso2      CHAR(2)  NOT NULL,
  dest_iso2        CHAR(2)  NOT NULL,
  rate_low_eur     INTEGER  NOT NULL,
  rate_high_eur    INTEGER  NOT NULL,
  transit_days_min INTEGER  NOT NULL,
  transit_days_max INTEGER  NOT NULL,
  mode             TEXT     NOT NULL CHECK (mode IN ('road','road_ferry')),
  validated_date   DATE     NOT NULL,
  notes            TEXT,
  PRIMARY KEY (origin_iso2, dest_iso2)
);

INSERT INTO freight_benchmarks VALUES
('XK','AT', 2400,3100, 4,6, 'road',       '2026-05-01', NULL),
('XK','DE', 2800,3600, 5,7, 'road',       '2026-05-01', NULL),
('XK','IT', 2600,3400, 3,5, 'road',       '2026-05-01', 'Via Bar ferry or Slovenia road'),
('XK','FR', 3200,4200, 6,8, 'road',       '2026-05-01', NULL),
('XK','NL', 3000,3900, 6,8, 'road',       '2026-05-01', NULL),
('XK','CH', 3000,3900, 5,7, 'road',       '2026-05-01', NULL),
('AL','IT',  800,1200, 3,5, 'road_ferry', '2026-05-01', 'Durrës→Bari/Ancona ferry + road'),
('AL','DE', 2600,3400, 5,7, 'road',       '2026-05-01', NULL),
('AL','AT', 2200,2900, 4,6, 'road',       '2026-05-01', NULL),
('RS','DE', 2200,3000, 4,6, 'road',       '2026-05-01', NULL),
('RS','AT', 1800,2400, 3,5, 'road',       '2026-05-01', NULL),
('RS','IT', 2000,2800, 3,5, 'road',       '2026-05-01', NULL),
('BA','AT', 1600,2200, 4,5, 'road',       '2026-05-01', NULL),
('BA','DE', 2000,2800, 5,6, 'road',       '2026-05-01', NULL),
('MK','DE', 2600,3400, 5,7, 'road',       '2026-05-01', NULL),
('MK','IT', 2200,3000, 4,6, 'road',       '2026-05-01', NULL),
('ME','IT',  900,1300, 3,5, 'road_ferry', '2026-05-01', 'Bar→Bari ferry + road');

-- ─────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────

CREATE INDEX idx_reports_manufacturer ON reports(manufacturer_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_report_buyers_report ON report_buyers(report_id);
CREATE INDEX idx_report_buyers_tier ON report_buyers(tier);
CREATE INDEX idx_report_compliance_report ON report_compliance(report_id);
CREATE INDEX idx_retention_triggers_report ON retention_triggers(report_id);
