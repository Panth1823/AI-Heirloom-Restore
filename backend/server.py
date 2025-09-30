from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import base64
import io
# Note: emergentintegrations is not available on PyPI
# This is a placeholder implementation - you'll need to get the actual package from Emergent AI
# or use an alternative AI service like OpenAI's API directly

ROOT_DIR = Path(__file__).parent

# Create storage directory for restored images
STORAGE_DIR = ROOT_DIR / "restored_images"
STORAGE_DIR.mkdir(exist_ok=True)

# Load environment variables with BOM handling
env_path = ROOT_DIR / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"').strip("'")
                os.environ[key] = value

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'heirloom_ai')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

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

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Utility functions
def convert_image_to_base64(image_data: bytes) -> str:
    """Convert image bytes to base64 string"""
    return base64.b64encode(image_data).decode('utf-8')

async def restore_photo_with_ai(image_data: bytes, filename: str) -> bytes:
    """Restore and colorize photo using AI (placeholder implementation)"""
    try:
        # PLACEHOLDER IMPLEMENTATION
        # This is a temporary solution until you get the proper emergentintegrations package
        
        # For now, we'll just return the original image as a placeholder
        # In production, you would integrate with:
        # 1. Emergent AI's actual package (if available)
        # 2. OpenAI's API directly
        # 3. Google Gemini API directly
        # 4. Another AI service
        
        logging.info(f"AI restoration placeholder called for file: {filename}")
        logging.info("To enable real AI restoration, you need to:")
        logging.info("1. Get the emergentintegrations package from Emergent AI")
        logging.info("2. Or integrate with OpenAI/Google Gemini API directly")
        logging.info("3. Or use another AI service for image restoration")
        
        # Return the original image as placeholder
        # In a real implementation, this would be the AI-restored image
        return image_data
            
    except Exception as e:
        logging.error(f"AI restoration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Photo restoration failed: {str(e)}")

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Heirloom AI Photo Restoration Service"}

@api_router.post("/upload", response_model=PhotoRestoration)
async def upload_photo(file: UploadFile = File(...)):
    """Upload a photo for restoration"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file data
        image_data = await file.read()
        
        # Validate file size (minimum 100 bytes, maximum 10MB)
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
        
        # Save to database
        restoration_dict = restoration.dict()
        restoration_dict['created_at'] = restoration_dict['created_at'].isoformat()
        await db.photo_restorations.insert_one(restoration_dict)
        
        # Start restoration process in background
        try:
            start_time = datetime.now()
            restored_image_data = await restore_photo_with_ai(image_data, file.filename or "unknown.jpg")
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Store restored image (in production, you'd use cloud storage)
            # For now, we'll store in a simple file system
            restored_path = STORAGE_DIR / restoration.restored_filename
            with open(restored_path, "wb") as f:
                f.write(restored_image_data)
            
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
            
        except Exception as e:
            # Update database with error
            error_msg = str(e)
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
        # Re-raise HTTP exceptions to preserve status codes
        raise
    except Exception as e:
        logging.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@api_router.get("/restoration/{restoration_id}")
async def get_restoration_status(restoration_id: str):
    """Get restoration status"""
    restoration = await db.photo_restorations.find_one({"id": restoration_id})
    if not restoration:
        raise HTTPException(status_code=404, detail="Restoration not found")
    
    # Remove MongoDB ObjectId to avoid serialization issues
    if '_id' in restoration:
        del restoration['_id']
    
    return restoration

@api_router.get("/download/{restoration_id}")
async def download_restored_photo(restoration_id: str):
    """Download the restored photo"""
    restoration = await db.photo_restorations.find_one({"id": restoration_id})
    if not restoration:
        raise HTTPException(status_code=404, detail="Restoration not found")
    
    if restoration["status"] != "completed":
        raise HTTPException(status_code=400, detail="Photo restoration not completed yet")
    
    # Read restored image file
    restored_path = STORAGE_DIR / restoration['restored_filename']
    if not restored_path.exists():
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
    restorations = await db.photo_restorations.find().to_list(100)
    # Remove MongoDB ObjectId to avoid serialization issues
    for restoration in restorations:
        if '_id' in restoration:
            del restoration['_id']
    return [PhotoRestoration(**restoration) for restoration in restorations]

# Legacy routes for testing
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    status_dict_for_db = status_obj.dict()
    status_dict_for_db['timestamp'] = status_dict_for_db['timestamp'].isoformat()
    _ = await db.status_checks.insert_one(status_dict_for_db)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
