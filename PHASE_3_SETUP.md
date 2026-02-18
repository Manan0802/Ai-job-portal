
# 🚀 Phase 3: Asset Generation & Networking Setup

The "Resume Tailor" and "Networking Engine" are now live in your dashboard!

## 1. 📝 Resume Tailor
- **Location**: Go to the **"📝 Resume Tailor"** tab in the sidebar.
- **How to use**:
    1. Select a job from your database OR paste a Job Description.
    2. Click **"🚀 Analyze & Tailor Resume"**.
    3. Review the "Gap Analysis" and "Suggested Improvements".
    4. Uncheck any suggestions you don't like.
    5. Click **"💾 Generate Tailored PDF"** to get your new resume.
    6. Click **"✉️ Generate Cover Letter"** for a custom cover letter.

## 2. 🤝 Networking Engine
- **Location**: Go to the **"🤝 Networking Engine"** tab.
- **How to use**:
    1. Enter a **Target Company** (e.g., Google).
    2. Select a **Role** (e.g., Recruiter, Alumni).
    3. Click **"Find People"**.
    4. Click **"Generate Message"** next to a person to get a custom Connection Request or Cold Email.

---

## ⚠️ Important Setup for Networking
To use the "Find People" feature, you need a **SerpApi Key** (Free tier allows 100 searches/month).

1. **Get a Key**: Sign up at [SerpApi.com](https://serpapi.com/) (Free).
2. **Add to Config**:
    - Open `scrapper/ai_config.json`.
    - Add `"serp_api_key": "YOUR_KEY_HERE"` to the JSON.

```json
{
    "openrouter_key": "...",
    "model": "google/gemini-2.5-flash",
    "serp_api_key": "Paste_Your_SerpApi_Key_Here"
}
```

## 📄 Note on PDF Generation
The current PDF generator creates a clean, simple layout. 
- To edit your details (Name, Email, etc.), update `scrapper/resume_tailor.py` around line 130 inside the `resume_data` dictionary.
- Future phases can include deep resume parsing to auto-fill this.
