import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "text" | "circle" | "card";
}

export function Skeleton({ className, variant = "default", ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "skeleton",
        variant === "text" && "h-4 rounded",
        variant === "circle" && "rounded-full",
        variant === "card" && "h-32 rounded-2xl",
        className
      )}
      {...props}
    />
  );
}

/** Skeleton for price card */
export function PriceCardSkeleton() {
  return (
    <div className="rounded-2xl p-5 bg-bg-card border border-border">
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-14" />
      </div>
      <Skeleton className="h-9 w-32 mb-2" />
      <Skeleton className="h-3 w-24 mb-4" />
      <div className="flex gap-2 mb-3">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-3 w-20" />
      </div>
      <Skeleton className="h-1.5 w-full rounded-full mb-3" />
      <div className="flex justify-between pt-3 border-t border-border/50">
        <Skeleton className="h-8 w-10" />
        <Skeleton className="h-8 w-10" />
        <Skeleton className="h-8 w-10" />
        <Skeleton className="h-8 w-10" />
      </div>
    </div>
  );
}

/** Skeleton for news card (compact) */
export function NewsCardSkeleton() {
  return (
    <div className="p-3 rounded-xl bg-bg-surface/50 border border-transparent">
      <div className="flex items-start gap-3">
        <Skeleton className="w-1 self-stretch rounded-full" />
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-3 w-10" />
            <Skeleton className="h-3 w-16 ml-auto" />
          </div>
          <Skeleton className="h-4 w-full mb-1" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    </div>
  );
}
