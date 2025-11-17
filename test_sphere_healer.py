#!/usr/bin/env python3
"""
Test sphere healer - replaces circle + extrude with sphere
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import CriticAgent, SelfHealingAgent, WorkflowContext


async def test_sphere_healer():
    """Test that healer fixes sphere code using circle + extrude"""
    print("\n" + "="*80)
    print("TEST: Sphere healer - circle + extrude → sphere")
    print("="*80)

    # Prompt for sphere
    prompt = "Create a sphere diameter 80 mm"

    # Bad code with circle + extrude (likely what LLM generates)
    bad_code = """import cadquery as cq
from pathlib import Path

result = (cq.Workplane("XY")
          .circle(40)
          .extrude(80, taper=0))

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
"""

    print("\nBAD CODE (circle + extrude for sphere):")
    print("-" * 80)
    print(bad_code)
    print("-" * 80)

    # Create Critic agent
    critic = CriticAgent()

    # Critic should detect sphere pattern issue
    result = await critic.critique_code(bad_code, prompt)
    errors = result.errors

    if errors:
        print("\n✅ Critic detected errors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    else:
        print("\n❌ Critic FAILED to detect sphere pattern issue!")
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

        if ".sphere(" in fixed_code:
            print("✅ Uses .sphere()")
        else:
            print("❌ Missing .sphere()")
            success = False

        if ".extrude(" in fixed_code:
            print("❌ Still has .extrude() - should be removed!")
            success = False
        else:
            print("✅ .extrude() removed")

        if ".circle(" in fixed_code and "result =" in fixed_code:
            # Check if circle is in the result definition (bad) or elsewhere (ok)
            lines = fixed_code.split('\n')
            for line in lines:
                if 'result =' in line or 'result=' in line:
                    if '.circle(' in line:
                        print("❌ Still uses .circle() in result definition!")
                        success = False
                        break
            else:
                print("✅ .circle() removed from result definition")
        else:
            print("✅ .circle() removed")

        # Check for correct radius (diameter 80 → radius 40)
        if "sphere(40)" in fixed_code:
            print("✅ Correctly extracted diameter 80 → radius 40")
        else:
            print("⚠️  Radius may not be correct (expected 40 from diameter 80)")

        # Check that output_dir is preserved
        if "output_dir" in fixed_code and "output_dir.mkdir" in fixed_code:
            print("✅ output_dir definition preserved")
        else:
            print("❌ output_dir definition missing!")
            success = False

        # Check for balanced parens
        if fixed_code.count('(') != fixed_code.count(')'):
            print(f"❌ Unbalanced parentheses! ( count: {fixed_code.count('(')}, ) count: {fixed_code.count(')')}")
            success = False
        else:
            print("✅ Balanced parentheses")

        print()
        if success:
            print("✅ Sphere healer SUCCESSFULLY fixed circle + extrude!")
        else:
            print("❌ Sphere healer failed!")

        return success

    except Exception as e:
        print(f"\n❌ EXCEPTION during healing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_sphere_healer())
    sys.exit(0 if success else 1)
