export type StudyPlanStatus = "active" | "completed" | "archived";

export interface StudyPlanTask {
  id: string;
  sequence: number;
  day_offset: number;
  title: string;
  description?: string | null;
  category: string;
  estimated_minutes: number;
  resource_path?: string | null;
  is_done: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudyPlan {
  id: string;
  title: string;
  summary?: string | null;
  status: StudyPlanStatus | string;
  weeks: number;
  focus_areas?: string[] | null;
  model_provider?: string | null;
  created_at: string;
  updated_at: string;
  task_count: number;
  done_count: number;
}

export interface StudyPlanDetail extends StudyPlan {
  tasks: StudyPlanTask[];
}

export interface CoachMessage {
  id: string;
  role: "user" | "assistant" | string;
  content: string;
  extra?: Record<string, unknown> | null;
  created_at: string;
}

export interface CoachAskResult {
  reply: CoachMessage;
  history: CoachMessage[];
}

export interface CoachInsight {
  headline: string;
  tips: string[];
  weak_topics: string[];
  focus_areas: string[];
  suggested_weeks: number;
}
