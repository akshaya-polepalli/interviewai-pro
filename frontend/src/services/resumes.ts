import { apiClient } from "@/services/api";
import type { AnalyzeResponse, ResumeDetail, ResumeItem } from "@/types/resumes";

export async function listResumes(): Promise<ResumeItem[]> {
  const { data } = await apiClient.get<ResumeItem[]>("/resumes");
  return data;
}

export async function getResume(id: string): Promise<ResumeDetail> {
  const { data } = await apiClient.get<ResumeDetail>(`/resumes/${id}`);
  return data;
}

export async function uploadResume(input: {
  file: File;
  targetRole?: string;
  sync?: boolean;
}): Promise<AnalyzeResponse | ResumeItem> {
  const form = new FormData();
  form.append("file", input.file);
  form.append("analyze", "true");
  form.append("sync", String(input.sync ?? true));
  if (input.targetRole) {
    form.append("target_role", input.targetRole);
  }
  const { data } = await apiClient.post<AnalyzeResponse | ResumeItem>("/resumes", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function analyzeResume(
  id: string,
  payload: { target_role?: string; job_description?: string; sync?: boolean },
): Promise<AnalyzeResponse> {
  const { data } = await apiClient.post<AnalyzeResponse>(`/resumes/${id}/analyze`, {
    sync: true,
    ...payload,
  });
  return data;
}

export async function deleteResume(id: string): Promise<void> {
  await apiClient.delete(`/resumes/${id}`);
}

export function downloadResumeUrl(id: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
  return `${base}/resumes/${id}/download`;
}
