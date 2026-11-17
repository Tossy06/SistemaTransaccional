"""RF-06: apertura, votación ponderada y cierre de puntos."""
from domain import reglas
from domain.catalogos import DECISIONES_VOTO
from domain.excepciones import ReglaNegocioError
from infrastructure.dao import (AsambleaDAO, AsistenciaDAO, ConjuntoDAO, PuntoOrdenDiaDAO,
                                ResultadoVotacionDAO, UnidadDAO, VotoDAO)
from infrastructure.db import solo_lectura, transaccion
from infrastructure.errores_bd import traducir_errores_bd


class VotacionService:
    @traducir_errores_bd
    def abrir_punto(self, punto_id: int) -> int:
        """Abre la votación de un punto pendiente. Solo un punto abierto por asamblea.

        Devuelve el id de la asamblea.
        """
        with transaccion() as conn:
            puntos = PuntoOrdenDiaDAO(conn)
            punto = puntos.obtener(punto_id, bloquear=True)
            asamblea = AsambleaDAO(conn).obtener(punto["asamblea_id"], bloquear=True)
            if asamblea["estado"] != "en_curso":
                raise ReglaNegocioError("La asamblea debe estar en curso para abrir votaciones.")
            if punto["estado"] != "pendiente":
                raise ReglaNegocioError("El punto ya fue votado o está abierto.")
            if puntos.punto_abierto(asamblea["id"]):
                raise ReglaNegocioError("Ya hay otro punto en votación. Ciérrelo antes de abrir uno nuevo.")
            puntos.abrir(punto_id)
            return asamblea["id"]

    def panel_votante(self, usuario: dict) -> list[dict]:
        """Asambleas en curso donde el usuario representa unidades, con el punto abierto."""
        with solo_lectura() as conn:
            salida = []
            for a in AsambleaDAO(conn).listar_en_curso():
                unidades = UnidadDAO(conn).unidades_habilitadas_para_votar(a["id"], usuario["documento"])
                if not unidades:
                    continue
                punto = PuntoOrdenDiaDAO(conn).punto_abierto(a["id"])
                votaron = VotoDAO(conn).unidades_que_votaron(punto["id"]) if punto else set()
                for u in unidades:
                    u["ya_voto"] = u["id"] in votaron
                salida.append({"asamblea": a, "punto": punto, "unidades": unidades})
            return salida

    @traducir_errores_bd
    def votar(self, punto_id: int, unidad_id: int, usuario: dict, decision: str) -> None:
        """Registra el voto de una unidad que el usuario representa.

        FOR SHARE sobre el punto permite votos simultáneos pero bloquea el cierre
        hasta que terminen. El doble voto lo impide un índice único en la BD.
        """
        if decision not in DECISIONES_VOTO:
            raise ReglaNegocioError("Decisión inválida.")
        with transaccion() as conn:
            punto = PuntoOrdenDiaDAO(conn).obtener_compartido(punto_id)
            if not punto or punto["estado"] != "abierto":
                raise ReglaNegocioError("La votación de este punto no está abierta.")
            habilitadas = {u["id"]: u for u in UnidadDAO(conn).unidades_habilitadas_para_votar(
                punto["asamblea_id"], usuario["documento"])}
            if unidad_id not in habilitadas:
                raise ReglaNegocioError("No está habilitado para votar por esta unidad.")
            # Se pondera con el coeficiente congelado al registrar la asistencia.
            VotoDAO(conn).crear(punto_id, unidad_id, usuario["id"], decision,
                                habilitadas[unidad_id]["coeficiente_al_momento"])

    @traducir_errores_bd
    def votar_unidad(self, punto_id: int, unidad_id: int, usuario_id: int | None, decision: str) -> None:
        """Voto desde la sala virtual: el enlace único identifica la unidad. Mismo FOR SHARE e índice
        único que el voto con sesión; se guarda el usuario del representante si tiene cuenta."""
        if decision not in DECISIONES_VOTO:
            raise ReglaNegocioError("Decisión inválida.")
        with transaccion() as conn:
            punto = PuntoOrdenDiaDAO(conn).obtener_compartido(punto_id)
            if not punto or punto["estado"] != "abierto":
                raise ReglaNegocioError("La votación de este punto no está abierta.")
            asistencia = AsistenciaDAO(conn).de_unidad(punto["asamblea_id"], unidad_id)
            if not asistencia:
                raise ReglaNegocioError("Confirme su ingreso a la sala antes de votar.")
            VotoDAO(conn).crear(punto_id, unidad_id, usuario_id, decision, asistencia["coeficiente_al_momento"])

    @traducir_errores_bd
    def cerrar_punto(self, punto_id: int) -> dict:
        """Cierra la votación y persiste el resultado.

        FOR UPDATE espera a los votos en curso (FOR SHARE). Tras el cierre, los
        triggers de la BD impiden modificar votos y resultados.
        """
        with transaccion() as conn:
            puntos = PuntoOrdenDiaDAO(conn)
            punto = puntos.obtener(punto_id, bloquear=True)
            if punto["estado"] != "abierto":
                raise ReglaNegocioError("Solo se puede cerrar un punto abierto.")
            asamblea = AsambleaDAO(conn).obtener(punto["asamblea_id"])
            conjunto = ConjuntoDAO(conn).obtener(asamblea["conjunto_id"])
            totales = VotoDAO(conn).totales_por_punto(punto_id)
            presente = AsistenciaDAO(conn).suma_coeficientes(asamblea["id"])
            resultado = reglas.resultado_votacion(punto["tipo_mayoria"], totales["a_favor"], presente,
                                                  conjunto["coeficiente_total"])
            ResultadoVotacionDAO(conn).crear(punto_id, totales["a_favor"], totales["en_contra"],
                                             totales["abstencion"], resultado)
            puntos.cerrar(punto_id)
            return {"asamblea_id": asamblea["id"], "resultado": resultado, **totales}
