"""Redacción del acta e integridad de su contenido."""
import hashlib
from datetime import datetime


MODALIDAD_TEXTO = {"presencial": "presencial", "virtual": "virtual (sala web)",
                   "mixta": "mixta (salón y sala web)"}


def calcular_hash(contenido: str) -> str:
    """SHA-256 (FIPS 180-4) del contenido del acta."""
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def es_integra(contenido: str, hash_guardado: str) -> bool:
    """True si el contenido no fue alterado desde que se generó."""
    return calcular_hash(contenido) == hash_guardado


def _texto_mayoria(tipo_mayoria: str) -> str:
    if tipo_mayoria == "calificada_70":
        return "calificada (70 % del conjunto)"
    return "simple (coef. presentes)"


def redactar(asamblea: dict, asistentes: list[dict], puntos: list[dict],
             resultados: dict[int, dict]) -> str:
    """Construye el texto del acta a partir del historial de la asamblea.

    resultados: resultado de votación indexado por id de punto.
    """
    a = asamblea
    lineas = [
        f"ACTA DE ASAMBLEA GENERAL {a['tipo'].upper()} DE COPROPIETARIOS",
        a["conjunto_nombre"],
        "",
        f"Fecha: {a['fecha']:%Y-%m-%d}   Hora: {a['hora']:%H:%M}   "
        f"Modalidad: {MODALIDAD_TEXTO.get(a.get('modalidad'), a.get('modalidad'))}"
        + (f"   Lugar: {a['lugar_modalidad']}" if a.get("lugar_modalidad") else ""),
    ]
    if a.get("modalidad") in ("virtual", "mixta"):
        lineas.append("Reunión no presencial o mixta (art. 42, Ley 675 de 2001): cada ingreso y cada voto "
                      "por la sala web quedó registrado con el usuario, la unidad y la hora.")
    if a["asamblea_original_id"]:
        lineas.append(f"Reunión de segunda convocatoria (art. 41, Ley 675 de 2001) "
                      f"de la asamblea #{a['asamblea_original_id']}.")

    lineas += ["", "1. VERIFICACIÓN DE QUÓRUM",
               f"Unidades presentes o representadas: {len(asistentes)}",
               f"Coeficientes presentes: {a['quorum_alcanzado']} % de {a['coeficiente_total']}",
               "", "2. ASISTENTES"]
    for s in asistentes:
        hora = f"{s['hora_registro']:%H:%M}" if s.get("hora_registro") else ""
        if s["tipo_asistencia"] == "poder":
            via = f"por poder: {s['apoderado_nombre']} (doc. {s['apoderado_documento']})"
        elif s["tipo_asistencia"] == "virtual":
            via = f"virtual, ingreso por la sala a las {hora}"
        else:
            via = "presencial"
        lineas.append(f"  - {s['identificador']}: {s['propietario_nombre']} "
                      f"| coef. {s['coeficiente_al_momento']} | {via}")

    lineas += ["", "3. ORDEN DEL DÍA Y DECISIONES"]
    for p in puntos:
        lineas.append(f"  {p['orden']}. {p['descripcion']} — mayoría {_texto_mayoria(p['tipo_mayoria'])}")
        r = resultados.get(p["id"])
        if r:
            lineas.append(f"     A favor: {r['total_a_favor']} | En contra: {r['total_en_contra']} | "
                          f"Abstención: {r['total_abstencion']} => {r['resultado'].upper()}")

    lineas += ["", f"Acta generada automáticamente el {datetime.now():%Y-%m-%d %H:%M} a partir del "
                   f"historial transaccional del sistema."]
    return "\n".join(lineas)
