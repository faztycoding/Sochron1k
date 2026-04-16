import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary-900/50 text-primary-300 border border-primary-700/30",
        success: "bg-success-dim/30 text-success border border-success/20",
        danger: "bg-danger-dim/30 text-danger border border-danger/20",
        warning: "bg-warning-dim/30 text-warning border border-warning/20",
        neutral: "bg-bg-surface text-text-muted border border-border",
        buy: "bg-buy/15 text-buy border border-buy/25",
        sell: "bg-sell/15 text-sell border border-sell/25",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
