from .base_dao import BaseDAO


class ResultadoVotacionDAO(BaseDAO):
    """Resultado inmutable de cada punto votado."""

    tabla = "resultado_votacion"

    def crear(self, punto_id, a_favor, en_contra, abstencion, resultado) -> int:
        return self._escalar(
            """INSERT INTO resultado_votacion (punto_id, total_a_favor, total_en_contra,
                                               total_abstencion, resultado)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (punto_id, a_favor, en_contra, abstencion, resultado),
        )

    def listar_por_asamblea(self, asamblea_id: int) -> list[dict]:
        return self._todos(
            """SELECT r.*, p.orden, p.descripcion, p.tipo_mayoria
               FROM resultado_votacion r JOIN punto_orden_dia p ON p.id = r.punto_id
               WHERE p.asamblea_id = %s ORDER BY p.orden""",
            (asamblea_id,),
        )
