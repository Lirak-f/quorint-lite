"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn, COUNTRY_NAMES, COUNTRY_FLAGS, ORIGIN_COUNTRIES } from "@/lib/utils";
import { CheckCircle2, Search, ChevronRight, ChevronLeft, Loader2 } from "lucide-react";
import { analytics } from "@/lib/analytics";

type Step = 1 | 2 | 3;

interface HsResult {
  code: string;
  description: string;
}

interface FormData {
  hsMode: "known" | "search";
  hsCode: string;
  hsDescription: string;
  originIso2: string;
  targetIso2: string;
  unitCostEur: string;
  capacityUnits: "<100/mo" | "100-500/mo" | "500+/mo";
  certifications: string[];
  tier: "starter" | "full";
}

const CERTIFICATIONS = [
  { id: "FSC", label: "FSC Chain of Custody" },
  { id: "CE", label: "CE Marking" },
  { id: "ISO9001", label: "ISO 9001" },
  { id: "HACCP", label: "HACCP" },
  { id: "IATF16949", label: "IATF 16949" },
  { id: "none", label: "None held yet" },
];

const TARGET_COUNTRIES = Object.entries(COUNTRY_NAMES)
  .map(([iso2, name]) => ({ iso2, name }))
  .sort((a, b) => a.name.localeCompare(b.name));

const HS_DESCRIPTIONS: Record<string, string> = {
  "940360": "Wooden furniture for bedrooms, dining rooms, living rooms",
  "620520": "Men's shirts of cotton",
  "870899": "Parts and accessories for motor vehicles",
  "150910": "Virgin olive oil",
  "940350": "Wooden furniture for bedroom",
  "940310": "Metal furniture for offices",
  "6205": "Men's shirts",
  "9403": "Other furniture and parts thereof",
  "8708": "Parts and accessories for motor vehicles",
  "1509": "Olive oil and its fractions",
};

export function NewReportForm() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [data, setData] = useState<FormData>({
    hsMode: "known",
    hsCode: "",
    hsDescription: "",
    originIso2: "XK",
    targetIso2: "",
    unitCostEur: "",
    capacityUnits: "<100/mo",
    certifications: [],
    tier: "full",
  });

  const [hsSearchQuery, setHsSearchQuery] = useState("");
  const [hsSearchResults, setHsSearchResults] = useState<HsResult[]>([]);
  const [hsSearching, setHsSearching] = useState(false);
  const [hsLocked, setHsLocked] = useState(false);
  const [hsError, setHsError] = useState("");
  const [countrySearch, setCountrySearch] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function validateHsCode(code: string): boolean {
    return /^\d{4,6}$/.test(code.trim());
  }

  function handleHsBlur() {
    const code = data.hsCode.trim();
    if (!code) return;
    if (!validateHsCode(code)) {
      setHsError("HS code must be 4 or 6 digits.");
      setHsLocked(false);
      return;
    }
    setHsError("");
    const desc = HS_DESCRIPTIONS[code] || `HS ${code} — product category`;
    setData((d) => ({ ...d, hsDescription: desc }));
    setHsLocked(true);
  }

  async function handleHsSearch() {
    if (!hsSearchQuery.trim()) return;
    setHsSearching(true);
    // Simulate WITS HS lookup — real implementation calls /api/hs-search
    await new Promise((r) => setTimeout(r, 700));
    const fakeResults: HsResult[] = [
      { code: "940360", description: "Wooden furniture for dining rooms" },
      { code: "940350", description: "Wooden furniture for bedrooms" },
      { code: "940340", description: "Wooden furniture for kitchens" },
      { code: "940310", description: "Metal furniture for offices" },
      { code: "940389", description: "Other furniture, not elsewhere classified" },
    ].filter((r) =>
      r.description.toLowerCase().includes(hsSearchQuery.toLowerCase()) ||
      r.code.includes(hsSearchQuery)
    );
    setHsSearchResults(fakeResults.length ? fakeResults : [
      { code: "940360", description: "Wooden furniture for dining rooms" },
      { code: "620520", description: "Men's shirts of cotton" },
      { code: "870899", description: "Parts for motor vehicles" },
    ]);
    setHsSearching(false);
  }

  function selectHsResult(result: HsResult) {
    setData((d) => ({ ...d, hsCode: result.code, hsDescription: result.description }));
    setHsLocked(true);
    setHsSearchResults([]);
  }

  function toggleCert(id: string) {
    setData((d) => {
      if (id === "none") return { ...d, certifications: ["none"] };
      const without = d.certifications.filter((c) => c !== "none");
      return {
        ...d,
        certifications: without.includes(id)
          ? without.filter((c) => c !== id)
          : [...without, id],
      };
    });
  }

  function canAdvanceStep1() {
    return hsLocked && data.hsCode.length >= 4;
  }

  function canAdvanceStep2() {
    return data.targetIso2 && data.unitCostEur && parseFloat(data.unitCostEur) > 0;
  }

  async function handleCheckout() {
    setSubmitting(true);
    try {
      analytics.reportCreated(data.hsCode, data.originIso2, data.targetIso2, data.tier);
      const res = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          hs_code: data.hsCode,
          origin_iso2: data.originIso2,
          target_iso2: data.targetIso2,
          unit_cost_eur: parseFloat(data.unitCostEur),
          capacity_units: data.capacityUnits,
          certifications: data.certifications,
          tier: data.tier,
        }),
      });
      const json = await res.json();
      if (json.checkout_url) {
        window.location.href = json.checkout_url;
      } else {
        alert(json.error ?? "Could not create checkout session. Please try again.");
        setSubmitting(false);
      }
    } catch {
      alert("Network error. Please try again.");
      setSubmitting(false);
    }
  }

  const filteredCountries = TARGET_COUNTRIES.filter((c) =>
    c.name.toLowerCase().includes(countrySearch.toLowerCase())
  );

  const costNum = parseFloat(data.unitCostEur);

  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-slate-900">New export report</h1>
          <p className="text-slate-500 mt-1 text-sm">
            Answer three questions — get your full market report in under 5 minutes.
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-3 mb-8">
          {([1, 2, 3] as const).map((s) => (
            <div key={s} className="flex items-center gap-3">
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold",
                  step === s
                    ? "bg-slate-900 text-white"
                    : step > s
                    ? "bg-green-600 text-white"
                    : "bg-slate-100 text-slate-400"
                )}
              >
                {step > s ? (
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  s
                )}
              </div>
              <span
                className={cn(
                  "text-sm",
                  step === s ? "text-slate-900 font-medium" : "text-slate-400"
                )}
              >
                {s === 1 ? "Product" : s === 2 ? "Market details" : "Choose plan"}
              </span>
              {s < 3 && <span className="text-slate-300">›</span>}
            </div>
          ))}
        </div>

        {/* Step 1 — HS Code */}
        {step === 1 && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-1">Your product</h2>
            <p className="text-sm text-slate-500 mb-6">
              We need the HS code to pull import data, tariff rates, and compliance requirements.
            </p>

            {/* Mode toggle */}
            <div className="flex gap-2 mb-6">
              <button
                onClick={() => { setData((d) => ({ ...d, hsMode: "known" })); setHsLocked(false); }}
                className={cn(
                  "flex-1 py-2.5 text-sm font-medium rounded-lg border transition-all",
                  data.hsMode === "known"
                    ? "bg-slate-900 text-white border-slate-900"
                    : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
                )}
              >
                I know my HS code
              </button>
              <button
                onClick={() => { setData((d) => ({ ...d, hsMode: "search" })); setHsLocked(false); }}
                className={cn(
                  "flex-1 py-2.5 text-sm font-medium rounded-lg border transition-all",
                  data.hsMode === "search"
                    ? "bg-slate-900 text-white border-slate-900"
                    : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
                )}
              >
                Search by description
              </button>
            </div>

            {data.hsMode === "known" ? (
              <div className="space-y-4">
                <Input
                  label="HS code (4 or 6 digits)"
                  value={data.hsCode}
                  onChange={(e) => {
                    setData((d) => ({ ...d, hsCode: e.target.value }));
                    setHsLocked(false);
                    setHsError("");
                  }}
                  onBlur={handleHsBlur}
                  placeholder="940360"
                  maxLength={8}
                  error={hsError}
                  hint="Enter the 4 or 6-digit HS code for your product"
                />
                {hsLocked && (
                  <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                    <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
                    <div>
                      <span className="text-sm font-semibold text-green-800">HS {data.hsCode}</span>
                      <span className="text-sm text-green-700"> — {data.hsDescription}</span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex gap-2">
                  <div className="flex-1">
                    <Input
                      label="Describe your product"
                      value={hsSearchQuery}
                      onChange={(e) => setHsSearchQuery(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleHsSearch()}
                      placeholder="e.g. solid oak dining table"
                    />
                  </div>
                  <div className="flex items-end">
                    <Button
                      variant="secondary"
                      onClick={handleHsSearch}
                      loading={hsSearching}
                      className="whitespace-nowrap"
                    >
                      <Search className="w-4 h-4" />
                      Search
                    </Button>
                  </div>
                </div>

                {hsSearchResults.length > 0 && !hsLocked && (
                  <div className="border border-slate-200 rounded-lg divide-y divide-slate-100 overflow-hidden">
                    {hsSearchResults.map((r) => (
                      <button
                        key={r.code}
                        onClick={() => selectHsResult(r)}
                        className="w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors"
                      >
                        <span className="text-sm font-semibold text-slate-900 mr-2">{r.code}</span>
                        <span className="text-sm text-slate-600">{r.description}</span>
                      </button>
                    ))}
                  </div>
                )}

                {hsLocked && (
                  <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                    <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
                    <div>
                      <span className="text-sm font-semibold text-green-800">HS {data.hsCode}</span>
                      <span className="text-sm text-green-700"> — {data.hsDescription}</span>
                    </div>
                    <button
                      onClick={() => { setHsLocked(false); setHsSearchResults([]); }}
                      className="ml-auto text-xs text-slate-400 hover:text-slate-600"
                    >
                      Change
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Origin country */}
            <div className="mt-6">
              <label className="text-sm font-medium text-slate-700 block mb-2">
                Country of manufacture
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {ORIGIN_COUNTRIES.map((c) => (
                  <button
                    key={c.iso2}
                    onClick={() => setData((d) => ({ ...d, originIso2: c.iso2 }))}
                    className={cn(
                      "px-3 py-2.5 text-sm rounded-lg border font-medium transition-all text-left",
                      data.originIso2 === c.iso2
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
                    )}
                  >
                    {c.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-8 flex justify-end">
              <Button
                onClick={() => setStep(2)}
                disabled={!canAdvanceStep1()}
                className="gap-2"
              >
                Continue <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 2 — Market details */}
        {step === 2 && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-1">Market details</h2>
            <p className="text-sm text-slate-500 mb-6">
              These three inputs determine your margin, compliance requirements, and buyer targeting.
            </p>

            {/* Target country */}
            <div className="mb-5">
              <label className="text-sm font-medium text-slate-700 block mb-2">
                Target country
              </label>
              <div className="relative mb-2">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Search country..."
                  value={countrySearch}
                  onChange={(e) => setCountrySearch(e.target.value)}
                  className="w-full pl-9 pr-4 py-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-48 overflow-y-auto pr-1">
                {filteredCountries.map((c) => (
                  <button
                    key={c.iso2}
                    onClick={() => {
                      setData((d) => ({ ...d, targetIso2: c.iso2 }));
                      setCountrySearch(c.name);
                    }}
                    className={cn(
                      "px-3 py-2 text-sm rounded-lg border font-medium transition-all text-left flex items-center gap-1.5",
                      data.targetIso2 === c.iso2
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
                    )}
                  >
                    <span>{COUNTRY_FLAGS[c.iso2]}</span>
                    <span>{c.name}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Unit cost */}
            <div className="mb-5">
              <Input
                label="Unit production cost (EUR)"
                type="number"
                min="1"
                step="0.01"
                value={data.unitCostEur}
                onChange={(e) => setData((d) => ({ ...d, unitCostEur: e.target.value }))}
                placeholder="200"
                hint="Your total cost per unit to produce and package — excluding any export costs"
              />
              {data.targetIso2 && costNum > 0 && (
                <div className="mt-2 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-800">
                  <span className="font-medium">Margin preview:</span> We&apos;ll calculate your exact landed margin
                  for {COUNTRY_FLAGS[data.targetIso2]} {COUNTRY_NAMES[data.targetIso2]} after payment — including
                  freight, customs, and insurance.
                </div>
              )}
            </div>

            {/* Capacity */}
            <div className="mb-5">
              <label className="text-sm font-medium text-slate-700 block mb-2">
                Monthly production capacity
              </label>
              <div className="flex gap-2">
                {(["<100/mo", "100-500/mo", "500+/mo"] as const).map((cap) => (
                  <button
                    key={cap}
                    onClick={() => setData((d) => ({ ...d, capacityUnits: cap }))}
                    className={cn(
                      "flex-1 py-2.5 text-sm font-medium rounded-lg border transition-all",
                      data.capacityUnits === cap
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
                    )}
                  >
                    {cap}
                  </button>
                ))}
              </div>
            </div>

            {/* Certifications */}
            <div className="mb-6">
              <label className="text-sm font-medium text-slate-700 block mb-2">
                Certifications currently held
              </label>
              <div className="grid grid-cols-2 gap-2">
                {CERTIFICATIONS.map((cert) => {
                  const checked = data.certifications.includes(cert.id);
                  return (
                    <button
                      key={cert.id}
                      onClick={() => toggleCert(cert.id)}
                      className={cn(
                        "text-left px-4 py-3 rounded-lg border text-sm transition-all flex items-center gap-2.5",
                        checked
                          ? "bg-slate-900 text-white border-slate-900"
                          : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
                      )}
                    >
                      <div
                        className={cn(
                          "w-4 h-4 rounded border flex items-center justify-center shrink-0",
                          checked
                            ? "border-white bg-white/20"
                            : "border-slate-300"
                        )}
                      >
                        {checked && (
                          <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 12 10" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M1 5l3.5 4L11 1" />
                          </svg>
                        )}
                      </div>
                      {cert.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(1)} className="gap-2">
                <ChevronLeft className="w-4 h-4" /> Back
              </Button>
              <Button
                onClick={() => setStep(3)}
                disabled={!canAdvanceStep2()}
                className="gap-2"
              >
                Continue <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Step 3 — Tier selection */}
        {step === 3 && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-1">Choose your plan</h2>
            <p className="text-sm text-slate-500 mb-6">
              One report, one market. Delivered in under 5 minutes.
            </p>

            {/* Summary */}
            <div className="bg-slate-50 rounded-lg border border-slate-200 px-4 py-3 mb-6 text-sm text-slate-600 flex flex-wrap gap-x-4 gap-y-1">
              <span>
                <span className="font-medium text-slate-900">HS {data.hsCode}</span> —{" "}
                {data.hsDescription}
              </span>
              <span>
                {COUNTRY_FLAGS[data.targetIso2]}{" "}
                <span className="font-medium text-slate-900">
                  {COUNTRY_NAMES[data.targetIso2]}
                </span>
              </span>
              <span>
                Cost:{" "}
                <span className="font-medium text-slate-900">€{data.unitCostEur}/unit</span>
              </span>
            </div>

            <div className="grid sm:grid-cols-2 gap-4 mb-8">
              {/* Starter */}
              <button
                onClick={() => { setData((d) => ({ ...d, tier: "starter" })); analytics.tierSelected("starter", 29); }}
                className={cn(
                  "text-left rounded-xl border-2 p-5 transition-all",
                  data.tier === "starter"
                    ? "border-slate-900 bg-slate-50"
                    : "border-slate-200 hover:border-slate-300 bg-white"
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-semibold text-slate-900">Starter</p>
                    <p className="text-2xl font-bold text-slate-900 mt-0.5">€29</p>
                  </div>
                  <div
                    className={cn(
                      "w-5 h-5 rounded-full border-2 mt-0.5",
                      data.tier === "starter"
                        ? "border-slate-900 bg-slate-900"
                        : "border-slate-300"
                    )}
                  >
                    {data.tier === "starter" && (
                      <svg className="w-full h-full p-0.5" fill="none" viewBox="0 0 14 14" stroke="white">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M2 7l3.5 4L12 2" />
                      </svg>
                    )}
                  </div>
                </div>
                <ul className="space-y-1.5 text-sm text-slate-600">
                  {[
                    "Market demand snapshot",
                    "Compliance checklist",
                    "Top 5 buyer contacts",
                    "Basic 90-day plan",
                  ].map((item) => (
                    <li key={item} className="flex items-center gap-2">
                      <svg className="w-3.5 h-3.5 text-slate-400 shrink-0" fill="none" viewBox="0 0 16 16" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l3.5 4L13 3" />
                      </svg>
                      {item}
                    </li>
                  ))}
                </ul>
              </button>

              {/* Full */}
              <button
                onClick={() => { setData((d) => ({ ...d, tier: "full" })); analytics.tierSelected("full", 49); }}
                className={cn(
                  "text-left rounded-xl border-2 p-5 transition-all relative",
                  data.tier === "full"
                    ? "border-slate-900 bg-slate-50"
                    : "border-slate-200 hover:border-slate-300 bg-white"
                )}
              >
                <div className="absolute -top-3 left-4">
                  <span className="bg-slate-900 text-white text-xs font-semibold px-2.5 py-1 rounded-full">
                    Recommended
                  </span>
                </div>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-semibold text-slate-900">Full</p>
                    <p className="text-2xl font-bold text-slate-900 mt-0.5">€49</p>
                  </div>
                  <div
                    className={cn(
                      "w-5 h-5 rounded-full border-2 mt-0.5",
                      data.tier === "full"
                        ? "border-slate-900 bg-slate-900"
                        : "border-slate-300"
                    )}
                  >
                    {data.tier === "full" && (
                      <svg className="w-full h-full p-0.5" fill="none" viewBox="0 0 14 14" stroke="white">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M2 7l3.5 4L12 2" />
                      </svg>
                    )}
                  </div>
                </div>
                <ul className="space-y-1.5 text-sm text-slate-600">
                  {[
                    "Everything in Starter",
                    "Exact margin calculation",
                    "Buyer receptiveness scores",
                    "Localised outreach email",
                    "Deep market narrative",
                    "Risk flags & alternatives",
                  ].map((item) => (
                    <li key={item} className="flex items-center gap-2">
                      <svg className="w-3.5 h-3.5 text-green-500 shrink-0" fill="none" viewBox="0 0 16 16" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l3.5 4L13 3" />
                      </svg>
                      {item}
                    </li>
                  ))}
                </ul>
              </button>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
              <Button variant="outline" onClick={() => setStep(2)} className="gap-2 w-full sm:w-auto">
                <ChevronLeft className="w-4 h-4" /> Back
              </Button>
              <Button
                onClick={handleCheckout}
                loading={submitting}
                size="lg"
                className="w-full sm:w-auto gap-2"
              >
                {submitting ? "Redirecting to payment..." : `Pay €${data.tier === "starter" ? "29" : "49"} — Generate report`}
              </Button>
            </div>

            <p className="text-xs text-slate-400 text-center mt-4">
              Secure payment via Paddle. Report delivered in under 5 minutes.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
