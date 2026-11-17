"""Render de plantillas, mensajes flash y redirecciones."""
from pathlib import Path

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from .dependencias import csrf_token

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Texto visible para los valores internos de estados y catálogos.
ETIQUETAS = {
    "programada": "Programada", "convocada": "Convocada", "en_curso": "En curso",
    "sin_quorum": "Sin quórum", "finalizada": "Finalizada", "pendiente": "Pendiente",
    "abierto": "En votación", "cerrado": "Cerrado", "simple": "Simple",
    "calificada_70": "Calificada 70 %", "a_favor": "A favor", "en_contra": "En contra",
    "abstencion": "Abstención", "aprobado": "Aprobado", "rechazado": "Rechazado",
    "borrador": "Borrador", "aprobada": "Aprobada", "presencial": "Presencial", "poder": "Por poder", "virtual": "Virtual", "mixta": "Mixta",
    "ordinaria": "Ordinaria", "extraordinaria": "Extraordinaria", "email": "Correo", "fisico": "Físico",
}

ROLES_VISIBLES = {
    "administrador": "Administración", "recepcionista": "Recepción",
    "copropietario": "Copropietario", "apoderado": "Apoderado",
    "presidente": "Presidencia", "secretario": "Secretaría",
}

# Filtros Jinja: {{ valor|etiqueta }} y {{ valor|chip }}
templates.env.filters["etiqueta"] = lambda v: ETIQUETAS.get(v, v)
templates.env.filters["chip"] = lambda v: Markup(
    f'<span class="estado {escape(v)}">{escape(ETIQUETAS.get(v, v))}</span>'
)
# Nombre visible de cada rol para el menú de cuenta.
templates.env.filters["roles_texto"] = lambda roles: ", ".join(
    ROLES_VISIBLES.get(r, r) for r in roles)


def flash(request: Request, mensaje: str, tipo: str = "ok") -> None:
    """Guarda un mensaje en sesión para mostrarlo en la siguiente página."""
    # Se reasigna la lista: mutarla en su lugar no marca la sesión como modificada.
    request.session["flash"] = [*request.session.get("flash", []), {"tipo": tipo, "mensaje": mensaje}]


def render(request: Request, plantilla: str, **contexto):
    """Renderiza la plantilla con usuario, mensajes pendientes y campo CSRF."""
    campo_csrf = Markup(
        f'<input type="hidden" name="csrf_token" value="{escape(csrf_token(request))}">'
    )
    return templates.TemplateResponse(
        request, plantilla,
        {"usuario": request.session.get("usuario"),
         "mensajes": request.session.pop("flash", []),
         "csrf_field": campo_csrf,
         **contexto},
    )


def redirigir(url: str) -> RedirectResponse:
    """Redirección 303 (patrón POST-Redirect-GET)."""
    return RedirectResponse(url, status_code=303)
