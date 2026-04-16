"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Newspaper, Calculator, TrendingUp, Activity } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "แดชบอร์ด", icon: BarChart3 },
  { href: "/analysis", label: "วิเคราะห์", icon: TrendingUp },
  { href: "/news", label: "ข่าว", icon: Newspaper },
  { href: "/calculator", label: "คำนวณ", icon: Calculator },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/50 bg-bg-dark/70 backdrop-blur-xl supports-[backdrop-filter]:bg-bg-dark/60">
      {/* Ambient gradient glow */}
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary-500/30 to-transparent" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group btn-press">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-primary-500 to-accent-500 rounded-lg blur-md opacity-60 group-hover:opacity-100 transition-opacity" />
            <div className="relative w-8 h-8 rounded-lg btn-gradient flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-bold gradient-text leading-tight tracking-tight">Sochron1k</span>
            <span className="text-[9px] text-text-muted leading-tight hidden sm:block uppercase tracking-widest">Forex Intelligence</span>
          </div>
        </Link>

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all btn-press group",
                  active
                    ? "bg-primary-600/20 text-primary-300"
                    : "text-text-muted hover:text-text-primary hover:bg-bg-surface"
                )}
              >
                {active && (
                  <span className="absolute inset-0 rounded-lg border border-primary-500/30 pointer-events-none" />
                )}
                {active && (
                  <span className="absolute -bottom-[14px] left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full bg-gradient-to-r from-primary-400 to-accent-400" />
                )}
                <Icon className={cn("w-3.5 h-3.5 transition-transform", active && "scale-110")} />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
