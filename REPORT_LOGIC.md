# Quorint Report Logic — System Documentation

## Overview

Quorint generates export market intelligence reports for Balkan manufacturers targeting specific EU countries. Each report answers five questions: Is there demand? Can we make money? What compliance is required? Who should we contact? What do we do first?

A report is scoped to a single manufacturer × single target country × single HS code combination. The pipeline runs five workers in sequence, each producing a structured output that feeds into the next, culminating in a complete markdown report delivered in under 5 minutes.

---

## Report Generation Trigger

### Prerequisites

Before a report job is enqueued, the manufacturer must provide:

| Field | Description |
|---|---|
| `hs_code` | 4 or 6-digit HS code — **user-confirmed, never AI-inferred** |
| `origin_iso2` | Origin country (XK / AL / RS / BA / MK / ME) |
| `target_iso2` | Single target country (one report per purchase) |
| `unit_cost_eur` | Unit production cost in EUR |
| `certifications` | Certifications currently held (checkboxes) |
| `capacity_units` | Monthly production capacity range |
| `tier` | `"starter"` (€29) or `"full"` (€49) |

### Payment Gate

All report jobs pass through Paddle. The tier determines which report sections are included:

- **Starter (€29):** Sections 1, 3, top-5 buyers (no score detail), Section 6 (basic)
- **Full (€49):** All 7 sections, buyer receptiveness scores + signals, personalised email
- **Internal test:** `POST /api/reports/test` with `Authorization: Bearer $INTERNAL_TEST_TOKEN` header — always generates full tier, `is_test = true`

### Job Queue

After payment, a job is enqueued to BullMQ + Redis and a `report_id` (UUID) is returned immediately. The frontend subscribes to Supabase Realtime for status updates (`queued → running → complete / failed`). Progress is broadcast after each worker completes.

---

## Pipeline Architecture

```
MANUFACTURER FORM
       │
       ▼
PADDLE PAYMENT GATE
       │
       ▼
BULLMQ JOB ENQUEUED ──► report_id returned to frontend
       │
       ▼
LANGGRAPH SUPERVISOR (LangGraph StateGraph)
       │
       ├──► Worker 1: Market Demand + Pricing   (~60s)
       │         │
       ├──► Worker 2: Compliance Map            (~30s)
       │         │
       ├──► Worker 3: Buyer Discovery + Scoring (~90s)
       │         │
       ├──► Worker 4: Deep Market Research      (~120s)
       │         │
       └──► Worker 5: Report Synthesis          (~90s)
                 │
                 ▼
         Supabase (results stored)
                 │
                 ▼
         WeasyPrint (PDF generated)
                 │
                 ▼
         Supabase Storage (PDF uploaded, signed URL)
                 │
                 ▼
         Supabase Realtime ──► Frontend ("complete")
```

**Total pipeline time:** approximately 6–7 minutes for a full-tier report.

### Orchestration Layer

The pipeline is implemented as a [LangGraph](https://github.com/langchain-ai/langgraph) `StateGraph`. The shared state object (`PipelineState`) carries all worker inputs and outputs between nodes. Workers run in a fixed linear sequence: W1 → W2 → W3 → W4 → W5 → END.

Each node is a thin wrapper that calls the worker's entry-point function and writes its output back into shared state. The graph is defined in [apps/api/pipeline/graph.py](apps/api/pipeline/graph.py).

### Sector Configuration System

At the start of the pipeline, each worker loads a **sector YAML config** based on the first two digits of the HS code. These configs encode everything sector-specific (price query templates, compliance checks, buyer filters, trade fairs, working capital parameters) so the pipeline code itself is sector-agnostic.

```
HS chapter → sector config mapping:
  94 / 44        → furniture_wood.yaml
  61–63          → textiles_apparel.yaml
  07–22          → food_beverage.yaml
  72–76, 79–83   → metals_steel.yaml
  84–85          → machinery.yaml
  87             → auto_parts.yaml
```

Config files live at `apps/api/scoring/configs/<sector_name>.yaml`.

See the [Sector Configuration System](#sector-configuration-system-detail) section below for a full breakdown of what each YAML file contains and how each worker uses it.

### Observability

Every worker entry point is wrapped in a Langfuse `@observe()` decorator. This records token usage, latency, and cost per worker per report from day one. All Claude API calls in the project are auto-instrumented via `langfuse.anthropic`.

---

## Worker Reference

### Worker 1 — Market Demand + Pricing

**File:** [apps/api/workers/market_demand.py](apps/api/workers/market_demand.py)  
**Entry point:** `run_market_demand(hs_code, origin_iso2, target_iso2, unit_cost_eur)`  
**Langfuse tag:** `worker_market_demand`  
**Estimated runtime:** ~60 seconds  
**Approximate cost:** €0.15/report

#### Purpose

Answers "Does this market want my product?" and "Can I make money?" — the two highest-value questions in the report.

#### Execution Steps

| Step | Operation | Data Source |
|---|---|---|
| 1 | Load sector YAML config | Local file |
| 2 | Fetch import value, 5yr CAGR, top 5 supplying countries | UN Comtrade v2 API |
| 3 | Fetch MFN tariff and preferential tariff (WB6 → EU = 0% under CEFTA + SAA) | World Bank WITS REST API; falls back to chapter-level EU MFN table |
| 4 | Fetch Revealed Comparative Advantage score for origin × HS code | OEC REST API |
| 5 | Fetch target country GDP and Logistics Performance Index | World Bank WDI API |
| 6 | Scrape geo-targeted Google Shopping for retail price distribution (p25, median, p75) | ScraperAPI; queries from sector YAML |
| 7 | Query live competitor names and wholesale prices | Perplexity Sonar Pro (template from sector YAML) |
| 8 | Fetch 90-day FX volatility for non-EUR origin currencies | ExchangeRate-API |
| 9 | Look up road freight benchmark (origin → target route) | Supabase `freight_benchmarks` table |
| 10 | Calculate landed cost and margin (deterministic Python math — no LLM) | Internal calculation |
| 11 | Synthesise demand narrative and one-sentence verdict | Claude Sonnet 4.6 (fallback: Gemini) |

#### Landed Cost Calculation

This is the most valuable single calculation in the product. It is deterministic Python — no LLM is involved.

```python
units_per_truck = freight_low_eur / (unit_cost_eur × 0.8)  # capped at 200
freight_per_unit = freight_low_eur / units_per_truck
customs_per_unit = 280 / units_per_truck
insurance_per_unit = (unit_cost_eur × 1.1 × 0.011) / units_per_truck
dap_per_unit = unit_cost_eur + freight + customs + insurance
margin = (wholesale_mid - dap_per_unit) / wholesale_mid

verdict: viable if margin > 20%, tight if > 12%, not_viable otherwise
```

Wholesale price is derived from retail via the sector YAML `retail_to_wholesale_ratio` (e.g. 0.37 for furniture).

#### Outputs (`DemandOutput`)

```
import_value_usd, cagr_5yr, top_suppliers[]
tariff_mfn, tariff_preferential, trade_agreement
rca_score, gdp_usd, lpi_score
retail_p25_eur, retail_median_eur, retail_p75_eur
wholesale_low_eur, wholesale_high_eur
freight_low_eur, freight_high_eur, freight_mode
fx_volatility_90d
landed_cost (full breakdown)
competitor_summary
demand_narrative, one_sentence_verdict
```

Stored in the `report_demand` table in Supabase.

---

### Worker 2 — Compliance Map

**File:** [apps/api/workers/compliance.py](apps/api/workers/compliance.py)  
**Entry point:** `run_compliance(hs_code, target_iso2)`  
**Langfuse tag:** `worker_compliance`  
**Estimated runtime:** ~30 seconds  
**Approximate cost:** €0.10/report

> **Note:** As of the current codebase, Worker 2 is bypassed in the LangGraph graph (`node_w2_compliance` returns an empty `ComplianceOutput` directly). The worker implementation is complete and ready to re-enable.

#### Purpose

Answers "What do I legally need to sell there?" with 3–5 specific certifications, realistic costs, lead times, and named providers. Flags exactly one item as the critical deal-killer.

#### Execution Steps

1. **Load sector YAML** — read the `compliance_checks` list for this HS chapter (e.g. FSC CoC, EUDR, EN 1730 for furniture)
2. **ECHA REACH check** — query ECHA REST API to confirm REACH applicability for chemical-adjacent HS chapters (28–38, 64–65, 73). Falls back to regulatory default if API unreachable.
3. **EU TRACES check** — if target is an EU member state and HS chapter is 01–24 (food/agri), add a mandatory SPS certificate requirement.
4. **FDA FSVP check** — if target is US and HS chapter is 07–24, add FDA Foreign Supplier Verification Program requirement.
5. **Claude Sonnet 4.6 synthesis** — uses tool-use (forced JSON schema) to enrich all compliance items: add specific regulation citations, real provider names and contacts, validated cost ranges and lead times, and flag the single most critical item. Falls back to Gemini.
6. **Output normalisation** — ensures exactly one item has `critical=true`; corrects zero or multiple critical flags automatically.

#### Outputs (`ComplianceOutput`)

```
items[]:
  cert_id, cert_name, cert_type (mandatory|commercial_expected|recommended)
  critical (bool — exactly one per report)
  cost_low_eur, cost_high_eur
  lead_time_min, lead_time_max (weeks)
  providers[] (specific named bodies with contacts)
  note

total_cost_low_eur, total_cost_high_eur
critical_item_id
```

Stored row-per-item in the `report_compliance` table.

---

### Worker 3 — Buyer Discovery + Receptiveness Scoring

**File:** [apps/api/workers/buyers.py](apps/api/workers/buyers.py)  
**Entry point:** `run_buyers(hs_code, origin_iso2, target_iso2, manufacturer)`  
**Langfuse tag:** `worker_buyers`  
**Estimated runtime:** ~90 seconds  
**Approximate cost:** €0.08/report

#### Purpose

Answers "Who specifically should I contact right now?" — not a generic company list, but a scored shortlist where each buyer is ranked by observable signals indicating they are actively looking for a new supplier.

#### Execution Steps

1. **Apollo.io buyer discovery** — search `/v1/people/search` filtered by sector YAML `person_titles`, `company_keywords`, and `company_size_ranges` in the target country. Returns up to 25 contacts (free tier cap).
2. **Perplexity fallback** — if Apollo returns zero results, query Perplexity Sonar Pro with a sector-specific discovery prompt to find wholesalers and distributors not in commercial databases.
3. **PDL enrichment** — for each buyer record missing an email or job title, call People Data Labs `/v5/person/enrich`. Updates `enrichment_source` to `"pdl"` when data is found.
4. **Comtrade mirror data** — fetch import patterns for the target country's HS code from UN Comtrade. Determines whether the buyer's country currently imports from the manufacturer's origin, and whether that trend is growing or declining.
5. **Perplexity live signals** — for up to 15 buyers, query Perplexity Sonar Pro: "Has [company] posted procurement/sourcing jobs in the last 90 days? Any news about supplier expansion?" Returns `{job_posting: bool, sourcing_news: bool, summary: str}`.
6. **10times trade fair cross-reference** — fetch upcoming industry events from 10times API; merge with sector YAML fair list. Identifies which buyers are currently exhibiting (in market-development mode).
7. **Receptiveness scoring** — Python scoring engine assigns a 0–100 score per buyer based on five weighted signals (see below).
8. **Tier assignment and filtering** — buyers sorted by score; top-5 warm (≥70) and top-10 cold (40–69) are retained. Skip (<40) are dropped.

#### Receptiveness Scoring Engine

Defined in [apps/api/scoring/engine.py](apps/api/scoring/engine.py).

| Signal | Max Points | What it detects |
|---|---|---|
| **Import diversification** | 35 pts | Does the buyer's country import from the manufacturer's origin? No = +25 (no incumbent). Any existing supplier declining = +10. |
| **Active sourcing behaviour** | 30 pts | Perplexity: job posting found = +20; supplier expansion news = +10. |
| **Growth trajectory** | 15 pts | Company revenue trend (`growing` = +15, `flat`/unknown = +8, `declining` = 0). |
| **Trade fair activity** | 10 pts | Fuzzy match of company name against 10times exhibitor lists. |
| **Decision-maker accessibility** | 10 pts | Named contact + verified email = +10; name only = +5; neither = 0. |

**Tiers:**
- `warm` (score ≥ 70, shown as "Contact This Week")
- `cold` (score 40–69, shown as "90-Day Nurture")
- `skip` (score < 40, not shown in report)

#### Outputs (`BuyerList`)

```
warm[]:   up to 5 BuyerOutput records
cold[]:   up to 10 BuyerOutput records
total_scored: int

Per BuyerOutput:
  company_name, company_domain, city, country_iso2, buyer_type
  contact_name, contact_title, contact_email, linkedin_url
  enrichment_source (apollo|pdl|perplexity)
  receptiveness_score (0–100)
  receptiveness_signals[] (list of human-readable signal descriptions)
  tier (warm|cold)
```

Stored row-per-buyer in the `report_buyers` table with `enrichment_source` logged to Langfuse.

---

### Worker 4 — Deep Market Research

**File:** [apps/api/workers/deep_research.py](apps/api/workers/deep_research.py)  
**Entry point:** `run_deep_research(hs_code, origin_iso2, target_iso2)`  
**Langfuse tag:** `worker_deep_research`  
**Estimated runtime:** ~120 seconds  
**Approximate cost:** €0.20/report

#### Purpose

Produces the market narrative that makes the report feel intelligent rather than data-pasted. Covers distribution structure, buyer behaviour, cultural norms for this specific origin country, recent regulatory changes, seasonal patterns, and success factors for foreign entrants — all with citations.

#### Execution Steps

1. **Build research query** — structured 7-topic prompt covering distribution channels, buyer onboarding behaviour, cultural norms (origin country–specific), recent developments (2024–2025), seasonal patterns, success/failure factors, and regional buyers not in commercial databases.
2. **Perplexity Sonar Deep Research** — the primary call. `sonar-deep-research` autonomously plans its research strategy, conducts dozens of iterative web searches, and returns a cited markdown narrative. Timeout: 240 seconds.
3. **Fallback: Perplexity Sonar Pro** — if deep-research fails or times out, `sonar-pro` handles the same query with a 60-second timeout and fewer internal search iterations.
4. **Fallback: Gemini** — if both Perplexity models fail, Gemini Flash handles the query.
5. **Additional buyer extraction** — regex patterns parse company names from the narrative (GmbH, AG, Handel, Furniture, etc.) to surface up to 10 regional buyers not found by Apollo.

#### Outputs (`DeepResearchOutput`)

```
market_narrative: str  (full cited markdown narrative)
sources: list[str]    (URLs extracted from citations or response text)
additional_buyers: list[dict]  (company names extracted from narrative)
```

The `market_narrative` is included verbatim as an Appendix in full-tier reports and the first 400 characters are passed to Workers 5's synthesis prompts for context.

---

### Worker 5 — Report Synthesis

**File:** [apps/api/workers/synthesis.py](apps/api/workers/synthesis.py)  
**Entry point:** `run_synthesis(manufacturer, demand, compliance, buyer_list, deep_research, tier)`  
**Langfuse tag:** `worker_synthesis`  
**Estimated runtime:** ~90 seconds  
**Approximate cost:** €0.25/report

#### Purpose

Assembles all worker outputs into the final report. Writes three LLM-generated sections (first contact emails, 90-day action plan, risk flags) and assembles the complete markdown document.

#### Execution Steps

**Step 1 — Working capital estimate (deterministic Python)**

Calculates total capital needed before revenue arrives:

```python
goods_cost = unit_cost × typical_first_order_units  # from sector YAML
compliance_cost = compliance_output.total_cost_high_eur
sample_shipping = 800 EUR  (fixed)
buffer = goods_cost × 0.15
total_needed = sum of above
days_to_revenue = 35 (lead time) + 30–60 (payment terms)
```

**Step 2 — Section 5: First Contact Kit (Claude Sonnet 4.6)**

Writes personalised outreach emails — not templates. Uses Claude tool-use with a JSON schema to produce per-buyer emails for the top 2–3 warm contacts. Each email:
- Uses the contact's real name and company (no placeholders)
- References the manufacturer's actual product and unit cost
- Is 120–160 words
- Ends with one clear ask (call or sample request)
- Includes Day 3 and Day 7 follow-up sequences

Falls back to Gemini, then to a placeholder generator if both LLMs fail.

**Step 3 — Section 6: 90-Day Action Plan**

Currently disabled in the LangGraph node (returns empty). The full implementation is present in the worker and ready to re-enable. When active, Claude writes a week-by-week plan naming specific companies, phone numbers, and owners, with a Day 30 go/no-go checkpoint.

**Step 4 — Section 7: Risk Flags (Claude Sonnet 4.6)**

Writes 3–4 specific risk flags using Claude tool-use. Risks are specific to this manufacturer × market pair, not generic. Covers:
- Most likely compliance deal-killer
- Main competitive threat (named competitors)
- FX or working capital exposure
- One alternative market if this one fails

Falls back to Gemini, then to a placeholder generator.

**Step 5 — Report Assembly**

`_assemble_report_markdown()` combines all worker outputs into the final markdown document. Tier gates apply: cold buyer list and follow-up sequences are Full-only. Deep research narrative is appended as an Appendix for Full-tier reports.

#### Inputs

All previous worker outputs, plus the original `ManufacturerInput`:
- `DemandOutput` (from Worker 1)
- `ComplianceOutput` (from Worker 2)
- `BuyerList` (from Worker 3)
- `DeepResearchOutput` (from Worker 4)

#### Outputs (`ReportSynthesis`)

```
first_contact_email: str         (top-ranked buyer's email body)
first_contact_subject_lines: []  (subject lines per contact)
follow_up_sequence: dict         (day3, day7, day14)
risk_flags_markdown: str
working_capital: WorkingCapitalEstimate
full_report_markdown: str        (complete report)
per_buyer_emails: []             (all ranked buyer emails)
```

---

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PIPELINE STATE                               │
│  manufacturer_input ────────────────────────────────────────────►  │
│                                                                     │
│  W1 ──► demand_output ──────────────────────────────────────────►  │
│                                                                     │
│  W2 ──► compliance_output ──────────────────────────────────────►  │
│                                                                     │
│  W3 ──► buyer_list ─────────────────────────────────────────────►  │
│                                                                     │
│  W4 ──► deep_research_output ───────────────────────────────────►  │
│                                                                     │
│  W5: receives all four outputs ──► synthesis_output ─────────────  │
└─────────────────────────────────────────────────────────────────────┘

Data flows between workers:

  W1 output ─────────────────────────────────────────── to W5
    └─ demand_output (market data, prices, landed cost)

  W2 output ─────────────────────────────────────────── to W5
    └─ compliance_output (cert list, critical item, costs)

  W3 output ─────────────────────────────────────────── to W5
    └─ buyer_list (warm/cold buyers with scores + signals)

  W4 output ─────────────────────────────────────────── to W5
    └─ deep_research_output (market narrative, citations)

  W5 synthesises all four ─────────────────────────────► final report
    └─ working capital (uses W2 compliance costs + sector YAML)
    └─ Section 5 email (uses W3 warm buyers + W1 market data + W4 narrative)
    └─ Section 6 action plan (uses W2 items + W3 buyers + W4 narrative)
    └─ Section 7 risk flags (uses W1 + W2 + W3 + W4)
```

---

## Report Sections and Worker Ownership

| Section | Title | Primary Worker | Notes |
|---|---|---|---|
| 1 | Market Demand Snapshot | Worker 1 | Import value, CAGR, top suppliers, trade agreement, verdict |
| 2 | Price Reality Check | Worker 1 | Retail prices, wholesale range, full landed cost breakdown, margin verdict |
| 3 | Compliance Map | Worker 2 | Certifications, costs, lead times, named providers, critical flag |
| 4 | Buyer Shortlist | Worker 3 | Warm + cold tiers, scores, signals, contact details |
| 5 | First Contact Kit | Worker 5 | Per-buyer personalised emails, follow-up sequences |
| 6 | 90-Day Action Plan | Worker 5 | Week-by-week plan, working capital warning, go/no-go checkpoint |
| 7 | Risk Flags | Worker 5 | 3–4 specific risks for this manufacturer × market pair |
| Appendix | Market Intelligence | Worker 4 | Full deep research narrative with citations (Full tier only) |

---

## Data Storage

### Tables

| Table | Written by | Contents |
|---|---|---|
| `reports` | Orchestrator | Report metadata, status, tier, `is_test`, PDF URL |
| `report_demand` | After W1 | All market and pricing data, landed cost breakdown |
| `report_compliance` | After W2 | One row per compliance item |
| `report_buyers` | After W3 | One row per buyer with score and signals |
| `report_embeddings` | Post-synthesis | pgvector embedding for future "similar reports" feature |
| `freight_benchmarks` | Seed data | Road freight rates per origin→destination pair (validated quarterly) |

### PDF Generation

WeasyPrint converts the `full_report_markdown` to PDF. The PDF is uploaded to Supabase Storage and a 24-hour signed URL is returned to the frontend.

---

## Canonical Test Case

```bash
# Full pipeline test (no queue, no Paddle)
cd apps/api
python test_report.py --hs 940360 --origin XK --target AT --cost 200 --pdf

# Worker 1 only
python tests/test_worker1.py
```

Parameters: Kosovo → Austria, HS 940360 (wooden furniture), unit cost €200.  
This should produce a margin verdict of `viable` (~23%) with FSC Chain of Custody as the critical compliance item.

---

## LLM Fallback Chain

Each worker that calls an LLM uses the same fallback priority:

```
1. Claude Sonnet 4.6    (ANTHROPIC_API_KEY)
2. Gemini Flash         (GEMINI_API_KEY)
3. Placeholder output   (graceful degradation — report still generated)
```

Worker 4 (deep research) uses a different chain:

```
1. Perplexity Sonar Deep Research  (primary — multi-step web research, ~3 min)
2. Perplexity Sonar Pro            (faster fallback, less thorough)
3. Gemini Flash                    (final fallback)
```

The pipeline never hard-fails on an LLM error — it degrades to placeholder content and completes.

---

## Sector Configuration System (Detail)

Every report is sector-specific, but the pipeline code is not. All sector knowledge lives in YAML files that the pipeline reads at runtime. This is the mechanism that makes the system extensible: adding a new sector means adding one YAML file — no code changes required.

### How HS Codes Map to Config Files

The mapping is defined as a hardcoded dict in [apps/api/scoring/config_loader.py](apps/api/scoring/config_loader.py):

```python
HS_CHAPTER_TO_SECTOR = {
    "44": "furniture_wood",
    "94": "furniture_wood",
    "61": "textiles_apparel",
    "62": "textiles_apparel",
    "63": "textiles_apparel",
    "07": "food_beverage",  # through "22"
    ...
    "72": "metals_steel",   # through "83" (excluding 77–78)
    "84": "machinery",
    "85": "machinery",
    "87": "auto_parts",
}
```

At runtime, `load_sector_config(hs_code)` extracts the first two digits of the HS code, looks up the sector name, loads `apps/api/scoring/configs/<sector_name>.yaml`, and caches the result in memory for the duration of the process. If the HS chapter is not in the mapping, the function raises `ValueError` immediately — reports cannot be generated for unsupported sectors.

Currently supported sectors and their YAML files:

| File | Covers |
|---|---|
| `furniture_wood.yaml` | HS 44 (wood), HS 94 (furniture) |
| `textiles_apparel.yaml` | HS 61–63 (knitted, woven, textile furnishings) |
| `food_beverage.yaml` | HS 07–22 (food, drink, oils) |
| `metals_steel.yaml` | HS 72–76, 79–83 (steel, iron, non-ferrous metals, fabricated parts) |
| `machinery.yaml` | HS 84–85 (industrial and electrical machinery) |
| `auto_parts.yaml` | HS 87 (automotive components) |

### What Each YAML File Contains

Every config file has the same top-level structure. Here is what each field does and which worker consumes it:

#### `price_queries` — Worker 1

Language-specific Google Shopping search queries used by Worker 1's ScraperAPI step. Queries are chosen to match how buyers in that country search for the product at retail.

```yaml
price_queries:
  DE: ["Kfz-Ersatzteile Großhandel", "Autoteile Großhandel Deutschland"]
  AT: ["Autoteile Großhandel Österreich"]
  IT: ["ricambi auto ingrosso"]
  FR: ["pièces auto grossiste"]
```

Worker 1 reads `price_queries[target_iso2]` and passes those strings to ScraperAPI. If the target country has no entry, it falls back to the first available language. Using native-language queries is critical — searching German Google Shopping in English returns different (often wrong) price distributions.

#### `retail_to_wholesale_ratio` — Worker 1

A decimal multiplier applied to the scraped retail prices to derive the wholesale price range:

```yaml
retail_to_wholesale_ratio: 0.55   # auto_parts
retail_to_wholesale_ratio: 0.37   # furniture_wood
```

Worker 1 applies this as:
```python
wholesale_low  = retail_p25  × ratio
wholesale_high = retail_p75  × ratio
```

The ratio is sector-specific because retailer margins differ significantly (furniture ~45%, auto parts ~40%). This is the only mechanism connecting live retail price data to the landed cost calculation — getting this wrong directly affects the margin verdict.

#### `compliance_checks` — Worker 2

A list of pre-defined compliance items for this sector. Each item is a dict matching the `ComplianceItem` schema. Worker 2 loads this list as the starting point, then enriches it via Claude (which adds regulation citations, validates costs against current market rates, names specific providers, and selects the single critical item).

```yaml
compliance_checks:
  - id: ece_type_approval
    name: ECE Type Approval / e-Mark Certification
    type: mandatory
    critical: true
    cost_low_eur: 5000
    cost_high_eur: 25000
    lead_time_weeks_min: 12
    lead_time_weeks_max: 30
    providers:
      - "TÜV SÜD Auto Service GmbH: +49 89 5791 0"
      - "KBA (Federal Motor Transport Authority DE): +49 6142 403 0"
    note: "..."

  - id: iso_9001
    name: ISO 9001:2015 Quality Management System
    type: commercial_expected
    critical: false
    ...
```

The YAML items are the "seed" — Claude's job is to prune irrelevant items, enrich accurate ones, and produce the final 3–5 item list. If Claude fails, the YAML items are used directly as-is.

#### `buyer_filters` — Worker 3

Apollo.io search parameters specific to this sector. Worker 3 passes these directly to the Apollo `/v1/people/search` API:

```yaml
buyer_filters:
  person_titles:
    - "procurement"
    - "purchasing"
    - "einkauf"       # German
    - "acquisti"      # Italian
    - "achat"         # French
    - "parts manager"
    - "aftermarket"
  company_keywords:
    - "autoteile"
    - "kfz"
    - "auto parts"
    - "wholesale"
    - "distributor"
  company_size_ranges: ["11-50", "51-200", "201-500", "501-1000"]
```

Multilingual titles matter: a German procurement manager may have the title "Einkaufsleiter" — the YAML encodes the right language-specific keywords per sector. The `company_size_ranges` filter prevents returning individual retailers or mega-corporations that aren't realistic first buyers.

The Perplexity fallback discovery prompt (used when Apollo returns nothing) is also keyed by `sector_name` — it uses a sector-appropriate template to find wholesalers and distributors.

#### `trade_fairs` — Worker 3

Upcoming industry trade fairs for this sector and target region. Worker 3 uses this list as the base for trade fair cross-referencing (Signal 4 in the receptiveness scoring engine). The 10times API enriches these with exhibitor names if available.

```yaml
trade_fairs:
  - name: "Automechanika Frankfurt"
    country: DE
    city: Frankfurt
    month: 9
    url: "https://www.automechanika.messefrankfurt.com"
  - name: "Vienna Motor Show"
    country: AT
    city: Vienna
    month: 3
```

Worker 5's action plan also references the relevant fair (keyed by `target_iso2`) as the fallback recommendation if buyer outreach fails by day 45.

#### `typical_first_order_units`, `typical_compliance_cost_eur`, `sample_shipping_cost_eur` — Worker 5

These three values drive the deterministic working capital estimate in Worker 5:

```yaml
typical_first_order_units: 200        # auto_parts
typical_compliance_cost_eur: 15000    # auto_parts
sample_shipping_cost_eur: 400         # auto_parts

typical_first_order_units: 60         # furniture_wood
typical_compliance_cost_eur: 6000     # furniture_wood
sample_shipping_cost_eur: 800         # furniture_wood
```

Worker 5 calculates:
```python
goods_cost     = unit_cost_eur × typical_first_order_units
compliance     = compliance_output.total_cost_high_eur  (from Worker 2)
sample_shipping = sector_config["sample_shipping_cost_eur"]
buffer         = goods_cost × 0.15
total_needed   = goods_cost + compliance + sample_shipping + buffer
```

The plain-English working capital warning in the report ("Have at least €X liquid before you send the first email") is derived entirely from these values.

#### `competitor_query_template` — Worker 1

A Perplexity Sonar Pro query template for named competitor research. Worker 1 fills in `{target_country}` and executes it:

```yaml
competitor_query_template: >
  Who are the top 3-5 auto parts and automotive component wholesale manufacturers
  currently supplying {target_country} distributors and aftermarket importers in 2025?
  Focus on suppliers from Eastern Europe, Turkey, and the Balkans.
  For each: country of origin, approximate wholesale price range per unit,
  certifications held (ECE, ISO 9001, IATF), and which distributors they supply.
  Cite sources.
```

The resulting text becomes `competitor_summary` in the `DemandOutput` and appears in Section 2 of the report. The specificity of this template — sector vocabulary, relevant certifications, relevant origin regions — is what makes the competitor analysis useful rather than generic.

### Adding a New Sector

To support a new HS chapter:

1. Add the chapter → sector mapping in [apps/api/scoring/config_loader.py](apps/api/scoring/config_loader.py)
2. Create `apps/api/scoring/configs/<sector_name>.yaml` with all required fields
3. Run the canonical test case for a product in that chapter to verify end-to-end

No pipeline code changes are required.

---

## Hard Constraints

These constraints are enforced at the code level and must not be violated:

- **HS code is always user-provided.** No AI model maps product descriptions to HS codes.
- **SeaRates is not used.** All freight is road-only (WB6 → EU). Rates come from the manually validated `freight_benchmarks` table.
- **MOQ and payment terms are not estimated.** These come from buyer interaction; no database has this reliably.
- **Landed cost is deterministic Python math.** No LLM calculates or approximates the margin.
- **Every LLM call is wrapped in `@observe()`.** Langfuse is mandatory from the first report.
- **Internal test reports are gated by `INTERNAL_TEST_TOKEN`.** `is_test=true` is never counted in metrics.
