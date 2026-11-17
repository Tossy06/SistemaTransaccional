"""Modelo relacional redibujado: mismas tablas, columnas, tipos y FK que modelo_asambleas.sql.
Rutas ortogonales definidas a mano + verificación automática de cruces y solapes."""
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

from geom import verificar

SQL = open("/mnt/user-data/uploads/ca4c4a2f-modelo_asambleas.sql", encoding="utf-8").read()

# ------------------------------------------------------------ leer el modelo del SQL
tablas = {}
for m in re.finditer(r'CREATE TABLE "(\w+)" \((.*?)\n\);', SQL, re.S):
    cols = []
    for linea in m.group(2).strip().splitlines():
        linea = linea.strip().rstrip(",")
        cm = re.match(r'"(\w+)" (\w+)', linea)
        if cm:
            cols.append((cm.group(1), cm.group(2).lower(), "PRIMARY KEY" in linea, "UNIQUE" in linea))
        pk = re.match(r'PRIMARY KEY \((.*)\)', linea)
        if pk:
            claves = re.findall(r'"(\w+)"', pk.group(1))
            cols = [(n, t, n in claves or p, u) for n, t, p, u in cols]
    tablas[m.group(1)] = cols
fks = re.findall(r'ALTER TABLE "(\w+)" ADD FOREIGN KEY \("(\w+)"\) REFERENCES "(\w+)" \("(\w+)"\)', SQL)
assert len(tablas) == 14 and len(fks) == 20, (len(tablas), len(fks))
fk_cols = {(t, c) for t, c, _, _ in fks}

# ------------------------------------------------------------ geometría (pulgadas, y hacia abajo)
HEAD, ROW, CH = 0.30, 0.215, 0.068
def ancho(t):
    n = max(len(c[0]) for c in tablas[t] + [(t, "", 0, 0)])
    ty = max(len(c[1]) for c in tablas[t])
    return round(0.42 + CH * n + CH * ty + 0.25, 2)
W = {t: ancho(t) for t in tablas}
H = {t: HEAD + ROW * len(tablas[t]) for t in tablas}
G = 0.75  # separación entre columnas
W["asamblea"] = max(W["asamblea"], max(W["punto_orden_dia"], W["voto"]) + 0.75)

pos = {}
xLLL = 0.0
xLL = xLLL + max(W["acta_aprobacion"], W["usuario"], W["usuario_rol"], W["rol"]) + G
xL = xLL + max(W["acta"], W["resultado_votacion"]) + G
xM = xL + W["asamblea"] + G
xR = xM + max(W["convocatoria"], W["poder"], W["asistencia"], W["conjunto"]) + G
WM = max(W["convocatoria"], W["poder"], W["asistencia"], W["conjunto"])
for t in ("convocatoria", "poder", "asistencia", "conjunto"):
    W[t] = WM
W["punto_orden_dia"] = W["voto"] = max(W["punto_orden_dia"], W["voto"])
W["usuario_rol"] = W["rol"] = W["acta_aprobacion"] = W["usuario"] = max(W["usuario"], W["acta_aprobacion"], W["usuario_rol"], W["rol"])
W["acta"] = W["resultado_votacion"] = max(W["acta"], W["resultado_votacion"])
assert W["punto_orden_dia"] < W["asamblea"] - 0.6, "punto debe dejar libre la parte derecha de asamblea"

pos["asamblea"] = (xL, 0.0)
pos["conjunto"] = (xM, -0.6 - H["conjunto"])
pos["convocatoria"] = (xM, 0.40)
pos["poder"] = (xM, 0.40 + H["convocatoria"] + 0.45)
pos["asistencia"] = (xM, pos["poder"][1] + H["poder"] + 0.45)
pos["unidad"] = (xR, 0.0)
pos["punto_orden_dia"] = (xL, H["asamblea"] + 0.55)
pos["resultado_votacion"] = (xLL, pos["punto_orden_dia"][1])
pos["acta"] = (xLL, 0.62)
pos["acta_aprobacion"] = (xLLL, 0.62)
pos["usuario"] = (xLLL, pos["acta_aprobacion"][1] + H["acta_aprobacion"] + 0.55)
pos["usuario_rol"] = (xLLL, pos["usuario"][1] + H["usuario"] + 0.55)
pos["rol"] = (xLLL, pos["usuario_rol"][1] + H["usuario_rol"] + 0.55)
y_voto = max(pos["punto_orden_dia"][1] + H["punto_orden_dia"] + 0.55,
             pos["asistencia"][1] + H["asistencia"] + 0.25 - HEAD - ROW * 1.5)
pos["voto"] = (xL, y_voto)

L = lambda t: pos[t][0]
R = lambda t: pos[t][0] + W[t]
T = lambda t: pos[t][1]
B = lambda t: pos[t][1] + H[t]
def Y(t, col):
    i = [c[0] for c in tablas[t]].index(col)
    return T(t) + HEAD + ROW * (i + 0.5)

# ------------------------------------------------------------ rutas (hijo -> padre)
yC = (B("conjunto") + T("convocatoria")) / 2
xa1, xa2 = R("asamblea") - 0.18, R("asamblea") - 0.42
xu1, xu2, xu3 = L("unidad") + 0.45, L("unidad") + 0.85, L("unidad") + 1.25
cxM = L("convocatoria") + W["convocatoria"] / 2
xl = R("usuario") + 0.35
rutas = {
 ("asamblea", "conjunto_id"): [(R("asamblea"), Y("asamblea", "conjunto_id")), (R("asamblea") + 0.3, Y("asamblea", "conjunto_id")),
                               (R("asamblea") + 0.3, yC), (L("conjunto") + 0.45, yC), (L("conjunto") + 0.45, B("conjunto"))],
 ("unidad", "conjunto_id"): [(L("unidad"), Y("unidad", "conjunto_id")), (L("unidad") - 0.3, Y("unidad", "conjunto_id")),
                             (L("unidad") - 0.3, yC), (R("conjunto") - 0.45, yC), (R("conjunto") - 0.45, B("conjunto"))],
 ("convocatoria", "asamblea_id"): [(L("convocatoria"), Y("convocatoria", "asamblea_id")), (R("asamblea"), Y("convocatoria", "asamblea_id"))],
 ("convocatoria", "unidad_id"): [(R("convocatoria"), Y("convocatoria", "unidad_id")), (L("unidad"), Y("convocatoria", "unidad_id"))],
 ("poder", "asamblea_id"): [(L("poder"), Y("poder", "asamblea_id")), (xa1, Y("poder", "asamblea_id")), (xa1, B("asamblea"))],
 ("poder", "unidad_id"): [(R("poder"), Y("poder", "unidad_id")), (xu1, Y("poder", "unidad_id")), (xu1, B("unidad"))],
 ("asistencia", "asamblea_id"): [(L("asistencia"), Y("asistencia", "asamblea_id")), (xa2, Y("asistencia", "asamblea_id")), (xa2, B("asamblea"))],
 ("asistencia", "unidad_id"): [(R("asistencia"), Y("asistencia", "unidad_id")), (xu2, Y("asistencia", "unidad_id")), (xu2, B("unidad"))],
 ("asistencia", "poder_id"): [(cxM, T("asistencia")), (cxM, B("poder"))],
 ("punto_orden_dia", "asamblea_id"): [(L("asamblea") + 0.9, T("punto_orden_dia")), (L("asamblea") + 0.9, B("asamblea"))],
 ("resultado_votacion", "punto_id"): [(R("resultado_votacion"), Y("resultado_votacion", "punto_id")), (L("punto_orden_dia"), Y("resultado_votacion", "punto_id"))],
 ("voto", "punto_id"): [(L("voto") + 0.9, T("voto")), (L("voto") + 0.9, B("punto_orden_dia"))],
 ("voto", "unidad_id"): [(R("voto"), Y("voto", "unidad_id")), (xu3, Y("voto", "unidad_id")), (xu3, B("unidad"))],
 ("voto", "usuario_id"): [(L("voto"), Y("voto", "usuario_id")), (xl, Y("voto", "usuario_id")), (xl, B("usuario") - 0.35), (R("usuario"), B("usuario") - 0.35)],
 ("acta", "asamblea_id"): [(R("acta"), Y("acta", "asamblea_id")), (L("asamblea"), Y("acta", "asamblea_id"))],
 ("asamblea", "asamblea_original_id"): [(L("asamblea"), Y("asamblea", "asamblea_original_id")), (L("asamblea") - 0.42, Y("asamblea", "asamblea_original_id")),
                                        (L("asamblea") - 0.42, Y("asamblea", "fecha_creacion")), (L("asamblea"), Y("asamblea", "fecha_creacion"))],
 ("acta_aprobacion", "acta_id"): [(R("acta_aprobacion"), Y("acta_aprobacion", "acta_id")), (L("acta"), Y("acta_aprobacion", "acta_id"))],
 ("acta_aprobacion", "usuario_id"): [(L("acta_aprobacion"), Y("acta_aprobacion", "usuario_id")), (L("acta_aprobacion") - 0.3, Y("acta_aprobacion", "usuario_id")),
                                     (L("acta_aprobacion") - 0.3, T("usuario") + 0.4), (L("usuario"), T("usuario") + 0.4)],
 ("usuario_rol", "usuario_id"): [(L("usuario_rol") + W["usuario_rol"] / 2, T("usuario_rol")), (L("usuario") + W["usuario"] / 2, B("usuario"))],
 ("usuario_rol", "rol_id"): [(L("rol") + W["rol"] / 2, T("rol")), (L("usuario_rol") + W["usuario_rol"] / 2, B("usuario_rol"))],
}
assert set(rutas) == fk_cols, set(fk_cols) ^ set(rutas)
# validar que los extremos verticales/horizontales de cada ruta sean ortogonales
for k, pts in rutas.items():
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        assert abs(x0 - x1) < 1e-9 or abs(y0 - y1) < 1e-9, k

cajas = {t: (L(t), T(t), R(t), B(t)) for t in tablas}
cajas["leyenda"] = (x_min + 0.25 if False else min(L(t) for t in tablas) - 0.35, min(T(t) for t in tablas) + 0.1, min(L(t) for t in tablas) + 3.2, min(T(t) for t in tablas) + 1.1)
x_min = min(L(t) for t in tablas) - 0.6
y_min = min(T(t) for t in tablas) - 0.3
problemas = verificar({f"{a}.{b}": v for (a, b), v in rutas.items()}, cajas, 0.12, "modelo relacional")

# ------------------------------------------------------------ dibujo
AZ, AZC, GR = "#1f4e79", "#dbe7f3", "#555555"
x_min = min(L(t) for t in tablas) - 0.6
x_max = max(R(t) for t in tablas) + 0.3
y_min = min(T(t) for t in tablas) - 0.3
y_max = max(B(t) for t in tablas) + 0.3
fig = plt.figure(figsize=(x_max - x_min, y_max - y_min))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(x_min, x_max); ax.set_ylim(y_max, y_min); ax.axis("off")
F = "DejaVu Sans"
for t, cols in tablas.items():
    x, y = pos[t]
    ax.add_patch(Rectangle((x, y), W[t], H[t], fc="white", ec=AZ, lw=1.2, zorder=3))
    ax.add_patch(Rectangle((x, y), W[t], HEAD, fc=AZ, ec=AZ, lw=1.2, zorder=3))
    ax.text(x + 0.1, y + HEAD / 2, t, color="white", fontsize=10, fontweight="bold", va="center", family=F, zorder=4)
    for i, (n, ty, pk, uq) in enumerate(cols):
        yy = y + HEAD + ROW * (i + 0.5)
        if (t, n) in fk_cols:
            ax.add_patch(Rectangle((x, yy - ROW / 2), W[t], ROW, fc="#eef4fb", ec="none", zorder=3))
        etiqueta = "PK" if pk else ("FK" if (t, n) in fk_cols else ("UQ" if uq else ""))
        ax.text(x + 0.07, yy, etiqueta, fontsize=6.5, color=AZ if etiqueta != "UQ" else "#7f6000", fontweight="bold", va="center", family=F, zorder=4)
        ax.text(x + 0.38, yy, n, fontsize=8.5, va="center", family=F, zorder=4, fontweight="bold" if pk else "normal")
        ax.text(x + W[t] - 0.08, yy, ty, fontsize=7.5, va="center", ha="right", color="#666666", family=F, zorder=4)
        if i:
            ax.plot([x, x + W[t]], [yy - ROW / 2] * 2, color="#e3e8ef", lw=0.5, zorder=3)

def dir_unit(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    n = (dx * dx + dy * dy) ** 0.5
    return dx / n, dy / n

for (t, c), pts in rutas.items():
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=GR, lw=1.1, zorder=2, solid_joinstyle="miter")
    # extremo hijo: pata de gallo (muchos)
    (px, py), (qx, qy) = pts[0], pts[1]
    ux, uy = dir_unit(pts[0], pts[1]); nx, ny = -uy, ux
    tip = (px + ux * 0.14, py + uy * 0.14)
    for s in (-1, 0, 1):
        ax.plot([tip[0], px + nx * 0.07 * s], [tip[1], py + ny * 0.07 * s], color=GR, lw=1.1, zorder=2)
    # extremo padre: doble barra (uno y solo uno)
    (px, py), (qx, qy) = pts[-1], pts[-2]
    ux, uy = dir_unit(pts[-1], pts[-2]); nx, ny = -uy, ux
    for d in (0.08, 0.13):
        cx, cy = px + ux * d, py + uy * d
        ax.plot([cx - nx * 0.065, cx + nx * 0.065], [cy - ny * 0.065, cy + ny * 0.065], color=GR, lw=1.1, zorder=2)

# leyenda
lx, ly = x_min + 0.35, y_min + 0.45
ax.text(lx, ly - 0.05, "Notación:", fontsize=8, fontweight="bold", family=F)
ax.plot([lx, lx + 0.6], [ly + 0.25, ly + 0.25], color=GR, lw=1.1)
for s in (-1, 0, 1):
    ax.plot([lx + 0.14, lx], [ly + 0.25, ly + 0.25 + 0.07 * s], color=GR, lw=1.1)
for d in (0.08, 0.13):
    ax.plot([lx + 0.6 - d] * 2, [ly + 0.185, ly + 0.315], color=GR, lw=1.1)
ax.text(lx + 0.75, ly + 0.25, "muchos (FK)  →  uno (PK)", fontsize=7.5, va="center", family=F)
ax.text(lx, ly + 0.5, "PK llave primaria · FK llave foránea · UQ única", fontsize=7.5, va="center", family=F)

fig.savefig(sys.argv[1] if len(sys.argv) > 1 else "modelo_relacional.png", dpi=300, facecolor="white")
print("tamaño (in):", round(x_max - x_min, 2), "x", round(y_max - y_min, 2))
sys.exit(1 if problemas else 0)
