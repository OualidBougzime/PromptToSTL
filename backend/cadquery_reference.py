#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CadQuery API Reference for LLM Code Generation
===============================================
This document provides valid CadQuery methods, patterns, and common fixes
to help LLMs generate correct, working code.

IMPORTANT: Use this as a reference to avoid hallucinating non-existent methods.
"""

# ============================================================================
# CADQUERY METHOD REFERENCE
# ============================================================================

CADQUERY_VALID_METHODS = {
    # Basic primitives
    "box": {
        "signature": "box(length, width, height, [centered=(True, True, True)])",
        "example": 'result = cq.Workplane("XY").box(50, 50, 50)',
        "description": "Create a box with given dimensions"
    },
    "sphere": {
        "signature": "sphere(radius, [direct=True, angle1=-90, angle2=90, angle3=360])",
        "example": 'result = cq.Workplane("XY").sphere(25)',
        "description": "Create a sphere with given radius"
    },
    "cylinder": {
        "signature": "circle(radius).extrude(height)",
        "example": 'result = cq.Workplane("XY").circle(25).extrude(50)',
        "description": "Create a cylinder (via circle + extrude)"
    },
    "cone": {
        "signature": "circle(r1).workplane(offset=h).circle(r2).loft()",
        "example": 'result = cq.Workplane("XY").circle(30).workplane(offset=50).circle(10).loft()',
        "description": "Create a cone/frustum (via loft between circles)"
    },

    # 2D sketching
    "circle": {
        "signature": "circle(radius)",
        "example": 'result = cq.Workplane("XY").circle(25)',
        "description": "Create a circle"
    },
    "rect": {
        "signature": "rect(xLen, yLen, [centered=True])",
        "example": 'result = cq.Workplane("XY").rect(50, 30)',
        "description": "Create a rectangle"
    },
    "polygon": {
        "signature": "polygon(nSides, diameter, [circumscribed=False])",
        "example": 'result = cq.Workplane("XY").polygon(6, 50)',
        "description": "Create a regular polygon (e.g., hexagon with nSides=6)"
    },
    "ellipse": {
        "signature": "ellipse(x_radius, y_radius)",
        "example": 'result = cq.Workplane("XY").ellipse(30, 20)',
        "description": "Create an ellipse"
    },

    # 3D operations
    "extrude": {
        "signature": "extrude(distance, [combine=True, clean=True])",
        "example": 'result = cq.Workplane("XY").circle(25).extrude(50)',
        "description": "Extrude 2D shape into 3D"
    },
    "revolve": {
        "signature": "revolve([angleDegrees=360], [axisStart=(0,0,0)], [axisEnd=(0,0,1)])",
        "example": 'result = cq.Workplane("XY").moveTo(10, 0).lineTo(10, 5).lineTo(20, 5).lineTo(20, 0).close().revolve()',
        "description": "Revolve a 2D profile around an axis"
    },
    "loft": {
        "signature": "loft([ruled=False], [combine=True])",
        "example": 'result = cq.Workplane("XY").circle(30).workplane(offset=50).circle(10).loft()',
        "description": "Loft between multiple cross-sections"
    },
    "sweep": {
        "signature": "sweep(path, [multisection=False], [combine=True])",
        "example": 'path = cq.Workplane("XZ").spline([(0,0),(10,10),(20,0)])\nresult = cq.Workplane("XY").circle(5).sweep(path)',
        "description": "Sweep profile along a path"
    },

    # Boolean operations
    "union": {
        "signature": "union(toUnion, [clean=True])",
        "example": 'box1 = cq.Workplane("XY").box(50, 50, 50)\nbox2 = cq.Workplane("XY").box(30, 30, 70)\nresult = box1.union(box2)',
        "description": "Boolean union with another shape"
    },
    "cut": {
        "signature": "cut(toCut, [clean=True])",
        "example": 'result = cq.Workplane("XY").box(50, 50, 50).faces(">Z").circle(10).cutThruAll()',
        "description": "Boolean subtraction - REQUIRES toCut argument or use cutThruAll()"
    },
    "cutThruAll": {
        "signature": "cutThruAll()",
        "example": 'result = cq.Workplane("XY").box(50, 50, 50).faces(">Z").circle(10).cutThruAll()',
        "description": "Cut through entire solid"
    },
    "cutBlind": {
        "signature": "cutBlind(depth)",
        "example": 'result = cq.Workplane("XY").box(50, 50, 50).faces(">Z").circle(10).cutBlind(20)',
        "description": "Cut to a specific depth"
    },
    "intersect": {
        "signature": "intersect(toIntersect, [clean=True])",
        "example": 'box1 = cq.Workplane("XY").box(50, 50, 50)\nbox2 = cq.Workplane("XY").box(30, 30, 70)\nresult = box1.intersect(box2)',
        "description": "Boolean intersection"
    },

    # Edge modifications
    "fillet": {
        "signature": "fillet(radius)",
        "example": 'result = cq.Workplane("XY").box(50, 50, 50).edges().fillet(5)',
        "description": "Round edges with given radius"
    },
    "chamfer": {
        "signature": "chamfer(length, [length2=None])",
        "example": 'result = cq.Workplane("XY").box(50, 50, 50).edges().chamfer(5)',
        "description": "Chamfer edges"
    },

    # Workplane operations
    "workplane": {
        "signature": "workplane([offset=0], [invert=False])",
        "example": 'result = cq.Workplane("XY").circle(30).workplane(offset=50).circle(10).loft()',
        "description": "Create a new workplane at offset"
    },
    "faces": {
        "signature": 'faces([selector=">Z" | "<Z" | ">X" | etc.])',
        "example": 'result = cq.Workplane("XY").box(50, 50, 50).faces(">Z").circle(10).extrude(5)',
        "description": "Select faces for operations"
    },
    "edges": {
        "signature": 'edges([selector="|Z" | ">Z" | etc.])',
        "example": 'result = cq.Workplane("XY").box(50, 50, 50).edges("|Z").fillet(5)',
        "description": "Select edges for operations"
    },

    # Transformations
    "translate": {
        "signature": "translate((x, y, z))",
        "example": 'result = cq.Workplane("XY").box(20, 20, 20).translate((30, 0, 0))',
        "description": "Move shape by vector"
    },
    "rotate": {
        "signature": "rotate((x,y,z), (x,y,z), angleDegrees)",
        "example": 'result = cq.Workplane("XY").box(50, 20, 10).rotate((0,0,0), (0,0,1), 45)',
        "description": "Rotate around axis"
    },
    "mirror": {
        "signature": 'mirror([mirrorPlane="XY" | "YZ" | "XZ"])',
        "example": 'result = cq.Workplane("XY").box(50, 20, 10).mirror("XZ")',
        "description": "Mirror across a plane"
    },

    # Patterns
    "polarArray": {
        "signature": "polarArray(radius, startAngle, angle, count)",
        "example": 'result = cq.Workplane("XY").box(50, 50, 10).faces(">Z").workplane().polarArray(30, 0, 360, 6).circle(5).cutThruAll()',
        "description": "Circular pattern"
    },
    "rarray": {
        "signature": "rarray(xSpacing, ySpacing, xCount, yCount, [center=True])",
        "example": 'result = cq.Workplane("XY").box(100, 100, 10).faces(">Z").workplane().rarray(20, 20, 3, 3).circle(3).cutThruAll()',
        "description": "Rectangular array pattern"
    },
}

# ============================================================================
# COMMON MISTAKES AND FIXES
# ============================================================================

COMMON_ERROR_FIXES = {
    # Method doesn't exist errors
    "'Workplane' object has no attribute 'torus'": {
        "error_type": "method_not_found",
        "wrong_code": 'result = cq.Workplane("XY").torus(40, 10)',
        "correct_code": '''# Torus via revolve
circle_profile = cq.Workplane("XZ").moveTo(40, 0).circle(10)
result = circle_profile.revolve(360, (0, 0, 0), (0, 1, 0))''',
        "explanation": "CadQuery has no .torus() method. Create a torus by revolving a circle profile."
    },

    "'Workplane' object has no attribute 'regularPolygon'": {
        "error_type": "method_not_found",
        "wrong_code": 'result = cq.Workplane("XY").regularPolygon(6, 50)',
        "correct_code": 'result = cq.Workplane("XY").polygon(6, 50)',
        "explanation": "Use .polygon(nSides, diameter), not .regularPolygon()"
    },

    # Parameter errors
    "Workplane.revolve() got an unexpected keyword argument 'angle'": {
        "error_type": "wrong_parameter",
        "wrong_code": 'result = shape.revolve(angle=90)',
        "correct_code": 'result = shape.revolve(90)',  # First positional arg
        "explanation": "revolve() takes angleDegrees as first positional argument, not 'angle' kwarg"
    },

    "Workplane.loft() got an unexpected keyword argument 'closed'": {
        "error_type": "wrong_parameter",
        "wrong_code": 'result = shape.loft(closed=True)',
        "correct_code": 'result = shape.loft()',  # No 'closed' parameter
        "explanation": "loft() has no 'closed' parameter. Use 'ruled' parameter instead if needed."
    },

    # Missing arguments
    "Workplane.cut() missing 1 required positional argument: 'toCut'": {
        "error_type": "missing_argument",
        "wrong_code": 'result = box.faces(">Z").circle(10).cut()',
        "correct_code": 'result = box.faces(">Z").circle(10).cutThruAll()',
        "explanation": ".cut() requires an argument. Use .cutThruAll() or .cutBlind(depth) instead."
    },

    # Solid/workplane chain errors
    "Cannot find a solid on the stack or in the parent chain": {
        "error_type": "no_solid_in_stack",
        "wrong_code": '''result = cq.Workplane("XY")
result = result.circle(50)  # This is still 2D!
result = result.faces(">Z").circle(10).cutThruAll()  # ERROR: no solid yet''',
        "correct_code": '''result = cq.Workplane("XY")
result = result.circle(50).extrude(10)  # Make it 3D first
result = result.faces(">Z").circle(10).cutThruAll()  # Now OK''',
        "explanation": "Must have a 3D solid before using .cut() or .cutThruAll(). Use .extrude() first."
    },

    "Cannot union type '<class 'NoneType'>'": {
        "error_type": "none_in_operation",
        "wrong_code": '''part1 = cq.Workplane("XY").box(50, 50, 50)
part2 = part1.faces(">Z").circle(10).extrude(5)  # This returns modified part1, not separate
result = part1.union(part2)  # part2 is None or already merged''',
        "correct_code": '''# Option 1: Build parts separately
part1 = cq.Workplane("XY").box(50, 50, 50)
part2 = cq.Workplane("XY").transformed(offset=(0, 0, 50)).circle(10).extrude(5)
result = part1.union(part2)

# Option 2: Chain operations (usually better)
result = (cq.Workplane("XY")
    .box(50, 50, 50)
    .faces(">Z")
    .circle(10)
    .extrude(5))''',
        "explanation": "Operations modify the workplane in place. Create truly separate parts or chain operations."
    },

    # Revolve errors
    "BRep_API: command not done": {
        "error_type": "brep_failure",
        "wrong_code": '''# Attempting to revolve a closed circle (invalid)
result = cq.Workplane("XY").circle(30).revolve()''',
        "correct_code": '''# Revolve an open profile
result = (cq.Workplane("XZ")
    .moveTo(10, 0)
    .lineTo(10, 5)
    .lineTo(20, 5)
    .lineTo(20, 0)
    .close()
    .revolve())''',
        "explanation": "Revolve needs a properly formed profile. Don't revolve a circle for sphere - use .sphere() instead."
    },
}

# ============================================================================
# WORKING CODE PATTERNS
# ============================================================================

WORKING_PATTERNS = {
    "simple_box": '''import cadquery as cq
result = cq.Workplane("XY").box(50, 50, 50)''',

    "cylinder": '''import cadquery as cq
result = cq.Workplane("XY").circle(25).extrude(50)''',

    "cone_frustum": '''import cadquery as cq
result = (cq.Workplane("XY")
    .circle(40)
    .workplane(offset=80)
    .circle(10)
    .loft())''',

    "torus": '''import cadquery as cq
# Create circle profile offset from origin
profile = cq.Workplane("XZ").moveTo(40, 0).circle(10)
# Revolve around Y-axis
result = profile.revolve(360, (0, 0, 0), (0, 1, 0))''',

    "hexagonal_nut": '''import cadquery as cq
result = (cq.Workplane("XY")
    .polygon(6, 30)  # Hexagon with 30mm diameter
    .extrude(15)
    .faces(">Z")
    .circle(6)  # Thread hole
    .cutThruAll())''',

    "gear_simple": '''import cadquery as cq
import math

# Parameters
num_teeth = 20
module = 2
thickness = 10
pressure_angle = 20

# Calculate gear dimensions
pitch_diameter = num_teeth * module
outer_diameter = pitch_diameter + 2 * module

# Create gear body
result = (cq.Workplane("XY")
    .circle(outer_diameter / 2)
    .extrude(thickness))

# Add tooth profile (simplified)
tooth_width = math.pi * module / 2
for i in range(num_teeth):
    angle = i * 360 / num_teeth
    result = (result
        .faces(">Z")
        .workplane()
        .transformed(rotate=(0, 0, angle))
        .rect(tooth_width, module)
        .extrude(2))

# Central hole
result = result.faces(">Z").circle(4).cutThruAll()''',

    "bearing_housing": '''import cadquery as cq
result = (cq.Workplane("XY")
    .circle(40)  # Outer
    .extrude(40)
    .faces(">Z")
    .circle(25)  # Inner bore
    .cutThruAll()
    .faces(">Z")
    .workplane()
    .polarArray(30, 0, 360, 4)
    .circle(4)  # 4 mounting holes
    .cutThruAll())''',

    "t_joint_connector": '''import cadquery as cq
# Main tube
main = cq.Workplane("XY").circle(10).extrude(50)

# Branch tube
branch = (cq.Workplane("YZ")
    .transformed(offset=(0, 0, 25))
    .circle(10)
    .extrude(30))

# Union them
result = main.union(branch)''',
}

# ============================================================================
# HELPER FUNCTIONS FOR CODE GENERATION
# ============================================================================

def get_fix_for_error(error_message: str) -> dict:
    """Get the fix information for a given error message"""
    for err_pattern, fix_info in COMMON_ERROR_FIXES.items():
        if err_pattern in error_message:
            return fix_info
    return None


def get_method_info(method_name: str) -> dict:
    """Get information about a CadQuery method"""
    return CADQUERY_VALID_METHODS.get(method_name, None)


def generate_cadquery_reference_prompt() -> str:
    """
    Generate a comprehensive prompt section with CadQuery reference.
    Use this in LLM prompts to reduce hallucinations.
    """

    prompt = """
=== CADQUERY API REFERENCE ===

IMPORTANT: Only use these methods - they are guaranteed to exist in CadQuery.

Basic Shapes:
- box(length, width, height): Create a box
- sphere(radius): Create a sphere
- circle(radius).extrude(height): Create a cylinder
- circle(r1).workplane(offset=h).circle(r2).loft(): Create cone/frustum
- polygon(nSides, diameter): Create regular polygon (e.g., hexagon: nSides=6)

CRITICAL: These methods DO NOT EXIST (common hallucinations):
- ❌ .torus() - Use revolve instead
- ❌ .regularPolygon() - Use .polygon() instead
- ❌ .cone() - Use circle+loft pattern instead

3D Operations:
- extrude(distance): Extrude 2D to 3D
- revolve([angleDegrees]): Revolve around axis (angle is POSITIONAL arg, not kwarg!)
- loft(): Loft between sections (no 'closed' parameter!)

Boolean Operations:
- union(shape): Add shapes together
- cut(shape): Subtract shape (REQUIRES argument!)
- cutThruAll(): Cut through all (no argument needed)
- cutBlind(depth): Cut to depth
- intersect(shape): Intersection

Edge Operations:
- fillet(radius): Round edges
- chamfer(length): Chamfer edges

Workplane & Selection:
- faces(">Z"): Select top faces (">X", "<Y", etc. for other faces)
- edges("|Z"): Select vertical edges
- workplane(offset=z): Create new workplane at height

Patterns:
- polarArray(radius, startAngle, angle, count): Circular pattern
- rarray(xSpacing, ySpacing, xCount, yCount): Rectangular pattern

Common Patterns:
```python
# Torus (revolve a circle)
profile = cq.Workplane("XZ").moveTo(40, 0).circle(10)
result = profile.revolve(360, (0, 0, 0), (0, 1, 0))

# Hexagon
result = cq.Workplane("XY").polygon(6, 30).extrude(15)

# Box with holes
result = (cq.Workplane("XY")
    .box(50, 50, 50)
    .faces(">Z")
    .circle(10)
    .cutThruAll())
```

CRITICAL RULES:
1. Must create a 3D solid (via extrude/revolve/loft) before using cut/union
2. revolve() angle is POSITIONAL: revolve(90), not revolve(angle=90)
3. loft() has no 'closed' parameter
4. Use .cutThruAll() not .cut() when cutting through
5. Always chain operations properly: .method1().method2().method3()
"""

    return prompt


if __name__ == "__main__":
    # Test the reference
    print(generate_cadquery_reference_prompt())
