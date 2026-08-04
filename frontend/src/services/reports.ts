import { apiClient } from "@/services/api";
import type { NotificationItem, ReportDetail, ReportItem, ReportType } from "@/types/reports";

export async function listReports(): Promise<ReportItem[]> {
  const { data } = await apiClient.get<ReportItem[]>("/reports");
  return data;
}

export async function createReport(payload: {
  report_type: ReportType;
  format?: "pdf" | "json" | "markdown";
  sync?: boolean;
}): Promise<ReportDetail> {
  const { data } = await apiClient.post<ReportDetail>("/reports", {
    sync: true,
    format: "pdf",
    ...payload,
  });
  return data;
}

export async function deleteReport(id: string): Promise<void> {
  await apiClient.delete(`/reports/${id}`);
}

export function downloadReportUrl(id: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
  return `${base}/reports/${id}/download`;
}

export async function listNotifications(): Promise<NotificationItem[]> {
  const { data } = await apiClient.get<NotificationItem[]>("/notifications");
  return data;
}

export async function markNotificationRead(id: string): Promise<void> {
  await apiClient.post(`/notifications/${id}/read`);
}
