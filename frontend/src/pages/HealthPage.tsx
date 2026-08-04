import { useQuery } from "@tanstack/react-query";

import { fetchHealth, fetchReady } from "@/services/health";

export function HealthPage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });

  const readyQuery = useQuery({
    queryKey: ["ready"],
    queryFn: fetchReady,
    retry: 1,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold text-ink">System status</h1>
        <p className="mt-2 text-ink-muted">
          Live probes against the FastAPI liveness and readiness endpoints.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <StatusCard
          title="Liveness (/health)"
          loading={healthQuery.isLoading}
          error={healthQuery.error}
          data={healthQuery.data}
        />
        <StatusCard
          title="Readiness (/ready)"
          loading={readyQuery.isLoading}
          error={readyQuery.error}
          data={readyQuery.data}
        />
      </div>
    </div>
  );
}

function StatusCard({
  title,
  loading,
  error,
  data,
}: {
  title: string;
  loading: boolean;
  error: unknown;
  data: unknown;
}) {
  return (
    <article className="glass-panel p-5">
      <h2 className="font-display text-lg font-semibold text-ink">{title}</h2>
      {loading && <p className="mt-3 text-sm text-ink-muted">Checking…</p>}
      {error != null && (
        <p className="mt-3 text-sm text-danger">
          {error instanceof Error ? error.message : "Request failed"}
        </p>
      )}
      {data != null && (
        <pre className="mt-3 overflow-x-auto rounded-xl bg-black/30 p-3 font-mono text-xs text-ink-muted">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </article>
  );
}
