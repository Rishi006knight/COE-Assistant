import sys
import os

# Append the project root to the sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    print("Testing Backend Python Imports...")
    
    try:
        import backend.config as config
        print("  [OK] config.py imported successfully.")
    except Exception as e:
        print(f"  [ERROR] config.py failed: {e}")
        return False
        
    try:
        import backend.database as database
        print("  [OK] database.py imported successfully.")
    except Exception as e:
        print(f"  [ERROR] database.py failed: {e}")
        return False

    try:
        import backend.parser as parser
        print("  [OK] parser.py imported successfully.")
    except Exception as e:
        print(f"  [ERROR] parser.py failed: {e}")
        return False

    try:
        import backend.agent as agent
        print("  [OK] agent.py imported successfully.")
        
        # Test Gemini connection and list models
        if agent.GEMINI_API_KEY:
            print("\nQuerying available Gemini models for your API key...")
            import google.generativeai as genai
            genai.configure(api_key=agent.GEMINI_API_KEY)
            models = list(genai.list_models())
            print(f"  Found {len(models)} available models:")
            for m in models:
                if 'generateContent' in m.supported_generation_methods:
                    print(f"    - {m.name}")
            print("")
    except Exception as e:
        print(f"  [ERROR] agent.py failed or Gemini query failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    try:
        import backend.main as main
        print("  [OK] main.py (FastAPI App) imported successfully.")
    except Exception as e:
        print(f"  [ERROR] main.py failed: {e}")
        return False

    print("\nAll Backend Imports passed successfully! Logical files are syntax-error free.")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
