"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Search, RefreshCw, Flame, X, Newspaper, Filter, SortAsc, LayoutGrid, List } from "lucide-react";

import { api } from "@/lib/api";
import type { NewsItem } from "@/lib/api";
import { NewsCard } from "@/components/news/news-card";
import { NewsDetailDialog } from "@/components/news/news-detail-dialog";
import {
  CATEGORY_META,
  SOURCE_META,
  CURRENCY_FLAGS,
  filterAndSortNews,
  formatRelativeTime,
  type NewsSortBy,
} from "@/lib/news-utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY", "GBP/USD", "AUD/USD"];
const CURRENCIES = ["EUR", "USD", "JPY", "GBP", "AUD"];
const IMPACT_LEVELS = [
  { value: "high", label: "สูง", color: "text-red-400" },
  { value: "medium", label: "ปานกลาง", color: "text-amber-400" },
  { value: "low", label: "ต่ำ", color: "text-blue-400" },
];

const SORT_OPTIONS: { value: NewsSortBy; label: string }[] = [
  { value: "latest", label: "ล่าสุด" },
  { value: "impact", label: "ผลกระทบสูง" },
  { value: "volatility", label: "Volatility สูง" },
  { value: "sentiment", label: "Sentiment แรง" },
];

export default function NewsPage() {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedNews, setSelectedNews] = useState<NewsItem | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [pair, setPair] = useState<string>("");
  const [currency, setCurrency] = useState<string>("");
  const [impact, setImpact] = useState<string>("");
  const [category, setCategory] = useState<string>("");
  const [source, setSource] = useState<string>("");
  const [onlyUrgent, setOnlyUrgent] = useState(false);
  const [sortBy, setSortBy] = useState<NewsSortBy>("latest");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const loadNews = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.news.list(100);
      setItems(res.items || []);
      setLastUpdated(new Date());
    } catch {
      // silent
    }
    setLoading(false);
  }, []);

  const refreshNews = async () => {
    setRefreshing(true);
    try {
      await api.news.refresh();
      await loadNews();
    } catch {
      // silent
    }
    setRefreshing(false);
  };

  useEffect(() => {
    loadNews();
    // Auto-refresh every 2 minutes
    const interval = setInterval(loadNews, 120_000);
    return () => clearInterval(interval);
  }, [loadNews]);

  const filtered = useMemo(
    () =>
      filterAndSortNews(
        items,
        { search, pair, currency, impact, category, source, onlyUrgent },
        sortBy
      ),
    [items, search, pair, currency, impact, category, source, onlyUrgent, sortBy]
  );

  const urgentNews = useMemo(() => items.filter((n) => n.is_urgent).slice(0, 3), [items]);
  const featured = filtered[0];
  const rest = filtered.slice(1);

  const hasFilters = !!(pair || currency || impact || category || source || onlyUrgent || search);
  const clearFilters = () => {
    setSearch("");
    setPair("");
    setCurrency("");
    setImpact("");
    setCategory("");
    setSource("");
    setOnlyUrgent(false);
  };

  // Source list from items
  const sources = useMemo(() => {
    const set = new Set<string>();
    items.forEach((i) => {
      const key = i.source?.replace("_xml", "");
      if (key) set.add(key);
    });
    return Array.from(set);
  }, [items]);

  return (
    <main className="min-h-screen max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-fade-in">
      {/* Header */}
      <div className="mb-5">
        <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold gradient-text flex items-center gap-2">
              <Newspaper className="w-6 h-6 text-primary-400" />
              ข่าวสาร Forex
            </h1>
            <p className="text-xs text-text-muted mt-0.5">
              ประเมินโดย AI ระดับโลก • อัพเดทแบบเรียลไทม์ • แปลไทยอัตโนมัติ
            </p>
          </div>

          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-[11px] text-text-muted hidden sm:block">
                อัพเดทล่าสุด {formatRelativeTime(lastUpdated.toISOString())}
              </span>
            )}
            <Button
              onClick={refreshNews}
              loading={refreshing}
              shine
              size="md"
            >
              {!refreshing && <RefreshCw className="w-4 h-4" />}
              <span className="hidden sm:inline">{refreshing ? "กำลังดึงข่าวใหม่..." : "ดึงข่าวใหม่"}</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Urgent ticker */}
      {urgentNews.length > 0 && (
        <div className="mb-4 p-3 rounded-xl bg-gradient-to-r from-red-500/15 via-red-500/5 to-transparent border border-red-500/30">
          <div className="flex items-center gap-2 mb-2">
            <Flame className="w-4 h-4 text-red-400 animate-pulse" />
            <span className="text-xs font-semibold text-red-300">ข่าวด่วน</span>
            <Badge variant="danger" className="text-[10px]">
              {urgentNews.length}
            </Badge>
          </div>
          <div className="flex flex-col gap-1.5">
            {urgentNews.map((n, i) => (
              <button
                key={i}
                onClick={() => setSelectedNews(n)}
                className="text-left flex items-center gap-2 text-xs text-text-secondary hover:text-text-primary transition-colors"
              >
                <span className="text-red-400 font-mono">●</span>
                <span className="flex-1 truncate">{n.title_th || n.title_original}</span>
                <span className="text-[10px] text-text-muted flex-shrink-0">
                  {formatRelativeTime(n.scraped_at)}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search + Sort + View */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="ค้นหาข่าว..."
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-bg-surface border border-border focus:border-primary-500/50 focus:outline-none text-sm"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-bg-elevated text-text-muted"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Sort */}
        <div className="flex gap-1 p-1 rounded-xl bg-bg-surface">
          {SORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setSortBy(opt.value)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                sortBy === opt.value
                  ? "bg-primary-600 text-white"
                  : "text-text-muted hover:text-text-primary"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* View mode */}
        <div className="flex gap-1 p-1 rounded-xl bg-bg-surface">
          <button
            onClick={() => setViewMode("grid")}
            className={cn(
              "p-1.5 rounded-lg transition-all",
              viewMode === "grid" ? "bg-primary-600 text-white" : "text-text-muted"
            )}
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={cn(
              "p-1.5 rounded-lg transition-all",
              viewMode === "list" ? "bg-primary-600 text-white" : "text-text-muted"
            )}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter chips */}
      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        {/* Urgent toggle */}
        <button
          onClick={() => setOnlyUrgent(!onlyUrgent)}
          className={cn(
            "flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium transition-all border",
            onlyUrgent
              ? "bg-red-500/20 text-red-300 border-red-500/40"
              : "bg-bg-surface text-text-muted border-border hover:border-red-500/30"
          )}
        >
          <Flame className="w-3 h-3" />
          ด่วน
        </button>

        {/* Pair filter */}
        {PAIRS.map((p) => (
          <FilterChip key={p} active={pair === p} onClick={() => setPair(pair === p ? "" : p)}>
            {p}
          </FilterChip>
        ))}

        <div className="w-px h-4 bg-border mx-1" />

        {/* Currency filter */}
        {CURRENCIES.map((c) => (
          <FilterChip key={c} active={currency === c} onClick={() => setCurrency(currency === c ? "" : c)}>
            <span className="mr-1">{CURRENCY_FLAGS[c]}</span>
            {c}
          </FilterChip>
        ))}

        <div className="w-px h-4 bg-border mx-1" />

        {/* Impact filter */}
        {IMPACT_LEVELS.map((imp) => (
          <FilterChip
            key={imp.value}
            active={impact === imp.value}
            onClick={() => setImpact(impact === imp.value ? "" : imp.value)}
            className={impact === imp.value ? "" : imp.color}
          >
            {imp.label}
          </FilterChip>
        ))}

        {/* Category filter */}
        <div className="w-px h-4 bg-border mx-1" />
        {Object.entries(CATEGORY_META).slice(0, 4).map(([key, meta]) => (
          <FilterChip
            key={key}
            active={category === key}
            onClick={() => setCategory(category === key ? "" : key)}
          >
            <span className="mr-1">{meta.icon}</span>
            {meta.label}
          </FilterChip>
        ))}

        {hasFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium text-text-muted hover:text-danger transition-colors ml-auto"
          >
            <X className="w-3 h-3" />
            ล้างตัวกรอง
          </button>
        )}
      </div>

      {/* Source filter chips (secondary) */}
      {sources.length > 0 && (
        <div className="flex items-center gap-1.5 mb-4 overflow-x-auto pb-1">
          <span className="text-[11px] text-text-muted flex-shrink-0">แหล่ง:</span>
          {sources.map((s) => {
            const meta = SOURCE_META[s] || { label: s, color: "text-text-muted" };
            return (
              <FilterChip key={s} active={source === s} onClick={() => setSource(source === s ? "" : s)}>
                <span className={meta.color}>{meta.label}</span>
              </FilterChip>
            );
          })}
        </div>
      )}

      {/* Results count */}
      <div className="flex items-center justify-between mb-3 text-xs text-text-muted">
        <span>
          พบ <span className="text-text-primary font-semibold">{filtered.length}</span> ข่าว
          {hasFilters && ` จาก ${items.length} ข่าวทั้งหมด`}
        </span>
      </div>

      {/* News grid / list */}
      {loading && items.length === 0 ? (
        <div className="py-12 text-center">
          <RefreshCw className="w-6 h-6 text-text-muted animate-spin mx-auto mb-2" />
          <p className="text-sm text-text-muted">กำลังโหลดข่าว...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-12 text-center">
          <Newspaper className="w-10 h-10 text-text-muted/40 mx-auto mb-3" />
          <p className="text-sm text-text-muted mb-1">
            {hasFilters ? "ไม่พบข่าวตามเงื่อนไข" : "ยังไม่มีข่าว"}
          </p>
          <p className="text-[11px] text-text-muted">
            {hasFilters ? "ลองปรับตัวกรองหรือเคลียร์ทั้งหมด" : "กดปุ่ม 'ดึงข่าวใหม่' ด้านบน"}
          </p>
        </div>
      ) : viewMode === "grid" ? (
        <>
          {/* Featured (first item) */}
          {featured && (
            <div className="mb-4">
              <NewsCard
                item={featured}
                variant="featured"
                onClick={() => setSelectedNews(featured)}
              />
            </div>
          )}

          {/* Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {rest.map((item, i) => (
              <NewsCard
                key={`${item.source}-${i}`}
                item={item}
                onClick={() => setSelectedNews(item)}
              />
            ))}
          </div>
        </>
      ) : (
        /* List view */
        <div className="flex flex-col gap-2">
          {filtered.map((item, i) => (
            <NewsCard
              key={`${item.source}-${i}`}
              item={item}
              variant="compact"
              onClick={() => setSelectedNews(item)}
            />
          ))}
        </div>
      )}

      {/* Detail Dialog */}
      <NewsDetailDialog
        item={selectedNews}
        open={!!selectedNews}
        onClose={() => setSelectedNews(null)}
      />
    </main>
  );
}

function FilterChip({
  active,
  onClick,
  children,
  className,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-2.5 py-1 rounded-full text-[11px] font-medium transition-all border whitespace-nowrap",
        active
          ? "bg-primary-600 text-white border-primary-500"
          : "bg-bg-surface text-text-secondary border-border hover:border-primary-500/30 hover:text-text-primary",
        className
      )}
    >
      {children}
    </button>
  );
}
