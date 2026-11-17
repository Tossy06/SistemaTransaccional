"""Construcción de la aplicación FastAPI: middlewares, rutas y manejo de errores."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from application.excepciones import NoAutenticado, NoAutorizado
from domain.excepciones import ReglaNegocioError
from infrastructure.config import settings

from .routers import actas, administracion, asambleas, auth, inicio, sala, votacion
from .vistas import flash, redirigir, render

CABECERAS_SEGURIDAD = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
    ),
    "Cache-Control": "no-store",
}


def _registrar_manejadores(app: FastAPI) -> None:
    """Convierte excepciones de las capas internas en respuestas HTTP."""

    @app.exception_handler(NoAutenticado)
    async def _no_autenticado(request: Request, exc: NoAutenticado):
        if request.method == "GET" and request.url.path.startswith("/sala/"):
            request.session["siguiente"] = request.url.path
            flash(request, "Inicie sesión para entrar a la sala de la asamblea.", "error")
        else:
            flash(request, "Inicie sesión para continuar.", "error")
        return redirigir("/login")

    @app.exception_handler(NoAutorizado)
    async def _no_autorizado(request: Request, exc: NoAutorizado):
        respuesta = render(request, "error.html", mensaje=str(exc) or "Acceso no autorizado.")
        respuesta.status_code = 403
        return respuesta

    @app.exception_handler(ReglaNegocioError)
    async def _regla_negocio(request: Request, exc: ReglaNegocioError):
        respuesta = render(request, "error.html", mensaje=str(exc))
        respuesta.status_code = 400
        return respuesta


def crear_app() -> FastAPI:
    app = FastAPI(title="Sistema de Gestión Transaccional de Asambleas",
                  docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def cabeceras_seguridad(request: Request, call_next):
        respuesta = await call_next(request)
        respuesta.headers.update(CABECERAS_SEGURIDAD)
        return respuesta

    # Sesión firmada en cookie (SameSite=strict).
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="asambleas_sesion",
        max_age=settings.session_max_age,
        same_site="strict",
        https_only=settings.session_https_only,
    )
    app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

    for modulo in (inicio, auth, administracion, asambleas, votacion, sala, actas):
        app.include_router(modulo.router)

    _registrar_manejadores(app)
    return app
