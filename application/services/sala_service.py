"""RF-05 y RF-06 en asambleas virtuales: sala web de cada unidad (art. 42, Ley 675 de 2001).

Como en el módulo nuvoll_asambleas, cada convocatoria lleva un enlace personal y único
(token_acceso, 192 bits aleatorios): quien lo abre entra a la sala de esa unidad sin iniciar
sesión. El enlace es la credencial, por eso:
- no se puede adivinar ni deducir de otro enlace;
- al registrar un poder se renueva y el del propietario deja de servir;
- cada ingreso y cada voto quedan con la unidad, la hora y, si el representante tiene cuenta,
  su usuario: la prueba que exige el artículo 42 para las reuniones no presenciales.
"""
from domain import reglas
from domain.excepciones import ReglaNegocioError
from infrastructure.dao import (AsambleaDAO, AsistenciaDAO, ConjuntoDAO, ConvocatoriaDAO,
                                PoderDAO, PuntoOrdenDiaDAO, ResultadoVotacionDAO, UsuarioDAO, VotoDAO)
from infrastructure.db import solo_lectura, transaccion
from infrastructure.errores_bd import traducir_errores_bd

from .asamblea_service import _kpis
from .votacion_service import VotacionService

ESTADOS_SALA = ("convocada", "en_curso")


def _acceso(conn, token: str) -> dict:
    """Valida el enlace y resuelve quién representa la unidad (propietario o apoderado)."""
    cv = ConvocatoriaDAO(conn).obtener_por_token(token or "")
    if not cv:
        raise ReglaNegocioError("Este enlace no es válido o fue renovado. Pida a la administración el enlace vigente.")
    asamblea = AsambleaDAO(conn).obtener_detalle(cv["asamblea_id"])
    if asamblea["modalidad"] == "presencial":
        raise ReglaNegocioError("Esta asamblea es presencial: no tiene sala virtual.")
    poder = PoderDAO(conn).vigente_de_unidad(asamblea["id"], cv["unidad_id"])
    if poder:
        calidad, nombre, documento = "apoderado", poder["apoderado_nombre"], poder["apoderado_documento"]
    else:
        calidad, nombre, documento = "propietario", cv["propietario_nombre"], cv["propietario_documento"]
    cuenta = UsuarioDAO(conn).obtener_por_documento(documento)
    return {"convocatoria": cv, "asamblea": asamblea, "poder": poder, "calidad": calidad,
            "representante": nombre, "usuario_id": cuenta["id"] if cuenta else None}


def _quorum(conn, asamblea: dict) -> dict:
    asistencia = AsistenciaDAO(conn)
    porcentaje = reglas.porcentaje_quorum(asistencia.suma_coeficientes(asamblea["id"]),
                                          asamblea["coeficiente_total"])
    return {"porcentaje": float(porcentaje), "unidades_presentes": asistencia.contar(asamblea["id"]),
            "hay_quorum": reglas.hay_quorum_deliberatorio(porcentaje)}


class SalaService:
    # ------------------------------------------------------------ propietario / apoderado (con su enlace)
    def ver(self, token: str) -> dict:
        """Todo lo que muestra la sala: unidad, ingreso, punto abierto y si ya votó."""
        with solo_lectura() as conn:
            ctx = _acceso(conn, token)
            a, cv = ctx["asamblea"], ctx["convocatoria"]
            ingreso = AsistenciaDAO(conn).de_unidad(a["id"], cv["unidad_id"])
            punto = PuntoOrdenDiaDAO(conn).punto_abierto(a["id"]) if a["estado"] == "en_curso" else None
            ya_voto = bool(punto) and cv["unidad_id"] in VotoDAO(conn).unidades_que_votaron(punto["id"])
            puntos = PuntoOrdenDiaDAO(conn).listar_por_asamblea(a["id"])
            resultados = {r["punto_id"]: r for r in ResultadoVotacionDAO(conn).listar_por_asamblea(a["id"])}
            return {**ctx, "ingreso": ingreso, "punto": punto, "ya_voto": ya_voto, "puntos": puntos,
                    "resultados": resultados, "quorum": _quorum(conn, a), "token": token}

    def estado(self, token: str) -> dict:
        """Versión breve para la actualización automática de la sala (cada 4 s)."""
        v = self.ver(token)
        return {"estado": v["asamblea"]["estado"], "ingresado": bool(v["ingreso"]),
                "punto_id": v["punto"]["id"] if v["punto"] else None, "ya_voto": v["ya_voto"],
                "quorum": v["quorum"]}

    @traducir_errores_bd
    def ingresar(self, token: str) -> dict:
        """Confirma el ingreso: crea la asistencia y recalcula el quórum en UNA transacción, con el
        mismo bloqueo de la asamblea que usa la recepción (RF-05)."""
        with transaccion() as conn:
            ctx = _acceso(conn, token)
            asamblea = AsambleaDAO(conn).obtener(ctx["asamblea"]["id"], bloquear=True)
            if asamblea["estado"] not in ESTADOS_SALA:
                raise ReglaNegocioError("La sala solo admite ingresos con la asamblea convocada o en curso.")
            cv = ctx["convocatoria"]
            if not cv["unidad_activa"]:
                raise ReglaNegocioError("La unidad está inactiva.")
            if AsistenciaDAO(conn).de_unidad(asamblea["id"], cv["unidad_id"]):
                raise ReglaNegocioError("La unidad ya registró su ingreso.")
            tipo, poder_id = ("poder", ctx["poder"]["id"]) if ctx["poder"] else ("virtual", None)
            AsistenciaDAO(conn).crear(asamblea["id"], cv["unidad_id"], poder_id, tipo,
                                      cv["coeficiente_copropiedad"])
            quorum = _quorum(conn, {**asamblea, "coeficiente_total": ctx["asamblea"]["coeficiente_total"]})
            AsambleaDAO(conn).actualizar_quorum(asamblea["id"], quorum["porcentaje"])
            return quorum

    def votar(self, token: str, decision: str) -> None:
        """Vota por la unidad del enlace en el punto abierto (misma transacción de RF-06)."""
        with solo_lectura() as conn:
            ctx = _acceso(conn, token)
            punto = PuntoOrdenDiaDAO(conn).punto_abierto(ctx["asamblea"]["id"])
        if not punto:
            raise ReglaNegocioError("No hay ningún punto abierto a votación.")
        VotacionService().votar_unidad(punto["id"], ctx["convocatoria"]["unidad_id"], ctx["usuario_id"], decision)

    def mis_salas(self, usuario: dict) -> list[dict]:
        with solo_lectura() as conn:
            return ConvocatoriaDAO(conn).salas_de(usuario["documento"])

    # ------------------------------------------------------------ administración
    def en_vivo(self, asamblea_id: int) -> dict:
        """Pantalla de la administración: quórum, punto abierto con votos y participación."""
        with solo_lectura() as conn:
            asamblea = AsambleaDAO(conn).obtener_detalle(asamblea_id)
            if not asamblea:
                raise ReglaNegocioError("Asamblea no encontrada.")
            quorum = _quorum(conn, asamblea)
            punto = PuntoOrdenDiaDAO(conn).punto_abierto(asamblea_id)
            votos = None
            if punto:
                votos = {k: float(v) for k, v in VotoDAO(conn).totales_por_punto(punto["id"]).items()}
                votos["unidades"] = VotoDAO(conn).contar(punto["id"])
                presentes = quorum["unidades_presentes"] or 1
                votos["participacion"] = round(votos["unidades"] * 100 / presentes, 1)
            puntos = PuntoOrdenDiaDAO(conn).listar_por_asamblea(asamblea_id)
            resultados = {r["punto_id"]: r for r in ResultadoVotacionDAO(conn).listar_por_asamblea(asamblea_id)}
            kpis = _kpis(AsambleaDAO(conn).indicadores(asamblea_id),
                         {**asamblea, "quorum_alcanzado": quorum["porcentaje"]})
            return {"asamblea": asamblea, "quorum": quorum, "punto": punto, "votos": votos, "kpis": kpis,
                    "puntos": puntos, "resultados": resultados,
                    "conjunto": ConjuntoDAO(conn).obtener(asamblea["conjunto_id"])}

    def en_vivo_json(self, asamblea_id: int) -> dict:
        v = self.en_vivo(asamblea_id)
        return {"estado": v["asamblea"]["estado"], "quorum": v["quorum"], "votos": v["votos"],
                "punto": ({"id": v["punto"]["id"], "orden": v["punto"]["orden"],
                           "descripcion": v["punto"]["descripcion"]} if v["punto"] else None),
                "cerrados": len(v["resultados"])}

    def enlaces(self, asamblea_id: int) -> list[dict]:
        with solo_lectura() as conn:
            return ConvocatoriaDAO(conn).listar_por_asamblea(asamblea_id)
