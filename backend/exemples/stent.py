#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stent_serpentine_vertical.py — Stent avec anneaux serpentins empilés verticalement
Motif : anneaux zigzag + ponts axiaux → cellules losange régulières (IMAGE 1)
"""

import math
import argparse
import cadquery as cq

# ------------------------- CONFIG (mm) -------------------------
CFG = {
    # Cylindre de base
    "outer_radius": 8.0,      # rayon extérieur du stent
    "length": 40.0,           # longueur totale du stent
    
    # Motif serpentin
    "n_peaks": 8,             # nombre de pics (peaks) par anneau
    "n_rings": 6,             # nombre d'anneaux serpentins
    "amplitude": 3.0,         # amplitude du zigzag (hauteur peak-to-valley)
    "ring_spacing": 6.0,      # espacement entre centres d'anneaux
    
    # Struts (barres)
    "strut_width": 0.6,       # largeur des barres
    "strut_depth": 0.4,       # profondeur (épaisseur radiale)
    
    # Languettes aux extrémités
    "tab_length": 2.0,
    "tab_width": 0.8,
    "enable_tabs": True,
}

# ------------------------- OUTILS -------------------------
def export_stl(shape, path: str, lin_tol=0.01, ang_tol=0.1):
    obj = shape.val() if isinstance(shape, cq.Workplane) else shape
    cq.exporters.export(obj, path, tolerance=lin_tol, angularTolerance=ang_tol)

def create_strut_between_points(cfg, p1, p2):
    """Crée une barre rectangulaire entre deux points 3D."""
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    
    width = cfg["strut_width"]
    depth = cfg["strut_depth"]
    
    # Vecteur direction
    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    
    if length < 0.001:
        return None
    
    # Centre
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    cz = (z1 + z2) / 2
    
    # Angles de rotation
    # Rotation autour de Z pour orienter dans le plan XY
    angle_z = math.degrees(math.atan2(dy, dx))
    # Rotation autour de Y pour l'inclinaison verticale
    horizontal_dist = math.sqrt(dx*dx + dy*dy)
    angle_y = math.degrees(math.atan2(dz, horizontal_dist))
    
    # Créer une barre orientée selon X initialement
    strut = (cq.Workplane("XY")
            .center(0, 0)
            .rect(length, width)
            .extrude(depth))
    
    # Appliquer les rotations et translation
    strut = (strut
            .rotate((0, 0, 0), (0, 1, 0), -angle_y)
            .rotate((0, 0, 0), (0, 0, 1), angle_z)
            .translate((cx, cy, cz)))
    
    return strut

def get_ring_points(cfg, z_center, phase_shift=0):
    """
    Génère les points d'un anneau serpentin à une hauteur Z donnée.
    Retourne deux listes : peaks (pics) et valleys (creux).
    phase_shift : décalage angulaire en degrés
    """
    R = cfg["outer_radius"]
    n_peaks = cfg["n_peaks"]
    amplitude = cfg["amplitude"]
    
    peaks = []
    valleys = []
    
    # Angle entre chaque peak
    angle_step = 360.0 / n_peaks
    
    for i in range(n_peaks):
        # Angle du peak
        angle_peak = i * angle_step + phase_shift
        x_peak = R * math.cos(math.radians(angle_peak))
        y_peak = R * math.sin(math.radians(angle_peak))
        z_peak = z_center + amplitude / 2
        peaks.append((x_peak, y_peak, z_peak))
        
        # Valley entre ce peak et le suivant
        angle_valley = angle_peak + angle_step / 2
        x_valley = R * math.cos(math.radians(angle_valley))
        y_valley = R * math.sin(math.radians(angle_valley))
        z_valley = z_center - amplitude / 2
        valleys.append((x_valley, y_valley, z_valley))
    
    return peaks, valleys

def create_ring_struts(cfg, peaks, valleys):
    """Crée les struts d'un anneau zigzag : peak->valley->peak->valley..."""
    stent = None
    n = len(peaks)
    
    for i in range(n):
        # Peak actuel vers valley actuel
        s1 = create_strut_between_points(cfg, peaks[i], valleys[i])
        if s1:
            stent = s1 if stent is None else stent.union(s1)
        
        # Valley actuel vers peak suivant
        next_peak = peaks[(i + 1) % n]
        s2 = create_strut_between_points(cfg, valleys[i], next_peak)
        if s2:
            stent = stent.union(s2) if stent else s2
    
    return stent

def create_bridges_between_rings(cfg, rings_points):
    """
    Crée les ponts verticaux entre anneaux adjacents.
    rings_points : liste de (peaks, valleys) pour chaque anneau.
    Les ponts alternent : peak->valley, valley->peak entre anneaux successifs.
    """
    bridges = None
    
    for ring_idx in range(len(rings_points) - 1):
        peaks1, valleys1 = rings_points[ring_idx]
        peaks2, valleys2 = rings_points[ring_idx + 1]
        
        n_peaks = len(peaks1)
        
        # Stratégie d'alternance pour créer des losanges
        # Ring pair : connecter peaks1 -> valleys2
        # Ring impair : connecter valleys1 -> peaks2
        
        if ring_idx % 2 == 0:
            # Peaks de l'anneau inférieur vers valleys de l'anneau supérieur
            for i in range(n_peaks):
                bridge = create_strut_between_points(cfg, peaks1[i], valleys2[i])
                if bridge:
                    bridges = bridge if bridges is None else bridges.union(bridge)
        else:
            # Valleys de l'anneau inférieur vers peaks de l'anneau supérieur
            for i in range(n_peaks):
                bridge = create_strut_between_points(cfg, valleys1[i], peaks2[i])
                if bridge:
                    bridges = bridge if bridges is None else bridges.union(bridge)
    
    return bridges

def build_stent(cfg) -> cq.Workplane:
    """Construit le stent complet avec anneaux serpentins verticaux."""
    n_rings = cfg["n_rings"]
    ring_spacing = cfg["ring_spacing"]
    length = cfg["length"]
    n_peaks = cfg["n_peaks"]
    
    # Calculer les positions Z des anneaux
    # Centrer le stent autour de Z=0
    total_height = (n_rings - 1) * ring_spacing
    z_start = -total_height / 2
    
    stent = None
    rings_points = []
    
    # Créer tous les anneaux
    for ring_idx in range(n_rings):
        z = z_start + ring_idx * ring_spacing
        
        # Alterner légèrement la phase pour créer les losanges
        # Anneau 0 : phase 0
        # Anneau 1 : phase décalée de angle_step/2 pour aligner valleys avec peaks
        phase_shift = 0 if ring_idx % 2 == 0 else (360.0 / n_peaks) / 2
        
        # Obtenir les points
        peaks, valleys = get_ring_points(cfg, z, phase_shift)
        rings_points.append((peaks, valleys))
        
        # Créer les struts de l'anneau
        ring = create_ring_struts(cfg, peaks, valleys)
        if ring:
            stent = ring if stent is None else stent.union(ring)
    
    # Ajouter les ponts entre anneaux
    bridges = create_bridges_between_rings(cfg, rings_points)
    if bridges:
        stent = stent.union(bridges)
    
    # Ajouter les languettes aux extrémités
    if cfg["enable_tabs"]:
        stent = add_end_tabs(cfg, stent, rings_points)
    
    return stent

def add_end_tabs(cfg, stent, rings_points):
    """Ajoute des languettes radiales aux extrémités."""
    if not rings_points:
        return stent
    
    tab_len = cfg["tab_length"]
    tab_w = cfg["tab_width"]
    depth = cfg["strut_depth"]
    
    # Tabs sur le premier anneau (peaks)
    first_peaks, _ = rings_points[0]
    for x, y, z in first_peaks:
        angle = math.degrees(math.atan2(y, x))
        
        tab = (cq.Workplane("XY")
              .rect(tab_len, tab_w)
              .extrude(depth))
        
        # Orienter radialement vers l'extérieur et descendre
        tab = (tab
              .rotate((0, 0, 0), (0, 1, 0), 90)
              .rotate((0, 0, 0), (0, 0, 1), angle)
              .translate((x, y, z - tab_len/2)))
        
        stent = stent.union(tab)
    
    # Tabs sur le dernier anneau (peaks)
    last_peaks, _ = rings_points[-1]
    for x, y, z in last_peaks:
        angle = math.degrees(math.atan2(y, x))
        
        tab = (cq.Workplane("XY")
              .rect(tab_len, tab_w)
              .extrude(depth))
        
        tab = (tab
              .rotate((0, 0, 0), (0, 1, 0), 90)
              .rotate((0, 0, 0), (0, 0, 1), angle)
              .translate((x, y, z + tab_len/2)))
        
        stent = stent.union(tab)
    
    return stent

# ------------------------- CLI -------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Stent serpentin avec anneaux verticaux (IMAGE 1)"
    )
    ap.add_argument("--out", type=str, default="stent_vertical.stl")
    ap.add_argument("--linTol", type=float, default=0.01)
    ap.add_argument("--angTol", type=float, default=0.1)
    args = ap.parse_args()
    
    stent = build_stent(CFG)
    export_stl(stent, args.out, lin_tol=args.linTol, ang_tol=args.angTol)
    
    bb = stent.val().BoundingBox()
    print("✅ Stent serpentin généré (anneaux verticaux - IMAGE 1).")
    print(f"- Rayon: {CFG['outer_radius']}mm")
    print(f"- Longueur totale: ~{(CFG['n_rings']-1) * CFG['ring_spacing']:.1f}mm")
    print(f"- Anneaux: {CFG['n_rings']}")
    print(f"- Peaks par anneau: {CFG['n_peaks']}")
    print(f"- Amplitude zigzag: {CFG['amplitude']}mm")
    print(f"- BBox: min=({bb.xmin:.2f},{bb.ymin:.2f},{bb.zmin:.2f})  "
          f"max=({bb.xmax:.2f},{bb.ymax:.2f},{bb.zmax:.2f})")
    print(f"- STL: {args.out}")

if __name__ == "__main__":
    main()