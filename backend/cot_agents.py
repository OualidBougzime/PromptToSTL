#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cot_agents.py - Chain-of-Thought Agents for Universal CAD Generation
Permet de générer N'IMPORTE QUELLE forme, pas juste les templates prédéfinis
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

log = logging.getLogger("cadamx.cot_agents")


# ========== DATA CLASSES ==========

@dataclass
class DesignAnalysis:
    """Résultat de l'analyse architecturale"""
    description: str
    primitives_needed: List[str]
    operations_sequence: List[str]
    parameters: Dict[str, Any]
    complexity: str  # "simple", "medium", "complex"
    reasoning: str


@dataclass
class ConstructionPlan:
    """Plan de construction détaillé"""
    steps: List[Dict[str, Any]]
    variables: Dict[str, Any]
    constraints: List[str]
    estimated_complexity: int


@dataclass
class GeneratedCode:
    """Code généré avec métadonnées"""
    code: str
    language: str
    primitives_used: List[str]
    confidence: float


# ========== OPENAI CLIENT ==========

class OpenAIClient:
    """Client pour interagir avec OpenAI GPT-4"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.use_fallback = not self.api_key

        if self.use_fallback:
            log.warning("⚠️ No OpenAI API key, Chain-of-Thought will use fallback mode")
        else:
            log.info(f"✅ OpenAI Client initialized: {model}")

    async def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Génère une réponse via OpenAI API"""

        if self.use_fallback:
            return await self._fallback_generate(messages)

        try:
            import openai
            import aiohttp

            openai.api_key = self.api_key

            # Utiliser l'API OpenAI async
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        log.error(f"OpenAI API error {response.status}: {error_text}")
                        return await self._fallback_generate(messages)

        except Exception as e:
            log.error(f"OpenAI API call failed: {e}")
            return await self._fallback_generate(messages)

    async def _fallback_generate(self, messages: List[Dict[str, str]]) -> str:
        """Fallback basique si OpenAI non disponible"""
        # Extraire le dernier message utilisateur
        user_msg = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_msg = msg["content"].lower()
                break

        # Réponses basiques selon le contexte
        if "cube" in user_msg or "box" in user_msg:
            return "Create a box with dimensions 50x50x50mm using workplane and box primitive."

        if "cylinder" in user_msg or "circle" in user_msg:
            return "Create a cylinder with radius 25mm and height 50mm using circle and extrude."

        if "sphere" in user_msg:
            return "Create a sphere using sphere primitive with radius 25mm."

        return "Create basic shape using CadQuery primitives: workplane, box, circle, extrude."


# ========== AGENT 1: ARCHITECT (Chain-of-Thought) ==========

class ArchitectAgent:
    """
    🏗️ ARCHITECT AGENT
    Rôle: Analyser la demande et raisonner sur le design (Chain-of-Thought)
    Utilise: GPT-4 pour raisonnement complexe
    """

    def __init__(self):
        model = os.getenv("COT_ARCHITECT_MODEL", "gpt-4")
        self.client = OpenAIClient(model=model)
        log.info("🏗️ ArchitectAgent (Chain-of-Thought) initialized")

    async def analyze_design(self, prompt: str) -> DesignAnalysis:
        """
        Analyse la demande utilisateur avec raisonnement Chain-of-Thought
        """

        log.info(f"🏗️ Analyzing design with CoT: {prompt[:100]}...")

        system_prompt = """You are an expert CAD architect. Your role is to analyze user requests for 3D shapes and reason about how to construct them.

Think step by step:
1. What is the user asking for?
2. What are the basic geometric primitives needed? (box, cylinder, sphere, cone, torus, etc.)
3. What operations are needed? (extrude, revolve, loft, sweep, fillet, chamfer, boolean ops, etc.)
4. What's the construction sequence?
5. What parameters are important?

Output your analysis in this JSON format:
{
  "description": "Brief description of the shape",
  "primitives_needed": ["primitive1", "primitive2"],
  "operations_sequence": ["step1", "step2", "step3"],
  "parameters": {"param1": value1, "param2": value2},
  "complexity": "simple|medium|complex",
  "reasoning": "Your step-by-step reasoning"
}
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

            data = json.loads(json_str)

            return DesignAnalysis(
                description=data.get("description", "Unknown shape"),
                primitives_needed=data.get("primitives_needed", []),
                operations_sequence=data.get("operations_sequence", []),
                parameters=data.get("parameters", {}),
                complexity=data.get("complexity", "medium"),
                reasoning=data.get("reasoning", "")
            )

        except Exception as e:
            log.error(f"Architect analysis failed: {e}")
            # Fallback simple
            return DesignAnalysis(
                description=prompt,
                primitives_needed=["box"],
                operations_sequence=["create_workplane", "create_box"],
                parameters={"width": 50, "height": 50, "depth": 50},
                complexity="simple",
                reasoning="Fallback analysis - creating basic box"
            )


# ========== AGENT 2: PLANNER ==========

class PlannerAgent:
    """
    📐 PLANNER AGENT
    Rôle: Décomposer en étapes de construction détaillées
    """

    def __init__(self):
        model = os.getenv("COT_PLANNER_MODEL", "gpt-4")
        self.client = OpenAIClient(model=model)
        log.info("📐 PlannerAgent initialized")

    async def create_plan(self, analysis: DesignAnalysis, prompt: str) -> ConstructionPlan:
        """
        Crée un plan de construction détaillé à partir de l'analyse
        """

        log.info(f"📐 Creating construction plan for: {analysis.description}")

        system_prompt = """You are a CAD construction planner. Given an architectural analysis, create a detailed step-by-step construction plan for CadQuery.

Each step should specify:
- operation: The CadQuery operation to perform
- parameters: The parameters for that operation
- description: What this step does

CadQuery operations available:
- Workplane(plane): Create a workplane (XY, XZ, YZ)
- box(length, width, height): Create a box
- circle(radius): Create a circle
- rect(width, height): Create a rectangle
- extrude(distance): Extrude 2D to 3D
- revolve(angle): Revolve around axis
- fillet(radius): Round edges
- chamfer(distance): Chamfer edges
- union(): Boolean union
- cut(): Boolean subtraction
- intersect(): Boolean intersection
- translate(x, y, z): Move shape
- rotate(axis, angle): Rotate shape
- polarArray(radius, count): Circular pattern

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

            data = json.loads(json_str)

            return ConstructionPlan(
                steps=data.get("steps", []),
                variables=data.get("variables", {}),
                constraints=data.get("constraints", []),
                estimated_complexity=data.get("estimated_complexity", 5)
            )

        except Exception as e:
            log.error(f"Planner failed: {e}")
            # Fallback simple
            return ConstructionPlan(
                steps=[
                    {"operation": "Workplane", "parameters": {"plane": "XY"}, "description": "Create base"},
                    {"operation": "box", "parameters": {"length": 50, "width": 50, "height": 50}, "description": "Create box"}
                ],
                variables={},
                constraints=[],
                estimated_complexity=1
            )


# ========== AGENT 3: CODE SYNTHESIZER ==========

class CodeSynthesizerAgent:
    """
    💻 CODE SYNTHESIZER AGENT
    Rôle: Générer du code CadQuery à partir du plan de construction
    """

    def __init__(self):
        model = os.getenv("COT_SYNTHESIZER_MODEL", "gpt-4")
        self.client = OpenAIClient(model=model)
        log.info("💻 CodeSynthesizerAgent initialized")

    async def generate_code(self, plan: ConstructionPlan, analysis: DesignAnalysis) -> GeneratedCode:
        """
        Génère le code CadQuery final à partir du plan
        """

        log.info(f"💻 Synthesizing CadQuery code for: {analysis.description}")

        system_prompt = """You are an expert CadQuery code generator. Generate clean, working CadQuery code based on the construction plan.

IMPORTANT RULES:
1. Start with: import cadquery as cq
2. Create the shape step by step following the plan
3. End with: result = <final_shape>
4. Use proper CadQuery syntax
5. Add comments for clarity
6. Handle errors gracefully
7. Ensure all operations are chained correctly

Example structure:
```python
import cadquery as cq

# Step 1: Create base
result = cq.Workplane("XY")

# Step 2: Create main body
result = result.box(50, 50, 50)

# Step 3: Add features
result = result.faces(">Z").circle(10).extrude(5)

# Final result
result
```

Output ONLY the Python code, no explanations.
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

            # Vérifier que le code contient les imports nécessaires
            if "import cadquery" not in code:
                code = "import cadquery as cq\n\n" + code

            # Vérifier que le code se termine par result
            if "result" not in code:
                code += "\n\n# Final result\nresult"

            return GeneratedCode(
                code=code,
                language="python",
                primitives_used=analysis.primitives_needed,
                confidence=0.8 if not self.client.use_fallback else 0.5
            )

        except Exception as e:
            log.error(f"Code synthesis failed: {e}")
            # Fallback: code simple
            fallback_code = """import cadquery as cq

# Fallback: Create simple box
result = cq.Workplane("XY").box(50, 50, 50)
"""
            return GeneratedCode(
                code=fallback_code,
                language="python",
                primitives_used=["box"],
                confidence=0.3
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
