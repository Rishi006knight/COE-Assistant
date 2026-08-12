import os
import json
import re
from pathlib import Path
from pypdf import PdfReader

# Matches course codes starting with I, U, or P followed by letters and digits, and captures the rest of the line as title
LINE_PATTERN = re.compile(r'\b([I|U|P][A-Z]{1,3}\d{3,4})[\s\-:]*(.*)', re.IGNORECASE)

def build_cache():
    base_dir = Path("d:/projects/coeautomator/coe materials/question paper")
    cache_file = Path("d:/projects/coeautomator/backend/course_code_cache.json")
    
    if not base_dir.exists():
        print(f"Error: Directory does not exist at {base_dir}")
        return
        
    print(f"Building course code metadata cache from {base_dir.resolve()}...")
    
    cache = {}
    processed_count = 0
    success_count = 0
    
    for root, dirs, files in os.walk(str(base_dir)):
        for file in files:
            if file.lower().endswith(".pdf"):
                file_path = os.path.join(root, file)
                processed_count += 1
                
                try:
                    reader = PdfReader(file_path)
                    if len(reader.pages) > 0:
                        first_page_text = reader.pages[0].extract_text()
                        if first_page_text:
                            # Search line-by-line for course code and title
                            for line in first_page_text.split('\n'):
                                line = line.strip()
                                match = LINE_PATTERN.match(line)
                                if match:
                                    code = match.group(1).upper()
                                    title = match.group(2).strip()
                                    
                                    # Clean up any leading page numbers, spaces, slashes, or redundant code prefixes
                                    title = re.sub(r'^[\d\s\-–—/|]*([A-Z]{3,4}\d{3,4})?[\d\s\-–—/|]*', '', title).strip()
                                    
                                    # Clean up trailing common to / regulation clauses
                                    title = re.sub(r'\s*\(\s*common\s+to\s+.*\b', '', title, flags=re.IGNORECASE)
                                    title = re.sub(r'\s*\(\s*regulations\s+.*\b', '', title, flags=re.IGNORECASE)
                                    
                                    # Clean leading "AND" or "AND N" conjunctions that got matched due to split lines
                                    title = re.sub(r'^(AND\s+N\b|AND\s+)\s*', '', title, flags=re.IGNORECASE).strip()
                                    
                                    # Helper to check if a title is valid (doesn't contain college name headers)
                                    title_lower = title.lower()
                                    junk_words = [
                                        "college of engineering", "sri sivasubramaniya", "nadar college", 
                                        "autonomous institution", "affiliated to", "examinations", "semester", 
                                        "regulations", "time:", "maximum:", "answer all", "register no", 
                                        "kalavakkam", "tamil nadu", "department of", "degree examination", 
                                        "branch", "regulations 20", "regulation 20"
                                    ]
                                    
                                    if any(jw in title_lower for jw in junk_words) or len(title) <= 2:
                                        continue
                                    
                                    # Save to cache if valid
                                    cache[code] = title
                                    success_count += 1
                                    break
                except Exception:
                    pass
                    
    # Save cache to JSON
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
        
    print(f"\nCache built successfully!")
    print(f"  - Scanned PDFs: {processed_count}")
    print(f"  - Unique course mappings cached: {len(cache)}")
    print(f"  - Output saved to: {cache_file.resolve()}")

if __name__ == "__main__":
    build_cache()
