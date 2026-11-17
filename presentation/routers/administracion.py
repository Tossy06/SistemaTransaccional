"""RF-01 usuarios y roles, RF-02 conjuntos y unidades. Solo administrador."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from application.services import CensoService, ConjuntoService, UsuarioService
from domain.excepciones import ReglaNegocioError
from infrastructure.archivos import leer_unidades, plantilla_unidades

from ..dependencias import leer_formulario, requiere_roles
from ..vistas import flash, redirigir, render

router = APIRouter(dependencies=[Depends(requiere_roles("administrador"))])
usuarios, conjuntos, censo = UsuarioService(), ConjuntoService(), CensoService()


def _roles(form) -> list[int]:
    """Ids de los checkbox 'roles' marcados."""
    return [int(r) for r in form["_multi"].getlist("roles")]


@router.get("/usuarios")
def listar_usuarios(request: Request):
    lista, roles = usuarios.listar()
    return render(request, "usuarios.html", usuarios=lista, roles=roles)


@router.post("/usuarios")
async def crear_usuario(request: Request):
    f = await leer_formulario(request)
    try:
        usuarios.crear(f.get("nombre"), f.get("email"), f.get("password"), f.get("documento"),
                       f.get("telefono"), _roles(f))
        flash(request, "Usuario creado.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir("/usuarios")


@router.post("/usuarios/{usuario_id}/roles")
async def roles_usuario(request: Request, usuario_id: int):
    f = await leer_formulario(request)
    try:
        usuarios.actualizar_roles(usuario_id, _roles(f))
        flash(request, "Roles actualizados.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir("/usuarios")


@router.post("/usuarios/{usuario_id}/password")
async def password_usuario(request: Request, usuario_id: int):
    f = await leer_formulario(request)
    try:
        usuarios.restablecer_password(usuario_id, f.get("password", ""))
        flash(request, "Contraseña restablecida. Entréguela al usuario por un medio seguro.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir("/usuarios")


@router.post("/usuarios/{usuario_id}/activo")
async def activo_usuario(request: Request, usuario_id: int):
    f = await leer_formulario(request)
    try:
        usuarios.cambiar_activo(usuario_id, f.get("activo") == "1", request.session["usuario"]["id"])
        flash(request, "Estado del usuario actualizado.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir("/usuarios")


@router.get("/conjuntos")
def listar_conjuntos(request: Request):
    return render(request, "conjuntos.html", conjuntos=conjuntos.listar())


@router.post("/conjuntos")
async def crear_conjunto(request: Request):
    f = await leer_formulario(request)
    try:
        nuevo = conjuntos.crear(f.get("nombre"), f.get("nit"), f.get("direccion"), f.get("ciudad"),
                                f.get("numero_unidades"), f.get("coeficiente_total"))
        flash(request, "Conjunto registrado.")
        return redirigir(f"/conjuntos/{nuevo}")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        return redirigir("/conjuntos")


@router.get("/conjuntos/plantilla-unidades.xlsx")
def plantilla():
    return Response(plantilla_unidades(), headers={
        "Content-Disposition": 'attachment; filename="plantilla_unidades.xlsx"'},
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.post("/conjuntos/{conjunto_id}/importar")
async def importar_unidades(request: Request, conjunto_id: int):
    f = await leer_formulario(request)
    archivo = f.get("archivo")
    try:
        if not hasattr(archivo, "read"):
            raise ReglaNegocioError("Seleccione un archivo .xlsx o .csv.")
        filas = leer_unidades(archivo.filename, await archivo.read())
        creadas = conjuntos.importar_unidades(conjunto_id, filas)
        flash(request, f"Se registraron {creadas} unidades desde {archivo.filename}.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(f"/conjuntos/{conjunto_id}")


@router.get("/conjuntos/{conjunto_id}")
def detalle_conjunto(request: Request, conjunto_id: int):
    datos = conjuntos.detalle(conjunto_id)
    token = datos["conjunto"].get("formulario_token")
    enlace = f"{str(request.base_url).rstrip('/')}/registro/{token}" if token else None
    return render(request, "conjunto_detalle.html", enlace_formulario=enlace,
                  pendientes=censo.contar_pendientes(conjunto_id), **datos)


@router.post("/conjuntos/{conjunto_id}/formulario")
async def formulario_conjunto(request: Request, conjunto_id: int):
    f = await leer_formulario(request)
    if f.get("accion") == "cerrar":
        censo.cerrar_formulario(conjunto_id)
        flash(request, "Formulario cerrado. El enlace anterior ya no recibe solicitudes.")
    else:
        censo.abrir_formulario(conjunto_id)
        flash(request, "Formulario abierto. Copie el enlace y compártalo con los propietarios.")
    return redirigir(f"/conjuntos/{conjunto_id}#formulario")


@router.get("/conjuntos/{conjunto_id}/solicitudes")
def solicitudes(request: Request, conjunto_id: int):
    return render(request, "solicitudes.html", **censo.solicitudes(conjunto_id))


@router.post("/solicitudes/{solicitud_id}/aprobar")
async def aprobar_solicitud(request: Request, solicitud_id: int):
    f = await leer_formulario(request)
    try:
        conjunto_id = censo.aprobar(solicitud_id, request.session["usuario"]["id"])
        flash(request, "Solicitud aprobada. La unidad quedó con los datos del nuevo representante.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        conjunto_id = int(f.get("conjunto_id", 0))
    return redirigir(f"/conjuntos/{conjunto_id}/solicitudes")


@router.post("/solicitudes/{solicitud_id}/rechazar")
async def rechazar_solicitud(request: Request, solicitud_id: int):
    f = await leer_formulario(request)
    try:
        conjunto_id = censo.rechazar(solicitud_id, request.session["usuario"]["id"], f.get("motivo"))
        flash(request, "Solicitud rechazada.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        conjunto_id = int(f.get("conjunto_id", 0))
    return redirigir(f"/conjuntos/{conjunto_id}/solicitudes")


@router.post("/conjuntos/{conjunto_id}/unidades")
async def crear_unidad(request: Request, conjunto_id: int):
    f = await leer_formulario(request)
    try:
        conjuntos.crear_unidad(conjunto_id, f.get("identificador"), f.get("propietario_nombre"),
                               f.get("propietario_documento"), f.get("propietario_email"),
                               f.get("propietario_telefono"), f.get("coeficiente"))
        flash(request, "Unidad registrada.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(f"/conjuntos/{conjunto_id}")


@router.post("/unidades/{unidad_id}/activo")
async def activo_unidad(request: Request, unidad_id: int):
    f = await leer_formulario(request)
    conjunto_id = conjuntos.cambiar_activo_unidad(unidad_id, f.get("activo") == "1")
    flash(request, "Estado de la unidad actualizado.")
    return redirigir(f"/conjuntos/{conjunto_id}")
