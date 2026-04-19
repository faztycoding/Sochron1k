"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, BarChart3, Newspaper, TrendingUp } from "lucide-react";

import { api } from "@/lib/api";
import type { PriceData, AnalysisResult, NewsItem, CurrencyStrength, SessionInfo, PairPerformance } from "@/lib/api";

import { PriceCard } from "@/components/dashboard/price-card";
import { NewsFeed } from "@/components/dashboard/news-feed";
import { SignalPanel } from "@/components/dashboard/signal-panel";
import { CurrencyStrengthBar } from "@/components/dashboard/currency-strength";
import { SessionInfoBar } from "@/components/dashboard/session-info";
import { PriceCardSkeleton } from "@/components/ui/skeleton";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { PAIRS, API_BASE } from "@/lib/constants";
import { tradeApi, type OverviewStats } from "@/lib/api-trade";

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
  numeric,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  accent?: string;
  numeric?: boolean;
}) {
  return (
    <div className="card-hover flex items-center gap-3 rounded-xl bg-bg-surface/80 backdrop-blur p-4 border border-border/30 hover:border-primary-500/40 group relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary-500/0 to-accent-500/0 group-hover:from-primary-500/5 group-hover:to-accent-500/5 transition-colors" />
      <div className="p-2 rounded-lg bg-primary-600/20 group-hover:bg-primary-600/30 transition-colors relative">
        <Icon className="w-5 h-5 text-primary-400 group-hover:text-primary-300 transition-colors" />
      </div>
      <div className="relative">
        <p className="text-xs text-text-muted">{label}</p>
        <p className={`text-lg font-semibold font-mono ${accent || ""}`}>
          {numeric && typeof value === "number" ? (
            <AnimatedNumber value={value} decimals={0} flashOnChange={false} />
          ) : (
            value
          )}
        </p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [prices, setPrices] = useState<Record<string, PriceData>>({});
  const [prevPrices, setPrevPrices] = useState<Record<string, number>>({});
  const [flashes, setFlashes] = useState<Record<string, "up" | "down" | null>>({});
  const [analyses, setAnalyses] = useState<Record<string, AnalysisResult | null>>({});
  const [performance, setPerformance] = useState<Record<string, PairPerformance>>({});
  const [news, setNews] = useState<NewsItem[]>([]);
  const [strength, setStrength] = useState<CurrencyStrength | null>(null);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [tradeStats, setTradeStats] = useState<OverviewStats | null>(null);
  const [newsLoading, setNewsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const sseRef = useRef<EventSource | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoadError(null);
      // Batch 1: core dashboard data (all parallel)
      const [priceRes, sessionRes, perfRes, newsRes, strengthRes, tradeStatsRes] =
        await Promise.allSettled([
          api.prices.realtime(),
          api.analysis.session(),
          api.prices.performance(),
          api.news.list(10),
          api.indicators.strength(),
          tradeApi.stats.overview(),
        ]);

      if (priceRes.status === "fulfilled") setPrices(priceRes.value.prices);
      if (sessionRes.status === "fulfilled") setSession(sessionRes.value);
      if (perfRes.status === "fulfilled") setPerformance(perfRes.value.performance);
      if (newsRes.status === "fulfilled") setNews(newsRes.value.items || []);
      if (strengthRes.status === "fulfilled") setStrength(strengthRes.value);
      if (tradeStatsRes.status === "fulfilled") setTradeStats(tradeStatsRes.value);

      // Batch 2: analysis for all pairs IN PARALLEL (backend now caches + parallelizes)
      const analysisPromises = PAIRS.map(async (p) => {
        try {
          const result = await api.analysis.run(p);
          return [p, result] as const;
        } catch {
          return [p, null] as const;
        }
      });
      const analysisResults = await Promise.all(analysisPromises);
      const newAnalyses: Record<string, AnalysisResult | null> = {};
      for (const [pair, result] of analysisResults) newAnalyses[pair] = result;
      setAnalyses(newAnalyses);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "โหลดข้อมูลล้มเหลว");
    }
  }, []);

  const refreshNews = async () => {
    setNewsLoading(true);
    try {
      await api.news.refresh();
      const res = await api.news.list(10);
      setNews(res.items || []);
    } catch {
      // silent
    }
    setNewsLoading(false);
  };

  // SSE real-time price stream with exponential backoff reconnect
  useEffect(() => {
    let attempts = 0;
    let reconnectTimer: NodeJS.Timeout | null = null;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      const sse = new EventSource(`${API_BASE}/price/stream`);
      sseRef.current = sse;

      sse.onopen = () => {
        attempts = 0; // reset backoff on successful connection
      };

      sse.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.prices) {
            setPrices((prev) => {
              const newFlashes: Record<string, "up" | "down" | null> = {};
              for (const [pair, pData] of Object.entries(data.prices) as [string, PriceData][]) {
                const oldPrice = prev[pair]?.price;
                if (oldPrice && pData.price !== oldPrice) {
                  newFlashes[pair] = pData.price > oldPrice ? "up" : "down";
                }
              }
              if (Object.keys(newFlashes).length > 0) {
                setFlashes(newFlashes);
                setTimeout(() => setFlashes({}), 600);
              }
              return data.prices;
            });
          }
        } catch {
          // parse error — skip
        }
      };

      sse.onerror = () => {
        sse.close();
        if (cancelled) return;
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 30s)
        const delay = Math.min(1000 * Math.pow(2, attempts), 30_000);
        attempts += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      sseRef.current?.close();
      sseRef.current = null;
    };
  }, []);

  useEffect(() => {
    loadData();
    const dataInterval = setInterval(loadData, 120_000); // full reload every 2 min
    return () => {
      clearInterval(dataInterval);
    };
  }, [loadData]);

  const signalCount = Object.values(analyses).filter(
    (a) => a && a.direction !== "NO_TRADE" && a.confidence >= 0.5
  ).length;

  return (
    <main className="min-h-screen px-4 sm:px-6 py-4 max-w-7xl mx-auto animate-fade-in">
      {/* Session */}
      <div className="mb-5">
        <SessionInfoBar session={session} />
      </div>

      {loadError && (
        <div className="mb-4 p-3 rounded-xl bg-danger-dim/20 border border-danger/30 text-sm text-danger">
          {loadError} — ข้อมูลจะอัพเดทอัตโนมัติ
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6 stagger-children">
        <StatCard
          icon={TrendingUp}
          label="สัญญาณวันนี้"
          value={signalCount}
          numeric
          accent={signalCount > 0 ? "text-buy" : ""}
        />
        <StatCard
          icon={Activity}
          label="Win Rate"
          value={
            tradeStats && tradeStats.total_trades > 0
              ? `${(tradeStats.win_rate * 100).toFixed(1)}%`
              : "—"
          }
          accent={
            tradeStats && tradeStats.win_rate >= 0.5
              ? "text-emerald-400"
              : tradeStats && tradeStats.win_rate > 0
                ? "text-amber-400"
                : ""
          }
        />
        <StatCard icon={Newspaper} label="ข่าวล่าสุด" value={news.length} numeric />
        <StatCard
          icon={BarChart3}
          label="เทรดทั้งหมด"
          value={tradeStats?.total_trades ?? 0}
          numeric
        />
      </div>

      {/* Price Cards */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-text-secondary flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-gradient-to-b from-primary-400 to-accent-400" />
            ราคาเรียลไทม์
            <span className="text-[10px] text-text-muted font-normal">อัพเดททุกวิผ่าน WebSocket</span>
          </h2>
          <span className="text-[11px] text-text-muted">
            {Object.keys(prices).length}/{PAIRS.length} คู่
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 stagger-children">
          {PAIRS.map((pair) =>
            prices[pair] || performance[pair] ? (
              <PriceCard
                key={pair}
                pair={pair}
                price={prices[pair]}
                analysis={analyses[pair]}
                performance={performance[pair]}
                flash={flashes[pair]}
              />
            ) : (
              <PriceCardSkeleton key={pair} />
            )
          )}
        </div>
      </div>

      {/* Bottom grid: Signals + News + Strength */}
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-text-secondary flex items-center gap-2 mb-3">
          <span className="w-1 h-4 rounded-full bg-gradient-to-b from-accent-400 to-primary-400" />
          ข้อมูลตลาด
        </h2>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 stagger-children">
        <div className="lg:col-span-1">
          <SignalPanel analyses={analyses} news={news} />
        </div>
        <div className="lg:col-span-1">
          <NewsFeed items={news} onRefresh={refreshNews} loading={newsLoading} />
        </div>
        <div className="lg:col-span-1">
          <CurrencyStrengthBar data={strength} />
        </div>
      </div>
    </main>
  );
}
