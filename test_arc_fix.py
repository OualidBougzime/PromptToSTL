#!/usr/bin/env python3
"""
Test arc healing with Edge.makeCircle approach
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import SelfHealingAgent, WorkflowContext


def test_arc_healing():
    """Test arc healing generates correct code"""
    print("\n" + "="*80)
    print("TEST: Arc healing with Edge.makeCircle approach")
    print("="*80)

    # Bad code
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

    # Error from Critic
    error = 'SEMANTIC ERROR: Prompt asks for ARC (annular sector / portion de couronne) but code uses missing threePointArc, lineTo, close. Use annular sector pattern: moveTo(R_ext, 0) → threePointArc(outer) → lineTo(R_int) → threePointArc(inner) → close() → extrude()'

    # Prompt
    prompt = "Create an arc radius 60 mm sweep 210 deg"

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

        if "threePointArc" in fixed_code:
            print("⚠️  Still contains threePointArc (should use Edge.makeCircle)")
            # Don't fail, but warn
        else:
            print("✅ Does NOT contain problematic threePointArc")

        print()
        if success:
            print("✅ Arc healing SUCCESSFUL!")
        else:
            print("❌ Arc healing FAILED!")

        return success

    except Exception as e:
        print(f"\n❌ EXCEPTION during healing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_arc_healing()
    sys.exit(0 if success else 1)
