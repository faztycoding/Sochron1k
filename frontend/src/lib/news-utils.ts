import type { NewsItem } from "./api";

// Category display with icons
export const CATEGORY_META: Record<string, { label: string; icon: string; color: string }> = {
  central_bank: { label: "ธนาคารกลาง", icon: "🏛️", color: "text-purple-400" },
  economic_data: { label: "ข้อมูลเศรษฐกิจ", icon: "📊", color: "text-blue-400" },
  geopolitical: { label: "ภูมิรัฐศาสตร์", icon: "🌐", color: "text-red-400" },
  corporate: { label: "ธุรกิจ/บริษัท", icon: "🏢", color: "text-amber-400" },
  commodity: { label: "สินค้าโภคภัณฑ์", icon: "🛢️", color: "text-orange-400" },
  sentiment: { label: "ทิศทางตลาด", icon: "📈", color: "text-cyan-400" },
  technical: { label: "เทคนิคอล", icon: "📉", color: "text-pink-400" },
};

// Source display
export const SOURCE_META: Record<string, { label: string; color: string }> = {
  forex_factory: { label: "Forex Factory", color: "text-emerald-400" },
  forex_factory_xml: { label: "Forex Factory", color: "text-emerald-400" },
  investing: { label: "Investing.com", color: "text-blue-400" },
  tradingview: { label: "TradingView", color: "text-cyan-400" },
  babypips: { label: "BabyPips", color: "text-pink-400" },
  finviz: { label: "Finviz", color: "text-amber-400" },
  rss_fallback: { label: "RSS Feed", color: "text-text-muted" },
};

// Currency flags
export const CURRENCY_FLAGS: Record<string, string> = {
  EUR: "🇪🇺", USD: "🇺🇸", JPY: "🇯🇵", GBP: "🇬🇧", AUD: "🇦🇺",
  CHF: "🇨🇭", CAD: "🇨🇦", NZD: "🇳🇿", CNY: "🇨🇳",
};

// Impact score (1-5) → label + color
export function getImpactMeta(score: number) {
  if (score >= 5) return { label: "วิกฤต", color: "text-red-500", bg: "bg-red-500/15", border: "border-red-500/30", stars: "★★★★★" };
  if (score >= 4) return { label: "สูงมาก", color: "text-red-400", bg: "bg-red-400/15", border: "border-red-400/30", stars: "★★★★" };
  if (score >= 3) return { label: "ปานกลาง", color: "text-amber-400", bg: "bg-amber-400/15", border: "border-amber-400/30", stars: "★★★" };
  if (score >= 2) return { label: "ต่ำ", color: "text-blue-400", bg: "bg-blue-400/15", border: "border-blue-400/30", stars: "★★" };
  return { label: "เล็กน้อย", color: "text-text-muted", bg: "bg-bg-surface", border: "border-border", stars: "★" };
}

// Time horizon → Thai
export const TIME_HORIZON_LABEL: Record<string, string> = {
  instant: "ทันที",
  short: "ระยะสั้น",
  medium: "ระยะกลาง",
  long: "ระยะยาว",
};

// Actionability → Thai + color
export function getActionMeta(action: string) {
  switch (action) {
    case "tradable":
      return { label: "พร้อมเทรด", color: "text-emerald-400", bg: "bg-emerald-500/15" };
    case "watch":
      return { label: "จับตา", color: "text-amber-400", bg: "bg-amber-500/15" };
    case "ignore":
      return { label: "ข้ามได้", color: "text-text-muted", bg: "bg-bg-surface" };
    default:
      return { label: "รอประเมิน", color: "text-text-muted", bg: "bg-bg-surface" };
  }
}

// Sentiment → color
export function getSentimentMeta(sentiment: string) {
  switch (sentiment) {
    case "bullish":
      return { label: "ขาขึ้น", color: "text-buy", bg: "bg-buy/15", arrow: "↑" };
    case "bearish":
      return { label: "ขาลง", color: "text-sell", bg: "bg-sell/15", arrow: "↓" };
    default:
      return { label: "กลาง", color: "text-text-muted", bg: "bg-bg-surface", arrow: "→" };
  }
}

// Relative time in Thai
export function formatRelativeTime(isoDate: string): string {
  const now = Date.now();
  const then = new Date(isoDate).getTime();
  const diff = Math.floor((now - then) / 1000);

  if (diff < 0) {
    const absDiff = Math.abs(diff);
    if (absDiff < 60) return `อีก ${absDiff} วิ`;
    if (absDiff < 3600) return `อีก ${Math.floor(absDiff / 60)} นาที`;
    if (absDiff < 86400) return `อีก ${Math.floor(absDiff / 3600)} ชม.`;
    return `อีก ${Math.floor(absDiff / 86400)} วัน`;
  }

  if (diff < 60) return "เมื่อกี้";
  if (diff < 3600) return `${Math.floor(diff / 60)} นาทีที่แล้ว`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} ชม.ที่แล้ว`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} วันที่แล้ว`;
  return new Date(isoDate).toLocaleDateString("th-TH", { day: "numeric", month: "short" });
}

// Thai time format
export function formatThaiTime(isoDate: string): string {
  return new Date(isoDate).toLocaleString("th-TH", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "short",
    timeZone: "Asia/Bangkok",
  });
}

// Filter + sort news
export type NewsSortBy = "latest" | "impact" | "volatility" | "sentiment";

export function filterAndSortNews(
  items: NewsItem[],
  filters: {
    search?: string;
    pair?: string;
    currency?: string;
    impact?: string;
    category?: string;
    source?: string;
    actionability?: string;
    onlyUrgent?: boolean;
  },
  sortBy: NewsSortBy = "latest"
): NewsItem[] {
  let result = items;

  if (filters.search) {
    const q = filters.search.toLowerCase();
    result = result.filter(
      (n) =>
        n.title_original?.toLowerCase().includes(q) ||
        n.title_th?.toLowerCase().includes(q) ||
        n.summary_original?.toLowerCase().includes(q) ||
        n.summary_th?.toLowerCase().includes(q)
    );
  }

  if (filters.pair) result = result.filter((n) => n.pair === filters.pair);
  if (filters.currency) result = result.filter((n) => n.currency?.includes(filters.currency!));
  if (filters.impact) result = result.filter((n) => n.impact_level === filters.impact);
  if (filters.category) result = result.filter((n) => n.category === filters.category);
  if (filters.source) result = result.filter((n) => n.source === filters.source || n.source === `${filters.source}_xml`);
  if (filters.actionability) result = result.filter((n) => n.actionability === filters.actionability);
  if (filters.onlyUrgent) result = result.filter((n) => n.is_urgent);

  switch (sortBy) {
    case "impact":
      return [...result].sort((a, b) => (b.impact_score ?? 0) - (a.impact_score ?? 0));
    case "volatility":
      return [...result].sort((a, b) => (b.expected_volatility_pips ?? 0) - (a.expected_volatility_pips ?? 0));
    case "sentiment":
      return [...result].sort((a, b) => Math.abs(b.sentiment_score ?? 0) - Math.abs(a.sentiment_score ?? 0));
    case "latest":
    default:
      return [...result].sort((a, b) => new Date(b.scraped_at).getTime() - new Date(a.scraped_at).getTime());
  }
}
