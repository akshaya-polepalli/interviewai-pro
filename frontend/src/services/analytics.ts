import { apiClient } from "@/services/api";
import type { AnalyticsBundle } from "@/types/analytics";

export async function getMyAnalytics(refresh = true): Promise<AnalyticsBundle> {
  const { data } = await apiClient.get<AnalyticsBundle>("/analytics/me", {
    params: { refresh },
  });
  return data;
}
