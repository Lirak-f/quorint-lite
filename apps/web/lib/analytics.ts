"use client";

import posthog from "posthog-js";

let _initialised = false;

export function initAnalytics() {
  if (_initialised || typeof window === "undefined") return;
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  const host = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://eu.i.posthog.com";
  if (!key) return;
  posthog.init(key, { api_host: host, capture_pageview: false });
  _initialised = true;
}

export function trackEvent(
  event: string,
  properties?: Record<string, string | number | boolean | null>
) {
  if (!_initialised || typeof window === "undefined") return;
  posthog.capture(event, properties);
}

export function identifyUser(userId: string, email?: string) {
  if (!_initialised || typeof window === "undefined") return;
  posthog.identify(userId, email ? { email } : undefined);
}

// Typed event helpers for the events that matter
export const analytics = {
  reportCreated: (hs: string, origin: string, target: string, tier: string) =>
    trackEvent("report_created", { hs_code: hs, origin, target, tier }),

  reportCompleted: (reportId: string, tier: string, durationMs: number) =>
    trackEvent("report_completed", { report_id: reportId, tier, duration_ms: durationMs }),

  pdfDownloaded: (reportId: string) =>
    trackEvent("pdf_downloaded", { report_id: reportId }),

  tierSelected: (tier: string, price: number) =>
    trackEvent("tier_selected", { tier, price_eur: price }),

  reportFailed: (reportId: string, error: string) =>
    trackEvent("report_failed", { report_id: reportId, error }),
};
