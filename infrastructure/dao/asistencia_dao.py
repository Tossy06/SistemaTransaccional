from decimal import Decimal

from .base_dao import BaseDAO


class AsistenciaDAO(BaseDAO):
    """Asistencia de unidades: presencial, virtual (sala web) o por poder."""

    tabla = "asistencia"

    def crear(self, asamblea_id, unidad_id, poder_id, tipo, coeficiente) -> int:
        return self._escalar(
            """INSERT INTO asistencia (asamblea_id, unidad_id, poder_id, tipo_asistencia,
                                       coeficiente_al_momento)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (asamblea_id, unidad_id, poder_id, tipo, coeficiente),
        )

    def listar_por_asamblea(self, asamblea_id: int) -> list[dict]:
        return self._todos(
            """SELECT a.*, u.identificador, u.propietario_nombre,
                      p.apoderado_nombre, p.apoderado_documento
               FROM asistencia a
               JOIN unidad u ON u.id = a.unidad_id
               LEFT JOIN poder p ON p.id = a.poder_id
               WHERE a.asamblea_id = %s ORDER BY a.hora_registro""",
            (asamblea_id,),
        )

    def de_unidad(self, asamblea_id: int, unidad_id: int) -> dict | None:
        return self._uno("SELECT * FROM asistencia WHERE asamblea_id = %s AND unidad_id = %s",
                         (asamblea_id, unidad_id))

    def suma_coeficientes(self, asamblea_id: int) -> Decimal:
        """Coeficiente presente según el valor congelado al registrar la asistencia."""
        return self._escalar(
            "SELECT COALESCE(SUM(coeficiente_al_momento), 0) FROM asistencia WHERE asamblea_id = %s",
            (asamblea_id,),
        )

    def contar(self, asamblea_id: int) -> int:
        return self._escalar("SELECT count(*) FROM asistencia WHERE asamblea_id = %s", (asamblea_id,))
