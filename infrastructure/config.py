"""Configuración leída de variables de entorno (ver .env.example)."""
import os


def _bool(nombre: str, defecto: bool) -> bool:
    return os.getenv(nombre, str(defecto)).lower() in ("1", "true", "si", "yes")


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/asambleas"
    )
    secret_key: str = os.getenv("SECRET_KEY", "cambie-esta-clave-en-produccion")
    session_https_only: bool = _bool("SESSION_HTTPS_ONLY", False)
    session_max_age: int = int(os.getenv("SESSION_MAX_AGE", "3600"))  # segundos
    max_intentos_login: int = int(os.getenv("MAX_INTENTOS_LOGIN", "5"))
    minutos_bloqueo: int = int(os.getenv("MINUTOS_BLOQUEO", "15"))
    dias_antelacion_ordinaria: int = int(os.getenv("DIAS_ANTELACION_ORDINARIA", "15"))


settings = Settings()
