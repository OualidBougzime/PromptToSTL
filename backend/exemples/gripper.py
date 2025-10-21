#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
medical_gripper.py — Gripper médical en forme de croix avec perforations
"""

import math
import argparse
import cadquery as cq

# ------------------------- CONFIG (mm) -------------------------
CFG = {
    # Dimensions de la croix
    "arm_length": 25.0,       # longueur de chaque bras
    "arm_width": 8.0,         # largeur de chaque bras
    "center_diameter": 6.0,   # diamètre du centre de la croix
    "thickness": 1.5,         # épaisseur totale
    
    # Cadre/bordure
    "frame_width": 1.2,       # largeur du cadre autour des bras
    "frame_height": 0.8,      # hauteur supplémentaire du cadre
    
    # Perforations (trous)
    "enable_perforations": True,
    "hole_diameter": 0.8,     # diamètre des trous
    "hole_spacing": 1.5,      # espacement entre trous
    "perforation_depth": 1.0, # profondeur des trous
    
    # Arrondis
    "arm_fillet": 3.0,        # rayon d'arrondi des bouts de bras
    "center_fillet": 1.0,     # rayon d'arrondi au centre
}

# ------------------------- OUTILS -------------------------
def export_stl(shape, path: str, lin_tol=0.02, ang_tol=0.1):
    obj = shape.val() if isinstance(shape, cq.Workplane) else shape
    cq.exporters.export(obj, path, tolerance=lin_tol, angularTolerance=ang_tol)

# ------------------------- CONSTRUCTION DU GRIPPER -------------------------
def create_cross_base(cfg) -> cq.Workplane:
    """Crée la forme de base de la croix (4 bras)."""
    arm_len = cfg["arm_length"]
    arm_w = cfg["arm_width"]
    center_d = cfg["center_diameter"]
    thickness = cfg["thickness"]
    
    # Créer le centre circulaire
    base = cq.Workplane("XY").circle(center_d / 2).extrude(thickness)
    
    # Créer les 4 bras
    for angle in [0, 90, 180, 270]:
        # Position de départ du bras (depuis le bord du centre)
        start_offset = center_d / 2
        
        # Créer un bras rectangulaire
        arm = (cq.Workplane("XY")
              .rect(arm_len, arm_w)
              .extrude(thickness))
        
        # Positionner le bras (centrer son origine au milieu du cercle central)
        arm = (arm
              .translate((start_offset + arm_len/2, 0, 0))
              .rotate((0, 0, 0), (0, 0, 1), angle))
        
        base = base.union(arm)
    
    return base

def add_rounded_edges(cfg, cross) -> cq.Workplane:
    """Arrondit les extrémités des bras."""
    arm_fillet = cfg["arm_fillet"]
    
    # Sélectionner et arrondir les edges
    # Note: CadQuery peut avoir des difficultés avec les fillets complexes
    # On va essayer une approche simplifiée
    try:
        # Arrondir les edges verticales (perpendiculaires à Z)
        cross = cross.edges("|Z").fillet(cfg["center_fillet"])
    except:
        pass  # Si le fillet échoue, continuer sans
    
    return cross

def create_frame(cfg, cross_base) -> cq.Workplane:
    """Crée le cadre autour de la croix."""
    frame_w = cfg["frame_width"]
    frame_h = cfg["frame_height"]
    thickness = cfg["thickness"]
    
    # Créer une version légèrement plus grande de la croix
    arm_len = cfg["arm_length"] + frame_w * 2
    arm_w = cfg["arm_width"] + frame_w * 2
    center_d = cfg["center_diameter"] + frame_w * 2
    
    # Créer la croix externe
    outer = cq.Workplane("XY").circle(center_d / 2).extrude(thickness + frame_h)
    
    for angle in [0, 90, 180, 270]:
        start_offset = center_d / 2
        arm = (cq.Workplane("XY")
              .rect(arm_len, arm_w)
              .extrude(thickness + frame_h))
        arm = (arm
              .translate((start_offset + arm_len/2, 0, 0))
              .rotate((0, 0, 0), (0, 0, 1), angle))
        outer = outer.union(arm)
    
    # Soustraire la croix de base pour créer le cadre
    # Élever légèrement la base pour créer le cadre autour
    cross_raised = cross_base.translate((0, 0, frame_h))
    frame = outer.cut(cross_raised)
    
    return frame

def add_perforations(cfg, gripper) -> cq.Workplane:
    """Ajoute un motif de perforations (trous) sur la surface."""
    if not cfg["enable_perforations"]:
        return gripper
    
    hole_d = cfg["hole_diameter"]
    spacing = cfg["hole_spacing"]
    depth = cfg["perforation_depth"]
    thickness = cfg["thickness"]
    arm_len = cfg["arm_length"]
    arm_w = cfg["arm_width"]
    center_d = cfg["center_diameter"]
    frame_w = cfg["frame_width"]
    
    # Créer les trous dans une grille
    # Pour chaque bras et le centre
    holes = None
    
    # Centre circulaire
    radius = center_d / 2 - frame_w
    n_rows = int(radius * 2 / spacing)
    
    for i in range(-n_rows, n_rows + 1):
        for j in range(-n_rows, n_rows + 1):
            x = i * spacing
            y = j * spacing
            
            # Vérifier si le point est dans le cercle central
            if math.sqrt(x*x + y*y) < radius:
                hole = (cq.Workplane("XY")
                       .center(x, y)
                       .circle(hole_d / 2)
                       .extrude(depth)
                       .translate((0, 0, thickness - depth)))
                holes = hole if holes is None else holes.union(hole)
    
    # Perforations dans les 4 bras
    for angle in [0, 90, 180, 270]:
        # Zone du bras
        start_x = center_d / 2 + frame_w
        end_x = center_d / 2 + arm_len - frame_w
        half_width = (arm_w - 2 * frame_w) / 2
        
        n_x = int((end_x - start_x) / spacing)
        n_y = int((2 * half_width) / spacing)
        
        for i in range(n_x):
            for j in range(-n_y//2, n_y//2 + 1):
                x_local = start_x + i * spacing
                y_local = j * spacing
                
                # Vérifier si dans les limites du bras
                if abs(y_local) < half_width:
                    # Créer le trou
                    hole = (cq.Workplane("XY")
                           .center(x_local, y_local)
                           .circle(hole_d / 2)
                           .extrude(depth)
                           .translate((0, 0, thickness - depth)))
                    
                    # Rotation selon l'angle du bras
                    hole = hole.rotate((0, 0, 0), (0, 0, 1), angle)
                    holes = hole if holes is None else holes.union(hole)
    
    # Soustraire tous les trous
    if holes:
        gripper = gripper.cut(holes)
    
    return gripper

def create_decorative_holes_pattern(cfg, gripper) -> cq.Workplane:
    """Alternative: motif hexagonal de trous."""
    if not cfg["enable_perforations"]:
        return gripper
    
    hole_d = cfg["hole_diameter"]
    spacing = cfg["hole_spacing"]
    depth = cfg["perforation_depth"]
    thickness = cfg["thickness"]
    arm_len = cfg["arm_length"]
    arm_w = cfg["arm_width"]
    center_d = cfg["center_diameter"]
    frame_w = cfg["frame_width"]
    
    # Motif hexagonal (honeycomb)
    holes = None
    
    # Définir la zone à perforer
    max_extent = center_d / 2 + arm_len
    n_rows = int(max_extent * 2 / spacing) + 2
    
    for row in range(-n_rows, n_rows + 1):
        for col in range(-n_rows, n_rows + 1):
            # Position hexagonale
            x = col * spacing
            y = row * spacing * math.sqrt(3) / 2
            
            # Décalage alterné pour motif hexagonal
            if row % 2 == 1:
                x += spacing / 2
            
            # Vérifier si le point est dans la croix (approximation)
            in_cross = False
            
            # Centre
            if math.sqrt(x*x + y*y) < (center_d / 2 - frame_w):
                in_cross = True
            
            # Bras horizontaux
            if abs(y) < (arm_w / 2 - frame_w):
                if (center_d/2 + frame_w) < abs(x) < (center_d/2 + arm_len - frame_w):
                    in_cross = True
            
            # Bras verticaux
            if abs(x) < (arm_w / 2 - frame_w):
                if (center_d/2 + frame_w) < abs(y) < (center_d/2 + arm_len - frame_w):
                    in_cross = True
            
            if in_cross:
                hole = (cq.Workplane("XY")
                       .center(x, y)
                       .circle(hole_d / 2)
                       .extrude(depth)
                       .translate((0, 0, thickness - depth)))
                holes = hole if holes is None else holes.union(hole)
    
    if holes:
        gripper = gripper.cut(holes)
    
    return gripper

def build_gripper(cfg, hexagonal_pattern=False) -> cq.Workplane:
    """Construit le gripper complet."""
    # Créer la base de la croix
    cross = create_cross_base(cfg)
    
    # Ajouter le cadre
    frame = create_frame(cfg, cross)
    gripper = cross.union(frame)
    
    # Arrondir les bords
    gripper = add_rounded_edges(cfg, gripper)
    
    # Ajouter les perforations
    if hexagonal_pattern:
        gripper = create_decorative_holes_pattern(cfg, gripper)
    else:
        gripper = add_perforations(cfg, gripper)
    
    return gripper

# ------------------------- CLI -------------------------
def main():
    ap = argparse.ArgumentParser(description="CadQuery — Gripper médical en croix")
    ap.add_argument("--out", type=str, default="gripper.stl")
    ap.add_argument("--hex", action="store_true", help="Utiliser motif hexagonal")
    ap.add_argument("--linTol", type=float, default=0.02)
    ap.add_argument("--angTol", type=float, default=0.1)
    args = ap.parse_args()
    
    gripper = build_gripper(CFG, hexagonal_pattern=args.hex)
    export_stl(gripper, args.out, lin_tol=args.linTol, ang_tol=args.angTol)
    
    bb = gripper.val().BoundingBox()
    print("✅ Gripper médical généré.")
    print(f"- Longueur de bras: {CFG['arm_length']}mm")
    print(f"- Largeur de bras: {CFG['arm_width']}mm")
    print(f"- Épaisseur: {CFG['thickness']}mm")
    print(f"- BBox: min=({bb.xmin:.2f},{bb.ymin:.2f},{bb.zmin:.2f})  "
          f"max=({bb.xmax:.2f},{bb.ymax:.2f},{bb.zmax:.2f})")
    print(f"- STL: {args.out}")

if __name__ == "__main__":
    main()