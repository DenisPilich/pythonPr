import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { JobListItem } from "../api/types";
import JobCard from "./JobCard";

const job: JobListItem = {
  id: "job-1",
  title: "Senior Python Developer",
  company: {
    id: "company-1",
    name: "Acme",
    normalized_name: "acme",
    website: null,
    logo_url: null,
  },
  url: "https://example.com/jobs/1",
  location_raw: "Remote",
  city: null,
  country_code: null,
  work_format: "remote",
  seniority: "senior",
  language: "en",
  salary_min: 5000,
  salary_max: 5000,
  salary_currency: "EUR",
  salary_period: "month",
  salary_monthly_eur: "5000",
  published_at: "2026-11-01T10:00:00Z",
  first_seen_at: "2026-11-01T10:05:00Z",
  technologies: [
    { slug: "python", name: "Python", category: "language" },
    { slug: "fastapi", name: "FastAPI", category: "framework" },
  ],
  sources: [{ source: "hh", name: "hh.ru", url: "https://example.com/jobs/1" }],
};

describe("JobCard", () => {
  it("renders the vacancy with score and technologies", () => {
    render(
      <MemoryRouter>
        <JobCard job={job} score={87} />
      </MemoryRouter>,
    );

    expect(screen.getByText("Senior Python Developer")).toBeInTheDocument();
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByText("87%")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("FastAPI")).toBeInTheDocument();
    expect(screen.getByText("~€5 000 / month")).toBeInTheDocument();

    const link = screen.getByRole("link", { name: "Senior Python Developer" });
    expect(link).toHaveAttribute("href", "/jobs/job-1");
  });
});
