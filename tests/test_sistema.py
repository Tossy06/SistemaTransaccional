import threading
from decimal import Decimal

import psycopg
import pytest

from application.services import AsambleaService, AsistenciaService, VotacionService
from domain.excepciones import ReglaNegocioError
from infrastructure.config import settings


def q(sql, *p):
    with psycopg.connect(settings.database_url) as c:
        return c.execute(sql, p).fetchall()


def unidad(ident):
    return q("SELECT id FROM unidad WHERE identificador=%s", ident)[0][0]


# ------------------------------------------------------------ login seguro
def test_login_correcto_e_incorrecto(cliente):
    c = cliente()
    assert "incorrectos" in c.http.get(c.login("admin@cerezos.co", "mala").headers["location"]).text
    r = c.login("admin@cerezos.co")
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert 'href="/usuarios"' in c.http.get("/").text
    assert q("SELECT password_hash FROM usuario WHERE email='admin@cerezos.co'")[0][0].startswith("$2b$12$")


def test_bloqueo_por_intentos_fallidos(cliente):
    c = cliente()
    for _ in range(5):
        c.login("andres@correo.co", "incorrecta1")
    r = c.login("andres@correo.co")  # contraseña correcta, pero bloqueada
    assert "bloqueada" in c.http.get(r.headers["location"]).text


def test_asamblea_virtual_por_sala(cliente):
    """Como nuvoll_asambleas: el enlace único de cada unidad es la credencial (sin contraseña); el
    ingreso cuenta para el quórum y el voto queda con la unidad, la hora y la cuenta si existe."""
    import re
    admin = cliente(); admin.login("admin@cerezos.co")
    q("UPDATE asamblea SET modalidad = 'virtual', lugar_modalidad = NULL WHERE id = 1 RETURNING id")
    admin.post("/asambleas/1/videollamada", enlace_videollamada="http://inseguro.co")
    assert q("SELECT enlace_videollamada FROM asamblea")[0][0] is None  # solo https
    admin.post("/asambleas/1/videollamada", enlace_videollamada="https://meet.example.com/abc")
    admin.post("/asambleas/1/cerrar-orden"); admin.post("/asambleas/1/convocatoria")
    tokens = dict(q("""SELECT u.identificador, cv.token_acceso FROM convocatoria cv
                       JOIN unidad u ON u.id = cv.unidad_id"""))
    assert len(set(tokens.values())) == 10 and all(len(t) >= 30 for t in tokens.values())
    assert tokens["Apto 101"] in admin.http.get("/asambleas/1/enlaces.csv").text

    # Sin sesión: el enlace basta para entrar a la sala de su unidad; un enlace inventado no.
    pres = cliente()
    html = pres.http.get(f"/sala/{tokens['Apto 101']}").text
    assert "Confirmar mi ingreso" in html and "Carlos Presidente" in html
    assert pres.http.get("/sala/enlace-inventado").status_code == 400
    # En una asamblea virtual la recepción no acredita presencial.
    rec = cliente(); rec.login("recepcion@cerezos.co")
    rec.post("/asambleas/1/asistencia", unidad_id=str(unidad("Apto 102")), tipo_asistencia="presencial")
    assert q("SELECT count(*) FROM asistencia")[0][0] == 0

    def ingresar(c, ident):
        html = c.http.get(f"/sala/{tokens[ident]}").text
        m = re.search(r'name="csrf_token" value="([^"]+)"', html)
        # Si la sala ya no muestra formularios, el token de la sesión se toma de otra página.
        tok = m.group(1) if m else re.search(r'name="csrf_token" value="([^"]+)"',
                                             c.http.get("/login", follow_redirects=True).text).group(1)
        return c.http.post(f"/sala/{tokens[ident]}/ingresar", data={"csrf_token": tok})

    ingresar(pres, "Apto 101")
    assert q("SELECT tipo_asistencia, coeficiente_al_momento FROM asistencia") == [("virtual", Decimal("12.0"))]
    assert "ya registró su ingreso" in pres.http.get(ingresar(pres, "Apto 101").headers["location"]).text
    # Poder previo: el enlace de la unidad se renueva para el apoderado; el del propietario deja de servir.
    rec.post("/asambleas/1/poderes", unidad_id=str(unidad("Apto 401")), apoderado_nombre="Jorge Apoderado",
             apoderado_documento="2001")
    viejo = tokens["Apto 401"]
    tokens["Apto 401"] = q("SELECT token_acceso FROM convocatoria WHERE unidad_id = %s", unidad("Apto 401"))[0][0]
    assert tokens["Apto 401"] != viejo and cliente().http.get(f"/sala/{viejo}").status_code == 400
    jorge = cliente(); jorge.login("jorge@correo.co")
    assert tokens["Apto 401"] in jorge.http.get("/").text  # su sala aparece en el inicio
    assert "Jorge Apoderado (apoderado)" in jorge.http.get(f"/sala/{tokens['Apto 401']}").text
    ingresar(jorge, "Apto 401")
    for email, ident in (("secretaria@cerezos.co", "Apto 102"), ("andres@correo.co", "Apto 201"),
                         ("sofia@correo.co", "Apto 202")):
        c = cliente(); c.login(email); ingresar(c, ident)
    assert q("SELECT tipo_asistencia FROM asistencia WHERE unidad_id=%s", unidad("Apto 401")) == [("poder",)]
    assert q("SELECT quorum_alcanzado FROM asamblea")[0][0] == Decimal("53.00")

    admin.post("/asambleas/1/iniciar")
    punto = q("SELECT id FROM punto_orden_dia ORDER BY orden")[0][0]
    admin.post(f"/puntos/{punto}/abrir")
    estado = pres.http.get(f"/api/sala/{tokens['Apto 101']}/estado").json()
    assert estado["punto_id"] == punto and estado["ingresado"] and not estado["ya_voto"]
    html = pres.http.get(f"/sala/{tokens['Apto 101']}").text
    tok = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    pres.http.post(f"/sala/{tokens['Apto 101']}/votar", data={"decision": "a_favor", "csrf_token": tok})
    r = pres.http.post(f"/sala/{tokens['Apto 101']}/votar", data={"decision": "en_contra", "csrf_token": tok})
    assert "ya votó" in pres.http.get(r.headers["location"]).text
    assert q("SELECT u.email, v.decision FROM voto v JOIN usuario u ON u.id = v.usuario_id") == [
        ("presidente@cerezos.co", "a_favor")]
    vivo = admin.http.get("/api/asambleas/1/en-vivo").json()
    assert vivo["votos"]["a_favor"] == 12.0 and vivo["votos"]["unidades"] == 1
    assert "Pantalla en vivo" in admin.http.get("/asambleas/1").text

    admin.post(f"/puntos/{punto}/cerrar")
    for p_id in [x[0] for x in q("SELECT id FROM punto_orden_dia WHERE estado = 'pendiente' ORDER BY orden")]:
        admin.post(f"/puntos/{p_id}/abrir"); admin.post(f"/puntos/{p_id}/cerrar")
    admin.post("/asambleas/1/finalizar"); admin.post("/asambleas/1/acta")
    acta = q("SELECT contenido FROM acta")[0][0]
    assert "art. 42" in acta and "virtual, ingreso por la sala" in acta and "Modalidad: virtual" in acta


def test_panel_de_administracion_y_votacion_calificada(cliente):
    """El administrador ve el siguiente paso, los indicadores y cada participante con su cuenta y su
    enlace; con las cuentas de demostración se puede aprobar un punto de mayoría calificada (70 %)."""
    import re
    from datetime import date
    admin = cliente(); admin.login("admin@cerezos.co")
    # Una ordinaria sin 15 días de antelación se rechaza al programarla, con la fecha sugerida.
    r = admin.post("/asambleas", conjunto_id="1", tipo="ordinaria", fecha=str(date.today()), hora="20:00",
                   modalidad="virtual", lugar_modalidad="", enlace_videollamada="")
    assert "15 días de antelación" in admin.http.get(r.headers["location"]).text
    r = admin.post("/asambleas", conjunto_id="1", tipo="extraordinaria", fecha=str(date.today()), hora="20:00",
                   modalidad="virtual", lugar_modalidad="", enlace_videollamada="")
    nueva = int(r.headers["location"].rsplit("/", 1)[1])
    html = admin.http.get(f"/asambleas/{nueva}").text
    assert "Siguiente paso" in html and "Arme y cierre el orden del día" in html
    admin.post(f"/asambleas/{nueva}/puntos", descripcion="Reforma del reglamento", tipo_mayoria="calificada_70")
    admin.post(f"/asambleas/{nueva}/cerrar-orden")
    assert "Genere la convocatoria" in admin.http.get(f"/asambleas/{nueva}").text
    admin.post(f"/asambleas/{nueva}/convocatoria")
    html = admin.http.get(f"/asambleas/{nueva}").text
    assert "Abra la asamblea cuando haya quórum" in html and "luis@correo.co" in html  # cuenta para ingresar
    tokens = dict(q("""SELECT us.email, cv.token_acceso FROM convocatoria cv JOIN unidad un ON un.id = cv.unidad_id
                       JOIN usuario us ON us.documento = un.propietario_documento WHERE cv.asamblea_id = %s""", nueva))
    assert len(tokens) == 7 and all(t in html for t in tokens.values())  # enlace de cada unidad
    sesiones = {}
    for email, token in tokens.items():
        c = cliente(); c.login(email)
        tok = re.search(r'name="csrf_token" value="([^"]+)"', c.http.get(f"/sala/{token}").text).group(1)
        c.http.post(f"/sala/{token}/ingresar", data={"csrf_token": tok})
        sesiones[email] = (c, token, tok)
    ind = admin.http.get(f"/asambleas/{nueva}").text
    assert "71.00 %" in ind and ">7<" in ind.replace(" ", "")  # coeficiente presente e ingresaron
    admin.post(f"/asambleas/{nueva}/iniciar")
    punto = q("SELECT id FROM punto_orden_dia WHERE asamblea_id = %s", nueva)[0][0]
    admin.post(f"/puntos/{punto}/abrir")
    for c, token, tok in sesiones.values():
        c.http.post(f"/sala/{token}/votar", data={"decision": "a_favor", "csrf_token": tok})
    assert "7 de 7 unidades presentes" in admin.http.get(f"/asambleas/{nueva}").text
    admin.post(f"/puntos/{punto}/cerrar")
    # 71 % del conjunto a favor >= 70 % (art. 46): aprobado
    assert q("SELECT total_a_favor, resultado FROM resultado_votacion WHERE punto_id = %s", punto) == [
        (Decimal("71.0"), "aprobado")]
    assert "Todos los puntos están votados" in admin.http.get(f"/asambleas/{nueva}").text
    lista = admin.http.get("/asambleas").text
    assert "7 de 10" in lista and "1 de 1" in lista  # ingresaron y puntos votados en la lista


def test_estados_eliminar_y_voto_solo_con_enlace(cliente):
    """Reabrir orden, anular convocatoria y eliminar solo mientras nadie haya ingresado; una unidad
    sin cuenta vota con su enlace único y el voto queda sin usuario pero con unidad y hora."""
    import re
    admin = cliente(); admin.login("admin@cerezos.co")
    q("UPDATE asamblea SET modalidad = 'virtual', lugar_modalidad = NULL WHERE id = 1 RETURNING id")
    admin.post("/asambleas/1/cerrar-orden")
    admin.post("/asambleas/1/reabrir-orden")
    assert q("SELECT orden_del_dia_cerrado FROM asamblea")[0][0] is False
    admin.post("/asambleas/1/cerrar-orden"); admin.post("/asambleas/1/convocatoria")
    viejos = [t[0] for t in q("SELECT token_acceso FROM convocatoria")]
    admin.post("/asambleas/1/anular-convocatoria")
    assert q("SELECT estado FROM asamblea")[0][0] == "programada" and q("SELECT count(*) FROM convocatoria")[0][0] == 0
    assert cliente().http.get(f"/sala/{viejos[0]}").status_code == 400  # enlaces anulados
    admin.post("/asambleas/1/convocatoria")
    token = q("SELECT token_acceso FROM convocatoria WHERE unidad_id = %s", unidad("Apto 302"))[0][0]
    ana = cliente()  # Ana Torres no tiene cuenta: solo su enlace
    html = ana.http.get(f"/sala/{token}").text
    tok = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    ana.http.post(f"/sala/{token}/ingresar", data={"csrf_token": tok})
    # Con alguien adentro ya no se puede anular ni eliminar.
    r = admin.post("/asambleas/1/eliminar")
    assert "ya hay unidades que ingresaron" in admin.http.get(r.headers["location"]).text
    r = admin.post("/asambleas/1/anular-convocatoria")
    assert "ya hay unidades que ingresaron" in admin.http.get(r.headers["location"]).text
    q("UPDATE asamblea SET estado = 'en_curso' WHERE id = 1 RETURNING id")
    punto = q("SELECT id FROM punto_orden_dia WHERE orden = 1")[0][0]
    admin.post(f"/puntos/{punto}/abrir")
    ana.http.post(f"/sala/{token}/votar", data={"decision": "en_contra", "csrf_token": tok})
    assert q("SELECT unidad_id, usuario_id, decision FROM voto") == [(unidad("Apto 302"), None, "en_contra")]
    # Una asamblea programada sin ingresos sí se elimina, con su orden del día.
    r = admin.post("/asambleas", conjunto_id="1", tipo="extraordinaria", fecha="2027-01-10", hora="19:00",
                   modalidad="virtual", lugar_modalidad="", enlace_videollamada="")
    nueva = int(r.headers["location"].rsplit("/", 1)[1])
    admin.post(f"/asambleas/{nueva}/puntos", descripcion="Punto de prueba", tipo_mayoria="simple")
    admin.post(f"/asambleas/{nueva}/eliminar")
    assert q("SELECT count(*) FROM asamblea WHERE id = %s", nueva)[0][0] == 0
    assert q("SELECT count(*) FROM punto_orden_dia WHERE asamblea_id = %s", nueva)[0][0] == 0


def test_carga_masiva_de_unidades_es_atomica(cliente):
    import io, re
    from openpyxl import Workbook
    admin = cliente(); admin.login("admin@cerezos.co")
    conjunto = admin.post("/conjuntos", nombre="Torres del Parque", nit="901000000-1",
                          coeficiente_total="100").headers["location"]
    cid = int(conjunto.rsplit("/", 1)[1])

    def subir(nombre, contenido):
        token = re.search(r'name="csrf_token" value="([^"]+)"', admin.http.get(conjunto).text).group(1)
        r = admin.http.post(f"{conjunto}/importar", data={"csrf_token": token},
                            files={"archivo": (nombre, contenido)})
        return admin.http.get(r.headers["location"]).text

    contar = lambda: q("SELECT count(*) FROM unidad WHERE conjunto_id=%s", cid)[0][0]
    # CSV con una fila mala (coeficiente negativo) y un identificador repetido: no entra ninguna.
    malo = ("identificador;propietario;documento;correo;telefono;coeficiente\n"
            "T1-101;Ana;5001;ana@correo.co;;40\nT1-102;Luis;5002;;;-3\nT1-101;Eva;5003;;;10\n").encode()
    html = subir("censo.csv", malo)
    assert "No se registró ninguna unidad" in html and "Fila 3" in html and "Fila 4" in html
    assert contar() == 0
    # Excel válido desde la plantilla: entran todas, documentos numéricos sin decimales.
    libro = Workbook(); hoja = libro.active
    hoja.append(["Identificador", "Propietario", "Documento", "Correo", "Teléfono", "Coeficiente"])
    hoja.append(["T1-101", "Ana Ruiz", 5001, "ana@correo.co", None, 55.5])
    hoja.append(["T1-102", "Luis Mora", 5002, None, 3001112233, 44.5])
    buf = io.BytesIO(); libro.save(buf)
    assert "Se registraron 2 unidades" in subir("censo.xlsx", buf.getvalue())
    assert q("SELECT propietario_documento FROM unidad WHERE identificador='T1-101'")[0][0] == "5001"
    # Superar el coeficiente total también revierte todo.
    assert "por encima del total" in subir("extra.csv", b"identificador,propietario,documento,coeficiente\nT9,X,9,1\n")
    assert contar() == 2
    assert admin.http.get("/conjuntos/plantilla-unidades.xlsx").content[:2] == b"PK"


def test_formulario_publico_de_registro(cliente):
    import re
    admin = cliente(); admin.login("admin@cerezos.co")
    cid = q("SELECT id FROM conjunto")[0][0]
    anon = cliente()
    assert anon.http.get("/registro/no-existe").status_code == 404
    admin.post(f"/conjuntos/{cid}/formulario", accion="abrir")
    token = q("SELECT formulario_token FROM conjunto")[0][0]
    assert token and token in admin.http.get(f"/conjuntos/{cid}").text

    def enviar(**datos):
        html = anon.http.get(f"/registro/{token}").text
        assert "Diana Rojas" not in html  # el formulario no expone datos personales del censo
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
        base = {"nombre": "Diana Rojas", "documento": "1008", "email": "diana@correo.co",
                "telefono": "", "autoriza": "si", "csrf_token": csrf}
        return anon.http.post(f"/registro/{token}", data={**base, **datos})

    apto402, apto301 = unidad("Apto 402"), unidad("Apto 301")
    # Sin autorización de datos o con documento no numérico: rechazado, nada se guarda.
    assert enviar(unidad_id=apto402, autoriza="").status_code == 400
    assert "solo números" in enviar(unidad_id=apto402, documento="10A8").text
    # Envío válido: queda pendiente y el censo NO cambia todavía.
    assert enviar(unidad_id=apto402).status_code == 303
    assert q("SELECT propietario_email FROM unidad WHERE id=%s", apto402)[0][0] is None
    # Una unidad no recibe un segundo representante en espera.
    r = enviar(unidad_id=apto402, nombre="Otra persona", documento="9999", email="otra@correo.co")
    assert r.status_code == 400 and "solicitud pendiente" in r.text
    # Una persona sí puede representar varias unidades.
    assert enviar(unidad_id=apto301, documento="1008").status_code == 303
    # Unidad de otro conjunto: rechazada.
    q("INSERT INTO conjunto (nombre, nit) VALUES ('Otro', '1') RETURNING id")
    q("""INSERT INTO unidad (conjunto_id, identificador, propietario_nombre, propietario_documento,
          coeficiente_copropiedad) SELECT id, 'X1', 'X', '1', 5 FROM conjunto WHERE nit='1' RETURNING id""")
    assert "no pertenece" in enviar(unidad_id=unidad("X1")).text

    # Revisión: rechazar exige motivo; aprobar actualiza el censo en la misma transacción.
    s402 = q("SELECT id FROM solicitud_censo WHERE unidad_id=%s", apto402)[0][0]
    s301 = q("SELECT id FROM solicitud_censo WHERE unidad_id=%s", apto301)[0][0]
    assert "Diana Rojas" in admin.http.get(f"/conjuntos/{cid}/solicitudes").text
    r = admin.post(f"/solicitudes/{s301}/rechazar", motivo="", conjunto_id=str(cid))
    assert "motivo" in admin.http.get(r.headers["location"]).text
    admin.post(f"/solicitudes/{s301}/rechazar", motivo="No es el propietario según la escritura",
               conjunto_id=str(cid))
    admin.post(f"/solicitudes/{s402}/aprobar", conjunto_id=str(cid))
    assert q("SELECT estado FROM solicitud_censo ORDER BY id") == [("aprobada",), ("rechazada",)]
    assert q("SELECT propietario_email FROM unidad WHERE id=%s", apto402)[0][0] == "diana@correo.co"
    assert q("SELECT propietario_documento FROM unidad WHERE id=%s", apto301)[0][0] == "1005"
    # Una solicitud revisada no se vuelve a revisar, y la BD exige rastro de la revisión.
    r = admin.post(f"/solicitudes/{s402}/aprobar", conjunto_id=str(cid))
    assert "ya fue revisada" in admin.http.get(r.headers["location"]).text
    with pytest.raises(psycopg.errors.CheckViolation):
        q("UPDATE solicitud_censo SET revisado_por = NULL WHERE id=%s RETURNING id", s402)
    # Con la solicitud aprobada, Diana activa su cuenta como copropietaria.
    act = cliente()
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', act.http.get("/activar").text).group(1)
    r = act.http.post("/activar", data={"documento": "1008", "email": "diana@correo.co",
                                        "password": "Clave2026x", "confirmacion": "Clave2026x",
                                        "csrf_token": csrf})
    assert r.status_code == 303
    # Formulario cerrado: el enlace deja de funcionar.
    admin.post(f"/conjuntos/{cid}/formulario", accion="cerrar")
    assert anon.http.get(f"/registro/{token}").status_code == 404


def test_activacion_de_cuenta_desde_el_censo(cliente):
    import re
    c = cliente()
    def activar(**datos):
        token = re.search(r'name="csrf_token" value="([^"]+)"', c.http.get("/activar").text).group(1)
        base = {"password": "Clave2026x", "confirmacion": "Clave2026x", "csrf_token": token}
        return c.http.post("/activar", data={**base, **datos})
    # Propietario del Apto 301 con el correo registrado: queda activo como copropietario.
    assert activar(documento="1005", email="pedro@correo.co").status_code == 303
    assert q("""SELECT u.nombre, r.nombre FROM usuario u JOIN usuario_rol ur ON ur.usuario_id=u.id
               JOIN rol r ON r.id=ur.rol_id WHERE u.documento='1005'""") == [("Pedro Gómez", "copropietario")]
    assert cliente().login("pedro@correo.co", "Clave2026x").headers["location"] == "/"
    # Documento de propietario con otro correo, o documento desconocido: mismo mensaje, sin cuenta.
    for doc, correo in (("1006", "otro@correo.co"), ("7777", "nadie@correo.co")):
        r = activar(documento=doc, email=correo)
        assert r.status_code == 400 and "no coinciden" in r.text
    assert q("SELECT count(*) FROM usuario WHERE documento IN ('1006','7777')")[0][0] == 0
    # Segunda activación del mismo documento: rechazada.
    assert "Ya existe una cuenta" in activar(documento="1005", email="pedro@correo.co").text
    # Apoderado: solo con un poder vigente en una asamblea convocada o en curso.
    assert activar(documento="3001", email="apoderada@correo.co").status_code == 400
    admin = cliente(); admin.login("admin@cerezos.co")
    q("UPDATE asamblea SET fecha = current_date + 20 WHERE id = 1 RETURNING id")
    admin.post("/asambleas/1/cerrar-orden"); admin.post("/asambleas/1/convocatoria")
    rec = cliente(); rec.login("recepcion@cerezos.co")
    rec.post("/asambleas/1/asistencia", unidad_id=str(unidad("Apto 402")), tipo_asistencia="poder",
             apoderado_nombre="Marta Apoderada", apoderado_documento="3001")
    assert activar(documento="3001", email="apoderada@correo.co").status_code == 303
    assert q("""SELECT r.nombre FROM usuario u JOIN usuario_rol ur ON ur.usuario_id=u.id
               JOIN rol r ON r.id=ur.rol_id WHERE u.documento='3001'""") == [("apoderado",)]


def test_cambio_y_restablecimiento_de_password(cliente):
    c = cliente(); c.login("andres@correo.co")
    r = c.post("/cuenta/password", actual="mala", nueva="Nueva2026x", confirmacion="Nueva2026x")
    assert "no es correcta" in c.http.get(r.headers["location"]).text
    c.post("/cuenta/password", actual="Asamblea2026*", nueva="Nueva2026x", confirmacion="Nueva2026x")
    assert cliente().login("andres@correo.co", "Nueva2026x").headers["location"] == "/"
    admin = cliente(); admin.login("admin@cerezos.co")
    uid = q("SELECT id FROM usuario WHERE email='andres@correo.co'")[0][0]
    admin.post(f"/usuarios/{uid}/password", password="Reset2026x")
    assert cliente().login("andres@correo.co", "Reset2026x").headers["location"] == "/"


def test_csrf_y_control_de_roles(cliente):
    c = cliente()
    assert c.http.get("/usuarios", follow_redirects=False).status_code == 303  # sin sesión
    c.login("andres@correo.co")
    assert c.http.get("/usuarios").status_code == 403  # copropietario no administra
    c2 = cliente(); c2.login("admin@cerezos.co")
    assert c2.http.post("/conjuntos", data={"nombre": "X", "nit": "1"}).status_code == 403  # sin token CSRF


# ------------------------------------------------------- flujo completo
def test_flujo_completo_asamblea(cliente):
    admin = cliente(); admin.login("admin@cerezos.co")
    asamblea_id = q("SELECT id FROM asamblea")[0][0]
    admin.post(f"/asambleas/{asamblea_id}/cerrar-orden")
    admin.post(f"/asambleas/{asamblea_id}/convocatoria")
    assert q("SELECT count(*) FROM convocatoria")[0][0] == 10

    rec = cliente(); rec.login("recepcion@cerezos.co")
    for ident in ("Apto 101", "Apto 102", "Apto 201", "Apto 202", "Apto 301"):
        rec.post(f"/asambleas/{asamblea_id}/asistencia", unidad_id=unidad(ident), tipo_asistencia="presencial")
    rec.post(f"/asambleas/{asamblea_id}/asistencia", unidad_id=unidad("Apto 401"), tipo_asistencia="poder",
             apoderado_nombre="Jorge Apoderado", apoderado_documento="2001")
    # segundo registro de la misma unidad: rechazado por la BD
    r = rec.post(f"/asambleas/{asamblea_id}/asistencia", unidad_id=unidad("Apto 401"), tipo_asistencia="presencial")
    assert "ya fue registrada" in rec.http.get(r.headers["location"]).text
    assert q("SELECT quorum_alcanzado FROM asamblea")[0][0] == Decimal("63.00")

    admin.post(f"/asambleas/{asamblea_id}/iniciar")
    assert q("SELECT estado FROM asamblea")[0][0] == "en_curso"

    puntos = [p[0] for p in q("SELECT id FROM punto_orden_dia ORDER BY orden")]
    admin.post(f"/puntos/{puntos[0]}/abrir")
    r = admin.post(f"/puntos/{puntos[1]}/abrir")  # un solo punto abierto
    assert "otro punto" in admin.http.get(r.headers["location"]).text

    votantes = {"presidente@cerezos.co": "Apto 101", "secretaria@cerezos.co": "Apto 102",
                "andres@correo.co": "Apto 201", "jorge@correo.co": "Apto 401"}
    for email, ident in votantes.items():
        v = cliente(); v.login(email)
        v.post(f"/votar/{puntos[0]}", unidad_id=unidad(ident), decision="a_favor")
    # Jorge no puede votar por una unidad que no representa; Andrés no vota dos veces
    v = cliente(); v.login("jorge@correo.co")
    r = v.post(f"/votar/{puntos[0]}", unidad_id=unidad("Apto 202"), decision="en_contra")
    assert "No está habilitado" in v.http.get(r.headers["location"]).text
    v = cliente(); v.login("andres@correo.co")
    r = v.post(f"/votar/{puntos[0]}", unidad_id=unidad("Apto 201"), decision="en_contra")
    assert "ya votó" in v.http.get(r.headers["location"]).text

    admin.post(f"/puntos/{puntos[0]}/cerrar")
    # 12+11+10+10 = 43 a favor > 63/2 → aprobado (mayoría simple)
    assert q("SELECT total_a_favor, resultado FROM resultado_votacion")[0] == (Decimal("43.0"), "aprobado")

    # punto 2 sin votos; punto 3 calificado: 43 < 70 → rechazado
    for p in puntos[1:]:
        admin.post(f"/puntos/{p}/abrir")
        if p == puntos[2]:
            for email, ident in votantes.items():
                v = cliente(); v.login(email)
                v.post(f"/votar/{p}", unidad_id=unidad(ident), decision="a_favor")
        admin.post(f"/puntos/{p}/cerrar")
    assert q("SELECT resultado FROM resultado_votacion r JOIN punto_orden_dia p ON p.id=r.punto_id WHERE p.orden=3")[0][0] == "rechazado"

    admin.post(f"/asambleas/{asamblea_id}/finalizar")
    admin.post(f"/asambleas/{asamblea_id}/acta")
    acta_id = q("SELECT id FROM acta")[0][0]
    for email, rol in (("presidente@cerezos.co", "presidente"), ("secretaria@cerezos.co", "secretario")):
        f = cliente(); f.login(email); f.post(f"/actas/{acta_id}/aprobar", rol=rol)
    assert q("SELECT estado FROM acta")[0][0] == "aprobada"
    assert "Verificada" in admin.http.get(f"/actas/{acta_id}").text

    # inmutabilidad a nivel de base de datos
    for sql in ("UPDATE voto SET decision='en_contra'", "DELETE FROM resultado_votacion",
                "UPDATE acta SET contenido='alterado'"):
        with pytest.raises(psycopg.errors.RaiseException):
            q(sql)


def test_segunda_convocatoria(cliente):
    s, a = AsambleaService(), AsistenciaService()
    aid = q("SELECT id FROM asamblea")[0][0]
    s.cerrar_orden_del_dia(aid); s.generar_convocatoria(aid)
    a.registrar(aid, unidad("Apto 101"), "presencial")
    a.registrar(aid, unidad("Apto 102"), "presencial")
    assert "No hay quórum" in s.iniciar(aid)
    nueva = s.crear_segunda_convocatoria(aid)
    assert q("SELECT count(*) FROM punto_orden_dia WHERE asamblea_id=%s", nueva)[0][0] == 3
    s.generar_convocatoria(nueva)
    a.registrar(nueva, unidad("Apto 101"), "presencial")
    with pytest.raises(ReglaNegocioError):  # una sola unidad no es "número plural"
        s.iniciar(nueva)
    a.registrar(nueva, unidad("Apto 102"), "presencial")
    s.iniciar(nueva)
    assert q("SELECT estado FROM asamblea WHERE id=%s", nueva)[0][0] == "en_curso"


def test_concurrencia_asistencia_quorum():
    """10 registros simultáneos: el quórum guardado debe ser exactamente 100 %."""
    s, a = AsambleaService(), AsistenciaService()
    aid = q("SELECT id FROM asamblea")[0][0]
    s.cerrar_orden_del_dia(aid); s.generar_convocatoria(aid)
    ids = [r[0] for r in q("SELECT id FROM unidad")]
    hilos = [threading.Thread(target=a.registrar, args=(aid, u, "presencial")) for u in ids]
    [h.start() for h in hilos]; [h.join() for h in hilos]
    assert q("SELECT quorum_alcanzado FROM asamblea")[0][0] == Decimal("100.00")


def test_concurrencia_votos_y_cierre():
    """Votos simultáneos y doble voto concurrente de la misma unidad."""
    s, a, v = AsambleaService(), AsistenciaService(), VotacionService()
    aid = q("SELECT id FROM asamblea")[0][0]
    s.cerrar_orden_del_dia(aid); s.generar_convocatoria(aid)
    for u in q("SELECT id FROM unidad"):
        a.registrar(aid, u[0], "presencial")
    s.iniciar(aid)
    punto = q("SELECT id FROM punto_orden_dia WHERE orden=1")[0][0]
    v.abrir_punto(punto)
    usuarios = {r[0]: {"id": r[1], "documento": r[2]} for r in q(
        "SELECT un.id, us.id, us.documento FROM unidad un JOIN usuario us ON us.documento = un.propietario_documento")}
    errores = []

    def votar(uid, usr):
        try:
            v.votar(punto, uid, usr, "a_favor")
        except ReglaNegocioError as e:
            errores.append(str(e))

    hilos = [threading.Thread(target=votar, args=(u, usr)) for u, usr in usuarios.items() for _ in range(3)]
    [h.start() for h in hilos]; [h.join() for h in hilos]
    assert q("SELECT count(*) FROM voto")[0][0] == len(usuarios)
    assert len(errores) == 2 * len(usuarios) and all("ya votó" in e for e in errores)
    r = v.cerrar_punto(punto)
    esperado = q("""SELECT sum(un.coeficiente_copropiedad) FROM unidad un
                    JOIN usuario us ON us.documento = un.propietario_documento""")[0][0]
    assert r["a_favor"] == esperado
    with pytest.raises(ReglaNegocioError):
        v.votar(punto, next(iter(usuarios)), next(iter(usuarios.values())), "en_contra")
