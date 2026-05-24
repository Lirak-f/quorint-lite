"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    let valid = true;
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailError("Enter a valid work email.");
      valid = false;
    }
    if (!password) {
      setPasswordError("Password is required.");
      valid = false;
    }
    if (!valid) return;

    setLoading(true);
    setEmailError(null);
    setPasswordError(null);

    const { error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      setPasswordError(error.message);
      setLoading(false);
      return;
    }

    router.push("/reports");
    router.refresh();
  }

  return (
    <div className="grid min-h-screen h-screen" style={{ gridTemplateColumns: "45fr 55fr" }}>

      {/* ── LEFT PANEL ── */}
      <aside
        className="hidden lg:flex flex-col relative overflow-hidden px-14 py-12"
        style={{
          background: "#F5EDD6",
          borderTopRightRadius: 36,
          borderBottomRightRadius: 36,
        }}
      >
        {/* dot pattern */}
        <div
          className="absolute inset-0 pointer-events-none opacity-50"
          style={{
            backgroundImage: "radial-gradient(rgba(99,73,33,0.06) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
            maskImage: "linear-gradient(180deg, transparent, #000 25%, #000 75%, transparent)",
            WebkitMaskImage: "linear-gradient(180deg, transparent, #000 25%, #000 75%, transparent)",
          }}
        />

        {/* Brand */}
        <div className="relative z-10">
          <Link href="/" className="inline-flex items-center gap-2.5 no-underline">
            <div className="relative w-6.5 h-6.5 rounded-[7px] bg-ink flex-shrink-0" style={{ width: 26, height: 26 }}>
              <span className="absolute w-2 h-2 rounded-[2px] bg-green" style={{ top: 5, left: 5 }} />
            </div>
            <span className="font-serif text-[22px] text-ink" style={{ letterSpacing: "-0.01em" }}>Quorint</span>
          </Link>
        </div>

        {/* Mid content */}
        <div className="relative z-10 my-auto max-w-[520px]">
          <span
            className="inline-flex items-center gap-2 text-[13px] font-medium text-warm-ink rounded-full px-3.5 py-2"
            style={{ background: "rgba(255,255,255,0.7)", border: "1px solid rgba(59,47,30,0.08)" }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full bg-green-deep flex-shrink-0"
              style={{ boxShadow: "0 0 0 3px rgba(200,232,78,0.35)" }}
            />
            500+ manufacturers trust us
          </span>

          <h1
            className="font-serif text-ink mt-[22px] mb-0"
            style={{ fontSize: "clamp(36px,4.2vw,52px)", lineHeight: 1.05, letterSpacing: "-0.02em" }}
          >
            Your next EU buyer<br />
            is one lead list <em>away</em>
          </h1>

          {/* Lead card */}
          <article
            className="mt-8 bg-white rounded-2xl p-5 max-w-[460px]"
            style={{
              boxShadow: "0 1px 0 rgba(80,60,30,0.04), 0 22px 44px -24px rgba(60,40,10,0.30)",
              border: "1px solid rgba(80,60,30,0.05)",
            }}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 text-[15px] font-semibold text-ink">
                  <span
                    className="w-[18px] h-[13px] rounded-[2px] flex-shrink-0"
                    style={{
                      background: "linear-gradient(180deg,#000 0 33%,#DD0000 33% 66%,#FFCC00 66%)",
                      border: "1px solid rgba(0,0,0,0.08)",
                    }}
                  />
                  Müller Naturkost GmbH
                </div>
                <div className="text-[12.5px] text-ink-3 mt-0.5">Munich · Germany</div>
              </div>
              <span
                className="inline-flex items-center gap-1.5 text-[11.5px] font-bold text-green-ink rounded-full px-2.5 py-1.5 flex-shrink-0"
                style={{ background: "#C8E84E", letterSpacing: "0.02em" }}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-green-deep" />
                91% Match
              </span>
            </div>

            <div
              className="mt-3 flex items-center gap-2 text-[12.5px] text-ink-2 rounded-lg px-3 py-2.5"
              style={{ background: "#FAFAF7", border: "1px solid #F0EEE6" }}
            >
              <svg className="text-green-deep flex-shrink-0" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>
              </svg>
              Imported <strong className="text-ink font-semibold mx-0.5">€1.8M</strong> · <strong className="text-ink font-semibold mx-0.5">+34% YoY</strong>
            </div>

            <div className="mt-3 pt-3 flex items-center gap-2.5" style={{ borderTop: "1px dashed #E9E3D2" }}>
              <div
                className="w-[30px] h-[30px] rounded-full flex items-center justify-center text-[11px] font-semibold text-warm-ink flex-shrink-0"
                style={{ background: "linear-gradient(135deg,#E8DDB7,#C8B583)" }}
              >
                KW
              </div>
              <div>
                <div className="text-[13px] font-semibold text-ink">Klaus Weber</div>
                <div className="text-[11.5px] text-ink-3">Head of Purchasing</div>
              </div>
            </div>

            <div className="mt-3.5">
              <span
                className="inline-flex items-center gap-1.5 text-[12px] font-semibold text-green-ink rounded-full px-3 py-1.5"
                style={{ background: "#C8E84E" }}
              >
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                Email ready in German
              </span>
            </div>
          </article>

          {/* Micro stats */}
          <div className="mt-6 flex gap-7 max-w-[460px]">
            {[
              { icon: <path d="M3 7h18M3 12h18M3 17h12"/>, value: "10", label: "Leads" },
              { icon: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>, value: "4h", label: "Delivery" },
              { icon: <path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>, value: "€300", label: "Flat price" },
            ].map(({ icon, value, label }) => (
              <div key={label} className="flex flex-col items-start gap-1">
                <div className="flex items-center gap-1.5 font-serif text-[22px] text-ink leading-none">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="opacity-65 text-warm-ink">
                    {icon}
                  </svg>
                  {value}
                </div>
                <div className="font-mono text-[11px] text-warm-ink opacity-65 uppercase tracking-widest">{label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10 mt-auto flex justify-between font-mono text-[11px] uppercase tracking-widest text-warm-ink opacity-55">
          <span>© Quorint 2026</span>
          <span>Built in Kosovo</span>
        </div>
      </aside>

      {/* ── RIGHT PANEL ── */}
      <section className="flex flex-col bg-white px-6 py-12 lg:px-14 overflow-auto">
        <div className="flex items-center justify-end text-[13px] text-ink-3">
          <span>New here?</span>
          <Link
            href="/signup"
            className="text-ink font-medium ml-1.5 no-underline"
            style={{ borderBottom: "1px solid #0a0a0a", paddingBottom: 1 }}
          >
            Get started →
          </Link>
        </div>

        <div className="my-auto w-full max-w-[420px] self-center">
          <h2
            className="font-serif font-normal text-ink m-0"
            style={{ fontSize: 40, letterSpacing: "-0.02em", lineHeight: 1.1 }}
          >
            Welcome back
          </h2>
          <p className="text-[15px] text-ink-3 mt-2.5 mb-8">Sign in to access your lead lists.</p>

          <form onSubmit={handleSubmit} noValidate>
            {/* Email */}
            <div className="mb-3.5">
              <label className="block font-mono text-[12px] font-medium text-ink-2 mb-1.5 uppercase tracking-widest">
                Work email
              </label>
              <input
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setEmailError(null); }}
                className="w-full rounded-xl px-4 py-3.5 text-[15px] text-ink bg-white outline-none transition-all"
                style={{
                  border: emailError ? "1px solid #C8332B" : "1px solid #E5E7EB",
                  boxShadow: emailError ? "0 0 0 3px rgba(200,51,43,0.10)" : undefined,
                }}
              />
              {emailError && (
                <div className="flex items-center gap-1.5 mt-1.5 text-[12.5px]" style={{ color: "#C8332B" }}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
                  </svg>
                  {emailError}
                </div>
              )}
            </div>

            {/* Password */}
            <div className="mb-0.5">
              <label className="block font-mono text-[12px] font-medium text-ink-2 mb-1.5 uppercase tracking-widest">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setPasswordError(null); }}
                  className="w-full rounded-xl px-4 py-3.5 text-[15px] text-ink bg-white outline-none transition-all pr-12"
                  style={{
                    border: passwordError ? "1px solid #C8332B" : "1px solid #E5E7EB",
                    boxShadow: passwordError ? "0 0 0 3px rgba(200,51,43,0.10)" : undefined,
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute top-1/2 -translate-y-1/2 right-3 p-1.5 rounded-md text-ink-3 hover:text-ink hover:bg-muted transition-colors"
                >
                  {showPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.5 10.5 0 0 1 12 20c-7 0-11-8-11-8a19.8 19.8 0 0 1 4.22-5.94"/>
                      <path d="M9.9 4.24A10.5 10.5 0 0 1 12 4c7 0 11 8 11 8a19.8 19.8 0 0 1-3.16 4.19"/>
                      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  )}
                </button>
              </div>
              {passwordError && (
                <div className="flex items-center gap-1.5 mt-1.5 text-[12.5px]" style={{ color: "#C8332B" }}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
                  </svg>
                  {passwordError}
                </div>
              )}
            </div>

            <div className="flex justify-end mt-0.5 mb-4.5">
              <a href="#" className="text-[13px] text-ink-3 hover:text-ink hover:underline underline-offset-2">
                Forgot password?
              </a>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full inline-flex items-center justify-center gap-2 font-semibold text-[14.5px] rounded-full py-3.5 px-5 transition-all"
              style={{
                background: "#C8E84E",
                color: "#1F2A07",
                border: "1px solid transparent",
                boxShadow: "0 1px 0 rgba(0,0,0,0.04)",
                opacity: loading ? 0.85 : 1,
                cursor: loading ? "wait" : "pointer",
              }}
              onMouseEnter={(e) => { if (!loading) { (e.currentTarget as HTMLButtonElement).style.background = "#bfe042"; (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-1px)"; (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 20px -8px rgba(156,193,41,0.6)"; } }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "#C8E84E"; (e.currentTarget as HTMLButtonElement).style.transform = ""; (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 1px 0 rgba(0,0,0,0.04)"; }}
            >
              {loading ? (
                <>
                  <span
                    className="inline-block w-3.5 h-3.5 rounded-full border-2 animate-spin"
                    style={{ borderColor: "rgba(31,42,7,0.25)", borderTopColor: "#1F2A07" }}
                  />
                  Signing in...
                </>
              ) : (
                <>
                  Sign in
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14M13 5l7 7-7 7"/>
                  </svg>
                </>
              )}
            </button>

            {/* Divider */}
            <div className="flex items-center gap-3.5 my-5 font-mono text-[11.5px] uppercase tracking-[0.18em] text-ink-4"
              style={{ ["--tw-divide-before" as string]: "1px solid #E5E7EB" }}
            >
              <span className="flex-1 h-px bg-line" />
              or
              <span className="flex-1 h-px bg-line" />
            </div>

            {/* SSO buttons */}
            <div className="flex flex-col gap-2.5">
              <a
                href="#"
                className="w-full inline-flex items-center justify-center gap-2 font-medium text-[14.5px] rounded-full py-3.5 px-5 bg-white text-ink transition-colors hover:bg-[#fafafa]"
                style={{ border: "1px solid #E5E7EB" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLAnchorElement).style.borderColor = "#cfcfcf"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLAnchorElement).style.borderColor = "#E5E7EB"; }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v3.8h5.4c-.2 1.3-.9 2.4-2 3.1v2.6h3.3c1.9-1.8 3-4.4 3-7.5z" fill="#4285F4"/>
                  <path d="M12 22c2.7 0 5-.9 6.7-2.4l-3.3-2.6c-.9.6-2.1 1-3.4 1-2.6 0-4.8-1.8-5.6-4.1H3v2.6C4.7 19.7 8.1 22 12 22z" fill="#34A853"/>
                  <path d="M6.4 13.9c-.2-.6-.3-1.3-.3-1.9s.1-1.3.3-1.9V7.5H3C2.4 8.9 2 10.4 2 12s.4 3.1 1 4.5l3.4-2.6z" fill="#FBBC05"/>
                  <path d="M12 6c1.5 0 2.8.5 3.8 1.5l2.9-2.9C16.9 2.9 14.7 2 12 2 8.1 2 4.7 4.3 3 7.5l3.4 2.6C7.2 7.8 9.4 6 12 6z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </a>
              <a
                href="#"
                className="w-full inline-flex items-center justify-center gap-2 font-medium text-[14.5px] rounded-full py-3.5 px-5 bg-white text-ink transition-colors hover:bg-[#fafafa]"
                style={{ border: "1px solid #E5E7EB" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLAnchorElement).style.borderColor = "#cfcfcf"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLAnchorElement).style.borderColor = "#E5E7EB"; }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="8" height="8" fill="#F25022"/>
                  <rect x="13" y="3" width="8" height="8" fill="#7FBA00"/>
                  <rect x="3" y="13" width="8" height="8" fill="#00A4EF"/>
                  <rect x="13" y="13" width="8" height="8" fill="#FFB900"/>
                </svg>
                Continue with Microsoft
              </a>
            </div>

            <div className="mt-8 text-center text-[14px] text-ink-3">
              Don&apos;t have an account?{" "}
              <Link
                href="/signup"
                className="font-semibold no-underline"
                style={{
                  color: "#1F2A07",
                  background: "linear-gradient(180deg, transparent 60%, rgba(200,232,78,0.55) 60%)",
                  padding: "1px 3px",
                  borderRadius: 3,
                }}
              >
                Get started →
              </Link>
            </div>
          </form>
        </div>

        <div className="mt-auto pt-8 flex items-center justify-between font-mono text-[11px] uppercase tracking-widest text-ink-4">
          <a href="#" className="text-ink-3 hover:text-ink no-underline">Terms</a>
          <a href="#" className="text-ink-3 hover:text-ink no-underline">Privacy</a>
          <a href="mailto:hello@quorint.com" className="text-ink-3 hover:text-ink no-underline">hello@quorint.com</a>
        </div>
      </section>
    </div>
  );
}
