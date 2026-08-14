import sys
import os

# Append the parent directory to sys.path so we can import 'backend.*' modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import re
from pathlib import Path

from backend.config import HOST, PORT
from backend.database import (
    init_db,
    get_all_courses,
    get_course_details,
    get_db_stats
)
from backend.parser import scan_and_ingest
from backend.agent import analyze_course_questions

app = FastAPI(title="COE Materials AI Agent API")

# Setup CORS for frontend and deployment communication
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")] if allowed_origins_env != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state to track ingestion progress
class IngestionState:
    is_indexing = False
    message = "Idle"
    error = None

state = IngestionState()

@app.on_event("startup")
async def startup_event():
    # Automatically initialize tables on start
    try:
        await init_db()
    except Exception as e:
        print(f"Error initializing DB during startup: {e}")

async def run_ingestion_task():
    state.is_indexing = True
    state.message = "Scanning coe materials and parsing PDFs..."
    state.error = None
    try:
        # Run scan and ingest in a separate thread if needed, or simply await since it is async
        await scan_and_ingest()
        state.message = "Ingestion completed successfully."
    except Exception as e:
        state.message = "Ingestion failed."
        state.error = str(e)
        print(f"Ingestion task failed: {e}")
    finally:
        state.is_indexing = False

class QueryRequest(BaseModel):
    course_code: Optional[str] = None
    portion_query: str

@app.get("/api/status")
async def get_status():
    """Returns database stats and indexing status."""
    try:
        stats = await get_db_stats()
    except Exception as e:
        stats = {"total_courses": 0, "total_papers": 0, "total_questions": 0, "db_error": str(e)}
        
    return {
        "is_indexing": state.is_indexing,
        "indexing_message": state.message,
        "indexing_error": state.error,
        "stats": stats
    }

@app.post("/api/ingest")
async def trigger_ingest(background_tasks: BackgroundTasks):
    """Triggers PDF ingestion in the background."""
    if state.is_indexing:
        return {"status": "already_running", "message": "Indexing is already in progress."}
        
    background_tasks.add_task(run_ingestion_task)
    return {"status": "started", "message": "Indexing started in background."}

@app.get("/api/courses")
async def list_courses():
    """Returns a list of all courses, merging DB indexed courses and cache courses."""
    try:
        # Get already indexed courses from DB
        db_courses = await get_all_courses()
        db_codes = {c["course_code"].upper() for c in db_courses}
        
        # Load from course_code_cache.json
        cache_courses = []
        cache_file = Path(__file__).resolve().parent / "course_code_cache.json"
        if cache_file.exists():
            try:
                import json
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Department mapping helper
                def get_dept_from_code(code: str) -> str:
                    prefix = re.match(r'^([A-Z]{3,4})', code.upper())
                    if not prefix:
                        return "General"
                    p = prefix.group(1)
                    if p in {"UCS", "ICS", "PCP", "UCO", "PCO"}:
                        return "Computer Science & Engineering"
                    elif p in {"UIT", "PIF"}:
                        return "Information Technology"
                    elif p in {"UEC", "PEC"}:
                        return "Electronics & Communication"
                    elif p in {"UEE", "PED"}:
                        return "Electrical & Electronics"
                    elif p in {"UBM", "PBM"}:
                        return "Biomedical Engineering"
                    elif p in {"IBA", "PBA"}:
                        return "Management Studies"
                    elif p in {"UMA", "PMA"}:
                        return "Mathematics"
                    elif p in {"UCY", "PCY"}:
                        return "Chemistry"
                    elif p in {"UPH", "PPH"}:
                        return "Physics"
                    elif p in {"UHS"}:
                        return "Humanities & Sciences"
                    return p  # fallback to prefix
                
                for code, name in cache_data.items():
                    code_upper = code.upper()
                    if code_upper not in db_codes:
                        cache_courses.append({
                            "course_code": code_upper,
                            "course_name": name,
                            "department": get_dept_from_code(code_upper),
                            "regulation": "Curriculum"
                        })
            except Exception as ce:
                print(f"Error loading course cache: {ce}")
                
        # Merge DB courses (higher priority) and cache courses
        all_courses = db_courses + cache_courses
        # Sort by course code
        all_courses.sort(key=lambda x: x["course_code"])
        return {"courses": all_courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/courses/{course_code}")
async def course_info(course_code: str):
    """Returns details and syllabus portions for a course."""
    try:
        details = await get_course_details(course_code)
        if not details:
            raise HTTPException(status_code=404, detail="Course not found")
        return details
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/query")
async def query_agent(payload: QueryRequest):
    """Analyzes questions for a course and portion using the AI agent."""
    if not payload.portion_query or payload.portion_query.strip() == "":
        raise HTTPException(status_code=400, detail="Query text is required.")
        
    try:
        course_str = payload.course_code if payload.course_code else "General Chat"
        print(f"Received query request: Course={course_str}, Query={payload.portion_query}")
        result = await analyze_course_questions(payload.course_code, payload.portion_query)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Agent error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
