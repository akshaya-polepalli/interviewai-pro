import type { CoachAskResult, CoachInsight, CoachMessage, StudyPlan, StudyPlanDetail } from "@/types/coach";
import { apiClient } from "@/services/api";

export async function getInsights(): Promise<CoachInsight> {
  const { data } = await apiClient.get<CoachInsight>("/coach/insights");
  return data;
}

export async function listPlans(): Promise<StudyPlan[]> {
  const { data } = await apiClient.get<StudyPlan[]>("/coach/plans");
  return data;
}

export async function getPlan(id: string): Promise<StudyPlanDetail> {
  const { data } = await apiClient.get<StudyPlanDetail>(`/coach/plans/${id}`);
  return data;
}

export async function generatePlan(payload: {
  weeks?: number;
  title?: string;
  focus_areas?: string[];
}): Promise<StudyPlanDetail> {
  const { data } = await apiClient.post<StudyPlanDetail>("/coach/plans", payload);
  return data;
}

export async function updateTask(
  planId: string,
  taskId: string,
  isDone: boolean,
): Promise<StudyPlanDetail> {
  const { data } = await apiClient.patch<StudyPlanDetail>(
    `/coach/plans/${planId}/tasks/${taskId}`,
    { is_done: isDone },
  );
  return data;
}

export async function archivePlan(planId: string): Promise<StudyPlanDetail> {
  const { data } = await apiClient.post<StudyPlanDetail>(`/coach/plans/${planId}/archive`);
  return data;
}

export async function listMessages(): Promise<CoachMessage[]> {
  const { data } = await apiClient.get<CoachMessage[]>("/coach/messages");
  return data;
}

export async function askCoach(message: string): Promise<CoachAskResult> {
  const { data } = await apiClient.post<CoachAskResult>("/coach/ask", { message });
  return data;
}
