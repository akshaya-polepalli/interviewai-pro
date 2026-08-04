import { apiClient } from "@/services/api";
import type { CodingProblemDetail, CodingProblemListItem, SubmissionItem } from "@/types/coding";

export async function listProblems(): Promise<CodingProblemListItem[]> {
  const { data } = await apiClient.get<CodingProblemListItem[]>("/coding/problems");
  return data;
}

export async function getProblem(id: string): Promise<CodingProblemDetail> {
  const { data } = await apiClient.get<CodingProblemDetail>(`/coding/problems/${id}`);
  return data;
}

export async function submitSolution(
  problemId: string,
  payload: { source_code: string; language?: string; sync?: boolean },
): Promise<SubmissionItem> {
  const { data } = await apiClient.post<SubmissionItem>(
    `/coding/problems/${problemId}/submissions`,
    {
      language: "python",
      sync: true,
      ...payload,
    },
  );
  return data;
}

export async function listSubmissions(problemId?: string): Promise<SubmissionItem[]> {
  const { data } = await apiClient.get<SubmissionItem[]>("/coding/submissions", {
    params: problemId ? { problem_id: problemId } : undefined,
  });
  return data;
}
