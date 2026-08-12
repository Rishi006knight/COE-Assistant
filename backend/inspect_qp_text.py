from pypdf import PdfReader
from pathlib import Path

def inspect_file():
    filepath = Path("d:/projects/coeautomator/coe materials/question paper/April-May 2024/B.E. B.Tech. 6 SEM/ESTE QP UCS2043-FINAL-APR MAY2024.pdf")
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return
        
    try:
        reader = PdfReader(filepath)
        text = reader.pages[0].extract_text()
        print("--- FIRST PAGE TEXT ---")
        print(text[:1500])
        print("-----------------------")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_file()
