import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { CheckCircle2, Circle, Map as MapIcon } from "lucide-react";

import * as roadmapsApi from "@/services/roadmaps";
import type { ApiErrorBody } from "@/types/auth";
import type { CompanyTrackDetail, Milestone } from "@/types/roadmaps";

function extractError(err: unknown): string {
  if (err instanceof AxiosError) {
    const body = err.response?.data as ApiErrorBody | undefined;
    return body?.message || body?.detail || err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

export function RoadmapsPage() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ["roadmaps"],
    queryFn: roadmapsApi.listRoadmaps,
  });

  const activeCompany = useMemo(() => {
    if (selected) return selected;
    const enrolled = listQuery.data?.find((t) => t.enrolled);
    return enrolled?.company ?? listQuery.data?.[0]?.company ?? "google";
  }, [listQuery.data, selected]);

  const detailQuery = useQuery({
    queryKey: ["roadmaps", activeCompany],
    queryFn: () => roadmapsApi.getRoadmap(activeCompany),
    enabled: !!activeCompany,
  });

  const enrollMutation = useMutation({
    mutationFn: () => roadmapsApi.enrollRoadmap(activeCompany),
    onSuccess: async () => {
      setMessage(`Enrolled in ${activeCompany} track`);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["roadmaps"] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, done }: { id: string; done: boolean }) =>
      roadmapsApi.toggleMilestone(activeCompany, id, done),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["roadmaps"] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const archiveMutation = useMutation({
    mutationFn: () => roadmapsApi.archiveRoadmap(activeCompany),
    onSuccess: async () => {
      setMessage("Track archived");
      await queryClient.invalidateQueries({ queryKey: ["roadmaps"] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const detail = detailQuery.data;
  const tracks = listQuery.data ?? [];

  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-[0.2em] text-ink-muted">Targets</p>
        <h1 className="font-display text-3xl text-ink sm:text-4xl">Company roadmaps</h1>
        <p className="max-w-2xl text-ink-muted">
          Enroll in a Google, Amazon, Meta, or other track. Milestones auto-complete from your
          resumes, coding, interviews, coach plans, and reports — or check them off manually.
        </p>
      </div>

      {error && <p className="text-sm text-rose-300">{error}</p>}
      {message && <p className="text-sm text-emerald-300">{message}</p>}

      <div className="flex flex-wrap gap-2 border-t border-white/10 pt-6">
        {tracks.map((t) => (
          <button
            key={t.company}
            type="button"
            onClick={() => {
              setSelected(t.company);
              setMessage(null);
              setError(null);
            }}
            className={[
              "rounded-lg border px-3 py-2 text-left text-sm transition",
              t.company === activeCompany
                ? "border-accent/50 bg-accent/10 text-ink"
                : "border-white/10 text-ink-muted hover:text-ink",
            ].join(" ")}
          >
            <span className="font-medium">{t.name}</span>
            <span className="mt-0.5 block text-xs opacity-80">
              {t.progress_pct}% · {t.weeks}w
              {t.enrolled ? " · enrolled" : ""}
            </span>
          </button>
        ))}
      </div>

      {detailQuery.isLoading && <p className="text-ink-muted">Loading track…</p>}
      {detail && <TrackDetail detail={detail} onEnroll={() => enrollMutation.mutate()} enrollPending={enrollMutation.isPending} onArchive={() => archiveMutation.mutate()} onToggle={(m, done) => toggleMutation.mutate({ id: m.id, done })} />}
    </div>
  );
}

function TrackDetail({
  detail,
  onEnroll,
  enrollPending,
  onArchive,
  onToggle,
}: {
  detail: CompanyTrackDetail;
  onEnroll: () => void;
  enrollPending: boolean;
  onArchive: () => void;
  onToggle: (m: Milestone, done: boolean) => void;
}) {
  const byWeek = useMemo(() => {
    const map = new Map<number, Milestone[]>();
    for (const m of detail.milestones) {
      const list = map.get(m.week) ?? [];
      list.push(m);
      map.set(m.week, list);
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0]);
  }, [detail.milestones]);

  return (
    <section className="space-y-8 border-t border-white/10 pt-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl space-y-3">
          <div className="flex items-center gap-2 text-accent">
            <MapIcon className="h-4 w-4" />
            <h2 className="font-display text-2xl text-ink">{detail.name}</h2>
          </div>
          <p className="text-ink-muted">{detail.tagline}</p>
          <p className="text-sm text-ink-muted">
            Focus: {detail.focus.join(" · ")} · {detail.done_count}/{detail.milestone_count} ·{" "}
            {detail.progress_pct}%
          </p>
          <div className="h-1.5 max-w-md overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full bg-accent transition-all"
              style={{ width: `${detail.progress_pct}%` }}
            />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {!detail.enrolled ? (
            <button
              type="button"
              className="btn-primary"
              disabled={enrollPending}
              onClick={onEnroll}
            >
              {enrollPending ? "Enrolling…" : "Enroll in track"}
            </button>
          ) : (
            <button type="button" className="btn-ghost" onClick={onArchive}>
              Archive
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 font-display text-lg text-ink">Interview loop</h3>
          <ol className="space-y-2 text-sm text-ink-muted">
            {detail.interview_loop.map((step, i) => (
              <li key={step}>
                {i + 1}. {step}
              </li>
            ))}
          </ol>
        </div>
        <div>
          <h3 className="mb-3 font-display text-lg text-ink">Principles</h3>
          <ul className="space-y-2 text-sm text-ink-muted">
            {detail.principles.map((p) => (
              <li key={p}>• {p}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="space-y-8">
        {byWeek.map(([week, items]) => (
          <div key={week}>
            <h3 className="mb-4 font-display text-lg text-ink">Week {week}</h3>
            <ul className="space-y-3">
              {items.map((m) => (
                <li
                  key={m.id}
                  className="flex gap-3 border-b border-white/5 pb-3 last:border-0"
                >
                  <button
                    type="button"
                    className="mt-0.5 shrink-0 text-accent disabled:opacity-40"
                    disabled={!detail.enrolled || m.done_via === "auto"}
                    title={
                      m.done_via === "auto"
                        ? "Auto-completed from your activity"
                        : detail.enrolled
                          ? "Toggle milestone"
                          : "Enroll to check off"
                    }
                    onClick={() => onToggle(m, !m.done)}
                  >
                    {m.done ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : (
                      <Circle className="h-5 w-5 opacity-60" />
                    )}
                  </button>
                  <div className="min-w-0 flex-1">
                    <p
                      className={[
                        "font-medium",
                        m.done ? "text-ink-muted line-through" : "text-ink",
                      ].join(" ")}
                    >
                      {m.title}
                    </p>
                    <p className="mt-1 text-sm text-ink-muted">{m.description}</p>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-ink-muted">
                      <span className="uppercase tracking-wide">{m.category}</span>
                      {m.done_via && <span>via {m.done_via}</span>}
                      {m.resource_path && (
                        <Link to={m.resource_path} className="text-accent hover:underline">
                          Open {m.resource_path.replace("/", "") || "app"}
                        </Link>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
