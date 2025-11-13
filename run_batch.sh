#!/bin/bash

# Batch runner script for PromptToSTL
# Executes all CAD prompts automatically and saves logs

echo "=========================================="
echo "  PromptToSTL Batch Runner"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

# Check if backend server is running
echo "🔍 Checking if Ollama models are available..."
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Warning: Ollama not found. Make sure Ollama is installed and running."
    echo "   Visit: https://ollama.ai"
fi

# Check if requirements are installed
echo "🔍 Checking Python dependencies..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "📦 Installing requirements..."
    pip install -r requirements.txt
fi

echo ""
echo "🚀 Starting batch execution..."
echo "   Processing 8 CAD prompts"
echo "   Results will be saved to: ./batch_results/"
echo ""

# Run the batch runner
python3 batch_runner.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Batch execution completed successfully!"
    echo "📁 Check the batch_results/ folder for:"
    echo "   - Execution logs (.log files)"
    echo "   - Results summary (.json files)"
    echo "   - Generated code (.py files)"
    echo "   - STL files (in backend/output/)"
else
    echo ""
    echo "❌ Batch execution failed. Check the logs for details."
    exit 1
fi
