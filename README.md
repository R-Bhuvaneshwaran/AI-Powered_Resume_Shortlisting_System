# AI-Powered_Resume_Shortlisting_System
A complete walkthrough of building a real-world recruiter tool using FastAPI, Google Gemini, and Semantic Search

<div align="center">

# 🚀 TalentLens AI
### AI-Powered Resume Shortlisting System

[![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Google_Gemini-API-orange?style=for-the-badge&logo=google)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)](LICENSE)

**Stop manually reading 300 resumes. Let AI do it.**

[📖 Read the Full Blog on Medium](https://medium.com/@Bhuvaneshwaran_16) • [🐛 Report a Bug](https://github.com/Bhuvaneshwaran-16/TalentLens-AI/issues) • [⭐ Star this Repo](https://github.com/Bhuvaneshwaran-16/TalentLens-AI)

</div>

---

## 📸 Preview

| Candidate Upload | Recruiter Dashboard | Top Candidates |
|:---:|:---:|:---:|
| Upload resume → AI extracts details | Filter by domain, skills, experience | Ranked candidates with score |

---

## 🧠 What Is This?

TalentLens AI is a full-stack web application that automates resume screening for recruiters. It:

1. Accepts resumes in **PDF, DOCX, PNG, JPG, TXT, ODT** formats
2. Uses **Google Gemini LLM** to extract name, email, skills, experience, and location
3. Stores candidates in **role-specific CSVs** (datascience, developer, cloud engineer, etc.)
4. Lets recruiters **filter + score** candidates using **Semantic AI** (not just keyword matching)
5. Sends **interview invitation emails** to shortlisted candidates in one click

---

## 🗂️ Project Structure

```
TalentLens-AI/
│
├── run.py                  ← Entry point. Run this to start the app.
├── main.py                 ← FastAPI backend — all routes and logic
├── llm_extractor.py        ← Google Gemini integration for resume parsing
├── resume_extractor.py     ← Text extraction router (used by main.py)
├── Text_Extraction.py      ← Text extraction logic (used by llm_extractor.py)
├── semantic_matcher.py     ← Semantic skill scoring with Sentence Transformers
|── settings_env.py         ← It contains Gemini API key and Google App Password
│
├── templates/
│   ├── home.html           ← Landing page
│   ├── recruiter.html      ← Recruiter dashboard
│   └── candidate.html      ← Candidate resume upload page
│
├── data/                   ← Auto-created. Stores per-role CSV files
├── uploads/                ← Auto-created. Stores uploaded resume files
└── requirements.txt        ← All Python dependencies
```

---

## ⚙️ How It Works

```
                    ┌─────────────────────────────────┐
                    │        Candidate uploads         │
                    │   resume (PDF/DOCX/Image/TXT)    │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │     Text_Extraction.py           │
                    │  pdfplumber → OCR fallback       │
                    │  python-docx / pytesseract       │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │       llm_extractor.py           │
                    │   Google Gemini API call         │
                    │  Returns: name, email, skills,   │
                    │           experience, location   │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │    Saved to role CSV file        │
                    │  (datascience.csv, dev.csv ...)  │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │    Recruiter applies filter      │
                    │  skills + experience + location  │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │     semantic_matcher.py          │
                    │  Sentence Transformers scoring   │
                    │  Score = skills% + exp% + loc%   │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │    Top candidates ranked         │
                    │    Email shortlisted candidates  │
                    └─────────────────────────────────┘
```

---

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.9 or higher
- Tesseract OCR installed on your system
- Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### Step 1 — Install Tesseract OCR

**Ubuntu / Linux:**
```bash
sudo apt install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download and install from [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

---

### Step 2 — Clone the Repository

```bash
https://github.com/R-Bhuvaneshwaran/AI-Powered_Resume_Shortlisting_System/
cd TalentLens-AI
```

### Step 3 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install fastapi uvicorn python-multipart jinja2 pandas
pip install pdfplumber python-docx pytesseract pillow pdf2image odfpy
pip install google-generativeai sentence-transformers scikit-learn
```

### Step 4 — Add Your Gemini API Key

Open `settings_env.py` and replace :
```python
GEMINI_API_KEY = "your-gemini-api-key-here"
```

Get your free API key at: [aistudio.google.com](https://aistudio.google.com)

### Step 5 — (Optional) Configure Email

Open `settings_env.py` email shortlisting feature:
```python
app_password = "your_gmail@gmail.com"
app_password = "your-16-char-app-password"
```

> To generate a Gmail App Password: Google Account → Security → 2-Step Verification → App Passwords

### Step 6 — Run the Application

```bash
python run.py
```

Open your browser at: **http://127.0.0.1:8000** 🎉

---

## 🎯 Features

- ✅ **Multi-format Resume Support** — PDF, DOCX, PNG, JPG, TXT, ODT
- ✅ **OCR Fallback** — Handles scanned/image-based PDFs automatically
- ✅ **LLM Extraction** — Gemini AI parses skills, experience, contact details
- ✅ **Model Fallback Chain** — If one Gemini model hits rate limit, auto-switches to next
- ✅ **Semantic Skill Matching** — AI understands meaning, not just keywords
- ✅ **Domain Roles** — Data Science, Developer, Cloud Engineer, Data Engineer, HR, QA
- ✅ **Duplicate Prevention** — Blocks same email from applying twice to same role
- ✅ **One-Click Email** — Send interview invitations to shortlisted candidates
- ✅ **Export Candidate List** — View full candidate table in new browser tab

---

## 🐛 Known Problems & How They're Solved

| Problem | Cause | Solution |
|---|---|---|
| PDF text is empty | Scanned/image-based PDF | OCR fallback via pytesseract + pdf2image |
| LLM returns broken JSON | Gemini wraps response in markdown | `clean_json()` strips fences + regex extracts JSON |
| API Rate Limit (429) | Free tier quota exceeded | Auto-rotates through 4 Gemini models |
| Wrong experience count | LLM trusted resume summary, not dates | Prompt explicitly instructs: calculate from job date ranges only |
| Filter returns empty | Threshold too strict / Python `0 == False` | Lowered threshold to 15; fixed `experience > 0` check |
| Duplicate candidates | No email uniqueness check | Pre-save check against existing CSV emails |

---

## 🧩 Tech Stack

| Component | Technology |
|---|---|
| Web Framework | FastAPI + Uvicorn |
| Frontend | Jinja2 HTML Templates |
| LLM | Google Gemini (gemini-2.5-flash) |
| Semantic Matching | Sentence Transformers (all-MiniLM-L6-v2) |
| PDF Parsing | pdfplumber + pdf2image |
| OCR | pytesseract |
| Data Storage | CSV via pandas |
| Email | Python smtplib (Gmail SMTP) |

---

## 📖 Full Article

For a complete beginner-friendly explanation of how this system works, every bug I hit, and how I fixed them:

**👉 [Read the full blog on Medium](https://medium.com/@Bhuvaneshwaran_16)**

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

This project is licensed under the MIT License.

---

<div align="center">

**Made with ❤️ by [Bhuvaneshwaran R](https://medium.com/@Bhuvaneshwaran_16)**

*On a mission to evolve from building data pipelines to building smart AI systems.*

</div>
