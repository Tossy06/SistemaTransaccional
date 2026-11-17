from decimal import Decimal

from .base_dao import BaseDAO


class UnidadDAO(BaseDAO):
    """Unidades privadas y su coeficiente de copropiedad."""

    tabla = "unidad"

    def listar_por_conjunto(self, conjunto_id: int, solo_activas: bool = False) -> list[dict]:
        filtro = " AND activo" if solo_activas else ""
        return self._todos(
            f"SELECT * FROM unidad WHERE conjunto_id = %s{filtro} ORDER BY identificador",
            (conjunto_id,),
        )

    def crear(self, conjunto_id, identificador, nombre, documento, email, telefono, coeficiente) -> int:
        return self._escalar(
            """INSERT INTO unidad (conjunto_id, identificador, propietario_nombre,
                   propietario_documento, propietario_email, propietario_telefono,
                   coeficiente_copropiedad)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (conjunto_id, identificador, nombre, documento, email, telefono, coeficiente),
        )

    def activas_por_documento(self, documento: str) -> list[dict]:
        """Unidades activas cuyo propietario tiene ese documento."""
        return self._todos(
            "SELECT * FROM unidad WHERE propietario_documento = %s AND activo ORDER BY identificador",
            (documento,),
        )

    def identificadores(self, conjunto_id: int) -> set[str]:
        """Identificadores ya usados en el conjunto (en minúsculas)."""
        filas = self._todos("SELECT lower(identificador) AS i FROM unidad WHERE conjunto_id = %s",
                            (conjunto_id,))
        return {f["i"] for f in filas}

    def actualizar_propietario(self, unidad_id: int, nombre, documento, email, telefono) -> None:
        self.conn.execute(
            """UPDATE unidad SET propietario_nombre = %s, propietario_documento = %s,
                      propietario_email = %s, propietario_telefono = %s
               WHERE id = %s""",
            (nombre, documento, email, telefono, unidad_id),
        )

    def participantes(self, asamblea_id: int) -> list[dict]:
        """Cada unidad activa del conjunto con su convocatoria (enlace a la sala), cuenta de acceso,
        asistencia, poder y voto en el punto abierto: la vista de participantes de la asamblea."""
        return self._todos(
            """SELECT u.id, u.identificador, u.propietario_nombre, u.propietario_documento,
                      u.propietario_email, u.coeficiente_copropiedad,
                      cv.id AS convocatoria_id, cv.token_acceso, cv.medio, cv.confirmado_entrega,
                      a.tipo_asistencia, a.hora_registro,
                      p.apoderado_nombre, p.apoderado_documento,
                      uo.email AS cuenta_propietario, uo.activo AS cuenta_propietario_activa,
                      ua.email AS cuenta_apoderado,
                      v.decision AS voto_punto_abierto
               FROM asamblea s
               JOIN unidad u ON u.conjunto_id = s.conjunto_id AND u.activo
               LEFT JOIN convocatoria cv ON cv.asamblea_id = s.id AND cv.unidad_id = u.id
               LEFT JOIN asistencia a ON a.asamblea_id = s.id AND a.unidad_id = u.id
               LEFT JOIN poder p ON p.asamblea_id = s.id AND p.unidad_id = u.id AND p.vigente
               LEFT JOIN usuario uo ON uo.documento = u.propietario_documento
               LEFT JOIN usuario ua ON ua.documento = p.apoderado_documento
               LEFT JOIN punto_orden_dia po ON po.asamblea_id = s.id AND po.estado = 'abierto'
               LEFT JOIN voto v ON v.punto_id = po.id AND v.unidad_id = u.id
               WHERE s.id = %s
               ORDER BY u.identificador""",
            (asamblea_id,),
        )

    def cambiar_activo(self, unidad_id: int, activo: bool) -> None:
        self.conn.execute("UPDATE unidad SET activo = %s WHERE id = %s", (activo, unidad_id))

    def suma_coeficientes(self, conjunto_id: int) -> Decimal:
        """Suma de coeficientes de las unidades activas del conjunto."""
        return self._escalar(
            "SELECT COALESCE(SUM(coeficiente_copropiedad), 0) FROM unidad WHERE conjunto_id = %s AND activo",
            (conjunto_id,),
        )

    def unidades_habilitadas_para_votar(self, asamblea_id: int, documento: str) -> list[dict]:
        """Unidades con asistencia registrada que el documento representa:
        como propietario (presencial o virtual) o como apoderado (poder vigente)."""
        return self._todos(
            """SELECT u.id, u.identificador, a.coeficiente_al_momento, a.tipo_asistencia
               FROM asistencia a
               JOIN unidad u ON u.id = a.unidad_id
               LEFT JOIN poder p ON p.id = a.poder_id
               WHERE a.asamblea_id = %s
                 AND ((a.tipo_asistencia IN ('presencial', 'virtual') AND u.propietario_documento = %s)
                   OR (a.tipo_asistencia = 'poder' AND p.vigente AND p.apoderado_documento = %s))
               ORDER BY u.identificador""",
            (asamblea_id, documento, documento),
        )
