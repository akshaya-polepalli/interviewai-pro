export interface Milestone {
  id: string;
  title: string;
  description: string;
  week: number;
  category: string;
  resource_path?: string | null;
  auto_rule?: string | null;
  done: boolean;
  done_via?: string | null;
}

export interface CompanyTrackSummary {
  company: string;
  name: string;
  tagline: string;
  weeks: number;
  focus: string[];
  milestone_count: number;
  enrolled: boolean;
  progress_pct: number;
  status?: string | null;
}

export interface CompanyTrackDetail {
  company: string;
  name: string;
  tagline: string;
  weeks: number;
  focus: string[];
  interview_loop: string[];
  principles: string[];
  milestones: Milestone[];
  enrolled: boolean;
  enrollment_id?: string | null;
  status?: string | null;
  notes?: string | null;
  done_count: number;
  milestone_count: number;
  progress_pct: number;
  created_at?: string | null;
  updated_at?: string | null;
}
