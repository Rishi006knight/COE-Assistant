import os
from pathlib import Path

def inspect_structure():
    base_dir = Path("d:/projects/coeautomator/coe materials/question paper")
    if not base_dir.exists():
        print("Directory does not exist.")
        return
        
    print(f"Inspecting: {base_dir.resolve()}\n")
    
    # List top level directories and files
    try:
        items = os.listdir(base_dir)
        print(f"Top-level items ({len(items)}):")
        for item in sorted(items)[:30]:
            item_path = base_dir / item
            if item_path.is_dir():
                # Count files inside recursively
                file_count = sum(len(files) for _, _, files in os.walk(item_path))
                print(f"  [DIR] {item} ({file_count} files inside)")
            else:
                print(f"  [FILE] {item}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_structure()
