"""
ORM model package.

Importing this package registers every model on `Base.metadata`
so Alembic autogenerate sees the full schema.
"""

from app.models.achievement import Achievement, UserAchievement
from app.models.activity_log import ActivityLog
from app.models.analytics import Analytics
from app.models.auth_token import EmailVerificationToken, PasswordResetToken
from app.models.coding_problem import CodingProblem
from app.models.enums import (
    ActivityAction,
    CoachMessageRole,
    DifficultyLevel,
    InterviewStatus,
    InterviewType,
    NotificationChannel,
    NotificationStatus,
    PlanCode,
    ProgrammingLanguage,
    QuestionCategory,
    ReportStatus,
    ReportType,
    ResumeStatus,
    RoadmapEnrollmentStatus,
    StudyPlanStatus,
    SubmissionStatus,
    SubscriptionStatus,
    TargetCompany,
    TargetRole,
    UserStatus,
)
from app.models.billing import UserSubscription
from app.models.coach import CoachMessage, StudyPlan, StudyPlanTask
from app.models.interview import Answer, Feedback, Interview, Question
from app.models.roadmap import UserCompanyRoadmap
from app.models.notification import Notification
from app.models.rbac import Permission, Role, role_permissions, user_roles
from app.models.refresh_token import RefreshToken
from app.models.report import Report
from app.models.resume import Resume, ResumeAnalysis
from app.models.session import UserSession
from app.models.submission import ExecutionResult, Submission
from app.models.user import User

__all__ = [
    "Achievement",
    "ActivityAction",
    "ActivityLog",
    "Analytics",
    "Answer",
    "CoachMessage",
    "CoachMessageRole",
    "CodingProblem",
    "DifficultyLevel",
    "EmailVerificationToken",
    "ExecutionResult",
    "Feedback",
    "Interview",
    "InterviewStatus",
    "InterviewType",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "PasswordResetToken",
    "Permission",
    "PlanCode",
    "ProgrammingLanguage",
    "Question",
    "QuestionCategory",
    "RefreshToken",
    "Report",
    "ReportStatus",
    "ReportType",
    "Resume",
    "ResumeAnalysis",
    "ResumeStatus",
    "RoadmapEnrollmentStatus",
    "Role",
    "StudyPlan",
    "StudyPlanStatus",
    "StudyPlanTask",
    "Submission",
    "SubmissionStatus",
    "SubscriptionStatus",
    "TargetCompany",
    "TargetRole",
    "User",
    "UserAchievement",
    "UserCompanyRoadmap",
    "UserSession",
    "UserSubscription",
    "UserStatus",
    "role_permissions",
    "user_roles",
]
