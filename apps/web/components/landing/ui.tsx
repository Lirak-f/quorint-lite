export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 font-mono-brand text-[11.5px] tracking-[0.08em] uppercase text-ink-3 px-3 py-1.5 bg-muted border border-line rounded-full">
      <span className="w-1.5 h-1.5 rounded-full bg-green-deep" />
      {children}
    </span>
  );
}

export function FeatureTag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#F3F1EA] text-[#5C5440] text-xs font-medium font-mono-brand tracking-[0.06em] uppercase">
      <span className="w-1.5 h-1.5 rounded-full bg-green-deep" />
      {children}
    </span>
  );
}

export function CheckIcon() {
  return (
    <span className="w-4.5 h-4.5 rounded-full bg-[#EBF6C8] text-green-deep inline-flex items-center justify-center shrink-0 mt-px">
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12" />
      </svg>
    </span>
  );
}

export function ArrowRight({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  );
}
