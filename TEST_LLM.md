# 🧪 Test des Agents LLM (Fast-Path Désactivé)

## ✅ Modifications Apportées

### 1. **Fast-Path Désactivé**
- ❌ Code statique court-circuité
- ✅ Tous les prompts passent par les 3 agents LLM

### 2. **Prompts Améliorés**

#### **ArchitectAgent**
- ✅ Instructions plus claires sur l'analyse
- ✅ Extraction de paramètres renforcée
- ✅ Focus sur les primitives CadQuery

#### **PlannerAgent**
- ✅ Référence complète des opérations CadQuery
- ✅ Principes de planification (simple → complexe)
- ✅ Guide de sélection de plans (faces, edges, etc.)

#### **CodeSynthesizerAgent**
- ✅ Règles de succès critiques (8 règles)
- ✅ Patterns d'erreurs communs à éviter
- ✅ Template de structure de code
- ✅ Exemples concrets (torus, cône, engrenage)

### 3. **Paramètres LLM Optimisés**

| Agent | Modèle | Température | Max Tokens | Rôle |
|-------|--------|-------------|------------|------|
| Architect | qwen2.5:14b | 0.7 | 1000 | Créativité pour analyse |
| Planner | qwen2.5-coder:14b | 0.5 | 1500 | Balance planification |
| Synthesizer | deepseek-coder:33b | 0.3 | 2000 | Précision pour code |

---

## 🚀 Installation d'Ollama

### **Option 1 : Modèles 14B/33B (Haute qualité)**
```bash
# Lancer Ollama (terminal séparé)
ollama serve

# Télécharger les modèles (~36GB total)
ollama pull qwen2.5:14b           # 8.5GB - Architect
ollama pull qwen2.5-coder:14b     # 8.5GB - Planner
ollama pull deepseek-coder:33b    # 19GB - Synthesizer
```

**Requis** :
- RAM : 32GB minimum
- GPU : 8GB+ VRAM (ou CPU puissant)
- Disque : 40GB libres

---

### **Option 2 : Modèles 7B (Léger - RECOMMANDÉ)**
```bash
# Lancer Ollama
ollama serve

# Télécharger les modèles légers (~13GB total)
ollama pull qwen2.5:7b           # 4.7GB
ollama pull qwen2.5-coder:7b     # 4.7GB
ollama pull deepseek-coder:6.7b  # 3.8GB
```

**Modifier `.env`** :
```bash
COT_ARCHITECT_MODEL=qwen2.5:7b
COT_PLANNER_MODEL=qwen2.5-coder:7b
COT_SYNTHESIZER_MODEL=deepseek-coder:6.7b
```

**Requis** :
- RAM : 16GB
- GPU : 4GB+ VRAM (optionnel)
- Disque : 15GB libres

---

## 🧪 Tests à Effectuer

### **Test 1 : Formes Simples** (anciennement Fast-Path)

Ces formes utilisaient du code statique, maintenant elles passent par LLM :

```
1. "Create a cube with dimensions 50mm × 50mm × 50mm"
2. "Generate a cylinder with radius 25mm and height 60mm"
3. "Make a sphere with radius 30mm"
4. "Create a cone with base radius 40mm, top radius 10mm, and height 80mm"
5. "Generate a torus with major radius 40mm and minor radius 10mm"
```

**Attendu** :
```
INFO: 🧠 Using full LLM pipeline (Fast-path disabled)
INFO: 🏗️ Architect: [Description] (complexity: simple/medium)
INFO: 📐 Planner: [N] steps
INFO: 💻 Synthesizer: Code generated (confidence: 0.75-0.90)
✅ STL exported to: ...
```

---

### **Test 2 : Formes Moyennes**

```
6. "Create a hexagonal prism with side 20mm and height 50mm"
7. "Generate an L-shaped bracket 50x50x5mm with 4 mounting holes"
8. "Create a gear with 20 teeth, diameter 40mm, thickness 10mm"
```

**Attendu** :
- Architect doit identifier les primitives (polygon, box+cut, circle+polarArray)
- Planner doit créer un plan détaillé
- Synthesizer doit générer du code fonctionnel

---

### **Test 3 : Formes Complexes**

```
9. "Create a phone stand with 70° angle, base 100x80mm, slot 10mm wide"
10. "Generate a parametric vase with height 150mm, base 60mm, top 40mm, with wavy pattern"
```

**Attendu** :
- Les agents doivent "réfléchir" et décomposer le problème
- Le code généré peut être plus long (50-100 lignes)

---

## 📊 Métriques de Succès

| Métrique | Cible |
|----------|-------|
| **Taux de réussite** | >80% pour formes simples |
| **Temps de génération** | 2-5 secondes par forme |
| **Erreurs de syntaxe** | <10% (détectées par SyntaxValidator) |
| **Hallucinations** | <5% (méthodes inexistantes) |

---

## 🐛 Debugging

### **Si Ollama ne répond pas**

```bash
# Vérifier qu'Ollama tourne
curl http://localhost:11434/api/tags

# Devrait retourner la liste des modèles installés
```

### **Si les agents hallucinent**

Les agents ont maintenant des **listes exhaustives** de méthodes valides dans leurs prompts.

Si un agent invente une méthode (ex: `.torus()`), le **SyntaxValidator** ou le **ValidatorAgent** le détectera.

Le **SelfHealingAgent** tentera de corriger automatiquement :
```python
# cot_agents.py:950-1100 (SelfHealingAgent)
# Détecte et corrige :
- .torus() → revolve pattern
- .regularPolygon() → .polygon()
- revolve(angle=X) → revolve(X)
- cut() → cutThruAll()
```

---

## 📈 Prochaines Étapes

1. **Lancer Ollama** : `ollama serve`
2. **Télécharger les modèles** (7B recommandé pour commencer)
3. **Redémarrer le backend** : Tuer et relancer `python backend/main.py`
4. **Tester les 10 prompts** ci-dessus
5. **Analyser les logs** pour voir le raisonnement des agents

---

## 🎯 Objectif Final

Avoir un système **100% dynamique** où les LLMs peuvent générer **n'importe quelle forme** sans code statique, avec :

- ✅ Raisonnement transparent (logs détaillés)
- ✅ Corrections automatiques (self-healing)
- ✅ Haute fiabilité (>80% de succès)
- ✅ Extensible à l'infini (pas de limite de formes)

---

## 📝 Notes de Développement

### **Température LLM**

- **0.1-0.3** : Très déterministe (code, calculs)
- **0.5-0.7** : Balance créativité/précision (planification, analyse)
- **0.8-1.0** : Très créatif (génération artistique)

Nos réglages :
- Architect : 0.7 (créativité pour décomposer le problème)
- Planner : 0.5 (équilibre pour planifier)
- Synthesizer : 0.3 (précision pour générer du code)

### **Ajustements Possibles**

Si les agents sont trop créatifs (hallucinent) :
```python
# cot_agents.py - Lignes 177, 363, 639
temperature=0.5  # Réduire de 0.7 → 0.5 (Architect)
temperature=0.3  # Réduire de 0.5 → 0.3 (Planner)
temperature=0.1  # Réduire de 0.3 → 0.1 (Synthesizer)
```

Si les agents manquent de créativité :
- Augmenter la température
- Augmenter max_tokens
- Utiliser des modèles plus gros (14B → 33B)
