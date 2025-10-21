import os
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from agents import AnalystAgent, GeneratorAgent, ValidatorAgent

# ========== CONFIGURATION ==========
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

# Agents
analyst = AnalystAgent()
generator = GeneratorAgent()
validator = ValidatorAgent()

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
            # === PHASE 1: ANALYSE ===
            log.info(f"Analyzing prompt: {request.prompt[:100]}...")
            yield await send_sse_event("status", {
                "message": "Analyzing prompt...",
                "progress": 10
            })
            
            analysis = await analyst.analyze(request.prompt)
            app_type = analysis.get('type', 'splint')
            _last_app_type = app_type
            
            yield await send_sse_event("status", {
                "message": f"Detected: {app_type.upper()}",
                "progress": 25
            })
            
            # === PHASE 2: GENERATION ===
            log.info("Generating code...")
            yield await send_sse_event("status", {
                "message": "Generating code...",
                "progress": 40
            })
            
            code, detected_type = await generator.generate(analysis)
            
            # Envoyer le code (échappé pour JSON)
            yield await send_sse_event("code", {
                "code": escape_for_json(code),
                "app_type": detected_type,
                "progress": 60
            })
            
            # === PHASE 3: VALIDATION ET EXECUTION ===
            log.info("Validating and executing...")
            yield await send_sse_event("status", {
                "message": "Validating and executing...",
                "progress": 75
            })
            
            result = await validator.validate_and_execute(code, detected_type)
            
            if result["success"]:
                # Succès - stocker les paths
                _last_stl_path = result.get("stl_path")
                _last_step_path = result.get("step_path")
                
                log.info(f"Generation successful!")
                if _last_stl_path:
                    log.info(f"  STL: {_last_stl_path}")
                if _last_step_path:
                    log.info(f"  STEP: {_last_step_path}")
                
                # Envoyer résultat final
                response_data = {
                    "success": True,
                    "mesh": result.get("mesh"),
                    "analysis": result.get("analysis"),
                    "code": code,  # Code non échappé pour le résultat final
                    "app_type": detected_type,
                    "progress": 100
                }
                
                # Ajouter les paths si disponibles (pour info frontend)
                if _last_stl_path:
                    response_data["stl_path"] = _last_stl_path
                if _last_step_path:
                    response_data["step_path"] = _last_step_path
                
                yield await send_sse_event("complete", response_data)
                
            else:
                # Erreur de validation/exécution
                errors = result.get("errors", ["Unknown validation error"])
                log.error(f"Validation failed: {errors}")
                
                yield await send_sse_event("error", {
                    "success": False,
                    "errors": errors,
                    "progress": 0
                })
        
        except Exception as e:
            # Erreur générale
            log.error(f"Generation error: {e}", exc_info=True)
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