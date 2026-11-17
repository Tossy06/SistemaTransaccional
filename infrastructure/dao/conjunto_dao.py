from .base_dao import BaseDAO


class ConjuntoDAO(BaseDAO):
    """Conjuntos residenciales."""

    tabla = "conjunto"

    def crear(self, nombre, nit, direccion, ciudad, numero_unidades, coeficiente_total) -> int:
        return self._escalar(
            """INSERT INTO conjunto (nombre, nit, direccion, ciudad, numero_unidades, coeficiente_total)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (nombre, nit, direccion, ciudad, numero_unidades, coeficiente_total),
        )

    def obtener_por_token(self, token: str) -> dict | None:
        """Conjunto activo cuyo formulario público está abierto con ese enlace."""
        return self._uno("SELECT * FROM conjunto WHERE formulario_token = %s AND activo", (token,))

    def cambiar_token(self, conjunto_id: int, token: str | None) -> None:
        self.conn.execute("UPDATE conjunto SET formulario_token = %s WHERE id = %s", (token, conjunto_id))

    def listar_activos(self) -> list[dict]:
        return self._todos("SELECT * FROM conjunto WHERE activo ORDER BY nombre")
