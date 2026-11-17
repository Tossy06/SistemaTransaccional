from .base_dao import BaseDAO


class ActaAprobacionDAO(BaseDAO):
    """Firmas de aprobación del acta (presidente y secretario)."""

    tabla = "acta_aprobacion"

    def crear(self, acta_id: int, usuario_id: int, rol: str) -> int:
        return self._escalar(
            """INSERT INTO acta_aprobacion (acta_id, usuario_id, rol_en_aprobacion)
               VALUES (%s, %s, %s) RETURNING id""",
            (acta_id, usuario_id, rol),
        )

    def listar_por_acta(self, acta_id: int) -> list[dict]:
        return self._todos(
            """SELECT ap.*, u.nombre FROM acta_aprobacion ap JOIN usuario u ON u.id = ap.usuario_id
               WHERE ap.acta_id = %s ORDER BY ap.fecha""",
            (acta_id,),
        )
