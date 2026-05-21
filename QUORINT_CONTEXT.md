# QUORINT — Claude Code Context File
# Version 4.0 — Built from manufacturer reality, not assumptions
# May 2026

---

## What this product actually is

A Balkan manufacturer — furniture, textiles, auto parts, food — spends years
wondering whether to export. They have a good product. They have capacity.
They have no idea where to start.

They can't afford a consultant (€3,000–€8,000, 6–8 weeks).
They don't trust generic market reports (written for someone else).
They don't have an export department.

Quorint answers the five questions every manufacturer actually asks
before committing to a new export market — in one report, for one country,
in under 5 minutes, for €29–€49.

The five questions:
1. Does this market actually want my product?
2. Can I make money after all the costs?
3. What do I legally need to sell there?
4. Who specifically should I contact — and are they actually buying right now?
5. What do I do first thing tomorrow morning?

Everything else is noise. We answer exactly these five questions.

---

## What we learned from acting as the manufacturer

Kosovo furniture maker, solid oak, 14 employees, €700k revenue.
Has been thinking about Austria for two years. Can't afford to get it wrong.

### What they actually need from a report

**Question 1 — Does this market want my product?**
Not: "The Austrian furniture market is worth €X billion."
Yes: "Austria imported €340M of wooden furniture last year, growing 2.1%/yr.
Poland supplies 44%. The mid-tier solid oak segment is underserved.
Your product has a realistic opening."

**Question 2 — Can I make money?**
Not: "Wholesale prices range from €200–€800."
Yes: "At your stated cost of €200/table, your margin after road freight
(~€2,750 per truck, ~60 tables), customs (€280), and insurance (€230) is 23%.
That is viable. Italy at 17% is too tight. Austria is your entry market."

This requires one input from the manufacturer: their unit production cost.
Everything else is calculated. This single calculation — done explicitly —
is worth the entire €49 price on its own.

**Question 3 — What do I legally need?**
Not: a 20-item generic checklist.
Yes: "For HS 940360 into Austria, you need three things:
— FSC Chain of Custody: €3,500–€6,000, 12 weeks, SGS Vienna.
  CRITICAL: Your Peja oak suppliers must be FSC forest-certified first.
  Start with them before booking the audit.
— EUDR due diligence statement: free, but requires GPS polygon data
  from your forest source. Get this from your timber supplier now.
— EN 1730 stability test: €800–€1,200, 3–4 weeks, TÜV Austria.
  Buyers will ask for this on first order."

Three items. Costs. Timelines. Who to call. One critical warning.

**Question 4 — Who specifically should I contact?**
Not: a list of 20 Austrian furniture companies.
Yes: Five companies scored on whether they are actively looking for
a new supplier RIGHT NOW — based on observable signals:
— Do they currently import from Kosovo or WB6? (No = no incumbent to beat)
— Has their import frequency from existing suppliers dropped? (Comtrade mirror)
— Did they post a purchasing or sourcing job in the last 90 days? (LinkedIn)
— Are they exhibiting at an upcoming fair? (10times)
— Is there a named purchasing contact with a verified email? (Apollo → PDL)

A buyer who shows 3+ of these signals gets a "Warm" designation.
They get the personalised email this week.

**Question 5 — What do I do tomorrow morning?**
A week-by-week 90-day plan. Not "get certified." Specific:
Week 1: Email three Warm buyers using the template below. Call your Peja
timber supplier about FSC certification — ask if they're already certified.
Week 2: Book a pre-audit call with SGS Vienna (+43 1 79567).
Week 3: Request EN 1730 test slots at TÜV Austria.
Week 6: Follow up with buyers who didn't reply. Adjust subject line.

Plus a working capital warning:
"Before starting this process, ensure you have at least €[X] liquid.
First order goods will cost €[Y]. Compliance will cost €[Z].
You will wait ~65 days from first email to first payment."

This stops manufacturers who can't fund the process from starting and failing.

### What we explicitly do NOT estimate

MOQ. Payment terms. Whether a specific buyer will like the product.
These require actual interaction. No database has this reliably.
Our job is to get the manufacturer in front of the right buyer.
The buyer tells them the rest.

---

## Report structure — seven sections

One report. One country. One manufacturer.

### Section 1: Market demand snapshot
**Purpose:** Answer "does this market want my product?"
**Data sources:** UN Comtrade (import value, CAGR, top suppliers)
                  OEC (Revealed Comparative Advantage)
                  World Bank WDI (GDP, LPI)
**Output:**
- Import value of their HS code into target country (latest year)
- 5-year trend (growing / stable / declining + CAGR)
- Top 5 supplying countries by share
- One-sentence verdict

**Example verdict:** "Austria imported €341M of wooden furniture (HS 940360)
in 2024, up 2.1%/yr. Poland (44%) leads but solid oak from emerging European
producers is a growing niche. Opportunity is real."

### Section 2: Price reality check
**Purpose:** Answer "can I make money?"
**Data sources:** Google Shopping (geo-targeted scrape via ScraperAPI)
                  Sector YAML (retail-to-wholesale ratio)
                  Freight benchmark table (Supabase, manually validated)
                  ExchangeRate-API (FX volatility if origin not EUR)
**Required manufacturer input:** Unit production cost in EUR
**Output:**
- Retail price distribution (p25, median, p75) from live market data
- Derived wholesale price range
- Explicit landed cost breakdown:
  FOB = unit_cost × (1 + target_margin_assumption)
  Freight per unit = benchmark_rate / units_per_truck
  Customs/docs per unit = 280 / units_per_truck
  Insurance = FOB × 0.011 / units_per_truck
  DAP = FOB + freight + customs + insurance
  Margin = (wholesale_mid - DAP) / wholesale_mid
- Plain-English verdict: viable / tight / not viable
- If not viable: suggest adjacent market that is

**This section earns the €49 alone. No manufacturer has ever seen
their actual margin calculated this explicitly before.**

### Section 3: Compliance map
**Purpose:** Answer "what do I legally need?"
**Data sources:** EUR-Lex (CE marking), ECHA (REACH), TRACES (food/agri),
                  Sector YAML (sector-specific requirements)
**Output:**
- 3–5 specific certifications/requirements (not a 20-item list)
- For each: mandatory or commercial, cost range (EUR), lead time (weeks),
  specific provider name and contact (not generic "contact a notified body")
- ONE item flagged CRITICAL — the most likely deal-killer if missed
- Total compliance investment estimate

### Section 4: Buyer shortlist with receptiveness scoring
**Purpose:** Answer "who specifically should I contact right now?"
**Data sources (waterfall):**
  Primary: Apollo.io (buyer contact discovery)
  Fallback: People Data Labs (enrichment for missing fields)
  Gap-fill: Perplexity Sonar (regional buyers not in databases)
  Signals: Comtrade mirror data, LinkedIn (via Perplexity), 10times API

**Receptiveness scoring (5 signals):**
  Signal 1 — Import diversification (HIGH weight)
    Does this buyer currently import from manufacturer's origin country?
    If NO → no incumbent relationship to displace. Positive.
    If their import frequency from existing suppliers has dropped → stronger signal.
    Source: UN Comtrade mirror data (who imports what from where)

  Signal 2 — Active sourcing behaviour (HIGH weight)
    Did they post a procurement/purchasing/sourcing job in last 90 days?
    Source: LinkedIn job posts via Perplexity live search
    Did their company page mention new suppliers or sourcing expansion?

  Signal 3 — Growth trajectory (MEDIUM weight)
    Is this company growing? Growing companies need more product.
    Source: Kompass revenue data or Perplexity company news

  Signal 4 — Trade fair activity (MEDIUM weight)
    Are they exhibiting at an upcoming fair in their sector?
    Exhibitors are in market-development mode, not cost-cutting mode.
    Source: 10times API exhibitor lists

  Signal 5 — Decision-maker accessibility (LOW weight)
    Is there a named purchasing contact with a verified email?
    No name = cold company-level outreach = much lower conversion.
    Source: Apollo → PDL enrichment

**Tiers:**
  Warm (score ≥70, 2+ signals): top 5 buyers, personalised email this week
  Cold (score 40–69): next 10, 90-day nurture
  Skip (<40): not shown

**Per-buyer output:**
  Company, city, type, contact name, title, email, LinkedIn
  Receptiveness score + specific signal evidence
  Enrichment source (apollo / pdl / perplexity)

### Section 5: First contact kit
**Purpose:** Answer "what do I send tomorrow morning?"
**Output:**
- Pre-written email in target country language (DE/IT/FR/EN)
  Not a template. Uses actual manufacturer product, origin, certifications.
  References buyer's company type and product range where known.
- Three subject line variants
- Follow-up sequence: day 3, day 7, day 14 (what to say at each stage)
- Two sentences on how to position origin as an asset
  ("Kosovo oak — proximity to EU, lower cost than Austrian domestic,
  FSC-certifiable from Peja forests — positions you as a credible
  European supplier, not a distant importer")
- What to attach: certifications currently held, product photos, spec sheet

### Section 6: 90-day action plan
**Purpose:** Turn the report into a sequence of specific acts
**Output (week-by-week):**
  Each item: owner (who does it), task (specific, not vague),
  definition of done, cash timing note

**Working capital estimate:**
  goods_cost = unit_cost × typical_first_order_units (from sector YAML)
  compliance_cost = total from Section 3
  sample_shipping = 800 EUR (fixed)
  buffer = goods_cost × 0.15
  total_needed = sum of above
  days_to_revenue = 35 (lead time) + 30–60 (buyer payment terms)
  Output: "Have at least €[X] liquid before you send the first email.
  First revenue arrives approximately [N] days after outreach begins."

**Go/no-go checkpoint at day 30:**
  If no buyer reply by day 30: switch from Warm list to Cold list.
  Adjust subject line. If still no response by day 45:
  consider attending [specific trade fair] in [month] to get in-person meetings.

### Section 7: Risk flags
**Purpose:** What could kill this — specific to this manufacturer × this market
**Output (3–4 items, not a generic list):**
  The one compliance issue most likely to stop the first deal
  The one competitive threat to watch (specific, e.g., "Polish mass-market
  producers will undercut you on price — compete on FSC and origin story")
  FX exposure if origin country is not EUR (ExchangeRate-API 90-day range)
  One "what if this fails" alternative market (two sentences only)

---

## AI architecture — task-matched models

**Philosophy:** No single model wins everything.
Use the best tool for each specific task. Cheapest model that does the job.

### Orchestration layer
**Framework:** LangGraph Supervisor pattern
**Model:** Claude Sonnet 4.6
**Why:** Best for expert-level agent workflows, long-context reasoning,
and sustained analytical depth across a complex multi-step pipeline.
The supervisor holds state, delegates to workers, handles retries.

### Worker 1 — Market demand + pricing (Claude Sonnet 4.6)
**Tasks:**
- UN Comtrade API: import value, CAGR, top suppliers for HS × target country
- World Bank WITS API: tariff rate (MFN + preferential) for origin → target
- OEC API: Revealed Comparative Advantage for origin × HS code
- World Bank WDI: GDP, LPI for target country
- ScraperAPI Google Shopping: retail price distribution (geo-targeted)
  Uses queries from sector YAML config (e.g., "Eichenholz Esstisch massiv" for DE)
- Perplexity Sonar Pro: named competitor query
  ("Top 3–5 [product] wholesale suppliers in [country] 2025, with price range")
- ExchangeRate-API: FX 90-day volatility (if origin ≠ EUR)
- Freight benchmark lookup: Supabase query by (origin_iso2, target_iso2)
- Landed cost calculation: deterministic Python math (no LLM)
**Why Claude Sonnet 4.6:** Superior structured reasoning over heterogeneous
data sources. 1M token context. Prompt caching cuts cost ~90% on repeat runs.
**Langfuse:** @observe(name="worker_market_demand")

### Worker 2 — Compliance (Claude Sonnet 4.6 with structured output)
**Tasks:**
- Load sector YAML to identify relevant certification categories
- EUR-Lex: CE marking applicability for HS chapter
- ECHA REST API: REACH requirements (chemicals-adjacent products)
- EU TRACES: SPS certificates (food/agri HS chapters 01–24 only)
- FDA FSVP database: US market only
- Synthesise into structured JSON with cost/time/provider per item
- Flag the single most critical compliance risk
**Why Claude Sonnet 4.6:** Reliable structured JSON output with deep
regulatory reasoning. GPT-5 was previously used here but Claude Sonnet 4.6
now matches on JSON reliability while being faster and cheaper on caching.
**Langfuse:** @observe(name="worker_compliance")

### Worker 3 — Buyer discovery + receptiveness scoring (Claude Sonnet 4.6)
**Tasks:**
- Apollo.io API: buyer discovery filtered by country, industry, company size
- PDL API: enrichment for records missing email or title
- Comtrade mirror data: import pattern per buyer (who they currently buy from)
- Perplexity Sonar Pro: live signals per buyer
  ("Has [company] posted sourcing or procurement jobs in last 90 days?
   Any news about [company] expanding supplier base?")
- 10times API: cross-reference buyer against upcoming fair exhibitor lists
- Scoring engine (Python): compute receptiveness score per buyer, assign tier
**Why Claude Sonnet 4.6:** The scoring requires multi-signal reasoning —
"this buyer shows three signals, here is why the score is 74, not 82."
This is synthesis, not retrieval.
**Langfuse:** @observe(name="worker_buyers") — log enrichment_source per record

### Worker 4 — Deep market research (Perplexity Sonar Deep Research)
**Tasks:**
- Autonomous multi-step research on:
  Distribution structure in target country for this product category
  Cultural/business norms for new foreign suppliers
  Recent sector developments (regulation changes, demand shifts)
  Seasonal buying patterns
  What differentiates successful foreign entrants
  Specific named wholesalers/distributors not captured by Apollo
**Model:** perplexity/sonar-deep-research
**Why:** Only provider with a true Deep Research API. Autonomously plans
research strategy, conducts dozens of iterative web searches, returns
cited, structured report. ~3 minutes. $2/$8 per MTok.
This worker produces the market narrative that makes the report feel
intelligent, not data-pasted.
**Langfuse:** @observe(name="worker_deep_research")

### Worker 5 — Report synthesis (Claude Sonnet 4.6)
**Tasks:**
- Receive all worker outputs + full manufacturer profile
- Compute working capital estimate (deterministic Python)
- Write Section 5 (first contact email in target language — NOT a template)
- Write Section 6 (90-day plan, week-by-week, specific)
- Write Section 7 (risk flags, specific to this pair)
- Assemble all sections into final report markdown
**Why Claude Sonnet 4.6:** Best prose quality for long-form structured output.
The email must read like it was written by someone who knows the manufacturer's
business — Claude achieves this; generic models produce templates.
**Langfuse:** @observe(name="worker_synthesis")

### Cost per report
Worker 1 (market + pricing): ~€0.15 (heavy caching)
Worker 2 (compliance): ~€0.10
Worker 3 (buyers): ~€0.08 (Apollo free tier, PDL free tier)
Worker 4 (deep research): ~€0.20 (Sonar Deep Research)
Worker 5 (synthesis): ~€0.25
Total: ~€0.78/report
At €49: 98.4% gross margin on AI cost alone.

---

## Data sources

### Always used
| Source | What it provides | Access |
|---|---|---|
| UN Comtrade+ | Import flows by HS code and country | REST + SDK, free (500 calls/day) |
| World Bank WITS | Tariff rates MFN + preferential | SDMX REST, free |
| OEC | Revealed Comparative Advantage | REST, free |
| World Bank WDI | GDP, LPI, trade/GDP | REST, free |
| ScraperAPI | Google Shopping geo-targeted prices | REST, free (1k/month) |
| Perplexity Sonar Pro | Competitor + buyer live signals | API, ~$5/1k calls |
| Perplexity Sonar Deep Research | Full market narrative | API, $2/$8 per MTok |
| Apollo.io | Buyer contact discovery | API, free (10k credits/month) |
| People Data Labs | Contact enrichment fallback | API, free (100 records/month) |
| 10times | Trade fair exhibitor data | API, free tier |
| ExchangeRate-API | FX rates + 90-day range | REST, free (1,500/month) |
| Freight benchmarks | Road rates WB6→EU (manually validated) | Supabase lookup |

### Conditional
| Source | When |
|---|---|
| ECHA REST | HS chapters with chemical relevance (28–38, 64–65, 73) |
| EUR-Lex | EU target countries (CE marking) |
| EU TRACES | Food/agri (HS 01–24) |
| FDA FSVP | US target only |
| Coface risk grades | Cached quarterly in Supabase for all reports |

### Deliberately excluded
| Source | Why |
|---|---|
| SeaRates | Ocean freight only. WB6→EU is road. Returns inaccurate/no data. |
| MOQ databases | Data doesn't exist reliably. Must come from buyer interaction. |
| Payment terms APIs | Negotiated and confidential. Same reason. |

---

## Freight benchmark table

Road freight only. Full truck (FTL) rates.
Updated quarterly by calling 2–3 freight forwarders per origin country.

```sql
CREATE TABLE freight_benchmarks (
  origin_iso2     CHAR(2)  NOT NULL,
  dest_iso2       CHAR(2)  NOT NULL,
  rate_low_eur    INTEGER  NOT NULL,
  rate_high_eur   INTEGER  NOT NULL,
  transit_days_min INTEGER NOT NULL,
  transit_days_max INTEGER NOT NULL,
  mode            TEXT     NOT NULL,  -- 'road' | 'road_ferry'
  validated_date  DATE     NOT NULL,
  notes           TEXT,
  PRIMARY KEY (origin_iso2, dest_iso2)
);

-- Seed data (validate quarterly with local forwarders)
INSERT INTO freight_benchmarks VALUES
('XK','AT', 2400,3100, 4,6, 'road',      '2026-05-01', NULL),
('XK','DE', 2800,3600, 5,7, 'road',      '2026-05-01', NULL),
('XK','IT', 2600,3400, 3,5, 'road',      '2026-05-01', 'Via Bar ferry or Slovenia road'),
('XK','FR', 3200,4200, 6,8, 'road',      '2026-05-01', NULL),
('XK','NL', 3000,3900, 6,8, 'road',      '2026-05-01', NULL),
('XK','CH', 3000,3900, 5,7, 'road',      '2026-05-01', NULL),
('AL','IT',  800,1200, 3,5, 'road_ferry','2026-05-01', 'Durrës→Bari/Ancona ferry + road'),
('AL','DE', 2600,3400, 5,7, 'road',      '2026-05-01', NULL),
('AL','AT', 2200,2900, 4,6, 'road',      '2026-05-01', NULL),
('RS','DE', 2200,3000, 4,6, 'road',      '2026-05-01', NULL),
('RS','AT', 1800,2400, 3,5, 'road',      '2026-05-01', NULL),
('RS','IT', 2000,2800, 3,5, 'road',      '2026-05-01', NULL),
('BA','AT', 1600,2200, 4,5, 'road',      '2026-05-01', NULL),
('BA','DE', 2000,2800, 5,6, 'road',      '2026-05-01', NULL),
('MK','DE', 2600,3400, 5,7, 'road',      '2026-05-01', NULL),
('MK','IT', 2200,3000, 4,6, 'road',      '2026-05-01', NULL),
('ME','IT',  900,1300, 3,5, 'road_ferry','2026-05-01', 'Bar→Bari ferry + road');
```

---

## Sector YAML config system

One YAML file per sector. Loaded at pipeline start based on first 2 digits of HS code.
Encodes everything sector-specific so the pipeline code never changes.

Location: `apps/api/scoring/configs/[sector_name].yaml`

### Mapping: HS chapter → sector config
```python
HS_CHAPTER_TO_SECTOR = {
    "44": "furniture_wood",
    "94": "furniture_wood",
    "61": "textiles_apparel",
    "62": "textiles_apparel",
    "63": "textiles_apparel",
    "07": "food_beverage", "08": "food_beverage",
    "09": "food_beverage", "15": "food_beverage",
    "16": "food_beverage", "17": "food_beverage",
    "18": "food_beverage", "19": "food_beverage",
    "20": "food_beverage", "21": "food_beverage",
    "22": "food_beverage",
    "72": "metals_steel",  "73": "metals_steel",
    "84": "machinery",     "85": "machinery",
    "87": "auto_parts",
}
```

### Example: furniture_wood.yaml
```yaml
sector_name: furniture_wood
hs_chapters: ["44", "94"]

# Google Shopping queries per target country language
# Used by Worker 1 to scrape retail prices
price_queries:
  DE: ["Eichenholz Esstisch massiv", "Massivholz Esstisch Eiche", "Massivholzmöbel Esstisch"]
  AT: ["Eichenholz Esstisch massiv", "Massivholzmöbel Österreich"]
  IT: ["tavolo rovere massello", "tavolo legno massello rovere"]
  FR: ["table chêne massif", "table bois massif"]
  NL: ["eiken tafel massief", "massief houten tafel"]
  CH: ["Eichenholz Esstisch massiv", "Massivholz Tisch Schweiz"]

# How to derive wholesale from retail
retail_to_wholesale_ratio: 0.37
typical_retailer_margin: 0.45

# Compliance items to check (Worker 2 loads these for each report)
compliance_checks:
  - id: fsc_coc
    name: FSC Chain of Custody
    type: commercial_expected
    critical: true
    cost_low_eur: 3500
    cost_high_eur: 6500
    lead_time_weeks_min: 10
    lead_time_weeks_max: 16
    providers: ["SGS Vienna: +43 1 79567", "Bureau Veritas Austria", "BVQI"]
    note: "Forest source must be FSC-certified before audit. Check your timber supplier first."

  - id: eudr_dds
    name: EU Deforestation Regulation (EUDR) Due Diligence Statement
    type: mandatory
    critical: true
    cost_low_eur: 0
    cost_high_eur: 500
    lead_time_weeks_min: 2
    lead_time_weeks_max: 4
    providers: ["Self-prepared via EU TRACES portal"]
    note: "Requires GPS polygon data for forest origin. Obtain from your timber supplier."

  - id: en_1730
    name: EN 1730 Table Stability Test
    type: commercial_expected
    critical: false
    cost_low_eur: 800
    cost_high_eur: 1400
    lead_time_weeks_min: 3
    lead_time_weeks_max: 5
    providers: ["TÜV Austria: +43 1 514 07", "SGS Vienna", "Intertek Vienna"]
    note: "Most EU wholesale buyers require this before first order."

  - id: reach_svhc
    name: REACH SVHC Declaration
    type: mandatory
    critical: false
    cost_low_eur: 0
    cost_high_eur: 200
    lead_time_weeks_min: 1
    lead_time_weeks_max: 2
    providers: ["Self-prepared or via chemical compliance consultant"]

  - id: formaldehyde_e1
    name: Formaldehyde E1 Class Compliance (wood panels)
    type: mandatory
    critical: false
    cost_low_eur: 200
    cost_high_eur: 600
    lead_time_weeks_min: 2
    lead_time_weeks_max: 4
    providers: ["Any EU-accredited wood testing lab"]

# Apollo buyer filter parameters for this sector
buyer_filters:
  person_titles:
    - "procurement"
    - "purchasing"
    - "einkauf"      # German
    - "acquisti"     # Italian
    - "achat"        # French
    - "buying"
    - "supply chain"
  company_keywords:
    - "möbel"        # German
    - "furniture"
    - "holz"         # German
    - "legno"        # Italian
    - "bois"         # French
    - "ameublement"
    - "interior"
    - "home decor"
    - "wholesale"
    - "distributor"
    - "importer"
  company_size_ranges: ["11-50", "51-200", "201-500"]

# Key trade fairs (used in receptiveness scoring + action plan)
trade_fairs:
  - name: "imm cologne"
    country: DE
    city: Cologne
    month: 1
    url: "https://www.imm-cologne.de"
  - name: "Salone del Mobile"
    country: IT
    city: Milan
    month: 4
    url: "https://www.salonemilano.it"
  - name: "MÖFA Salzburg"
    country: AT
    city: Salzburg
    month: 9
  - name: "Maison & Objet"
    country: FR
    city: Paris
    month: 1

# Working capital estimates for action plan
typical_first_order_units: 60
typical_compliance_cost_eur: 6000
sample_shipping_cost_eur: 800

# Competitor Perplexity query template
competitor_query_template: >
  Who are the top 3-5 solid oak furniture wholesale suppliers currently
  selling to {target_country} distributors and wholesalers in 2025?
  For each: country of origin, approximate wholesale price range per dining table,
  certifications held, and which Austrian/German distributors they work with.
  Cite sources.
```

Sector configs to build at launch:
- furniture_wood.yaml (above — most important for WB6)
- textiles_apparel.yaml
- food_beverage.yaml
- auto_parts.yaml

---

## Pipeline architecture

```
MANUFACTURER FILLS ONBOARDING FORM
─────────────────────────────────────────
Fields:
  hs_code:        string (4 or 6 digits — user confirms, no AI mapping)
  origin_iso2:    string (XK / AL / RS / BA / MK / ME)
  target_iso2:    string (single country — one report per purchase)
  unit_cost_eur:  number (e.g. 200)
  certifications: string[] (checkboxes: FSC, CE, ISO9001, etc.)
  capacity_units: string (range: "<100/mo" / "100-500/mo" / "500+/mo")
  tier:           "starter" | "full"

PADDLE PAYMENT GATE
─────────────────────────────────────────
  €29 Starter: Sections 1, 3, 4 (top 5 buyers, no scores), 6 (basic)
  €49 Full: All 7 sections, receptiveness scores + signals, localised email
  Internal test: bypass gate with INTERNAL_TEST_TOKEN header

JOB ENQUEUED TO BULLMQ + REDIS
─────────────────────────────────────────
  Returns report_id immediately.
  Frontend subscribes to Supabase Realtime for status updates.
  User sees live progress: "Worker 1/5 complete ✓"

LANGGRAPH SUPERVISOR (Claude Sonnet 4.6)
─────────────────────────────────────────
  Receives: full job payload
  Coordinates: 5 workers in sequence
  Manages: shared state, retries, fallbacks
  Writes: intermediate results to Supabase after each worker

  WORKER 1 — Market demand + pricing (~60s)
  ├─ Comtrade API → import_value, cagr, top_suppliers
  ├─ WITS API → tariff_mfn, tariff_preferential, trade_agreement
  ├─ OEC API → rca_score
  ├─ WDI API → gdp_usd, lpi_score
  ├─ ScraperAPI Google Shopping → price_p25, price_median, price_p75
  │   (uses sector YAML query templates, geo-targeted to target_iso2)
  ├─ Perplexity Sonar Pro → competitor_narrative (named competitors + prices)
  ├─ ExchangeRate-API → fx_volatility_90d (if origin_iso2 not in EUR zone)
  ├─ Supabase freight lookup → freight_rate_low, freight_rate_high
  └─ Python calculation → dap_per_unit, margin, margin_verdict

  WORKER 2 — Compliance (~30s)
  ├─ Load sector YAML → compliance_check_list
  ├─ EUR-Lex → ce_marking_applies (boolean)
  ├─ ECHA REST → reach_applies (boolean)
  ├─ TRACES → sps_required (food/agri only)
  └─ Claude Sonnet 4.6 → compliance_checklist JSON
      (schema-enforced: cert_name, type, critical, cost, lead_time, providers, note)

  WORKER 3 — Buyers + receptiveness (~90s)
  ├─ Apollo.io → raw_buyer_list (filtered by sector YAML params)
  ├─ PDL → enrich records where email or title is missing
  ├─ Comtrade mirror → import_pattern per buyer
  │   (does this company import from manufacturer's origin region?)
  ├─ Perplexity Sonar Pro → live signals per buyer (job posts, news)
  ├─ 10times API → upcoming_fairs cross-referenced with buyer list
  └─ Python scoring engine → receptiveness_score, tier per buyer

  WORKER 4 — Deep research (~120s)
  └─ Perplexity Sonar Deep Research
      Query: structured prompt about target market, distribution channels,
      buyer behaviour, cultural norms, sector trends, successful entrant
      characteristics, and any named buyers not found in databases.
      Returns: cited markdown narrative

  WORKER 5 — Report synthesis (~90s)
  ├─ Input: all worker outputs + manufacturer profile
  ├─ Python → working_capital_estimate
  └─ Claude Sonnet 4.6
      Writes: Section 5 email (in target language, NOT a template)
      Writes: Section 6 action plan (week-by-week, specific tasks)
      Writes: Section 7 risk flags (specific to this pair)
      Assembles: complete report markdown

STORE RESULTS IN SUPABASE
─────────────────────────────────────────
  Tables: reports, report_demand, report_compliance,
          report_buyers, report_embeddings

SUPABASE REALTIME → FRONTEND
  Report status: "complete"
  User sees full report in dashboard

WEASYPRINT → PDF
  Generated from report markdown
  Uploaded to Supabase Storage
  Signed URL (24hr expiry) shown in dashboard
```

---

## Database schema

```sql
-- Core tables

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
  target_iso2     CHAR(2)     NOT NULL,  -- one country per report
  unit_cost_eur   NUMERIC(10,2),         -- enables margin calculation
  tier            TEXT        NOT NULL CHECK (tier IN ('starter','full')),
  status          TEXT        NOT NULL DEFAULT 'queued'
                  CHECK (status IN ('queued','running','complete','failed')),
  is_test         BOOLEAN     NOT NULL DEFAULT false,
  paddle_transaction_id TEXT,
  pdf_url         TEXT,
  error_message   TEXT,
  created_at      TIMESTAMPTZ DEFAULT now(),
  completed_at    TIMESTAMPTZ
);

CREATE TABLE report_demand (
  report_id           UUID PRIMARY KEY REFERENCES reports(id),
  import_value_usd    BIGINT,
  cagr_5yr            NUMERIC(6,4),
  top_suppliers       JSONB,   -- [{country, share, trend}]
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
  cert_id         TEXT,   -- e.g. 'fsc_coc'
  cert_name       TEXT,
  cert_type       TEXT CHECK (cert_type IN ('mandatory','commercial_expected','recommended')),
  critical        BOOLEAN DEFAULT false,
  cost_low_eur    INTEGER,
  cost_high_eur   INTEGER,
  lead_time_min   INTEGER,  -- weeks
  lead_time_max   INTEGER,  -- weeks
  providers       TEXT[],
  note            TEXT
);

CREATE TABLE report_buyers (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id            UUID REFERENCES reports(id),
  company_name         TEXT,
  company_domain       TEXT,
  city                 TEXT,
  country_iso2         CHAR(2),
  buyer_type           TEXT,
  contact_name         TEXT,
  contact_title        TEXT,
  contact_email        TEXT,
  linkedin_url         TEXT,
  enrichment_source    TEXT CHECK (enrichment_source IN ('apollo','pdl','perplexity')),
  receptiveness_score  INTEGER CHECK (receptiveness_score BETWEEN 0 AND 100),
  receptiveness_signals JSONB,  -- string[] of signal descriptions
  tier                 TEXT CHECK (tier IN ('warm','cold','skip')),
  created_at           TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE report_embeddings (
  report_id  UUID PRIMARY KEY REFERENCES reports(id),
  embedding  vector(1536)   -- for future "similar reports" feature
);

CREATE TABLE retention_triggers (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id    UUID REFERENCES reports(id),
  trigger_type TEXT CHECK (trigger_type IN ('tariff_change','new_buyer','day30')),
  fired_at     TIMESTAMPTZ DEFAULT now(),
  email_sent   BOOLEAN DEFAULT false,
  opened       BOOLEAN DEFAULT false
);
```

---

## Pricing and tiers

| Tier | Price | Contents |
|---|---|---|
| Starter | €29 | Sections 1, 3, 5 buyers (no score detail), 6 (basic) |
| Full | €49 | All 7 sections + buyer scores + signals + localised email |
| Copilot | €299/month | Monthly refresh + tariff alerts + new buyer signals |

Use Paddle Price IDs in env vars — never hardcode amounts.
Paddle handles EU VAT (OSS) automatically.

### Internal test mode
Endpoint: `POST /api/reports/test`
Header: `Authorization: Bearer $INTERNAL_TEST_TOKEN`
Always generates full tier. `is_test = true`. Never counted in metrics.

CLI tool `apps/api/test_report.py`:
```bash
python test_report.py --hs 940360 --origin XK --target AT --cost 200 --pdf
python test_report.py --hs 620520 --origin AL --target IT --cost 15 --pdf
python test_report.py --hs 870899 --origin RS --target DE --cost 85 --pdf
python test_report.py --hs 150910 --origin MK --target DE --cost 3.50 --pdf
```

QA criterion before first customer: "Would I pay €49 for this report?"

---

## Retention mechanism (three cron-based triggers)

### Trigger 1 — Tariff change alert (weekly)
Check WITS for tariff change on manufacturer's HS × target country.
If changed: email "Your Austria tariff position changed.
Log in to see the updated margin — or upgrade to Copilot for
automatic monthly tracking."
**Why it works:** Genuine utility, fires rarely, maximally relevant when it does.

### Trigger 2 — New buyer signal (monthly)
Perplexity search for new importers/distributors in target country
matching manufacturer's HS category.
If found: email "A new furniture distributor opened in Vienna.
We've added them to your buyer list — log in to see their contact."
**Why it works:** Creates urgency, demonstrates ongoing value.

### Trigger 3 — Day 30 re-engagement (once per report)
30 days after delivery: "It's been 30 days. Have you sent the first email?
Click here — we'll pre-fill the template with your product details."
**Why it works:** 30 days is exactly when manufacturers stall. Practical nudge.

---

## Partner strategy (not built at launch, pursued in parallel)

Three partner types that provide the human interaction layer Quorint can't automate
(buyer MOQ, payment terms, relationship introduction):

**1. Export promotion agencies** (KIESA Kosovo, AIDA Albania, RAS Serbia)
Already have buyer relationships in EU markets.
Quorint identifies which of their manufacturers best fit which buyers.
Agency does warm introduction. Pitch: "Make your matchmaking data-backed."

**2. Enterprise Europe Network (EEN)**
Runs buyer-supplier matchmaking in 60+ countries, currently manually.
Quorint's receptiveness score makes their matching 10× more accurate.
Pitch: "Give your coordinators a compatibility score before every introduction."

**3. Sector associations in target markets**
VÖM (Austrian furniture), FederlegnoArredo (Italy)
They represent the buyers. They want their members to find new suppliers.
Pitch: "We notify you when a Balkan FSC-certified manufacturer matches your
members' product range."

---

## Tech stack

```
Frontend:    Next.js 15 + TypeScript + Tailwind + shadcn/ui — Vercel
Backend:     FastAPI + Python 3.12 + LangGraph — Railway
Queue:       BullMQ + Redis — Railway
Database:    Supabase (Postgres 16 + pgvector + auth + realtime + storage)
PDF:         WeasyPrint (Python)
Payments:    Paddle (Checkout + Billing)
Email:       Resend (retention triggers)
Observability: Langfuse (mandatory from day 1)
Monitoring:  Sentry + PostHog
```

---

## Environment variables

```bash
# AI models
ANTHROPIC_API_KEY=           # All Claude workers
PERPLEXITY_API_KEY=          # Workers 3, 4

# Data
SCRAPERAPI_KEY=              # Google Shopping (free: 1k/month)
APOLLO_API_KEY=              # Buyer discovery (free: 10k credits/month)
PDL_API_KEY=                 # Enrichment fallback (free: 100 records/month)
EXCHANGERATE_API_KEY=        # FX data (free: 1,500/month)
TENTIMES_API_KEY=            # Trade fair data (free tier)

# Observability
LANGFUSE_SECRET_KEY=         # sk-lf-...
LANGFUSE_PUBLIC_KEY=         # pk-lf-...
LANGFUSE_HOST=               # https://cloud.langfuse.com

# Infrastructure
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
REDIS_URL=

# Payments (Paddle)
PADDLE_API_KEY=                       # server-side API key
PADDLE_NOTIFICATION_WEBHOOK_SECRET=   # from Paddle dashboard → Notifications
PADDLE_PRICE_ID_STARTER=              # pri_xxx for €29 one-time
PADDLE_PRICE_ID_FULL=                 # pri_xxx for €49 one-time
PADDLE_PRICE_ID_COPILOT=              # pri_xxx for €299/month subscription
NEXT_PUBLIC_PADDLE_CLIENT_TOKEN=      # client-side token (test_ prefix in sandbox)
NEXT_PUBLIC_PADDLE_ENV=               # "sandbox" or "production"

# Internal test
INTERNAL_TEST_TOKEN=         # Random string, never expose to frontend

# Email
RESEND_API_KEY=

# App
NEXT_PUBLIC_APP_URL=
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

---

## Monthly cost at Stage 0 (0–50 reports)

| Service | Monthly cost | Notes |
|---|---|---|
| Vercel | €0 | Free tier |
| Railway | €0 | Free tier |
| Supabase | €0 | Free tier |
| Anthropic | ~€18 | Workers 1,2,3,5 + Supervisor (heavy caching) |
| Perplexity | ~€12 | Workers 3,4 combined |
| All data APIs | €0 | Free tiers sufficient for 50 reports |
| Langfuse | €0 | Free cloud tier |
| Resend | €0 | Free 100 emails/month |
| **Total** | **~€30/month** | |

Break-even: 1 report at €29. 50 reports/month = ~€2,000 revenue, €30 cost.

---

## Langfuse — mandatory from day 1

Install: `pip install langfuse`

```python
from langfuse import observe
from langfuse.anthropic import anthropic  # auto-instruments all Anthropic calls

@observe(name="worker_market_demand", tags=["worker-1"])
async def run_market_demand(hs_code, origin, target, unit_cost, sector_config):
    ...

@observe(name="worker_compliance", tags=["worker-2"])
async def run_compliance(hs_code, target, sector_config):
    ...

@observe(name="worker_buyers", tags=["worker-3"])
async def run_buyers(hs_code, target, sector_config):
    # log enrichment_source per buyer record in Langfuse metadata
    ...

@observe(name="worker_deep_research", tags=["worker-4"])
async def run_deep_research(product_desc, target, sector):
    ...

@observe(name="worker_synthesis", tags=["worker-5"])
async def run_synthesis(all_outputs, manufacturer_profile, tier):
    ...
```

What Langfuse gives us from day 1:
— Real cost per report broken down by worker
— Which prompts produce the best buyer scores
— Where the pipeline fails and why
— Which manufacturers generate expensive reports

---

## Claude Code prompt — first session

```
Read QUORINT_CONTEXT.md completely before writing any code.

Build in this order:

STEP 1 — Project scaffold
Create the monorepo: apps/web (Next.js 15), apps/api (FastAPI),
packages/shared (TypeScript types). All folders and placeholder files.
Python files: one-line docstring. TypeScript: one-line comment.

STEP 2 — Database
supabase/migrations/001_initial.sql
Implement the complete schema from the context file.
Seed the freight_benchmarks table with all 17 routes.

STEP 3 — Python environment
apps/api/pyproject.toml with all dependencies:
fastapi, uvicorn, langchain, langgraph, langfuse, anthropic,
httpx, pydantic, supabase, python-dotenv, weasyprint,
comtradeapicall, world_trade_data, redis, pyyaml, pandas,
rich, resend
apps/api/.env.example with all variables from the context file.

STEP 4 — Sector config
apps/api/scoring/configs/furniture_wood.yaml
Implement exactly as specified in the context file.

STEP 5 — Worker 1 (market demand + pricing)
apps/api/workers/market_demand.py
Implement all data fetching steps in order:
  1. Comtrade API (import value, CAGR, top suppliers for HS × target)
  2. WITS API (tariff rate origin → target at HS6)
  3. OEC API (RCA score for origin × HS)
  4. WDI API (GDP, LPI for target country)
  5. ScraperAPI Google Shopping (geo-targeted, queries from sector YAML)
  6. Perplexity Sonar Pro (competitor query from sector YAML template)
  7. ExchangeRate-API (FX 90-day range if origin not in EUR zone)
  8. Supabase freight lookup (by origin_iso2, target_iso2)
  9. Python landed cost calculation (deterministic math, exact formula from context)
  10. Claude Sonnet 4.6 synthesis call (demand narrative + market verdict)
Wrap in @observe(name="worker_market_demand") Langfuse decorator.
Output: DemandOutput Pydantic model matching report_demand table schema.

STEP 6 — CLI test tool
apps/api/test_report.py
Flags: --hs, --origin, --target, --cost, --pdf, --verbose, --tier
Calls Worker 1 directly (synchronous, no queue for testing).
Prints structured output using rich library.

STEP 7 — Worker 1 test script
apps/api/tests/test_worker1.py
Calls market_demand with:
  hs_code="940360", origin="XK", target="AT", unit_cost=200.0
Prints full output as formatted JSON.
This is the first thing to run to verify all APIs work.

Rules:
- Use real APIs throughout. os.getenv() with # TODO: add to .env for missing keys.
- No mocks.
- No clarifying questions. Make decisions.
- The canonical test case throughout: XK → AT, HS 940360, cost €200.
```
