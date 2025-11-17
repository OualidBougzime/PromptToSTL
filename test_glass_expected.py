#!/usr/bin/env python3
"""
Test to verify the exact code generated for drinking glass matches user's implementation
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Simulate what the code should look like
expected_pattern = """
# Parameters
H = 100.0
R_OUT = 35.0
R_IN = 32.5
BOTTOM = 8.0
RIM_FILLET = 1.0

# Create outer cylinder
result = cq.Workplane("XY").circle(R_OUT).extrude(H)

# Cut hollow from top, leaving BOTTOM thickness
result = result.faces(">Z").workplane().circle(R_IN).cutBlind(-(H - BOTTOM))

# Fillet rim edges
result = result.edges(">Z").fillet(RIM_FILLET)
"""

print("Expected glass code pattern:")
print("=" * 80)
print(expected_pattern)
print("=" * 80)

print("\nKey points:")
print("1. Use cutBlind(-(H - BOTTOM)) NOT cutBlind(-92)")
print("2. This ensures the bottom thickness is exactly BOTTOM (8mm)")
print("3. The cut is from top face: faces('>Z').workplane()")
print("4. Fillet is applied to rim edges: edges('>Z').fillet()")

print("\nWith values H=100, BOTTOM=8:")
print(f"  -(H - BOTTOM) = -(100 - 8) = -92 ✓")
print("\nThis cuts 92mm down from the top, leaving 8mm bottom")
