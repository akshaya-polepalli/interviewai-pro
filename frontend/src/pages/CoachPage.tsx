import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { CheckCircle2, Circle, MessageSquare, Sparkles } from "lucide-react";

import { SelectField } from "@/components/SelectField";
import * as coachApi from "@/services/coach";
import type { ApiErrorBody } from "@/types/auth";
import type { StudyPlanDetail, StudyPlanTask } from "@/types/coach";

function extractError(err: unknown): string {
  if (err instanceof AxiosError) {
    const body = err.response?.data as ApiErrorBody | undefined;
    return body?.message || body?.detail || err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

const WEEK_OPTIONS = [
  { value: "1", label: "1 week" },
  { value: "2", label: "2 weeks" },
  { value: "3", label: "3 weeks" },
  { value: "4", label: "4 weeks" },
];

export function CoachPage() {
  const queryClient = useQueryClient();
  const [weeks, setWeeks] = useState("2");
  const [ask, setAsk] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);

  const insightsQuery = useQuery({
    queryKey: ["coach", "insights"],
    queryFn: coachApi.getInsights,
  });

  const plansQuery = useQuery({
    queryKey: ["coach", "plans"],
    queryFn: coachApi.listPlans,
  });

  const activePlanId = useMemo(() => {
    if (selectedPlanId) return selectedPlanId;
    const plans = plansQuery.data ?? [];
    const active = plans.find((p) => p.status === "active");
    return active?.id ?? plans[0]?.id ?? null;
  }, [plansQuery.data, selectedPlanId]);

  const planQuery = useQuery({
    queryKey: ["coach", "plan", activePlanId],
    queryFn: () => coachApi.getPlan(activePlanId!),
    enabled: !!activePlanId,
  });

  const messagesQuery = useQuery({
    queryKey: ["coach", "messages"],
    queryFn: coachApi.listMessages,
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      coachApi.generatePlan({
        weeks: Number(weeks),
        focus_areas: insightsQuery.data?.focus_areas,
      }),
    onSuccess: async (plan) => {
      setSelectedPlanId(plan.id);
      setMessage("Study plan generated");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["coach"] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const taskMutation = useMutation({
    mutationFn: ({ taskId, isDone }: { taskId: string; isDone: boolean }) =>
      coachApi.updateTask(activePlanId!, taskId, isDone),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["coach"] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const askMutation = useMutation({
    mutationFn: () => coachApi.askCoach(ask.trim()),
    onSuccess: async () => {
      setAsk("");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["coach", "messages"] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const plan = planQuery.data;
  const insights = insightsQuery.data;

  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-[0.2em] text-ink-muted">Mentor</p>
        <h1 className="font-display text-3xl text-ink sm:text-4xl">AI Coach</h1>
        <p className="max-w-2xl text-ink-muted">
          Turn analytics into a day-by-day study plan, then ask for focused prep advice.
          Plans work offline; chat uses OpenAI when a key is configured.
        </p>
      </div>

      {error && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      )}
      {message && (
        <p className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
          {message}
        </p>
      )}

      <section className="grid gap-8 border-t border-white/10 pt-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-accent">
              <Sparkles className="h-4 w-4" />
              <h2 className="font-display text-xl text-ink">Insights</h2>
            </div>
            {insightsQuery.isLoading && <p className="text-ink-muted">Reading your progress…</p>}
            {insights && (
              <>
                <p className="text-lg text-ink">{insights.headline}</p>
                <ul className="space-y-2 text-sm text-ink-muted">
                  {insights.tips.map((tip) => (
                    <li key={tip}>• {tip}</li>
                  ))}
                </ul>
                {insights.weak_topics.length > 0 && (
                  <p className="text-sm text-ink-muted">
                    Weak topics: {insights.weak_topics.join(", ")}
                  </p>
                )}
              </>
            )}
          </div>

          <div className="flex flex-wrap items-end gap-4 border-t border-white/10 pt-6">
            <div className="w-40">
              <SelectField
                label="Plan length"
                value={weeks}
                onChange={setWeeks}
                options={WEEK_OPTIONS}
              />
            </div>
            <button
              type="button"
              className="btn-primary"
              disabled={generateMutation.isPending}
              onClick={() => generateMutation.mutate()}
            >
              {generateMutation.isPending ? "Generating…" : "Generate study plan"}
            </button>
          </div>

          {!!plansQuery.data?.length && (
            <div className="flex flex-wrap gap-2">
              {plansQuery.data.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={[
                    "rounded-lg border px-3 py-1.5 text-sm transition",
                    p.id === activePlanId
                      ? "border-accent/50 bg-accent/10 text-ink"
                      : "border-white/10 text-ink-muted hover:text-ink",
                  ].join(" ")}
                  onClick={() => setSelectedPlanId(p.id)}
                >
                  {p.title} · {p.done_count}/{p.task_count}
                </button>
              ))}
            </div>
          )}

          {plan && <PlanPanel plan={plan} onToggle={(task, done) => taskMutation.mutate({ taskId: task.id, isDone: done })} />}
          {!plan && !planQuery.isLoading && (
            <p className="text-ink-muted">No plan yet — generate one to get daily tasks.</p>
          )}
        </div>

        <div className="space-y-4 border-t border-white/10 pt-6 lg:border-t-0 lg:border-l lg:pl-8 lg:pt-0">
          <div className="flex items-center gap-2 text-accent">
            <MessageSquare className="h-4 w-4" />
            <h2 className="font-display text-xl text-ink">Ask the coach</h2>
          </div>
          <div className="max-h-[28rem] space-y-3 overflow-y-auto pr-1">
            {(messagesQuery.data ?? []).length === 0 && (
              <p className="text-sm text-ink-muted">
                Try: “Help me plan the next two weeks” or “How should I prep behavioral?”
              </p>
            )}
            {(messagesQuery.data ?? []).map((m) => (
              <div
                key={m.id}
                className={[
                  "rounded-xl px-3 py-2 text-sm whitespace-pre-wrap",
                  m.role === "user"
                    ? "ml-6 bg-accent/15 text-ink"
                    : "mr-6 border border-white/10 bg-white/[0.03] text-ink-muted",
                ].join(" ")}
              >
                {m.content}
              </div>
            ))}
          </div>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (!ask.trim() || askMutation.isPending) return;
              askMutation.mutate();
            }}
          >
            <textarea
              className="field min-h-[96px] w-full resize-y"
              placeholder="Ask about coding, resumes, STAR stories, or your study plan…"
              value={ask}
              onChange={(e) => setAsk(e.target.value)}
              maxLength={2000}
            />
            <button
              type="submit"
              className="btn-primary"
              disabled={!ask.trim() || askMutation.isPending}
            >
              {askMutation.isPending ? "Thinking…" : "Send"}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}

function PlanPanel({
  plan,
  onToggle,
}: {
  plan: StudyPlanDetail;
  onToggle: (task: StudyPlanTask, done: boolean) => void;
}) {
  const progress =
    plan.task_count > 0 ? Math.round((plan.done_count / plan.task_count) * 100) : 0;

  return (
    <div className="space-y-4 border-t border-white/10 pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="font-display text-xl text-ink">{plan.title}</h2>
          <p className="mt-1 max-w-xl text-sm text-ink-muted">{plan.summary}</p>
        </div>
        <p className="text-sm text-ink-muted">
          {plan.done_count}/{plan.task_count} · {progress}% · {plan.status}
        </p>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
        <div className="h-full bg-accent transition-all" style={{ width: `${progress}%` }} />
      </div>
      <ul className="space-y-3">
        {plan.tasks.map((task) => (
          <li
            key={task.id}
            className="flex gap-3 border-b border-white/5 pb-3 last:border-0"
          >
            <button
              type="button"
              className="mt-0.5 shrink-0 text-accent"
              aria-label={task.is_done ? "Mark incomplete" : "Mark done"}
              onClick={() => onToggle(task, !task.is_done)}
            >
              {task.is_done ? (
                <CheckCircle2 className="h-5 w-5" />
              ) : (
                <Circle className="h-5 w-5 opacity-60" />
              )}
            </button>
            <div className="min-w-0 flex-1">
              <p className={["font-medium", task.is_done ? "text-ink-muted line-through" : "text-ink"].join(" ")}>
                {task.title}
              </p>
              {task.description && (
                <p className="mt-1 text-sm text-ink-muted">{task.description}</p>
              )}
              <div className="mt-2 flex flex-wrap gap-3 text-xs text-ink-muted">
                <span>{task.estimated_minutes} min</span>
                <span className="uppercase tracking-wide">{task.category}</span>
                {task.resource_path && (
                  <Link to={task.resource_path} className="text-accent hover:underline">
                    Open {task.resource_path.replace("/", "") || "app"}
                  </Link>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
