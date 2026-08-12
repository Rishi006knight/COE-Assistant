import os
import shutil
import re
from pathlib import Path
from pypdf import PdfReader

# Pattern for standard course codes (e.g. UCS2043, UIT3562, ICS3211, PCS7012)
CODE_PATTERN = re.compile(r'\b([I|U|P][A-Z]{1,3}\d{3,4})', re.IGNORECASE)

# Pattern for Honors/Elective course codes containing H (e.g. UCS2H22, UCE2H24, UIT2H11)
HONORS_PATTERN = re.compile(r'\b([I|U|P][A-Z]{1,3}\d?H\d{1,3})', re.IGNORECASE)

# Department Code to Display Name Mapping
DEPT_NAMES = {
    # Undergraduate
    "UCS": "UCS - B.E. Computer Science and Engineering",
    "UIT": "UIT - B.Tech Information Technology",
    "UBM": "UBM - B.E. Biomedical Engineering",
    "UME": "UME - B.E. Mechanical Engineering",
    "UCE": "UCE - B.E. Civil Engineering",
    "UEC": "UEC - B.E. Electronics and Communication Engineering",
    "UEE": "UEE - B.E. Electrical and Electronics Engineering",
    "UCH": "UCH - B.Tech Chemical Engineering",
    "UPH": "UPH - Physics",
    "UCY": "UCY - Chemistry",
    "UMA": "UMA - Mathematics",
    "UGE": "UGE - General Engineering",
    "UHS": "UHS - Humanities and Social Sciences",
    "UEN": "UEN - English",
    "UGA": "UGA - General Academics",
    "UBA": "UBA - Common",
    "UPA": "UPA - Public Administration",
    
    # Integrated
    "ICS": "ICS - Integrated CSE",
    "IBA": "IBA - Integrated MBA",
    "IEN": "IEN - Integrated English",
    "IGA": "IGA - Integrated General Academics",
    "IHS": "IHS - Integrated Humanities",
    "IMA": "IMA - Integrated Mathematics",
    "IPH": "IPH - Integrated Physics",
    
    # Postgraduate
    "PBA": "PBA - Master of Business Administration",
    "PCP": "PCP - M.E. Computer Science and Engineering",
    "PCN": "PCN - M.E. Computer Networks",
    "PES": "PES - M.E. Embedded Systems Technologies",
    "PEY": "PEY - Postgraduate Electronics",
    "PGE": "PGE - Postgraduate General Engineering",
    "PIF": "PIF - M.E. Information Technology",
    "PMA": "PMA - Postgraduate Mathematics",
    "PMD": "PMD - M.E. Power Electronics and Drives",
    "PMF": "PMF - Postgraduate Manufacturing Engineering",
    "PPE": "PPE - Postgraduate Power Electronics",
    "PVL": "PVL - M.E. VLSI Design",
    "PAE": "PAE - M.E. Applied Electronics",
    
    # Other Fallback
    "UNK": "UNK - Unknown",
}

def extract_course_code(file_path):
    # Try from filename first
    filename = os.path.basename(file_path)
    
    match = HONORS_PATTERN.search(filename)
    if match:
        return match.group(1).upper()
        
    match = CODE_PATTERN.search(filename)
    if match:
        return match.group(1).upper()
        
    # Fallback to page 1 text content
    try:
        reader = PdfReader(file_path)
        if len(reader.pages) > 0:
            first_page_text = reader.pages[0].extract_text()
            if first_page_text:
                match = HONORS_PATTERN.search(first_page_text)
                if match:
                    return match.group(1).upper()
                match = CODE_PATTERN.search(first_page_text)
                if match:
                    return match.group(1).upper()
    except Exception:
        pass
        
    return None

def is_already_correct_folder(folder_name):
    # Only skip a folder if its name EXACTLY matches the correct display name or fallback name
    if " - " in folder_name:
        parts = folder_name.split(" - ")
        prefix = parts[0].upper()
        if len(prefix) in [3, 4] and prefix[0] in ['I', 'U', 'P']:
            correct_name = DEPT_NAMES.get(prefix, f"{prefix} - Department")
            if folder_name.upper() == correct_name.upper():
                return True
    return False

def regroup_pdfs():
    base_dir = Path("d:/projects/coeautomator/coe materials/question paper")
    if not base_dir.exists():
        print(f"Error: Base directory does not exist at '{base_dir.resolve()}'")
        return
        
    print(f"Self-Correcting Regroup of PDFs in '{base_dir.resolve()}' with Descriptive Names...\n")
    
    # 1. Collect all PDF files to process
    all_pdfs = []
    for root, dirs, files in os.walk(str(base_dir)):
        # Avoid walking inside already regrouped descriptive directories
        rel_path = os.path.relpath(root, str(base_dir))
        first_part = rel_path.split(os.sep)[0]
        if is_already_correct_folder(first_part):
            continue
            
        for file in files:
            if file.lower().endswith(".pdf"):
                all_pdfs.append(os.path.join(root, file))
                
    print(f"Found {len(all_pdfs)} total PDFs to check/sort.")
    
    stats = {}
    moved_count = 0
    duplicate_deleted_count = 0
    skipped_correct_count = 0
    
    # 2. Process each file
    for file_path in all_pdfs:
        filename = os.path.basename(file_path)
        current_dir_name = Path(file_path).parent.name.upper()
        
        code = extract_course_code(file_path)
        if not code:
            target_prefix = "UNK"
        else:
            # Universal Prefix Extractor: extract all letters before the first digit
            prefix_match = re.match(r'^([A-Z]+)', code)
            if prefix_match:
                target_prefix = prefix_match.group(1).upper()
            else:
                target_prefix = "UNK"
            
        # Get target folder display name
        target_folder_name = DEPT_NAMES.get(target_prefix, f"{target_prefix} - Department")
        
        # If it is already in the correct folder, skip it
        if current_dir_name == target_folder_name.upper():
            skipped_correct_count += 1
            continue
            
        # Target directory path
        target_dir = base_dir / target_folder_name
        target_dir.mkdir(exist_ok=True)
        
        # Target path
        dest_path = target_dir / filename
        
        # Handle filename collisions (duplicates)
        counter = 1
        is_duplicate = False
        while dest_path.exists():
            if dest_path.stat().st_size == os.path.getsize(file_path):
                # Same file size: delete the duplicate in the wrong folder
                try:
                    os.remove(file_path)
                    duplicate_deleted_count += 1
                    is_duplicate = True
                except Exception as e:
                    print(f"    [Error] Failed to delete duplicate {filename}: {e}")
                break
                
            name, ext = os.path.splitext(filename)
            dest_path = target_dir / f"{name}_{counter}{ext}"
            counter += 1
            
        if is_duplicate:
            continue
            
        try:
            shutil.move(file_path, str(dest_path))
            stats[target_folder_name] = stats.get(target_folder_name, 0) + 1
            moved_count += 1
            print(f"    [Moved] {current_dir_name}/{filename} -> {target_folder_name}/{os.path.basename(dest_path)}")
        except Exception as e:
            print(f"    [Error] Failed to move {filename} from {current_dir_name}: {e}")
            
    print(f"\nRegroup complete!")
    print(f"  - Moved/re-sorted: {moved_count} files")
    print(f"  - Cleaned up duplicates: {duplicate_deleted_count} files")
    print(f"  - Already correctly sorted: {skipped_correct_count} files")
    
    if stats:
        print("Updated Department counts:")
        for folder, count in sorted(stats.items()):
            print(f"    - {folder}: {count} files")
            
    # Clean up empty directories
    print("\nCleaning up empty source directories...")
    for root, dirs, files in os.walk(str(base_dir), topdown=False):
        if root == str(base_dir):
            continue
        rel_path = os.path.relpath(root, str(base_dir))
        # Remove any empty folders
        if not os.listdir(root):
            try:
                os.rmdir(root)
                print(f"    [Cleaned] Removed empty directory: '{rel_path}'")
            except Exception:
                pass

if __name__ == "__main__":
    regroup_pdfs()
