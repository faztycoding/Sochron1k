import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef } from "react";
import { Loader2 } from "lucide-react";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl font-medium transition-all btn-press focus-ring disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none relative overflow-hidden",
  {
    variants: {
      variant: {
        primary: "btn-gradient text-white shadow-lg shadow-primary-600/20 hover:shadow-primary-600/40",
        secondary: "bg-bg-surface hover:bg-bg-elevated text-text-primary border border-border hover:border-primary-500/40",
        ghost: "hover:bg-bg-surface text-text-secondary hover:text-text-primary",
        outline: "border border-primary-500/40 text-primary-300 hover:bg-primary-500/10",
        danger: "bg-danger/90 hover:bg-danger text-white shadow-lg shadow-danger/20",
        success: "bg-success/90 hover:bg-success text-white shadow-lg shadow-success/20",
      },
      size: {
        sm: "text-xs px-3 py-1.5",
        md: "text-sm px-4 py-2",
        lg: "text-base px-5 py-2.5",
        icon: "p-2",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  }
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
  shine?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, shine, children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(buttonVariants({ variant, size }), shine && "shine-wrapper", className)}
        {...props}
      >
        {loading && <Loader2 className="w-4 h-4 animate-spin" />}
        <span className={cn("inline-flex items-center gap-2", loading && "opacity-70")}>
          {children}
        </span>
      </button>
    );
  }
);
Button.displayName = "Button";
