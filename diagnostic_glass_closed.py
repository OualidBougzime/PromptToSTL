#!/usr/bin/env python3
"""
Diagnostic: Why is the glass closed on both ends?
"""

print("DIAGNOSTIC: Cylindre fermé des deux côtés")
print("=" * 80)

print("\nProblème possible 1: cutBlind ne coupe pas assez profond")
print("-" * 80)
print("Si cutBlind(-(H - BOTTOM)) ne coupe pas jusqu'au fond:")
print("  H = 100, BOTTOM = 8")
print("  cutBlind(-(100 - 8)) = cutBlind(-92)")
print("  → Devrait couper 92mm depuis le haut")
print("  → Laissant 8mm au fond")
print()
print("Vérifier: Le cutBlind part-il bien du haut (faces('>Z'))?")

print("\n" + "-" * 80)
print("Problème possible 2: faces('>Z') sélectionne la mauvaise face")
print("-" * 80)
print("Après .extrude(100), le cylindre a:")
print("  - Face inférieure (Z=0)")
print("  - Face supérieure (Z=100) ← faces('>Z') devrait sélectionner celle-ci")
print("  - Face cylindrique latérale")
print()
print("workplane() sur faces('>Z') crée un plan de travail au sommet")
print("cutBlind(-92) devrait couper vers le bas depuis ce plan")

print("\n" + "-" * 80)
print("Problème possible 3: cutBlind avec combine mode")
print("-" * 80)
print("Par défaut, cutBlind utilise combine='s' (subtract)")
print("Cela devrait soustraire le cylindre intérieur")

print("\n" + "=" * 80)
print("CODE CORRECT (comme celui de l'utilisateur):")
print("=" * 80)
correct_code = """
# Outer cylinder
result = cq.Workplane("XY").circle(35).extrude(100)

# Cut hollow from top, leaving 8mm bottom
result = result.faces(">Z").workplane().circle(32.5).cutBlind(-(100 - 8))

# Fillet rim
result = result.edges(">Z").fillet(1)
"""
print(correct_code)

print("\n" + "=" * 80)
print("VÉRIFICATIONS À FAIRE:")
print("=" * 80)
print("1. Le serveur backend a-t-il été redémarré?")
print("2. Le code généré contient-il exactement '.faces(\">Z\").workplane().circle().cutBlind(-'?")
print("3. La profondeur de cut est-elle -(H - BOTTOM) ou une valeur fixe?")
print("4. Y a-t-il une erreur Python lors de l'exécution?")
print()
print("Si le code est correct mais le résultat est mauvais,")
print("le problème peut être dans CadQuery lui-même avec la syntaxe chaînée.")
print("Dans ce cas, il faut absolument utiliser la syntaxe SÉPARÉE.")
