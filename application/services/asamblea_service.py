"""RF-03 asambleas y orden del día, RF-04 convocatoria y desarrollo de la sesión."""
import secrets
from datetime import date, time

from domain import reglas
from domain.catalogos import MODALIDADES, TIPOS_ASAMBLEA, TIPOS_MAYORIA
from domain.excepciones import ReglaNegocioError
from infrastructure.config import settings
from infrastructure.dao import (ActaDAO, AsambleaDAO, AsistenciaDAO, ConjuntoDAO, PoderDAO,
                                ConvocatoriaDAO, PuntoOrdenDiaDAO, ResultadoVotacionDAO,
                                UnidadDAO)
from infrastructure.db import solo_lectura, transaccion
from infrastructure.errores_bd import traducir_errores_bd


def _validar_modalidad(modalidad: str, lugar: str | None, enlace: str | None):
    """Presencial y mixta necesitan lugar; el enlace de videollamada es opcional y https."""
    modalidad = (modalidad or "virtual").strip()
    if modalidad not in MODALIDADES:
        raise ReglaNegocioError("Modalidad inválida.")
    if modalidad != "virtual" and not (lugar or "").strip():
        raise ReglaNegocioError("Indique el lugar de la reunión presencial.")
    enlace = (enlace or "").strip() or None
    if enlace and not enlace.startswith("https://"):
        raise ReglaNegocioError("El enlace de la videollamada debe empezar por https://.")
    return modalidad, enlace


def _kpis(ind: dict, asamblea: dict) -> dict:
    """Indicadores de la sesión listos para mostrar."""
    total = float(asamblea.get("coeficiente_total") or 100)
    quorum = float(asamblea.get("quorum_alcanzado") or 0)
    presentes = ind["ingresaron"] or 0
    return {**ind, "quorum": quorum, "coeficiente_total": total,
            "participacion": round(ind["votos_punto_abierto"] * 100 / presentes, 1) if presentes else 0.0}


def _antelacion(asamblea: dict) -> dict:
    """Días que faltan y si la convocatoria cumple la antelación (ordinarias de primera convocatoria)."""
    dias = (asamblea["fecha"] - date.today()).days
    exige = asamblea["tipo"] == "ordinaria" and not asamblea["asamblea_original_id"]
    minimo = settings.dias_antelacion_ordinaria
    return {"dias": dias, "minimo": minimo, "cumple": (not exige) or dias >= minimo, "exige": exige}


def _asamblea_bloqueada(conn, asamblea_id: int) -> dict:
    """Obtiene la asamblea con FOR UPDATE para serializar cambios de estado."""
    asamblea = AsambleaDAO(conn).obtener(asamblea_id, bloquear=True)
    if not asamblea:
        raise ReglaNegocioError("Asamblea no encontrada.")
    return asamblea


def _exigir_orden_abierto(asamblea: dict) -> None:
    if asamblea["orden_del_dia_cerrado"]:
        raise ReglaNegocioError("El orden del día ya está cerrado y no admite cambios.")


class AsambleaService:
    # ---------------------------------------------------------------- consultas
    def listar(self) -> dict:
        with solo_lectura() as conn:
            return {
                "asambleas": AsambleaDAO(conn).listar_con_conjunto(),
                "conjuntos": ConjuntoDAO(conn).listar_activos(),
            }

    def detalle(self, asamblea_id: int) -> dict:
        """Datos completos para la vista de detalle de la asamblea."""
        with solo_lectura() as conn:
            dao = AsambleaDAO(conn)
            asamblea = dao.obtener_detalle(asamblea_id)
            if not asamblea:
                raise ReglaNegocioError("Asamblea no encontrada.")
            original_id = asamblea["asamblea_original_id"]
            return {
                "asamblea": asamblea,
                "puntos": PuntoOrdenDiaDAO(conn).listar_por_asamblea(asamblea_id),
                "resultados": {r["punto_id"]: r
                               for r in ResultadoVotacionDAO(conn).listar_por_asamblea(asamblea_id)},
                "convocatorias": ConvocatoriaDAO(conn).listar_por_asamblea(asamblea_id),
                "asistentes": AsistenciaDAO(conn).contar(asamblea_id),
                "original": dao.obtener(original_id) if original_id else None,
                "segunda": dao.segunda_de(asamblea_id),
                "acta": ActaDAO(conn).obtener_por_asamblea(asamblea_id),
                "kpis": _kpis(dao.indicadores(asamblea_id), asamblea),
                "participantes": UnidadDAO(conn).participantes(asamblea_id),
                "punto_abierto": PuntoOrdenDiaDAO(conn).punto_abierto(asamblea_id),
                "antelacion": _antelacion(asamblea),
            }

    # ------------------------------------------------- registro y orden del día
    @traducir_errores_bd
    def crear(self, conjunto_id: int, tipo: str, fecha: str, hora: str, lugar: str,
              modalidad: str = "virtual", enlace: str | None = None) -> int:
        """Registra la asamblea en estado 'programada'."""
        if tipo not in TIPOS_ASAMBLEA:
            raise ReglaNegocioError("Tipo de asamblea inválido.")
        modalidad, enlace = _validar_modalidad(modalidad, lugar, enlace)
        if not (fecha and hora):
            raise ReglaNegocioError("Fecha y hora son obligatorias.")
        f, h = date.fromisoformat(fecha), time.fromisoformat(hora)
        if f < date.today():
            raise ReglaNegocioError("La fecha de la asamblea no puede estar en el pasado.")
        minimo = settings.dias_antelacion_ordinaria
        if tipo == "ordinaria" and (f - date.today()).days < minimo:
            # Se avisa al programar: si no, la asamblea quedaría sin poder convocarse (HU-06).
            desde = date.today().toordinal() + minimo
            raise ReglaNegocioError(
                f"Una asamblea ordinaria se convoca con al menos {minimo} días de antelación: elija una "
                f"fecha desde el {date.fromordinal(desde):%Y-%m-%d} o regístrela como extraordinaria.")
        with transaccion() as conn:
            return AsambleaDAO(conn).crear(conjunto_id, tipo, f, h, (lugar or '').strip() or None,
                                           modalidad, enlace)

    def reabrir_orden_del_dia(self, asamblea_id: int) -> None:
        """Vuelve a permitir cambios en el orden del día mientras la asamblea no esté convocada."""
        with transaccion() as conn:
            asamblea = _asamblea_bloqueada(conn, asamblea_id)
            if asamblea["estado"] != "programada" or not asamblea["orden_del_dia_cerrado"]:
                raise ReglaNegocioError("Solo se reabre el orden del día de una asamblea programada sin convocar.")
            AsambleaDAO(conn).reabrir_orden_del_dia(asamblea_id)

    def anular_convocatoria(self, asamblea_id: int) -> None:
        """Deshace la convocatoria (y sus enlaces y poderes) si todavía nadie ha ingresado."""
        with transaccion() as conn:
            asamblea = _asamblea_bloqueada(conn, asamblea_id)
            if asamblea["estado"] != "convocada":
                raise ReglaNegocioError("Solo se anula la convocatoria de una asamblea convocada.")
            if AsistenciaDAO(conn).contar(asamblea_id):
                raise ReglaNegocioError("No se puede anular: ya hay unidades que ingresaron.")
            PoderDAO(conn).eliminar_de_asamblea(asamblea_id)
            ConvocatoriaDAO(conn).eliminar_de_asamblea(asamblea_id)
            AsambleaDAO(conn).cambiar_estado(asamblea_id, "programada")

    def eliminar(self, asamblea_id: int) -> None:
        """Borra una asamblea que no ha sesionado: sin asistencias, votos ni segunda convocatoria."""
        with transaccion() as conn:
            asamblea = _asamblea_bloqueada(conn, asamblea_id)
            dao = AsambleaDAO(conn)
            if asamblea["estado"] not in ("programada", "convocada"):
                raise ReglaNegocioError("Solo se elimina una asamblea programada o convocada que no ha sesionado.")
            if AsistenciaDAO(conn).contar(asamblea_id):
                raise ReglaNegocioError("No se puede eliminar: ya hay unidades que ingresaron.")
            if dao.segunda_de(asamblea_id):
                raise ReglaNegocioError("No se puede eliminar: tiene una reunión de segunda convocatoria.")
            PoderDAO(conn).eliminar_de_asamblea(asamblea_id)
            ConvocatoriaDAO(conn).eliminar_de_asamblea(asamblea_id)
            PuntoOrdenDiaDAO(conn).eliminar_de_asamblea(asamblea_id)
            dao.eliminar(asamblea_id)

    def actualizar_enlace(self, asamblea_id: int, enlace: str | None) -> None:
        """Cambia el enlace de videollamada mientras la asamblea no haya terminado."""
        with transaccion() as conn:
            asamblea = _asamblea_bloqueada(conn, asamblea_id)
            if asamblea["estado"] in ("finalizada", "sin_quorum"):
                raise ReglaNegocioError("La asamblea ya terminó.")
            _, enlace = _validar_modalidad(asamblea["modalidad"], asamblea["lugar_modalidad"] or "-", enlace)
            AsambleaDAO(conn).actualizar_enlace(asamblea_id, enlace)

    @traducir_errores_bd
    def agregar_punto(self, asamblea_id: int, descripcion: str, tipo_mayoria: str) -> None:
        if not descripcion:
            raise ReglaNegocioError("La descripción del punto es obligatoria.")
        if tipo_mayoria not in TIPOS_MAYORIA:
            raise ReglaNegocioError("Todo punto debe clasificarse como mayoría simple o calificada (70 %).")
        with transaccion() as conn:
            _exigir_orden_abierto(_asamblea_bloqueada(conn, asamblea_id))
            puntos = PuntoOrdenDiaDAO(conn)
            puntos.crear(asamblea_id, puntos.siguiente_orden(asamblea_id), descripcion, tipo_mayoria)

    def eliminar_punto(self, punto_id: int) -> int:
        """Elimina el punto y devuelve el id de su asamblea."""
        with transaccion() as conn:
            puntos = PuntoOrdenDiaDAO(conn)
            punto = puntos.obtener(punto_id)
            _exigir_orden_abierto(_asamblea_bloqueada(conn, punto["asamblea_id"]))
            puntos.eliminar(punto_id)
            return punto["asamblea_id"]

    def cerrar_orden_del_dia(self, asamblea_id: int) -> None:
        with transaccion() as conn:
            _asamblea_bloqueada(conn, asamblea_id)
            if not PuntoOrdenDiaDAO(conn).listar_por_asamblea(asamblea_id):
                raise ReglaNegocioError("Registre al menos un punto antes de cerrar el orden del día.")
            AsambleaDAO(conn).cerrar_orden_del_dia(asamblea_id)

    # ------------------------------------------------------------- convocatoria
    @traducir_errores_bd
    def generar_convocatoria(self, asamblea_id: int) -> int:
        """Crea una convocatoria por unidad activa en una sola transacción.

        Devuelve la cantidad de unidades convocadas.
        """
        with transaccion() as conn:
            asamblea = _asamblea_bloqueada(conn, asamblea_id)
            if asamblea["estado"] != "programada":
                raise ReglaNegocioError("Solo se puede convocar una asamblea en estado 'programada'.")
            if not asamblea["orden_del_dia_cerrado"]:
                raise ReglaNegocioError("Cierre el orden del día antes de enviar la convocatoria.")

            # La antelación mínima solo aplica a ordinarias de primera convocatoria.
            es_segunda = asamblea["asamblea_original_id"] is not None
            dias = (asamblea["fecha"] - date.today()).days
            minimo = settings.dias_antelacion_ordinaria
            if asamblea["tipo"] == "ordinaria" and not es_segunda and dias < minimo:
                raise ReglaNegocioError(
                    f"Una asamblea ordinaria debe convocarse con al menos "
                    f"{minimo} días de antelación (faltan {dias})."
                )

            unidades = UnidadDAO(conn).listar_por_conjunto(asamblea["conjunto_id"], solo_activas=True)
            if not unidades:
                raise ReglaNegocioError("El conjunto no tiene unidades activas.")
            convocatorias = ConvocatoriaDAO(conn)
            for u in unidades:
                medio = "email" if u["propietario_email"] else "fisico"
                # Enlace personal de la sala virtual (como el access_token de cada inscrito).
                convocatorias.crear(asamblea_id, u["id"], medio, secrets.token_urlsafe(24))
            AsambleaDAO(conn).cambiar_estado(asamblea_id, "convocada")
            return len(unidades)

    def confirmar_entrega(self, convocatoria_id: int) -> int:
        """Marca la convocatoria como entregada y devuelve el id de la asamblea."""
        with transaccion() as conn:
            dao = ConvocatoriaDAO(conn)
            convocatoria = dao.obtener(convocatoria_id)
            dao.confirmar_entrega(convocatoria_id)
            return convocatoria["asamblea_id"]

    # ---------------------------------------------------- desarrollo de la sesión
    def iniciar(self, asamblea_id: int) -> str:
        """Verifica el quórum (art. 41 y 45) y abre la sesión o la deja 'sin_quorum'.

        Devuelve el mensaje para el usuario.
        """
        with transaccion() as conn:
            asamblea = _asamblea_bloqueada(conn, asamblea_id)
            if asamblea["estado"] != "convocada":
                raise ReglaNegocioError("Solo se puede iniciar una asamblea convocada.")
            asambleas = AsambleaDAO(conn)
            asistencia = AsistenciaDAO(conn)
            conjunto = ConjuntoDAO(conn).obtener(asamblea["conjunto_id"])
            porcentaje = reglas.porcentaje_quorum(asistencia.suma_coeficientes(asamblea_id),
                                                  conjunto["coeficiente_total"])
            asambleas.actualizar_quorum(asamblea_id, porcentaje)

            if asamblea["asamblea_original_id"]:  # segunda convocatoria
                if not reglas.hay_quorum_segunda_convocatoria(asistencia.contar(asamblea_id)):
                    raise ReglaNegocioError("La segunda convocatoria requiere al menos dos unidades presentes.")
                asambleas.cambiar_estado(asamblea_id, "en_curso")
                return f"Sesión de segunda convocatoria iniciada con {porcentaje} % de coeficientes."

            if reglas.hay_quorum_deliberatorio(porcentaje):
                asambleas.cambiar_estado(asamblea_id, "en_curso")
                return f"Quórum verificado ({porcentaje} %). Asamblea en curso."
            asambleas.marcar_requiere_segunda(asamblea_id)
            return (f"No hay quórum deliberatorio ({porcentaje} % ≤ 50 %). "
                    f"La asamblea queda 'sin quórum' y puede programarse la segunda convocatoria.")

    @traducir_errores_bd
    def crear_segunda_convocatoria(self, asamblea_id: int) -> int:
        """Programa la segunda reunión (tercer día hábil, 8:00 p. m.) con el mismo orden del día."""
        with transaccion() as conn:
            original = _asamblea_bloqueada(conn, asamblea_id)
            dao = AsambleaDAO(conn)
            if original["estado"] != "sin_quorum" or not original["requiere_segunda_convocatoria"]:
                raise ReglaNegocioError("Solo aplica a asambleas que no alcanzaron quórum.")
            if dao.segunda_de(asamblea_id):
                raise ReglaNegocioError("La segunda convocatoria ya fue creada.")
            nueva_id = dao.crear(original["conjunto_id"], original["tipo"],
                                 reglas.tercer_dia_habil(original["fecha"]), time(20, 0),
                                 original["lugar_modalidad"], original["modalidad"],
                                 original["enlace_videollamada"], asamblea_original_id=asamblea_id)
            puntos = PuntoOrdenDiaDAO(conn)
            for p in puntos.listar_por_asamblea(asamblea_id):
                puntos.crear(nueva_id, p["orden"], p["descripcion"], p["tipo_mayoria"])
            dao.cerrar_orden_del_dia(nueva_id)
            return nueva_id

    def finalizar(self, asamblea_id: int) -> None:
        """Cierra la sesión; exige que todos los puntos estén votados."""
        with transaccion() as conn:
            asamblea = _asamblea_bloqueada(conn, asamblea_id)
            if asamblea["estado"] != "en_curso":
                raise ReglaNegocioError("Solo se puede finalizar una asamblea en curso.")
            if PuntoOrdenDiaDAO(conn).contar_no_cerrados(asamblea_id):
                raise ReglaNegocioError("Todos los puntos del orden del día deben estar cerrados.")
            AsambleaDAO(conn).cambiar_estado(asamblea_id, "finalizada")
