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

const PAIRS = ["EUR/USD", "USD/JPY", "EUR/JPY", "GBP/USD", "AUD/USD"];
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function StatCard({ icon: Icon, label, value, accent }: { icon: React.ElementType; label: string; value: string; accent?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-bg-surface/80 backdrop-blur p-4 border border-border/30 hover:border-primary-500/30 transition-colors">
      <div className="p-2 rounded-lg bg-primary-600/20">
        <Icon className="w-5 h-5 text-primary-400" />
      </div>
      <div>
        <p className="text-xs text-text-muted">{label}</p>
        <p className={`text-lg font-semibold font-mono ${accent || ""}`}>{value}</p>
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
  const [newsLoading, setNewsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const sseRef = useRef<EventSource | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoadError(null);
      const [priceRes, sessionRes, perfRes] = await Promise.allSettled([
        api.prices.realtime(),
        api.analysis.session(),
        api.prices.performance(),
      ]);

      if (priceRes.status === "fulfilled") setPrices(priceRes.value.prices);
      if (sessionRes.status === "fulfilled") setSession(sessionRes.value);
      if (perfRes.status === "fulfilled") setPerformance(perfRes.value.performance);

      const [newsRes, strengthRes] = await Promise.allSettled([
        api.news.list(10),
        api.indicators.strength(),
      ]);

      if (newsRes.status === "fulfilled") setNews(newsRes.value.items || []);
      if (strengthRes.status === "fulfilled") setStrength(strengthRes.value);

      // Analysis — run sequentially to avoid API rate limits
      const newAnalyses: Record<string, AnalysisResult | null> = {};
      for (const p of PAIRS) {
        try {
          newAnalyses[p] = await api.analysis.run(p);
        } catch {
          newAnalyses[p] = null;
        }
        setAnalyses({ ...newAnalyses });
      }
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

  // SSE real-time price stream
  useEffect(() => {
    const sse = new EventSource(`${API_BASE}/price/stream`);
    sseRef.current = sse;

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
        // parse error
      }
    };

    sse.onerror = () => {
      sse.close();
      // Reconnect after 5s
      setTimeout(() => {
        if (sseRef.current === sse) {
          sseRef.current = null;
        }
      }, 5000);
    };

    return () => {
      sse.close();
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
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatCard icon={TrendingUp} label="สัญญาณวันนี้" value={String(signalCount)} />
        <StatCard icon={Activity} label="Win Rate" value="—" />
        <StatCard icon={Newspaper} label="ข่าวล่าสุด" value={String(news.length)} />
        <StatCard icon={BarChart3} label="เทรดทั้งหมด" value="0" />
      </div>

      {/* Price Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-6">
        {PAIRS.map((pair) => (
          <PriceCard
            key={pair}
            pair={pair}
            price={prices[pair]}
            analysis={analyses[pair]}
            performance={performance[pair]}
            flash={flashes[pair]}
          />
        ))}
      </div>

      {/* Bottom grid: Signals + News + Strength */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
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
