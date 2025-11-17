#!/usr/bin/env python3
"""
Test to debug helical spring generation issue
"""

# The generated code that produces a cylinder
code_generated = """
import cadquery as cq
from pathlib import Path

# Create a helix with major radius 20 mm, pitch 8 mm, and 10 turns
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20)

# Base workplane for the circle to be swept
result = cq.Workplane("XY")

# Create a circle with radius 1.5 mm
result = result.circle(1.5)

# Sweep the circle along the helix path
result = result.sweep(path, isFrenet=True)

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated_spring.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
"""

# The correct code that should work (healer version)
code_healer = """
import cadquery as cq
from pathlib import Path

# Helical spring using Wire.makeHelix + sweep
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20, lefthand=False)
result = cq.Workplane("XY").circle(1.5).sweep(path, isFrenet=True)

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "healer_spring.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
"""

# Alternative approach: position circle at helix start
code_alternative = """
import cadquery as cq
from pathlib import Path

# Create helix path
helix = cq.Wire.makeHelix(pitch=8, height=80, radius=20, lefthand=False)

# Create circle at the start point of the helix
# The helix starts at (radius, 0, 0)
result = (cq.Workplane("YZ")  # Use YZ plane so circle is perpendicular to X axis
          .center(20, 0)  # Position at (x=20, z=0)
          .circle(1.5)
          .sweep(helix, isFrenet=True))

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "alternative_spring.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
"""

print("Generated code (produces cylinder):")
print("=" * 80)
print(code_generated)
print()

print("Healer code (should work):")
print("=" * 80)
print(code_healer)
print()

print("Alternative code (explicit positioning):")
print("=" * 80)
print(code_alternative)
print()

print("ANALYSIS:")
print("-" * 80)
print("The issue is likely that the circle needs to be positioned at the")
print("helix start point. Wire.makeHelix creates a helix starting at")
print("(radius, 0, 0), but a circle in XY plane at origin is at (0, 0, 0).")
print()
print("CadQuery's sweep with isFrenet=True should handle this automatically,")
print("but there might be a bug or the circle needs to be created differently.")
