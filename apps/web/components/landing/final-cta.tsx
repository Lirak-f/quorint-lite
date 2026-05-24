import { Eyebrow } from "./ui";
import { EmailSignupRow } from "./hero-section";

export function FinalCTA() {
  return (
    <section className="px-8 pt-30 pb-25 text-center">
      <div className="max-w-310 mx-auto">
        <Eyebrow>Begin</Eyebrow>
        <h2 className="font-serif text-[clamp(34px,4.5vw,56px)] tracking-[-0.02em] leading-[1.05] text-ink mt-4.5 max-w-170 mx-auto">
          Ready to find your first EU buyer?
        </h2>
        <p className="text-[16.5px] leading-relaxed text-ink-2 mt-4.5 max-w-140 mx-auto">
          Join 500+ manufacturers from the Western Balkans who stopped guessing and started exporting.
        </p>
        <EmailSignupRow className="mt-9" />
        <p className="text-xs text-ink-4 mt-5">
          4-hour delivery · refund inside 24h · no subscription
        </p>
      </div>
    </section>
  );
}
