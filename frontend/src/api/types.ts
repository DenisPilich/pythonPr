export type WorkFormat = "remote" | "hybrid" | "office" | "unknown";
export type Seniority = "intern" | "junior" | "middle" | "senior" | "lead" | "unknown";
export type Recommendation = "apply" | "consider" | "skip";
export type VacancyStatus = "new" | "viewed" | "saved" | "applied" | "rejected";
export type SalaryPeriod = "hour" | "day" | "month" | "year" | "unknown";
export type TechnologyCategory =
  | "language"
  | "framework"
  | "database"
  | "devops"
  | "cloud"
  | "frontend"
  | "mobile"
  | "testing"
  | "messaging"
  | "other";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface CompanyBrief {
  id: string;
  name: string;
  normalized_name: string;
  website: string | null;
  logo_url: string | null;
}

export interface TechnologyBrief {
  slug: string;
  name: string;
  category: TechnologyCategory;
}

export interface TechnologyRead {
  id: string;
  slug: string;
  name: string;
  category: TechnologyCategory;
  aliases: string[];
  vacancy_count: number;
}

export interface SourceRef {
  source: string;
  name: string;
  url: string;
}

export interface JobListItem {
  id: string;
  title: string;
  company: CompanyBrief;
  url: string;
  location_raw: string | null;
  city: string | null;
  country_code: string | null;
  work_format: WorkFormat;
  seniority: Seniority;
  language: string;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  salary_period: SalaryPeriod;
  salary_monthly_eur: string | null;
  published_at: string | null;
  first_seen_at: string;
  technologies: TechnologyBrief[];
  sources: SourceRef[];
}

export interface JobDetail extends JobListItem {
  description: string;
  created_at: string;
  updated_at: string;
}

export interface JobFilters {
  q?: string;
  technology?: string[];
  seniority?: string[];
  work_format?: string[];
  min_salary?: number;
  source?: string;
  company?: string;
  sort?: string;
  order?: string;
  limit?: number;
  offset?: number;
}

export interface Analysis {
  id: string;
  vacancy_id: string;
  match_score: number;
  experience_match: string;
  skills_match: string;
  missing_skills: string[];
  strong_matches: string[];
  red_flags: string[];
  recommendation: Recommendation;
  reason: string;
  provider: string;
  model: string;
  is_degraded: boolean;
  prompt_version: string;
  created_at: string;
}

export interface DistributionItem {
  key: string;
  count: number;
  share: number;
}

export interface TechnologyStat {
  slug: string;
  name: string;
  count: number;
  share: number;
}

export interface CompanyStat {
  id: string;
  name: string;
  count: number;
}

export interface SourceStat {
  code: string;
  name: string;
  is_enabled: boolean;
  vacancies: number;
  last_success_at: string | null;
  last_run_status: string | null;
}

export interface Stats {
  generated_at: string;
  vacancies: {
    total: number;
    active: number;
    with_salary: number;
    new_last_7_days: number;
    remote: number;
    remote_share: number;
  };
  sources: SourceStat[];
  top_technologies: TechnologyStat[];
  top_companies: CompanyStat[];
  seniority: DistributionItem[];
  work_formats: DistributionItem[];
  languages: DistributionItem[];
  analyses: { analyses: number; average_match_score: number | null };
  collector_runs: { last_24h: number; failed_last_24h: number; last_status: string | null };
}

export interface Profile {
  id: string;
  telegram_id: number;
  headline: string | null;
  desired_positions: string[];
  target_seniority: Seniority[];
  skills: string[];
  preferred_stack: string[];
  excluded_stack: string[];
  english_level: string;
  min_salary_amount: number | null;
  salary_currency: string;
  preferred_locations: string[];
  work_formats: WorkFormat[];
  min_match_score: number;
  notifications_enabled: boolean;
  max_notifications_per_day: number;
  profile_hash: string;
  created_at: string;
  updated_at: string;
}

export type ProfilePayload = Omit<
  Profile,
  "id" | "telegram_id" | "profile_hash" | "created_at" | "updated_at"
>;

export interface HistoryItem {
  job: JobListItem;
  status: VacancyStatus;
  match_score: number | null;
  notified_at: string | null;
  created_at: string;
}

export interface HistoryCounts {
  new: number;
  viewed: number;
  saved: number;
  applied: number;
  rejected: number;
  total: number;
}

export interface HistoryPage extends Page<HistoryItem> {
  counts: HistoryCounts;
}
