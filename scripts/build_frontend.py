#!/usr/bin/env python3
"""
Frontend build script for AI Power BI Dashboard Generator
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minute timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def build_frontend():
    """Build the React frontend"""
    print("🚀 Building Frontend...")
    
    # Get project root
    project_root = Path(__file__).parent.parent
    frontend_dir = project_root / "frontend"
    
    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        return False
    
    print(f"📁 Frontend directory: {frontend_dir}")
    
    # Check if node_modules exists
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("📦 Installing dependencies...")
        success, stdout, stderr = run_command("npm install", cwd=frontend_dir)
        if not success:
            print(f"❌ Failed to install dependencies: {stderr}")
            return False
        print("✅ Dependencies installed successfully")
    
    # Build the project
    print("🔨 Building React app...")
    success, stdout, stderr = run_command("npm run build", cwd=frontend_dir)
    
    if not success:
        print(f"❌ Build failed: {stderr}")
        # Try alternative build method
        print("🔄 Trying alternative build method...")
        success, stdout, stderr = run_command("npx react-scripts build", cwd=frontend_dir)
        
        if not success:
            print(f"❌ Alternative build also failed: {stderr}")
            return False
    
    # Check if build directory was created
    build_dir = frontend_dir / "build"
    if build_dir.exists():
        print("✅ Frontend build completed successfully!")
        print(f"📁 Build output: {build_dir}")
        
        # List build contents
        build_files = list(build_dir.rglob("*"))
        print(f"📄 Build contains {len(build_files)} files")
        
        return True
    else:
        print("❌ Build directory not created")
        return False

def main():
    """Main function"""
    print("=" * 50)
    print("🎯 AI Power BI Frontend Build Script")
    print("=" * 50)
    
    if build_frontend():
        print("\n✅ Frontend build completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Frontend build failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()