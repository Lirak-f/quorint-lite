import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number, currency = "EUR"): string {
  return new Intl.NumberFormat("en-EU", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export const COUNTRY_NAMES: Record<string, string> = {
  AT: "Austria",
  DE: "Germany",
  IT: "Italy",
  FR: "France",
  NL: "Netherlands",
  CH: "Switzerland",
  BE: "Belgium",
  PL: "Poland",
  CZ: "Czech Republic",
  SK: "Slovakia",
  HU: "Hungary",
  RO: "Romania",
  BG: "Bulgaria",
  HR: "Croatia",
  SI: "Slovenia",
  SE: "Sweden",
  NO: "Norway",
  DK: "Denmark",
  FI: "Finland",
  ES: "Spain",
  PT: "Portugal",
  GR: "Greece",
  LU: "Luxembourg",
  IE: "Ireland",
  EE: "Estonia",
  LV: "Latvia",
  LT: "Lithuania",
};

export const COUNTRY_FLAGS: Record<string, string> = {
  AT: "🇦🇹",
  DE: "🇩🇪",
  IT: "🇮🇹",
  FR: "🇫🇷",
  NL: "🇳🇱",
  CH: "🇨🇭",
  BE: "🇧🇪",
  PL: "🇵🇱",
  CZ: "🇨🇿",
  SK: "🇸🇰",
  HU: "🇭🇺",
  RO: "🇷🇴",
  BG: "🇧🇬",
  HR: "🇭🇷",
  SI: "🇸🇮",
  SE: "🇸🇪",
  NO: "🇳🇴",
  DK: "🇩🇰",
  FI: "🇫🇮",
  ES: "🇪🇸",
  PT: "🇵🇹",
  GR: "🇬🇷",
  LU: "🇱🇺",
  IE: "🇮🇪",
  EE: "🇪🇪",
  LV: "🇱🇻",
  LT: "🇱🇹",
};

export const ORIGIN_COUNTRIES = [
  { iso2: "XK", name: "Kosovo" },
  { iso2: "AL", name: "Albania" },
  { iso2: "RS", name: "Serbia" },
  { iso2: "BA", name: "Bosnia & Herzegovina" },
  { iso2: "MK", name: "North Macedonia" },
  { iso2: "ME", name: "Montenegro" },
];
