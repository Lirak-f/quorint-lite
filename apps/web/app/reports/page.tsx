import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { COUNTRY_FLAGS, COUNTRY_NAMES, formatPercent } from "@/lib/utils";

export const metadata = { title: "Reports — Quorint" };

export default async function ReportsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Find the manufacturer record for this user
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
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Reports</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {reports.length === 0
              ? "No reports yet"
              : `${reports.length} report${reports.length === 1 ? "" : "s"}`}
          </p>
        </div>
        <Link href="/new">
          <Button>New report</Button>
        </Link>
      </div>

      {reports.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-3">
          {reports.map((report) => (
            <ReportRow key={report.id} report={report} />
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

function ReportRow({ report }: { report: ReportRow }) {
  const demand = Array.isArray(report.report_demand)
    ? report.report_demand[0]
    : report.report_demand;
  const date = new Date(report.created_at).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  return (
    <Link href={`/reports/${report.id}`} className="block">
      <div className="bg-white border border-slate-200 rounded-xl px-5 py-4 hover:border-slate-300 hover:shadow-sm transition-all flex items-center gap-4">
        {/* Country + flag */}
        <div className="text-2xl shrink-0">
          {COUNTRY_FLAGS[report.target_iso2] ?? "🌍"}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <p className="text-sm font-semibold text-slate-900">
              {COUNTRY_NAMES[report.target_iso2] ?? report.target_iso2}
            </p>
            <span className="text-xs text-slate-400">·</span>
            <p className="text-sm text-slate-500">HS {report.hs_code}</p>
          </div>
          <p className="text-xs text-slate-400">{date}</p>
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-end">
          {demand?.margin_verdict && (
            <MarginBadge verdict={demand.margin_verdict} margin={demand.margin} />
          )}
          <StatusBadge status={report.status} />
        </div>

        <svg className="w-4 h-4 text-slate-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </Link>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, "default" | "info" | "success" | "error"> = {
    queued: "default",
    running: "info",
    complete: "success",
    failed: "error",
  };
  const labels: Record<string, string> = {
    queued: "Queued",
    running: "Generating…",
    complete: "Complete",
    failed: "Failed",
  };
  return (
    <Badge variant={map[status] ?? "default"}>{labels[status] ?? status}</Badge>
  );
}

function MarginBadge({ verdict, margin }: { verdict: string | null; margin: number | null }) {
  if (!verdict) return null;
  const map: Record<string, "success" | "warning" | "error"> = {
    viable: "success",
    tight: "warning",
    not_viable: "error",
  };
  return (
    <Badge variant={map[verdict] ?? "default"}>
      {margin != null ? formatPercent(margin) : ""}{" "}
      {verdict === "viable" ? "margin" : verdict === "tight" ? "tight" : "not viable"}
    </Badge>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-20 bg-white rounded-xl border border-slate-200">
      <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      </div>
      <h3 className="text-base font-semibold text-slate-900 mb-1">No reports yet</h3>
      <p className="text-sm text-slate-500 mb-6 max-w-xs mx-auto">
        Create your first export market report to see which EU markets fit your product.
      </p>
      <Link href="/new">
        <Button>Create first report</Button>
      </Link>
    </div>
  );
}
