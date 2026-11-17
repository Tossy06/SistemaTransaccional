"""Las pruebas recrean la base de datos indicada en DATABASE_URL (¡usar una BD de pruebas!)."""
import re
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from infrastructure.config import settings
from application.services.censo_service import limitador_formulario
from infrastructure.seguridad import limitador
from main import app

DB = Path(__file__).resolve().parent.parent / "db"


@pytest.fixture(autouse=True)
def base_limpia():
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.execute((DB / "01_schema.sql").read_text(encoding="utf-8"))
        conn.execute((DB / "02_datos_iniciales.sql").read_text(encoding="utf-8"))
    limitador._fallos.clear()
    limitador_formulario._fallos.clear()
    yield


def _csrf(html: str) -> str:
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


class Cliente:
    def __init__(self):
        self.http = TestClient(app, follow_redirects=False)

    def login(self, email, password="Asamblea2026*"):
        token = _csrf(self.http.get("/login").text)
        return self.http.post("/login", data={"email": email, "password": password, "csrf_token": token})

    def post(self, url, **datos):
        token = _csrf(self.http.get("/").text)
        return self.http.post(url, data={**datos, "csrf_token": token})


@pytest.fixture
def cliente():
    return Cliente
