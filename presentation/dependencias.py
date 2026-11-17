"""Dependencias HTTP: sesión, control de roles y protección CSRF."""
import secrets

from fastapi import Request

from application.excepciones import NoAutenticado, NoAutorizado


# ---------------------------------------------------------------------- CSRF
def csrf_token(request: Request) -> str:
    """Token CSRF de la sesión; se crea en la primera petición."""
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(32)
    return request.session["csrf"]


async def leer_formulario(request: Request) -> dict:
    """Lee el formulario POST, valida el token CSRF y recorta espacios.

    La clave '_multi' conserva el formulario original para campos repetidos.
    """
    form = await request.form()
    enviado = form.get("csrf_token", "")
    esperado = request.session.get("csrf", "")
    if not esperado or not secrets.compare_digest(str(enviado), esperado):
        raise NoAutorizado("Token CSRF inválido. Recargue la página e intente de nuevo.")
    datos = {k: (v.strip() if isinstance(v, str) else v) for k, v in form.multi_items()}
    return datos | {"_multi": form}


# ----------------------------------------------------------- sesión y roles
def usuario_actual(request: Request) -> dict:
    usuario = request.session.get("usuario")
    if not usuario:
        raise NoAutenticado()
    return usuario


def requiere_roles(*roles: str):
    """Dependencia FastAPI: exige sesión y al menos uno de los roles.

    Sin roles solo exige sesión iniciada.
    """

    def dependencia(request: Request) -> dict:
        usuario = usuario_actual(request)
        if roles and not set(roles) & set(usuario["roles"]):
            raise NoAutorizado("No tiene permisos para acceder a este módulo.")
        return usuario

    return dependencia
