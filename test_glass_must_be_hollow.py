#!/usr/bin/env python3
"""
Test glass healing with "Glass must be hollow" error
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import SelfHealingAgent, WorkflowContext


def test_glass_must_be_hollow_error():
    """Test healing with 'Glass must be hollow' error"""
    print("\n" + "="*80)
    print("TEST: Healing with 'Glass must be hollow' error")
    print("="*80)

    # Code without cutBlind (MISSING HOLLOW)
    bad_code = """
import cadquery as cq
from pathlib import Path

# Create outer cylinder
result = cq.Workplane("XY").circle(35).extrude(100)

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "glass.stl"
cq.exporters.export(result, str(output_path))
"""

    # Error from Critic
    error = 'SEMANTIC ERROR: Glass must be hollow (use .cutBlind(-depth) to cut from top)'

    # Prompt
    prompt = "Create a drinking glass: make an outer cylinder radius 35 mm height 100 mm, subtract an inner cylinder radius 32.5 mm height 92 mm to leave an 8 mm solid bottom, then fillet the rim 1 mm"

    # Create healing agent
    healing = SelfHealingAgent()
    context = WorkflowContext(prompt=prompt)

    try:
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

        if "cutBlind" in fixed_code:
            print("✅ Fixed code contains 'cutBlind'")
        else:
            print("❌ Fixed code does NOT contain 'cutBlind'")
            success = False

        if "faces(\">Z\")" in fixed_code.replace(" ", ""):
            print("✅ Fixed code contains 'faces(\">Z\")'")
        else:
            print("❌ Fixed code does NOT contain 'faces(\">Z\")'")
            success = False

        result_count = fixed_code.count('result =')
        if result_count >= 2:
            print(f"✅ Uses split syntax ({result_count} 'result =' assignments)")
        else:
            print(f"⚠️  Uses chained or single syntax ({result_count} 'result =' assignments)")

        print()
        if success:
            print("✅ Glass 'must be hollow' healing SUCCESSFUL!")
        else:
            print("❌ Glass 'must be hollow' healing FAILED!")

        return success

    except Exception as e:
        print(f"\n❌ EXCEPTION during healing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_glass_must_be_hollow_error()
    sys.exit(0 if success else 1)
