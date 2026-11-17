"""Verificador geométrico: cruces entre líneas, líneas que se tocan y líneas sobre cajas/textos."""
from itertools import combinations


def _seg_dist(p, q, r, s):
    """Distancia mínima entre dos segmentos (muestreo fino: suficiente para rutas ortogonales/rectas)."""
    import math
    def pt_seg(a, b, c):
        (ax, ay), (bx, by), (cx, cy) = a, b, c
        dx, dy = cx - bx, cy - by
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((ax - bx) * dx + (ay - by) * dy) / L))
        return math.hypot(ax - (bx + t * dx), ay - (by + t * dy))
    if _cruza(p, q, r, s):
        return 0.0
    return min(pt_seg(p, r, s), pt_seg(q, r, s), pt_seg(r, p, q), pt_seg(s, p, q))


def _orient(a, b, c):
    v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)


def _cruza(p, q, r, s):
    o1, o2, o3, o4 = _orient(p, q, r), _orient(p, q, s), _orient(r, s, p), _orient(r, s, q)
    if o1 != o2 and o3 != o4:
        return True
    def on(a, b, c):
        return min(a[0], b[0]) - 1e-9 <= c[0] <= max(a[0], b[0]) + 1e-9 and min(a[1], b[1]) - 1e-9 <= c[1] <= max(a[1], b[1]) + 1e-9
    return (o1 == 0 and on(p, q, r)) or (o2 == 0 and on(p, q, s)) or (o3 == 0 and on(r, s, p)) or (o4 == 0 and on(r, s, q))


def seg_rect(p, q, rect, eps=0.012):
    """True si el segmento entra en el interior del rectángulo (x0,y0,x1,y1) reducido en eps."""
    x0, y0, x1, y1 = rect[0] + eps, rect[1] + eps, rect[2] - eps, rect[3] - eps
    if x0 >= x1 or y0 >= y1:
        return False
    # muestreo denso
    n = 200
    for i in range(n + 1):
        t = i / n
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if x0 < x < x1 and y0 < y < y1:
            return True
    return False


def verificar(lineas, cajas, distancia_min=0.08, nombre="", elipses=None):
    """lineas: {id: [puntos]}; cajas: {id: (x0,y0,x1,y1)} (incluye cajas de texto).
    Devuelve lista de problemas."""
    problemas = []
    segs = {k: list(zip(v[:-1], v[1:])) for k, v in lineas.items()}
    for a, b in combinations(segs, 2):
        d = min(_seg_dist(p, q, r, s) for p, q in segs[a] for r, s in segs[b])
        if d < distancia_min:
            problemas.append(f"líneas {a} y {b} a {d:.3f}")
    for k, ss in segs.items():
        for c, rect in cajas.items():
            if any(seg_rect(p, q, rect) for p, q in ss):
                problemas.append(f"línea {k} pasa sobre {c}")
    for k, ss in segs.items():
        for c, (cx, cy, rx, ry) in (elipses or {}).items():
            for p, q in ss:
                for i in range(1, 400):
                    t = i / 400
                    x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
                    if ((x - cx) / (rx - 0.015)) ** 2 + ((y - cy) / (ry - 0.015)) ** 2 < 1:
                        problemas.append(f"línea {k} pasa sobre elipse {c}")
                        break
                else:
                    continue
                break
    print(f"[{nombre}] {len(lineas)} líneas, {len(cajas)} cajas -> {len(problemas)} problemas")
    for p in problemas:
        print("   ", p)
    return problemas
