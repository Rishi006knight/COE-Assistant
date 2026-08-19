import os
import re
import time
import asyncio
from pathlib import Path
import google.generativeai as genai
from openai import OpenAI
from backend.config import GEMINI_API_KEY, OPENAI_API_KEY, COE_MATERIALS_DIR
from backend.database import get_course_details, get_course_questions
from backend.parser import extract_text_from_pdf
from pypdf import PdfReader

# Configure Google Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Initialize OpenAI Client
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are an expert Autonomous Academic AI Tutor and University Exam Specialist.
Your goal is to provide exceptionally clear, beautifully structured, and comprehensive responses for university students.

### CRITICAL FORMATTING & STRUCTURE RULES:
1. **Always Use Clean Markdown Structure**:
   - Organize every response with clear headings (e.g. `## 📌 Overview`, `## 📋 Key Concepts`, `## 📊 Comparison / Analysis`, `## 💡 Exam Tips & Key Takeaways`).
   - Use double line breaks between paragraphs, list items, and sections to ensure clean visual separation.
   
2. **Use Structured Tables**:
   - Whenever comparing concepts, summarizing topics, or listing question frequencies and marks, ALWAYS format them as clean Markdown tables with header rows (`| Header 1 | Header 2 | Header 3 |`).
   
3. **Use Bullet Points with Bold Titles**:
   - Format lists with clear bold prefixes, e.g.:
     - **Concept Name**: Direct concise explanation or details.
     - **Key Feature**: Explanation...
   - Avoid long dense walls of unbroken text.
   
4. **Highlight Key Takeaways & Warnings**:
   - Use Markdown blockquotes for tips or important notes:
     > 💡 **Exam Tip:** Focus on Unit 2 architecture diagrams as they carry 16 marks regularly.
     
5. **Formulas and Code**:
   - DO NOT use LaTeX ($ or $$ delimiters). Use clean plain text, unicode characters (e.g., θ, λ, ∑, ², ³, →, ↔), or inline code (` `) instead.
   - For code or pseudo-code, always specify language tags (e.g. ```python, ```html, ```c).

6. **For Question Paper & Repeated Questions Queries**:
   - Group questions by frequency (High Frequency, Medium Frequency, Once Asked).
   - Include a summary table of Repeated Questions: `| Question | Marks | Frequency / Years | Unit / Topic |`.
   - List detailed questions with their exact parts (Part A / Part B), marks, and exam periods.
"""

def call_gemini_api(prompt: str) -> str:
    """Call Google Gemini API."""
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API Key is not configured.")
    
    # Try standard model names in order
    models_to_try = ['gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-2.5-flash']
    last_err = None
    
    for model_name in models_to_try:
        try:
            print(f"Trying Gemini model: {model_name}...")
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT
            )
            # 30-second timeout to prevent hanging forever
            response = model.generate_content(
                prompt,
                request_options={"timeout": 30}
            )
            if response.text:
                print(f"Success using Gemini model: {model_name}")
                return response.text
        except Exception as e:
            print(f"Gemini model {model_name} failed: {e}")
            last_err = e
            continue
            
    raise last_err or ValueError("All Gemini model attempts failed.")

def call_openai_api(prompt: str) -> str:
    """Call OpenAI API (fallback)."""
    if not openai_client:
        raise ValueError("OpenAI API Client is not initialized (Key is missing).")
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        timeout=30
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("Received empty response from OpenAI API.")
    return content

COURSE_CODE_PATTERN = re.compile(r'\b(U[A-Z]{2,3}\d{4})\b')

async def resolve_course_codes_for_query(query_text: str) -> list:
    """
    Attempts to resolve a course name (like 'Operating Systems') to course codes
    (like 'UCS2043') by querying the DB first. If the DB is empty, it scans
    the curriculum PDFs and question papers in the folder to find the mapping on-the-fly.
    """
    resolved_codes = []
    
    # Clean the input query (strip common query prefixes)
    query_text_clean = query_text.lower().strip()
    patterns = [
        r"^repeated\s+questions\s+(?:in|for|of)\s+",
        r"^important\s+questions\s+(?:in|for|of)\s+",
        r"^questions\s+(?:in|for|of|about)\s+",
        r"^syllabus\s+(?:in|for|of)\s+",
        r"^notes\s+(?:in|for|of)\s+",
        r"^materials\s+(?:in|for|of)\s+",
        r"^show\s+me\s+(?:repeated|important)?\s*questions\s+(?:in|for|of)\s+",
        r"^give\s+me\s+(?:repeated|important)?\s*questions\s+(?:in|for|of)\s+",
        r"^list\s+(?:repeated|important)?\s*questions\s+(?:in|for|of)\s+",
    ]
    for pattern in patterns:
        query_text_clean = re.sub(pattern, "", query_text_clean, flags=re.IGNORECASE)
    query_text_clean = query_text_clean.strip()
    
    print(f"Resolving course codes for cleaned query: '{query_text_clean}' (original: '{query_text}')")
    
    # 1. Try resolving via Database
    try:
        from backend.database import execute_query
        # Search for course names matching the query
        db_res = await execute_query(
            "SELECT course_code FROM courses WHERE course_name LIKE ? OR course_code LIKE ?",
            [f"%{query_text_clean}%", f"%{query_text_clean}%"]
        )
        if db_res.rows:
            for row in db_res.rows:
                resolved_codes.append(row[0].upper())
            print(f"Resolved course codes from DB: {resolved_codes}")
            return resolved_codes
    except Exception as e:
        print(f"DB course resolution failed: {e}")
        
    # 2. Try resolving via local JSON cache
    cache_file = Path("d:/projects/coeautomator/backend/course_code_cache.json")
    if cache_file.exists():
        try:
            print("Resolving course codes from local JSON cache...")
            import json
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                
            # Direct/partial match lookup
            for code, title in cache.items():
                if query_text_clean in title.lower() or query_text_clean in code.lower():
                    resolved_codes.append(code.upper())
                    
            # If no matches found, try matching course keywords (scored/ranked matching)
            if not resolved_codes:
                stop_words = {"what", "are", "is", "the", "in", "of", "and", "for", "course", "questions", "important", "repeated", "show", "me", "give", "list", "to", "a", "an", "how", "why", "who", "where", "when", "which", "about", "any", "some", "random", "queries", "query", "papers", "paper", "syllabus", "curriculum"}
                words = re.findall(r'\b[a-zA-Z0-9]{3,}\b', query_text_clean)
                keywords = [w for w in words if w not in stop_words]
                if keywords:
                    print(f"No exact match in cache, searching by keywords: {keywords}")
                    scored_courses = []
                    for code, title in cache.items():
                        title_lower = title.lower()
                        # Count matches in title or code
                        matches = sum(1 for kw in keywords if kw in title_lower or kw in code.lower())
                        if matches > 0:
                            scored_courses.append((code, title, matches))
                    
                    if scored_courses:
                        # Sort by matches descending
                        scored_courses.sort(key=lambda x: x[2], reverse=True)
                        max_matches = scored_courses[0][2]
                        # We require at least 2 matching words (or 1 if query only has 1 word)
                        min_required = min(2, len(keywords))
                        if max_matches >= min_required:
                            # Add all courses that have the maximum number of matches
                            for code, title, matches in scored_courses:
                                if matches == max_matches:
                                    resolved_codes.append(code.upper())
            
            if resolved_codes:
                print(f"Resolved course codes from JSON cache: {resolved_codes}")
                return resolved_codes
        except Exception as e:
            print(f"JSON cache course resolution failed: {e}")
        
    # 3. Fallback: Parse curriculum PDFs in filesystem on-the-fly (in a separate thread)
    materials_dir = Path(COE_MATERIALS_DIR)
    syllabus_dir = materials_dir / "curriculum and syllabus"
    prefixes = set()
    
    if syllabus_dir.exists():
        print("Resolving course codes from curriculum PDFs (optimized first 10 pages)...")
        def scan_syllabus_files():
            found_codes = []
            for syllabus_file in syllabus_dir.rglob("*.pdf"):
                try:
                    reader = PdfReader(syllabus_file)
                    # Scan only first 10 pages (contains course listing table) to optimize performance
                    for page in reader.pages[:10]:
                        page_text = page.extract_text()
                        if not page_text:
                            continue
                        
                        # Search for occurrences of query_text_clean
                        for match in re.finditer(re.escape(query_text_clean), page_text.lower()):
                            start = max(0, match.start() - 150)
                            end = min(len(page_text), match.end() + 150)
                            snippet = page_text[start:end]
                            codes = COURSE_CODE_PATTERN.findall(snippet)
                            for c in codes:
                                code_upper = c.upper()
                                if code_upper not in found_codes:
                                    found_codes.append(code_upper)
                except Exception as e:
                    print(f"Error parsing syllabus {syllabus_file.name}: {e}")
            return found_codes

        try:
            extracted_codes = await asyncio.to_thread(scan_syllabus_files)
            for code in extracted_codes:
                if code not in resolved_codes:
                    resolved_codes.append(code)
                    prefix_match = re.match(r'^([A-Z]{3,4})', code)
                    if prefix_match:
                        prefixes.add(prefix_match.group(1))
        except Exception as e:
            print(f"Syllabus file scanning failed: {e}")
                
    # If no prefixes were resolved, add default department prefixes for CS/IT/ECE/EEE
    if not prefixes:
        prefixes = {"UCS", "UIT", "UEC", "UEE", "UBM"}
        
    print(f"Syllabus resolved codes: {resolved_codes}, Prefixes to scan in QPs: {prefixes}")
    
    # 3. Fallback 2: Scan the first page of relevant question papers to find matching old codes (Optimized)
    qp_dir = materials_dir / "question paper"
    if qp_dir.exists() and not resolved_codes:
        print("Scanning first page of matching question papers for content matches...")
        # Find which subdirectories match our prefixes (e.g. 'UCS', 'UIT')
        scan_dirs = []
        for p in prefixes:
            for item in qp_dir.iterdir():
                if item.is_dir():
                    item_name = item.name.upper()
                    if item_name.startswith(p) or item_name == p:
                        if item not in scan_dirs:
                            scan_dirs.append(item)
                            
        # If no matching folders found, scan the whole folder as fallback
        if not scan_dirs:
            scan_dirs = [qp_dir]
            
        print(f"Optimized fallback scanning in directories: {[d.name for d in scan_dirs]}")
        
        def scan_qp_files():
            found_codes = []
            qp_count = 0
            for s_dir in scan_dirs:
                for root, dirs, files in os.walk(str(s_dir)):
                    for file in files:
                        if file.lower().endswith(".pdf"):
                            filename = file.upper()
                            if any(p in filename for p in prefixes):
                                try:
                                    qp_count += 1
                                    file_path = os.path.join(root, file)
                                    reader = PdfReader(file_path)
                                    if len(reader.pages) > 0:
                                        first_page_text = reader.pages[0].extract_text()
                                        if first_page_text and query_text_clean in first_page_text.lower():
                                            # Extract course code from the text or filename
                                            codes = COURSE_CODE_PATTERN.findall(filename) + COURSE_CODE_PATTERN.findall(first_page_text)
                                            for c in codes:
                                                code_upper = c.upper()
                                                if code_upper not in found_codes:
                                                    print(f"Found match in QP {file}: resolved code {code_upper}")
                                                    found_codes.append(code_upper)
                                except Exception as e:
                                    print(f"Error reading QP {file}: {e}")
            print(f"Scanned {qp_count} question papers in background thread.")
            return found_codes

        try:
            extracted_qp_codes = await asyncio.to_thread(scan_qp_files)
            for code in extracted_qp_codes:
                if code not in resolved_codes:
                    resolved_codes.append(code)
        except Exception as e:
            print(f"QP scanning failed: {e}")
                
    print(f"Final resolved course codes: {resolved_codes}")
    return resolved_codes

async def search_files_in_folder(query_text: str, limit: int = 3, course_code: str = None, target_subfolder: str = None) -> str:
    """
    Scans the coe materials folder (or target subfolder like 'curriculum and syllabus') for PDFs matching the query keywords and resolved course codes,
    extracts their text, and returns them as a combined context.
    """
    t_start = time.time()
    if not query_text or query_text.strip() == "":
        return ""
        
    materials_dir = Path(COE_MATERIALS_DIR)
    if not materials_dir.exists():
        print(f"Materials dir does not exist: {materials_dir}")
        return ""
        
    # 1. Resolve course codes
    t_res_start = time.time()
    if course_code and course_code != "SYLLABUS":
        resolved_codes = [course_code.upper()]
    else:
        resolved_codes = await resolve_course_codes_for_query(query_text)
    print(f"[Time Log] Code resolution took {time.time() - t_res_start:.4f} seconds")
    
    # 2. Extract keywords (exclude common stop words)
    stop_words = {"what", "are", "is", "the", "in", "of", "and", "for", "course", "questions", "important", "repeated", "show", "me", "give", "list", "to", "a", "an", "how", "why", "who", "where", "when", "which", "about", "any", "some", "random", "queries", "query", "papers", "paper", "syllabus", "curriculum"}
    
    # Split query into words, clean them
    words = re.findall(r'\b[a-zA-Z0-9]{3,}\b', query_text.lower())
    keywords = [w for w in words if w not in stop_words]
    
    if not keywords:
        keywords = words
        if not keywords:
            return ""
        
    print(f"Direct folder search keywords: {keywords} (resolved codes: {resolved_codes})")
    
    matched_files = []
    
    # 3. Determine target subdirectories to scan (Optimized)
    t_walk_start = time.time()
    scan_dirs = []
    if target_subfolder:
        target_dir = materials_dir / target_subfolder
        if target_dir.exists():
            scan_dirs = [target_dir]
            
    if not scan_dirs:
        qp_dir = materials_dir / "question paper"
        if qp_dir.exists():
            if resolved_codes:
                for code in resolved_codes:
                    prefix = code[:3].upper()
                    for item in qp_dir.iterdir():
                        if item.is_dir():
                            item_name = item.name.upper()
                            if item_name.startswith(prefix) or item_name == prefix:
                                if item not in scan_dirs:
                                    scan_dirs.append(item)
            
            # If no specific directories resolved, check keywords to match folder names
            if not scan_dirs and keywords:
                for kw in keywords:
                    for item in qp_dir.iterdir():
                        if item.is_dir() and kw in item.name.lower():
                            if item not in scan_dirs:
                                scan_dirs.append(item)
                                
            # Fallback to whole directory if nothing matched
            if not scan_dirs:
                scan_dirs = [materials_dir]
                
    print(f"Optimized search walking inside: {[d.name for d in scan_dirs]}")
    
    # Recursively find matching PDFs only in selected directories
    for s_dir in scan_dirs:
        for root, dirs, files in os.walk(str(s_dir)):
            for file in files:
                if file.lower().endswith(".pdf"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, str(materials_dir))
                    filename_upper = file.upper()
                    
                    score = 0
                    # Check resolved course codes match (highest weight)
                    for code in resolved_codes:
                        if code in filename_upper:
                            score += 50
                    
                    # Check keyword match
                    for kw in keywords:
                        if kw in file.lower():
                            score += 5
                        elif kw in rel_path.lower():
                            score += 2
                            
                    if score > 0:
                        matched_files.append((file_path, score))
                        
    print(f"[Time Log] Directory walking and file matching took {time.time() - t_walk_start:.4f} seconds")
    
    if not matched_files:
        print("No matching PDFs found in folder.")
        return ""
        
    # Sort by score descending and take top files
    matched_files.sort(key=lambda x: x[1], reverse=True)
    top_matches = matched_files[:limit]
    
    t_extract_start = time.time()
    context = "### Context Extracted Directly from Filesystem PDFs\n"
    for file_path, score in top_matches:
        filename = os.path.basename(file_path)
        print(f"Reading matching PDF on-the-fly: {filename} (score: {score})")
        text = await asyncio.to_thread(extract_text_from_pdf, file_path, max_pages=2)
        if text:
            # Take a chunk of the text (first 2000 characters) to keep prompt small and fast
            context += f"\n--- File: {filename} ---\n{text[:2000]}\n"
            
    print(f"[Time Log] PDF text extraction of {len(top_matches)} files took {time.time() - t_extract_start:.4f} seconds")
    print(f"[Time Log] Total search_files_in_folder took {time.time() - t_start:.4f} seconds")
    return context

async def analyze_course_questions(course_code: str = None, portion_query: str = None) -> dict:
    """
    Retrieves course details, syllabus, and questions.
    Constructs the prompt, calls Gemini, and falls back to OpenAI if Gemini fails.
    """
    # 0. Check for General Chat Mode (No Course Code selected)
    if not course_code or course_code.strip() == "" or course_code == "GENERAL":
        # Search the folder on-the-fly for matching PDFs!
        folder_context = await search_files_in_folder(portion_query)
        
        prompt = f"### User Academic Query / Question:\n{portion_query}\n\n"
        if folder_context:
            prompt += f"### Reference Materials Context (Extracted from course PDFs):\n{folder_context}\n\n"
        
        prompt += (
            "### REQUIRED RESPONSE STRUCTURE:\n"
            "Please deliver a comprehensive, structured response formatted in clean Markdown:\n"
            "1. `## 📌 Overview / Definition` (Clear explanation with core context)\n"
            "2. `## 📋 Key Concepts & Breakdown` (Use bold bullet points like `- **Concept**: Explanation...`)\n"
            "3. `## 📊 Comparison / Summary Table` (Use a clean Markdown table with headers `| Key Aspect | Description / Detail |` where applicable)\n"
            "4. `## 💡 Exam Tips & Key Takeaways` (Use a blockquote `> 💡 **Tip:** ...`)\n\n"
            "Keep line breaks spacious and clean between paragraphs and sections. DO NOT clump text together."
        )
        
        provider = "Google Gemini"
        analysis_result = ""
        t_api_start = time.time()
        try:
            print("Calling Gemini API for general chat...")
            analysis_result = await asyncio.to_thread(call_gemini_api, prompt)
            print(f"[Time Log] Gemini API execution took {time.time() - t_api_start:.4f} seconds")
        except Exception as e:
            print(f"Gemini API failed: {e}. Falling back to OpenAI (gpt-4o-mini)...")
            try:
                t_openai_start = time.time()
                analysis_result = await asyncio.to_thread(call_openai_api, prompt)
                provider = "OpenAI (Fallback)"
                print(f"[Time Log] OpenAI API execution took {time.time() - t_openai_start:.4f} seconds")
            except Exception as oe:
                print(f"OpenAI API fallback also failed: {oe}")
                analysis_result = f"Error: Both AI services failed.\n\nGemini Error: {e}\n\nOpenAI Error: {oe}"
                provider = "None"
        return {
            "course_code": None,
            "course_name": "General Chat",
            "portion_analyzed": "N/A",
            "analysis": analysis_result,
            "provider": provider
        }

    # 0.5. Check for Syllabus Query Mode
    if course_code == "SYLLABUS":
        folder_context = await search_files_in_folder(portion_query, limit=5, target_subfolder="curriculum and syllabus")
        
        db_syllabus_context = ""
        try:
            db_res = await execute_query("""
                SELECT cp.course_code, c.course_name, cp.unit_number, cp.unit_title, cp.unit_content 
                FROM course_portions cp 
                JOIN courses c ON cp.course_code = c.course_code 
                WHERE cp.unit_title LIKE ? OR cp.unit_content LIKE ? OR c.course_name LIKE ? OR cp.course_code LIKE ?
                LIMIT 10
            """, [f"%{portion_query}%", f"%{portion_query}%", f"%{portion_query}%", f"%{portion_query}%"])
            if db_res and db_res.rows:
                db_syllabus_context = "### Database Syllabus Units Context\n"
                for row in db_res.rows:
                    db_syllabus_context += f"Course: {row[0]} - {row[1]} | Unit {row[2]}: {row[3]}\nContent: {row[4]}\n\n"
        except Exception as dbe:
            print(f"Error querying syllabus from DB: {dbe}")
            
        prompt = "You are an expert academic curriculum and syllabus advisor.\n\n"
        if db_syllabus_context:
            prompt += f"{db_syllabus_context}\n"
        if folder_context:
            prompt += f"{folder_context}\n\n"
            prompt += "The above text was extracted directly from the official curriculum and syllabus PDFs in the 'curriculum and syllabus' folder.\n\n"
            
        prompt += f"### User Syllabus Query:\n{portion_query}\n\n"
        prompt += (
            "### REQUIRED RESPONSE STRUCTURE:\n"
            "Format your response in clean, organized Markdown:\n"
            "1. `## 📚 Course & Curriculum Details` (Code, Title, Regulation)\n"
            "2. `## 📑 Unit Breakdown & Topics` (List each unit with `- **Topic**: Details`)\n"
            "3. `## 🎯 Course Objectives & Expected Outcomes`\n"
            "4. `## 📊 Structure / Hours / Scheme` (Markdown table if available)\n\n"
            "Keep line breaks spacious and clean between paragraphs and sections."
        )
        
        provider = "Google Gemini"
        analysis_result = ""
        t_api_start = time.time()
        try:
            print("Calling Gemini API for syllabus query...")
            analysis_result = await asyncio.to_thread(call_gemini_api, prompt)
            print(f"[Time Log] Gemini API execution took {time.time() - t_api_start:.4f} seconds")
        except Exception as e:
            print(f"Gemini API failed: {e}. Falling back to OpenAI (gpt-4o-mini)...")
            try:
                t_openai_start = time.time()
                analysis_result = await asyncio.to_thread(call_openai_api, prompt)
                provider = "OpenAI (Fallback)"
                print(f"[Time Log] OpenAI API execution took {time.time() - t_openai_start:.4f} seconds")
            except Exception as oe:
                print(f"OpenAI API fallback also failed: {oe}")
                analysis_result = f"Error: Both AI services failed.\n\nGemini Error: {e}\n\nOpenAI Error: {oe}"
                provider = "None"
                
        return {
            "course_code": "SYLLABUS",
            "course_name": "Curriculum & Syllabus Assistant",
            "portion_analyzed": portion_query,
            "analysis": analysis_result,
            "provider": provider
        }

    # 1. Fetch Course details & syllabus portions
    course_details = await get_course_details(course_code)
    
    # If course is not in DB, let's treat it as folder search
    if not course_details:
        print(f"Course {course_code} not found in DB. Performing direct folder search...")
        folder_context = await search_files_in_folder(course_code + " " + (portion_query or ""), course_code=course_code)
        
        prompt = f"### Course Context ({course_code})\n"
        if folder_context:
            prompt += f"{folder_context}\n\n"
            prompt += f"The above text was extracted directly from the PDFs in the 'coe materials' folder matching course code {course_code}.\n"
        
        prompt += f"### User Query:\n{portion_query if portion_query else 'Analyze repeated questions'}\n\n"
        prompt += (
            "### REQUIRED RESPONSE STRUCTURE:\n"
            "Format your response in clean, organized Markdown:\n"
            "1. `## 📌 Overview / Course Summary`\n"
            "2. `## 📊 Repeated / Important Questions Table` (`| Question | Marks | Frequency / Appears In | Unit / Topic |`)\n"
            "3. `## 📋 Detailed Questions Breakdown` (Grouped with bold bullets)\n"
            "4. `## 💡 Exam Preparation Strategy` (Blockquote tips)"
        )
        
        provider = "Google Gemini"
        analysis_result = ""
        try:
            analysis_result = await asyncio.to_thread(call_gemini_api, prompt)
        except Exception as e:
            try:
                analysis_result = await asyncio.to_thread(call_openai_api, prompt)
                provider = "OpenAI (Fallback)"
            except Exception as oe:
                analysis_result = f"Error: Both AI services failed.\n\nGemini Error: {e}\n\nOpenAI Error: {oe}"
                provider = "None"
        return {
            "course_code": course_code,
            "course_name": f"Dynamic Folder Search ({course_code})",
            "portion_analyzed": portion_query if portion_query else "Entire Course",
            "analysis": analysis_result,
            "provider": provider
        }
        
    course_name = course_details["course_name"]
    portions = course_details["portions"]
    
    # 2. Fetch all questions from previous QPs
    all_questions = await get_course_questions(course_code)
    
    # If the course is registered but has NO questions in DB, crawl on-the-fly!
    if not all_questions:
        print(f"No questions in DB for {course_code}. Running direct folder search...")
        folder_context = await search_files_in_folder(course_code + " " + (portion_query or ""), course_code=course_code)
        
        prompt = f"### Course Details\nCourse Code: {course_code}\nCourse Name: {course_name}\n\n"
        if folder_context:
            prompt += f"{folder_context}\n\n"
            prompt += f"The above text was extracted directly from the PDFs in the 'coe materials' folder.\n"
        
        prompt += f"### User Query:\n{portion_query if portion_query else 'Analyze repeated questions'}\n\n"
        prompt += (
            "### REQUIRED RESPONSE STRUCTURE:\n"
            "Format your response in clean Markdown with:\n"
            "1. `## 📌 Overview`\n"
            "2. `## 📊 Repeated Questions Summary Table` (`| Question | Marks | Frequency / Appears In | Unit / Topic |`)\n"
            "3. `## 📋 High-Priority Questions Breakdown` (Part A & Part B with bold bullets)\n"
            "4. `## 💡 Exam Tips & Core Focus Areas` (Blockquotes)"
        )
        
        provider = "Google Gemini"
        analysis_result = ""
        try:
            analysis_result = await asyncio.to_thread(call_gemini_api, prompt)
        except Exception as e:
            try:
                analysis_result = await asyncio.to_thread(call_openai_api, prompt)
                provider = "OpenAI (Fallback)"
            except Exception as oe:
                analysis_result = f"Error: Both AI services failed.\n\nGemini Error: {e}\n\nOpenAI Error: {oe}"
                provider = "None"
        return {
            "course_code": course_code,
            "course_name": course_name,
            "portion_analyzed": portion_query if portion_query else "Entire Course",
            "analysis": analysis_result,
            "provider": provider
        }
        
    # 3. Filter by syllabus portion if requested
    target_portion_text = ""
    target_unit_info = ""
    
    if portion_query:
        # User specified a unit or topic, e.g. "Unit 1" or "HTML"
        matched_portion = None
        
        # Check if they wrote something like "Unit 1", "Unit I", "Unit 2", etc.
        unit_match = re.search(r'(?:unit|module)\s*([0-9]+|[i|v|x]+)', portion_query, re.IGNORECASE)
        if unit_match:
            unit_val = unit_match.group(1).upper()
            roman_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
            unit_num = roman_map.get(unit_val)
            if unit_num:
                for p in portions:
                    if p["unit_number"] == unit_num:
                        matched_portion = p
                        break
        
        # If no numeric match, try text-based matching against unit titles
        if not matched_portion:
            for p in portions:
                if portion_query.lower() in p["unit_title"].lower() or portion_query.lower() in p["unit_content"].lower():
                    matched_portion = p
                    break
                    
        if matched_portion:
            target_unit_info = f"Unit {matched_portion['unit_number']}: {matched_portion['unit_title']}"
            target_portion_text = matched_portion["unit_content"]
            print(f"Filtering query for: {target_unit_info}")
        else:
            # General topic search query
            target_unit_info = f"Topic Portion: '{portion_query}'"
            target_portion_text = f"Filter questions relevant to the topic: {portion_query}"
            
    # 4. Format the questions for the LLM prompt
    questions_list_str = ""
    for idx, q in enumerate(all_questions, 1):
        questions_list_str += f"{idx}. [Part {q['part']}, Q{q['question_number']}] {q['question_text']} ({q['marks']} Marks) - Exam: {q['exam_period']} (Sem {q['semester']})\n"
        
    # 5. Build prompt
    prompt = f"### Course Details\n"
    prompt += f"Course Code: {course_code}\n"
    prompt += f"Course Name: {course_name}\n\n"
    
    if target_unit_info:
        prompt += f"### Target Portion / Unit Details\n"
        prompt += f"{target_unit_info}\n"
        prompt += f"Syllabus Content for this portion:\n{target_portion_text}\n\n"
        prompt += f"**INSTRUCTION**: Focus the analysis primarily on questions that match the above portion's syllabus. If a question is not related to this portion, filter it out.\n\n"
    else:
        prompt += f"### Full Course Syllabus\n"
        for p in portions:
            prompt += f"Unit {p['unit_number']}: {p['unit_title']}\nSyllabus: {p['unit_content']}\n\n"
            
    prompt += f"### Previous Year Questions List\n"
    prompt += questions_list_str + "\n"
    prompt += f"### User Request / Question\n"
    if portion_query:
        prompt += f"Question/Request: {portion_query}\n\n"
    else:
        prompt += f"Question/Request: Extract and analyze all the important, repeated questions across the entire course.\n\n"
        
    prompt += (
        "### MANDATORY RESPONSE STRUCTURE:\n"
        "1. If this is a question analysis / repeated questions request:\n"
        "   - `## 📊 Repeated Questions Summary Table` with columns: `| Question | Marks | Frequency / Appears In | Unit / Topic |`.\n"
        "   - `## 🔥 High-Priority / Most Repeated Questions (Part A & Part B)` with detailed breakdowns.\n"
        "   - `## 📌 Unit-Wise Key Topics to Focus On`.\n"
        "   - `## 💡 High-Scoring Exam Strategy & Tips` (in blockquotes).\n"
        "2. If this is an explanation / syllabus concept request:\n"
        "   - `## 📌 Overview / Definition`\n"
        "   - `## 📋 Core Concepts & Detailed Breakdown` (use bold bullet points `- **Topic**: Details`)\n"
        "   - `## 📊 Summary / Comparison Table` (if comparing concepts or architectures)\n"
        "   - `## 💡 Exam Tips & Takeaways`\n\n"
        "Maintain clean spacing and double line breaks between paragraphs and list items. NEVER output unstructured walls of text."
    )

    # 6. Execute with Fallback logic
    provider = "Google Gemini"
    analysis_result = ""
    
    try:
        print(f"Calling Gemini API to analyze questions for {course_code}...")
        analysis_result = call_gemini_api(prompt)
    except Exception as e:
        print(f"Gemini API failed: {e}. Falling back to OpenAI (gpt-4o-mini)...")
        try:
            analysis_result = call_openai_api(prompt)
            provider = "OpenAI (Fallback)"
        except Exception as oe:
            print(f"OpenAI API fallback also failed: {oe}")
            analysis_result = f"Error: Both AI services failed.\n\nGemini Error: {e}\n\nOpenAI Error: {oe}"
            provider = "None"
            
    return {
        "course_code": course_code,
        "course_name": course_name,
        "portion_analyzed": target_unit_info if target_unit_info else "Entire Course",
        "analysis": analysis_result,
        "provider": provider
    }
