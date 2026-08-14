import libsql_client
from backend.config import DATABASE_URL, DATABASE_AUTH_TOKEN, BASE_DIR

# Absolute local database URL to ensure consistency across directory roots
local_db_path = BASE_DIR / "coe_materials.db"
local_url = f"file:{local_db_path.as_posix()}"

def is_read_query(query: str) -> bool:
    cleaned = query.strip().upper()
    return cleaned.startswith("SELECT")

# Circuit breaker flag to disable cloud DB calls if connection fails
CLOUD_ACTIVE = True

def get_cloud_db_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    cleaned = raw_url.strip()
    # Convert libsql:// to https:// so libsql_client uses reliable HTTP Hrana instead of WebSockets
    if cleaned.startswith("libsql://"):
        return "https://" + cleaned[len("libsql://"):]
    return cleaned

# Helper to execute queries on both local and cloud databases
async def execute_query(query: str, params: list = None):
    global CLOUD_ACTIVE
    use_cloud = CLOUD_ACTIVE and DATABASE_URL and (DATABASE_URL.startswith("libsql://") or DATABASE_URL.startswith("https://"))
    
    cloud_result = None
    cloud_success = False
    
    # 1. Try executing on Cloud Turso DB if configured
    if use_cloud:
        try:
            token = DATABASE_AUTH_TOKEN.strip() if DATABASE_AUTH_TOKEN else None
            cloud_url = get_cloud_db_url(DATABASE_URL)
            client = libsql_client.create_client(url=cloud_url, auth_token=token)
            try:
                cloud_result = await client.execute(query, params or [])
                cloud_success = True
            finally:
                await client.close()
        except Exception as e:
            print(f"[Database Warn] Cloud DB query failed: {e}. Disabling Cloud DB (circuit breaker tripped)...")
            CLOUD_ACTIVE = False
            
    # 2. Execute on Local SQLite DB
    # - If read query and cloud succeeded, skip local DB read
    if is_read_query(query) and cloud_success:
        return cloud_result
        
    try:
        client = libsql_client.create_client(url=local_url)
        try:
            local_result = await client.execute(query, params or [])
            return local_result
        finally:
            await client.close()
    except Exception as e:
        print(f"[Database Error] Local DB query failed: {e}")
        if cloud_success:
            return cloud_result
        raise e

# Batch execute multiple queries
async def execute_batch(queries_with_params: list):
    global CLOUD_ACTIVE
    use_cloud = CLOUD_ACTIVE and DATABASE_URL and (DATABASE_URL.startswith("libsql://") or DATABASE_URL.startswith("https://"))
    
    cloud_results = None
    cloud_success = False
    
    # 1. Try Cloud DB
    if use_cloud:
        try:
            token = DATABASE_AUTH_TOKEN.strip() if DATABASE_AUTH_TOKEN else None
            cloud_url = get_cloud_db_url(DATABASE_URL)
            client = libsql_client.create_client(url=cloud_url, auth_token=token)
            try:
                results = []
                for query, params in queries_with_params:
                    res = await client.execute(query, params)
                    results.append(res)
                cloud_results = results
                cloud_success = True
            finally:
                await client.close()
        except Exception as e:
            print(f"[Database Warn] Cloud DB batch failed: {e}. Disabling Cloud DB (circuit breaker tripped)...")
            CLOUD_ACTIVE = False
            
    # 2. Local DB
    all_reads = all(is_read_query(q) for q, _ in queries_with_params)
    if all_reads and cloud_success:
        return cloud_results
        
    try:
        client = libsql_client.create_client(url=local_url)
        try:
            local_results = []
            for query, params in queries_with_params:
                res = await client.execute(query, params)
                local_results.append(res)
            return local_results
        finally:
            await client.close()
    except Exception as e:
        print(f"[Database Error] Local DB batch failed: {e}")
        if cloud_success:
            return cloud_results
        raise e

async def init_db():
    print(f"Initializing database. Cloud: {DATABASE_URL}, Local fallback: file:coe_materials.db")
    
    # Create courses table
    await execute_query("""
    CREATE TABLE IF NOT EXISTS courses (
        course_code TEXT PRIMARY KEY,
        course_name TEXT NOT NULL,
        department TEXT,
        regulation TEXT
    )
    """)
    
    # Create course_portions table (syllabus units)
    await execute_query("""
    CREATE TABLE IF NOT EXISTS course_portions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_code TEXT,
        unit_number INTEGER,
        unit_title TEXT,
        unit_content TEXT,
        FOREIGN KEY(course_code) REFERENCES courses(course_code)
    )
    """)
    
    # Create question_papers table
    await execute_query("""
    CREATE TABLE IF NOT EXISTS question_papers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT UNIQUE,
        course_code TEXT,
        semester TEXT,
        exam_period TEXT,
        raw_text TEXT
    )
    """)
    
    # Create questions table
    await execute_query("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        qp_id INTEGER,
        part TEXT,
        question_number INTEGER,
        question_text TEXT,
        marks INTEGER,
        FOREIGN KEY(qp_id) REFERENCES question_papers(id)
    )
    """)
    print("Database tables initialized successfully.")

# Database Helper Functions
async def add_course(course_code: str, course_name: str, department: str = "", regulation: str = ""):
    await execute_query(
        "INSERT OR REPLACE INTO courses (course_code, course_name, department, regulation) VALUES (?, ?, ?, ?)",
        [course_code.upper().strip(), course_name.strip(), department, regulation]
    )

async def add_course_portion(course_code: str, unit_number: int, unit_title: str, unit_content: str):
    # Check if this portion already exists for the course
    res = await execute_query(
        "SELECT id FROM course_portions WHERE course_code = ? AND unit_number = ?",
        [course_code.upper().strip(), unit_number]
    )
    if res.rows:
        portion_id = res.rows[0][0]
        await execute_query(
            "UPDATE course_portions SET unit_title = ?, unit_content = ? WHERE id = ?",
            [unit_title, unit_content, portion_id]
        )
    else:
        await execute_query(
            "INSERT INTO course_portions (course_code, unit_number, unit_title, unit_content) VALUES (?, ?, ?, ?)",
            [course_code.upper().strip(), unit_number, unit_title, unit_content]
        )

async def add_question_paper(filepath: str, course_code: str, semester: str, exam_period: str, raw_text: str):
    res = await execute_query(
        "INSERT OR REPLACE INTO question_papers (filepath, course_code, semester, exam_period, raw_text) VALUES (?, ?, ?, ?, ?)",
        [filepath, course_code.upper().strip(), semester, exam_period, raw_text]
    )
    # Get the ID of the inserted paper
    res = await execute_query("SELECT id FROM question_papers WHERE filepath = ?", [filepath])
    return res.rows[0][0] if res.rows else None

async def add_question(qp_id: int, part: str, question_number: int, question_text: str, marks: int):
    # Prevent inserting duplicate questions for the same QP
    res = await execute_query(
        "SELECT id FROM questions WHERE qp_id = ? AND part = ? AND question_number = ?",
        [qp_id, part, question_number]
    )
    if res.rows:
        q_id = res.rows[0][0]
        await execute_query(
            "UPDATE questions SET question_text = ?, marks = ? WHERE id = ?",
            [question_text, marks, q_id]
        )
    else:
        await execute_query(
            "INSERT INTO questions (qp_id, part, question_number, question_text, marks) VALUES (?, ?, ?, ?, ?)",
            [qp_id, part, question_number, question_text, marks]
        )

async def clear_qp_questions(qp_id: int):
    await execute_query("DELETE FROM questions WHERE qp_id = ?", [qp_id])

async def get_all_courses():
    res = await execute_query("SELECT course_code, course_name, department, regulation FROM courses")
    return [
        {"course_code": row[0], "course_name": row[1], "department": row[2], "regulation": row[3]}
        for row in res.rows
    ]

async def get_course_details(course_code: str):
    res = await execute_query(
        "SELECT course_code, course_name, department, regulation FROM courses WHERE course_code = ?",
        [course_code.upper().strip()]
    )
    if not res.rows:
        return None
    row = res.rows[0]
    
    # Get portions
    portions_res = await execute_query(
        "SELECT unit_number, unit_title, unit_content FROM course_portions WHERE course_code = ? ORDER BY unit_number",
        [course_code.upper().strip()]
    )
    portions = [
        {"unit_number": r[0], "unit_title": r[1], "unit_content": r[2]}
        for r in portions_res.rows
    ]
    
    return {
        "course_code": row[0],
        "course_name": row[1],
        "department": row[2],
        "regulation": row[3],
        "portions": portions
    }

async def get_course_questions(course_code: str):
    # Get questions across all question papers for a course
    query = """
    SELECT q.id, q.part, q.question_number, q.question_text, q.marks, qp.exam_period, qp.semester
    FROM questions q
    JOIN question_papers qp ON q.qp_id = qp.id
    WHERE qp.course_code = ?
    ORDER BY qp.exam_period DESC, q.part, q.question_number
    """
    res = await execute_query(query, [course_code.upper().strip()])
    return [
        {
            "id": row[0],
            "part": row[1],
            "question_number": row[2],
            "question_text": row[3],
            "marks": row[4],
            "exam_period": row[5],
            "semester": row[6]
        }
        for row in res.rows
    ]

async def get_db_stats():
    courses_cnt = await execute_query("SELECT COUNT(*) FROM courses")
    papers_cnt = await execute_query("SELECT COUNT(*) FROM question_papers")
    questions_cnt = await execute_query("SELECT COUNT(*) FROM questions")
    return {
        "total_courses": courses_cnt.rows[0][0] if courses_cnt.rows else 0,
        "total_papers": papers_cnt.rows[0][0] if papers_cnt.rows else 0,
        "total_questions": questions_cnt.rows[0][0] if questions_cnt.rows else 0
    }
