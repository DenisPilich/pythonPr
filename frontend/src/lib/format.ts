import type { JobListItem, VacancyStatus } from "../api/types";

const PERIOD: Record<string, string> = {
  hour: "hour",
  day: "day",
  month: "month",
  year: "year",
};

function thousands(value: number): string {
  return value.toLocaleString("en-US").replace(/,/g, " ");
}

export function formatSalary(job: JobListItem): string {
  if (job.salary_monthly_eur) {
    return `~€${thousands(Math.round(Number(job.salary_monthly_eur)))} / month`;
  }
  if (job.salary_min === null && job.salary_max === null) return "Salary not specified";
  const currency = job.salary_currency ? ` ${job.salary_currency}` : "";
  const period = PERIOD[job.salary_period] ?? "period";
  if (job.salary_min !== null && job.salary_max !== null) {
    return `${thousands(job.salary_min)}–${thousands(job.salary_max)}${currency} / ${period}`;
  }
  if (job.salary_min !== null) return `from ${thousands(job.salary_min)}${currency} / ${period}`;
  return `up to ${thousands(job.salary_max ?? 0)}${currency} / ${period}`;
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function formatRelative(value: string): string {
  const date = new Date(value);
  const days = Math.floor((Date.now() - date.getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  return formatDate(value);
}

export function formatShare(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function scoreTone(score: number): "high" | "medium" | "low" {
  if (score >= 75) return "high";
  if (score >= 50) return "medium";
  return "low";
}

export const STATUS_LABEL: Record<VacancyStatus, string> = {
  new: "New",
  viewed: "Viewed",
  saved: "Saved",
  applied: "Applied",
  rejected: "Skipped",
};

export function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
