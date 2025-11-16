#!/usr/bin/env python3
"""
Test correct revolve approach for hemispherical bowl
"""
import cadquery as cq
from pathlib import Path

# Parameters
radius = 40  # Bowl radius (mm)
base_thickness = 3  # Base thickness (mm)
wall_thickness = 3  # Wall thickness (mm)

# Method 1: Revolve with proper profile (creates bowl with solid base)
print("Method 1: Revolve with profile (base + arc)")
profile = (
    cq.Workplane("XZ")  # Work in XZ plane for revolve around Z axis
    .moveTo(0, 0)  # Start at origin
    .lineTo(radius - wall_thickness, 0)  # Inner bottom
    .lineTo(radius - wall_thickness, base_thickness)  # Go up to base top
    .threePointArc((radius - wall_thickness, radius - wall_thickness), (0, radius - wall_thickness))  # Semicircle inner
    .lineTo(0, radius)  # Top outer edge
    .threePointArc((radius, radius), (radius, 0))  # Semicircle outer
    .lineTo(radius, 0)  # Bottom outer
    .close()  # Complete the profile
)
bowl_method1 = profile.revolve(360, (0, 0, 0), (0, 1, 0))  # Revolve around Y axis

# Export Method 1
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path1 = output_dir / "bowl_revolve_method1.stl"
cq.exporters.export(bowl_method1, str(output_path1))
print(f"✅ Method 1 exported to: {output_path1}")

# Method 2: Simple sphere + cut + shell (current healer approach)
print("\nMethod 2: Sphere + cut + shell")
bowl = cq.Workplane("XY").sphere(radius)
cutter = cq.Workplane("XY").workplane(offset=0.1).box(radius*3, radius*3, radius*2, centered=True)
bowl = bowl.cut(cutter)
bowl_method2 = bowl.shell(-wall_thickness)

# Export Method 2
output_path2 = output_dir / "bowl_sphere_method2.stl"
cq.exporters.export(bowl_method2, str(output_path2))
print(f"✅ Method 2 exported to: {output_path2}")

# Method 3: Simpler revolve (semicircle profile only - hollow from start)
print("\nMethod 3: Simple semicircle revolve")
profile3 = (
    cq.Workplane("XZ")
    .moveTo(radius - wall_thickness, base_thickness)  # Start at inner base top
    .lineTo(radius - wall_thickness, base_thickness)  # (same point)
    .threePointArc((radius - wall_thickness, radius - wall_thickness), (0, radius - wall_thickness))  # Inner arc
    .lineTo(0, radius)  # Go to outer top
    .threePointArc((radius, radius), (radius, base_thickness))  # Outer arc
    .lineTo(radius - wall_thickness, base_thickness)  # Complete
    .close()
)
bowl_method3 = profile3.revolve(360, (0, 0, 0), (0, 1, 0))

# Export Method 3
output_path3 = output_dir / "bowl_revolve_method3.stl"
cq.exporters.export(bowl_method3, str(output_path3))
print(f"✅ Method 3 exported to: {output_path3}")

print("\n" + "="*80)
print("Compare the three methods:")
print("  Method 1: Full revolve profile with base")
print("  Method 2: Sphere + cut + shell (current fix)")
print("  Method 3: Simpler revolve profile")
print("="*80)
