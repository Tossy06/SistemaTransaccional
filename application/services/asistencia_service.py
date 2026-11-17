"""RF-05: registro de asistencia, poderes y quórum en tiempo real."""
import secrets
from domain import reglas
from domain.excepciones import ReglaNegocioError
from infrastructure.dao import (AsambleaDAO, AsistenciaDAO, ConjuntoDAO, ConvocatoriaDAO, PoderDAO,
                                UnidadDAO)
from infrastructure.db import solo_lectura, transaccion
from infrastructure.errores_bd import traducir_errores_bd


def _calcular_quorum(conn, asamblea_id: int) -> dict:
    asamblea = AsambleaDAO(conn).obtener(asamblea_id)
    conjunto = ConjuntoDAO(conn).obtener(asamblea["conjunto_id"])
    asistencia = AsistenciaDAO(conn)
    presente = asistencia.suma_coeficientes(asamblea_id)
    porcentaje = reglas.porcentaje_quorum(presente, conjunto["coeficiente_total"])
    return {
        "porcentaje": float(porcentaje),
        "coeficiente_presente": float(presente),
        "coeficiente_total": float(conjunto["coeficiente_total"]),
        "unidades_presentes": asistencia.contar(asamblea_id),
        "hay_quorum": reglas.hay_quorum_deliberatorio(porcentaje),
    }


class AsistenciaService:
    def quorum(self, asamblea_id: int) -> dict:
        """Estado actual del quórum (consultado por la interfaz cada pocos segundos)."""
        with solo_lectura() as conn:
            return _calcular_quorum(conn, asamblea_id)

    def panel(self, asamblea_id: int) -> dict:
        """Unidades registradas, pendientes y quórum para la vista de recepción."""
        with solo_lectura() as conn:
            asamblea = AsambleaDAO(conn).obtener_detalle(asamblea_id)
            if not asamblea:
                raise ReglaNegocioError("Asamblea no encontrada.")
            registrados = AsistenciaDAO(conn).listar_por_asamblea(asamblea_id)
            ids = {r["unidad_id"] for r in registrados}
            pendientes = [u for u in UnidadDAO(conn).listar_por_conjunto(asamblea["conjunto_id"], True)
                          if u["id"] not in ids]
            return {"asamblea": asamblea, "registrados": registrados, "pendientes": pendientes,
                    "quorum": _calcular_quorum(conn, asamblea_id)}

    @traducir_errores_bd
    def registrar(self, asamblea_id: int, unidad_id: int, tipo: str,
                  apoderado_nombre: str = "", apoderado_documento: str = "") -> dict:
        """Registra asistencia (y poder si aplica) y recalcula el quórum en una transacción.

        El FOR UPDATE sobre la asamblea serializa registros simultáneos, así el
        quórum guardado siempre es consistente. Devuelve el quórum actualizado.
        """
        if tipo not in ("presencial", "poder"):  # la asistencia virtual la registra la propia sala
            raise ReglaNegocioError("Tipo de asistencia inválido.")
        with transaccion() as conn:
            asamblea = AsambleaDAO(conn).obtener(asamblea_id, bloquear=True)
            if not asamblea or asamblea["estado"] not in ("convocada", "en_curso"):
                raise ReglaNegocioError("Solo se registra asistencia en asambleas convocadas o en curso.")
            if asamblea["modalidad"] == "virtual":
                raise ReglaNegocioError("La asamblea es virtual: cada asistente ingresa por la sala. "
                                        "Para un apoderado, registre el poder previo.")
            unidad = UnidadDAO(conn).obtener(unidad_id)
            if not unidad or unidad["conjunto_id"] != asamblea["conjunto_id"] or not unidad["activo"]:
                raise ReglaNegocioError("La unidad no pertenece al conjunto o está inactiva.")

            poder_id = None
            if tipo == "poder":
                if not (apoderado_nombre and apoderado_documento):
                    raise ReglaNegocioError("Indique nombre y documento del apoderado.")
                if apoderado_documento == unidad["propietario_documento"]:
                    raise ReglaNegocioError("El apoderado no puede ser el mismo propietario.")
                poder_id = PoderDAO(conn).crear(asamblea_id, unidad_id, apoderado_nombre, apoderado_documento)

            # Se congela el coeficiente vigente para ponderar los votos de esta sesión.
            AsistenciaDAO(conn).crear(asamblea_id, unidad_id, poder_id, tipo, unidad["coeficiente_copropiedad"])
            quorum = _calcular_quorum(conn, asamblea_id)
            AsambleaDAO(conn).actualizar_quorum(asamblea_id, quorum["porcentaje"])
            return quorum

    @traducir_errores_bd
    def registrar_poder_previo(self, asamblea_id: int, unidad_id: int,
                               apoderado_nombre: str, apoderado_documento: str) -> None:
        """Poder para una asamblea virtual o mixta: se registra antes de la reunión y el
        apoderado acredita la asistencia al ingresar a la sala (no cuenta para el quórum aún)."""
        apoderado_nombre = (apoderado_nombre or "").strip()
        apoderado_documento = (apoderado_documento or "").strip()
        if not (apoderado_nombre and apoderado_documento):
            raise ReglaNegocioError("Indique nombre y documento del apoderado.")
        with transaccion() as conn:
            asamblea = AsambleaDAO(conn).obtener(asamblea_id, bloquear=True)
            if not asamblea or asamblea["estado"] not in ("convocada", "en_curso"):
                raise ReglaNegocioError("Solo se registran poderes en asambleas convocadas o en curso.")
            if asamblea["modalidad"] == "presencial":
                raise ReglaNegocioError("En una asamblea presencial el poder se registra en la recepción.")
            unidad = UnidadDAO(conn).obtener(unidad_id)
            if not unidad or unidad["conjunto_id"] != asamblea["conjunto_id"] or not unidad["activo"]:
                raise ReglaNegocioError("La unidad no pertenece al conjunto o está inactiva.")
            if apoderado_documento == unidad["propietario_documento"]:
                raise ReglaNegocioError("El apoderado no puede ser el mismo propietario.")
            if AsistenciaDAO(conn).de_unidad(asamblea_id, unidad_id):
                raise ReglaNegocioError("La unidad ya registró su asistencia.")
            PoderDAO(conn).crear(asamblea_id, unidad_id, apoderado_nombre, apoderado_documento)
            # El enlace de la unidad pasa al apoderado: se renueva y el del propietario deja de servir.
            ConvocatoriaDAO(conn).renovar_token(asamblea_id, unidad_id, secrets.token_urlsafe(24))

