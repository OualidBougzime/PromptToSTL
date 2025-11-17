#!/usr/bin/env python3
"""
Test the corrected spring generation code
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import SelfHealingAgent, WorkflowContext

def test_spring_generation():
    """Test that spring healing generates correct code with split()"""
    print("\n" + "="*80)
    print("TEST: Spring generation with proper trimming using split()")
    print("="*80)

    # Bad code that will be replaced
    bad_code = """
import cadquery as cq
from pathlib import Path

# Wrong approach
result = cq.Workplane("XY").circle(1.5).extrude(80)

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "spring.stl"
cq.exporters.export(result, str(output_path))
"""

    # Error that triggers spring fix
    error = "SEMANTIC ERROR: Spring needs Wire.makeHelix(pitch, height, radius) to create helix path"

    # Prompt
    prompt = "Create a helical spring by sweeping a circle radius 1.5 mm along a right-hand helix with major radius 20 mm, pitch 8 mm, and 10 turns, then trim both ends flat"

    # Create healing agent
    healing = SelfHealingAgent()
    context = WorkflowContext(prompt=prompt)

    # Apply healing
    fixed_code = healing._basic_fixes(bad_code, [error], context)

    print("GENERATED CODE:")
    print("-" * 80)
    print(fixed_code)
    print("-" * 80)

    # Verifications
    success = True

    if "Wire.makeHelix" in fixed_code:
        print("✅ Contains Wire.makeHelix")
    else:
        print("❌ Missing Wire.makeHelix")
        success = False

    if ".center(" in fixed_code and ", 0)" in fixed_code:
        print("✅ Contains .center(..., 0) for positioning")
    else:
        print("❌ Missing .center() for positioning")
        success = False

    if ".split(" in fixed_code:
        print("✅ Contains .split() for trimming")
    else:
        print("❌ Missing .split() for trimming")
        success = False

    if "margin" in fixed_code:
        print("✅ Contains margin calculation")
    else:
        print("❌ Missing margin")
        success = False

    if "keepTop=True" in fixed_code and "keepBottom=False" in fixed_code:
        print("✅ Contains correct split parameters (keepTop=True, keepBottom=False)")
    else:
        print("❌ Missing or wrong split parameters")
        success = False

    if "keepTop=False" in fixed_code and "keepBottom=True" in fixed_code:
        print("✅ Contains correct split parameters (keepTop=False, keepBottom=True)")
    else:
        print("❌ Missing or wrong split parameters")
        success = False

    # Check it doesn't have the bad extrude approach
    lines_with_extrude = [line for line in fixed_code.split('\n') if '.extrude(' in line and 'Export' not in line]
    if not lines_with_extrude:
        print("✅ Does NOT contain bad .extrude() for trimming")
    else:
        print(f"❌ Still contains .extrude() for trimming: {lines_with_extrude}")
        success = False

    print()
    if success:
        print("✅ Spring generation SUCCESSFUL!")
    else:
        print("❌ Spring generation FAILED!")

    return success

if __name__ == "__main__":
    success = test_spring_generation()
    sys.exit(0 if success else 1)
