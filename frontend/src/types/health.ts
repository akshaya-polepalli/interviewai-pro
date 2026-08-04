export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  environment: string;
  timestamp: string;
};

export type DependencyCheck = {
  status: "up" | "down";
  error?: string;
};

export type ReadyResponse = {
  status: "ready" | "degraded";
  checks: {
    database: DependencyCheck;
    redis: DependencyCheck;
  };
  timestamp: string;
};
