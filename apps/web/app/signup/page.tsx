"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

const COUNTRIES = [
  { code: "XK", label: "Kosovo" },
  { code: "AL", label: "Albania" },
  { code: "RS", label: "Serbia" },
  { code: "BA", label: "Bosnia and Herzegovina" },
  { code: "MK", label: "North Macedonia" },
  { code: "XX", label: "Other" },
];

function scorePw(v: string): number {
  if (!v) return 0;
  let s = 0;
  if (v.length >= 8) s++;
  if (v.length >= 12) s++;
  if (/[A-Z]/.test(v) && /[a-z]/.test(v)) s++;
  if (/[0-9]/.test(v) && /[^A-Za-z0-9]/.test(v)) s++;
  return Math.min(s, 4);
}

const PW_LABELS = ["", "Weak", "Fair", "Good", "Strong"];
const PW_BAR_COLORS = ["", "#E5826B", "#E5B26B", "#A6D444", "#9CC129"];

function FlagSwatch({ code }: { code: string }) {
  const base = "w-5 h-[14px] rounded-[2px] flex-shrink-0 border border-black/[0.08]";
  if (code === "XK")
    return (
      <span
        className={base}
        style={{
          background:
            "#244AA5 url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 14'><path fill='%23D0A650' d='M10 3.5 10.5 4.5 11.6 4.7 10.8 5.4 11 6.5 10 6 9 6.5 9.2 5.4 8.4 4.7 9.5 4.5z'/><g fill='%23fff'><circle cx='5' cy='9.5' r='0.5'/><circle cx='7' cy='9.5' r='0.5'/><circle cx='9' cy='9.5' r='0.5'/><circle cx='11' cy='9.5' r='0.5'/><circle cx='13' cy='9.5' r='0.5'/><circle cx='15' cy='9.5' r='0.5'/></g></svg>\") center/cover no-repeat",
        }}
      />
    );
  if (code === "AL")
    return (
      <span
        className={base}
        style={{
          background:
            "#E41E20 url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 14'><text x='10' y='10.5' font-size='8' text-anchor='middle' fill='%23000' font-family='serif'>★</text></svg>\") center/contain no-repeat",
        }}
      />
    );
  if (code === "RS")
    return (
      <span
        className={base}
        style={{ background: "linear-gradient(180deg,#C6363C 0 33%,#0C4076 33% 66%,#fff 66%)" }}
      />
    );
  if (code === "BA")
    return (
      <span
        className={base}
        style={{
          background:
            "#002F6C url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 14'><path fill='%23FECB00' d='M3 0 17 14H3z'/></svg>\") center/cover no-repeat",
        }}
      />
    );
  if (code === "MK")
    return (
      <span
        className={base}
        style={{
          background:
            "#D82126 url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 14'><circle cx='10' cy='7' r='2' fill='%23F8E92E'/></svg>\") center/cover no-repeat",
        }}
      />
    );
  return (
    <span
      className={base}
      style={{ background: "linear-gradient(135deg,#cfcfcf,#9ca3af)" }}
    />
  );
}

function FieldError({ msg }: { msg: string | null }) {
  if (!msg) return null;
  return (
    <div className="flex items-center gap-1.5 mt-1.5 text-[12.5px]" style={{ color: "#C8332B" }}>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" />
      </svg>
      {msg}
    </div>
  );
}

export default function SignupPage() {
  const router = useRouter();
  const supabase = createClient();

  const [fullName, setFullName] = useState("");
  const [company, setCompany] = useState("");
  const [country, setCountry] = useState("XK");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const [nameErr, setNameErr] = useState<string | null>(null);
  const [companyErr, setCompanyErr] = useState<string | null>(null);
  const [emailErr, setEmailErr] = useState<string | null>(null);
  const [pwErr, setPwErr] = useState<string | null>(null);
  const [serverErr, setServerErr] = useState<string | null>(null);

  const pwScore = scorePw(password);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    let ok = true;
    if (!fullName.trim() || fullName.trim().length < 2) {
      setNameErr("Enter your full name.");
      ok = false;
    }
    if (!company.trim()) {
      setCompanyErr("Enter your company name.");
      ok = false;
    }
    const emailTrimmed = email.trim();
    if (!emailTrimmed || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailTrimmed)) {
      setEmailErr("Enter a valid work email.");
      ok = false;
    }
    if (password.length < 8) {
      setPwErr("Password must be at least 8 characters.");
      ok = false;
    }
    if (!ok) return;

    setLoading(true);
    setServerErr(null);

    const { error } = await supabase.auth.signUp({
      email: emailTrimmed,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback?next=/new`,
        data: { full_name: fullName.trim(), company, country },
      },
    });

    if (error) {
      setServerErr(error.message);
      setLoading(false);
      return;
    }

    setDone(true);
    setLoading(false);
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
            <div className="relative rounded-[7px] bg-ink shrink-0" style={{ width: 26, height: 26 }}>
              <span className="absolute rounded-xs bg-green" style={{ width: 8, height: 8, top: 5, left: 5 }} />
            </div>
            <span className="font-serif text-[22px] text-ink" style={{ letterSpacing: "-0.01em" }}>Quorint</span>
          </Link>
        </div>

        {/* Mid content */}
        <div className="relative z-10 my-auto max-w-130 py-10">
          <span
            className="inline-flex items-center gap-2 text-[13px] font-medium rounded-full px-3.5 py-2"
            style={{ background: "rgba(255,255,255,0.7)", border: "1px solid rgba(59,47,30,0.08)", color: "#3B2F1E" }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ background: "#9CC129", boxShadow: "0 0 0 3px rgba(200,232,78,0.35)" }}
            />
            Join 500+ manufacturers
          </span>

          <h1
            className="font-serif text-ink mt-5.5 mb-7"
            style={{ fontSize: "clamp(34px,3.8vw,46px)", lineHeight: 1.06, letterSpacing: "-0.02em" }}
          >
            Find your first EU<br />
            wholesale buyer in <em>4 hours</em>
          </h1>

          <ul className="flex flex-col gap-3.5 max-w-120 list-none p-0 m-0">
            {[
              <><b className="text-ink font-semibold">10 buyers</b> scored and ranked by conversion probability</>,
              <>Personalized <b className="text-ink font-semibold">outreach email</b> in their language</>,
              <><b className="text-ink font-semibold">Pipeline tracker</b> — from first contact to closed deal</>,
            ].map((text, i) => (
              <li key={i} className="flex items-start gap-3 text-[15px] leading-[1.45]" style={{ color: "#3B2F1E" }}>
                <span
                  className="shrink-0 w-6 h-6 rounded-full inline-flex items-center justify-center mt-px"
                  style={{ background: "#C8E84E", boxShadow: "0 0 0 4px rgba(200,232,78,0.25)" }}
                  aria-hidden="true"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" style={{ width: 12, height: 12, color: "#1F2A07" }}>
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </span>
                <span>{text}</span>
              </li>
            ))}
          </ul>

          {/* Image card */}
          <figure
            className="mt-9 rounded-2xl overflow-hidden max-w-120 m-0"
            style={{
              border: "1px solid rgba(80,60,30,0.07)",
              boxShadow: "0 1px 0 rgba(80,60,30,0.04), 0 22px 44px -24px rgba(60,40,10,0.30)",
              background: "#EAD7B0",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="https://images.unsplash.com/photo-1504148455328-c376907d081c?auto=format&fit=crop&w=900&q=70"
              alt="Craftsman at workbench"
              referrerPolicy="no-referrer"
              className="block w-full object-cover"
              style={{ height: 200 }}
            />
            <figcaption
              className="flex items-center gap-2 px-3.5 py-2.5 bg-white text-[12.5px]"
              style={{ borderTop: "1px solid rgba(80,60,30,0.07)", color: "#6B7280" }}
            >
              <svg style={{ width: 14, height: 14, color: "#3B2F1E", opacity: 0.6, flexShrink: 0 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" />
              </svg>
              <span><b className="text-ink font-semibold">Furniture manufacturer</b> · Prizren, Kosovo</span>
            </figcaption>
          </figure>
        </div>

        {/* Footer */}
        <div className="relative z-10 mt-auto flex justify-between font-mono text-[11px] uppercase tracking-widest opacity-55" style={{ color: "#3B2F1E" }}>
          <span>© Quorint 2026</span>
          <span>Built in Kosovo</span>
        </div>
      </aside>

      {/* ── RIGHT PANEL ── */}
      <section className="flex flex-col bg-white px-6 py-12 lg:px-14 overflow-auto">
        <div className="flex items-center justify-end text-[13px] text-ink-3">
          <span>Already have an account?</span>
          <Link
            href="/login"
            className="text-ink font-medium ml-1.5 no-underline"
            style={{ borderBottom: "1px solid #0a0a0a", paddingBottom: 1 }}
          >
            Sign in →
          </Link>
        </div>

        <div className="my-auto w-full max-w-110 self-center py-6">

          {done ? (
            /* ── Success state ── */
            <div className="flex flex-col items-center text-center py-10" style={{ animation: "fadeUp 0.55s ease both" }}>
              <style>{`
                @keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
                @keyframes pop { 0%{transform:scale(0.4);opacity:0;} 60%{transform:scale(1.08);opacity:1;} 100%{transform:scale(1);} }
                @keyframes drawCheck { to { stroke-dashoffset: 0; } }
                @keyframes progressFill { to { width: 100%; } }
              `}</style>
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center"
                style={{
                  background: "#C8E84E",
                  boxShadow: "0 0 0 10px rgba(200,232,78,0.22), 0 12px 32px -10px rgba(156,193,41,0.55)",
                  animation: "pop 0.55s cubic-bezier(.2,.9,.2,1.2) both",
                }}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="#1F2A07" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round"
                  style={{ width: 38, height: 38, strokeDasharray: 30, strokeDashoffset: 30, animation: "drawCheck 0.5s ease 0.25s forwards" }}>
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <h2 className="font-serif font-normal text-ink mt-6 mb-2" style={{ fontSize: 34, letterSpacing: "-0.02em", lineHeight: 1.1 }}>
                Check your email
              </h2>
              <p className="text-[14.5px] text-ink-3 mb-6">
                We sent a confirmation link to <strong className="text-ink font-semibold">{email}</strong>.
                Click it to activate your account.
              </p>
              <div className="w-55 h-0.75 rounded-full overflow-hidden" style={{ background: "#E5E7EB" }}>
                <div
                  className="h-full rounded-full"
                  style={{
                    width: "0%",
                    background: "linear-gradient(90deg, #9CC129, #C8E84E)",
                    animation: "progressFill 2.4s cubic-bezier(.45,.05,.55,.95) 0.4s forwards",
                  }}
                />
              </div>
              <Link href="/login" className="mt-8 text-[13px] text-ink-3 hover:text-ink no-underline">
                Back to sign in
              </Link>
            </div>
          ) : (
            <>
              <h2
                className="font-serif font-normal text-ink m-0"
                style={{ fontSize: 40, letterSpacing: "-0.02em", lineHeight: 1.1 }}
              >
                Create your account
              </h2>
              <p className="text-[15px] text-ink-3 mt-2.5 mb-7">Start finding EU buyers today.</p>

              {/* SSO */}
              <div className="flex flex-col gap-2.5 mb-0">
                <button
                  type="button"
                  className="w-full inline-flex items-center justify-center gap-2 font-medium text-[14.5px] rounded-full py-3.5 px-5 bg-white text-ink transition-colors"
                  style={{ border: "1px solid #E5E7EB" }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v3.8h5.4c-.2 1.3-.9 2.4-2 3.1v2.6h3.3c1.9-1.8 3-4.4 3-7.5z" fill="#4285F4" />
                    <path d="M12 22c2.7 0 5-.9 6.7-2.4l-3.3-2.6c-.9.6-2.1 1-3.4 1-2.6 0-4.8-1.8-5.6-4.1H3v2.6C4.7 19.7 8.1 22 12 22z" fill="#34A853" />
                    <path d="M6.4 13.9c-.2-.6-.3-1.3-.3-1.9s.1-1.3.3-1.9V7.5H3C2.4 8.9 2 10.4 2 12s.4 3.1 1 4.5l3.4-2.6z" fill="#FBBC05" />
                    <path d="M12 6c1.5 0 2.8.5 3.8 1.5l2.9-2.9C16.9 2.9 14.7 2 12 2 8.1 2 4.7 4.3 3 7.5l3.4 2.6C7.2 7.8 9.4 6 12 6z" fill="#EA4335" />
                  </svg>
                  Continue with Google
                </button>
                <button
                  type="button"
                  className="w-full inline-flex items-center justify-center gap-2 font-medium text-[14.5px] rounded-full py-3.5 px-5 bg-white text-ink transition-colors"
                  style={{ border: "1px solid #E5E7EB" }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="3" width="8" height="8" fill="#F25022" />
                    <rect x="13" y="3" width="8" height="8" fill="#7FBA00" />
                    <rect x="3" y="13" width="8" height="8" fill="#00A4EF" />
                    <rect x="13" y="13" width="8" height="8" fill="#FFB900" />
                  </svg>
                  Continue with Microsoft
                </button>
              </div>

              {/* Divider */}
              <div className="flex items-center gap-3.5 my-5 font-mono text-[11px] uppercase tracking-[0.18em] text-ink-4">
                <span className="flex-1 h-px bg-line" />
                <span>or continue with email</span>
                <span className="flex-1 h-px bg-line" />
              </div>

              <form onSubmit={handleSubmit} noValidate>
                {/* Full name */}
                <div className="mb-3">
                  <label className="block font-mono text-[11.5px] font-medium text-ink-2 mb-1.5 uppercase tracking-widest">
                    Full name
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      autoComplete="name"
                      placeholder="Arta Hoxha"
                      value={fullName}
                      onChange={(e) => { setFullName(e.target.value); setNameErr(null); }}
                      onBlur={() => { if (!fullName.trim() || fullName.trim().length < 2) setNameErr("Enter your full name."); }}
                      className="w-full rounded-xl px-4 py-3.5 text-[15px] text-ink bg-white outline-none transition-all pr-12"
                      style={{
                        border: nameErr ? "1px solid #C8332B" : "1px solid #E5E7EB",
                        boxShadow: nameErr ? "0 0 0 3px rgba(200,51,43,0.10)" : undefined,
                      }}
                    />
                    <span className="absolute top-1/2 -translate-y-1/2 right-4 pointer-events-none text-ink-4">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
                      </svg>
                    </span>
                  </div>
                  <FieldError msg={nameErr} />
                </div>

                {/* Company */}
                <div className="mb-3">
                  <label className="block font-mono text-[11.5px] font-medium text-ink-2 mb-1.5 uppercase tracking-widest">
                    Company name
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      autoComplete="organization"
                      placeholder="Hoxha Furniture"
                      value={company}
                      onChange={(e) => { setCompany(e.target.value); setCompanyErr(null); }}
                      onBlur={() => { if (!company.trim()) setCompanyErr("Enter your company name."); }}
                      className="w-full rounded-xl px-4 py-3.5 text-[15px] text-ink bg-white outline-none transition-all pr-12"
                      style={{
                        border: companyErr ? "1px solid #C8332B" : "1px solid #E5E7EB",
                        boxShadow: companyErr ? "0 0 0 3px rgba(200,51,43,0.10)" : undefined,
                      }}
                    />
                    <span className="absolute top-1/2 -translate-y-1/2 right-4 pointer-events-none text-ink-4">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
                        <path d="M3 21h18M5 21V7l7-4 7 4v14" /><path d="M9 9h.01M9 13h.01M9 17h.01M15 9h.01M15 13h.01M15 17h.01" />
                      </svg>
                    </span>
                  </div>
                  <FieldError msg={companyErr} />
                </div>

                {/* Country */}
                <div className="mb-3">
                  <label className="block font-mono text-[11.5px] font-medium text-ink-2 mb-1.5 uppercase tracking-widest">
                    Country
                  </label>
                  <div className="relative">
                    <div className="absolute top-1/2 -translate-y-1/2 left-4 pointer-events-none">
                      <FlagSwatch code={country} />
                    </div>
                    <select
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                      className="w-full rounded-xl py-3.5 text-[15px] text-ink bg-white outline-none transition-all appearance-none cursor-pointer"
                      style={{
                        border: "1px solid #E5E7EB",
                        paddingLeft: 52,
                        paddingRight: 40,
                        backgroundImage: "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236B7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>\")",
                        backgroundRepeat: "no-repeat",
                        backgroundPosition: "right 14px center",
                        backgroundSize: "16px 16px",
                      }}
                    >
                      {COUNTRIES.map((c) => (
                        <option key={c.code} value={c.code}>{c.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Email */}
                <div className="mb-3">
                  <label className="block font-mono text-[11.5px] font-medium text-ink-2 mb-1.5 uppercase tracking-widest">
                    Work email
                  </label>
                  <div className="relative">
                    <input
                      type="email"
                      autoComplete="email"
                      placeholder="you@company.com"
                      value={email}
                      onChange={(e) => { setEmail(e.target.value); setEmailErr(null); }}
                      onBlur={() => {
                        const v = email.trim();
                        if (!v || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) setEmailErr("Enter a valid work email.");
                      }}
                      className="w-full rounded-xl px-4 py-3.5 text-[15px] text-ink bg-white outline-none transition-all pr-12"
                      style={{
                        border: emailErr ? "1px solid #C8332B" : "1px solid #E5E7EB",
                        boxShadow: emailErr ? "0 0 0 3px rgba(200,51,43,0.10)" : undefined,
                      }}
                    />
                    <span className="absolute top-1/2 -translate-y-1/2 right-4 pointer-events-none text-ink-4">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
                        <rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" />
                      </svg>
                    </span>
                  </div>
                  <FieldError msg={emailErr} />
                </div>

                {/* Password */}
                <div className="mb-1">
                  <label className="block font-mono text-[11.5px] font-medium text-ink-2 mb-1.5 uppercase tracking-widest">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPw ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="At least 8 characters"
                      value={password}
                      onChange={(e) => { setPassword(e.target.value); setPwErr(null); }}
                      onBlur={() => { if (password.length < 8) setPwErr("Password must be at least 8 characters."); }}
                      className="w-full rounded-xl px-4 py-3.5 text-[15px] text-ink bg-white outline-none transition-all pr-12"
                      style={{
                        border: pwErr ? "1px solid #C8332B" : "1px solid #E5E7EB",
                        boxShadow: pwErr ? "0 0 0 3px rgba(200,51,43,0.10)" : undefined,
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(!showPw)}
                      aria-label={showPw ? "Hide password" : "Show password"}
                      className="absolute top-1/2 -translate-y-1/2 right-3 p-1.5 rounded-md text-ink-3 hover:text-ink hover:bg-muted transition-colors"
                    >
                      {showPw ? (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.94 17.94A10.5 10.5 0 0 1 12 20c-7 0-11-8-11-8a19.8 19.8 0 0 1 4.22-5.94" />
                          <path d="M9.9 4.24A10.5 10.5 0 0 1 12 4c7 0 11 8 11 8a19.8 19.8 0 0 1-3.16 4.19" />
                          <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
                          <line x1="1" y1="1" x2="23" y2="23" />
                        </svg>
                      ) : (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      )}
                    </button>
                  </div>

                  {/* Password strength meter */}
                  {password.length > 0 && (
                    <div className="flex items-center gap-2.5 mt-2">
                      <div className="flex gap-1 flex-1">
                        {[1, 2, 3, 4].map((i) => (
                          <div
                            key={i}
                            className="h-0.75 flex-1 rounded-full transition-all duration-200"
                            style={{ background: pwScore >= i ? PW_BAR_COLORS[pwScore] : "#E5E7EB" }}
                          />
                        ))}
                      </div>
                      <span className="font-mono text-[11px] uppercase tracking-widest text-ink-3 shrink-0">
                        {PW_LABELS[pwScore] || "Weak"}
                      </span>
                    </div>
                  )}

                  <FieldError msg={pwErr} />
                </div>

                {serverErr && (
                  <div className="mt-3 text-[13px] rounded-lg px-3 py-2.5" style={{ color: "#C8332B", background: "#FBEAE8", border: "1px solid #f5c6c4" }}>
                    {serverErr}
                  </div>
                )}

                <div className="mt-5">
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
                  >
                    {loading ? (
                      <>
                        <span
                          className="inline-block w-3.5 h-3.5 rounded-full border-2 animate-spin"
                          style={{ borderColor: "rgba(31,42,7,0.25)", borderTopColor: "#1F2A07" }}
                        />
                        Creating account…
                      </>
                    ) : (
                      <>
                        Create account
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M5 12h14M13 5l7 7-7 7" />
                        </svg>
                      </>
                    )}
                  </button>
                </div>

                <p className="mt-3.5 text-[12px] leading-relaxed text-ink-3 text-center">
                  By creating an account you agree to our{" "}
                  <a href="#" className="text-ink-2 underline underline-offset-2 decoration-line hover:decoration-ink">Terms of Service</a>{" "}
                  and{" "}
                  <a href="#" className="text-ink-2 underline underline-offset-2 decoration-line hover:decoration-ink">Privacy Policy</a>.
                </p>

                <div className="mt-7 text-center text-[14px] text-ink-3">
                  Already have an account?{" "}
                  <Link
                    href="/login"
                    className="font-semibold no-underline"
                    style={{
                      color: "#1F2A07",
                      background: "linear-gradient(180deg, transparent 60%, rgba(200,232,78,0.55) 60%)",
                      padding: "1px 3px",
                      borderRadius: 3,
                    }}
                  >
                    Sign in →
                  </Link>
                </div>
              </form>
            </>
          )}
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
