from .base_dao import BaseDAO


class RolDAO(BaseDAO):
    """Acceso a las tablas rol y usuario_rol (relación N:M)."""

    tabla = "rol"

    def listar_activos(self) -> list[dict]:
        return self._todos("SELECT * FROM rol WHERE activo ORDER BY id")

    def id_por_nombre(self, nombre: str) -> int:
        return self._escalar("SELECT id FROM rol WHERE nombre = %s AND activo", (nombre,))

    def roles_de_usuario(self, usuario_id: int) -> list[str]:
        filas = self._todos(
            """SELECT r.nombre FROM usuario_rol ur JOIN rol r ON r.id = ur.rol_id
               WHERE ur.usuario_id = %s AND r.activo ORDER BY r.nombre""",
            (usuario_id,),
        )
        return [f["nombre"] for f in filas]

    def asignar_roles(self, usuario_id: int, roles_ids: list[int]) -> None:
        """Reemplaza todos los roles del usuario por los indicados."""
        self.conn.execute("DELETE FROM usuario_rol WHERE usuario_id = %s", (usuario_id,))
        for rol_id in roles_ids:
            self.conn.execute(
                "INSERT INTO usuario_rol (usuario_id, rol_id) VALUES (%s, %s)",
                (usuario_id, rol_id),
            )
