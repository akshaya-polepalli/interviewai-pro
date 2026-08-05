import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { Check, CreditCard } from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import * as billingApi from "@/services/billing";
import type { ApiErrorBody } from "@/types/auth";
import type { PlanInfo } from "@/types/billing";

function extractError(err: unknown): string {
  if (err instanceof AxiosError) {
    const body = err.response?.data as ApiErrorBody | undefined;
    return body?.error?.message || body?.message || body?.detail || err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong";
}

export function BillingPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const plansQuery = useQuery({
    queryKey: ["billing", "plans"],
    queryFn: billingApi.listPlans,
  });

  const subQuery = useQuery({
    queryKey: ["billing", "me"],
    queryFn: billingApi.getMySubscription,
    enabled: !!user,
  });

  const checkoutMutation = useMutation({
    mutationFn: (plan: string) => billingApi.checkout(plan),
    onSuccess: async (result) => {
      setError(null);
      if (result.mode === "checkout_url" && result.checkout_url) {
        window.location.href = result.checkout_url;
        return;
      }
      setMessage(result.message);
      await queryClient.invalidateQueries({ queryKey: ["billing"] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const cancelMutation = useMutation({
    mutationFn: () => billingApi.cancelPlan(true),
    onSuccess: async () => {
      setMessage("Cancellation scheduled at period end");
      await queryClient.invalidateQueries({ queryKey: ["billing"] });
    },
    onError: (err) => setError(extractError(err)),
  });

  const sub = subQuery.data;
  const plans = plansQuery.data ?? [];

  return (
    <div className="space-y-10">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-[0.2em] text-ink-muted">Plans</p>
        <h1 className="font-display text-3xl text-ink sm:text-4xl">Billing</h1>
        <p className="max-w-2xl text-ink-muted">
          Free for core prep. Pro unlocks voice interviews and the AI coach. Local mode activates
          instantly when Stripe keys are not configured.
        </p>
      </div>

      {error && <p className="text-sm text-rose-300">{error}</p>}
      {message && <p className="text-sm text-emerald-300">{message}</p>}

      {sub && (
        <section className="space-y-3 border-t border-white/10 pt-8">
          <div className="flex items-center gap-2 text-accent">
            <CreditCard className="h-4 w-4" />
            <h2 className="font-display text-xl text-ink">Current plan</h2>
          </div>
          <p className="text-ink">
            <span className="capitalize">{sub.plan}</span> · {sub.status}
            {sub.cancel_at_period_end ? " · cancels at period end" : ""}
          </p>
          <p className="text-sm text-ink-muted">
            Mode: {sub.billing_mode} · Interviews this month:{" "}
            {sub.entitlements.interviews_used_this_month}
            {sub.entitlements.interviews_per_month != null
              ? ` / ${sub.entitlements.interviews_per_month}`
              : " (unlimited)"}
            {" · "}
            Voice {sub.entitlements.can_use_voice ? "on" : "off"} · Coach{" "}
            {sub.entitlements.can_use_coach ? "on" : "off"}
          </p>
          {sub.plan !== "free" && !sub.cancel_at_period_end && (
            <button
              type="button"
              className="btn-ghost"
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
            >
              Cancel at period end
            </button>
          )}
        </section>
      )}

      <section className="grid gap-6 border-t border-white/10 pt-8 md:grid-cols-3">
        {plans.map((plan) => (
          <PlanCard
            key={plan.code}
            plan={plan}
            current={sub?.plan === plan.code}
            busy={checkoutMutation.isPending}
            onSelect={() => {
              if (plan.code === "free") {
                setMessage("You are already on Free, or cancel a paid plan to return.");
                return;
              }
              checkoutMutation.mutate(plan.code);
            }}
          />
        ))}
      </section>
    </div>
  );
}

function PlanCard({
  plan,
  current,
  busy,
  onSelect,
}: {
  plan: PlanInfo;
  current: boolean;
  busy: boolean;
  onSelect: () => void;
}) {
  return (
    <article
      className={[
        "flex flex-col border-t border-white/10 pt-5",
        current ? "opacity-100" : "",
      ].join(" ")}
    >
      <h3 className="font-display text-xl text-ink">{plan.name}</h3>
      <p className="mt-1 font-display text-3xl text-accent">
        ${plan.price_monthly_usd}
        <span className="text-sm font-body text-ink-muted">/mo</span>
      </p>
      <p className="mt-2 text-sm text-ink-muted">{plan.blurb}</p>
      <ul className="mt-4 flex-1 space-y-2 text-sm text-ink-muted">
        {plan.features.map((f) => (
          <li key={f} className="flex gap-2">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
            <span>{f}</span>
          </li>
        ))}
      </ul>
      <button
        type="button"
        className={current ? "btn-ghost mt-6" : "btn-primary mt-6"}
        disabled={busy || current}
        onClick={onSelect}
      >
        {current ? "Current plan" : plan.price_monthly_usd === 0 ? "Included" : "Upgrade"}
      </button>
    </article>
  );
}
