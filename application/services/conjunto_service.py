"""RF-02: conjuntos residenciales y unidades."""
from decimal import Decimal

from domain.excepciones import ReglaNegocioError
from domain.validaciones import a_decimal_positivo
from infrastructure.dao import ConjuntoDAO, UnidadDAO
from infrastructure.db import solo_lectura, transaccion
from infrastructure.errores_bd import traducir_errores_bd

MAXIMO_ERRORES_MOSTRADOS = 8


class ConjuntoService:
    def listar(self) -> list[dict]:
        with solo_lectura() as conn:
            return ConjuntoDAO(conn).listar()

    def detalle(self, conjunto_id: int) -> dict:
        """Conjunto, sus unidades y la suma de coeficientes activos."""
        with solo_lectura() as conn:
            conjunto = ConjuntoDAO(conn).obtener(conjunto_id)
            if not conjunto:
                raise ReglaNegocioError("Conjunto no encontrado.")
            unidades = UnidadDAO(conn)
            return {
                "conjunto": conjunto,
                "unidades": unidades.listar_por_conjunto(conjunto_id),
                "suma": unidades.suma_coeficientes(conjunto_id),
            }

    @traducir_errores_bd
    def crear(self, nombre, nit, direccion, ciudad, numero_unidades, coeficiente_total) -> int:
        """Registra un conjunto. Coeficiente total por defecto: 100."""
        if not (nombre and nit):
            raise ReglaNegocioError("Nombre y NIT son obligatorios.")
        with transaccion() as conn:
            return ConjuntoDAO(conn).crear(
                nombre, nit, direccion, ciudad, int(numero_unidades or 0),
                a_decimal_positivo(coeficiente_total or 100, "coeficiente total"),
            )

    @traducir_errores_bd
    def crear_unidad(self, conjunto_id, identificador, nombre, documento, email, telefono, coeficiente) -> int:
        """Registra una unidad sin superar el coeficiente total del conjunto."""
        if not (identificador and nombre and documento):
            raise ReglaNegocioError("Identificador, propietario y documento son obligatorios.")
        coef = a_decimal_positivo(coeficiente, "coeficiente")
        with transaccion() as conn:
            # El bloqueo del conjunto evita que dos altas simultáneas superen el total.
            conjunto = ConjuntoDAO(conn).obtener(conjunto_id, bloquear=True)
            unidades = UnidadDAO(conn)
            if unidades.suma_coeficientes(conjunto_id) + coef > conjunto["coeficiente_total"]:
                raise ReglaNegocioError(
                    "La suma de coeficientes superaría el coeficiente total del conjunto."
                )
            return unidades.crear(conjunto_id, identificador, nombre, documento, email or None, telefono, coef)

    @traducir_errores_bd
    def importar_unidades(self, conjunto_id: int, filas: list[dict]) -> int:
        """Carga masiva del censo de propietarios en UNA transacción.

        Valida todas las filas antes de escribir; si una sola falla, no se
        registra ninguna (atomicidad). Devuelve el número de unidades creadas.
        """
        errores, nuevas, vistos, suma_archivo = [], [], set(), Decimal("0")
        for f in filas:
            n = f["_fila"]
            faltan = [c for c, k in (("identificador", "identificador"), ("propietario", "propietario_nombre"),
                                     ("documento", "propietario_documento"), ("coeficiente", "coeficiente"))
                      if not f.get(k)]
            if faltan:
                errores.append(f"Fila {n}: falta {', '.join(faltan)}.")
                continue
            try:
                coef = a_decimal_positivo(f["coeficiente"], "coeficiente")
            except ReglaNegocioError as e:
                errores.append(f"Fila {n}: {e}")
                continue
            clave = f["identificador"].lower()
            if clave in vistos:
                errores.append(f"Fila {n}: el identificador {f['identificador']} está repetido en el archivo.")
                continue
            vistos.add(clave)
            suma_archivo += coef
            nuevas.append((f, coef))

        with transaccion() as conn:
            # Mismo bloqueo que el alta individual: nadie más agrega unidades mientras tanto.
            conjunto = ConjuntoDAO(conn).obtener(conjunto_id, bloquear=True)
            if not conjunto:
                raise ReglaNegocioError("Conjunto no encontrado.")
            unidades = UnidadDAO(conn)
            existentes = unidades.identificadores(conjunto_id)
            errores += [f"Fila {f['_fila']}: la unidad {f['identificador']} ya existe en el conjunto."
                        for f, _ in nuevas if f["identificador"].lower() in existentes]
            total = unidades.suma_coeficientes(conjunto_id) + suma_archivo
            if total > conjunto["coeficiente_total"]:
                errores.append(f"La suma de coeficientes quedaría en {total}, por encima del total "
                               f"del conjunto ({conjunto['coeficiente_total']}).")
            if errores:
                extra = len(errores) - MAXIMO_ERRORES_MOSTRADOS
                detalle = " ".join(errores[:MAXIMO_ERRORES_MOSTRADOS])
                if extra > 0:
                    detalle += f" Y {extra} errores más."
                raise ReglaNegocioError(f"No se registró ninguna unidad. {detalle}")
            for f, coef in nuevas:
                unidades.crear(conjunto_id, f["identificador"], f["propietario_nombre"],
                               f["propietario_documento"], f.get("propietario_email") or None,
                               f.get("propietario_telefono") or None, coef)
            return len(nuevas)

    def cambiar_activo_unidad(self, unidad_id: int, activo: bool) -> int:
        """Activa o desactiva la unidad y devuelve el id de su conjunto."""
        with transaccion() as conn:
            dao = UnidadDAO(conn)
            unidad = dao.obtener(unidad_id)
            dao.cambiar_activo(unidad_id, activo)
            return unidad["conjunto_id"]
