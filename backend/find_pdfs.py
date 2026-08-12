import os
from pathlib import Path
from pypdf import PdfReader

def verify_all_files():
    materials_dir = Path("d:/projects/coeautomator/coe materials")
    if not materials_dir.exists():
        print("Materials directory does not exist.")
        return
        
    print(f"Scanning the text of all PDFs in {materials_dir.resolve()}...")
    
    matches = []
    scanned_count = 0
    
    for root, dirs, files in os.walk(str(materials_dir)):
        for file in files:
            if file.lower().endswith(".pdf"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, str(materials_dir))
                
                try:
                    scanned_count += 1
                    reader = PdfReader(full_path)
                    if len(reader.pages) > 0:
                        first_page = reader.pages[0].extract_text()
                        if first_page and "operating system" in first_page.lower():
                            matches.append((rel_path, file, first_page.split("\n")[:10]))
                except Exception as e:
                    # Ignore parsing errors for individual files
                    pass
                    
    print(f"\nScan complete. Scanned {scanned_count} PDFs.")
    print(f"Found {len(matches)} files containing 'Operating System' in their text:")
    for rel_path, filename, headers in matches:
        print(f"\n- File: {filename}")
        print(f"  Path: {rel_path}")
        print("  Top lines:")
        for line in headers[:6]:
            print(f"    {line}")

if __name__ == "__main__":
    verify_all_files()
