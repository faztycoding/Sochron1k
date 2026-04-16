const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export interface CalculateResult {
  pair: string;
  direction: string;
  entry_price: number;
  sl_price: number;
  tp_price: number;
  sl_pips: number;
  tp_pips: number;
  lot_size: number;
  risk_amount: number;
  potential_profit: number;
  risk_reward: number;
  pip_value: number;
  warnings: string[];
}

export interface AutoSLTPResult {
  pair: string;
  direction: string;
  entry_price: number;
  sl_price: number;
  tp_price: number;
  sl_pips: number;
  tp_pips: number;
  atr_used: number;
  risk_reward: number;
  method: string;
}

export interface TradeItem {
  id: number;
  pair: string;
  direction: string;
  timeframe: string;
  account_balance: number;
  risk_percent: number;
  lot_size: number;
  entry_price: number;
  sl_price: number | null;
  tp_price: number | null;
  sl_pips: number | null;
  tp_pips: number | null;
  exit_price: number | null;
  actual_pips: number | null;
  profit_loss: number | null;
  risk_reward_actual: number | null;
  status: string;
  result: string | null;
  system_confidence: number | null;
  system_direction: string | null;
  system_regime: string | null;
  system_correct: boolean | null;
  opened_at: string;
  closed_at: string | null;
  user_notes: string | null;
}

export interface TradeList {
  items: TradeItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface WinRateStats {
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_profit_pips: number;
  avg_loss_pips: number;
  profit_factor: number;
  best_trade_pips: number;
  worst_trade_pips: number;
  total_pips: number;
  by_pair: Record<string, { wins: number; losses: number; win_rate: number; total_pips: number }>;
}

export interface OverviewStats {
  total_trades: number;
  open_trades: number;
  win_rate: number;
  total_pips: number;
  profit_factor: number;
  system_accuracy: number;
  best_pair: string | null;
  worst_pair: string | null;
  avg_confidence: number;
  consecutive_wins: number;
  consecutive_losses: number;
  today_trades: number;
  today_pips: number;
}

export const tradeApi = {
  calculate: (data: {
    pair: string;
    direction: string;
    account_balance: number;
    risk_percent: number;
    entry_price: number;
    sl_price?: number;
    tp_price?: number;
    sl_pips?: number;
    tp_pips?: number;
  }) => fetchAPI<CalculateResult>("/calculate", { method: "POST", body: JSON.stringify(data) }),

  autoSL: (data: { pair: string; direction: string; entry_price: number; timeframe?: string }) =>
    fetchAPI<AutoSLTPResult>("/calculate/auto-sl", { method: "POST", body: JSON.stringify(data) }),

  trades: {
    list: (page = 1, pair?: string, status?: string) => {
      const params = new URLSearchParams({ page: String(page) });
      if (pair) params.set("pair", pair);
      if (status) params.set("status", status);
      return fetchAPI<TradeList>(`/trades?${params}`);
    },
    create: (data: Record<string, unknown>) =>
      fetchAPI<TradeItem>("/trades", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Record<string, unknown>) =>
      fetchAPI<TradeItem>(`/trades/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) => fetchAPI(`/trades/${id}`, { method: "DELETE" }),
    get: (id: number) => fetchAPI<TradeItem>(`/trades/${id}`),
  },

  stats: {
    winrate: (pair?: string) => {
      const q = pair ? `?pair=${pair}` : "";
      return fetchAPI<WinRateStats>(`/trades/stats/winrate${q}`);
    },
    accuracy: () => fetchAPI<Record<string, unknown>>("/trades/stats/accuracy"),
    overview: () => fetchAPI<OverviewStats>("/trades/stats/overview"),
  },
};
