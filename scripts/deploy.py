#!/usr/bin/env python3
"""
Production Deployment Script for AI Power BI Dashboard Generator
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_production_requirements():
    """Check if all production requirements are met"""
    print("🔍 Checking production requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print("✅ Python version OK")
    
    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Node.js not found")
            return False
        print(f"✅ Node.js version: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Node.js not installed")
        return False
    
    # Check environment file
    if not os.path.exists(".env"):
        print("❌ .env file not found")
        return False
    
    # Validate environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check AI API keys
    has_openai = os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here"
    has_anthropic = os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_API_KEY") != "your_anthropic_api_key_here"
    
    if not has_openai and not has_anthropic:
        print("❌ No AI API keys configured")
        return False
    print("✅ AI API keys configured")
    
    # Check Power BI credentials
    powerbi_keys = ["POWER_BI_TENANT_ID", "POWER_BI_CLIENT_ID", "POWER_BI_CLIENT_SECRET"]
    has_powerbi = all(
        os.getenv(key) and os.getenv(key) != f"your_{key.lower().replace('_', '_')}"
        for key in powerbi_keys
    )
    
    if not has_powerbi:
        print("❌ Power BI credentials not configured")
        return False
    print("✅ Power BI credentials configured")
    
    return True

def install_dependencies():
    """Install production dependencies"""
    print("📦 Installing dependencies...")
    
    # Install Python dependencies
    print("Installing Python packages...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    if result.returncode != 0:
        print("❌ Failed to install Python dependencies")
        return False
    
    # Install Node.js dependencies
    print("Installing Node.js packages...")
    os.chdir("frontend")
    result = subprocess.run(["npm", "install", "--production"])
    if result.returncode != 0:
        print("❌ Failed to install Node.js dependencies")
        return False
    os.chdir("..")
    
    print("✅ Dependencies installed")
    return True

def build_frontend():
    """Build production frontend"""
    print("🏗️ Building frontend for production...")
    
    os.chdir("frontend")
    result = subprocess.run(["npm", "run", "build"])
    if result.returncode != 0:
        print("❌ Frontend build failed")
        return False
    os.chdir("..")
    
    print("✅ Frontend built successfully")
    return True

def create_production_config():
    """Create production configuration"""
    print("⚙️ Creating production configuration...")
    
    # Create production .env if it doesn't exist
    if not os.path.exists(".env.production"):
        with open(".env.production", "w") as f:
            f.write("""# Production Configuration
DEBUG=False
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Copy your real credentials from .env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
POWER_BI_TENANT_ID=
POWER_BI_CLIENT_ID=
POWER_BI_CLIENT_SECRET=
POWER_BI_USERNAME=
POWER_BI_PASSWORD=

# Production Database
DATABASE_URL=postgresql://user:password@localhost/powerbi_db

# Security
SECRET_KEY=your-production-secret-key-here

# CORS for production
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
""")
        print("✅ Created .env.production template")
    
    # Create systemd service file
    service_content = f"""[Unit]
Description=AI Power BI Dashboard Generator
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory={os.getcwd()}
Environment=PATH={os.getcwd()}/venv/bin
EnvironmentFile={os.getcwd()}/.env.production
ExecStart={sys.executable} main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    with open("powerbi-dashboard.service", "w") as f:
        f.write(service_content)
    
    print("✅ Created systemd service file")
    return True

def create_nginx_config():
    """Create nginx configuration"""
    print("🌐 Creating nginx configuration...")
    
    nginx_config = """server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Serve React frontend
    location / {
        root /path/to/PowerBI_V2/frontend/build;
        try_files $uri $uri/ /index.html;
    }
    
    # Proxy API requests to FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket support for real-time updates
    location /ws {
        proxy_pass http://127.0.0.1:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
"""
    
    with open("nginx-powerbi-dashboard.conf", "w") as f:
        f.write(nginx_config)
    
    print("✅ Created nginx configuration")
    return True

def run_production_tests():
    """Run production readiness tests"""
    print("🧪 Running production tests...")
    
    # Test AI client
    try:
        from ai_client import AIClient
        client = AIClient()
        print("✅ AI client initialized")
    except Exception as e:
        print(f"❌ AI client test failed: {e}")
        return False
    
    # Test Power BI client
    try:
        from powerbi_client import PowerBIClient
        client = PowerBIClient()
        print("✅ Power BI client initialized")
    except Exception as e:
        print(f"❌ Power BI client test failed: {e}")
        return False
    
    # Test data processor
    try:
        from data_processor import DataProcessor
        processor = DataProcessor()
        print("✅ Data processor initialized")
    except Exception as e:
        print(f"❌ Data processor test failed: {e}")
        return False
    
    print("✅ All production tests passed")
    return True

def main():
    """Main deployment function"""
    print("🚀 AI Power BI Dashboard Generator - Production Deployment")
    print("=" * 60)
    
    # Check requirements
    if not check_production_requirements():
        print("\n❌ Production requirements not met!")
        print("Please fix the issues above before deploying.")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Failed to install dependencies!")
        sys.exit(1)
    
    # Build frontend
    if not build_frontend():
        print("\n❌ Failed to build frontend!")
        sys.exit(1)
    
    # Create production config
    if not create_production_config():
        print("\n❌ Failed to create production config!")
        sys.exit(1)
    
    # Create nginx config
    create_nginx_config()
    
    # Run tests
    if not run_production_tests():
        print("\n❌ Production tests failed!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ DEPLOYMENT READY!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Copy .env.production and add your real credentials")
    print("2. Set up PostgreSQL database (optional)")
    print("3. Copy powerbi-dashboard.service to /etc/systemd/system/")
    print("4. Copy nginx-powerbi-dashboard.conf to /etc/nginx/sites-available/")
    print("5. Enable and start services:")
    print("   sudo systemctl enable powerbi-dashboard")
    print("   sudo systemctl start powerbi-dashboard")
    print("   sudo nginx -t && sudo systemctl reload nginx")
    print("\n🌐 Your AI Power BI Dashboard Generator is ready for production!")

if __name__ == "__main__":
    main()