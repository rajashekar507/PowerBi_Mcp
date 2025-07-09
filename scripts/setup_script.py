#!/usr/bin/env python3
"""
AI Power BI Dashboard Generator - Setup Script
This script sets up the complete environment for the AI Power BI system.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None, description=""):
    """Run a command and handle errors"""
    print(f"🔄 {description or f'Running: {command}'}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✅ Success: {description or command}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {description or command}")
        print(f"   Error output: {e.stderr}")
        return None

def check_python():
    """Check Python version"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required. Please upgrade Python.")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")

def check_node():
    """Check Node.js installation"""
    print("📦 Checking Node.js...")
    result = run_command("node --version", description="Checking Node.js version")
    if result is None:
        print("❌ Node.js is not installed. Please install Node.js 16+ from https://nodejs.org/")
        return False
    print(f"✅ Node.js is installed: {result.strip()}")
    return True

def create_virtual_environment():
    """Create Python virtual environment"""
    print("🏗️  Creating Python virtual environment...")
    
    if os.path.exists("venv"):
        print("✅ Virtual environment already exists")
        return True
    
    result = run_command(
        "python -m venv venv", 
        description="Creating virtual environment"
    )
    return result is not None

def install_python_dependencies():
    """Install Python dependencies"""
    print("📚 Installing Python dependencies...")
    
    # Activate virtual environment and install requirements
    if os.name == 'nt':  # Windows
        pip_cmd = "venv\\Scripts\\pip install -r requirements.txt"
    else:  # Unix/Linux/macOS
        pip_cmd = "source venv/bin/activate && pip install -r requirements.txt"
    
    result = run_command(
        pip_cmd,
        description="Installing Python packages"
    )
    return result is not None

def setup_frontend():
    """Setup React frontend"""
    print("⚛️  Setting up React frontend...")
    
    # Create frontend directory if it doesn't exist
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        frontend_dir.mkdir()
        print("✅ Created frontend directory")
    
    # Install npm dependencies
    result = run_command(
        "npm install",
        cwd="frontend",
        description="Installing Node.js dependencies"
    )
    return result is not None

def create_directories():
    """Create necessary directories"""
    print("📁 Creating necessary directories...")
    
    directories = [
        "uploads",
        "output", 
        "logs",
        "data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created {directory}/ directory")

def setup_environment_file():
    """Setup environment configuration"""
    print("⚙️  Setting up environment configuration...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("📝 Please edit .env file with your API keys and configuration")
    elif env_file.exists():
        print("✅ .env file already exists")
    else:
        print("⚠️  No .env.example found, creating basic .env file")
        with open(".env", "w") as f:
            f.write("""# AI API Keys (REQUIRED - Add at least one)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Power BI Configuration (REQUIRED - Add your Azure app details)
POWER_BI_TENANT_ID=your_azure_tenant_id
POWER_BI_CLIENT_ID=your_azure_app_client_id
POWER_BI_CLIENT_SECRET=your_azure_app_client_secret
POWER_BI_USERNAME=your_powerbi_username
POWER_BI_PASSWORD=your_powerbi_password

# Database Configuration
DATABASE_URL=sqlite:///conversations.db

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Security
SECRET_KEY=your_secret_key_here

# File Upload Limits
MAX_FILE_SIZE=104857600
MAX_FILES_PER_UPLOAD=10

# Logging
LOG_LEVEL=INFO
LOG_FILE=app.log

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
""")

def create_startup_scripts():
    """Create startup scripts for easy running"""
    print("🚀 Creating startup scripts...")
    
    # Backend startup script
    if os.name == 'nt':  # Windows
        with open("start_backend.bat", "w") as f:
            f.write("""@echo off
echo Starting AI Power BI Backend...
call venv\\Scripts\\activate
python main.py
pause
""")
        
        with open("start_frontend.bat", "w") as f:
            f.write("""@echo off
echo Starting AI Power BI Frontend...
cd frontend
npm start
pause
""")
        
        with open("start_all.bat", "w") as f:
            f.write("""@echo off
echo Starting AI Power BI Complete System...
start "Backend" cmd /k start_backend.bat
timeout /t 3
start "Frontend" cmd /k start_frontend.bat
echo Both services are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
pause
""")
    else:  # Unix/Linux/macOS
        with open("start_backend.sh", "w") as f:
            f.write("""#!/bin/bash
echo "Starting AI Power BI Backend..."
source venv/bin/activate
python main.py
""")
        
        with open("start_frontend.sh", "w") as f:
            f.write("""#!/bin/bash
echo "Starting AI Power BI Frontend..."
cd frontend
npm start
""")
        
        with open("start_all.sh", "w") as f:
            f.write("""#!/bin/bash
echo "Starting AI Power BI Complete System..."
./start_backend.sh &
sleep 3
./start_frontend.sh &
echo "Both services are starting..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
wait
""")
        
        # Make scripts executable
        os.chmod("start_backend.sh", 0o755)
        os.chmod("start_frontend.sh", 0o755)
        os.chmod("start_all.sh", 0o755)
    
    print("✅ Created startup scripts")

def create_frontend_files():
    """Create necessary frontend files if they don't exist"""
    print("📱 Creating frontend files...")
    
    frontend_dir = Path("frontend")
    src_dir = frontend_dir / "src"
    public_dir = frontend_dir / "public"
    
    # Create directories
    src_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)
    
    # Create public/index.html
    index_html = public_dir / "index.html"
    if not index_html.exists():
        with open(index_html, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta name="description" content="AI-powered Power BI Dashboard Generator" />
    <title>AI Power BI Dashboard Generator</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>
""")
    
    # Create src/index.js
    index_js = src_dir / "index.js"
    if not index_js.exists():
        with open(index_js, "w") as f:
            f.write("""import React from 'react';
import ReactDOM from 'react-dom/client';
import './App.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""")

def main():
    """Main setup function"""
    print("🎯 AI Power BI Dashboard Generator - Setup")
    print("=" * 50)
    
    # Check prerequisites
    check_python()
    node_available = check_node()
    
    # Setup backend
    print("\n🔧 Setting up Backend...")
    if not create_virtual_environment():
        print("❌ Failed to create virtual environment")
        sys.exit(1)
    
    if not install_python_dependencies():
        print("❌ Failed to install Python dependencies")
        sys.exit(1)
    
    # Setup frontend (only if Node.js is available)
    if node_available:
        print("\n🔧 Setting up Frontend...")
        create_frontend_files()
        if not setup_frontend():
            print("❌ Failed to setup frontend")
            sys.exit(1)
    else:
        print("⚠️  Skipping frontend setup (Node.js not available)")
    
    # Create directories and files
    create_directories()
    setup_environment_file()
    create_startup_scripts()
    
    print("\n🎉 Setup Complete!")
    print("=" * 50)
    print("\n📋 Next Steps:")
    print("1. Edit .env file with your API keys:")
    print("   - Add your OpenAI or Anthropic API key")
    print("   - Add your Power BI Azure app credentials")
    print("\n2. Start the system:")
    if os.name == 'nt':
        print("   - Run start_all.bat to start both backend and frontend")
        print("   - Or run start_backend.bat and start_frontend.bat separately")
    else:
        print("   - Run ./start_all.sh to start both backend and frontend")
        print("   - Or run ./start_backend.sh and ./start_frontend.sh separately")
    
    print("\n🌐 Access URLs:")
    print("   - Backend API: http://localhost:8000")
    print("   - Frontend App: http://localhost:3000")
    print("\n📚 Documentation:")
    print("   - API Docs: http://localhost:8000/docs")
    print("   - Upload files and chat to create dashboards!")
    
    print("\n⚠️  Important:")
    print("   - Make sure to configure your .env file before starting")
    print("   - For Power BI integration, you need Azure App registration")
    print("   - Both AI API keys and Power BI credentials are required for full functionality")

if __name__ == "__main__":
    main()
