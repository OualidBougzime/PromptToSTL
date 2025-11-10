# 🚀 Guide d'Installation Ollama - PromptToSTL

## ⚙️ Installation sur Votre Machine Locale

### **Pour Linux** (votre système actuel)

```bash
# Méthode 1 : Installation automatique
curl -fsSL https://ollama.com/install.sh | sh

# Méthode 2 : Installation manuelle (si curl bloqué)
# 1. Télécharger depuis https://ollama.com/download/linux
# 2. Extraire et déplacer le binaire :
sudo mv ollama /usr/local/bin/
sudo chmod +x /usr/local/bin/ollama
```

### **Pour Windows**
- Télécharger l'installateur : https://ollama.com/download/windows
- Exécuter `OllamaSetup.exe`
- Ollama démarre automatiquement au démarrage de Windows

### **Pour macOS**
```bash
# Télécharger depuis https://ollama.com/download/mac
# Ou via Homebrew :
brew install ollama
```

---

## 🚀 Étape 1 : Lancer Ollama

**IMPORTANT** : Ollama doit toujours tourner en arrière-plan pour que PromptToSTL fonctionne en mode LLM.

### **Terminal 1 : Lancer le serveur Ollama**
```bash
ollama serve
```

**Attendu** :
```
Ollama is running on http://localhost:11434
```

**NOTE** : Laissez ce terminal ouvert ! Ollama doit tourner en permanence.

---

## 📦 Étape 2 : Télécharger les Modèles LLM

**Ouvrez un NOUVEAU terminal** (le premier doit rester ouvert avec `ollama serve`).

### **Option Recommandée : Modèles 7B (Légers)**

Parfait pour développement et tests. Nécessite **16GB RAM**.

```bash
# Terminal 2
ollama pull qwen2.5:7b           # 4.7GB - Architect (analyse)
ollama pull qwen2.5-coder:7b     # 4.7GB - Planner (planification)
ollama pull deepseek-coder:6.7b  # 3.8GB - Synthesizer (génération code)
```

**Total : ~13GB de téléchargement**

**Temps estimé** : 5-15 minutes selon votre connexion

---

### **Option Haute Performance : Modèles 14B/33B**

Meilleure qualité, mais nécessite **32GB RAM** et GPU recommandé.

```bash
# Terminal 2
ollama pull qwen2.5:14b           # 8.5GB
ollama pull qwen2.5-coder:14b     # 8.5GB
ollama pull deepseek-coder:33b    # 19GB
```

**Total : ~36GB**

---

## ✅ Étape 3 : Vérifier l'Installation

### **Test 1 : Vérifier qu'Ollama répond**
```bash
curl http://localhost:11434/api/tags
```

**Attendu** : JSON avec la liste des modèles installés
```json
{
  "models": [
    {"name": "qwen2.5:7b", ...},
    {"name": "qwen2.5-coder:7b", ...},
    {"name": "deepseek-coder:6.7b", ...}
  ]
}
```

### **Test 2 : Tester un modèle**
```bash
ollama run qwen2.5:7b "Hello, write a Python function to add two numbers"
```

**Attendu** : Le modèle génère du code Python

---

## 🔧 Étape 4 : Configurer PromptToSTL

### **Si vous utilisez les modèles 7B (recommandé)**

Modifiez le fichier `.env` :

```bash
# .env
COT_ARCHITECT_MODEL=qwen2.5:7b
COT_PLANNER_MODEL=qwen2.5-coder:7b
COT_SYNTHESIZER_MODEL=deepseek-coder:6.7b
```

### **Si vous utilisez les modèles 14B/33B**

**Aucune modification nécessaire**, le `.env` est déjà configuré pour ces modèles :

```bash
COT_ARCHITECT_MODEL=qwen2.5:14b
COT_PLANNER_MODEL=qwen2.5-coder:14b
COT_SYNTHESIZER_MODEL=deepseek-coder:33b
```

---

## 🚀 Étape 5 : Redémarrer le Backend

```bash
# Terminal 3 (ou le terminal où tourne le backend)
cd /home/user/PromptToSTL/backend
python main.py
```

**Logs attendus au démarrage** :
```
INFO: Ollama available at http://localhost:11434
INFO: Chain-of-Thought agents ready (Architect, Planner, Synthesizer)
INFO: Fast-path disabled - using full LLM pipeline
```

---

## 🧪 Étape 6 : Tester la Génération Dynamique

Ouvrez l'interface web et testez ces prompts :

### **Test 1 : Formes Simples (anciennement Fast-Path)**
```
1. "Generate a torus with major radius 40mm and minor radius 10mm"
2. "Create a cylinder with radius 25mm and height 60mm"
3. "Make a sphere with radius 30mm"
```

**Logs attendus** (sans "fallback") :
```
INFO: 🧠 Using full LLM pipeline (Fast-path disabled)
INFO: 🏗️ Architect: Analyzing torus geometry...
INFO: 📐 Planner: Planning 4-step construction...
INFO: 💻 Synthesizer: Code generated (confidence: 0.85)
✅ STL exported to: output/torus_xxx.stl
```

### **Test 2 : Formes Complexes (impossible en fallback)**
```
4. "Create a hexagonal prism with side 20mm and height 50mm"
5. "Generate a gear with 15 teeth, diameter 50mm, thickness 8mm"
```

**Attendu** : Ces formes devraient maintenant fonctionner (impossible en fallback statique).

---

## 🐛 Dépannage

### **Problème : "Ollama API call failed"**

**Cause** : Ollama n'est pas lancé ou pas accessible

**Solution** :
```bash
# Vérifier qu'Ollama tourne
ps aux | grep ollama

# Si non lancé, démarrer :
ollama serve
```

### **Problème : "Model not found"**

**Cause** : Modèle pas téléchargé ou mauvais nom dans `.env`

**Solution** :
```bash
# Lister les modèles installés
ollama list

# Télécharger le modèle manquant
ollama pull qwen2.5:7b
```

### **Problème : "Out of memory"**

**Cause** : Pas assez de RAM pour les modèles 14B/33B

**Solution** : Utiliser les modèles 7B (modifiez `.env`)

---

## 📊 Comparaison : Avant vs Après Ollama

| Critère | Sans Ollama (Fallback) | Avec Ollama (LLM) ✅ |
|---------|------------------------|---------------------|
| **Formes supportées** | 5 (torus, cylinder, sphere, cone, box) | ∞ (toutes) |
| **Extraction paramètres** | ❌ Valeurs fixes | ✅ Du prompt |
| **Code dynamique** | ❌ Statique | ✅ Généré par LLM |
| **Confiance** | 50% | 80-90% |
| **Vitesse** | <1s | 2-5s |
| **Formes complexes** | ❌ Impossible | ✅ Possible |

---

## 🎯 Checklist Finale

Avant de considérer l'installation terminée :

- [ ] Ollama installé (`ollama --version` fonctionne)
- [ ] Ollama lancé (`ollama serve` tourne en arrière-plan)
- [ ] 3 modèles téléchargés (`ollama list` affiche qwen2.5, qwen2.5-coder, deepseek-coder)
- [ ] `.env` configuré avec les bons noms de modèles
- [ ] Backend redémarré
- [ ] Test torus : pas de message "fallback" dans les logs
- [ ] Test forme complexe (hexagonal prism) réussit

---

## 💡 Conseils d'Utilisation

### **Quand Ollama Tourne**
- ✅ Génération 100% dynamique
- ✅ Extraction automatique des paramètres
- ✅ Formes complexes supportées
- ✅ Haute confiance (80-90%)

### **Quand Ollama Est Arrêté**
- 🟡 Fallback automatique activé (sécurité)
- 🟡 Seulement 5 formes simples
- 🟡 Valeurs par défaut (non extraites du prompt)
- 🟡 Confiance basse (50%)

**Recommandation** : Toujours lancer `ollama serve` avant de démarrer le backend !

---

## 📞 Support

**Problèmes persistants ?**
- Consultez `TROUBLESHOOTING.md` pour erreurs détaillées
- Consultez `TEST_LLM.md` pour cas de test complets
- Vérifiez les logs du backend pour messages d'erreur

**Ressources Ollama** :
- Documentation : https://ollama.com/docs
- Modèles disponibles : https://ollama.com/library
- GitHub : https://github.com/ollama/ollama
