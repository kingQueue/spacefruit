from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = "spacefruit-local-development-only"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

ROOT_URLCONF = "spacefruit_api.urls"
MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]
INSTALLED_APPS = []
TEMPLATES = []
WSGI_APPLICATION = "spacefruit_api.wsgi.application"
DATABASES = {}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
