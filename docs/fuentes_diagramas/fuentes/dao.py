import glob, re, sys, textwrap
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from geom import verificar

AZ, AZC, GR, F = "#1f4e79", "#dbe7f3", "#555555", "DejaVu Sans"
# ------------------------------------------------ leer clases del código fuente
clases = {}
for f in sorted(glob.glob("/home/claude/asambleas/app/dao/*_dao.py")):
    src = open(f).read()
    for m in re.finditer(r"class (\w+)(?:\((\w+)\))?:(.*?)(?=\nclass |\Z)", src, re.S):
        nombre, base, cuerpo = m.groups()
        tabla = re.search(r'tabla = "(\w+)"', cuerpo)
        met = []
        for mm in re.finditer(r"def (\w+)\(self(?:, )?([^)]*)\)(?: -> ([^:]+))?:", cuerpo):
            n, args, ret = mm.groups()
            args = ", ".join(a.split(":")[0].split("=")[0].strip() for a in args.split(",") if a.strip())
            met.append(("#" if n.startswith("_") else "+") + f" {n}({args})" + (f": {ret.strip()}" if ret else ""))
        clases[nombre] = (tabla.group(1) if tabla else None, met)
base_met = clases.pop("BaseDAO")[1]
daos = sorted(clases)
assert len(daos) == 13

LH = 0.22  # alto de línea
def caja(ax, x, y, w, titulo, estereo, atributos, metodos, color=AZC, fs=9.5, h_min=0):
    """Dibuja una clase UML y devuelve su alto."""
    h_head = 0.42 if estereo else 0.3
    h = max(h_min, h_head + (len(atributos) * LH + 0.1 if atributos else 0.12) + (len(metodos) * LH + 0.1 if metodos else 0.12))
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=AZ, lw=1.2, zorder=3))
    ax.add_patch(Rectangle((x, y), w, h_head, fc=color, ec=AZ, lw=1.2, zorder=3))
    if estereo:
        ax.text(x + w / 2, y + 0.13, f"«{estereo}»", ha="center", va="center", fontsize=fs - 2, family=F, zorder=4)
    ax.text(x + w / 2, y + h_head - 0.15, titulo, ha="center", va="center", fontsize=fs + 0.5, fontweight="bold", family=F, zorder=4)
    yy = y + h_head
    for bloque in (atributos, metodos):
        yy += 0.05
        for linea in bloque:
            ax.text(x + 0.09, yy + LH / 2, linea, va="center", fontsize=fs - 1, family=F, zorder=4)
            yy += LH
        yy += 0.05
        if bloque is atributos:
            ax.plot([x, x + w], [yy, yy], color=AZ, lw=0.8, zorder=4)
    return h

def alto(estereo, atributos, metodos):
    return (0.42 if estereo else 0.3) + (len(atributos) * LH + 0.1 if atributos else 0.12) + (len(metodos) * LH + 0.1 if metodos else 0.12)

# =============================================================== Figura A: estructura
izq, der = daos[:7], daos[7:]
WB, WD, GAPC = 3.3, 2.55, 1.35
xL0, xB = 0.0, 2.55 + GAPC
xR0 = xB + WB + GAPC
base_attr = ["# conn: psycopg.Connection", "+ tabla: str"]
base_mets = ["+ __init__(conn)", "# _uno(sql, params): dict", "# _todos(sql, params): list[dict]", "# _escalar(sql, params)",
             "+ obtener(id_, bloquear): dict", "+ listar(): list[dict]"]
hB = max(alto("abstract", base_attr, base_mets), 7 * 0.3 + 0.6)
yTop = 2.35  # alto reservado a la fila superior
hD = alto(None, ["tabla = \"resultado_votacion\""], [])
paso = hD + 0.28
y_col_ini = yTop + 0.5
yB = y_col_ini + (7 * paso - 0.28) / 2 - hB / 2

fig = plt.figure(figsize=(1, 1))
pos, cajas, lineas = {}, {}, {}

def registrar(n, x, y, w, h):
    pos[n] = (x, y, w, h); cajas[n] = (x, y, x + w, y + h)

registrar("BaseDAO", xB, yB, WB, hB)
for i, n in enumerate(izq):
    registrar(n, xL0, y_col_ini + i * paso, WD, hD)
for i, n in enumerate(der):
    registrar(n, xR0, y_col_ini + (i + 0.5) * paso, WD, hD)
# fila superior
serv_attr = ["AuthService, UsuarioService,", "ConjuntoService, AsambleaService,", "AsistenciaService, VotacionService,", "ActaService"]
serv_met = ["abren la transacción y crean los", "DAO con la misma conexión"]
ges_attr = ["- database_url: str"]
ges_met = ["+ transaccion(aislamiento): Connection", "+ solo_lectura(): Connection"]
con_met = ["+ execute(sql, params)", "+ transaction()"]
hS, hG, hC = alto("capa", serv_attr, serv_met), alto("utility", ges_attr, ges_met), alto("library", [], con_met)
WS, WG, WC = 3.1, 3.2, 2.2
xS = xB - 1.6
xG = xS - 0.75 - WG
xC = xB + WB - 1.0
yS = 0.15
registrar("Servicios", xS, yS, WS, hS)
registrar("Gestor", xG, yS + (hS - hG) / 2, WG, hG)
registrar("Connection", xC, yS + (hS - hC) / 2, WC, hC)
assert xS + WS + 0.35 < xC, "Servicios y Connection se solapan"

# rutas
pS = (xB + 0.75, yS + hS); lineas["Servicios-BaseDAO"] = [pS, (pS[0], yB)]
pC = (xC + 0.9, yS + (hS - hC) / 2 + hC); lineas["BaseDAO-Connection"] = [(pC[0], yB), pC]
lineas["Servicios-Gestor"] = [(xS, yS + hS / 2), (xG + WG, yS + hS / 2)]
yArr = yS - 0.0
gx, cx = xG + WG / 2, xC + WC / 2
y_arriba = -0.45
lineas["Gestor-Connection"] = [(gx, pos["Gestor"][1]), (gx, y_arriba), (cx, y_arriba), (cx, pos["Connection"][1])]
for lado, lista, x_borde in (("L", izq, xB), ("R", der, xB + WB)):
    n = len(lista)
    margen = (hB - 0.3 * (n - 1)) / 2
    for i, d in enumerate(lista):
        x, y, w, h = pos[d]
        sx = x + w if lado == "L" else x
        lineas[f"{d}-BaseDAO"] = [(sx, y + h / 2), (x_borde, yB + margen + 0.3 * i)]
cajas["leyenda"] = (xB + 0.3, yB + hB + 0.35, xB + WB - 0.3, yB + hB + 0.95)
problemas = verificar(lineas, cajas, 0.09, "clases DAO (estructura)")

xmin = min(c[0] for c in cajas.values()) - 0.2; xmax = max(c[2] for c in cajas.values()) + 0.2
ymin = y_arriba - 0.3; ymax = max(c[3] for c in cajas.values()) + 0.25
fig = plt.figure(figsize=(xmax - xmin, ymax - ymin)); ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(xmin, xmax); ax.set_ylim(ymax, ymin); ax.axis("off")
caja(ax, xB, yB, WB, "BaseDAO", "abstract", base_attr, base_mets, "#c9daf0", h_min=hB)
for d in daos:
    x, y, w, h = pos[d]
    caja(ax, x, y, w, d, None, [f'tabla = "{clases[d][0]}"'], [])
caja(ax, xS, yS, WS, "Servicios de negocio", "capa", serv_attr, serv_met, "#fff2cc")
caja(ax, xG, pos["Gestor"][1], WG, "GestorTransacciones (db.py)", "utility", ges_attr, ges_met, "#e2efda")
caja(ax, xC, pos["Connection"][1], WC, "psycopg.Connection", "library", [], con_met, "#eeeeee")
def flecha_abierta(p, q):  # dependencia: línea discontinua con punta abierta en q
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="->,head_length=0.5,head_width=0.3", ls="--", color=GR, lw=1.1, shrinkA=0, shrinkB=0))
for k, pts in lineas.items():
    xs, ys = zip(*pts)
    if k.endswith("-BaseDAO") and k.split("-")[0] in clases:
        ax.plot(xs, ys, color=GR, lw=1.0, zorder=2)
        (x1, y1), (x0, y0) = pts[-1], pts[-2]
        dx, dy = x1 - x0, y1 - y0; L = (dx * dx + dy * dy) ** .5; ux, uy = dx / L, dy / L; nx, ny = -uy, ux
        b = (x1 - ux * 0.2, y1 - uy * 0.2)
        ax.add_patch(Polygon([(x1, y1), (b[0] + nx * 0.08, b[1] + ny * 0.08), (b[0] - nx * 0.08, b[1] - ny * 0.08)], fc="white", ec=GR, lw=1.0, zorder=3))
    elif len(pts) == 2:
        flecha_abierta(pts[0], pts[1])
    else:
        ax.plot(xs[:-1], ys[:-1], color=GR, lw=1.1, ls="--", zorder=2)
        flecha_abierta(pts[-2], pts[-1])
etq = {"Servicios-BaseDAO": "«usa»", "BaseDAO-Connection": "«usa»", "Servicios-Gestor": "«usa»", "Gestor-Connection": "«crea»"}
for k, t in etq.items():
    pts = lineas[k]
    if k == "Gestor-Connection":
        ax.text((pts[1][0] + pts[2][0]) / 2, y_arriba - 0.13, t, ha="center", fontsize=8.5, color=GR, family=F)
    elif k == "Servicios-Gestor":
        ax.text((pts[0][0] + pts[1][0]) / 2, pts[0][1] - 0.13, t, ha="center", fontsize=8.5, color=GR, family=F)
    else:
        ax.text(pts[0][0] + 0.1, (pts[0][1] + pts[1][1]) / 2, t, ha="left", va="center", fontsize=8.5, color=GR, family=F)
ax.text(xB + WB / 2, yB + hB + 0.7, "△ herencia (extends BaseDAO)\n⇢ dependencia «usa» / «crea»", ha="center", fontsize=8.5, color="#444", family=F)
fig.savefig("clases_dao_estructura.png", dpi=250, facecolor="white")
print("A:", round(xmax - xmin, 1), "x", round(ymax - ymin, 1))

# =============================================================== Figura B: detalle de métodos
def envolver(m, ancho=40):
    cab, resto = m.split("(", 1)
    args, ret = resto.rsplit(")", 1)
    tokens = [a + "," for a in args.split(", ")] if args else []
    if tokens:
        tokens[-1] = tokens[-1][:-1] + ")" + ret
    else:
        cab, tokens = cab + "()" + ret, []
        return [cab]
    lineas, linea = [], cab + "("
    for t in tokens:
        if len(linea) + len(t) + 1 > ancho and linea.strip() not in ("", cab.strip() + "(") or (len(linea) + len(t) > ancho and linea.endswith("(")):
            lineas.append(linea.rstrip()); linea = "      "
        linea += t + " "
    lineas.append(linea.rstrip())
    return lineas
COLS, WBX, GX, GY = 5, 3.05, 0.25, 0.3
filas = [daos[i:i + COLS] for i in range(0, 13, COLS)]
contenido = {d: ([f'tabla = "{clases[d][0]}"'], [l for m in clases[d][1] for l in envolver(m)]) for d in daos}
alto_fila = [max(alto("extends BaseDAO", *contenido[d]) for d in f) for f in filas]
W2 = COLS * WBX + (COLS - 1) * GX + 0.3; H2 = sum(alto_fila) + GY * (len(filas) - 1) + 0.3
fig = plt.figure(figsize=(W2, H2)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(-0.15, W2 - 0.15); ax.set_ylim(H2 - 0.15, -0.15); ax.axis("off")
y = 0
for f, hf in zip(filas, alto_fila):
    for j, d in enumerate(f):
        caja(ax, j * (WBX + GX), y, WBX, d, "extends BaseDAO", *contenido[d])
    y += hf + GY
fig.savefig("clases_dao_detalle.png", dpi=250, facecolor="white")
print("B:", round(W2, 1), "x", round(H2, 1))
sys.exit(1 if problemas else 0)
