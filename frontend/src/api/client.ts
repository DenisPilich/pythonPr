import type {
  Analysis,
  HistoryPage,
  HistoryCounts,
  JobDetail,
  JobFilters,
  JobListItem,
  Page,
  Profile,
  ProfilePayload,
  Stats,
  TechnologyCategory,
  TechnologyRead,
  VacancyStatus,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
const API_KEY = import.meta.env.VITE_API_KEY ?? "dev-secret-change-me";
const TELEGRAM_ID = import.meta.env.VITE_TELEGRAM_ID ?? "100000001";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, message: string, code = "error") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  headers.set("X-API-Key", API_KEY);
  headers.set("X-Telegram-Id", TELEGRAM_ID);

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let detail = `Request failed with ${response.status}`;
    let code = "error";
    try {
      const problem = await response.json();
      detail = problem.detail ?? detail;
      code = problem.code ?? code;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(response.status, detail, code);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function query(params: object): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params as Record<string, unknown>)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const item of value) search.append(key, String(item));
    } else {
      search.set(key, String(value));
    }
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  async jobs(filters: JobFilters = {}): Promise<Page<JobListItem>> {
    return request<Page<JobListItem>>(`/jobs${query(filters)}`);
  },

  async job(id: string): Promise<JobDetail> {
    return request<JobDetail>(`/jobs/${id}`);
  },

  async analysis(id: string): Promise<Analysis | null> {
    try {
      return await request<Analysis>(`/jobs/${id}/analysis`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },

  async analyze(id: string): Promise<Analysis> {
    return request<Analysis>(`/jobs/${id}/analyze`, { method: "POST" });
  },

  async stats(): Promise<Stats> {
    return request<Stats>("/stats");
  },

  async profile(): Promise<Profile | null> {
    try {
      return await request<Profile>("/profile");
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },

  async updateProfile(payload: ProfilePayload): Promise<Profile> {
    return request<Profile>("/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async history(status?: VacancyStatus): Promise<HistoryPage> {
    return request<HistoryPage>(`/history${query({ status, limit: 50 })}`);
  },

  async technologies(category?: TechnologyCategory): Promise<Page<TechnologyRead>> {
    return request<Page<TechnologyRead>>(`/technologies${query({ category, limit: 100 })}`);
  },
};

export const historyCountsEmpty: HistoryCounts = {
  new: 0,
  viewed: 0,
  saved: 0,
  applied: 0,
  rejected: 0,
  total: 0,
};
