import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { Bell, Download, FileText, Trash2 } from "lucide-react";

import { SelectField } from "@/components/SelectField";
import { getAccessToken } from "@/services/tokenStorage";
import * as reportsApi from "@/services/reports";
import type { ApiErrorBody } from "@/types/auth";
import type { ReportType } from "@/types/reports";

const REPORT_TYPES: { value: ReportType; label: string }[] = [
  { value: "weekly_progress", label: "Weekly progress" },
  { value: "monthly_progress", label: "Monthly progress" },
  { value: "roadmap", label: "Prep roadmap" },
  { value: "resume_ats", label: "Resume ATS" },
];

const FORMAT_OPTIONS = [
  { value: "pdf", label: "PDF (.pdf)" },
  { value: "markdown", label: "Markdown (.md)" },
  { value: "json", label: "JSON (.json)" },
];

function extractError(err: unknown): string {
  if (err instanceof AxiosError) {
    const body = err.response?.data as ApiErrorBody | undefined;
    return body?.message || body?.detail || err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

export function ReportsPage() {
  const queryClient = useQueryClient();
  const [reportType, setReportType] = useState<ReportType>("weekly_progress");
  const [format, setFormat] = useState("pdf");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ["reports"],
    queryFn: reportsApi.listReports,
  });

  const notifQuery = useQuery({
    queryKey: ["notifications"],
    queryFn: reportsApi.listNotifications,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      reportsApi.createReport({
        report_type: reportType,
        format: format as "pdf" | "json" | "markdown",
        sync: true,
      }),
    onSuccess: async () => {
      setMessage("Report generated");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => reportsApi.deleteReport(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
      setMessage("Report deleted");
    },
    onError: (err) => setError(extractError(err)),
  });

  async function onDownload(id: string, title: string, contentType?: string | null) {
    const token = getAccessToken();
    const res = await fetch(reportsApi.downloadReportUrl(id), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      setError("Download failed");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const ext = contentType?.includes("pdf")
      ? "pdf"
      : contentType?.includes("json")
        ? "json"
        : "md";
    a.download = `${title.replaceAll(" ", "_").toLowerCase()}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-[0.2em] text-ink-muted">Exports</p>
        <h1 className="font-display text-3xl text-ink sm:text-4xl">Reports</h1>
        <p className="max-w-2xl text-ink-muted">
          Generate downloadable PDF, Markdown, or JSON summaries of your prep progress. Ready
          reports also create an in-app notification.
        </p>
      </div>

      <section className="grid gap-4 border-t border-white/10 pt-8 sm:grid-cols-3">
        <SelectField
          label="Report type"
          value={reportType}
          onChange={(v) => setReportType(v as ReportType)}
          options={REPORT_TYPES}
        />
        <SelectField
          label="Format"
          value={format}
          onChange={setFormat}
          options={FORMAT_OPTIONS}
        />
        <div className="flex items-end">
          <button
            type="button"
            className="btn-primary"
            disabled={createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            <FileText className="h-4 w-4" />
            {createMutation.isPending ? "Generating…" : "Generate report"}
          </button>
        </div>
      </section>

      {(error || message) && (
        <p className={error ? "text-sm text-rose-300" : "text-sm text-emerald-300"}>
          {error || message}
        </p>
      )}

      <section className="space-y-3">
        <h2 className="font-display text-2xl text-ink">Your reports</h2>
        {listQuery.isLoading && <p className="text-ink-muted">Loading…</p>}
        {(listQuery.data?.length ?? 0) === 0 && (
          <p className="text-ink-muted">No reports yet — generate one above.</p>
        )}
        <ul className="divide-y divide-white/10">
          {(listQuery.data ?? []).map((r) => (
            <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 py-4">
              <div>
                <div className="font-medium text-ink">{r.title}</div>
                <p className="mt-1 text-sm text-ink-muted">
                  {r.report_type.replaceAll("_", " ")} · {r.status}
                  {r.ready_at ? ` · ${new Date(r.ready_at).toLocaleString()}` : ""}
                </p>
                {r.error_message && <p className="text-sm text-rose-300">{r.error_message}</p>}
              </div>
              <div className="flex items-center gap-2">
                {r.status === "ready" && (
                  <button
                    type="button"
                    className="btn-ghost text-sm"
                    onClick={() => void onDownload(r.id, r.title, r.content_type)}
                  >
                    <Download className="h-4 w-4" /> Download
                  </button>
                )}
                <button
                  type="button"
                  className="btn-ghost text-sm text-rose-300"
                  onClick={() => deleteMutation.mutate(r.id)}
                  aria-label="Delete report"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3 border-t border-white/10 pt-8">
        <div className="flex items-center gap-2 text-accent">
          <Bell className="h-4 w-4" />
          <h2 className="font-display text-2xl text-ink">Notifications</h2>
        </div>
        {(notifQuery.data?.length ?? 0) === 0 && (
          <p className="text-sm text-ink-muted">No notifications yet.</p>
        )}
        <ul className="space-y-2">
          {(notifQuery.data ?? []).slice(0, 10).map((n) => (
            <li
              key={n.id}
              className={[
                "rounded-xl border px-4 py-3 text-sm",
                n.status === "read"
                  ? "border-white/10 text-ink-muted"
                  : "border-accent/30 bg-accent/5 text-ink",
              ].join(" ")}
            >
              <div className="font-medium">{n.title}</div>
              <p className="mt-1 text-ink-muted">{n.body}</p>
              {n.status !== "read" && (
                <button
                  type="button"
                  className="mt-2 text-xs text-accent hover:underline"
                  onClick={async () => {
                    await reportsApi.markNotificationRead(n.id);
                    await queryClient.invalidateQueries({ queryKey: ["notifications"] });
                  }}
                >
                  Mark as read
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
