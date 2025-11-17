#!/usr/bin/env python3
"""
Show the exact code that SHOULD be generated for a drinking glass
"""

print("=" * 80)
print("CODE ATTENDU pour un verre (DOIT être généré par le système):")
print("=" * 80)

expected_code = """import cadquery as cq
from pathlib import Path

# Drinking glass (fixed from chained syntax)
# Outer cylinder
result = cq.Workplane("XY").circle(35.0).extrude(100.0)

# Hollow interior, leaving 8.0mm solid bottom
result = result.faces(">Z").workplane().circle(32.5).cutBlind(-(100.0 - 8.0))

# Fillet rim edges
result = result.edges(">Z").fillet(1.0)

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "drinking_glass_no_handle.stl"
cq.exporters.export(result, str(output_path))
print(f"✅ STL exported to: {output_path}")
"""

print(expected_code)

print("=" * 80)
print("POINTS CLÉS:")
print("=" * 80)
print("✓ Syntaxe SÉPARÉE (3 lignes 'result =')")
print("✓ faces('>Z') sélectionne la face DU HAUT")
print("✓ cutBlind(-(100.0 - 8.0)) = cutBlind(-92.0)")
print("✓ Coupe 92mm vers le bas depuis le haut")
print("✓ Laisse 8mm de fond solide")
print()
print("RÉSULTAT: Verre ouvert sur le dessus, fermé sur le fond")
print("=" * 80)
