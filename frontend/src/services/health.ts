import { apiClient } from "@/services/api";
import type { HealthResponse, ReadyResponse } from "@/types/health";

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>("/health");
  return data;
}

export async function fetchReady(): Promise<ReadyResponse> {
  const { data } = await apiClient.get<ReadyResponse>("/ready");
  return data;
}
