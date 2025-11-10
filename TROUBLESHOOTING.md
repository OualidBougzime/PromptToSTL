# 🔧 Troubleshooting Guide - PromptToSTL

## ❌ Erreur : "Ollama API call failed: All connection attempts failed"

### **Symptômes**
```
ERROR:cadamx.cot_agents:Ollama CoT API call failed: All connection attempts failed
WARNING:cadamx.cot_agents:Falling back to heuristic mode
ERROR:cadamx.cot_agents:❌ Architect JSON parsing failed: Expecting value: line 1 column 1
```

### **Cause**
**Ollama n'est pas lancé** ou n'est pas accessible sur `http://localhost:11434`.

---

## ✅ Solutions

### **Solution 1 : Lancer Ollama** (Recommandé)

#### **Étape 1 : Vérifier qu'Ollama est installé**
```bash
ollama --version
```

Si pas installé :
- **Windows** : https://ollama.com/download
- **Linux/Mac** : `curl -fsSL https://ollama.com/install.sh | sh`

#### **Étape 2 : Lancer Ollama (terminal séparé)**
```bash
ollama serve
```

**Attendu** :
```
Ollama is running
```

#### **Étape 3 : Télécharger les modèles LLM**

**Option A : Modèles 7B (Légers - 13GB total)**
```bash
ollama pull qwen2.5:7b           # 4.7GB - Architect
ollama pull qwen2.5-coder:7b     # 4.7GB - Planner
ollama pull deepseek-coder:6.7b  # 3.8GB - Synthesizer
```

**Option B : Modèles 14B/33B (Lourds - 36GB total)**
```bash
ollama pull qwen2.5:14b           # 8.5GB
ollama pull qwen2.5-coder:14b     # 8.5GB
ollama pull deepseek-coder:33b    # 19GB
```

#### **Étape 4 : Configurer `.env`**

Pour modèles 7B (légers) :
```bash
COT_ARCHITECT_MODEL=qwen2.5:7b
COT_PLANNER_MODEL=qwen2.5-coder:7b
COT_SYNTHESIZER_MODEL=deepseek-coder:6.7b
```

Pour modèles 14B/33B (configuration par défaut) :
```bash
COT_ARCHITECT_MODEL=qwen2.5:14b
COT_PLANNER_MODEL=qwen2.5-coder:14b
COT_SYNTHESIZER_MODEL=deepseek-coder:33b
```

#### **Étape 5 : Vérifier la connexion**
```bash
curl http://localhost:11434/api/tags
```

**Attendu** : Liste JSON des modèles installés

#### **Étape 6 : Redémarrer le backend**
```bash
# Tuer le processus Python existant (Ctrl+C)
cd backend
python main.py
```

#### **Étape 7 : Tester**
```
Prompt: "Generate a torus with major radius 40mm and minor radius 10mm"
```

**Logs attendus** :
```
INFO: 🧠 Using full LLM pipeline (Fast-path disabled)
INFO: 🏗️ Analyzing: Generate a torus...
INFO: 📐 Planning: Simple torus
INFO: 💻 Synthesizer: Code generated (confidence: 0.80-0.90)
✅ STL exported to: ...
```

---

### **Solution 2 : Mode Fallback** (Sans Ollama)

Si vous ne pouvez pas lancer Ollama, le système utilise un **fallback intelligent** qui fonctionne pour les formes simples :

**Formes supportées en fallback** :
- ✅ Torus (tore)
- ✅ Cylinder (cylindre)
- ✅ Sphere (sphère)
- ✅ Cone (cône)
- ✅ Box (cube)

**Limitations** :
- ❌ Pas de génération dynamique (code statique)
- ❌ Paramètres fixes (pas d'extraction du prompt)
- ❌ Formes complexes non supportées (engrenages, brackets, etc.)
- 🟡 Confiance : 50% (vs 80-90% avec LLM)

Le fallback génère du code Python valide mais utilise des **valeurs par défaut** :
```python
# Torus fallback
profile = cq.Workplane("XZ").moveTo(40, 0).circle(10)  # Valeurs fixes !
result = profile.revolve(360, (0, 0, 0), (0, 1, 0))
```

---

## 🐛 Autres Erreurs Courantes

### **Erreur : "Syntax validation failed"**
```
WARNING:cadamx.multi_agent:⚠️ Syntax Validation failed, retrying...
ERROR:cadamx.multi_agent:❌ Healing failed: invalid syntax
```

**Cause** : Le code généré par le LLM (ou fallback) est syntaxiquement invalide.

**Solutions** :
1. **Avec Ollama** : Le LLM peut halluciner des méthodes inexistantes
   - Solution : Améliorer les prompts système (déjà fait)
   - Solution : Ajuster la température (réduire de 0.3 → 0.1 pour Synthesizer)

2. **Sans Ollama (fallback)** : Bug dans le fallback
   - Solution : Vérifier `cot_agents.py:144-228` (fallback Synthesizer)

---

### **Erreur : "No pending wires present"**
```
ERROR: StdFail_NotDone: TopoDS_Builder::MakeCompound: No pending wires present
```

**Cause** : Tentative de `revolve()` sur un plan incorrect pour le tore.

**Solution** : Utiliser le **plan XZ** (pas XY) pour revolve autour de l'axe Y :
```python
# ✅ CORRECT
profile = cq.Workplane("XZ").moveTo(40, 0).circle(10)
result = profile.revolve(360, (0, 0, 0), (0, 1, 0))

# ❌ INCORRECT
profile = cq.Workplane("XY").moveTo(40, 0).circle(10)  # Erreur !
result = profile.revolve(360, (0, 0, 0), (0, 1, 0))
```

---

### **Erreur : "Hallucination LLM" (méthodes inexistantes)**
```
ERROR: AttributeError: 'Workplane' object has no attribute 'torus'
ERROR: AttributeError: 'Workplane' object has no attribute 'cone'
```

**Cause** : Le LLM invente des méthodes qui n'existent pas en CadQuery.

**Solution** : Le **SelfHealingAgent** corrige automatiquement :
```python
# Détecte et corrige :
- .torus() → revolve pattern
- .cone() → circle + loft
- .regularPolygon() → .polygon()
- revolve(angle=360) → revolve(360)
- cut() → cutThruAll()
```

Si correction échoue :
- Réduire la température du Synthesizer : `temperature=0.1` (ligne 639)
- Utiliser un modèle plus gros : `deepseek-coder:33b`

---

## 📊 Comparaison : LLM vs Fallback

| Critère | Avec Ollama (LLM) | Sans Ollama (Fallback) |
|---------|-------------------|------------------------|
| **Formes supportées** | ∞ (tout) | 5 (simples) |
| **Extraction paramètres** | ✅ Oui (du prompt) | ❌ Non (valeurs fixes) |
| **Génération dynamique** | ✅ Oui | ❌ Non (statique) |
| **Confiance** | 80-90% | 50% |
| **Vitesse** | 2-5s | <1s |
| **Requiert Ollama** | ✅ Oui | ❌ Non |
| **Requis RAM** | 8-16GB | Minimal |

---

## 🎯 Recommandations

### **Pour Développement**
- ✅ **Utiliser Ollama** avec modèles 7B (bon compromis vitesse/qualité)
- ✅ Tester d'abord les formes simples (cube, cylindre, sphère)
- ✅ Surveiller les logs pour détecter les hallucinations

### **Pour Production**
- ✅ **Utiliser Ollama** avec modèles 14B/33B (meilleure qualité)
- ✅ Configurer un retry automatique (déjà implémenté : max 3 tentatives)
- ✅ Monitorer les taux de succès et confiance

### **Pour Tests Rapides**
- 🟡 Le fallback peut être utilisé pour des tests basiques
- ⚠️ Mais ne représente PAS le vrai comportement du système
- ⚠️ Toujours valider avec Ollama avant déploiement

---

## 📞 Support

Si le problème persiste :
1. Vérifier les logs complets dans le terminal backend
2. Vérifier que les modèles sont bien téléchargés : `ollama list`
3. Vérifier la RAM disponible : Les modèles 14B/33B nécessitent 16-32GB
4. Consulter `TEST_LLM.md` pour les cas de test

---

## ⚙️ Configuration Avancée

### **Changer l'URL Ollama**
```bash
# .env
OLLAMA_BASE_URL=http://autre-serveur:11434
```

### **Ajuster la température LLM**
```python
# cot_agents.py

# Architect (ligne 177)
response = await self.client.generate(messages, temperature=0.5)  # 0.7 → 0.5

# Planner (ligne 363)
response = await self.client.generate(messages, temperature=0.3)  # 0.5 → 0.3

# Synthesizer (ligne 639)
response = await self.client.generate(messages, temperature=0.1)  # 0.3 → 0.1
```

**Plus bas = plus déterministe, moins de hallucinations**

### **Augmenter le nombre de retries**
```bash
# .env
MAX_RETRIES=5  # Défaut : 3
```
