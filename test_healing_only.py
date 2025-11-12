#!/usr/bin/env python3
"""
Test simple pour vérifier le healing du code (sans exécution)
"""
import sys
from pathlib import Path

# Ajouter le répertoire backend au path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import SelfHealingAgent


def test_arc_healing():
    """Test que le healing remplace .box() par annular sector pour arc"""
    print("\n" + "="*80)
    print("TEST: Arc Healing")
    print("="*80)

    # Code avec .box() (mauvais)
    bad_code = """
import cadquery as cq

# Arc with radius 60 mm and sweep angle 210 degrees
result = cq.Workplane("XY").box(60, 60, 10)

# Export
result
"""

    # Erreur du Critic
    error = "SEMANTIC ERROR: Prompt asks for ARC (annular sector / portion de couronne) but code uses .box(. Use annular sector pattern: moveTo(R_ext, 0) → threePointArc(outer) → lineTo(R_int) → threePointArc(inner) → close() → extrude()"

    # Créer le healing agent
    healing = SelfHealingAgent()

    # Appliquer le healing
    fixed_code = healing._basic_fixes(bad_code, [error])

    print("ORIGINAL CODE:")
    print("-" * 80)
    print(bad_code)
    print("-" * 80)

    print("\nFIXED CODE:")
    print("-" * 80)
    print(fixed_code)
    print("-" * 80)

    # Vérifications
    success = True

    if "threePointArc" in fixed_code:
        print("✅ Fixed code contains 'threePointArc'")
    else:
        print("❌ Fixed code does NOT contain 'threePointArc'")
        success = False

    if "lineTo" in fixed_code:
        print("✅ Fixed code contains 'lineTo'")
    else:
        print("❌ Fixed code does NOT contain 'lineTo'")
        success = False

    if ".close()" in fixed_code:
        print("✅ Fixed code contains '.close()'")
    else:
        print("❌ Fixed code does NOT contain '.close()'")
        success = False

    if ".box(" not in fixed_code:
        print("✅ Fixed code does NOT contain '.box()' (good!)")
    else:
        print("❌ Fixed code still contains '.box()' (bad!)")
        success = False

    if "import math" in fixed_code:
        print("✅ Fixed code imports math")
    else:
        print("⚠️  Fixed code does not import math")

    print()
    if success:
        print("✅ Arc healing SUCCESSFUL!")
    else:
        print("❌ Arc healing FAILED!")

    return success


def test_cone_healing():
    """Test que le healing remplace .cylinder() par loft pour cone"""
    print("\n" + "="*80)
    print("TEST: Cone Healing")
    print("="*80)

    # Code avec .cylinder() (mauvais)
    bad_code = """
import cadquery as cq

# Cone with base diameter 50 mm and height 60 mm
base_plane = cq.Workplane("XY")
cone = base_plane.cylinder(25, 60)

result = cone
"""

    # Erreur du Critic
    error = "SEMANTIC ERROR: Prompt asks for CONE but code uses .cylinder(). Use cone loft pattern with two circles and loft."

    # Créer le healing agent
    healing = SelfHealingAgent()

    # Appliquer le healing
    fixed_code = healing._basic_fixes(bad_code, [error])

    print("ORIGINAL CODE:")
    print("-" * 80)
    print(bad_code)
    print("-" * 80)

    print("\nFIXED CODE:")
    print("-" * 80)
    print(fixed_code)
    print("-" * 80)

    # Vérifications
    success = True

    if ".loft(" in fixed_code:
        print("✅ Fixed code contains '.loft()'")
    else:
        print("❌ Fixed code does NOT contain '.loft()'")
        success = False

    if ".cylinder(" not in fixed_code:
        print("✅ Fixed code does NOT contain '.cylinder()' (good!)")
    else:
        print("❌ Fixed code still contains '.cylinder()' (bad!)")
        success = False

    if ".circle(" in fixed_code:
        print("✅ Fixed code contains '.circle()' (for loft profile)")
    else:
        print("⚠️  Fixed code does not contain '.circle()'")

    print()
    if success:
        print("✅ Cone healing SUCCESSFUL!")
    else:
        print("❌ Cone healing FAILED!")

    return success


if __name__ == "__main__":
    arc_ok = test_arc_healing()
    cone_ok = test_cone_healing()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Arc healing:  {'✅ SUCCESS' if arc_ok else '❌ FAILED'}")
    print(f"Cone healing: {'✅ SUCCESS' if cone_ok else '❌ FAILED'}")
    print("="*80)

    sys.exit(0 if (arc_ok and cone_ok) else 1)
