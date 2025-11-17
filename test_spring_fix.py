#!/usr/bin/env python3
"""
Test for helical spring generation fix
"""
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import SelfHealingAgent, CriticAgent, WorkflowContext


def test_spring_critic_detects_missing_center():
    """Test that Critic detects when circle is not positioned at helix start"""
    print("\n" + "="*80)
    print("TEST: Critic should FLAG missing .center() for spring")
    print("="*80)

    # Code without .center() (BAD)
    code = """
import cadquery as cq

# Create helix
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20)
# Create circle and sweep
result = cq.Workplane("XY").circle(1.5).sweep(path, isFrenet=True)
"""

    # Prompt asks for helical spring
    prompt = "Create a helical spring by sweeping a circle radius 1.5 mm along a helix with pitch 8 mm, total height 80 mm, major radius 20 mm"

    # Create critic agent
    critic = CriticAgent()

    # Check spring pattern
    error = critic._check_spring_pattern(code, prompt)

    print(f"Code has: .circle(1.5).sweep() WITHOUT .center()")
    print(f"Critic result: {error}")

    if error and "positioned at helix start" in error:
        print("✅ Critic correctly detects missing .center()")
        return True
    else:
        print(f"❌ Critic should have detected missing .center()")
        return False


def test_spring_critic_allows_center():
    """Test that Critic allows code with .center()"""
    print("\n" + "="*80)
    print("TEST: Critic should ALLOW code with .center()")
    print("="*80)

    # Code WITH .center() (GOOD)
    code = """
import cadquery as cq

# Create helix
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20)
# Create circle at helix start and sweep
result = cq.Workplane("XY").center(20, 0).circle(1.5).sweep(path, isFrenet=True)
"""

    # Prompt asks for helical spring
    prompt = "Create a helical spring by sweeping a circle radius 1.5 mm along a helix"

    # Create critic agent
    critic = CriticAgent()

    # Check spring pattern
    error = critic._check_spring_pattern(code, prompt)

    print(f"Code has: .center(20, 0).circle(1.5).sweep()")
    print(f"Critic result: {error}")

    if error is None:
        print("✅ Critic correctly allows code with .center()")
        return True
    else:
        print(f"❌ Critic incorrectly flagged: {error}")
        return False


def test_spring_healing_adds_center():
    """Test that healing adds .center() when missing"""
    print("\n" + "="*80)
    print("TEST: Healing should add .center() to spring code")
    print("="*80)

    # Code without .center()
    bad_code = """
import cadquery as cq
from pathlib import Path

# Create helix
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20)
# Create circle and sweep
result = cq.Workplane("XY").circle(1.5).sweep(path, isFrenet=True)

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "spring.stl"
cq.exporters.export(result, str(output_path))
"""

    # Error from Critic
    error = 'SEMANTIC ERROR: Circle must be positioned at helix start. Use: Workplane("XY").center(20, 0).circle(...) or .moveTo(20, 0).circle(...)'

    # Create healing agent
    healing = SelfHealingAgent()

    # Create workflow context
    context = WorkflowContext(
        prompt="Create a helical spring by sweeping a circle radius 1.5 mm along a helix with major radius 20 mm"
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

    if ".center(" in fixed_code and ", 0)" in fixed_code:
        print("✅ Fixed code contains '.center(..., 0)'")
    else:
        print("❌ Fixed code does NOT contain '.center()' or '.moveTo()'")
        success = False

    if "makeHelix" in fixed_code:
        print("✅ Fixed code still contains 'makeHelix'")
    else:
        print("❌ Fixed code lost 'makeHelix'")
        success = False

    if ".sweep(" in fixed_code:
        print("✅ Fixed code still contains '.sweep()'")
    else:
        print("❌ Fixed code lost '.sweep()'")
        success = False

    print()
    if success:
        print("✅ Spring healing SUCCESSFUL!")
    else:
        print("❌ Spring healing FAILED!")

    return success


if __name__ == "__main__":
    critic_detects_ok = test_spring_critic_detects_missing_center()
    critic_allows_ok = test_spring_critic_allows_center()
    healing_ok = test_spring_healing_adds_center()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Critic detects missing:  {'✅ SUCCESS' if critic_detects_ok else '❌ FAILED'}")
    print(f"Critic allows correct:   {'✅ SUCCESS' if critic_allows_ok else '❌ FAILED'}")
    print(f"Healing adds center:     {'✅ SUCCESS' if healing_ok else '❌ FAILED'}")
    print("="*80)

    sys.exit(0 if (critic_detects_ok and critic_allows_ok and healing_ok) else 1)
