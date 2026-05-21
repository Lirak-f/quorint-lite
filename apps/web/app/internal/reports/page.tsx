import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { COUNTRY_FLAGS, COUNTRY_NAMES, formatPercent } from "@/lib/utils";

export const metadata = { title: "Internal — Quorint" };

export default async function InternalReportsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Check admin role
  const { data: profile } = await supabase
    .from("manufacturers")
    .select("user_id")
    .eq("user_id", user.id)
    .maybeSingle();

  // Simple admin check: user metadata role OR allow if user is owner of any test report
  // Real implementation: Supabase custom claims or a separate admin table
  const { data: adminRpc } = await supabase.rpc("is_admin", { uid: user.id }).maybeSingle();
  if (!adminRpc && !profile) {
    redirect("/reports");
  }

  const { data: testReports } = await supabase
    .from("reports")
    .select(`*, report_demand(margin, margin_verdict)`)
    .eq("is_test", true)
    .order("created_at", { ascending: false });

  const reports = testReports ?? [];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-semibold text-slate-900">Internal reports</h1>
            <Badge variant="warning">QA only</Badge>
          </div>
          <p className="text-sm text-slate-500">
            Test reports — not counted in metrics. {reports.length} report{reports.length !== 1 ? "s" : ""}.
          </p>
        </div>
      </div>

      {reports.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <p className="text-sm text-slate-500">No test reports yet.</p>
          <p className="text-xs text-slate-400 mt-2">
            Run: <code className="bg-slate-100 px-1.5 py-0.5 rounded">python test_report.py --hs 940360 --origin XK --target AT --cost 200</code>
          </p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Market
                </th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  HS Code
                </th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Origin
                </th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Margin
                </th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Status
                </th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Date
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {reports.map((report: any) => {
                const demand = Array.isArray(report.report_demand)
                  ? report.report_demand[0]
                  : report.report_demand;
                const date = new Date(report.created_at).toLocaleDateString("en-GB", {
                  day: "numeric",
                  month: "short",
                  year: "2-digit",
                });

                return (
                  <tr key={report.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-3.5">
                      <Link
                        href={`/reports/${report.id}`}
                        className="flex items-center gap-2 hover:text-slate-900"
                      >
                        <span className="text-base">{COUNTRY_FLAGS[report.target_iso2] ?? "🌍"}</span>
                        <span className="font-medium text-slate-900">
                          {COUNTRY_NAMES[report.target_iso2] ?? report.target_iso2}
                        </span>
                      </Link>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-slate-600">
                      {report.hs_code}
                    </td>
                    <td className="px-5 py-3.5 text-slate-600">{report.origin_iso2}</td>
                    <td className="px-5 py-3.5">
                      {demand?.margin_verdict ? (
                        <Badge
                          variant={
                            demand.margin_verdict === "viable"
                              ? "success"
                              : demand.margin_verdict === "tight"
                              ? "warning"
                              : "error"
                          }
                        >
                          {demand.margin != null ? formatPercent(demand.margin) : ""}
                          {" "}
                          {demand.margin_verdict}
                        </Badge>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={report.status} />
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 text-xs">{date}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
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
    running: "Running",
    complete: "Complete",
    failed: "Failed",
  };
  return (
    <Badge variant={map[status] ?? "default"}>{labels[status] ?? status}</Badge>
  );
}
