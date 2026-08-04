export interface SkillRadar {
  technical: number;
  behavioral: number;
  communication: number;
  coding: number;
  resume: number;
}

export interface RoadmapItem {
  id: string;
  title: string;
  done: boolean;
  hint?: string | null;
}

export interface SeriesPoint {
  label: string;
  interviews: number;
  coding: number;
  resumes: number;
}

export interface AnalyticsData {
  user_id: string;
  total_interviews: number;
  completed_interviews: number;
  average_score?: string | number | null;
  coding_submissions: number;
  coding_accepted: number;
  current_streak_days: number;
  longest_streak_days: number;
  strong_topics?: string[] | null;
  weak_topics?: string[] | null;
  skill_radar?: SkillRadar | null;
  weekly_series?: SeriesPoint[] | null;
  roadmap?: RoadmapItem[] | null;
  latest_ats_score?: string | number | null;
  updated_at?: string | null;
}

export interface AchievementItem {
  code: string;
  title: string;
  description: string;
  points: number;
  unlocked: boolean;
  unlocked_at?: string | null;
}

export interface AnalyticsBundle {
  analytics: AnalyticsData;
  achievements: AchievementItem[];
  recently_unlocked: string[];
}
