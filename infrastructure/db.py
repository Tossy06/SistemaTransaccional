"""Gestor de transacciones sobre PostgreSQL.

Cada caso de uso abre una sola transacción y comparte la conexión con todos
los DAO que participan: se confirma todo (COMMIT) o se revierte todo (ROLLBACK).
"""
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg
from psycopg import IsolationLevel
from psycopg.rows import dict_row

from .config import settings


@contextmanager
def transaccion(aislamiento: Optional[IsolationLevel] = None) -> Iterator[psycopg.Connection]:
    """Transacción de escritura. ROLLBACK automático ante cualquier excepción."""
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        if aislamiento is not None:
            conn.isolation_level = aislamiento
        with conn.transaction():
            yield conn
    finally:
        conn.close()


@contextmanager
def solo_lectura() -> Iterator[psycopg.Connection]:
    """Transacción de solo lectura para consultas."""
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        conn.read_only = True
        with conn.transaction():
            yield conn
    finally:
        conn.close()
