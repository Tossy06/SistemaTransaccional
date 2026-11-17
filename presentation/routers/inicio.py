"""Página de inicio tras iniciar sesión."""
from fastapi import APIRouter, Depends, Request

from application.services import SalaService

from ..dependencias import requiere_roles
from ..vistas import render

router = APIRouter()


@router.get("/")
def inicio(request: Request, usuario: dict = Depends(requiere_roles())):
    return render(request, "inicio.html", salas=SalaService().mis_salas(usuario))
