import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const API_BASE = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Proxy to FastAPI POST /api/reports.
 * Returns { report_id, price_id } — frontend opens Paddle overlay checkout.
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

  let data: Record<string, unknown> = {};
  if (text) {
    try {
      data = JSON.parse(text) as Record<string, unknown>;
    } catch {
      return NextResponse.json(
        { error: text || "Upstream error", detail: text },
        { status: upstream.ok ? 502 : upstream.status }
      );
    }
  }

  if (!upstream.ok) {
    const detail = data.detail;
    const error =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((item) =>
                item && typeof item === "object" && "msg" in item
                  ? String((item as { msg: string }).msg)
                  : String(item)
              )
              .join("; ")
          : typeof data.error === "string"
            ? data.error
            : "Failed to create report";
    return NextResponse.json({ error, detail }, { status: upstream.status });
  }

  return NextResponse.json(data);
}
