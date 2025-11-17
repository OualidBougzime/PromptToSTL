#!/usr/bin/env python3
"""
Test glass healing with chained syntax conversion
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import SelfHealingAgent, WorkflowContext


def test_glass_chained_to_split():
    """Test that chained glass syntax is converted to split syntax"""
    print("\n" + "="*80)
    print("TEST: Convert chained glass syntax to split syntax")
    print("="*80)

    # Chained code (PROBLEMATIC)
    chained_code = """
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

    # Prompt
    prompt = "Create a drinking glass: make an outer cylinder radius 35 mm height 100 mm, subtract an inner cylinder radius 32.5 mm height 92 mm to leave an 8 mm solid bottom, then fillet the rim 1 mm"

    # Create healing agent
    healing = SelfHealingAgent()
    context = WorkflowContext(prompt=prompt)

    # Apply healing
    fixed_code = healing._basic_fixes(chained_code, [error], context)

    print("ORIGINAL CODE (chained):")
    print("-" * 80)
    print(chained_code)
    print("-" * 80)

    print("\nFIXED CODE (should be split):")
    print("-" * 80)
    print(fixed_code)
    print("-" * 80)

    # Verifications
    success = True

    if ".cutBlind(-(100" in fixed_code or ".cutBlind(-(100.0" in fixed_code:
        print("✅ Uses cutBlind with formula -(H - BOTTOM)")
    else:
        print("❌ Missing cutBlind with formula")
        success = False

    # Check for split syntax (multiple 'result =' lines)
    result_count = fixed_code.count('result =')
    if result_count >= 3:
        print(f"✅ Uses split syntax ({result_count} 'result =' assignments)")
    else:
        print(f"❌ Still uses chained syntax (only {result_count} 'result =' assignments)")
        success = False

    if "Drinking glass (fixed from chained syntax)" in fixed_code:
        print("✅ Contains fix comment")
    else:
        print("❌ Missing fix comment")
        success = False

    if "faces(\">Z\").workplane().circle(32.5).cutBlind" in fixed_code.replace(' ', '').replace('\n', ''):
        print("✅ Correct cut pattern")
    else:
        print("❌ Wrong cut pattern")
        success = False

    print()
    if success:
        print("✅ Chained to split conversion SUCCESSFUL!")
    else:
        print("❌ Chained to split conversion FAILED!")

    return success


if __name__ == "__main__":
    success = test_glass_chained_to_split()
    sys.exit(0 if success else 1)
