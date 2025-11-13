# 🚀 Batch Runner - Exécution Automatique de Prompts CAD

Ce module permet d'exécuter automatiquement plusieurs prompts CAD et de sauvegarder tous les résultats (logs, code généré, fichiers STL).

## 📋 Fonctionnalités

- ✅ Exécution automatique de 8 prompts CAD prédéfinis
- 📝 Sauvegarde des logs d'exécution pour chaque prompt
- 💾 Sauvegarde du code Python généré pour chaque prompt
- 📊 Génération d'un rapport JSON avec tous les résultats
- ⏱️ Mesure du temps d'exécution pour chaque prompt
- 🎯 Résumé des succès/échecs à la fin

## 🎯 Utilisation Rapide

### Option 1: Script Bash (recommandé)

```bash
./run_batch.sh
```

### Option 2: Script Python Direct

```bash
python3 batch_runner.py
```

## 📂 Structure des Fichiers Générés

Après l'exécution, un dossier `batch_results/` est créé avec:

```
batch_results/
├── batch_run_YYYYMMDD_HHMMSS.log      # Logs complets de l'exécution
├── batch_results_YYYYMMDD_HHMMSS.json # Résultats structurés (JSON)
├── prompt_01_code.py                   # Code généré pour le prompt 1
├── prompt_02_code.py                   # Code généré pour le prompt 2
├── ...
└── prompt_08_code.py                   # Code généré pour le prompt 8
```

Les fichiers STL générés sont dans `backend/output/`.

## 📊 Format du Fichier JSON de Résultats

Le fichier `batch_results_*.json` contient:

```json
{
  "timestamp": "20250113_143022",
  "total_prompts": 8,
  "successful": 7,
  "failed": 1,
  "results": [
    {
      "index": 1,
      "prompt": "Create a table: make a rectangular...",
      "start_time": "2025-01-13T14:30:22.123456",
      "end_time": "2025-01-13T14:30:45.789012",
      "execution_time_seconds": 23.67,
      "success": true,
      "code": "# Code Python généré...",
      "stl_path": "/path/to/generated.stl",
      "error": null,
      "logs": [
        "[Progress 10%] Analyzing prompt...",
        "[Progress 50%] Generating code...",
        "[Progress 100%] Complete!"
      ]
    }
  ]
}
```

## 🎨 Personnalisation des Prompts

### Méthode 1: Modifier `prompts.json`

Éditez le fichier `prompts.json` pour ajouter/modifier/désactiver des prompts:

```json
{
  "prompts": [
    {
      "id": 1,
      "name": "Mon Objet",
      "enabled": true,
      "prompt": "Votre prompt personnalisé ici..."
    }
  ]
}
```

Puis mettez à jour `batch_runner.py` pour lire depuis ce fichier:

```python
# Au lieu de la liste PROMPTS hardcodée, ajoutez:
import json

with open('prompts.json', 'r') as f:
    config = json.load(f)
    PROMPTS = [p['prompt'] for p in config['prompts'] if p['enabled']]
```

### Méthode 2: Modifier directement `batch_runner.py`

Éditez la liste `PROMPTS` au début du fichier:

```python
PROMPTS = [
    "Votre premier prompt...",
    "Votre deuxième prompt...",
    # etc.
]
```

## 🔧 Configuration

### Prérequis

1. **Ollama** doit être installé et en cours d'exécution
   ```bash
   ollama serve
   ```

2. **Modèles Ollama** requis:
   ```bash
   ollama pull qwen2.5:7b
   ollama pull qwen2.5:14b
   ollama pull qwen2.5-coder:7b
   ollama pull qwen2.5-coder:14b
   ollama pull deepseek-coder:6.7b
   ollama pull deepseek-coder:33b
   ```

3. **Dépendances Python**:
   ```bash
   pip install -r requirements.txt
   ```

## 📈 Exemple de Sortie

```
==========================================
  PromptToSTL Batch Runner
==========================================

🚀 Starting batch run with 8 prompts...
   Processing 8 CAD prompts
   Results will be saved to: ./batch_results/

================================================================================
[1/8] Processing prompt:
  Create a table: make a rectangular top 200 mm × 100 mm × 15 mm, add four...
================================================================================

  [Progress 10%] Analyzing prompt structure...
  [Progress 30%] Generating CAD code...
  [Progress 70%] Validating code...
  [Progress 100%] Executing and generating STL...
  ✅ Success! STL saved to: backend/output/generated_table.stl
  📝 Code saved to: batch_results/prompt_01_code.py
  ⏱️  Execution time: 12.34s

================================================================================
[2/8] Processing prompt:
  Create a vase by revolving a smooth profile...
================================================================================

...

================================================================================
BATCH RUN SUMMARY
================================================================================
Total prompts: 8
Successful:    7 ✅
Failed:        1 ❌
Total time:    156.78s
Average time:  19.60s per prompt
================================================================================

✅ Batch execution completed successfully!
📁 Check the batch_results/ folder for:
   - Execution logs (.log files)
   - Results summary (.json files)
   - Generated code (.py files)
   - STL files (in backend/output/)
```

## 🐛 Dépannage

### Problème: "Module not found"
```bash
pip install -r requirements.txt
```

### Problème: "Ollama not found"
Installez Ollama depuis https://ollama.ai et lancez:
```bash
ollama serve
```

### Problème: Échec de certains prompts
- Consultez le fichier `.log` pour les détails
- Vérifiez que les modèles Ollama sont bien téléchargés
- Certains prompts complexes (comme Stanford Bunny) peuvent nécessiter plus de ressources

## 🎯 Exemples d'Utilisation

### Exécuter seulement certains prompts

Modifiez la liste `PROMPTS` dans `batch_runner.py`:

```python
PROMPTS = [
    "Create a table: ...",  # Garder celui-ci
    # "Create a vase: ...",  # Commenter pour sauter
]
```

### Lancer en mode silencieux

```bash
python3 batch_runner.py > /dev/null 2>&1
```

### Surveiller l'exécution en temps réel

```bash
./run_batch.sh | tee batch_execution.log
```

## 📚 Ressources

- [Documentation PromptToSTL](README.md)
- [Exemples de prompts](frontend/app.js)
- [Documentation CadQuery](https://cadquery.readthedocs.io/)

## 🤝 Contribution

Pour ajouter de nouveaux prompts de test:
1. Ajoutez-les dans `prompts.json` ou `PROMPTS` dans `batch_runner.py`
2. Testez avec `./run_batch.sh`
3. Partagez vos résultats!

---

**Note**: L'exécution complète des 8 prompts peut prendre entre 2 et 20 minutes selon la complexité et les performances de votre machine.
