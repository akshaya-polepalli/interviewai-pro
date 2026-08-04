import { apiClient } from "@/services/api";
import type { CompanyTrackDetail, CompanyTrackSummary } from "@/types/roadmaps";

export async function listRoadmaps(): Promise<CompanyTrackSummary[]> {
  const { data } = await apiClient.get<CompanyTrackSummary[]>("/roadmaps");
  return data;
}

export async function getRoadmap(company: string): Promise<CompanyTrackDetail> {
  const { data } = await apiClient.get<CompanyTrackDetail>(`/roadmaps/${company}`);
  return data;
}

export async function enrollRoadmap(company: string, notes?: string): Promise<CompanyTrackDetail> {
  const { data } = await apiClient.post<CompanyTrackDetail>("/roadmaps/enroll", {
    company,
    notes,
  });
  return data;
}

export async function toggleMilestone(
  company: string,
  milestoneId: string,
  isDone: boolean,
): Promise<CompanyTrackDetail> {
  const { data } = await apiClient.post<CompanyTrackDetail>(`/roadmaps/${company}/milestones`, {
    milestone_id: milestoneId,
    is_done: isDone,
  });
  return data;
}

export async function archiveRoadmap(company: string): Promise<CompanyTrackDetail> {
  const { data } = await apiClient.post<CompanyTrackDetail>(`/roadmaps/${company}/archive`);
  return data;
}
