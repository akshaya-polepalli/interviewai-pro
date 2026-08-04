export type InterviewType = "technical" | "coding" | "behavioral" | "hr" | "mixed" | "voice";
export type InterviewStatus =
  | "draft"
  | "scheduled"
  | "in_progress"
  | "completed"
  | "abandoned"
  | "evaluated";

export interface AnswerItem {
  id: string;
  question_id: string;
  answer_text: string | null;
  transcript?: string | null;
  has_audio?: boolean;
  code_snippet?: string | null;
  language?: string | null;
  time_spent_seconds?: number | null;
  score?: string | number | null;
  evaluation?: Record<string, unknown> | null;
  created_at: string;
}

export interface QuestionItem {
  id: string;
  sequence: number;
  category: string;
  difficulty?: string | null;
  prompt: string;
  expected_points?: string[] | null;
  is_follow_up: boolean;
  answers: AnswerItem[];
}

export interface FeedbackItem {
  id: string;
  overall_score?: string | number | null;
  technical_score?: string | number | null;
  communication_score?: string | number | null;
  confidence_score?: string | number | null;
  star_method_score?: string | number | null;
  strengths?: string[] | null;
  improvements?: string[] | null;
  detailed_feedback?: string | null;
  model_provider?: string | null;
  model_name?: string | null;
}

export interface InterviewItem {
  id: string;
  title: string;
  interview_type: string;
  status: string;
  difficulty: string;
  target_role?: string | null;
  target_company?: string | null;
  overall_score?: string | number | null;
  summary?: string | null;
  question_count: number;
  answered_count: number;
  started_at?: string | null;
  completed_at?: string | null;
  duration_seconds?: number | null;
  created_at: string;
  updated_at: string;
}

export interface InterviewDetail extends InterviewItem {
  questions: QuestionItem[];
  feedback?: FeedbackItem | null;
  config?: Record<string, unknown> | null;
}

export interface CreateInterviewPayload {
  title?: string;
  interview_type: InterviewType;
  difficulty?: string;
  target_role?: string;
  target_company?: string;
  question_count?: number;
}

export interface EvaluateResponse {
  interview_id: string;
  status: string;
  message: string;
  overall_score?: string | number | null;
}
