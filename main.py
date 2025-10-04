from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from openai import OpenAI
from sheety import SheetyClient
from schema import LeadAnalysis
from body import simplify_elevenlabs_payload
from system import agent_prompt_factory
from llm import StructuredOpenAI
import ast
import logging
from datetime import datetime
import asyncio

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Inicializar cliente OpenAI (cambié a gpt-4)
llm = StructuredOpenAI(OpenAI(api_key=os.getenv("OPENAI_API_KEY")), model="gpt-5")

# Inicializar cliente Sheety
try:
    sheety_keys = ast.literal_eval(os.getenv("SHEETY_KEYS", "[]"))
    sheety_client = SheetyClient(
        name="phone",
        url=os.getenv("SHEETY_URL", ""),
        keys=sheety_keys
    )
    logger.info("Sheety client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Sheety client: {e}")
    sheety_client = None

app = FastAPI(title="Eleven Labs to Sheety Webhook", version="1.0.0")

async def process_webhook_background(webhook_data: dict, request_id: str):
    """
    Procesa el webhook en background para no bloquear la respuesta
    """
    start_time = datetime.now()
    logger.info(f"[{request_id}] Starting background processing")
    
    try:
        # 1. Simplificar payload de Eleven Labs
        try:
            data = simplify_elevenlabs_payload(webhook_data)
            logger.info(f"[{request_id}] Eleven Labs payload simplified successfully")
            print(data)
        except Exception as e:
            logger.error(f"[{request_id}] Error simplifying Eleven Labs payload: {e}")
            return
        
        # 2. Validar que tenga transcript
        if not data.get("transcript"):
            logger.warning(f"[{request_id}] No transcript found in payload")
            return
        
        transcript_length = len(data["transcript"])
        logger.info(f"[{request_id}] Transcript length: {transcript_length} characters")
        
        # 3. Generar prompts y análisis con OpenAI
        try:
            system, prompt = agent_prompt_factory(
                data["transcript"], 
                data.get("transcript_summary", "")
            )
            logger.info(f"[{request_id}] System and user prompts generated")
            
            # Esta es la parte que puede tomar tiempo
            analysis = llm.response(system, prompt, LeadAnalysis)
            logger.info(f"[{request_id}] OpenAI analysis completed successfully")
            
        except Exception as e:
            logger.error(f"[{request_id}] Error generating analysis with OpenAI: {e}")
            return
        
        # 4. Validar análisis
        if not analysis:
            logger.error(f"[{request_id}] OpenAI returned empty analysis")
            return
        
        # 5. Convertir a diccionario para Sheety
        try:
            lead_dict = analysis.model_dump(exclude_none=True)
            # Agregar timestamp y request ID
            
            if "dynamic_variables" in data and "system__time" in data["dynamic_variables"]:
                lead_dict["dateTime"] = data["dynamic_variables"]["system__time"]
            else:
                lead_dict["dateTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "dynamic_variables" in data and "system__caller_id" in data["dynamic_variables"]:
                lead_dict["phoneNumber"] = data["dynamic_variables"]["system__caller_id"]
            else:
                lead_dict["phoneNumber"] = "NA"

            logger.info(f"[{request_id}] Lead analysis converted to dict with {len(lead_dict)} fields")
            
        except Exception as e:
            logger.error(f"[{request_id}] Error converting analysis to dict: {e}")
            return
        
        # 6. Enviar a Sheety
        sheety_success = False
        if sheety_client:
            try:
                sheety_success = sheety_client.post(lead_dict)
                if sheety_success:
                    logger.info(f"[{request_id}] Data sent to Sheety successfully")
                else:
                    logger.warning(f"[{request_id}] Failed to send data to Sheety")
            except Exception as e:
                logger.error(f"[{request_id}] Error sending to Sheety: {e}")
        else:
            logger.warning(f"[{request_id}] Sheety client not initialized, skipping send")
        
        # 7. Log final
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"[{request_id}] Background processing completed in {processing_time:.2f} seconds. Sheety success: {sheety_success}")
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"[{request_id}] Unexpected error in background processing: {e} (after {processing_time:.2f}s)")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "sheety": bool(sheety_client),
            "sheety_url": bool(os.getenv("SHEETY_URL"))
        }
    }

@app.post("/webhook")
async def receive_elevenlabs_webhook(webhook_data: dict, background_tasks: BackgroundTasks):
    """
    Recibe webhook de Eleven Labs y responde inmediatamente.
    El procesamiento se hace en background para evitar timeouts.
    """
    request_id = webhook_data["data"]["conversation_id"]  # ID corto para tracking
    receive_time = datetime.now()
    
    logger.info(f"[{request_id}] Received webhook from Eleven Labs")
    
    try:
        # 1. Validación rápida del payload
        if not webhook_data:
            logger.warning(f"[{request_id}] Empty webhook payload received")
            raise HTTPException(status_code=400, detail="Empty payload")
        
        payload_size = len(str(webhook_data))
        logger.info(f"[{request_id}] Payload size: {payload_size} characters")
        
        # 2. Validación básica rápida (sin procesar todo)
        # Esto debe ser lo más rápido posible
        try:
            # Solo verificamos que tenga estructura básica, no procesamos aún
            if not isinstance(webhook_data, dict):
                raise ValueError("Invalid payload format")
            logger.info(f"[{request_id}] Basic payload validation passed")
        except Exception as e:
            logger.error(f"[{request_id}] Basic validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
        
        # 3. Agregar tarea en background ANTES de responder
        background_tasks.add_task(process_webhook_background, webhook_data, request_id)
        
        # 4. Responder inmediatamente (esto es lo importante!)
        response_time = (datetime.now() - receive_time).total_seconds()
        logger.info(f"[{request_id}] Responding immediately after {response_time:.3f}s, processing in background")
        
        return JSONResponse(
            status_code=202,  # 202 = Accepted (processing in background)
            content={
                "status": "accepted",
                "message": "Webhook received and processing started",
                "request_id": request_id,
                "data": {
                    "payload_size": payload_size,
                    "response_time_seconds": round(response_time, 3),
                    "processing_status": "background"
                }
            }
        )
        
    except HTTPException:
        # Re-raise HTTPExceptions
        raise
        
    except Exception as e:
        # Error inesperado en validación rápida
        response_time = (datetime.now() - receive_time).total_seconds()
        logger.error(f"[{request_id}] Unexpected error in webhook validation: {e}")
        
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error",
                "request_id": request_id,
                "error": str(e),
                "response_time_seconds": round(response_time, 3)
            }
        )

if __name__ == "__main__":
    import uvicorn
    
    # Configuración del servidor
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting Eleven Labs to Sheety Webhook server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,  # Para desarrollo
        log_level="info"
    )
