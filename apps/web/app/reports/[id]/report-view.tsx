"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";
import { cn, COUNTRY_NAMES } from "@/lib/utils";
import { analytics } from "@/lib/analytics";
import {
  ArrowLeft,
  Briefcase,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  GripVertical,
  ExternalLink,
  Mail,
  Search,
  TrendingUp,
  User,
} from "lucide-react";

type ReportStatus = "queued" | "running" | "complete" | "failed";
type PipelineStatus = "notcontacted" | "contacted" | "replied" | "meeting" | "deal";
type TierFilter = "all" | "warm" | "cold";

interface WorkerStep {
  label: string;
  sub: string;
  key: string;
}

const WORKER_STEPS: WorkerStep[] = [
  { key: "w1", label: "Analyzing market demand", sub: "Import data, pricing, and tariffs" },
  { key: "w2", label: "Checking compliance", sub: "EU requirements for your product" },
  { key: "w3", label: "Discovering buyer companies", sub: "Searching Apollo and trade directories" },
  { key: "w4", label: "Analyzing sourcing signals", sub: "Job postings, fairs, and growth data" },
  { key: "w5", label: "Writing outreach emails", sub: "Personalising for each buyer" },
];

const AVG_WORKER_SECONDS = [60, 5, 90, 120, 90];

const FLAG_STYLES: Record<string, React.CSSProperties> = {
  DE: { background: "linear-gradient(180deg,#000 0 33%,#DD0000 33% 66%,#FFCC00 66%)" },
  AT: { background: "linear-gradient(180deg,#ED2939 0 33%,#fff 33% 66%,#ED2939 66%)" },
  IT: { background: "linear-gradient(90deg,#009246 0 33%,#fff 33% 66%,#CE2B37 66%)" },
  FR: { background: "linear-gradient(90deg,#0055A4 0 33%,#fff 33% 66%,#EF4135 66%)" },
  NL: { background: "linear-gradient(180deg,#AE1C28 0 33%,#fff 33% 66%,#21468B 66%)" },
  CH: { background: "#DA291C" },
  BE: { background: "linear-gradient(90deg,#000 0 33%,#FAE042 33% 66%,#ED2939 66%)" },
  PL: { background: "linear-gradient(180deg,#fff 50%,#DC143C 50%)" },
  ES: { background: "linear-gradient(180deg,#AA151B 0 25%,#F1BF00 25% 75%,#AA151B 75%)" },
  PT: { background: "linear-gradient(90deg,#046A38 0 40%,#DA291C 40%)" },
  DK: { background: "linear-gradient(180deg,#C8102E 0 33%,#fff 33% 55%,#C8102E 55%)" },
  GB: { background: "linear-gradient(45deg,#012169 0 40%,#fff 40% 50%,#C8102E 50% 60%,#fff 60% 70%,#012169 70%)" },
};

const PIPELINE_BUCKETS: { key: PipelineStatus; label: string; dot: string; chip: string }[] = [
  { key: "notcontacted", label: "Not contacted", dot: "#9CA3AF", chip: "bg-muted text-ink-3" },
  { key: "contacted", label: "Contacted", dot: "#1F3B5C", chip: "bg-[#EAF1FA] text-[#1F3B5C]" },
  { key: "replied", label: "Replied", dot: "#5A4416", chip: "bg-[#FBF1DA] text-[#5A4416]" },
  { key: "meeting", label: "Meeting booked", dot: "#9CC129", chip: "bg-[#EBF6C8] text-green-ink" },
  { key: "deal", label: "Deal closed", dot: "#5C1F38", chip: "bg-[#FAEAF0] text-[#5C1F38]" },
];

const STATUS_LABELS: Record<PipelineStatus, string> = {
  notcontacted: "Not contacted",
  contacted: "Contacted",
  replied: "Replied",
  meeting: "Meeting",
  deal: "Deal",
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function ReportView({ report: initialReport }: { report: any }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [report, setReport] = useState<any>(initialReport);
  const [completedWorkers, setCompletedWorkers] = useState<number>(
    initialReport.status === "complete" ? 5 : (initialReport.current_worker ?? 0)
  );
  const [userEmail, setUserEmail] = useState<string | null>(null);

  const status: ReportStatus = report.status;
  const isRunning = status === "queued" || status === "running";

  useEffect(() => {
    if (status !== "queued") return;
    fetch(`/api/reports/${report.id}/run`, { method: "POST" }).catch(() => {});
  }, [report.id, status]);

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(({ data }) => setUserEmail(data.user?.email ?? null));
  }, []);

  useEffect(() => {
    if (!isRunning) return;

    const supabase = createClient();

    async function fetchFullReport() {
      const { data } = await supabase
        .from("reports")
        .select("*, report_demand(*), report_buyers(*)")
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

  const listTitle = `HS ${report.hs_code}`;
  const targetName = COUNTRY_NAMES[report.target_iso2] ?? report.target_iso2;

  if (status === "failed") {
    return (
      <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-6 py-12">
        <div className="max-w-lg w-full bg-red-50 border border-red-200 rounded-2xl p-6">
          <p className="text-sm font-semibold text-red-800 mb-1">Report generation failed</p>
          <p className="text-sm text-red-700">
            {report.error_message ?? "An unexpected error occurred. Please contact support."}
          </p>
        </div>
      </div>
    );
  }

  if (isRunning) {
    return (
      <ProcessingView
        listTitle={listTitle}
        targetName={targetName}
        completedWorkers={completedWorkers}
        remainingSeconds={remainingSeconds}
        userEmail={userEmail}
        leadCount={report.report_buyers?.length}
      />
    );
  }

  return (
    <CompleteDashboard
      report={report}
      listTitle={listTitle}
      targetName={targetName}
    />
  );
}

function ProcessingView({
  listTitle,
  targetName,
  completedWorkers,
  remainingSeconds,
  userEmail,
  leadCount,
}: {
  listTitle: string;
  targetName: string;
  completedWorkers: number;
  remainingSeconds: number;
  userEmail: string | null;
  leadCount?: number;
}) {
  const pct = Math.min(99, Math.max(8, Math.round((completedWorkers / WORKER_STEPS.length) * 100)));
  const circumference = 2 * Math.PI * 30;

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-6 py-10 bg-white overflow-auto">
      <div className="relative w-full max-w-[560px] bg-warm-1 rounded-[28px] px-11 pt-11 pb-9 shadow-[0_1px_0_rgba(80,60,30,0.04),0_30px_60px_-30px_rgba(99,73,33,0.30)] overflow-hidden">
        <div
          className="absolute inset-0 pointer-events-none opacity-45"
          style={{
            backgroundImage: "radial-gradient(rgba(99,73,33,0.06) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
            maskImage: "radial-gradient(120% 100% at 50% 0%, #000 0%, transparent 70%)",
            WebkitMaskImage: "radial-gradient(120% 100% at 50% 0%, #000 0%, transparent 70%)",
          }}
        />

        <div className="relative z-10">
          <div className="flex justify-center mb-6">
            <div className="relative w-24 h-24">
              <svg width="96" height="96" viewBox="0 0 80 80" className="-rotate-90">
                <circle cx="40" cy="40" r="30" fill="none" stroke="rgba(99,73,33,0.10)" strokeWidth="5" />
                <g className="origin-center animate-[spin_2.8s_linear_infinite]">
                  <circle
                    cx="40"
                    cy="40"
                    r="30"
                    fill="none"
                    stroke="#9CC129"
                    strokeWidth="5"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={circumference * (1 - pct / 100)}
                  />
                </g>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center font-serif text-2xl text-warm-ink tracking-tight">
                {pct}%
              </div>
            </div>
          </div>

          <h1 className="font-serif text-[30px] leading-tight tracking-tight text-warm-ink text-center">
            Finding your buyers
          </h1>
          <p className="mt-2.5 text-center text-[#7a6741] font-mono-brand text-[11.5px] uppercase tracking-[0.08em]">
            {listTitle} · {targetName}
            {leadCount != null ? ` · ${leadCount} leads` : ""}
          </p>

          <div className="mt-7 py-4 border-y border-[rgba(99,73,33,0.10)] flex flex-col gap-0.5">
            {WORKER_STEPS.map((step, i) => {
              const done = i < completedWorkers;
              const active = i === completedWorkers;
              return (
                <div key={step.key} className="flex items-center gap-3.5 py-2 px-1">
                  <StepIcon done={done} active={active} />
                  <div className="flex-1 min-w-0">
                    <p
                      className={cn(
                        "text-sm font-medium text-warm-ink",
                        done && "text-[rgba(59,47,30,0.6)]",
                        !done && !active && "text-[rgba(59,47,30,0.5)]"
                      )}
                    >
                      {step.label}
                    </p>
                    <p
                      className={cn(
                        "text-xs text-[#7a6741] mt-0.5",
                        !done && !active && "text-[rgba(122,103,65,0.6)]"
                      )}
                    >
                      {step.sub}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {remainingSeconds > 0 && (
            <div className="mt-5 flex items-center justify-center gap-2 text-[13px] font-medium text-warm-ink">
              <Clock className="w-3.5 h-3.5 text-[#7a6741]" />
              ~{Math.max(1, Math.ceil(remainingSeconds / 60))} min remaining
            </div>
          )}

          {userEmail && (
            <p className="mt-3.5 text-center text-xs text-[#7a6741]">
              We&apos;ll email you at{" "}
              <a href={`mailto:${userEmail}`} className="text-warm-ink underline underline-offset-2">
                {userEmail}
              </a>{" "}
              when your leads are ready.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function StepIcon({ done, active }: { done: boolean; active: boolean }) {
  if (done) {
    return (
      <div className="w-[22px] h-[22px] rounded-full bg-green-deep flex items-center justify-center shrink-0">
        <Check className="w-2.5 h-2.5 text-white" strokeWidth={3.5} />
      </div>
    );
  }
  if (active) {
    return (
      <div className="relative w-[22px] h-[22px] rounded-full bg-white border border-[rgba(99,73,33,0.10)] shrink-0">
        <span className="absolute inset-0.5 rounded-full border-2 border-green-deep border-t-transparent animate-spin" />
      </div>
    );
  }
  return (
    <div className="w-[22px] h-[22px] rounded-full border border-[rgba(99,73,33,0.20)] shrink-0" />
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CompleteDashboard({ report, listTitle, targetName }: { report: any; listTitle: string; targetName: string }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const buyers: any[] = useMemo(
    () =>
      [...(report.report_buyers ?? [])]
        .filter((b) => b.tier !== "skip")
        .sort((a, b) => (b.receptiveness_score ?? 0) - (a.receptiveness_score ?? 0)),
    [report.report_buyers]
  );

  const perBuyerEmails: Record<string, Record<string, unknown>> = {};
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  for (const e of (report.per_buyer_emails ?? []) as any[]) {
    if (e.company_name) perBuyerEmails[e.company_name] = e;
  }

  const [selectedId, setSelectedId] = useState<string | null>(buyers[0]?.id ?? null);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState<TierFilter>("all");
  const [pipeline, setPipeline] = useState<Record<string, PipelineStatus>>({});

  useEffect(() => {
    try {
      const saved = localStorage.getItem(`quorint-pipeline-${report.id}`);
      if (saved) setPipeline(JSON.parse(saved));
    } catch {
      /* ignore */
    }
  }, [report.id]);

  useEffect(() => {
    if (buyers.length && !buyers.some((b) => b.id === selectedId)) {
      setSelectedId(buyers[0].id);
    }
  }, [buyers, selectedId]);

  function updatePipeline(buyerId: string, status: PipelineStatus) {
    setPipeline((prev) => {
      const next = { ...prev, [buyerId]: status };
      try {
        localStorage.setItem(`quorint-pipeline-${report.id}`, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  function getStatus(buyerId: string): PipelineStatus {
    return pipeline[buyerId] ?? "notcontacted";
  }

  const filteredBuyers = useMemo(() => {
    const q = search.trim().toLowerCase();
    return buyers.filter((b) => {
      if (tierFilter === "warm" && b.tier !== "warm") return false;
      if (tierFilter === "cold" && b.tier !== "cold") return false;
      if (!q) return true;
      return (
        b.company_name?.toLowerCase().includes(q) ||
        b.city?.toLowerCase().includes(q) ||
        b.contact_name?.toLowerCase().includes(q)
      );
    });
  }, [buyers, search, tierFilter]);

  const selectedBuyer = buyers.find((b) => b.id === selectedId) ?? null;
  const deliveredLabel = report.completed_at
    ? `delivered ${formatRelativeTime(report.completed_at)}`
    : "delivered recently";

  const activeConversations = buyers.filter((b) => {
    const s = getStatus(b.id);
    return s === "contacted" || s === "replied" || s === "meeting";
  }).length;
  const dealsClosed = buyers.filter((b) => getStatus(b.id) === "deal").length;

  return (
    <div className="flex flex-1 min-h-0 h-[calc(100vh-3.5rem)]">
      {/* Left sidebar */}
      <aside className="w-[280px] shrink-0 bg-[#F9FAFB] border-r border-line flex flex-col min-h-0 max-[720px]:hidden">
        <div className="px-5 pt-4 pb-2 shrink-0">
          <Link
            href="/reports"
            className="inline-flex items-center gap-1.5 text-[12.5px] text-ink-3 hover:text-ink mb-3.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            My lead lists
          </Link>
          <h2 className="font-serif text-[22px] tracking-tight leading-tight text-ink">{listTitle}</h2>
          <p className="mt-1 text-xs text-ink-3">
            {targetName} · {buyers.length} leads · {deliveredLabel}
          </p>
          <div className="mt-4 border-b border-line">
            <span className="inline-block pb-2 text-[13px] font-semibold text-ink border-b-2 border-ink -mb-px">
              Lead list
            </span>
          </div>
        </div>

        <div className="px-5 pt-3.5 pb-2.5 shrink-0">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-4" />
            <input
              type="text"
              placeholder="Search leads..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full border border-line bg-white rounded-[10px] py-2 pl-8 pr-3 text-[13px] text-ink outline-none focus:border-ink-4 placeholder:text-ink-4"
            />
          </div>
          <div className="mt-2.5 flex gap-1">
            {(["all", "warm", "cold"] as TierFilter[]).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setTierFilter(f)}
                className={cn(
                  "px-2.5 py-1 rounded-full text-xs font-medium capitalize",
                  tierFilter === f
                    ? "bg-white border border-line text-ink"
                    : "text-ink-3 hover:text-ink"
                )}
              >
                {f === "all" ? "All" : f}
              </button>
            ))}
          </div>
          {(report.pdf_url) && (
            <div className="mt-3 flex gap-2">
              <a
                href={report.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => analytics.pdfDownloaded(report.id)}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-2 hover:text-ink"
              >
                <Download className="w-3.5 h-3.5" />
                PDF
              </a>
            </div>
          )}
        </div>

        <p className="px-5 py-2 text-[11.5px] text-ink-4 font-mono-brand uppercase tracking-[0.06em] shrink-0">
          {filteredBuyers.length} leads found
        </p>

        <div className="flex-1 overflow-y-auto min-h-0 px-3 pb-4">
          {filteredBuyers.map((buyer) => {
            const status = getStatus(buyer.id);
            const bucket = PIPELINE_BUCKETS.find((b) => b.key === status)!;
            return (
              <button
                key={buyer.id}
                type="button"
                onClick={() => setSelectedId(buyer.id)}
                className={cn(
                  "w-full text-left px-3 py-2.5 rounded-[10px] mb-1 border-l-[3px] transition-colors",
                  selectedId === buyer.id
                    ? "bg-white border-l-green-deep shadow-[0_1px_0_rgba(0,0,0,0.02),0_4px_10px_-8px_rgba(0,0,0,0.12)]"
                    : "border-l-transparent hover:bg-black/[0.025]"
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[13px] font-semibold text-ink truncate">{buyer.company_name}</span>
                  <span
                    className={cn(
                      "shrink-0 px-2 py-0.5 rounded-full text-[10.5px] font-bold font-mono-brand",
                      buyer.tier === "cold" ? "bg-muted text-ink-3" : "bg-green text-green-ink"
                    )}
                  >
                    {buyer.receptiveness_score ?? "—"}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 mt-1 text-[11.5px] text-ink-3">
                  <CountryFlag iso2={buyer.country_iso2 ?? report.target_iso2} size={14} />
                  {buyer.city ?? COUNTRY_NAMES[buyer.country_iso2] ?? buyer.country_iso2}
                </div>
                <span className={cn("inline-flex items-center gap-1 mt-1.5 px-1.5 py-0.5 rounded-md text-[10.5px] font-medium", bucket.chip)}>
                  <span className="w-1 h-1 rounded-full" style={{ background: bucket.dot }} />
                  {STATUS_LABELS[status]}
                </span>
              </button>
            );
          })}
        </div>
      </aside>

      {/* Center panel */}
      <section className="flex-1 min-w-0 overflow-y-auto bg-white px-9 py-7 pb-16 max-[1180px]:px-7">
        {selectedBuyer ? (
          <LeadDetail
            buyer={selectedBuyer}
            report={report}
            outreach={perBuyerEmails[selectedBuyer.company_name]}
            pipelineStatus={getStatus(selectedBuyer.id)}
            onMarkContacted={() => updatePipeline(selectedBuyer.id, "contacted")}
          />
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center text-ink-3">
            <TrendingUp className="w-14 h-14 text-ink-5 mb-4 opacity-40" strokeWidth={1.4} />
            <h3 className="font-serif text-2xl text-ink tracking-tight mb-2">Select a lead to view their profile</h3>
            <p className="text-sm">Click any lead in the sidebar to get started</p>
          </div>
        )}
      </section>

      {/* Right pipeline sidebar */}
      <aside className="w-[340px] shrink-0 border-l border-line bg-white flex flex-col min-h-0 max-[900px]:hidden">
        <div className="px-5 pt-5 pb-3 flex items-baseline justify-between shrink-0">
          <h2 className="font-serif text-[22px] tracking-tight text-ink">Pipeline</h2>
          <span className="text-[11.5px] text-ink-3 font-mono-brand uppercase tracking-[0.06em]">
            {buyers.length} leads
          </span>
        </div>
        <div className="flex-1 overflow-y-auto min-h-0 px-4">
          {PIPELINE_BUCKETS.map((bucket) => {
            const items = buyers.filter((b) => getStatus(b.id) === bucket.key);
            return (
              <div key={bucket.key} className="mb-4">
                <div className="flex items-center justify-between py-2 px-1.5 mb-1.5 border-b border-line">
                  <span className="flex items-center gap-2 text-xs font-semibold text-ink font-mono-brand uppercase tracking-wide">
                    <span className="w-2 h-2 rounded-full" style={{ background: bucket.dot }} />
                    {bucket.label}
                  </span>
                  <span className="text-[11px] font-semibold text-ink-2 bg-muted rounded-full px-2 py-0.5 font-mono-brand">
                    {items.length}
                  </span>
                </div>
                {items.length === 0 ? (
                  <div className="border border-dashed border-line rounded-[9px] py-3.5 text-center text-xs text-ink-4">
                    No leads yet
                  </div>
                ) : (
                  items.map((buyer) => (
                    <button
                      key={buyer.id}
                      type="button"
                      onClick={() => setSelectedId(buyer.id)}
                      className="w-full flex items-center gap-2 border border-line rounded-[9px] px-2.5 py-2 mb-1 text-[12.5px] font-medium text-ink hover:border-[#cfcfcf] hover:shadow-[0_1px_0_rgba(0,0,0,0.02),0_4px_10px_-8px_rgba(0,0,0,0.15)] transition-all group"
                    >
                      <CountryFlag iso2={buyer.country_iso2 ?? report.target_iso2} size={14} />
                      <span className="flex-1 truncate text-left">{buyer.company_name}</span>
                      <GripVertical className="w-3.5 h-3.5 text-ink-4 opacity-0 group-hover:opacity-100 shrink-0" />
                    </button>
                  ))
                )}
              </div>
            );
          })}
        </div>
        <div className="px-5 py-4 border-t border-line text-xs text-ink-3 shrink-0">
          <span className="font-semibold text-ink">{activeConversations}</span> active conversation
          {activeConversations !== 1 ? "s" : ""} ·{" "}
          <span className="font-semibold text-ink">{dealsClosed}</span> deals closed
        </div>
      </aside>
    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function LeadDetail({
  buyer,
  report,
  outreach,
  pipelineStatus,
  onMarkContacted,
}: {
  buyer: any;
  report: any;
  outreach?: Record<string, unknown>;
  pipelineStatus: PipelineStatus;
  onMarkContacted: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const signals: string[] = buyer.receptiveness_signals ?? [];
  const breakdown = scoreBreakdown(signals);
  const signalCards = buildSignalCards(signals, buyer);

  const emailBody = outreach?.email_body as string | undefined;
  const subjectLine = outreach?.subject_line as string | undefined;
  const whyPriority = outreach?.why_priority as string | undefined;

  async function copyEmail() {
    if (!emailBody) return;
    await navigator.clipboard.writeText(
      subjectLine ? `Subject: ${subjectLine}\n\n${emailBody}` : emailBody
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const countryName = COUNTRY_NAMES[buyer.country_iso2] ?? buyer.country_iso2;
  const initials = getInitials(buyer.contact_name ?? buyer.company_name);

  return (
    <>
      <div className="flex items-start justify-between gap-6 pb-5 border-b border-line">
        <div>
          <h1 className="font-serif text-4xl tracking-tight leading-tight text-ink">{buyer.company_name}</h1>
          <div className="flex items-center gap-1.5 mt-1.5 text-[13px] text-ink-3 flex-wrap">
            <CountryFlag iso2={buyer.country_iso2 ?? report.target_iso2} size={16} />
            <span>
              {buyer.city ? `${buyer.city} · ` : ""}
              {countryName}
            </span>
            {buyer.buyer_type && (
              <>
                <span className="text-ink-5">·</span>
                <span>{buyer.buyer_type}</span>
              </>
            )}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="font-serif text-[54px] leading-none tracking-tight text-green-deep">
            {buyer.receptiveness_score ?? "—"}
          </div>
          <p className="mt-1 text-[11px] font-mono-brand uppercase tracking-[0.08em] text-ink-3">
            Match score
          </p>
        </div>
      </div>

      <div className="pt-5 pb-1">
        <p className="text-[11px] font-mono-brand uppercase tracking-[0.08em] text-ink-3 mb-3.5">
          Match breakdown
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            ["Structural fit", breakdown.structural],
            ["Active sourcing", breakdown.sourcing],
            ["Growth", breakdown.growth],
            ["Reachability", breakdown.reach],
          ].map(([label, value]) => (
            <div key={label as string}>
              <div className="flex items-center justify-between text-xs text-ink-2 mb-1.5">
                <span>{label}</span>
                <span className="font-mono-brand font-semibold text-ink">{value}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-green-deep rounded-full" style={{ width: `${value}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {signalCards.length > 0 && (
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {signalCards.map((card) => (
            <div key={card.title} className="border border-line rounded-[14px] p-4">
              <div className="flex items-center gap-2.5 mb-2.5">
                <div className="w-8 h-8 rounded-[9px] bg-[#F4FADF] text-green-deep flex items-center justify-center">
                  {card.icon}
                </div>
                <p className="text-[13px] font-semibold text-ink font-mono-brand uppercase tracking-wide">
                  {card.title}
                </p>
              </div>
              <p className="text-[13.5px] text-ink-2 leading-relaxed">{card.body}</p>
            </div>
          ))}
        </div>
      )}

      {(buyer.contact_name || buyer.contact_email) && (
        <div className="mt-5 border border-line rounded-[14px] px-5 py-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#E8DDB7] to-[#A88D5A] text-white font-semibold text-base flex items-center justify-center shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[11px] font-mono-brand uppercase tracking-[0.08em] text-ink-3 mb-1">
              Decision maker
            </p>
            {buyer.contact_name && (
              <p className="text-base font-semibold text-ink">{buyer.contact_name}</p>
            )}
            {buyer.contact_title && <p className="text-[13px] text-ink-3 mt-0.5">{buyer.contact_title}</p>}
            {buyer.contact_email && (
              <p className="mt-1.5 text-[12.5px] text-ink-2 font-mono-brand">
                {buyer.contact_email}
                {buyer.enrichment_source && (
                  <span className="inline-flex items-center gap-1 ml-2 text-[11px] text-green-deep font-sans font-semibold">
                    <Check className="w-2.5 h-2.5" strokeWidth={3} />
                    verified via {buyer.enrichment_source}
                  </span>
                )}
              </p>
            )}
            {whyPriority && <p className="mt-2 text-xs text-ink-3 italic">{whyPriority}</p>}
          </div>
          <div className="flex gap-2 shrink-0">
            {buyer.linkedin_url && (
              <a
                href={buyer.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="w-9 h-9 rounded-[10px] border border-line bg-white text-ink-2 flex items-center justify-center hover:border-ink-4 hover:text-ink"
                aria-label="LinkedIn"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
            {buyer.contact_email && (
              <a
                href={`mailto:${buyer.contact_email}`}
                className="w-9 h-9 rounded-[10px] border border-line bg-white text-ink-2 flex items-center justify-center hover:border-ink-4 hover:text-ink"
                aria-label="Email"
              >
                <Mail className="w-4 h-4" />
              </a>
            )}
          </div>
        </div>
      )}

      {emailBody && (
        <div className="mt-7">
          <div className="flex items-center justify-between gap-4 mb-3">
            <p className="text-[13px] font-semibold text-ink font-mono-brand uppercase tracking-wide">
              Personalized outreach email
            </p>
          </div>
          <div className="border border-line rounded-[14px] bg-white px-5 py-5 text-sm leading-relaxed text-ink-2 whitespace-pre-wrap">
            {subjectLine && (
              <p className="text-[12.5px] text-ink-3 pb-3 mb-3.5 border-b border-dashed border-line font-mono-brand">
                <span className="font-semibold text-ink">Subject:</span> {subjectLine}
              </p>
            )}
            {emailBody}
          </div>
          <div className="mt-3.5 flex flex-wrap gap-2.5 items-center">
            <button
              type="button"
              onClick={copyEmail}
              className="inline-flex items-center gap-1.5 bg-white text-ink font-semibold text-[13.5px] px-4 py-2.5 rounded-full border border-line hover:border-[#cfcfcf] hover:bg-[#fafafa]"
            >
              {copied ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-deep" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  Copy email
                </>
              )}
            </button>
            {pipelineStatus === "notcontacted" && (
              <button
                type="button"
                onClick={onMarkContacted}
                className="inline-flex items-center gap-1.5 bg-green text-green-ink font-semibold text-[13.5px] px-4 py-2.5 rounded-full hover:bg-green-hover hover:-translate-y-px transition-transform"
              >
                <Check className="w-3.5 h-3.5" strokeWidth={2.4} />
                Mark as contacted
              </button>
            )}
          </div>
          {pipelineStatus === "notcontacted" && (
            <p className="mt-3 text-xs text-ink-3">
              Marking as contacted moves this lead to your pipeline tracker.
            </p>
          )}
        </div>
      )}
    </>
  );
}

function CountryFlag({ iso2, size = 20 }: { iso2: string; size?: number }) {
  const style = FLAG_STYLES[iso2] ?? { background: "linear-gradient(135deg,#cfcfcf,#9ca3af)" };
  return (
    <span
      className="shrink-0 rounded-[1.5px] border border-black/8 inline-block overflow-hidden"
      style={{ width: size, height: Math.round(size * 0.7), ...style }}
      aria-hidden="true"
    />
  );
}

function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diff / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function scoreBreakdown(signals: string[]) {
  let structural = 0;
  let sourcing = 0;
  let growth = 0;
  let reach = 0;

  for (const signal of signals) {
    if (signal.startsWith("Import diversification+:")) structural += 10;
    else if (signal.startsWith("Import diversification:")) {
      structural += signal.includes("does not currently import") ? 25 : 5;
    } else if (signal.startsWith("Active sourcing:")) {
      sourcing += signal.includes("Job posting") ? 20 : 10;
    } else if (signal.startsWith("Growth trajectory:")) {
      growth += 15;
    } else if (signal.startsWith("Trade fair activity:")) {
      reach += 10;
    } else if (signal.startsWith("Decision-maker")) {
      reach += signal.includes("verified email") ? 10 : 5;
    }
  }

  return {
    structural: Math.min(100, Math.round((structural / 35) * 100)),
    sourcing: Math.min(100, Math.round((sourcing / 30) * 100)),
    growth: Math.min(100, Math.round((growth / 15) * 100)),
    reach: Math.min(100, Math.round((reach / 10) * 100)),
  };
}

function buildSignalCards(signals: string[], buyer: { contact_email?: string; linkedin_url?: string }) {
  const cards: { title: string; body: React.ReactNode; icon: React.ReactNode }[] = [];
  const importSig = signals.find((s) => s.startsWith("Import diversification"));
  const sourcingSig = signals.find((s) => s.startsWith("Active sourcing"));
  const growthSig = signals.find((s) => s.startsWith("Growth trajectory"));
  const reachSig = signals.find((s) => s.startsWith("Decision-maker") || s.startsWith("Trade fair"));

  if (importSig) {
    cards.push({
      title: "Import Behavior",
      icon: <TrendingUp className="w-4 h-4" />,
      body: stripSignalPrefix(importSig),
    });
  }
  if (sourcingSig) {
    cards.push({
      title: "Active Sourcing",
      icon: <Briefcase className="w-4 h-4" />,
      body: stripSignalPrefix(sourcingSig),
    });
  }
  if (growthSig) {
    cards.push({
      title: "Growth",
      icon: <TrendingUp className="w-4 h-4" />,
      body: stripSignalPrefix(growthSig),
    });
  }

  const reachParts: string[] = [];
  if (reachSig) reachParts.push(stripSignalPrefix(reachSig));
  if (buyer.contact_email) reachParts.push("Verified email available.");
  if (buyer.linkedin_url) reachParts.push("LinkedIn profile on file.");
  if (reachParts.length) {
    cards.push({
      title: "Reachability",
      icon: <User className="w-4 h-4" />,
      body: reachParts.join(" "),
    });
  }

  return cards.slice(0, 4);
}

function stripSignalPrefix(signal: string): string {
  const idx = signal.indexOf(":");
  return idx >= 0 ? signal.slice(idx + 1).trim() : signal;
}
