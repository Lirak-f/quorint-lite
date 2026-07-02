-- Enable RLS on all public tables exposed via PostgREST.
-- freight_benchmarks is public read-only reference data.
-- All other tables are scoped to the owning authenticated user.

-- ─────────────────────────────────────────
-- Enable RLS
-- ─────────────────────────────────────────

ALTER TABLE manufacturers       ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports             ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_demand       ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_compliance   ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_buyers       ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_embeddings   ENABLE ROW LEVEL SECURITY;
ALTER TABLE retention_triggers  ENABLE ROW LEVEL SECURITY;
ALTER TABLE freight_benchmarks  ENABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────
-- manufacturers
-- ─────────────────────────────────────────

CREATE POLICY "manufacturers_select_own"
  ON manufacturers FOR SELECT
  TO authenticated
  USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "manufacturers_insert_own"
  ON manufacturers FOR INSERT
  TO authenticated
  WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "manufacturers_update_own"
  ON manufacturers FOR UPDATE
  TO authenticated
  USING  ((SELECT auth.uid()) = user_id)
  WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "manufacturers_delete_own"
  ON manufacturers FOR DELETE
  TO authenticated
  USING ((SELECT auth.uid()) = user_id);

-- ─────────────────────────────────────────
-- reports
-- ─────────────────────────────────────────

CREATE POLICY "reports_select_own"
  ON reports FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM manufacturers m
      WHERE m.id = reports.manufacturer_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "reports_insert_own"
  ON reports FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM manufacturers m
      WHERE m.id = reports.manufacturer_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "reports_update_own"
  ON reports FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM manufacturers m
      WHERE m.id = reports.manufacturer_id
        AND m.user_id = (SELECT auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM manufacturers m
      WHERE m.id = reports.manufacturer_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "reports_delete_own"
  ON reports FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM manufacturers m
      WHERE m.id = reports.manufacturer_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

-- ─────────────────────────────────────────
-- report_demand
-- ─────────────────────────────────────────

CREATE POLICY "report_demand_select_own"
  ON report_demand FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_demand.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "report_demand_insert_own"
  ON report_demand FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_demand.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "report_demand_update_own"
  ON report_demand FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_demand.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_demand.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

-- ─────────────────────────────────────────
-- report_compliance
-- ─────────────────────────────────────────

CREATE POLICY "report_compliance_select_own"
  ON report_compliance FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_compliance.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "report_compliance_insert_own"
  ON report_compliance FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_compliance.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "report_compliance_update_own"
  ON report_compliance FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_compliance.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_compliance.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

-- ─────────────────────────────────────────
-- report_buyers
-- ─────────────────────────────────────────

CREATE POLICY "report_buyers_select_own"
  ON report_buyers FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_buyers.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "report_buyers_insert_own"
  ON report_buyers FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_buyers.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "report_buyers_update_own"
  ON report_buyers FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_buyers.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_buyers.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

-- ─────────────────────────────────────────
-- report_embeddings
-- ─────────────────────────────────────────

CREATE POLICY "report_embeddings_select_own"
  ON report_embeddings FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_embeddings.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "report_embeddings_insert_own"
  ON report_embeddings FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_embeddings.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "report_embeddings_update_own"
  ON report_embeddings FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_embeddings.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = report_embeddings.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

-- ─────────────────────────────────────────
-- retention_triggers
-- ─────────────────────────────────────────

CREATE POLICY "retention_triggers_select_own"
  ON retention_triggers FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM reports r
      JOIN manufacturers m ON m.id = r.manufacturer_id
      WHERE r.id = retention_triggers.report_id
        AND m.user_id = (SELECT auth.uid())
    )
  );

-- ─────────────────────────────────────────
-- freight_benchmarks — public read-only reference data
-- ─────────────────────────────────────────

CREATE POLICY "freight_benchmarks_select_all"
  ON freight_benchmarks FOR SELECT
  TO authenticated
  USING (true);
