"""Excepciones del dominio."""


class ReglaNegocioError(Exception):
    """Violación de una regla de negocio. El mensaje se muestra al usuario."""
