"""RF-07: generación, aprobación y consulta de actas."""
from domain import acta as reglas_acta
from domain.catalogos import ROLES_FIRMA_ACTA, ROLES_GESTION_ACTA
from domain.excepciones import ReglaNegocioError
from infrastructure.dao import (ActaAprobacionDAO, ActaDAO, AsambleaDAO, AsistenciaDAO,
                                PuntoOrdenDiaDAO, ResultadoVotacionDAO)
from infrastructure.db import solo_lectura, transaccion
from infrastructure.errores_bd import traducir_errores_bd

from ..excepciones import NoAutorizado


def _es_gestor(usuario: dict) -> bool:
    return bool(set(ROLES_GESTION_ACTA) & set(usuario["roles"]))


class ActaService:
    @traducir_errores_bd
    def generar(self, asamblea_id: int) -> int:
        """Redacta el acta de una asamblea finalizada y guarda su hash."""
        with transaccion() as conn:
            asamblea = AsambleaDAO(conn).obtener(asamblea_id, bloquear=True)
            if asamblea["estado"] != "finalizada":
                raise ReglaNegocioError("El acta solo se genera cuando la asamblea está finalizada.")
            resultados = {r["punto_id"]: r
                          for r in ResultadoVotacionDAO(conn).listar_por_asamblea(asamblea_id)}
            contenido = reglas_acta.redactar(
                AsambleaDAO(conn).obtener_detalle(asamblea_id),
                AsistenciaDAO(conn).listar_por_asamblea(asamblea_id),
                PuntoOrdenDiaDAO(conn).listar_por_asamblea(asamblea_id),
                resultados,
            )
            return ActaDAO(conn).crear(asamblea_id, contenido, reglas_acta.calcular_hash(contenido))

    def detalle(self, acta_id: int, usuario: dict) -> dict:
        """Acta con aprobaciones y verificación de integridad.

        Las actas en borrador solo son visibles para los roles de gestión.
        """
        with solo_lectura() as conn:
            acta = ActaDAO(conn).obtener(acta_id)
            if not acta:
                raise ReglaNegocioError("Acta no encontrada.")
            if acta["estado"] != "aprobada" and not _es_gestor(usuario):
                raise NoAutorizado("El acta aún no está aprobada.")
            return {
                "acta": acta,
                "aprobaciones": ActaAprobacionDAO(conn).listar_por_acta(acta_id),
                "integra": reglas_acta.es_integra(acta["contenido"], acta["hash"]),
                "asamblea": AsambleaDAO(conn).obtener_detalle(acta["asamblea_id"]),
            }

    @traducir_errores_bd
    def aprobar(self, acta_id: int, usuario: dict, rol: str) -> None:
        """Registra la firma del rol; con todas las firmas el acta queda aprobada."""
        if rol not in ROLES_FIRMA_ACTA or rol not in usuario["roles"]:
            raise ReglaNegocioError("Solo el presidente o el secretario pueden aprobar el acta.")
        with transaccion() as conn:
            actas = ActaDAO(conn)
            acta = actas.obtener(acta_id, bloquear=True)
            if acta["estado"] != "borrador":
                raise ReglaNegocioError("El acta ya está aprobada.")
            if not reglas_acta.es_integra(acta["contenido"], acta["hash"]):
                raise ReglaNegocioError("El contenido del acta fue alterado: el hash no coincide.")
            aprobaciones = ActaAprobacionDAO(conn)
            aprobaciones.crear(acta_id, usuario["id"], rol)
            firmas = {a["rol_en_aprobacion"] for a in aprobaciones.listar_por_acta(acta_id)}
            if firmas == set(ROLES_FIRMA_ACTA):
                actas.marcar_aprobada(acta_id)

    def historico(self, usuario: dict) -> list[dict]:
        """Asambleas cerradas. Sin rol de gestión solo se enlazan actas aprobadas."""
        with solo_lectura() as conn:
            filas = AsambleaDAO(conn).listar_historico()
        if not _es_gestor(usuario):
            for f in filas:
                if f["acta_estado"] != "aprobada":
                    f["acta_id"] = None
        return filas
