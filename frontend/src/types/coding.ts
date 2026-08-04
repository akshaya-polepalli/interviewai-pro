export interface CodingProblemListItem {
  id: string;
  slug: string;
  title: string;
  difficulty: string;
  tags?: string[] | null;
  company_tags?: string[] | null;
  time_limit_ms: number;
  memory_limit_mb: number;
}

export interface CodingProblemDetail extends CodingProblemListItem {
  statement_md: string;
  starter_code?: Record<string, string> | null;
  public_tests?: Array<{ args: unknown[]; expected: unknown }> | null;
}

export interface ExecutionResultItem {
  id: string;
  test_index: number;
  is_hidden: boolean;
  status: string;
  expected_stdout?: string | null;
  actual_stdout?: string | null;
  stderr?: string | null;
  runtime_ms?: number | null;
}

export interface SubmissionItem {
  id: string;
  problem_id: string;
  language: string;
  status: string;
  verdict?: string | null;
  score?: string | number | null;
  passed_tests?: number | null;
  total_tests?: number | null;
  runtime_ms?: number | null;
  created_at: string;
  source_code?: string | null;
  execution_results: ExecutionResultItem[];
}
