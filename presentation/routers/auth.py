"""RF-01: inicio y cierre de sesión, activación de cuenta y cambio de contraseña."""
from fastapi import APIRouter, Depends, Request

from application.services import AuthService, CensoService
from domain.excepciones import ReglaNegocioError

from ..dependencias import leer_formulario, requiere_roles
from ..vistas import flash, redirigir, render

router = APIRouter()
servicio, censo = AuthService(), CensoService()


@router.get("/login")
def formulario_login(request: Request):
    if request.session.get("usuario"):
        return redirigir("/")
    return render(request, "login.html")


@router.post("/login")
async def login(request: Request):
    form = await leer_formulario(request)
    try:
        usuario = servicio.autenticar(form.get("email", ""), form.get("password", ""))
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        return redirigir("/login")
    siguiente = request.session.get("siguiente", "")
    request.session.clear()  # sesión nueva: evita fijación de sesión
    request.session["usuario"] = usuario
    flash(request, f"Bienvenido(a), {usuario['nombre']}.")
    return redirigir(siguiente if siguiente.startswith("/sala/") else "/")


@router.post("/logout")
async def logout(request: Request):
    await leer_formulario(request)
    request.session.clear()
    return redirigir("/login")


@router.get("/activar")
def formulario_activar(request: Request):
    if request.session.get("usuario"):
        return redirigir("/")
    return render(request, "activar.html", datos={})


@router.post("/activar")
async def activar(request: Request):
    f = await leer_formulario(request)
    try:
        servicio.activar_cuenta(f.get("documento"), f.get("email"), f.get("password", ""),
                                f.get("confirmacion", ""))
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        respuesta = render(request, "activar.html",
                           datos={k: f.get(k, "") for k in ("documento", "email")})
        respuesta.status_code = 400
        return respuesta
    flash(request, "Cuenta activada. Ya puede iniciar sesión con su correo y su contraseña.")
    return redirigir("/login")


@router.get("/registro/{token}")
def formulario_registro(request: Request, token: str, enviado: int = 0):
    try:
        datos = censo.formulario(token)
    except ReglaNegocioError as e:
        respuesta = render(request, "registro_cerrado.html", mensaje=str(e))
        respuesta.status_code = 404
        return respuesta
    return render(request, "registro.html", token=token, enviado=bool(enviado), valores={}, **datos)


@router.post("/registro/{token}")
async def enviar_registro(request: Request, token: str):
    f = await leer_formulario(request)
    origen = request.client.host if request.client else "desconocido"
    try:
        censo.enviar(token, origen, f.get("unidad_id"), f.get("nombre"), f.get("documento"),
                     f.get("email"), f.get("telefono"), f.get("autoriza") == "si")
        return redirigir(f"/registro/{token}?enviado=1")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        valores = {k: f.get(k, "") for k in ("unidad_id", "nombre", "documento", "email", "telefono")}
    try:
        datos = censo.formulario(token)
    except ReglaNegocioError as e:
        return render(request, "registro_cerrado.html", mensaje=str(e))
    respuesta = render(request, "registro.html", token=token, enviado=False, valores=valores, **datos)
    respuesta.status_code = 400
    return respuesta


@router.get("/cuenta")
def cuenta(request: Request, usuario: dict = Depends(requiere_roles())):
    return render(request, "cuenta.html")


@router.post("/cuenta/password")
async def cambiar_password(request: Request, usuario: dict = Depends(requiere_roles())):
    f = await leer_formulario(request)
    try:
        servicio.cambiar_password(usuario["id"], f.get("actual", ""), f.get("nueva", ""),
                                  f.get("confirmacion", ""))
        flash(request, "Contraseña actualizada.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir("/cuenta")
