#!/usr/bin/env python3
"""
Test to compare chained vs split syntax for glass generation
"""

print("ISSUE: Chained syntax with cutBlind() might not work correctly")
print("=" * 80)

chained_code = """
# Chained syntax (POSSIBLY BROKEN):
result = (cq.Workplane("XY")
           .circle(35)
           .extrude(100)
           .faces(">Z")
           .workplane()
           .circle(32.5)
           .cutBlind(-92)     # ❌ Might not work in chain
           .edges(">Z")
           .fillet(1))
"""

split_code = """
# Split syntax (WORKS - user's code):
result = cq.Workplane("XY").circle(35).extrude(100)
result = result.faces(">Z").workplane().circle(32.5).cutBlind(-92)  # ✅ Works
result = result.edges(">Z").fillet(1)
"""

print("\nChained syntax:")
print("-" * 80)
print(chained_code)

print("\nSplit syntax (USER'S WORKING CODE):")
print("-" * 80)
print(split_code)

print("\n" + "=" * 80)
print("HYPOTHESIS:")
print("The chained syntax might cause cutBlind() to not work correctly because")
print("the workplane context gets lost or the cut operation returns the wrong object.")
print()
print("SOLUTION:")
print("The healer should generate split syntax like the user's code, not chained syntax.")
print("=" * 80)
