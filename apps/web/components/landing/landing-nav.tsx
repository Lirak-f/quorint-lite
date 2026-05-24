"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export function LandingNav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-50 bg-white/92 backdrop-blur-[10px] transition-[border-color] duration-200 ${
        scrolled ? "border-b border-line" : "border-b border-transparent"
      }`}
    >
      <div className="max-w-310 mx-auto px-8 py-4.5 flex items-center justify-between gap-8">
        <Link href="/" className="flex items-center gap-2.5 no-underline text-ink">
          <BrandMark />
          <span className="font-serif text-[22px]">Quorint</span>
        </Link>

        <nav className="hidden md:flex gap-[30px]">
          {[
            ["How it works", "#how"],
            ["Product", "#features"],
            ["Pricing", "#pricing"],
          ].map(([label, href]) => (
            <a
              key={href}
              href={href}
              className="text-ink-2 text-sm font-medium no-underline hover:text-ink transition-colors"
            >
              {label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2.5">
          <Link
            href="/login"
            className="inline-flex items-center justify-center px-5 py-3 rounded-full text-[14.5px] font-semibold text-ink hover:bg-muted transition-colors no-underline"
          >
            Log in
          </Link>
          <Link
            href="/signup"
            className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-full text-[14.5px] font-semibold bg-green text-green-ink hover:bg-green-hover hover:-translate-y-px shadow-sm transition-all no-underline"
          >
            Get started
          </Link>
        </div>
      </div>
    </header>
  );
}

function BrandMark() {
  return (
    <div className="relative w-6.5 h-6.5 rounded-[7px] bg-ink flex items-center justify-center shrink-0">
      <span className="absolute w-2 h-2 rounded-sm bg-green top-1.25 left-1.25" />
    </div>
  );
}
