import pandas as pd
import google.generativeai as genai
import os,re,json
from datetime import datetime
from Text_Extraction import extract_text
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import time
from settings_env import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

# 🔥 Model priority list
MODEL_LIST = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-lite-latest",
    "gemini-pro-latest"
]


def clean_json(text):
    import re
    text = text.replace("```json", "").replace("```", "")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text.strip()


def extract_details(text):

    # ── Dynamic date — always accurate, no hardcoding ──────────────────
    from datetime import datetime
    _now        = datetime.now()
    _today_str  = _now.strftime("%B %Y")          # e.g. "April 2026"
    _today_yr   = _now.year
    _today_mo   = _now.month
    _yrs_2019   = round((_today_yr - 2019) + (_today_mo - 6) / 12, 2)
    _yr_diff    = _today_yr - 2019

    prompt = f"""
You are an expert resume parser. Today's date is {_today_str}.

Extract the following fields from the resume below.

=== EXPERIENCE CALCULATION — STRICT RULES ===

STEP 1 — Find ALL jobs in the Work Experience / Employment History section.
STEP 2 — For each job, calculate its duration from START DATE to END DATE.
  - If end date is "Present", "Till Present", "Current", "Ongoing" → use {_today_str}.
  - Date math examples (based on today = {_today_str}):
      * "2019 to Present"         → {_today_yr} - 2019 = {_yr_diff} years
      * "June 2019 to Present"    → {_today_str} - Jun 2019 ≈ {_yrs_2019} years
      * "Jan 2018 to Dec 2020"    → 3 years
      * "2 years 5 months"        → 2.42
      * "3+ years"                → 3
STEP 3 — ADD UP all individual job durations to get the TOTAL.
  - Example: Job1=3yr + Job2=2yr + Job3=1yr + Job4=2yr + Job5=2yr → output 10
STEP 4 — Output ONLY that final total number (int or float).

⚠ CRITICAL RULES:
- IGNORE any mention of experience in the Summary/Objective/Profile section completely.
  Those are self-descriptions and are often wrong or understated.
  Example: Summary says "2 years experience" but Work History shows 2019–Present → trust Work History.
- NEVER use the summary/profile number. ALWAYS use actual job date ranges.
- If no Work Experience section exists at all → output 0 (fresher).
- Output ONLY a plain number. Never output strings like "3+ years", "Fresher", "N/A".

=== OTHER FIELD RULES ===
- "skills" → flat JSON array of individual skill name strings. No nested objects.
- "location" → candidate's city/state from contact info or resume header. null if not found.
- "name", "email", "phone" → plain strings from contact info.
- Return ONLY a valid raw JSON object. No markdown, no code fences, no explanation.

Fields to extract: name, email, phone, location, skills, experience

Resume:
{text}
"""

    for model_name in MODEL_LIST:

        try:
            print(f"🔄 Trying model: {model_name}")

            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)

            cleaned = clean_json(response.text)
            return json.loads(cleaned)

        except Exception as e:

            error_msg = str(e).lower()

            # 🔥 Rate limit → try next model
            if "quota" in error_msg or "429" in error_msg:
                print(f"⚠️ {model_name} hit limit, switching...")
                continue

            # Other errors → break
            return {"error": str(e)}

    # 🔥 If all models fail → wait and retry once
    print("⏳ All models exhausted. Waiting 60 seconds...")
    time.sleep(60)

    return {"error": "All models failed after retry"}