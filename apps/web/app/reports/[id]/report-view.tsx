"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatCurrency, formatPercent, COUNTRY_FLAGS, COUNTRY_NAMES } from "@/lib/utils";
import { analytics } from "@/lib/analytics";
import {
  Download,
  Copy,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Mail,
} from "lucide-react";

type ReportStatus = "queued" | "running" | "complete" | "failed";

interface WorkerStep {
  label: string;
  key: string;
}

const WORKER_STEPS: WorkerStep[] = [
  { key: "w1", label: "Market demand + pricing" },
  { key: "w2", label: "Compliance map" },
  { key: "w3", label: "Buyer discovery" },
  { key: "w4", label: "Deep market research" },
  { key: "w5", label: "Report synthesis" },
];

const AVG_WORKER_SECONDS = [60, 30, 90, 120, 90];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function ReportView({ report: initialReport }: { report: any }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [report, setReport] = useState<any>(initialReport);
  const [completedWorkers, setCompletedWorkers] = useState<number>(
    initialReport.status === "complete" ? 5 : (initialReport.current_worker ?? 0)
  );
  const [copied, setCopied] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  const [emailCopied, setEmailCopied] = useState(false);

  const status: ReportStatus = report.status;
  const isRunning = status === "queued" || status === "running";

  useEffect(() => {
    if (!isRunning) return;

    const supabase = createClient();

    async function fetchFullReport() {
      const { data } = await supabase
        .from("reports")
        .select("*, report_demand(*), report_compliance(*), report_buyers(*)")
        .eq("id", report.id)
        .single();
      if (data) setReport(data);
    }

    const channel = supabase
      .channel(`report:${report.id}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "reports",
          filter: `id=eq.${report.id}`,
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (payload: any) => {
          if (payload.new.current_worker != null) {
            setCompletedWorkers(
              payload.new.status === "complete" ? 5 : payload.new.current_worker
            );
          }
          if (payload.new.status === "complete" || payload.new.status === "failed") {
            // Full re-fetch to get joined child tables (demand, compliance, buyers)
            fetchFullReport();
          } else {
            setReport((prev: any) => ({ ...prev, ...payload.new }));
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [isRunning, report.id]);

  const remainingSeconds = isRunning
    ? AVG_WORKER_SECONDS.slice(completedWorkers).reduce((a, b) => a + b, 0)
    : 0;

  function toggleSection(key: string) {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  async function copyUrl() {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const demand = report.report_demand;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const compliance: any[] = report.report_compliance ?? [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const buyers: any[] = report.report_buyers ?? [];
  const warmBuyers = buyers.filter((b) => b.tier === "warm");
  const coldBuyers = buyers.filter((b) => b.tier === "cold");

  const marginVerdict = demand?.margin_verdict;
  const marginBadgeVariant =
    marginVerdict === "viable"
      ? "success"
      : marginVerdict === "tight"
      ? "warning"
      : "error";

  const fullReportMarkdown = report.full_report_markdown ?? "";
  const firstContactEmail = report.first_contact_email ?? "";
  const subjectLines: string[] = report.first_contact_subject_lines ?? [];
  const actionPlan = report.action_plan_markdown ?? "";
  const riskFlags = report.risk_flags_markdown ?? "";

  const criticalItem = compliance.find((c) => c.critical);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">
              {COUNTRY_FLAGS[report.target_iso2] ?? "🌍"}
            </span>
            <h1 className="text-2xl font-semibold text-slate-900">
              {COUNTRY_NAMES[report.target_iso2] ?? report.target_iso2} — HS {report.hs_code}
            </h1>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge status={status} />
            {report.tier === "full" && (
              <Badge variant="info">Full report</Badge>
            )}
            {report.is_test && <Badge variant="outline">Test</Badge>}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={copyUrl} className="gap-1.5">
            {copied ? (
              <><CheckCircle2 className="w-4 h-4 text-green-600" /> Copied</>
            ) : (
              <><Copy className="w-4 h-4" /> Share</>
            )}
          </Button>
          {report.pdf_url && (
            <a href={report.pdf_url} target="_blank" rel="noopener noreferrer" onClick={() => analytics.pdfDownloaded(report.id)}>
              <Button size="sm" className="gap-1.5">
                <Download className="w-4 h-4" /> Download PDF
              </Button>
            </a>
          )}
        </div>
      </div>

      {/* Progress tracker (while running) */}
      {isRunning && (
        <Card className="mb-8">
          <CardContent className="py-6">
            <div className="flex items-center gap-2 mb-5">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              <p className="text-sm font-medium text-slate-700">
                Generating your report…
              </p>
              {remainingSeconds > 0 && (
                <span className="text-sm text-slate-400 ml-auto flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  ~{Math.ceil(remainingSeconds / 60)} min remaining
                </span>
              )}
            </div>
            <div className="space-y-3">
              {WORKER_STEPS.map((step, i) => {
                const done = i < completedWorkers;
                const active = i === completedWorkers;
                return (
                  <div key={step.key} className="flex items-center gap-3">
                    <div
                      className={cn(
                        "w-5 h-5 rounded-full flex items-center justify-center shrink-0",
                        done
                          ? "bg-green-100"
                          : active
                          ? "bg-blue-100"
                          : "bg-slate-100"
                      )}
                    >
                      {done ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
                      ) : active ? (
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                      ) : (
                        <div className="w-2 h-2 bg-slate-300 rounded-full" />
                      )}
                    </div>
                    <span
                      className={cn(
                        "text-sm",
                        done
                          ? "text-slate-500 line-through"
                          : active
                          ? "text-slate-900 font-medium"
                          : "text-slate-400"
                      )}
                    >
                      Worker {i + 1}: {step.label}
                    </span>
                    {active && (
                      <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full ml-auto">
                        running…
                      </span>
                    )}
                    {done && (
                      <span className="text-xs text-slate-400 ml-auto">complete</span>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {status === "failed" && (
        <div className="mb-8 bg-red-50 border border-red-200 rounded-xl p-5">
          <p className="text-sm font-semibold text-red-800 mb-1">Report generation failed</p>
          <p className="text-sm text-red-700">
            {report.error_message ?? "An unexpected error occurred. Please contact support."}
          </p>
        </div>
      )}

      {/* Full report (when complete) */}
      {status === "complete" && (
        <div className="space-y-6">
          {/* Section 1 — Market demand */}
          {demand && (
            <ReportSection title="1. Market demand snapshot" defaultOpen>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
                <Stat
                  label="Import value"
                  value={demand.import_value_usd ? formatCurrency(demand.import_value_usd / 1.1, "EUR") : "—"}
                  sub="latest year"
                />
                <Stat
                  label="5-yr trend"
                  value={demand.cagr_5yr ? `+${formatPercent(demand.cagr_5yr)}/yr` : "—"}
                  sub="CAGR"
                />
                <Stat
                  label="MFN tariff"
                  value={demand.tariff_mfn != null ? formatPercent(demand.tariff_mfn) : "—"}
                  sub={demand.trade_agreement ?? "standard"}
                />
                <Stat
                  label="GDP"
                  value={demand.gdp_usd ? `$${(demand.gdp_usd / 1e12).toFixed(1)}T` : "—"}
                  sub="target market"
                />
              </div>

              {demand.top_suppliers?.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
                    Top suppliers
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {demand.top_suppliers.map((s: any) => (
                      <span
                        key={s.country}
                        className="text-sm bg-slate-100 text-slate-700 px-3 py-1 rounded-full"
                      >
                        {s.country}{" "}
                        <span className="font-semibold">{formatPercent(s.share)}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {demand.demand_narrative && (
                <p className="text-sm text-slate-700 leading-relaxed">
                  {demand.demand_narrative}
                </p>
              )}
              {demand.one_sentence_verdict && (
                <div className="mt-3 text-sm font-medium text-slate-900 bg-slate-50 border border-slate-200 rounded-lg px-4 py-3">
                  {demand.one_sentence_verdict}
                </div>
              )}
            </ReportSection>
          )}

          {/* Section 2 — Price reality check */}
          {demand && (
            <ReportSection title="2. Price reality check">
              <div className="flex items-center gap-3 mb-5">
                <div className="text-3xl font-bold text-slate-900">
                  {demand.margin != null ? formatPercent(demand.margin) : "—"}
                </div>
                <div>
                  <p className="text-sm text-slate-500">estimated margin</p>
                  {marginVerdict && (
                    <Badge variant={marginBadgeVariant} className="mt-0.5">
                      {marginVerdict === "viable"
                        ? "✓ Viable"
                        : marginVerdict === "tight"
                        ? "⚠ Tight"
                        : "✗ Not viable"}
                    </Badge>
                  )}
                </div>
              </div>

              {demand.retail_median_eur && (
                <div className="grid grid-cols-3 gap-3 mb-5">
                  <Stat label="Retail p25" value={formatCurrency(demand.retail_p25_eur)} sub="low" />
                  <Stat label="Retail median" value={formatCurrency(demand.retail_median_eur)} sub="mid" />
                  <Stat label="Retail p75" value={formatCurrency(demand.retail_p75_eur)} sub="high" />
                </div>
              )}

              <CollapsibleBlock label="Show full cost breakdown">
                <div className="space-y-2 text-sm">
                  {[
                    ["Your unit cost", formatCurrency(report.unit_cost_eur)],
                    [
                      "Road freight per unit",
                      demand.freight_low_eur
                        ? `~${formatCurrency(Math.round((demand.freight_low_eur + demand.freight_high_eur) / 2 / 60))}`
                        : "—",
                    ],
                    ["Customs + docs", "~€5/unit"],
                    ["Insurance", "~€4/unit"],
                    [
                      "DAP landed cost",
                      demand.dap_per_unit_eur
                        ? formatCurrency(demand.dap_per_unit_eur)
                        : "—",
                    ],
                    [
                      "Wholesale price (mid)",
                      demand.wholesale_low_eur
                        ? formatCurrency((demand.wholesale_low_eur + demand.wholesale_high_eur) / 2)
                        : "—",
                    ],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between py-1.5 border-b border-slate-100 last:border-0">
                      <span className="text-slate-600">{label}</span>
                      <span className="font-medium text-slate-900">{value}</span>
                    </div>
                  ))}
                </div>
              </CollapsibleBlock>

              {demand.competitor_summary && (
                <div className="mt-4 text-sm text-slate-700 leading-relaxed">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
                    Competitive landscape
                  </p>
                  {demand.competitor_summary}
                </div>
              )}
            </ReportSection>
          )}

          {/* Section 3 — Compliance */}
          {compliance.length > 0 && (
            <ReportSection title="3. Compliance map">
              {criticalItem && (
                <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
                  <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-amber-800">
                      Critical: {criticalItem.cert_name}
                    </p>
                    {criticalItem.note && (
                      <p className="text-sm text-amber-700 mt-0.5">{criticalItem.note}</p>
                    )}
                  </div>
                </div>
              )}
              <div className="space-y-3">
                {compliance.map((item) => (
                  <div
                    key={item.id}
                    className={cn(
                      "rounded-lg border p-4",
                      item.critical
                        ? "border-amber-200 bg-amber-50/50"
                        : "border-slate-200 bg-white"
                    )}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-semibold text-slate-900">{item.cert_name}</p>
                        {item.critical && (
                          <Badge variant="warning">Critical</Badge>
                        )}
                        <Badge variant={item.cert_type === "mandatory" ? "error" : "default"}>
                          {item.cert_type === "mandatory" ? "Mandatory" : "Commercial expected"}
                        </Badge>
                      </div>
                      <p className="text-sm font-semibold text-slate-900 whitespace-nowrap">
                        €{item.cost_low_eur}–{item.cost_high_eur}
                      </p>
                    </div>
                    <p className="text-xs text-slate-500 mb-1">
                      Lead time: {item.lead_time_min}–{item.lead_time_max} weeks
                    </p>
                    {item.providers?.length > 0 && (
                      <p className="text-xs text-slate-600">
                        <span className="font-medium">Provider: </span>
                        {item.providers[0]}
                      </p>
                    )}
                    {item.note && (
                      <p className="text-xs text-slate-500 mt-1">{item.note}</p>
                    )}
                  </div>
                ))}
              </div>
            </ReportSection>
          )}

          {/* Section 4 — Buyers */}
          {buyers.length > 0 && (
            <ReportSection title="4. Buyer shortlist">
              {warmBuyers.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">
                    Warm — contact this week ({warmBuyers.length})
                  </p>
                  <div className="space-y-3">
                    {warmBuyers.slice(0, 3).map((buyer) => (
                      <BuyerCard key={buyer.id} buyer={buyer} email={firstContactEmail} />
                    ))}
                    {warmBuyers.length > 3 && (
                      <CollapsibleBlock label={`Show ${warmBuyers.length - 3} more warm buyers`}>
                        <div className="space-y-3">
                          {warmBuyers.slice(3).map((buyer) => (
                            <BuyerCard key={buyer.id} buyer={buyer} email={firstContactEmail} />
                          ))}
                        </div>
                      </CollapsibleBlock>
                    )}
                  </div>
                </div>
              )}
              {coldBuyers.length > 0 && (
                <CollapsibleBlock label={`Show ${coldBuyers.length} cold buyers (90-day nurture)`}>
                  <div className="space-y-3">
                    {coldBuyers.map((buyer) => (
                      <BuyerCard key={buyer.id} buyer={buyer} email={firstContactEmail} dimmed />
                    ))}
                  </div>
                </CollapsibleBlock>
              )}
            </ReportSection>
          )}

          {/* Section 5 — First contact kit */}
          {firstContactEmail && (
            <ReportSection title="5. First contact email">
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                {subjectLines.map((line, i) => (
                  <span
                    key={i}
                    className="text-xs bg-slate-100 text-slate-700 px-3 py-1 rounded-full"
                  >
                    Option {i + 1}: {line}
                  </span>
                ))}
              </div>
              <div className="relative bg-slate-50 border border-slate-200 rounded-lg p-5">
                <button
                  onClick={async () => {
                    await navigator.clipboard.writeText(firstContactEmail);
                    setEmailCopied(true);
                    setTimeout(() => setEmailCopied(false), 2000);
                  }}
                  className="absolute top-3 right-3 flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 bg-white border border-slate-200 rounded px-2.5 py-1.5"
                >
                  {emailCopied ? (
                    <><CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> Copied</>
                  ) : (
                    <><Copy className="w-3.5 h-3.5" /> Copy</>
                  )}
                </button>
                <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans leading-relaxed pr-16">
                  {firstContactEmail}
                </pre>
              </div>
            </ReportSection>
          )}

          {/* Section 6 — 90-day action plan */}
          {actionPlan && (
            <ReportSection title="6. 90-day action plan">
              <div className="prose prose-sm prose-slate max-w-none">
                <MarkdownRenderer content={actionPlan} />
              </div>
            </ReportSection>
          )}

          {/* Section 7 — Risk flags */}
          {riskFlags && (
            <ReportSection title="7. Risk flags">
              <div className="prose prose-sm prose-slate max-w-none">
                <MarkdownRenderer content={riskFlags} />
              </div>
            </ReportSection>
          )}

          {/* PDF download CTA (bottom) */}
          {report.pdf_url && (
            <div className="flex justify-center pt-4">
              <a href={report.pdf_url} target="_blank" rel="noopener noreferrer" onClick={() => analytics.pdfDownloaded(report.id)}>
                <Button size="lg" className="gap-2">
                  <Download className="w-5 h-5" />
                  Download full PDF report
                </Button>
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Sub-components ─── */

function StatusBadge({ status }: { status: ReportStatus }) {
  const map: Record<ReportStatus, { variant: "default" | "info" | "success" | "error"; label: string }> = {
    queued: { variant: "default", label: "Queued" },
    running: { variant: "info", label: "Generating…" },
    complete: { variant: "success", label: "Complete" },
    failed: { variant: "error", label: "Failed" },
  };
  const { variant, label } = map[status];
  return <Badge variant={variant}>{label}</Badge>;
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-slate-50 rounded-lg border border-slate-200 px-4 py-3">
      <p className="text-xs text-slate-500 mb-0.5">{label}</p>
      <p className="text-lg font-bold text-slate-900 leading-tight">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function ReportSection({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <Card>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50 rounded-t-xl transition-colors"
      >
        <h2 className="text-base font-semibold text-slate-900 text-left">{title}</h2>
        {open ? (
          <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
        )}
      </button>
      {open && <CardContent className="pt-0">{children}</CardContent>}
    </Card>
  );
}

function CollapsibleBlock({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="text-sm text-slate-600 hover:text-slate-900 flex items-center gap-1.5 py-1"
      >
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        {label}
      </button>
      {open && <div className="mt-3">{children}</div>}
    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function BuyerCard({ buyer, email, dimmed }: { buyer: any; email?: string; dimmed?: boolean }) {
  const [showEmail, setShowEmail] = useState(false);

  const personalised = email
    ? email.replace(/\[COMPANY\]/g, buyer.company_name).replace(/\[CONTACT\]/g, buyer.contact_name ?? "")
    : "";

  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        buyer.tier === "warm" ? "border-green-200 bg-green-50/40" : "border-slate-200 bg-white",
        dimmed && "opacity-70"
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <p className="text-sm font-semibold text-slate-900">{buyer.company_name}</p>
          <p className="text-xs text-slate-500">
            {buyer.city}, {buyer.country_iso2} · {buyer.buyer_type}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {buyer.receptiveness_score != null && (
            <div
              className={cn(
                "text-xs font-semibold px-2 py-1 rounded-full",
                buyer.receptiveness_score >= 70
                  ? "bg-green-100 text-green-800"
                  : "bg-amber-100 text-amber-800"
              )}
            >
              {buyer.receptiveness_score}/100
            </div>
          )}
          {buyer.tier === "warm" && <Badge variant="success">Warm</Badge>}
        </div>
      </div>

      {buyer.contact_name && (
        <p className="text-xs text-slate-600 mb-1">
          <span className="font-medium">{buyer.contact_name}</span>
          {buyer.contact_title && ` — ${buyer.contact_title}`}
        </p>
      )}

      {buyer.receptiveness_signals?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {buyer.receptiveness_signals.slice(0, 2).map((signal: string, i: number) => (
            <span key={i} className="text-xs bg-white border border-slate-200 text-slate-600 px-2 py-0.5 rounded-full">
              {signal}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        {buyer.contact_email && (
          <a
            href={`mailto:${buyer.contact_email}`}
            className="inline-flex items-center gap-1.5 text-xs bg-slate-900 text-white px-3 py-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <Mail className="w-3 h-3" />
            {buyer.contact_email}
          </a>
        )}
        {buyer.linkedin_url && (
          <a
            href={buyer.linkedin_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
          >
            <ExternalLink className="w-3 h-3" />
            LinkedIn
          </a>
        )}
        {email && buyer.tier === "warm" && (
          <button
            onClick={() => setShowEmail((o) => !o)}
            className="text-xs text-slate-500 hover:text-slate-700"
          >
            {showEmail ? "Hide" : "Show"} personalised email
          </button>
        )}
      </div>

      {showEmail && personalised && (
        <pre className="mt-3 text-xs text-slate-700 bg-white border border-slate-200 rounded-lg p-3 whitespace-pre-wrap font-sans leading-relaxed">
          {personalised}
        </pre>
      )}
    </div>
  );
}

function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        if (line.startsWith("## ")) {
          return <h3 key={i} className="text-sm font-semibold text-slate-900 mt-4 mb-1">{line.replace("## ", "")}</h3>;
        }
        if (line.startsWith("### ")) {
          return <h4 key={i} className="text-sm font-semibold text-slate-700">{line.replace("### ", "")}</h4>;
        }
        if (line.startsWith("**") && line.endsWith("**")) {
          return <p key={i} className="text-sm font-semibold text-slate-900">{line.replace(/\*\*/g, "")}</p>;
        }
        if (line.startsWith("- ") || line.startsWith("* ")) {
          return (
            <div key={i} className="flex items-start gap-2 text-sm text-slate-700">
              <span className="mt-1 w-1.5 h-1.5 bg-slate-400 rounded-full shrink-0" />
              <span dangerouslySetInnerHTML={{ __html: line.replace(/^[-*] /, "").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") }} />
            </div>
          );
        }
        if (line.trim() === "") return <div key={i} className="h-2" />;
        return (
          <p key={i} className="text-sm text-slate-700 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") }}
          />
        );
      })}
    </div>
  );
}
