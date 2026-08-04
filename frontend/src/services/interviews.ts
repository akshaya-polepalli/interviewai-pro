import { apiClient } from "@/services/api";
import type {
  CreateInterviewPayload,
  EvaluateResponse,
  InterviewDetail,
  InterviewItem,
} from "@/types/interviews";

export async function listInterviews(): Promise<InterviewItem[]> {
  const { data } = await apiClient.get<InterviewItem[]>("/interviews");
  return data;
}

export async function getInterview(id: string): Promise<InterviewDetail> {
  const { data } = await apiClient.get<InterviewDetail>(`/interviews/${id}`);
  return data;
}

export async function createInterview(payload: CreateInterviewPayload): Promise<InterviewDetail> {
  const { data } = await apiClient.post<InterviewDetail>("/interviews", payload);
  return data;
}

export async function startInterview(id: string): Promise<InterviewDetail> {
  const { data } = await apiClient.post<InterviewDetail>(`/interviews/${id}/start`);
  return data;
}

export async function submitAnswer(
  id: string,
  payload: {
    question_id: string;
    answer_text: string;
    time_spent_seconds?: number;
    code_snippet?: string;
    language?: string;
  },
): Promise<InterviewDetail> {
  const { data } = await apiClient.post<InterviewDetail>(`/interviews/${id}/answers`, payload);
  return data;
}

export async function submitVoiceAnswer(
  id: string,
  payload: {
    question_id: string;
    transcript?: string;
    time_spent_seconds?: number;
    audio?: Blob | null;
    filename?: string;
  },
): Promise<InterviewDetail> {
  const form = new FormData();
  form.append("question_id", payload.question_id);
  if (payload.transcript?.trim()) {
    form.append("transcript", payload.transcript.trim());
  }
  if (payload.time_spent_seconds != null) {
    form.append("time_spent_seconds", String(payload.time_spent_seconds));
  }
  if (payload.audio && payload.audio.size > 0) {
    form.append("audio", payload.audio, payload.filename || "answer.webm");
  }
  const { data } = await apiClient.post<InterviewDetail>(`/interviews/${id}/answers/voice`, form);
  return data;
}

export function answerAudioUrl(interviewId: string, answerId: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
  return `${base}/interviews/${interviewId}/answers/${answerId}/audio`;
}

export async function completeInterview(
  id: string,
  opts?: { evaluate?: boolean; sync?: boolean },
): Promise<EvaluateResponse | InterviewDetail> {
  const params = new URLSearchParams({
    evaluate: String(opts?.evaluate ?? true),
    sync: String(opts?.sync ?? true),
  });
  const { data } = await apiClient.post<EvaluateResponse | InterviewDetail>(
    `/interviews/${id}/complete?${params.toString()}`,
  );
  return data;
}

export async function deleteInterview(id: string): Promise<void> {
  await apiClient.delete(`/interviews/${id}`);
}
