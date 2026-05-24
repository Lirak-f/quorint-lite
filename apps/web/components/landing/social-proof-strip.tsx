const COUNTRIES = [
  { name: "Kosovo", flag: "linear-gradient(180deg,#244AA5 0 50%,#D0A650 50%)" },
  { name: "Albania", flag: "linear-gradient(180deg,#E41E20 50%,#000 50%)" },
  { name: "Serbia", flag: "linear-gradient(180deg,#C6363C 0 33%,#0C4076 33% 66%,#FFFFFF 66%)" },
  { name: "Bosnia", flag: "linear-gradient(90deg,#002395 0 33%,#FFCD00 33% 66%,#FFFFFF 66%)" },
  { name: "N. Macedonia", flag: "linear-gradient(180deg,#D20000 0 50%,#FFE600 50%)" },
];

const STATS = [
  { value: "10", label: "leads" },
  { value: "4 hrs", label: "delivery" },
  { value: "€300", label: "flat price" },
];

export function SocialProofStrip() {
  return (
    <section className="bg-[#F8F7F4] border-t border-b border-line px-8 py-6.5">
      <div className="max-w-310 mx-auto flex items-center justify-between gap-6 flex-wrap">
        <div className="flex items-center gap-[18px] flex-wrap">
          <span className="text-[13px] text-ink-3">
            Manufacturers from these countries use Quorint:
          </span>
          <div className="flex gap-2 flex-wrap">
            {COUNTRIES.map(({ name, flag }) => (
              <span
                key={name}
                className="inline-flex items-center gap-1.75 px-3 py-1.5 pl-2 bg-white border border-line rounded-full text-[13px] font-medium text-ink"
              >
                <span
                  className="inline-block w-4.5 h-3.25 rounded-sm border border-black/8 shrink-0"
                  style={{ background: flag }}
                />
                {name}
              </span>
            ))}
          </div>
        </div>

        <div className="flex gap-8 items-center">
          {STATS.map(({ value, label }) => (
            <div key={label} className="flex flex-col items-start">
              <b className="font-serif text-2xl text-ink">{value}</b>
              <span className="font-mono-brand text-[11.5px] text-ink-3 tracking-[0.04em] uppercase">
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
