#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# step2s_double_bars_taper_solid_with_bites_rect_sides.py
# Deux barres pleines symétriques, tuyau à côtés RECTANGULAIRES (coins remplis).

import cadquery as cq
import argparse

CFG = dict(
    # Plaque
    plate_w=40.0, plate_h=40.0, plate_t=3.0, corner_r=2.0,
    center_d=34.0, hole_pitch=32.0, hole_d=3.3,
    # Tuyau
    tube_od=42.0, tube_len=10.0,
    # Barres
    bar_len=22.0, bar_angle_in=20.0,
    taper_start=None, bar_tip_t_ratio=0.15, bar_tip_t_min=0.2,
    # Clip / robustesse
    overlap=0.4, clip_extra=4.0, edge_inset=0.0,
    # Morsures locales (mettre 0 pour désactiver)
    cut_h_bottom=6.0, cut_h_top=6.0, cut_clear=0.05
)

def _make_taper_bar(W,H,T,Tb,Lb,Ang,ov,inset,taper_start,tip_ratio,tip_min,side=+1):
    y_bar = side*(W/2 - Tb/2) - side*inset
    x0 = T - ov
    L_const = taper_start if taper_start is not None else 0.0
    L_const = max(0.0, min(L_const, Lb-0.1))
    tip_t = max(tip_min, Tb*max(0.05, tip_ratio))
    bar = (cq.Workplane("YZ")
           .workplane(offset=x0).center(y_bar,0).rect(Tb, H+10)
           .workplane(offset=L_const).center(0,0).rect(Tb, H+10)
           .workplane(offset=Lb).center(0,0).rect(tip_t, H+10)
           .loft(combine=True, ruled=True))
    bar = bar.rotate((x0,y_bar,0),(x0,y_bar,1), -side*abs(Ang))
    return bar, y_bar, x0

def build(c=CFG):
    W,H,T,R = c["plate_w"], c["plate_h"], c["plate_t"], c["corner_r"]
    D0,P,Dh = c["center_d"], c["hole_pitch"], c["hole_d"]
    Do,Lt   = c["tube_od"], c["tube_len"]
    Lb,Ang  = c["bar_len"], c["bar_angle_in"]
    ov,clip_extra,inset = c["overlap"], c["clip_extra"], c["edge_inset"]
    taper_start = c["taper_start"]
    tip_ratio, tip_min = c["bar_tip_t_ratio"], c["bar_tip_t_min"]
    cut_h_bot, cut_h_top, clr = c["cut_h_bottom"], c["cut_h_top"], c["cut_clear"]

    Tb = 0.5*(Do - D0)  # épaisseur paroi = épaisseur barres

    # 1) Plaque
    plate = cq.Workplane("YZ").rect(W,H).extrude(T)
    if R>0: plate = plate.edges("|X").fillet(R)
    plate = plate.cut(cq.Workplane("YZ").circle(D0/2).extrude(T))
    pts = [(+P/2,+P/2),(+P/2,-P/2),(-P/2,+P/2),(-P/2,-P/2)]
    plate = plate.faces(">X").workplane().pushPoints(pts).hole(Dh)

    # 2) TUYAU à côtés RECTANGULAIRES (coins remplis)
    #    Extérieur = RECTANGLE (largeur > plaque, pour être recoupé par le clip)
    #    Intérieur = CERCLE (Ø = D0)
    rect_w = W + 2.0  # un peu plus large, sera rogné par le clip
    tube_outer = (cq.Workplane("YZ")
                  .workplane(offset=T-ov)
                  .rect(rect_w, Do)
                  .extrude(Lt+ov))
    tube_inner = (cq.Workplane("YZ")
                  .workplane(offset=T-ov)
                  .circle(D0/2)
                  .extrude(Lt+ov))
    tube = tube_outer.cut(tube_inner)

    # 3) Deux barres symétriques + amincissement après le tuyau
    L_const_default = Lt if taper_start is None else taper_start
    barR, yR, x0R = _make_taper_bar(W,H,T,Tb,Lb,Ang,ov,inset,L_const_default,tip_ratio,tip_min, +1)
    barL, yL, x0L = _make_taper_bar(W,H,T,Tb,Lb,Ang,ov,inset,L_const_default,tip_ratio,tip_min, -1)

    # 4) Rogner le TUYAU côté extérieur des barres (barres laissées pleines)
    Wcut, Hcut = 2*W, H+20
    Lcut = max(Lt,Lb)+ov+2
    cutR = (cq.Workplane("YZ").workplane(offset=x0R)
            .center(yR + Tb/2 + Wcut/2,0).rect(Wcut,Hcut).extrude(Lcut)
            .rotate((x0R,yR,0),(x0R,yR,1), -abs(Ang)))
    cutL = (cq.Workplane("YZ").workplane(offset=x0L)
            .center(yL - Tb/2 - Wcut/2,0).rect(Wcut,Hcut).extrude(Lcut)
            .rotate((x0L,yL,0),(x0L,yL,1), +abs(Ang)))
    tube = tube.cut(cutR).cut(cutL)

    # 5) Clip = empreinte de la plaque (même congé) pour rogner proprement
    clip_len = max(Lt,Lb)+ov+clip_extra
    clip = cq.Workplane("YZ").workplane(offset=T-ov).rect(W,H).extrude(clip_len)
    if R>0: clip = clip.edges("|X").fillet(R)
    tube = tube.intersect(clip)
    barR = barR.intersect(clip)
    barL = barL.intersect(clip)

    asm = plate.union(tube).union(barR).union(barL)

    # 6) Morsures locales (optionnelles) — bandes limitées en hauteur
    x_start = T - ov
    cut_len = clip_len + 2.0
    if cut_h_bot > 0:
        bandB = (cq.Workplane("YZ").workplane(offset=x_start)
                 .center(0, -H/2 + cut_h_bot/2).rect(W+20, cut_h_bot).extrude(cut_len))
        for y in (+P/2, -P/2):
            cyl = (cq.Workplane("YZ").workplane(offset=x_start)
                   .center(y, -P/2).circle(Dh/2 + clr).extrude(cut_len))
            asm = asm.cut(cyl.intersect(bandB))
    if cut_h_top > 0:
        bandT = (cq.Workplane("YZ").workplane(offset=x_start)
                 .center(0, +H/2 - cut_h_top/2).rect(W+20, cut_h_top).extrude(cut_len))
        for y in (+P/2, -P/2):
            cyl = (cq.Workplane("YZ").workplane(offset=x_start)
                   .center(y, +P/2).circle(Dh/2 + clr).extrude(cut_len))
            asm = asm.cut(cyl.intersect(bandT))

    return asm

def main():
    ap = argparse.ArgumentParser(description="2 barres pleines, tuyau à côtés rectangulaires (coins remplis)")
    ap.add_argument("--out", default="step2s_double_bars_rect_sides.stl")
    ap.add_argument("--barLen", type=float, default=None)
    ap.add_argument("--angle",  type=float, default=None)
    ap.add_argument("--taperStart", type=float, default=None)
    ap.add_argument("--tipRatio",   type=float, default=None)
    ap.add_argument("--tipMin",     type=float, default=None)
    ap.add_argument("--cutBottomH", type=float, default=None)
    ap.add_argument("--cutTopH",    type=float, default=None)
    ap.add_argument("--linTol",     type=float, default=0.03)
    ap.add_argument("--angTol",     type=float, default=0.15)
    args = ap.parse_args()

    cfg = CFG.copy()
    if args.barLen is not None:     cfg["bar_len"]       = float(args.barLen)
    if args.angle  is not None:     cfg["bar_angle_in"]  = float(args.angle)
    if args.taperStart is not None: cfg["taper_start"]   = float(args.taperStart)
    if args.tipRatio is not None:   cfg["bar_tip_t_ratio"]= float(args.tipRatio)
    if args.tipMin   is not None:   cfg["bar_tip_t_min"] = float(args.tipMin)
    if args.cutBottomH is not None: cfg["cut_h_bottom"]  = float(args.cutBottomH)
    if args.cutTopH    is not None: cfg["cut_h_top"]     = float(args.cutTopH)

    model = build(cfg)
    cq.exporters.export(model.val(), args.out,
                        tolerance=args.linTol, angularTolerance=args.angTol)
    bb = model.val().BoundingBox()
    print("✅ Tuyau à côtés rectangulaires (sans losange), coins remplis ; 2 barres pleines amincies.")
    print(f"BBox: ({bb.xlen:.2f} × {bb.ylen:.2f} × {bb.zlen:.2f}) mm → {args.out}")

if __name__ == "__main__":
    main()
