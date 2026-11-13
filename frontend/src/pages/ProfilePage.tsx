import { FormEvent, useEffect, useState } from "react";
import type { ReactNode } from "react";
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

function Field({
  name,
  children,
}: {
  name: string;
  children: ReactNode;
}) {
  return (
    <label className="grid gap-1">
      <span className="text-[9px] uppercase tracking-[0.16em] text-slate-500">
        {name}:
      </span>
      {children}
    </label>
  );
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

  if (profile.isPending) return <Spinner label="reading profile" />;
  if (profile.isError) {
    return (
      <ErrorState message={profile.error.message} onRetry={() => profile.refetch()} />
    );
  }

  return (
    <div>
      <PageHeader
        title="Profile"
        subtitle="The same profile the Telegram bot uses. Scores are cached by its hash."
        actions={
          profile.data ? (
            <div className="flex items-center gap-2">
              <Badge tone="emerald">active</Badge>
              <Badge tone="sky">hash {profile.data.profile_hash.slice(0, 8)}</Badge>
            </div>
          ) : (
            <Badge tone="amber">not created yet</Badge>
          )
        }
      />

      <form onSubmit={submit} className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Card className="corner-frame">
          <CardHeader
            title="profile.kdl"
            subtitle="matching preferences"
            action={<span className="text-[9px] text-slate-600">[ editable ]</span>}
          />
          <div className="border-b border-slate-800 bg-black/20 px-4 py-2 text-[10px] text-slate-500">
            <span className="text-emerald-400">$</span> edit
            ~/.radar/profile --telegram=100000001
          </div>

          <div className="grid gap-4 p-4">
            <p className="code-label">identity</p>

            <Field name="headline">
              <Input
                value={form.headline ?? ""}
                placeholder="Python backend developer, 3 years"
                onChange={(event) =>
                  setForm({ ...form, headline: event.target.value || null })
                }
              />
            </Field>

            <Field name="desired_positions">
              <Input
                value={positions}
                placeholder="Python Backend Developer, Backend Engineer"
                onChange={(event) => setPositions(event.target.value)}
              />
            </Field>

            <Field name="skills">
              <textarea
                value={skills}
                onChange={(event) => setSkills(event.target.value)}
                rows={2}
                placeholder="Python, FastAPI, PostgreSQL, Docker"
                className="w-full rounded-none border border-slate-700 bg-black/30 px-2.5 py-2 font-mono text-[11px] text-slate-100 placeholder:text-slate-600 focus:border-sky-500 focus:outline-none"
              />
            </Field>

            <Field name="preferred_stack">
              <Input
                value={stack}
                placeholder="FastAPI, PostgreSQL, Redis"
                onChange={(event) => setStack(event.target.value)}
              />
            </Field>

            <div className="grid gap-4 md:grid-cols-2">
              <Field name="min_salary_amount">
                <Input
                  type="number"
                  min={0}
                  value={form.min_salary_amount ?? ""}
                  placeholder="2500"
                  onChange={(event) =>
                    setForm({
                      ...form,
                      min_salary_amount: event.target.value
                        ? Number(event.target.value)
                        : null,
                    })
                  }
                />
              </Field>
              <Field name="salary_currency">
                <Select
                  value={form.salary_currency}
                  onChange={(event) =>
                    setForm({ ...form, salary_currency: event.target.value })
                  }
                >
                  {["EUR", "USD", "GBP", "RUB", "PLN"].map((currency) => (
                    <option key={currency} value={currency}>
                      {currency}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>

            <Field name="preferred_locations">
              <Input
                value={locations}
                placeholder="Germany, Poland, Remote"
                onChange={(event) => setLocations(event.target.value)}
              />
            </Field>

            <div className="mt-1 border-t border-slate-800 pt-4">
              <p className="code-label">filters</p>
            </div>

            <div className="grid gap-2">
              <span className="text-[9px] uppercase tracking-[0.16em] text-slate-500">
                target_seniority:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {SENIORITY.map((level) => (
                  <Button
                    key={level}
                    type="button"
                    size="sm"
                    variant={
                      form.target_seniority.includes(level) ? "primary" : "outline"
                    }
                    onClick={() => toggleSeniority(level)}
                  >
                    {form.target_seniority.includes(level) ? "[x]" : "[ ]"} {level}
                  </Button>
                ))}
              </div>
            </div>

            <div className="grid gap-2">
              <span className="text-[9px] uppercase tracking-[0.16em] text-slate-500">
                work_formats:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {FORMATS.map((format) => (
                  <Button
                    key={format}
                    type="button"
                    size="sm"
                    variant={form.work_formats.includes(format) ? "primary" : "outline"}
                    onClick={() => toggleFormat(format)}
                  >
                    {form.work_formats.includes(format) ? "[x]" : "[ ]"} {format}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader
              title="notify.kdl"
              subtitle="dispatch rules"
              action={<Badge tone={form.notifications_enabled ? "emerald" : "rose"}>
                {form.notifications_enabled ? "on" : "off"}
              </Badge>}
            />
            <div className="grid gap-4 p-4">
              <Field name="english_level">
                <Select
                  value={form.english_level}
                  onChange={(event) =>
                    setForm({ ...form, english_level: event.target.value })
                  }
                >
                  {["unknown", "a1", "a2", "b1", "b2", "c1", "c2", "native"].map(
                    (level) => (
                      <option key={level} value={level}>
                        {level.toUpperCase()}
                      </option>
                    ),
                  )}
                </Select>
              </Field>

              <div>
                <div className="flex items-center justify-between text-[9px] uppercase tracking-[0.16em] text-slate-500">
                  <span>min_match_score:</span>
                  <span className="text-sky-300">{form.min_match_score}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={form.min_match_score}
                  onChange={(event) =>
                    setForm({ ...form, min_match_score: Number(event.target.value) })
                  }
                  className="mt-2 w-full accent-sky-500"
                />
              </div>

              <label className="flex items-center justify-between gap-3 border-t border-slate-800 pt-3 text-[10px] text-slate-300">
                <span>telegram_notifications</span>
                <input
                  type="checkbox"
                  checked={form.notifications_enabled}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      notifications_enabled: event.target.checked,
                    })
                  }
                  className="h-4 w-4 accent-sky-500"
                />
              </label>

              <Button type="submit" disabled={save.isPending}>
                <Save className="h-3.5 w-3.5" />
                {save.isPending ? "[ writing ]" : "[ write profile ]"}
              </Button>

              {save.isSuccess ? (
                <p className="text-[10px] text-emerald-300">
                  &gt; saved · profile_hash recomputed
                </p>
              ) : null}
              {save.isError ? (
                <p className="text-[10px] text-rose-300">&gt; {save.error.message}</p>
              ) : null}
            </div>
          </Card>

          <Card className="p-4">
            <p className="code-label">how_it_works</p>
            <p className="mt-2 text-[10px] leading-5 text-slate-400">
              Vacancies below the salary floor, outside the seniority list or in a
              different work format are filtered before the LLM. Everything else
              is scored against this profile.
            </p>
            <div className="mt-3 border-t border-slate-800 pt-2 text-[9px] text-slate-600">
              <p>prefilter → cache → provider → repair</p>
              <p className="mt-1 text-slate-500">
                hash ties every analysis to this exact configuration.
              </p>
            </div>
          </Card>
        </div>
      </form>
    </div>
  );
}
