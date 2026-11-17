import sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from geom import verificar
AZ, F = "#1f4e79", "DejaVu Sans"
cajas, lineas = {}, {}
fig = plt.figure(figsize=(11, 9.6)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 11); ax.set_ylim(9.6, 0); ax.axis("off")
def caja(n, x, y, w, h, texto, fc="white", ec=AZ, fs=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12", fc=fc, ec=ec, lw=1.4, zorder=3))
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=fs, family=F, zorder=4)
    cajas[n] = (x, y, x + w, y + h)
def banda(n, y, h, titulo, fc, ec, tc):
    ax.add_patch(FancyBboxPatch((0.25, y), 10.5, h, boxstyle="round,pad=0,rounding_size=0.18", fc=fc, ec=ec, lw=1.4, zorder=1))
    ax.text(0.45, y + 0.28, titulo, fontsize=12.5, fontweight="bold", color=tc, family=F, va="center", zorder=2)
    cajas["titulo-" + n] = (0.4, y + 0.1, 0.45 + 0.13 * len(titulo), y + 0.46)
caja("nav", 2.3, 0.2, 3.0, 0.8, "Navegador web\n(formularios HTML + JS de quórum)", "#eeeeee")
banda("p", 1.55, 1.75, "Capa de presentación", "#eef4fb", "#2e75b6", AZ)
caja("mw", 2.3, 2.15, 3.0, 0.85, "Middlewares: sesión firmada,\ncabeceras de seguridad")
caja("rt", 5.9, 2.15, 2.15, 0.85, "Routers FastAPI\n+ plantillas Jinja2")
caja("sec", 8.55, 2.15, 2.0, 0.85, "security.py\nbcrypt · CSRF ·\nroles · bloqueo", fs=10)
banda("n", 3.85, 1.75, "Capa de lógica de negocio", "#fff8e6", "#bf9000", "#7f6000")
caja("sv", 4.6, 4.45, 3.45, 0.85, "Servicios (Asamblea, Asistencia,\nVotación, Acta, …)")
caja("rg", 8.55, 4.45, 2.0, 0.85, "reglas.py\nquórum y mayorías\n(Ley 675)", fs=10)
banda("d", 6.15, 1.75, "Capa de persistencia", "#eef7ea", "#548235", "#375623")
caja("gt", 3.35, 6.75, 2.6, 0.85, "GestorTransacciones\nCOMMIT / ROLLBACK")
caja("dao", 6.7, 6.75, 2.6, 0.85, "13 DAO\n(uno por tabla)")
caja("pg", 5.75, 8.4, 4.5, 0.9, "PostgreSQL\ntablas · índices únicos · CHECK · triggers", "#dbe7f3")
lineas["nav-mw"] = [(3.8, 1.0), (3.8, 2.15)]
lineas["mw-rt"] = [(5.3, 2.575), (5.9, 2.575)]
lineas["rt-sec"] = [(8.05, 2.575), (8.55, 2.575)]
lineas["rt-sv"] = [(6.975, 3.0), (6.975, 4.45)]
lineas["sv-rg"] = [(8.05, 4.875), (8.55, 4.875)]
lineas["sv-gt"] = [(5.1, 5.3), (5.1, 6.75)]
lineas["sv-dao"] = [(7.5, 5.3), (7.5, 6.75)]
lineas["gt-dao"] = [(5.95, 7.175), (6.7, 7.175)]
lineas["dao-pg"] = [(8.0, 7.6), (8.0, 8.4)]
problemas = verificar(lineas, cajas, 0.1, "arquitectura")
for k, (p, q) in ((k, v) for k, v in lineas.items()):
    estilo = "--" if k in ("rt-sec", "sv-rg", "gt-dao") else "-"
    flecha = "-" if k == "gt-dao" else "->,head_length=0.6,head_width=0.35"
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle=flecha, ls=estilo, color=AZ, lw=1.4, shrinkA=0, shrinkB=0), zorder=2)
ax.text(3.9, 1.27, "HTTP", fontsize=9.5, family=F, color="#333", va="center")
ax.text(8.1, 8.0, "SQL parametrizado", fontsize=9.5, family=F, color="#333", va="center")
cajas_txt = {"http": (3.85, 1.18, 4.35, 1.36), "sql": (8.05, 7.9, 9.4, 8.1)}
problemas += verificar(lineas, cajas_txt, 0.1, "arquitectura-textos")
fig.savefig("arquitectura.png", dpi=250, facecolor="white")
sys.exit(1 if problemas else 0)
