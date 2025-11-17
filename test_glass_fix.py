#!/usr/bin/env python3
"""
Test for drinking glass generation fix
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import SelfHealingAgent, CriticAgent, WorkflowContext


def test_glass_critic_detects_extrude():
    """Test that Critic detects .extrude(-) instead of .cutBlind(-)"""
    print("\n" + "="*80)
    print("TEST: Critic should FLAG .extrude(-) for glass hollow")
    print("="*80)

    # Code with .extrude(-) (BAD)
    code = """
import cadquery as cq

result = (cq.Workplane("XY")
           .circle(35)
           .extrude(100)
           .faces(">Z")
           .workplane()
           .circle(32.5)
           .extrude(-92))
"""

    # Prompt asks for drinking glass
    prompt = "Create a drinking glass: make an outer cylinder radius 35 mm height 100 mm, subtract an inner cylinder radius 32.5 mm height 92 mm"

    # Create critic agent
    critic = CriticAgent()

    # Check glass pattern
    error = critic._check_glass_pattern(code, prompt)

    print(f"Code has: .workplane().circle(32.5).extrude(-92)")
    print(f"Critic result: {error}")

    if error and "cutBlind" in error:
        print("✅ Critic correctly detects .extrude(-) should be .cutBlind(-)")
        return True
    else:
        print(f"❌ Critic should have detected the issue")
        return False


def test_glass_critic_allows_cutblind():
    """Test that Critic allows code with .cutBlind(-)"""
    print("\n" + "="*80)
    print("TEST: Critic should ALLOW code with .cutBlind(-)")
    print("="*80)

    # Code WITH .cutBlind(-) (GOOD)
    code = """
import cadquery as cq

result = cq.Workplane("XY").circle(35).extrude(100)
result = result.faces(">Z").workplane().circle(32.5).cutBlind(-92)
"""

    # Prompt asks for drinking glass
    prompt = "Create a drinking glass"

    # Create critic agent
    critic = CriticAgent()

    # Check glass pattern
    error = critic._check_glass_pattern(code, prompt)

    print(f"Code has: .workplane().circle(32.5).cutBlind(-92)")
    print(f"Critic result: {error}")

    if error is None:
        print("✅ Critic correctly allows code with .cutBlind(-)")
        return True
    else:
        print(f"❌ Critic incorrectly flagged: {error}")
        return False


def test_glass_healing_replaces_extrude():
    """Test that healing replaces .extrude(-) with .cutBlind(-)"""
    print("\n" + "="*80)
    print("TEST: Healing should replace .extrude(-) with .cutBlind(-)")
    print("="*80)

    # Code with .extrude(-)
    bad_code = """
import cadquery as cq
from pathlib import Path

result = (cq.Workplane("XY")
           .circle(35)
           .extrude(100)
           .faces(">Z")
           .workplane()
           .circle(32.5)
           .extrude(-92)
           .edges(">Z")
           .fillet(1))

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "glass.stl"
cq.exporters.export(result, str(output_path))
"""

    # Error from Critic
    error = 'SEMANTIC ERROR: Glass hollow must use .cutBlind(-depth), not .extrude(-depth). Use: .workplane().circle(R_in).cutBlind(-(height - bottom))'

    # Create healing agent
    healing = SelfHealingAgent()

    # Create workflow context
    context = WorkflowContext(
        prompt="Create a drinking glass: make an outer cylinder radius 35 mm height 100 mm, subtract an inner cylinder radius 32.5 mm height 92 mm"
    )

    # Apply healing
    fixed_code = healing._basic_fixes(bad_code, [error], context)

    print("ORIGINAL CODE:")
    print("-" * 80)
    print(bad_code)
    print("-" * 80)

    print("\nFIXED CODE:")
    print("-" * 80)
    print(fixed_code)
    print("-" * 80)

    # Verifications
    success = True

    if ".cutBlind(-92)" in fixed_code or ".cutBlind(-" in fixed_code:
        print("✅ Fixed code contains '.cutBlind(-'")
    else:
        print("❌ Fixed code does NOT contain '.cutBlind(-'")
        success = False

    # Count occurrences of .extrude(- in fixed code (should be 0 or only for initial cylinder)
    extrude_neg_count = fixed_code.count('.extrude(-')
    if extrude_neg_count == 0:
        print("✅ Fixed code does NOT contain '.extrude(-' (good!)")
    else:
        print(f"❌ Fixed code still contains {extrude_neg_count} '.extrude(-' (should be 0)")
        success = False

    if ".circle(35)" in fixed_code and ".extrude(100)" in fixed_code:
        print("✅ Fixed code still has outer cylinder creation")
    else:
        print("❌ Fixed code lost outer cylinder")
        success = False

    print()
    if success:
        print("✅ Glass healing SUCCESSFUL!")
    else:
        print("❌ Glass healing FAILED!")

    return success


if __name__ == "__main__":
    critic_detects_ok = test_glass_critic_detects_extrude()
    critic_allows_ok = test_glass_critic_allows_cutblind()
    healing_ok = test_glass_healing_replaces_extrude()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Critic detects extrude:  {'✅ SUCCESS' if critic_detects_ok else '❌ FAILED'}")
    print(f"Critic allows cutBlind:  {'✅ SUCCESS' if critic_allows_ok else '❌ FAILED'}")
    print(f"Healing replaces:        {'✅ SUCCESS' if healing_ok else '❌ FAILED'}")
    print("="*80)

    sys.exit(0 if (critic_detects_ok and critic_allows_ok and healing_ok) else 1)
