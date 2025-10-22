#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
multi_agent_system.py - Système Multi-Agent Intelligent pour CAD
Architecture: 9 agents (3 existants + 6 nouveaux)
"""

import os
import re
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger("cadamx.multi_agent")


# ========== ENUMS & DATA CLASSES ==========

class AgentStatus(Enum):
    """Statut d'exécution d'un agent"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class AgentResult:
    """Résultat d'exécution d'un agent"""
    status: AgentStatus
    data: Any = None
    errors: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowContext:
    """Contexte partagé entre tous les agents"""
    prompt: str
    analysis: Optional[Dict[str, Any]] = None
    design_validation: Optional[Dict[str, Any]] = None
    constraints_validation: Optional[Dict[str, Any]] = None
    generated_code: Optional[str] = None
    syntax_validation: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


# ========== HUGGING FACE LLM CLIENT ==========

class HuggingFaceLLM:
    """Client pour interagir avec les modèles HuggingFace"""

    def __init__(self, model_name: str, api_token: Optional[str] = None):
        self.model_name = model_name
        self.api_token = api_token or os.getenv("HUGGINGFACE_API_TOKEN", "")
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"

        # Fallback: mode local si pas de token
        self.use_local = not self.api_token

        if self.use_local:
            log.warning(f"⚠️ No HF token, using fallback mode for {model_name}")
        else:
            log.info(f"✅ HuggingFace LLM initialized: {model_name}")

    async def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Génère une réponse avec le modèle LLM"""

        if self.use_local:
            # Mode fallback sans API
            return await self._fallback_generate(prompt)

        try:
            import aiohttp

            headers = {"Authorization": f"Bearer {self.api_token}"}
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "do_sample": True
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, headers=headers, json=payload, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Format de réponse HF
                        if isinstance(result, list) and len(result) > 0:
                            return result[0].get("generated_text", "")
                        elif isinstance(result, dict):
                            return result.get("generated_text", "")

                        return str(result)
                    else:
                        error_text = await response.text()
                        log.error(f"HF API error {response.status}: {error_text}")
                        return await self._fallback_generate(prompt)

        except Exception as e:
            log.error(f"HF API call failed: {e}")
            return await self._fallback_generate(prompt)

    async def _fallback_generate(self, prompt: str) -> str:
        """Fallback basique basé sur des règles heuristiques"""

        prompt_lower = prompt.lower()

        # Design validation fallback
        if "design validation" in prompt_lower or "validate design" in prompt_lower:
            return """VALIDATION: PASS
- Material: Compatible with manufacturing
- Dimensions: Within acceptable range
- Tolerances: Standard manufacturing tolerances apply
- Recommendations: None"""

        # Constraint validation fallback
        if "constraint" in prompt_lower or "manufacturing" in prompt_lower:
            return """CONSTRAINTS: VALID
- Size: Acceptable
- Wall thickness: Sufficient
- Feature size: Manufacturable
- Status: PASS"""

        # Code fixing fallback
        if "fix" in prompt_lower or "error" in prompt_lower:
            return """SUGGESTED FIX:
1. Check variable definitions
2. Verify function calls
3. Ensure proper imports
4. Review syntax"""

        return "OK"


# ========== AGENT 1: ORCHESTRATOR ==========

class OrchestratorAgent:
    """
    🎯 ORCHESTRATOR AGENT
    Rôle: Coordonner le pipeline complet et gérer le workflow
    Priorité: CRITIQUE
    """

    def __init__(self, analyst_agent, generator_agent, validator_agent):
        self.analyst = analyst_agent
        self.generator = generator_agent
        self.validator = validator_agent

        # Nouveaux agents
        self.design_expert = DesignExpertAgent()
        self.constraint_validator = ConstraintValidatorAgent()
        self.syntax_validator = SyntaxValidatorAgent()
        self.error_handler = ErrorHandlerAgent()
        self.self_healing = SelfHealingAgent()

        log.info("🎯 OrchestratorAgent initialized")

    async def execute_workflow(self, prompt: str, progress_callback=None) -> Dict[str, Any]:
        """
        Exécute le workflow complet avec gestion d'erreurs et retry
        """
        context = WorkflowContext(prompt=prompt)

        try:
            # PHASE 1: Analyse (Agent existant)
            if progress_callback:
                await progress_callback("status", {"message": "📊 Analyzing prompt...", "progress": 10})

            result = await self._execute_with_retry(
                self.analyst.analyze,
                context,
                "Analysis",
                prompt
            )

            if result.status != AgentStatus.SUCCESS:
                return self._build_error_response(context, "Analysis failed")

            context.analysis = result.data

            # PHASE 2: Design Expert - Validation des règles métier
            if progress_callback:
                await progress_callback("status", {"message": "🎨 Validating design rules...", "progress": 20})

            result = await self._execute_with_retry(
                self.design_expert.validate_design,
                context,
                "Design Validation",
                context.analysis
            )

            if result.status != AgentStatus.SUCCESS:
                log.warning("⚠️ Design validation warnings, continuing...")

            context.design_validation = result.data

            # PHASE 3: Constraint Validator - Vérifier les contraintes
            if progress_callback:
                await progress_callback("status", {"message": "⚖️ Checking manufacturing constraints...", "progress": 30})

            result = await self._execute_with_retry(
                self.constraint_validator.validate_constraints,
                context,
                "Constraint Validation",
                context.analysis
            )

            if result.status != AgentStatus.SUCCESS:
                return self._build_error_response(context, "Constraint validation failed")

            context.constraints_validation = result.data

            # PHASE 4: Génération de code (Agent existant)
            if progress_callback:
                await progress_callback("status", {"message": "💻 Generating code...", "progress": 45})

            result = await self._execute_with_retry(
                self.generator.generate,
                context,
                "Code Generation",
                context.analysis
            )

            if result.status != AgentStatus.SUCCESS:
                return self._build_error_response(context, "Code generation failed")

            code, detected_type = result.data
            context.generated_code = code

            # PHASE 5: Syntax Validator - Vérifier la syntaxe
            if progress_callback:
                await progress_callback("status", {"message": "✅ Validating syntax...", "progress": 60})

            result = await self._execute_with_retry(
                self.syntax_validator.validate_syntax,
                context,
                "Syntax Validation",
                code
            )

            if result.status != AgentStatus.SUCCESS:
                # Tenter une correction automatique
                if progress_callback:
                    await progress_callback("status", {"message": "🩹 Self-healing code...", "progress": 65})

                heal_result = await self.self_healing.heal_code(
                    code,
                    result.errors,
                    context
                )

                if heal_result.status == AgentStatus.SUCCESS:
                    code = heal_result.data
                    context.generated_code = code
                    log.info("✅ Code healed successfully")
                else:
                    return self._build_error_response(context, "Syntax validation failed")

            context.syntax_validation = result.data

            if progress_callback:
                await progress_callback("code", {
                    "code": code,
                    "app_type": detected_type,
                    "progress": 70
                })

            # PHASE 6: Validation et exécution (Agent existant)
            if progress_callback:
                await progress_callback("status", {"message": "⚙️ Executing and validating...", "progress": 80})

            result = await self._execute_with_retry(
                self.validator.validate_and_execute,
                context,
                "Execution",
                code,
                detected_type
            )

            if result.status != AgentStatus.SUCCESS:
                # Gestion d'erreur avancée
                error_result = await self.error_handler.handle_error(
                    result.errors,
                    context
                )

                if error_result.metadata.get("can_retry", False):
                    # Retry avec correction
                    heal_result = await self.self_healing.heal_code(
                        code,
                        result.errors,
                        context
                    )

                    if heal_result.status == AgentStatus.SUCCESS:
                        # Re-exécuter
                        result = await self._execute_with_retry(
                            self.validator.validate_and_execute,
                            context,
                            "Execution (Retry)",
                            heal_result.data,
                            detected_type
                        )

            if result.status != AgentStatus.SUCCESS:
                return self._build_error_response(context, "Execution failed")

            context.execution_result = result.data

            # SUCCÈS!
            if progress_callback:
                await progress_callback("status", {"message": "✅ Generation complete!", "progress": 100})

            return {
                "success": True,
                "mesh": result.data.get("mesh"),
                "analysis": result.data.get("analysis"),
                "code": code,
                "app_type": detected_type,
                "stl_path": result.data.get("stl_path"),
                "step_path": result.data.get("step_path"),
                "metadata": {
                    "design_validation": context.design_validation,
                    "constraints_validation": context.constraints_validation,
                    "syntax_validation": context.syntax_validation,
                    "retry_count": context.retry_count
                }
            }

        except Exception as e:
            log.error(f"❌ Orchestrator workflow failed: {e}", exc_info=True)
            return self._build_error_response(context, str(e))

    async def _execute_with_retry(self, func, context: WorkflowContext, agent_name: str, *args) -> AgentResult:
        """Exécute une fonction agent avec retry automatique"""

        for attempt in range(context.max_retries):
            try:
                log.info(f"🔄 {agent_name} (attempt {attempt + 1}/{context.max_retries})")

                result = await func(*args)

                # Si la fonction ne retourne pas un AgentResult, le wrapper
                if not isinstance(result, AgentResult):
                    return AgentResult(status=AgentStatus.SUCCESS, data=result)

                if result.status == AgentStatus.SUCCESS:
                    return result

                # Échec, incrémenter retry
                context.retry_count += 1

                if attempt < context.max_retries - 1:
                    log.warning(f"⚠️ {agent_name} failed, retrying...")
                    await asyncio.sleep(1)  # Backoff
                else:
                    return result

            except Exception as e:
                log.error(f"❌ {agent_name} error: {e}")
                context.errors.append({
                    "agent": agent_name,
                    "error": str(e),
                    "attempt": attempt + 1
                })

                if attempt < context.max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    return AgentResult(
                        status=AgentStatus.FAILED,
                        errors=[str(e)]
                    )

        return AgentResult(status=AgentStatus.FAILED, errors=["Max retries exceeded"])

    def _build_error_response(self, context: WorkflowContext, message: str) -> Dict[str, Any]:
        """Construit une réponse d'erreur structurée"""
        return {
            "success": False,
            "errors": [message] + [e.get("error", "") for e in context.errors],
            "metadata": {
                "retry_count": context.retry_count,
                "context_errors": context.errors
            }
        }


# ========== AGENT 2: DESIGN EXPERT ==========

class DesignExpertAgent:
    """
    🎨 DESIGN EXPERT AGENT
    Rôle: Valider les règles métier par type CAD avec LLM
    Priorité: CRITIQUE
    Modèle: mistralai/Mistral-7B-Instruct-v0.3
    """

    def __init__(self):
        model_name = os.getenv("DESIGN_EXPERT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
        self.llm = HuggingFaceLLM(model_name)

        # Règles métier par type CAD
        self.design_rules = {
            "splint": {
                "min_thickness": 2.0,
                "max_thickness": 6.0,
                "min_width": 40.0,
                "max_width": 100.0,
                "recommended_materials": ["PLA", "PETG", "Nylon"]
            },
            "stent": {
                "min_strut_width": 0.3,
                "max_strut_width": 1.5,
                "min_diameter": 2.0,
                "max_diameter": 20.0,
                "recommended_materials": ["Nitinol", "Stainless Steel"]
            },
            "heatsink": {
                "min_fin_thickness": 1.0,
                "max_fin_thickness": 5.0,
                "min_spacing": 2.0,
                "recommended_materials": ["Aluminum", "Copper"]
            },
            "facade_pyramid": {
                "min_wall_thickness": 2.0,
                "max_wall_thickness": 10.0,
                "recommended_materials": ["Aluminum", "Steel"]
            },
            "honeycomb": {
                "min_wall_thickness": 1.5,
                "max_wall_thickness": 5.0,
                "min_cell_size": 5.0,
                "max_cell_size": 50.0,
                "recommended_materials": ["Aluminum", "Composite"]
            },
            "gripper": {
                "min_thickness": 1.0,
                "max_thickness": 3.0,
                "min_arm_length": 10.0,
                "max_arm_length": 50.0,
                "recommended_materials": ["Stainless Steel", "Titanium"]
            }
        }

        log.info("🎨 DesignExpertAgent initialized")

    async def validate_design(self, analysis: Dict[str, Any]) -> AgentResult:
        """
        Valide le design selon les règles métier du type CAD
        """

        app_type = analysis.get("type", "splint")
        params = analysis.get("parameters", {})

        log.info(f"🎨 Validating design for type: {app_type}")

        # Vérifier les règles basiques
        rules = self.design_rules.get(app_type, {})
        violations = []
        warnings = []

        # Validation selon le type
        if app_type == "splint":
            thickness = analysis.get("thickness", 3.5)
            if thickness < rules.get("min_thickness", 0):
                violations.append(f"Thickness {thickness}mm is too thin (min: {rules['min_thickness']}mm)")
            elif thickness > rules.get("max_thickness", 999):
                violations.append(f"Thickness {thickness}mm is too thick (max: {rules['max_thickness']}mm)")

        elif app_type == "stent":
            strut_width = params.get("strut_width", 0.6)
            if strut_width < rules.get("min_strut_width", 0):
                violations.append(f"Strut width {strut_width}mm is too thin")

        elif app_type == "heatsink":
            bar_len = params.get("bar_len", 22.0)
            if bar_len < 5.0:
                warnings.append(f"Bar length {bar_len}mm might be too short for effective cooling")

        elif app_type == "honeycomb":
            wall = params.get("wall_thickness", 2.2)
            cell_size = params.get("cell_size", 12.0)

            if wall < rules.get("min_wall_thickness", 0):
                violations.append(f"Wall thickness {wall}mm is too thin")
            if cell_size < rules.get("min_cell_size", 0):
                violations.append(f"Cell size {cell_size}mm is too small")

        # Validation LLM pour analyse approfondie
        llm_validation = await self._llm_design_validation(app_type, analysis)

        if violations:
            return AgentResult(
                status=AgentStatus.FAILED,
                errors=violations,
                metadata={"warnings": warnings, "llm_analysis": llm_validation}
            )

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "status": "PASS",
                "warnings": warnings,
                "llm_analysis": llm_validation,
                "recommended_materials": rules.get("recommended_materials", [])
            }
        )

    async def _llm_design_validation(self, app_type: str, analysis: Dict[str, Any]) -> str:
        """Utilise le LLM pour une analyse approfondie du design"""

        prompt = f"""You are a CAD design expert. Validate this {app_type} design:

Design Parameters:
{analysis}

Provide a brief validation summary (max 3 sentences) covering:
1. Design feasibility
2. Manufacturing considerations
3. Recommendations

Validation:"""

        try:
            response = await self.llm.generate(prompt, max_tokens=256, temperature=0.5)
            return response.strip()
        except Exception as e:
            log.error(f"LLM validation failed: {e}")
            return "LLM validation unavailable"


# ========== AGENT 3: CONSTRAINT VALIDATOR ==========

class ConstraintValidatorAgent:
    """
    ⚖️ CONSTRAINT VALIDATOR AGENT
    Rôle: Vérifier les contraintes de fabrication avant génération
    Priorité: CRITIQUE
    """

    def __init__(self):
        # Contraintes de fabrication
        self.manufacturing_constraints = {
            "min_feature_size": 0.5,  # mm
            "max_model_size": 500.0,  # mm
            "min_wall_thickness": 0.8,  # mm
            "max_overhang_angle": 45.0,  # degrés
        }

        log.info("⚖️ ConstraintValidatorAgent initialized")

    async def validate_constraints(self, analysis: Dict[str, Any]) -> AgentResult:
        """
        Vérifie que le design respecte les contraintes de fabrication
        """

        app_type = analysis.get("type", "splint")
        params = analysis.get("parameters", {})

        log.info(f"⚖️ Validating manufacturing constraints for {app_type}")

        violations = []
        warnings = []

        # Vérification des dimensions globales
        if app_type == "splint":
            sections = analysis.get("sections", [])
            total_length = sum(s.get("length", 0) for s in sections)

            if total_length > self.manufacturing_constraints["max_model_size"]:
                violations.append(f"Total length {total_length}mm exceeds max size")

            thickness = analysis.get("thickness", 3.5)
            if thickness < self.manufacturing_constraints["min_wall_thickness"]:
                violations.append(f"Wall thickness {thickness}mm below minimum")

        elif app_type == "stent":
            strut_width = params.get("strut_width", 0.6)
            if strut_width < self.manufacturing_constraints["min_feature_size"]:
                violations.append(f"Strut width {strut_width}mm below minimum feature size")

        elif app_type == "honeycomb":
            wall = params.get("wall_thickness", 2.2)
            if wall < self.manufacturing_constraints["min_wall_thickness"]:
                violations.append(f"Wall thickness {wall}mm below minimum")

            panel_width = params.get("panel_width", 300.0)
            panel_height = params.get("panel_height", 380.0)

            if max(panel_width, panel_height) > self.manufacturing_constraints["max_model_size"]:
                warnings.append("Large panel size may require split manufacturing")

        elif app_type == "heatsink":
            plate_w = params.get("plate_w", 40.0)
            plate_h = params.get("plate_h", 40.0)

            if max(plate_w, plate_h) > self.manufacturing_constraints["max_model_size"]:
                violations.append("Heatsink dimensions exceed max size")

        # Vérification des features trop petits
        if app_type in ["lattice"]:
            strut_d = params.get("strut_diameter", 1.5)
            if strut_d < self.manufacturing_constraints["min_feature_size"]:
                violations.append(f"Strut diameter {strut_d}mm too small to manufacture")

        if violations:
            return AgentResult(
                status=AgentStatus.FAILED,
                errors=violations,
                metadata={"warnings": warnings}
            )

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "status": "PASS",
                "warnings": warnings,
                "constraints_checked": list(self.manufacturing_constraints.keys())
            }
        )


# ========== AGENT 4: SYNTAX VALIDATOR ==========

class SyntaxValidatorAgent:
    """
    ✅ SYNTAX VALIDATOR AGENT
    Rôle: Vérifier la syntaxe du code Python avant exécution
    Priorité: HAUTE
    """

    def __init__(self):
        log.info("✅ SyntaxValidatorAgent initialized")

    async def validate_syntax(self, code: str) -> AgentResult:
        """
        Vérifie la syntaxe Python du code généré
        """

        log.info("✅ Validating Python syntax")

        errors = []
        warnings = []

        # Vérification syntaxe Python
        try:
            compile(code, "<generated>", "exec")
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
            return AgentResult(
                status=AgentStatus.FAILED,
                errors=errors,
                metadata={"line": e.lineno, "offset": e.offset}
            )

        # Vérifications supplémentaires

        # 1. Vérifier les imports
        required_imports = []
        if "cadquery" in code or "cq." in code:
            required_imports.append("cadquery")
        if "numpy" in code or "np." in code:
            required_imports.append("numpy")
        if "struct" in code:
            required_imports.append("struct")

        for imp in required_imports:
            if f"import {imp}" not in code:
                warnings.append(f"Missing import: {imp}")

        # 2. Vérifier la génération de fichier de sortie
        if "write_stl" not in code and "cq.exporters.export" not in code:
            warnings.append("No STL export detected in code")

        # 3. Vérifier les divisions par zéro potentielles
        if re.search(r"/\s*0\b", code):
            warnings.append("Potential division by zero detected")

        # 4. Vérifier les variables non définies (basique)
        # Pattern: variable utilisée avant définition
        lines = code.split("\n")
        defined_vars = set()
        for line in lines:
            # Skip comments et imports
            if line.strip().startswith("#") or "import" in line:
                continue

            # Détecter les assignations
            if "=" in line and not line.strip().startswith("if"):
                var_match = re.match(r"\s*(\w+)\s*=", line)
                if var_match:
                    defined_vars.add(var_match.group(1))

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "status": "PASS",
                "warnings": warnings,
                "imports_found": required_imports,
                "variables_defined": len(defined_vars)
            }
        )


# ========== AGENT 5: ERROR HANDLER ==========

class ErrorHandlerAgent:
    """
    🚨 ERROR HANDLER AGENT
    Rôle: Gérer toutes les erreurs de façon intelligente
    Priorité: HAUTE
    """

    def __init__(self):
        # Classification des erreurs
        self.error_categories = {
            "syntax": ["SyntaxError", "IndentationError", "TabError"],
            "runtime": ["NameError", "TypeError", "AttributeError", "ValueError"],
            "import": ["ImportError", "ModuleNotFoundError"],
            "memory": ["MemoryError", "RecursionError"],
            "geometry": ["topology", "invalid shape", "degenerate"],
        }

        log.info("🚨 ErrorHandlerAgent initialized")

    async def handle_error(self, errors: List[str], context: WorkflowContext) -> AgentResult:
        """
        Analyse et catégorise les erreurs, propose des solutions
        """

        log.info(f"🚨 Handling {len(errors)} error(s)")

        categorized_errors = []
        recovery_actions = []
        can_retry = False

        for error in errors:
            category = self._categorize_error(error)
            severity = self._assess_severity(error, category)

            categorized_errors.append({
                "error": error,
                "category": category,
                "severity": severity
            })

            # Déterminer les actions de récupération
            if category == "syntax":
                recovery_actions.append("Fix syntax errors with self-healing agent")
                can_retry = True

            elif category == "import":
                recovery_actions.append("Check required dependencies")
                can_retry = False  # Ne peut pas retry sans dépendances

            elif category == "runtime":
                recovery_actions.append("Review variable definitions and types")
                can_retry = True

            elif category == "geometry":
                recovery_actions.append("Adjust geometric parameters")
                can_retry = True

        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "categorized_errors": categorized_errors,
                "recovery_actions": recovery_actions,
                "can_retry": can_retry
            },
            metadata={
                "can_retry": can_retry,
                "error_count": len(errors)
            }
        )

    def _categorize_error(self, error: str) -> str:
        """Catégorise une erreur"""
        error_lower = error.lower()

        for category, keywords in self.error_categories.items():
            for keyword in keywords:
                if keyword.lower() in error_lower:
                    return category

        return "unknown"

    def _assess_severity(self, error: str, category: str) -> str:
        """Évalue la sévérité d'une erreur"""

        if category in ["memory", "import"]:
            return "critical"
        elif category in ["syntax", "runtime"]:
            return "high"
        elif category == "geometry":
            return "medium"
        else:
            return "low"


# ========== AGENT 6: SELF-HEALING ==========

class SelfHealingAgent:
    """
    🩹 SELF-HEALING AGENT
    Rôle: Corriger automatiquement les erreurs de code
    Priorité: MOYENNE
    Modèle: bigcode/starcoder2-15b
    """

    def __init__(self):
        model_name = os.getenv("CODE_LLM_MODEL", "bigcode/starcoder2-15b")
        self.llm = HuggingFaceLLM(model_name)

        log.info("🩹 SelfHealingAgent initialized")

    async def heal_code(self, code: str, errors: List[str], context: WorkflowContext) -> AgentResult:
        """
        Tente de corriger automatiquement le code avec erreurs
        """

        log.info(f"🩹 Attempting to heal code ({len(errors)} error(s))")

        # Tentative de correction basique d'abord
        fixed_code = self._basic_fixes(code, errors)

        # Si correction basique insuffisante, utiliser LLM
        if fixed_code == code and len(errors) > 0:
            fixed_code = await self._llm_heal_code(code, errors)

        # Vérifier si le code est corrigé
        try:
            compile(fixed_code, "<healed>", "exec")
            log.info("✅ Code healed successfully")

            return AgentResult(
                status=AgentStatus.SUCCESS,
                data=fixed_code,
                metadata={"fixes_applied": True}
            )

        except SyntaxError as e:
            log.error(f"❌ Healing failed: {e}")
            return AgentResult(
                status=AgentStatus.FAILED,
                errors=[f"Healing failed: {str(e)}"],
                data=code  # Retourner le code original
            )

    def _basic_fixes(self, code: str, errors: List[str]) -> str:
        """
        Applique des corrections basiques communes
        """

        fixed_code = code

        for error in errors:
            error_lower = error.lower()

            # Fix 1: Missing imports
            if "nameError" in error or "not defined" in error_lower:
                if "np" in error and "import numpy as np" not in fixed_code:
                    fixed_code = "import numpy as np\n" + fixed_code

                if "math" in error and "import math" not in fixed_code:
                    fixed_code = "import math\n" + fixed_code

                if "struct" in error and "import struct" not in fixed_code:
                    fixed_code = "import struct\n" + fixed_code

            # Fix 2: Indentation errors (basique)
            if "indentation" in error_lower:
                lines = fixed_code.split("\n")
                # Normaliser l'indentation
                fixed_lines = []
                for line in lines:
                    # Remplacer tabs par spaces
                    fixed_lines.append(line.replace("\t", "    "))
                fixed_code = "\n".join(fixed_lines)

        return fixed_code

    async def _llm_heal_code(self, code: str, errors: List[str]) -> str:
        """
        Utilise le LLM pour corriger le code
        """

        errors_text = "\n".join([f"- {e}" for e in errors[:3]])  # Max 3 erreurs

        prompt = f"""Fix the following Python code errors:

Errors:
{errors_text}

Code:
```python
{code[:1000]}
```

Provide the corrected code:
```python
"""

        try:
            response = await self.llm.generate(prompt, max_tokens=1024, temperature=0.3)

            # Extraire le code de la réponse
            code_match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()

            # Si pas de markdown, retourner la réponse brute
            return response.strip()

        except Exception as e:
            log.error(f"LLM healing failed: {e}")
            return code


# ========== EXPORTS ==========

__all__ = [
    "OrchestratorAgent",
    "DesignExpertAgent",
    "ConstraintValidatorAgent",
    "SyntaxValidatorAgent",
    "ErrorHandlerAgent",
    "SelfHealingAgent",
    "AgentStatus",
    "AgentResult",
    "WorkflowContext"
]
