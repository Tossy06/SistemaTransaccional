"""Asambleas virtuales: sala de cada unidad, pantalla en vivo y enlaces de acceso."""
import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from application.services import AsambleaService, AsistenciaService, SalaService
from domain.excepciones import ReglaNegocioError

from ..dependencias import leer_formulario, requiere_roles
from ..vistas import flash, redirigir, render

router = APIRouter()
sala, asambleas, asistencia = SalaService(), AsambleaService(), AsistenciaService()
admin = Depends(requiere_roles("administrador"))
recepcion = Depends(requiere_roles("administrador", "recepcionista"))


# ------------------------------------------------------------ sala del propietario / apoderado
@router.get("/sala/{token}")
def ver_sala(request: Request, token: str):
    """Pública: el enlace único es la credencial (como nuvoll_asambleas)."""
    return render(request, "sala.html", **sala.ver(token))


@router.post("/sala/{token}/ingresar")
async def ingresar(request: Request, token: str):
    await leer_formulario(request)
    try:
        q = sala.ingresar(token)
        flash(request, f"Ingreso registrado. Quórum actual: {q['porcentaje']} %.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(f"/sala/{token}")


@router.post("/sala/{token}/votar")
async def votar(request: Request, token: str):
    f = await leer_formulario(request)
    try:
        sala.votar(token, f.get("decision"))
        flash(request, "Voto registrado.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(f"/sala/{token}")


@router.get("/api/sala/{token}/estado")
def estado_sala(token: str):
    return sala.estado(token)


# ------------------------------------------------------------ administración
@router.get("/asambleas/{asamblea_id}/en-vivo", dependencies=[recepcion])
def en_vivo(request: Request, asamblea_id: int):
    return render(request, "en_vivo.html", **sala.en_vivo(asamblea_id))


@router.get("/api/asambleas/{asamblea_id}/en-vivo", dependencies=[recepcion])
def en_vivo_json(asamblea_id: int):
    return sala.en_vivo_json(asamblea_id)


@router.get("/asambleas/{asamblea_id}/enlaces.csv", dependencies=[admin])
def enlaces_csv(request: Request, asamblea_id: int):
    """Enlace personal de cada unidad para enviarlo por correo o WhatsApp."""
    base = str(request.base_url).rstrip("/")
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow(["unidad", "propietario", "correo", "enlace_sala"])
    for c in sala.enlaces(asamblea_id):
        escritor.writerow([c["identificador"], c["propietario_nombre"], c["propietario_email"] or "",
                           f"{base}/sala/{c['token_acceso']}"])
    return Response("﻿" + salida.getvalue(), media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="enlaces_sala_asamblea_{asamblea_id}.csv"'})


async def _accion(request: Request, accion, destino: str, exito: str):
    await leer_formulario(request)
    try:
        accion()
        flash(request, exito)
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(destino)


@router.post("/asambleas/{asamblea_id}/reabrir-orden", dependencies=[admin])
async def reabrir_orden(request: Request, asamblea_id: int):
    return await _accion(request, lambda: asambleas.reabrir_orden_del_dia(asamblea_id),
                         f"/asambleas/{asamblea_id}", "Orden del día reabierto: puede agregar o quitar puntos.")


@router.post("/asambleas/{asamblea_id}/anular-convocatoria", dependencies=[admin])
async def anular_convocatoria(request: Request, asamblea_id: int):
    return await _accion(request, lambda: asambleas.anular_convocatoria(asamblea_id), f"/asambleas/{asamblea_id}",
                         "Convocatoria anulada: la asamblea volvió a Programada y sus enlaces dejaron de servir.")


@router.post("/asambleas/{asamblea_id}/eliminar", dependencies=[admin])
async def eliminar(request: Request, asamblea_id: int):
    await leer_formulario(request)
    try:
        asambleas.eliminar(asamblea_id)
        flash(request, f"Asamblea n.º {asamblea_id} eliminada.")
        return redirigir("/asambleas")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        return redirigir(f"/asambleas/{asamblea_id}")


@router.post("/asambleas/{asamblea_id}/videollamada", dependencies=[admin])
async def videollamada(request: Request, asamblea_id: int):
    f = await leer_formulario(request)
    try:
        asambleas.actualizar_enlace(asamblea_id, f.get("enlace_videollamada"))
        flash(request, "Enlace de la videollamada actualizado.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(f"/asambleas/{asamblea_id}")


@router.post("/asambleas/{asamblea_id}/poderes", dependencies=[recepcion])
async def poder_previo(request: Request, asamblea_id: int):
    f = await leer_formulario(request)
    try:
        asistencia.registrar_poder_previo(asamblea_id, int(f.get("unidad_id") or 0),
                                          f.get("apoderado_nombre"), f.get("apoderado_documento"))
        flash(request, "Poder registrado. El enlace de la unidad se renovó: entréguelo al apoderado "
                       "(tabla de participantes de la asamblea).")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(f"/asambleas/{asamblea_id}/asistencia")
