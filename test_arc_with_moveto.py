#!/usr/bin/env python3
"""
Test arc healer with multi-line code including moveTo + threePointArc
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import CriticAgent, SelfHealingAgent, WorkflowContext


async def test_arc_with_moveto():
    """Test that healer handles code with moveTo before threePointArc"""
    print("\n" + "="*80)
    print("TEST: Arc healer with moveTo + threePointArc chain")
    print("="*80)

    # Prompt for arc
    prompt = "Create an arc radius 60 mm sweep 210 deg"

    # Bad code with moveTo + threePointArc (likely what's being generated)
    bad_code = """import cadquery as cq
from pathlib import Path

result = (cq.Workplane("XY")
          .moveTo(60, 0)
          .threePointArc((30, 52), (-30, 52))
          .close())

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
"""

    print("\nBAD CODE (with moveTo + threePointArc):")
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
            print(f"   Offset: {e.offset}")
            # Print context around the error
            lines = fixed_code.split('\n')
            if e.lineno:
                start = max(0, e.lineno - 3)
                end = min(len(lines), e.lineno + 2)
                print(f"\n   Context around line {e.lineno}:")
                for i in range(start, end):
                    marker = ">>>" if i == e.lineno - 1 else "   "
                    print(f"   {marker} {i+1:3d}: {lines[i]}")
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

        # Check that continuation lines were removed
        if ".moveTo(" in fixed_code and ".threePointArc(" not in fixed_code:
            print("⚠️  moveTo still present (should be removed with chain)")
        else:
            print("✅ Chained methods removed")

        # Check for balanced parens
        if fixed_code.count('(') != fixed_code.count(')'):
            print(f"❌ Unbalanced parentheses! ( count: {fixed_code.count('(')}, ) count: {fixed_code.count(')')}")
            success = False
        else:
            print("✅ Balanced parentheses")

        print()
        if success:
            print("✅ Arc healer handles moveTo + threePointArc SUCCESSFULLY!")
        else:
            print("❌ Arc healer failed!")

        return success

    except Exception as e:
        print(f"\n❌ EXCEPTION during healing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_arc_with_moveto())
    sys.exit(0 if success else 1)
