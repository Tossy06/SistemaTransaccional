"""Reglas de quórum, mayorías y plazos de la Ley 675 de 2001."""
from datetime import date, timedelta
from decimal import Decimal

CIEN = Decimal("100")


def porcentaje_quorum(coef_presente: Decimal, coef_total: Decimal) -> Decimal:
    """Porcentaje de coeficientes presentes, redondeado a dos decimales."""
    if not coef_total:
        return Decimal("0")
    return (Decimal(coef_presente) * CIEN / Decimal(coef_total)).quantize(Decimal("0.01"))


def hay_quorum_deliberatorio(porcentaje: Decimal) -> bool:
    """Art. 45: más de la mitad de los coeficientes de copropiedad."""
    return porcentaje > Decimal("50")


def hay_quorum_segunda_convocatoria(unidades_presentes: int) -> bool:
    """Art. 41: la segunda convocatoria sesiona con cualquier número plural."""
    return unidades_presentes >= 2


def resultado_votacion(tipo_mayoria: str, a_favor: Decimal, coef_presente: Decimal,
                       coef_total: Decimal) -> str:
    """Devuelve 'aprobado' o 'rechazado'.

    Simple (art. 45): más de la mitad de los coeficientes presentes.
    Calificada (art. 46): 70 % de los coeficientes del conjunto.
    """
    if tipo_mayoria == "calificada_70":
        aprobado = Decimal(a_favor) >= Decimal(coef_total) * Decimal("0.70")
    else:
        aprobado = Decimal(a_favor) > Decimal(coef_presente) / 2
    return "aprobado" if aprobado else "rechazado"


def tercer_dia_habil(desde: date) -> date:
    """Fecha de la segunda convocatoria (art. 41). No contempla festivos."""
    dia, habiles = desde, 0
    while habiles < 3:
        dia += timedelta(days=1)
        if dia.weekday() < 5:
            habiles += 1
    return dia
