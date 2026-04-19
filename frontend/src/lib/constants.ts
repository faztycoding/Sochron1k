/**
 * Shared constants across the app.
 * Keep in sync with backend/app/config.py TARGET_PAIRS.
 */

export const PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY", "GBP/USD", "AUD/USD"] as const;
export type Pair = typeof PAIRS[number];

export const CURRENCIES = ["EUR", "USD", "JPY", "GBP", "AUD"] as const;
export type Currency = typeof CURRENCIES[number];

export const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;
export type Timeframe = typeof TIMEFRAMES[number];

export const DEFAULT_TIMEFRAME: Timeframe = "1h";

/** Map pair → display decimals (JPY pairs use 3, others 5) */
export function pipDecimals(pair: string): number {
  return pair.includes("JPY") ? 3 : 5;
}

/** Pip multiplier for price difference → pips */
export function pipMultiplier(pair: string): number {
  return pair.includes("JPY") ? 100 : 10000;
}

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
