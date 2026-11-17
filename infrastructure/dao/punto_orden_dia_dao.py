from .base_dao import BaseDAO


class PuntoOrdenDiaDAO(BaseDAO):
    """Puntos del orden del día y su ciclo de votación."""

    tabla = "punto_orden_dia"

    def listar_por_asamblea(self, asamblea_id: int) -> list[dict]:
        return self._todos(
            "SELECT * FROM punto_orden_dia WHERE asamblea_id = %s ORDER BY orden", (asamblea_id,)
        )

    def obtener_compartido(self, punto_id: int) -> dict | None:
        """Bloqueo compartido: varios votos simultáneos, pero el cierre espera."""
        return self._uno("SELECT * FROM punto_orden_dia WHERE id = %s FOR SHARE", (punto_id,))

    def siguiente_orden(self, asamblea_id: int) -> int:
        """Número consecutivo para un nuevo punto."""
        return self._escalar(
            "SELECT COALESCE(MAX(orden), 0) + 1 FROM punto_orden_dia WHERE asamblea_id = %s",
            (asamblea_id,),
        )

    def crear(self, asamblea_id, orden, descripcion, tipo_mayoria) -> int:
        return self._escalar(
            """INSERT INTO punto_orden_dia (asamblea_id, orden, descripcion, tipo_mayoria, estado)
               VALUES (%s, %s, %s, %s, 'pendiente') RETURNING id""",
            (asamblea_id, orden, descripcion, tipo_mayoria),
        )

    def eliminar_de_asamblea(self, asamblea_id: int) -> None:
        self.conn.execute("DELETE FROM punto_orden_dia WHERE asamblea_id = %s", (asamblea_id,))

    def eliminar(self, punto_id: int) -> None:
        self.conn.execute("DELETE FROM punto_orden_dia WHERE id = %s", (punto_id,))

    def abrir(self, punto_id: int) -> None:
        self.conn.execute(
            "UPDATE punto_orden_dia SET estado = 'abierto', fecha_apertura = now() WHERE id = %s",
            (punto_id,),
        )

    def cerrar(self, punto_id: int) -> None:
        self.conn.execute(
            "UPDATE punto_orden_dia SET estado = 'cerrado', fecha_cierre = now() WHERE id = %s",
            (punto_id,),
        )

    def punto_abierto(self, asamblea_id: int) -> dict | None:
        return self._uno(
            "SELECT * FROM punto_orden_dia WHERE asamblea_id = %s AND estado = 'abierto'",
            (asamblea_id,),
        )

    def contar_no_cerrados(self, asamblea_id: int) -> int:
        return self._escalar(
            "SELECT count(*) FROM punto_orden_dia WHERE asamblea_id = %s AND estado <> 'cerrado'",
            (asamblea_id,),
        )
