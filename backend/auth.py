"""FlowSense authentication service."""
import base64, hashlib, hmac, os, secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from database import engine
try:
    from authlib.integrations.starlette_client import OAuth
except ImportError:
    OAuth = None

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
AUTH_SECRET = os.getenv("AUTH_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
TOKEN_TTL_HOURS = int(os.getenv("AUTH_TOKEN_TTL_HOURS", "24"))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")

def _require_secret():
    if len(AUTH_SECRET.strip()) < 32:
        raise HTTPException(500, "AUTH_SECRET is not configured. Set a random secret of at least 32 characters.")
    return AUTH_SECRET.strip()

def _b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")

def _unb64(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def _hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210000)
    return "pbkdf2_sha256$210000$" + _b64(salt) + "$" + _b64(digest)

def _verify_password(password, encoded):
    try:
        scheme, rounds, salt_b64, digest_b64 = encoded.split("$")
        if scheme != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _unb64(salt_b64), int(rounds))
        return hmac.compare_digest(actual, _unb64(digest_b64))
    except Exception:
        return False

def _create_token(user_id, email):
    secret = _require_secret()
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    payload = user_id + "|" + email + "|" + str(int(exp.timestamp()))
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    return _b64(payload.encode()) + "." + _b64(signature)

def _read_token(token):
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        payload = _unb64(encoded_payload).decode()
        expected = hmac.new(_require_secret().encode(), payload.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_unb64(encoded_signature), expected): raise ValueError("Invalid signature")
        user_id, email, exp = payload.split("|", 2)
        if int(exp) <= int(datetime.now(timezone.utc).timestamp()): raise ValueError("Expired token")
        return {"user_id": user_id, "email": email}
    except Exception as exc:
        raise HTTPException(401, "Invalid or expired authentication token.") from exc

def _public_user(row):
    return {"user_id": str(row["user_id"]), "full_name": row["full_name"], "email": row["email"], "auth_provider": row["auth_provider"], "profile_image": row["profile_image"], "created_at": row["created_at"].isoformat() if row["created_at"] else None}

def _get_user_by_email(email):
    with engine.connect() as conn:
        return conn.execute(text("""SELECT user_id, full_name, email, password_hash, auth_provider, google_subject_id, profile_image, created_at FROM users WHERE lower(email) = lower(:email)"""), {"email": email}).mappings().first()

def _get_user_by_id(user_id):
    with engine.connect() as conn:
        return conn.execute(text("""SELECT user_id, full_name, email, password_hash, auth_provider, google_subject_id, profile_image, created_at FROM users WHERE user_id = CAST(:user_id AS uuid) AND is_active = TRUE"""), {"user_id": user_id}).mappings().first()

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

@router.post("/register")
def register(payload: RegisterRequest):
    email = str(payload.email).strip().lower()
    if _get_user_by_email(email): raise HTTPException(409, "An account with this email already exists.")
    with engine.begin() as conn:
        row = conn.execute(text("""INSERT INTO users (full_name, email, password_hash, auth_provider) VALUES (:full_name, :email, :password_hash, 'local') RETURNING user_id, full_name, email, auth_provider, profile_image, created_at"""), {"full_name": payload.full_name.strip(), "email": email, "password_hash": _hash_password(payload.password)}).mappings().one()
    return {"access_token": _create_token(str(row["user_id"]), email), "token_type": "bearer", "user": _public_user(row)}

@router.post("/login")
def login(payload: LoginRequest):
    email = str(payload.email).strip().lower()
    row = _get_user_by_email(email)
    if not row or not row["password_hash"] or not _verify_password(payload.password, row["password_hash"]): raise HTTPException(401, "Invalid email or password.")
    return {"access_token": _create_token(str(row["user_id"]), email), "token_type": "bearer", "user": _public_user(row)}

@router.get("/me")
def me(request: Request):
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "): raise HTTPException(401, "Authentication required.")
    token_data = _read_token(header.split(" ", 1)[1].strip())
    row = _get_user_by_id(token_data["user_id"])
    if not row: raise HTTPException(401, "User account is unavailable.")
    return {"user": _public_user(row)}

def _google_oauth():
    if OAuth is None: raise HTTPException(500, "Google authentication dependency is not installed.")
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET: raise HTTPException(503, "Google authentication is not configured yet.")
    oauth = OAuth()
    oauth.register(name="google", client_id=GOOGLE_CLIENT_ID, client_secret=GOOGLE_CLIENT_SECRET, server_metadata_url="https://accounts.google.com/.well-known/openid-configuration", client_kwargs={"scope": "openid email profile"})
    return oauth.google

@router.get("/google")
async def google_login(request: Request):
    return await _google_oauth().authorize_redirect(request, GOOGLE_REDIRECT_URI)

@router.get("/google/callback")
async def google_callback(request: Request):
    try:
        google = _google_oauth()
        token = await google.authorize_access_token(request)
        userinfo = token.get("userinfo") or await google.userinfo(token=token)
        subject = str(userinfo["sub"])
        email = str(userinfo["email"]).strip().lower()
        name = str(userinfo.get("name") or email.split("@", 1)[0]).strip()
        picture = userinfo.get("picture")
        row = _get_user_by_email(email)
        if row:
            if row["google_subject_id"] and row["google_subject_id"] != subject: raise HTTPException(409, "This email is already linked to another Google account.")
            with engine.begin() as conn:
                conn.execute(text("""UPDATE users SET google_subject_id = :subject, auth_provider = 'google', profile_image = COALESCE(:picture, profile_image), updated_at = NOW() WHERE user_id = CAST(:user_id AS uuid)"""), {"subject": subject, "picture": picture, "user_id": str(row["user_id"])})
                user_id = str(row["user_id"])
        else:
            with engine.begin() as conn:
                user_id = str(conn.execute(text("""INSERT INTO users (full_name, email, auth_provider, google_subject_id, profile_image) VALUES (:name, :email, 'google', :subject, :picture) RETURNING user_id"""), {"name": name, "email": email, "subject": subject, "picture": picture}).scalar_one())
        return RedirectResponse(FRONTEND_URL + "/auth/callback?token=" + _create_token(user_id, email), status_code=302)
    except HTTPException:
        raise
    except Exception as exc:
        print("[Auth] Google callback failed:", exc)
        return RedirectResponse(FRONTEND_URL + "/login?error=google_auth_failed", status_code=302)