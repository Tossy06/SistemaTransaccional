from .base_dao import BaseDAO


class PoderDAO(BaseDAO):
    """Poderes otorgados a apoderados para una asamblea."""

    tabla = "poder"

    def crear(self, asamblea_id, unidad_id, apoderado_nombre, apoderado_documento) -> int:
        return self._escalar(
            """INSERT INTO poder (asamblea_id, unidad_id, apoderado_nombre, apoderado_documento)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (asamblea_id, unidad_id, apoderado_nombre, apoderado_documento),
        )

    def vigente_por_documento(self, documento: str) -> dict | None:
        """Poder vigente del apoderado en una asamblea convocada o en curso."""
        return self._uno(
            """SELECT p.* FROM poder p JOIN asamblea a ON a.id = p.asamblea_id
               WHERE p.apoderado_documento = %s AND p.vigente
                 AND a.estado IN ('convocada', 'en_curso')
               ORDER BY p.id DESC LIMIT 1""",
            (documento,),
        )

    def vigente_de_unidad(self, asamblea_id: int, unidad_id: int) -> dict | None:
        return self._uno(
            "SELECT * FROM poder WHERE asamblea_id = %s AND unidad_id = %s AND vigente",
            (asamblea_id, unidad_id),
        )

    def eliminar_de_asamblea(self, asamblea_id: int) -> None:
        self.conn.execute("DELETE FROM poder WHERE asamblea_id = %s", (asamblea_id,))

    def listar_por_asamblea(self, asamblea_id: int) -> list[dict]:
        return self._todos("SELECT * FROM poder WHERE asamblea_id = %s ORDER BY id", (asamblea_id,))
