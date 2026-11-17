"""RF-03 asambleas y orden del día, RF-04 convocatoria, RF-05 asistencia y quórum."""
from fastapi import APIRouter, Depends, Request

from application.services import AsambleaService, AsistenciaService
from domain.excepciones import ReglaNegocioError

from ..dependencias import leer_formulario, requiere_roles
from ..vistas import flash, redirigir, render

router = APIRouter()
# Dependencias de rol reutilizadas en las rutas.
admin = Depends(requiere_roles("administrador"))
recepcion = Depends(requiere_roles("administrador", "recepcionista"))
asambleas, asistencia = AsambleaService(), AsistenciaService()


async def _ejecutar(request: Request, accion, destino: str, exito: str | None = None):
    """Valida CSRF, ejecuta la acción de negocio y muestra el mensaje correspondiente."""
    await leer_formulario(request)
    try:
        msg = accion()
        flash(request, exito or msg or "Operación realizada.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(destino)


@router.get("/asambleas", dependencies=[recepcion])
def listar(request: Request):
    return render(request, "asambleas.html", **asambleas.listar())


@router.post("/asambleas", dependencies=[admin])
async def crear(request: Request):
    f = await leer_formulario(request)
    try:
        nueva = asambleas.crear(int(f.get("conjunto_id")), f.get("tipo"), f.get("fecha"),
                                f.get("hora"), f.get("lugar_modalidad"), f.get("modalidad"),
                                f.get("enlace_videollamada"))
        flash(request, "Asamblea registrada en estado 'programada'.")
        return redirigir(f"/asambleas/{nueva}")
    except (ReglaNegocioError, ValueError, TypeError) as e:
        flash(request, str(e) if isinstance(e, ReglaNegocioError) else "Datos inválidos.", "error")
        return redirigir("/asambleas")


@router.get("/asambleas/{asamblea_id}", dependencies=[recepcion])
def detalle(request: Request, asamblea_id: int):
    return render(request, "asamblea_detalle.html", **asambleas.detalle(asamblea_id),
                  quorum=asistencia.quorum(asamblea_id))


@router.post("/asambleas/{asamblea_id}/puntos", dependencies=[admin])
async def agregar_punto(request: Request, asamblea_id: int):
    f = await leer_formulario(request)
    try:
        asambleas.agregar_punto(asamblea_id, f.get("descripcion"), f.get("tipo_mayoria"))
        flash(request, "Punto agregado al orden del día.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(f"/asambleas/{asamblea_id}")


@router.post("/puntos/{punto_id}/eliminar", dependencies=[admin])
async def eliminar_punto(request: Request, punto_id: int):
    await leer_formulario(request)
    try:
        asamblea_id = asambleas.eliminar_punto(punto_id)
        flash(request, "Punto eliminado.")
        return redirigir(f"/asambleas/{asamblea_id}")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        return redirigir(request.headers.get("referer", "/asambleas"))


@router.post("/asambleas/{asamblea_id}/cerrar-orden", dependencies=[admin])
async def cerrar_orden(request: Request, asamblea_id: int):
    return await _ejecutar(request, lambda: asambleas.cerrar_orden_del_dia(asamblea_id),
                           f"/asambleas/{asamblea_id}", "Orden del día cerrado.")


@router.post("/asambleas/{asamblea_id}/convocatoria", dependencies=[admin])
async def convocar(request: Request, asamblea_id: int):
    return await _ejecutar(
        request,
        lambda: f"Convocatoria generada para {asambleas.generar_convocatoria(asamblea_id)} unidades.",
        f"/asambleas/{asamblea_id}")


@router.post("/convocatorias/{convocatoria_id}/confirmar", dependencies=[admin])
async def confirmar(request: Request, convocatoria_id: int):
    await leer_formulario(request)
    asamblea_id = asambleas.confirmar_entrega(convocatoria_id)
    flash(request, "Entrega confirmada.")
    return redirigir(f"/asambleas/{asamblea_id}#convocatoria")


@router.post("/asambleas/{asamblea_id}/iniciar", dependencies=[admin])
async def iniciar(request: Request, asamblea_id: int):
    return await _ejecutar(request, lambda: asambleas.iniciar(asamblea_id), f"/asambleas/{asamblea_id}")


@router.post("/asambleas/{asamblea_id}/segunda-convocatoria", dependencies=[admin])
async def segunda(request: Request, asamblea_id: int):
    await leer_formulario(request)
    try:
        nueva = asambleas.crear_segunda_convocatoria(asamblea_id)
        flash(request, "Reunión de segunda convocatoria programada (tercer día hábil, 8:00 p. m.).")
        return redirigir(f"/asambleas/{nueva}")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        return redirigir(f"/asambleas/{asamblea_id}")


@router.post("/asambleas/{asamblea_id}/finalizar", dependencies=[admin])
async def finalizar(request: Request, asamblea_id: int):
    return await _ejecutar(request, lambda: asambleas.finalizar(asamblea_id),
                           f"/asambleas/{asamblea_id}", "Asamblea finalizada.")


# ------------------------------------------------------------- asistencia
@router.get("/asambleas/{asamblea_id}/asistencia", dependencies=[recepcion])
def panel_asistencia(request: Request, asamblea_id: int):
    return render(request, "asistencia.html", **asistencia.panel(asamblea_id))


@router.post("/asambleas/{asamblea_id}/asistencia", dependencies=[recepcion])
async def registrar_asistencia(request: Request, asamblea_id: int):
    f = await leer_formulario(request)
    try:
        q = asistencia.registrar(asamblea_id, int(f.get("unidad_id") or 0), f.get("tipo_asistencia"),
                                 f.get("apoderado_nombre", ""), f.get("apoderado_documento", ""))
        flash(request, f"Asistencia registrada. Quórum actual: {q['porcentaje']} %.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(f"/asambleas/{asamblea_id}/asistencia")


@router.get("/api/asambleas/{asamblea_id}/quorum", dependencies=[Depends(requiere_roles())])
def quorum_json(asamblea_id: int):
    """Consulta en tiempo real usada por la interfaz (actualización cada 5 s)."""
    return asistencia.quorum(asamblea_id)
