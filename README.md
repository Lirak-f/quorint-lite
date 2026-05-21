# Quorint

Export market intelligence for Balkan manufacturers. Generate a full market report (demand, pricing, compliance, buyer contacts, 90-day action plan) in under 5 minutes.

## Prerequisites

- Python 3.11 (via pyenv recommended)
- Node.js 20+
- Redis 7+
- [Supabase](https://supabase.com) project
- [Langfuse](https://langfuse.com) project (LLM observability)
- API keys: Anthropic or Gemini (LLM), Perplexity (research), Apollo (buyers), ScraperAPI (pricing)

## Local setup

**1. Clone and install**

```bash
git clone <repo>
cd quorint-lite
pip3 install -e apps/api
cd apps/web && npm install
```

**2. Configure environment — API**

Create `apps/api/.env`:

```env
# LLM (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...

# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...

# Research & data
PERPLEXITY_API_KEY=pplx-...
SCRAPERAPI_KEY=...
EXCHANGERATE_API_KEY=...

# Buyer discovery
APOLLO_API_KEY=...
PDL_API_KEY=...
TENTIMES_API_KEY=...

# Observability
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Redis
REDIS_URL=redis://localhost:6379

# Payments (Paddle)
PADDLE_API_KEY=...
PADDLE_WEBHOOK_SECRET=...

# Optional
SENTRY_DSN_API=https://...@sentry.io/...
INTERNAL_TEST_TOKEN=some-secret
```

**3. Configure environment — web**

Create `apps/web/.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_POSTHOG_KEY=phc_...
NEXT_PUBLIC_POSTHOG_HOST=https://eu.i.posthog.com
NEXT_PUBLIC_SENTRY_DSN=https://...@sentry.io/...
```

**4. Run database migrations**

```bash
supabase db push
```

**5. Start all services**

```bash
# Terminal 1 — API
cd apps/api && uvicorn main:app --reload

# Terminal 2 — BullMQ worker
cd apps/api && python -m jobqueue.worker

# Terminal 3 — Web
cd apps/web && npm run dev
```

Or with Docker (Redis included):

```bash
docker compose up
cd apps/web && npm run dev
```

## Canonical test

Verify the full pipeline works end-to-end (no queue, no Paddle):

```bash
cd apps/api
python test_report.py --hs 940360 --origin XK --target AT --cost 200 --pdf
```

Expected: `report_940360_XK_AT.md` and `report_940360_XK_AT.pdf` generated in `apps/api/`.

Run a single worker in isolation:

```bash
python tests/test_worker1.py
```

## Deploy

### API → Railway

1. Create a new Railway project, connect this repo
2. Add a service pointing to `apps/api/` as root directory
3. Railway picks up `nixpacks.toml` (system libs) and `railway.toml` (start command) automatically
4. Set all `apps/api/.env` variables in Railway → Variables
5. Add a Redis service (Railway provides one); set `REDIS_URL` from the Railway Redis internal URL
6. Add a second service from the same repo for the BullMQ worker — override start command to:
   ```
   python -m jobqueue.worker
   ```

### Web → Vercel

1. Import the repo into Vercel
2. Vercel reads `vercel.json` at the repo root — no further config needed
3. Set all `apps/web/.env.local` variables in Vercel → Environment Variables
4. Set `NEXT_PUBLIC_API_URL` to your Railway API URL

## Adding a new sector config

Create `apps/api/scoring/configs/<sector>.yaml` following the structure of `furniture_wood.yaml`:

```yaml
hs_chapters: [84, 85]          # list of 2-digit HS chapters this sector covers

price_queries:                 # used by Worker 1 to scrape retail prices
  de: "Maschinenteil kaufen"
  en: "machine part buy wholesale"

compliance_checks:             # used by Worker 2
  - id: ce_machinery
    name: "CE Marking — Machinery Directive 2006/42/EC"
    regulation: "Directive 2006/42/EC"
    critical: true             # marks report as blocked if missing
    typical_cost_eur: 8000
    typical_weeks: 16
    certifier_name: "TÜV SÜD"
    certifier_phone: "+49 89 5791 0"
    certifier_url: "https://www.tuvsud.com"

buyer_filters:                 # passed to Apollo search
  keywords: ["machinery", "industrial equipment"]
  sic_codes: ["3559", "3679"]

trade_fairs:                   # included in synthesis / action plan
  - name: "Hannover Messe"
    city: "Hannover"
    month: "April"
    url: "https://www.hannovermesse.de"

working_capital:
  typical_first_order_units: 5
  typical_compliance_cost_eur: 20000
  retail_to_wholesale_ratio: 0.6
```

The pipeline picks up any YAML in that directory automatically — no code changes required.
