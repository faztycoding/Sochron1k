const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

// Prices
export const api = {
  prices: {
    realtime: () => fetchAPI<PricesResponse>("/price/realtime"),
    candles: (pair: string, tf = "1h", limit = 200) =>
      fetchAPI<CandlesResponse>(`/price/candles/${pair.replace("/", "-")}?timeframe=${tf}&limit=${limit}`),
    quote: (pair: string) => fetchAPI<QuoteData>(`/price/quote/${pair.replace("/", "-")}`),
  },
  indicators: {
    get: (pair: string, tf = "1h") =>
      fetchAPI<IndicatorSnapshot>(`/indicators/${pair.replace("/", "-")}?timeframe=${tf}`),
    summary: (pair: string) =>
      fetchAPI<QuickSummary>(`/indicators/${pair.replace("/", "-")}/summary`),
    strength: () => fetchAPI<CurrencyStrength>("/indicators/strength/currencies"),
  },
  analysis: {
    run: (pair: string, tf = "1h") =>
      fetchAPI<AnalysisResult>(`/analysis/${pair.replace("/", "-")}/run?timeframe=${tf}`, { method: "POST" }),
    all: () => fetchAPI<Record<string, AnalysisResult>>("/analysis/all/run"),
    killSwitch: (pair: string) =>
      fetchAPI<KillSwitchResult>(`/analysis/${pair.replace("/", "-")}/kill-switch`),
    session: () => fetchAPI<SessionInfo>("/analysis/session/current"),
  },
  news: {
    list: (limit = 20) => fetchAPI<NewsListResponse>(`/news?limit=${limit}`),
    refresh: () => fetchAPI<unknown>("/news/refresh", { method: "POST" }),
  },
};

// Types
export interface PricesResponse {
  prices: Record<string, PriceData>;
  count: number;
}

export interface PriceData {
  pair: string;
  price: number;
  timestamp: string;
  previous_close?: number;
}

export interface QuoteData {
  pair: string;
  open: number;
  high: number;
  low: number;
  close: number;
  previous_close: number;
  change: number;
  percent_change: number;
  volume: number;
  timestamp: string;
}

export interface CandlesResponse {
  pair: string;
  timeframe: string;
  count: number;
  candles: CandleData[];
}

export interface CandleData {
  pair: string;
  timeframe: string;
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorSnapshot {
  pair: string;
  timeframe: string;
  calculated_at: string;
  candle_count: number;
  latest_price: number;
  ema_9?: number;
  ema_21?: number;
  ema_50?: number;
  ema_200?: number;
  sma_50?: number;
  sma_200?: number;
  adx?: number;
  rsi?: number;
  macd_line?: number;
  macd_signal?: number;
  macd_hist?: number;
  stoch_k?: number;
  stoch_d?: number;
  cci?: number;
  bb_upper?: number;
  bb_middle?: number;
  bb_lower?: number;
  atr?: number;
  keltner_upper?: number;
  keltner_lower?: number;
  obv?: number;
  z_score?: number;
  currency_strength?: number;
  session_vol_index?: number;
  multi_tf_confluence?: number;
  news_impact_score?: number;
  liquidity_spike?: number;
  correlation_divergence?: number;
}

export interface QuickSummary {
  pair: string;
  overall_bias: string;
  bullish_signals: number;
  bearish_signals: number;
  signals: SignalItem[];
  snapshot: IndicatorSnapshot;
}

export interface SignalItem {
  name: string;
  signal: string;
  value: number;
  bias: string;
}

export interface CurrencyStrength {
  currencies: Record<string, number>;
  strongest: string | null;
  weakest: string | null;
}

export interface AnalysisResult {
  pair: string;
  timeframe: string;
  direction: string;
  confidence: number;
  original_confidence: number;
  strength: string;
  recommendation: string;
  confidence_breakdown: Record<string, number>;
  regime: { regime: string; regime_score: number; details: string[] };
  news: { news_score: number; sentiment: string; high_impact_soon: boolean; details: string[] };
  technical: { technical_score: number; agreements: number; total_checks: number; signals: string[] };
  correlation: { correlation_score: number; checks: unknown[] };
  risk_gate: { risk_gate_score: number; details: string[] };
  kill_switch: KillSwitchResult;
  diagnosis: { diagnostics: DiagnosticItem[]; overall_health: string; issues: number; total_checks: number };
  session: SessionInfo;
  suggested_entry: number | null;
  suggested_sl: number | null;
  suggested_tp: number | null;
  sl_pips: number | null;
  tp_pips: number | null;
  risk_reward: number | null;
  price: number;
  indicators_summary: Record<string, number | null>;
  analysis_duration: number;
  analyzed_at: string;
}

export interface KillSwitchResult {
  kill_switch_active: boolean;
  triggers: { condition: string; message: string; action: string }[];
  trigger_count: number;
  message: string;
}

export interface DiagnosticItem {
  check: string;
  severity: string;
  message: string;
  recommendation?: string;
}

export interface SessionInfo {
  session: string;
  is_dead_zone: boolean;
  utc_hour: number;
  thai_hour: number;
}

export interface NewsListResponse {
  items: NewsItem[];
  total: number;
}

export interface NewsItem {
  id: number;
  source: string;
  currency: string;
  pair?: string;
  title_original: string;
  title_th?: string;
  summary_th?: string;
  impact_level: string;
  sentiment_score?: number;
  event_time?: string;
  scraped_at: string;
}
