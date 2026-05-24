"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden px-8 pt-18 pb-9 text-center">
      <HeroCanvas />
      <div className="relative z-10 max-w-310 mx-auto">
        <div className="animate-fade-in">
          <span className="inline-flex items-center gap-2 px-3.5 py-1.75 pl-2.75 bg-muted border border-line rounded-full text-[13px] text-ink-2 font-medium">
            <StarIcon />
            Trusted by 500+ Western Balkans manufacturers
          </span>
        </div>

        <h1 className="font-serif text-[clamp(40px,6.2vw,78px)] leading-[1.04] tracking-[-0.022em] text-ink mt-6 mb-0 max-w-270 mx-auto">
          The buyer matching platform
          <br />
          for manufacturers who are <em className="italic text-[#222]">ready</em>
          <br />
          to export
        </h1>

        <p className="text-[17px] leading-[1.55] text-ink-2 mt-6 max-w-140 mx-auto">
          Enter your product. We find the 10 EU wholesale buyers most likely to
          place an order — scored, ranked, with outreach emails written in their
          language.
        </p>

        <EmailSignupRow className="mt-9" />

        <div className="flex items-center gap-3.5 max-w-95 mx-auto mt-6 text-ink-4 text-xs uppercase tracking-[0.16em] before:flex-1 before:h-px before:bg-line after:flex-1 after:h-px after:bg-line">
          or
        </div>

        <div className="flex gap-2.5 justify-center flex-wrap mt-4.5">
          <SsoButton icon={<GoogleIcon />} label="Continue with Google" />
          <SsoButton icon={<MicrosoftIcon />} label="Continue with Microsoft" />
        </div>

        <p className="text-xs text-ink-4 mt-4.5 max-w-120 mx-auto">
          By signing up you agree to our{" "}
          <a href="#" className="text-ink-3 underline underline-offset-2">
            Terms
          </a>{" "}
          and{" "}
          <a href="#" className="text-ink-3 underline underline-offset-2">
            Privacy Policy
          </a>
          . No subscription — pay per lead list.
        </p>
      </div>
    </section>
  );
}

export function EmailSignupRow({ className = "" }: { className?: string }) {
  return (
    <form
      className={`flex items-center gap-2 bg-white border border-line rounded-full px-5 py-1.5 max-w-130 mx-auto shadow-[0_1px_0_rgba(0,0,0,0.02),0_6px_22px_-14px_rgba(0,0,0,0.12)] ${className}`}
      onSubmit={(e) => e.preventDefault()}
    >
      <input
        type="email"
        placeholder="Enter your work email"
        aria-label="Work email"
        className="flex-1 border-0 outline-none bg-transparent text-[15px] text-ink placeholder:text-ink-4 py-2.5 min-w-0"
      />
      <button
        type="submit"
        className="inline-flex items-center gap-2 px-[22px] py-[13px] rounded-full text-[14.5px] font-semibold bg-green text-green-ink hover:bg-green-hover hover:-translate-y-px transition-all whitespace-nowrap"
      >
        Get your leads
        <ArrowRight size={14} />
      </button>
    </form>
  );
}

function SsoButton({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button className="inline-flex items-center gap-2 px-[18px] py-[11px] rounded-full text-[14.5px] font-medium bg-white border border-line hover:border-[#cfcfcf] hover:bg-[#fafafa] transition-all cursor-pointer">
      {icon}
      {label}
    </button>
  );
}

function StarIcon() {
  return (
    <svg className="w-3.5 h-3.5 text-green-deep" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l2.7 6.3 6.8.6-5.2 4.5 1.6 6.6L12 16.8 6.1 20l1.6-6.6L2.5 8.9l6.8-.6L12 2z" />
    </svg>
  );
}

function ArrowRight({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v3.8h5.4c-.2 1.3-.9 2.4-2 3.1v2.6h3.3c1.9-1.8 3-4.4 3-7.5z" fill="#4285F4" />
      <path d="M12 22c2.7 0 5-.9 6.7-2.4l-3.3-2.6c-.9.6-2.1 1-3.4 1-2.6 0-4.8-1.8-5.6-4.1H3v2.6C4.7 19.7 8.1 22 12 22z" fill="#34A853" />
      <path d="M6.4 13.9c-.2-.6-.3-1.3-.3-1.9s.1-1.3.3-1.9V7.5H3C2.4 8.9 2 10.4 2 12s.4 3.1 1 4.5l3.4-2.6z" fill="#FBBC05" />
      <path d="M12 6c1.5 0 2.8.5 3.8 1.5l2.9-2.9C16.9 2.9 14.7 2 12 2 8.1 2 4.7 4.3 3 7.5l3.4 2.6C7.2 7.8 9.4 6 12 6z" fill="#EA4335" />
    </svg>
  );
}

function MicrosoftIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="8" height="8" fill="#F25022" />
      <rect x="13" y="3" width="8" height="8" fill="#7FBA00" />
      <rect x="3" y="13" width="8" height="8" fill="#00A4EF" />
      <rect x="13" y="13" width="8" height="8" fill="#FFB900" />
    </svg>
  );
}

function HeroCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const DPR = Math.min(window.devicePixelRatio || 1, 2);
    let W = 0, H = 0;
    let nodes: { type: string; x: number; y: number; r: number; drift: number }[] = [];
    let links: [number, number, number][] = [];
    let beams: { from: typeof nodes[0]; via: typeof nodes[0]; to: typeof nodes[0]; t: number; speed: number; hue: string }[] = [];
    let rafId = 0;

    function build() {
      const rect = canvas!.getBoundingClientRect();
      W = rect.width; H = rect.height;
      canvas!.width = W * DPR;
      canvas!.height = H * DPR;
      ctx!.setTransform(DPR, 0, 0, DPR, 0, 0);
      nodes = [];
      for (let i = 0; i < 8; i++) {
        nodes.push({ type: "src", x: W * (0.06 + Math.random() * 0.14), y: H * (0.12 + (i + 0.5) / 8 * 0.78 + (Math.random() - 0.5) * 0.04), r: 2.2 + Math.random() * 0.8, drift: (Math.random() - 0.5) * 0.12 });
      }
      for (let i = 0; i < 10; i++) {
        nodes.push({ type: "buyer", x: W * (0.80 + Math.random() * 0.14), y: H * (0.10 + (i + 0.5) / 10 * 0.82 + (Math.random() - 0.5) * 0.04), r: 2.2 + Math.random() * 0.8, drift: (Math.random() - 0.5) * 0.12 });
      }
      nodes.push({ type: "core", x: W * 0.5, y: H * 0.5, r: 0, drift: 0 });
      links = [];
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          if (nodes[i].type === "core" || nodes[j].type === "core") continue;
          if (nodes[i].type !== nodes[j].type) continue;
          const d = Math.hypot(nodes[i].x - nodes[j].x, nodes[i].y - nodes[j].y);
          if (d < W * 0.14) links.push([i, j, d]);
        }
      }
    }

    function spawnBeam() {
      const srcs = nodes.filter(n => n.type === "src");
      const buys = nodes.filter(n => n.type === "buyer");
      const core = nodes.find(n => n.type === "core")!;
      beams.push({ from: srcs[Math.floor(Math.random() * srcs.length)], via: core, to: buys[Math.floor(Math.random() * buys.length)], t: 0, speed: 0.0035 + Math.random() * 0.0025, hue: Math.random() < 0.5 ? "green" : "warm" });
    }

    function eio(t: number) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }

    function draw() {
      ctx!.clearRect(0, 0, W, H);
      for (const n of nodes) {
        if (n.type === "core") continue;
        n.y += n.drift * 0.06;
        if (n.y < H * 0.05 || n.y > H * 0.95) n.drift *= -1;
      }
      ctx!.lineWidth = 1;
      for (const [i, j, d] of links) {
        const a = nodes[i], b = nodes[j];
        ctx!.strokeStyle = `rgba(40,32,18,${Math.max(0, 0.08 - d / (W * 1.6))})`;
        ctx!.beginPath(); ctx!.moveTo(a.x, a.y); ctx!.lineTo(b.x, b.y); ctx!.stroke();
      }
      for (const n of nodes) {
        if (n.type === "core") continue;
        ctx!.beginPath(); ctx!.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx!.fillStyle = "rgba(40,32,18,0.55)"; ctx!.fill();
        ctx!.beginPath(); ctx!.arc(n.x, n.y, n.r + 4, 0, Math.PI * 2);
        ctx!.fillStyle = "rgba(40,32,18,0.06)"; ctx!.fill();
      }
      for (const beam of beams) {
        const e = eio(beam.t);
        const px = e < 0.5 ? beam.from.x + (beam.via.x - beam.from.x) * (e / 0.5) : beam.via.x + (beam.to.x - beam.via.x) * ((e - 0.5) / 0.5);
        const py = e < 0.5 ? beam.from.y + (beam.via.y - beam.from.y) * (e / 0.5) : beam.via.y + (beam.to.y - beam.via.y) * ((e - 0.5) / 0.5);
        const guideAlpha = 0.10 * Math.sin(Math.min(1, beam.t * 3) * Math.PI);
        if (guideAlpha > 0.005) {
          ctx!.strokeStyle = beam.hue === "green" ? `rgba(156,193,41,${guideAlpha})` : `rgba(170,130,60,${guideAlpha})`;
          ctx!.lineWidth = 1; ctx!.beginPath(); ctx!.moveTo(beam.from.x, beam.from.y); ctx!.lineTo(beam.via.x, beam.via.y); ctx!.lineTo(beam.to.x, beam.to.y); ctx!.stroke();
        }
        const head = beam.hue === "green" ? "200,232,78" : "210,170,90";
        const grd = ctx!.createRadialGradient(px, py, 0, px, py, 18);
        grd.addColorStop(0, `rgba(${head},0.55)`); grd.addColorStop(1, `rgba(${head},0)`);
        ctx!.fillStyle = grd; ctx!.beginPath(); ctx!.arc(px, py, 18, 0, Math.PI * 2); ctx!.fill();
        ctx!.fillStyle = `rgba(${head},0.95)`; ctx!.beginPath(); ctx!.arc(px, py, 2.4, 0, Math.PI * 2); ctx!.fill();
        if (e > 0.9) { const pulse = (e - 0.9) / 0.1; ctx!.beginPath(); ctx!.arc(beam.to.x, beam.to.y, 4 + pulse * 10, 0, Math.PI * 2); ctx!.strokeStyle = `rgba(${head},${0.6 * (1 - pulse)})`; ctx!.lineWidth = 1.2; ctx!.stroke(); }
        if (e < 0.08) { const pulse = e / 0.08; ctx!.beginPath(); ctx!.arc(beam.from.x, beam.from.y, 4 + pulse * 8, 0, Math.PI * 2); ctx!.strokeStyle = `rgba(${head},${0.5 * (1 - pulse)})`; ctx!.lineWidth = 1.2; ctx!.stroke(); }
        beam.t += beam.speed;
      }
      beams = beams.filter(b => b.t < 1);
      if (Math.random() < 0.018 && beams.length < 4) spawnBeam();
      rafId = requestAnimationFrame(draw);
    }

    const prefersReduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    build();
    spawnBeam();
    if (!prefersReduce) { setTimeout(spawnBeam, 600); rafId = requestAnimationFrame(draw); }
    else { draw(); beams = []; }

    let resizeRaf = 0;
    const onResize = () => { cancelAnimationFrame(resizeRaf); resizeRaf = requestAnimationFrame(build); };
    window.addEventListener("resize", onResize);
    return () => { cancelAnimationFrame(rafId); window.removeEventListener("resize", onResize); };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="absolute inset-0 w-full h-full pointer-events-none z-0 opacity-85"
      style={{ maskImage: "radial-gradient(ellipse 70% 70% at 50% 45%, transparent 0%, transparent 28%, #000 70%, #000 100%)", WebkitMaskImage: "radial-gradient(ellipse 70% 70% at 50% 45%, transparent 0%, transparent 28%, #000 70%, #000 100%)" }}
    />
  );
}
