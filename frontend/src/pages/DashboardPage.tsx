import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/contexts/AuthContext";
import * as analyticsApi from "@/services/analytics";
import type { SkillRadar } from "@/types/analytics";

export function DashboardPage() {
  const { user, loading, logout } = useAuth();
  const analyticsQuery = useQuery({
    queryKey: ["analytics", "me"],
    queryFn: () => analyticsApi.getMyAnalytics(true),
    enabled: !!user,
  });

  if (loading) {
    return <p className="text-ink-muted">Loading session…</p>;
  }

  if (!user) {
    return (
      <div className="glass-panel mx-auto max-w-lg p-8 text-center">
        <h1 className="font-display text-2xl font-semibold">Sign in required</h1>
        <Link to="/login" className="btn-primary mt-6 inline-flex">
          Go to login
        </Link>
      </div>
    );
  }

  const a = analyticsQuery.data?.analytics;
  const achievements = analyticsQuery.data?.achievements ?? [];
  const radar = a?.skill_radar;
  const roadmap = a?.roadmap ?? [];
  const series = a?.weekly_series ?? [];
  const maxSeries = Math.max(1, ...series.map((p) => p.interviews + p.coding + p.resumes));

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-[0.2em] text-accent">Dashboard</p>
        <h1 className="font-display text-3xl font-semibold text-ink">Hello, {user.full_name}</h1>
        <p className="text-ink-muted">
          {user.email} · streak {a?.current_streak_days ?? 0} day
          {(a?.current_streak_days ?? 0) === 1 ? "" : "s"}
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <Link to="/interviews" className="btn-primary">
            Mock interviews
          </Link>
          <Link to="/coding" className="btn-ghost">
            Coding
          </Link>
          <Link to="/resumes" className="btn-ghost">
            Resume & ATS
          </Link>
          <Link to="/reports" className="btn-ghost">
            Reports
          </Link>
          <Link to="/coach" className="btn-ghost">
            Coach
          </Link>
          <Link to="/roadmaps" className="btn-ghost">
            Roadmaps
          </Link>
          <Link to="/billing" className="btn-ghost">
            Billing
          </Link>
          {user.roles.includes("admin") && (
            <Link to="/admin" className="btn-ghost">
              Admin
            </Link>
          )}
          <button type="button" className="btn-ghost" onClick={() => void logout()}>
            Sign out
          </button>
        </div>
      </div>

      {analyticsQuery.isLoading && <p className="text-ink-muted">Loading progress…</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Interviews done" value={String(a?.completed_interviews ?? 0)} />
        <Stat
          label="Avg interview score"
          value={a?.average_score != null ? Number(a.average_score).toFixed(0) : "—"}
        />
        <Stat
          label="Coding accepted"
          value={`${a?.coding_accepted ?? 0}/${a?.coding_submissions ?? 0}`}
        />
        <Stat
          label="Latest ATS"
          value={a?.latest_ats_score != null ? Number(a.latest_ats_score).toFixed(0) : "—"}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <h2 className="font-display text-xl text-ink">Skill radar</h2>
          <p className="mt-1 text-sm text-ink-muted">Scores recomputed from your practice history.</p>
          <div className="mt-4 space-y-3">
            {(["technical", "behavioral", "communication", "coding", "resume"] as const).map(
              (key) => (
                <RadarBar key={key} label={key} value={radarValue(radar, key)} />
              ),
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <h2 className="font-display text-xl text-ink">Prep roadmap</h2>
          <ul className="mt-4 space-y-3">
            {roadmap.map((item) => (
              <li key={item.id} className="flex gap-3 text-sm">
                <span className={item.done ? "text-accent" : "text-ink-subtle"}>
                  {item.done ? "✓" : "○"}
                </span>
                <div>
                  <div className={item.done ? "text-ink-muted line-through" : "text-ink"}>
                    {item.title}
                  </div>
                  {!item.done && item.hint && (
                    <div className="text-xs text-ink-muted">{item.hint}</div>
                  )}
                </div>
              </li>
            ))}
            {roadmap.length === 0 && (
              <li className="text-sm text-ink-muted">Practice to unlock your roadmap.</li>
            )}
          </ul>
        </section>
      </div>

      <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
        <h2 className="font-display text-xl text-ink">Weekly activity</h2>
        <div className="mt-4 flex h-36 items-end gap-2">
          {series.map((point) => {
            const total = point.interviews + point.coding + point.resumes;
            const height = Math.max(4, Math.round((total / maxSeries) * 100));
            return (
              <div key={point.label} className="flex flex-1 flex-col items-center gap-2">
                <div
                  className="w-full rounded-t-md bg-accent/70"
                  style={{ height: `${height}%` }}
                  title={`${total} actions`}
                />
                <span className="text-[10px] text-ink-muted">{point.label}</span>
              </div>
            );
          })}
          {series.length === 0 && <p className="text-sm text-ink-muted">No weekly data yet.</p>}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-xl text-ink">Achievements</h2>
        <ul className="grid gap-3 sm:grid-cols-2">
          {achievements.map((ach) => (
            <li
              key={ach.code}
              className={[
                "rounded-xl border px-4 py-3",
                ach.unlocked
                  ? "border-accent/40 bg-accent/10"
                  : "border-white/10 bg-white/[0.02] opacity-60",
              ].join(" ")}
            >
              <div className="font-medium text-ink">
                {ach.title}{" "}
                <span className="text-xs text-ink-muted">+{ach.points} pts</span>
              </div>
              <p className="mt-1 text-sm text-ink-muted">{ach.description}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
      <div className="text-xs uppercase tracking-wider text-ink-muted">{label}</div>
      <div className="mt-1 font-display text-2xl text-ink">{value}</div>
    </div>
  );
}

function RadarBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-ink-muted">
        <span className="capitalize">{label}</span>
        <span>{value.toFixed(0)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div className="h-full rounded-full bg-accent" style={{ width: `${Math.min(100, value)}%` }} />
      </div>
    </div>
  );
}

function radarValue(radar: SkillRadar | null | undefined, key: keyof SkillRadar): number {
  if (!radar) return 0;
  return Number(radar[key] ?? 0);
}
