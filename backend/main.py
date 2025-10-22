import os
import json
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from agents import AnalystAgent, GeneratorAgent, ValidatorAgent
from multi_agent_system import OrchestratorAgent

# ========== CONFIGURATION ==========
# Charger les variables d'environnement depuis .env
load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cadamx")

app = FastAPI(title="CadaMx API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agents (3 existants)
analyst = AnalystAgent()
generator = GeneratorAgent()
validator = ValidatorAgent()

# Orchestrateur (coordonne les 9 agents: 3 existants + 6 nouveaux)
orchestrator = OrchestratorAgent(analyst, generator, validator)

# Stockage temporaire des derniers fichiers générés
_last_stl_path: Optional[str] = None
_last_step_path: Optional[str] = None
_last_app_type: Optional[str] = None


# ========== MODELS ==========
class GenerateRequest(BaseModel):
    prompt: str


# ========== HELPERS ==========
def escape_for_json(text: str) -> str:
    """
    Échappe une chaîne pour l'inclure dans du JSON.
    Important pour le code Python qui contient des newlines, quotes, etc.
    """
    if not text:
        return text
    
    return (text
        .replace('\\', '\\\\')  # Backslash d'abord
        .replace('\n', '\\n')   # Newlines
        .replace('\r', '\\r')   # Carriage returns
        .replace('\t', '\\t')   # Tabs
        .replace('"', '\\"')    # Double quotes
    )


async def send_sse_event(event_type: str, data: dict) -> str:
    """
    Formate un événement SSE.
    Retourne une chaîne prête à être envoyée.
    """
    data['type'] = event_type
    json_str = json.dumps(data, ensure_ascii=False)
    return f"data: {json_str}\n\n"


# ========== ENDPOINTS ==========

@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "service": "CadaMx API"}


@app.post("/api/generate")
async def generate_endpoint(request: GenerateRequest):
    """
    Endpoint principal de génération avec streaming SSE.
    
    Flux d'événements:
    1. type: "status" - Mises à jour de progression
    2. type: "code" - Code Python généré (peut être échappé)
    3. type: "complete" - Résultat final avec mesh, analysis, etc.
    4. type: "error" - En cas d'erreur
    """
    
    global _last_stl_path, _last_step_path, _last_app_type
    
    async def event_stream():
        try:
            log.info(f"🚀 Starting multi-agent workflow for prompt: {request.prompt[:100]}...")

            # Liste pour collecter les événements de progression
            progress_events = []

            # Callback pour envoyer les événements de progression
            async def progress_callback(event_type: str, data: dict):
                if event_type == "code":
                    # Échapper le code pour JSON
                    data["code"] = escape_for_json(data.get("code", ""))
                event = await send_sse_event(event_type, data)
                progress_events.append(event)

            # Exécuter le workflow orchestré avec les 9 agents
            result = await orchestrator.execute_workflow(
                request.prompt,
                progress_callback=progress_callback
            )

            # Envoyer tous les événements de progression
            for event in progress_events:
                yield event

            if result["success"]:
                # Succès - stocker les paths
                _last_stl_path = result.get("stl_path")
                _last_step_path = result.get("step_path")
                _last_app_type = result.get("app_type", "model")

                log.info(f"✅ Multi-agent generation successful!")
                if _last_stl_path:
                    log.info(f"  STL: {_last_stl_path}")
                if _last_step_path:
                    log.info(f"  STEP: {_last_step_path}")

                # Envoyer résultat final
                response_data = {
                    "success": True,
                    "mesh": result.get("mesh"),
                    "analysis": result.get("analysis"),
                    "code": result.get("code"),  # Code non échappé pour le résultat final
                    "app_type": result.get("app_type"),
                    "progress": 100
                }

                # Ajouter les paths si disponibles
                if _last_stl_path:
                    response_data["stl_path"] = _last_stl_path
                if _last_step_path:
                    response_data["step_path"] = _last_step_path

                # Ajouter les métadonnées du système multi-agent
                if "metadata" in result:
                    response_data["metadata"] = result["metadata"]

                yield await send_sse_event("complete", response_data)

            else:
                # Erreur - les agents ont géré l'erreur
                errors = result.get("errors", ["Unknown error"])
                log.error(f"❌ Multi-agent workflow failed: {errors}")

                yield await send_sse_event("error", {
                    "success": False,
                    "errors": errors,
                    "progress": 0,
                    "metadata": result.get("metadata", {})
                })

        except Exception as e:
            # Erreur générale non capturée
            log.error(f"❌ Orchestrator error: {e}", exc_info=True)
            yield await send_sse_event("error", {
                "success": False,
                "errors": [str(e)],
                "progress": 0
            })
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.get("/api/export/stl")
async def export_stl():
    """Télécharge le dernier fichier STL généré"""
    from pathlib import Path
    
    # Utiliser le chemin du dernier fichier généré
    if _last_stl_path and os.path.exists(_last_stl_path):
        stl_file = Path(_last_stl_path)
    else:
        # Fallback: chercher le fichier le plus récent
        output_dir = Path(__file__).parent / "output"
        stl_files = sorted(
            output_dir.glob("generated_*.stl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if stl_files:
            stl_file = stl_files[0]
        else:
            raise HTTPException(status_code=404, detail="No STL file available")
    
    # Déterminer le nom du fichier basé sur le type
    filename = f"{_last_app_type or 'model'}_generated.stl"
    
    return FileResponse(
        str(stl_file),
        media_type="application/octet-stream",
        filename=filename
    )


@app.get("/api/export/step")
async def export_step():
    """Télécharge le dernier fichier STEP généré"""
    if not _last_step_path or not os.path.exists(_last_step_path):
        raise HTTPException(status_code=404, detail="No STEP file available")
    
    filename = f"{_last_app_type or 'model'}_generated.step"
    
    return FileResponse(
        _last_step_path,
        media_type="application/octet-stream",
        filename=filename
    )


# ========== MAIN ==========
if __name__ == "__main__":
    import uvicorn
    
    # Créer le dossier output si nécessaire
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    log.info("Starting CadaMx API server...")
    log.info("Output directory: " + str(output_dir))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )