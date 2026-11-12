import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";

import { api } from "../api/client";
import type { Profile, ProfilePayload, Seniority, WorkFormat } from "../api/types";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  ErrorState,
  Input,
  PageHeader,
  Select,
  Spinner,
} from "../components/ui";

const DEFAULT_PROFILE: ProfilePayload = {
  headline: null,
  desired_positions: [],
  target_seniority: [],
  skills: [],
  preferred_stack: [],
  excluded_stack: [],
  english_level: "unknown",
  min_salary_amount: null,
  salary_currency: "EUR",
  preferred_locations: [],
  work_formats: [],
  min_match_score: 70,
  notifications_enabled: true,
  max_notifications_per_day: 10,
};

function toPayload(profile: Profile): ProfilePayload {
  return {
    headline: profile.headline,
    desired_positions: profile.desired_positions,
    target_seniority: profile.target_seniority,
    skills: profile.skills,
    preferred_stack: profile.preferred_stack,
    excluded_stack: profile.excluded_stack,
    english_level: profile.english_level,
    min_salary_amount: profile.min_salary_amount,
    salary_currency: profile.salary_currency,
    preferred_locations: profile.preferred_locations,
    work_formats: profile.work_formats,
    min_match_score: profile.min_match_score,
    notifications_enabled: profile.notifications_enabled,
    max_notifications_per_day: profile.max_notifications_per_day,
  };
}

function splitList(value: string): string[] {
  return value
    .split(/[,\n;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

const SENIORITY: Seniority[] = ["junior", "middle", "senior"];
const FORMATS: WorkFormat[] = ["remote", "hybrid", "office"];

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile });

  const [form, setForm] = useState<ProfilePayload>(DEFAULT_PROFILE);
  const [positions, setPositions] = useState("");
  const [skills, setSkills] = useState("");
  const [stack, setStack] = useState("");
  const [locations, setLocations] = useState("");

  useEffect(() => {
    if (!profile.data) return;
    const payload = toPayload(profile.data);
    setForm(payload);
    setPositions(payload.desired_positions.join(", "));
    setSkills(payload.skills.join(", "));
    setStack(payload.preferred_stack.join(", "));
    setLocations(payload.preferred_locations.join(", "));
  }, [profile.data]);

  const save = useMutation({
    mutationFn: () =>
      api.updateProfile({
        ...form,
        desired_positions: splitList(positions),
        skills: splitList(skills),
        preferred_stack: splitList(stack),
        preferred_locations: splitList(locations),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["profile"], data);
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  function toggleSeniority(level: Seniority) {
    setForm((current) => ({
      ...current,
      target_seniority: current.target_seniority.includes(level)
        ? current.target_seniority.filter((item) => item !== level)
        : [...current.target_seniority, level],
    }));
  }

  function toggleFormat(format: WorkFormat) {
    setForm((current) => ({
      ...current,
      work_formats: current.work_formats.includes(format)
        ? current.work_formats.filter((item) => item !== format)
        : [...current.work_formats, format],
    }));
  }

  if (profile.isPending) return <Spinner label="Loading profile" />;
  if (profile.isError) {
    return <ErrorState message={profile.error.message} onRetry={() => profile.refetch()} />;
  }

  return (
    <div>
      <PageHeader
        title="Profile"
        subtitle="The same profile the Telegram bot uses. Scores are cached by its hash."
        actions={
          profile.data ? (
            <Badge tone="sky">hash {profile.data.profile_hash.slice(0, 8)}</Badge>
          ) : (
            <Badge tone="amber">not created yet</Badge>
          )
        }
      />

      <form onSubmit={submit} className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Matching preferences" subtitle="Used by prefilters and the LLM prompt" />
          <div className="grid gap-4 p-5">
            <label className="grid gap-1.5 text-sm">
              <span className="text-slate-300">Headline</span>
              <Input
                value={form.headline ?? ""}
                placeholder="Python backend developer, 3 years"
                onChange={(event) => setForm({ ...form, headline: event.target.value || null })}
              />
            </label>

            <label className="grid gap-1.5 text-sm">
              <span className="text-slate-300">Desired positions</span>
              <Input
                value={positions}
                placeholder="Python Backend Developer, Backend Engineer"
                onChange={(event) => setPositions(event.target.value)}
              />
            </label>

            <label className="grid gap-1.5 text-sm">
              <span className="text-slate-300">Skills</span>
              <textarea
                value={skills}
                onChange={(event) => setSkills(event.target.value)}
                rows={2}
                placeholder="Python, FastAPI, PostgreSQL, Docker"
                className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none"
              />
            </label>

            <label className="grid gap-1.5 text-sm">
              <span className="text-slate-300">Preferred stack</span>
              <Input
                value={stack}
                placeholder="FastAPI, PostgreSQL, Redis"
                onChange={(event) => setStack(event.target.value)}
              />
            </label>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="grid gap-1.5 text-sm">
                <span className="text-slate-300">Minimum salary</span>
                <Input
                  type="number"
                  min={0}
                  value={form.min_salary_amount ?? ""}
                  placeholder="2500"
                  onChange={(event) =>
                    setForm({
                      ...form,
                      min_salary_amount: event.target.value ? Number(event.target.value) : null,
                    })
                  }
                />
              </label>
              <label className="grid gap-1.5 text-sm">
                <span className="text-slate-300">Currency</span>
                <Select
                  value={form.salary_currency}
                  onChange={(event) => setForm({ ...form, salary_currency: event.target.value })}
                >
                  {["EUR", "USD", "GBP", "RUB", "PLN"].map((currency) => (
                    <option key={currency} value={currency}>
                      {currency}
                    </option>
                  ))}
                </Select>
              </label>
            </div>

            <label className="grid gap-1.5 text-sm">
              <span className="text-slate-300">Preferred locations</span>
              <Input
                value={locations}
                placeholder="Germany, Poland, Remote"
                onChange={(event) => setLocations(event.target.value)}
              />
            </label>

            <div className="grid gap-2">
              <span className="text-sm text-slate-300">Target seniority</span>
              <div className="flex gap-2">
                {SENIORITY.map((level) => (
                  <Button
                    key={level}
                    type="button"
                    size="sm"
                    variant={form.target_seniority.includes(level) ? "primary" : "outline"}
                    onClick={() => toggleSeniority(level)}
                  >
                    {level}
                  </Button>
                ))}
              </div>
            </div>

            <div className="grid gap-2">
              <span className="text-sm text-slate-300">Work formats</span>
              <div className="flex gap-2">
                {FORMATS.map((format) => (
                  <Button
                    key={format}
                    type="button"
                    size="sm"
                    variant={form.work_formats.includes(format) ? "primary" : "outline"}
                    onClick={() => toggleFormat(format)}
                  >
                    {format}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Notification rules" subtitle="Applied by the dispatcher" />
            <div className="grid gap-4 p-5">
              <label className="grid gap-1.5 text-sm">
                <span className="text-slate-300">English level</span>
                <Select
                  value={form.english_level}
                  onChange={(event) => setForm({ ...form, english_level: event.target.value })}
                >
                  {["unknown", "a1", "a2", "b1", "b2", "c1", "c2", "native"].map((level) => (
                    <option key={level} value={level}>
                      {level.toUpperCase()}
                    </option>
                  ))}
                </Select>
              </label>

              <label className="grid gap-1.5 text-sm">
                <span className="text-slate-300">Minimum match score: {form.min_match_score}%</span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={form.min_match_score}
                  onChange={(event) =>
                    setForm({ ...form, min_match_score: Number(event.target.value) })
                  }
                  className="accent-sky-500"
                />
              </label>

              <label className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-300">Telegram notifications</span>
                <input
                  type="checkbox"
                  checked={form.notifications_enabled}
                  onChange={(event) =>
                    setForm({ ...form, notifications_enabled: event.target.checked })
                  }
                  className="h-4 w-4 accent-sky-500"
                />
              </label>

              <Button type="submit" disabled={save.isPending}>
                <Save className="h-4 w-4" />
                {save.isPending ? "Saving…" : "Save profile"}
              </Button>
              {save.isSuccess ? (
                <p className="text-xs text-emerald-300">Profile saved and hash recomputed.</p>
              ) : null}
              {save.isError ? (
                <p className="text-xs text-rose-300">{save.error.message}</p>
              ) : null}
            </div>
          </Card>

          <Card className="p-5 text-xs leading-5 text-slate-400">
            <p className="font-medium text-slate-300">How it works</p>
            <p className="mt-1">
              Vacancies below the salary floor, outside the seniority list or in a different work
              format are filtered before the LLM. Everything else is scored against this profile.
            </p>
          </Card>
        </div>
      </form>
    </div>
  );
}
