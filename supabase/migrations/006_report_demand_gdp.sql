-- Add gdp_usd and lpi_score columns that were in DemandOutput but missing from report_demand
ALTER TABLE report_demand
  ADD COLUMN IF NOT EXISTS gdp_usd   NUMERIC(20,2),
  ADD COLUMN IF NOT EXISTS lpi_score NUMERIC(5,3);
