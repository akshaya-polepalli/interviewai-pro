import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { FileText, Trash2, Upload } from "lucide-react";

import { SelectField } from "@/components/SelectField";
import { getAccessToken } from "@/services/tokenStorage";
import * as resumesApi from "@/services/resumes";
import type { ApiErrorBody } from "@/types/auth";
import type { ResumeItem } from "@/types/resumes";

const TARGET_ROLE_OPTIONS = [
  "software_engineer",
  "backend_engineer",
  "frontend_engineer",
  "full_stack_engineer",
  "data_analyst",
  "ml_engineer",
  "devops_engineer",
  "student",
  "other",
].map((role) => ({ value: role, label: role.replaceAll("_", " ") }));

export function ResumesPage() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [targetRole, setTargetRole] = useState("software_engineer");
  const [jobDescription, setJobDescription] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ["resumes"],
    queryFn: resumesApi.listResumes,
  });

  const detailQuery = useQuery({
    queryKey: ["resume", selectedId],
    queryFn: () => resumesApi.getResume(selectedId!),
    enabled: !!selectedId,
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose a file first");
      return resumesApi.uploadResume({ file, targetRole, sync: true });
    },
    onSuccess: async (result) => {
      setMessage("Resume uploaded and analyzed");
      setError(null);
      setFile(null);
      await queryClient.invalidateQueries({ queryKey: ["resumes"] });
      const id = "resume_id" in result ? result.resume_id : result.id;
      setSelectedId(id);
    },
    onError: (err) => setError(extractError(err)),
  });

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      if (!selectedId) throw new Error("Select a resume");
      return resumesApi.analyzeResume(selectedId, {
        target_role: targetRole,
        job_description: jobDescription || undefined,
        sync: true,
      });
    },
    onSuccess: async () => {
      setMessage("ATS analysis refreshed");
      await queryClient.invalidateQueries({ queryKey: ["resumes"] });
      await queryClient.invalidateQueries({ queryKey: ["resume", selectedId] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => resumesApi.deleteResume(id),
    onSuccess: async (_, id) => {
      if (selectedId === id) setSelectedId(null);
      await queryClient.invalidateQueries({ queryKey: ["resumes"] });
      setMessage("Resume deleted");
    },
    onError: (err) => setError(extractError(err)),
  });

  const selected: ResumeItem | undefined = useMemo(
    () => listQuery.data?.find((r) => r.id === selectedId),
    [listQuery.data, selectedId],
  );

  const analysis = detailQuery.data?.analysis ?? selected?.analysis ?? null;

  async function onUpload(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    uploadMutation.mutate();
  }

  async function onDownload(id: string, filename: string) {
    const url = resumesApi.downloadResumeUrl(id);
    const token = getAccessToken();
    const res = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      setError("Download failed");
      return;
    }
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(objectUrl);
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold">Resume & ATS</h1>
        <p className="mt-2 text-ink-muted">
          Upload a PDF/DOCX, extract text, and get an ATS score with keyword gaps.
        </p>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}
      {message && <p className="text-sm text-accent">{message}</p>}

      <section className="glass-panel p-6">
        <h2 className="font-display text-xl font-semibold">Upload</h2>
        <form className="mt-4 grid gap-4 md:grid-cols-2" onSubmit={onUpload}>
          <label className="block space-y-1 md:col-span-2">
            <span className="text-sm text-ink-muted">Resume file</span>
            <input
              className="field"
              type="file"
              accept=".pdf,.doc,.docx,.txt,application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </label>
          <SelectField
            label="Target role"
            value={targetRole}
            onChange={setTargetRole}
            options={TARGET_ROLE_OPTIONS}
          />
          <div className="flex items-end">
            <button type="submit" className="btn-primary" disabled={uploadMutation.isPending}>
              <Upload className="h-4 w-4" />
              {uploadMutation.isPending ? "Analyzing…" : "Upload & analyze"}
            </button>
          </div>
        </form>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <section className="glass-panel p-6">
          <h2 className="font-display text-xl font-semibold">Your resumes</h2>
          <div className="mt-4 space-y-3">
            {(listQuery.data ?? []).map((resume) => (
              <button
                key={resume.id}
                type="button"
                onClick={() => setSelectedId(resume.id)}
                className={[
                  "w-full rounded-xl border p-3 text-left transition",
                  selectedId === resume.id
                    ? "border-accent/50 bg-accent/10"
                    : "border-white/10 hover:bg-white/5",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="flex items-center gap-2 text-ink">
                      <FileText className="h-4 w-4 text-accent" />
                      {resume.original_filename}
                    </p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {resume.status} · {(resume.file_size_bytes / 1024).toFixed(1)} KB
                      {resume.analysis?.ats_score != null
                        ? ` · ATS ${resume.analysis.ats_score}`
                        : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="text-danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm("Delete this resume?")) {
                        deleteMutation.mutate(resume.id);
                      }
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </button>
            ))}
            {!listQuery.data?.length && (
              <p className="text-sm text-ink-muted">No resumes yet — upload one to begin.</p>
            )}
          </div>
        </section>

        <section className="glass-panel p-6">
          <h2 className="font-display text-xl font-semibold">ATS report</h2>
          {!selectedId && (
            <p className="mt-3 text-sm text-ink-muted">Select a resume to view analysis.</p>
          )}
          {selectedId && (
            <div className="mt-4 space-y-4">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-ghost text-sm"
                  onClick={() =>
                    selected && void onDownload(selected.id, selected.original_filename)
                  }
                >
                  Download
                </button>
                <button
                  type="button"
                  className="btn-primary text-sm"
                  disabled={analyzeMutation.isPending}
                  onClick={() => analyzeMutation.mutate()}
                >
                  {analyzeMutation.isPending ? "Running…" : "Re-analyze"}
                </button>
              </div>

              <label className="block space-y-1">
                <span className="text-sm text-ink-muted">Optional job description</span>
                <textarea
                  className="field min-h-24"
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste a JD to bias keyword matching…"
                />
              </label>

              {analysis ? (
                <>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <ScoreCard label="ATS score" value={analysis.ats_score} />
                    <ScoreCard label="Keyword match" value={analysis.keyword_match_score} />
                  </div>

                  {analysis.section_scores && (
                    <div>
                      <h3 className="text-sm font-medium text-ink">Section scores</h3>
                      <div className="mt-2 grid gap-2 sm:grid-cols-2">
                        {Object.entries(analysis.section_scores).map(([key, value]) => (
                          <div
                            key={key}
                            className="rounded-xl border border-white/10 px-3 py-2 text-sm text-ink-muted"
                          >
                            {key}: <span className="text-ink">{value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <TagBlock title="Matched keywords" items={analysis.matched_keywords ?? []} tone="good" />
                  <TagBlock title="Missing keywords" items={analysis.missing_keywords ?? []} tone="warn" />

                  <div>
                    <h3 className="text-sm font-medium text-ink">Suggestions</h3>
                    <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-ink-muted">
                      {(analysis.suggestions ?? []).map((tip) => (
                        <li key={tip}>{tip}</li>
                      ))}
                    </ul>
                  </div>

                  <p className="text-xs text-ink-subtle">
                    Engine: {analysis.model_provider}/{analysis.model_name}
                  </p>
                </>
              ) : (
                <p className="text-sm text-ink-muted">No analysis yet for this resume.</p>
              )}

              {detailQuery.data?.raw_text_preview && (
                <div>
                  <h3 className="text-sm font-medium text-ink">Extracted text preview</h3>
                  <pre className="mt-2 max-h-56 overflow-auto rounded-xl bg-black/30 p-3 font-mono text-xs text-ink-muted whitespace-pre-wrap">
                    {detailQuery.data.raw_text_preview}
                  </pre>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function ScoreCard({ label, value }: { label: string; value: number | string | null }) {
  return (
    <article className="rounded-xl border border-white/10 bg-black/20 p-4">
      <p className="text-xs uppercase tracking-wide text-ink-muted">{label}</p>
      <p className="mt-2 font-display text-3xl font-semibold text-accent">{value ?? "—"}</p>
    </article>
  );
}

function TagBlock({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "good" | "warn";
}) {
  return (
    <div>
      <h3 className="text-sm font-medium text-ink">{title}</h3>
      <div className="mt-2 flex flex-wrap gap-2">
        {items.slice(0, 18).map((item) => (
          <span
            key={item}
            className={[
              "rounded-lg border px-2 py-1 text-xs",
              tone === "good"
                ? "border-accent/30 text-accent"
                : "border-warn/40 text-warn",
            ].join(" ")}
          >
            {item}
          </span>
        ))}
        {!items.length && <span className="text-xs text-ink-muted">None</span>}
      </div>
    </div>
  );
}

function extractError(err: unknown): string {
  if (err instanceof AxiosError) {
    const data = err.response?.data as ApiErrorBody | undefined;
    return data?.error?.message ?? err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}
