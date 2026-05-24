"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function Nav({ userEmail }: { userEmail?: string | null }) {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/login");
  }

  const isAuthPage = pathname === "/login" || pathname === "/signup";
  const isLandingPage = pathname === "/";
  if (isAuthPage || isLandingPage) return null;

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <Link href="/reports" className="font-semibold text-slate-900 tracking-tight">
          Quorint
        </Link>

        {userEmail ? (
          <div className="flex items-center gap-4">
            <Link
              href="/reports"
              className={cn(
                "text-sm text-slate-600 hover:text-slate-900",
                pathname.startsWith("/reports") && !pathname.startsWith("/reports/") && "text-slate-900 font-medium"
              )}
            >
              Reports
            </Link>
            <Link href="/new">
              <Button size="sm">New report</Button>
            </Link>
            <button
              onClick={handleSignOut}
              className="text-sm text-slate-500 hover:text-slate-700 cursor-pointer"
            >
              Sign out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" size="sm">Sign in</Button>
            </Link>
            <Link href="/signup">
              <Button size="sm">Get started</Button>
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
