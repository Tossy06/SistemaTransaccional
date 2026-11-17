"""Regenera los diagramas del documento en PDF vectorial (carpeta docs/diagramas) a partir del código.

Uso (desde la raíz del proyecto):  python docs/fuentes_diagramas/generar_diagramas.py
Los métodos de cada DAO se leen del código fuente, así el diagrama no se
desactualiza cuando cambia un DAO.
"""
import ast
import glob
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SALIDA = os.path.join(RAIZ, "docs", "diagramas")
AZUL = "#1f4e79"
plt.rcParams["font.family"] = "DejaVu Sans"


def _guardar(fig, nombre: str, dpi: int) -> None:
    """Solo PDF vectorial: no pierde calidad al ampliar ni al imprimir."""
    fig.savefig(os.path.join(SALIDA, f"{nombre}.pdf"), facecolor="white")
    plt.close(fig)


# --------------------------------------------------------------- cronograma
def cronograma():
    from datetime import date, timedelta
    import matplotlib.dates as mdates
    tareas = [
        ("Fase 1 · Análisis (requisitos Ley 675, procesos, actores)", date(2026, 8, 17), date(2026, 8, 29), "#8faadc"),
        ("Fase 2 · Diseño (arquitectura, modelo relacional, CU, DAO)", date(2026, 8, 31), date(2026, 9, 19), "#8faadc"),
        ("Fase 3 · Sprint 1 · Login, usuarios y roles, conjuntos y unidades", date(2026, 9, 21), date(2026, 9, 26), "#2e75b6"),
        ("Sprint 2 · Asamblea, orden del día y convocatoria", date(2026, 9, 28), date(2026, 10, 3), "#2e75b6"),
        ("Sprint 3 · Asistencia, poderes y quórum", date(2026, 10, 5), date(2026, 10, 10), "#2e75b6"),
        ("Sprint 4 · Apertura de votación y voto ponderado", date(2026, 10, 12), date(2026, 10, 17), "#2e75b6"),
        ("Sprint 5 · Cierre con mayorías y segunda convocatoria", date(2026, 10, 19), date(2026, 10, 24), "#2e75b6"),
        ("Sprint 6 · Acta, aprobación e histórico", date(2026, 10, 26), date(2026, 10, 31), "#2e75b6"),
        ("Fase 4 · Implementación: pruebas funcionales y de concurrencia", date(2026, 11, 2), date(2026, 11, 14), "#548235"),
        ("Ajustes, manual técnico y entrega final", date(2026, 11, 16), date(2026, 11, 21), "#548235"),
    ]
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=100)
    for i, (nombre, ini, fin, color) in enumerate(tareas):
        ax.barh(i, (fin - ini).days, left=mdates.date2num(ini), height=0.58, color=color)
    ax.set_yticks(range(len(tareas)), [t[0] for t in tareas], fontsize=10.5)
    ax.invert_yaxis()
    ini = date(2026, 8, 17)
    ax.set_xlim(mdates.date2num(ini), mdates.date2num(date(2026, 11, 24)))
    marcas = [ini + timedelta(days=7 * k) for k in range(15)]
    ax.set_xticks([mdates.date2num(m) for m in marcas], [m.strftime("%d/%m") for m in marcas], rotation=45, fontsize=9.5)
    ax.grid(axis="x", color="#e2e2e2", lw=0.8); ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    fig.tight_layout()
    _guardar(fig, "cronograma", 200)


# --------------------------------------------------------------- clases DAO
def _metodos_dao() -> dict[str, list[str]]:
    clases = {}
    for ruta in sorted(glob.glob(os.path.join(RAIZ, "infrastructure", "dao", "*_dao.py"))):
        arbol = ast.parse(open(ruta, encoding="utf-8").read())
        for c in (n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name != "BaseDAO"):
            tabla = next((n.value.value for n in c.body if isinstance(n, ast.Assign)
                          and getattr(n.targets[0], "id", "") == "tabla"), "")
            metodos = []
            for f in (n for n in c.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")):
                args = ", ".join(a.arg for a in f.args.args if a.arg != "self")
                ret = f": {ast.unparse(f.returns)}" if f.returns else ""
                metodos.append(f"+ {f.name}({args}){ret}")
            clases[c.name] = (tabla, metodos)
    return clases


def _envolver(texto: str, ancho: int = 36) -> list[str]:
    """Corta '+ metodo(a, b): tipo' después de '(' o de una coma, como en UML."""
    if len(texto) <= ancho:
        return [texto]
    cabeza, resto = texto.split("(", 1)
    piezas = [p + ", " for p in resto.split(", ")]
    piezas[-1] = piezas[-1][:-2]
    lineas, actual = [], cabeza + "("
    for pieza in piezas:
        if len(actual) + len(pieza) > ancho and actual.strip() not in ("", cabeza + "("):
            lineas.append(actual.rstrip()); actual = "     " + pieza
        elif len(actual) + len(pieza) > ancho:
            lineas.append(actual.rstrip()); actual = "     " + pieza
        else:
            actual += pieza
    lineas.append(actual.rstrip())
    return lineas


def clases_dao_detalle(ancho_pag=6.5, alto_max=8.2, columnas=3):
    """Se dibuja ya al tamaño de una hoja vertical (pulgadas reales) para que el documento no
    necesite una página horizontal: tres columnas equilibradas (cada clase va a la más corta)."""
    clases = _metodos_dao()
    gap, pad = 0.09, 0.05
    w = (ancho_pag - gap * (columnas + 1)) / columnas
    fs, lh, cab, attr = 6.2, 0.103, 0.29, 0.155
    cajas = []
    for nombre, (tabla, metodos) in clases.items():
        lineas = [l for m in metodos for l in _envolver(m, 39)]
        cajas.append((nombre, tabla, lineas, cab + attr + 2 * pad + lh * len(lineas)))
    # Reparto equilibrado: de la más alta a la más baja, siempre a la columna más corta.
    cols = [[] for _ in range(columnas)]; altos = [gap] * columnas
    for caja in sorted(cajas, key=lambda c: -c[3]):
        k = altos.index(min(altos)); cols[k].append(caja); altos[k] += caja[3] + gap
    for col in cols:
        col.sort(key=lambda c: c[0])
    alto_total = max(altos)
    fig = plt.figure(figsize=(ancho_pag, alto_total), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, ancho_pag); ax.set_ylim(alto_total, 0); ax.axis("off")
    for k, col in enumerate(cols):
        x, y = gap + k * (w + gap), gap
        for nombre, tabla, lineas, h in col:
            ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=AZUL, lw=0.9))
            ax.add_patch(Rectangle((x, y), w, cab, fc="#dce6f1", ec=AZUL, lw=0.9))
            ax.text(x + w / 2, y + 0.085, "«extends BaseDAO»", ha="center", va="center", fontsize=fs - 1)
            ax.text(x + w / 2, y + 0.205, nombre, ha="center", va="center", fontsize=fs + 1, weight="bold")
            ax.text(x + pad, y + cab + attr / 2, f'tabla = "{tabla}"', va="center", fontsize=fs)
            ax.plot([x, x + w], [y + cab + attr] * 2, color=AZUL, lw=0.7)
            for n, l in enumerate(lineas):
                ax.text(x + pad, y + cab + attr + pad + lh * (n + 0.5), l, va="center", fontsize=fs)
            y += h + gap
    _guardar(fig, "clases_dao_detalle", 300)
    print(f"clases_dao_detalle: {ancho_pag} x {alto_total:.2f} in (máximo {alto_max})")


# --------------------------------------------------------------- arquitectura
def _caja(ax, x, y, w, h, texto, fc="white", fs=13, radio=0.12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radio}",
                                fc=fc, ec=AZUL, lw=2))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=fs, linespacing=1.35)


def _capa(ax, y, h, titulo, carpeta, borde, fondo, color_titulo):
    ax.add_patch(FancyBboxPatch((0.3, y), 13.1, h, boxstyle="round,pad=0,rounding_size=0.18",
                                fc=fondo, ec=borde, lw=2))
    ax.text(0.55, y + 0.33, titulo, fontsize=15, weight="bold", color=color_titulo, va="center")
    ax.text(0.55, y + 0.68, carpeta, fontsize=12, color=color_titulo, va="center")


def _flecha(ax, x1, y1, x2, y2, punteada=False):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color=AZUL, lw=2, mutation_scale=18,
                                linestyle=(0, (4, 3)) if punteada else "-"))


def arquitectura():
    fig = plt.figure(figsize=(13.75, 12.3), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 13.75); ax.set_ylim(12.3, 0); ax.axis("off")

    _caja(ax, 2.9, 0.25, 3.75, 1.0, "Navegador web\n(formularios HTML + JS de quórum)", fc="#eeeeee")
    _flecha(ax, 4.775, 1.25, 4.775, 2.68); ax.text(4.9, 1.6, "HTTP", fontsize=11, color="#333")

    _capa(ax, 1.95, 2.2, "Capa de presentación", "presentation/", "#2e75b6", "#ecf3fa", AZUL)
    _caja(ax, 2.9, 2.7, 3.75, 1.05, "app.py: middlewares de sesión\nfirmada y cabeceras de seguridad", fs=12)
    _caja(ax, 7.4, 2.7, 2.7, 1.05, "routers/ FastAPI\n+ plantillas Jinja2", fs=12)
    _caja(ax, 10.7, 2.7, 2.5, 1.05, "dependencias.py\nCSRF y control\nde roles", fs=11.5)
    _flecha(ax, 6.65, 3.22, 7.4, 3.22); _flecha(ax, 10.1, 3.22, 10.7, 3.22, punteada=True)

    _capa(ax, 4.85, 2.2, "Capa de lógica de negocio", "application/ y domain/", "#bf9000", "#fff7e6", "#7f6000")
    _caja(ax, 5.75, 5.6, 4.35, 1.05, "application/services/\nAuth, Usuario, Conjunto, Censo, Asamblea,\nAsistencia, Sala, Votacion, Acta", fs=11.5)
    _caja(ax, 10.7, 5.6, 2.5, 1.05, "domain/reglas.py\nquórum y mayorías\n(Ley 675)", fs=11.5)
    _flecha(ax, 8.75, 3.75, 8.75, 5.6); _flecha(ax, 10.1, 6.12, 10.7, 6.12, punteada=True)

    _capa(ax, 7.75, 2.45, "Capa de persistencia", "infrastructure/", "#548235", "#eef5e9", "#375623")
    _caja(ax, 0.75, 8.8, 3.0, 1.05, "seguridad.py\nbcrypt y bloqueo\npor intentos", fs=11.5)
    _caja(ax, 4.2, 8.8, 3.25, 1.05, "db.py\nGestorTransacciones\nCOMMIT / ROLLBACK", fs=11.5)
    _caja(ax, 7.9, 8.8, 2.55, 1.05, "dao/\n14 DAO\n(uno por tabla)", fs=11.5)
    _caja(ax, 10.9, 8.8, 2.3, 1.05, "archivos.py\nlectura de\nExcel y CSV", fs=11.5)
    _flecha(ax, 6.4, 6.65, 5.83, 8.8); _flecha(ax, 8.6, 6.65, 9.17, 8.8)
    _flecha(ax, 5.95, 6.65, 3.2, 8.8); _flecha(ax, 9.6, 6.65, 12.05, 8.8)
    ax.plot([7.45, 7.9], [9.32, 9.32], color=AZUL, lw=2, ls=(0, (4, 3)))

    _caja(ax, 6.6, 10.95, 5.15, 1.0, "PostgreSQL\ntablas, índices únicos, CHECK y triggers", fc="#dce6f1")
    _flecha(ax, 9.17, 9.85, 9.17, 10.95); ax.text(9.3, 10.5, "SQL parametrizado", fontsize=11, color="#333")
    _guardar(fig, "arquitectura", 200)


# --------------------------------------------------------------- modelo relacional
def _esquema():
    """Tablas, columnas (tipo, PK, UQ) y llaves foráneas leídas de db/01_schema.sql."""
    import re
    sql = open(os.path.join(RAIZ, "db", "01_schema.sql"), encoding="utf-8").read()
    tablas = {}
    for nombre, cuerpo in re.findall(r'CREATE TABLE "(\w+)" \((.*?)\n\);', sql, re.S):
        cols, pk_comp = [], []
        for linea in cuerpo.strip().splitlines():
            linea = linea.strip().rstrip(",")
            m = re.match(r'PRIMARY KEY \((.*)\)', linea)
            if m:
                pk_comp = re.findall(r'"(\w+)"', m.group(1))
                continue
            m = re.match(r'"(\w+)" (\w+)(.*)', linea)
            if m:
                col, tipo, resto = m.groups()
                cols.append({"col": col, "tipo": tipo.lower(), "pk": "PRIMARY KEY" in resto,
                             "uq": "UNIQUE" in resto, "fk": False})
        for c in cols:
            c["pk"] = c["pk"] or c["col"] in pk_comp
        tablas[nombre] = cols
    for t, c in re.findall(r'ALTER TABLE "(\w+)" ADD FOREIGN KEY \("(\w+)"\)', sql):
        for col in tablas[t]:
            if col["col"] == c:
                col["fk"] = True
    return tablas


def modelo_relacional():
    tablas = _esquema()
    W, H, CAB, FILA = 2408, 1640, 40, 29
    pos = {  # x, y, ancho (misma disposición del modelo original)
        "acta_aprobacion": (80, 505, 330), "usuario": (80, 765, 330), "usuario_rol": (80, 1110, 330),
        "rol": (80, 1312, 330), "solicitud_censo": (510, 60, 340), "acta": (510, 505, 340),
        "resultado_votacion": (510, 960, 340), "asamblea": (950, 421, 475),
        "punto_orden_dia": (950, 960, 375), "voto": (950, 1330, 375), "conjunto": (1527, 40, 373),
        "convocatoria": (1527, 475, 373), "poder": (1527, 790, 373), "asistencia": (1527, 1100, 373),
        "unidad": (2002, 421, 366),
    }
    assert set(pos) == set(tablas), set(tablas) ^ set(pos)
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    pt = 72 / 100  # píxeles del lienzo -> puntos tipográficos

    def fila_y(t, col):
        i = [c["col"] for c in tablas[t]].index(col)
        return pos[t][1] + CAB + FILA * i + FILA / 2

    def abajo(t):
        return pos[t][1] + CAB + FILA * len(tablas[t])

    for t, cols in tablas.items():
        x, y, w = pos[t]
        h = CAB + FILA * len(cols)
        compuesta = len([k for k in cols if k["pk"]]) > 1
        ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=AZUL, lw=2.2, zorder=3))
        ax.add_patch(Rectangle((x, y), w, CAB, fc=AZUL, ec=AZUL, lw=2.2, zorder=3))
        ax.text(x + 14, y + CAB / 2, t, color="white", fontsize=19 * pt, weight="bold", va="center", zorder=4)
        for i, c in enumerate(cols):
            yy = y + CAB + FILA * i
            if c["fk"] or (c["pk"] and compuesta):
                ax.add_patch(Rectangle((x + 1.5, yy), w - 3, FILA, fc="#edf3fa", ec="none", zorder=3))
            if i:
                ax.plot([x, x + w], [yy, yy], color="#e3e7ec", lw=1, zorder=3)
            if c["pk"]:
                marca, color = "PK", AZUL
            elif c["fk"]:
                marca, color = "FK", AZUL
            elif c["uq"]:
                marca, color = "UQ", "#8a6d00"
            else:
                marca, color = "", "black"
            ax.text(x + 10, yy + FILA / 2, marca, color=color, fontsize=12 * pt, weight="bold", va="center", zorder=4)
            ax.text(x + 50, yy + FILA / 2, c["col"], fontsize=16 * pt, va="center", zorder=4,
                    weight="bold" if c["pk"] else "normal")
            ax.text(x + w - 10, yy + FILA / 2, c["tipo"], fontsize=13.5 * pt, color="#666", va="center",
                    ha="right", zorder=4)

    def relacion(puntos):
        """Lado 'muchos' (FK) en el primer punto y lado 'uno' (PK) en el último."""
        xs, ys = zip(*puntos)
        ax.plot(xs, ys, color="#555", lw=1.8, zorder=2)
        for (x0, y0), (x1, y1), tipo in ((puntos[0], puntos[1], "muchos"), (puntos[-1], puntos[-2], "uno")):
            dx, dy = (x1 > x0) - (x1 < x0), (y1 > y0) - (y1 < y0)
            nx, ny = -dy, dx
            if tipo == "muchos":
                for k in (-1, 1):
                    ax.plot([x0 + dx * 20, x0 + nx * 11 * k], [y0 + dy * 20, y0 + ny * 11 * k],
                            color="#555", lw=1.8, zorder=2)
            else:
                for d in (10, 18):
                    ax.plot([x0 + dx * d - nx * 10, x0 + dx * d + nx * 10],
                            [y0 + dy * d - ny * 10, y0 + dy * d + ny * 10], color="#555", lw=1.8, zorder=2)

    def R(t): return pos[t][0] + pos[t][2]
    def L(t): return pos[t][0]
    def T(t): return pos[t][1]

    y = fila_y("asamblea", "conjunto_id")
    relacion([(R("asamblea"), y), (1466, y), (1466, 408), (1587, 408), (1587, abajo("conjunto"))])
    ya = fila_y("asamblea", "asamblea_original_id")
    relacion([(L("asamblea"), ya), (893, ya), (893, ya + 58), (L("asamblea"), ya + 58)])
    y = fila_y("unidad", "conjunto_id")
    relacion([(L("unidad"), y), (1962, y), (1962, 408), (1840, 408), (1840, abajo("conjunto"))])
    relacion([(245, T("usuario_rol")), (245, abajo("usuario"))])
    relacion([(245, abajo("usuario_rol")), (245, T("rol"))])
    y = fila_y("convocatoria", "asamblea_id"); relacion([(L("convocatoria"), y), (R("asamblea"), y)])
    y = fila_y("convocatoria", "unidad_id"); relacion([(R("convocatoria"), y), (L("unidad"), y)])
    y = fila_y("poder", "asamblea_id"); relacion([(L("poder"), y), (1400, y), (1400, abajo("asamblea"))])
    y = fila_y("poder", "unidad_id"); relacion([(R("poder"), y), (2063, y), (2063, abajo("unidad"))])
    y = fila_y("asistencia", "asamblea_id"); relacion([(L("asistencia"), y), (1368, y), (1368, abajo("asamblea"))])
    y = fila_y("asistencia", "unidad_id"); relacion([(R("asistencia"), y), (2117, y), (2117, abajo("unidad"))])
    relacion([(1714, T("asistencia")), (1714, abajo("poder"))])
    relacion([(1071, T("punto_orden_dia")), (1071, abajo("asamblea"))])
    relacion([(1071, T("voto")), (1071, abajo("punto_orden_dia"))])
    y = fila_y("voto", "unidad_id"); relacion([(R("voto"), y), (2170, y), (2170, abajo("unidad"))])
    y = fila_y("voto", "usuario_id"); relacion([(L("voto"), y), (457, y), (457, 991), (R("usuario"), 991)])
    y = fila_y("resultado_votacion", "punto_id"); relacion([(R("resultado_votacion"), y), (L("punto_orden_dia"), y)])
    y = fila_y("acta", "asamblea_id"); relacion([(R("acta"), y), (L("asamblea"), y)])
    y = fila_y("acta_aprobacion", "acta_id"); relacion([(R("acta_aprobacion"), y), (L("acta"), y)])
    y = fila_y("acta_aprobacion", "usuario_id")
    yu = fila_y("usuario", "id")
    relacion([(L("acta_aprobacion"), y), (40, y), (40, yu), (L("usuario"), yu)])
    y = fila_y("solicitud_censo", "unidad_id")
    relacion([(R("solicitud_censo"), y), (1480, y), (1480, 18), (2185, 18), (2185, T("unidad"))])
    y = fila_y("solicitud_censo", "revisado_por")
    yn = fila_y("usuario", "nombre")
    relacion([(L("solicitud_censo"), y), (462, y), (462, yn), (R("usuario"), yn)])

    ax.text(47, 48, "Notación:", fontsize=15 * pt, weight="bold")
    relacion([(47, 94), (128, 94)])
    ax.text(148, 94, "muchos (FK)  →  uno (PK)", fontsize=14 * pt, va="center")
    ax.text(47, 128, "PK llave primaria, FK llave foránea, UQ única", fontsize=14 * pt, va="center")
    _guardar(fig, "modelo_relacional", 223)


# --------------------------------------------------------------- clases DAO: estructura
def clases_dao_estructura():
    """Herencia BaseDAO -> DAO de cada tabla y dependencias con servicios y GestorTransacciones."""
    clases = _metodos_dao()
    servicios = sorted(os.path.basename(f)[:-11].capitalize() + "Service"
                       for f in glob.glob(os.path.join(RAIZ, "application", "services", "*_service.py")))
    W, H = 2140, 1780
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    pt = 72 / 100
    GRIS = "#555"

    def clase(x, y, w, estereotipo, nombre, atributos, metodos, fondo="#dce6f1", lh=36):
        cab = 70 if estereotipo else 50
        h = cab + 16 + lh * len(atributos) + (16 + lh * len(metodos) if metodos else 18)
        ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=AZUL, lw=2.2, zorder=3))
        ax.add_patch(Rectangle((x, y), w, cab, fc=fondo, ec=AZUL, lw=2.2, zorder=3))
        if estereotipo:
            ax.text(x + w / 2, y + 20, f"«{estereotipo}»", ha="center", va="center", fontsize=15 * pt, zorder=4)
        ax.text(x + w / 2, y + cab - 24, nombre, ha="center", va="center", fontsize=23 * pt, weight="bold", zorder=4)
        yy = y + cab + 8
        for a in atributos:
            ax.text(x + 14, yy + lh / 2, a, va="center", fontsize=19 * pt, zorder=4); yy += lh
        yy += 8
        ax.plot([x, x + w], [yy, yy], color=AZUL, lw=1.2, zorder=4)
        yy += 8
        for m in metodos:
            ax.text(x + 14, yy + lh / 2, m, va="center", fontsize=19 * pt, zorder=4); yy += lh
        return h

    def flecha(puntos, texto=None, pos_texto=None):
        xs, ys = zip(*puntos)
        ax.plot(xs, ys, color=GRIS, lw=1.8, ls=(0, (5, 3)), zorder=2)
        (x0, y0), (x1, y1) = puntos[-2], puntos[-1]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", color=GRIS, lw=1.8, mutation_scale=22))
        if texto:
            ax.text(*pos_texto, texto, fontsize=17 * pt, color=GRIS, ha="center", va="center")

    # Fila superior
    clase(32, 200, 520, "utility", "GestorTransacciones (db.py)", ["- database_url: str"],
          ["+ transaccion(aislamiento): Connection", "+ solo_lectura(): Connection"], fondo="#e2efda")
    lineas, actual = [], ""
    for s in servicios:
        pieza = s + ", "
        if len(actual) + len(pieza) > 34:
            lineas.append(actual.rstrip()); actual = ""
        actual += pieza
    lineas.append(actual.rstrip(", "))
    h_serv = clase(672, 146, 504, "capa", "Servicios de negocio", lineas,
                   ["abren la transacción y crean los", "DAO con la misma conexión"], fondo="#fff2cc")
    clase(1306, 215, 356, "library", "psycopg.Connection", [], ["+ execute(sql, params)", "+ transaction()"],
          fondo="#eeeeee")

    # BaseDAO al centro
    bx, by, bw = 932, 920, 535
    clase(bx, by, bw, "abstract", "BaseDAO", ["# conn: psycopg.Connection", "+ tabla: str"],
          ["+ __init__(conn)", "# _uno(sql, params): dict", "# _todos(sql, params): list[dict]",
           "# _escalar(sql, params)", "+ obtener(id_, bloquear): dict", "+ listar(): list[dict]"],
          fondo="#c9daf0")

    # DAO concretos: mitad a cada lado
    nombres = list(clases)
    izq, der = nombres[:(len(nombres) + 1) // 2], nombres[(len(nombres) + 1) // 2:]
    alto, paso = 120, 158
    for columna, x, lista in ((0, 300, izq), (1, 1686, der)):
        y0 = 584 if columna == 0 else 584 + (len(izq) - len(lista)) * paso / 2
        for i, n in enumerate(lista):
            y = y0 + i * paso
            clase(x, y, 413, None, n, [f'tabla = "{clases[n][0]}"'], [], lh=34)
            if columna == 0:
                inicio, fin = (x + 413, y + alto / 2), (bx, by + 70 + 330 * (i + 0.5) / len(lista))
            else:
                inicio, fin = (x, y + alto / 2), (bx + bw, by + 70 + 330 * (i + 0.5) / len(lista))
            ax.plot([inicio[0], fin[0]], [inicio[1], fin[1]], color=GRIS, lw=1.8, zorder=2)
            # Triángulo hueco de herencia en el extremo de BaseDAO
            import math
            ang = math.atan2(fin[1] - inicio[1], fin[0] - inicio[0])
            punta = fin
            base1 = (fin[0] - 30 * math.cos(ang) + 14 * math.sin(ang), fin[1] - 30 * math.sin(ang) - 14 * math.cos(ang))
            base2 = (fin[0] - 30 * math.cos(ang) - 14 * math.sin(ang), fin[1] - 30 * math.sin(ang) + 14 * math.cos(ang))
            ax.add_patch(plt.Polygon([punta, base1, base2], closed=True, fc="white", ec=GRIS, lw=1.8, zorder=3))

    # Dependencias
    flecha([(672, 302), (553, 302)], "«usa»", (612, 275))
    flecha([(1054, 146 + h_serv), (1054, by)], "«usa»", (1100, 690))
    flecha([(1451, by), (1451, 392)], "«usa»", (1497, 655))
    flecha([(292, 200), (292, 48), (1484, 48), (1484, 215)], "«crea»", (888, 22))

    ax.text(1200, 1700, "△ herencia (extends BaseDAO)\n⇢ dependencia «usa» / «crea»", ha="center", va="center",
            fontsize=17 * pt, color="#444")
    _guardar(fig, "clases_dao_estructura", 154)


if __name__ == "__main__":
    cronograma()
    modelo_relacional()
    clases_dao_estructura()
    clases_dao_detalle()
    arquitectura()
    print("Diagramas generados en", SALIDA)
