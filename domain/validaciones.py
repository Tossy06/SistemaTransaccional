"""Validaciones de datos de entrada independientes de la persistencia."""
import re
from decimal import Decimal, InvalidOperation

from .excepciones import ReglaNegocioError

# Mínimo 8 caracteres, al menos una letra y un dígito.
_REGLA_PASSWORD = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def validar_politica_password(password: str) -> None:
    """Exige la política mínima de contraseñas."""
    if not _REGLA_PASSWORD.match(password or ""):
        raise ReglaNegocioError(
            "La contraseña debe tener mínimo 8 caracteres e incluir letras y números."
        )


def a_decimal_positivo(valor, campo: str) -> Decimal:
    """Convierte a Decimal (acepta coma decimal) y exige valor mayor que cero."""
    try:
        numero = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ReglaNegocioError(f"El campo {campo} debe ser numérico.")
    if numero <= 0:
        raise ReglaNegocioError(f"El campo {campo} debe ser mayor que cero.")
    return numero
