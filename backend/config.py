import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file relative to this file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

BASE_DIR = Path(__file__).resolve().parent.parent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "file:coe_materials.db")
DATABASE_AUTH_TOKEN = os.getenv("DATABASE_AUTH_TOKEN", "")

# Default COE materials directory (relative to workspace or absolute)
COE_MATERIALS_DIR = os.getenv("COE_MATERIALS_DIR", str(BASE_DIR / "coe materials"))

# Host & Port settings
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

print("Configuration Loaded:")
print(f"  - Database URL: {DATABASE_URL}")
print(f"  - Materials Dir: {COE_MATERIALS_DIR}")
print(f"  - Gemini Key Present: {bool(GEMINI_API_KEY)}")
print(f"  - OpenAI Key Present: {bool(OPENAI_API_KEY)}")
