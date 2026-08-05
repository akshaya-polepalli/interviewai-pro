import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { ArrowLeft, CheckCircle2, Mic2, Trash2 } from "lucide-react";

import { SelectField } from "@/components/SelectField";
import { VoiceAnswerPanel } from "@/components/VoiceAnswerPanel";
import * as interviewsApi from "@/services/interviews";
import type { ApiErrorBody } from "@/types/auth";
import type { CreateInterviewPayload, InterviewType } from "@/types/interviews";

const TYPES: { value: InterviewType; label: string; blurb: string }[] = [
  { value: "technical", label: "Technical", blurb: "Systems, APIs, databases" },
  { value: "behavioral", label: "Behavioral", blurb: "STAR storytelling" },
  { value: "hr", label: "HR", blurb: "Motivation & fit" },
  { value: "voice", label: "Voice", blurb: "Speak answers aloud" },
];

const ROLE_OPTIONS = [
  "software_engineer",
  "backend_engineer",
  "frontend_engineer",
  "full_stack_engineer",
  "data_analyst",
  "ml_engineer",
  "devops_engineer",
  "student",
].map((r) => ({
  value: r,
  label: r.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()),
}));

const COMPANY_OPTIONS = [
  "general",
  "google",
  "amazon",
  "microsoft",
  "meta",
  "netflix",
  "stripe",
  "openai",
].map((c) => ({ value: c, label: c }));

const DIFFICULTY_OPTIONS = ["easy", "medium", "hard", "expert"].map((d) => ({
  value: d,
  label: d,
}));

function extractError(err: unknown): string {
  if (err instanceof AxiosError) {
    const body = err.response?.data as ApiErrorBody | undefined;
    return body?.error?.message || body?.message || body?.detail || err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

function scoreLabel(value: string | number | null | undefined): string {
  if (value == null || value === "") return "—";
  return `${Number(value).toFixed(0)}`;
}

export function InterviewsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [interviewType, setInterviewType] = useState<InterviewType>("technical");
  const [targetRole, setTargetRole] = useState("software_engineer");
  const [targetCompany, setTargetCompany] = useState("general");
  const [difficulty, setDifficulty] = useState("medium");
  const [questionCount, setQuestionCount] = useState(5);
  const [error, setError] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ["interviews"],
    queryFn: interviewsApi.listInterviews,
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateInterviewPayload) => interviewsApi.createInterview(payload),
    onSuccess: async (detail) => {
      await queryClient.invalidateQueries({ queryKey: ["interviews"] });
      navigate(`/interviews/${detail.id}`);
    },
    onError: (err) => setError(extractError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => interviewsApi.deleteInterview(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["interviews"] });
    },
    onError: (err) => setError(extractError(err)),
  });

  function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    createMutation.mutate({
      interview_type: interviewType,
      difficulty,
      target_role: interviewType === "hr" ? undefined : targetRole,
      target_company: targetCompany,
      question_count: questionCount,
    });
  }

  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-[0.2em] text-ink-muted">Practice</p>
        <h1 className="font-display text-3xl text-ink sm:text-4xl">AI mock interviews</h1>
        <p className="max-w-2xl text-ink-muted">
          Generate technical, behavioral, HR, or voice rounds. Voice mode speaks questions aloud and
          records your spoken answers.
        </p>
      </div>

      <form onSubmit={onCreate} className="grid gap-6 border-t border-white/10 pt-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-5">
          <div>
            <label className="mb-2 block text-sm text-ink-muted">Interview type</label>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setInterviewType(t.value)}
                  className={[
                    "rounded-xl border px-4 py-3 text-left transition",
                    interviewType === t.value
                      ? "border-accent/60 bg-accent/10 text-ink"
                      : "border-white/10 bg-white/5 text-ink-muted hover:border-white/20",
                  ].join(" ")}
                >
                  <div className="font-medium text-ink">{t.label}</div>
                  <div className="mt-1 text-xs">{t.blurb}</div>
                </button>
              ))}
            </div>
          </div>

          {interviewType !== "hr" && (
            <SelectField
              label="Target role"
              value={targetRole}
              onChange={setTargetRole}
              options={ROLE_OPTIONS}
            />
          )}

          <div className="grid gap-4 sm:grid-cols-3">
            <SelectField
              label="Company flavor"
              value={targetCompany}
              onChange={setTargetCompany}
              options={COMPANY_OPTIONS}
            />
            <SelectField
              label="Difficulty"
              value={difficulty}
              onChange={setDifficulty}
              options={DIFFICULTY_OPTIONS}
            />
            <div>
              <label className="mb-2 block text-sm text-ink-muted">Questions</label>
              <input
                className="field"
                type="number"
                min={1}
                max={10}
                value={questionCount}
                onChange={(e) => setQuestionCount(Number(e.target.value))}
              />
            </div>
          </div>

          {error && <p className="text-sm text-rose-300">{error}</p>}

          <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating…" : "Start new interview"}
          </button>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <div className="mb-4 flex items-center gap-2 text-accent">
            <Mic2 className="h-5 w-5" />
            <h2 className="font-display text-xl text-ink">How it works</h2>
          </div>
          <ol className="space-y-3 text-sm text-ink-muted">
            <li>1. Pick type, role, and company style.</li>
            <li>2. Answer each question in your own words.</li>
            <li>3. Complete the session for scored feedback (STAR + content coverage).</li>
          </ol>
        </div>
      </form>

      <section className="space-y-4 border-t border-white/10 pt-8">
        <h2 className="font-display text-2xl text-ink">Your sessions</h2>
        {listQuery.isLoading && <p className="text-ink-muted">Loading…</p>}
        {listQuery.data?.length === 0 && (
          <p className="text-ink-muted">No interviews yet — create one above.</p>
        )}
        <ul className="divide-y divide-white/10">
          {listQuery.data?.map((item) => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-4">
              <div>
                <Link to={`/interviews/${item.id}`} className="font-medium text-ink hover:text-accent">
                  {item.title}
                </Link>
                <p className="mt-1 text-sm text-ink-muted">
                  {item.interview_type} · {item.status} · {item.answered_count}/{item.question_count}{" "}
                  answered
                  {item.overall_score != null ? ` · score ${scoreLabel(item.overall_score)}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Link to={`/interviews/${item.id}`} className="btn-ghost text-sm">
                  Open
                </Link>
                <button
                  type="button"
                  className="btn-ghost text-sm text-rose-300"
                  onClick={() => deleteMutation.mutate(item.id)}
                  aria-label="Delete interview"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export function InterviewSessionPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeIndex, setActiveIndex] = useState(0);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number>(() => Date.now());

  const detailQuery = useQuery({
    queryKey: ["interview", id],
    queryFn: () => interviewsApi.getInterview(id!),
    enabled: !!id,
  });

  const detail = detailQuery.data;
  const questions = detail?.questions ?? [];
  const active = questions[activeIndex];

  useEffect(() => {
    if (!active) return;
    const existing = active.answers[active.answers.length - 1]?.answer_text ?? "";
    setDraft(existing);
    setStartedAt(Date.now());
  }, [active?.id]);

  const feedback = detail?.feedback;
  const isFinished = useMemo(
    () => detail?.status === "completed" || detail?.status === "evaluated",
    [detail?.status],
  );

  const startMutation = useMutation({
    mutationFn: () => interviewsApi.startInterview(id!),
    onSuccess: async (data) => {
      await queryClient.setQueryData(["interview", id], data);
      setMessage("Interview started");
    },
    onError: (err) => setError(extractError(err)),
  });

  const saveMutation = useMutation({
    mutationFn: () =>
      interviewsApi.submitAnswer(id!, {
        question_id: active!.id,
        answer_text: draft,
        time_spent_seconds: Math.max(1, Math.round((Date.now() - startedAt) / 1000)),
      }),
    onSuccess: async (data) => {
      await queryClient.setQueryData(["interview", id], data);
      setMessage("Answer saved");
      setError(null);
      if (activeIndex < questions.length - 1) {
        setActiveIndex((i) => i + 1);
      }
    },
    onError: (err) => setError(extractError(err)),
  });

  const voiceMutation = useMutation({
    mutationFn: (payload: { transcript: string; audio: Blob | null }) =>
      interviewsApi.submitVoiceAnswer(id!, {
        question_id: active!.id,
        transcript: payload.transcript || undefined,
        audio: payload.audio,
        filename: payload.audio?.type.includes("mp4") ? "answer.mp4" : "answer.webm",
        time_spent_seconds: Math.max(1, Math.round((Date.now() - startedAt) / 1000)),
      }),
    onSuccess: async (data) => {
      await queryClient.setQueryData(["interview", id], data);
      setMessage("Voice answer saved");
      setError(null);
      if (activeIndex < questions.length - 1) {
        setActiveIndex((i) => i + 1);
      }
    },
    onError: (err) => setError(extractError(err)),
  });

  const isVoice = detail?.interview_type === "voice";
  const completeMutation = useMutation({
    mutationFn: () => interviewsApi.completeInterview(id!, { evaluate: true, sync: true }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["interview", id] });
      await queryClient.invalidateQueries({ queryKey: ["interviews"] });
      setMessage("Interview evaluated");
    },
    onError: (err) => setError(extractError(err)),
  });

  if (detailQuery.isLoading) {
    return <p className="text-ink-muted">Loading interview…</p>;
  }
  if (!detail) {
    return (
      <div className="space-y-4">
        <p className="text-rose-300">Interview not found.</p>
        <Link to="/interviews" className="btn-ghost">
          Back
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <button
            type="button"
            className="inline-flex items-center gap-2 text-sm text-ink-muted hover:text-ink"
            onClick={() => navigate("/interviews")}
          >
            <ArrowLeft className="h-4 w-4" /> All interviews
          </button>
          <h1 className="font-display text-3xl text-ink">{detail.title}</h1>
          <p className="text-sm text-ink-muted">
            {detail.interview_type} · {detail.difficulty} · {detail.status}
            {detail.target_company ? ` · ${detail.target_company}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {detail.status === "draft" && (
            <button
              type="button"
              className="btn-primary"
              onClick={() => startMutation.mutate()}
              disabled={startMutation.isPending}
            >
              Begin
            </button>
          )}
          {!isFinished && (
            <button
              type="button"
              className="btn-primary"
              onClick={() => completeMutation.mutate()}
              disabled={completeMutation.isPending}
            >
              {completeMutation.isPending ? "Evaluating…" : "Complete & evaluate"}
            </button>
          )}
        </div>
      </div>

      {(error || message) && (
        <p className={error ? "text-sm text-rose-300" : "text-sm text-emerald-300"}>
          {error || message}
        </p>
      )}

      {feedback && (
        <section className="space-y-4 rounded-2xl border border-accent/30 bg-accent/5 p-6">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-accent" />
            <h2 className="font-display text-xl text-ink">Feedback</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-4">
            <ScoreTile label="Overall" value={feedback.overall_score} />
            <ScoreTile label="Content" value={feedback.technical_score} />
            <ScoreTile label="Communication" value={feedback.communication_score} />
            <ScoreTile
              label={feedback.star_method_score != null ? "STAR" : "Confidence"}
              value={feedback.star_method_score ?? feedback.confidence_score}
            />
          </div>
          {feedback.detailed_feedback && (
            <p className="text-sm leading-relaxed text-ink-muted">{feedback.detailed_feedback}</p>
          )}
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <h3 className="mb-2 text-sm font-medium text-ink">Strengths</h3>
              <ul className="space-y-1 text-sm text-ink-muted">
                {(feedback.strengths ?? []).map((s) => (
                  <li key={s}>• {s}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="mb-2 text-sm font-medium text-ink">Improvements</h3>
              <ul className="space-y-1 text-sm text-ink-muted">
                {(feedback.improvements ?? []).map((s) => (
                  <li key={s}>• {s}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      <div className="grid gap-8 lg:grid-cols-[220px_1fr]">
        <aside className="space-y-2">
          {questions.map((q, idx) => {
            const answered = q.answers.length > 0;
            return (
              <button
                key={q.id}
                type="button"
                onClick={() => setActiveIndex(idx)}
                className={[
                  "w-full rounded-lg border px-3 py-2 text-left text-sm transition",
                  idx === activeIndex
                    ? "border-accent/50 bg-accent/10 text-ink"
                    : "border-white/10 text-ink-muted hover:border-white/20",
                ].join(" ")}
              >
                Q{q.sequence}
                {answered ? " · saved" : ""}
                {q.answers[0]?.score != null ? ` · ${scoreLabel(q.answers[0].score)}` : ""}
              </button>
            );
          })}
        </aside>

        {active && (
          <section className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-wider text-ink-muted">
                {active.category.replaceAll("_", " ")}
                {active.difficulty ? ` · ${active.difficulty}` : ""}
                {isVoice ? " · voice" : ""}
              </p>
              <h2 className="mt-2 font-display text-2xl text-ink">{active.prompt}</h2>
            </div>
            {isVoice ? (
              <VoiceAnswerPanel
                key={active.id}
                questionText={active.prompt}
                initialTranscript={
                  active.answers[active.answers.length - 1]?.transcript ||
                  active.answers[active.answers.length - 1]?.answer_text ||
                  ""
                }
                disabled={!!isFinished}
                busy={voiceMutation.isPending}
                onSubmit={(payload) => voiceMutation.mutate(payload)}
              />
            ) : (
              <>
                <textarea
                  className="field min-h-[220px] resize-y"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={isFinished}
                  placeholder="Write your answer here. Use specifics, tradeoffs, and outcomes."
                />
                {!isFinished && (
                  <div className="flex flex-wrap gap-3">
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={!draft.trim() || saveMutation.isPending}
                      onClick={() => saveMutation.mutate()}
                    >
                      {saveMutation.isPending
                        ? "Saving…"
                        : activeIndex < questions.length - 1
                          ? "Save & next"
                          : "Save answer"}
                    </button>
                    {activeIndex > 0 && (
                      <button
                        type="button"
                        className="btn-ghost"
                        onClick={() => setActiveIndex((i) => Math.max(0, i - 1))}
                      >
                        Previous
                      </button>
                    )}
                  </div>
                )}
              </>
            )}
            {isVoice && !isFinished && activeIndex > 0 && (
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setActiveIndex((i) => Math.max(0, i - 1))}
              >
                Previous
              </button>
            )}
            {isVoice && active.answers[0]?.has_audio && (
              <p className="text-sm text-ink-muted">Audio recording saved with this answer.</p>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

function ScoreTile({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
      <div className="text-xs uppercase tracking-wider text-ink-muted">{label}</div>
      <div className="mt-1 font-display text-2xl text-ink">{scoreLabel(value)}</div>
    </div>
  );
}
