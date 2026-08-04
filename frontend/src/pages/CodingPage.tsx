import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { ArrowLeft, Code2, Play } from "lucide-react";

import * as codingApi from "@/services/coding";
import type { ApiErrorBody } from "@/types/auth";
import type { SubmissionItem } from "@/types/coding";

function extractError(err: unknown): string {
  if (err instanceof AxiosError) {
    const body = err.response?.data as ApiErrorBody | undefined;
    return body?.message || body?.detail || err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

function difficultyClass(d: string): string {
  if (d === "easy") return "text-emerald-300";
  if (d === "hard" || d === "expert") return "text-rose-300";
  return "text-amber-300";
}

function verdictTone(status: string): string {
  if (status === "accepted") return "text-emerald-300";
  if (status === "wrong_answer") return "text-amber-300";
  if (status === "queued" || status === "running") return "text-ink-muted";
  return "text-rose-300";
}

export function CodingProblemsPage() {
  const listQuery = useQuery({
    queryKey: ["coding-problems"],
    queryFn: codingApi.listProblems,
  });

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-[0.2em] text-ink-muted">Practice</p>
        <h1 className="font-display text-3xl text-ink sm:text-4xl">Coding problems</h1>
        <p className="max-w-2xl text-ink-muted">
          Solve interview-style Python and JavaScript problems. Public tests show details; hidden
          tests only report pass/fail. Java/C++ are not enabled (need a compiler sandbox).
        </p>
      </div>

      {listQuery.isLoading && <p className="text-ink-muted">Loading problems…</p>}
      {listQuery.isError && <p className="text-rose-300">Failed to load problems.</p>}

      <ul className="divide-y divide-white/10 border-t border-white/10">
        {(listQuery.data ?? []).map((p) => (
          <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 py-4">
            <div>
              <Link to={`/coding/${p.id}`} className="font-medium text-ink hover:text-accent">
                {p.title}
              </Link>
              <p className="mt-1 text-sm text-ink-muted">
                <span className={difficultyClass(p.difficulty)}>{p.difficulty}</span>
                {p.tags?.length ? ` · ${p.tags.join(", ")}` : ""}
              </p>
            </div>
            <Link to={`/coding/${p.id}`} className="btn-ghost text-sm">
              Solve
            </Link>
          </li>
        ))}
      </ul>
      {!listQuery.isLoading && (listQuery.data?.length ?? 0) === 0 && (
        <p className="text-ink-muted">No problems yet — run the DB seed to load the catalog.</p>
      )}
    </div>
  );
}

export function CodingProblemPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [language, setLanguage] = useState<"python" | "javascript">("python");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<SubmissionItem | null>(null);

  const problemQuery = useQuery({
    queryKey: ["coding-problem", id],
    queryFn: () => codingApi.getProblem(id!),
    enabled: !!id,
  });

  const submissionsQuery = useQuery({
    queryKey: ["coding-submissions", id],
    queryFn: () => codingApi.listSubmissions(id),
    enabled: !!id,
  });

  useEffect(() => {
    const starter = problemQuery.data?.starter_code?.[language];
    if (starter != null) setCode(starter);
  }, [problemQuery.data?.id, language]);

  const submitMutation = useMutation({
    mutationFn: () =>
      codingApi.submitSolution(id!, { source_code: code, language, sync: true }),
    onSuccess: async (result) => {
      setLastResult(result);
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["coding-submissions", id] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const publicCases = useMemo(
    () => problemQuery.data?.public_tests ?? [],
    [problemQuery.data?.public_tests],
  );

  if (problemQuery.isLoading) {
    return <p className="text-ink-muted">Loading problem…</p>;
  }
  const problem = problemQuery.data;
  if (!problem) {
    return (
      <div className="space-y-4">
        <p className="text-rose-300">Problem not found.</p>
        <Link to="/coding" className="btn-ghost">
          Back
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <button
          type="button"
          className="inline-flex items-center gap-2 text-sm text-ink-muted hover:text-ink"
          onClick={() => navigate("/coding")}
        >
          <ArrowLeft className="h-4 w-4" /> All problems
        </button>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-display text-3xl text-ink">{problem.title}</h1>
            <p className="mt-1 text-sm text-ink-muted">
              <span className={difficultyClass(problem.difficulty)}>{problem.difficulty}</span>
              {" · "}
              {problem.time_limit_ms}ms limit
              {problem.tags?.length ? ` · ${problem.tags.join(", ")}` : ""}
            </p>
          </div>
          <button
            type="button"
            className="btn-primary"
            disabled={submitMutation.isPending || !code.trim()}
            onClick={() => submitMutation.mutate()}
          >
            <Play className="h-4 w-4" />
            {submitMutation.isPending ? "Running…" : "Run tests"}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-rose-300">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <section className="space-y-4">
          <article className="prose-invert whitespace-pre-wrap rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-sm leading-relaxed text-ink-muted">
            {problem.statement_md}
          </article>
          <div>
            <h2 className="mb-2 font-display text-lg text-ink">Public examples</h2>
            <ul className="space-y-2 text-sm text-ink-muted">
              {publicCases.map((c, i) => (
                <li key={i} className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 font-mono text-xs">
                  args={JSON.stringify(c.args)} → {JSON.stringify(c.expected)}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-accent">
              <Code2 className="h-4 w-4" />
              <h2 className="font-display text-lg text-ink">Editor</h2>
            </div>
            <label className="flex items-center gap-2 text-sm text-ink-muted">
              Language
              <select
                className="rounded-lg border border-white/10 bg-black/30 px-2 py-1.5 text-ink"
                value={language}
                onChange={(e) => setLanguage(e.target.value as "python" | "javascript")}
              >
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
              </select>
            </label>
          </div>
          <textarea
            className="field min-h-[320px] resize-y font-mono text-sm"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            spellCheck={false}
          />
        </section>
      </div>

      {lastResult && (
        <section className="space-y-3 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <h2 className="font-display text-xl text-ink">Latest result</h2>
          <p className={`text-sm font-medium ${verdictTone(lastResult.status)}`}>
            {lastResult.status.replaceAll("_", " ")}
            {lastResult.passed_tests != null && lastResult.total_tests != null
              ? ` · ${lastResult.passed_tests}/${lastResult.total_tests} passed`
              : ""}
            {lastResult.score != null ? ` · score ${Number(lastResult.score).toFixed(0)}` : ""}
          </p>
          <ul className="space-y-2">
            {lastResult.execution_results.map((r) => (
              <li
                key={r.id}
                className="rounded-xl border border-white/10 px-3 py-2 text-sm text-ink-muted"
              >
                <span className={verdictTone(r.status)}>
                  Case {r.test_index + 1}
                  {r.is_hidden ? " (hidden)" : ""}: {r.status.replaceAll("_", " ")}
                </span>
                {!r.is_hidden && r.expected_stdout != null && (
                  <div className="mt-1 font-mono text-xs">
                    expected {r.expected_stdout}
                    {r.actual_stdout != null ? ` · got ${r.actual_stdout}` : ""}
                    {r.stderr ? ` · ${r.stderr}` : ""}
                  </div>
                )}
                {r.is_hidden && r.status !== "accepted" && (
                  <div className="mt-1 text-xs">Hidden case failed</div>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-3 border-t border-white/10 pt-6">
        <h2 className="font-display text-xl text-ink">Your submissions</h2>
        {(submissionsQuery.data ?? []).length === 0 && (
          <p className="text-sm text-ink-muted">No submissions yet.</p>
        )}
        <ul className="divide-y divide-white/10">
          {(submissionsQuery.data ?? []).map((s) => (
            <li key={s.id} className="flex flex-wrap justify-between gap-2 py-3 text-sm">
              <span className={verdictTone(s.status)}>{s.status.replaceAll("_", " ")}</span>
              <span className="text-ink-muted">
                {s.passed_tests ?? 0}/{s.total_tests ?? 0} ·{" "}
                {new Date(s.created_at).toLocaleString()}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
