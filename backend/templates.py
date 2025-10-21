#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
templates.py — Templates de génération pour tous les types CAD
Supporte: splint, stent, lattice, facade_pyramid, facade_parametric, gripper
"""

import logging
from typing import Dict, Any

log = logging.getLogger("cadamx.templates")


class CodeTemplates:
    """Générateur de code basé sur des templates pour chaque type d'application"""
    
    @staticmethod
    def generate_splint(analysis: Dict[str, Any]) -> str:
        """Template pour splint (orthèse) - VERSION COMPLÈTE"""
        sections = analysis.get('sections', [])
        features = analysis.get('features', {})
        curvatures = analysis.get('curvatures', {})
        splint_type = analysis.get('splint_type', 'resting')
        edge_radius = analysis.get('edge_radius', 2.0)
        
        if not sections:
            sections = [{
                'name': 'main',
                'length': 270.0,
                'width_start': 70.0,
                'width_end': 60.0,
                'angle': 0.0
            }]
        
        total_length = analysis.get('total_length_explicit')
        if total_length is None:
            total_length = sum(s.get('length', 100) for s in sections)
        
        section_configs = []
        cumulative_length = 0.0
        
        for idx, section in enumerate(sections):
            length = section.get('length', 100.0)
            width_start = section.get('width_start', section.get('width', 70.0))
            width_end = section.get('width_end', section.get('width', 70.0))
            angle = section.get('angle', 0.0)
            name = section.get('name', f'section{idx}')
            
            v_start = cumulative_length / total_length
            v_end = (cumulative_length + length) / total_length
            
            curve_depth = curvatures.get(name, 5.0 if name == 'forearm' else 8.0 if name == 'palm' else 3.0)
            
            section_configs.append({
                'name': name,
                'v_start': v_start,
                'v_end': v_end,
                'r_start': width_start / 2,
                'r_end': width_end / 2,
                'angle': angle,
                'curve_depth': curve_depth
            })
            
            cumulative_length += length
        
        arc_deg = 220.0
        thickness = analysis.get('thickness', 3.5)
        
        fillets = features.get('fillets')
        if fillets and isinstance(fillets, dict):
            fillet_enabled = fillets.get('enabled', True)
            fillet_radius = fillets.get('radius', 8.0)
        else:
            fillet_enabled = bool(fillets) if fillets else False
            fillet_radius = 8.0 if fillet_enabled else 0.0
        
        slots = features.get('slots')
        if slots:
            positions = slots.get('positions', [50, 150, 220])
            strap_pos_norm = [p / total_length for p in positions]
            strap_width = slots.get('width', 25.0)
            strap_depth = slots.get('depth', 3.0)
            strap_length = slots.get('length', 20.0)
        else:
            strap_pos_norm = [0.18, 0.55, 0.82]
            strap_width = 25.0
            strap_depth = 3.0
            strap_length = 20.0
        
        section_names = ', '.join([s.get('name', f'section{i}') for i, s in enumerate(sections)])
        
        code = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import struct, math
import numpy as np
from pathlib import Path

# ===== PARAMETERS =====
LENGTH = {total_length}
ARC_DEG = {arc_deg}
THICKNESS = {thickness}
NU, NV = 120, 180

SECTIONS = {section_configs}

STRAP_POSITIONS = {strap_pos_norm}
STRAP_WIDTH = {strap_width}
STRAP_LENGTH = {strap_length}
STRAP_HEIGHT = 8.0

# ===== FUNCTIONS =====
def compute_normals(tris):
    v1 = tris[:,1] - tris[:,0]
    v2 = tris[:,2] - tris[:,0]
    n = np.cross(v1, v2)
    lens = np.linalg.norm(n, axis=1)
    lens[lens == 0] = 1.0
    return (n.T / lens).T.astype(np.float32)

def write_stl(path, tris):
    tris = np.asarray(tris, dtype=np.float32)
    norms = compute_normals(tris)
    with open(path, "wb") as f:
        f.write(b"Generated Splint" + b" " * 64)
        f.write(struct.pack("<I", len(tris)))
        for i in range(len(tris)):
            nx, ny, nz = norms[i]
            v1, v2, v3 = tris[i,0], tris[i,1], tris[i,2]
            f.write(struct.pack("<12f", nx, ny, nz, *v1, *v2, *v3))
            f.write(struct.pack("<H", 0))

def find_section_params(v):
    for s in SECTIONS:
        if s['v_start'] <= v <= s['v_end']:
            v_range = s['v_end'] - s['v_start']
            v_local = (v - s['v_start']) / max(v_range, 0.001)
            r = (1.0 - v_local) * s['r_start'] + v_local * s['r_end']
            return r, s['curve_depth']
    last = SECTIONS[-1]
    return last['r_end'], last['curve_depth']

def radius_profile(v, u_norm):
    r, curve = find_section_params(v)
    if curve > 0 and abs(u_norm) > 0.01:
        if u_norm < 0:
            r -= curve * ((-u_norm) ** 1.5) * (1 - v * 0.3)
        else:
            r += curve * 0.15 * (u_norm ** 2)
    return r

def grid_param(length, arc_deg, thickness, nu, nv):
    arc_rad = np.deg2rad(arc_deg)
    u_values = np.linspace(-arc_rad/2, arc_rad/2, nu+1)
    v_values = np.linspace(0.0, 1.0, nv+1)
    
    inner = np.zeros((nv+1, nu+1, 3))
    outer = np.zeros((nv+1, nu+1, 3))
    
    for i, v in enumerate(v_values):
        z = v * length
        for j, u in enumerate(u_values):
            u_norm = 2.0 * u / arc_rad
            r_in = radius_profile(v, u_norm)
            r_out = r_in + thickness
            
            cos_u, sin_u = np.cos(u), np.sin(u)
            inner[i,j] = [r_in * cos_u, r_in * sin_u, z]
            outer[i,j] = [r_out * cos_u, r_out * sin_u, z]
    
    return inner, outer

def triangulate(inner, outer):
    nv, nu = inner.shape[0]-1, inner.shape[1]-1
    tris = []
    
    for i in range(nv):
        for j in range(nu):
            # Inner
            a, b = inner[i,j], inner[i,j+1]
            c, d = inner[i+1,j+1], inner[i+1,j]
            tris.extend([
                np.array([a,b,c],dtype=np.float32),
                np.array([a,c,d],dtype=np.float32)
            ])
            # Outer
            a, b = outer[i,j], outer[i,j+1]
            c, d = outer[i+1,j+1], outer[i+1,j]
            tris.extend([
                np.array([a,b,c],dtype=np.float32),
                np.array([a,c,d],dtype=np.float32)
            ])
    
    # Edges
    for i in range(nv):
        tris.extend([
            np.array([inner[i,0], outer[i,0], outer[i+1,0]],dtype=np.float32),
            np.array([inner[i,0], outer[i+1,0], inner[i+1,0]],dtype=np.float32),
            np.array([inner[i,nu], outer[i,nu], outer[i+1,nu]],dtype=np.float32),
            np.array([inner[i,nu], outer[i+1,nu], inner[i+1,nu]],dtype=np.float32)
        ])
    
    # Caps
    for j in range(nu):
        tris.extend([
            np.array([inner[0,j], inner[0,j+1], outer[0,j+1]],dtype=np.float32),
            np.array([inner[0,j], outer[0,j+1], outer[0,j]],dtype=np.float32),
            np.array([inner[nv,j], inner[nv,j+1], outer[nv,j+1]],dtype=np.float32),
            np.array([inner[nv,j], outer[nv,j+1], outer[nv,j]],dtype=np.float32)
        ])
    
    return tris

def add_straps(inner, outer, positions, width, length, height):
    nv, nu = inner.shape[0]-1, inner.shape[1]-1
    tris = []
    
    for v_pos in positions:
        i = min(int(v_pos * nv), nv - 1)
        
        for j_side in [0, nu]:
            p_in, p_out = inner[i, j_side], outer[i, j_side]
            center = (p_in + p_out) / 2
            
            tangent = (inner[min(i+1, nv), j_side] - inner[max(i-1, 0), j_side])
            tangent = tangent / (np.linalg.norm(tangent) + 1e-6)
            
            normal = (p_out - p_in)
            normal = normal / (np.linalg.norm(normal) + 1e-6)
            
            perp = np.cross(tangent, normal)
            perp = perp / (np.linalg.norm(perp) + 1e-6)
            
            hw, hh, hl = width/2, height/2, length/2
            
            corners_local = [
                (-hl, -hw, -hh), (hl, -hw, -hh), (hl, hw, -hh), (-hl, hw, -hh),
                (-hl, -hw, hh), (hl, -hw, hh), (hl, hw, hh), (-hl, hw, hh)
            ]
            
            corners = []
            for lx, ly, lz in corners_local:
                point = center + lx * tangent + ly * perp + lz * normal
                corners.append(point)
            
            v = corners
            tris.extend([
                np.array([v[0],v[1],v[2]],dtype=np.float32), np.array([v[0],v[2],v[3]],dtype=np.float32),
                np.array([v[4],v[6],v[5]],dtype=np.float32), np.array([v[4],v[7],v[6]],dtype=np.float32),
                np.array([v[0],v[1],v[5]],dtype=np.float32), np.array([v[0],v[5],v[4]],dtype=np.float32),
                np.array([v[1],v[2],v[6]],dtype=np.float32), np.array([v[1],v[6],v[5]],dtype=np.float32),
                np.array([v[2],v[3],v[7]],dtype=np.float32), np.array([v[2],v[7],v[6]],dtype=np.float32),
                np.array([v[3],v[0],v[4]],dtype=np.float32), np.array([v[3],v[4],v[7]],dtype=np.float32),
            ])
    
    return tris

# ===== MAIN =====
print("Generating splint...")
inner, outer = grid_param(LENGTH, ARC_DEG, THICKNESS, NU, NV)
tris = triangulate(inner, outer)
tris.extend(add_straps(inner, outer, STRAP_POSITIONS, STRAP_WIDTH, STRAP_LENGTH, STRAP_HEIGHT))

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
write_stl(str(output_dir / "generated_splint.stl"), tris)
print(f"✅ STL: generated_splint.stl ({{len(tris)}} triangles)")
"""
        return code
    
    @staticmethod
    def generate_stent(analysis: Dict[str, Any]) -> str:
        """Template stent - VERSION CADQUERY avec cellules diamant"""
        params = analysis.get('parameters', {})
        
        outer_radius = params.get('outer_radius', 8.0)
        length = params.get('length', 40.0)
        n_peaks = params.get('n_peaks', 8)
        n_rings = params.get('n_rings', 6)
        amplitude = params.get('amplitude', 3.0)
        ring_spacing = params.get('ring_spacing', 6.0)
        strut_width = params.get('strut_width', 0.6)
        strut_depth = params.get('strut_depth', 0.4)
        
        code = f"""#!/usr/bin/env python3
import math
import cadquery as cq
from pathlib import Path

CFG = {{
    "outer_radius": {outer_radius},
    "length": {length},
    "n_peaks": {n_peaks},
    "n_rings": {n_rings},
    "amplitude": {amplitude},
    "ring_spacing": {ring_spacing},
    "strut_width": {strut_width},
    "strut_depth": {strut_depth},
}}

def create_strut_between_points(cfg, p1, p2):
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    
    width = cfg["strut_width"]
    depth = cfg["strut_depth"]
    
    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    
    if length < 0.001:
        return None
    
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    cz = (z1 + z2) / 2
    
    angle_z = math.degrees(math.atan2(dy, dx))
    horizontal_dist = math.sqrt(dx*dx + dy*dy)
    angle_y = math.degrees(math.atan2(dz, horizontal_dist))
    
    strut = (cq.Workplane("XY")
            .center(0, 0)
            .rect(length, width)
            .extrude(depth))
    
    strut = (strut
            .rotate((0, 0, 0), (0, 1, 0), -angle_y)
            .rotate((0, 0, 0), (0, 0, 1), angle_z)
            .translate((cx, cy, cz)))
    
    return strut

def get_ring_points(cfg, z_center, phase_shift=0):
    R = cfg["outer_radius"]
    n_peaks = cfg["n_peaks"]
    amplitude = cfg["amplitude"]
    
    peaks = []
    valleys = []
    
    angle_step = 360.0 / n_peaks
    
    for i in range(n_peaks):
        angle_peak = i * angle_step + phase_shift
        x_peak = R * math.cos(math.radians(angle_peak))
        y_peak = R * math.sin(math.radians(angle_peak))
        z_peak = z_center + amplitude / 2
        peaks.append((x_peak, y_peak, z_peak))
        
        angle_valley = angle_peak + angle_step / 2
        x_valley = R * math.cos(math.radians(angle_valley))
        y_valley = R * math.sin(math.radians(angle_valley))
        z_valley = z_center - amplitude / 2
        valleys.append((x_valley, y_valley, z_valley))
    
    return peaks, valleys

def create_ring_struts(cfg, peaks, valleys):
    stent = None
    n = len(peaks)
    
    for i in range(n):
        s1 = create_strut_between_points(cfg, peaks[i], valleys[i])
        if s1:
            stent = s1 if stent is None else stent.union(s1)
        
        next_peak = peaks[(i + 1) % n]
        s2 = create_strut_between_points(cfg, valleys[i], next_peak)
        if s2:
            stent = stent.union(s2) if stent else s2
    
    return stent

def create_bridges_between_rings(cfg, rings_points):
    bridges = None
    
    for ring_idx in range(len(rings_points) - 1):
        peaks1, valleys1 = rings_points[ring_idx]
        peaks2, valleys2 = rings_points[ring_idx + 1]
        
        n_peaks = len(peaks1)
        
        if ring_idx % 2 == 0:
            for i in range(n_peaks):
                bridge = create_strut_between_points(cfg, peaks1[i], valleys2[i])
                if bridge:
                    bridges = bridge if bridges is None else bridges.union(bridge)
        else:
            for i in range(n_peaks):
                bridge = create_strut_between_points(cfg, valleys1[i], peaks2[i])
                if bridge:
                    bridges = bridge if bridges is None else bridges.union(bridge)
    
    return bridges

def build_stent(cfg):
    n_rings = cfg["n_rings"]
    ring_spacing = cfg["ring_spacing"]
    n_peaks = cfg["n_peaks"]
    
    total_height = (n_rings - 1) * ring_spacing
    z_start = -total_height / 2
    
    stent = None
    rings_points = []
    
    for ring_idx in range(n_rings):
        z = z_start + ring_idx * ring_spacing
        phase_shift = 0 if ring_idx % 2 == 0 else (360.0 / n_peaks) / 2
        
        peaks, valleys = get_ring_points(cfg, z, phase_shift)
        rings_points.append((peaks, valleys))
        
        ring = create_ring_struts(cfg, peaks, valleys)
        if ring:
            stent = ring if stent is None else stent.union(ring)
    
    bridges = create_bridges_between_rings(cfg, rings_points)
    if bridges:
        stent = stent.union(bridges)
    
    return stent

print("Generating stent with diamond cells...")
model = build_stent(CFG)

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
cq.exporters.export(model.val(), str(output_dir / "generated_stent.stl"))
print(f"✅ STL: generated_stent.stl ({{CFG['n_rings']}} rings, {{CFG['n_peaks']}} peaks)")
"""
        return code
    
    @staticmethod
    def generate_gripper(analysis: Dict[str, Any]) -> str:
        """Template pour gripper - SUPPORT MULTI-BRAS"""
        params = analysis.get('parameters', {})
        
        arm_length = params.get('arm_length', 25.0)
        arm_width = params.get('arm_width', 8.0)
        center_diameter = params.get('center_diameter', 6.0)
        thickness = params.get('thickness', 1.5)
        n_arms = params.get('n_arms', 4)
        
        code = f"""#!/usr/bin/env python3
import math, struct, numpy as np
from pathlib import Path

ARM_L, ARM_W = {arm_length}, {arm_width}
CENTER_D, THICK = {center_diameter}, {thickness}
N_ARMS = {n_arms}

def compute_normals(tris):
    v1, v2 = tris[:,1] - tris[:,0], tris[:,2] - tris[:,0]
    n = np.cross(v1, v2)
    lens = np.linalg.norm(n, axis=1)
    lens[lens == 0] = 1.0
    return (n.T / lens).T.astype(np.float32)

def write_stl(path, tris):
    tris = np.asarray(tris, dtype=np.float32)
    norms = compute_normals(tris)
    with open(path, "wb") as f:
        header = f"Gripper {{N_ARMS}}-Armed".encode('ascii')
        f.write(header + b" " * (80 - len(header)))
        f.write(struct.pack("<I", len(tris)))
        for i in range(len(tris)):
            nx, ny, nz = norms[i]
            v1, v2, v3 = tris[i,0], tris[i,1], tris[i,2]
            f.write(struct.pack("<12f", nx, ny, nz, *v1, *v2, *v3))
            f.write(struct.pack("<H", 0))

def create_box(cx, cy, cz, w, h, d):
    hw, hh, hd = w/2, h/2, d/2
    v = [np.array([cx+x, cy+y, cz+z]) for x in [-hw,hw] for y in [-hh,hh] for z in [-hd,hd]]
    return [
        np.array([v[0],v[1],v[3]],dtype=np.float32), np.array([v[0],v[3],v[2]],dtype=np.float32),
        np.array([v[4],v[6],v[5]],dtype=np.float32), np.array([v[4],v[7],v[6]],dtype=np.float32),
        np.array([v[0],v[1],v[5]],dtype=np.float32), np.array([v[0],v[5],v[4]],dtype=np.float32),
        np.array([v[1],v[3],v[7]],dtype=np.float32), np.array([v[1],v[7],v[5]],dtype=np.float32),
        np.array([v[3],v[2],v[6]],dtype=np.float32), np.array([v[3],v[6],v[7]],dtype=np.float32),
        np.array([v[2],v[0],v[4]],dtype=np.float32), np.array([v[2],v[4],v[6]],dtype=np.float32),
    ]

def create_cylinder(cx, cy, cz, r, h, seg=16):
    tris = []
    for i in range(seg):
        a1 = 2 * math.pi * i / seg
        a2 = 2 * math.pi * (i + 1) / seg
        x1, y1 = r * math.cos(a1), r * math.sin(a1)
        x2, y2 = r * math.cos(a2), r * math.sin(a2)
        
        v1 = np.array([cx+x1, cy+y1, cz])
        v2 = np.array([cx+x2, cy+y2, cz])
        v3 = np.array([cx+x2, cy+y2, cz+h])
        v4 = np.array([cx+x1, cy+y1, cz+h])
        
        tris.extend([
            np.array([v1,v2,v3],dtype=np.float32),
            np.array([v1,v3,v4],dtype=np.float32)
        ])
    return tris

print(f"Generating {{N_ARMS}}-armed gripper...")
tris = []

# Center hub
tris.extend(create_cylinder(0, 0, 0, CENTER_D/2, THICK))

# Arms
angle_step = 360.0 / N_ARMS
for i in range(N_ARMS):
    angle = math.radians(i * angle_step)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    
    arm_cx = CENTER_D/2 + ARM_L/2
    arm_tris = create_box(arm_cx, 0, THICK/2, ARM_L, ARM_W, THICK)
    
    for tri in arm_tris:
        rotated = []
        for v in tri:
            x, y, z = v[0], v[1], v[2]
            x2 = x * cos_a - y * sin_a
            y2 = x * sin_a + y * cos_a
            rotated.append(np.array([x2, y2, z]))
        tris.append(np.array(rotated, dtype=np.float32))

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
write_stl(str(output_dir / "generated_gripper.stl"), tris)
print(f"✅ STL: generated_gripper.stl ({{len(tris)}} triangles, {{N_ARMS}} arms)")
"""
        return code
    
    @staticmethod
    def generate_lattice(analysis: Dict[str, Any]) -> str:
        """Template pour lattice"""
        params = analysis.get('parameters', {})
        
        cell_type = params.get('cell_type', 'cubic')
        cell_size = params.get('cell_size', 10.0)
        strut_d = params.get('strut_diameter', 1.5)
        length = params.get('length', 100.0)
        width = params.get('width', 100.0)
        height = params.get('height', 100.0)
        
        code = f"""#!/usr/bin/env python3
import math, struct, numpy as np
from pathlib import Path

CELL_TYPE = "{cell_type}"
CELL_SIZE = {cell_size}
STRUT_D = {strut_d}
LEN, WID, HEI = {length}, {width}, {height}

def compute_normals(tris):
    v1, v2 = tris[:,1] - tris[:,0], tris[:,2] - tris[:,0]
    n = np.cross(v1, v2)
    lens = np.linalg.norm(n, axis=1)
    lens[lens == 0] = 1.0
    return (n.T / lens).T.astype(np.float32)

def write_stl(path, tris):
    tris = np.asarray(tris, dtype=np.float32)
    norms = compute_normals(tris)
    with open(path, "wb") as f:
        header = f"Lattice {{CELL_TYPE.upper()}}".encode('ascii')
        f.write(header + b" " * (80 - len(header)))
        f.write(struct.pack("<I", len(tris)))
        for i in range(len(tris)):
            nx, ny, nz = norms[i]
            v1, v2, v3 = tris[i,0], tris[i,1], tris[i,2]
            f.write(struct.pack("<12f", nx, ny, nz, *v1, *v2, *v3))
            f.write(struct.pack("<H", 0))

def make_cyl(p1, p2, r, seg=8):
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    l = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    if l < 0.001: return []
    
    tris = []
    for i in range(seg):
        a1 = 2 * math.pi * i / seg
        a2 = 2 * math.pi * (i + 1) / seg
        
        rx1, ry1 = r * math.cos(a1), r * math.sin(a1)
        rx2, ry2 = r * math.cos(a2), r * math.sin(a2)
        
        v1 = np.array([x1+rx1, y1+ry1, z1])
        v2 = np.array([x1+rx2, y1+ry2, z1])
        v3 = np.array([x2+rx2, y2+ry2, z2])
        v4 = np.array([x2+rx1, y2+ry1, z2])
        
        tris.extend([
            np.array([v1,v2,v3],dtype=np.float32),
            np.array([v1,v3,v4],dtype=np.float32)
        ])
    return tris

def cubic_cell(cx, cy, cz, s, r):
    h = s / 2
    nodes = [
        (cx-h,cy-h,cz-h), (cx+h,cy-h,cz-h), (cx+h,cy+h,cz-h), (cx-h,cy+h,cz-h),
        (cx-h,cy-h,cz+h), (cx+h,cy-h,cz+h), (cx+h,cy+h,cz+h), (cx-h,cy+h,cz+h)
    ]
    edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    tris = []
    for i, j in edges:
        tris.extend(make_cyl(nodes[i], nodes[j], r))
    return tris

print(f"Generating {{CELL_TYPE.upper()}} lattice...")

nx, ny, nz = int(LEN/CELL_SIZE), int(WID/CELL_SIZE), int(HEI/CELL_SIZE)
tris = []
r = STRUT_D / 2

for i in range(nx):
    for j in range(ny):
        for k in range(nz):
            cx = (i + 0.5) * CELL_SIZE
            cy = (j + 0.5) * CELL_SIZE
            cz = (k + 0.5) * CELL_SIZE
            tris.extend(cubic_cell(cx, cy, cz, CELL_SIZE, r))

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
write_stl(str(output_dir / "generated_lattice.stl"), tris)
print(f"✅ STL: generated_lattice.stl ({{len(tris)}} triangles, {{nx}}x{{ny}}x{{nz}} cells)")
"""
        return code


    @staticmethod
    def generate_facade_pyramid(analysis: Dict[str, Any]) -> str:
        """Template facade pyramid - VOTRE CODE ORIGINAL"""
        params = analysis.get('parameters', {})
        
        hex_radius = params.get('hex_radius', 60.0)
        w_frame = params.get('w_frame', 8.0)
        h_frame = params.get('h_frame', 10.0)
        tri_height = params.get('tri_height', 55.0)
        tri_thickness = params.get('tri_thickness', 2.4)
        w_bar = params.get('w_bar', 8.0)
        
        code = f"""#!/usr/bin/env python3
import math
import struct
import numpy as np
from pathlib import Path

HEX_RADIUS = {hex_radius}
W_FRAME = {w_frame}
H_FRAME = {h_frame}
TRI_HEIGHT = {tri_height}
TRI_THICKNESS = {tri_thickness}
W_BAR = {w_bar}
H_BAR = 10.0

def compute_normals(tris):
    v1 = tris[:,1] - tris[:,0]
    v2 = tris[:,2] - tris[:,0]
    n = np.cross(v1, v2)
    lens = np.linalg.norm(n, axis=1)
    lens[lens == 0] = 1.0
    n = (n.T / lens).T
    return n.astype(np.float32)

def write_binary_stl(path, tris):
    tris = np.asarray(tris, dtype=np.float32)
    norms = compute_normals(tris)
    with open(path, "wb") as f:
        header = b"Generated Facade"
        f.write(header + b" " * (80 - len(header)))
        f.write(struct.pack("<I", tris.shape[0]))
        for i in range(tris.shape[0]):
            nx, ny, nz = norms[i].tolist()
            v1, v2, v3 = tris[i,0].tolist(), tris[i,1].tolist(), tris[i,2].tolist()
            f.write(struct.pack("<12f", nx, ny, nz, *v1, *v2, *v3))
            f.write(struct.pack("<H", 0))

def hexagon_points(radius):
    return [(radius * math.cos(i * math.pi / 3), 
             radius * math.sin(i * math.pi / 3)) 
            for i in range(6)]

def extrude_polygon(points, height):
    tris = []
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        p1 = np.array([points[i][0], points[i][1], 0])
        p2 = np.array([points[j][0], points[j][1], 0])
        p3 = np.array([points[j][0], points[j][1], height])
        p4 = np.array([points[i][0], points[i][1], height])
        tris.extend([
            np.array([p1,p2,p3],dtype=np.float32),
            np.array([p1,p3,p4],dtype=np.float32)
        ])
    return tris

def make_frame():
    tris = []
    outer_pts = hexagon_points(HEX_RADIUS)
    inner_pts = hexagon_points(HEX_RADIUS - W_FRAME)
    tris.extend(extrude_polygon(outer_pts, H_FRAME))
    tris.extend(extrude_polygon(inner_pts, H_FRAME))
    return tris

def make_triangle(base_width):
    B, H, t = base_width, TRI_HEIGHT, TRI_THICKNESS
    poly = [(-B/2,0,0), (B/2,0,0), (0,0,H)]
    v1 = np.array(poly[0])
    v2 = np.array(poly[1])
    v3 = np.array(poly[2])
    
    v4 = v1 + np.array([0,t,0])
    v5 = v2 + np.array([0,t,0])
    v6 = v3 + np.array([0,t,0])
    
    return [
        np.array([v1,v2,v3],dtype=np.float32),
        np.array([v4,v6,v5],dtype=np.float32),
        np.array([v1,v2,v5],dtype=np.float32), np.array([v1,v5,v4],dtype=np.float32),
        np.array([v2,v3,v6],dtype=np.float32), np.array([v2,v6,v5],dtype=np.float32),
        np.array([v3,v1,v4],dtype=np.float32), np.array([v3,v4,v6],dtype=np.float32),
    ]

def rotate_translate_tris(tris, angle, tx, ty, tz):
    cos_a, sin_a = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    result = []
    for tri in tris:
        rotated = []
        for v in tri:
            x, y, z = v[0], v[1], v[2]
            x2 = x * cos_a - y * sin_a
            y2 = x * sin_a + y * cos_a
            rotated.append(np.array([x2+tx, y2+ty, z+tz]))
        result.append(np.array(rotated, dtype=np.float32))
    return result

print("Generating facade...")
tris = make_frame()

Ri = HEX_RADIUS - W_FRAME
base_width = 2 * Ri * math.sin(math.pi / 6)
tri_template = make_triangle(base_width)

for i in range(6):
    angle = i * 60.0 + 30.0
    x = (Ri - TRI_THICKNESS/2) * math.cos(math.radians(angle))
    y = (Ri - TRI_THICKNESS/2) * math.sin(math.radians(angle))
    rotated = rotate_translate_tris(tri_template, angle - 90, x, y, H_FRAME)
    tris.extend(rotated)

for i in range(6):
    angle = i * 60.0
    bar_len = Ri
    x1, y1 = 0, 0
    x2 = bar_len * math.cos(math.radians(angle))
    y2 = bar_len * math.sin(math.radians(angle))
    
    hw = W_BAR / 2
    corners = [
        (x1-hw, y1-hw, 0), (x2-hw, y2-hw, 0),
        (x2+hw, y2+hw, 0), (x1+hw, y1+hw, 0),
        (x1-hw, y1-hw, H_BAR), (x2-hw, y2-hw, H_BAR),
        (x2+hw, y2+hw, H_BAR), (x1+hw, y1+hw, H_BAR)
    ]
    v = [np.array([c[0],c[1],c[2]]) for c in corners]
    tris.extend([
        np.array([v[0],v[1],v[2]],dtype=np.float32), np.array([v[0],v[2],v[3]],dtype=np.float32),
        np.array([v[4],v[6],v[5]],dtype=np.float32), np.array([v[4],v[7],v[6]],dtype=np.float32),
    ])

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
stl_path = output_dir / "generated_facade.stl"
tris_array = np.array(tris, dtype=np.float32)
write_binary_stl(str(stl_path), tris_array)

print(f"✅ STL: {{stl_path}} ({{len(tris):,}} triangles)")
"""
        return code


    @staticmethod
    def generate_facade_parametric(analysis: Dict[str, Any]) -> str:
        """Template pour facade parametrique"""
        params = analysis.get('parameters', {})
        
        pattern_type = params.get('pattern_type', 'wavy')
        width = params.get('width', 20000.0)
        height = params.get('height', 10000.0)
        depth = params.get('depth', 500.0)
        element_size = params.get('element_size', 200.0)
        
        code = f"""#!/usr/bin/env python3
import math, struct, numpy as np
from pathlib import Path

PATTERN = "{pattern_type}"
WIDTH = {width}
HEIGHT = {height}
DEPTH = {depth}
ELEM_SIZE = {element_size}

def compute_normals(tris):
    v1, v2 = tris[:,1] - tris[:,0], tris[:,2] - tris[:,0]
    n = np.cross(v1, v2)
    lens = np.linalg.norm(n, axis=1)
    lens[lens == 0] = 1.0
    return (n.T / lens).T.astype(np.float32)

def write_stl(path, tris):
    tris = np.asarray(tris, dtype=np.float32)
    norms = compute_normals(tris)
    with open(path, "wb") as f:
        header = f"Facade {{PATTERN.upper()}}".encode('ascii')
        f.write(header + b" " * (80 - len(header)))
        f.write(struct.pack("<I", len(tris)))
        for i in range(len(tris)):
            nx, ny, nz = norms[i]
            v1, v2, v3 = tris[i,0], tris[i,1], tris[i,2]
            f.write(struct.pack("<12f", nx, ny, nz, *v1, *v2, *v3))
            f.write(struct.pack("<H", 0))

def wavy_panel(x, y, w, h):
    tris = []
    seg = 10
    
    for i in range(seg):
        for j in range(seg):
            x0 = x + j * w / seg
            y0 = y + i * h / seg
            x1 = x + (j + 1) * w / seg
            y1 = y + (i + 1) * h / seg
            
            z00 = DEPTH * math.sin(3 * math.pi * j / seg)
            z10 = DEPTH * math.sin(3 * math.pi * (j + 1) / seg)
            z01 = DEPTH * math.sin(3 * math.pi * j / seg)
            z11 = DEPTH * math.sin(3 * math.pi * (j + 1) / seg)
            
            v1 = np.array([x0, y0, z00])
            v2 = np.array([x1, y0, z10])
            v3 = np.array([x1, y1, z11])
            v4 = np.array([x0, y1, z01])
            
            tris.extend([
                np.array([v1, v2, v3], dtype=np.float32),
                np.array([v1, v3, v4], dtype=np.float32)
            ])
    
    return tris

print(f"Generating {{PATTERN.upper()}} facade...")

nx = max(1, int(WIDTH / ELEM_SIZE))
ny = max(1, int(HEIGHT / ELEM_SIZE))

tris = []
for i in range(ny):
    for j in range(nx):
        x = j * ELEM_SIZE
        y = i * ELEM_SIZE
        tris.extend(wavy_panel(x, y, ELEM_SIZE, ELEM_SIZE))

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
write_stl(str(output_dir / "generated_facade.stl"), tris)
print(f"✅ STL: generated_facade.stl ({{len(tris)}} triangles)")
"""
        return code

    @staticmethod
    def generate_heatsink(analysis: Dict[str, Any]) -> str:
        """Template heatsink - Utilise CadQuery directement"""
        params = analysis.get('parameters', {})
        
        plate_w = params.get('plate_w', 40.0)
        plate_h = params.get('plate_h', 40.0)
        plate_t = params.get('plate_t', 3.0)
        tube_od = params.get('tube_od', 42.0)
        tube_len = params.get('tube_len', 10.0)
        bar_len = params.get('bar_len', 22.0)
        bar_angle = params.get('bar_angle', 20.0)
        hole_d = params.get('hole_d', 3.3)
        hole_pitch = params.get('hole_pitch', 32.0)
        
        # COPIEZ DIRECTEMENT VOTRE CODE CADQUERY ICI
        code = f"""#!/usr/bin/env python3
import cadquery as cq
from pathlib import Path

CFG = dict(
    plate_w={plate_w}, plate_h={plate_h}, plate_t={plate_t}, corner_r=2.0,
    center_d=34.0, hole_pitch={hole_pitch}, hole_d={hole_d},
    tube_od={tube_od}, tube_len={tube_len},
    bar_len={bar_len}, bar_angle_in={bar_angle},
    taper_start=None, bar_tip_t_ratio=0.15, bar_tip_t_min=0.2,
    overlap=0.4, clip_extra=4.0, edge_inset=0.0,
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

    Tb = 0.5*(Do - D0)

    # 1) Plaque
    plate = cq.Workplane("YZ").rect(W,H).extrude(T)
    if R>0: plate = plate.edges("|X").fillet(R)
    plate = plate.cut(cq.Workplane("YZ").circle(D0/2).extrude(T))
    pts = [(+P/2,+P/2),(+P/2,-P/2),(-P/2,+P/2),(-P/2,-P/2)]
    plate = plate.faces(">X").workplane().pushPoints(pts).hole(Dh)

    # 2) TUYAU à côtés RECTANGULAIRES
    rect_w = W + 2.0
    tube_outer = (cq.Workplane("YZ")
                  .workplane(offset=T-ov)
                  .rect(rect_w, Do)
                  .extrude(Lt+ov))
    tube_inner = (cq.Workplane("YZ")
                  .workplane(offset=T-ov)
                  .circle(D0/2)
                  .extrude(Lt+ov))
    tube = tube_outer.cut(tube_inner)

    # 3) Deux barres symétriques
    L_const_default = Lt if taper_start is None else taper_start
    barR, yR, x0R = _make_taper_bar(W,H,T,Tb,Lb,Ang,ov,inset,L_const_default,tip_ratio,tip_min, +1)
    barL, yL, x0L = _make_taper_bar(W,H,T,Tb,Lb,Ang,ov,inset,L_const_default,tip_ratio,tip_min, -1)

    # 4) Rogner le TUYAU
    Wcut, Hcut = 2*W, H+20
    Lcut = max(Lt,Lb)+ov+2
    cutR = (cq.Workplane("YZ").workplane(offset=x0R)
            .center(yR + Tb/2 + Wcut/2,0).rect(Wcut,Hcut).extrude(Lcut)
            .rotate((x0R,yR,0),(x0R,yR,1), -abs(Ang)))
    cutL = (cq.Workplane("YZ").workplane(offset=x0L)
            .center(yL - Tb/2 - Wcut/2,0).rect(Wcut,Hcut).extrude(Lcut)
            .rotate((x0L,yL,0),(x0L,yL,1), +abs(Ang)))
    tube = tube.cut(cutR).cut(cutL)

    # 5) Clip
    clip_len = max(Lt,Lb)+ov+clip_extra
    clip = cq.Workplane("YZ").workplane(offset=T-ov).rect(W,H).extrude(clip_len)
    if R>0: clip = clip.edges("|X").fillet(R)
    tube = tube.intersect(clip)
    barR = barR.intersect(clip)
    barL = barL.intersect(clip)

    asm = plate.union(tube).union(barR).union(barL)

    # 6) Morsures
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

print("Generating heatsink with CadQuery...")
model = build()
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
cq.exporters.export(model.val(), str(output_dir / "generated_heatsink.stl"))
print("✅ STL: generated_heatsink.stl")
"""
        return code

    @staticmethod
    def generate_louvre_wall(analysis: Dict[str, Any]) -> str:
        params = analysis.get('parameters', {})
        
        width = params.get('width', 280.0)
        height = params.get('height', 260.0)
        thickness = params.get('thickness', 40.0)
        corner_fillet = params.get('corner_fillet', 3.0)
        angle_deg = params.get('angle_deg', 35.0)
        pitch = params.get('pitch', 12.0)
        slat_width = params.get('slat_width', 8.0)
        slat_depth = params.get('slat_depth', 12.0)
        end_radius = params.get('end_radius', 3.0)
        layer1_z = params.get('layer1_z', 6.0)
        layer2_enabled = params.get('layer2_enabled', True)
        layer2_angle = params.get('layer2_angle', 55.0)
        layer2_z_offset = params.get('layer2_z_offset', 0.0)
        boolean_mode = params.get('boolean_mode', 'union')
        same_layer = params.get('same_layer', False)
        full_depth = params.get('full_depth', False)
        
        return f"""#!/usr/bin/env python3
import math
import cadquery as cq
from pathlib import Path

CFG = dict(
    width={width},
    height={height},
    thickness={thickness},
    corner_fillet={corner_fillet},
    angle_deg={angle_deg},
    pitch={pitch},
    slat_width={slat_width},
    slat_depth={slat_depth},
    end_radius={end_radius},
    layer1_z={layer1_z},
    layer2=dict(
        enabled={layer2_enabled},
        angle_deg={layer2_angle},
        z_offset={layer2_z_offset}
    ),
    boolean="{boolean_mode}",
    same_layer={same_layer},
    full_depth={full_depth},
)

def _triangle_prism(W, H, T, rf=0.0):
    tri = cq.Workplane("XY").polyline([(0, 0), (0, H), (W, 0)]).close().extrude(T)
    if rf and rf > 0:
        tri = tri.edges("|Z").fillet(rf)
    return tri

def _make_louver_field(W, H, T, angle_deg, pitch, slat_w, slat_d, end_r, z0):
    theta = math.radians(angle_deg)
    diag = math.hypot(W, H)
    L = diag * 2.1
    
    # DÉCALAGE VERS LE CENTRE DU TRIANGLE
    cx = W / 3.0  # Centre du triangle
    cy = H / 3.0
    
    nx = math.cos(theta + math.pi/2.0)
    ny = math.sin(theta + math.pi/2.0)
    
    span = W + H
    n_slats = int(math.ceil(span / pitch)) + 4
    
    if end_r > 0:
        slot_w = min(2.0*end_r, slat_w)
        core_len = max(L, slot_w + 1.0)
        prof2d = cq.Workplane("XY").slot2D(core_len, slot_w)
    else:
        prof2d = cq.Workplane("XY").rect(L, slat_w)
    
    base3d = (prof2d.extrude(slat_d)
              .rotate((0, 0, 0), (0, 0, 1), math.degrees(theta))
              .translate((cx, cy, z0)))  # DÉCALAGE ICI
    
    field = None
    start = -(n_slats // 2)
    for i in range(start, start + n_slats):
        d = i * pitch
        slat = base3d.translate((d*nx, d*ny, 0))
        field = slat if field is None else field.union(slat)
    return field

def build(cfg=CFG):
    W, H, T = cfg["width"], cfg["height"], cfg["thickness"]
    rf = cfg["corner_fillet"]
    ang, pitch = cfg["angle_deg"], cfg["pitch"]
    sw, sd, er = cfg["slat_width"], cfg["slat_depth"], cfg["end_radius"]
    z1 = cfg["layer1_z"]
    
    tri = _triangle_prism(W, H, T, rf)
    
    if cfg["full_depth"]:
        sd1 = sd2 = T
        z1u = 0.0
        z2u = 0.0
    else:
        sd1 = sd
        z1u = z1
        if cfg["layer2"]["enabled"]:
            z2 = cfg["layer2"]["z_offset"]
            z2u = z1u if cfg["same_layer"] else z2
            sd2 = sd
    
    f1 = _make_louver_field(W, H, T, ang, pitch, sw, sd1, er, z1u)
    
    if cfg["layer2"]["enabled"]:
        ang2 = cfg["layer2"]["angle_deg"]
        f2 = _make_louver_field(W, H, T, ang2, pitch, sw, sd2, er, z2u)
        model = f1.union(f2).intersect(tri) if cfg["boolean"] == "union" else f1.intersect(f2).intersect(tri)
    else:
        model = f1.intersect(tri)
    
    return model

model = build(CFG)
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
cq.exporters.export(model.val(), str(output_dir / "generated_facade.stl"))
print("✅ generated_facade.stl")
"""

    @staticmethod
    def generate_honeycomb(analysis: Dict[str, Any]) -> str:
        """Template pour honeycomb panel (panneau alvéolaire hexagonal CadQuery)"""
        params = analysis.get('parameters', {})
        
        W = params.get('panel_width', 300.0)
        H = params.get('panel_height', 380.0)
        T = params.get('panel_thickness', 40.0)
        cell_size = params.get('cell_size', 12.0)
        wall = params.get('wall_thickness', 2.2)
        depth = params.get('cell_depth', 40.0)
        corner_fillet = params.get('corner_fillet', 0.0)
        full_depth = params.get('full_depth', False)
        
        code = f"""#!/usr/bin/env python3
import cadquery as cq
import math
from pathlib import Path

W = {W}
H = {H}
T = {T}
CELL_SIZE = {cell_size}
WALL = {wall}
DEPTH = {depth}
CORNER_FILLET = {corner_fillet}
FULL_DEPTH = {full_depth}

def hex_vertices_flat_top(a):
    r = a
    s = (math.sqrt(3)/2.0) * a
    return [
        (r, 0.0),
        (r/2.0, s),
        (-r/2.0, s),
        (-r, 0.0),
        (-r/2.0, -s),
        (r/2.0, -s),
    ]

def make_hex_face(a, wall):
    verts = hex_vertices_flat_top(a)
    outer = cq.Workplane("XY").polyline(verts).close()
    inner = outer.offset2D(-wall)
    face = (outer
            .toPending()
            .consolidateWires()
            .add(inner.wires())
            .toPending()
            .consolidateWires())
    return face

def honeycomb_field(w, h, t, a, wall, depth, z0=0.0):
    dx = 1.5 * a
    dy = math.sqrt(3.0) * a
    
    half_w = a
    half_h = dy/2.0
    
    cell2d = make_hex_face(a, wall)
    cell3d = cell2d.extrude(depth).translate((0, 0, z0))
    
    nx = int(math.ceil((w + 2*half_w) / dx)) + 2
    ny = int(math.ceil((h + 2*half_h) / dy)) + 2
    
    solids = None
    x0 = 0.0
    y0 = 0.0
    
    for i in range(nx):
        cx = x0 + i*dx
        col_off = (dy/2.0) if (i % 2) else 0.0
        for j in range(ny):
            cy = y0 + j*dy + col_off
            
            if not ((x0 + half_w) <= cx <= (w - half_w) and
                    (y0 + half_h) <= cy <= (h - half_h)):
                continue
            
            c = cell3d.translate((cx, cy, 0.0))
            solids = c if solids is None else solids.union(c)
    
    return solids if solids is not None else cq.Workplane("XY")

print("Generating honeycomb panel...")

depth_final = T if FULL_DEPTH else DEPTH
z0 = 0.0

panel = cq.Workplane("XY").rect(W, H, centered=False).extrude(T)
if CORNER_FILLET > 0:
    panel = panel.edges("|Z").fillet(CORNER_FILLET)

honey = honeycomb_field(W, H, T, CELL_SIZE, WALL, depth_final, z0)

model = honey.intersect(panel)

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
cq.exporters.export(model.val(), str(output_dir / "generated_facade.stl"))
print("✅ STL: generated_facade.stl (Honeycomb Panel)")
"""
        return code

    @staticmethod
    def generate_sine_wave_fins(analysis: Dict[str, Any]) -> str:
        """Template pour sine wave fins (façade ondulée)"""
        params = analysis.get('parameters', {})
        
        panel_length = params.get('panel_length', 420.0)
        panel_height = params.get('panel_height', 180.0)
        depth = params.get('depth', 140.0)
        n_fins = params.get('n_fins', 34)
        fin_thickness = params.get('fin_thickness', 3.0)
        amplitude = params.get('amplitude', 40.0)
        period_ratio = params.get('period_ratio', 0.9)
        base_thickness = params.get('base_thickness', 6.0)
        
        code = f"""#!/usr/bin/env python3
import cadquery as cq
import math
from pathlib import Path

L = {panel_length}
H = {panel_height}
DEPTH = {depth}
N_FINS = {n_fins}
FIN_T = {fin_thickness}
AMP = {amplitude}
PERIOD_RATIO = {period_ratio}
BASE_THICK = {base_thickness}

print("Generating sine wave fins...")

base = cq.Workplane("XY").rect(L, H).extrude(BASE_THICK)

freq = 2.0 * math.pi / (L * PERIOD_RATIO)

ribs = cq.Workplane("XY")
x0 = -L/2
for i in range(N_FINS):
    x = x0 + i*(L/(N_FINS-1))
    off0 = AMP * math.sin(freq*(x + 0.00*L))
    off1 = AMP * math.sin(freq*(x + 0.25*L))
    fin = (cq.Workplane("XY")
           .center(x, off0).rect(FIN_T, H)
           .workplane(offset=DEPTH).center(0, off1-off0).rect(FIN_T, H)
           .loft(ruled=True, combine=True))
    ribs = ribs.union(fin)

clip = cq.Workplane("XY").rect(L, H).extrude(DEPTH + BASE_THICK + 6.0)
model = base.union(ribs.intersect(clip))

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
cq.exporters.export(model.val(), str(output_dir / "generated_facade.stl"))
print("✅ STL: generated_facade.stl")
"""
        return code