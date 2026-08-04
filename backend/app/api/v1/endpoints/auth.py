"""
Authentication HTTP endpoints.

POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
POST /auth/verify-email
POST /auth/forgot-password
POST /auth/reset-password
GET  /auth/oauth/{provider}/authorize
GET  /auth/oauth/{provider}/callback
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.core.exceptions import ValidationAppError
from app.dependencies import AuthServiceDep, CurrentUser, OAuthServiceDep, OptionalUser
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    OAuthAuthorizeResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserPublic,
    VerifyEmailRequest,
)
from app.services.auth_service import user_to_public

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    return user_agent, ip


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new candidate account",
)
def register(payload: RegisterRequest, service: AuthServiceDep) -> MessageResponse:
    _, raw_verify = service.register(
        email=str(payload.email),
        full_name=payload.full_name,
        password=payload.password,
    )
    from app.core.config import get_settings

    settings = get_settings()
    return MessageResponse(
        message="Registration successful. Check your email to verify your account.",
        detail="In development without SMTP, use debug_token or API logs.",
        debug_token=raw_verify if (settings.app_debug and not settings.is_production) else None,
    )


@router.post("/login", response_model=TokenResponse, summary="Login with email and password")
def login(payload: LoginRequest, request: Request, service: AuthServiceDep) -> TokenResponse:
    user_agent, ip = _client_meta(request)
    return service.login(
        email=str(payload.email),
        password=payload.password,
        user_agent=user_agent,
        ip_address=ip,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Rotate refresh token")
def refresh(payload: RefreshRequest, request: Request, service: AuthServiceDep) -> TokenResponse:
    user_agent, ip = _client_meta(request)
    return service.refresh(
        refresh_token=payload.refresh_token,
        user_agent=user_agent,
        ip_address=ip,
    )


@router.post("/logout", response_model=MessageResponse, summary="Revoke refresh token(s)")
def logout(
    payload: LogoutRequest,
    service: AuthServiceDep,
    user: OptionalUser,
) -> MessageResponse:
    if payload.everywhere and user is None:
        raise ValidationAppError("Authentication required for logout everywhere")
    service.logout(
        refresh_token=payload.refresh_token,
        user_id=user.id if user else None,
        everywhere=payload.everywhere,
    )
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserPublic, summary="Current authenticated user")
def me(user: CurrentUser) -> UserPublic:
    return user_to_public(user)


@router.post("/verify-email", response_model=UserPublic, summary="Verify email with token")
def verify_email(payload: VerifyEmailRequest, service: AuthServiceDep) -> UserPublic:
    return service.verify_email(token=payload.token)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset email",
)
def forgot_password(payload: ForgotPasswordRequest, service: AuthServiceDep) -> MessageResponse:
    raw = service.forgot_password(email=str(payload.email))
    from app.core.config import get_settings

    settings = get_settings()
    return MessageResponse(
        message="If that email exists, a reset link has been sent.",
        detail="In development without SMTP, use debug_token or API logs.",
        debug_token=raw if (raw and settings.app_debug and not settings.is_production) else None,
    )


@router.post("/reset-password", response_model=MessageResponse, summary="Reset password with token")
def reset_password(payload: ResetPasswordRequest, service: AuthServiceDep) -> MessageResponse:
    service.reset_password(token=payload.token, new_password=payload.new_password)
    return MessageResponse(message="Password updated. Please log in with your new password.")


@router.get(
    "/oauth/{provider}/authorize",
    response_model=OAuthAuthorizeResponse,
    summary="Start OAuth authorization (Google/GitHub)",
)
def oauth_authorize(
    provider: str,
    request: Request,
    oauth: OAuthServiceDep,
) -> OAuthAuthorizeResponse:
    provider = provider.lower()
    redirect_uri = str(request.url_for("oauth_callback", provider=provider))
    if provider == "google":
        url, state = oauth.google_authorize_url(redirect_uri=redirect_uri)
    elif provider == "github":
        url, state = oauth.github_authorize_url(redirect_uri=redirect_uri)
    else:
        raise ValidationAppError("Unsupported OAuth provider. Use google or github.")
    return OAuthAuthorizeResponse(provider=provider, authorize_url=url, state=state)


@router.get(
    "/oauth/{provider}/callback",
    name="oauth_callback",
    summary="OAuth callback — exchanges code and redirects to the SPA with tokens",
)
def oauth_callback(
    provider: str,
    request: Request,
    oauth: OAuthServiceDep,
    service: AuthServiceDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    from urllib.parse import urlencode

    from fastapi.responses import RedirectResponse

    from app.core.config import get_settings

    settings = get_settings()
    frontend = settings.frontend_url.rstrip("/")
    if error:
        return RedirectResponse(
            url=f"{frontend}/login?oauth_error={error}",
            status_code=302,
        )

    provider = provider.lower()
    redirect_uri = str(request.url_for("oauth_callback", provider=provider))
    user_agent, ip = _client_meta(request)
    try:
        profile = oauth.exchange(
            provider=provider,
            code=code or "",
            state=state,
            redirect_uri=redirect_uri,
        )
        tokens = service.login_oauth(
            provider=profile.provider,
            provider_user_id=profile.provider_user_id,
            email=profile.email,
            full_name=profile.full_name,
            avatar_url=profile.avatar_url,
            email_verified=profile.email_verified,
            user_agent=user_agent,
            ip_address=ip,
        )
    except Exception as exc:
        message = getattr(exc, "message", None) or str(exc)
        return RedirectResponse(
            url=f"{frontend}/login?{urlencode({'oauth_error': message[:200]})}",
            status_code=302,
        )

    # Pass tokens in the URL hash so they are not sent to intermediary servers as referrers.
    params = urlencode(
        {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_in": str(tokens.expires_in),
        }
    )
    return RedirectResponse(url=f"{frontend}/oauth/callback#{params}", status_code=302)
