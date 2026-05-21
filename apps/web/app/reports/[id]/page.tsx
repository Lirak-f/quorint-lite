import { createClient } from "@/lib/supabase/server";
import { notFound, redirect } from "next/navigation";
import { ReportView } from "./report-view";

export const metadata = { title: "Report — Quorint" };

export default async function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: report } = await supabase
    .from("reports")
    .select(
      `
      *,
      report_demand(*),
      report_compliance(*),
      report_buyers(*)
    `
    )
    .eq("id", id)
    .single();

  if (!report) notFound();

  // Only allow owner to view (or admin via is_test)
  const { data: manufacturer } = await supabase
    .from("manufacturers")
    .select("user_id")
    .eq("id", report.manufacturer_id)
    .single();

  if (manufacturer && manufacturer.user_id !== user.id) {
    // Check admin
    const { data: adminCheck } = await supabase.rpc("is_admin", { uid: user.id });
    if (!adminCheck) redirect("/reports");
  }

  return <ReportView report={report} />;
}
