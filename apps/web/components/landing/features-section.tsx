import { FeatureTag } from "./ui";

const FEATURES = [
  {
    tag: "Buyer Intelligence",
    title: "We tell you who is buying right now, not just who exists.",
    body: "Our scoring engine combines import history, active sourcing signals, and decision-maker reachability to rank buyers by their probability of placing an order with you today — not in some abstract future quarter.",
    link: { label: "See how scoring works", href: "#" },
    imgStyle: {
      background: "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, transparent 40%), repeating-linear-gradient(45deg, rgba(60,40,10,0.04) 0 2px, transparent 2px 14px), linear-gradient(180deg, #E5D5B0 0%, #C9A87A 100%)",
      color: "rgba(60,40,10,0.85)",
    },
    imgLabel: "FIG · 02",
    imgCaption: "Manufacturer reviewing import data",
    reverse: false,
  },
  {
    tag: "Outreach Ready",
    title: "Your first email, written and translated before you ask.",
    body: "Every lead arrives with a personalised outreach email in the buyer's own language — German, Italian, French or English — referencing their actual import behaviour. Not a template. Not a generic intro.",
    link: { label: "See a sample lead", href: "#" },
    imgStyle: {
      background: "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, transparent 40%), repeating-linear-gradient(45deg, rgba(0,0,0,0.10) 0 2px, transparent 2px 14px), linear-gradient(180deg, #6B5436 0%, #3D2E1A 100%)",
      color: "rgba(255,250,238,0.92)",
    },
    imgLabel: "FIG · 03",
    imgCaption: "Production line · wide shot · CNC + assembly",
    reverse: true,
  },
  {
    tag: "Pipeline Tracker",
    title: "Track every conversation from first email to closed deal.",
    body: "Mark leads as contacted, replied, meeting booked, deal closed. Your entire export pipeline lives in one place — no spreadsheet sprawl, no losing track of who you sent what to in February.",
    link: { label: "See the dashboard", href: "#" },
    imgStyle: {
      background: "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, transparent 40%), repeating-linear-gradient(45deg, rgba(60,40,10,0.06) 0 2px, transparent 2px 14px), linear-gradient(180deg, #C9A87A 0%, #A07E50 100%)",
      color: "rgba(255,250,238,0.92)",
    },
    imgLabel: "FIG · 04",
    imgCaption: "Handshake · contract · buyer meeting in Munich",
    reverse: false,
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="px-8 pt-15 pb-25">
      {FEATURES.map((feat, i) => (
        <FeatureRow key={i} {...feat} />
      ))}
    </section>
  );
}

function FeatureRow({ tag, title, body, link, imgStyle, imgLabel, imgCaption, reverse }: {
  tag: string; title: string; body: string;
  link: { label: string; href: string };
  imgStyle: React.CSSProperties;
  imgLabel: string; imgCaption: string; reverse: boolean;
}) {
  return (
    <div
      className={`max-w-295 mx-auto mb-24 last:mb-0 grid grid-cols-1 md:grid-cols-2 gap-18 items-center ${
        reverse ? "direction-reverse" : ""
      }`}
    >
      <div className={reverse ? "md:order-2" : ""}>
        <div
          className="rounded-xl overflow-hidden aspect-5/4 relative shadow-[0_1px_0_rgba(0,0,0,0.03),0_22px_40px_-28px_rgba(0,0,0,0.15)]"
          style={imgStyle}
        >
          <div className="absolute inset-0 flex items-end justify-start p-5.5 font-mono-brand text-[11px] tracking-[0.06em] uppercase">
            <div className="flex flex-col gap-1">
              <span>{imgLabel}</span>
              <small className="text-[10px] opacity-60">{imgCaption}</small>
            </div>
            <span className="absolute top-4.5 right-4.5 w-2 h-2 rounded-full bg-current opacity-70" />
          </div>
        </div>
      </div>

      <div className={reverse ? "md:order-1" : ""}>
        <FeatureTag>{tag}</FeatureTag>
        <h3 className="font-serif text-[clamp(28px,3.5vw,42px)] tracking-[-0.018em] leading-tight mt-4.5 mb-4.5 text-ink">
          {title}
        </h3>
        <p className="text-base leading-[1.65] text-ink-2 mb-5.5 max-w-130">
          {body}
        </p>
        <a
          href={link.href}
          className="inline-flex items-center gap-1.5 text-ink font-semibold text-[14.5px] no-underline border-b border-ink pb-0.5 hover:text-green-deep hover:border-green-deep transition-colors"
        >
          {link.label} <span>→</span>
        </a>
      </div>
    </div>
  );
}
