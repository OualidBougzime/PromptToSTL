import re, math, os, logging
import builtins as py_builtins
from typing import Dict, Any, List, Optional
from templates import CodeTemplates

log = logging.getLogger("cadamx.agents")


class AnalystAgent:
    """Détecte le type d'application et extrait les paramètres"""
    
    APPLICATION_KEYWORDS = {
        'splint': ['splint', 'orthosis', 'orthèse', 'brace', 'hand', 'wrist', 'forearm', 'finger'],
        'stent': ['stent', 'vascular', 'serpentine', 'expandable'],  # 🔥 Restreint - pas de 'ring', 'strut', 'helical'
        'facade_pyramid': ['pyramid facade', 'hexagonal pyramid', 'triangle pyramid', 'pyramidal'],  # 🔥 Retiré 'hub' générique
        'honeycomb': ['honeycomb panel', 'alveolar', 'hexagonal cells', 'hex panel', 'cellular panel'],  # 🔥 Plus spécifique
        'louvre_wall': ['louvre', 'louver', 'slat', 'diagonal', 'pavilion', 'lattice wall'],
        'sine_wave_fins': ['sine', 'wave', 'fins', 'undulating', 'ribbed', 'zahner'],
        'lattice': ['lattice', 'truss', 'cellular', 'gyroid', 'diamond', 'cubic', 'octet', 'kelvin'],
        'gripper': ['gripper', 'surgical gripper', 'medical gripper'],  # 🔥 Très restreint - pas de 'arm', 'clamp', 'holder' génériques
        'heatsink': ['heatsink', 'heat sink', 'cooling fins', 'thermal dissipator', 'radiator']  # 🔥 Plus spécifique
    }
    
    async def analyze(self, prompt: str) -> Dict[str, Any]:
        """Analyse et détecte le type d'application + paramètres"""
        p = prompt.lower()

        app_type = self._detect_application_type(p)
        log.info(f"✅ Detected application type: {app_type.upper()}")

        if app_type == 'splint':
            return self._analyze_splint(prompt)
        elif app_type == 'stent':
            return self._analyze_stent(prompt)
        elif app_type == 'facade_pyramid':
            return self._analyze_facade_pyramid(prompt)
        elif app_type == 'honeycomb':
            return self._analyze_honeycomb(prompt)
        elif app_type == 'louvre_wall':
            return self._analyze_louvre_wall(prompt)
        elif app_type == 'sine_wave_fins':
            return self._analyze_sine_wave_fins(prompt)
        elif app_type == 'lattice':
            return self._analyze_lattice(prompt)
        elif app_type == 'gripper':
            return self._analyze_gripper(prompt)
        elif app_type == 'heatsink':
            return self._analyze_heatsink(prompt)
        elif app_type == 'unknown':
            # Type inconnu → va utiliser Chain-of-Thought
            return {
                "type": "unknown",
                "parameters": {},
                "raw_prompt": prompt
            }
        else:
            # Fallback (ne devrait jamais arriver)
            return self._analyze_splint(prompt)

    def _analyze_honeycomb(self, prompt: str) -> Dict[str, Any]:
        """Analyse pour honeycomb panel (panneau alvéolaire hexagonal)"""
        params = {
            # Panneau
            'panel_width': self._find_number(prompt, r'(?:panel\s+)?width\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 300.0),
            'panel_height': self._find_number(prompt, r'(?:panel\s+)?height\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 380.0),
            'panel_thickness': self._find_number(prompt, r'(?:panel\s+)?thickness\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 40.0),
            
            # Cellules hexagonales
            'cell_size': self._find_number(prompt, r'cell\s+size\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 12.0),
            'wall_thickness': self._find_number(prompt, r'wall\s+thickness\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 2.2),
            'cell_depth': self._find_number(prompt, r'cell\s+depth\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 40.0),
            
            # Options
            'corner_fillet': self._find_number(prompt, r'corner\s+fillet\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 0.0),
            'full_depth': 'full depth' in prompt.lower() or 'through' in prompt.lower(),
        }
        
        log.info(f"✅ HONEYCOMB: {params['panel_width']}×{params['panel_height']}mm, cell={params['cell_size']}mm")
        
        return {
            "type": "honeycomb",
            "parameters": params,
            "raw_prompt": prompt
        }
    
    def _detect_application_type(self, prompt: str) -> str:
        """Détecte le type d'application basé sur les mots-clés avec détection plus stricte"""
        scores = {app: 0 for app in self.APPLICATION_KEYWORDS}

        for app_type, keywords in self.APPLICATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in prompt:
                    scores[app_type] += 1

        # Règles strictes de détection (par ordre de priorité)

        # 1. HEATSINK - Très spécifique
        if 'heatsink' in prompt or 'heat sink' in prompt:
            return 'heatsink'

        # 2. LOUVRE WALL - AVANT GRIPPER !
        if 'louvre' in prompt or 'louver' in prompt or 'pavilion' in prompt:
            return 'louvre_wall'
        
        # 3. GRIPPER - Requiert le mot exact "gripper"
        if 'gripper' in prompt:
            return 'gripper'

        # 4. STENT - Requiert au moins 2 mots-clés spécifiques
        if 'stent' in prompt and ('serpentine' in prompt or 'vascular' in prompt or 'expandable' in prompt):
            return 'stent'

        # 5. HONEYCOMB PANEL - Requiert "honeycomb" + contexte
        if ('honeycomb panel' in prompt or 'alveolar' in prompt or
            'hexagonal cells' in prompt or 'cellular panel' in prompt or
            ('honeycomb' in prompt and ('panel' in prompt or 'cell' in prompt))):
            return 'honeycomb'

        # 6. PYRAMID FACADE - Requiert "pyramid" explicite
        if 'pyramid facade' in prompt or 'hexagonal pyramid' in prompt or 'pyramidal' in prompt:
            return 'facade_pyramid'

        # 7. SINE WAVE FINS - Requiert combinaison "sine" ou "wave" + "fins"
        if (('sine' in prompt or 'wave' in prompt) and 'fin' in prompt) or 'zahner' in prompt:
            return 'sine_wave_fins'

        # 8. LATTICE - Requiert mots-clés spécifiques de structures lattice
        lattice_words = ['lattice', 'cubic cell', 'diamond cell', 'gyroid', 'octet', 'kelvin', 'bcc', 'fcc']
        if any(word in prompt for word in lattice_words):
            return 'lattice'

        # 9. Score-based detection with higher threshold
        detected = max(scores, key=scores.get)

        # Requiert au moins 2 matches pour considérer un template valide
        if scores[detected] < 2:
            log.info("🧠 No strong template match (score < 2) → routing to Chain-of-Thought")
            return 'unknown'

        log.info(f"✅ Template detected via scoring: {detected} (score: {scores[detected]})")
        return detected

    def _analyze_heatsink(self, prompt: str) -> Dict[str, Any]:
        """Analyse pour heatsink (dissipateur thermique)"""
        params = {
            # Plaque
            'plate_w': self._find_number(prompt, r'plate.*?width\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 40.0),
            'plate_h': self._find_number(prompt, r'plate.*?height\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 40.0),
            'plate_t': self._find_number(prompt, r'plate.*?thickness\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 3.0),
            
            # Tuyau/tube
            'tube_od': self._find_number(prompt, r'tube.*?(?:outer\s+)?diameter\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 42.0),
            'tube_len': self._find_number(prompt, r'tube.*?length\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 10.0),
            
            # Barres/ailettes
            'bar_len': self._find_number(prompt, r'(?:bar|fin).*?length\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 22.0),
            'bar_angle': self._find_number(prompt, r'(?:bar|fin).*?angle\s*:?\s*(\d+(?:\.\d+)?)\s*(?:deg|°)', 20.0),
            
            # Trous
            'hole_d': self._find_number(prompt, r'hole.*?diameter\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 3.3),
            'hole_pitch': self._find_number(prompt, r'hole.*?pitch\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 32.0),
        }
        
        log.info(f"✅ HEATSINK: plate {params['plate_w']}×{params['plate_h']}mm, bars {params['bar_len']}mm @ {params['bar_angle']}°")
        
        return {
            "type": "heatsink",
            "parameters": params,
            "raw_prompt": prompt
        }

    def _analyze_louvre_wall(self, prompt: str) -> Dict[str, Any]:
        """Analyse pour louvre wall (pavilion avec lattes diagonales)"""
        params = {
            # Triangle
            'width': self._find_number(prompt, r'width\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 280.0),
            'height': self._find_number(prompt, r'height\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 260.0),
            'thickness': self._find_number(prompt, r'thickness\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 40.0),
            'corner_fillet': self._find_number(prompt, r'(?:corner|fillet)\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 3.0),
            
            # Louvres (nappe 1)
            'angle_deg': self._find_number(prompt, r'(?:angle|slat angle)\s*:?\s*(\d+(?:\.\d+)?)\s*(?:deg|°)', 35.0),
            'pitch': self._find_number(prompt, r'(?:pitch|spacing)\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 12.0),
            'slat_width': self._find_number(prompt, r'slat\s+width\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 8.0),
            'slat_depth': self._find_number(prompt, r'slat\s+depth\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 12.0),
            'end_radius': self._find_number(prompt, r'(?:end|edge)\s+radius\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 3.0),
            'layer1_z': self._find_number(prompt, r'layer\s+1\s+z\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 6.0),
            
            # Nappe 2 (optionnelle)
            'layer2_enabled': 'layer 2' in prompt.lower() or 'crossed' in prompt.lower() or 'double' in prompt.lower(),
            'layer2_angle': self._find_number(prompt, r'layer\s+2\s+angle\s*:?\s*(\d+(?:\.\d+)?)\s*(?:deg|°)', 55.0),
            'layer2_z_offset': self._find_number(prompt, r'layer\s+2\s+z\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 0.0),
            
            # Options
            'boolean_mode': 'intersect' if 'intersect' in prompt.lower() else 'union',
            'same_layer': 'same layer' in prompt.lower() or 'same z' in prompt.lower(),
            'full_depth': 'full depth' in prompt.lower() or 'through' in prompt.lower(),
        }
        
        log.info(f"✅ LOUVRE WALL: {params['width']}×{params['height']}mm, angle={params['angle_deg']}°")
        
        return {
            "type": "louvre_wall",
            "parameters": params,
            "raw_prompt": prompt
        }

    def _analyze_sine_wave_fins(self, prompt: str) -> Dict[str, Any]:
        """Analyse pour sine wave fins (façade ondulée avec ailettes)"""
        params = {
            # Panneau
            'panel_length': self._find_number(prompt, r'(?:panel\s+)?(?:length|width)\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 420.0),
            'panel_height': self._find_number(prompt, r'(?:panel\s+)?height\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 180.0),
            'depth': self._find_number(prompt, r'depth\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 140.0),
            
            # Ailettes
            'n_fins': int(self._find_number(prompt, r'(\d+)\s+(?:fins|ribs|blades)', 34)),
            'fin_thickness': self._find_number(prompt, r'fin\s+thickness\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 3.0),
            
            # Sinusoïde
            'amplitude': self._find_number(prompt, r'amplitude\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 40.0),
            'period_ratio': self._find_number(prompt, r'period\s+ratio\s*:?\s*(\d+(?:\.\d+)?)', 0.9),
            
            # Base
            'base_thickness': self._find_number(prompt, r'base\s+thickness\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 6.0),
        }
        
        log.info(f"✅ SINE WAVE FINS: {params['panel_length']}×{params['panel_height']}mm, {params['n_fins']} fins")
        
        return {
            "type": "sine_wave_fins",
            "parameters": params,
            "raw_prompt": prompt
        }
    
    def _analyze_facade_pyramid(self, prompt: str) -> Dict[str, Any]:
        """Analyse pour facade avec pyramides (ANCIENNE VERSION)"""
        p = prompt.lower()
        
        params = {
            'hex_radius': self._find_number(prompt, r'radius\s+(\d+(?:\.\d+)?)\s*mm', 60.0),
            'w_frame': self._find_number(prompt, r'frame.*?width\s+(\d+(?:\.\d+)?)\s*mm', 8.0),
            'h_frame': self._find_number(prompt, r'frame.*?height\s+(\d+(?:\.\d+)?)\s*mm', 10.0),
            'tri_height': self._find_number(prompt, r'triangle.*?height\s+(\d+(?:\.\d+)?)\s*mm', 55.0),
            'tri_thickness': self._find_number(prompt, r'(?:triangle|plate).*?thickness\s+(\d+(?:\.\d+)?)\s*mm', 2.4),
            'w_bar': self._find_number(prompt, r'bar.*?width\s+(\d+(?:\.\d+)?)\s*mm', 8.0),
        }
        
        log.info(f"✅ FACADE PYRAMID: hex radius={params['hex_radius']}mm, triangle height={params['tri_height']}mm")
        
        return {
            "type": "facade_pyramid",
            "parameters": params,
            "raw_prompt": prompt
        }
    
    def _analyze_lattice(self, prompt: str) -> Dict[str, Any]:
        """Analyse pour lattice structures"""
        p = prompt.lower()
        
        # Type de cellule
        cell_type = 'cubic'
        cell_types = ['cubic', 'diamond', 'gyroid', 'octet', 'kelvin', 'bcc', 'fcc']
        for ct in cell_types:
            if ct in p:
                cell_type = ct
                break
        
        params = {
            'cell_type': cell_type,
            'cell_size': self._find_number(prompt, r'cell\s+size\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 10.0),
            'strut_diameter': self._find_number(prompt, r'strut\s+(?:diameter|thickness)\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 1.5),
            'length': self._find_number(prompt, r'length\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 100.0),
            'width': self._find_number(prompt, r'width\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 100.0),
            'height': self._find_number(prompt, r'height\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 100.0),
        }
        
        log.info(f"✅ LATTICE: {cell_type.upper()}, cell={params['cell_size']}mm, strut={params['strut_diameter']}mm")
        
        return {
            "type": "lattice",
            "parameters": params,
            "raw_prompt": prompt
        }
    
    def _analyze_facade_parametric(self, prompt: str) -> Dict[str, Any]:
        """Analyse pour facade parametrique (NOUVELLE VERSION)"""
        p = prompt.lower()
        
        # Type de pattern
        pattern_type = 'wavy'
        patterns = ['wavy', 'hexagonal', 'triangular', 'fins', 'louvers', 'diamond', 'scales']
        for pt in patterns:
            if pt in p:
                pattern_type = pt
                break
        
        params = {
            'pattern_type': pattern_type,
            'width': self._find_number(prompt, r'width\s*:?\s*(\d+(?:\.\d+)?)\s*(?:m|mm)', 20000.0),
            'height': self._find_number(prompt, r'height\s*:?\s*(\d+(?:\.\d+)?)\s*(?:m|mm)', 10000.0),
            'depth': self._find_number(prompt, r'(?:depth|relief)\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 500.0),
            'element_size': self._find_number(prompt, r'element\s+size\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 200.0),
            'spacing': self._find_number(prompt, r'spacing\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 50.0),
            'amplitude': self._find_number(prompt, r'amplitude\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 300.0),
            'frequency': self._find_number(prompt, r'frequency\s*:?\s*(\d+(?:\.\d+)?)', 3.0),
        }
        
        log.info(f"✅ FACADE PARAMETRIC: {pattern_type.upper()}, {params['width']}×{params['height']}mm")
        
        return {
            "type": "facade_parametric",
            "parameters": params,
            "raw_prompt": prompt
        }
    
    def _analyze_splint(self, prompt: str) -> Dict[str, Any]:
        """Analyse pour splint/orthèse"""
        p = prompt.lower()
        sections = self._extract_sections(prompt)
        
        splint_type = self._extract_splint_type(p)
        curvatures = self._extract_curvatures(prompt)
        
        features = {
            'holes': self._extract_holes(p),
            'slots': self._extract_slots(p),
            'fillets': self._extract_fillets(p)
        }
        
        thickness = self._find_number(prompt, r'(?:wall\s+)?thickness\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 3.5)
        edge_radius = self._find_number(prompt, r'(?:edge|edges)\s*:?\s*(\d+(?:\.\d+)?)\s*mm\s+radius', 2.0)
        total_length_explicit = self._find_number(prompt, r'total\s+(?:assembled\s+)?length\s*:?\s*(\d+(?:\.\d+)?)\s*mm', None)
        
        log.info(f"✅ SPLINT ({splint_type}): {len(sections)} sections")
        
        return {
            "type": "splint",
            "splint_type": splint_type,
            "sections": sections,
            "features": features,
            "thickness": thickness,
            "edge_radius": edge_radius,
            "total_length_explicit": total_length_explicit,
            "curvatures": curvatures,
            "raw_prompt": prompt
        }
    
    def _extract_splint_type(self, text: str) -> str:
        match = re.search(r'\b(resting|dynamic|static|functional)\s+(?:hand\s+)?splint', text)
        return match.group(1) if match else 'resting'
    
    def _extract_curvatures(self, prompt: str) -> Dict[str, float]:
        curvatures = {}
        lines = prompt.split('\n')
        current_section = None
        
        for line in lines:
            line_lower = line.lower()
            
            if 'forearm' in line_lower:
                current_section = 'forearm'
            elif 'palm' in line_lower:
                current_section = 'palm'
            elif 'finger' in line_lower:
                current_section = 'finger'
            
            if current_section and 'curv' in line_lower:
                curve_match = re.search(r'(\d+(?:\.\d+)?)\s*mm', line)
                if curve_match:
                    curvatures[current_section] = float(curve_match.group(1))
        
        return curvatures
    
    def _extract_fillets(self, text: str) -> Optional[Dict[str, Any]]:
        has_smooth = 'smooth' in text or 'curved' in text or 'rounded' in text or 'fillet' in text
        
        if not has_smooth:
            return None
        
        radius_match = re.search(r'(?:smooth|filleted?)\s+(?:transitions?|edges?)\s*:?\s*(\d+(?:\.\d+)?)\s*mm', text, re.I)
        radius = float(radius_match.group(1)) if radius_match else 8.0
        
        return {
            'enabled': True,
            'radius': radius
        }
    
    def _extract_sections(self, prompt: str) -> List[Dict[str, Any]]:
        sections = []
        lines = prompt.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            
            if re.search(r'\bpalm\s+(?:platform|section|support)\b', line_lower):
                length = self._find_number(line, r'length\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 80.0)
                width_match = re.search(r'(?:constant\s+)?(\d+(?:\.\d+)?)\s*mm', line, re.I)
                width = float(width_match.group(1)) if width_match else 75.0
                
                sections.append({
                    'name': 'palm',
                    'length': length,
                    'width': width,
                    'width_start': width,
                    'width_end': width,
                    'angle': 20.0
                })
                continue
            
            if re.search(r'\bforearm\s+(?:support|section)\b', line_lower):
                length = self._find_number(line, r'length\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 150.0)
                
                taper_match = re.search(r'tapers?\s+from\s+(\d+(?:\.\d+)?)\s*mm.*?to\s+(\d+(?:\.\d+)?)\s*mm', line, re.I)
                if taper_match:
                    width_start = float(taper_match.group(1))
                    width_end = float(taper_match.group(2))
                else:
                    width_start = 70.0
                    width_end = 60.0
                
                sections.append({
                    'name': 'forearm',
                    'length': length,
                    'width_start': width_start,
                    'width_end': width_end,
                    'angle': 0.0
                })
                continue
            
            if re.search(r'\bfinger\s+(?:support|section)\b', line_lower):
                length = self._find_number(line, r'length\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 40.0)
                width_match = re.search(r'(\d+(?:\.\d+)?)\s*mm', line, re.I)
                width = float(width_match.group(1)) if width_match else 65.0
                
                sections.append({
                    'name': 'finger',
                    'length': length,
                    'width': width,
                    'width_start': width,
                    'width_end': width,
                    'angle': 0.0
                })
        
        if not sections:
            sections = [{'name': 'main', 'length': 270.0, 'width_start': 70.0, 'width_end': 60.0, 'angle': 0.0}]
        
        order = {'forearm': 0, 'palm': 1, 'finger': 2}
        sections.sort(key=lambda s: order.get(s['name'], 99))
        
        return sections
    
    def _extract_holes(self, text: str) -> Optional[Dict[str, Any]]:
        if 'hole' not in text and 'ventilation' not in text and 'perforation' not in text:
            return None
        
        diameter_match = re.search(r'(\d+(?:\.\d+)?)\s*mm\s+diameter', text, re.I)
        diameter = float(diameter_match.group(1)) if diameter_match else 6.0
        
        grid_match = re.search(r'(\d+)\s*[x×]\s*(\d+)', text, re.I)
        if grid_match:
            grid_x, grid_y = int(grid_match.group(1)), int(grid_match.group(2))
        else:
            grid_x, grid_y = 10, 3
        
        return {'diameter': diameter, 'grid_x': grid_x, 'grid_y': grid_y}
    
    def _extract_slots(self, text: str) -> Optional[Dict[str, Any]]:
        if 'slot' not in text and 'strap' not in text:
            return None
        
        width_match = re.search(r'(\d+(?:\.\d+)?)\s*mm\s+wide', text, re.I)
        width = float(width_match.group(1)) if width_match else 25.0
        
        depth_match = re.search(r'(\d+(?:\.\d+)?)\s*mm\s+deep', text, re.I)
        depth = float(depth_match.group(1)) if depth_match else 3.0
        
        positions = []
        pos_matches = re.findall(r'(\d+(?:\.\d+)?)\s*mm', text)
        if len(pos_matches) >= 3:
            positions = [float(p) for p in pos_matches[-3:]]
        else:
            positions = [50.0, 150.0, 220.0]
        
        return {'width': width, 'depth': depth, 'length': 20.0, 'positions': positions}
    
    def _find_number(self, text: str, pattern: str, default: float) -> float:
        match = re.search(pattern, text, re.I)
        return float(match.group(1)) if match else default
    
    def _analyze_stent(self, prompt: str) -> Dict[str, Any]:
        p = prompt.lower()
        
        params = {
            'outer_radius': self._find_number(prompt, r'radius\s+(\d+(?:\.\d+)?)\s*mm', 8.0),
            'length': self._find_number(prompt, r'length\s+(\d+(?:\.\d+)?)\s*mm', 40.0),
            'n_peaks': int(self._find_number(prompt, r'(\d+)\s+peaks?', 8)),
            'n_rings': int(self._find_number(prompt, r'(\d+)\s+rings?', 6)),
            'amplitude': self._find_number(prompt, r'amplitude\s+(\d+(?:\.\d+)?)\s*mm', 3.0),
            'ring_spacing': self._find_number(prompt, r'spacing\s+(\d+(?:\.\d+)?)\s*mm', 6.0),
            'strut_width': self._find_number(prompt, r'strut.*?width\s+(\d+(?:\.\d+)?)\s*mm', 0.6),
            'strut_depth': self._find_number(prompt, r'strut.*?depth\s+(\d+(?:\.\d+)?)\s*mm', 0.4),
        }
        
        return {"type": "stent", "parameters": params, "raw_prompt": prompt}
    
    def _analyze_gripper(self, prompt: str) -> Dict[str, Any]:
        params = {
            'arm_length': self._find_number(prompt, r'arm.*?length\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 25.0),
            'arm_width': self._find_number(prompt, r'arm.*?width\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 8.0),
            'center_diameter': self._find_number(prompt, r'center.*?diameter\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 6.0),
            'thickness': self._find_number(prompt, r'thickness\s*:?\s*(\d+(?:\.\d+)?)\s*mm', 1.5),
            'n_arms': int(self._find_number(prompt, r'(\d+)[- ]arm', 4)),  # 🔥 EXTRACTION DU NOMBRE DE BRAS
        }
        
        log.info(f"✅ GRIPPER: {params['n_arms']} arms, length={params['arm_length']}mm")
        
        return {"type": "gripper", "parameters": params, "raw_prompt": prompt}


class GeneratorAgent:
    def __init__(self):
        self.templates = CodeTemplates()
    
    async def generate(self, analysis: Dict[str, Any]) -> tuple[str, str]:
        app_type = analysis.get('type', 'splint')
        
        log.info(f"🎯 GeneratorAgent: Generating code for type='{app_type}'")
        
        if app_type == 'splint':
            code = self.templates.generate_splint(analysis)
            file_type = 'splint'
        elif app_type == 'stent':
            code = self.templates.generate_stent(analysis)
            file_type = 'stent'
        elif app_type == 'facade_pyramid':
            code = self.templates.generate_facade_pyramid(analysis)
            file_type = 'facade'
        elif app_type == 'honeycomb':  # 🔥 NOUVEAU
            code = self.templates.generate_honeycomb(analysis)
            file_type = 'facade'
        elif app_type == 'louvre_wall':
            code = self.templates.generate_louvre_wall(analysis)
            file_type = 'facade'
        elif app_type == 'sine_wave_fins':
            code = self.templates.generate_sine_wave_fins(analysis)
            file_type = 'facade'
        elif app_type == 'lattice':
            code = self.templates.generate_lattice(analysis)
            file_type = 'lattice'
        elif app_type == 'gripper':
            code = self.templates.generate_gripper(analysis)
            file_type = 'gripper'
        elif app_type == 'heatsink':
            code = self.templates.generate_heatsink(analysis)
            file_type = 'heatsink'
        else:
            log.warning(f"⚠️ Unknown app_type '{app_type}', defaulting to splint")
            code = self.templates.generate_splint(analysis)
            file_type = 'splint'
        
        log.info(f"✅ Generated code for file_type='{file_type}'")
        return code, file_type


class ValidatorAgent:
    def __init__(self):
        try:
            import cadquery as cq
            self.cq_ok = True
        except Exception:
            self.cq_ok = False

    def _safe_builtins(self):
        allowed = [
            "abs", "min", "max", "range", "len", "float", "int", "pow", "sum",
            "zip", "enumerate", "print", "list", "dict", "set", "tuple", "round",
            "__import__", "Exception", "BaseException", "ValueError", "any",
            "str", "open", "bytes", "bool", "isinstance", "type", "iter",
            "next", "hasattr", "getattr", "setattr", "dir", "format",
            "ord", "chr", "hex", "bin", "oct", "sorted", "reversed",
            "map", "filter", "all", "repr", "hash", "id", "callable"
        ]
        return {k: getattr(py_builtins, k) for k in allowed}

    async def validate_and_execute(self, code: str, app_type: str = "model") -> Dict[str, Any]:
        try:
            compile(code, "<cad>", "exec")
        except SyntaxError as e:
            return {"success": False, "errors": [f"Syntax: {e.msg}"]}

        import numpy as np
        from pathlib import Path
        import time

        # Fonction no-op pour show_object (utilisée par CQ-Editor)
        def show_object(obj, name=None, options=None):
            """Dummy function - show_object is only for CQ-Editor"""
            pass

        ns = {
            "__builtins__": self._safe_builtins(),
            "math": math,
            "np": np,
            "numpy": np,
            "struct": __import__('struct'),
            "Path": Path,
            "show_object": show_object,
            "__file__": str(Path(__file__).parent / "temp_exec.py"),
        }

        try:
            exec(compile(code, "<cad>", "exec"), ns)

            backend_dir = Path(__file__).parent
            output_dir = backend_dir / "output"

            time.sleep(0.1)

            # TOUJOURS chercher le fichier .stl le plus récent (pas seulement generated_*.stl)
            # Cela corrige le bug où un vieux fichier était retourné au lieu du nouveau
            stl_files = sorted(output_dir.glob("*.stl"), key=lambda p: p.stat().st_mtime, reverse=True)
            stl_path = str(stl_files[0].absolute()) if stl_files else None
            
        except Exception as e:
            log.error(f"Execution failed: {e}", exc_info=True)
            # Include exception type in error message so ErrorHandlerAgent can categorize it
            error_type = type(e).__name__
            return {"success": False, "errors": [f"Execution: {error_type}: {e}"]}

        if stl_path and os.path.exists(stl_path):
            mesh = self._create_mesh_from_stl(stl_path)
        else:
            mesh = self._create_mesh()

        return {
            "success": True,
            "mesh": mesh,
            "analysis": {"dimensions": {}, "features": {}, "validation": {}},
            "stl_path": stl_path,
            "step_path": None,
        }

    def _create_mesh_from_stl(self, stl_path: str) -> Dict[str, Any]:
        try:
            import struct
            
            with open(stl_path, 'rb') as f:
                f.read(80)
                num_triangles = struct.unpack('<I', f.read(4))[0]
                
                vertices = []
                faces = []
                
                for i in range(num_triangles):
                    f.read(12)
                    v1 = struct.unpack('<3f', f.read(12))
                    v2 = struct.unpack('<3f', f.read(12))
                    v3 = struct.unpack('<3f', f.read(12))
                    
                    base_idx = len(vertices) // 3
                    vertices.extend(v1)
                    vertices.extend(v2)
                    vertices.extend(v3)
                    
                    faces.extend([base_idx, base_idx+1, base_idx+2])
                    f.read(2)
                
                if num_triangles > 10000:
                    step = num_triangles // 5000
                    vertices_decimated = []
                    faces_decimated = []
                    for i in range(0, len(faces), step*3):
                        if i+2 < len(faces):
                            base = len(vertices_decimated) // 3
                            for j in range(3):
                                idx = faces[i+j] * 3
                                vertices_decimated.extend(vertices[idx:idx+3])
                            faces_decimated.extend([base, base+1, base+2])
                    
                    vertices = vertices_decimated
                    faces = faces_decimated
                
                return {"vertices": vertices, "faces": faces, "normals": []}
                
        except Exception as e:
            log.warning(f"Failed to load STL: {e}")
            return self._create_mesh()
    
    def _create_mesh(self) -> Dict[str, Any]:
        vertices = []
        faces = []
        
        for i in range(10):
            for j in range(10):
                vertices.extend([(i-5)*10, j*10, math.sin(i*0.5)*math.cos(j*0.5)*5])
        
        for i in range(9):
            for j in range(9):
                v0, v1 = i*10+j, (i+1)*10+j
                v2, v3 = (i+1)*10+(j+1), i*10+(j+1)
                faces.extend([v0, v1, v2, v0, v2, v3])
        
        return {"vertices": vertices, "faces": faces, "normals": []}