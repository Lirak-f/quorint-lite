import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import { COUNTRY_FLAGS, COUNTRY_NAMES, formatPercent } from "@/lib/utils";

export const metadata = { title: "My lead lists — Quorint" };

export default async function ReportsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  const { data: manufacturer } = await supabase
    .from("manufacturers")
    .select("id")
    .eq("user_id", user.id)
    .maybeSingle();

  let reports: ReportRow[] = [];

  if (manufacturer) {
    const { data } = await supabase
      .from("reports")
      .select(`*, report_demand(margin, margin_verdict)`)
      .eq("manufacturer_id", manufacturer.id)
      .eq("is_test", false)
      .order("created_at", { ascending: false });

    reports = (data ?? []) as ReportRow[];
  }

  return (
    <div className="max-w-[1240px] mx-auto px-8 py-10 pb-20">
      {/* Page header */}
      <div className="flex items-start justify-between gap-6 mb-9">
        <div>
          <h1
            className="text-5xl tracking-tight leading-none text-slate-900"
            style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
          >
            My lead lists
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            {reports.length === 0 ? (
              "No lead lists yet"
            ) : (
              <>
                <span className="font-semibold text-slate-700">
                  {reports.length} {reports.length === 1 ? "list" : "lists"}
                </span>{" "}
                · across {new Set(reports.map((r) => r.target_iso2)).size} EU{" "}
                {new Set(reports.map((r) => r.target_iso2)).size === 1
                  ? "country"
                  : "countries"}
              </>
            )}
          </p>
        </div>
        <Link
          href="/new"
          className="inline-flex items-center gap-2 bg-green text-green-ink font-semibold text-sm px-5 py-3 rounded-full hover:bg-green-hover transition-colors whitespace-nowrap"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New lead list
        </Link>
      </div>

      {reports.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {reports.map((report) => (
            <ReportCard key={report.id} report={report} />
          ))}
        </div>
      )}
    </div>
  );
}

type ReportRow = {
  id: string;
  hs_code: string;
  origin_iso2: string;
  target_iso2: string;
  status: string;
  tier: string;
  created_at: string;
  report_demand?: { margin: number | null; margin_verdict: string | null } | null;
};

function ReportCard({ report }: { report: ReportRow }) {
  const demand = Array.isArray(report.report_demand)
    ? report.report_demand[0]
    : report.report_demand;

  const date = new Date(report.created_at).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  const statusLabel: Record<string, string> = {
    queued: "Queued",
    running: "Processing",
    complete: "Ready",
    failed: "Failed",
  };

  const isProcessing = report.status === "queued" || report.status === "running";
  const isComplete = report.status === "complete";

  return (
    <Link href={`/reports/${report.id}`} className="block group">
      <article className="bg-white border border-slate-200 rounded-[18px] overflow-hidden flex flex-col transition-all duration-150 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-slate-200/80 hover:border-slate-300">
        {/* Warm beige strip header */}
        <div
          className="relative px-5 pt-5 pb-4 flex flex-col justify-end min-h-[100px] bg-warm-1"
        >
          {/* Dot grid texture */}
          <div
            className="absolute inset-0 pointer-events-none opacity-50"
            style={{
              backgroundImage: "radial-gradient(rgba(99,73,33,0.06) 1px, transparent 1px)",
              backgroundSize: "18px 18px",
              maskImage: "radial-gradient(120% 100% at 50% 0%, #000 0%, transparent 80%)",
              WebkitMaskImage: "radial-gradient(120% 100% at 50% 0%, #000 0%, transparent 80%)",
            }}
          />

          {/* Status pill */}
          <div className="absolute top-3.5 right-3.5 z-10">
            <StatusPill status={report.status} label={statusLabel[report.status] ?? report.status} />
          </div>

          {/* Country name as card title */}
          <h3
            className="relative z-10 text-2xl leading-tight tracking-tight text-warm-ink max-w-[calc(100%-72px)]"
            style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
          >
            {COUNTRY_NAMES[report.target_iso2] ?? report.target_iso2}
          </h3>
        </div>

        {/* Card body */}
        <div className="px-5 pt-3.5 pb-5 flex flex-col flex-1">
          {/* Meta row */}
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-3.5">
            <span
              className="font-mono font-medium text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded"
              style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "11.5px" }}
            >
              HS {report.hs_code}
            </span>
            <span className="text-slate-300">·</span>
            <span className="flex items-center gap-1.5">
              <span className="text-lg leading-none">
                {COUNTRY_FLAGS[report.target_iso2] ?? "🌍"}
              </span>
              <span className="text-slate-500">{date}</span>
            </span>
          </div>

          <div className="h-px bg-slate-100 -mx-5 mb-3.5" />

          {/* Processing progress */}
          {isProcessing && (
            <div className="mb-3.5">
              <div className="h-1 rounded-full bg-slate-100 overflow-hidden relative">
                <div className="absolute top-0 left-0 h-full rounded-full bg-green-deep animate-pulse" style={{ width: "42%" }} />
              </div>
              <p
                className="mt-1.5 text-slate-400"
                style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "10.5px", letterSpacing: "0.06em", textTransform: "uppercase" }}
              >
                Generating report…
              </p>
            </div>
          )}

          {/* Margin badge for complete reports */}
          {isComplete && demand?.margin_verdict && (
            <div className="mb-3.5">
              <MarginBadge verdict={demand.margin_verdict} margin={demand.margin} />
            </div>
          )}

          {/* CTA */}
          <div className="mt-auto">
            {isProcessing ? (
              <button
                disabled
                className="w-full inline-flex items-center justify-center gap-2 bg-slate-100 text-slate-400 font-semibold text-sm px-4 py-2.5 rounded-full cursor-not-allowed"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="9" />
                  <polyline points="12 7 12 12 15 14" />
                </svg>
                Processing
              </button>
            ) : (
              <div className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-700 group-hover:text-slate-900 transition-colors">
                View report
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </div>
            )}
          </div>
        </div>
      </article>
    </Link>
  );
}

function StatusPill({ status, label }: { status: string; label: string }) {
  if (status === "running" || status === "queued") {
    return (
      <span className="inline-flex items-center gap-1.5 bg-white text-[#3B2F1E] text-xs font-semibold px-2.5 py-1 rounded-full">
        <span className="w-1.5 h-1.5 rounded-full bg-[#9CC129] animate-pulse" />
        {label}
      </span>
    );
  }
  if (status === "complete") {
    return (
      <span className="inline-flex items-center gap-1.5 bg-[#EBF6C8] text-[#1F2A07] text-xs font-semibold px-2.5 py-1 rounded-full">
        <span className="w-1.5 h-1.5 rounded-full bg-[#9CC129]" />
        {label}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 bg-white text-slate-400 text-xs font-semibold px-2.5 py-1 rounded-full">
      <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
      {label}
    </span>
  );
}

function MarginBadge({
  verdict,
  margin,
}: {
  verdict: string | null;
  margin: number | null;
}) {
  if (!verdict) return null;
  const styles: Record<string, string> = {
    viable: "bg-[#EBF6C8] text-[#1F2A07]",
    tight: "bg-[#FBF1DA] text-[#5A4416]",
    not_viable: "bg-red-50 text-red-800",
  };
  const labels: Record<string, string> = {
    viable: "margin",
    tight: "tight",
    not_viable: "not viable",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-md ${styles[verdict] ?? "bg-slate-100 text-slate-600"}`}
    >
      {margin != null ? formatPercent(margin) : ""}
      {" "}
      {labels[verdict] ?? verdict}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex justify-center mt-9">
      <div
        className="w-full max-w-[880px] rounded-[28px] p-14 relative overflow-hidden grid gap-12 items-center bg-warm-1"
        style={{
          gridTemplateColumns: "1.05fr 1fr",
          boxShadow: "0 1px 0 rgba(80,60,30,0.04), 0 30px 60px -30px rgba(99,73,33,0.22)",
        }}
      >
        {/* Dot grid texture */}
        <div
          className="absolute inset-0 pointer-events-none opacity-40"
          style={{
            backgroundImage: "radial-gradient(rgba(99,73,33,0.06) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
            maskImage: "radial-gradient(140% 100% at 0% 0%, #000 0%, transparent 70%)",
            WebkitMaskImage: "radial-gradient(140% 100% at 0% 0%, #000 0%, transparent 70%)",
          }}
        />

        {/* Left text */}
        <div className="relative z-10">
          <div
            className="flex items-center gap-2 text-[#7a6741] mb-4"
            style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "11.5px", letterSpacing: "0.1em", textTransform: "uppercase" }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#9CC129]" />
            Get started
          </div>

          <h2
            className="text-[42px] leading-tight tracking-tight text-[#3B2F1E] mb-4"
            style={{ fontFamily: "'DM Serif Display', Georgia, serif" }}
          >
            Your first EU buyers are waiting
          </h2>

          <p className="text-[15px] text-[#5e4f33] leading-relaxed max-w-[38ch] mb-6">
            Create a lead list to find the 10 wholesale buyers most likely to purchase your product — scored, ranked, and ready to contact.
          </p>

          <ul className="flex flex-col gap-2 mb-7">
            {[
              "One HS code, one country, ten verified buyers",
              "Decision-maker emails + a personalised outreach draft",
              "Delivered in ~4 hours, €300 flat",
            ].map((item) => (
              <li key={item} className="flex items-center gap-2.5 text-[13.5px] text-[#5e4f33]">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9CC129" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                {item}
              </li>
            ))}
          </ul>

          <Link
            href="/new"
            className="inline-flex items-center gap-2 bg-green text-green-ink font-semibold text-[15px] px-6 py-3.5 rounded-full hover:bg-green-hover transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Create my first lead list
          </Link>
        </div>

        {/* Right image */}
        <div
          className="relative z-10 rounded-[20px] overflow-hidden aspect-[4/5]"
          style={{ boxShadow: "0 20px 50px -20px rgba(99,73,33,0.4)", background: "#d9c89a" }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=900&q=80&auto=format&fit=crop"
            alt="Manufacturer reviewing buyer leads"
            className="w-full h-full object-cover block"
          />
          <div
            className="absolute left-3.5 bottom-3.5 bg-white/90 backdrop-blur-sm text-[#3B2F1E] px-3 py-1.5 rounded-full"
            style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "10.5px", letterSpacing: "0.06em", textTransform: "uppercase" }}
          >
            Pristina · 11:42
          </div>
        </div>
      </div>
    </div>
  );
}
