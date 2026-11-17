from .base_dao import BaseDAO


class VotoDAO(BaseDAO):
    """Votos ponderados por coeficiente."""

    tabla = "voto"

    def crear(self, punto_id, unidad_id, usuario_id, decision, coeficiente) -> int:
        return self._escalar(
            """INSERT INTO voto (punto_id, unidad_id, usuario_id, decision, coeficiente_al_momento)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (punto_id, unidad_id, usuario_id, decision, coeficiente),
        )

    def totales_por_punto(self, punto_id: int) -> dict:
        """Coeficientes sumados por decisión y cantidad de votos."""
        return self._uno(
            """SELECT
                 COALESCE(SUM(coeficiente_al_momento) FILTER (WHERE decision = 'a_favor'), 0)    AS a_favor,
                 COALESCE(SUM(coeficiente_al_momento) FILTER (WHERE decision = 'en_contra'), 0)  AS en_contra,
                 COALESCE(SUM(coeficiente_al_momento) FILTER (WHERE decision = 'abstencion'), 0) AS abstencion,
                 count(*) AS cantidad
               FROM voto WHERE punto_id = %s""",
            (punto_id,),
        )

    def unidades_que_votaron(self, punto_id: int) -> set[int]:
        return {f["unidad_id"] for f in self._todos("SELECT unidad_id FROM voto WHERE punto_id = %s", (punto_id,))}

    def contar(self, punto_id: int) -> int:
        """Unidades que ya votaron el punto (para la participación en vivo)."""
        return self._escalar("SELECT count(*) FROM voto WHERE punto_id = %s", (punto_id,))
