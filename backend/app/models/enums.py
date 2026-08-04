"""
Domain enumerations.

Stored as PostgreSQL ENUM (or VARCHAR with check) via SQLAlchemy Enum.
Using `str, enum.Enum` keeps values JSON-serializable and OpenAPI-friendly.
"""

from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class InterviewType(str, Enum):
    TECHNICAL = "technical"
    CODING = "coding"
    BEHAVIORAL = "behavioral"
    HR = "hr"
    MIXED = "mixed"
    VOICE = "voice"


class InterviewStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EVALUATED = "evaluated"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class QuestionCategory(str, Enum):
    ALGORITHMS = "algorithms"
    DATA_STRUCTURES = "data_structures"
    SYSTEM_DESIGN = "system_design"
    DATABASES = "databases"
    NETWORKING = "networking"
    FRONTEND = "frontend"
    BACKEND = "backend"
    ML = "ml"
    BEHAVIORAL = "behavioral"
    HR = "hr"
    RESUME = "resume"
    OTHER = "other"


class TargetRole(str, Enum):
    SOFTWARE_ENGINEER = "software_engineer"
    BACKEND_ENGINEER = "backend_engineer"
    FRONTEND_ENGINEER = "frontend_engineer"
    FULL_STACK_ENGINEER = "full_stack_engineer"
    DATA_ANALYST = "data_analyst"
    DATA_SCIENTIST = "data_scientist"
    ML_ENGINEER = "ml_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    STUDENT = "student"
    OTHER = "other"


class TargetCompany(str, Enum):
    GOOGLE = "google"
    AMAZON = "amazon"
    MICROSOFT = "microsoft"
    META = "meta"
    APPLE = "apple"
    NETFLIX = "netflix"
    STRIPE = "stripe"
    OPENAI = "openai"
    GENERAL = "general"


class SubmissionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    RUNTIME_ERROR = "runtime_error"
    COMPILATION_ERROR = "compilation_error"
    SYSTEM_ERROR = "system_error"


class ProgrammingLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "cpp"


class ResumeStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    ANALYZED = "analyzed"
    FAILED = "failed"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    READ = "read"
    FAILED = "failed"


class ReportType(str, Enum):
    INTERVIEW_SUMMARY = "interview_summary"
    WEEKLY_PROGRESS = "weekly_progress"
    MONTHLY_PROGRESS = "monthly_progress"
    RESUME_ATS = "resume_ats"
    ROADMAP = "roadmap"
    ADMIN_EXPORT = "admin_export"


class ReportStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class StudyPlanStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CoachMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class RoadmapEnrollmentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class PlanCode(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class ActivityAction(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_RESET = "password_reset"
    PROFILE_UPDATE = "profile_update"
    RESUME_UPLOAD = "resume_upload"
    INTERVIEW_START = "interview_start"
    INTERVIEW_COMPLETE = "interview_complete"
    CODE_SUBMIT = "code_submit"
    ADMIN_ACTION = "admin_action"
    OTHER = "other"
