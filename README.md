# PromptToSTL

Génération de modèles 3D (STL/STEP) à partir de descriptions en langage naturel. Le système utilise une architecture multi-agent avec des LLMs locaux (Ollama) pour transformer du texte en code CAD exécutable.

## Fonctionnalités

### Templates Optimisés (8 types)
Génération ultra-rapide (~2s) pour les types courants :
- **Médical** : splints (orthèses), stents cardiovasculaires
- **Mécanique** : dissipateurs thermiques, pinces robotiques
- **Architecture** : façades paramétriques, structures en nid d'abeille
- **Structures** : lattices, géométries paramétriques

### Génération Universelle (Chain-of-Thought)
Pour tout ce qui n'est pas dans les templates (~20s) :
- Engrenages, vis, écrous
- Supports, brackets, adaptateurs
- Boîtiers, enclosures
- Connecteurs, joints
- **N'importe quelle forme descriptible**

## Architecture

### 12 Agents Spécialisés

**Agents Base** (3)
- `AnalystAgent` : Détecte le type et extrait les paramètres
- `GeneratorAgent` : Génère le code depuis les templates
- `ValidatorAgent` : Exécute et valide le code

**Agents Multi-Agent** (6)
- `OrchestratorAgent` : Coordonne tout le pipeline + routing intelligent
- `DesignExpertAgent` : Valide les règles métier (Qwen2.5-Coder 7B)
- `ConstraintValidatorAgent` : Vérifie les contraintes de fabrication
- `SyntaxValidatorAgent` : Valide la syntaxe Python avant exécution
- `ErrorHandlerAgent` : Catégorise et gère les erreurs
- `SelfHealingAgent` : Corrige automatiquement le code (DeepSeek-Coder 6.7B)

**Agents Chain-of-Thought** (3)
- `ArchitectAgent` : Analyse et raisonne sur le design (Qwen2.5 14B)
- `PlannerAgent` : Crée le plan de construction (Qwen2.5-Coder 14B)
- `CodeSynthesizerAgent` : Génère le code final (DeepSeek-Coder 33B)

### Routing Intelligent

```
Prompt utilisateur
    ↓
Analyst Agent détecte le type
    ↓
    ├─ Type connu → Template (2s, local)
    └─ Type inconnu → Chain-of-Thought (20s, local)
```

## Installation

> 📚 **Guides Détaillés Disponibles** :
> - **[INSTALL_OLLAMA.md](INSTALL_OLLAMA.md)** - Guide complet d'installation d'Ollama (recommandé pour débutants)
> - **[verify_ollama.sh](verify_ollama.sh)** - Script de vérification automatique de l'installation
> - **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Résolution des erreurs courantes
> - **[TEST_LLM.md](TEST_LLM.md)** - Tests et cas d'usage

### Prérequis
- Python 3.10+
- Ollama
- 16-32 GB RAM (selon les modèles)

### 1. Installer Ollama

**Guide rapide** - Téléchargez depuis [ollama.ai](https://ollama.ai)

**Guide complet** - Voir [INSTALL_OLLAMA.md](INSTALL_OLLAMA.md) pour instructions détaillées

### 2. Télécharger les Modèles

**Configuration standard (32GB RAM)** :
```bash
ollama pull qwen2.5-coder:7b
ollama pull deepseek-coder:6.7b
ollama pull qwen2.5:14b
ollama pull qwen2.5-coder:14b
ollama pull deepseek-coder:33b
```

**Configuration légère (16GB RAM)** :
```bash
ollama pull qwen2.5-coder:7b
ollama pull deepseek-coder:6.7b
ollama pull qwen2.5:7b
```

### 3. Installer les Dépendances Python

```bash
pip install -r requirements.txt
```

### 4. Configuration

Copiez `.env.example` vers `.env` et ajustez si nécessaire :

```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Modèles pour agents multi-agent
DESIGN_EXPERT_MODEL=qwen2.5-coder:7b
CODE_LLM_MODEL=deepseek-coder:6.7b

# Modèles pour Chain-of-Thought
COT_ARCHITECT_MODEL=qwen2.5:14b
COT_PLANNER_MODEL=qwen2.5-coder:14b
COT_SYNTHESIZER_MODEL=deepseek-coder:33b
```

### 5. Lancer l'Application

```bash
# Terminal 1 : Ollama
ollama serve

# Terminal 2 : Backend
cd backend
python main.py

# Terminal 3 : Frontend (optionnel)
cd frontend
python -m http.server 3000
```

L'API sera disponible sur `http://localhost:8000`

## Utilisation

### API REST

**Endpoint principal** : `POST /api/generate`

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "create a gear with 20 teeth"}'
```

**Réponse** (Server-Sent Events) :
```json
{"type": "status", "message": "Analyzing...", "progress": 10}
{"type": "code", "code": "import cadquery as cq\n...", "progress": 70}
{"type": "complete", "mesh": {...}, "stl_path": "output/gear.stl"}
```

**Télécharger les fichiers** :
- STL : `GET /api/export/stl`
- STEP : `GET /api/export/step`

### Interface Web

Ouvrez `http://localhost:3000` dans votre navigateur.

### Exemples

```python
# Orthèse médicale (template)
{
  "prompt": "create a wrist splint 270mm long, 70mm wide, 3.5mm thick"
}

# Engrenage (Chain-of-Thought)
{
  "prompt": "create a gear with 20 teeth, 50mm diameter, 10mm thick"
}

# Support personnalisé (Chain-of-Thought)
{
  "prompt": "create a camera mount bracket for 1/4 inch screw"
}

# Forme simple (Chain-of-Thought)
{
  "prompt": "create a cube 50mm"
}
```

### 🚀 Batch Runner - Exécution Automatique

Exécutez automatiquement plusieurs prompts CAD avec logs et sauvegarde des résultats :

```bash
# Méthode simple (recommandée)
./run_batch.sh

# Ou directement avec Python
python3 batch_runner.py

# Avec fichier de prompts personnalisé
python3 batch_runner.py mes_prompts.json
```

**Fonctionnalités** :
- ✅ Exécution séquentielle de tous les prompts
- 📝 Logs complets pour chaque prompt
- 💾 Sauvegarde du code Python généré
- 📊 Rapport JSON avec résultats et métriques
- ⏱️ Mesure du temps d'exécution

**Personnalisation** : Éditez `prompts.json` pour ajouter vos propres prompts :

```json
{
  "prompts": [
    {
      "id": 1,
      "name": "Mon Objet",
      "enabled": true,
      "prompt": "Create a custom object..."
    }
  ]
}
```

**Résultats** : Tous les fichiers sont sauvegardés dans `batch_results/` :
- `batch_run_*.log` - Logs d'exécution complets
- `batch_results_*.json` - Résultats structurés avec tous les détails
- `prompt_*_code.py` - Code Python généré pour chaque prompt
- Fichiers STL dans `backend/output/`

Voir [BATCH_README.md](BATCH_README.md) pour la documentation complète.

## Performance

| Type | Temps | Coût | Mode |
|------|-------|------|------|
| Template | 1-2s | $0 | Local |
| CoT Simple | 12-15s | $0 | Local |
| CoT Moyen | 18-22s | $0 | Local |
| CoT Complexe | 25-35s | $0 | Local |

*Temps avec modèles 14B/33B sur CPU. 2-3x plus rapide avec GPU.*

## Avantages

- ✅ **100% Gratuit** - Aucun frais d'API, modèles open-source
- ✅ **100% Local** - Pas de connexion internet requise (après setup)
- ✅ **100% Privé** - Vos données restent sur votre machine
- ✅ **Illimité** - Pas de quota, pas de rate limiting
- ✅ **Flexible** - Génère n'importe quelle forme 3D

## Technologies

- **Backend** : FastAPI, Python 3.10+
- **CAD** : CadQuery 2.4
- **LLMs** : Ollama (Qwen2.5, DeepSeek-Coder)
- **Export** : STL, STEP

## Documentation

### Architecture et Système
- [COT_SYSTEM.md](COT_SYSTEM.md) - Documentation du système Chain-of-Thought
- [MULTI_AGENT_SYSTEM.md](MULTI_AGENT_SYSTEM.md) - Architecture multi-agent détaillée

### Installation et Configuration
- [INSTALL_OLLAMA.md](INSTALL_OLLAMA.md) - Guide complet d'installation d'Ollama
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Résolution des problèmes courants
- [TEST_LLM.md](TEST_LLM.md) - Tests et validation du système LLM

## Dépannage

**Ollama n'est pas accessible**
```bash
# Vérifiez qu'Ollama tourne
ollama serve

# Test
curl http://localhost:11434/api/tags
```

**Modèle non trouvé**
```bash
ollama pull qwen2.5:14b
```

**Mémoire insuffisante**

Utilisez les modèles 7B dans `.env` :
```bash
COT_ARCHITECT_MODEL=qwen2.5:7b
COT_PLANNER_MODEL=qwen2.5-coder:7b
COT_SYNTHESIZER_MODEL=deepseek-coder:6.7b
```

**Génération trop lente**

- Utilisez un GPU (2-3x plus rapide)
- Passez aux modèles 7B
- Fermez les autres applications

## Contribuer

Les contributions sont bienvenues !

1. Fork le repo
2. Créez votre branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push sur la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## Auteurs

- Développement initial et architecture multi-agent

## Remerciements

- [CadQuery](https://github.com/CadQuery/cadquery) pour le moteur CAD
- [Ollama](https://ollama.ai) pour l'infrastructure LLM locale
- [Qwen](https://github.com/QwenLM/Qwen) et [DeepSeek](https://github.com/deepseek-ai/DeepSeek-Coder) pour les modèles open-source
