# Améliorations de la Pipeline Chain-of-Thought (CoT)

## Vue d'ensemble

Ce document décrit les améliorations majeures apportées à la pipeline CoT pour corriger les échecs identifiés lors des tests avec des prompts complexes (table, vase, glass, spring, pipe, bowl, screw, bunny).

## Fichiers créés/modifiés

### 1. **Nouveau fichier: `backend/cot_prompts.py`**
Contient tous les prompts système améliorés et les ressources partagées :

#### Prompts système renforcés :
- **ARCHITECT_SYSTEM_PROMPT** : Analyse améliorée avec identification précise des formes
- **PLANNER_SYSTEM_PROMPT** : Schéma JSON strict avec patterns CadQuery validés
- **SYNTHESIZER_SYSTEM_PROMPT** : Code generation avec API autorisée et interdite clairement définie

#### Few-shot examples :
- `pipe` : Cylindre creux avec chamfer
- `glass` : Verre avec fond solide et rim fillet
- `spring` : Ressort hélicoïdal avec Wire.makeHelix
- `bowl` : Bol hémisphérique shellé
- `screw` : Vis avec tête hexagonale
- `vase` : Vase lofté avec shell
- `table` : Table avec 4 pieds aux coins

#### Règles du Critic :
Règles sémantiques par type d'objet (pipe, glass, vase, spring, bowl, screw, table, bunny)

#### Patterns du Healer :
Patterns de correction automatique pour erreurs courantes

### 2. **`backend/cot_agents.py` - Modifié**

#### ArchitectAgent :
- ✅ Utilise `ARCHITECT_SYSTEM_PROMPT` depuis `cot_prompts.py`
- ✅ Meilleure extraction des paramètres numériques
- ✅ Identification correcte des formes (torus, cone, cylinder, sphere, etc.)

#### PlannerAgent :
- ✅ Utilise `PLANNER_SYSTEM_PROMPT` avec schéma JSON strict
- ✅ Plans avec opérations CadQuery validées uniquement
- ✅ Patterns spécifiques pour pipe, glass, table, bowl intégrés

#### CodeSynthesizerAgent :
- ✅ Utilise `SYNTHESIZER_SYSTEM_PROMPT` avec liste exhaustive des méthodes CadQuery
- ✅ Few-shot examples injectés automatiquement selon le type d'objet détecté
- ✅ Suppression du vieux prompt (400+ lignes) - remplacé par version compacte et correcte

### 3. **`backend/multi_agent_system.py` - Modifié**

#### CriticAgent - Amélioré :
✅ **Nouvelles vérifications ajoutées** :
- `_check_glass_pattern()` : Vérifie pattern verre (outer + inner cut + fillet)
- `_check_spring_pattern()` : Vérifie Wire.makeHelix + sweep + isFrenet
- `_check_vase_pattern()` : Vérifie loft XOR revolve, shell obligatoire
- `_check_pipe_pattern()` : Vérifie hollow + faces selection
- `_check_hallucinated_methods()` : Détecte .torus(), .cylinder(), .cone(), .helix()

✅ **Import des règles** depuis `cot_prompts.CRITIC_RULES`

#### SelfHealingAgent - Déjà complet :
Le SelfHealingAgent contenait déjà des fixes détaillés (lignes 1035-1723) :
- ✅ Fix .torus() → revolve pattern
- ✅ Fix .helix() → Wire.makeHelix
- ✅ Fix revolve(angle=X) → revolve(X)
- ✅ Fix BRep_API errors (clean=False, workplane XZ pour Y-axis)
- ✅ Fixes sémantiques (table legs, hollow objects, loft+revolve conflicts)

### 4. **Nouveau fichier: `backend/sanity_checker.py`**
Module optionnel de vérification post-génération :

#### Checks implémentés :
- `check_pipe()` : Hauteur, diamètre, faces circulaires
- `check_glass()` : Hauteur, diamètre, rim edges
- `check_spring()` : Hauteur > largeur, structure hélicoïdale
- `check_bowl()` : Diamètre, hauteur hémisphérique
- `check_vase()` : Hauteur minimale
- `check_table()` : Dimensions plateau, hauteur totale

## Corrections spécifiques par prompt

### 1. TABLE ✅
**Problème** : Pieds positionnés au centre au lieu des coins
**Solution** :
- Architect : Extrait dimensions et inset
- Planner : Calcule positions coins : `±(width/2 - inset), ±(depth/2 - inset)`
- Synthesizer : Pattern avec loop sur positions des 4 coins
- Critic : Vérifie coordonnées des pieds

### 2. VASE ✅
**Problème** : JSON parsing failed, No pending wires, loft+revolve conflict
**Solution** :
- Planner : JSON schema strict, nettoie commentaires et trailing commas
- Synthesizer : Pattern loft robuste (circles à Z différents + loft + shell)
- Critic : Détecte loft+revolve conflict, vérifie shell présent
- Healer : Supprime revolve si loft existe

### 3. GLASS (Drinking) ✅
**Problème** : Ordre paramètres cylinder inversé, fillet échoue, pas creux
**Solution** :
- Synthesizer : N'utilise JAMAIS .cylinder() (n'existe pas!) → circle().extrude()
- Pattern : outer.faces(">Z").workplane().circle(inner_r).extrude(-92)
- Critic : Vérifie hollow (extrude négatif), vérifie fillet sur rim
- Healer : Remplace .cylinder() par circle+extrude, fix fillet selector

### 4. SPRING (Helical) ✅
**Problème** : .helix() n'existe pas sur Workplane
**Solution** :
- Synthesizer : Pattern correct `Wire.makeHelix(pitch, height, radius)` + `sweep(path, isFrenet=True)`
- Critic : Détecte .helix() sur Workplane, vérifie isFrenet
- Healer : Commente .helix() et suggère Wire.makeHelix

### 5. PIPE ✅
**Problème** : cutThruAll sans pending wire, chamfer fail
**Solution** :
- Synthesizer : Pattern `outer.faces(">Z").workplane().circle(inner).extrude(-height)`
- Critic : Vérifie faces() avant extrude négatif
- Healer : Remplace cutThruAll par circle+extrude, fix chamfer selector (%Circle)

### 6. BOWL (Hemispherical) ✅
**Problème** : BRep_API error sur revolve, pas hollow
**Solution** :
- Synthesizer : Pattern robuste `sphere → split(keepBottom=True) → shell(-3) → add flat bottom`
- Alternative : Revolve avec profil fermé + .close()
- Critic : Vérifie shell présent
- Healer : Fix BRep_API (clean=False, workplane XZ)

### 7. SCREW ✅
**Problème** : .placeSketch + .copy() n'existent pas
**Solution** :
- Synthesizer : Pattern simple `shaft.union(head)` avec polygon(6, diameter=2*circumradius)
- Critic : Vérifie polygon avec diamètre (pas rayon)
- Note : polygon(6, 12) pour circumradius=6

### 8. BUNNY ✅
**Problème** : Import DXF inexistant, opérations surfaciques impossibles
**Solution** :
- Synthesizer : Pattern `importers.importStl("assets/bunny.stl")` + scale from BoundingBox
- Critic : Vérifie chemin fichier
- Graceful fail si fichier manquant

## Résumé des améliorations techniques

### Architect Agent
- ✅ Extraction paramètres numériques améliorée
- ✅ Identification formes avec patterns (torus, cone, cylinder, sphere, arc)
- ✅ JSON validation stricte (no expressions, no "value" placeholder)

### Planner Agent
- ✅ Schéma JSON strict avec opérations CadQuery validées
- ✅ Patterns spécifiques intégrés (pipe, glass, table, bowl, spring)
- ✅ Nettoyage JSON (commentaires, trailing commas, math expressions)

### Synthesizer Agent
- ✅ API autorisée/interdite clairement documentée
- ✅ Few-shot examples injection automatique
- ✅ Patterns corrects pour toutes les formes testées
- ✅ Export STL systématique

### Critic Agent
- ✅ Vérifications sémantiques par type d'objet
- ✅ Détection méthodes hallucinées (.torus, .cylinder, .cone, .helix)
- ✅ Vérifications hollow objects, workflow conflicts
- ✅ Import règles depuis cot_prompts.py

### Self-Healing Agent
- ✅ Fixes automatiques pour erreurs courantes
- ✅ Fixes sémantiques (table legs, hollow, loft+revolve)
- ✅ Fixes BRep_API (clean=False, workplane)
- ✅ Removal hallucinated imports proactif

### Sanity Checker (nouveau)
- ✅ Vérifications post-génération optionnelles
- ✅ Checks dimensions, structure, cohérence géométrique
- ✅ Status : passed / warning / failed / error

## Méthodes CadQuery autorisées/interdites

### ✅ AUTORISÉES :
```python
# Primitives
.box(l, w, h), .sphere(r), .polygon(n, diameter)
.circle(r), .rect(w, h), .moveTo(x, y), .lineTo(x, y)
.threePointArc(), .radiusArc(), .close()

# 3D Operations
.extrude(distance), .loft(), .shell(thickness)
.revolve(angle_degrees)  # angle is POSITIONAL
.sweep(path, isFrenet=True)

# Modifications
.fillet(r), .chamfer(d)

# Boolean
.union(shape), .cut(shape)

# Selection
.faces(">Z"), .edges("|Z"), .workplane(offset=z)

# Advanced
Wire.makeHelix(pitch, height, radius)
importers.importStl(path), importers.importStep(path)
```

### ❌ INTERDITES (n'existent pas!) :
```python
.torus(major, minor)  # → Use revolve pattern
.cylinder(h, r)       # → Use circle(r).extrude(h)
.cone(r1, r2, h)      # → Use loft pattern
.helix(...)           # → Use Wire.makeHelix
.regularPolygon()     # → Use .polygon()
.cutThruAll()         # → Use circle().extrude(-h) avec faces selection
revolve(angle=X)      # → Use revolve(X) positional
loft(closed=True)     # → Use loft() (no closed param)
sweep(sweepAngle=X)   # → sweep() has no sweepAngle
```

## Patterns CadQuery corrects

### Pipe (hollow cylinder)
```python
outer = cq.Workplane("XY").circle(20).extrude(150)
result = outer.faces(">Z").workplane().circle(15).extrude(-150)
result = result.edges("%Circle").chamfer(1)
```

### Glass
```python
result = cq.Workplane("XY").circle(35).extrude(100)
result = result.faces(">Z").workplane().circle(32.5).extrude(-92)
result = result.edges(">Z").fillet(1)
```

### Spring
```python
path = cq.Wire.makeHelix(pitch=8, height=80, radius=20)
result = cq.Workplane("XY").circle(1.5).sweep(path, isFrenet=True)
```

### Bowl
```python
result = cq.Workplane("XY").sphere(40)
result = result.faces(">Z").workplane().split(keepTop=True, keepBottom=False)
result = result.shell(-3)
result = result.faces("<Z").workplane().circle(37).extrude(3)
result = result.edges(">Z").fillet(1)
```

### Vase (lofted)
```python
outer = (cq.Workplane("XY").circle(30)
    .workplane(offset=60).circle(22)
    .workplane(offset=120).circle(35)
    .loft())
result = outer.faces(">Z").shell(-3)
result = result.faces("<Z").workplane().circle(32).extrude(3)
```

### Table
```python
top = cq.Workplane("XY").box(200, 100, 15).translate((0, 0, 127.5))
leg = cq.Workplane("XY").circle(6).extrude(120)
result = top
for x, y in [(85,35), (-85,35), (85,-35), (-85,-35)]:
    result = result.union(leg.translate((x, y, 0)))
```

### Screw
```python
shaft = cq.Workplane("XY").circle(4).extrude(50)
head = cq.Workplane("XY").polygon(6, 12).extrude(5).translate((0,0,50))
result = shaft.union(head).edges(">Z").chamfer(0.5)
```

## Tests recommandés

Pour valider les améliorations, testez avec les prompts suivants :

1. **Table** : `Create a table: make a rectangular top 200 mm × 100 mm × 15 mm, add four cylindrical legs diameter 12 mm height 120 mm inset 15 mm from each corner under the top, and union all parts.`

2. **Vase** : `Create a vase by revolving a smooth profile with radius 30 mm at base, 22 mm at mid-height 60 mm, and 35 mm at top height 120 mm, then shell to 3 mm wall thickness and keep a flat 3 mm bottom.`

3. **Glass** : `Create a drinking glass: make an outer cylinder radius 35 mm height 100 mm, subtract an inner cylinder radius 32.5 mm height 92 mm to leave an 8 mm solid bottom, then fillet the rim 1 mm.`

4. **Spring** : `Create a helical spring by sweeping a circle radius 1.5 mm along a right-hand helix with major radius 20 mm, pitch 8 mm, and 10 turns, then trim both ends flat.`

5. **Pipe** : `Create a pipe by subtracting an inner cylinder radius 15 mm length 150 mm from an outer cylinder radius 20 mm length 150 mm, then optionally chamfer both rim edges 1 mm.`

6. **Bowl** : `Create a hemispherical bowl by revolving a semicircle radius 40 mm to form a hemisphere, then shell to 3 mm wall thickness while keeping a 3 mm bottom and fillet the rim 1 mm.`

7. **Screw** : `Create a screw: make a cylindrical shaft radius 4 mm height 50 mm, place a hexagonal head circumradius 6 mm height 5 mm on top, and union the head and shaft (optional 0.5 mm chamfer on head edges).`

8. **Bunny** : `Create the Stanford Bunny mesh, scale to overall height 70 mm, fix non-manifold edges and unify normals, then remesh to about 18 000 triangles.`

## Conclusion

Les améliorations apportées renforcent significativement la robustesse de la pipeline CoT :

✅ **Prompts système** : Basés sur les échecs réels, avec API CadQuery validée
✅ **Few-shot learning** : Exemples corrects pour chaque type d'objet
✅ **Critic** : Détection proactive des erreurs sémantiques AVANT exécution
✅ **Healer** : Corrections automatiques étendues pour erreurs courantes
✅ **Sanity checks** : Validation post-génération optionnelle

Ces changements devraient résoudre la majorité des cas d'échec documentés.
