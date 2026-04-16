"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Newspaper, RefreshCw, ArrowUpRight } from "lucide-react";
import type { NewsItem } from "@/lib/api";
import { NewsCard } from "@/components/news/news-card";
import { NewsDetailDialog } from "@/components/news/news-detail-dialog";

interface NewsFeedProps {
  items: NewsItem[];
  onRefresh?: () => void;
  loading?: boolean;
}

export function NewsFeed({ items, onRefresh, loading }: NewsFeedProps) {
  const [selected, setSelected] = useState<NewsItem | null>(null);

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-primary-400" />
            <CardTitle>ข่าวล่าสุด</CardTitle>
          </div>
          <div className="flex items-center gap-1">
            <Link
              href="/news"
              className="flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-bg-surface text-[11px] text-primary-400 transition-colors"
            >
              ดูทั้งหมด
              <ArrowUpRight className="w-3 h-3" />
            </Link>
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={loading}
                className="p-1.5 rounded-lg hover:bg-bg-surface transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 text-text-muted ${loading ? "animate-spin" : ""}`} />
              </button>
            )}
          </div>
        </CardHeader>

        <p className="text-[11px] text-text-muted -mt-1 mb-2">
          ข่าวเศรษฐกิจที่ส่งผลต่อตลาด Forex • กดเพื่อดูรายละเอียด
        </p>

        <div className="flex flex-col gap-1.5 max-h-80 overflow-y-auto -mx-1 px-1">
          {items.length === 0 && (
            <div className="py-6 text-center">
              <p className="text-sm text-text-muted">ยังไม่มีข่าว</p>
              <p className="text-[11px] text-text-muted mt-1">กดปุ่ม ↻ เพื่อดึงข่าวล่าสุด</p>
            </div>
          )}
          {items.slice(0, 8).map((item, i) => (
            <NewsCard
              key={`${item.source}-${i}`}
              item={item}
              variant="compact"
              onClick={() => setSelected(item)}
            />
          ))}
        </div>
      </Card>

      <NewsDetailDialog item={selected} open={!!selected} onClose={() => setSelected(null)} />
    </>
  );
}
