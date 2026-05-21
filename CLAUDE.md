# Quorint — Claude Code Configuration

## Project
Vertical AI tool for Balkan manufacturers to generate export market reports.
Full spec: QUORINT_CONTEXT.md — read it before touching any pipeline code.

## Stack
- Frontend: Next.js 15 + TypeScript + Tailwind + shadcn/ui — apps/web/
- Backend: FastAPI + Python 3.12 + LangGraph — apps/api/
- Database: Supabase (Postgres + pgvector + realtime)
- Queue: BullMQ + Redis
- AI: Claude Sonnet 4.6 (all workers) + Perplexity Sonar Deep Research (Worker 4)
- Observability: Langfuse — mandatory on every worker via @observe()

## Commands
```bash
# Backend
cd apps/api && uvicorn main:app --reload

# Test a single worker (no queue, no Paddle)
cd apps/api && python test_report.py --hs 940360 --origin XK --target AT --cost 200 --pdf

# Run worker 1 test only
cd apps/api && python tests/test_worker1.py

# Frontend
cd apps/web && npm run dev

# DB migrations
supabase db push
```

## Hard rules
- HS code mapping is ALWAYS done by the user — never by AI. No exceptions.
- SeaRates API is NOT used. Road freight only for WB6→EU. Use freight_benchmarks table.
- MOQ and payment terms are NOT estimated. These come from buyer interaction.
- Every LLM call must be wrapped in a Langfuse @observe() decorator.
- Internal test reports: is_test=true, gated by INTERNAL_TEST_TOKEN header.
- Landed cost calculation is deterministic Python math — no LLM involved.

## Key files
- QUORINT_CONTEXT.md — full product spec, report structure, data sources, schema
- apps/api/scoring/configs/ — sector YAML configs (read before touching Worker 1 or 3)
- apps/api/workers/ — one file per worker (market_demand, compliance, buyers, deep_research, synthesis)
- supabase/migrations/001_initial.sql — DB schema including freight_benchmarks seed data

## Canonical test case
HS 940360, origin XK, target AT, unit_cost 200
Run this to verify any pipeline change works end to end.
