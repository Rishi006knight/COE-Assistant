import os
import re
from pathlib import Path
from pypdf import PdfReader
import asyncio
from backend.config import COE_MATERIALS_DIR
from backend.database import (
    init_db,
    add_course,
    add_course_portion,
    add_question_paper,
    add_question,
    clear_qp_questions
)

# Regex patterns
COURSE_CODE_PATTERN = re.compile(r'\b(U[A-Z]{2,3}\d{4})\b')
UNIT_PATTERN = re.compile(r'\bUNIT\s+(I{1,3}|IV|V|VI)\b', re.IGNORECASE)

def extract_text_from_pdf(pdf_path: str, max_pages: int = None) -> str:
    """Extract raw text from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        pages_to_read = reader.pages
        if max_pages is not None:
            pages_to_read = reader.pages[:max_pages]
        for page in pages_to_read:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""

def parse_course_info_from_syllabus(pdf_path: str):
    """
    Parses a curriculum PDF page by page to find course codes, course names, and syllabus units.
    """
    reader = PdfReader(pdf_path)
    current_course_code = None
    current_course_name = None
    current_unit_num = None
    current_unit_title = None
    unit_buffer = []
    
    courses_found = {} # course_code -> {name, regulation, portions: {unit_num: {title, content}}}
    
    # Simple regulations match from filename (e.g. R2024)
    regulation = "R2024"
    reg_match = re.search(r'R\d{4}', os.path.basename(pdf_path))
    if reg_match:
        regulation = reg_match.group(0)

    print(f"Scanning curriculum PDF: {os.path.basename(pdf_path)}")
    
    # Process text page by page
    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue
            
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        for i, line in enumerate(lines):
            # 1. Search for Course Code
            # Typical line: "UCS2601 INTERNET PROGRAMMING" or "Course Code: UCS2601"
            code_match = COURSE_CODE_PATTERN.search(line)
            if code_match:
                code = code_match.group(1).upper()
                
                # Check if this looks like a course introduction line (usually has Course Code and Title)
                # Let's clean the line and check if there's more words (the title)
                line_without_code = line.replace(code, "").strip()
                # Remove symbols like ':', '-', etc.
                line_without_code = re.sub(r'^[:\-\s\.]+', '', line_without_code).strip()
                
                # If the line has words, it is likely the course name
                if len(line_without_code) > 3 and not any(x in line_without_code.upper() for x in ["PREREQUISITE", "L T P C", "SEMESTER", "SYLLABI"]):
                    # Save previous buffer before switching
                    if current_course_code and unit_buffer and current_unit_num:
                        courses_found[current_course_code]["portions"][current_unit_num] = {
                            "title": current_unit_title or f"Unit {current_unit_num}",
                            "content": "\n".join(unit_buffer).strip()
                        }
                        unit_buffer = []
                        current_unit_num = None
                    
                    current_course_code = code
                    current_course_name = line_without_code
                    if current_course_code not in courses_found:
                        courses_found[current_course_code] = {
                            "name": current_course_name,
                            "regulation": regulation,
                            "portions": {}
                        }
                    # Reset unit state
                    current_unit_num = None
                    continue
                
                # If name not found on the same line, check next line
                elif i + 1 < len(lines):
                    next_line = lines[i+1]
                    if len(next_line) > 3 and not any(x in next_line.upper() for x in ["PREREQUISITE", "L T P C", "SEMESTER", "SYLLABI", "COURSE CODE"]):
                        if current_course_code and unit_buffer and current_unit_num:
                            courses_found[current_course_code]["portions"][current_unit_num] = {
                                "title": current_unit_title or f"Unit {current_unit_num}",
                                "content": "\n".join(unit_buffer).strip()
                            }
                            unit_buffer = []
                            current_unit_num = None
                            
                        current_course_code = code
                        current_course_name = next_line
                        if current_course_code not in courses_found:
                            courses_found[current_course_code] = {
                                "name": current_course_name,
                                "regulation": regulation,
                                "portions": {}
                            }
                        current_unit_num = None
                        continue

            # 2. Search for Unit markers: UNIT I, UNIT II, etc.
            if current_course_code:
                unit_match = UNIT_PATTERN.search(line)
                if unit_match:
                    # Save previous unit buffer
                    if unit_buffer and current_unit_num:
                        courses_found[current_course_code]["portions"][current_unit_num] = {
                            "title": current_unit_title or f"Unit {current_unit_num}",
                            "content": "\n".join(unit_buffer).strip()
                        }
                        unit_buffer = []
                    
                    roman = unit_match.group(1).upper()
                    roman_to_num = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}
                    current_unit_num = roman_to_num.get(roman, 1)
                    
                    # Extract unit title if it's on the same line, e.g. "UNIT I - INTRODUCTION"
                    unit_title_part = line[unit_match.end():].strip()
                    unit_title_part = re.sub(r'^[:\-\s\.]+', '', unit_title_part).strip()
                    current_unit_title = unit_title_part if len(unit_title_part) > 2 else f"Unit {roman}"
                    continue
                
                # Append text to the current unit buffer
                if current_unit_num is not None:
                    # Don't add reference lines or text books lines to syllabus unit content if we can avoid
                    if any(x in line.upper() for x in ["TOTAL:", "REFERENCES:", "TEXT BOOKS:", "OUTCOMES:"]):
                        # Stop collecting for this unit
                        courses_found[current_course_code]["portions"][current_unit_num] = {
                            "title": current_unit_title or f"Unit {current_unit_num}",
                            "content": "\n".join(unit_buffer).strip()
                        }
                        unit_buffer = []
                        current_unit_num = None
                    else:
                        unit_buffer.append(line)
                        
        # Save last course's unit of page if any
        if current_course_code and unit_buffer and current_unit_num:
            courses_found[current_course_code]["portions"][current_unit_num] = {
                "title": current_unit_title or f"Unit {current_unit_num}",
                "content": "\n".join(unit_buffer).strip()
            }
            unit_buffer = []
            current_unit_num = None

    return courses_found

def parse_questions_from_qp(qp_text: str):
    """
    Parses a question paper's raw text to extract list of questions.
    Returns: list of dicts: {"part": str, "question_number": int, "question_text": str, "marks": int}
    """
    questions = []
    lines = [line.strip() for line in qp_text.split("\n") if line.strip()]
    
    current_part = "A"
    
    # Helper to parse marks from question line (e.g. "(2)" or "[13]" or "(15)")
    def extract_marks(line_text: str, default_marks: int) -> int:
        marks_match = re.search(r'[\(\[\{](\d+)[\)\]\}]\s*Marks?\s*$', line_text, re.IGNORECASE)
        if not marks_match:
            marks_match = re.search(r'[\(\[\{](\d+)[\)\]\}]\s*$', line_text)
        if marks_match:
            return int(marks_match.group(1))
        return default_marks

    i = 0
    while i < len(lines):
        line = lines[i]
        line_upper = line.upper()
        
        # Detect sections
        if "PART - A" in line_upper or "PART A" in line_upper:
            current_part = "A"
            i += 1
            continue
        elif "PART - B" in line_upper or "PART B" in line_upper:
            current_part = "B"
            i += 1
            continue
        elif "PART - C" in line_upper or "PART C" in line_upper:
            current_part = "C"
            i += 1
            continue
            
        # Parse Part A Questions (normally 1 to 10)
        # Matches: "1. What is HTTP?" or "10. State the use of DNS."
        part_a_match = re.match(r'^([1-9]|10)\.\s*(.*)', line)
        if current_part == "A" and part_a_match:
            q_num = int(part_a_match.group(1))
            q_text = part_a_match.group(2)
            marks = extract_marks(q_text, 2)
            
            # Read next lines until we hit another question number or PART section
            q_lines = [q_text]
            while i + 1 < len(lines):
                next_line = lines[i+1]
                # If next line starts a new question or part, stop
                if (re.match(r'^([1-9]|10|11)\.\s*', next_line) or 
                    any(x in next_line.upper() for x in ["PART A", "PART B", "PART C", "PART - A", "PART - B", "PART - C"])):
                    break
                q_lines.append(next_line)
                i += 1
            
            full_q_text = " ".join(q_lines)
            # Remove marks indicator from text
            full_q_text = re.sub(r'[\(\[\{]\d+[\)\]\}]\s*Marks?\s*$', '', full_q_text, flags=re.IGNORECASE).strip()
            full_q_text = re.sub(r'[\(\[\{]\d+[\)\]\}]\s*$', '', full_q_text).strip()
            
            questions.append({
                "part": "A",
                "question_number": q_num,
                "question_text": full_q_text,
                "marks": marks
            })
            i += 1
            continue

        # Parse Part B & C Questions (normally 11 to 16, often has subparts and OR choices)
        # Matches: "11. (a) Explain the layout..." or "11. a) Write notes on..."
        # Or simple "11. Describe..."
        part_bc_match = re.match(r'^(1[1-6])\.\s*(.*)', line)
        if current_part in ["B", "C"] and part_bc_match:
            q_num = int(part_bc_match.group(1))
            q_text = part_bc_match.group(2)
            default_m = 13 if current_part == "B" else 15
            marks = extract_marks(q_text, default_m)
            
            q_lines = [q_text]
            while i + 1 < len(lines):
                next_line = lines[i+1]
                # If next line starts a new main question or part, stop
                if (re.match(r'^(1[1-6])\.\s*', next_line) or 
                    any(x in next_line.upper() for x in ["PART A", "PART B", "PART C", "PART - A", "PART - B", "PART - C"])):
                    break
                q_lines.append(next_line)
                i += 1
                
            full_q_text = " ".join(q_lines)
            full_q_text = re.sub(r'[\(\[\{]\d+[\)\]\}]\s*Marks?\s*$', '', full_q_text, flags=re.IGNORECASE).strip()
            full_q_text = re.sub(r'[\(\[\{]\d+[\)\]\}]\s*$', '', full_q_text).strip()
            
            questions.append({
                "part": current_part,
                "question_number": q_num,
                "question_text": full_q_text,
                "marks": marks
            })
            i += 1
            continue
            
        i += 1

    return questions

async def scan_and_ingest():
    """Main scanning logic. Reads materials folder and populates DB."""
    # Ensure database tables exist
    await init_db()
    
    materials_path = Path(COE_MATERIALS_DIR)
    if not materials_path.exists():
        print(f"Materials directory does not exist: {materials_path}")
        return
        
    print(f"Scanning COE Materials in: {materials_path.resolve()}")
    
    # 1. Process Curriculum and Syllabus
    syllabus_dir = materials_path / "curriculum and syllabus"
    if syllabus_dir.exists():
        for syllabus_file in syllabus_dir.rglob("*.pdf"):
            try:
                courses_data = parse_course_info_from_syllabus(str(syllabus_file))
                for course_code, course_info in courses_data.items():
                    print(f"Ingesting Course: {course_code} - {course_info['name']}")
                    # Add course to DB
                    await add_course(
                        course_code=course_code,
                        course_name=course_info['name'],
                        department=os.path.basename(syllabus_file).replace("Curriculum and Syllabi - ", "").split(" - ")[0],
                        regulation=course_info['regulation']
                    )
                    # Add syllabus portions
                    for unit_num, portion in course_info['portions'].items():
                        await add_course_portion(
                            course_code=course_code,
                            unit_number=unit_num,
                            unit_title=portion['title'],
                            unit_content=portion['content']
                        )
            except Exception as e:
                print(f"Failed to process syllabus {syllabus_file}: {e}")

    # 2. Process Question Papers
    qp_dir = materials_path / "question paper"
    if qp_dir.exists():
        # Traverse subdirectories to find PDFs
        # Directory format e.g. "question paper/April-May 2024/B.E. B.Tech. 6 SEM/ESTE QP UCS2601-FINAL-APR MAY 2024.pdf"
        for qp_file in qp_dir.rglob("*.pdf"):
            try:
                filename = qp_file.name
                
                # Extract Course Code from filename (e.g. ESTE QP UCS2601-FINAL-APR MAY 2024.pdf)
                code_match = COURSE_CODE_PATTERN.search(filename)
                if not code_match:
                    print(f"Skipping {filename}: Could not find course code in filename.")
                    continue
                course_code = code_match.group(1).upper()
                
                # Retrieve relative path structures to determine Exam Period and Semester
                # e.g., parts: ['question paper', 'April-May 2024', 'B.E. B.Tech. 6 SEM', 'ESTE QP...pdf']
                rel_parts = qp_file.relative_to(qp_dir).parts
                exam_period = rel_parts[0] if len(rel_parts) > 1 else "Unknown"
                semester = rel_parts[1] if len(rel_parts) > 2 else "Unknown"
                
                print(f"Parsing QP: {filename} ({exam_period} | {semester})")
                
                # Extract full text
                raw_text = extract_text_from_pdf(str(qp_file))
                if not raw_text:
                    continue
                
                # Extract Course Name from raw text if it is not already in the DB
                # Usually QPs list the course name in the header, e.g. "Internet Programming"
                # Let's check if the course exists, if not try to add it with a guessed name from headers
                # (Often in QPs, the course title is right after or before the code, let's look for it)
                lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
                course_name = "Unknown Course Name"
                for i, line in enumerate(lines[:10]): # scan first few lines of header
                    if course_code in line.upper():
                        # Guess course name from line or surrounding lines
                        cleaned = line.replace(course_code, "").strip()
                        cleaned = re.sub(r'^[:\-\s\.]+', '', cleaned).strip()
                        if len(cleaned) > 5 and not any(x in cleaned.upper() for x in ["ESTE", "QP", "B.E", "B.TECH", "DEGREE"]):
                            course_name = cleaned
                            break
                        elif i + 1 < len(lines):
                            next_l = lines[i+1]
                            if len(next_l) > 5 and not any(x in next_l.upper() for x in ["DEGREE", "SEMESTER", "MAX. MARKS"]):
                                course_name = next_l
                                break
                
                # Ensure the course exists in courses table
                # We do this so even if it wasn't found in curriculum syllabus, the QP registers it!
                await add_course(course_code, course_name, regulation="Unknown")
                
                # Save paper details
                qp_id = await add_question_paper(
                    filepath=str(qp_file.resolve()).replace("\\", "/"),
                    course_code=course_code,
                    semester=semester,
                    exam_period=exam_period,
                    raw_text=raw_text
                )
                
                if qp_id:
                    # Clean previous parsed questions (to prevent duplicates if re-indexed)
                    await clear_qp_questions(qp_id)
                    
                    # Parse individual questions from raw text
                    parsed_qs = parse_questions_from_qp(raw_text)
                    print(f"  Extracted {len(parsed_qs)} structured questions from {filename}")
                    
                    for q in parsed_qs:
                        await add_question(
                            qp_id=qp_id,
                            part=q["part"],
                            question_number=q["question_number"],
                            question_text=q["question_text"],
                            marks=q["marks"]
                        )
            except Exception as e:
                print(f"Failed to process QP {qp_file}: {e}")
                
    print("Ingestion complete.")

if __name__ == "__main__":
    # To run independently
    asyncio.run(scan_and_ingest())
