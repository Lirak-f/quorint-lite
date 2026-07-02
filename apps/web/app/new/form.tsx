"use client";

import { useState } from "react";
import { toast } from "sonner";
import Link from "next/link";
import { cn, COUNTRY_NAMES, ORIGIN_COUNTRIES } from "@/lib/utils";
import { analytics } from "@/lib/analytics";
import { usePaddle } from "@/components/paddle-provider";

type Step = 1 | 2 | 3 | 4;
type LeadCount = 10 | 20 | 30;
type ReportTier = "starter" | "full";

const LEAD_TIERS: {
  leads: LeadCount;
  tier: ReportTier;
  price: number;
  perLead: number;
  best?: true;
}[] = [
  { leads: 10, tier: "starter", price: 29, perLead: 2.9 },
  { leads: 20, tier: "full", price: 49, perLead: 2.45, best: true },
  { leads: 30, tier: "full", price: 49, perLead: 1.63 },
];

const SUPPORTED_TARGET_ISO2 = ["AT", "DE", "IT", "FR", "NL", "CH", "SE"] as const;

const TARGET_COUNTRIES = SUPPORTED_TARGET_ISO2.map((iso2) => ({
  iso2,
  name: COUNTRY_NAMES[iso2] ?? iso2,
}));


function parseApiError(payload: { error?: unknown; detail?: unknown }): string {
  if (typeof payload.error === "string") return payload.error;
  const detail = payload.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: string }).msg);
        }
        return String(item);
      })
      .join("; ");
  }
  return "Could not create checkout session. Please try again.";
}

const FLAG_STYLES: Record<string, React.CSSProperties> = {
  DE: { background: "linear-gradient(180deg,#000 0 33%,#DD0000 33% 66%,#FFCC00 66%)" },
  AT: { background: "linear-gradient(180deg,#ED2939 0 33%,#fff 33% 66%,#ED2939 66%)" },
  IT: { background: "linear-gradient(90deg,#009246 0 33%,#fff 33% 66%,#CE2B37 66%)" },
  FR: { background: "linear-gradient(90deg,#0055A4 0 33%,#fff 33% 66%,#EF4135 66%)" },
  CH: { background: "#DA291C" },
  NL: { background: "linear-gradient(180deg,#AE1C28 0 33%,#fff 33% 66%,#21468B 66%)" },
  BE: { background: "linear-gradient(90deg,#000 0 33%,#FAE042 33% 66%,#ED2939 66%)" },
  PL: { background: "linear-gradient(180deg,#fff 50%,#DC143C 50%)" },
  ES: { background: "linear-gradient(180deg,#AA151B 0 25%,#F1BF00 25% 75%,#AA151B 75%)" },
  CZ: { background: "linear-gradient(135deg,#11457E 0 50%,transparent 50%),linear-gradient(180deg,#fff 50%,#D7141A 50%)" },
  SE: { background: "linear-gradient(180deg,#006AA7 0 33%,#FECC02 33% 55%,#006AA7 55%)" },
  NO: { background: "linear-gradient(180deg,#EF2B2D 0 33%,#fff 33% 55%,#EF2B2D 55%)" },
  DK: { background: "linear-gradient(180deg,#C60C30 0 33%,#fff 33% 55%,#C60C30 55%)" },
  FI: { background: "linear-gradient(180deg,#fff 35%,#003580 35% 65%,#fff 65%)" },
  PT: { background: "linear-gradient(90deg,#006600 0 35%,#FF0000 35%)" },
  GR: { background: "linear-gradient(180deg,#0D5EAF 0 11%,#fff 11% 22%,#0D5EAF 22% 33%,#fff 33% 44%,#0D5EAF 44% 55%,#fff 55% 66%,#0D5EAF 66%)" },
};

function CountryFlag({ iso2, size = 20 }: { iso2: string; size?: number }) {
  const style = FLAG_STYLES[iso2] ?? { background: "linear-gradient(135deg,#cfcfcf,#9ca3af)" };
  return (
    <span
      className="shrink-0 rounded-xs border border-black/8 inline-block"
      style={{ width: size, height: Math.round(size * 0.7), ...style }}
      aria-hidden="true"
    />
  );
}

const STEP_LABELS: Record<Step, string> = {
  1: "Your product",
  2: "Buyer profile",
  3: "Target market",
  4: "Review & pay",
};

// ── Sector detection: HS chapter (first 2 digits) → sector name ──
// Mirrors apps/api/scoring/config_loader.py logic, client-side for instant feedback.
const HS_CHAPTER_TO_SECTOR: Record<string, string> = {
  "02": "live_animals_meat", "04": "food_beverage", "07": "food_beverage",
  "08": "food_beverage", "09": "food_beverage", "10": "food_beverage",
  "11": "food_beverage", "15": "food_beverage", "16": "food_beverage",
  "17": "food_beverage", "19": "food_beverage", "20": "food_beverage",
  "21": "food_beverage", "22": "food_beverage", "24": "tobacco",
  "25": "minerals_mining", "26": "minerals_mining", "28": "chemicals_pharma",
  "29": "chemicals_pharma", "30": "chemicals_pharma", "31": "chemicals_pharma",
  "32": "chemicals_pharma", "33": "chemicals_pharma", "34": "chemicals_pharma",
  "38": "chemicals_pharma", "39": "plastics_rubber", "40": "plastics_rubber",
  "41": "leather_footwear", "42": "leather_footwear", "43": "leather_footwear",
  "44": "furniture_wood", "47": "paper_printing", "48": "paper_printing",
  "49": "paper_printing", "50": "raw_textiles", "51": "raw_textiles",
  "52": "raw_textiles", "53": "raw_textiles", "54": "raw_textiles",
  "55": "raw_textiles", "56": "raw_textiles", "57": "raw_textiles",
  "58": "raw_textiles", "59": "raw_textiles", "60": "raw_textiles",
  "61": "textiles_apparel", "62": "textiles_apparel", "63": "textiles_apparel",
  "64": "leather_footwear", "69": "stone_ceramics_glass", "70": "stone_ceramics_glass",
  "72": "metals_steel", "73": "metals_steel", "74": "metals_steel",
  "75": "metals_steel", "76": "metals_steel", "78": "metals_steel",
  "79": "metals_steel", "80": "metals_steel", "81": "metals_steel",
  "82": "metals_steel", "83": "metals_steel", "84": "machinery",
  "85": "machinery", "86": "transport_other", "87": "transport_other",
  "88": "transport_other", "89": "transport_other", "90": "instruments_optical",
  "91": "instruments_optical", "92": "instruments_optical", "93": "arms_ammunition",
  "94": "furniture_wood", "95": "toys_sports_misc", "96": "toys_sports_misc",
  "97": "works_of_art",
};

const SECTOR_LABELS: Record<string, string> = {
  food_beverage: "Food & Beverage", textiles_apparel: "Textiles & Apparel",
  furniture_wood: "Furniture & Wood", metals_steel: "Metals & Steel",
  chemicals_pharma: "Chemicals & Pharma", plastics_rubber: "Plastics & Rubber",
  leather_footwear: "Leather & Footwear", machinery: "Machinery & Equipment",
  raw_textiles: "Raw Textiles", paper_printing: "Paper & Printing",
  stone_ceramics_glass: "Stone, Ceramics & Glass", minerals_mining: "Minerals & Mining",
  instruments_optical: "Instruments & Optical", transport_other: "Transport Equipment",
  tobacco: "Tobacco", arms_ammunition: "Arms & Ammunition",
  toys_sports_misc: "Toys, Sports & Misc", works_of_art: "Works of Art",
  live_animals_meat: "Live Animals & Meat",
};


interface FormData {
  productName: string;
  productDesc: string;
  hsCode: string;
  unitCostEur: string;
  targetIso2: string;
  leads: LeadCount;
  tier: ReportTier;
  price: number;
  originIso2: string;
  // Step 2 — Buyer profile
  productPhrase: string;
  endBuyerType: string;
  packagingFormat: string[];
  profileConfirmed: boolean;
}

export function NewReportForm() {
  const [step, setStep] = useState<Step>(1);
  const [direction, setDirection] = useState<"forward" | "back">("forward");
  const [data, setData] = useState<FormData>({
    productName: "",
    productDesc: "",
    hsCode: "",
    unitCostEur: "",
    targetIso2: "DE",
    leads: 20,
    tier: "full",
    price: 49,
    originIso2: "XK",
    // Step 2 — Buyer profile
    productPhrase: "",
    endBuyerType: "",
    packagingFormat: [],
    profileConfirmed: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const paddle = usePaddle();

  function goTo(target: Step, dir: "forward" | "back") {
    setDirection(dir);
    setStep(target);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function next() { goTo((step + 1) as Step, "forward"); }
  function back() { goTo((step - 1) as Step, "back"); }

  function canStep1() {
    const cost = Number(data.unitCostEur);
    return (
      data.productName.trim().length >= 2 &&
      /^\d{4,6}$/.test(data.hsCode.trim()) &&
      data.unitCostEur.trim().length > 0 &&
      Number.isFinite(cost) &&
      cost > 0
    );
  }

  function canStep2() {
    const phrase = data.productPhrase.trim().toLowerCase();
    const vague = ["plastic", "metal", "wood", "fabric", "food", "chemical", "part", "product", "item", "goods"];
    const tooVague = vague.some((v) => phrase === v);
    return phrase.length >= 5 && !tooVague && !!data.endBuyerType && data.profileConfirmed;
  }

  function canStep3() {
    return !!data.targetIso2;
  }

  async function handleCheckout() {
    setSubmitting(true);
    try {
      const productDesc = data.productDesc.trim();
      const payload: {
        hs_code: string;
        origin_iso2: string;
        target_iso2: string;
        unit_cost_eur: number;
        tier: ReportTier;
        lead_count: LeadCount;
        product_name: string;
        product_desc?: string;
        product_phrase?: string;
        end_buyer_type?: string;
        packaging_format?: string[];
      } = {
        hs_code: data.hsCode.trim(),
        origin_iso2: data.originIso2,
        target_iso2: data.targetIso2,
        unit_cost_eur: Number(data.unitCostEur),
        tier: data.tier,
        lead_count: data.leads,
        product_name: data.productName.trim(),
        ...(productDesc ? { product_desc: productDesc } : {}),
        ...(data.productPhrase.trim() ? { product_phrase: data.productPhrase.trim() } : {}),
        ...(data.endBuyerType ? { end_buyer_type: data.endBuyerType } : {}),
        ...(data.packagingFormat.length ? { packaging_format: data.packagingFormat } : {}),
      };

      analytics.reportCreated(data.hsCode, data.originIso2, data.targetIso2, data.tier);

      const res = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (res.ok && json.price_id) {
        if (!paddle) {
          toast.error("Payment system not loaded. Please refresh and try again.");
          setSubmitting(false);
          return;
        }
        paddle.Checkout.open({
          items: [{ priceId: json.price_id as string }],
          customData: { report_id: json.report_id as string },
          settings: {
            successUrl: `${window.location.origin}/reports/${json.report_id as string}`,
          },
        });
        setSubmitting(false);
        return;
      }
      toast.error(parseApiError(json));
      setSubmitting(false);
    } catch {
      toast.error("Network error. Please try again.");
      setSubmitting(false);
    }
  }

  const animClass = direction === "forward" ? "animate-slide-in-left" : "animate-slide-in-right";

  return (
    <div className="min-h-screen" style={{ background: "#fff", color: "#0a0a0a" }}>
      <style>{`
        @keyframes slideInLeft  { from{opacity:0;transform:translateX(40px)} to{opacity:1;transform:translateX(0)} }
        @keyframes slideInRight { from{opacity:0;transform:translateX(-40px)} to{opacity:1;transform:translateX(0)} }
        .animate-slide-in-left  { animation: slideInLeft  .3s ease both }
        .animate-slide-in-right { animation: slideInRight .3s ease both }
      `}</style>

      {/* ── Top bar ── */}
      <header
        className="sticky top-0 z-30 bg-white"
        style={{ borderBottom: "1px solid #E5E7EB" }}
      >
        <div
          className="max-w-310 mx-auto px-8 py-[18px] grid items-center gap-8"
          style={{ gridTemplateColumns: "auto 1fr auto" }}
        >
          {/* Brand */}
          <Link href="/" className="inline-flex items-center gap-2.5 no-underline text-[#0a0a0a]">
            <div className="relative rounded-[7px] shrink-0" style={{ width: 26, height: 26, background: "#0a0a0a" }}>
              <span className="absolute rounded-xs" style={{ width: 8, height: 8, top: 5, left: 5, background: "#C8E84E" }} />
            </div>
            <span style={{ fontFamily: "'DM Serif Display',Georgia,serif", fontSize: 22, letterSpacing: "-0.01em" }}>
              Quorint
            </span>
          </Link>

          {/* Desktop stepper */}
          <nav className="hidden md:flex items-center justify-center max-w-190 w-full mx-auto">
            {([1, 2, 3, 4] as Step[]).map((s, idx) => (
              <div key={s} className="flex items-center">
                <div
                  className="flex items-center gap-2.5"
                  style={{
                    color: step === s ? "#0a0a0a" : step > s ? "#374151" : "#9CA3AF",
                    fontSize: 13.5,
                    fontWeight: step === s ? 600 : 500,
                    whiteSpace: "nowrap",
                  }}
                >
                  <span
                    className="w-6.5 h-6.5 rounded-full inline-flex items-center justify-center shrink-0 transition-all duration-200"
                    style={
                      step > s
                        ? { background: "#C8E84E", border: "1.5px solid #9CC129", color: "#1F2A07" }
                        : step === s
                        ? { background: "#fff", border: "1.5px solid #9CC129", color: "#0a0a0a", boxShadow: "0 0 0 4px rgba(200,232,78,0.30)" }
                        : { background: "#fff", border: "1.5px solid #E5E7EB", color: "#9CA3AF" }
                    }
                  >
                    {step > s ? (
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : (
                      <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 12, fontWeight: 600 }}>{s}</span>
                    )}
                  </span>
                  <span>{STEP_LABELS[s]}</span>
                </div>
                {idx < 3 && (
                  <div
                    className="mx-3.5 h-[1.5px] min-w-6 max-w-20 flex-1 relative overflow-hidden"
                    style={{ background: "#E5E7EB" }}
                  >
                    <span
                      className="absolute inset-0 transition-transform duration-[0.4s] ease-in-out origin-left"
                      style={{ background: "#9CC129", transform: step > s ? "scaleX(1)" : "scaleX(0)" }}
                    />
                  </div>
                )}
              </div>
            ))}
          </nav>

          {/* Help link */}
          <a href="#" className="hidden md:inline-flex items-center gap-1.5 no-underline" style={{ fontSize: 13, color: "#6B7280" }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
            </svg>
            <span>Need help?</span>
          </a>
        </div>

        {/* Mobile progress */}
        <div className="md:hidden px-5 pb-3.5 pt-3" style={{ borderTop: "1px solid #E5E7EB" }}>
          <div className="flex items-center justify-between mb-2" style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 12, letterSpacing: "0.06em", textTransform: "uppercase", color: "#6B7280" }}>
            <span>Step <strong style={{ color: "#0a0a0a" }}>{step}</strong> of 4</span>
            <span>{STEP_LABELS[step]}</span>
          </div>
          <div className="h-0.75 rounded-full overflow-hidden" style={{ background: "#E5E7EB" }}>
            <div className="h-full rounded-full transition-all duration-300 ease-out" style={{ width: `${step * 25}%`, background: "#9CC129" }} />
          </div>
        </div>
      </header>

      {/* ── Content ── */}
      <main className="px-6 py-14 pb-20">
        <div className="max-w-150 mx-auto">

          {/* ── Step 1: Your product ── */}
          {step === 1 && (
            <div key="step1" className={animClass}>
              <StepTag step={1} />
              <h2 className="step-heading">Tell us about your product</h2>
              <p className="step-sub">We use this to find buyers in the right category.</p>

              <Field label="Product name">
                <input
                  className="form-input"
                  type="text"
                  placeholder="e.g. Solid oak dining tables"
                  value={data.productName}
                  onChange={(e) => setData((d) => ({ ...d, productName: e.target.value }))}
                />
              </Field>

              <Field label="Product description">
                <textarea
                  className="form-input"
                  rows={3}
                  placeholder="Describe your product, materials, finish options, certifications you hold..."
                  value={data.productDesc}
                  onChange={(e) => setData((d) => ({ ...d, productDesc: e.target.value }))}
                  style={{ resize: "vertical", minHeight: 96 }}
                />
              </Field>

              <Field label="HS Code (4–6 digits)">
                <input
                  className="form-input"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="940360"
                  value={data.hsCode}
                  onChange={(e) => setData((d) => ({ ...d, hsCode: e.target.value }))}
                />
                <FieldInfo>
                  Your 4–6 digit Harmonized System code. Example: <strong>940360</strong> for wooden furniture.
                  Find yours at{" "}
                  <a href="https://hscode.org" target="_blank" rel="noopener noreferrer" style={{ color: "#0a0a0a", textDecoration: "underline", textUnderlineOffset: 2 }}>
                    hscode.org →
                  </a>
                </FieldInfo>
              </Field>

              <Field label="Production cost per unit (EUR)">
                <input
                  className="form-input"
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="0.01"
                  placeholder="e.g. 45.00"
                  value={data.unitCostEur}
                  onChange={(e) => setData((d) => ({ ...d, unitCostEur: e.target.value }))}
                />
                <FieldInfo>
                  Your ex-works production cost per unit, in EUR. Used to calculate landed cost and margin in your report.
                </FieldInfo>
              </Field>

              <Field label="Country of manufacture">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {ORIGIN_COUNTRIES.map((c) => (
                    <button
                      key={c.iso2}
                      type="button"
                      onClick={() => setData((d) => ({ ...d, originIso2: c.iso2 }))}
                      className={cn(
                        "px-3 py-2.5 text-sm rounded-xl border font-medium transition-all text-left",
                        data.originIso2 === c.iso2
                          ? "border-green-deep text-green-ink"
                          : "border-[#E5E7EB] text-ink-2 hover:border-[#cfcfcf]"
                      )}
                      style={data.originIso2 === c.iso2 ? { background: "#C8E84E" } : { background: "#fff" }}
                    >
                      {c.name}
                    </button>
                  ))}
                </div>
              </Field>

              <div className="mt-8">
                <PrimaryButton onClick={next} disabled={!canStep1()}>
                  Continue
                  <ArrowRight />
                </PrimaryButton>
              </div>
            </div>
          )}

          {/* ── Step 2: Buyer profile ── */}
          {step === 2 && (() => {
            const chapter = data.hsCode.trim().slice(0, 2).padStart(2, "0");
            const sector = HS_CHAPTER_TO_SECTOR[chapter] ?? "";
            const sectorLabel = SECTOR_LABELS[sector] ?? "your sector";
            const phrase = data.productPhrase.trim().toLowerCase();
            const vagueTerms = ["plastic", "metal", "wood", "fabric", "food", "chemical", "part", "product", "item", "goods"];
            const isTooVague = vagueTerms.some((v) => phrase === v);
            const isConflict = data.packagingFormat.includes("bulk") && data.endBuyerType === "retail";
            const tradeChannelNote: Record<string, string[]> = {
              furniture_wood: ["imm cologne", "Salone del Mobile"],
              food_beverage: ["ANUGA", "SIAL Paris"],
              textiles_apparel: ["Première Vision", "Munich Fabric Start"],
              metals_steel: ["EuroBLECH", "wire Düsseldorf"],
              machinery: ["Hannover Messe", "EMO"],
            };
            const fairs = tradeChannelNote[sector] ?? [];
            return (
              <div key="step2" className={animClass}>
                <StepTag step={2} />
                <h2 className="step-heading">Tell us exactly what you make</h2>
                <p className="step-sub">This shapes which buyers we find — be specific to get better leads.</p>

                {/* Screen A: Sub-type & Buyer */}
                <Field label="Describe your product in one phrase">
                  <input
                    className="form-input"
                    type="text"
                    maxLength={60}
                    placeholder={`e.g. solid oak dining tables, precision CNC brackets`}
                    value={data.productPhrase}
                    onChange={(e) => setData((d) => ({ ...d, productPhrase: e.target.value, profileConfirmed: false }))}
                  />
                  {isTooVague && data.productPhrase.trim().length > 0 && (
                    <div className="mt-2 flex items-start gap-2 rounded-md px-3.5 py-3 text-[12.5px]" style={{ background: "#FEF3C7", border: "1px solid #F59E0B", color: "#92400E", lineHeight: 1.5 }}>
                      <span style={{ fontSize: 14 }}>⚠</span>
                      <span>Too broad — buyers won't find you. Try: <strong>"solid oak dining tables"</strong> instead of <strong>"{data.productPhrase.trim()}"</strong>.</span>
                    </div>
                  )}
                  {sector && (
                    <div className="mt-2.5 flex items-start gap-2.5 rounded-md px-3.5 py-3" style={{ background: "#F6F6F4", border: "1px solid #E5E7EB", fontSize: 12.5, color: "#374151", lineHeight: 1.5 }}>
                      <span className="shrink-0 mt-px" style={{ color: "#6B7280" }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" />
                        </svg>
                      </span>
                      <span>HS chapter {chapter} → <strong>{sectorLabel}</strong>. We'll search buyers in this category.</span>
                    </div>
                  )}
                </Field>

                <Field label="Who is the end buyer of your product?">
                  <div className="grid grid-cols-1 gap-2">
                    {[
                      { value: "wholesale", label: "Wholesale distributor / importer" },
                      { value: "retail", label: "Retail chain or independent retailer" },
                      { value: "oem", label: "Industrial / OEM manufacturer" },
                      { value: "hospitality", label: "Hospitality / contract buyer (hotels, restaurants)" },
                      { value: "institutional", label: "Government / institutional buyer" },
                    ].map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setData((d) => ({ ...d, endBuyerType: opt.value, profileConfirmed: false }))}
                        className={cn("px-3.5 py-3 text-[14px] rounded-xl border font-medium transition-all text-left")}
                        style={data.endBuyerType === opt.value
                          ? { background: "#C8E84E", borderColor: "#9CC129", color: "#1F2A07" }
                          : { background: "#fff", borderColor: "#E5E7EB", color: "#374151" }}
                      >{opt.label}</button>
                    ))}
                  </div>
                </Field>

                <Field label="How do you ship to buyers?">
                  <div className="flex flex-col gap-2">
                    {[
                      { value: "bulk", label: "Bulk / industrial (pallets, big bags — no retail packaging)" },
                      { value: "wholesale_packs", label: "Wholesale inner packs (cartons of 6, 12, 24 units)" },
                      { value: "retail_ready", label: "Retail-ready (barcoded, branded, shelf-ready)" },
                      { value: "private_label", label: "Private label / OEM (buyer's brand, we manufacture)" },
                    ].map((opt) => {
                      const checked = data.packagingFormat.includes(opt.value);
                      return (
                        <button
                          key={opt.value}
                          type="button"
                          onClick={() => setData((d) => ({
                            ...d,
                            packagingFormat: checked
                              ? d.packagingFormat.filter((v) => v !== opt.value)
                              : [...d.packagingFormat, opt.value],
                            profileConfirmed: false,
                          }))}
                          className="flex items-center gap-3 px-3.5 py-3 rounded-xl border text-[14px] text-left transition-all"
                          style={checked
                            ? { background: "#C8E84E", borderColor: "#9CC129", color: "#1F2A07" }
                            : { background: "#fff", borderColor: "#E5E7EB", color: "#374151" }}
                        >
                          <span
                            className="shrink-0 w-4.5 h-4.5 rounded border-[1.5px] inline-flex items-center justify-center"
                            style={checked ? { background: "#1F2A07", borderColor: "#1F2A07" } : { background: "#fff", borderColor: "#D1D5DB" }}
                          >
                            {checked && (
                              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#C8E84E" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="20 6 9 17 4 12" />
                              </svg>
                            )}
                          </span>
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                  {isConflict && (
                    <div className="mt-2 flex items-start gap-2 rounded-md px-3.5 py-3 text-[12.5px]" style={{ background: "#FEF3C7", border: "1px solid #F59E0B", color: "#92400E", lineHeight: 1.5 }}>
                      <span style={{ fontSize: 14 }}>⚠</span>
                      <span>Most retail chains require retail-ready packaging. Confirm you can supply in individual cartons, or change the buyer type to "Wholesale distributor".</span>
                    </div>
                  )}
                </Field>

                {/* Validation checkpoint */}
                {data.productPhrase.trim().length >= 5 && !isTooVague && data.endBuyerType && (
                  <div
                    className="rounded-xl p-5 mb-6 mt-2"
                    style={{ background: "#F6F6F4", border: "1px solid #E5E7EB" }}
                  >
                    <div className="text-[12px] font-semibold mb-3" style={{ fontFamily: "'IBM Plex Mono',monospace", letterSpacing: "0.08em", textTransform: "uppercase", color: "#6B7280" }}>
                      Your search profile
                    </div>
                    <div className="text-[15px] font-semibold mb-4" style={{ color: "#0a0a0a", lineHeight: 1.4 }}>
                      "{data.productPhrase.trim()}"
                    </div>
                    <div className="flex flex-col gap-2 mb-4 text-[13.5px]" style={{ color: "#374151" }}>
                      {[
                        ["Buyer type", {wholesale:"Wholesale distributor / importer",retail:"Retail chain",oem:"Industrial / OEM",hospitality:"Hospitality / contract",institutional:"Institutional"}[data.endBuyerType] ?? data.endBuyerType],
                        ...(data.packagingFormat.length ? [["Packaging", data.packagingFormat.join(", ")]] : []),
                        ...(sectorLabel ? [["Sector", `${sectorLabel} (HS chapter ${chapter})`]] : []),
                      ].map(([k, v]) => (
                        <div key={k} className="flex items-baseline gap-2">
                          <span className="shrink-0 w-28" style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11, color: "#9CA3AF", letterSpacing: "0.04em", textTransform: "uppercase" }}>{k}</span>
                          <span className="font-medium">{v}</span>
                        </div>
                      ))}
                    </div>
                    {fairs.length > 0 && (
                      <div className="text-[12.5px] mb-4" style={{ color: "#6B7280", lineHeight: 1.6 }}>
                        We'll also cross-reference buyers attending <strong style={{ color: "#374151" }}>{fairs.join(", ")}</strong>.
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => setData((d) => ({ ...d, profileConfirmed: true }))}
                      className="w-full inline-flex items-center justify-center gap-2 font-semibold rounded-full transition-all duration-150"
                      style={data.profileConfirmed
                        ? { background: "#1F2A07", color: "#C8E84E", border: "1px solid #1F2A07", padding: "14px 24px", fontSize: 14.5, cursor: "default" }
                        : { background: "#C8E84E", color: "#1F2A07", border: "1px solid transparent", padding: "14px 24px", fontSize: 14.5, cursor: "pointer", boxShadow: "0 1px 0 rgba(0,0,0,0.04)" }}
                    >
                      {data.profileConfirmed ? (
                        <>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          Profile confirmed
                        </>
                      ) : "This looks right — confirm profile"}
                    </button>
                  </div>
                )}

                <div className="mt-4">
                  <BackLink onClick={back} />
                  <PrimaryButton onClick={next} disabled={!canStep2()}>
                    Continue <ArrowRight />
                  </PrimaryButton>
                </div>
              </div>
            );
          })()}

          {/* ── Step 3: Target market ── */}
          {step === 3 && (
            <div key="step3" className={animClass}>
              <StepTag step={3} />
              <h2 className="step-heading">Where do you want to sell?</h2>
              <p className="step-sub">Pick a target market and how many ranked buyers you want.</p>

              <Field label="Target country">
                <div className="relative">
                  <span className="absolute top-1/2 -translate-y-1/2 left-3.5 pointer-events-none">
                    <CountryFlag iso2={data.targetIso2} />
                  </span>
                  <select
                    className="form-input appearance-none cursor-pointer"
                    value={data.targetIso2}
                    onChange={(e) => setData((d) => ({ ...d, targetIso2: e.target.value }))}
                    style={{
                      paddingLeft: 44,
                      paddingRight: 40,
                      backgroundImage: "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236B7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>\")",
                      backgroundRepeat: "no-repeat",
                      backgroundPosition: "right 14px center",
                      backgroundSize: "16px 16px",
                    }}
                  >
                    {TARGET_COUNTRIES.map((c) => (
                      <option key={c.iso2} value={c.iso2}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </Field>

              <Field label="Number of leads" style={{ marginTop: 28 }}>
                <div className="grid grid-cols-3 gap-2.5 sm:gap-3">
                  {LEAD_TIERS.map((tier) => {
                    const selected = data.leads === tier.leads;
                    return (
                      <button
                        key={tier.leads}
                        type="button"
                        onClick={() =>
                          setData((d) => ({
                            ...d,
                            leads: tier.leads,
                            tier: tier.tier,
                            price: tier.price,
                          }))
                        }
                        role="radio"
                        aria-checked={selected}
                        className="relative rounded-xl border-[1.5px] p-4 text-left flex flex-col gap-1 transition-all duration-150"
                        style={
                          selected
                            ? { background: "#C8E84E", borderColor: "#9CC129", boxShadow: "0 10px 24px -16px rgba(156,193,41,0.6)" }
                            : { background: "#fff", borderColor: "#E5E7EB" }
                        }
                      >
                        {tier.best && (
                          <span
                            className="absolute -top-2.5 left-1/2 -translate-x-1/2 rounded-full whitespace-nowrap"
                            style={{
                              fontFamily: "'IBM Plex Mono',monospace",
                              fontSize: 9.5,
                              fontWeight: 700,
                              letterSpacing: "0.08em",
                              textTransform: "uppercase",
                              padding: "3px 10px",
                              background: selected ? "#1F2A07" : "#C8E84E",
                              color: selected ? "#C8E84E" : "#1F2A07",
                              boxShadow: "0 4px 10px -4px rgba(156,193,41,0.55)",
                            }}
                          >
                            Best value
                          </span>
                        )}
                        <span className="text-[15px] font-semibold" style={{ color: selected ? "#1F2A07" : "#0a0a0a", letterSpacing: "-0.005em" }}>
                          {tier.leads} leads
                        </span>
                        <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 13, color: selected ? "#1F2A07" : "#6B7280", letterSpacing: "0.02em" }}>
                          €{tier.price}
                        </span>
                        <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 10.5, color: selected ? "rgba(31,42,7,0.7)" : "#9CA3AF", letterSpacing: "0.04em", textTransform: "uppercase", marginTop: 2 }}>
                          €{tier.perLead} / lead
                        </span>
                      </button>
                    );
                  })}
                </div>
              </Field>

              <div className="mt-9">
                <BackLink onClick={back} />
                <PrimaryButton onClick={next} disabled={!canStep3()}>
                  Continue <ArrowRight />
                </PrimaryButton>
              </div>
            </div>
          )}

          {/* ── Step 4: Review & pay ── */}
          {step === 4 && (
            <div key="step4" className={animClass}>
              <StepTag step={4} />
              <h2 className="step-heading">Review your order</h2>

              {/* Summary card */}
              <div
                className="rounded-xl p-6 mb-6"
                style={{ background: "#fff", border: "1px solid #E5E7EB", boxShadow: "0 1px 0 rgba(0,0,0,0.02), 0 18px 40px -28px rgba(0,0,0,0.10)" }}
              >
                {[
                  { k: "Product", v: data.productName || "—" },
                  { k: "HS Code", v: data.hsCode || "—" },
                  { k: "Unit cost", v: data.unitCostEur ? `€${data.unitCostEur}` : "—" },
                  {
                    k: "Target country",
                    v: (
                      <span className="flex items-center gap-2">
                        <CountryFlag iso2={data.targetIso2} />
                        <span>{COUNTRY_NAMES[data.targetIso2] ?? data.targetIso2}</span>
                      </span>
                    ),
                  },
                  { k: "Lead count", v: `${data.leads} leads` },
                  { k: "Delivery", v: "Within 4 hours of payment" },
                ].map((row, idx) => (
                  <div
                    key={row.k}
                    className="grid items-center gap-4 py-2.75"
                    style={{
                      gridTemplateColumns: "140px 1fr",
                      borderTop: idx > 0 ? "1px solid #F1F1EE" : undefined,
                    }}
                  >
                    <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11.5, color: "#6B7280", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                      {row.k}
                    </span>
                    <span className="text-[15px] font-medium" style={{ color: "#0a0a0a" }}>
                      {row.v}
                    </span>
                  </div>
                ))}

                <div className="h-px my-1.5" style={{ background: "#E5E7EB" }} />

                <div className="flex items-baseline justify-between pt-3.5 pb-1">
                  <span className="text-[15px] font-medium" style={{ color: "#374151" }}>Total</span>
                  <span style={{ fontFamily: "'DM Serif Display',Georgia,serif", fontSize: 38, letterSpacing: "-0.02em", color: "#0a0a0a", lineHeight: 1 }}>
                    €{data.price}
                  </span>
                </div>
              </div>

              {/* What happens next */}
              <div className="flex flex-col gap-3.5 mb-7">
                {[
                  {
                    icon: (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                      </svg>
                    ),
                    text: <><strong style={{ color: "#0a0a0a", fontWeight: 600 }}>Your pipeline starts immediately</strong> after payment</>,
                  },
                  {
                    icon: (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
                        <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
                      </svg>
                    ),
                    text: <><strong style={{ color: "#0a0a0a", fontWeight: 600 }}>Lead list ready within 4 hours</strong></>,
                  },
                  {
                    icon: (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
                      </svg>
                    ),
                    text: <><strong style={{ color: "#0a0a0a", fontWeight: 600 }}>Email notification</strong> when your leads are ready</>,
                  },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-3.5 text-[14.5px]" style={{ color: "#374151", lineHeight: 1.5 }}>
                    <span
                      className="shrink-0 rounded-md inline-flex items-center justify-center"
                      style={{ width: 34, height: 34, background: "#EBF6C8", color: "#9CC129" }}
                    >
                      {item.icon}
                    </span>
                    <span className="mt-1.5">{item.text}</span>
                  </div>
                ))}
              </div>

              <BackLink onClick={back} />
              <PrimaryButton
                onClick={handleCheckout}
                loading={submitting}
              >
                {submitting ? "Processing…" : `Pay €${data.price} — Get my leads`}
                {!submitting && <ArrowRight />}
              </PrimaryButton>

              <div className="mt-3.5 flex items-center justify-center gap-1.5 text-[12.5px]" style={{ color: "#6B7280" }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                Secured by Paddle. Card details never touch our servers.
              </div>
            </div>
          )}

        </div>
      </main>

      {/* Shared field styles injected once */}
      <style>{`
        .form-input {
          width: 100%;
          border: 1px solid #E5E7EB;
          background: #fff;
          border-radius: 12px;
          padding: 13px 16px;
          font-family: inherit;
          font-size: 15px;
          color: #0a0a0a;
          outline: none;
          transition: border-color .15s ease, box-shadow .15s ease;
        }
        .form-input::placeholder { color: #9CA3AF; }
        .form-input:hover { border-color: #cfcfcf; }
        .form-input:focus { border-color: #0a0a0a; box-shadow: 0 0 0 3px rgba(10,10,10,0.06); }
        .step-heading {
          font-family: 'DM Serif Display', Georgia, serif;
          font-weight: 400;
          font-size: clamp(32px, 3.8vw, 42px);
          line-height: 1.08;
          letter-spacing: -0.02em;
          color: #0a0a0a;
          margin: 18px 0 10px;
        }
        .step-sub {
          color: #6B7280;
          font-size: 15.5px;
          line-height: 1.55;
          margin: 0 0 32px;
        }
      `}</style>
    </div>
  );
}

/* ── Shared small components ── */

function StepTag({ step }: { step: Step }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full"
      style={{
        background: "#F6F6F4",
        border: "1px solid #E5E7EB",
        fontFamily: "'IBM Plex Mono',monospace",
        fontSize: 11.5,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: "#6B7280",
        fontWeight: 500,
      }}
    >
      <span className="w-1.25 h-1.25 rounded-full shrink-0" style={{ background: "#9CC129" }} />
      Step {step} of 5
    </span>
  );
}

function Field({ label, children, style }: { label: string; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div className="mb-5" style={style}>
      <label
        className="block mb-2"
        style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: 11.5, fontWeight: 500, color: "#374151", letterSpacing: "0.06em", textTransform: "uppercase" }}
      >
        {label}
      </label>
      {children}
    </div>
  );
}

function FieldInfo({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="mt-2.5 flex items-start gap-2.5 rounded-md px-3.5 py-3"
      style={{ background: "#F6F6F4", border: "1px solid #E5E7EB", fontSize: 12.5, color: "#374151", lineHeight: 1.5 }}
    >
      <span className="shrink-0 mt-px" style={{ color: "#6B7280" }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" />
        </svg>
      </span>
      <span>{children}</span>
    </div>
  );
}

function PrimaryButton({ onClick, disabled, loading, children }: { onClick: () => void; disabled?: boolean; loading?: boolean; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      className="w-full inline-flex items-center justify-center gap-2 font-semibold rounded-full transition-all duration-150"
      style={{
        background: disabled ? "#E5E7EB" : "#C8E84E",
        color: disabled ? "#9CA3AF" : "#1F2A07",
        border: "1px solid transparent",
        padding: "16px 24px",
        fontSize: 15.5,
        cursor: disabled ? "not-allowed" : "pointer",
        boxShadow: disabled ? "none" : "0 1px 0 rgba(0,0,0,0.04)",
      }}
    >
      {loading && (
        <span
          className="inline-block w-3.5 h-3.5 rounded-full border-2 animate-spin"
          style={{ borderColor: "rgba(31,42,7,0.25)", borderTopColor: "#1F2A07" }}
        />
      )}
      {children}
    </button>
  );
}

function BackLink({ onClick }: { onClick: () => void }) {
  return (
    <div className="mb-3.5">
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-1.5 bg-transparent border-0 cursor-pointer p-0"
        style={{ fontFamily: "inherit", fontSize: 13.5, color: "#6B7280" }}
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 12H5M11 19l-7-7 7-7" />
        </svg>
        Back
      </button>
    </div>
  );
}

function ArrowRight() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  );
}
