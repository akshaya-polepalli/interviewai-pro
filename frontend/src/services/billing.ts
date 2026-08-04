import { apiClient } from "@/services/api";
import type { CheckoutResult, PlanInfo, SubscriptionInfo } from "@/types/billing";

export async function listPlans(): Promise<PlanInfo[]> {
  const { data } = await apiClient.get<PlanInfo[]>("/billing/plans");
  return data;
}

export async function getMySubscription(): Promise<SubscriptionInfo> {
  const { data } = await apiClient.get<SubscriptionInfo>("/billing/me");
  return data;
}

export async function checkout(plan: string): Promise<CheckoutResult> {
  const { data } = await apiClient.post<CheckoutResult>("/billing/checkout", { plan });
  return data;
}

export async function activatePlan(plan: string): Promise<SubscriptionInfo> {
  const { data } = await apiClient.post<SubscriptionInfo>("/billing/activate", { plan });
  return data;
}

export async function cancelPlan(atPeriodEnd = true): Promise<SubscriptionInfo> {
  const { data } = await apiClient.post<SubscriptionInfo>("/billing/cancel", {
    at_period_end: atPeriodEnd,
  });
  return data;
}
