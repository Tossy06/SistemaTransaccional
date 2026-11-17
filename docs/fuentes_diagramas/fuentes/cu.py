import math, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyBboxPatch, Polygon
from geom import verificar

AZ, AZ2, GR, F = "#1f4e79", "#2e75b6", "#555555", "DejaVu Sans"
nombres = {"01": "Iniciar sesión", "02": "Gestionar usuarios y roles", "03": "Gestionar conjuntos y unidades",
 "04": "Registrar asamblea y orden del día", "05": "Generar convocatoria", "06": "Registrar asistencia y poderes",
 "07": "Calcular quórum", "08": "Gestionar segunda convocatoria", "09": "Abrir y cerrar votación",
 "10": "Emitir voto ponderado", "11": "Generar acta", "12": "Aprobar acta", "13": "Consultar histórico"}
CX, RX, RY, DY, Y0 = 6.0, 2.3, 0.32, 0.86, 2.6
orden = ["02", "03", "04", "05", "09", "11", "08", "07", "06", "10", "12"]
extra = {"07": 0.35, "06": 0.7, "10": 0.7, "12": 0.7}
el = {c: (CX, Y0 + i * DY + extra.get(c, 0), RX, RY) for i, c in enumerate(orden)}
el["01"] = (4.6, 1.55, 1.3, RY + 0.04); el["13"] = (7.4, 1.55, 1.3, RY + 0.04)
BOX = (3.1, 0.95, 8.9, el["12"][1] + 1.05)

def borde(c, ang):  # punto del borde de la elipse (ángulo en grados, 0 = derecha, 90 = abajo)
    cx, cy, rx, ry = el[c]
    return (cx + rx * math.cos(math.radians(ang)), cy + ry * math.sin(math.radians(ang)))

# ------------------------------------------------ actores (x, y del cuerpo)
XL, XR = 1.0, 10.75
act = {"Administrador": (XL, el["05"][1]), "Recepcionista": (XL, el["06"][1]),
       "Sistema": (XR, (el["05"][1] + el["07"][1]) / 2),
       "Copropietario": (XR, el["10"][1] - 0.55), "Apoderado": (XR, el["10"][1] + 0.85),
       "Presidente": (XR, el["12"][1] + 1.45), "Secretario": (XR, el["12"][1] + 2.85),
       "Usuario": (CX, -0.15)}
lineas, flechas = {}, []

def abanico(actor, destinos, lado):
    x, y = act[actor]
    n = len(destinos)
    destinos = sorted(destinos, key=lambda d: d[1])
    for k, (c, yy, ang) in enumerate(destinos):
        paso = 0.13
        sy = y - 0.11 - paso * (n - 1) / 2 + paso * k
        sx = x + (0.42 if lado == "L" else -0.42) if actor != "Sistema" else x - 0.72
        lineas[f"{actor}-{c}"] = [(sx, sy), borde(c, ang)]

abanico("Administrador", [(c, el[c][1], 180) for c in ["02", "03", "04", "05", "09", "11", "08"]], "L")
abanico("Recepcionista", [("06", el["06"][1], 180)], "L")
abanico("Sistema", [(c, el[c][1], 0) for c in ["05", "09", "11", "07"]], "R")
abanico("Copropietario", [("10", el["10"][1] - 0.1, -28)], "R")
abanico("Apoderado", [("10", el["10"][1] + 0.1, 28)], "R")
abanico("Presidente", [("12", el["12"][1] + 0.05, 18)], "R")
abanico("Secretario", [("12", el["12"][1] + 0.1, 50)], "R")
ux, uy = act["Usuario"]
lineas["Usuario-01"] = [(ux - 0.22, uy + 0.45), borde("01", -55)]
lineas["Usuario-13"] = [(ux + 0.22, uy + 0.45), borde("13", -125)]

# generalizaciones hacia Usuario (rutas ortogonales en carriles propios)
gen = {}
ax_, ay_ = act["Administrador"]
gen["Administrador"] = [(ax_ - 0.3, ay_ - 0.1), (0.08, ay_ - 0.1), (0.08, uy + 0.05), (ux - 0.42, uy + 0.05)]
rx_, ry_ = act["Recepcionista"]
gen["Recepcionista"] = [(rx_ - 0.3, ry_), (-0.3, ry_), (-0.3, uy - 0.25), (ux - 0.42, uy - 0.25)]
carriles = {"Copropietario": (11.95, uy + 0.2), "Apoderado": (12.3, uy - 0.05), "Presidente": (12.65, uy - 0.3), "Secretario": (13.0, uy - 0.55)}
for a, (lx, ly) in carriles.items():
    x, y = act[a]
    gen[a] = [(x + 0.3, y), (lx, y), (lx, ly), (ux + 0.42, ly)]
for a, pts in gen.items():
    lineas[f"gen-{a}"] = pts
# include / extend (verticales en el hueco central)
lineas["include"] = [borde("06", -90), borde("07", 90)]
lineas["extend"] = [borde("08", 90), borde("07", -90)]
lineas["include"] = [(CX - 0.35, el["06"][1] - RY + 0.004), (CX - 0.35, el["07"][1] + RY - 0.004)]
lineas["extend"] = [(CX + 0.35, el["08"][1] + RY - 0.004), (CX + 0.35, el["07"][1] - RY + 0.004)]

# cajas de texto y figuras de actores para el verificador
cajas = {}
for a, (x, y) in act.items():
    if a == "Sistema":
        cajas[a] = (x - 0.7, y - 0.33, x + 0.7, y + 0.33)
    else:
        cajas[a + "-fig"] = (x - 0.24, y - 0.6, x + 0.24, y + 0.38)
        w = 0.1 * len(a) / 2 + 0.05
        ly = y - 0.98 if a in ("Usuario", "Administrador") else y + 0.62
        cajas[a + "-txt"] = (x - w, ly - 0.13, x + w, ly + 0.13)
cajas["titulo"] = (BOX[0] + 0.1, BOX[3] - 0.68, BOX[0] + 3.3, BOX[3] - 0.08)
cajas["lbl-include"] = (CX - 1.5, el["07"][1] + 0.44, CX - 0.45, el["07"][1] + 0.6)
cajas["lbl-extend"] = (CX + 0.45, el["07"][1] - 0.6, CX + 1.45, el["07"][1] - 0.44)
# excluir del chequeo la caja propia de cada actor en sus líneas: se usan márgenes en los puntos de salida
problemas = verificar(lineas, {k: v for k, v in cajas.items()}, 0.09, "casos de uso",
                      {c: v for c, v in el.items()})

# ------------------------------------------------ dibujo
xmin, xmax, ymin, ymax = -0.55, 13.3, -1.35, act["Secretario"][1] + 0.95
fig = plt.figure(figsize=(xmax - xmin, ymax - ymin)); ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymax, ymin); ax.axis("off")
ax.add_patch(FancyBboxPatch((BOX[0], BOX[1]), BOX[2] - BOX[0], BOX[3] - BOX[1], boxstyle="round,pad=0,rounding_size=0.25", fill=False, ec=AZ, lw=1.6))
ax.text(BOX[0] + 0.2, BOX[3] - 0.36, "Sistema de Gestión\nTransaccional de Asambleas", color=AZ, fontsize=12.5, fontweight="bold", family=F, va="center")
for c, (cx, cy, rx, ry) in el.items():
    ax.add_patch(Ellipse((cx, cy), 2 * rx, 2 * ry, fc="white", ec=AZ2, lw=1.4, zorder=3))
    ax.text(cx, cy, f"CU-{c} {nombres[c]}" if rx > 1.5 else f"CU-{c}\n{nombres[c]}", ha="center", va="center", fontsize=12, family=F, zorder=4)
def monigote(x, y, nombre):
    ax.add_patch(plt.Circle((x, y - 0.45), 0.13, fc="white", ec=AZ, lw=1.5, zorder=3))
    for xs, ys in (([x, x], [y - 0.32, y + 0.05]), ([x - 0.22, x + 0.22], [y - 0.18, y - 0.18]),
                   ([x, x - 0.18], [y + 0.05, y + 0.35]), ([x, x + 0.18], [y + 0.05, y + 0.35])):
        ax.plot(xs, ys, c=AZ, lw=1.5, zorder=3)
    ly = y - 0.98 if nombre in ("Usuario", "Administrador") else y + 0.62
    ax.text(x, ly, nombre, ha="center", va="center", fontsize=12, fontweight="bold", color=AZ, family=F)
for a, (x, y) in act.items():
    if a == "Sistema":
        ax.add_patch(FancyBboxPatch((x - 0.68, y - 0.31), 1.36, 0.62, boxstyle="round,pad=0,rounding_size=0.1", fc="#eeeeee", ec="#555", ls="--", lw=1.2))
        ax.text(x, y, "«sistema»\nSistema", ha="center", va="center", fontsize=11.5, family=F)
    else:
        monigote(x, y, a)
for k, pts in lineas.items():
    xs, ys = zip(*pts)
    if k.startswith("gen-"):
        ax.plot(xs, ys, c=GR, lw=1.0, zorder=2)
        (x1, y1), (x0, y0) = pts[-1], pts[-2]
        d = 1 if x1 > x0 else -1
        ax.add_patch(Polygon([(x1, y1), (x1 - d * 0.2, y1 - 0.09), (x1 - d * 0.2, y1 + 0.09)], closed=True, fc="white", ec=GR, lw=1.0, zorder=3))
    elif k in ("include", "extend"):
        ax.annotate("", xy=pts[1], xytext=pts[0], arrowprops=dict(arrowstyle="->", ls="--", color=AZ2, lw=1.2))
    else:
        ax.plot(xs, ys, c=GR, lw=1.0, zorder=2)
ax.text(CX - 0.45, el["07"][1] + 0.52, "«include»", ha="right", va="center", fontsize=10.5, color=AZ2, family=F)
ax.text(CX + 0.45, el["07"][1] - 0.52, "«extend»", ha="left", va="center", fontsize=10.5, color=AZ2, family=F)
_base = (sys.argv[1] if len(sys.argv) > 1 else "../../diagramas/casos_uso.pdf").rsplit(".", 1)[0]
fig.savefig(f"{_base}.pdf", facecolor="white")  # PDF vectorial
print("tamaño", round(xmax - xmin, 1), round(ymax - ymin, 1))
