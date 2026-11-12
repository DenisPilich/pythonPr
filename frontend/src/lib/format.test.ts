import { describe, expect, it } from "vitest";

import type { JobListItem } from "../api/types";
import { formatSalary, formatShare, scoreTone, titleCase } from "./format";

function job(overrides: Partial<JobListItem> = {}): JobListItem {
  return {
    id: "1",
    title: "Python Developer",
    company: {
      id: "c1",
      name: "Acme",
      normalized_name: "acme",
      website: null,
      logo_url: null,
    },
    url: "https://example.com/1",
    location_raw: "Remote",
    city: null,
    country_code: null,
    work_format: "remote",
    seniority: "middle",
    language: "en",
    salary_min: null,
    salary_max: null,
    salary_currency: null,
    salary_period: "unknown",
    salary_monthly_eur: null,
    published_at: null,
    first_seen_at: "2026-11-01T10:00:00Z",
    technologies: [],
    sources: [],
    ...overrides,
  };
}

describe("formatSalary", () => {
  it("prefers the normalized monthly figure", () => {
    expect(formatSalary(job({ salary_monthly_eur: "5000" }))).toBe("~€5 000 / month");
  });

  it("formats ranges", () => {
    expect(
      formatSalary(
        job({
          salary_min: 60000,
          salary_max: 80000,
          salary_currency: "EUR",
          salary_period: "year",
        }),
      ),
    ).toBe("60 000–80 000 EUR / year");
  });

  it("handles missing salary", () => {
    expect(formatSalary(job())).toBe("Salary not specified");
  });
});

describe("helpers", () => {
  it("maps scores to tones", () => {
    expect(scoreTone(80)).toBe("high");
    expect(scoreTone(60)).toBe("medium");
    expect(scoreTone(20)).toBe("low");
  });

  it("formats shares", () => {
    expect(formatShare(0.426)).toBe("43%");
  });

  it("title-cases values", () => {
    expect(titleCase("remote")).toBe("Remote");
  });
});
