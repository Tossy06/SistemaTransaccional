"""Hash de contraseñas (bcrypt) y bloqueo de cuentas por intentos fallidos."""
import secrets
import threading
from datetime import datetime, timedelta

import bcrypt

from .config import settings

BCRYPT_COSTO = 12


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(BCRYPT_COSTO)).decode()


def verificar_password(password: str, password_hash: str) -> bool:
    """False también si el hash guardado no tiene formato bcrypt."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# Se compara contra este hash cuando el correo no existe, para que el tiempo
# de respuesta no revele qué cuentas están registradas.
HASH_FICTICIO = hash_password(secrets.token_hex(8))


class LimitadorIntentos:
    """Bloquea una cuenta durante `minutos` tras `maximo` fallos seguidos.

    Estado en memoria del proceso; protegido con lock para peticiones concurrentes.
    """

    def __init__(self, maximo: int, minutos: int):
        self.maximo, self.minutos = maximo, minutos
        self._fallos: dict[str, tuple[int, datetime | None]] = {}  # clave -> (fallos, bloqueado_hasta)
        self._lock = threading.Lock()

    def esta_bloqueado(self, clave: str) -> bool:
        with self._lock:
            _, hasta = self._fallos.get(clave, (0, None))
            if hasta and hasta > datetime.now():
                return True
            if hasta:  # bloqueo vencido: se reinicia el contador
                self._fallos.pop(clave, None)
            return False

    def registrar_fallo(self, clave: str) -> None:
        with self._lock:
            n, _ = self._fallos.get(clave, (0, None))
            n += 1
            hasta = datetime.now() + timedelta(minutes=self.minutos) if n >= self.maximo else None
            self._fallos[clave] = (n, hasta)

    def limpiar(self, clave: str) -> None:
        with self._lock:
            self._fallos.pop(clave, None)


limitador = LimitadorIntentos(settings.max_intentos_login, settings.minutos_bloqueo)
