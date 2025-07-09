#!/usr/bin/env python3
"""
AI Power BI Dashboard Generator - Run Script
Simple script to start the complete system with proper configuration checking.
"""

import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path
import threading

def print_banner():
    """Print application banner"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║    🤖 AI Power BI Dashboard Generator                         ║
║                                                               ║
║    Create professional Power BI dashboards by chatting!      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_environment():
    """Check if environment is properly set up"""
    print("🔍 Checking environment setup...")
    
    issues = []
    
    # Check if virtual environment exists
    if not Path("venv").exists():
        issues.append("Virtual environment not found. Run 'python setup.py' first.")
    
    # Check if requirements are installed
    if Path("venv").exists():
        try:
            if os.name == 'nt':  # Windows
                result = subprocess.run(
                    "venv\\Scripts\\python -c \"import fastapi, openai, pandas\"",
                    shell=True, capture_output=True, text=True
                )
            else:  # Unix/Linux/macOS
                result = subprocess.run(
                    "venv/bin/python -c \"import fastapi, openai, pandas\"",
                    shell=True, capture_output=True, text=True
                )
            
            if result.returncode != 0:
                issues.append("Python dependencies not installed. Run 'python setup.py' first.")
        except:
            issues.append("Cannot verify Python dependencies.")
    
    # Check if .env file exists
    if not Path(".env").exists():
        issues.append("Environment file (.env) not found. Copy .env.example to .env and configure.")
    
    # Check if frontend is set up
    if Path("frontend").exists() and Path("frontend/package.json").exists():
        if not Path("frontend/node_modules").exists():
            issues.append("Frontend dependencies not installed. Run 'python setup.py' or 'cd frontend && npm install'.")
    
    if issues:
        print("❌ Setup issues found:")
        for issue in issues:
            print(f"   • {issue}")
        print("\n🔧 Please run 'python setup.py' to fix these issues.")
        return False
    
    print("✅ Environment setup looks good!")
    return True

def check_api_keys():
    """Check if API keys are configured"""
    print("🔑 Checking API key configuration...")
    
    if not Path(".env").exists():
        print("❌ No .env file found")
        return False
    
    # Read .env file
    env_vars = {}
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    
    # Check for AI API keys
    has_openai = env_vars.get("OPENAI_API_KEY", "").replace("your_openai_api_key_here", "").strip()
    has_anthropic = env_vars.get("ANTHROPIC_API_KEY", "").replace("your_anthropic_api_key_here", "").strip()
    
    if not has_openai and not has_anthropic:
        print("❌ No AI API keys configured!")
        print("   Please add either OPENAI_API_KEY or ANTHROPIC_API_KEY to your .env file")
        print("   The system CANNOT function without AI integration.")
        return False
    
    if has_openai:
        print("✅ OpenAI API key configured")
    if has_anthropic:
        print("✅ Anthropic API key configured")
    
    # Check Power BI configuration
    has_powerbi = all([
        env_vars.get("POWER_BI_TENANT_ID", "").replace("your_azure_tenant_id", "").strip(),
        env_vars.get("POWER_BI_CLIENT_ID", "").replace("your_azure_app_client_id", "").strip(),
        env_vars.get("POWER_BI_CLIENT_SECRET", "").replace("your_azure_app_client_secret", "").strip()
    ])
    
    if has_powerbi:
        print("✅ Power BI credentials configured - Real dashboards will be created!")
    else:
        print("❌ Power BI credentials not configured - Dashboard creation will FAIL")
        print("   Add your Azure app credentials to .env for Power BI integration")
        print("   System requires both AI API keys AND Power BI credentials to function")
    
    return True

def start_backend():
    """Start the backend server"""
    print("🚀 Starting backend server...")
    
    try:
        # Set environment variables
        env = os.environ.copy()
        if Path(".env").exists():
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env[key.strip()] = value.strip()
        
        # Start the server
        if os.name == 'nt':  # Windows
            cmd = "venv\\Scripts\\python main.py"
        else:  # Unix/Linux/macOS
            cmd = "venv/bin/python main.py"
        
        process = subprocess.Popen(
            cmd,
            shell=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor output
        backend_ready = False
        for line in iter(process.stdout.readline, ''):
            print(f"[Backend] {line.strip()}")
            if "Application startup complete" in line or "Uvicorn running on" in line:
                backend_ready = True
                break
            if process.poll() is not None:
                break
        
        if backend_ready:
            print("✅ Backend server is running!")
            return process
        else:
            print("❌ Backend failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Error starting backend: {e}")
        return None

def start_frontend():
    """Start the frontend development server"""
    print("⚛️  Starting frontend server...")
    
    try:
        if not Path("frontend").exists():
            print("⚠️  Frontend directory not found, skipping frontend startup")
            return None
        
        process = subprocess.Popen(
            "npm start",
            shell=True,
            cwd="frontend",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor output
        frontend_ready = False
        for line in iter(process.stdout.readline, ''):
            print(f"[Frontend] {line.strip()}")
            if "webpack compiled" in line.lower() or "compiled successfully" in line.lower():
                frontend_ready = True
                break
            if "Local:" in line and "http://localhost:3000" in line:
                frontend_ready = True
                break
            if process.poll() is not None:
                break
        
        if frontend_ready:
            print("✅ Frontend server is running!")
            return process
        else:
            print("❌ Frontend failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        return None

def open_browser():
    """Open browser to the application"""
    time.sleep(3)  # Wait a bit for servers to fully start
    print("🌐 Opening browser...")
    try:
        webbrowser.open("http://localhost:3000")
    except:
        print("Could not open browser automatically")

def main():
    """Main function"""
    print_banner()
    
    # Check if setup is complete
    if not check_environment():
        sys.exit(1)
    
    # Check API keys - exit if not configured
    if not check_api_keys():
        print("\n❌ Cannot start system without proper configuration!")
        print("Please configure your .env file with required API keys.")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("🚀 Starting AI Power BI Dashboard Generator")
    print("="*60)
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        print("❌ Cannot start without backend server")
        sys.exit(1)
    
    # Start frontend in a separate thread
    frontend_process = None
    if Path("frontend").exists():
        frontend_thread = threading.Thread(target=lambda: globals().update({'frontend_process': start_frontend()}))
        frontend_thread.daemon = True
        frontend_thread.start()
        
        # Wait a bit for frontend to start
        time.sleep(5)
    
    # Open browser
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    print("\n" + "="*60)
    print("🎉 AI Power BI Dashboard Generator is running!")
    print("="*60)
    print("\n📍 Access URLs:")
    print("   • Frontend App: http://localhost:3000")
    print("   • Backend API:  http://localhost:8000")
    print("   • API Docs:     http://localhost:8000/docs")
    
    print("\n💡 How to use:")
    print("   1. Open http://localhost:3000 in your browser")
    print("   2. Upload your data files (Excel, CSV, JSON)")
    print("   3. Chat with AI to create your dashboard!")
    print("   4. Example: 'Create a sales dashboard with monthly trends'")
    
    print("\n⚠️  Notes:")
    if not check_api_keys():
        print("   • Configure API keys in .env for full AI functionality")
    print("   • Press Ctrl+C to stop all services")
    print("   • Check logs if you encounter any issues")
    
    print("\n🔄 System Status:")
    print(f"   • Backend:  ✅ Running on port 8000")
    if Path("frontend").exists():
        print(f"   • Frontend: ✅ Running on port 3000")
    else:
        print(f"   • Frontend: ⚠️  Not available")
    
    try:
        # Keep the script running
        print("\n" + "="*60)
        print("Press Ctrl+C to stop all services...")
        while True:
            time.sleep(1)
            # Check if backend is still running
            if backend_process.poll() is not None:
                print("❌ Backend process stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping services...")
        
        # Terminate processes
        if backend_process:
            backend_process.terminate()
            print("✅ Backend stopped")
        
        if frontend_process:
            frontend_process.terminate()
            print("✅ Frontend stopped")
        
        print("👋 Thanks for using AI Power BI Dashboard Generator!")

if __name__ == "__main__":
    main()
