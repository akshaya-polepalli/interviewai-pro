export type ResumeAnalysis = {
  id: string;
  resume_id: string;
  ats_score: number | string | null;
  keyword_match_score: number | string | null;
  matched_keywords: string[] | null;
  missing_keywords: string[] | null;
  suggestions: string[] | null;
  section_scores: Record<string, number> | null;
  model_provider: string | null;
  model_name: string | null;
  created_at: string;
  updated_at: string;
};

export type ResumeItem = {
  id: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  status: string;
  storage_backend: string;
  created_at: string;
  updated_at: string;
  word_count: number | null;
  has_analysis: boolean;
  analysis: ResumeAnalysis | null;
};

export type ResumeDetail = ResumeItem & {
  raw_text_preview: string | null;
  parsed_json: Record<string, unknown> | null;
};

export type AnalyzeResponse = {
  message: string;
  resume_id: string;
  status: string;
  task_id: string | null;
  analysis: ResumeAnalysis | null;
};
