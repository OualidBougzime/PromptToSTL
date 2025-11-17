#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vase_revolve.py — Vase avec profil révolutif lisse et ouverture au sommet
Crée un vase creux par révolution avec des rayons variables en hauteur:
- Base: rayon 30 mm à hauteur 0
- Mi-hauteur: rayon 22 mm à hauteur 60 mm
- Sommet: rayon 35 mm à hauteur 120 mm
Le vase est ouvert en haut (hollow/open top) pour permettre d'y placer des fleurs.
"""

import argparse
import cadquery as cq

# ------------------------- CONFIG (mm) -------------------------
CFG = {
    # Rayons aux différentes hauteurs
    "radius_base": 30.0,      # rayon à la base (hauteur 0)
    "radius_mid": 22.0,       # rayon au milieu (hauteur 60 mm)
    "radius_top": 35.0,       # rayon au sommet (hauteur 120 mm)
    "height_mid": 60.0,       # hauteur du point milieu
    "height_top": 120.0,      # hauteur totale du vase

    # Épaisseurs
    "wall_thickness": 2.0,    # épaisseur des parois
    "base_thickness": 3.0,    # épaisseur du fond
}

# ------------------------- OUTILS -------------------------
def export_stl(shape, path: str, lin_tol=0.02, ang_tol=0.1):
    """Exporte un objet CadQuery en fichier STL."""
    obj = shape.val() if isinstance(shape, cq.Workplane) else shape
    cq.exporters.export(obj, path, tolerance=lin_tol, angularTolerance=ang_tol)

def export_step(shape, path: str):
    """Exporte un objet CadQuery en fichier STEP."""
    obj = shape.val() if isinstance(shape, cq.Workplane) else shape
    cq.exporters.export(obj, path)

# ------------------------- CONSTRUCTION DU VASE -------------------------
def create_vase_with_revolve(cfg) -> cq.Workplane:
    """
    Crée un vase creux avec un profil révolutif.

    Méthode: Création d'un profil 2D dans le plan XZ avec épaisseur de paroi,
    puis révolution autour de l'axe Y pour créer le vase 3D.
    Le profil inclut les courbes intérieures et extérieures pour créer
    automatiquement l'ouverture au sommet et le fond solide.
    """
    # Récupération des paramètres
    r_base = cfg["radius_base"]
    r_mid = cfg["radius_mid"]
    r_top = cfg["radius_top"]
    h_mid = cfg["height_mid"]
    h_top = cfg["height_top"]
    wall = cfg["wall_thickness"]
    base = cfg["base_thickness"]

    # Calcul des rayons intérieurs
    r_base_inner = r_base - wall
    r_mid_inner = r_mid - wall
    r_top_inner = r_top - wall

    # Création du profil 2D dans le plan XZ
    # Le profil trace: centre bas → rayon extérieur → profil extérieur →
    # sommet extérieur → sommet intérieur → profil intérieur → centre
    profile = (
        cq.Workplane("XZ")
        .moveTo(0, 0)  # Point de départ au centre de la base
        .lineTo(r_base, 0)  # Ligne vers le rayon extérieur de la base

        # Profil extérieur avec spline lisse
        .spline([
            (r_base, 0),        # Base extérieure
            (r_mid, h_mid),     # Milieu extérieur
            (r_top, h_top)      # Sommet extérieur
        ])

        # Ligne horizontale vers l'intérieur au sommet (crée l'ouverture)
        .lineTo(r_top_inner, h_top)

        # Profil intérieur avec spline lisse (retour vers la base)
        .spline([
            (r_top_inner, h_top),           # Sommet intérieur
            (r_mid_inner, h_mid),           # Milieu intérieur
            (r_base_inner, base)            # Arrêt à l'épaisseur du fond
        ])

        # Retour au centre
        .lineTo(0, base)
        .close()  # Fermeture du profil
    )

    # Révolution du profil à 360° autour de l'axe Y
    # axisStart=(0,0,0) : point de départ de l'axe au centre
    # axisEnd=(0,1,0) : direction de l'axe = axe Y (vertical)
    vase = profile.revolve(360, (0, 0, 0), (0, 1, 0))

    return vase


def create_vase_alternative(cfg) -> cq.Workplane:
    """
    Méthode alternative: Création d'un vase solide puis évidement.

    Cette méthode crée d'abord un vase solide complet, puis soustrait
    la forme intérieure pour créer la cavité et l'ouverture.
    """
    # Récupération des paramètres
    r_base = cfg["radius_base"]
    r_mid = cfg["radius_mid"]
    r_top = cfg["radius_top"]
    h_mid = cfg["height_mid"]
    h_top = cfg["height_top"]
    wall = cfg["wall_thickness"]
    base = cfg["base_thickness"]

    # Création du profil extérieur
    outer_profile = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(r_base, 0)
        .spline([
            (r_base, 0),
            (r_mid, h_mid),
            (r_top, h_top)
        ])
        .lineTo(0, h_top)
        .close()
    )

    # Révolution pour créer le vase solide
    vase_solid = outer_profile.revolve(360, (0, 0, 0), (0, 1, 0))

    # Création du profil intérieur pour l'évidement
    r_base_inner = r_base - wall
    r_mid_inner = r_mid - wall
    r_top_inner = r_top - wall

    inner_profile = (
        cq.Workplane("XZ")
        .moveTo(0, base)
        .lineTo(r_base_inner, base)
        .spline([
            (r_base_inner, base),
            (r_mid_inner, h_mid),
            (r_top_inner, h_top)
        ])
        .lineTo(0, h_top)
        .close()
    )

    # Révolution de la forme intérieure
    inner_solid = inner_profile.revolve(360, (0, 0, 0), (0, 1, 0))

    # Soustraction pour créer le vase creux
    vase = vase_solid.cut(inner_solid)

    return vase


# ------------------------- MAIN -------------------------
def main():
    parser = argparse.ArgumentParser(description="Génère un vase avec profil révolutif")
    parser.add_argument("--output", "-o", default="vase_revolve.stl",
                        help="Chemin du fichier de sortie STL")
    parser.add_argument("--step", action="store_true",
                        help="Exporter également en format STEP")
    parser.add_argument("--method", choices=["revolve", "alternative"], default="revolve",
                        help="Méthode de construction: 'revolve' (défaut) ou 'alternative'")

    # Paramètres personnalisables
    parser.add_argument("--radius-base", type=float, default=CFG["radius_base"],
                        help=f"Rayon à la base en mm (défaut: {CFG['radius_base']})")
    parser.add_argument("--radius-mid", type=float, default=CFG["radius_mid"],
                        help=f"Rayon au milieu en mm (défaut: {CFG['radius_mid']})")
    parser.add_argument("--radius-top", type=float, default=CFG["radius_top"],
                        help=f"Rayon au sommet en mm (défaut: {CFG['radius_top']})")
    parser.add_argument("--height-mid", type=float, default=CFG["height_mid"],
                        help=f"Hauteur du point milieu en mm (défaut: {CFG['height_mid']})")
    parser.add_argument("--height-top", type=float, default=CFG["height_top"],
                        help=f"Hauteur totale en mm (défaut: {CFG['height_top']})")
    parser.add_argument("--wall-thickness", type=float, default=CFG["wall_thickness"],
                        help=f"Épaisseur des parois en mm (défaut: {CFG['wall_thickness']})")
    parser.add_argument("--base-thickness", type=float, default=CFG["base_thickness"],
                        help=f"Épaisseur du fond en mm (défaut: {CFG['base_thickness']})")

    args = parser.parse_args()

    # Mise à jour de la configuration avec les arguments
    config = CFG.copy()
    config.update({
        "radius_base": args.radius_base,
        "radius_mid": args.radius_mid,
        "radius_top": args.radius_top,
        "height_mid": args.height_mid,
        "height_top": args.height_top,
        "wall_thickness": args.wall_thickness,
        "base_thickness": args.base_thickness,
    })

    # Création du vase selon la méthode choisie
    print(f"Création du vase avec la méthode '{args.method}'...")
    if args.method == "revolve":
        vase = create_vase_with_revolve(config)
    else:
        vase = create_vase_alternative(config)

    # Export STL
    print(f"Export STL vers {args.output}...")
    export_stl(vase, args.output)
    print(f"✓ Fichier STL créé: {args.output}")

    # Export STEP si demandé
    if args.step:
        step_path = args.output.rsplit(".", 1)[0] + ".step"
        print(f"Export STEP vers {step_path}...")
        export_step(vase, step_path)
        print(f"✓ Fichier STEP créé: {step_path}")

    print("\n✓ Vase généré avec succès!")
    print(f"  - Rayon base: {config['radius_base']} mm")
    print(f"  - Rayon milieu: {config['radius_mid']} mm (à {config['height_mid']} mm)")
    print(f"  - Rayon sommet: {config['radius_top']} mm (à {config['height_top']} mm)")
    print(f"  - Épaisseur paroi: {config['wall_thickness']} mm")
    print(f"  - Épaisseur fond: {config['base_thickness']} mm")
    print(f"  - Le vase est ouvert en haut et creux à l'intérieur")


if __name__ == "__main__":
    main()
