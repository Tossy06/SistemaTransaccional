"""Traducción de errores de PostgreSQL a errores de negocio legibles."""
from functools import wraps

from psycopg import errors

from domain.excepciones import ReglaNegocioError

# Nombre de restricción única -> mensaje para el usuario.
MENSAJES_UNICIDAD = {
    "poder_asamblea_id_unidad_id_idx": "La unidad ya tiene un poder registrado en esta asamblea (solo se permite uno por unidad).",
    "asistencia_asamblea_id_unidad_id_idx": "La asistencia de esta unidad ya fue registrada.",
    "voto_punto_id_unidad_id_idx": "Esta unidad ya votó en este punto.",
    "uq_un_punto_abierto": "Ya hay otro punto en votación. Ciérrelo antes de abrir uno nuevo.",
    "usuario_email_key": "Ya existe un usuario con ese correo.",
    "usuario_documento_key": "Ya existe un usuario con ese documento.",
    "conjunto_nit_key": "Ya existe un conjunto con ese NIT.",
    "uq_solicitud_pendiente": "Esta unidad ya tiene una solicitud pendiente de revisión. La administración "
                              "debe revisarla antes de recibir otra.",
    "uq_unidad_identificador": "Ya existe una unidad con ese identificador en el conjunto.",
    "uq_convocatoria_unidad": "La convocatoria ya fue generada para esta asamblea.",
    "uq_acta_asamblea": "El acta de esta asamblea ya fue generada.",
    "uq_acta_aprobacion_rol": "El acta ya tiene la aprobación de ese rol.",
    "uq_resultado_punto": "El resultado de este punto ya fue calculado.",
}


def traducir_errores_bd(funcion):
    """Decorador: convierte violaciones de restricciones y triggers en ReglaNegocioError."""
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        try:
            return funcion(*args, **kwargs)
        except errors.UniqueViolation as e:
            restriccion = e.diag.constraint_name or ""
            raise ReglaNegocioError(MENSAJES_UNICIDAD.get(restriccion, "Registro duplicado.")) from e
        except errors.RaiseException as e:  # RAISE EXCEPTION desde un trigger
            raise ReglaNegocioError(e.diag.message_primary) from e
        except (errors.CheckViolation, errors.InvalidTextRepresentation,
                errors.NumericValueOutOfRange, errors.InvalidDatetimeFormat) as e:
            raise ReglaNegocioError("Datos inválidos: revise los valores ingresados.") from e

    return envoltura
