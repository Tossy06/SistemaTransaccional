from .base_dao import BaseDAO


class SolicitudCensoDAO(BaseDAO):
    """Solicitudes del formulario público de registro de propietarios."""

    tabla = "solicitud_censo"

    def crear(self, unidad_id, nombre, documento, email, telefono, autoriza_datos) -> int:
        return self._escalar(
            """INSERT INTO solicitud_censo (unidad_id, nombre, documento, email, telefono, autoriza_datos)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (unidad_id, nombre, documento, email, telefono, autoriza_datos),
        )

    def listar_por_conjunto(self, conjunto_id: int) -> list[dict]:
        """Pendientes primero; cada una con los datos que hoy tiene la unidad en el censo."""
        return self._todos(
            """SELECT s.*, u.identificador, u.propietario_nombre, u.propietario_documento,
                      u.propietario_email, rev.nombre AS revisor
               FROM solicitud_censo s
               JOIN unidad u ON u.id = s.unidad_id
               LEFT JOIN usuario rev ON rev.id = s.revisado_por
               WHERE u.conjunto_id = %s
               ORDER BY s.estado <> 'pendiente', s.fecha_envio DESC""",
            (conjunto_id,),
        )

    def contar_pendientes(self, conjunto_id: int) -> int:
        return self._escalar(
            """SELECT count(*) FROM solicitud_censo s JOIN unidad u ON u.id = s.unidad_id
               WHERE u.conjunto_id = %s AND s.estado = 'pendiente'""",
            (conjunto_id,),
        )

    def aprobar(self, solicitud_id: int, usuario_id: int) -> None:
        self.conn.execute(
            """UPDATE solicitud_censo SET estado = 'aprobada', revisado_por = %s, fecha_revision = now()
               WHERE id = %s""",
            (usuario_id, solicitud_id),
        )

    def rechazar(self, solicitud_id: int, usuario_id: int, motivo: str) -> None:
        self.conn.execute(
            """UPDATE solicitud_censo SET estado = 'rechazada', revisado_por = %s, fecha_revision = now(),
                      motivo_rechazo = %s
               WHERE id = %s""",
            (usuario_id, motivo, solicitud_id),
        )
