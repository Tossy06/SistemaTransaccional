from .base_dao import BaseDAO


class AsambleaDAO(BaseDAO):
    """Asambleas, su estado y el quórum alcanzado."""

    tabla = "asamblea"

    def listar_con_conjunto(self) -> list[dict]:
        """Asambleas con sus indicadores básicos (convocadas, ingresaron, puntos votados)."""
        return self._todos(
            """SELECT a.*, c.nombre AS conjunto_nombre,
                      (SELECT count(*) FROM convocatoria cv WHERE cv.asamblea_id = a.id) AS convocadas,
                      (SELECT count(*) FROM asistencia s WHERE s.asamblea_id = a.id) AS ingresaron,
                      (SELECT count(*) FROM punto_orden_dia p WHERE p.asamblea_id = a.id) AS puntos,
                      (SELECT count(*) FROM punto_orden_dia p WHERE p.asamblea_id = a.id
                         AND p.estado = 'cerrado') AS puntos_cerrados
               FROM asamblea a JOIN conjunto c ON c.id = a.conjunto_id
               ORDER BY a.fecha DESC, a.id DESC"""
        )

    def indicadores(self, asamblea_id: int) -> dict:
        """Totales de la sesión (como los contadores del módulo de asambleas de Odoo)."""
        return self._uno(
            """SELECT
                 (SELECT count(*) FROM unidad u JOIN asamblea a ON a.conjunto_id = u.conjunto_id
                   WHERE a.id = %(id)s AND u.activo) AS unidades,
                 (SELECT count(*) FROM convocatoria WHERE asamblea_id = %(id)s) AS convocadas,
                 (SELECT count(*) FROM convocatoria WHERE asamblea_id = %(id)s AND confirmado_entrega) AS entregadas,
                 (SELECT count(*) FROM asistencia WHERE asamblea_id = %(id)s) AS ingresaron,
                 (SELECT count(*) FROM asistencia WHERE asamblea_id = %(id)s AND tipo_asistencia = 'presencial') AS presenciales,
                 (SELECT count(*) FROM asistencia WHERE asamblea_id = %(id)s AND tipo_asistencia = 'virtual') AS virtuales,
                 (SELECT count(*) FROM asistencia WHERE asamblea_id = %(id)s AND tipo_asistencia = 'poder') AS por_poder,
                 (SELECT count(*) FROM poder WHERE asamblea_id = %(id)s AND vigente) AS poderes,
                 (SELECT count(*) FROM punto_orden_dia WHERE asamblea_id = %(id)s) AS puntos,
                 (SELECT count(*) FROM punto_orden_dia WHERE asamblea_id = %(id)s AND estado = 'cerrado') AS puntos_cerrados,
                 (SELECT count(*) FROM voto v JOIN punto_orden_dia p ON p.id = v.punto_id
                   WHERE p.asamblea_id = %(id)s AND p.estado = 'abierto') AS votos_punto_abierto""",
            {"id": asamblea_id},
        )

    def obtener_detalle(self, asamblea_id: int) -> dict | None:
        return self._uno(
            """SELECT a.*, c.nombre AS conjunto_nombre, c.coeficiente_total
               FROM asamblea a JOIN conjunto c ON c.id = a.conjunto_id
               WHERE a.id = %s""",
            (asamblea_id,),
        )

    def crear(self, conjunto_id, tipo, fecha, hora, lugar, modalidad, enlace,
              asamblea_original_id=None) -> int:
        return self._escalar(
            """INSERT INTO asamblea (conjunto_id, tipo, fecha, hora, lugar_modalidad, modalidad,
                                     enlace_videollamada, estado, asamblea_original_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'programada', %s) RETURNING id""",
            (conjunto_id, tipo, fecha, hora, lugar, modalidad, enlace, asamblea_original_id),
        )

    def actualizar_enlace(self, asamblea_id: int, enlace: str | None) -> None:
        self.conn.execute("UPDATE asamblea SET enlace_videollamada = %s WHERE id = %s",
                          (enlace, asamblea_id))

    def eliminar(self, asamblea_id: int) -> None:
        self.conn.execute("DELETE FROM asamblea WHERE id = %s", (asamblea_id,))

    def reabrir_orden_del_dia(self, asamblea_id: int) -> None:
        self.conn.execute("UPDATE asamblea SET orden_del_dia_cerrado = false WHERE id = %s", (asamblea_id,))

    def cambiar_estado(self, asamblea_id: int, estado: str) -> None:
        self.conn.execute("UPDATE asamblea SET estado = %s WHERE id = %s", (estado, asamblea_id))

    def cerrar_orden_del_dia(self, asamblea_id: int) -> None:
        self.conn.execute(
            "UPDATE asamblea SET orden_del_dia_cerrado = true WHERE id = %s", (asamblea_id,)
        )

    def actualizar_quorum(self, asamblea_id: int, porcentaje) -> None:
        self.conn.execute(
            "UPDATE asamblea SET quorum_alcanzado = %s WHERE id = %s", (porcentaje, asamblea_id)
        )

    def marcar_requiere_segunda(self, asamblea_id: int) -> None:
        """Deja la asamblea sin quórum y habilitada para segunda convocatoria."""
        self.conn.execute(
            """UPDATE asamblea SET requiere_segunda_convocatoria = true, estado = 'sin_quorum'
               WHERE id = %s""",
            (asamblea_id,),
        )

    def segunda_de(self, asamblea_id: int) -> dict | None:
        """Asamblea de segunda convocatoria creada a partir de la indicada."""
        return self._uno("SELECT * FROM asamblea WHERE asamblea_original_id = %s", (asamblea_id,))

    def listar_historico(self) -> list[dict]:
        """Asambleas cerradas (finalizadas o sin quórum) con su acta, si existe."""
        return self._todos(
            """SELECT a.*, c.nombre AS conjunto_nombre, ac.id AS acta_id, ac.estado AS acta_estado
               FROM asamblea a
               JOIN conjunto c ON c.id = a.conjunto_id
               LEFT JOIN acta ac ON ac.asamblea_id = a.id
               WHERE a.estado IN ('finalizada', 'sin_quorum')
               ORDER BY a.fecha DESC"""
        )

    def listar_en_curso(self) -> list[dict]:
        return self._todos(
            """SELECT a.*, c.nombre AS conjunto_nombre FROM asamblea a
               JOIN conjunto c ON c.id = a.conjunto_id
               WHERE a.estado = 'en_curso' ORDER BY a.fecha"""
        )
