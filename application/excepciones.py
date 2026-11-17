"""Excepciones de autenticación y autorización."""


class NoAutenticado(Exception):
    """No hay sesión activa."""


class NoAutorizado(Exception):
    """El usuario no tiene permiso para la operación."""
