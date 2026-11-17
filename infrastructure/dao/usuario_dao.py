from typing import Optional

from .base_dao import BaseDAO


class UsuarioDAO(BaseDAO):
    """Usuarios del sistema."""

    tabla = "usuario"

    def obtener_por_email(self, email: str) -> Optional[dict]:
        """Búsqueda sin distinguir mayúsculas."""
        return self._uno("SELECT * FROM usuario WHERE lower(email) = lower(%s)", (email,))

    def listar_con_roles(self) -> list[dict]:
        return self._todos(
            """SELECT u.id, u.nombre, u.email, u.documento, u.telefono, u.activo,
                      COALESCE(array_agg(r.nombre ORDER BY r.nombre)
                               FILTER (WHERE r.id IS NOT NULL), '{}') AS roles
               FROM usuario u
               LEFT JOIN usuario_rol ur ON ur.usuario_id = u.id
               LEFT JOIN rol r ON r.id = ur.rol_id AND r.activo
               GROUP BY u.id ORDER BY u.nombre"""
        )

    def obtener_por_documento(self, documento: str) -> Optional[dict]:
        return self._uno("SELECT * FROM usuario WHERE documento = %s", (documento,))

    def crear(self, nombre, email, password_hash, documento, telefono) -> int:
        return self._escalar(
            """INSERT INTO usuario (nombre, email, password_hash, documento, telefono)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (nombre, email, password_hash, documento, telefono),
        )

    def actualizar_password(self, usuario_id: int, password_hash: str) -> None:
        self.conn.execute("UPDATE usuario SET password_hash = %s WHERE id = %s",
                          (password_hash, usuario_id))

    def cambiar_activo(self, usuario_id: int, activo: bool) -> None:
        self.conn.execute("UPDATE usuario SET activo = %s WHERE id = %s", (activo, usuario_id))
