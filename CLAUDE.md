# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project
Vertical AI tool for Balkan (WB6: Kosovo, Albania, Serbia, Bosnia, North Macedonia, Montenegro)
manufacturers to generate export market reports (demand, pricing, compliance, buyer contacts,
90-day action plan) in under 5 minutes.
Full product spec: QUORINT_CONTEXT.md — read it before touching any pipeline code. Report
section-by-section logic: REPORT_LOGIC.md.

Note: QUORINT_CONTEXT.md describes the original design (LangGraph "Supervisor" pattern, 4 sector
configs, 5 always-on workers). The actual implementation has diverged — see Architecture below
for what's really there.

## Stack
- Frontend: Next.js 16 (App Router) + TypeScript + Tailwind v4 + shadcn/ui — apps/web/
- Backend: FastAPI + Python 3.11/3.12 + LangGraph — apps/api/
- Database: Supabase (Postgres + pgvector + realtime), RLS enabled on all tables
- Queue: Custom Redis-list poller in `apps/api/jobqueue/` (BullMQ-compatible key format, not real BullMQ)
- AI: Claude (Anthropic SDK, all workers) + Perplexity Sonar / Sonar Deep Research (buyers + research)
- Payments: Paddle (Checkout + webhooks)
- Observability: Langfuse (mandatory `@observe()` on every LLM-calling function), Sentry, PostHog

## Commands
```bash
# Run both API + web together (root)
npm run dev

# Backend only
cd apps/api && uvicorn main:app --reload

# BullMQ-style queue worker (separate process, required for real job processing)
cd apps/api && python -m jobqueue.worker

# Full pipeline test, no queue, no Paddle (the canonical smoke test)
cd apps/api && python test_report.py --hs 940360 --origin XK --target AT --cost 200 --pdf

# Run only specific workers, verbose output
cd apps/api && python test_report.py --hs 940360 --origin XK --target AT --cost 200 --workers 1,2,3 --verbose

# Run worker 1 (market demand) test only
cd apps/api && python tests/test_worker1.py

# Run workers 1-3 integration test
cd apps/api && python tests/test_workers_1_2_3.py

# Full pipeline pytest suite
cd apps/api && pytest tests/test_full_pipeline.py

# Frontend
cd apps/web && npm run dev      # dev server
cd apps/web && npm run build    # production build
cd apps/web && npm run lint     # eslint

# DB migrations
supabase db push
```

Other canonical test cases from QUORINT_CONTEXT.md (different sectors/margins):
```bash
python test_report.py --hs 620520 --origin AL --target IT --cost 15 --pdf
python test_report.py --hs 870899 --origin RS --target DE --cost 85 --pdf
python test_report.py --hs 150910 --origin MK --target DE --cost 3.50 --pdf
```

## Hard rules
- HS code mapping is ALWAYS done by the user — never by AI. No exceptions.
- SeaRates API is NOT used. Road freight only for WB6→EU. Use the `freight_benchmarks` table.
- MOQ and payment terms are NOT estimated. These come from buyer interaction, not AI inference.
- Every LLM call must be wrapped in a Langfuse `@observe()` decorator.
- Internal test reports: `is_test=true`, gated by `INTERNAL_TEST_TOKEN` header (`POST /api/reports/test`), never counted in metrics.
- Landed cost calculation is deterministic Python math — no LLM involved.
- Adding a new sector = drop a YAML into `apps/api/scoring/configs/` — no code changes required. HS chapters must not overlap between configs (enforced at load time — raises `ValueError`).

## Architecture

### Pipeline flow
```
Web form (apps/web/app/new/) → POST /api/reports (Paddle gate) → job enqueued to Redis
  → apps/api/jobqueue/worker.py polls Redis (BullMQ key format: bull:report-generation:waiting/active)
  → pipeline/orchestrator.py::run_pipeline() runs the LangGraph graph synchronously
  → each worker node writes progress to Supabase `reports.current_worker` (1-5)
  → apps/web subscribes to Supabase Realtime for live "Worker N/5 complete" status
  → on completion: PDF generated (WeasyPrint) → Supabase Storage → signed URL
```

For local/manual testing, `test_report.py` and `tests/test_worker*.py` call worker functions
directly (or via `pipeline/orchestrator.py`), bypassing Redis and Paddle entirely.

### LangGraph pipeline is a fixed linear sequence, not a supervisor
Despite QUORINT_CONTEXT.md describing a "Supervisor" pattern, `apps/api/pipeline/graph.py`
builds a strictly linear graph: `w1_market → w2_compliance → w3_buyers → w4_deep_research → w5_synthesis → END`.
State is a plain dict (`PipelineState`) threaded through each node function. Each node in
`pipeline/graph.py` is a thin wrapper — actual logic lives in `apps/api/workers/*.py`.

**Worker 2 (compliance) is currently disabled** (`node_w2_compliance` in `pipeline/graph.py`
short-circuits to an empty `ComplianceOutput` without calling `workers/compliance.py` or any LLM).
Check this before assuming compliance data is populated in a report.

### Workers (`apps/api/workers/`)
One file per pipeline stage — implementation, not just orchestration:
- `market_demand.py` — Comtrade, WITS, OEC, WDI, ScraperAPI (Google Shopping), Perplexity, FX, freight lookup, then deterministic landed-cost math
- `compliance.py` — exists but not wired into the live graph (see above)
- `buyers.py` — Apollo → PDL → Perplexity waterfall, then scoring
- `deep_research.py` — Perplexity Sonar Deep Research
- `synthesis.py` — assembles all worker outputs + manufacturer profile into final report markdown, email copy, action plan, risk flags

### External data clients (`apps/api/data/`)
One thin client per external API: `apollo.py`, `comtrade.py`, `exchangerate.py`, `oec.py`,
`pdl.py`, `perplexity.py`, `scraper.py`, `tentimes.py`, `wdi.py`, `wits.py`. Wrap outbound
HTTP calls with `resilience.retry_with_backoff()` (exponential backoff on 429/5xx/transport
errors) and `resilience.log_langfuse_error()` for failures.

### Sector YAML config system (`apps/api/scoring/`)
`config_loader.py::load_sector_config(hs_code)` builds an HS-chapter → sector index by
scanning every YAML in `scoring/configs/` on first call (cached after that), keyed by each
file's `hs_chapters` list. **21 sector configs exist** (agriculture_raw, arms_ammunition,
auto_parts, chemicals_pharma, food_beverage, furniture_wood, instruments_optical,
leather_footwear, live_animals_meat, machinery, metals_steel, minerals_mining, paper_printing,
plastics_rubber, raw_textiles, stone_ceramics_glass, textiles_apparel, tobacco,
toys_sports_misc, transport_other, works_of_art) — far more than the 4 described in
QUORINT_CONTEXT.md. Read the relevant YAML before touching Worker 1 or 3 logic for a sector.

`scoring/engine.py::score_buyer()` implements receptiveness scoring — note it has **6 signals**
in code (import diversification, active sourcing, growth trajectory, trade fair activity,
decision-maker accessibility, plus a price-tier/buyer-type alignment bonus/penalty), one more
than the 5 documented in QUORINT_CONTEXT.md. Tiers: `warm` (≥70), `cold` (40-69), `skip` (<40).

`scoring/working_capital.py` — deterministic working-capital estimate math for Section 6.

### API routes (`apps/api/routers/`)
- `reports.py`: `POST /api/reports` (create + Paddle checkout gate), `POST /api/reports/{id}/run`, `GET /api/reports/{id}`
- `test_reports.py`: `POST /api/reports/test` — internal bypass, requires `INTERNAL_TEST_TOKEN` bearer header
- `webhooks.py`: `POST /api/webhooks/paddle` — payment completion triggers job enqueue

Auth (`auth.py`) verifies Supabase JWTs by calling `auth/v1/user` on the Supabase Auth server
(no local JWT verification) — `require_auth` FastAPI dependency.

### Frontend (`apps/web/`)
App Router structure: `app/new/` (onboarding form) → `app/reports/[id]/` (live status +
report view via Supabase Realtime) → `app/api/checkout/route.ts` (Paddle) and
`app/api/reports/[id]/run/route.ts` (proxies to FastAPI). `app/internal/reports/` is the
internal test-report dashboard. Supabase client helpers split by context in `lib/supabase/`
(`client.ts` browser, `server.ts` RSC/route handlers, `middleware.ts` session refresh).

`packages/shared/` holds cross-app TypeScript types (report/worker output shapes) shared
between `apps/web` and any TS tooling — keep in sync with the Pydantic models in `apps/api/models.py`
when changing report output shape.

**Note:** `apps/web/AGENTS.md` states this Next.js version has breaking changes from training
data — check `node_modules/next/dist/docs/` for the installed version's actual APIs before
writing App Router code that looks "obviously right."

### Database (`supabase/migrations/`)
Migrations are sequential and additive (001 through 010, plus one RLS-enablement migration
run out of numeric sequence — `20260527181505_enable_rls_all_tables.sql`). Core tables:
`manufacturers`, `reports`, `report_demand`, `report_compliance`, `report_buyers`,
`report_embeddings`, `retention_triggers`, `freight_benchmarks`. RLS is enabled on all tables —
check policy implications before adding new tables or columns that the frontend queries directly.

### Retention crons (`apps/api/crons/retention.py`)
Scheduled via APScheduler in `main.py` lifespan (not a separate cron service): weekly tariff-change
check (Mon 06:00), monthly new-buyer signal (day 1, 07:00), daily day-30 re-engagement sweep (08:00).

## Key files
- QUORINT_CONTEXT.md — full product spec, report structure, data sources, schema, cost model
- REPORT_LOGIC.md — section-by-section report generation logic
- apps/api/scoring/configs/ — sector YAML configs (read before touching Worker 1 or 3)
- apps/api/pipeline/graph.py — actual pipeline wiring (source of truth over the spec doc)
- apps/api/workers/ — one file per worker
- apps/api/models.py — Pydantic models for all worker I/O; keep in sync with packages/shared/types.ts
- supabase/migrations/001_initial.sql — base schema including freight_benchmarks seed data

## Canonical test case
HS 940360, origin XK, target AT, unit_cost 200
Run this to verify any pipeline change works end to end.
