#!/usr/bin/env python3
"""
Test different approaches for helical spring generation
"""

print("Testing different spring generation approaches...")
print("=" * 80)

# Approach 1: Original generated code (BROKEN - produces cylinder)
approach1 = """
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20)
result = cq.Workplane("XY")
result = result.circle(1.5)
result = result.sweep(path, isFrenet=True)
"""

# Approach 2: Healer version (should work)
approach2 = """
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20, lefthand=False)
result = cq.Workplane("XY").circle(1.5).sweep(path, isFrenet=True)
"""

# Approach 3: Position circle at helix start with moveTo
approach3 = """
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20)
result = cq.Workplane("XY").moveTo(20, 0).circle(1.5).sweep(path, isFrenet=True)
"""

# Approach 4: Create circle in YZ plane at x=20
approach4 = """
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20)
result = cq.Workplane("YZ").center(20, 0).circle(1.5).sweep(path, isFrenet=True)
"""

# Approach 5: Create circle at first point of helix
approach5 = """
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20)
# Get first point and tangent of helix
start_point = path.startPoint()
# Create workplane at helix start, perpendicular to helix
result = cq.Workplane("XY").center(start_point.x, start_point.y).circle(1.5).sweep(path, isFrenet=True)
"""

print("Approach 1 (BROKEN):")
print(approach1)
print()

print("Approach 2 (Healer - should work):")
print(approach2)
print()

print("Approach 3 (Move circle to helix start):")
print(approach3)
print()

print("Approach 4 (Create in YZ plane at x=20):")
print(approach4)
print()

print("Approach 5 (Use helix start point):")
print(approach5)
print()

print("=" * 80)
print("KEY INSIGHT:")
print("The makeHelix creates a helix starting at (radius, 0, 0).")
print("A circle created in XY plane at origin (0,0,0) might not sweep correctly.")
print("The circle needs to be at the helix start point (20, 0, 0).")
print()
print("Try: .center(20, 0) or .moveTo(20, 0) before .circle(1.5)")
