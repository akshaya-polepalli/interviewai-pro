export type ReportType =
  | "interview_summary"
  | "weekly_progress"
  | "monthly_progress"
  | "resume_ats"
  | "roadmap"
  | "admin_export";

export interface ReportItem {
  id: string;
  report_type: string;
  status: string;
  title: string;
  content_type?: string | null;
  ready_at?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  has_file: boolean;
}

export interface ReportDetail extends ReportItem {
  payload?: Record<string, unknown> | null;
}

export interface NotificationItem {
  id: string;
  title: string;
  body: string;
  channel: string;
  status: string;
  payload?: Record<string, unknown> | null;
  read_at?: string | null;
  sent_at?: string | null;
  created_at: string;
}
