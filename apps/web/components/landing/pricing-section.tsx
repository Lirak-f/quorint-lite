import { Eyebrow, CheckIcon, ArrowRight } from "./ui";

const FEATURES = [
  "10 buyers scored and ranked",
  "Personalised email in buyer's language",
  "Decision maker: name, title, verified email",
  "Signal rationale for each lead",
  "Pipeline tracker included",
  "No subscription — pay once",
];

export function PricingSection() {
  return (
    <section id="pricing" className="px-8 py-25 text-center bg-[#FBFAF7] border-t border-b border-line">
      <div className="max-w-310 mx-auto">
        <Eyebrow>Simple pricing</Eyebrow>
        <h2 className="font-serif text-[clamp(34px,4.5vw,56px)] tracking-[-0.02em] leading-[1.05] text-ink mt-4.5 max-w-195 mx-auto">
          One price. No subscriptions.
        </h2>
        <p className="text-[16.5px] leading-relaxed text-ink-2 mt-4.5 max-w-140 mx-auto">
          Pay per lead list. Order when you're ready to enter a market. Come back when you're ready for the next one.
        </p>

        <div className="mt-14 max-w-130 mx-auto bg-white border border-line rounded-3xl p-10 text-left shadow-[0_1px_0_rgba(0,0,0,0.02),0_24px_50px_-30px_rgba(0,0,0,0.12)]">
          <span className="inline-flex items-center gap-1.5 bg-green text-green-ink rounded-full px-2.75 py-1.25 text-[11.5px] font-bold font-mono-brand tracking-[0.06em] uppercase">
            Most popular · single market
          </span>

          <div className="flex items-baseline gap-2.5 mt-4">
            <span className="font-serif text-[76px] leading-none tracking-[-0.02em]">€300</span>
            <span className="text-sm text-ink-3">flat · VAT excl.</span>
          </div>
          <div className="text-sm text-ink-3 mt-1.5">
            Per lead list · one country · 10 scored buyers
          </div>

          <hr className="my-6 border-line" />

          <ul className="flex flex-col gap-3 mb-7">
            {FEATURES.map((f) => (
              <li key={f} className="flex items-start gap-2.5 text-[14.5px] text-ink-2">
                <CheckIcon />
                {f}
              </li>
            ))}
          </ul>

          <a
            href="/signup"
            className="w-full inline-flex items-center justify-center gap-2 px-6.5 py-[15px] rounded-full text-[15.5px] font-semibold bg-green text-green-ink hover:bg-green-hover hover:-translate-y-px transition-all no-underline"
          >
            Get your lead list
            <ArrowRight size={14} />
          </a>

          <p className="text-[13px] text-ink-3 text-center mt-3.5">
            Need 20 or 30 leads?{" "}
            <a href="#" className="text-ink-2 underline">
              We have options.
            </a>
          </p>
        </div>
      </div>
    </section>
  );
}
