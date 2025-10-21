#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# sine_wave_fins.py — Façade "Sine Wave Fins" (extraite du script multi-façades)

import cadquery as cq
import math
import argparse

# ------------------ paramètres par défaut ------------------
CFG = dict(
    L=420.0,          # largeur du panneau (X)
    H=180.0,          # hauteur du panneau (Y)
    depth=140.0,      # profondeur des ailerons (Z)
    n_fins=34,        # nombre d’ailerons
    fin_t=3.0,        # épaisseur d’un aileron (en plan)
    amp=40.0,         # amplitude de la sinusoïde (déplacement Y)
    period_ratio=0.9, # longueur d’onde ≈ L * period_ratio
    base_thick=6.0,   # épaisseur de la plaque arrière
    out="05_Sine Wave Fins.stl",
    linTol=0.03,
    angTol=0.15,
)

# ------------------ construction ------------------
def build(c=CFG) -> cq.Workplane:
    L, H, depth = c["L"], c["H"], c["depth"]
    n_fins, fin_t = int(c["n_fins"]), c["fin_t"]
    amp, pr = c["amp"], c["period_ratio"]
    base_thick = c["base_thick"]

    # plaque arrière
    base = cq.Workplane("XY").rect(L, H).extrude(base_thick)

    # fréquence de la sinusoïde
    # (même logique que le script original : période = L*period_ratio)
    freq = 2.0 * math.pi / (L * pr)

    ribs = cq.Workplane("XY")
    x0 = -L/2
    for i in range(n_fins):
        x = x0 + i*(L/(n_fins-1))
        off0 = amp * math.sin(freq*(x + 0.00*L))
        off1 = amp * math.sin(freq*(x + 0.25*L))  # léger déphasage
        fin = (cq.Workplane("XY")
               .center(x, off0).rect(fin_t, H)
               .workplane(offset=depth).center(0, off1-off0).rect(fin_t, H)
               .loft(ruled=True, combine=True))
        ribs = ribs.union(fin)

    # clip pour couper tout dépassement
    clip = cq.Workplane("XY").rect(L, H).extrude(depth + base_thick + 6.0)
    return base.union(ribs.intersect(clip))

# ------------------ export ------------------
def export_wp(wp: cq.Workplane, out_path: str, lin=0.03, ang=0.15):
    solid = wp.val()
    cq.exporters.export(solid, out_path, tolerance=lin, angularTolerance=ang)
    bb = solid.BoundingBox()
    print(f"✅ {out_path} | BBox {bb.xlen:.1f}×{bb.ylen:.1f}×{bb.zlen:.1f} mm")

# ------------------ CLI ------------------
def main():
    ap = argparse.ArgumentParser(description="Façade Sine Wave Fins (standalone)")
    ap.add_argument("--L", type=float)
    ap.add_argument("--H", type=float)
    ap.add_argument("--depth", type=float)
    ap.add_argument("--n_fins", type=int)
    ap.add_argument("--fin_t", type=float)
    ap.add_argument("--amp", type=float)
    ap.add_argument("--period_ratio", type=float)
    ap.add_argument("--base_thick", type=float)
    ap.add_argument("--out", default=CFG["out"])
    ap.add_argument("--linTol", type=float, default=CFG["linTol"])
    ap.add_argument("--angTol", type=float, default=CFG["angTol"])
    args = ap.parse_args()

    c = CFG.copy()
    for k in c.keys():
        if hasattr(args, k) and getattr(args, k) is not None:
            c[k] = type(c[k])(getattr(args, k))

    model = build(c)
    export_wp(model, c["out"], c["linTol"], c["angTol"])

if __name__ == "__main__":
    main()
