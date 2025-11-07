# api/api.py
# Este archivo contiene el endpoint de la API que recibe un JSON con el mensaje del usuario y devuelve la respuesta del agent, usado para el despliegue en Cloud Run e integración con el frontend.
import os
import sys

# Configurar el path para importar módulos desde la carpeta raíz
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi import UploadFile, File, Form
from fastapi.responses import JSONResponse
from json.decoder import JSONDecodeError
from datetime import datetime
from multiagent.main import process_message_multiagent

# from multiagent.sensors.multimedia_capture import MultimediaSensorCapture (aun no se usa)
from multiagent.agents.agent_electrovalvula import AgentElectrovalvula
from multiagent.vision.image_analyzer import ImageAnalyzer
from config import GEMINI_API_KEY, MONGO_URI
from multiagent.memory.mongodb_memory import MongoMemory

app = FastAPI(
    title="API de Detección de Anomalías en Electroválvulas",
    description="API para detección de anomalías usando LLM y sensores multimodales",
    version="1.0.0",
)

# Modelos Pydantic para validación de datos


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    agent_used: str
    rag_activated: Optional[bool] = None


class AnomalyDetectionRequest(BaseModel):
    location: str
    temperature: Optional[float] = None
    pressure: Optional[float] = None


class AnomalyDetectionResponse(BaseModel):
    analysis_result: dict
    timestamp: str
    method: str


class BaselineSampleRequest(BaseModel):
    location: str
    temperature: Optional[float] = None
    pressure: Optional[float] = None


class BaselineSampleResponse(BaseModel):
    message: str


# Endpoint principal de chat multiagente
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint que recibe un JSON con:
        {
            "user_id": "abc123",
            "message": "Hola"
        }
    y devuelve la respuesta del agente multiagente en JSON:
        {
            "response": "Hola, ¿en qué puedo ayudarte?",
            "agent_used": "main",
            "rag_activated": false
        }
    """
    try:
        state = {"query": request.message, "user_id": request.user_id}
        result = process_message_multiagent(state)

        # Si result es un dict con información extendida, extraer los valores
        if isinstance(result, dict):
            return ChatResponse(
                response=result.get("response", ""),
                agent_used=result.get("agent_used", "unknown"),
                rag_activated=result.get("rag_activated"),
            )
        else:
            # Compatibilidad con formato anterior (solo string)
            return ChatResponse(
                response=result, agent_used="unknown", rag_activated=None
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error procesando mensaje: {str(e)}"
        )


# Comento metodos que aun no se usan

'''@app.post("/detect_anomaly", response_model=AnomalyDetectionResponse)
async def detect_anomaly_endpoint(request: AnomalyDetectionRequest):
    """Detección de anomalías usando inteligencia del LLM"""

    try:
        metadata = {
            "location": request.location,
            "temperature": request.temperature,
            "pressure": request.pressure
        }

        result = process_anomaly_detection(metadata)

        return AnomalyDetectionResponse(
            analysis_result=result,
            timestamp=datetime.now().isoformat(),
            method="LLM-based_reasoning"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en detección de anomalías: {str(e)}")

@app.post("/baseline/add_sample", response_model=BaselineSampleResponse)
async def add_baseline_sample_endpoint(request: BaselineSampleRequest):
    """Añade muestra de baseline"""

    try:
        metadata = {
            "location": request.location,
            "temperature": request.temperature,
            "pressure": request.pressure
        }

        add_baseline_sample(metadata)
        return BaselineSampleResponse(message="Muestra de baseline añadida exitosamente")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error añadiendo muestra baseline: {str(e)}")

@app.get("/test_sensors")
async def test_sensors_endpoint():
    """Endpoint para probar que los sensores están funcionando"""
    try:
        sensor_capture = MultimediaSensorCapture()
        test_results = sensor_capture.test_sensors()

        return {
            "sensor_status": test_results,
            "system_ready": test_results["camera"] and test_results["microphone"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "sensor_status": {"camera": False, "microphone": False, "errors": [str(e)]},
            "system_ready": False,
            "timestamp": datetime.now().isoformat()
        }
        '''


# Endpoint raíz para verificar que la API está funcionando
@app.get("/")
async def root():
    return {
        "message": "API Multiagente Edgemant operativa",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {"chat": "POST /chat - Chat conversacional con el agente"},
    }


# Endpoint para análisis de imagen de electroválvula
@app.post("/analyze_image")
async def analyze_image_endpoint(
    user_id: str = Form(...),
    message: str = Form(None),
    image: UploadFile = File(...)
):
    try:
        image_bytes = await image.read()
        memory_db = MongoMemory(MONGO_URI)
        agent = AgentElectrovalvula(GEMINI_API_KEY, memory_db)
        history = memory_db.get_conversation(user_id)

        diagnosis = agent.run(message or "", history=history, user_id=user_id, image_bytes=image_bytes)
        memory_db.save_message(user_id, "user", message or "")
        memory_db.save_message(user_id, "agent", diagnosis)

        return {"diagnosis": diagnosis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis de imagen: {str(e)}")

'''
@app.post("/analyze_image")
async def analyze_image_endpoint(
    user_id: str = Form(...), message: str = Form(""), image: UploadFile = File(...)
):
    """
    Recibe una imagen de electroválvula (form-data), genera descripción visual y análisis técnico usando el agente especializado.
    """
    try:
        image_bytes = await image.read()

        memory_db = MongoMemory(MONGO_URI)
        agent = AgentElectrovalvula(GEMINI_API_KEY, memory_db)
        history = memory_db.get_conversation(user_id)
        # Enviar imagen y texto al agente (multimodal, usando bytes)
        diagnosis = agent.run(
            message, history=history, user_id=user_id, image_bytes=image_bytes
        )

        memory_db.save_message(user_id, "user", message)
        memory_db.save_message(user_id, "agent", diagnosis)

        return {"diagnosis": diagnosis}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error en análisis de imagen: {str(e)}"
        )
        '''


# Comentando metodo que aun no se usa
'''
@app.get("/health")
async def health_check():
    """Endpoint de health check para monitoreo"""
    try:
        from config import test_connection
        db_status = test_connection()

        return {
            "status": "healthy" if db_status else "degraded",
            "database": "connected" if db_status else "disconnected",
            "timestamp": datetime.now().isoformat(),
            "service": "anomaly_detection_api"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "service": "anomaly_detection_api"
        }
'''

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api.api:app", host="0.0.0.0", port=port, reload=True)
