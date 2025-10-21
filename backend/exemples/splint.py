#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_orthosis_parametric.py — Génère une orthèse (attelle) paramétrique au format STL
VERSION PROFESSIONNELLE avec courbure anatomique et sangles 3D

Dépendances : numpy uniquement.
Installation : pip install numpy
"""

import argparse
import struct
import numpy as np
from typing import Tuple

# ------------------- Outils STL -------------------

def compute_normals(tris: np.ndarray) -> np.ndarray:
    v1 = tris[:,1] - tris[:,0]
    v2 = tris[:,2] - tris[:,0]
    n = np.cross(v1, v2)
    lens = np.linalg.norm(n, axis=1)
    lens[lens == 0] = 1.0
    n = (n.T / lens).T
    return n.astype(np.float32)

def write_binary_stl(path: str, tris: np.ndarray):
    tris = np.asarray(tris, dtype=np.float32)
    norms = compute_normals(tris)
    with open(path, "wb") as f:
        header = b"Professional orthosis parametric"
        f.write(header + b" " * (80 - len(header)))
        f.write(struct.pack("<I", tris.shape[0]))
        for i in range(tris.shape[0]):
            nx, ny, nz = norms[i].tolist()
            v1 = tris[i,0].tolist()
            v2 = tris[i,1].tolist()
            v3 = tris[i,2].tolist()
            packed = struct.pack("<12f", nx, ny, nz, *v1, *v2, *v3)
            f.write(packed)
            f.write(struct.pack("<H", 0))

# ------------------- Géométrie orthèse -------------------

def radius_profile(v: float, r0: float, r1: float, flare: float, 
                   u_norm: float = 0.0, curve_depth: float = 0.0) -> float:
    """
    Profil de rayon avec courbure anatomique palmaire.
    
    Parameters:
        v: position normalisée le long de la longueur (0-1)
        r0: rayon proximal
        r1: rayon distal
        flare: évasement distal
        u_norm: angle normalisé (-1 à 1, -1 = face palmaire)
        curve_depth: profondeur de la voûte palmaire (mm)
    """
    r = (1.0 - v) * r0 + v * r1
    
    # Évasement progressif proche du distal (dernier 20%)
    if flare != 0.0:
        t = max(0.0, (v - 0.8) / 0.2)
        r += t * flare
    
    # Courbure anatomique palmaire
    if curve_depth > 0.0:
        if u_norm < 0:  # Face palmaire (creux)
            curve_factor = (1 - v * 0.5)  # Diminue vers le distal
            curve = curve_depth * ((-u_norm) ** 1.5) * curve_factor
            r -= curve
        else:  # Face dorsale (légère bosse)
            r += curve_depth * 0.1 * (u_norm ** 2)
    
    return r

def grid_param(length: float, r0: float, r1: float, arc_deg: float, thickness: float,
               nu: int, nv: int, flare: float, curve_depth: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Construit les grilles (inner, outer) de taille [(nv+1), (nu+1), 3]
    avec courbure anatomique palmaire.
    """
    arc_rad = np.deg2rad(arc_deg)
    u_values = np.linspace(-arc_rad/2.0, arc_rad/2.0, nu+1, dtype=np.float64)
    v_values = np.linspace(0.0, 1.0, nv+1, dtype=np.float64)

    inner = np.zeros((nv+1, nu+1, 3), dtype=np.float64)
    outer = np.zeros((nv+1, nu+1, 3), dtype=np.float64)

    for i, v in enumerate(v_values):
        z = v * length
        
        for j, u in enumerate(u_values):
            # Angle normalisé pour courbure anatomique
            u_norm = 2.0 * u / arc_rad  # -1 à 1
            
            r_in = radius_profile(v, r0, r1, flare, u_norm, curve_depth)
            r_out = r_in + thickness
            
            cosu = np.cos(u)
            sinu = np.sin(u)

            inner[i, j, 0] = r_in * cosu
            inner[i, j, 1] = r_in * sinu
            inner[i, j, 2] = z

            outer[i, j, 0] = r_out * cosu
            outer[i, j, 1] = r_out * sinu
            outer[i, j, 2] = z

    return inner, outer

def quads_to_tris(a, b, c, d):
    """Retourne 2 triangles pour une face quad (a,b,c,d)."""
    return np.array([[a, b, c], [a, c, d]], dtype=np.float32)

def triangulate_cuff(inner: np.ndarray, outer: np.ndarray) -> np.ndarray:
    """
    Triangule les surfaces intérieure/extérieur + murs latéraux + bords.
    """
    nv, nu = inner.shape[0]-1, inner.shape[1]-1
    tris = []

    # Surfaces principale: inner et outer
    for i in range(nv):
        for j in range(nu):
            # Inner
            a = inner[i, j];     b = inner[i, j+1]
            c = inner[i+1, j+1]; d = inner[i+1, j]
            tris.extend(quads_to_tris(a, b, c, d))

            # Outer
            a = outer[i, j];     b = outer[i, j+1]
            c = outer[i+1, j+1]; d = outer[i+1, j]
            tris.extend(quads_to_tris(a, b, c, d))

    # Murs latéraux (ouverture)
    for i in range(nv):
        # bord -u (j=0)
        a = inner[i, 0];    b = outer[i, 0]
        c = outer[i+1, 0];  d = inner[i+1, 0]
        tris.extend(quads_to_tris(a, b, c, d))

        # bord +u (j=nu)
        a = inner[i, nu];    b = outer[i, nu]
        c = outer[i+1, nu];  d = inner[i+1, nu]
        tris.extend(quads_to_tris(a, b, c, d))

    # Bords proximal et distal
    for j in range(nu):
        # proximal (i=0)
        a = inner[0, j];     b = inner[0, j+1]
        c = outer[0, j+1];   d = outer[0, j]
        tris.extend(quads_to_tris(a, b, c, d))

        # distal (i=nv)
        a = inner[nv, j];     b = inner[nv, j+1]
        c = outer[nv, j+1];   d = outer[nv, j]
        tris.extend(quads_to_tris(a, b, c, d))

    return np.asarray(tris, dtype=np.float32)

def add_straps_3d(inner: np.ndarray, outer: np.ndarray, 
                  positions: list, width: float, height: float) -> list:
    """
    Ajoute des sangles 3D en relief aux positions données (v normalisé 0-1).
    """
    nv, nu = inner.shape[0]-1, inner.shape[1]-1
    tris = []
    
    for v_pos in positions:
        i = int(v_pos * nv)
        if i >= nv:
            i = nv - 1
        
        # Sangles sur les bords latéraux (j=0 et j=nu)
        for j_side in [0, nu]:
            p_in = inner[i, j_side]
            p_out = outer[i, j_side]
            
            # Centre de la sangle
            center = (p_in + p_out) / 2
            
            # Direction tangente (le long de Z)
            if i < nv - 1:
                tangent = inner[i+1, j_side] - p_in
            else:
                tangent = p_in - inner[i-1, j_side]
            tangent = tangent / np.linalg.norm(tangent)
            
            # Direction normale (radiale)
            normal = (p_out - p_in)
            normal = normal / np.linalg.norm(normal)
            
            # Direction perpendiculaire
            perp = np.cross(tangent, normal)
            
            # 8 sommets d'une box
            hw = width / 2
            hh = height / 2
            
            # 4 coins de base
            c1 = center - tangent * hw - perp * hh
            c2 = center + tangent * hw - perp * hh
            c3 = center + tangent * hw + perp * hh
            c4 = center - tangent * hw + perp * hh
            
            # Extrusion vers l'extérieur
            extrude = normal * 4.0
            v1 = c1 - extrude
            v2 = c2 - extrude
            v3 = c3 - extrude
            v4 = c4 - extrude
            v5 = c1 + extrude
            v6 = c2 + extrude
            v7 = c3 + extrude
            v8 = c4 + extrude
            
            # 12 triangles (6 faces)
            # Face avant
            tris.append(np.array([v5, v6, v7], dtype=np.float32))
            tris.append(np.array([v5, v7, v8], dtype=np.float32))
            # Face arrière
            tris.append(np.array([v1, v3, v2], dtype=np.float32))
            tris.append(np.array([v1, v4, v3], dtype=np.float32))
            # Côtés
            tris.append(np.array([v1, v2, v6], dtype=np.float32))
            tris.append(np.array([v1, v6, v5], dtype=np.float32))
            tris.append(np.array([v2, v3, v7], dtype=np.float32))
            tris.append(np.array([v2, v7, v6], dtype=np.float32))
            tris.append(np.array([v3, v4, v8], dtype=np.float32))
            tris.append(np.array([v3, v8, v7], dtype=np.float32))
            tris.append(np.array([v4, v1, v5], dtype=np.float32))
            tris.append(np.array([v4, v5, v8], dtype=np.float32))
    
    return tris

def make_orthosis(length=270.0, r0=35.0, r1=30.0, arc_deg=220.0, thickness=3.5,
                  nu=120, nv=150, flare=6.0, curve_depth=15.0,
                  add_straps=True, strap_positions=[0.18, 0.55, 0.82],
                  strap_width=25.0, strap_height=8.0) -> np.ndarray:
    """
    Génère une orthèse professionnelle avec courbure anatomique et sangles 3D.
    """
    inner, outer = grid_param(length, r0, r1, arc_deg, thickness, nu, nv, flare, curve_depth)
    tris = triangulate_cuff(inner, outer)
    tris_list = list(tris)
    
    # Ajouter sangles si demandé
    if add_straps:
        strap_tris = add_straps_3d(inner, outer, strap_positions, strap_width, strap_height)
        tris_list.extend(strap_tris)
    
    return np.asarray(tris_list, dtype=np.float32)

# ------------------- CLI -------------------

def main():
    ap = argparse.ArgumentParser(description="Génère une orthèse professionnelle paramétrique (STL binaire).")
    ap.add_argument("--length", type=float, default=270.0, help="Longueur (mm)")
    ap.add_argument("--r0", type=float, default=35.0, help="Rayon intérieur proximal (mm)")
    ap.add_argument("--r1", type=float, default=30.0, help="Rayon intérieur distal (mm)")
    ap.add_argument("--arc-deg", type=float, default=220.0, help="Angle couvert en degrés")
    ap.add_argument("--thickness", type=float, default=3.5, help="Épaisseur coque (mm)")
    ap.add_argument("--nu", type=int, default=120, help="Résolution angulaire (mailles)")
    ap.add_argument("--nv", type=int, default=150, help="Résolution axiale (mailles)")
    ap.add_argument("--flare", type=float, default=6.0, help="Évasement distal additionnel (mm)")
    ap.add_argument("--curve-depth", type=float, default=15.0, help="Profondeur courbure palmaire (mm)")
    ap.add_argument("--add-straps", action="store_true", default=True, help="Ajouter sangles 3D")
    ap.add_argument("--strap-width", type=float, default=25.0, help="Largeur sangles (mm)")
    ap.add_argument("--strap-height", type=float, default=8.0, help="Hauteur relief sangles (mm)")
    ap.add_argument("--out", type=str, default="professional_hand_splint.stl", help="Chemin de sortie STL (binaire)")
    args = ap.parse_args()

    tris = make_orthosis(
        length=args.length, r0=args.r0, r1=args.r1,
        arc_deg=args.arc_deg, thickness=args.thickness,
        nu=args.nu, nv=args.nv, flare=args.flare,
        curve_depth=args.curve_depth,
        add_straps=args.add_straps,
        strap_width=args.strap_width,
        strap_height=args.strap_height
    )

    write_binary_stl(args.out, tris)

    # Résumé
    pts = tris.reshape(-1,3)
    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    size = maxs - mins
    print("✅ Orthèse professionnelle générée.")
    print(f"- Triangles : {tris.shape[0]}")
    print(f"- Boîte englobante min : {mins}")
    print(f"- Boîte englobante max : {maxs}")
    print(f"- Dimensions (LxHxP)   : {size}")
    print(f"- Fichier STL : {args.out}")

if __name__ == "__main__":
    main()