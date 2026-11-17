"""RF-01: administración de usuarios y roles."""
from domain.excepciones import ReglaNegocioError
from domain.validaciones import validar_politica_password
from infrastructure.dao import RolDAO, UsuarioDAO
from infrastructure.db import solo_lectura, transaccion
from infrastructure.errores_bd import traducir_errores_bd
from infrastructure.seguridad import hash_password


class UsuarioService:
    def listar(self) -> tuple[list[dict], list[dict]]:
        """Usuarios con sus roles y catálogo de roles activos."""
        with solo_lectura() as conn:
            return UsuarioDAO(conn).listar_con_roles(), RolDAO(conn).listar_activos()

    @traducir_errores_bd
    def crear(self, nombre, email, password, documento, telefono, roles_ids: list[int]) -> int:
        """Crea el usuario y asigna sus roles en una sola transacción."""
        if not (nombre and email and documento):
            raise ReglaNegocioError("Nombre, correo y documento son obligatorios.")
        if not roles_ids:
            raise ReglaNegocioError("Asigne al menos un rol al usuario.")
        validar_politica_password(password)
        with transaccion() as conn:
            usuario_id = UsuarioDAO(conn).crear(nombre, email.lower(), hash_password(password),
                                                documento, telefono)
            RolDAO(conn).asignar_roles(usuario_id, roles_ids)
            return usuario_id

    @traducir_errores_bd
    def actualizar_roles(self, usuario_id: int, roles_ids: list[int]) -> None:
        if not roles_ids:
            raise ReglaNegocioError("El usuario debe conservar al menos un rol.")
        with transaccion() as conn:
            RolDAO(conn).asignar_roles(usuario_id, roles_ids)

    def restablecer_password(self, usuario_id: int, password: str) -> None:
        """La administración asigna una contraseña nueva (recuperación de acceso)."""
        validar_politica_password(password)
        with transaccion() as conn:
            dao = UsuarioDAO(conn)
            if not dao.obtener(usuario_id, bloquear=True):
                raise ReglaNegocioError("El usuario no existe.")
            dao.actualizar_password(usuario_id, hash_password(password))

    def cambiar_activo(self, usuario_id: int, activo: bool, usuario_sesion_id: int) -> None:
        """Activa o desactiva un usuario. Nadie puede desactivarse a sí mismo."""
        if usuario_id == usuario_sesion_id and not activo:
            raise ReglaNegocioError("No puede desactivar su propio usuario.")
        with transaccion() as conn:
            UsuarioDAO(conn).cambiar_activo(usuario_id, activo)
