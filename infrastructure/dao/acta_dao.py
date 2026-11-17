from .base_dao import BaseDAO


class ActaDAO(BaseDAO):
    """Actas generadas al finalizar una asamblea."""

    tabla = "acta"

    def crear(self, asamblea_id: int, contenido: str, hash_: str) -> int:
        return self._escalar(
            """INSERT INTO acta (asamblea_id, contenido, hash, estado)
               VALUES (%s, %s, %s, 'borrador') RETURNING id""",
            (asamblea_id, contenido, hash_),
        )

    def obtener_por_asamblea(self, asamblea_id: int) -> dict | None:
        return self._uno("SELECT * FROM acta WHERE asamblea_id = %s", (asamblea_id,))

    def marcar_aprobada(self, acta_id: int) -> None:
        self.conn.execute("UPDATE acta SET estado = 'aprobada' WHERE id = %s", (acta_id,))
