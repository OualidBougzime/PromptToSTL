#!/usr/bin/env python3
"""
Script de test pour vérifier les 3 formes problématiques:
- ARC (annular sector)
- CONE (loft, not .cylinder())
- TORUS (revolve)
"""
import asyncio
import sys
import os
from pathlib import Path

# Ajouter le répertoire backend au path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from agents import AnalystAgent, GeneratorAgent, ValidatorAgent
from multi_agent_system import OrchestratorAgent


async def test_shape(orchestrator, prompt_name: str, prompt: str):
    """Test une forme spécifique"""
    print(f"\n{'='*80}")
    print(f"TEST: {prompt_name}")
    print(f"{'='*80}")
    print(f"Prompt: {prompt}")
    print()

    try:
        result = await orchestrator.execute_workflow(prompt)

        if result.get("success"):
            print(f"✅ SUCCESS: {prompt_name}")

            # Vérifier le code généré
            code = result.get("code", "")

            # Validations spécifiques selon la forme
            if prompt_name == "ARC":
                if "threePointArc" in code and "lineTo" in code and "close" in code:
                    print("   ✅ Code contains annular sector pattern (threePointArc + lineTo + close)")
                else:
                    print("   ⚠️  WARNING: Code may not use correct annular sector pattern")
                    if ".revolve(" in code:
                        print("   ❌ ERROR: Code uses revolve (wrong for annular sector)")
                    if ".sweep(" in code:
                        print("   ❌ ERROR: Code uses sweep (wrong for annular sector)")

            elif prompt_name == "CONE":
                if ".loft(" in code:
                    print("   ✅ Code uses loft (correct method)")
                else:
                    print("   ⚠️  WARNING: Code may not use loft")

                if ".cylinder(" in code:
                    print("   ❌ ERROR: Code uses .cylinder() hallucinated method")
                elif "import Helpers" in code or "from Helpers" in code:
                    print("   ❌ ERROR: Code imports Helpers hallucinated module")

            elif prompt_name == "TORUS":
                if ".revolve(" in code:
                    print("   ✅ Code uses revolve (correct method)")
                else:
                    print("   ⚠️  WARNING: Code may not use revolve")

            print(f"\n📝 Generated code (first 30 lines):")
            print("-" * 80)
            lines = code.split('\n')
            for i, line in enumerate(lines[:30], 1):
                print(f"{i:3d} | {line}")
            if len(lines) > 30:
                print(f"... ({len(lines) - 30} more lines)")
            print("-" * 80)

        else:
            print(f"❌ FAILED: {prompt_name}")
            errors = result.get("errors", ["Unknown error"])
            for error in errors:
                print(f"   Error: {error}")

    except Exception as e:
        print(f"❌ EXCEPTION: {prompt_name}")
        print(f"   {type(e).__name__}: {e}")

    print()
    return result.get("success", False)


async def main():
    """Fonction principale de test"""
    print("\n" + "="*80)
    print("TEST SUITE: Arc, Cone, Torus Generation")
    print("="*80)

    # Créer l'orchestrateur
    analyst = AnalystAgent()
    generator = GeneratorAgent()
    validator = ValidatorAgent()
    orchestrator = OrchestratorAgent(analyst, generator, validator)

    # Tests
    tests = [
        ("ARC", "Create an arc with radius 60 mm and sweep angle 210 degrees"),
        ("CONE", "Create a cone with base diameter 50 mm and height 60 mm"),
        ("TORUS", "Create a torus with major radius 50 mm and minor radius 10 mm"),
    ]

    results = {}
    for name, prompt in tests:
        results[name] = await test_shape(orchestrator, name, prompt)

    # Résumé
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {name}")

    print()
    print(f"Success rate: {success_count}/{total_count} ({success_count*100//total_count}%)")
    print("="*80)

    return success_count == total_count


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
