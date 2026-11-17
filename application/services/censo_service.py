"""RF-02: formulario público de registro de propietarios y revisión de solicitudes.

La administración comparte un enlace (como un formulario en línea); cada propietario
envía sus datos y la administración los aprueba antes de que cuenten en el censo.
Reglas:
- La unidad debe existir en el conjunto del enlace y estar activa.
- Una unidad tiene un solo representante: el censo guarda uno por unidad y la base de
  datos admite una sola solicitud pendiente por unidad (índice único parcial).
- Una persona puede representar varias unidades (propietaria de varias).
- Sin autorización de tratamiento de datos (Ley 1581 de 2012) no se guarda nada.
- Enviar el formulario no da derecho a votar: solo la aprobación actualiza el censo.
"""
import re
import secrets

from domain.excepciones import ReglaNegocioError
from infrastructure.config import settings
from infrastructure.dao import ConjuntoDAO, SolicitudCensoDAO, UnidadDAO, UsuarioDAO
from infrastructure.db import solo_lectura, transaccion
from infrastructure.errores_bd import traducir_errores_bd
from infrastructure.seguridad import LimitadorIntentos

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Freno a envíos masivos desde un mismo origen: 10 solicitudes cada 15 minutos.
limitador_formulario = LimitadorIntentos(10, settings.minutos_bloqueo)


class CensoService:
    # ------------------------------------------------------------ administración
    def abrir_formulario(self, conjunto_id: int) -> str:
        """Genera (o renueva) el enlace público del conjunto."""
        token = secrets.token_urlsafe(18)
        with transaccion() as conn:
            if not ConjuntoDAO(conn).obtener(conjunto_id, bloquear=True):
                raise ReglaNegocioError("Conjunto no encontrado.")
            ConjuntoDAO(conn).cambiar_token(conjunto_id, token)
        return token

    def cerrar_formulario(self, conjunto_id: int) -> None:
        with transaccion() as conn:
            ConjuntoDAO(conn).cambiar_token(conjunto_id, None)

    def solicitudes(self, conjunto_id: int) -> dict:
        with solo_lectura() as conn:
            conjunto = ConjuntoDAO(conn).obtener(conjunto_id)
            if not conjunto:
                raise ReglaNegocioError("Conjunto no encontrado.")
            filas = SolicitudCensoDAO(conn).listar_por_conjunto(conjunto_id)
            usuarios = UsuarioDAO(conn)
            for f in filas:
                f["coincide"] = f["documento"] == f["propietario_documento"]
                # ¿El representante actual ya tiene cuenta? Aprobar otro documento lo reemplaza.
                f["representante_con_cuenta"] = (
                    not f["coincide"] and usuarios.obtener_por_documento(f["propietario_documento"]) is not None)
            return {"conjunto": conjunto, "solicitudes": filas}

    def contar_pendientes(self, conjunto_id: int) -> int:
        with solo_lectura() as conn:
            return SolicitudCensoDAO(conn).contar_pendientes(conjunto_id)

    def aprobar(self, solicitud_id: int, usuario_id: int) -> int:
        """Pasa los datos de la solicitud al censo de la unidad en UNA transacción.

        Devuelve el id del conjunto.
        """
        with transaccion() as conn:
            solicitudes = SolicitudCensoDAO(conn)
            s = solicitudes.obtener(solicitud_id, bloquear=True)
            if not s:
                raise ReglaNegocioError("Solicitud no encontrada.")
            if s["estado"] != "pendiente":
                raise ReglaNegocioError("La solicitud ya fue revisada.")
            unidades = UnidadDAO(conn)
            unidad = unidades.obtener(s["unidad_id"], bloquear=True)
            otro = UsuarioDAO(conn).obtener_por_email(s["email"])
            if otro and otro["documento"] != s["documento"]:
                raise ReglaNegocioError("El correo de la solicitud ya pertenece a otra persona con cuenta. "
                                        "Recházela o pida al propietario otro correo.")
            unidades.actualizar_propietario(unidad["id"], s["nombre"], s["documento"], s["email"],
                                            s["telefono"])
            solicitudes.aprobar(solicitud_id, usuario_id)
            return unidad["conjunto_id"]

    def rechazar(self, solicitud_id: int, usuario_id: int, motivo: str) -> int:
        motivo = (motivo or "").strip()
        if not motivo:
            raise ReglaNegocioError("Escriba el motivo del rechazo.")
        with transaccion() as conn:
            solicitudes = SolicitudCensoDAO(conn)
            s = solicitudes.obtener(solicitud_id, bloquear=True)
            if not s or s["estado"] != "pendiente":
                raise ReglaNegocioError("La solicitud ya fue revisada.")
            solicitudes.rechazar(solicitud_id, usuario_id, motivo[:300])
            return UnidadDAO(conn).obtener(s["unidad_id"])["conjunto_id"]

    # ------------------------------------------------------------ formulario público
    def formulario(self, token: str) -> dict:
        """Conjunto del enlace y sus unidades activas (solo identificadores, sin datos personales)."""
        with solo_lectura() as conn:
            conjunto = ConjuntoDAO(conn).obtener_por_token(token or "")
            if not conjunto:
                raise ReglaNegocioError("Este formulario no existe o ya fue cerrado por la administración.")
            unidades = UnidadDAO(conn).listar_por_conjunto(conjunto["id"], solo_activas=True)
            return {"conjunto": conjunto,
                    "unidades": [{"id": u["id"], "identificador": u["identificador"]} for u in unidades]}

    @traducir_errores_bd
    def enviar(self, token, origen, unidad_id, nombre, documento, email, telefono, autoriza) -> None:
        nombre, documento = (nombre or "").strip(), (documento or "").strip()
        email, telefono = (email or "").strip().lower(), (telefono or "").strip()
        if limitador_formulario.esta_bloqueado(origen):
            raise ReglaNegocioError("Se recibieron demasiadas solicitudes desde esta conexión. "
                                    "Intente de nuevo más tarde.")
        if not (unidad_id and nombre and documento and email):
            raise ReglaNegocioError("Unidad, nombre, documento y correo son obligatorios.")
        if not documento.isdigit() or len(documento) > 15:
            raise ReglaNegocioError("El documento debe tener solo números (máximo 15).")
        if not _EMAIL.match(email):
            raise ReglaNegocioError("Escriba un correo electrónico válido.")
        if not autoriza:
            raise ReglaNegocioError("Debe autorizar el tratamiento de sus datos para enviar el formulario.")
        try:
            unidad_id = int(unidad_id)
        except (TypeError, ValueError):
            raise ReglaNegocioError("Seleccione su unidad.")

        with transaccion() as conn:
            conjunto = ConjuntoDAO(conn).obtener_por_token(token or "")
            if not conjunto:
                raise ReglaNegocioError("Este formulario no existe o ya fue cerrado por la administración.")
            unidad = UnidadDAO(conn).obtener(unidad_id)
            if not unidad or unidad["conjunto_id"] != conjunto["id"] or not unidad["activo"]:
                raise ReglaNegocioError("La unidad seleccionada no pertenece a este conjunto.")
            if (unidad["propietario_documento"] == documento
                    and (unidad["propietario_email"] or "").lower() == email):
                raise ReglaNegocioError("Sus datos ya están registrados para esta unidad. "
                                        "Puede activar su cuenta en el sistema.")
            limitador_formulario.registrar_fallo(origen)
            SolicitudCensoDAO(conn).crear(unidad_id, nombre[:120], documento, email[:120],
                                          telefono[:20] or None, True)
