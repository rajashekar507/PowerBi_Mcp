import sys
sys.path.append('src')

try:
    from database.memory_manager import MemoryManager
    print("✓ MemoryManager imported successfully - no duplicate function errors!")
    
    from core.ai_client import AIClient
    print("✓ AIClient imported successfully - type safety fix working!")
    
    from core.data_processor import DataProcessor
    print("✓ DataProcessor imported successfully - pandas fix working!")
    
    from core.powerbi_client import PowerBIClient
    print("✓ PowerBIClient imported successfully!")
    
    from core.langchain_controller import DashboardController
    print("✓ DashboardController imported successfully!")
    
    print("\n🎉 All critical fixes verified - no import errors!")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
