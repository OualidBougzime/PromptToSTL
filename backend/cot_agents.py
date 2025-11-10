#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chain-of-Thought agents pour générer n'importe quelle forme CAD.
Pas besoin de templates prédéfinis - le système analyse et génère du code
pour tout ce qu'on lui demande (engrenages, supports, boîtiers, etc.)
"""

import os
import json
import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

log = logging.getLogger("cadamx.cot_agents")


# Classes de données pour structurer les résultats entre agents
@dataclass
class DesignAnalysis:
    """Ce que l'architect agent comprend de la demande"""
    description: str
    primitives_needed: List[str]  # box, cylinder, sphere, etc.
    operations_sequence: List[str]
    parameters: Dict[str, Any]
    complexity: str  # simple, medium ou complex
    reasoning: str


@dataclass
class ConstructionPlan:
    """Plan étape par étape pour construire la pièce"""
    steps: List[Dict[str, Any]]
    variables: Dict[str, Any]
    constraints: List[str]
    estimated_complexity: int


@dataclass
class GeneratedCode:
    """Code Python/CadQuery final avec quelques infos"""
    code: str
    language: str
    primitives_used: List[str]
    confidence: float


class OllamaCoTClient:
    """
    Client pour parler avec Ollama en mode chat.
    On utilise Ollama plutôt qu'une API payante pour rester 100% local et gratuit.
    """

    def __init__(self, model: str, base_url: Optional[str] = None):
        self.model = model
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.use_fallback = False

        try:
            import ollama
            self.client = ollama.AsyncClient(host=self.base_url)
            log.info(f"✅ Ollama CoT Client initialized: {model} @ {self.base_url}")
        except ImportError:
            log.error("⚠️ Ollama package not installed, using fallback mode")
            self.use_fallback = True
        except Exception as e:
            log.warning(f"⚠️ Ollama connection failed: {e}, using fallback mode")
            self.use_fallback = True

    async def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Génère une réponse via Ollama (format chat compatible OpenAI)"""

        if self.use_fallback:
            return await self._fallback_generate(messages)

        try:
            import ollama

            # Ollama supporte le format messages (chat)
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                }
            )

            # Ollama retourne un dict avec 'message' -> 'content'
            if isinstance(response, dict) and "message" in response:
                return response["message"]["content"].strip()

            return str(response).strip()

        except Exception as e:
            log.error(f"Ollama CoT API call failed: {e}")
            log.warning("Falling back to heuristic mode")
            return await self._fallback_generate(messages)

    async def _fallback_generate(self, messages: List[Dict[str, str]]) -> str:
        """Fallback basique si Ollama non disponible"""
        # Extraire le message système et utilisateur
        system_msg = ""
        user_msg = ""

        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"].lower()
            elif msg["role"] == "user":
                user_msg = msg["content"].lower()

        # Détecter quel agent appelle (via le system prompt)
        is_architect = "architect" in system_msg and "analyze" in system_msg
        is_planner = "planner" in system_msg and "construction plan" in system_msg
        is_synthesizer = "code generator" in system_msg or "generate" in system_msg

        # === ARCHITECT FALLBACK ===
        if is_architect:
            # Détecter la forme demandée dans le prompt
            if "torus" in user_msg:
                primitive = "torus"
                operations = ["create_workplane", "create_torus"]
                params = {"major_radius": 40, "minor_radius": 10}
            elif "cylinder" in user_msg or "cylindre" in user_msg:
                primitive = "cylinder"
                operations = ["create_workplane", "create_cylinder"]
                params = {"radius": 25, "height": 60}
            elif "sphere" in user_msg or "sphère" in user_msg:
                primitive = "sphere"
                operations = ["create_workplane", "create_sphere"]
                params = {"radius": 30}
            elif "cone" in user_msg or "cône" in user_msg:
                primitive = "cone"
                operations = ["create_workplane", "create_cone"]
                params = {"radius1": 40, "radius2": 10, "height": 80}
            elif "cube" in user_msg or "box" in user_msg or "boîte" in user_msg or "carré" in user_msg:
                # Détection explicite de cube/box
                primitive = "box"
                operations = ["create_workplane", "create_box"]
                params = {"width": 50, "height": 50, "depth": 50}
            else:
                # Box par défaut si aucune forme détectée
                primitive = "box"
                operations = ["create_workplane", "create_box"]
                params = {"width": 50, "height": 50, "depth": 50}

            # Retourner un JSON valide pour ArchitectAgent
            import json
            return json.dumps({
                "description": f"Simple {primitive} from fallback",
                "primitives_needed": [primitive],
                "operations_sequence": operations,
                "parameters": params,
                "complexity": "simple",
                "reasoning": f"Fallback mode - Ollama unavailable, detected {primitive}"
            })

        # === PLANNER FALLBACK ===
        elif is_planner:
            # Détecter la forme demandée dans le prompt
            if "torus" in user_msg:
                steps = [
                    {"operation": "Workplane", "parameters": {"plane": "XZ"}, "description": "Create XZ plane for torus"},
                    {"operation": "moveTo", "parameters": {"x": 40, "y": 0}, "description": "Position at major radius"},
                    {"operation": "circle", "parameters": {"radius": 10}, "description": "Create minor circle"},
                    {"operation": "revolve", "parameters": {"angle": 360, "axis": [0, 1, 0]}, "description": "Revolve around Y-axis"}
                ]
            elif "cylinder" in user_msg or "cylindre" in user_msg:
                steps = [
                    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base plane"},
                    {"operation": "circle", "parameters": {"radius": 25}, "description": "Create circle"},
                    {"operation": "extrude", "parameters": {"distance": 60}, "description": "Extrude to height"}
                ]
            elif "sphere" in user_msg or "sphère" in user_msg:
                steps = [
                    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base plane"},
                    {"operation": "sphere", "parameters": {"radius": 30}, "description": "Create sphere"}
                ]
            elif "cone" in user_msg or "cône" in user_msg:
                steps = [
                    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base plane"},
                    {"operation": "circle", "parameters": {"radius": 40}, "description": "Create base circle"},
                    {"operation": "workplane", "parameters": {"offset": 80}, "description": "Create top plane"},
                    {"operation": "circle", "parameters": {"radius": 10}, "description": "Create top circle"},
                    {"operation": "loft", "parameters": {}, "description": "Loft between circles"}
                ]
            elif "cube" in user_msg or "box" in user_msg or "boîte" in user_msg or "carré" in user_msg:
                # Détection explicite de cube/box
                steps = [
                    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base plane"},
                    {"operation": "box", "parameters": {"length": 50, "width": 50, "height": 50}, "description": "Create box"}
                ]
            else:
                # Box par défaut si aucune forme détectée
                steps = [
                    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base plane"},
                    {"operation": "box", "parameters": {"length": 50, "width": 50, "height": 50}, "description": "Create box"}
                ]

            # Retourner un JSON valide pour PlannerAgent
            import json
            return json.dumps({
                "steps": steps,
                "variables": {},
                "constraints": [],
                "estimated_complexity": len(steps)
            })

        # === SYNTHESIZER FALLBACK ===
        elif is_synthesizer:
            # Détecter la forme demandée dans le prompt
            if "torus" in user_msg:
                code = '''```python
import cadquery as cq
from pathlib import Path

# Fallback: Torus
profile = cq.Workplane("XZ").moveTo(40, 0).circle(10)
result = profile.revolve(360, (0, 0, 0), (0, 1, 0))

# Export to STL
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
```'''
            elif "cylinder" in user_msg or "cylindre" in user_msg:
                code = '''```python
import cadquery as cq
from pathlib import Path

# Fallback: Cylinder
result = cq.Workplane("XY").circle(25).extrude(50)

# Export to STL
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
```'''
            elif "sphere" in user_msg or "sphère" in user_msg:
                code = '''```python
import cadquery as cq
from pathlib import Path

# Fallback: Sphere
result = cq.Workplane("XY").sphere(30)

# Export to STL
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
```'''
            elif "cone" in user_msg or "cône" in user_msg:
                code = '''```python
import cadquery as cq
from pathlib import Path

# Fallback: Cone
result = (cq.Workplane("XY")
    .circle(40)
    .workplane(offset=80)
    .circle(10)
    .loft())

# Export to STL
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
```'''
            elif "cube" in user_msg or "box" in user_msg or "boîte" in user_msg or "carré" in user_msg:
                # Détection explicite de cube/box
                code = '''```python
import cadquery as cq
from pathlib import Path

# Fallback: Box
result = cq.Workplane("XY").box(50, 50, 50)

# Export to STL
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
```'''
            else:
                # Cube par défaut si aucune forme détectée
                code = '''```python
import cadquery as cq
from pathlib import Path

# Fallback: Box
result = cq.Workplane("XY").box(50, 50, 50)

# Export to STL
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
```'''
            return code

        # Fallback générique (ne devrait pas arriver)
        return "OK"


class ArchitectAgent:
    """
    Premier agent : analyse ce que l'utilisateur veut vraiment.
    Utilise Qwen2.5 14B pour comprendre et décomposer le problème.
    """

    def __init__(self):
        model = os.getenv("COT_ARCHITECT_MODEL", "qwen2.5:14b")
        self.client = OllamaCoTClient(model=model)
        log.info("🏗️ ArchitectAgent initialized")

    async def analyze_design(self, prompt: str) -> DesignAnalysis:
        """Analyse la demande et figure out comment construire ça"""

        log.info(f"🏗️ Analyzing: {prompt[:100]}...")

        system_prompt = """You are an expert CAD architect specialized in 3D modeling with CadQuery.

Your role: Analyze user requests and decompose them into geometric primitives and operations.

ANALYSIS PROCESS (think step by step):
1. IDENTIFY the shape: What exactly is the user asking for?
2. PRIMITIVES: What basic shapes are needed? (box, cylinder, sphere, cone, torus, polygon, etc.)
3. OPERATIONS: What transformations? (extrude, revolve, loft, sweep, fillet, chamfer, union, cut, etc.)
4. SEQUENCE: In what order should operations be applied?
5. PARAMETERS: Extract ALL numeric values from the prompt (dimensions, angles, counts, etc.)

Output your analysis in this JSON format:
{
  "description": "Brief description of the shape",
  "primitives_needed": ["primitive1", "primitive2"],
  "operations_sequence": ["step1", "step2", "step3"],
  "parameters": {"param1": value1, "param2": value2},
  "complexity": "simple|medium|complex",
  "reasoning": "Your step-by-step reasoning"
}

CRITICAL RULES FOR VALID JSON:
- ALL parameter values MUST be actual numbers, NOT the word "value"
- Calculate ALL math expressions (e.g., 45*30=1350) and use the result
- Use concrete numeric values, estimate reasonable defaults
- NO variable names, NO placeholders, NO expressions
- ONLY use: strings, numbers, arrays, objects, true, false, null

GOOD: "parameters": {"radius": 25, "height": 50}
BAD:  "parameters": {"radius": value, "height": value}
BAD:  "parameters": {"angle": 45 * 30}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this CAD request: {prompt}"}
        ]

        try:
            response = await self.client.generate(messages, temperature=0.7, max_tokens=1000)

            # Parser la réponse JSON
            # Extraire JSON de la réponse (peut être entouré de markdown)
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            # Nettoyer les patterns JSON invalides courants
            # Pattern 1: Remplacer ": value" par ": 50" (valeur par défaut)
            json_str = re.sub(r':\s*value\b', ': 50', json_str, flags=re.IGNORECASE)

            # Pattern 2: Évaluer les expressions mathématiques simples (e.g., "45 * 30" → 1350)
            def eval_math(match):
                try:
                    expr = match.group(1)
                    # Sécurité: seulement autoriser nombres et opérateurs de base
                    if re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', expr):
                        result = eval(expr)
                        return f": {result}"  # IMPORTANT: Remettre le ':' !
                except:
                    pass
                return match.group(0)

            json_str = re.sub(r':\s*([0-9\s\+\-\*\/\(\)\.]+)(?=\s*[,}\]])', eval_math, json_str)

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as je:
                log.error(f"❌ Architect JSON parsing failed: {je}")
                log.error(f"📝 LLM full response (first 800 chars):\n{response[:800]}")
                log.error(f"📝 Extracted JSON string (first 500 chars):\n{json_str[:500]}")
                # Si le JSON est invalide, utiliser le fallback
                raise je

            return DesignAnalysis(
                description=data.get("description", "Unknown shape"),
                primitives_needed=data.get("primitives_needed", []),
                operations_sequence=data.get("operations_sequence", []),
                parameters=data.get("parameters", {}),
                complexity=data.get("complexity", "medium"),
                reasoning=data.get("reasoning", "")
            )

        except Exception as e:
            log.warning(f"Architect using fallback analysis: {e}")

            # Fallback intelligent - détecte les formes basiques dans le prompt
            prompt_lower = prompt.lower()

            # Fonction helper pour extraire les dimensions du prompt
            def extract_dimension(text: str, keywords: List[str]) -> Optional[float]:
                """Extrait une dimension numérique après un mot-clé"""
                for keyword in keywords:
                    # Pattern: keyword [=:] number [unit]
                    pattern = rf"{keyword}\s*[=:]?\s*(\d+(?:\.\d+)?)\s*(?:mm|cm|m)?"
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return float(match.group(1))
                return None

            # Détection de forme
            if "cylinder" in prompt_lower or "cylindre" in prompt_lower:
                primitives = ["cylinder"]
                operations = ["create_workplane", "create_cylinder"]
                radius = extract_dimension(prompt_lower, ["radius", "rayon", "r"]) or 25
                height = extract_dimension(prompt_lower, ["height", "hauteur", "h", "length"]) or 50
                params = {"radius": radius, "height": height}
                desc = "Simple cylinder"
            elif "sphere" in prompt_lower or "ball" in prompt_lower:
                primitives = ["sphere"]
                operations = ["create_workplane", "create_sphere"]
                radius = extract_dimension(prompt_lower, ["radius", "rayon", "r", "diameter", "diametre"]) or 25
                # Si c'est un diamètre, diviser par 2
                if "diameter" in prompt_lower or "diametre" in prompt_lower:
                    radius = radius / 2
                params = {"radius": radius}
                desc = "Simple sphere"
            elif "cone" in prompt_lower:
                primitives = ["cone"]
                operations = ["create_workplane", "create_cone"]
                r1 = extract_dimension(prompt_lower, ["base.?radius", "bottom.?radius", "radius1", "r1"]) or 30
                r2 = extract_dimension(prompt_lower, ["top.?radius", "radius2", "r2"]) or 0
                height = extract_dimension(prompt_lower, ["height", "hauteur", "h"]) or 50
                params = {"radius1": r1, "radius2": r2, "height": height}
                desc = "Simple cone"
            elif "torus" in prompt_lower:
                primitives = ["torus"]
                operations = ["create_workplane", "create_torus"]
                major = extract_dimension(prompt_lower, ["major.?radius", "outer.?radius", "big.?radius"]) or 40
                minor = extract_dimension(prompt_lower, ["minor.?radius", "inner.?radius", "small.?radius", "tube.?radius"]) or 10
                params = {"major_radius": major, "minor_radius": minor}
                desc = "Simple torus"
            else:
                # Par défaut: cube/box
                primitives = ["box"]
                operations = ["create_workplane", "create_box"]
                width = extract_dimension(prompt_lower, ["width", "largeur", "w"]) or 50
                height = extract_dimension(prompt_lower, ["height", "hauteur", "h"]) or 50
                depth = extract_dimension(prompt_lower, ["depth", "profondeur", "d", "length"]) or 50
                params = {"width": width, "height": height, "depth": depth}
                desc = "Simple box"

            return DesignAnalysis(
                description=desc,
                primitives_needed=primitives,
                operations_sequence=operations,
                parameters=params,
                complexity="simple",
                reasoning=f"Fallback analysis - detected '{primitives[0]}' in prompt"
            )


class PlannerAgent:
    """
    Deuxième agent : prend l'analyse et la transforme en plan étape par étape.
    Utilise Qwen2.5-Coder 14B qui est bon pour ce genre de tâches.
    """

    def __init__(self):
        model = os.getenv("COT_PLANNER_MODEL", "qwen2.5-coder:14b")
        self.client = OllamaCoTClient(model=model)
        log.info("📐 PlannerAgent initialized")

    async def create_plan(self, analysis: DesignAnalysis, prompt: str) -> ConstructionPlan:
        """Transforme l'analyse en plan concret avec des étapes CadQuery"""

        log.info(f"📐 Planning: {analysis.description}")

        system_prompt = """You are a CAD construction planner specialized in CadQuery workflows.

Your role: Transform architectural analysis into a precise, executable construction plan.

PLANNING PRINCIPLES:
1. START SIMPLE: Begin with basic workplane and primitives
2. BUILD UP: Add complexity progressively (2D → 3D → modifications → patterns)
3. BE SPECIFIC: Every parameter must have a concrete numeric value
4. THINK 3D: Consider which plane (XY, XZ, YZ) is best for each operation

CADQUERY OPERATIONS REFERENCE:

WORKPLANES & PRIMITIVES:
- Workplane(plane): Create workplane → plane: "XY"|"XZ"|"YZ"
- box(length, width, height): Solid box
- sphere(radius): Solid sphere
- circle(radius): 2D circle (needs extrude/revolve for 3D)
- rect(width, height): 2D rectangle
- polygon(nSides, diameter): Regular polygon (hexagon: nSides=6)

3D OPERATIONS:
- extrude(distance): Extrude 2D → 3D
- revolve(angleDegrees, axisStart, axisEnd): Revolve around axis (angle is POSITIONAL!)
- loft(): Loft between multiple 2D profiles
- sweep(path): Sweep profile along path

MODIFICATIONS:
- fillet(radius): Round edges
- chamfer(length): Chamfer edges
- shell(thickness): Hollow out solid

BOOLEAN OPERATIONS:
- union(shape): Add shapes together
- cut(shape): Subtract shape
- intersect(shape): Keep only intersection
- cutThruAll(): Cut through entire solid
- cutBlind(depth): Cut to specific depth

PATTERNS:
- polarArray(radius, startAngle, angle, count): Circular pattern
- rarray(xSpacing, ySpacing, xCount, yCount): Rectangular array

SELECTION:
- faces(selector): Select faces → ">Z" (top), "<Z" (bottom), "|Z" (vertical)
- edges(selector): Select edges → "|Z" (parallel to Z), "#Z" (perpendicular)
- vertices(): Select vertices

Output JSON format:
{
  "steps": [
    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base plane"},
    {"operation": "box", "parameters": {"length": 50, "width": 50, "height": 50}, "description": "Create main body"}
  ],
  "variables": {"main_size": 50, "detail_size": 10},
  "constraints": ["All dimensions positive", "Feature size > 1mm"],
  "estimated_complexity": 3
}

CRITICAL RULES FOR VALID JSON:
- ALL values MUST be actual numbers, NOT "value" or variables
- Calculate ALL math expressions (e.g., 45*30=1350)
- Use concrete numeric values
- NO expressions in JSON, NO placeholders
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Create a construction plan for:
Description: {analysis.description}
Primitives needed: {', '.join(analysis.primitives_needed)}
Operations: {', '.join(analysis.operations_sequence)}
Parameters: {json.dumps(analysis.parameters)}
Original prompt: {prompt}
"""}
        ]

        try:
            response = await self.client.generate(messages, temperature=0.5, max_tokens=1500)

            # Parser JSON
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            # Nettoyer les patterns JSON invalides
            json_str = re.sub(r':\s*value\b', ': 50', json_str, flags=re.IGNORECASE)

            # Évaluer les expressions mathématiques
            def eval_math(match):
                try:
                    expr = match.group(1)
                    if re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', expr):
                        result = eval(expr)
                        return f": {result}"  # IMPORTANT: Remettre le ':' !
                except:
                    pass
                return match.group(0)

            json_str = re.sub(r':\s*([0-9\s\+\-\*\/\(\)\.]+)(?=\s*[,}\]])', eval_math, json_str)

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as je:
                log.error(f"❌ Planner JSON parsing failed: {je}")
                log.error(f"📝 LLM full response (first 800 chars):\n{response[:800]}")
                log.error(f"📝 Extracted JSON string (first 500 chars):\n{json_str[:500]}")
                raise je

            return ConstructionPlan(
                steps=data.get("steps", []),
                variables=data.get("variables", {}),
                constraints=data.get("constraints", []),
                estimated_complexity=data.get("estimated_complexity", 5)
            )

        except Exception as e:
            log.warning(f"Planner using fallback plan: {e}")

            # Fallback intelligent basé sur l'analyse
            if analysis.primitives_needed and len(analysis.primitives_needed) > 0:
                primitive = analysis.primitives_needed[0]
                params = analysis.parameters
            else:
                primitive = "box"
                params = {"length": 50, "width": 50, "height": 50}

            # Créer le plan approprié
            if primitive == "cylinder":
                steps = [
                    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base workplane"},
                    {"operation": "circle", "parameters": {"radius": params.get("radius", 25)}, "description": "Create circle"},
                    {"operation": "extrude", "parameters": {"distance": params.get("height", 50)}, "description": "Extrude to height"}
                ]
            elif primitive == "sphere":
                steps = [
                    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base workplane"},
                    {"operation": "sphere", "parameters": {"radius": params.get("radius", 25)}, "description": "Create sphere"}
                ]
            elif primitive == "cone":
                steps = [
                    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base workplane"},
                    {"operation": "circle", "parameters": {"radius": params.get("radius1", 30)}, "description": "Create base circle"},
                    {"operation": "workplane", "parameters": {"offset": params.get("height", 50)}, "description": "Create top workplane"},
                    {"operation": "circle", "parameters": {"radius": params.get("radius2", 0)}, "description": "Create top circle"},
                    {"operation": "loft", "parameters": {}, "description": "Loft between circles"}
                ]
            else:
                # Box par défaut
                steps = [
                    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base"},
                    {"operation": "box", "parameters": {"length": params.get("width", 50), "width": params.get("height", 50), "height": params.get("depth", 50)}, "description": f"Create {primitive}"}
                ]

            return ConstructionPlan(
                steps=steps,
                variables={},
                constraints=[],
                estimated_complexity=len(steps)
            )


class CodeSynthesizerAgent:
    """
    Dernier agent : génère le code Python/CadQuery qui va vraiment créer la pièce.
    DeepSeek-Coder 33B est excellent pour ça - c'est un des meilleurs modèles code open-source.
    """

    def __init__(self):
        model = os.getenv("COT_SYNTHESIZER_MODEL", "deepseek-coder:33b")
        self.client = OllamaCoTClient(model=model)
        log.info("💻 CodeSynthesizerAgent initialized")

    async def generate_code(self, plan: ConstructionPlan, analysis: DesignAnalysis) -> GeneratedCode:
        """Génère le vrai code CadQuery exécutable"""

        log.info(f"💻 Generating code: {analysis.description}")

        # FAST-PATH DÉSACTIVÉ : Forcer l'utilisation des LLMs pour tout
        # if (analysis.complexity == "simple" and
        #     len(analysis.primitives_needed) == 1 and
        #     analysis.primitives_needed[0] in ["cylinder", "sphere", "cone", "torus", "box"]):
        #
        #     primitive = analysis.primitives_needed[0]
        #     params = analysis.parameters
        #     log.info(f"🚀 Fast-path for simple shape: {primitive}")
        #
        #     # Générer directement le code validé
        #     return self._generate_simple_shape_code(primitive, params)

        log.info(f"🧠 Using full LLM pipeline (Fast-path disabled)")

        system_prompt = """You are an expert CadQuery code generator with deep knowledge of the CadQuery Python library.

Your mission: Transform the construction plan into WORKING, EXECUTABLE CadQuery code.

🚨 CRITICAL WARNING - READ THIS FIRST 🚨
===========================================
CadQuery does NOT have a .torus() method!
If you need a TORUS, you MUST use the revolve pattern shown below.
NEVER write: result = cq.Workplane("XY").torus(...)  ← THIS WILL CRASH!
ALWAYS write: profile = cq.Workplane("XZ").moveTo(major_r, 0).circle(minor_r)
             result = profile.revolve(360, (0, 0, 0), (0, 1, 0))

CODE QUALITY REQUIREMENTS:
1. CORRECTNESS: Code must execute without errors
2. COMPLETENESS: Must include imports, creation, and export
3. CLARITY: Use descriptive variable names and comments for complex operations
4. EFFICIENCY: Chain operations when possible using method chaining

=== CRITICAL: CADQUERY API REFERENCE ===
Only use these VALIDATED methods (hallucinating non-existent methods causes failures!):

✅ VALID METHODS:
- box(length, width, height): Create a box
- sphere(radius): Create a sphere
- circle(radius).extrude(height): Cylinder
- polygon(nSides, diameter): Regular polygon (hexagon: nSides=6)
- rect(width, height): Rectangle
- extrude(distance): Extrude 2D to 3D
- revolve([angleDegrees]): Revolve (angle is POSITIONAL, not kwarg!)
- loft(): Loft between sections (no 'closed' parameter)
- fillet(radius), chamfer(length): Edge modifications
- cutThruAll(), cutBlind(depth): Cut operations
- union(shape), intersect(shape): Boolean operations
- faces(">Z"), edges("|Z"): Selection
- workplane(offset=z): New workplane
- polarArray(r, start, angle, count): Circular pattern
- moveTo(x, y): Move to position (used for torus profile)

❌ THESE DO NOT EXIST (common hallucinations):
- .torus(major, minor) → DOES NOT EXIST! Use revolve pattern below
- .regularPolygon() → Use .polygon()
- .cone() → Use circle+loft pattern
- revolve(angle=X) → Use revolve(X) positional
- loft(closed=True) → No 'closed' param
- cut() without argument → Use cutThruAll()

🚨 MANDATORY TORUS PATTERN (NO .torus() METHOD EXISTS!):
========================================================
For a torus with major_radius=40, minor_radius=10:

✅ CORRECT (ONLY WAY THAT WORKS):
```python
import cadquery as cq
# Create circular profile on XZ plane at major radius distance
profile = cq.Workplane("XZ").moveTo(40, 0).circle(10)
# Revolve 360° around Y-axis to create torus
result = profile.revolve(360, (0, 0, 0), (0, 1, 0))
```

❌ WRONG (THIS WILL CRASH - NO .torus() METHOD):
```python
result = cq.Workplane("XY").torus(40, 10)  # AttributeError!
result = cq.Workplane().torus(...)  # AttributeError!
```

⚠️ Important: MUST use XZ plane (not XY) for Y-axis revolve, or you get "No pending wires" error!

Cone/Frustum:
```python
result = (cq.Workplane("XY")
    .circle(40)
    .workplane(offset=80)
    .circle(10)
    .loft())
```

Hexagon:
```python
result = cq.Workplane("XY").polygon(6, 30).extrude(15)
```

Gear (simplified):
```python
import cadquery as cq
result = (cq.Workplane("XY")
    .circle(20)
    .extrude(10)
    .faces(">Z")
    .circle(4)
    .cutThruAll())
# Add teeth using polarArray
result = (result.faces(">Z")
    .workplane()
    .polarArray(18, 0, 360, 20)
    .rect(2, 3)
    .extrude(2))
```

CRITICAL SUCCESS RULES:
1. ✅ ALWAYS import: import cadquery as cq
2. ✅ Create 3D solid BEFORE cut/union (extrude/revolve/loft required first)
3. ✅ revolve() angle is POSITIONAL: revolve(360) NOT revolve(angle=360)
4. ✅ Use cutThruAll() not cut() for through-holes
5. ✅ Chain operations fluently: .method1().method2().method3()
6. ✅ Final shape MUST be assigned to: result = ...
7. ✅ TORUS: Profile on XZ plane for Y-axis revolve (NOT XY!)
8. ✅ Add export at the end (template provided below)

COMMON ERROR PATTERNS TO AVOID:
❌ NO: .torus(major, minor) → ✅ YES: Use revolve pattern
❌ NO: .cone(r1, r2, h) → ✅ YES: Use circle+loft
❌ NO: revolve(angle=360) → ✅ YES: revolve(360)
❌ NO: .cut() with no argument → ✅ YES: .cutThruAll()
❌ NO: loft(closed=True) → ✅ YES: loft() (no closed param)

CODE STRUCTURE TEMPLATE:
```python
import cadquery as cq
from pathlib import Path

# Build the shape (your code here)
result = cq.Workplane("XY")...

# Export to STL
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
```

Output ONLY the complete Python code following the template above.
"""

        plan_text = json.dumps({
            "steps": plan.steps,
            "variables": plan.variables,
            "constraints": plan.constraints
        }, indent=2)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Generate CadQuery code for:
Description: {analysis.description}
Primitives: {', '.join(analysis.primitives_needed)}

Construction Plan:
{plan_text}

Generate the complete working CadQuery code.
"""}
        ]

        try:
            response = await self.client.generate(messages, temperature=0.3, max_tokens=2000)

            # Extraire le code Python
            code = response
            if "```python" in response:
                code = response.split("```python")[1].split("```")[0].strip()
            elif "```" in response:
                code = response.split("```")[1].split("```")[0].strip()

            # Nettoyer les caractères Unicode problématiques (fullwidth → ASCII)
            unicode_replacements = {
                '｜': '|',  # Fullwidth vertical line
                '（': '(',  # Fullwidth left parenthesis
                '）': ')',  # Fullwidth right parenthesis
                '［': '[',  # Fullwidth left bracket
                '］': ']',  # Fullwidth right bracket
                '｛': '{',  # Fullwidth left brace
                '｝': '}',  # Fullwidth right brace
                '，': ',',  # Fullwidth comma
                '．': '.',  # Fullwidth period
                '：': ':',  # Fullwidth colon
                '；': ';',  # Fullwidth semicolon
                '＝': '=',  # Fullwidth equals
                '＋': '+',  # Fullwidth plus
                '－': '-',  # Fullwidth minus
                '＊': '*',  # Fullwidth asterisk
                '／': '/',  # Fullwidth slash
                '＜': '<',  # Fullwidth less than
                '＞': '>',  # Fullwidth greater than
                '＂': '"',  # Fullwidth quotation mark
                '＇': "'",  # Fullwidth apostrophe
            }

            for unicode_char, ascii_char in unicode_replacements.items():
                code = code.replace(unicode_char, ascii_char)

            # Vérifier que le code contient les imports nécessaires
            if "import cadquery" not in code:
                code = "import cadquery as cq\n\n" + code

            # Vérifier que le code se termine par result
            if "result" not in code:
                code += "\n\n# Final result\nresult"

            # Ajouter automatiquement l'export STL
            if "cq.exporters.export" not in code and ".exportStl" not in code:
                export_code = """

# Export to STL
from pathlib import Path
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
"""
                code += export_code

            return GeneratedCode(
                code=code,
                language="python",
                primitives_used=analysis.primitives_needed,
                confidence=0.8 if not self.client.use_fallback else 0.5
            )

        except Exception as e:
            log.warning(f"Code synthesis using fallback: {e}")

            # Fallback intelligent basé sur l'analyse
            if analysis.primitives_needed and len(analysis.primitives_needed) > 0:
                primitive = analysis.primitives_needed[0]
                params = analysis.parameters
            else:
                primitive = "box"
                params = {"width": 50, "height": 50, "depth": 50}

            # Générer le code approprié
            if primitive == "cylinder":
                shape_code = f'result = cq.Workplane("XY").circle({params.get("radius", 25)}).extrude({params.get("height", 50)})'
            elif primitive == "sphere":
                # Utiliser sphere() directement - plus fiable que revolve
                radius = params.get("radius", 25)
                shape_code = f'result = cq.Workplane("XY").sphere({radius})'
            elif primitive == "cone":
                r1 = params.get("radius1", params.get("base_radius", 30))
                r2 = params.get("radius2", params.get("top_radius", 0))
                h = params.get("height", 50)
                shape_code = f'''result = (cq.Workplane("XY")
    .circle({r1})
    .workplane(offset={h})
    .circle({r2})
    .loft())'''
            elif primitive == "torus":
                # Torus : revolve un cercle autour d'un axe
                major_r = params.get("major_radius", params.get("major", 40))
                minor_r = params.get("minor_radius", params.get("minor", 10))
                shape_code = f'''profile = cq.Workplane("XZ").moveTo({major_r}, 0).circle({minor_r})
result = profile.revolve(360, (0, 0, 0), (0, 1, 0))'''
            else:
                # Box par défaut
                w = params.get("width", 50)
                h = params.get("height", 50)
                d = params.get("depth", 50)
                shape_code = f'result = cq.Workplane("XY").box({w}, {h}, {d})'

            fallback_code = f"""import cadquery as cq
from pathlib import Path

# Fallback: Create {primitive}
{shape_code}

# Export to STL
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {{output_path}}")
"""
            return GeneratedCode(
                code=fallback_code,
                language="python",
                primitives_used=[primitive],
                confidence=0.5
            )

    def _generate_simple_shape_code(self, primitive: str, params: Dict[str, Any]) -> GeneratedCode:
        """Génère du code validé pour les formes simples (fast-path, évite les hallucinations LLM)"""

        # Générer le code de forme spécifique
        if primitive == "cylinder":
            radius = params.get("radius", 25)
            height = params.get("height", 50)
            shape_code = f'result = cq.Workplane("XY").circle({radius}).extrude({height})'

        elif primitive == "sphere":
            radius = params.get("radius", 25)
            shape_code = f'result = cq.Workplane("XY").sphere({radius})'

        elif primitive == "cone":
            r1 = params.get("radius1", params.get("base_radius", 30))
            r2 = params.get("radius2", params.get("top_radius", 0))
            h = params.get("height", 50)
            shape_code = f'''result = (cq.Workplane("XY")
    .circle({r1})
    .workplane(offset={h})
    .circle({r2})
    .loft())'''

        elif primitive == "torus":
            # CRITICAL: Utiliser plan XZ pour revolve autour de l'axe Y
            major_r = params.get("major_radius", params.get("major", 40))
            minor_r = params.get("minor_radius", params.get("minor", 10))
            shape_code = f'''# Create circular profile on XZ plane
profile = cq.Workplane("XZ").moveTo({major_r}, 0).circle({minor_r})
# Revolve around Y-axis
result = profile.revolve(360, (0, 0, 0), (0, 1, 0))'''

        else:  # box
            w = params.get("width", 50)
            h = params.get("height", 50)
            d = params.get("depth", 50)
            shape_code = f'result = cq.Workplane("XY").box({w}, {h}, {d})'

        # Code complet avec imports et export
        code = f"""import cadquery as cq
from pathlib import Path

# Generate {primitive}
{shape_code}

# Export to STL
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {{output_path}}")
"""

        log.info(f"✅ Generated validated code for {primitive} (fast-path)")

        return GeneratedCode(
            code=code,
            language="python",
            primitives_used=[primitive],
            confidence=0.95  # Haute confiance : code validé manuellement
        )


# ========== EXPORTS ==========

__all__ = [
    "ArchitectAgent",
    "PlannerAgent",
    "CodeSynthesizerAgent",
    "DesignAnalysis",
    "ConstructionPlan",
    "GeneratedCode"
]
