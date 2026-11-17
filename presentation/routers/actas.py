"""RF-07: actas e histórico."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from application.services import ActaService
from domain.excepciones import ReglaNegocioError

from ..dependencias import leer_formulario, requiere_roles
from ..vistas import flash, redirigir, render

router = APIRouter()
servicio = ActaService()


@router.post("/asambleas/{asamblea_id}/acta", dependencies=[Depends(requiere_roles("administrador"))])
async def generar(request: Request, asamblea_id: int):
    await leer_formulario(request)
    try:
        acta_id = servicio.generar(asamblea_id)
        flash(request, "Acta generada a partir del historial transaccional.")
        return redirigir(f"/actas/{acta_id}")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
        return redirigir(f"/asambleas/{asamblea_id}")


@router.get("/actas/{acta_id}")
def ver(request: Request, acta_id: int, usuario: dict = Depends(requiere_roles())):
    return render(request, "acta.html", **servicio.detalle(acta_id, usuario))


@router.get("/actas/{acta_id}/descargar")
def descargar(acta_id: int, usuario: dict = Depends(requiere_roles())):
    """Acta en texto plano con hash y firmas, como archivo adjunto."""
    datos = servicio.detalle(acta_id, usuario)
    a = datos["acta"]
    texto = f"{a['contenido']}\n\nHash SHA-256: {a['hash']}\nEstado: {a['estado']}\n"
    for ap in datos["aprobaciones"]:
        texto += f"Aprobada por {ap['rol_en_aprobacion']}: {ap['nombre']} ({ap['fecha']:%Y-%m-%d %H:%M})\n"
    return PlainTextResponse(
        texto, headers={"Content-Disposition": f'attachment; filename="acta_{acta_id}.txt"'}
    )


@router.post("/actas/{acta_id}/aprobar")
async def aprobar(request: Request, acta_id: int,
                  usuario: dict = Depends(requiere_roles("presidente", "secretario"))):
    f = await leer_formulario(request)
    try:
        servicio.aprobar(acta_id, usuario, f.get("rol"))
        flash(request, "Aprobación registrada.")
    except ReglaNegocioError as e:
        flash(request, str(e), "error")
    return redirigir(f"/actas/{acta_id}")


@router.get("/historico")
def historico(request: Request, usuario: dict = Depends(requiere_roles())):
    return render(request, "historico.html", asambleas=servicio.historico(usuario))
