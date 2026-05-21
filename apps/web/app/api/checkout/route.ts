import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Proxy to FastAPI POST /api/reports.
 * Returns { report_id, checkout_url } — frontend redirects to checkout_url.
 */
export async function POST(req: Request) {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json();

  const upstream = await fetch(`${API_BASE}/api/reports`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify(body),
  });

  const text = await upstream.text();
  console.log("[checkout] upstream status:", upstream.status, "body:", text);

  let data: Record<string, unknown>;
  try {
    data = JSON.parse(text);
  } catch {
    return NextResponse.json(
      { error: `Upstream error: ${text}` },
      { status: 502 }
    );
  }

  if (!upstream.ok) {
    return NextResponse.json(
      { error: data.detail ?? "Failed to create report" },
      { status: upstream.status }
    );
  }

  return NextResponse.json(data);
}
