-- Widen unit_cost_eur to support sub-cent values (e.g. commodity prices like 0.0001)
ALTER TABLE reports
  ALTER COLUMN unit_cost_eur TYPE NUMERIC(18,6);
