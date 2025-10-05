from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import base64
import mimetypes

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get root directory
ROOT_DIR = Path(__file__).parent

# Create storage directory for restored images
STORAGE_DIR = ROOT_DIR / "restored_images"
STORAGE_DIR.mkdir(exist_ok=True)
logger.info(f"Storage directory: {STORAGE_DIR}")

# Load environment variables with BOM handling
env_path = ROOT_DIR / '.env'
if env_path.exists():
    logger.info(f"Loading .env from: {env_path}")
    with open(env_path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"').strip("'")
                os.environ[key] = value
                if key == "GOOGLE_API_KEY":
                    logger.info(f"Loaded GOOGLE_API_KEY: {value[:10]}...")
else:
    logger.warning(f".env file not found at: {env_path}")

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'heirloom_ai')
logger.info(f"Connecting to MongoDB: {mongo_url}/{db_name}")

try:
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    logger.info("MongoDB client created successfully")
except Exception as e:
    logger.error(f"Failed to create MongoDB client: {e}")
    raise

# Define Models
class PhotoRestoration(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str
    restored_filename: str
    status: str = "processing"  # processing, completed, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time: Optional[float] = None
    error_message: Optional[str] = None

class PhotoRestorationCreate(BaseModel):
    original_filename: str

# Utility functions
def _extract_image_bytes_from_gemini_response(resp_obj) -> Optional[bytes]:
    """Best-effort extraction of image bytes from google-genai response."""
    def _scan(node):
        if isinstance(node, dict):
            inline = node.get("inline_data")
            if isinstance(inline, dict):
                data_b64 = inline.get("data")
                if isinstance(data_b64, str):
                    try:
                        return base64.b64decode(data_b64)
                    except Exception:
                        return None
            if "data" in node and isinstance(node.get("data"), (bytes, bytearray)):
                return bytes(node["data"])
            for v in node.values():
                out = _scan(v)
                if out:
                    return out
        elif isinstance(node, list):
            for item in node:
                out = _scan(item)
                if out:
                    return out
        return None

    # Try common SDK attributes first
    try:
        media = getattr(resp_obj, "media", None)
        if media:
            for m in media:
                mime = getattr(m, "mime_type", None)
                data = getattr(m, "data", None)
                if mime and data:
                    if isinstance(data, (bytes, bytearray)):
                        return bytes(data)
                    if isinstance(data, str):
                        try:
                            return base64.b64decode(data)
                        except Exception:
                            pass
    except Exception:
        pass

    # Fallback: convert to dict
    try:
        as_dict = resp_obj.to_dict() if hasattr(resp_obj, "to_dict") else None
    except Exception:
        as_dict = None
    
    if as_dict:
        maybe = _scan(as_dict)
        if maybe:
            return maybe

    return _scan(resp_obj)

async def restore_photo_with_ai(image_data: bytes, filename: str, api_key: str = None) -> bytes:
    """Restore and colorize photo using OpenRouter API with Gemini model."""
    import requests
    
    openrouter_api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
    google_api_key = os.environ.get("GOOGLE_API_KEY")  # Fallback
    gemini_model = os.environ.get("GEMINI_MODEL", "google/gemini-2.5-flash-image-preview")
    
    logger.info(f"Attempting restoration with model: {gemini_model}")
    logger.info(f"Using OpenRouter API: {bool(openrouter_api_key)}")

    # Use OpenRouter if available, otherwise fall back to direct Google API
    if openrouter_api_key:
        return await _restore_with_openrouter(image_data, filename, openrouter_api_key, gemini_model)
    elif google_api_key:
        return await _restore_with_google_direct(image_data, filename, google_api_key)
    else:
        logger.error("No API key found (neither OPENROUTER_API_KEY nor GOOGLE_API_KEY)")
        raise HTTPException(
            status_code=400, 
            detail="No API key provided. Please add your OpenRouter or Google API key to continue."
        )

async def _restore_with_openrouter(image_data: bytes, filename: str, api_key: str, model: str) -> bytes:
    """Restore photo using OpenRouter API."""
    import requests
    
    logger.info("Using OpenRouter API for restoration")
    
    base64_image = base64.b64encode(image_data).decode('utf-8')
    mime_type = mimetypes.guess_type(filename or "image.jpg")[0] or "image/jpeg"
    
    prompt_text = (
        "You are an expert photo restoration and colorization specialist. Your task is to restore and colorize this historical photograph. "
        
        "CRITICAL: You must generate a new image as output, not just describe what you would do.\n\n"
        
        "REQUIREMENTS:\n"
        "1. RESTORE: Remove scratches, dust, cracks, and other damage\n"
        "2. ENHANCE: Gently improve sharpness and clarity while preserving authenticity\n"
        "3. COLORIZE: Add realistic, period-accurate colors to this black and white or faded image\n"
        "4. PRESERVE: Maintain the subject's identity, facial features, and historical authenticity\n"
        
        "COLORIZATION GUIDELINES:\n"
        "- Use natural, realistic skin tones appropriate for the person's ethnicity and age\n"
        "- Add appropriate colors for clothing, hair, and background elements\n"
        "- Use period-accurate color palettes (avoid modern bright colors for historical photos)\n"
        "- Ensure lighting and shadows remain consistent with the original\n"
        "- Make colors subtle and realistic, not oversaturated\n"
        
        "OUTPUT REQUIREMENT:\n"
        "You MUST generate a new colorized and restored image as your response. Do not provide text descriptions - generate the actual image file.\n\n"
        
        "If this appears to be a portrait or people photo, focus on:\n"
        "- Realistic skin tones and facial coloring\n"
        "- Natural hair colors\n"
        "- Appropriate clothing colors for the era\n"
        "- Background colorization that complements the subject\n\n"
        
        "Generate the restored and colorized image now."
    )

    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "AI Heirloom Restore",
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    }

    try:
        logger.info("Sending request to OpenRouter API...")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        logger.info(f"OpenRouter response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            logger.info("OpenRouter restoration completed")
            logger.info(f"Response preview: {content[:200]}...")
            
            # Try to extract image from response if the model generated one
            generated_image = await _extract_generated_image_from_openrouter_response(result)
            
            if generated_image:
                logger.info(f"Successfully extracted generated image: {len(generated_image)} bytes")
                return generated_image
            else:
                logger.error("No image generated by the model")
                raise HTTPException(
                    status_code=502,
                    detail="The AI model did not generate a restored image. Please try again."
                )
            
        else:
            error_detail = response.text
            logger.error(f"OpenRouter API error: {response.status_code} - {error_detail}")
            
            if response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="OpenRouter API quota exceeded. Please check your OpenRouter account."
                )
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=403,
                    detail="Invalid OpenRouter API key. Please check your API key."
                )
            else:
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenRouter API error: {error_detail}"
                )
                
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenRouter network error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Network error connecting to OpenRouter: {str(e)}"
        )

async def _restore_with_google_direct(image_data: bytes, filename: str, api_key: str) -> bytes:
    """Fallback: Restore photo using direct Google API."""
    logger.info("Using direct Google API as fallback")
    
    base64_image = base64.b64encode(image_data).decode('utf-8')
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp")

    try:
        try:
            from google import genai
            logger.info("google-genai imported successfully")
        except Exception as import_err:
            logger.error(f"Failed to import google-genai: {import_err}")
            raise HTTPException(status_code=500, detail=f"google-genai not available: {import_err}")

        client = genai.Client(api_key=api_key)
        logger.info("Gemini client created")

        prompt_text = (
            "Restore and COLORIZE this historical photograph. Remove scratches/dust, gently enhance sharpness, and "
            "produce a realistic COLOR output with natural, period-accurate tones. Preserve subject identity, lighting, "
            "and scene authenticity. Avoid monochrome or stylized looks. IMPORTANT: The output must be in COLOR, "
            "not black and white. Add realistic colors based on the historical period and context."
        )

        mime_type = mimetypes.guess_type(filename or "image.jpg")[0] or "image/jpeg"
        logger.info(f"Sending request to Gemini with mime_type: {mime_type}")

        response = client.models.generate_content(
            model=gemini_model,
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt_text},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_image,
                            }
                        },
                    ],
                }
            ],
        )

        logger.info("Received response from Gemini, extracting image...")
        image_bytes = _extract_image_bytes_from_gemini_response(response)
        
        if not image_bytes:
            logger.info("First extraction failed, trying dict conversion...")
            try:
                as_dict = response.to_dict() if hasattr(response, "to_dict") else None
            except Exception as e:
                logger.error(f"Dict conversion failed: {e}")
                as_dict = None
            
            if as_dict:
                image_bytes = _extract_image_bytes_from_gemini_response(as_dict)

        if not image_bytes:
            logger.error("No image bytes extracted from response")
            raise HTTPException(
                status_code=502, 
                detail="No image returned from Gemini API. Please try again or check your API key."
            )

        logger.info(f"Successfully extracted {len(image_bytes)} bytes from Gemini response")
        return image_bytes

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gemini restoration failed: {str(e)}")
        error_str = str(e)
        
        if "429" in error_str or "quota" in error_str.lower() or "RESOURCE_EXHAUSTED" in error_str:
            raise HTTPException(
                status_code=429,
                detail="API quota exceeded. Please add your own Gemini API key to continue. Get a free key at: https://makersuite.google.com/app/apikey"
            )
        elif "403" in error_str or "invalid" in error_str.lower() or "unauthorized" in error_str.lower():
            raise HTTPException(
                status_code=403,
                detail="Invalid API key. Please check your Gemini API key and try again."
            )
        else:
            raise HTTPException(
                status_code=502,
                detail=f"Gemini API error: {str(e)}. Please try again or check your API key."
            )

async def _extract_generated_image_from_openrouter_response(result: dict) -> Optional[bytes]:
    """Extract generated image from OpenRouter response if available."""
    try:
        # Check if response contains image data
        choices = result.get("choices", [])
        if not choices:
            return None
            
        message = choices[0].get("message", {})
        content = message.get("content", "")
        
        # Look for base64 image data in the response
        if isinstance(content, str):
            # Check for base64 image patterns
            import re
            base64_pattern = r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)'
            matches = re.findall(base64_pattern, content)
            
            if matches:
                # Use the first base64 image found
                base64_data = matches[0]
                try:
                    image_bytes = base64.b64decode(base64_data)
                    logger.info(f"Extracted image from OpenRouter response: {len(image_bytes)} bytes")
                    return image_bytes
                except Exception as e:
                    logger.error(f"Failed to decode base64 image: {e}")
        
        # Check if content is a list with image data
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "image_url":
                    image_url = item.get("image_url", {}).get("url", "")
                    if image_url.startswith("data:image/"):
                        try:
                            # Extract base64 part
                            base64_data = image_url.split(",")[1]
                            image_bytes = base64.b64decode(base64_data)
                            logger.info(f"Extracted image from OpenRouter response: {len(image_bytes)} bytes")
                            return image_bytes
                        except Exception as e:
                            logger.error(f"Failed to decode image URL: {e}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting image from OpenRouter response: {e}")
        return None


# Create the main FastAPI app
app = FastAPI(
    title="Heirloom AI Photo Restoration",
    description="AI-powered photo restoration and colorization service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router
api_router = APIRouter(prefix="/api")

# Root endpoint (main app)
@app.get("/")
async def main_root():
    """Root endpoint to verify server is running"""
    return {
        "status": "ok",
        "message": "Heirloom AI Photo Restoration Service",
        "version": "1.0.0",
        "docs": "/docs",
        "api_base": "/api"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    mongo_status = "unknown"
    try:
        await db.command("ping")
        mongo_status = "connected"
    except Exception as e:
        mongo_status = f"disconnected: {str(e)}"
    
    return {
        "status": "ok",
        "mongodb": mongo_status,
        "storage_dir": str(STORAGE_DIR),
        "openrouter_configured": bool(os.environ.get("OPENROUTER_API_KEY")),
        "google_api_configured": bool(os.environ.get("GOOGLE_API_KEY")),
        "gemini_model": os.environ.get("GEMINI_MODEL", "google/gemini-2.5-flash-image-preview")
    }

# API Routes
@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {
        "message": "Heirloom AI Photo Restoration API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "POST /api/upload",
            "status": "GET /api/restoration/{id}",
            "download": "GET /api/download/{id}",
            "list": "GET /api/restorations",
            "test": "GET /api/gemini-test"
        }
    }

@api_router.get("/gemini-test")
async def gemini_test():
    """Test API connectivity (OpenRouter or Google)"""
    import requests
    
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    gemini_model = os.environ.get("GEMINI_MODEL", "google/gemini-2.5-flash-image-preview")
    
    logger.info(f"Testing API with model: {gemini_model}")
    logger.info(f"OpenRouter configured: {bool(openrouter_api_key)}")
    logger.info(f"Google API configured: {bool(google_api_key)}")
    
    # Test OpenRouter first if available
    if openrouter_api_key:
        try:
            logger.info("Testing OpenRouter API...")
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "AI Heirloom Restore",
            }
            
            payload = {
                "model": gemini_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Say 'ok' if you can read this."
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                logger.info(f"OpenRouter test successful. Response: {content}")
                return {
                    "status": "success",
                    "api_type": "OpenRouter",
                    "model": gemini_model,
                    "response": content or "(no text)",
                    "api_key_configured": True
                }
            else:
                logger.error(f"OpenRouter test failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"OpenRouter test failed: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter network error: {e}")
            raise HTTPException(status_code=500, detail=f"OpenRouter network error: {str(e)}")
    
    # Fallback to Google API
    elif google_api_key:
        try:
            try:
                from google import genai
                logger.info("google-genai imported successfully")
            except Exception as import_err:
                logger.error(f"Import failed: {import_err}")
                raise HTTPException(status_code=500, detail=f"google-genai not available: {import_err}")
            
            client = genai.Client(api_key=google_api_key)
            logger.info("Gemini client created, sending test request...")
            
            response = client.models.generate_content(
                model=gemini_model.replace("google/", ""),  # Remove google/ prefix for direct API
                contents=[{"role": "user", "parts": [{"text": "Say 'ok' if you can read this."}]}],
            )
            
            # Extract text safely
            text = None
            try:
                if hasattr(response, "text") and isinstance(response.text, str):
                    text = response.text
            except Exception:
                text = None
            
            if not text:
                try:
                    as_dict = response.to_dict() if hasattr(response, "to_dict") else None
                    if as_dict:
                        candidates = [as_dict]
                        while candidates:
                            cur = candidates.pop()
                            if isinstance(cur, dict):
                                if "text" in cur and isinstance(cur["text"], str):
                                    text = cur["text"]
                                    break
                                candidates.extend(cur.values())
                            elif isinstance(cur, list):
                                candidates.extend(cur)
                except Exception:
                    pass
            
            logger.info(f"Google API test successful. Response: {text}")
            return {
                "status": "success",
                "api_type": "Google Direct",
                "model": gemini_model,
                "response": text or "(no text)",
                "api_key_configured": True
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Google API test failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Google API test failed: {str(e)}")
    
    else:
        logger.error("No API keys configured")
        raise HTTPException(status_code=500, detail="No API keys configured. Please add OPENROUTER_API_KEY or GOOGLE_API_KEY.")

@api_router.post("/upload", response_model=PhotoRestoration)
async def upload_photo(
    file: UploadFile = File(...), 
    api_key: Optional[str] = Form(None)
):
    """Upload a photo for restoration"""
    logger.info(f"Received upload request for file: {file.filename}")
    
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file data
        image_data = await file.read()
        logger.info(f"Read {len(image_data)} bytes from uploaded file")
        
        # Validate file size
        if len(image_data) < 100:
            raise HTTPException(status_code=400, detail="Image file is too small or corrupted")
        if len(image_data) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="Image file is too large (max 10MB)")
        
        # Create restoration record
        restoration_id = str(uuid.uuid4())
        restoration = PhotoRestoration(
            id=restoration_id,
            original_filename=file.filename or "unknown.jpg",
            restored_filename=f"restored_{restoration_id}.jpg",
            status="processing"
        )
        
        logger.info(f"Created restoration record with ID: {restoration_id}")
        
        # Save to database
        restoration_dict = restoration.dict()
        restoration_dict['created_at'] = restoration_dict['created_at'].isoformat()
        await db.photo_restorations.insert_one(restoration_dict)
        logger.info("Saved restoration record to database")
        
        # Start restoration process
        try:
            start_time = datetime.now()
            logger.info("Starting AI restoration...")
            
            restored_image_data = await restore_photo_with_ai(
                image_data, 
                file.filename or "unknown.jpg", 
                api_key
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Restoration completed in {processing_time:.2f} seconds")
            
            # Store restored image
            restored_path = STORAGE_DIR / restoration.restored_filename
            with open(restored_path, "wb") as f:
                f.write(restored_image_data)
            logger.info(f"Saved restored image to: {restored_path}")
            
            # Update database with success
            await db.photo_restorations.update_one(
                {"id": restoration_id},
                {
                    "$set": {
                        "status": "completed",
                        "processing_time": processing_time
                    }
                }
            )
            
            restoration.status = "completed"
            restoration.processing_time = processing_time
            logger.info(f"Updated restoration status to completed")
            
        except Exception as e:
            # Update database with error
            error_msg = str(e)
            logger.error(f"Restoration failed: {error_msg}")
            
            await db.photo_restorations.update_one(
                {"id": restoration_id},
                {
                    "$set": {
                        "status": "failed",
                        "error_message": error_msg
                    }
                }
            )
            restoration.status = "failed"
            restoration.error_message = error_msg
        
        return restoration
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@api_router.get("/restoration/{restoration_id}")
async def get_restoration_status(restoration_id: str):
    """Get restoration status"""
    logger.info(f"Fetching restoration status for ID: {restoration_id}")
    
    restoration = await db.photo_restorations.find_one({"id": restoration_id})
    if not restoration:
        raise HTTPException(status_code=404, detail="Restoration not found")
    
    # Remove MongoDB ObjectId
    if '_id' in restoration:
        del restoration['_id']
    
    return restoration

@api_router.get("/download/{restoration_id}")
async def download_restored_photo(restoration_id: str):
    """Download the restored photo"""
    logger.info(f"Download request for restoration ID: {restoration_id}")
    
    restoration = await db.photo_restorations.find_one({"id": restoration_id})
    if not restoration:
        raise HTTPException(status_code=404, detail="Restoration not found")
    
    if restoration["status"] != "completed":
        raise HTTPException(status_code=400, detail="Photo restoration not completed yet")
    
    # Read restored image file
    restored_path = STORAGE_DIR / restoration['restored_filename']
    if not restored_path.exists():
        logger.error(f"Restored image file not found at: {restored_path}")
        raise HTTPException(status_code=404, detail="Restored image file not found")
    
    def iter_file(file_path: Path):
        with open(file_path, "rb") as f:
            yield from f
    
    return StreamingResponse(
        iter_file(restored_path),
        media_type="image/jpeg",
        headers={"Content-Disposition": f"attachment; filename={restoration['restored_filename']}"}
    )

@api_router.get("/restorations", response_model=List[PhotoRestoration])
async def get_restorations():
    """Get all photo restorations"""
    logger.info("Fetching all restorations")
    
    restorations = await db.photo_restorations.find().sort("created_at", -1).to_list(100)
    
    # Remove MongoDB ObjectId
    for restoration in restorations:
        if '_id' in restoration:
            del restoration['_id']
    
    return [PhotoRestoration(**restoration) for restoration in restorations]

# Include the API router
app.include_router(api_router)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection on shutdown"""
    logger.info("Shutting down MongoDB client")
    client.close()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("=" * 60)
    logger.info("Heirloom AI Photo Restoration Service Starting...")
    logger.info("=" * 60)
    logger.info(f"Storage Directory: {STORAGE_DIR}")
    logger.info(f"MongoDB URL: {mongo_url}")
    logger.info(f"Database Name: {db_name}")
    logger.info(f"Gemini Model: {os.environ.get('GEMINI_MODEL', 'google/gemini-2.5-flash-image-preview')}")
    logger.info(f"OpenRouter API Key: {'Configured' if os.environ.get('OPENROUTER_API_KEY') else 'Not configured'}")
    logger.info(f"Google API Key: {'Configured' if os.environ.get('GOOGLE_API_KEY') else 'Not configured'}")
    logger.info("=" * 60)
    logger.info("Server ready! Visit http://localhost:8000/docs for API documentation")
    logger.info("=" * 60)
