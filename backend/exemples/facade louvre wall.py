#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# facade_louvre_wall.py
# Pavillon triangulaire avec lattes diagonales (1 ou 2 nappes), 100% paramétrique.
# Ajouts:
# - --boolean {union,intersect}
# - --sameZ : force les deux nappes au même Z
# - --fullDepth : les lattes traversent toute l'épaisseur (Z=0..T)

import math
import cadquery as cq
import argparse

CFG = dict(
    # Triangle (vue XY, extrudé en Z)
    width=280.0,
    height=260.0,
    thickness=40.0,
    corner_fillet=3.0,

    # Louvres (nappe 1)
    angle_deg=35.0,   # angle par rapport à +X
    pitch=12.0,       # entraxe perpendiculaire à la latte
    slat_width=8.0,   # largeur perpendiculaire à la latte
    slat_depth=12.0,  # extrusion en Z
    end_radius=3.0,   # rayon d’extrémité (si >0 on passe en slot2D)
    layer1_z=6.0,     # position en Z de la nappe 1 (0..thickness-slat_depth)

    # Nappe 2 (croisée)
    layer2=dict(
        enabled=True,
        angle_deg=55.0,   # typiquement ~90° - angle_deg
        z_offset=0.0     # position en Z de la nappe 2
    ),

    # Booleans / positionnement
    boolean="union",   # "union" ou "intersect"
    same_layer=False,  # True => nappe2 au même Z que nappe1
    full_depth=False,  # True => lattes extrudées sur toute l'épaisseur
)

# ---------------- utils ----------------

def _triangle_prism(W: float, H: float, T: float, rf: float = 0.0) -> cq.Workplane:
    tri = cq.Workplane("XY").polyline([(0, 0), (0, H), (W, 0)]).close().extrude(T)
    if rf and rf > 0:
        tri = tri.edges("|Z").fillet(rf)
    return tri

def _make_louver_field(W, H, T, angle_deg, pitch, slat_w, slat_d, end_r, z0) -> cq.Workplane:
    """
    Crée un champ de lattes alignées à 'angle_deg'.
    - Si end_r > 0: utilise slot2D (extrémités arrondies robustes)
    - Sinon: section rectangulaire
    """
    theta = math.radians(angle_deg)
    diag = math.hypot(W, H)
    L = diag * 2.1  # longueur de latte sûre

    # normale (perpendiculaire) aux lattes
    nx = math.cos(theta + math.pi/2.0)
    ny = math.sin(theta + math.pi/2.0)

    span = W + H
    n_slats = int(math.ceil(span / pitch)) + 4

    # Profil 2D
    if end_r > 0:
        slot_w = min(2.0*end_r, slat_w)
        core_len = max(L, slot_w + 1.0)
        prof2d = cq.Workplane("XY").slot2D(core_len, slot_w)
    else:
        prof2d = cq.Workplane("XY").rect(L, slat_w)

    base3d = (prof2d
              .extrude(slat_d)
              .rotate((0, 0, 0), (0, 0, 1), math.degrees(theta))
              .translate((0, 0, z0)))

    field = None
    start = -(n_slats // 2)
    for i in range(start, start + n_slats):
        d = i * pitch
        slat = base3d.translate((d*nx, d*ny, 0))
        field = slat if field is None else field.union(slat)
    return field

# --------------- build ------------------

def build(cfg=CFG) -> cq.Workplane:
    W, H, T = cfg["width"], cfg["height"], cfg["thickness"]
    rf = cfg["corner_fillet"]
    ang, pitch = cfg["angle_deg"], cfg["pitch"]
    sw, sd, er = cfg["slat_width"], cfg["slat_depth"], cfg["end_radius"]
    z1 = cfg["layer1_z"]

    tri = _triangle_prism(W, H, T, rf)

    # gestion des options de profondeur/alignement
    if cfg["full_depth"]:
        sd1 = sd2 = T
        z1u = 0.0
        z2u = 0.0
    else:
        if not (0.0 <= z1 <= max(0.0, T - sd)):
            raise ValueError("layer1_z hors de l'épaisseur disponible")
        sd1 = sd
        z1u = z1
        if cfg["layer2"]["enabled"]:
            z2 = cfg["layer2"]["z_offset"]
            if cfg["same_layer"]:
                z2u = z1u
            else:
                if not (0.0 <= z2 <= max(0.0, T - sd)):
                    raise ValueError("layer2 z_offset hors de l'épaisseur disponible")
                z2u = z2
            sd2 = sd

    # nappe 1
    f1 = _make_louver_field(W, H, T, ang, pitch, sw, sd1, er, z1u)

    # nappe 2 optionnelle
    if cfg["layer2"]["enabled"]:
        ang2 = cfg["layer2"]["angle_deg"]
        f2 = _make_louver_field(W, H, T, ang2, pitch, sw, sd2, er, z2u)

        # booléen entre nappes puis découpe par le triangle
        if cfg["boolean"].lower() == "intersect":
            model = f1.intersect(f2).intersect(tri)
        else:
            model = f1.union(f2).intersect(tri)
    else:
        model = f1.intersect(tri)

    return model

# --------------- CLI --------------------

def main():
    p = argparse.ArgumentParser(description="Louvre Wall (triangle + lattes diagonales)")
    p.add_argument("--out", default="01_Diagonal_Louvers_Pavilion.stl")
    p.add_argument("--W", type=float)
    p.add_argument("--H", type=float)
    p.add_argument("--T", type=float)
    p.add_argument("--angle", type=float)
    p.add_argument("--pitch", type=float)
    p.add_argument("--width", type=float, dest="swidth")
    p.add_argument("--depth", type=float, dest="sdepth")
    p.add_argument("--endR", type=float)
    p.add_argument("--z1", type=float)
    p.add_argument("--layer2", action="store_true")
    p.add_argument("--angle2", type=float)
    p.add_argument("--z2", type=float)
    p.add_argument("--boolean", choices=["union","intersect"], default=None)
    p.add_argument("--sameZ", action="store_true")
    p.add_argument("--fullDepth", action="store_true")
    p.add_argument("--linTol", type=float, default=0.03)
    p.add_argument("--angTol", type=float, default=0.15)
    args = p.parse_args()

    cfg = {k: (v.copy() if isinstance(v, dict) else v) for k, v in CFG.items()}
    if args.W is not None:       cfg["width"] = float(args.W)
    if args.H is not None:       cfg["height"] = float(args.H)
    if args.T is not None:       cfg["thickness"] = float(args.T)
    if args.angle is not None:   cfg["angle_deg"] = float(args.angle)
    if args.pitch is not None:   cfg["pitch"] = float(args.pitch)
    if args.swidth is not None:  cfg["slat_width"] = float(args.swidth)
    if args.sdepth is not None:  cfg["slat_depth"] = float(args.sdepth)
    if args.endR is not None:    cfg["end_radius"] = float(args.endR)
    if args.z1 is not None:      cfg["layer1_z"] = float(args.z1)

    if args.layer2:
        cfg["layer2"]["enabled"] = True
    if args.angle2 is not None:
        cfg["layer2"]["angle_deg"] = float(args.angle2)
    if args.z2 is not None:
        cfg["layer2"]["z_offset"] = float(args.z2)

    if args.boolean is not None:
        cfg["boolean"] = args.boolean
    if args.sameZ:
        cfg["same_layer"] = True
    if args.fullDepth:
        cfg["full_depth"] = True

    model = build(cfg)
    cq.exporters.export(model.val(), args.out,
                        tolerance=args.linTol, angularTolerance=args.angTol)
    bb = model.val().BoundingBox()
    print(f"✅ {args.out} | BBox {bb.xlen:.1f}×{bb.ylen:.1f}×{bb.zlen:.1f} mm")

if __name__ == "__main__":
    main()
