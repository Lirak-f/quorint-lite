import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { NewReportForm } from "./form";

export const metadata = {
  title: "New report — Quorint",
};

export default async function NewReportPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return <NewReportForm />;
}
