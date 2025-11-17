#!/usr/bin/env python3
"""
Test arc detection by Critic and healing by SelfHealingAgent
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import CriticAgent, SelfHealingAgent, WorkflowContext


async def test_arc_detection_and_healing():
    """Test that Critic detects arc pattern and healer fixes it"""
    print("\n" + "="*80)
    print("TEST: Arc detection by Critic + healing by SelfHealingAgent")
    print("="*80)

    # Prompt for arc
    prompt = "Create an arc radius 60 mm sweep 210 deg"

    # Bad code that doesn't use Edge.makeCircle approach
    bad_code = """
import cadquery as cq
from pathlib import Path

# Create a workplane on XY plane
result = cq.Workplane("XY")

# Draw a circle with radius 60
result = result.circle(60)

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "arc.stl"
cq.exporters.export(result, str(output_path))
"""

    print("\nSTEP 1: Testing Critic Detection")
    print("-" * 80)
    print("PROMPT:", prompt)
    print()
    print("BAD CODE:")
    print(bad_code)
    print("-" * 80)

    # Create Critic agent
    critic = CriticAgent()

    # Critic should detect arc pattern issue
    result = await critic.critique_code(bad_code, prompt)

    errors = result.errors  # Extract errors list from AgentResult

    if errors:
        print("\n✅ Critic detected errors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    else:
        print("\n❌ Critic FAILED to detect arc pattern issue!")
        return False

    # Check if arc-specific error was detected
    arc_error_found = any("arc" in err.lower() or "makeCircle" in err for err in errors)
    if arc_error_found:
        print("\n✅ Critic detected ARC-specific error")
    else:
        print("\n❌ Critic did NOT detect arc-specific error")
        return False

    print("\n" + "="*80)
    print("STEP 2: Testing SelfHealingAgent Healing")
    print("="*80)

    # Create healing agent
    healing = SelfHealingAgent()
    context = WorkflowContext(prompt=prompt)

    try:
        # Apply healing
        fixed_code = healing._basic_fixes(bad_code, errors, context)

        print("\nFIXED CODE:")
        print("-" * 80)
        print(fixed_code)
        print("-" * 80)

        # Check for syntax errors
        try:
            compile(fixed_code, '<test>', 'exec')
            print("\n✅ Fixed code has valid Python syntax")
        except SyntaxError as e:
            print(f"\n❌ Fixed code has SYNTAX ERROR: {e}")
            print(f"   Line {e.lineno}: {e.text}")
            return False

        # Verifications
        success = True

        if "Edge.makeCircle" in fixed_code:
            print("✅ Uses Edge.makeCircle")
        else:
            print("❌ Missing Edge.makeCircle")
            success = False

        if "Wire.assembleEdges" in fixed_code:
            print("✅ Uses Wire.assembleEdges")
        else:
            print("❌ Missing Wire.assembleEdges")
            success = False

        if "outer_wire" in fixed_code and "inner_wire" in fixed_code:
            print("✅ Creates outer and inner wires")
        else:
            print("❌ Missing wire creation")
            success = False

        if ".cut(" in fixed_code:
            print("✅ Uses .cut() to subtract inner from outer")
        else:
            print("❌ Missing .cut()")
            success = False

        # Check parameters were extracted correctly
        if "R_OUT = 60" in fixed_code:
            print("✅ Correctly extracted radius 60 from prompt")
        else:
            print("⚠️  Radius may not have been extracted correctly from prompt")

        if "ANGLE = 210" in fixed_code:
            print("✅ Correctly extracted angle 210 from prompt")
        else:
            print("⚠️  Angle may not have been extracted correctly from prompt")

        if "threePointArc" in fixed_code:
            print("⚠️  Still contains threePointArc (should use Edge.makeCircle)")
            # Don't fail, but warn
        else:
            print("✅ Does NOT contain problematic threePointArc")

        print()
        if success:
            print("✅ Arc detection and healing SUCCESSFUL!")
        else:
            print("❌ Arc detection and healing FAILED!")

        return success

    except Exception as e:
        print(f"\n❌ EXCEPTION during healing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_arc_detection_and_healing())
    sys.exit(0 if success else 1)
