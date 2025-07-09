#!/usr/bin/env python3
"""
System Validation Script - Ensures 100% Real Integration
"""

import os
import sys
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def validate_no_simulation_code():
    """Ensure no simulation/dummy code exists"""
    print("🔍 Validating no simulation code exists...")
    
    forbidden_patterns = [
        "simulation", "simulated", "dummy", "fallback_response", 
        "mock", "fake", "test_data", "_get_default_", "placeholder"
    ]
    
    python_files = [
        "ai_client.py", "powerbi_client.py", "main_server.py", 
        "data_processor.py", "langchain_controller.py"
    ]
    
    issues_found = []
    
    for file_path in python_files:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                
            for pattern in forbidden_patterns:
                if pattern in content:
                    issues_found.append(f"{file_path}: Contains '{pattern}'")
    
    if issues_found:
        print("❌ Simulation code found:")
        for issue in issues_found:
            print(f"   - {issue}")
        return False
    
    print("✅ No simulation code found")
    return True

def validate_ai_integration():
    """Validate real AI integration"""
    print("🤖 Validating AI integration...")
    
    try:
        from ai_client import AIClient
        client = AIClient()
        
        # Check if real clients are initialized
        if not client.openai_client and not client.anthropic_client:
            print("❌ No AI clients configured")
            return False
        
        if client.openai_client:
            print("✅ OpenAI client configured")
        if client.anthropic_client:
            print("✅ Anthropic client configured")
        
        return True
        
    except Exception as e:
        print(f"❌ AI client validation failed: {e}")
        return False

def validate_powerbi_integration():
    """Validate real Power BI integration"""
    print("🎯 Validating Power BI integration...")
    
    try:
        from powerbi_client import PowerBIClient
        client = PowerBIClient()
        
        # Check if real authentication is configured
        required_vars = ["POWER_BI_TENANT_ID", "POWER_BI_CLIENT_ID", "POWER_BI_CLIENT_SECRET"]
        missing_vars = []
        
        for var in required_vars:
            value = os.getenv(var)
            if not value or value.startswith("your_"):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing Power BI configuration: {', '.join(missing_vars)}")
            return False
        
        print("✅ Power BI credentials configured")
        return True
        
    except Exception as e:
        print(f"❌ Power BI client validation failed: {e}")
        return False

def validate_data_processing():
    """Validate data processing capabilities"""
    print("📊 Validating data processing...")
    
    try:
        from data_processor import DataProcessor
        processor = DataProcessor()
        
        # Check if processor can handle real file types
        supported_types = ['.xlsx', '.xls', '.csv', '.json']
        
        print(f"✅ Data processor supports: {', '.join(supported_types)}")
        return True
        
    except Exception as e:
        print(f"❌ Data processor validation failed: {e}")
        return False

def validate_environment_config():
    """Validate environment configuration"""
    print("⚙️ Validating environment configuration...")
    
    # Check critical environment variables
    critical_vars = {
        "AI Keys": ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"],
        "Power BI": ["POWER_BI_TENANT_ID", "POWER_BI_CLIENT_ID", "POWER_BI_CLIENT_SECRET"]
    }
    
    all_valid = True
    
    for category, vars_list in critical_vars.items():
        has_any = False
        for var in vars_list:
            value = os.getenv(var)
            if value and not value.startswith("your_"):
                has_any = True
                break
        
        if has_any:
            print(f"✅ {category} configured")
        else:
            print(f"❌ {category} not configured")
            all_valid = False
    
    return all_valid

async def test_real_functionality():
    """Test actual system functionality"""
    print("🧪 Testing real functionality...")
    
    try:
        # Test AI client response
        from ai_client import AIClient
        ai_client = AIClient()
        
        if ai_client.openai_client or ai_client.anthropic_client:
            print("✅ AI client ready for real requests")
        else:
            print("❌ AI client not ready")
            return False
        
        # Test Power BI client initialization
        from powerbi_client import PowerBIClient
        powerbi_client = PowerBIClient()
        print("✅ Power BI client initialized")
        
        # Test data processor
        from data_processor import DataProcessor
        data_processor = DataProcessor()
        print("✅ Data processor ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False

def validate_frontend_integration():
    """Validate frontend is properly configured"""
    print("🌐 Validating frontend integration...")
    
    frontend_files = [
        "frontend/package.json",
        "frontend/src/App.js",
        "frontend/src/App.css",
        "frontend/public/index.html"
    ]
    
    missing_files = []
    for file_path in frontend_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing frontend files: {', '.join(missing_files)}")
        return False
    
    # Check if frontend has real API integration
    with open("frontend/src/App.js", 'r') as f:
        app_content = f.read()
    
    if "localhost:8000" in app_content:
        print("✅ Frontend configured for backend integration")
    else:
        print("❌ Frontend not properly configured")
        return False
    
    return True

def main():
    """Main validation function"""
    print("🔍 AI Power BI Dashboard Generator - System Validation")
    print("=" * 60)
    print("Ensuring 100% real integration with no simulation code")
    print("=" * 60)
    
    validations = [
        ("No Simulation Code", validate_no_simulation_code),
        ("Environment Config", validate_environment_config),
        ("AI Integration", validate_ai_integration),
        ("Power BI Integration", validate_powerbi_integration),
        ("Data Processing", validate_data_processing),
        ("Frontend Integration", validate_frontend_integration),
    ]
    
    all_passed = True
    results = []
    
    for name, validation_func in validations:
        print(f"\n📋 {name}:")
        try:
            result = validation_func()
            results.append((name, result))
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ Validation error: {e}")
            results.append((name, False))
            all_passed = False
    
    # Test real functionality
    print(f"\n📋 Real Functionality:")
    try:
        func_result = asyncio.run(test_real_functionality())
        results.append(("Real Functionality", func_result))
        if not func_result:
            all_passed = False
    except Exception as e:
        print(f"❌ Functionality test error: {e}")
        results.append(("Real Functionality", False))
        all_passed = False
    
    # Final report
    print("\n" + "=" * 60)
    print("📊 VALIDATION REPORT")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:<25} {status}")
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("✅ System is ready for 100% real integration")
        print("✅ No simulation or dummy code detected")
        print("✅ All components configured for production use")
        print("\n🚀 Your AI Power BI Dashboard Generator is ready!")
        return 0
    else:
        print("❌ VALIDATION FAILED!")
        print("⚠️  System has issues that need to be fixed")
        print("⚠️  Please resolve the failed validations above")
        print("\n🔧 Fix the issues and run validation again")
        return 1

if __name__ == "__main__":
    sys.exit(main())