from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
import os
import uuid
import shutil
from datetime import datetime
from dotenv import load_dotenv
import logging

# Load environment variables from config directory
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our custom modules with updated paths
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.ai_client import AIClient
from ..core.langchain_controller import DashboardController
from core.powerbi_client import PowerBIClient
from core.data_processor import DataProcessor
from database.memory_manager import MemoryManager
from utils.validators import FileValidator, InputValidator, ConfigValidator

def validate_environment():
    """Validate required environment variables"""
    required_ai_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    has_ai_key = any(os.getenv(key) and os.getenv(key) != f"your_{key.lower()}_here" for key in required_ai_keys)
    
    if not has_ai_key:
        logger.error("❌ No AI API keys configured!")
        logger.error("Please add either OPENAI_API_KEY or ANTHROPIC_API_KEY to your .env file")
        raise ValueError("No AI API keys configured. System cannot function without AI integration.")
    
    # Check Power BI credentials (optional but recommended)
    powerbi_keys = ["POWER_BI_TENANT_ID", "POWER_BI_CLIENT_ID", "POWER_BI_CLIENT_SECRET"]
    has_powerbi = all(os.getenv(key) and os.getenv(key) != f"your_{key.lower().replace('_', '_')}" for key in powerbi_keys)
    
    if has_powerbi:
        logger.info("✅ Power BI credentials configured - Real dashboards will be created!")
    else:
        logger.warning("⚠️  Power BI credentials not configured - Dashboard creation will fail")
        logger.warning("Add your Azure app credentials to .env for real Power BI integration")

# Validate environment on startup
validate_environment()

app = FastAPI(
    title="AI Power BI Dashboard Generator", 
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT", "development") == "development" else None
)

# Secure CORS configuration
environment = os.getenv("ENVIRONMENT", "development")
if environment == "production":
    # Production: Only allow specific origins
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
    allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]
    if not allowed_origins:
        raise ValueError("ALLOWED_ORIGINS must be set in production environment")
else:
    # Development: Allow localhost origins only
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

# Validate CORS origins
is_valid, cors_errors = ConfigValidator.validate_cors_origins(allowed_origins)
if not is_valid:
    logger.warning(f"CORS configuration warnings: {cors_errors}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specific methods only
    allow_headers=["Content-Type", "Authorization"],  # Specific headers only
)

# Initialize components
ai_client = AIClient()
dashboard_controller = DashboardController()
powerbi_client = PowerBIClient()
data_processor = DataProcessor()
memory_manager = MemoryManager()

# Data models
class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class DashboardRequest(BaseModel):
    message: str
    conversation_id: str
    file_paths: List[str] = []

class ConversationResponse(BaseModel):
    conversation_id: str
    response: str
    status: str
    progress: int
    dashboard_url: Optional[str] = None
    download_link: Optional[str] = None

# Global storage for tracking jobs
active_jobs = {}

@app.get("/")
async def root():
    return {"message": "AI Power BI Dashboard Generator API is running!", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Production health check endpoint"""
    try:
        # Check AI client
        ai_status = "configured" if (ai_client.openai_client or ai_client.anthropic_client) else "not_configured"
        
        # Check Power BI client
        powerbi_status = "configured" if powerbi_client.app else "not_configured"
        
        # Check database
        db_status = "connected" if memory_manager else "not_connected"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "ai_client": ai_status,
                "powerbi_client": powerbi_status,
                "database": db_status,
                "data_processor": "ready"
            },
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/config")
async def get_config():
    """Get system configuration status"""
    return {
        "ai_providers": {
            "openai": bool(ai_client.openai_client),
            "anthropic": bool(ai_client.anthropic_client)
        },
        "powerbi_configured": bool(powerbi_client.app),
        "max_file_size": int(os.getenv("MAX_FILE_SIZE", 104857600)),
        "max_files_per_upload": int(os.getenv("MAX_FILES_PER_UPLOAD", 10)),
        "debug_mode": os.getenv("DEBUG", "True").lower() == "true"
    }

@app.post("/chat", response_model=ConversationResponse)
async def chat_endpoint(message: ChatMessage, background_tasks: BackgroundTasks):
    """
    Main chat endpoint - handles natural language requests for dashboard creation
    """
    try:
        # Validate input message
        is_valid, error_msg = InputValidator.validate_chat_message(message.message)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Create or get conversation ID
        conversation_id = message.conversation_id or str(uuid.uuid4())
        
        # Store conversation
        memory_manager.add_message(conversation_id, "user", message.message)
        
        # Use AI for all responses - no more template responses
        # Only give template response for first hello
        if any(word in message.message.lower() for word in ["hello", "hi"]) and len(memory_manager.get_conversation(conversation_id)) <= 2:
            response_text = """Hello! I'm your AI Power BI Dashboard Generator. 
            
I can help you create professional Power BI dashboards just by chatting with me. Here's what I can do:

1. **Upload your data** (Excel, CSV, JSON files)
2. **Tell me what dashboard you want** in plain English
3. **I'll create a real Power BI dashboard** for you automatically

Example: "Create a sales dashboard with monthly trends from my uploaded data"

How can I help you today?"""
            
            memory_manager.add_message(conversation_id, "assistant", response_text)
            
            return ConversationResponse(
                conversation_id=conversation_id,
                response=response_text,
                status="completed",
                progress=100
            )
        
        # Check if this is a dashboard creation request
        dashboard_keywords = ["dashboard", "chart", "graph", "visualization", "report", "analytics"]
        if any(keyword in message.message.lower() for keyword in dashboard_keywords):
            # Start dashboard creation process
            job_id = str(uuid.uuid4())
            active_jobs[job_id] = {
                "status": "processing",
                "progress": 0,
                "conversation_id": conversation_id
            }
            
            # Start background task
            background_tasks.add_task(
                create_dashboard_background, 
                job_id, 
                conversation_id, 
                message.message, 
                []
            )
            
            response_text = "I understand you want to create a dashboard! I'm starting the process now. Please upload your data files, and I'll create exactly what you need."
            
            memory_manager.add_message(conversation_id, "assistant", response_text)
            
            return ConversationResponse(
                conversation_id=conversation_id,
                response=response_text,
                status="processing",
                progress=10
            )
        
        # General AI response for other queries
        # Get uploaded files for this conversation
        conversation_files = memory_manager.get_conversation_files(conversation_id)
        context = {}
        if conversation_files:
            context['uploaded_files'] = conversation_files
        
        ai_response = await ai_client.get_response(message.message, conversation_id, context)
        memory_manager.add_message(conversation_id, "assistant", ai_response)
        
        return ConversationResponse(
            conversation_id=conversation_id,
            response=ai_response,
            status="completed",
            progress=100
        )
        
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        
        # Return a user-friendly error response instead of raising exception
        error_response = "I apologize, but I encountered an issue processing your request. Please try again or rephrase your question."
        
        # Try to add error message to conversation
        try:
            memory_manager.add_message(conversation_id, "assistant", error_response)
        except:
            pass  # Don't fail if we can't save to memory
        
        return ConversationResponse(
            conversation_id=conversation_id or str(uuid.uuid4()),
            response=error_response,
            status="error",
            progress=100
        )

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...), conversation_id: str = ""):
    """
    Handle file uploads with comprehensive validation and security checks
    """
    try:
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Validate number of files
        max_files = int(os.getenv("MAX_FILES_PER_UPLOAD", 10))
        if len(files) > max_files:
            raise HTTPException(
                status_code=400, 
                detail=f"Too many files. Maximum {max_files} files allowed per upload"
            )
        
        # Create upload directory
        upload_dir = f"uploads/{conversation_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        uploaded_files = []
        temp_files = []  # Track temporary files for cleanup
        
        # First pass: Save and validate all files
        for file in files:
            if not file.filename:
                raise HTTPException(status_code=400, detail="File must have a filename")
            
            # Create temporary file path
            temp_file_path = f"{upload_dir}/temp_{uuid.uuid4()}_{file.filename}"
            
            # Save file with size limit enforcement
            max_size = int(os.getenv("MAX_FILE_SIZE", 104857600))  # 100MB default
            total_size = 0
            
            with open(temp_file_path, "wb") as buffer:
                while chunk := await file.read(8192):  # Read in 8KB chunks
                    total_size += len(chunk)
                    if total_size > max_size:
                        # Clean up partial file
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        raise HTTPException(
                            status_code=413, 
                            detail=f"File {file.filename} exceeds maximum size of {max_size / 1024 / 1024:.1f}MB"
                        )
                    buffer.write(chunk)
            
            temp_files.append((temp_file_path, file.filename))
        
        # Second pass: Validate all files
        is_valid, validation_errors = FileValidator.validate_multiple_files(temp_files)
        
        if not is_valid:
            # Clean up temporary files
            for temp_path, _ in temp_files:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
            raise HTTPException(
                status_code=400, 
                detail=f"File validation failed: {'; '.join(validation_errors)}"
            )
        
        # Third pass: Move validated files to final location
        for temp_path, original_filename in temp_files:
            final_path = f"{upload_dir}/{original_filename}"
            if os.path.exists(temp_path):
                shutil.move(temp_path, final_path)
                uploaded_files.append(final_path)
        
        # Process the uploaded data
        processed_data = await data_processor.analyze_files(uploaded_files)
        
        # Store file info in memory
        memory_manager.add_file_info(conversation_id, uploaded_files, processed_data)
        
        logger.info(f"Successfully uploaded {len(uploaded_files)} files for conversation {conversation_id}")
        
        return {
            "conversation_id": conversation_id,
            "files_uploaded": len(uploaded_files),
            "file_names": [filename for _, filename in temp_files],
            "data_summary": processed_data["summary"],
            "message": "Files uploaded and validated successfully! Now tell me what kind of dashboard you want to create."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up any temporary files on error
        for temp_path, _ in temp_files if 'temp_files' in locals() else []:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        logger.error(f"Error uploading files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading files: {str(e)}")

@app.get("/conversations")
async def get_conversations():
    """
    Get list of all conversations
    """
    try:
        conversations = memory_manager.list_conversations()
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        return {"conversations": []}

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get specific conversation with messages
    """
    try:
        conversation = memory_manager.get_conversation(conversation_id)
        return conversation
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Conversation not found")

@app.get("/conversations/{conversation_id}/files")
async def get_conversation_files(conversation_id: str):
    """
    Get files for a specific conversation
    """
    try:
        file_paths = memory_manager.get_conversation_files(conversation_id)
        files = []
        for file_path in file_paths:
            files.append({
                'name': os.path.basename(file_path),
                'path': file_path,
                'type': os.path.splitext(file_path)[1].lower().replace('.', ''),
                'uploadTime': datetime.now().isoformat()  # Could be improved with actual upload time
            })
        return {"files": files}
    except Exception as e:
        logger.error(f"Error getting files for conversation {conversation_id}: {str(e)}")
        return {"files": []}

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation
    """
    try:
        memory_manager.delete_conversation(conversation_id)
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting conversation")

@app.post("/create-dashboard")
async def create_dashboard(request: DashboardRequest, background_tasks: BackgroundTasks):
    """
    Create Power BI dashboard based on request and uploaded files
    """
    try:
        # Start dashboard creation job
        job_id = str(uuid.uuid4())
        active_jobs[job_id] = {
            "status": "starting",
            "progress": 0,
            "conversation_id": request.conversation_id
        }
        
        # Get uploaded files for this conversation
        file_info = memory_manager.get_file_info(request.conversation_id)
        if not file_info:
            return {
                "error": "No files found. Please upload your data first.",
                "conversation_id": request.conversation_id
            }
        
        # Start background dashboard creation
        background_tasks.add_task(
            create_dashboard_background,
            job_id,
            request.conversation_id,
            request.message,
            file_info["file_paths"]
        )
        
        return {
            "job_id": job_id,
            "conversation_id": request.conversation_id,
            "message": "Dashboard creation started! I'm analyzing your data and building your dashboard.",
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating dashboard: {str(e)}")

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a dashboard creation job
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return active_jobs[job_id]

@app.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get conversation history
    """
    try:
        messages = memory_manager.get_conversation(conversation_id)
        return {
            "conversation_id": conversation_id,
            "messages": messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversation: {str(e)}")

@app.get("/conversations")
async def list_conversations():
    """
    List all conversations
    """
    try:
        conversations = memory_manager.list_conversations()
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing conversations: {str(e)}")

@app.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation and its files
    """
    try:
        # Delete conversation from memory
        memory_manager.delete_conversation(conversation_id)
        
        # Delete uploaded files
        upload_dir = f"uploads/{conversation_id}"
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
        
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")

async def create_dashboard_background(job_id: str, conversation_id: str, user_request: str, file_paths: List[str]):
    """
    Background task for creating Power BI dashboard
    """
    try:
        # Update job status
        active_jobs[job_id]["status"] = "analyzing_request"
        active_jobs[job_id]["progress"] = 10
        
        # Step 1: AI analyzes the request and data
        memory_manager.add_message(conversation_id, "system", "🔍 Analyzing your request and data...")
        
        dashboard_plan = await dashboard_controller.create_dashboard_plan(
            user_request, 
            file_paths, 
            conversation_id
        )
        
        active_jobs[job_id]["progress"] = 30
        active_jobs[job_id]["status"] = "processing_data"
        memory_manager.add_message(conversation_id, "system", "📊 Processing your data...")
        
        # Step 2: Process and clean data
        processed_data = await data_processor.process_for_powerbi(file_paths, dashboard_plan)
        
        active_jobs[job_id]["progress"] = 50
        active_jobs[job_id]["status"] = "creating_dashboard"
        memory_manager.add_message(conversation_id, "system", "🎨 Creating your Power BI dashboard...")
        
        # Step 3: Create Power BI dashboard
        dashboard_result = await powerbi_client.create_dashboard(processed_data, dashboard_plan)
        
        active_jobs[job_id]["progress"] = 90
        active_jobs[job_id]["status"] = "finalizing"
        memory_manager.add_message(conversation_id, "system", "✅ Finalizing your dashboard...")
        
        # Step 4: Finalize and return links
        final_response = f"""🎉 **Your Power BI Dashboard is Ready!**

**Dashboard Created:** {dashboard_plan.get('title', 'Custom Dashboard')}

**What I Built For You:**
{dashboard_plan.get('description', 'Custom dashboard based on your requirements')}

**Access Your Dashboard:**
• **View Online:** {dashboard_result['view_url']}
• **Download .pbix:** {dashboard_result['download_url']}
• **Share Link:** {dashboard_result['share_url']}

**Dashboard Features:**
{chr(10).join(f"• {feature}" for feature in dashboard_plan.get('features', ['Custom visualizations', 'Interactive charts', 'Data insights']))}

Your dashboard is now live and ready to use! You can open it in Power BI, share it with your team, or download the .pbix file for further customization.

Need any changes or want to create another dashboard? Just let me know!"""
        
        memory_manager.add_message(conversation_id, "assistant", final_response)
        
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["progress"] = 100
        active_jobs[job_id]["dashboard_url"] = dashboard_result['view_url']
        active_jobs[job_id]["download_link"] = dashboard_result['download_url']
        active_jobs[job_id]["response"] = final_response
        
    except Exception as e:
        # Handle errors
        error_message = f"❌ Error creating dashboard: {str(e)}"
        memory_manager.add_message(conversation_id, "assistant", error_message)
        
        active_jobs[job_id]["status"] = "error"
        active_jobs[job_id]["error"] = str(e)
        active_jobs[job_id]["response"] = error_message

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print(f"🚀 Starting AI Power BI Dashboard Generator")
    print(f"📍 Server: http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    
    uvicorn.run(app, host=host, port=port, reload=debug)
