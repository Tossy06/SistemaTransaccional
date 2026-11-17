from .base_dao import BaseDAO


class ConvocatoriaDAO(BaseDAO):
    """Convocatorias enviadas a cada unidad."""

    tabla = "convocatoria"

    def crear(self, asamblea_id: int, unidad_id: int, medio: str, token_acceso: str) -> int:
        return self._escalar(
            """INSERT INTO convocatoria (asamblea_id, unidad_id, medio, token_acceso)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (asamblea_id, unidad_id, medio, token_acceso),
        )

    def renovar_token(self, asamblea_id: int, unidad_id: int, token: str) -> None:
        """Nuevo enlace para la unidad: el anterior deja de funcionar."""
        self.conn.execute("UPDATE convocatoria SET token_acceso = %s WHERE asamblea_id = %s AND unidad_id = %s",
                          (token, asamblea_id, unidad_id))

    def eliminar_de_asamblea(self, asamblea_id: int) -> None:
        self.conn.execute("DELETE FROM convocatoria WHERE asamblea_id = %s", (asamblea_id,))

    def obtener_por_token(self, token: str) -> dict | None:
        """Convocatoria del enlace de la sala, con su unidad y su asamblea."""
        return self._uno(
            """SELECT cv.id, cv.asamblea_id, cv.unidad_id, cv.token_acceso,
                      u.identificador, u.propietario_nombre, u.propietario_documento,
                      u.coeficiente_copropiedad, u.activo AS unidad_activa
               FROM convocatoria cv JOIN unidad u ON u.id = cv.unidad_id
               WHERE cv.token_acceso = %s""",
            (token,),
        )

    def salas_de(self, documento: str) -> list[dict]:
        """Enlaces de sala de las unidades que el documento representa (propietario o
        apoderado con poder vigente) en asambleas no presenciales convocadas o en curso."""
        return self._todos(
            """SELECT cv.token_acceso, u.identificador, a.id AS asamblea_id, a.fecha, a.hora,
                      a.estado, a.modalidad, c.nombre AS conjunto_nombre,
                      CASE WHEN u.propietario_documento = %s THEN 'propietario' ELSE 'apoderado' END AS calidad
               FROM convocatoria cv
               JOIN unidad u ON u.id = cv.unidad_id
               JOIN asamblea a ON a.id = cv.asamblea_id
               JOIN conjunto c ON c.id = a.conjunto_id
               WHERE a.estado IN ('convocada', 'en_curso') AND a.modalidad <> 'presencial'
                 AND (u.propietario_documento = %s OR EXISTS (
                      SELECT 1 FROM poder p WHERE p.asamblea_id = a.id AND p.unidad_id = u.id
                        AND p.vigente AND p.apoderado_documento = %s))
               ORDER BY a.fecha, u.identificador""",
            (documento, documento, documento),
        )

    def listar_por_asamblea(self, asamblea_id: int) -> list[dict]:
        return self._todos(
            """SELECT cv.*, u.identificador, u.propietario_nombre, u.propietario_email
               FROM convocatoria cv JOIN unidad u ON u.id = cv.unidad_id
               WHERE cv.asamblea_id = %s ORDER BY u.identificador""",
            (asamblea_id,),
        )

    def confirmar_entrega(self, convocatoria_id: int) -> None:
        self.conn.execute(
            "UPDATE convocatoria SET confirmado_entrega = true WHERE id = %s", (convocatoria_id,)
        )
