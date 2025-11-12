#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Système multi-agent pour la génération CAD.
12 agents qui travaillent ensemble : validation, génération, correction d'erreurs, etc.
Les agents CoT permettent de générer n'importe quelle forme, pas juste les templates.
"""

import os
import re
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from cot_agents import ArchitectAgent, PlannerAgent, CodeSynthesizerAgent

log = logging.getLogger("cadamx.multi_agent")


class AgentStatus(Enum):
    """Status d'un agent (pending, running, success, failed, retry)"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class AgentResult:
    """Ce qu'un agent retourne après son exécution"""
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


# ========== OLLAMA LLM CLIENT ==========

class OllamaLLM:
    """Client pour interagir avec les modèles Ollama (local)"""

    def __init__(self, model_name: str, base_url: Optional[str] = None):
        self.model_name = model_name
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.use_fallback = False

        try:
            import ollama
            self.client = ollama.AsyncClient(host=self.base_url)
            log.info(f"✅ Ollama LLM initialized: {model_name} @ {self.base_url}")
        except ImportError:
            log.error("⚠️ Ollama package not installed, using fallback mode")
            self.use_fallback = True
        except Exception as e:
            log.warning(f"⚠️ Ollama connection failed: {e}, using fallback mode")
            self.use_fallback = True

    async def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Génère une réponse avec le modèle LLM"""

        if self.use_fallback:
            return await self._fallback_generate(prompt)

        try:
            import ollama

            response = await self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                }
            )

            # Ollama retourne un dict avec 'response'
            if isinstance(response, dict):
                return response.get("response", "").strip()

            return str(response).strip()

        except Exception as e:
            log.error(f"Ollama API call failed: {e}")
            log.warning("Falling back to heuristic mode")
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

        # Agents multi-agent (7 - added CriticAgent)
        self.design_expert = DesignExpertAgent()
        self.constraint_validator = ConstraintValidatorAgent()
        self.syntax_validator = SyntaxValidatorAgent()
        self.error_handler = ErrorHandlerAgent()
        self.self_healing = SelfHealingAgent()
        self.critic = CriticAgent()  # 🔍 NEW: Semantic validation BEFORE execution

        # Agents Chain-of-Thought (3) - Pour formes universelles
        self.architect = ArchitectAgent()
        self.planner = PlannerAgent()
        self.code_synthesizer = CodeSynthesizerAgent()

        # Types connus supportés par templates
        self.known_types = {
            "splint", "stent", "lattice", "heatsink",
            "honeycomb", "gripper", "facade_pyramid", "facade_parametric"
        }

        log.info("🎯 OrchestratorAgent initialized (13 agents: 3 base + 7 multi-agent + 3 CoT)")

    def _should_use_cot(self, analysis: Dict[str, Any]) -> bool:
        """
        Détermine si on doit utiliser Chain-of-Thought (formes universelles)
        ou Templates (types connus)

        Returns:
            True si on doit utiliser CoT (forme inconnue)
            False si on peut utiliser un template (forme connue)
        """
        app_type = analysis.get("type", "unknown")

        # Si le type est inconnu ou si l'analyst n'est pas confiant
        if app_type == "unknown" or app_type not in self.known_types:
            log.info(f"🧠 Type '{app_type}' inconnu → Utilisation Chain-of-Thought")
            return True

        # Si type connu, utiliser template
        log.info(f"⚡ Type '{app_type}' connu → Utilisation Template")
        return False

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

            # PHASE 4: Génération de code - ROUTING: Template vs Chain-of-Thought
            use_cot = self._should_use_cot(context.analysis)

            if use_cot:
                # ========== CHAIN-OF-THOUGHT PATHWAY (Formes universelles) ==========
                log.info("🧠 Using Chain-of-Thought agents for universal shape generation")

                # PHASE 4a: Architect Agent - Raisonnement sur le design
                if progress_callback:
                    await progress_callback("status", {"message": "🏗️ Architect analyzing design...", "progress": 40})

                try:
                    design_analysis = await self.architect.analyze_design(prompt)
                    log.info(f"🏗️ Architect: {design_analysis.description} (complexity: {design_analysis.complexity})")
                except Exception as e:
                    log.error(f"Architect failed: {e}")
                    return self._build_error_response(context, f"Architect analysis failed: {e}")

                # PHASE 4b: Planner Agent - Plan de construction
                if progress_callback:
                    await progress_callback("status", {"message": "📐 Planner creating construction plan...", "progress": 50})

                try:
                    construction_plan = await self.planner.create_plan(design_analysis, prompt)
                    log.info(f"📐 Planner: {len(construction_plan.steps)} steps (complexity: {construction_plan.estimated_complexity})")
                except Exception as e:
                    log.error(f"Planner failed: {e}")
                    return self._build_error_response(context, f"Planning failed: {e}")

                # PHASE 4c: Code Synthesizer - Génération du code
                if progress_callback:
                    await progress_callback("status", {"message": "💻 Synthesizer generating code...", "progress": 60})

                try:
                    generated = await self.code_synthesizer.generate_code(construction_plan, design_analysis)
                    code = generated.code
                    detected_type = "cot_generated"  # Type spécial pour CoT
                    log.info(f"💻 Synthesizer: Code generated (confidence: {generated.confidence:.2f})")
                except Exception as e:
                    log.error(f"Code synthesis failed: {e}")
                    return self._build_error_response(context, f"Code synthesis failed: {e}")

                context.generated_code = code

            else:
                # ========== TEMPLATE PATHWAY (Types connus) ==========
                log.info("⚡ Using template-based generation")

                if progress_callback:
                    await progress_callback("status", {"message": "💻 Generating code from template...", "progress": 45})

                result = await self._execute_with_retry(
                    self.generator.generate,
                    context,
                    "Code Generation (Template)",
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

            # PHASE 5.5: 🔍 Critic Agent - Validation sémantique AVANT exécution (NEW!)
            if progress_callback:
                await progress_callback("status", {"message": "🔍 Critic validating code logic...", "progress": 73})

            critic_result = await self._execute_with_retry(
                self.critic.critique_code,
                context,
                "Semantic Validation",
                code,
                prompt
            )

            # Si le Critic détecte des problèmes sémantiques, tenter de corriger AVANT exécution
            if critic_result.status != AgentStatus.SUCCESS:
                log.warning("🔍 Critic detected semantic issues - attempting to heal BEFORE execution")

                if progress_callback:
                    await progress_callback("status", {"message": "🩹 Healing semantic issues...", "progress": 75})

                # Passer les erreurs sémantiques détectées au SelfHealingAgent
                heal_result = await self.self_healing.heal_code(
                    code,
                    critic_result.errors,
                    context
                )

                if heal_result.status == AgentStatus.SUCCESS:
                    code = heal_result.data
                    context.generated_code = code
                    log.info("✅ Code healed successfully after Critic feedback")

                    # Re-vérifier avec Critic après healing
                    critic_result = await self._execute_with_retry(
                        self.critic.critique_code,
                        context,
                        "Semantic Validation (Retry)",
                        code,
                        prompt
                    )

                    if critic_result.status == AgentStatus.SUCCESS:
                        log.info("✅ Critic: Code passed semantic validation after healing")
                    else:
                        log.warning("⚠️ Critic: Still has semantic issues after healing, proceeding with caution")
                else:
                    log.warning("⚠️ Self-healing failed for semantic issues, proceeding with original code")

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
                    # Save generated code to file for debugging
                    from pathlib import Path
                    debug_file = Path(__file__).parent / "output" / "debug_generated_code.py"
                    debug_file.parent.mkdir(exist_ok=True)
                    with open(debug_file, 'w', encoding='utf-8') as f:  # ✅ FIX: UTF-8 for Windows emoji support
                        f.write("# Generated code that failed:\n")
                        f.write(code)
                    log.info(f"💾 Saved failed code to: {debug_file}")

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
                    # Vérifier si c'est un dict avec success=False
                    if isinstance(result, dict) and result.get("success") is False:
                        return AgentResult(
                            status=AgentStatus.FAILED,
                            data=result,
                            errors=result.get("errors", ["Unknown error"])
                        )
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
        model_name = os.getenv("DESIGN_EXPERT_MODEL", "qwen2.5-coder:7b")
        self.llm = OllamaLLM(model_name)

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
            "runtime": ["NameError", "TypeError", "AttributeError"],
            "import": ["ImportError", "ModuleNotFoundError"],
            "memory": ["MemoryError", "RecursionError"],
            "geometry": ["topology", "invalid shape", "degenerate", "no pending wires",
                        "brep_api: command not done", "valueerror", "revolve", "loft"],
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
        model_name = os.getenv("CODE_LLM_MODEL", "deepseek-coder:6.7b")
        self.llm = OllamaLLM(model_name)

        log.info("🩹 SelfHealingAgent initialized")

    async def heal_code(self, code: str, errors: List[str], context: WorkflowContext) -> AgentResult:
        """
        Tente de corriger automatiquement le code avec erreurs
        """

        log.info(f"🩹 Attempting to heal code ({len(errors)} error(s))")

        # Log original code for debugging
        log.debug(f"📝 Original code (first 500 chars):\n{code[:500]}")

        # Tentative de correction basique d'abord
        fixed_code = self._basic_fixes(code, errors)

        # Log if code was modified
        if fixed_code != code:
            log.info(f"🔧 Code was modified by _basic_fixes")
            log.debug(f"📝 Fixed code (first 500 chars):\n{fixed_code[:500]}")

        # ⚠️ LLM healing DISABLED - deepseek-coder:6.7b adds bugs instead of fixing them
        # Problem: Adds hallucinated imports (e.g., 'import Helpers'), generates syntax errors
        # Solution: Keep only deterministic _basic_fixes which work reliably
        # if fixed_code == code and len(errors) > 0:
        #     fixed_code = await self._llm_heal_code(code, errors)

        # Vérifier si le code est corrigé
        try:
            compile(fixed_code, "<healed>", "exec")

            # Log the final fixed code
            if fixed_code != code:
                log.info(f"✅ Code healed successfully (modified)")
                # Show what changed
                original_lines = code.split('\n')
                fixed_lines = fixed_code.split('\n')
                for i, (orig, fixed) in enumerate(zip(original_lines, fixed_lines)):
                    if orig != fixed:
                        log.info(f"  Line {i+1}: '{orig.strip()}' → '{fixed.strip()}'")
            else:
                log.warning(f"⚠️ Code compiled but was not modified by healing")

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
        import re  # Import at function start to avoid UnboundLocalError

        fixed_code = code

        for error in errors:
            error_lower = error.lower()

            # Fix 1: Missing imports
            if "NameError" in error or "not defined" in error_lower:
                if "np" in error and "import numpy as np" not in fixed_code:
                    fixed_code = "import numpy as np\n" + fixed_code

                if "math" in error and "import math" not in fixed_code:
                    fixed_code = "import math\n" + fixed_code

                if "struct" in error and "import struct" not in fixed_code:
                    fixed_code = "import struct\n" + fixed_code

            # Fix 1b: Hallucinated imports (modules that don't exist)
            if "ModuleNotFoundError" in error or "No module named" in error:
                # Remove hallucinated imports
                hallucinated_modules = ['Helpers', 'cadquery.helpers', 'cq_helpers', 'utils', 'cad_utils']

                for module in hallucinated_modules:
                    if f"No module named '{module}'" in error or f'No module named "{module}"' in error:
                        # Remove the import line
                        lines = fixed_code.split('\n')
                        fixed_lines = []
                        for line in lines:
                            # Skip lines importing the hallucinated module
                            if f'import {module}' in line or f'from {module}' in line:
                                log.info(f"🩹 Removed hallucinated import: {line.strip()}")
                                continue
                            fixed_lines.append(line)
                        fixed_code = '\n'.join(fixed_lines)

            # Fix 2: Indentation errors (basique)
            if "indentation" in error_lower:
                lines = fixed_code.split("\n")
                # Normaliser l'indentation
                fixed_lines = []
                for line in lines:
                    # Remplacer tabs par spaces
                    fixed_lines.append(line.replace("\t", "    "))
                fixed_code = "\n".join(fixed_lines)

            # Fix 3: CadQuery-specific error fixes
            # 3a: .torus() doesn't exist - CRITICAL FIX
            if "'Workplane' object has no attribute 'torus'" in error:
                # Strategy: Replace entire line containing .torus() with proper revolve pattern

                # Find lines with .torus() call
                lines = fixed_code.split('\n')
                new_lines = []

                for line in lines:
                    if '.torus(' in line:
                        # Extract variable name if exists (e.g., "result = ...")
                        var_match = re.match(r'(\s*)(\w+)\s*=\s*.*\.torus\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)', line)
                        if var_match:
                            indent = var_match.group(1)
                            var_name = var_match.group(2)
                            major_r = var_match.group(3).strip()
                            minor_r = var_match.group(4).strip()

                            # Replace with correct pattern
                            new_lines.append(f'{indent}# Torus via revolve (fixed by SelfHealingAgent)')
                            new_lines.append(f'{indent}profile = cq.Workplane("XZ").moveTo({major_r}, 0).circle({minor_r})')
                            new_lines.append(f'{indent}{var_name} = profile.revolve(360, (0, 0, 0), (0, 1, 0))')
                        else:
                            # No variable assignment, just replace the call
                            indent_match = re.match(r'(\s*)', line)
                            indent = indent_match.group(1) if indent_match else ''

                            # Try to extract parameters
                            param_match = re.search(r'\.torus\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)', line)
                            if param_match:
                                major_r = param_match.group(1).strip()
                                minor_r = param_match.group(2).strip()
                                new_lines.append(f'{indent}# Torus via revolve (fixed by SelfHealingAgent)')
                                new_lines.append(f'{indent}profile = cq.Workplane("XZ").moveTo({major_r}, 0).circle({minor_r})')
                                new_lines.append(f'{indent}result = profile.revolve(360, (0, 0, 0), (0, 1, 0))')
                            else:
                                new_lines.append(line)  # Keep original if can't parse
                    else:
                        new_lines.append(line)

                fixed_code = '\n'.join(new_lines)
                log.info("🩹 Fixed: Replaced .torus() with revolve pattern")

            # 3b: .regularPolygon() doesn't exist
            if "'Workplane' object has no attribute 'regularPolygon'" in error:
                fixed_code = fixed_code.replace('.regularPolygon(', '.polygon(')
                log.info("🩹 Fixed: Replaced .regularPolygon() with .polygon()")

            # 3c: revolve() with wrong parameter name
            if "revolve() got an unexpected keyword argument 'angle'" in error:
                fixed_code = re.sub(
                    r'\.revolve\s*\(\s*angle\s*=\s*(\d+(?:\.\d+)?)\s*\)',
                    r'.revolve(\1)',
                    fixed_code
                )
                log.info("🩹 Fixed: Changed revolve(angle=X) to revolve(X)")

            # 3d: loft() with invalid 'closed' parameter
            if "loft() got an unexpected keyword argument 'closed'" in error:
                fixed_code = re.sub(
                    r'\.loft\s*\(\s*closed\s*=\s*\w+\s*\)',
                    '.loft()',
                    fixed_code
                )
                log.info("🩹 Fixed: Removed invalid 'closed' parameter from loft()")

            # 3d2: sweep() with invalid 'sweepAngle' parameter
            if "sweep() got an unexpected keyword argument 'sweepAngle'" in error or "unexpected keyword argument" in error:
                # Remove sweepAngle parameter from sweep()
                fixed_code = re.sub(
                    r'\.sweep\s*\([^)]*sweepAngle\s*=\s*[^,)]+[,\s]*([^)]*)\)',
                    r'.sweep(\1)',
                    fixed_code
                )
                log.info("🩹 Fixed: Removed invalid 'sweepAngle' parameter from sweep()")

            # 3e: cut() without argument
            if "cut() missing 1 required positional argument" in error:
                # Replace .cut() with .cutThruAll()
                fixed_code = re.sub(
                    r'\.cut\s*\(\s*\)',
                    '.cutThruAll()',
                    fixed_code
                )
                log.info("🩹 Fixed: Replaced .cut() with .cutThruAll()")

            # 3f: Cannot find solid in stack (need to extrude first)
            if "Cannot find a solid on the stack or in the parent chain" in error:
                # This is harder to fix automatically, but we can add a hint
                log.warning("⚠️ Error: No solid found. Need to extrude/revolve/loft before cut operations")
                # Try to find .circle() or .rect() without subsequent .extrude()
                # and add .extrude() if missing
                lines = fixed_code.split('\n')
                for i, line in enumerate(lines):
                    if ('.circle(' in line or '.rect(' in line) and '.extrude(' not in line:
                        # Check if next operation is a cut
                        if i + 1 < len(lines) and ('cutThruAll' in lines[i+1] or 'cut(' in lines[i+1]):
                            # Insert extrude before cut
                            # TODO: Implement automatic .extrude() insertion
                            pass

            # 3g: BRep_API command not done - CRITICAL for torus revolve
            # This happens when using wrong workplane OR missing clean=False for 360° revolves
            if "BRep_API: command not done" in error or "brep_api: command not done" in error.lower():
                log.info("🩹 Attempting to fix: BRep_API error (likely missing clean=False or wrong workplane)")

                # Strategy: First copy all lines, then make modifications
                lines = fixed_code.split('\n')

                # Find revolve operations and fix them
                for i, line in enumerate(lines):
                    if '.revolve(' in line:
                        # Fix 1: Add clean=False for 360° revolves
                        if '360' in line and 'clean=False' not in line:
                            # Find the closing parenthesis of revolve() and add clean=False before it
                            # Handle both revolve(360) and revolve(360, ...)
                            if '.revolve(360)' in line:
                                lines[i] = line.replace('.revolve(360)', '.revolve(360, clean=False)')
                                log.info("🩹 Fixed: Added clean=False to revolve(360)")
                            elif 'revolve(360,' in line and ')' in line:
                                # Find last ) before any comment or end of line
                                parts = line.split('#')[0]  # Remove comments
                                if parts.rstrip().endswith(')'):
                                    lines[i] = parts.rstrip()[:-1] + ', clean=False)' + ('#' + line.split('#')[1] if '#' in line else '')
                                    log.info("🩹 Fixed: Added clean=False to revolve(360, ...)")

                        # Fix 2: Check workplane for Y-axis revolves
                        if '(0, 1, 0)' in line:
                            # Look back to find the Workplane declaration
                            found_fix = False
                            for j in range(i-1, max(-1, i-5), -1):
                                if j >= 0 and 'Workplane("XY")' in lines[j]:
                                    # FOUND THE BUG: XY plane with Y-axis revolve
                                    lines[j] = lines[j].replace('Workplane("XY")', 'Workplane("XZ")')
                                    log.info("🩹 Fixed: Changed Workplane('XY') to Workplane('XZ') for Y-axis revolve")
                                    found_fix = True
                                    break

                            if not found_fix:
                                # Check if the Workplane is on the same line (method chaining)
                                if 'Workplane("XY")' in line:
                                    lines[i] = lines[i].replace('Workplane("XY")', 'Workplane("XZ")')
                                    log.info("🩹 Fixed: Changed Workplane('XY') to Workplane('XZ') for Y-axis revolve (inline)")

                fixed_code = '\n'.join(lines)

            # 3h: Invalid CadQuery methods (hallucinations)
            if "has no attribute" in error:
                # Common hallucinations and their fixes
                method_fixes = {
                    'transformedOffset': 'translate',
                    'transformed': 'rotate',
                    'torus': None,  # Already handled above
                    'regularPolygon': 'polygon',
                    'cone': None,  # Use loft instead
                }

                for bad_method, good_method in method_fixes.items():
                    if f"'{bad_method}'" in error or f'"{bad_method}"' in error:
                        if good_method:
                            fixed_code = fixed_code.replace(f'.{bad_method}(', f'.{good_method}(')
                            log.info(f"🩹 Fixed: Replaced .{bad_method}() with .{good_method}()")
                        else:
                            log.warning(f"⚠️ Method .{bad_method}() detected but no automatic fix available")

            # 3i: polarArray/rarray count parameter must be int, not float
            if "'float' object cannot be interpreted as an integer" in error:
                log.info("🩹 Attempting to fix: polarArray/rarray count must be int")

                # Fix polarArray(..., count) where count is float
                fixed_code = re.sub(
                    r'\.polarArray\s*\(([^,]+),\s*([^,]+),\s*([^,]+),\s*(\d+\.\d+)\s*\)',
                    lambda m: f'.polarArray({m.group(1)}, {m.group(2)}, {m.group(3)}, {int(float(m.group(4)))})',
                    fixed_code
                )

                # Fix rarray(..., xCount, yCount) where counts are floats
                fixed_code = re.sub(
                    r'\.rarray\s*\(([^,]+),\s*([^,]+),\s*(\d+\.\d+),\s*(\d+\.\d+)\s*\)',
                    lambda m: f'.rarray({m.group(1)}, {m.group(2)}, {int(float(m.group(3)))}, {int(float(m.group(4)))})',
                    fixed_code
                )

                log.info("🩹 Fixed: Converted float counts to int in polarArray/rarray")

            # 3j: offset2D KeyError - kind parameter must be string, not float
            if "KeyError" in error and "offset2D" in code:
                log.info("🩹 Attempting to fix: offset2D kind must be string")

                # Fix offset2D(distance, kind) where kind is a float instead of "arc"/"intersection"
                # The LLM sometimes passes a number instead of the kind string
                fixed_code = re.sub(
                    r'\.offset2D\s*\(([^,]+),\s*(\d+(?:\.\d+)?)\s*\)',
                    r'.offset2D(\1, "arc")',  # Default to "arc" mode
                    fixed_code
                )

                log.info("🩹 Fixed: Changed offset2D(dist, <number>) to offset2D(dist, \"arc\")")

            # ========== SEMANTIC FIXES (NEW!) ==========
            # These fix logical/geometric errors, not just syntax errors

            # Semantic Fix 0: Wrong shape generated (torus→sphere, cone→cylinder)
            if "SEMANTIC ERROR: Prompt asks for TORUS but code uses" in error:
                log.info("🩹 Attempting semantic fix: Replace sphere with torus revolve pattern")

                # Extract parameters from context if possible (fallback to defaults)
                major_r = 50  # default major radius
                minor_r = 10  # default minor radius

                # Try to extract from prompt or code
                import re
                major_match = re.search(r'major[_\s]*radius[:\s]*(\d+)', error.lower())
                minor_match = re.search(r'minor[_\s]*radius[:\s]*(\d+)', error.lower())
                if major_match:
                    major_r = int(major_match.group(1))
                if minor_match:
                    minor_r = int(minor_match.group(1))

                # Replace sphere code with torus code
                lines = fixed_code.split('\n')
                new_lines = []
                for line in lines:
                    if '.sphere(' in line:
                        # Extract variable name if any
                        var_match = re.match(r'(\s*)(\w+)\s*=\s*.*\.sphere\s*\(', line)
                        if var_match:
                            indent = var_match.group(1)
                            var_name = var_match.group(2)
                            new_lines.append(f'{indent}# Torus via revolve (fixed by SelfHealingAgent)')
                            new_lines.append(f'{indent}profile = cq.Workplane("XZ").moveTo({major_r}, 0).circle({minor_r})')
                            new_lines.append(f'{indent}{var_name} = profile.revolve(360, (0, 0, 0), (0, 1, 0), clean=False)')
                            log.info(f"🩹 Replaced .sphere() with torus revolve pattern (major={major_r}, minor={minor_r})")
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                fixed_code = '\n'.join(new_lines)

            elif "SEMANTIC ERROR: Prompt asks for ARC" in error:
                log.info("🩹 Attempting semantic fix: Replace wrong code with annular sector (portion de couronne)")

                # Extract parameters from prompt/error
                R_ext = 60        # default outer radius
                R_int = 50        # default inner radius (0.83 * outer)
                theta_deg = 210   # default sweep angle
                height = 10       # default extrusion height
                start_deg = 0     # default start angle

                import re
                # Try to extract from error or use defaults
                radius_match = re.search(r'radius[:\s]*(\d+)', error.lower())
                angle_match = re.search(r'(?:sweep|angle)[:\s]*(\d+)', error.lower())
                if radius_match:
                    R_ext = int(radius_match.group(1))
                    R_int = int(R_ext * 0.83)  # Inner radius ~83% of outer
                if angle_match:
                    theta_deg = int(angle_match.group(1))

                # Find result variable name
                lines = fixed_code.split('\n')
                result_var = 'result'
                for line in lines:
                    if '=' in line and ('.circle(' in line or '.extrude(' in line or 'revolve' in line or 'sweep' in line):
                        var_match = re.match(r'(\s*)(\w+)\s*=\s*', line)
                        if var_match:
                            result_var = var_match.group(2)
                            break

                # Rebuild with annular sector pattern
                new_lines = []
                skip_wrong_code = False
                replaced = False

                for line in lines:
                    # Check if we should stop skipping (reached export/result/comment section)
                    if skip_wrong_code:
                        # Stop skipping when we reach:
                        # - Empty line
                        # - Comment starting with #
                        # - show_object
                        # - Export section
                        # - Result assignment that's not shape creation
                        strip_line = line.strip()
                        if (not strip_line or
                            strip_line.startswith('#') or
                            'show_object' in line or
                            'Path' in line or
                            'export' in line or
                            (strip_line.startswith('result =') and not any(x in line for x in ['.circle(', '.extrude(', 'revolve', '.sweep(']))):
                            skip_wrong_code = False
                            # Continue to add this line
                        else:
                            # Still in wrong code section - skip it
                            continue

                    # Detect start of wrong shape creation code
                    if not replaced and ('.circle(' in line or '.extrude(' in line or 'revolve' in line or '.sweep(' in line):
                        # Get indent
                        indent_match = re.match(r'(\s*)', line)
                        indent = indent_match.group(1) if indent_match else ''

                        # Insert correct annular sector code
                        new_lines.append(f'{indent}# Arc annulaire (annular sector) - fixed by SelfHealingAgent')
                        new_lines.append(f'{indent}import math')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}R_ext = {R_ext}')
                        new_lines.append(f'{indent}R_int = {R_int}')
                        new_lines.append(f'{indent}theta_deg = {theta_deg}')
                        new_lines.append(f'{indent}height = {height}')
                        new_lines.append(f'{indent}start_deg = {start_deg}')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}th = math.radians(theta_deg)')
                        new_lines.append(f'{indent}a0 = math.radians(start_deg)')
                        new_lines.append(f'{indent}a1 = a0 + th')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}def P(R, a):')
                        new_lines.append(f'{indent}    return (R * math.cos(a), R * math.sin(a))')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}{result_var} = (cq.Workplane("XY")')
                        new_lines.append(f'{indent}    .moveTo(*P(R_ext, a0))')
                        new_lines.append(f'{indent}    .threePointArc(P(R_ext, a0 + th/2), P(R_ext, a1))')
                        new_lines.append(f'{indent}    .lineTo(*P(R_int, a1))')
                        new_lines.append(f'{indent}    .threePointArc(P(R_int, a0 + th/2), P(R_int, a0))')
                        new_lines.append(f'{indent}    .close()')
                        new_lines.append(f'{indent}    .extrude(height)')
                        new_lines.append(f'{indent})')
                        log.info(f"🩹 Replaced wrong code with annular sector (R_ext={R_ext}, R_int={R_int}, angle={theta_deg}°)")
                        replaced = True
                        skip_wrong_code = True
                        continue

                    # Add line if we're not skipping
                    new_lines.append(line)
                fixed_code = '\n'.join(new_lines)

            elif "SEMANTIC ERROR: Prompt asks for CONE but code uses" in error:
                log.info("🩹 Attempting semantic fix: Replace cylinder/wrong pattern with cone loft")

                # Extract parameters
                base_radius = 25  # default
                height = 50  # default

                import re
                base_match = re.search(r'(?:base|bottom)[_\s]*(?:diameter|radius)[:\s]*(\d+)', error.lower())
                height_match = re.search(r'height[:\s]*(\d+)', error.lower())
                if base_match:
                    base_radius = int(base_match.group(1)) / 2  # diameter to radius
                if height_match:
                    height = int(height_match.group(1))

                # Replace any wrong pattern with loft
                lines = fixed_code.split('\n')
                new_lines = []
                result_var = 'result'  # default
                replaced = False

                # Find the result variable
                for line in lines:
                    if '=' in line and ('circle' in line.lower() or 'revolve' in line.lower() or 'extrude' in line.lower()):
                        var_match = re.match(r'(\s*)(\w+)\s*=\s*', line)
                        if var_match:
                            result_var = var_match.group(2)
                        break

                # Rebuild with cone loft pattern
                skip_shape_creation = False
                for i, line in enumerate(lines):
                    # Skip wrong shape creation lines (including .cylinder() hallucination)
                    if not replaced and ('.circle(' in line or '.revolve(' in line or '.extrude(' in line or '.cylinder(' in line):
                        if 'loft' not in fixed_code:  # Only replace if no loft exists
                            indent_match = re.match(r'(\s*)', line)
                            indent = indent_match.group(1) if indent_match else ''

                            # Insert correct cone code
                            new_lines.append(f'{indent}# Cone via loft (fixed by SelfHealingAgent)')
                            new_lines.append(f'{indent}{result_var} = (cq.Workplane("XY")')
                            new_lines.append(f'{indent}    .circle({base_radius})')
                            new_lines.append(f'{indent}    .workplane(offset={height})')
                            new_lines.append(f'{indent}    .circle(0.1)')  # Small top radius for cone point
                            new_lines.append(f'{indent}    .loft())')
                            log.info(f"🩹 Replaced wrong pattern with cone loft (base_r={base_radius}, h={height})")
                            replaced = True
                            skip_shape_creation = True
                            continue
                    elif skip_shape_creation and ('revolve' in line or 'extrude' in line):
                        # Skip continuation of wrong pattern
                        continue
                    else:
                        skip_shape_creation = False

                    new_lines.append(line)
                fixed_code = '\n'.join(new_lines)

            # Semantic Fix 1: Table legs positioned at center instead of corners
            if "SEMANTIC ERROR: Table legs appear to be positioned near CENTER" in error:
                log.info("🩹 Attempting semantic fix: Table legs at center → corners")

                # Extract expected coordinates from error message
                import re
                expected_match = re.search(r'expected ~±([\d.]+), ±([\d.]+)', error)
                if expected_match:
                    expected_x = float(expected_match.group(1))
                    expected_y = float(expected_match.group(2))

                    # Find and replace small coordinates with corner positions
                    lines = fixed_code.split('\n')
                    for i, line in enumerate(lines):
                        # Find .moveTo() or .center() with small coordinates
                        moveto_match = re.search(r'\.(?:moveTo|center)\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\)', line)
                        if moveto_match:
                            x = abs(float(moveto_match.group(1)))
                            y = abs(float(moveto_match.group(2)))

                            # If coordinates are suspiciously small (< 30% of expected), fix them
                            if x < expected_x * 0.5 or y < expected_y * 0.5:
                                # Replace with proper corner positions
                                old_x = moveto_match.group(1)
                                old_y = moveto_match.group(2)

                                # Determine which corner based on signs
                                sign_x = '+' if '-' not in old_x else '-'
                                sign_y = '+' if '-' not in old_y else '-'

                                new_x = f"{sign_x}{expected_x:.0f}" if sign_x == '-' else f"{expected_x:.0f}"
                                new_y = f"{sign_y}{expected_y:.0f}" if sign_y == '-' else f"{expected_y:.0f}"

                                lines[i] = line.replace(f'({old_x}, {old_y})', f'({new_x}, {new_y})')
                                log.info(f"🩹 Fixed leg position: ({old_x}, {old_y}) → ({new_x}, {new_y})")

                    fixed_code = '\n'.join(lines)

            # Semantic Fix 2: Hollow object missing cut() or shell()
            if "SEMANTIC ERROR: Prompt mentions hollow/pipe/tube but code has no" in error:
                log.info("🩹 Attempting semantic fix: Add cut() for hollow object")

                # Strategy: Find the main shape creation and add inner cut
                lines = fixed_code.split('\n')

                # Find where result is assigned
                for i, line in enumerate(lines):
                    # Look for result = cq.Workplane...circle(...).extrude(...)
                    if 'result' in line and '.circle(' in line and '.extrude(' in line:
                        # Extract radius and height
                        radius_match = re.search(r'\.circle\s*\(\s*(\d+(?:\.\d+)?)\s*\)', line)
                        extrude_match = re.search(r'\.extrude\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*\)', line)

                        if radius_match and extrude_match:
                            outer_radius = float(radius_match.group(1))
                            height = float(extrude_match.group(2))
                            inner_radius = outer_radius * 0.75  # 25% wall thickness

                            # Rename outer cylinder
                            lines[i] = line.replace('result =', 'outer =')

                            # Add inner cylinder and cut after this line
                            indent = len(line) - len(line.lstrip())
                            indent_str = ' ' * indent

                            # Insert inner and cut operations
                            lines.insert(i + 1, f'{indent_str}inner = cq.Workplane("XY").circle({inner_radius}).extrude({height})')
                            lines.insert(i + 2, f'{indent_str}result = outer.cut(inner)  # Make hollow')

                            log.info(f"🩹 Added cut() to make hollow: outer_r={outer_radius}, inner_r={inner_radius}")
                            break

                fixed_code = '\n'.join(lines)

            # Semantic Fix 3: loft() followed by revolve() - IMPOSSIBLE
            if "SEMANTIC ERROR: Code uses .loft() then .revolve()" in error:
                log.info("🩹 Attempting semantic fix: Remove loft(), keep revolve()")

                # Strategy: Remove the loft() operation and its setup
                lines = fixed_code.split('\n')
                new_lines = []
                skip_until_revolve = False

                for line in lines:
                    if '.loft()' in line:
                        # Mark to skip lines until we hit revolve
                        skip_until_revolve = True
                        log.info("🩹 Removed .loft() operation (conflicts with revolve)")
                        continue

                    if skip_until_revolve:
                        # Skip lines until we find revolve
                        if '.revolve(' in line:
                            skip_until_revolve = False
                            new_lines.append(line)
                        # Skip intermediate workplane offsets for loft
                        elif '.workplane(offset=' in line or '.circle(' in line:
                            continue
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)

                fixed_code = '\n'.join(new_lines)

            # Semantic Fix 4: Bowl/vase without shell() or cut()
            if "hollow" in error.lower() and ("bowl" in error.lower() or "vase" in error.lower()):
                log.info("🩹 Attempting semantic fix: Add shell() for hollow bowl/vase")

                # Find result assignment and add .shell() if missing
                if '.shell(' not in fixed_code:
                    lines = fixed_code.split('\n')
                    for i, line in enumerate(lines):
                        if 'result =' in line and ('.loft()' in line or '.sphere(' in line):
                            # Add shell operation
                            lines[i] = line.rstrip()
                            if not lines[i].endswith(')'):
                                lines[i] += ')'
                            # Check if line ends with a method call
                            if lines[i].rstrip().endswith(')'):
                                # Add shell to the chain
                                indent_match = re.match(r'(\s*)', lines[i])
                                next_indent = indent_match.group(1) + '    ' if indent_match else '    '
                                lines.insert(i + 1, f'{next_indent}.faces(">Z").shell(-3))  # 3mm wall thickness')
                                log.info("🩹 Added .shell() for hollow bowl/vase")
                                break

                    fixed_code = '\n'.join(lines)

        # PROACTIVE FIX: Always remove hallucinated imports at the end (regardless of errors)
        # This prevents issues even if LLM accidentally generates these imports
        hallucinated_modules = ['Helpers', 'cadquery.helpers', 'cq_helpers', 'utils', 'cad_utils',
                                'geometry_utils', 'shape_utils', 'cq_utils']

        lines = fixed_code.split('\n')
        fixed_lines = []
        removed_any = False

        for line in lines:
            # Skip any line that imports a hallucinated module
            should_skip = False
            for module in hallucinated_modules:
                if f'import {module}' in line or f'from {module}' in line:
                    log.info(f"🩹 PROACTIVE: Removed hallucinated import: {line.strip()}")
                    removed_any = True
                    should_skip = True
                    break

            if not should_skip:
                fixed_lines.append(line)

        if removed_any:
            fixed_code = '\n'.join(fixed_lines)
            log.info("✅ Proactive hallucinated import cleanup completed")

        return fixed_code

    async def _llm_heal_code(self, code: str, errors: List[str]) -> str:
        """
        Utilise le LLM pour corriger le code
        """

        errors_text = "\n".join([f"- {e}" for e in errors[:3]])  # Max 3 erreurs

        prompt = f"""Fix the following CadQuery Python code errors:

Errors:
{errors_text}

Code:
```python
{code[:1000]}
```

COMMON CADQUERY FIXES:

1. "No pending wires present" when using revolve():
   - Ensure the profile is on the correct plane (XZ for vertical revolve)
   - The circle/shape must be closed and valid
   - Example: profile = cq.Workplane("XZ").moveTo(40, 0).circle(10)

2. "BRep_API: command not done" errors:
   - Check revolve axis format: revolve(360, (0,0,0), (0,1,0))
   - Ensure shapes are properly closed
   - Avoid degenerate geometry (zero-size features)

3. Torus generation:
   CORRECT:
   profile = cq.Workplane("XZ").moveTo(major_radius, 0).circle(minor_radius)
   result = profile.revolve(360, (0, 0, 0), (0, 1, 0))

4. Sphere generation:
   CORRECT: result = cq.Workplane("XY").sphere(radius)

Provide the corrected code:
```python
"""

        try:
            response = await self.llm.generate(prompt, max_tokens=1024, temperature=0.3)

            # Extraire le code de la réponse
            code_match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
            if code_match:
                healed_code = code_match.group(1).strip()
            else:
                # Si pas de markdown, retourner la réponse brute
                healed_code = response.strip()

            # Nettoyer les caractères Unicode problématiques (fullwidth + block drawing + autres)
            unicode_replacements = {
                # Fullwidth characters (U+FF00 block)
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
                # Block drawing / box drawing characters
                '▁': '_',   # Lower one eighth block (U+2581)
                '▂': '_',   # Lower one quarter block (U+2582)
                '▃': '_',   # Lower three eighths block (U+2583)
                '▄': '_',   # Lower half block (U+2584)
                '▅': '_',   # Lower five eighths block (U+2585)
                '▆': '_',   # Lower three quarters block (U+2586)
                '▇': '_',   # Lower seven eighths block (U+2587)
                '█': '_',   # Full block (U+2588)
                '▉': '_',   # Left seven eighths block (U+2589)
                '▊': '_',   # Left three quarters block (U+258A)
                '▋': '_',   # Left five eighths block (U+258B)
                '▌': '_',   # Left half block (U+258C)
                '▍': '_',   # Left three eighths block (U+258D)
                '▎': '_',   # Left one quarter block (U+258E)
                '▏': '_',   # Left one eighth block (U+258F)
            }

            for unicode_char, ascii_char in unicode_replacements.items():
                healed_code = healed_code.replace(unicode_char, ascii_char)

            return healed_code

        except Exception as e:
            log.error(f"LLM healing failed: {e}")
            return code


# ========== AGENT 7: CRITIC ==========

class CriticAgent:
    """
    🔍 CRITIC AGENT
    Rôle: Valider la logique et la sémantique du code AVANT exécution
    Priorité: HAUTE

    Détecte les erreurs sémantiques que SyntaxValidator ne peut pas voir :
    - Pieds de table mal positionnés (centre vs coins)
    - Objets censés être creux mais sans cut()/shell()
    - Conflits de workflow (loft() + revolve())
    - Dimensions incohérentes ou espacements incorrects
    """

    def __init__(self):
        log.info("🔍 CriticAgent initialized")

    async def critique_code(self, code: str, prompt: str) -> AgentResult:
        """
        Analyse le code généré pour détecter les erreurs sémantiques AVANT exécution
        """

        log.info(f"🔍 Critiquing generated code for prompt: '{prompt[:80]}...'")

        issues = []
        warnings = []

        # Analyse 0 : Forme générée correspond-elle au prompt ? (NOUVEAU - CRITIQUE!)
        shape_mismatch = self._check_shape_mismatch(code, prompt)
        if shape_mismatch:
            issues.append(shape_mismatch)

        # Analyse 1 : Tables avec pieds mal positionnés
        if any(keyword in prompt.lower() for keyword in ["table", "desk", "stand"]):
            leg_issue = self._check_table_legs(code, prompt)
            if leg_issue:
                issues.append(leg_issue)

        # Analyse 2 : Objets creux
        if any(keyword in prompt.lower() for keyword in ["hollow", "creux", "pipe", "tube", "vase", "bowl", "cup", "container"]):
            hollow_issue = self._check_hollow_object(code, prompt)
            if hollow_issue:
                issues.append(hollow_issue)

        # Analyse 3 : Conflits de workflow
        workflow_issue = self._check_workflow_conflicts(code)
        if workflow_issue:
            issues.append(workflow_issue)

        # Analyse 4 : Espacement et dimensions
        spacing_issue = self._check_spacing_and_dimensions(code, prompt)
        if spacing_issue:
            warnings.append(spacing_issue)

        # Analyse 5 : Axes de révolution
        revolve_issue = self._check_revolve_axis(code)
        if revolve_issue:
            warnings.append(revolve_issue)

        if issues:
            log.warning(f"🔍 Critic found {len(issues)} semantic issue(s)")
            for issue in issues:
                log.warning(f"   ⚠️ {issue}")

            return AgentResult(
                status=AgentStatus.FAILED,
                errors=issues,
                data={
                    "issues": issues,
                    "warnings": warnings,
                    "needs_healing": True
                }
            )

        if warnings:
            log.info(f"🔍 Critic found {len(warnings)} warning(s) (non-blocking)")
            for warning in warnings:
                log.info(f"   💡 {warning}")

        log.info("✅ Critic: Code looks semantically correct")
        return AgentResult(
            status=AgentStatus.SUCCESS,
            data={
                "issues": [],
                "warnings": warnings,
                "needs_healing": False
            }
        )

    def _check_shape_mismatch(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie que la forme générée correspond à ce qui est demandé dans le prompt.

        Exemple critique: Prompt demande "torus" mais code génère sphere()
        """
        prompt_lower = prompt.lower()

        # Définir les correspondances forme → méthodes requises
        shape_requirements = {
            'arc': {
                'required': ['threePointArc', 'lineTo', 'close'],  # Arc annulaire = annular sector
                'forbidden': ['.sphere(', '.box(', '.revolve('],
                'error_msg': 'SEMANTIC ERROR: Prompt asks for ARC (annular sector / portion de couronne) but code uses {method}. Use annular sector pattern: moveTo(R_ext, 0) → threePointArc(outer) → lineTo(R_int) → threePointArc(inner) → close() → extrude()'
            },
            'torus': {
                'required': ['revolve', 'moveTo'],  # Torus = profile.moveTo().circle().revolve()
                'forbidden': ['.sphere(', '.box(', '.cylinder('],
                'error_msg': 'SEMANTIC ERROR: Prompt asks for TORUS but code uses {method}. Use revolve pattern: profile = cq.Workplane("XZ").moveTo(major_r, 0).circle(minor_r); result = profile.revolve(360, (0,0,0), (0,1,0), clean=False)'
            },
            'cone': {
                'required': ['loft', 'circle', 'workplane'],  # Cone = circle + workplane + circle + loft
                'forbidden': ['.sphere(', '.box(', '.cylinder('],  # .cylinder() is hallucinated method
                'allow_cylinder': False,  # Cone ne doit PAS être un simple cylinder
                'error_msg': 'SEMANTIC ERROR: Prompt asks for CONE but code uses {method}. Use loft pattern: base circle + workplane(offset=height) + top circle + loft()'
            },
            'cylinder': {
                'required': ['.circle(', '.extrude('],  # Cylinder = circle + extrude
                'forbidden': ['.sphere(', '.box(', 'loft'],
                'error_msg': 'SEMANTIC ERROR: Prompt asks for CYLINDER but code uses {method}. Use: cq.Workplane("XY").circle(radius).extrude(height)'
            },
            'sphere': {
                'required': ['.sphere('],  # Sphere must use .sphere() method
                'forbidden': ['revolve', 'loft', '.box(', '.circle('],  # Not revolve/loft
                'error_msg': 'SEMANTIC ERROR: Prompt asks for SPHERE but code uses {method}. Use: cq.Workplane("XY").sphere(radius)'
            },
            'cube': {
                'required': ['.box('],
                'forbidden': ['.sphere(', '.circle(', 'revolve'],
                'error_msg': 'SEMANTIC ERROR: Prompt asks for CUBE/BOX but code uses {method}. Use: cq.Workplane("XY").box(width, height, depth)'
            },
            'box': {
                'required': ['.box('],
                'forbidden': ['.sphere(', '.circle(', 'revolve'],
                'error_msg': 'SEMANTIC ERROR: Prompt asks for BOX but code uses {method}. Use: cq.Workplane("XY").box(width, height, depth)'
            }
        }

        # Vérifier chaque forme mentionnée dans le prompt
        for shape, requirements in shape_requirements.items():
            if shape in prompt_lower:
                # Vérifier les méthodes interdites
                for forbidden in requirements['forbidden']:
                    if forbidden in code:
                        return requirements['error_msg'].format(method=forbidden)

                # Pour le cone, vérifier qu'il n'utilise PAS juste cylinder
                if shape == 'cone' and '.extrude(' in code and 'loft' not in code:
                    # Simple extrude sans loft = cylinder, pas cone
                    return requirements['error_msg'].format(method='.extrude() without loft')

                # Vérifier que les méthodes requises sont présentes
                if 'required' in requirements:
                    missing = []
                    for required in requirements['required']:
                        if required not in code:
                            missing.append(required)

                    if missing:
                        # Si des méthodes requises manquent, c'est probablement la mauvaise forme
                        return requirements['error_msg'].format(method=f"missing {', '.join(missing)}")

        return None

    def _check_table_legs(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie que les pieds d'une table sont positionnés aux coins, pas au centre
        """
        # Extraire les dimensions de la table du prompt
        import re

        # Chercher mentions de dimensions
        width_match = re.search(r'(\d+)\s*(?:mm|cm)?\s*(?:wide|width|large)', prompt.lower())
        depth_match = re.search(r'(\d+)\s*(?:mm|cm)?\s*(?:deep|depth|profond)', prompt.lower())

        if not width_match or not depth_match:
            # Si pas de dimensions explicites, on ne peut pas valider
            return None

        width = float(width_match.group(1))
        depth = float(depth_match.group(1))

        # Chercher les coordonnées des pieds dans le code
        # Pattern : .moveTo(x, y) ou .center(x, y) ou workplane offset
        leg_positions = re.findall(r'\.(?:moveTo|center)\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\)', code)

        if len(leg_positions) < 2:
            return None  # Pas assez de positions détectées

        # Calculer les positions attendues aux coins (approximatif)
        expected_x = width / 2 - 10  # 10mm de marge du bord
        expected_y = depth / 2 - 10

        # Vérifier si les pieds sont trop proches du centre
        for x_str, y_str in leg_positions:
            x = abs(float(x_str))
            y = abs(float(y_str))

            # Si les coordonnées sont trop petites (< 30% des dimensions), c'est suspect
            if x < width * 0.3 or y < depth * 0.3:
                return (f"SEMANTIC ERROR: Table legs appear to be positioned near CENTER "
                       f"(x={x_str}, y={y_str}), but should be at CORNERS "
                       f"(expected ~±{expected_x:.0f}, ±{expected_y:.0f})")

        return None

    def _check_hollow_object(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie qu'un objet creux utilise bien cut() ou shell()
        """
        # Ignorer si le code contient déjà cut, shell, ou cutBlind
        if any(op in code for op in ['.cut(', '.shell(', '.cutBlind(', '.cutThruAll(']):
            return None

        # Chercher des indices que l'objet devrait être creux
        hollow_keywords = ['hollow', 'creux', 'pipe', 'tube', 'container', 'cup', 'bowl']
        if any(kw in prompt.lower() for kw in hollow_keywords):
            return (f"SEMANTIC ERROR: Prompt mentions hollow/pipe/tube but code has no "
                   f".cut(), .shell(), or .cutBlind() operation. Object will be SOLID.")

        return None

    def _check_workflow_conflicts(self, code: str) -> Optional[str]:
        """
        Détecte les conflits de workflow CadQuery (ex: loft() puis revolve())
        """
        # Conflit 1 : loft() suivi de revolve()
        if '.loft()' in code and '.revolve(' in code:
            loft_index = code.find('.loft()')
            revolve_index = code.find('.revolve(')

            if loft_index < revolve_index:
                return (f"SEMANTIC ERROR: Code uses .loft() then .revolve(). "
                       f"loft() creates a 3D solid - you CANNOT revolve a solid. "
                       f"Choose ONE: either loft between profiles OR revolve a 2D profile.")

        # Conflit 2 : extrude() suivi de revolve()
        if '.extrude(' in code and '.revolve(' in code:
            extrude_index = code.find('.extrude(')
            revolve_index = code.find('.revolve(')

            if extrude_index < revolve_index:
                return (f"SEMANTIC ERROR: Code uses .extrude() then .revolve(). "
                       f"extrude() creates a 3D solid - you CANNOT revolve a solid. "
                       f"Choose ONE: either extrude OR revolve.")

        return None

    def _check_spacing_and_dimensions(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie que les espacements et dimensions sont cohérents
        """
        import re

        # Chercher les valeurs numériques dans le code
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', code)
        if not numbers:
            return None

        # Convertir en float
        values = [float(n) for n in numbers]

        # Détecter les valeurs suspicieusement petites pour un espacement
        if '.rarray(' in code or '.polarArray(' in code:
            # Si on utilise des arrays, vérifier que les espacements ne sont pas trop petits
            small_values = [v for v in values if 0.1 < v < 5]
            if small_values:
                return (f"WARNING: Detected small spacing values {small_values} in array pattern. "
                       f"This might cause overlapping elements. Verify spacing is adequate.")

        return None

    def _check_revolve_axis(self, code: str) -> Optional[str]:
        """
        Vérifie la cohérence entre workplane et axe de révolution
        """
        import re

        # Extraire les revolve avec leurs axes
        revolve_matches = re.findall(r'\.revolve\([^)]*\(0,\s*(\d),\s*0\)[^)]*\(0,\s*(\d),\s*0\)[^)]*\)', code)

        for match in revolve_matches:
            axis_start = match[0]
            axis_end = match[1]

            # Pour révolution autour de Y (0,1,0) -> (0,1,0), devrait être sur XZ
            if axis_start == '1' and axis_end == '1':
                if 'Workplane("XY")' in code:
                    return (f"WARNING: Y-axis revolve detected with XY workplane. "
                           f"Consider using XZ workplane for Y-axis revolve to avoid issues.")

        return None


# ========== EXPORTS ==========

__all__ = [
    "OrchestratorAgent",
    "DesignExpertAgent",
    "ConstraintValidatorAgent",
    "SyntaxValidatorAgent",
    "ErrorHandlerAgent",
    "SelfHealingAgent",
    "CriticAgent",
    "AgentStatus",
    "AgentResult",
    "WorkflowContext"
]
