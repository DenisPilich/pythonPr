import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";
import { Loader2, TriangleAlert } from "lucide-react";

import { cn } from "../lib/cn";
import { scoreTone } from "../lib/format";

type ButtonVariant = "primary" | "outline" | "ghost" | "danger";
type ButtonSize = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "border border-sky-500 bg-sky-500 text-slate-950 hover:bg-sky-400 hover:border-sky-400 disabled:bg-sky-500/40",
  outline:
    "border border-slate-700 bg-slate-900/40 text-slate-200 hover:border-sky-500 hover:text-sky-300",
  ghost:
    "border border-transparent text-slate-400 hover:border-slate-700 hover:text-sky-300",
  danger:
    "border border-rose-500/60 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20",
};

const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: "h-7 px-2.5 text-[9px]",
  md: "h-9 px-3.5 text-[10px]",
};

export function Button({
  className,
  variant = "primary",
  size = "md",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex cursor-pointer items-center justify-center gap-2 rounded-none font-mono font-medium uppercase tracking-[0.14em] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-500 disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "btn-sheen",
        BUTTON_VARIANTS[variant],
        BUTTON_SIZES[size],
        className,
      )}
      {...props}
    />
  );
}

export function Card({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return <div className={cn("panel", className)}>{children}</div>;
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-800 px-4 py-3">
      <div className="min-w-0">
        <p className="truncate text-[9px] uppercase tracking-[0.22em] text-slate-500">
          {subtitle ?? "radar://panel"}
        </p>
        <h2 className="mt-0.5 truncate text-[13px] font-medium text-slate-100">
          <span className="text-sky-400">// </span>
          {title}
        </h2>
      </div>
      {action}
    </div>
  );
}

type BadgeTone = "neutral" | "sky" | "emerald" | "amber" | "rose" | "violet";

const BADGE_TONES: Record<BadgeTone, string> = {
  neutral: "border-slate-700 bg-slate-800/60 text-slate-300",
  sky: "border-sky-500/40 bg-sky-500/10 text-sky-300",
  emerald: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  amber: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  rose: "border-rose-500/40 bg-rose-500/10 text-rose-300",
  violet: "border-violet-500/40 bg-violet-500/10 text-violet-300",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-none border px-1.5 py-0.5 font-mono text-[9px] font-medium uppercase tracking-[0.14em]",
        BADGE_TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function ScoreBadge({ score }: { score: number }) {
  const tone = scoreTone(score);
  return (
    <span
      className={cn(
        "inline-flex min-w-16 flex-col items-center justify-center border px-2 py-1",
        tone === "high" &&
          "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
        tone === "medium" &&
          "border-amber-500/40 bg-amber-500/10 text-amber-300",
        tone === "low" && "border-rose-500/40 bg-rose-500/10 text-rose-300",
      )}
    >
      <span className="font-display text-3xl leading-none">{score}%</span>
      <span className="mt-0.5 text-[8px] uppercase tracking-[0.2em] opacity-70">
        match
      </span>
    </span>
  );
}

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-none border border-slate-700 bg-black/30 px-2.5 font-mono text-[11px] text-slate-100 placeholder:text-slate-600 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/40",
        className,
      )}
      {...props}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "select-terminal h-9 w-full rounded-none border border-slate-700 bg-slate-950/80 px-2.5 font-mono text-[11px] text-slate-100 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/40",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 border border-slate-800 bg-slate-900/30 py-14 text-[10px] uppercase tracking-[0.2em] text-slate-500">
      <Loader2 className="h-4 w-4 animate-spin text-sky-400" aria-hidden />
      <span>[ {label} ]</span>
      <span className="terminal-cursor" aria-hidden />
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Card className="corner-frame mx-auto max-w-xl p-6">
      <div className="flex items-center gap-3 border-b border-rose-500/30 pb-3">
        <TriangleAlert className="h-5 w-5 text-rose-400" aria-hidden />
        <p className="text-[10px] uppercase tracking-[0.2em] text-rose-300">
          // runtime.error
        </p>
      </div>
      <p className="mt-4 font-mono text-xs text-slate-300">{message}</p>
      {onRetry ? (
        <Button className="mt-5" variant="outline" onClick={onRetry}>
          [ retry ]
        </Button>
      ) : null}
    </Card>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Card className="corner-frame p-10 text-center">
      <p className="text-[10px] uppercase tracking-[0.2em] text-sky-400">
        // no signal
      </p>
      <h2 className="mt-2 font-display text-3xl text-slate-100">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-xs leading-6 text-slate-400">
        {description}
      </p>
      {action ? <div className="mt-5">{action}</div> : null}
    </Card>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-col gap-4 border-b border-slate-800 pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-[9px] uppercase tracking-[0.28em] text-slate-500">
          radar://console <span className="text-slate-700">/</span> 2026
        </p>
        <h1 className="mt-1 flex items-start gap-2 py-1 font-display text-4xl leading-[1.05] text-white md:text-5xl">
          <span
            className="mt-1.5 inline-block h-4 w-1.5 shrink-0 bg-sky-500"
            aria-hidden
          />
          <span>{title}</span>
        </h1>
        {subtitle ? (
          <p className="mt-2 max-w-2xl text-[11px] text-slate-400">
            {subtitle}
          </p>
        ) : null}
      </div>
      {actions ? <div className="shrink-0">{actions}</div> : null}
    </div>
  );
}
