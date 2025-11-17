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

                # Clean emojis from generated code to avoid encoding issues
                import re
                emoji_pattern = re.compile("["
                    u"\U0001F600-\U0001F64F"  # emoticons
                    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                    u"\U0001F680-\U0001F6FF"  # transport & map symbols
                    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    u"\U00002702-\U000027B0"  # dingbats
                    u"\U000024C2-\U0001F251"
                    u"\u2705"  # ✅ check mark
                    u"\u274C"  # ❌ cross mark
                    "]+", flags=re.UNICODE)
                code = emoji_pattern.sub('', code)

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

                # Clean emojis from generated code to avoid encoding issues
                import re
                emoji_pattern = re.compile("["
                    u"\U0001F600-\U0001F64F"  # emoticons
                    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                    u"\U0001F680-\U0001F6FF"  # transport & map symbols
                    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    u"\U00002702-\U000027B0"  # dingbats
                    u"\U000024C2-\U0001F251"
                    u"\u2705"  # ✅ check mark
                    u"\u274C"  # ❌ cross mark
                    "]+", flags=re.UNICODE)
                code = emoji_pattern.sub('', code)

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

            # PROACTIVE: Remove hallucinated imports BEFORE execution (always, even if Critic said OK)
            log.info("🧹 Running proactive cleanup before execution...")
            code = self.self_healing._remove_hallucinated_imports(code)
            context.generated_code = code

            # DEBUG: Log generated code for spring cases to help debug cylinder issue
            if "spring" in prompt.lower() or "helix" in prompt.lower():
                log.info("=" * 80)
                log.info("🔍 DEBUG: Generated code for SPRING:")
                log.info("-" * 80)
                for i, line in enumerate(code.split('\n'), 1):
                    log.info(f"{i:3d}: {line}")
                log.info("=" * 80)

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
            # Sauvegarder le code qui échoue pour debugging
            from pathlib import Path
            import datetime
            output_dir = Path(__file__).parent / "output"
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            failed_file = output_dir / f"failed_syntax_{timestamp}.py"
            failed_file.write_text(code, encoding='utf-8')

            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            errors.append(error_msg)
            log.error(f"❌ {error_msg}")
            log.error(f"💾 Failed code saved to: {failed_file}")
            log.error(f"📝 Code snippet around error:\n{self._get_code_context(code, e.lineno)}")

            return AgentResult(
                status=AgentStatus.FAILED,
                errors=errors,
                metadata={"line": e.lineno, "offset": e.offset, "saved_to": str(failed_file)}
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

    def _get_code_context(self, code: str, error_line: int, context_lines: int = 3) -> str:
        """
        Retourne les lignes de code autour de l'erreur pour affichage
        """
        lines = code.split('\n')
        start = max(0, error_line - context_lines - 1)
        end = min(len(lines), error_line + context_lines)

        context = []
        for i in range(start, end):
            line_num = i + 1
            marker = " >>> " if line_num == error_line else "     "
            context.append(f"{marker}{line_num:4d} | {lines[i]}")

        return '\n'.join(context)


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
        fixed_code = self._basic_fixes(code, errors, context)

        # Log if code was modified
        if fixed_code != code:
            log.info(f"🔧 Code was modified by _basic_fixes")
            log.debug(f"📝 Fixed code (first 500 chars):\n{fixed_code[:500]}")

        # ✅ LLM healing RE-ENABLED with improved anti-hallucination prompt
        # If basic fixes didn't work, try LLM healing as last resort
        if fixed_code == code and len(errors) > 0:
            log.info("🤖 Basic fixes didn't help, trying LLM healing...")
            fixed_code = await self._llm_heal_code(code, errors)
        elif fixed_code != code:
            log.info("✅ Basic fixes resolved the issue")

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

    def _basic_fixes(self, code: str, errors: List[str], context: WorkflowContext) -> str:
        """
        Applique des corrections basiques communes
        """
        import re  # Import at function start to avoid UnboundLocalError

        fixed_code = code
        prompt = context.prompt if hasattr(context, 'prompt') else ""

        # Fix 0: Remove emojis from code (causes encoding errors on Windows)
        # Remove all emoji characters that can't be encoded in charmap
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"  # dingbats
            u"\U000024C2-\U0001F251"
            u"\u2705"  # ✅ check mark
            u"\u274C"  # ❌ cross mark
            "]+", flags=re.UNICODE)
        fixed_code = emoji_pattern.sub('', fixed_code)

        # Track which fixes have been applied to avoid duplicate work
        fixes_applied = set()

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
                            new_lines.append(f'{indent}{var_name} = (cq.Workplane("XY")')
                            new_lines.append(f'{indent}    .moveTo({major_r}, 0).circle({minor_r})')
                            new_lines.append(f'{indent}    .revolve(360, (0, 0, 0), (0, 0, 1)))')
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
                                new_lines.append(f'{indent}result = (cq.Workplane("XY")')
                                new_lines.append(f'{indent}    .moveTo({major_r}, 0).circle({minor_r})')
                                new_lines.append(f'{indent}    .revolve(360, (0, 0, 0), (0, 0, 1)))')
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

            # 3c: .unionAllParts() doesn't exist - TABLE fix
            if "'Workplane' object has no attribute 'unionAllParts'" in error:
                # Strategy: Replace .unionAllParts() with .combine()
                # .combine() merges all pending solids into one
                fixed_code = fixed_code.replace('.unionAllParts()', '.combine()')
                log.info("🩹 Fixed: Replaced .unionAllParts() with .combine()")

            # 3c0: .unionParts() doesn't exist (variant without "All")
            if "'Workplane' object has no attribute 'unionParts'" in error:
                fixed_code = fixed_code.replace('.unionParts()', '.union()')
                log.info("🩹 Fixed: Replaced .unionParts() with .union()")

            # 3c1: .splineThroughPoints() doesn't exist - VASE fix
            if "'Workplane' object has no attribute 'splineThroughPoints'" in error:
                # Strategy: Replace with .spline() or use lineTo() segments
                fixed_code = fixed_code.replace('.splineThroughPoints(', '.spline(')
                log.info("🩹 Fixed: Replaced .splineThroughPoints() with .spline()")

            # 3c1a: .spline() missing required argument 'listOfXYTuple'
            if "Workplane.spline() missing 1 required positional argument: 'listOfXYTuple'" in error:
                # Strategy: Comment out .spline() - can't auto-fix without knowing points
                lines = fixed_code.split('\n')
                fixed_lines = []
                for line in lines:
                    if '.spline()' in line and 'listOfXYTuple' not in line:
                        indent_match = re.match(r'(\s*)', line)
                        indent = indent_match.group(1) if indent_match else ''
                        fixed_lines.append(f'{indent}# {line.strip()}  # .spline() needs listOfXYTuple argument')
                        log.info(f"🩹 Commented out invalid .spline(): {line.strip()}")
                    else:
                        fixed_lines.append(line)
                fixed_code = '\n'.join(fixed_lines)

            # 3c1b: .helix() doesn't exist - SPRING fix
            if "'Workplane' object has no attribute 'helix'" in error:
                # Strategy: Comment out .helix() and suggest manual helix
                lines = fixed_code.split('\n')
                fixed_lines = []
                for line in lines:
                    if '.helix(' in line:
                        indent_match = re.match(r'(\s*)', line)
                        indent = indent_match.group(1) if indent_match else ''
                        fixed_lines.append(f'{indent}# {line.strip()}  # .helix() not available - use manual helix generation')
                        log.info(f"🩹 Commented out .helix(): {line.strip()}")
                    else:
                        fixed_lines.append(line)
                fixed_code = '\n'.join(fixed_lines)

            # 3c2: Chamfer/fillet on non-existent edges - PIPE fix
            if "There are no suitable edges for chamfer or fillet" in error:
                # Strategy: Comment out problematic chamfer/fillet calls
                lines = fixed_code.split('\n')
                fixed_lines = []

                for line in lines:
                    if '.chamfer(' in line or '.fillet(' in line:
                        # Comment out the line instead of removing it completely
                        indent_match = re.match(r'(\s*)', line)
                        indent = indent_match.group(1) if indent_match else ''
                        fixed_lines.append(f'{indent}# {line.strip()}  # Removed: no suitable edges')
                        log.info(f"🩹 Commented out chamfer/fillet: {line.strip()}")
                    else:
                        fixed_lines.append(line)

                fixed_code = '\n'.join(fixed_lines)

            # 3d: revolve() with wrong parameter name
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

            # 3d3: radiusArc() with invalid keyword arguments (endX, endY)
            if "radiusArc() got an unexpected keyword argument" in error:
                # radiusArc API: radiusArc((x, y), radius) NOT radiusArc(endX=x, endY=y, radius=r)
                # Pattern: .radiusArc(endX=30, endY=60, radius=22) → .radiusArc((30, 60), 22)
                def fix_radiusArc(match):
                    # Extract the full call
                    full_match = match.group(0)
                    # Try to find endX, endY, radius values
                    endX_match = re.search(r'endX\s*=\s*([^,\)]+)', full_match)
                    endY_match = re.search(r'endY\s*=\s*([^,\)]+)', full_match)
                    radius_match = re.search(r'radius\s*=\s*([^,\)]+)', full_match)

                    if endX_match and endY_match and radius_match:
                        x = endX_match.group(1).strip()
                        y = endY_match.group(1).strip()
                        r = radius_match.group(1).strip()
                        return f'.radiusArc(({x}, {y}), {r})'
                    return full_match

                fixed_code = re.sub(
                    r'\.radiusArc\s*\([^)]+\)',
                    fix_radiusArc,
                    fixed_code
                )
                log.info("🩹 Fixed: Converted radiusArc(endX=, endY=, radius=) to radiusArc((x, y), radius)")

            # 3d4: threePointArc() with invalid keyword arguments
            if "threePointArc() got an unexpected keyword argument" in error:
                # threePointArc API: threePointArc((x1, y1), (x2, y2)) NOT threePointArc(x1=, y1=, x2=, y2=)
                def fix_threePointArc(match):
                    full_match = match.group(0)
                    # Try to find point coordinates
                    x1_match = re.search(r'(?:x1|point1X)\s*=\s*([^,\)]+)', full_match)
                    y1_match = re.search(r'(?:y1|point1Y)\s*=\s*([^,\)]+)', full_match)
                    x2_match = re.search(r'(?:x2|point2X)\s*=\s*([^,\)]+)', full_match)
                    y2_match = re.search(r'(?:y2|point2Y)\s*=\s*([^,\)]+)', full_match)

                    if x1_match and y1_match and x2_match and y2_match:
                        x1 = x1_match.group(1).strip()
                        y1 = y1_match.group(1).strip()
                        x2 = x2_match.group(1).strip()
                        y2 = y2_match.group(1).strip()
                        return f'.threePointArc(({x1}, {y1}), ({x2}, {y2}))'
                    return full_match

                fixed_code = re.sub(
                    r'\.threePointArc\s*\([^)]+\)',
                    fix_threePointArc,
                    fixed_code
                )
                log.info("🩹 Fixed: Converted threePointArc keyword args to positional tuples")

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

            # 3g: BRep_API command not done - CRITICAL for torus revolve and bad revolve profiles
            # This happens when using wrong workplane OR missing clean=False for 360° revolves
            # OR trying to revolve an invalid/non-closed profile
            if "BRep_API: command not done" in error or "brep_api: command not done" in error.lower():
                log.info("🩹 Attempting to fix: BRep_API error (likely missing clean=False or wrong workplane)")

                # Strategy: First copy all lines, then make modifications
                lines = fixed_code.split('\n')
                revolve_found = False

                # Find revolve operations and fix them
                for i, line in enumerate(lines):
                    if '.revolve(' in line:
                        revolve_found = True

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

                        # Fix 3: Detect invalid revolve profile (circle() + lineTo() + close() → this creates TWO wires!)
                        # Look back for pattern: .circle() ... .lineTo() ... .close() ... .revolve()
                        # This is WRONG - revolve needs a SINGLE closed 2D profile
                        if revolve_found:
                            # Check last 10 lines for suspicious pattern
                            profile_section = lines[max(0, i-10):i+1]
                            has_circle = any('.circle(' in l for l in profile_section)
                            has_lineTo = any('.lineTo(' in l for l in profile_section)
                            has_close = any('.close()' in l for l in profile_section)

                            if has_circle and (has_lineTo or has_close):
                                log.warning("🩹 Detected invalid revolve profile: circle() + lineTo()/close() creates multiple wires!")
                                log.warning("   → Suggestion: Use sphere() method instead for bowl shapes")
                                # Can't auto-fix this easily - would need to replace entire shape logic
                                # But we can comment it out and leave a hint
                                pass

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
                minor_r = 8  # default minor radius

                # Try to extract from prompt or error
                import re
                # Try to extract from prompt first
                prompt_lower = context.prompt.lower() if context and context.prompt else ""
                major_match = re.search(r'major[_\s]*radius[:\s]*(\d+)', prompt_lower)
                minor_match = re.search(r'minor[_\s]*radius[:\s]*(\d+)', prompt_lower)
                if not major_match:
                    major_match = re.search(r'major[_\s]*radius[:\s]*(\d+)', error.lower())
                if not minor_match:
                    minor_match = re.search(r'minor[_\s]*radius[:\s]*(\d+)', error.lower())
                if major_match:
                    major_r = int(major_match.group(1))
                if minor_match:
                    minor_r = int(minor_match.group(1))

                # Strategy: Find the variable assignment and replace entire multi-line chain
                lines = fixed_code.split('\n')
                new_lines = []
                replaced = False
                in_chain_to_replace = False
                has_opening_paren = False  # Track if chain has opening paren
                indent = ''
                var_name = 'result'

                for i, line in enumerate(lines):
                    # Look for lines that indicate start of wrong torus code
                    if not replaced and not in_chain_to_replace:
                        # Check if this line starts the wrong pattern
                        if (('= (' in line or '=(' in line) and 'cq.Workplane' in line):
                            # Multi-line chain with opening paren
                            has_opening_paren = True
                            in_chain_to_replace = True
                            var_match = re.match(r'(\s*)(\w+)\s*=', line)
                            if var_match:
                                indent = var_match.group(1)
                                var_name = var_match.group(2)
                            log.info(f"🩹 Found start of wrong torus pattern (multi-line): {line[:60]}...")
                            continue
                        elif ('.sphere(' in line) or \
                             ('.revolve(' in line and '.moveTo(' not in line):
                            # Single-line or simple continuation
                            has_opening_paren = False
                            in_chain_to_replace = True
                            # Extract variable name and indent
                            var_match = re.match(r'(\s*)(\w+)\s*=', line)
                            if var_match:
                                indent = var_match.group(1)
                                var_name = var_match.group(2)
                            else:
                                indent_match = re.match(r'(\s*)', line)
                                indent = indent_match.group(1) if indent_match else ''

                            log.info(f"🩹 Found start of wrong torus pattern (single-line): {line[:60]}...")
                            continue

                    # If we're in a chain to replace, skip lines until we find the end
                    elif in_chain_to_replace:
                        # Check if this line is part of the chain to replace
                        stripped = line.strip()

                        # Skip blank lines and comments while in chain
                        if not stripped or stripped.startswith('#'):
                            log.info(f"🩹 Skipping blank/comment line in chain: {line[:60]}...")
                            continue

                        # If line starts with '.', it's a chained method call
                        if stripped.startswith('.'):
                            # Determine if this is the end based on chain type
                            if has_opening_paren:
                                # Multi-line with opening paren: look for )) to close it
                                is_end = stripped.endswith('))')
                            else:
                                # Single-line or simple chain: any line not starting with . ends it
                                is_end = stripped.endswith(')') and not stripped.endswith('))')

                            if is_end:
                                # This is the last chained call
                                log.info(f"🩹 Found end of chain: {line[:60]}...")
                                new_lines.append(f'{indent}# Torus via revolve (fixed by SelfHealingAgent)')
                                new_lines.append(f'{indent}{var_name} = (cq.Workplane("XY")')
                                new_lines.append(f'{indent}          .moveTo({major_r}, 0).circle({minor_r})')
                                new_lines.append(f'{indent}          .revolve(360, (0,0,0), (0,0,1)))')
                                log.info(f"🩹 Replaced wrong pattern with torus revolve (major={major_r}, minor={minor_r})")
                                replaced = True
                                in_chain_to_replace = False
                                continue
                            else:
                                # Still in the middle of the chain
                                log.info(f"🩹 Skipping chain line: {line[:60]}...")
                                continue
                        else:
                            # Not a chained call, not blank, not comment -> we've left the chain
                            # Insert the fix and keep this line (don't skip it!)
                            log.info(f"🩹 End of chain reached at non-chain line, keeping: {line[:60]}...")
                            new_lines.append(f'{indent}# Torus via revolve (fixed by SelfHealingAgent)')
                            new_lines.append(f'{indent}{var_name} = (cq.Workplane("XY")')
                            new_lines.append(f'{indent}          .moveTo({major_r}, 0).circle({minor_r})')
                            new_lines.append(f'{indent}          .revolve(360, (0,0,0), (0,0,1)))')
                            log.info(f"🩹 Replaced wrong pattern with torus revolve (major={major_r}, minor={minor_r})")
                            replaced = True
                            in_chain_to_replace = False
                            # CRITICAL: Keep this line instead of skipping it!
                            new_lines.append(line)
                            continue

                    # Normal line, keep it
                    new_lines.append(line)

                # If we finished the loop but are still in a chain (single-line pattern), insert the fix
                if in_chain_to_replace and not replaced:
                    new_lines.append(f'{indent}# Torus via revolve (fixed by SelfHealingAgent)')
                    new_lines.append(f'{indent}{var_name} = (cq.Workplane("XY")')
                    new_lines.append(f'{indent}          .moveTo({major_r}, 0).circle({minor_r})')
                    new_lines.append(f'{indent}          .revolve(360, (0,0,0), (0,0,1)))')
                    log.info(f"🩹 Replaced wrong pattern with torus revolve (major={major_r}, minor={minor_r})")

                fixed_code = '\n'.join(new_lines)

            # Semantic Fix 0b: Sphere with circle + extrude → sphere
            elif "SEMANTIC ERROR: Prompt asks for SPHERE but code uses .circle(" in error and 'sphere_fix' not in fixes_applied:
                fixes_applied.add('sphere_fix')  # Mark as applied to avoid duplicate
                log.info("🩹 Attempting semantic fix: Replace circle + extrude with sphere()")

                # Extract radius from prompt (handle both radius and diameter)
                import re
                radius = 40  # default radius
                prompt_lower = context.prompt.lower() if context and context.prompt else ""

                # Try to extract diameter first (sphere diameter 80 mm → radius 40)
                diameter_match = re.search(r'diameter[:\s]*(\d+)', prompt_lower)
                if diameter_match:
                    radius = int(diameter_match.group(1)) // 2
                    log.info(f"🩹 Extracted diameter {int(diameter_match.group(1))} → radius {radius}")
                else:
                    # Try radius
                    radius_match = re.search(r'radius[:\s]*(\d+)', prompt_lower)
                    if radius_match:
                        radius = int(radius_match.group(1))
                        log.info(f"🩹 Extracted radius {radius}")

                # Strategy: Replace entire .circle(...).extrude(...) chain with .sphere(radius)
                lines = fixed_code.split('\n')
                new_lines = []
                replaced = False
                in_chain_to_replace = False
                has_opening_paren = False
                indent = ''
                var_name = 'result'

                for i, line in enumerate(lines):
                    # Look for start of wrong sphere code (circle + extrude pattern)
                    if not replaced and not in_chain_to_replace:
                        # Check if this is an assignment with opening paren (multi-line chain)
                        if ('= (' in line or '=(' in line) and 'cq.Workplane' in line:
                            # This is the start of a multi-line chain like: result = (cq.Workplane("XY")
                            var_match = re.match(r'(\s*)(\w+)\s*=', line)
                            if var_match:
                                indent = var_match.group(1)
                                var_name = var_match.group(2)
                            has_opening_paren = True
                            in_chain_to_replace = True
                            log.info(f"🩹 Found start of multi-line sphere pattern: {line[:60]}...")
                            continue
                        # Check if this line has .circle in it (part of the wrong pattern)
                        elif '.circle(' in line:
                            # Check if assignment starts here
                            if '=' in line:
                                var_match = re.match(r'(\s*)(\w+)\s*=', line)
                                if var_match:
                                    indent = var_match.group(1)
                                    var_name = var_match.group(2)
                                in_chain_to_replace = True
                                log.info(f"🩹 Found start of wrong sphere pattern (circle): {line[:60]}...")
                                continue
                            else:
                                # Chained call like .circle(...) without assignment
                                in_chain_to_replace = True
                                indent_match = re.match(r'(\s*)', line)
                                indent = indent_match.group(1) if indent_match else ''
                                log.info(f"🩹 Found chained circle call: {line[:60]}...")
                                continue

                    # If we're in a chain to replace, skip until we find the extrude or end
                    elif in_chain_to_replace:
                        stripped = line.strip()

                        # Skip blank lines and comments
                        if not stripped or stripped.startswith('#'):
                            log.info(f"🩹 Skipping blank/comment line in chain: {line[:60]}...")
                            continue

                        # Check if this line has extrude (the end of the pattern we're replacing)
                        if '.extrude(' in line:
                            # This is the extrude call - replace the whole chain with sphere
                            log.info(f"🩹 Found extrude, replacing chain with sphere: {line[:60]}...")
                            new_lines.append(f'{indent}# Sphere (fixed by SelfHealingAgent)')
                            if has_opening_paren:
                                new_lines.append(f'{indent}{var_name} = cq.Workplane("XY").sphere({radius})')
                            else:
                                new_lines.append(f'{indent}{var_name} = cq.Workplane("XY").sphere({radius})')
                            log.info(f"🩹 Replaced circle + extrude with sphere(radius={radius})")
                            replaced = True
                            in_chain_to_replace = False
                            continue

                        # If line starts with '.', it's a chained call - skip it
                        if stripped.startswith('.'):
                            log.info(f"🩹 Skipping chained call: {line[:60]}...")
                            continue
                        else:
                            # Not a chain anymore, insert fix and keep this line
                            log.info(f"🩹 End of chain reached at non-chain line, keeping: {line[:60]}...")
                            new_lines.append(f'{indent}# Sphere (fixed by SelfHealingAgent)')
                            new_lines.append(f'{indent}{var_name} = cq.Workplane("XY").sphere({radius})')
                            log.info(f"🩹 Replaced circle pattern with sphere(radius={radius})")
                            replaced = True
                            in_chain_to_replace = False
                            # Keep this line
                            new_lines.append(line)
                            continue

                    # Normal line, keep it
                    new_lines.append(line)

                # If we finished but didn't find extrude, still replace
                if in_chain_to_replace and not replaced:
                    new_lines.append(f'{indent}# Sphere (fixed by SelfHealingAgent)')
                    new_lines.append(f'{indent}{var_name} = cq.Workplane("XY").sphere({radius})')
                    log.info(f"🩹 Replaced circle pattern with sphere(radius={radius})")

                fixed_code = '\n'.join(new_lines)

            elif "SEMANTIC ERROR: Prompt asks for ARC" in error and 'arc_sector_fix' not in fixes_applied:
                fixes_applied.add('arc_sector_fix')  # Mark as applied to avoid duplicate
                log.info("🩹 Attempting semantic fix: Replace wrong code with annular sector (portion de couronne)")

                # Extract parameters from prompt/error
                R_ext = 60        # default outer radius
                R_int = 50        # default inner radius (0.83 * outer)
                theta_deg = 210   # default sweep angle
                height = 10       # default extrusion height
                start_deg = 0     # default start angle

                import re
                # Try to extract from prompt first, then error, or use defaults
                prompt_lower = context.prompt.lower() if context and context.prompt else ""

                # Extract radius from prompt or error
                radius_match = re.search(r'radius[:\s]*(\d+)', prompt_lower)
                if not radius_match:
                    radius_match = re.search(r'radius[:\s]*(\d+)', error.lower())
                if radius_match:
                    R_ext = int(radius_match.group(1))
                    R_int = int(R_ext * 0.83)  # Inner radius ~83% of outer

                # Extract angle from prompt or error
                angle_match = re.search(r'(?:sweep|angle)[:\s]*(\d+)', prompt_lower)
                if not angle_match:
                    angle_match = re.search(r'(?:sweep|angle)[:\s]*(\d+)', error.lower())
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

                    # Detect start of wrong shape creation code (any primitive that's not annular sector)
                    # Include threePointArc and radiusArc since those are the problematic arc methods
                    if not replaced and ('.circle(' in line or '.extrude(' in line or 'revolve' in line or '.sweep(' in line or '.box(' in line or '.sphere(' in line or '.cylinder(' in line or '.threePointArc(' in line or '.radiusArc(' in line):
                        # Check if previous line(s) are part of multi-line chained statement
                        # (e.g., "result = (cq.Workplane("XY")" before ".box(50, 50, 50))")
                        # If so, remove them to avoid unclosed parenthesis
                        removed_chain_start = False
                        while new_lines:
                            last_line = new_lines[-1].strip()
                            # Check if last line is part of a chained statement:
                            # - Contains "= (" (assignment with opening paren for multi-line)
                            # - Contains "cq.Workplane" (start of CadQuery chain)
                            # - Ends with just "(" (opening paren)
                            # - Is indented and starts with "." (continuation of chain)
                            if ('= (' in last_line and 'cq.Workplane' in last_line) or \
                               last_line.endswith('(') or \
                               (last_line.startswith('.') and len(new_lines[-1]) - len(new_lines[-1].lstrip()) > 0):
                                log.info(f"🩹 Removing chained statement line: {new_lines[-1][:60]}...")
                                # If this line has the variable assignment, save its indent
                                if '=' in new_lines[-1] and not removed_chain_start:
                                    indent_match = re.match(r'(\s*)', new_lines[-1])
                                    indent = indent_match.group(1) if indent_match else ''
                                    removed_chain_start = True
                                new_lines.pop()
                            else:
                                break  # Stop when we find a line that's not part of the chain

                        # If we didn't remove a chain start, use current line's indent
                        if not removed_chain_start:
                            indent_match = re.match(r'(\s*)', line)
                            indent = indent_match.group(1) if indent_match else ''

                        # Insert correct annular sector code (using user's robust approach)
                        new_lines.append(f'{indent}# Arc annulaire (annular sector) - fixed by SelfHealingAgent')
                        new_lines.append(f'{indent}import math')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}R_OUT = {R_ext}')
                        new_lines.append(f'{indent}ANGLE = {theta_deg}')
                        new_lines.append(f'{indent}WIDTH = {R_ext - R_int}')
                        new_lines.append(f'{indent}THICK = {height}')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}R_IN = R_OUT - WIDTH')
                        new_lines.append(f'{indent}a1, a2 = -ANGLE/2.0, ANGLE/2.0')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}def V(r, deg):')
                        new_lines.append(f'{indent}    t = math.radians(deg)')
                        new_lines.append(f'{indent}    return cq.Vector(r*math.cos(t), r*math.sin(t), 0)')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}# Secteur extérieur (wire fermé)')
                        new_lines.append(f'{indent}outer_arc = cq.Edge.makeCircle(R_OUT, cq.Vector(), cq.Vector(0,0,1), a1, a2)')
                        new_lines.append(f'{indent}r1o = cq.Edge.makeLine(V(R_OUT, a2), cq.Vector(0,0,0))')
                        new_lines.append(f'{indent}r2o = cq.Edge.makeLine(cq.Vector(0,0,0), V(R_OUT, a1))')
                        new_lines.append(f'{indent}outer_wire = cq.Wire.assembleEdges([outer_arc, r1o, r2o])')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}# Secteur intérieur (wire fermé)')
                        new_lines.append(f'{indent}inner_arc = cq.Edge.makeCircle(R_IN, cq.Vector(), cq.Vector(0,0,1), a1, a2)')
                        new_lines.append(f'{indent}r1i = cq.Edge.makeLine(V(R_IN, a2), cq.Vector(0,0,0))')
                        new_lines.append(f'{indent}r2i = cq.Edge.makeLine(cq.Vector(0,0,0), V(R_IN, a1))')
                        new_lines.append(f'{indent}inner_wire = cq.Wire.assembleEdges([inner_arc, r1i, r2i])')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}# Extrusions séparées + soustraction')
                        new_lines.append(f'{indent}outer_solid = cq.Workplane("XY").add(outer_wire).toPending().extrude(THICK)')
                        new_lines.append(f'{indent}inner_solid = cq.Workplane("XY").add(inner_wire).toPending().extrude(THICK)')
                        new_lines.append(f'{indent}{result_var} = outer_solid.cut(inner_solid)')
                        new_lines.append(f'{indent}')
                        log.info(f"🩹 Replaced wrong code with annular sector (R_ext={R_ext}, R_int={R_int}, angle={theta_deg}°)")
                        replaced = True
                        skip_wrong_code = True
                        continue

                    # Add line if we're not skipping
                    new_lines.append(line)
                fixed_code = '\n'.join(new_lines)

            elif "SEMANTIC ERROR: Prompt asks for CONE but code uses" in error:
                log.info("🩹 Attempting semantic fix: Replace cylinder/wrong pattern with cone extrude+taper")

                # Extract parameters from prompt first, then error
                prompt_lower = context.prompt.lower() if context and context.prompt else ""
                base_radius = 25  # default
                height = 60  # default

                import re
                # Try prompt first
                base_match = re.search(r'(?:base|bottom)[_\s]*(?:diameter|radius)[:\s]*(\d+)', prompt_lower)
                height_match = re.search(r'height[:\s]*(\d+)', prompt_lower)
                # Fallback to error
                if not base_match:
                    base_match = re.search(r'(?:base|bottom)[_\s]*(?:diameter|radius)[:\s]*(\d+)', error.lower())
                if not height_match:
                    height_match = re.search(r'height[:\s]*(\d+)', error.lower())

                if base_match:
                    base_radius = int(base_match.group(1)) / 2  # diameter to radius
                if height_match:
                    height = int(height_match.group(1))

                # Strategy: Use state machine like torus healer
                lines = fixed_code.split('\n')
                new_lines = []
                replaced = False
                in_chain_to_replace = False
                indent = ''
                result_var = 'result'

                for i, line in enumerate(lines):
                    # Look for lines that indicate start of wrong cone code
                    if not replaced and not in_chain_to_replace:
                        # Check if this line starts a cylinder pattern (circle + extrude without taper)
                        # or if it contains .circle( or .revolve( or .extrude( or .cylinder(
                        if 'loft' not in fixed_code:  # Only replace if no loft exists
                            if (('= (' in line or '=(' in line) and 'cq.Workplane' in line) or \
                               ('.circle(' in line and 'taper' not in fixed_code) or \
                               ('.revolve(' in line) or \
                               ('.cylinder(' in line):

                                # Extract variable name and indent
                                var_match = re.match(r'(\s*)(\w+)\s*=', line)
                                if var_match:
                                    indent = var_match.group(1)
                                    result_var = var_match.group(2)
                                else:
                                    indent_match = re.match(r'(\s*)', line)
                                    indent = indent_match.group(1) if indent_match else ''

                                # Mark that we're in a chain to replace
                                in_chain_to_replace = True
                                log.info(f"🩹 Found start of wrong cone pattern: {line[:60]}...")
                                continue

                    # If we're in a chain to replace, skip lines until we find the end
                    elif in_chain_to_replace:
                        # Check if this line ends the chain
                        stripped = line.strip()
                        if stripped.endswith('))') or (stripped.endswith(')') and not stripped.startswith('.')):
                            # Found the end, insert correct code
                            log.info(f"🩹 Found end of chain: {line[:60]}...")

                            # Calculate taper angle: taper_deg = -atan2(radius, height) converted to degrees
                            import math
                            taper_deg = -math.degrees(math.atan2(base_radius, height))

                            new_lines.append(f'{indent}# Cone via extrude with taper (fixed by SelfHealingAgent)')
                            new_lines.append(f'{indent}import math')
                            new_lines.append(f'{indent}taper_deg = -math.degrees(math.atan2({base_radius}, {height}))')
                            new_lines.append(f'{indent}{result_var} = (cq.Workplane("XY")')
                            new_lines.append(f'{indent}          .circle({base_radius})')
                            new_lines.append(f'{indent}          .extrude({height}, taper=taper_deg))')
                            log.info(f"🩹 Replaced wrong pattern with cone extrude+taper (base_r={base_radius}, h={height})")
                            replaced = True
                            in_chain_to_replace = False
                            continue
                        else:
                            # Still in the chain, skip this line
                            log.info(f"🩹 Skipping chain line: {line[:60]}...")
                            continue

                    # Normal line, keep it
                    new_lines.append(line)

                # If we finished the loop but are still in a chain (single-line pattern), insert the fix
                if in_chain_to_replace and not replaced:
                    import math
                    taper_deg = -math.degrees(math.atan2(base_radius, height))

                    new_lines.append(f'{indent}# Cone via extrude with taper (fixed by SelfHealingAgent)')
                    new_lines.append(f'{indent}import math')
                    new_lines.append(f'{indent}taper_deg = -math.degrees(math.atan2({base_radius}, {height}))')
                    new_lines.append(f'{indent}{result_var} = (cq.Workplane("XY")')
                    new_lines.append(f'{indent}          .circle({base_radius})')
                    new_lines.append(f'{indent}          .extrude({height}, taper=taper_deg))')
                    log.info(f"🩹 Replaced wrong pattern with cone extrude+taper (base_r={base_radius}, h={height})")

                fixed_code = '\n'.join(new_lines)

            elif "SEMANTIC ERROR: Prompt asks for CYLINDER but code uses" in error:
                log.info("🩹 Attempting semantic fix: Replace .box() with .circle().extrude() for cylinder")

                # Extract parameters from error or prompt
                radius = 35  # default
                height = 100  # default

                import re
                radius_match = re.search(r'radius[:\s]*(\d+)', error.lower())
                height_match = re.search(r'(?:height|length)[:\s]*(\d+)', error.lower())
                if radius_match:
                    radius = int(radius_match.group(1))
                if height_match:
                    height = int(height_match.group(1))

                # Replace .box() with circle().extrude()
                lines = fixed_code.split('\n')
                new_lines = []
                replaced = False

                for line in lines:
                    # Detect .box() call and replace with circle().extrude()
                    if '.box(' in line and not replaced:
                        # Extract variable name if exists
                        var_match = re.match(r'(\s*)(\w+)\s*=\s*', line)
                        if var_match:
                            indent = var_match.group(1)
                            var_name = var_match.group(2)
                            new_lines.append(f'{indent}# Cylinder via circle + extrude (fixed by SelfHealingAgent)')
                            new_lines.append(f'{indent}{var_name} = cq.Workplane("XY").circle({radius}).extrude({height})')
                            log.info(f"🩹 Replaced .box() with circle({radius}).extrude({height})")
                            replaced = True
                        else:
                            # No assignment, replace in-place
                            indent_match = re.match(r'(\s*)', line)
                            indent = indent_match.group(1) if indent_match else ''
                            # Try to find the whole chain
                            if 'cq.Workplane' in line:
                                new_lines.append(f'{indent}# Cylinder via circle + extrude (fixed by SelfHealingAgent)')
                                new_lines.append(f'{indent}result = cq.Workplane("XY").circle({radius}).extrude({height})')
                                log.info(f"🩹 Replaced .box() with circle({radius}).extrude({height})")
                                replaced = True
                            else:
                                new_lines.append(line)
                    else:
                        new_lines.append(line)

                fixed_code = '\n'.join(new_lines)

            elif "SEMANTIC ERROR: Prompt asks for RING" in error or "SEMANTIC ERROR: Prompt asks for WASHER" in error or "SEMANTIC ERROR: Prompt asks for ANNULUS" in error:
                log.info("🩹 Attempting semantic fix: Generate ring/washer (annulus) pattern")

                # Extract parameters from prompt first, then error
                prompt_lower = context.prompt.lower() if context and context.prompt else ""
                r_outer = 60  # default outer radius
                r_inner = 30  # default inner radius
                thickness = 10  # default thickness

                import re
                # Try to extract outer diameter/radius
                outer_match = re.search(r'outer[_\s]*(?:diameter|radius)[:\s]*(\d+)', prompt_lower)
                if not outer_match:
                    outer_match = re.search(r'outer[_\s]*(?:diameter|radius)[:\s]*(\d+)', error.lower())
                if outer_match:
                    r_outer = int(outer_match.group(1)) / 2  # diameter to radius if needed
                    # Check if it's already a radius (usually < 100)
                    if int(outer_match.group(1)) < 100:
                        r_outer = int(outer_match.group(1))

                # Try to extract inner diameter/radius
                inner_match = re.search(r'inner[_\s]*(?:diameter|radius)[:\s]*(\d+)', prompt_lower)
                if not inner_match:
                    inner_match = re.search(r'inner[_\s]*(?:diameter|radius)[:\s]*(\d+)', error.lower())
                if inner_match:
                    r_inner = int(inner_match.group(1)) / 2
                    if int(inner_match.group(1)) < 100:
                        r_inner = int(inner_match.group(1))

                # Try to extract thickness
                thick_match = re.search(r'(?:extrude|thick(?:ness)?)[:\s]*(\d+)', prompt_lower)
                if not thick_match:
                    thick_match = re.search(r'(?:extrude|thick(?:ness)?)[:\s]*(\d+)', error.lower())
                if thick_match:
                    thickness = int(thick_match.group(1))

                # Strategy: Use state machine like torus and cone healers
                lines = fixed_code.split('\n')
                new_lines = []
                result_var = 'result'
                replaced = False
                in_chain_to_replace = False
                indent = ''

                for i, line in enumerate(lines):
                    # Look for lines that indicate start of wrong ring/washer code
                    if not replaced and not in_chain_to_replace:
                        # Check if this line starts wrong pattern (.box or single .circle without second circle)
                        if ('.box(' in line) or \
                           (('= (' in line or '=(' in line) and 'cq.Workplane' in line and '.extrude(' not in fixed_code):

                            # Extract variable name and indent
                            var_match = re.match(r'(\s*)(\w+)\s*=', line)
                            if var_match:
                                indent = var_match.group(1)
                                result_var = var_match.group(2)
                            else:
                                indent_match = re.match(r'(\s*)', line)
                                indent = indent_match.group(1) if indent_match else ''

                            # Mark that we're in a chain to replace
                            in_chain_to_replace = True
                            log.info(f"🩹 Found start of wrong ring/washer pattern: {line[:60]}...")
                            continue

                    # If we're in a chain to replace, skip lines until we find the end
                    elif in_chain_to_replace:
                        # Check if this line ends the chain
                        stripped = line.strip()
                        if stripped.endswith('))') or (stripped.endswith(')') and not stripped.startswith('.')):
                            # Found the end, insert correct code
                            log.info(f"🩹 Found end of chain: {line[:60]}...")
                            new_lines.append(f'{indent}# Ring/Washer (annulus) via two circles + extrude (fixed by SelfHealingAgent)')
                            new_lines.append(f'{indent}{result_var} = (cq.Workplane("XY")')
                            new_lines.append(f'{indent}          .circle({r_outer}).circle({r_inner})')
                            new_lines.append(f'{indent}          .extrude({thickness}))')
                            log.info(f"🩹 Replaced wrong pattern with ring/washer (R_out={r_outer}, R_in={r_inner}, thick={thickness})")
                            replaced = True
                            in_chain_to_replace = False
                            continue
                        else:
                            # Still in the chain, skip this line
                            log.info(f"🩹 Skipping chain line: {line[:60]}...")
                            continue

                    # Normal line, keep it
                    new_lines.append(line)

                # If we finished the loop but are still in a chain (single-line pattern), insert the fix
                if in_chain_to_replace and not replaced:
                    new_lines.append(f'{indent}# Ring/Washer (annulus) via two circles + extrude (fixed by SelfHealingAgent)')
                    new_lines.append(f'{indent}{result_var} = (cq.Workplane("XY")')
                    new_lines.append(f'{indent}          .circle({r_outer}).circle({r_inner})')
                    new_lines.append(f'{indent}          .extrude({thickness}))')
                    log.info(f"🩹 Replaced wrong pattern with ring/washer (R_out={r_outer}, R_in={r_inner}, thick={thickness})")

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

            # Semantic Fix 3b: Invalid revolve pattern (circle + moveTo + arc + revolve)
            if "Cannot use revolve() after circle() + moveTo()" in error and 'vase_loft_fix' not in fixes_applied:
                fixes_applied.add('vase_loft_fix')  # Mark as applied to avoid duplicate
                log.info("🩹 Attempting semantic fix: Replace invalid revolve with loft pattern")

                # Replace the invalid revolve pattern with valid LOFT code
                # Extract parameters from the PROMPT (more reliable than code)
                import re

                radii = []
                heights = []

                # Extract from prompt: "radius 30 mm at base, 22 mm at mid-height 60 mm, and 35 mm at top 120 mm"
                # Pattern 1: "radius X mm at base" or "radius X mm at height Y"
                radius_patterns = re.findall(r'radius\s+(\d+(?:\.\d+)?)\s*mm(?:\s+at\s+(?:base|mid-height|height|top)\s+)?(\d+(?:\.\d+)?)?', prompt, re.IGNORECASE)

                if radius_patterns:
                    for r_match in radius_patterns:
                        radius_val = float(r_match[0])
                        height_val = float(r_match[1]) if r_match[1] else (0 if len(radii) == 0 else heights[-1] + 60)
                        radii.append(radius_val)
                        heights.append(height_val)

                # Pattern 2: Try "base radius X, mid radius Y at Z, top radius W at H"
                if not radii:
                    # Alternative: extract all numbers after "radius"
                    all_radii = re.findall(r'radius[:\s]+(\d+(?:\.\d+)?)', prompt, re.IGNORECASE)
                    all_heights = re.findall(r'(?:height|mid-height|top)[:\s]+(\d+(?:\.\d+)?)', prompt, re.IGNORECASE)

                    if all_radii:
                        radii = [float(r) for r in all_radii[:3]]
                    if all_heights:
                        heights = [0] + [float(h) for h in all_heights[:2]]

                # Fallback defaults if extraction fails
                if len(radii) < 3:
                    radii = [30, 22, 35]  # From the vase prompt
                if len(heights) < 3:
                    heights = [0, 60, 120]  # From the vase prompt

                # Ensure heights are cumulative
                if len(heights) == 3 and heights[0] == 0:
                    # If heights are absolute, keep them; otherwise make cumulative
                    pass
                else:
                    heights = [0, 60, 120]  # Safe defaults

                # Find the result assignment and everything up to revolve
                # Strategy: Detect 'result =' then skip all lines until '.revolve(' and replace with LOFT
                lines = fixed_code.split('\n')
                new_lines = []
                skip_until_revolve = False
                replaced = False

                for i, line in enumerate(lines):
                    # Detect start of shape creation (first 'result =' that's not a reassignment)
                    if 'result =' in line and not replaced and 'result.faces' not in line and 'result.edges' not in line:
                        skip_until_revolve = True
                        indent_match = re.match(r'(\s*)', line)
                        indent = indent_match.group(1) if indent_match else ''

                        # Generate correct LOFT code
                        new_lines.append(f'{indent}# Vase with varying radii - using LOFT (fixed from invalid revolve)')
                        new_lines.append(f'{indent}outer = (cq.Workplane("XY")')
                        new_lines.append(f'{indent}    .circle({radii[0]})')
                        new_lines.append(f'{indent}    .workplane(offset={heights[1]})')
                        new_lines.append(f'{indent}    .circle({radii[1]})')
                        new_lines.append(f'{indent}    .workplane(offset={heights[2] - heights[1]})')
                        new_lines.append(f'{indent}    .circle({radii[2]})')
                        new_lines.append(f'{indent}    .loft())')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}# Shell 3mm wall - hollows the entire vase')
                        new_lines.append(f'{indent}result = outer.shell(-3)')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}# Open the top by cutting through the top face')
                        new_lines.append(f'{indent}result = result.faces(">Z").workplane().circle({radii[2] + 5}).cutBlind(-5)')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}# Add solid bottom 3mm')
                        new_lines.append(f'{indent}result = result.faces("<Z").workplane().circle({radii[0] - 3}).extrude(3)')
                        new_lines.append(f'{indent}')
                        replaced = True
                        continue  # Skip the 'result =' line

                    # Skip all lines until we find revolve
                    if skip_until_revolve:
                        if '.revolve(' in line or 'revolve(' in line:
                            # Found revolve, stop skipping
                            skip_until_revolve = False
                            continue  # Skip the revolve line itself
                        else:
                            # Skip intermediate shape creation lines (circle, moveTo, arc, close, etc.)
                            continue

                    # Keep all other lines (export, comments, etc.)
                    new_lines.append(line)

                fixed_code = '\n'.join(new_lines)
                log.info(f"🩹 Replaced invalid revolve pattern with LOFT: radii={radii}, heights={heights}")


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
                                # Add shell to the chain - shell() without face selection hollows the entire object
                                indent_match = re.match(r'(\s*)', lines[i])
                                next_indent = indent_match.group(1) + '    ' if indent_match else '    '
                                lines.insert(i + 1, f'{next_indent}.shell(-3))  # 3mm wall thickness - hollows entire object')
                                log.info("🩹 Added .shell() for hollow bowl/vase")
                                break

                    fixed_code = '\n'.join(lines)

            # Semantic Fix 5: Bowl with revolve → sphere + shell
            if "SEMANTIC ERROR: Prompt asks for SPHERE but code uses revolve" in error and 'bowl_sphere_fix' not in fixes_applied:
                fixes_applied.add('bowl_sphere_fix')  # Mark as applied to avoid duplicate
                log.info("🩹 Attempting semantic fix: Replace revolve with sphere() + shell() for bowl")

                # Extract radius from prompt (search for "radius 40 mm" pattern)
                import re
                radius = 40
                # Try to extract from prompt first (more reliable than error message)
                # Pattern: "radius 40 mm" or "semicircle radius 40"
                for err_line in [error] + context.errors if hasattr(context, 'errors') else [error]:
                    radius_match = re.search(r'(?:radius|diameter)\s+(\d+)\s*mm', str(err_line), re.IGNORECASE)
                    if radius_match:
                        radius = int(radius_match.group(1))
                        break

                # Replace revolve pattern with sphere + split + shell
                # Strategy: Detect first 'result =' (like vase/spring) then skip all until export
                lines = fixed_code.split('\n')
                new_lines = []
                skip_until_export = False
                replaced = False

                for line in lines:
                    # Detect START of shape creation (first 'result =')
                    if 'result =' in line and not replaced and 'result.faces' not in line and 'result.edges' not in line:
                        skip_until_export = True
                        indent_match = re.match(r'(\s*)', line)
                        indent = indent_match.group(1) if indent_match else ''

                        # Generate hemisphere bowl code
                        new_lines.append(f'{indent}# Hemispherical bowl (fixed from revolve pattern)')
                        new_lines.append(f'{indent}# Create full sphere')
                        new_lines.append(f'{indent}bowl = cq.Workplane("XY").sphere({radius})')
                        new_lines.append(f'{indent}# Cut away top half - box centered at z=radius to cut above z=0')
                        new_lines.append(f'{indent}cutter = cq.Workplane("XY").workplane(offset={radius}).box({radius*3}, {radius*3}, {radius*2}, centered=True)')
                        new_lines.append(f'{indent}bowl = bowl.cut(cutter)')
                        new_lines.append(f'{indent}# Shell 3mm wall thickness - select top face to create opening')
                        new_lines.append(f'{indent}result = bowl.faces(">Z").shell(-3)')
                        new_lines.append(f'{indent}')
                        log.info(f"🩹 Replaced revolve with hemisphere bowl (radius={radius})")
                        replaced = True
                        continue  # Skip the 'result =' line

                    # Skip ALL lines until we hit export/output section
                    if skip_until_export:
                        if 'export' in line.lower() or 'Path' in line or 'output' in line:
                            skip_until_export = False
                            new_lines.append(line)
                        else:
                            # Skip all shape creation lines
                            continue
                    else:
                        new_lines.append(line)

                fixed_code = '\n'.join(new_lines)

            # Semantic Fix 5.5: Spring circle positioning (quick fix before full replacement)
            if "Circle must be positioned at helix start" in error and 'spring_center_fix' not in fixes_applied:
                fixes_applied.add('spring_center_fix')  # Mark as applied to avoid duplicate
                log.info("🩹 Attempting semantic fix: Add .center() for spring circle positioning")

                # Extract radius from makeHelix in code or error message
                import re
                radius_match = re.search(r'makeHelix\s*\([^)]*radius\s*=\s*(\d+(?:\.\d+)?)', fixed_code)
                if radius_match:
                    radius = radius_match.group(1)
                else:
                    # Try to extract from error message
                    radius_match = re.search(r'center\((\d+(?:\.\d+)?),\s*0\)', error)
                    radius = radius_match.group(1) if radius_match else '20'

                # Find the line with .circle() before .sweep() and add .center()
                lines = fixed_code.split('\n')
                for i, line in enumerate(lines):
                    if '.circle(' in line and '.sweep(' in line and '.center(' not in line and '.moveTo(' not in line:
                        # Add .center() before .circle()
                        # Pattern: Workplane("XY").circle(1.5).sweep(...)
                        # Replace with: Workplane("XY").center(20, 0).circle(1.5).sweep(...)
                        fixed_line = line.replace('.circle(', f'.center({radius}, 0).circle(')
                        lines[i] = fixed_line
                        log.info(f"🩹 Added .center({radius}, 0) before .circle() for spring")
                        break

                fixed_code = '\n'.join(lines)

            # Semantic Fix 5.7: Glass hollow - replace extrude(-) with cutBlind(-) OR generate proper glass code
            # Trigger conditions:
            # 1. Error contains "cutBlind" and "extrude(-depth)" -> replace extrude with cutBlind
            # 2. Error contains "Glass must be hollow" -> generate proper glass code
            if (("cutBlind" in error and "extrude(-depth)" in error) or ("Glass must be hollow" in error and "glass" in prompt.lower())) and 'glass_cutblind_fix' not in fixes_applied:
                fixes_applied.add('glass_cutblind_fix')  # Mark as applied to avoid duplicate
                log.info("🩹 Attempting semantic fix: Generate proper glass code with .cutBlind()")

                # Check if code uses chained syntax (which might not work with cutBlind)
                # If so, convert to split syntax like user's working code
                import re

                # Try to detect chained glass pattern
                # Look for: result = (cq.Workplane... with multiple method calls in parentheses
                code_single_line = fixed_code.replace('\n', ' ')
                is_chained = (
                    'result = (cq.Workplane' in code_single_line and
                    '.faces(">Z")' in code_single_line and
                    '.workplane()' in code_single_line and
                    ('.cutBlind(-' in code_single_line or '.extrude(-' in code_single_line)
                )

                # Check if hollow cut is completely missing
                has_hollow_cut = '.cutBlind(' in fixed_code or ('.faces(">Z")' in fixed_code and '.workplane()' in fixed_code)

                if is_chained or not has_hollow_cut:
                    log.info("🩹 Detected chained glass syntax - converting to split syntax")

                    # Extract parameters from prompt
                    r_out = 35.0
                    r_in = 32.5
                    height = 100.0
                    bottom = 8.0
                    fillet_r = 1.0

                    # Extract from prompt: "outer cylinder radius 35 mm height 100 mm"
                    outer_r_match = re.search(r'outer\s+cylinder\s+radius\s+(\d+(?:\.\d+)?)\s*mm', prompt, re.IGNORECASE)
                    inner_r_match = re.search(r'inner\s+cylinder\s+radius\s+(\d+(?:\.\d+)?)\s*mm', prompt, re.IGNORECASE)
                    height_match = re.search(r'height\s+(\d+(?:\.\d+)?)\s*mm', prompt, re.IGNORECASE)
                    bottom_match = re.search(r'(\d+(?:\.\d+)?)\s*mm\s+(?:solid\s+)?bottom', prompt, re.IGNORECASE)
                    fillet_match = re.search(r'fillet.*?(\d+(?:\.\d+)?)\s*mm', prompt, re.IGNORECASE)

                    if outer_r_match:
                        r_out = float(outer_r_match.group(1))
                    if inner_r_match:
                        r_in = float(inner_r_match.group(1))
                    if height_match:
                        height = float(height_match.group(1))
                    if bottom_match:
                        bottom = float(bottom_match.group(1))
                    if fillet_match:
                        fillet_r = float(fillet_match.group(1))

                    # Generate glass code with split syntax (like user's working code)
                    lines = fixed_code.split('\n')
                    new_lines = []
                    skip_until_export = False
                    replaced = False

                    for line in lines:
                        # Find first 'result =' line
                        if 'result =' in line and not replaced and 'result.faces' not in line and 'result.edges' not in line:
                            skip_until_export = True
                            indent_match = re.match(r'(\s*)', line)
                            indent = indent_match.group(1) if indent_match else ''

                            # Generate glass code with split syntax
                            new_lines.append(f'{indent}# Drinking glass (fixed from chained syntax)')
                            new_lines.append(f'{indent}# Outer cylinder')
                            new_lines.append(f'{indent}result = cq.Workplane("XY").circle({r_out}).extrude({height})')
                            new_lines.append(f'{indent}')
                            new_lines.append(f'{indent}# Hollow interior, leaving {bottom}mm solid bottom')
                            new_lines.append(f'{indent}result = result.faces(">Z").workplane().circle({r_in}).cutBlind(-({height} - {bottom}))')
                            new_lines.append(f'{indent}')
                            new_lines.append(f'{indent}# Fillet rim edges')
                            new_lines.append(f'{indent}result = result.edges(">Z").fillet({fillet_r})')
                            new_lines.append(f'{indent}')
                            log.info(f"🩹 Generated glass: R_out={r_out}, R_in={r_in}, H={height}, bottom={bottom}")
                            replaced = True
                            continue

                        # Skip all lines until export section
                        if skip_until_export:
                            if 'export' in line.lower() or 'Path' in line or 'output' in line:
                                skip_until_export = False
                                new_lines.append(line)
                            else:
                                continue
                        else:
                            new_lines.append(line)

                    fixed_code = '\n'.join(new_lines)
                else:
                    # Simple replacement for non-chained syntax
                    lines = fixed_code.split('\n')
                    for i, line in enumerate(lines):
                        if '.extrude(-' in line and ('.workplane()' in fixed_code or i > 0):
                            # Check if this is part of a hollow cut pattern
                            prev_lines = '\n'.join(lines[max(0, i-5):i])
                            if 'faces(' in prev_lines or '.workplane()' in prev_lines:
                                lines[i] = line.replace('.extrude(-', '.cutBlind(-')
                                log.info(f"🩹 Replaced .extrude(- with .cutBlind(- on line {i+1}")

                    fixed_code = '\n'.join(lines)

            # Semantic Fix 6: Spring needs Wire.makeHelix + sweep
            # Note: removed "extrude" from condition as it's too generic and conflicts with glass hollow fix
            if "SEMANTIC ERROR" in error and ("spring" in error.lower() or "helix" in error.lower() or "sweep" in error.lower() or "turns" in error.lower() or "pitch" in error.lower() or "coil" in error.lower()) and 'spring_helix_fix' not in fixes_applied:
                fixes_applied.add('spring_helix_fix')  # Mark as applied to avoid duplicate
                log.info("🩹 Attempting semantic fix: Generate Wire.makeHelix + sweep for spring")

                # Extract parameters from PROMPT (more reliable than error)
                pitch = 8
                height = 80
                major_radius = 20
                wire_radius = 1.5

                import re
                # Extract from prompt: "pitch 8 mm", "height 80 mm", "major radius 20 mm", "circle radius 1.5 mm"
                pitch_match = re.search(r'pitch[:\s]+(\d+(?:\.\d+)?)\s*mm', prompt, re.IGNORECASE)
                height_match = re.search(r'(?:total\s+)?height[:\s]+(\d+(?:\.\d+)?)\s*mm', prompt, re.IGNORECASE)
                major_match = re.search(r'(?:major|coil)[_\s]+radius[:\s]+(\d+(?:\.\d+)?)\s*mm', prompt, re.IGNORECASE)
                # Wire radius can be "circle radius X" or "radius X" (first occurrence)
                wire_match = re.search(r'(?:circle|wire|minor)[_\s]+radius[:\s]+(\d+(?:\.\d+)?)\s*mm', prompt, re.IGNORECASE)

                if pitch_match:
                    pitch = float(pitch_match.group(1))
                if height_match:
                    height = float(height_match.group(1))
                if major_match:
                    major_radius = float(major_match.group(1))
                if wire_match:
                    wire_radius = float(wire_match.group(1))

                # Validate parameters to ensure visible spring
                if pitch <= 0:
                    pitch = 8
                    log.warning(f"⚠️ Invalid pitch (<= 0), using default: {pitch}")
                if height <= pitch * 2:
                    height = max(pitch * 10, 80)  # At least 10 turns
                    log.warning(f"⚠️ Height too small for spring, adjusted to: {height} (for ~{height/pitch:.1f} turns)")
                if major_radius <= 0:
                    major_radius = 20
                    log.warning(f"⚠️ Invalid major radius, using default: {major_radius}")
                if wire_radius <= 0:
                    wire_radius = 1.5
                    log.warning(f"⚠️ Invalid wire radius, using default: {wire_radius}")

                # Replace entire shape generation with correct spring code
                # Strategy: Find first 'result =' then skip until export section
                lines = fixed_code.split('\n')
                new_lines = []
                skip_until_export = False
                replaced = False

                for line in lines:
                    # Detect start of shape creation (first 'result =')
                    if 'result =' in line and not replaced and 'result.faces' not in line and 'result.edges' not in line:
                        skip_until_export = True
                        indent_match = re.match(r'(\s*)', line)
                        indent = indent_match.group(1) if indent_match else ''

                        # Insert correct spring code
                        new_lines.append(f'{indent}# Helical spring using Wire.makeHelix + sweep')
                        new_lines.append(f'{indent}# Add margin for clean trimming')
                        new_lines.append(f'{indent}margin = {wire_radius * 2}')
                        new_lines.append(f'{indent}path_height = {height} + 2 * margin')
                        new_lines.append(f'{indent}path = cq.Wire.makeHelix(pitch={pitch}, height=path_height, radius={major_radius}, lefthand=False)')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}# Position circle at helix start point ({major_radius}, 0, 0)')
                        new_lines.append(f'{indent}spring = cq.Workplane("XY").center({major_radius}, 0).circle({wire_radius}).sweep(path, isFrenet=True)')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}# Trim both ends flat using split()')
                        new_lines.append(f'{indent}z0 = margin')
                        new_lines.append(f'{indent}z1 = margin + {height}')
                        new_lines.append(f'{indent}spring = spring.workplane(offset=z0).split(keepTop=True, keepBottom=False)')
                        new_lines.append(f'{indent}spring = spring.workplane(offset=z1).split(keepTop=False, keepBottom=True)')
                        new_lines.append(f'{indent}')
                        new_lines.append(f'{indent}result = spring')
                        new_lines.append(f'{indent}')
                        log.info(f"🩹 Generated spring: pitch={pitch}, height={height}, R={major_radius}, r={wire_radius}")
                        replaced = True
                        continue  # Skip the 'result =' line

                    # Skip all lines until we hit export/output section
                    if skip_until_export:
                        if 'export' in line.lower() or 'Path' in line or 'output' in line or line.strip().startswith('#'):
                            skip_until_export = False
                            new_lines.append(line)
                        else:
                            # Skip shape creation lines
                            continue
                    else:
                        new_lines.append(line)

                fixed_code = '\n'.join(new_lines)

        # Call proactive cleanup at the end
        fixed_code = self._remove_hallucinated_imports(fixed_code)

        return fixed_code

    def _remove_hallucinated_imports(self, code: str) -> str:
        """
        PROACTIVE FIX: Always remove hallucinated imports
        This method is called:
        1. In _basic_fixes() after healing
        2. In execute_workflow() BEFORE execution (even if Critic says OK)

        This ensures ALL code is cleaned before execution, not just code that had errors.
        """
        hallucinated_modules = ['Helpers', 'cadquery.helpers', 'cq_helpers', 'utils', 'cad_utils',
                                'geometry_utils', 'shape_utils', 'cq_utils']

        lines = code.split('\n')
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
            code = '\n'.join(fixed_lines)
            log.info("✅ Proactive hallucinated import cleanup completed")

        return code

    async def _llm_heal_code(self, code: str, errors: List[str]) -> str:
        """
        Utilise le LLM pour corriger le code avec prompt anti-hallucination strict
        """

        errors_text = "\n".join([f"- {e}" for e in errors[:3]])  # Max 3 erreurs

        prompt = f"""You are a CadQuery code debugger. Fix the following CadQuery Python code errors.

**CRITICAL RULES - NEVER VIOLATE:**

1. **NO HALLUCINATED IMPORTS** - ONLY use these imports:
   ✅ ALLOWED: import cadquery as cq, import math, from pathlib import Path
   ❌ FORBIDDEN: Helpers, cadquery.helpers, cq_helpers, utils, geometry_utils, shape_utils

2. **NO HALLUCINATED METHODS** - Workplane does NOT have these methods:
   ❌ .torus(), .cylinder(), .unionAllParts(), .regularPolygon(), .Helix()
   ❌ .workplaneFromPlane(), .createHelix(), .sweepAlongPath()
   ✅ USE: .circle(), .extrude(), .revolve(), .loft(), .sphere(), .box(), .combine()

3. **FIX THE ERROR, NOT REWRITE** - Only change the lines causing errors
   - Keep existing variable names
   - Keep existing structure
   - Do NOT add unnecessary code

4. **COMMON FIXES:**

   - "Can not return Nth element of empty list" → `.faces()` selector wrong
     FIX: Remove selector or use .faces(">Z") / .faces("<Z")

   - "No pending wires present" → Wrong plane for revolve
     FIX: Use cq.Workplane("XZ") for vertical revolve, "XY" for horizontal

   - ".multiply() got Vector instead of float" → Wrong argument type
     FIX: Use offset=5.0 (float), not offset=Vector(0,0,5)

   - "There are no suitable edges for chamfer" → Edges don't exist
     FIX: Comment out .chamfer() or .fillet() line

   - "local variable referenced before assignment" → Bad Vector() usage
     FIX: Use tuple (x, y, z) instead of complex Vector expressions

**Errors to fix:**
{errors_text}

**Code to fix:**
```python
{code[:1500]}
```

**Your task:** Return ONLY the corrected Python code in ```python``` block. NO explanations. NO comments about changes. Just the fixed code."""

        try:
            # Augmenté à 2048 tokens pour permettre code complet
            response = await self.llm.generate(prompt, max_tokens=2048, temperature=0.1)

            # Extraction améliorée du code avec plusieurs stratégies
            healed_code = None

            # Stratégie 1: Chercher ```python ... ```
            code_match = re.search(r"```python\s*(.*?)\s*```", response, re.DOTALL)
            if code_match:
                healed_code = code_match.group(1).strip()

            # Stratégie 2: Chercher juste ``` ... ``` (sans language tag)
            if not healed_code:
                code_match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)
                if code_match:
                    healed_code = code_match.group(1).strip()

            # Stratégie 3: Prendre tout après "import cadquery"
            if not healed_code and 'import cadquery' in response:
                import_idx = response.find('import cadquery')
                healed_code = response[import_idx:].strip()

            # Stratégie 4: Fallback - retourner brut
            if not healed_code:
                healed_code = response.strip()

            # Nettoyer les explications avant/après le code
            lines = healed_code.split('\n')
            code_lines = []
            in_code = False

            for line in lines:
                stripped = line.strip()
                # Détecter début du code (import ou commentaire Python)
                if not in_code and (stripped.startswith('import ') or stripped.startswith('from ') or stripped.startswith('#')):
                    in_code = True

                # Si on est dans le code, ajouter la ligne
                if in_code:
                    # Arrêter si on trouve des explications en texte
                    if stripped and not any(stripped.startswith(x) for x in ['#', 'import', 'from', ' ', '\t']) and '=' not in line and '(' not in line:
                        # Ligne qui ressemble à du texte explicatif, pas du code
                        break
                    code_lines.append(line)

            if code_lines:
                healed_code = '\n'.join(code_lines)

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
    - Mauvaise forme générée (torus vs sphere, cone vs cylinder, etc.)
    """

    def __init__(self):
        # Import critic rules from cot_prompts
        try:
            from cot_prompts import CRITIC_RULES
            self.critic_rules = CRITIC_RULES
        except ImportError:
            log.warning("⚠️ Could not import CRITIC_RULES from cot_prompts")
            self.critic_rules = {}

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

        # Analyse 0b : Vérifications spécifiques par type d'objet
        glass_issue = self._check_glass_pattern(code, prompt)
        if glass_issue:
            issues.append(glass_issue)

        spring_issue = self._check_spring_pattern(code, prompt)
        if spring_issue:
            issues.append(spring_issue)

        vase_issue = self._check_vase_pattern(code, prompt)
        if vase_issue:
            issues.append(vase_issue)

        pipe_issue = self._check_pipe_pattern(code, prompt)
        if pipe_issue:
            issues.append(pipe_issue)

        bowl_issue = self._check_bowl_pattern(code, prompt)
        if bowl_issue:
            issues.append(bowl_issue)

        screw_issue = self._check_screw_pattern(code, prompt)
        if screw_issue:
            issues.append(screw_issue)

        arc_issue = self._check_arc_pattern(code, prompt)
        if arc_issue:
            issues.append(arc_issue)

        # Analyse 1 : Tables avec pieds mal positionnés
        if any(keyword in prompt.lower() for keyword in ["table", "desk", "stand"]):
            leg_issue = self._check_table_legs(code, prompt)
            if leg_issue:
                issues.append(leg_issue)

        # Analyse 2 : Objets creux
        if any(keyword in prompt.lower() for keyword in ["hollow", "creux", "pipe", "tube", "vase", "bowl", "cup", "container", "glass"]):
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

        # Analyse 6 : Vérification des méthodes halluc inées
        hallucination_issue = self._check_hallucinated_methods(code)
        if hallucination_issue:
            issues.append(hallucination_issue)

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
                'required': ['revolve', '.moveTo('],  # Torus = profile.moveTo().circle().revolve()
                'forbidden': ['.sphere(', '.box(', '.cylinder('],
                'error_msg': 'SEMANTIC ERROR: Prompt asks for TORUS but code uses {method}. Use revolve pattern: cq.Workplane("XY").moveTo(major_r, 0).circle(minor_r).revolve(360, (0,0,0), (0,0,1))'
            },
            'cone': {
                'required': [],  # Will check manually for cone (loft OR extrude+taper OR .cone())
                'forbidden': ['.sphere(', '.box(', '.cylinder('],  # .cylinder() is hallucinated method
                'allow_cylinder': False,  # Cone ne doit PAS être un simple cylinder
                'error_msg': 'SEMANTIC ERROR: Prompt asks for CONE but code uses {method}. Use: 1) .cone() method, 2) .extrude(taper=...), or 3) loft pattern'
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
            },
            'ring': {
                'required': ['.circle(', '.extrude('],  # Ring = 2 circles + extrude
                'forbidden': ['.box(', '.sphere(', 'revolve', 'loft'],
                'error_msg': 'SEMANTIC ERROR: Prompt asks for RING/WASHER (annulus) but code uses {method}. Use: cq.Workplane("XY").circle(R_outer).circle(R_inner).extrude(thickness)'
            },
            'washer': {
                'required': ['.circle(', '.extrude('],  # Washer = 2 circles + extrude
                'forbidden': ['.box(', '.sphere(', 'revolve', 'loft'],
                'error_msg': 'SEMANTIC ERROR: Prompt asks for WASHER/RING (annulus) but code uses {method}. Use: cq.Workplane("XY").circle(R_outer).circle(R_inner).extrude(thickness)'
            },
            'annulus': {
                'required': ['.circle(', '.extrude('],  # Annulus = 2 circles + extrude
                'forbidden': ['.box(', '.sphere(', 'revolve', 'loft'],
                'error_msg': 'SEMANTIC ERROR: Prompt asks for ANNULUS but code uses {method}. Use: cq.Workplane("XY").circle(R_outer).circle(R_inner).extrude(thickness)'
            }
        }

        # Vérifier chaque forme mentionnée dans le prompt
        for shape, requirements in shape_requirements.items():
            if shape in prompt_lower:
                # Vérifier les méthodes interdites
                for forbidden in requirements['forbidden']:
                    if forbidden in code:
                        return requirements['error_msg'].format(method=forbidden)

                # Pour le cone, vérifier qu'il utilise soit loft, soit taper, soit .cone()
                if shape == 'cone':
                    has_loft = 'loft' in code
                    has_taper = 'taper=' in code or 'taper =' in code
                    has_cone_method = '.cone(' in code

                    if not (has_loft or has_taper or has_cone_method):
                        # Ni loft, ni taper, ni .cone() = mauvaise forme
                        return requirements['error_msg'].format(method='.extrude() without loft or taper')

                # Vérifier que les méthodes requises sont présentes (skip if empty list)
                if 'required' in requirements and len(requirements['required']) > 0:
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

    def _check_glass_pattern(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie le pattern spécifique pour un verre (glass)
        """
        prompt_lower = prompt.lower()
        if "glass" not in prompt_lower and "drinking" not in prompt_lower and "cup" not in prompt_lower:
            return None

        # Glass = outer cylinder + inner cut from top + fillet rim
        # MUST have: circle().extrude() for outer, then faces(">Z").workplane().circle().cutBlind(-depth)
        if ".circle(" not in code or ".extrude(" not in code:
            return "SEMANTIC ERROR: Glass needs .circle().extrude() pattern"

        # Check for hollow structure - MUST use cutBlind() not extrude()
        # extrude(-X) doesn't properly cut, it creates wrong geometry
        if ".workplane()" in code and ".circle(" in code:
            # Look for extrude(-...) after workplane().circle() pattern
            import re
            # Pattern: workplane() ... circle(...) ... extrude(-...)
            if re.search(r'\.workplane\(\).*\.circle\([^)]+\).*\.extrude\(-', code):
                return "SEMANTIC ERROR: Glass hollow must use .cutBlind(-depth), not .extrude(-depth). Use: .workplane().circle(R_in).cutBlind(-(height - bottom))"

        # If no cutBlind and no proper cut method found
        if ".cutBlind(" not in code and ".cut(" not in code and "shell(" not in code:
            return "SEMANTIC ERROR: Glass must be hollow (use .cutBlind(-depth) to cut from top)"

        # Check rim fillet
        if "fillet" in prompt_lower and ".fillet(" not in code:
            return "SEMANTIC ERROR: Prompt mentions fillet but code missing .fillet()"

        return None

    def _check_spring_pattern(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie le pattern spécifique pour un ressort (spring)
        """
        prompt_lower = prompt.lower()
        if "spring" not in prompt_lower and "helix" not in prompt_lower:
            return None

        # Spring = Wire.makeHelix + sweep
        # MUST have Wire.makeHelix (not just check for invalid .helix())
        if "Wire.makeHelix" not in code and "makeHelix" not in code:
            return "SEMANTIC ERROR: Spring needs Wire.makeHelix(pitch, height, radius) to create helix path"

        # MUST NOT use: Workplane.helix() (doesn't exist)
        if ".helix(" in code and "Wire.makeHelix" not in code:
            return "SEMANTIC ERROR: Workplane.helix() doesn't exist. Use Wire.makeHelix(pitch, height, radius)"

        # MUST have sweep
        if "sweep" not in code and ".sweep(" not in code:
            return "SEMANTIC ERROR: Spring needs sweep() to follow helix path"

        # Check isFrenet parameter
        if "sweep(" in code and "isFrenet" not in code:
            return "SEMANTIC ERROR: Spring sweep should use isFrenet=True for proper orientation"

        # Check that code doesn't just extrude (cylinder fallback)
        if ".extrude(" in code and "sweep" not in code:
            return "SEMANTIC ERROR: Spring should use sweep(path), not extrude() - extrude creates cylinder not helix"

        # Validate Wire.makeHelix parameters to ensure visible spring
        import re
        helix_match = re.search(r'makeHelix\s*\(\s*pitch\s*=\s*(\d+(?:\.\d+)?)\s*,\s*height\s*=\s*(\d+(?:\.\d+)?)\s*,\s*radius\s*=\s*(\d+(?:\.\d+)?)', code)
        if helix_match:
            pitch = float(helix_match.group(1))
            height = float(helix_match.group(2))
            radius = float(helix_match.group(3))

            # Validate parameters
            if pitch <= 0:
                return "SEMANTIC ERROR: Spring pitch must be > 0 (pitch=0 creates circle, not helix)"
            if height <= pitch:
                return "SEMANTIC ERROR: Spring height must be > pitch (need at least 2 turns for visible spring)"
            if radius <= 0:
                return "SEMANTIC ERROR: Spring radius must be > 0"

            # Check for reasonable number of turns (at least 3 for a spring)
            turns = height / pitch
            if turns < 3:
                return f"SEMANTIC ERROR: Spring needs at least 3 turns for proper spring shape (current: {turns:.1f} turns = {height}mm / {pitch}mm)"

        # Check if circle is positioned at helix start point
        # Helix starts at (radius, 0, 0), so circle should use .center(radius, 0) or .moveTo(radius, 0)
        if ".circle(" in code and ".sweep(" in code:
            # Check if there's a .center() or .moveTo() before .circle()
            if ".center(" not in code and ".moveTo(" not in code:
                # Extract radius from makeHelix if we found it
                if helix_match:
                    radius = helix_match.group(3)
                    return f"SEMANTIC ERROR: Circle must be positioned at helix start. Use: Workplane(\"XY\").center({radius}, 0).circle(...) or .moveTo({radius}, 0).circle(...)"
                else:
                    return "SEMANTIC ERROR: Circle must be positioned at helix start. Use: .center(radius, 0).circle(...) before .sweep()"

        return None

    def _check_vase_pattern(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie le pattern spécifique pour un vase
        """
        prompt_lower = prompt.lower()
        if "vase" not in prompt_lower:
            return None

        # Vase = loft OR revolve, NOT BOTH
        has_loft = ".loft(" in code
        has_revolve = ".revolve(" in code

        if has_loft and has_revolve:
            return "SEMANTIC ERROR: Vase should use EITHER loft() OR revolve(), NOT BOTH"

        # If loft, must have shell
        if has_loft and ".shell(" not in code:
            return "SEMANTIC ERROR: Vase needs .shell() to be hollow after lofting"

        # Check for invalid revolve pattern (circle + moveTo + arc + close + revolve)
        if has_revolve:
            import re
            # Detect pattern: circle() followed by moveTo() before revolve()
            if re.search(r'\.circle\([^)]+\).*\.moveTo\([^)]+\).*\.revolve\(', code, re.DOTALL):
                return "SEMANTIC ERROR: Cannot use revolve() after circle() + moveTo() - this creates invalid profile. For varying radii at different heights, use LOFT instead: circle().workplane(offset=h).circle().loft()"

            # Vase with revolve must have explicit 2D profile (lineTo, arc, close)
            has_close = ".close(" in code
            has_lineto_or_arc = ".lineTo(" in code or ".radiusArc(" in code or ".threePointArc(" in code

            if not (has_close and has_lineto_or_arc):
                return "SEMANTIC ERROR: Vase with revolve() needs explicit closed 2D profile (lineTo/arc + close). For varying radii, use LOFT instead"

        # Check for multiple workplane offsets (loft pattern)
        if has_loft:
            import re
            workplane_count = len(re.findall(r'\.workplane\s*\(\s*offset\s*=', code))
            circle_count = len(re.findall(r'\.circle\s*\(', code))

            if circle_count < 2:
                return "SEMANTIC ERROR: Vase loft needs at least 2 circles at different heights"

        return None

    def _check_pipe_pattern(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie le pattern spécifique pour un tuyau (pipe)
        """
        prompt_lower = prompt.lower()
        if "pipe" not in prompt_lower and "tube" not in prompt_lower:
            return None

        # Pipe = outer cylinder + inner cut + chamfer/fillet rims
        # Check hollow
        if ".cut(" not in code and "shell(" not in code and "extrude(-" not in code:
            return "SEMANTIC ERROR: Pipe must be hollow (needs inner cylinder cut)"

        # Check for top face selection before inner cut
        if "extrude(-" in code and "faces(" not in code:
            return "SEMANTIC ERROR: Pipe inner cut needs faces('>Z').workplane() before circle"

        return None

    def _check_bowl_pattern(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie le pattern spécifique pour un bol (bowl)
        """
        prompt_lower = prompt.lower()
        if "bowl" not in prompt_lower and "hemisphere" not in prompt_lower:
            return None

        # If prompt explicitly asks for revolving, allow it
        # Only suggest sphere() if revolve is NOT mentioned in prompt
        if ".revolve(" in code and ".sphere(" not in code:
            if "revolv" not in prompt_lower:  # Allow "revolve", "revolving", etc.
                return "SEMANTIC ERROR: Prompt asks for SPHERE but code uses revolve. Use: cq.Workplane('XY').sphere(radius)"

        # Bowl must be hollow
        if ".shell(" not in code and ".cut(" not in code:
            return "SEMANTIC ERROR: Bowl must be hollow (use .shell() or .cut())"

        return None

    def _check_screw_pattern(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie le pattern spécifique pour une vis (screw)
        """
        prompt_lower = prompt.lower()
        if "screw" not in prompt_lower and "bolt" not in prompt_lower:
            return None

        # Screw = shaft + hex head + union
        # Check for shaft (cylinder)
        if ".circle(" not in code or ".extrude(" not in code:
            return "SEMANTIC ERROR: Screw needs cylindrical shaft: circle(r).extrude(h)"

        # Check for hex head (polygon)
        if "hex" in prompt_lower and ".polygon(" not in code:
            return "SEMANTIC ERROR: Hex head needs polygon(6, diameter)"

        # Check for union
        if ".union(" not in code:
            return "SEMANTIC ERROR: Screw needs .union() to join shaft and head"

        return None

    def _check_arc_pattern(self, code: str, prompt: str) -> Optional[str]:
        """
        Vérifie le pattern spécifique pour un arc (annular sector / portion de couronne)
        """
        prompt_lower = prompt.lower()

        # Check if prompt asks for arc
        if "arc" not in prompt_lower and "annular" not in prompt_lower and "sector" not in prompt_lower:
            return None

        # Arc = annular sector (portion de couronne)
        # MUST use Edge.makeCircle + Wire.assembleEdges approach
        # NOT threePointArc, radiusArc, or simple revolve

        # Check for problematic methods that don't work for arcs
        if ".threePointArc(" in code:
            return "SEMANTIC ERROR: Prompt asks for ARC (annular sector / portion de couronne) but code uses threePointArc which fails. Use Edge.makeCircle() + Wire.assembleEdges() pattern"

        if ".radiusArc(" in code:
            return "SEMANTIC ERROR: Prompt asks for ARC (annular sector / portion de couronne) but code uses radiusArc which fails. Use Edge.makeCircle() + Wire.assembleEdges() pattern"

        # Check for correct pattern
        if "Edge.makeCircle" not in code and "makeCircle" not in code:
            return "SEMANTIC ERROR: Prompt asks for ARC (annular sector / portion de couronne) but code missing Edge.makeCircle(). Use: Edge.makeCircle(R, center, normal, angle1, angle2) to create circular arcs"

        if "Wire.assembleEdges" not in code and "assembleEdges" not in code:
            return "SEMANTIC ERROR: Arc needs Wire.assembleEdges([edges]) to create closed wires from circular arcs and radial lines"

        # Arc should create outer and inner wires then subtract
        if ".cut(" not in code:
            return "SEMANTIC ERROR: Arc needs .cut() to subtract inner solid from outer solid"

        return None

    def _check_hallucinated_methods(self, code: str) -> Optional[str]:
        """
        Vérifie les méthodes hallucinées courantes
        """
        hallucinations = {
            ".torus(": "Use revolve pattern: result = cq.Workplane('XY').moveTo(major_r, 0).circle(minor_r).revolve(360, (0,0,0), (0,0,1))",
            ".cylinder(": "Use circle().extrude(): cq.Workplane('XY').circle(r).extrude(h)",
            ".cone(": "Use loft pattern: cq.Workplane('XY').circle(r1).workplane(offset=h).circle(r2).loft()",
            ".regularPolygon(": "Use .polygon(nSides, diameter)",
            ".helix(": "Use Wire.makeHelix(pitch, height, radius)",
            "Workplane.helix": "Use Wire.makeHelix(pitch, height, radius)",
        }

        for hallucination, fix in hallucinations.items():
            if hallucination in code:
                return f"SEMANTIC ERROR: {hallucination} doesn't exist. {fix}"

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
