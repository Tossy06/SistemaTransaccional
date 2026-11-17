"""RF-06: apertura y cierre de puntos (administrador) y voto (copropietario o apoderado)."""
from fastapi import APIRouter, Depends, Request

from application.services import SalaService, VotacionService
from domain.excepciones import ReglaNegocioError

from ..dependencias import leer_formulario, requiere_roles
from ..vistas import flash, redirigir, render

router = APIRouter()
servicio = VotacionService()
votante = requiere_roles("copropietario", "apoderado")


@router.post("/puntos/{punto_id}/abrir", dependencies=[Depends(requiere_roles("administrador"))])
async def abrir(request: Request, punto_id: int):
    await leer_formulario(request)
    try:
        asamblea_id = servicio.abrir_punto(punto_id)
        flash(request, "Votación abierta.")
        return redirigir(f"/asambleas/{asamblea_id}")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        return redirigir(request.headers.get("referer", "/asambleas"))


@router.post("/puntos/{punto_id}/cerrar", dependencies=[Depends(requiere_roles("administrador"))])
async def cerrar(request: Request, punto_id: int):
    await leer_formulario(request)
    try:
        r = servicio.cerrar_punto(punto_id)
        flash(request, f"Votación cerrada: {r['resultado'].upper()} "
                       f"(a favor {r['a_favor']}, en contra {r['en_contra']}, abstención {r['abstencion']}).")
        return redirigir(f"/asambleas/{r['asamblea_id']}")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        return redirigir(request.headers.get("referer", "/asambleas"))


@router.get("/votar")
def panel(request: Request, usuario: dict = Depends(votante)):
    return render(request, "votar.html", sesiones=servicio.panel_votante(usuario),
                  salas=SalaService().mis_salas(usuario))


@router.post("/votar/{punto_id}")
async def votar(request: Request, punto_id: int, usuario: dict = Depends(votante)):
    f = await leer_formulario(request)
    try:
        servicio.votar(punto_id, int(f.get("unidad_id") or 0), usuario, f.get("decision"))
        flash(request, "Voto registrado.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir("/votar")
