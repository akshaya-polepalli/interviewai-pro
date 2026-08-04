"""API v1 route aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    analytics,
    auth,
    billing,
    coach,
    coding,
    health,
    interviews,
    notifications,
    reports,
    resumes,
    roadmaps,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)
api_router.include_router(resumes.router)
api_router.include_router(interviews.router)
api_router.include_router(coding.router)
api_router.include_router(analytics.router)
api_router.include_router(reports.router)
api_router.include_router(notifications.router)
api_router.include_router(coach.router)
api_router.include_router(roadmaps.router)
api_router.include_router(billing.router)
