#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# honeycomb_panel.py — Panneau alvéolaire (hexagones) seul, clip complet au panneau.
#
# Paramètres clés :
#   W,H,T      = largeur, hauteur, épaisseur du panneau
#   size       = taille de l’hexagone (côté = rayon circumscrit "flat-top")
#   wall       = épaisseur du montant (épaisseur de l’hexagone)
#   depth      = extrusion en Z des alvéoles (si --fullDepth : traverse toute l’épaisseur)
#
# Notes :
# - Origine : bas-gauche (0,0). Le panneau couvre [0..W]×[0..H].
# - On garde uniquement les cellules entièrement dans le panneau (bords propres).
# - Aucune "rib/barre" verticale : uniquement le motif honeycomb.

import math
import argparse
import cadquery as cq

CFG = dict(
    W=300.0,     # largeur panneau (X)
    H=380.0,     # hauteur panneau (Y)
    T=40.0,      # épaisseur panneau (Z)
    size=12.0,   # côté de l’hexagone (flat-top). Aussi rayon vers les sommets.
    wall=2.2,    # épaisseur de montants (section alvéole)
    depth=40.0,  # extrusion des alvéoles (Z)
    corner_fillet=0.0,   # congé vertical sur le panneau (optionnel)
    fullDepth=False,     # True => depth = T et Z0=0
)

# ---------- Utils géométriques ----------

def hex_vertices_flat_top(a: float):
    """
    Coordonnées des 6 sommets d’un hexagone "flat-top" centré en (0,0)
    avec 'a' = longueur de côté = rayon vers les sommets.
    """
    r = a
    s = (math.sqrt(3)/2.0) * a  # demi-hauteur
    return [
        ( r, 0.0),
        ( r/2.0,  s),
        (-r/2.0,  s),
        (-r, 0.0),
        (-r/2.0, -s),
        ( r/2.0, -s),
    ]

def make_hex_face(a: float, wall: float) -> cq.Workplane:
    """
    Face 2D d’un hexagone épais (anneau).
    - On dessine l’hexagone extérieur puis on fait un offset interne de 'wall'.
    - Suppose wall < a/2 (sinon l’offset s’annule).
    """
    verts = hex_vertices_flat_top(a)
    outer = cq.Workplane("XY").polyline(verts).close()
    # Offset interne pour créer l’alvéole creuse
    inner = outer.offset2D(-wall)  # contraction
    # Remplit la zone entre outer et inner
    face = (outer
            .toPending()
            .consolidateWires()
            .add(inner.wires())
            .toPending()
            .consolidateWires())
    return face

def honeycomb_field(W, H, T, a, wall, depth, keep_full=True, z0=0.0) -> cq.Workplane:
    """
    Génère le champ honeycomb et (optionnel) filtre pour garder
    seulement les cellules entièrement incluses dans [0..W]×[0..H] (keep_full=True).
    Grille "flat-top" :
      dx = 1.5 * a
      dy = sqrt(3) * a
    """
    dx = 1.5 * a
    dy = math.sqrt(3.0) * a

    # demi-empreintes pour inclusion stricte (pour ne **pas** couper des cellules)
    half_w = a           # demi-largeur max (vers un sommet)
    half_h = dy/2.0      # demi-hauteur

    # Profil 2D d’une cellule
    cell2d = make_hex_face(a, wall)

    # Volume 3D de base
    cell3d = cell2d.extrude(depth).translate((0, 0, z0))

    # Nombre de colonnes/lignes suffisant pour recouvrir W×H
    nx = int(math.ceil((W + 2*half_w) / dx)) + 2
    ny = int(math.ceil((H + 2*half_h) / dy)) + 2

    solids = None
    x0 = 0.0
    y0 = 0.0

    for i in range(nx):
        cx = x0 + i*dx
        col_off = (dy/2.0) if (i % 2) else 0.0
        for j in range(ny):
            cy = y0 + j*dy + col_off

            if keep_full:
                # Test "completement inclus" : le contour ne doit pas sortir
                if not ( (x0 + half_w) <= cx <= (W - half_w) and
                         (y0 + half_h) <= cy <= (H - half_h) ):
                    continue
            else:
                # Variante permissive : garde aussi les partiels (seront coupés plus tard)
                if not (-half_w <= cx <= (W + half_w) and -half_h <= cy <= (H + half_h)):
                    continue

            c = cell3d.translate((cx, cy, 0.0))
            solids = c if solids is None else solids.union(c)

    return solids if solids is not None else cq.Workplane("XY")

# ---------- Construction principale ----------

def build(cfg=CFG) -> cq.Workplane:
    W, H, T = cfg["W"], cfg["H"], cfg["T"]
    a, wall = cfg["size"], cfg["wall"]
    depth = (T if cfg["fullDepth"] else cfg["depth"])
    z0 = 0.0

    # Panneau de clip [0..W]×[0..H]
    panel = cq.Workplane("XY").rect(W, H, centered=False).extrude(T)
    if cfg.get("corner_fillet", 0.0) > 0:
        panel = panel.edges("|Z").fillet(float(cfg["corner_fillet"]))

    honey = honeycomb_field(W, H, T, a, wall, depth, keep_full=True, z0=z0)

    # Clip final (sécurité) — ne garde rien hors panneau
    result = honey.intersect(panel)

    return result

# ---------- CLI ----------

def main():
    p = argparse.ArgumentParser(description="Honeycomb panel (no ribs)")
    p.add_argument("--out", default="honeycomb_panel.stl")
    p.add_argument("--W", type=float)
    p.add_argument("--H", type=float)
    p.add_argument("--T", type=float)
    p.add_argument("--size", type=float, help="côté de l’hexagone (flat-top)")
    p.add_argument("--wall", type=float, help="épaisseur des montants")
    p.add_argument("--depth", type=float, help="extrusion en Z")
    p.add_argument("--fullDepth", action="store_true", help="les alvéoles traversent toute l’épaisseur")
    p.add_argument("--linTol", type=float, default=0.05)
    p.add_argument("--angTol", type=float, default=0.3)
    args = p.parse_args()

    cfg = dict(CFG)
    if args.W is not None:      cfg["W"] = float(args.W)
    if args.H is not None:      cfg["H"] = float(args.H)
    if args.T is not None:      cfg["T"] = float(args.T)
    if args.size is not None:   cfg["size"] = float(args.size)
    if args.wall is not None:   cfg["wall"] = float(args.wall)
    if args.depth is not None:  cfg["depth"] = float(args.depth)
    if args.fullDepth:          cfg["fullDepth"] = True

    model = build(cfg)
    cq.exporters.export(model.val(), args.out,
                        tolerance=args.linTol, angularTolerance=args.angTol)
    bb = model.val().BoundingBox()
    print(f"✅ {args.out} | BBox {bb.xlen:.1f}×{bb.ylen:.1f}×{bb.zlen:.1f} mm")

if __name__ == "__main__":
    main()
