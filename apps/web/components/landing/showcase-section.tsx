export function ShowcaseSection() {
  return (
    <section className="px-8 pb-[90px] pt-10">
      <div className="flex items-center justify-center gap-2 text-[13px] text-ink-3 mb-4.5">
        <span className="w-1.5 h-1.5 rounded-full bg-green-deep shadow-[0_0_0_4px_rgba(200,232,78,0.25)]" />
        Your lead list — delivered in 4 hours
      </div>

      <div
        className="max-w-310 mx-auto rounded-3xl p-10 relative overflow-hidden"
        style={{
          background: "radial-gradient(110% 80% at 90% 10%, #F5E8C5 0%, transparent 55%), radial-gradient(80% 60% at 10% 100%, #EFD9A8 0%, transparent 60%), linear-gradient(180deg, #F6EDD3 0%, #ECD8AE 100%)",
          boxShadow: "0 1px 0 rgba(0,0,0,0.03), 0 30px 60px -30px rgba(99,73,33,0.25)",
        }}
      >
        <div
          className="absolute inset-0 pointer-events-none opacity-50"
          style={{
            backgroundImage: "radial-gradient(rgba(99,73,33,0.06) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
            maskImage: "linear-gradient(180deg, transparent, #000 30%, #000 70%, transparent)",
            WebkitMaskImage: "linear-gradient(180deg, transparent, #000 30%, #000 70%, transparent)",
          }}
        />

        <div className="relative z-10">
          <div className="flex items-center justify-between mb-6">
            <div className="font-serif text-[22px] text-warm-ink">
              Order #Q-2841 · Eichenmöbel · Germany
            </div>
            <div className="font-mono-brand text-[11px] tracking-[0.04em] uppercase text-[#7a6741]">
              Delivered 14:23 CET · 10 of 10 buyers ranked
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1.05fr_1fr] gap-7">
            <LeadList />
            <ManufacturerPlaceholder />
          </div>
        </div>
      </div>
    </section>
  );
}

function LeadList() {
  const leads = [
    {
      flag: "linear-gradient(180deg,#000 0 33%,#DD0000 33% 66%,#FFCC00 66%)",
      company: "Möbelhaus Westfalen GmbH",
      location: "Dortmund · Germany · €18M revenue",
      score: "Match 91%",
      signal: { icon: "trend", text: <>Imported <b>€1.8M</b> · Growing <b>34% YoY</b></> },
      dm: { initials: "SK", name: "Stefan König", role: "Head of Procurement · 11 yrs" },
      active: true,
    },
    {
      flag: "linear-gradient(90deg,#009246 0 33%,#FFFFFF 33% 66%,#CE2B37 66%)",
      company: "Bertinelli Arredamenti S.r.l.",
      location: "Milan · Italy · €11M revenue",
      score: "Match 84%",
      signal: { icon: "search", text: <>Posted <b>2 RFQs</b> for solid-oak tables · last 30 days</> },
      dm: { initials: "LB", name: "Lucia Bertinelli", role: "Direttore Acquisti · 8 yrs" },
      active: false,
    },
    {
      flag: "linear-gradient(180deg,#AE1C28 0 33%,#FFFFFF 33% 66%,#21468B 66%)",
      company: "Skandi Living B.V.",
      location: "Utrecht · Netherlands · €9M revenue",
      score: "Match 81%",
      signal: { icon: "person", text: <>Hired procurement lead · sourcing East-EU suppliers</> },
      dm: { initials: "PV", name: "Pieter de Vries", role: "Inkoopmanager · 6 yrs" },
      active: false,
    },
  ];

  return (
    <div className="flex flex-col gap-3.5">
      {leads.map((lead) => (
        <LeadCard key={lead.company} {...lead} />
      ))}
      <div className="text-center font-mono-brand text-[11px] text-[#7a6741] tracking-[0.08em] mt-0.5">
        + 7 MORE BUYERS RANKED
      </div>
    </div>
  );
}

function LeadCard({ flag, company, location, score, signal, dm, active }: {
  flag: string; company: string; location: string; score: string;
  signal: { icon: string; text: React.ReactNode };
  dm: { initials: string; name: string; role: string };
  active: boolean;
}) {
  return (
    <div
      className={`bg-white rounded-[14px] p-4.5 pb-4 border border-[rgba(80,60,30,0.05)] ${
        active
          ? "shadow-[0_1px_0_rgba(80,60,30,0.04),0_22px_44px_-22px_rgba(60,40,10,0.35)] -translate-y-px"
          : "shadow-[0_1px_0_rgba(80,60,30,0.04),0_14px_30px_-22px_rgba(60,40,10,0.25)]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-[15px] font-semibold text-ink">
            <span className="inline-block w-4.5 h-[13px] rounded-sm border border-black/8 shrink-0" style={{ background: flag }} />
            {company}
          </div>
          <div className="text-[12.5px] text-ink-3 mt-[3px]">{location}</div>
        </div>
        <div className="inline-flex items-center gap-1.25 px-2.5 py-1.25 rounded-full bg-green text-green-ink text-[11.5px] font-bold tracking-[0.02em] shrink-0">
          <span className="w-1.25 h-1.25 rounded-full bg-green-deep" />
          {score}
        </div>
      </div>

      <div className="mt-3 px-3 py-[9px] bg-[#FAFAF7] rounded-lg text-[12.5px] text-ink-2 flex items-center gap-2 border border-[#F0EEE6]">
        <SignalIcon type={signal.icon} />
        <span>{signal.text}</span>
      </div>

      <div className="mt-3 pt-3 border-t border-dashed border-[#E9E3D2] flex items-center gap-2.5">
        <div className="w-7.5 h-7.5 rounded-full bg-gradient-to-br from-[#E8DDB7] to-[#C8B583] flex items-center justify-center text-[11px] font-semibold text-warm-ink shrink-0">
          {dm.initials}
        </div>
        <div>
          <div className="text-[13px] font-semibold text-ink">{dm.name}</div>
          <div className="text-[11.5px] text-ink-3">{dm.role}</div>
        </div>
        <div className="ml-auto text-ink-4">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M13 5l7 7-7 7" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function SignalIcon({ type }: { type: string }) {
  if (type === "trend") return (
    <svg className="text-green-deep shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
      <polyline points="16 7 22 7 22 13" />
    </svg>
  );
  if (type === "search") return (
    <svg className="text-green-deep shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" />
    </svg>
  );
  return (
    <svg className="text-green-deep shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 11h-6M19 8v6" />
    </svg>
  );
}

function ManufacturerPlaceholder() {
  return (
    <div className="rounded-[14px] overflow-hidden relative min-h-[420px] shadow-[0_1px_0_rgba(80,60,30,0.04),0_14px_30px_-22px_rgba(60,40,10,0.25)]">
      <div
        className="absolute inset-0 flex items-end justify-start p-[22px] text-[rgba(255,250,238,0.92)] font-mono-brand text-[11px] tracking-[0.06em] uppercase"
        style={{
          background: "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, transparent 40%), repeating-linear-gradient(45deg, rgba(60,40,10,0.06) 0 2px, transparent 2px 14px), linear-gradient(180deg, #C9A87A 0%, #A07E50 100%)",
        }}
      >
        <div className="flex flex-col gap-1">
          <span>FIG · 01</span>
          <small className="text-[rgba(255,250,238,0.65)] text-[10px]">Craftsman · solid oak bench · Pristina workshop</small>
        </div>
        <span className="absolute top-4.5 right-4.5 w-2 h-2 rounded-full bg-white/70" />
      </div>

      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[rgba(40,28,8,0.45)] pointer-events-none" />

      <div className="absolute top-4.5 left-4.5 bg-white/94 rounded-lg px-2.75 py-1.75 text-[11.5px] font-semibold text-ink flex items-center gap-1.75 font-mono-brand tracking-[0.02em] backdrop-blur-sm">
        <span className="w-1.5 h-1.5 rounded-full bg-[#22C55E] shadow-[0_0_0_3px_rgba(34,197,94,0.2)] animate-pulse" />
        DRVODELO PRISTINA · KS
      </div>

      <div className="absolute left-4.5 bottom-4.5 right-4.5 bg-white/96 backdrop-blur-md rounded-xl px-4 py-3.5 flex items-center justify-between gap-3.5 shadow-[0_12px_30px_-10px_rgba(0,0,0,0.25)]">
        <div>
          <div className="text-[13.5px] font-semibold text-ink">First email · German, ready to send</div>
          <div className="text-[11.5px] text-ink-3 mt-0.5 font-mono-brand tracking-[0.02em]">
            SUBJ · SECHS WOCHEN LIEFERZEIT AB PRISTINA
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-semibold text-green-ink px-2.5 py-1.5 bg-green rounded-full shrink-0">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          Ready
        </div>
      </div>
    </div>
  );
}
