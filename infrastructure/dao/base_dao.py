"""Clase base del patrón DAO (Data Access Object).

Cada DAO encapsula el SQL de UNA tabla del modelo relacional y recibe la
conexión de la transacción en curso; nunca hace COMMIT por su cuenta.
Todas las consultas son parametrizadas (%s) para evitar inyección SQL.
"""
from typing import Any, Optional

import psycopg


class BaseDAO:
    tabla: str = ""  # nombre de la tabla para obtener() y listar()

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def _uno(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """Primera fila o None."""
        return self.conn.execute(sql, params).fetchone()

    def _todos(self, sql: str, params: tuple = ()) -> list[dict]:
        """Todas las filas."""
        return self.conn.execute(sql, params).fetchall()

    def _escalar(self, sql: str, params: tuple = ()) -> Any:
        """Primera columna de la primera fila (p. ej. RETURNING id o count)."""
        fila = self.conn.execute(sql, params).fetchone()
        return next(iter(fila.values())) if fila else None

    def obtener(self, id_: int, bloquear: bool = False) -> Optional[dict]:
        """Fila por id. bloquear=True aplica FOR UPDATE hasta el fin de la transacción."""
        sufijo = " FOR UPDATE" if bloquear else ""
        return self._uno(f'SELECT * FROM "{self.tabla}" WHERE id = %s{sufijo}', (id_,))

    def listar(self) -> list[dict]:
        return self._todos(f'SELECT * FROM "{self.tabla}" ORDER BY id')
