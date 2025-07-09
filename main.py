#!/usr/bin/env python3
"""
AI Power BI Dashboard Generator - Main Entry Point
"""

from src.api.main_server import app

if __name__ == "__main__":
    import uvicorn
    import os
    from dotenv import load_dotenv
    
    # Load environment variables from root directory
    load_dotenv(".env")
    
    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Get configuration from environment
    host = "127.0.0.1"  # Use localhost
    port = 8001  # Force port 8001
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print(f"🚀 Starting AI Power BI Dashboard Generator")
    print(f"📍 Server: http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    
    # For Docker deployment, disable reload to avoid issues
    try:
        uvicorn.run(app, host=host, port=port, reload=False, log_level="info")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        raise