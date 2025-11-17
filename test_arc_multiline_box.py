#!/usr/bin/env python3
"""
Test arc healer with multi-line box statement (the actual case from user logs)
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import CriticAgent, SelfHealingAgent, WorkflowContext


async def test_arc_multiline_box():
    """Test that healer handles multi-line chained statements properly"""
    print("\n" + "="*80)
    print("TEST: Arc healer with multi-line box statement")
    print("="*80)

    # Prompt for arc
    prompt = "Create an arc radius 60 mm sweep 210 deg"

    # Bad code with MULTI-LINE box statement (like the real generated code)
    bad_code = """import cadquery as cq
from pathlib import Path

result = (cq.Workplane("XY")
          .box(50, 50, 50))

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
"""

    print("\nBAD CODE (multi-line box):")
    print("-" * 80)
    print(bad_code)
    print("-" * 80)

    # Create Critic agent
    critic = CriticAgent()

    # Critic should detect arc pattern issue
    result = await critic.critique_code(bad_code, prompt)
    errors = result.errors

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
    print("STEP 2: Testing SelfHealingAgent Healing (MULTI-LINE)")
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
            print(f"\n   This is the BUG we're trying to fix!")
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

        # Check that multi-line statement was removed
        if "result = (cq.Workplane" in fixed_code and ".box(" in fixed_code:
            print("❌ Multi-line box statement NOT removed!")
            success = False
        else:
            print("✅ Multi-line box statement removed")

        # Check for unclosed parenthesis issues
        if fixed_code.count('(') != fixed_code.count(')'):
            print(f"❌ Unbalanced parentheses! ( count: {fixed_code.count('(')}, ) count: {fixed_code.count(')')}")
            success = False
        else:
            print("✅ Balanced parentheses")

        print()
        if success:
            print("✅ Arc healer handles multi-line statements SUCCESSFULLY!")
        else:
            print("❌ Arc healer multi-line handling FAILED!")

        return success

    except Exception as e:
        print(f"\n❌ EXCEPTION during healing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_arc_multiline_box())
    sys.exit(0 if success else 1)
