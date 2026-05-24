import Link from "next/link";

export function LandingFooter() {
  return (
    <footer className="border-t border-line px-8 py-7.5">
      <div className="max-w-310 mx-auto flex items-center justify-between gap-5 flex-wrap text-[13px] text-ink-3">
        <Link href="/" className="flex items-center gap-2.5 no-underline text-ink">
          <div className="relative w-5.5 h-5.5 rounded-md bg-ink shrink-0">
            <span className="absolute w-1.75 h-1.75 rounded-sm bg-green top-1 left-1" />
          </div>
          <span className="font-serif text-lg">Quorint</span>
        </Link>

        <nav className="flex gap-[22px]">
          {["Terms", "Privacy", "Contact"].map((item) => (
            <a
              key={item}
              href="#"
              className="text-ink-3 no-underline hover:text-ink transition-colors"
            >
              {item}
            </a>
          ))}
          <a
            href="mailto:hello@quorint.com"
            className="text-ink-3 no-underline hover:text-ink transition-colors"
          >
            hello@quorint.com
          </a>
        </nav>

        <div>Built in Kosovo for Western Balkans manufacturers.</div>
      </div>
    </footer>
  );
}
