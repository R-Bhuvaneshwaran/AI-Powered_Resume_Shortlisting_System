"""
TalentLens AI — Startup Script
================================
Run this file to start the application:

    python run.py

Then open your browser at: http://127.0.0.1:8000
"""

import os
import sys


def check_setup():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Ensure required folders exist
    for folder in ["templates", "data", "uploads"]:
        os.makedirs(os.path.join(BASE_DIR, folder), exist_ok=True)

    # Check required Python files
    required = [
        "main.py",
        "llm_extractor.py",
        "resume_extractor.py",
        "semantic_matcher.py",
        "Text_Extraction.py",
    ]
    missing = [f for f in required if not os.path.exists(os.path.join(BASE_DIR, f))]
    if missing:
        print(f"❌ Missing files: {missing}")
        sys.exit(1)


if __name__ == "__main__":
    check_setup()

    print("=" * 50)
    print("  🚀 TalentLens AI — Resume Screening System")
    print("=" * 50)
    print("  🌐 Open in browser: http://127.0.0.1:8000")
    print("  ⏹  Press CTRL+C to stop")
    print("=" * 50)

    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True   # auto-restarts when you edit any .py file
    )
