import { Eyebrow } from "./ui";

const STEPS = [
  {
    num: "01",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="4" y="4" width="16" height="16" rx="2" />
        <path d="M9 9h6M9 13h6M9 17h3" />
      </svg>
    ),
    title: "Enter your product",
    body: 'HS code, target country, unit cost. Two minutes — no calls, no demos, no sales engineer "discovery".',
  },
  {
    num: "02",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m21 21-4.3-4.3M11 7v8M7 11h8" />
      </svg>
    ),
    title: "We score every buyer",
    body: "Import behaviour, sourcing intent, decision-maker reachability. Ranked by conversion probability — not by who has the loudest logo.",
  },
  {
    num: "03",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M4 4h16v16H4z" />
        <polyline points="4 4 12 13 20 4" />
      </svg>
    ),
    title: "Start conversations",
    body: "Ten leads, personalised emails in German, Italian, French or English. Ready to send from your own inbox.",
  },
];

export function HowItWorks() {
  return (
    <section id="how" className="px-8 py-30 text-center">
      <div className="max-w-310 mx-auto">
        <Eyebrow>How it works</Eyebrow>
        <h2 className="font-serif text-[clamp(34px,4.5vw,56px)] tracking-[-0.02em] leading-[1.05] text-ink mt-4.5 max-w-195 mx-auto">
          Find your EU buyers in three steps
        </h2>
        <p className="text-[16.5px] leading-relaxed text-ink-2 mt-4.5 max-w-140 mx-auto">
          From form submission to ten ranked leads in your inbox. The whole loop
          closes inside an afternoon.
        </p>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          {STEPS.map((step) => (
            <div
              key={step.num}
              className="relative p-8 rounded-xl bg-white border border-line"
            >
              <div className="w-9 h-9 rounded-[10px] bg-muted border border-line flex items-center justify-center text-ink">
                {step.icon}
              </div>
              <span className="absolute top-6 right-6 font-mono-brand text-[11px] text-ink-4 tracking-[0.04em]">
                {step.num}
              </span>
              <h3 className="font-serif text-[22px] tracking-[-0.01em] mt-5 mb-2 font-normal">
                {step.title}
              </h3>
              <p className="text-[14.5px] text-ink-2 leading-relaxed m-0">
                {step.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
