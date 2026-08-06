"""
Bike Theft Tracker — Django Settings
"""
import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# False: already-set env vars (e.g. CI, `DB_PORT=5432 pytest`) win over `.env`.
load_dotenv(override=False)

BASE_DIR = Path(__file__).resolve().parent.parent


def _rasterio_wheel_gdal_geos() -> tuple[str | None, str | None]:
    """Prefer GDAL/GEOS from the rasterio wheel (matches venv Python ABI on Windows)."""
    if os.name != "nt":
        return None, None
    try:
        import rasterio
    except ImportError:
        return None, None
    libs = Path(rasterio.__file__).resolve().parent.parent / "rasterio.libs"
    if not libs.is_dir():
        return None, None
    gdal_dlls = sorted(libs.glob("gdal-*.dll"))
    geos_dlls = sorted(libs.glob("geos_c-*.dll"))
    if not gdal_dlls or not geos_dlls:
        return None, None
    return str(gdal_dlls[0]), str(geos_dlls[0])


def _resolve_gdal_library_path():
    # Prefer pip's rasterio wheel on Windows: a global GDAL_LIBRARY_PATH in the OS
    # environment often points at C:\\Program Files\\GDAL (ABI mismatch → WinError 127).
    gdal_r, _ = _rasterio_wheel_gdal_geos()
    if gdal_r and os.name == "nt":
        return gdal_r

    env_path = os.getenv("GDAL_LIBRARY_PATH")
    if env_path:
        return env_path

    common_candidates = [
        r"C:\Program Files\GDAL\gdal.dll",
        r"C:\OSGeo4W\bin\gdal311.dll",
        r"C:\OSGeo4W\bin\gdal310.dll",
        r"C:\OSGeo4W\bin\gdal309.dll",
        r"C:\Program Files\GDAL\gdal311.dll",
        r"C:\Program Files\GDAL\gdal310.dll",
        r"C:\Program Files\GDAL\gdal309.dll",
    ]
    for candidate in common_candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _resolve_geos_library_path():
    _, geos_r = _rasterio_wheel_gdal_geos()
    if geos_r and os.name == "nt":
        return geos_r

    env_path = os.getenv("GEOS_LIBRARY_PATH")
    if env_path:
        return env_path

    common_candidates = [
        r"C:\Program Files\GDAL\geos_c.dll",
        r"C:\OSGeo4W\bin\geos_c.dll",
        r"C:\OSGeo4W\bin\libgeos_c-1.dll",
    ]
    for candidate in common_candidates:
        if Path(candidate).exists():
            return candidate
    return None

# ─── Core ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "INSECURE-CHANGE-ME")
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
LOCAL_DEV_MODE = os.getenv("LOCAL_DEV_MODE", "False") == "True"
# Set DISABLE_THROTTLE=True in .env to lift all rate limits during local testing.
DISABLE_THROTTLE = os.getenv("DISABLE_THROTTLE", "False") == "True"

# ─── Apps ─────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",              # PostGIS support
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    # Project apps
    "apps.users",
    "apps.bikes",
    "apps.reports",
    "apps.sightings",
    "apps.notifications",
    "apps.ml",
]

# ─── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.users.middleware.AuditLoggingMiddleware",   # custom audit log
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─── Database (PostgreSQL + PostGIS) ─────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.getenv("DB_NAME", "bikethefttracker"),
        "USER": os.getenv("DB_USER", "bttadmin"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

GDAL_LIBRARY_PATH = _resolve_gdal_library_path()
GEOS_LIBRARY_PATH = _resolve_geos_library_path()

if os.name == "nt":
    if GDAL_LIBRARY_PATH and Path(GDAL_LIBRARY_PATH).resolve().parent.name == "rasterio.libs":
        try:
            import rasterio

            pdata = Path(rasterio.__file__).resolve().parent / "proj_data"
            if pdata.is_dir() and not os.getenv("PROJ_LIB"):
                os.environ["PROJ_LIB"] = str(pdata)
        except ImportError:
            pass

    _DLL_DIRECTORY_HANDLES = []
    dll_dirs = set()
    for lib_path in (GDAL_LIBRARY_PATH, GEOS_LIBRARY_PATH):
        if lib_path:
            dll_dirs.add(str(Path(lib_path).parent))
    for dll_dir in dll_dirs:
        if Path(dll_dir).exists():
            if hasattr(os, "add_dll_directory"):
                _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(dll_dir))
            os.environ["PATH"] = f"{dll_dir};{os.environ.get('PATH', '')}"

    gdal_dir = Path(GDAL_LIBRARY_PATH).parent if GDAL_LIBRARY_PATH else None
    if gdal_dir:
        proj_dir = gdal_dir / "projlib"
        if proj_dir.exists() and not os.getenv("PROJ_LIB"):
            os.environ["PROJ_LIB"] = str(proj_dir)

# ─── Auth ─────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── DRF ──────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # When DISABLE_THROTTLE=True (local dev), throttle classes are cleared so
    # no rate limiting applies — lets you hammer endpoints freely during testing.
    "DEFAULT_THROTTLE_CLASSES": (
        []
        if DISABLE_THROTTLE
        else [
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
        ]
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon":               "60/min",
        "user":               "200/min",
        "login":              "5/15min",
        "report_submit":      "10/hour",
        "ml_endpoints":       "30/15min",
        "availability_check": "30/min",
    },
}

# ─── JWT ──────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", 15))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# ─── Email ─────────────────────────────────────────────────────────────────────
# Use SMTP only when real credentials are present; fall back to console so that
# missing/empty EMAIL_HOST_USER / EMAIL_HOST_PASSWORD never causes a connection
# hang or authentication error that bleeds into notification daemon threads.
# For testing/prototype runs, set DISABLE_SMTP=True in your environment to force
# console backend even if SMTP credentials exist.
_disable_smtp_env = os.getenv("DISABLE_SMTP", "False") == "True" or LOCAL_DEV_MODE
_smtp_configured = (
    bool(os.getenv("EMAIL_HOST_USER", "").strip() and os.getenv("EMAIL_HOST_PASSWORD", "").strip())
    and not _disable_smtp_env
)
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if _smtp_configured
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@bikethefttracker.pk")

# ─── Twilio SMS ───────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

# ─── File Uploads ─────────────────────────────────────────────────────────────
MEDIA_URL = "/media/"
MEDIA_ROOT = os.getenv("MEDIA_ROOT", BASE_DIR / "media")
ALLOWED_UPLOAD_EXTENSIONS = os.getenv("ALLOWED_UPLOAD_EXTENSIONS", "jpg,jpeg,png").split(",")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 2))

# ─── Internationalization ─────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_I18N = True
USE_TZ = True

# ─── Static Files ────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Security ─────────────────────────────────────────────────────────────────
# SECURE_BROWSER_XSS_FILTER removed in Django 5.0 (browsers ignore X-XSS-Protection).
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"

# ─── Frontend ─────────────────────────────────────────────────────────────────
# BTT dev runs on 3001/8001 — ports 3000/8000 are taken by MuseAI locally.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3001")

# ─── ML Configuration ─────────────────────────────────────────────────────────
ML_DBSCAN_EPS = 0.009           # ~1km at Pakistan latitude (degrees)
ML_DBSCAN_MIN_SAMPLES = 3
ML_FUZZY_HIGH_THRESHOLD = 85
ML_FUZZY_MEDIUM_THRESHOLD = 70
ML_HOTSPOT_LOOKBACK_DAYS = 180  # 6 months
ML_MIN_RECORDS_FOR_CLUSTERING = 10
ML_MIN_RECORDS_FOR_CORRIDOR   = 3   # corridor/radius runs on fewer points (pairs need both locations)

# Workflow automation thresholds
OWNER_ALERT_THRESHOLD = int(os.getenv("OWNER_ALERT_THRESHOLD", 70))
PHOTO_HIGH_CONFIDENCE_THRESHOLD = int(os.getenv("PHOTO_HIGH_CONFIDENCE_THRESHOLD", 85))
SIGHTING_OWNER_RESPONSE_HOURS = int(os.getenv("SIGHTING_OWNER_RESPONSE_HOURS", 24))
