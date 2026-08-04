export interface PlanInfo {
  code: string;
  name: string;
  price_monthly_usd: number;
  blurb: string;
  features: string[];
  interviews_per_month?: number | null;
  voice_interviews: boolean;
  coach: boolean;
  reports: boolean;
  company_roadmaps: boolean;
  priority_support: boolean;
}

export interface Entitlements {
  plan: string;
  interviews_per_month?: number | null;
  interviews_used_this_month: number;
  voice_interviews: boolean;
  coach: boolean;
  reports: boolean;
  company_roadmaps: boolean;
  priority_support: boolean;
  can_start_interview: boolean;
  can_use_voice: boolean;
  can_use_coach: boolean;
}

export interface SubscriptionInfo {
  id?: string | null;
  plan: string;
  status: string;
  cancel_at_period_end: boolean;
  current_period_end?: string | null;
  stripe_customer_id?: string | null;
  billing_mode: "local" | "stripe" | string;
  entitlements: Entitlements;
}

export interface CheckoutResult {
  mode: string;
  plan: string;
  checkout_url?: string | null;
  message: string;
  subscription?: SubscriptionInfo | null;
}
