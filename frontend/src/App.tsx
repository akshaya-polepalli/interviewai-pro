import { Route, Routes } from "react-router-dom";

import { RequireAdmin, RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/layouts/AppShell";
import { AdminPage } from "@/pages/AdminPage";
import {
  ForgotPasswordPage,
  LoginPage,
  OAuthCallbackPage,
  ResetPasswordPage,
  SignupPage,
  VerifyEmailPage,
} from "@/pages/AuthPages";
import { DashboardPage } from "@/pages/DashboardPage";
import { CodingProblemsPage, CodingProblemPage } from "@/pages/CodingPage";
import { HealthPage } from "@/pages/HealthPage";
import { LandingPage } from "@/pages/LandingPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ResumesPage } from "@/pages/ResumesPage";
import { InterviewsPage, InterviewSessionPage } from "@/pages/InterviewsPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { CoachPage } from "@/pages/CoachPage";
import { RoadmapsPage } from "@/pages/RoadmapsPage";
import { BillingPage } from "@/pages/BillingPage";
import { SettingsPage } from "@/pages/SettingsPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<LandingPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="signup" element={<SignupPage />} />
        <Route path="oauth/callback" element={<OAuthCallbackPage />} />
        <Route path="forgot-password" element={<ForgotPasswordPage />} />
        <Route path="reset-password" element={<ResetPasswordPage />} />
        <Route path="verify-email" element={<VerifyEmailPage />} />
        <Route
          path="dashboard"
          element={
            <RequireAuth>
              <DashboardPage />
            </RequireAuth>
          }
        />
        <Route
          path="settings"
          element={
            <RequireAuth>
              <SettingsPage />
            </RequireAuth>
          }
        />
        <Route
          path="resumes"
          element={
            <RequireAuth>
              <ResumesPage />
            </RequireAuth>
          }
        />
        <Route
          path="interviews"
          element={
            <RequireAuth>
              <InterviewsPage />
            </RequireAuth>
          }
        />
        <Route
          path="interviews/:id"
          element={
            <RequireAuth>
              <InterviewSessionPage />
            </RequireAuth>
          }
        />
        <Route
          path="coding"
          element={
            <RequireAuth>
              <CodingProblemsPage />
            </RequireAuth>
          }
        />
        <Route
          path="coding/:id"
          element={
            <RequireAuth>
              <CodingProblemPage />
            </RequireAuth>
          }
        />
        <Route
          path="reports"
          element={
            <RequireAuth>
              <ReportsPage />
            </RequireAuth>
          }
        />
        <Route
          path="coach"
          element={
            <RequireAuth>
              <CoachPage />
            </RequireAuth>
          }
        />
        <Route
          path="roadmaps"
          element={
            <RequireAuth>
              <RoadmapsPage />
            </RequireAuth>
          }
        />
        <Route
          path="billing"
          element={
            <RequireAuth>
              <BillingPage />
            </RequireAuth>
          }
        />
        <Route
          path="admin"
          element={
            <RequireAdmin>
              <AdminPage />
            </RequireAdmin>
          }
        />
        <Route path="system/health" element={<HealthPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
