import Link from "next/link";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export default async function HomePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user) redirect("/reports");

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Hero */}
      <section className="flex-1 flex items-center justify-center px-4 py-20">
        <div className="max-w-2xl text-center">
          <div className="inline-flex items-center gap-2 bg-slate-100 rounded-full px-4 py-1.5 text-sm text-slate-600 mb-8">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            Built for Balkan manufacturers
          </div>

          <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 leading-tight mb-6">
            Your first EU export market,
            <br />
            in under 5 minutes.
          </h1>

          <p className="text-lg text-slate-500 max-w-xl mx-auto mb-8 leading-relaxed">
            One report. One market. Market demand, exact margin, compliance
            checklist, warm buyer contacts, and a 90-day action plan.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center mb-12">
            <Link href="/signup">
              <Button size="lg" className="w-full sm:w-auto">
                Get started — €29
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="outline" size="lg" className="w-full sm:w-auto">
                Sign in
              </Button>
            </Link>
          </div>

          <p className="text-sm text-slate-400">
            No subscription. One market, one payment.
          </p>
        </div>
      </section>

      {/* Five questions */}
      <section className="border-t border-slate-100 bg-slate-50 px-4 py-16">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold text-slate-900 mb-8 text-center">
            Five questions every manufacturer asks before committing to a new export market
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {[
              ["Does this market actually want my product?", "Import values, CAGR, top suppliers."],
              ["Can I make money after all the costs?", "Exact margin after freight, customs, insurance."],
              ["What do I legally need to sell there?", "3–5 items. Costs. Timelines. Specific providers."],
              ["Who specifically should I contact?", "5 warm buyers scored on observable signals."],
              ["What do I do first thing tomorrow morning?", "Week-by-week 90-day plan. Specific tasks."],
            ].map(([q, a], i) => (
              <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
                  Question {i + 1}
                </p>
                <p className="text-sm font-semibold text-slate-900 mb-1">{q}</p>
                <p className="text-sm text-slate-500">{a}</p>
              </div>
            ))}
            <div className="bg-slate-900 rounded-xl p-5 text-white flex items-center justify-center">
              <div className="text-center">
                <p className="text-2xl font-bold mb-1">€29 / €49</p>
                <p className="text-sm text-slate-300">One report. One market.</p>
                <Link href="/signup" className="mt-3 inline-block">
                  <span className="text-sm font-medium underline underline-offset-2">
                    Get started →
                  </span>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
