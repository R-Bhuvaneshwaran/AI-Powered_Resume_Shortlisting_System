from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import pandas as pd
import os
import ast
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pydantic import BaseModel
from typing import List
from datetime import datetime

from resume_extractor import extract_text
from llm_extractor import extract_details
from semantic_matcher import semantic_score

from settings_env import sender,app_password
app = FastAPI()

templates = Jinja2Templates(directory="templates")

# ──────────────────────────────────────
# EMAIL CONFIG  ← fill these in
# ──────────────────────────────────────
SMTP_SENDER_EMAIL = sender   # ← your Gmail address
SMTP_APP_PASSWORD = app_password      # ← your 16-char Gmail app password
SMTP_HOST         = "smtp.gmail.com"
SMTP_PORT         = 587
COMPANY_NAME      = "TalentLens AI"
COMPANY_ADDRESS   = "4th Floor, ABC Tower, Anna Nagar, Chennai – 600040"  # ← update this

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATA_FOLDER = os.path.join(BASE_DIR, "data")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

DOMAIN_WEIGHTS = {
    "datascience":    {"skills": 60, "experience": 25, "location": 15},
    "developer":      {"skills": 50, "experience": 30, "location": 20},
    "testing":        {"skills": 40, "experience": 40, "location": 20},
    "data_engineer":  {"skills": 60, "experience": 30, "location": 10},
    "cloud_engineer": {"skills": 70, "experience": 20, "location": 10},
    "hr":             {"skills": 30, "experience": 40, "location": 30},
}

# Map front-end role values → CSV file names
ROLE_ALIAS = {
    "qa": "testing",   # QA pill maps to testing CSV
}


def parse_experience(val) -> float:
    """
    Robustly convert any experience value to a float (years).
    Handles: 0, 2, 2.5, "3", "3+", "3+ years", "2 years 5 months",
             "Fresher", "fresher", None, NaN, lists, dicts, etc.
    """
    import re
    if val is None:
        return 0.0
    # Already a number
    if isinstance(val, (int, float)):
        return float(val) if not pd.isna(val) else 0.0
    s = str(val).strip().lower()
    if not s or s in ("nan", "none", "fresher", "freshers", "n/a", "-"):
        return 0.0
    # Extract all numbers from the string
    nums = re.findall(r"\d+\.?\d*", s)
    if not nums:
        return 0.0
    years = float(nums[0])
    # Add months if present: "2 years 5 months" → 2 + 5/12
    if "month" in s and len(nums) >= 2:
        years += float(nums[1]) / 12
    return round(years, 2)

def resolve_role(role: str) -> str:
    return ROLE_ALIAS.get(role.lower(), role.lower())


# ──────────────────────────────────────
# HOME
# ──────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


# ──────────────────────────────────────
# CANDIDATE PAGE
# ──────────────────────────────────────
@app.get("/candidate", response_class=HTMLResponse)
def candidate_page(request: Request):
    return templates.TemplateResponse(
        "candidate.html",
        {"request": request, "candidate": None}
    )


# ──────────────────────────────────────
# UPLOAD RESUME
# ──────────────────────────────────────
@app.post("/upload", response_class=HTMLResponse)
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    role: str = Form(...)
):
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print("📄 Extracting text...")
    text = extract_text(file_path)

    print("🤖 Calling LLM...")
    details = extract_details(text)

    print("✅ LLM Output:", details)

    if not details or not details.get("name"):
        print("❌ Invalid extraction")
        return templates.TemplateResponse(
            "candidate.html",
            {"request": request, "candidate": None,
             "message": "❌ Could not extract details. Please check your resume file."}
        )

    # Clean experience — convert ANY format to a numeric float
    details["experience"] = parse_experience(details.get("experience"))

    resolved_role = resolve_role(role)
    details["role"] = resolved_role

    # ── Duplicate check: block if same email already registered for this role ──
    csv_path = os.path.join(DATA_FOLDER, f"{resolved_role}.csv")
    candidate_email = str(details.get("email", "")).strip().lower()

    if candidate_email and os.path.exists(csv_path):
        existing_df = pd.read_csv(csv_path)
        if "email" in existing_df.columns:
            already_registered = existing_df["email"].astype(str).str.strip().str.lower()
            if candidate_email in already_registered.values:
                print(f"⚠️ Duplicate email blocked: {candidate_email} for role {resolved_role}")
                return templates.TemplateResponse(
                    "candidate.html",
                    {
                        "request": request,
                        "candidate": details,
                        "message": f"⚠️ Already registered! This email ({details.get('email')}) has already applied for the {resolved_role} role. Duplicate entries are not allowed.",
                        "duplicate": True
                    }
                )

    # Save to role-specific CSV
    new_row = pd.DataFrame([details])

    if os.path.exists(csv_path):
        old_df = pd.read_csv(csv_path)
        df = pd.concat([old_df, new_row], ignore_index=True)
    else:
        df = new_row

    df = df.dropna(subset=["name"])
    df = df[df["name"].astype(str) != "nan"]
    df.to_csv(csv_path, index=False)

    return templates.TemplateResponse(
        "candidate.html",
        {
            "request": request,
            "candidate": details,
            "message": "✅ Resume processed and saved successfully!"
        }
    )


# ──────────────────────────────────────
# RECRUITER PAGE  (GET — no filter)
# ──────────────────────────────────────
@app.get("/recruiter", response_class=HTMLResponse)
def recruiter_page(request: Request, role: str = "developer"):
    resolved_role = resolve_role(role)
    csv_path = os.path.join(DATA_FOLDER, f"{resolved_role}.csv")

    data, top_candidates = [], []

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)

        if "score" not in df.columns:
            df["score"] = 0

        # Normalise experience to a clean float, then store as rounded int-like float
        df["experience"] = df["experience"].apply(parse_experience)
        # Sort by experience DESC for default view (no filter applied)
        df = df.sort_values(by="experience", ascending=False)
        data = df.to_dict(orient="records")
        # On GET show top 5 by experience (no filter applied yet — show best exp first)
        # Only show if they have actual experience > 0, otherwise empty until filter used
        exp_df = df[df["experience"] > 0]
        top_candidates = exp_df.head(5).to_dict(orient="records")

    return templates.TemplateResponse(
        "recruiter.html",
        {
            "request": request,
            "data": data,
            "all_data": data,        # full CSV, no filter applied on GET
            "top_candidates": top_candidates,
            "selected_role": resolved_role,
            "filter_applied": False,   # page just loaded, no filter yet
        }
    )


# ──────────────────────────────────────
# FILTER  (POST)
# ──────────────────────────────────────
@app.post("/filter", response_class=HTMLResponse)
def filter_candidates(
    request: Request,
    role: str = Form(...),
    skills: str = Form(""),
    experience: float = Form(0),
    location: str = Form(""),
):
    resolved_role = resolve_role(role)
    csv_path = os.path.join(DATA_FOLDER, f"{resolved_role}.csv")

    if not os.path.exists(csv_path):
        return templates.TemplateResponse(
            "recruiter.html",
            {
                "request": request,
                "data": [],
                "all_data": [],
                "top_candidates": [],
                "selected_role": resolved_role,
                "filter_applied": True,
            }
        )

    # Load full CSV once — used for all_data regardless of filter
    full_df = pd.read_csv(csv_path)
    if "score" not in full_df.columns:
        full_df["score"] = 0
    # Normalise experience and sort by exp DESC for the "See All" view
    full_df["experience"] = full_df["experience"].apply(parse_experience)
    full_df = full_df.sort_values(by="experience", ascending=False)
    all_data = full_df.to_dict(orient="records")   # always the complete CSV

    df = pd.read_csv(csv_path)

    job_skills = [s.strip().lower() for s in skills.split(",")] if skills.strip() else []
    weights = DOMAIN_WEIGHTS.get(resolved_role, {"skills": 50, "experience": 30, "location": 20})

    # Normalise experience column ALWAYS (so sort & display are consistent)
    df["experience"] = df["experience"].apply(parse_experience)

    # ── Pre-filter ───────────────────────────────────
    if experience is not None and experience > 0:
        df = df[df["experience"] >= experience]

    if location:
        df = df[df["location"].astype(str).str.lower().str.contains(location.lower(), na=False)]

    # ── Score + skill relevance pre-check ────────────────────────────────
    # RAW_SEM_THRESHOLD: minimum raw semantic similarity (0-100) for a candidate
    # to even be considered when skills are specified.
    # Semantic cosine similarity for completely unrelated domains typically
    # returns 10-20. We require at least 30 raw similarity to pass.
    RAW_SEM_THRESHOLD = 15.0  # out of 100

    def calculate_score(row):
        score = 0
        raw_sem = 0.0

        try:
            candidate_skills = ast.literal_eval(str(row["skills"]))
            if not isinstance(candidate_skills, list):
                candidate_skills = [str(candidate_skills)]
        except Exception:
            candidate_skills = []

        if job_skills:
            raw_sem = semantic_score(candidate_skills, job_skills)
            if raw_sem < RAW_SEM_THRESHOLD:
                return 0.0
            score += (raw_sem * weights["skills"]) / 100

        exp_val = parse_experience(row.get("experience", 0))
        # ✅ Fix: use >= 0 check instead of truthiness check on `experience`
        if experience is not None and exp_val >= experience:
            score += weights["experience"]

        if location and location.lower() in str(row.get("location", "")).lower():
            score += weights["location"]

        # ✅ Fix: if no skills filter, always give a base score so row isn't excluded
        if not job_skills and score == 0:
            score = 1.0   # baseline so candidate isn't filtered out

        return round(score, 2)

    df["score"] = df.apply(calculate_score, axis=1)

    any_filter_applied = bool(job_skills) or bool(experience) or bool(location)

    if any_filter_applied:
        # Keep only candidates with score > 0 (skill threshold already enforced above)
        matched_df = df[df["score"] > 0]
        # Sort: score DESC, then experience DESC (tiebreak), then skills count DESC
        matched_df = matched_df.copy()
        matched_df["_skill_count"] = matched_df["skills"].apply(
            lambda s: len(ast.literal_eval(str(s))) if s and str(s) not in ("nan","[]") else 0
        )
        matched_df = matched_df.sort_values(
            by=["score", "experience", "_skill_count"],
            ascending=[False, False, False]
        ).drop(columns=["_skill_count"])
    else:
        # No filter → sort by experience DESC, then skill count DESC
        df_copy = df.copy()
        df_copy["_skill_count"] = df_copy["skills"].apply(
            lambda s: len(ast.literal_eval(str(s))) if s and str(s) not in ("nan","[]") else 0
        )
        matched_df = df_copy.sort_values(
            by=["experience", "_skill_count"],
            ascending=[False, False]
        ).drop(columns=["_skill_count"])

    data = matched_df.to_dict(orient="records")           # shown in new tab
    top_candidates = matched_df.head(5).to_dict(orient="records")  # top 5

    return templates.TemplateResponse(
        "recruiter.html",
        {
            "request": request,
            "data": data,
            "all_data": all_data,
            "top_candidates": top_candidates,
            "selected_role": resolved_role,
            "filter_applied": True,   # filter was run
        }
    )

# ──────────────────────────────────────
# EMAIL REQUEST MODEL
# ──────────────────────────────────────
class MailRequest(BaseModel):
    emails: List[str]
    names:  List[str]
    role:   str
    date:   str   # YYYY-MM-DD
    time:   str   # HH:MM
    venue:  str


def build_email_html(name: str, role: str, fmt_date: str, fmt_time: str, venue: str) -> str:
    """Build a beautiful HTML email body."""
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#f4f6f9; margin:0; padding:0; }}
  .wrapper {{ max-width:600px; margin:40px auto; background:#ffffff; border-radius:12px;
              overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.08); }}
  .header {{ background:linear-gradient(135deg,#0a1628,#0d2137); padding:36px 40px; text-align:center; }}
  .header h1 {{ color:#00d4ff; font-size:22px; margin:0 0 6px; letter-spacing:1px; }}
  .header p  {{ color:rgba(255,255,255,0.5); font-size:13px; margin:0; }}
  .body {{ padding:36px 40px; }}
  .congrats-badge {{
      display:inline-block;
      background:linear-gradient(135deg,#00c853,#00e676);
      color:#001a0a; font-weight:700; font-size:13px;
      padding:6px 18px; border-radius:50px;
      margin-bottom:20px; letter-spacing:0.5px;
  }}
  .body h2 {{ color:#1a1a2e; font-size:20px; margin:0 0 12px; }}
  .body p  {{ color:#555; font-size:15px; line-height:1.75; margin:0 0 16px; }}
  .detail-box {{
      background:#f0f9ff; border-left:4px solid #00d4ff;
      border-radius:0 8px 8px 0;
      padding:20px 24px; margin:24px 0;
  }}
  .detail-row {{ display:flex; align-items:flex-start; margin-bottom:12px; }}
  .detail-row:last-child {{ margin-bottom:0; }}
  .detail-icon {{ font-size:18px; margin-right:12px; min-width:24px; }}
  .detail-label {{ font-size:12px; color:#888; text-transform:uppercase; letter-spacing:1px; }}
  .detail-value {{ font-size:15px; color:#1a1a2e; font-weight:600; margin-top:2px; }}
  .note {{ background:#fff8e1; border:1px solid #ffe082; border-radius:8px;
           padding:14px 18px; font-size:13px; color:#5d4037; margin:20px 0; }}
  .footer {{ background:#f8f9fa; padding:24px 40px; text-align:center;
             border-top:1px solid #eee; }}
  .footer p {{ color:#aaa; font-size:12px; margin:0; line-height:1.6; }}
  .footer strong {{ color:#00d4ff; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>🚀 {COMPANY_NAME}</h1>
    <p>AI-Powered Recruitment System</p>
  </div>
  <div class="body">
    <div class="congrats-badge">🎉 Congratulations!</div>
    <h2>Dear {name},</h2>
    <p>
      We are thrilled to inform you that your resume has been
      <strong>shortlisted</strong> for the <strong>{role}</strong> role at
      <strong>{COMPANY_NAME}</strong>.
    </p>
    <p>Please find your interview details below:</p>

    <div class="detail-box">
      <div class="detail-row">
        <span class="detail-icon">📅</span>
        <div>
          <div class="detail-label">Date</div>
          <div class="detail-value">{fmt_date}</div>
        </div>
      </div>
      <div class="detail-row">
        <span class="detail-icon">🕐</span>
        <div>
          <div class="detail-label">Time</div>
          <div class="detail-value">{fmt_time}</div>
        </div>
      </div>
      <div class="detail-row">
        <span class="detail-icon">📍</span>
        <div>
          <div class="detail-label">Venue</div>
          <div class="detail-value">{venue}</div>
        </div>
      </div>
      <div class="detail-row">
        <span class="detail-icon">🏢</span>
        <div>
          <div class="detail-label">Company</div>
          <div class="detail-value">{COMPANY_NAME}</div>
        </div>
      </div>
    </div>

    <div class="note">
      📌 <strong>Please bring:</strong> A printed copy of your resume, a valid government-issued ID proof,
      and any certificates relevant to the <strong>{role}</strong> role.
    </div>

    <p>
      We look forward to meeting you. Should you have any questions, feel free to
      reply to this email.
    </p>
    <p style="color:#1a1a2e; font-weight:600;">Best regards,<br>HR Team — {COMPANY_NAME}</p>
  </div>
  <div class="footer">
    <p><strong>{COMPANY_NAME}</strong><br>{COMPANY_ADDRESS}</p>
  </div>
</div>
</body>
</html>"""


# ──────────────────────────────────────
# SEND MAIL ROUTE
# ──────────────────────────────────────
@app.post("/send-mail")
async def send_mail(req: MailRequest):
    try:
        # Format date & time nicely
        dt_obj = datetime.strptime(req.date, "%Y-%m-%d")
        fmt_date = dt_obj.strftime("%A, %d %B %Y")   # e.g. Monday, 05 May 2025

        t_obj = datetime.strptime(req.time, "%H:%M")
        fmt_time = t_obj.strftime("%I:%M %p")         # e.g. 10:30 AM

        venue = req.venue or COMPANY_ADDRESS

    except Exception as e:
        return JSONResponse({"success": False, "error": f"Invalid date/time format: {e}"})

    sent_count   = 0
    failed_count = 0
    errors       = []

    # Open SMTP connection once for all emails
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_SENDER_EMAIL, SMTP_APP_PASSWORD)
    except Exception as e:
        return JSONResponse({"success": False, "error": f"SMTP connection failed: {e}"})

    for email, name in zip(req.emails, req.names):
        if not email or "@" not in str(email):
            failed_count += 1
            continue
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🎉 Interview Shortlist – {req.role.title()} Role | {COMPANY_NAME}"
            msg["From"]    = f"{COMPANY_NAME} HR <{SMTP_SENDER_EMAIL}>"
            msg["To"]      = email

            # Plain text fallback
            plain = (
                f"Dear {name},\n\n"
                f"Congratulations! Your resume has been shortlisted for the {req.role} role "
                f"at {COMPANY_NAME}.\n\n"
                f"Interview Details:\n"
                f"Date  : {fmt_date}\n"
                f"Time  : {fmt_time}\n"
                f"Venue : {venue}\n\n"
                f"Please bring a copy of your resume and a valid ID proof.\n\n"
                f"Best regards,\nHR Team – {COMPANY_NAME}"
            )

            html_body = build_email_html(name, req.role.title(), fmt_date, fmt_time, venue)

            msg.attach(MIMEText(plain, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            server.sendmail(SMTP_SENDER_EMAIL, email, msg.as_string())
            sent_count += 1
            print(f"✅ Mail sent to {name} <{email}>")

        except Exception as e:
            failed_count += 1
            errors.append(f"{email}: {e}")
            print(f"❌ Failed for {email}: {e}")

    server.quit()

    return JSONResponse({
        "success": True,
        "sent":    sent_count,
        "failed":  failed_count,
        "errors":  errors
    })
