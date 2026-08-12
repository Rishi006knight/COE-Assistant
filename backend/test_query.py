import asyncio
import sys
import os

# Append the project root to the sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent import resolve_course_codes_for_query, search_files_in_folder

async def test_resolve():
    print("Testing course code resolution for 'Operating Systems'...")
    codes = await resolve_course_codes_for_query("Operating Systems")
    print(f"Resolved codes: {codes}")
    
    print("\nTesting folder search for 'Operating Systems'...")
    context = await search_files_in_folder("Operating Systems")
    print(f"Context length: {len(context)}")
    print(f"Context snippet:\n{context[:500]}")

if __name__ == "__main__":
    asyncio.run(test_resolve())

