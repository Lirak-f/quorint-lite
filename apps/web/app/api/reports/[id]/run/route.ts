import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const API_BASE = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const upstream = await fetch(`${API_BASE}/api/reports/${id}/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.access_token}`,
    },
  });

  if (!upstream.ok) {
    const text = await upstream.text();
    return NextResponse.json({ error: text }, { status: upstream.status });
  }

  const data = await upstream.json();
  return NextResponse.json(data, { status: 202 });
}
