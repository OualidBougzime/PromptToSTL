#!/usr/bin/env python3
"""
Test torus healer with revolve but missing moveTo
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import CriticAgent, SelfHealingAgent, WorkflowContext


async def test_torus_healer():
    """Test that healer fixes torus code missing moveTo"""
    print("\n" + "="*80)
    print("TEST: Torus healer - revolve without moveTo")
    print("="*80)

    # Prompt for torus
    prompt = "Create a torus major radius 50 mm minor radius 8 mm"

    # Bad code with revolve but missing moveTo (likely what LLM generates)
    bad_code = """import cadquery as cq
from pathlib import Path

result = (cq.Workplane("XZ")
          .circle(8)
          .revolve(360))

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_cot_generated.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
"""

    print("\nBAD CODE (revolve without moveTo):")
    print("-" * 80)
    print(bad_code)
    print("-" * 80)

    # Create Critic agent
    critic = CriticAgent()

    # Critic should detect torus pattern issue
    result = await critic.critique_code(bad_code, prompt)
    errors = result.errors

    if errors:
        print("\n✅ Critic detected errors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    else:
        print("\n❌ Critic FAILED to detect torus pattern issue!")
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

        if ".moveTo(" in fixed_code:
            print("✅ Uses .moveTo()")
        else:
            print("❌ Missing .moveTo()")
            success = False

        if ".revolve(" in fixed_code:
            print("✅ Uses .revolve()")
        else:
            print("❌ Missing .revolve()")
            success = False

        if "clean=False" in fixed_code:
            print("✅ Uses clean=False")
        else:
            print("⚠️  Missing clean=False (may cause BRep_API error)")

        # Check for correct parameters
        if "moveTo(50, 0)" in fixed_code:
            print("✅ Correctly extracted major radius 50 from prompt")
        else:
            print("⚠️  Major radius may not be correct")

        if "circle(8)" in fixed_code:
            print("✅ Correctly extracted minor radius 8 from prompt")
        else:
            print("⚠️  Minor radius may not be correct")

        # Check that multi-line statement was removed
        if "result = (cq.Workplane" in fixed_code and ".circle(8)" in fixed_code and ".revolve(360))" in fixed_code:
            print("❌ Multi-line revolve statement NOT removed!")
            success = False
        else:
            print("✅ Multi-line revolve statement removed")

        # Check for balanced parens
        if fixed_code.count('(') != fixed_code.count(')'):
            print(f"❌ Unbalanced parentheses! ( count: {fixed_code.count('(')}, ) count: {fixed_code.count(')')}")
            success = False
        else:
            print("✅ Balanced parentheses")

        print()
        if success:
            print("✅ Torus healer SUCCESSFULLY fixed missing moveTo!")
        else:
            print("❌ Torus healer failed!")

        return success

    except Exception as e:
        print(f"\n❌ EXCEPTION during healing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_torus_healer())
    sys.exit(0 if success else 1)
