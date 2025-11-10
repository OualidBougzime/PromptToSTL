#!/bin/bash

# 🔍 Script de Vérification Ollama pour PromptToSTL
# Exécutez ce script après avoir installé Ollama pour vérifier que tout fonctionne

echo "🔍 Vérification de l'installation Ollama..."
echo ""

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Compteur de succès
SUCCESS=0
TOTAL=0

# Test 1 : Ollama est installé
echo "📦 Test 1/5 : Vérification de l'installation d'Ollama..."
TOTAL=$((TOTAL + 1))
if command -v ollama &> /dev/null; then
    VERSION=$(ollama --version 2>&1 | head -n 1)
    echo -e "${GREEN}✅ Ollama est installé : $VERSION${NC}"
    SUCCESS=$((SUCCESS + 1))
else
    echo -e "${RED}❌ Ollama n'est pas installé${NC}"
    echo "   → Installez avec : curl -fsSL https://ollama.com/install.sh | sh"
    echo "   → Ou téléchargez depuis : https://ollama.com/download"
fi
echo ""

# Test 2 : Ollama est en cours d'exécution
echo "🚀 Test 2/5 : Vérification qu'Ollama est lancé..."
TOTAL=$((TOTAL + 1))
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama est accessible sur http://localhost:11434${NC}"
    SUCCESS=$((SUCCESS + 1))
else
    echo -e "${RED}❌ Ollama ne répond pas${NC}"
    echo "   → Lancez dans un terminal séparé : ollama serve"
    echo "   → Attendez le message : 'Ollama is running'"
fi
echo ""

# Test 3 : Modèles nécessaires sont téléchargés
echo "📚 Test 3/5 : Vérification des modèles LLM..."
TOTAL=$((TOTAL + 1))

# Lire les modèles depuis .env
if [ -f ".env" ]; then
    ARCHITECT_MODEL=$(grep "COT_ARCHITECT_MODEL=" .env | cut -d '=' -f2)
    PLANNER_MODEL=$(grep "COT_PLANNER_MODEL=" .env | cut -d '=' -f2)
    SYNTHESIZER_MODEL=$(grep "COT_SYNTHESIZER_MODEL=" .env | cut -d '=' -f2)

    echo "Modèles configurés dans .env :"
    echo "  - Architect: $ARCHITECT_MODEL"
    echo "  - Planner: $PLANNER_MODEL"
    echo "  - Synthesizer: $SYNTHESIZER_MODEL"
    echo ""

    # Vérifier si les modèles sont installés
    if ollama list > /dev/null 2>&1; then
        MODELS_LIST=$(ollama list)

        MISSING_MODELS=()

        if echo "$MODELS_LIST" | grep -q "$ARCHITECT_MODEL"; then
            echo -e "${GREEN}✅ $ARCHITECT_MODEL est installé${NC}"
        else
            echo -e "${RED}❌ $ARCHITECT_MODEL n'est pas installé${NC}"
            MISSING_MODELS+=("$ARCHITECT_MODEL")
        fi

        if echo "$MODELS_LIST" | grep -q "$PLANNER_MODEL"; then
            echo -e "${GREEN}✅ $PLANNER_MODEL est installé${NC}"
        else
            echo -e "${RED}❌ $PLANNER_MODEL n'est pas installé${NC}"
            MISSING_MODELS+=("$PLANNER_MODEL")
        fi

        if echo "$MODELS_LIST" | grep -q "$SYNTHESIZER_MODEL"; then
            echo -e "${GREEN}✅ $SYNTHESIZER_MODEL est installé${NC}"
        else
            echo -e "${RED}❌ $SYNTHESIZER_MODEL n'est pas installé${NC}"
            MISSING_MODELS+=("$SYNTHESIZER_MODEL")
        fi

        if [ ${#MISSING_MODELS[@]} -eq 0 ]; then
            SUCCESS=$((SUCCESS + 1))
        else
            echo ""
            echo "Téléchargez les modèles manquants avec :"
            for model in "${MISSING_MODELS[@]}"; do
                echo "  ollama pull $model"
            done
        fi
    else
        echo -e "${RED}❌ Impossible de lister les modèles (Ollama non lancé ?)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Fichier .env introuvable${NC}"
fi
echo ""

# Test 4 : Configuration .env
echo "⚙️  Test 4/5 : Vérification de la configuration..."
TOTAL=$((TOTAL + 1))
if [ -f ".env" ]; then
    if grep -q "COT_ARCHITECT_MODEL=" .env && \
       grep -q "COT_PLANNER_MODEL=" .env && \
       grep -q "COT_SYNTHESIZER_MODEL=" .env && \
       grep -q "OLLAMA_BASE_URL=" .env; then
        echo -e "${GREEN}✅ Fichier .env correctement configuré${NC}"
        SUCCESS=$((SUCCESS + 1))
    else
        echo -e "${RED}❌ Variables manquantes dans .env${NC}"
        echo "   → Vérifiez COT_ARCHITECT_MODEL, COT_PLANNER_MODEL, COT_SYNTHESIZER_MODEL"
    fi
else
    echo -e "${RED}❌ Fichier .env introuvable${NC}"
    echo "   → Créez un fichier .env à la racine du projet"
fi
echo ""

# Test 5 : Test de génération avec un modèle
echo "🧪 Test 5/5 : Test de génération avec Architect..."
TOTAL=$((TOTAL + 1))
if [ -n "$ARCHITECT_MODEL" ] && ollama list 2>/dev/null | grep -q "$ARCHITECT_MODEL"; then
    echo "Génération d'un test simple avec $ARCHITECT_MODEL..."
    TEST_OUTPUT=$(ollama run "$ARCHITECT_MODEL" "Write only the word 'WORKING' and nothing else" 2>&1 | head -n 1)
    if [ -n "$TEST_OUTPUT" ]; then
        echo -e "${GREEN}✅ Le modèle répond : $TEST_OUTPUT${NC}"
        SUCCESS=$((SUCCESS + 1))
    else
        echo -e "${RED}❌ Le modèle ne répond pas${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Test ignoré (modèle non disponible)${NC}"
fi
echo ""

# Résumé
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RÉSULTAT : $SUCCESS/$TOTAL tests réussis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $SUCCESS -eq $TOTAL ]; then
    echo -e "${GREEN}🎉 Installation complète ! Ollama est prêt à l'emploi${NC}"
    echo ""
    echo "Prochaines étapes :"
    echo "  1. Redémarrez le backend : cd backend && python main.py"
    echo "  2. Testez avec : 'Generate a torus with major radius 40mm and minor radius 10mm'"
    echo "  3. Vérifiez les logs : pas de message 'fallback'"
elif [ $SUCCESS -ge 3 ]; then
    echo -e "${YELLOW}⚠️  Installation presque complète (quelques avertissements)${NC}"
    echo "   → Corrigez les erreurs ci-dessus puis relancez ce script"
else
    echo -e "${RED}❌ Installation incomplète${NC}"
    echo "   → Suivez les instructions dans INSTALL_OLLAMA.md"
    echo "   → Corrigez les erreurs ci-dessus puis relancez ce script"
fi
echo ""

# Informations supplémentaires
if [ $SUCCESS -lt $TOTAL ]; then
    echo "📚 Ressources utiles :"
    echo "  - Guide d'installation : INSTALL_OLLAMA.md"
    echo "  - Dépannage : TROUBLESHOOTING.md"
    echo "  - Tests LLM : TEST_LLM.md"
fi

exit $((TOTAL - SUCCESS))
