#!/usr/bin/env python3
"""
Test for hemisphere bowl generation fix
"""
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import SelfHealingAgent, CriticAgent, WorkflowContext


def test_bowl_critic_allows_revolve():
    """Test that Critic allows revolve when prompt explicitly asks for it"""
    print("\n" + "="*80)
    print("TEST: Critic should ALLOW revolve for 'revolving a semicircle' prompt")
    print("="*80)

    # Code with .revolve() (GOOD when prompt asks for it)
    code = """
import cadquery as cq

# Create semicircle and revolve
result = cq.Workplane("XY").circle(40).revolve().shell(-3)
"""

    # Prompt explicitly asks for revolving
    prompt = "Create a hemispherical bowl by revolving a semicircle radius 40 mm"

    # Create critic agent
    critic = CriticAgent()

    # Check bowl pattern
    error = critic._check_bowl_pattern(code, prompt)

    print(f"Prompt: {prompt}")
    print(f"Code uses: .revolve()")
    print(f"Critic result: {error}")

    if error is None:
        print("✅ Critic correctly allows revolve when prompt asks for it")
        return True
    else:
        print(f"❌ Critic incorrectly flagged: {error}")
        return False


def test_bowl_critic_flags_revolve_without_prompt():
    """Test that Critic flags revolve when prompt does NOT ask for it"""
    print("\n" + "="*80)
    print("TEST: Critic should FLAG revolve for 'bowl' prompt without 'revolve'")
    print("="*80)

    # Code with .revolve() (BAD when prompt doesn't ask for it)
    code = """
import cadquery as cq

# Create bowl
result = cq.Workplane("XY").circle(40).revolve()
"""

    # Prompt does NOT mention revolving
    prompt = "Create a hemispherical bowl radius 40 mm"

    # Create critic agent
    critic = CriticAgent()

    # Check bowl pattern
    error = critic._check_bowl_pattern(code, prompt)

    print(f"Prompt: {prompt}")
    print(f"Code uses: .revolve()")
    print(f"Critic result: {error}")

    if error is not None and "SPHERE" in error:
        print("✅ Critic correctly flags revolve when prompt doesn't ask for it")
        return True
    else:
        print("❌ Critic should have flagged revolve")
        return False


def test_bowl_healing():
    """Test that healing generates valid hemisphere bowl code"""
    print("\n" + "="*80)
    print("TEST: Bowl Healing (sphere + cut + shell)")
    print("="*80)

    # Code with .revolve() that needs fixing
    bad_code = """
import cadquery as cq
from pathlib import Path

# Create semicircle
result = cq.Workplane("XY").circle(40).revolve().shell(-3)

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "bowl.stl"
cq.exporters.export(result, str(output_path))
"""

    # Error from Critic
    error = "SEMANTIC ERROR: Prompt asks for SPHERE but code uses revolve. Use: cq.Workplane('XY').sphere(radius)"

    # Create healing agent
    healing = SelfHealingAgent()

    # Create workflow context
    context = WorkflowContext(
        prompt="Create a hemispherical bowl by revolving a semicircle radius 40 mm"
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

    if ".sphere(" in fixed_code:
        print("✅ Fixed code contains '.sphere()'")
    else:
        print("❌ Fixed code does NOT contain '.sphere()'")
        success = False

    if ".cut(" in fixed_code:
        print("✅ Fixed code contains '.cut()' (to create hemisphere)")
    else:
        print("❌ Fixed code does NOT contain '.cut()'")
        success = False

    if ".shell(" in fixed_code:
        print("✅ Fixed code contains '.shell()' (to hollow)")
    else:
        print("❌ Fixed code does NOT contain '.shell()'")
        success = False

    if ".revolve(" not in fixed_code:
        print("✅ Fixed code does NOT contain '.revolve()' (good!)")
    else:
        print("❌ Fixed code still contains '.revolve()' (bad!)")
        success = False

    # Check that it doesn't have the problematic extrude for bottom disc
    if ".extrude(3)" not in fixed_code:
        print("✅ Fixed code does NOT have problematic bottom disc extrude")
    else:
        print("⚠️  Fixed code still has bottom disc extrude (may cause errors)")

    print()
    if success:
        print("✅ Bowl healing SUCCESSFUL!")
    else:
        print("❌ Bowl healing FAILED!")

    return success


if __name__ == "__main__":
    critic_allows_ok = test_bowl_critic_allows_revolve()
    critic_flags_ok = test_bowl_critic_flags_revolve_without_prompt()
    healing_ok = test_bowl_healing()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Critic allows revolve:  {'✅ SUCCESS' if critic_allows_ok else '❌ FAILED'}")
    print(f"Critic flags revolve:   {'✅ SUCCESS' if critic_flags_ok else '❌ FAILED'}")
    print(f"Bowl healing:           {'✅ SUCCESS' if healing_ok else '❌ FAILED'}")
    print("="*80)

    sys.exit(0 if (critic_allows_ok and critic_flags_ok and healing_ok) else 1)
