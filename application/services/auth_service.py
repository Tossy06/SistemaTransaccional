"""RF-01: autenticación de usuarios."""
import re

from domain.excepciones import ReglaNegocioError
from domain.validaciones import validar_politica_password
from infrastructure.dao import PoderDAO, RolDAO, UnidadDAO, UsuarioDAO
from infrastructure.db import solo_lectura, transaccion
from infrastructure.errores_bd import traducir_errores_bd
from infrastructure.seguridad import HASH_FICTICIO, hash_password, limitador, verificar_password



_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthService:
    # Mismo mensaje para correo inexistente y contraseña errada.
    MENSAJE_GENERICO = "Correo o contraseña incorrectos."
    MENSAJE_ACTIVACION = ("Los datos no coinciden con el registro de propietarios ni con un poder "
                          "vigente. Verifique el documento y el correo, o acuda a la administración.")

    def autenticar(self, email: str, password: str) -> dict:
        """Valida credenciales y devuelve los datos de sesión del usuario."""
        clave = (email or "").lower()
        if limitador.esta_bloqueado(clave):
            raise ReglaNegocioError(
                f"Cuenta bloqueada temporalmente por intentos fallidos. "
                f"Intente de nuevo en {limitador.minutos} minutos."
            )
        with solo_lectura() as conn:
            usuario = UsuarioDAO(conn).obtener_por_email(clave)
            roles = RolDAO(conn).roles_de_usuario(usuario["id"]) if usuario else []

        # bcrypt se ejecuta siempre para que el tiempo no revele si el correo existe.
        valido = verificar_password(password or "", usuario["password_hash"] if usuario else HASH_FICTICIO)
        if not (usuario and valido and usuario["activo"] and roles):
            limitador.registrar_fallo(clave)
            raise ReglaNegocioError(self.MENSAJE_GENERICO)

        limitador.limpiar(clave)
        return {
            "id": usuario["id"],
            "nombre": usuario["nombre"],
            "email": usuario["email"],
            "documento": usuario["documento"],
            "roles": roles,
        }

    @traducir_errores_bd
    def activar_cuenta(self, documento, email, password, confirmacion) -> None:
        """Primer ingreso: la persona crea su contraseña a partir de datos que la
        administración ya registró; no existe registro abierto.

        - Propietario: documento y correo deben coincidir con los de una unidad
          activa del censo (carga individual o masiva). Recibe el rol copropietario.
        - Apoderado: su documento debe figurar en un poder vigente de una asamblea
          convocada o en curso; la recepción verificó su identidad al registrar
          el poder. Recibe el rol apoderado.
        Cualquier otro caso recibe el mismo mensaje, para no revelar qué datos existen.
        """
        documento = (documento or "").strip()
        email = (email or "").strip().lower()
        if not (documento and email):
            raise ReglaNegocioError("Documento y correo son obligatorios.")
        if not _EMAIL.match(email):
            raise ReglaNegocioError("Escriba un correo electrónico válido.")
        if password != confirmacion:
            raise ReglaNegocioError("Las dos contraseñas no coinciden.")
        validar_politica_password(password)
        clave = f"activar:{documento}"
        if limitador.esta_bloqueado(clave):
            raise ReglaNegocioError(
                f"Demasiados intentos. Intente de nuevo en {limitador.minutos} minutos.")

        with transaccion() as conn:
            usuarios = UsuarioDAO(conn)
            if usuarios.obtener_por_documento(documento):
                raise ReglaNegocioError(
                    "Ya existe una cuenta con ese documento. Inicie sesión o pida a la "
                    "administración que restablezca su contraseña.")
            unidades = UnidadDAO(conn).activas_por_documento(documento)
            propias = [u for u in unidades if (u["propietario_email"] or "").lower() == email]
            poder = None if unidades else PoderDAO(conn).vigente_por_documento(documento)
            if propias:
                nombre, rol = propias[0]["propietario_nombre"], "copropietario"
            elif poder:
                nombre, rol = poder["apoderado_nombre"], "apoderado"
            else:
                limitador.registrar_fallo(clave)
                raise ReglaNegocioError(self.MENSAJE_ACTIVACION)
            usuario_id = usuarios.crear(nombre, email, hash_password(password), documento, None)
            roles = RolDAO(conn)
            roles.asignar_roles(usuario_id, [roles.id_por_nombre(rol)])
        limitador.limpiar(clave)

    def cambiar_password(self, usuario_id: int, actual: str, nueva: str, confirmacion: str) -> None:
        """Exige la contraseña actual; la nueva debe cumplir la política y ser distinta."""
        if nueva != confirmacion:
            raise ReglaNegocioError("Las dos contraseñas nuevas no coinciden.")
        validar_politica_password(nueva)
        with transaccion() as conn:
            dao = UsuarioDAO(conn)
            usuario = dao.obtener(usuario_id, bloquear=True)
            if not usuario or not verificar_password(actual or "", usuario["password_hash"]):
                raise ReglaNegocioError("La contraseña actual no es correcta.")
            if verificar_password(nueva, usuario["password_hash"]):
                raise ReglaNegocioError("La contraseña nueva debe ser distinta de la actual.")
            dao.actualizar_password(usuario_id, hash_password(nueva))
