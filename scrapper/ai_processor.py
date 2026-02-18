"""
🤖 SYSTEM RECOMMENDATION ENGINE - ELITE MNC MATCHER
Uses Gemini 2.5 Flash via OpenRouter to score jobs based on Master Resume
Prioritizes high-paying Top MNC roles matching tech stack
"""

import json
import os
import time
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ========== CONFIGURATION ==========

def load_config():
    """Load AI configuration from ai_config.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, 'ai_config.json')
    
    with open(config_file, 'r') as f:
        return json.load(f)

def load_resume():
    """Load the Master Resume from Assets folder"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level from scrapper to Ai-job, then into Assets
    resume_path = os.path.join(os.path.dirname(script_dir), 'Assets', 'master resume.txt')
    
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"Resume not found at: {resume_path}")
    
    with open(resume_path, 'r', encoding='utf-8') as f:
        return f.read()

# Load configuration and resume
config = load_config()
MASTER_RESUME = load_resume()

# Initialize OpenAI client for OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=config['openrouter_key']
)

print(f"✓ Resume loaded successfully ({len(MASTER_RESUME)} characters)")
print(f"✓ Model: {config['model']}")

# ========== GOOGLE SHEETS CONNECTION ==========

def connect_to_sheets():
    """Connect to Google Sheets"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_file = os.path.join(script_dir, 'google_key.json')
    
    if not os.path.exists(credentials_file):
        raise FileNotFoundError(f"google_key.json not found at {credentials_file}")
    
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
    client = gspread.authorize(creds)
    
    return client.open('Ai Job Tracker')

# ========== AI SCORING FUNCTIONS ==========

def get_ai_match_score(role, company, description):
    """
    Use Gemini to score a job match (0-100) with AI reasoning
    CRITICAL: Prioritizes Top MNCs and high-paying roles
    """
    
    # Elite recruiter prompt with MNC bias
    system_prompt = """You are an elite Tech Recruiter. Evaluate this job against the candidate's Master Resume. 

CRITICAL RULE: The candidate strictly targets high-paying jobs in top, well-known MNCs. 

Give a massive score boost (85-100) if:
- The company is a recognized Top MNC (Google, Microsoft, Amazon, Meta, Apple, Netflix, Adobe, Salesforce, Oracle, IBM, etc.)
- The role offers a high salary bracket or is at a prestigious tech company
- AND it matches their tech stack (MERN, Python, AI/ML, C++)

Heavily penalize or score low (<50) for:
- Generic, low-paying, or irrelevant startup roles
- Companies that are not well-known or established
- Roles that don't match the candidate's skills

Be strict and selective. Only top opportunities deserve high scores."""

    user_prompt = f"""CANDIDATE'S MASTER RESUME:
{MASTER_RESUME}

JOB DETAILS:
- Role: {role}
- Company: {company}
- Description/Snippet: {description[:800]}

TASK:
Analyze this job against the resume. Return ONLY a valid JSON object with exactly two keys:

1. Match_Score: An integer from 0-100
2. AI_Reasoning: A crisp 1-sentence explanation (e.g., "95 - Top MNC, matches your React/Node skills perfectly")

RESPOND WITH ONLY THE JSON OBJECT, NO OTHER TEXT:
{{"Match_Score": <number>, "AI_Reasoning": "<explanation>"}}"""
    
    try:
        # Call Gemini via OpenRouter
        response = client.chat.completions.create(
            model=config['model'],
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.2,  # Low temperature for consistent scoring
            max_tokens=200
        )
        
        # Parse the response
        ai_response = response.choices[0].message.content.strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        result = json.loads(ai_response)
        
        match_score = int(result.get('Match_Score', 50))
        ai_reasoning = result.get('AI_Reasoning', 'AI analysis completed')
        
        # Validate score range
        if match_score < 0 or match_score > 100:
            match_score = 50
        
        return match_score, ai_reasoning
        
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON parsing error: {e}")
        print(f"   Raw response: {ai_response[:200]}")
        return None, None
    except Exception as e:
        print(f"   ⚠️ Error getting AI score: {e}")
        return None, None

# ========== BATCH PROCESSING ==========

def ensure_columns_exist(worksheet, headers):
    """
    Ensure Match_Score and AI_Reasoning columns exist in the worksheet
    """
    needs_update = False
    
    if 'Match_Score' not in headers:
        print(f"   📝 Adding 'Match_Score' column...")
        headers.append('Match_Score')
        needs_update = True
    
    if 'AI_Reasoning' not in headers:
        print(f"   📝 Adding 'AI_Reasoning' column...")
        headers.append('AI_Reasoning')
        needs_update = True
    
    if needs_update:
        # Update the header row
        worksheet.update('1:1', [headers])
        print(f"   ✓ Columns added successfully")
        time.sleep(2)  # Wait for Google Sheets to update
    
    return headers

def process_worksheet(worksheet, sheet_name, batch_size=3):
    """
    Process jobs in a worksheet that don't have Match_Score yet
    """
    print(f"\n📋 Processing: {sheet_name}")
    
    try:
        # Get all data
        all_data = worksheet.get_all_records()
        
        if not all_data:
            print(f"   ℹ️ No jobs found in {sheet_name}")
            return 0
        
        # Get headers
        headers = worksheet.row_values(1)
        
        # Ensure Match_Score and AI_Reasoning columns exist
        headers = ensure_columns_exist(worksheet, headers)
        
        # Find column indices
        match_score_col = headers.index('Match_Score') + 1 if 'Match_Score' in headers else None
        ai_reasoning_col = headers.index('AI_Reasoning') + 1 if 'AI_Reasoning' in headers else None
        
        if match_score_col is None or ai_reasoning_col is None:
            print(f"   ❌ Could not find required columns in {sheet_name}")
            return 0
        
        # Reload data after column addition
        all_data = worksheet.get_all_records()
        
        # Process jobs without scores
        jobs_processed = 0
        jobs_to_process = []
        
        for idx, row in enumerate(all_data, start=2):  # Start at row 2 (after headers)
            # Skip if already has a Match_Score
            score_value = row.get('Match_Score', '')
            if score_value and str(score_value).strip():
                continue
            
            jobs_to_process.append((idx, row))
        
        total_to_process = len(jobs_to_process)
        
        if total_to_process == 0:
            print(f"   ✅ All jobs already scored in {sheet_name}")
            return 0
        
        print(f"   🎯 Found {total_to_process} jobs to score")
        
        # Process in batches
        for i in range(0, len(jobs_to_process), batch_size):
            batch = jobs_to_process[i:i+batch_size]
            
            for row_idx, job in batch:
                role = job.get('Role', 'Unknown Role')
                company = job.get('Company', 'Unknown Company')
                
                # Try to get description from various possible columns
                description = (
                    job.get('Description', '') or 
                    job.get('Snippet', '') or 
                    job.get('Summary', '') or
                    f"Role: {role} at {company}"
                )
                
                print(f"   🤖 Analyzing: {role} at {company}...")
                
                # Get AI match score and reasoning
                match_score, ai_reasoning = get_ai_match_score(role, company, description)
                
                if match_score is not None:
                    # Update the sheet
                    try:
                        # Update Match_Score column
                        worksheet.update_cell(row_idx, match_score_col, match_score)
                        # Update AI_Reasoning column
                        worksheet.update_cell(row_idx, ai_reasoning_col, ai_reasoning)
                        
                        print(f"      ✓ Score: {match_score}/100 - {ai_reasoning}")
                        jobs_processed += 1
                        
                    except Exception as update_error:
                        print(f"      ⚠️ Could not update sheet: {update_error}")
                else:
                    print(f"      ⚠️ Skipping due to AI error")
                
                # Delay to avoid rate limits (OpenRouter + Google Sheets)
                time.sleep(2)
            
            # Longer delay between batches
            if i + batch_size < len(jobs_to_process):
                print(f"   ⏳ Batch complete. Waiting 5 seconds before next batch...")
                time.sleep(5)
        
        return jobs_processed
        
    except Exception as e:
        print(f"   ❌ Error processing {sheet_name}: {e}")
        import traceback
        traceback.print_exc()
        return 0

# ========== MAIN EXECUTION ==========

def main():
    """Main execution function"""
    print("=" * 70)
    print("🤖 SYSTEM RECOMMENDATION ENGINE - ELITE MNC MATCHER")
    print("=" * 70)
    print(f"✓ Model: {config['model']}")
    print(f"✓ Resume loaded from: Assets/master resume.txt")
    print(f"✓ Processing 5 sheets with AI analysis")
    print(f"✓ Prioritizing: Top MNCs + High Salary + Tech Stack Match")
    print("=" * 70)
    
    try:
        # Connect to Google Sheets
        print("\n📊 Connecting to Google Sheets...")
        sheet = connect_to_sheets()
        
        # Define the 5 worksheets (exact order as specified)
        sheet_names = [
            'Indian_Onsite',
            'Indian_Remote',
            'International_Remote',
            'Career_Portals',
            'Direct_Portals'
        ]
        
        total_processed = 0
        
        # Process each worksheet
        for sheet_name in sheet_names:
            try:
                worksheet = sheet.worksheet(sheet_name)
                processed = process_worksheet(worksheet, sheet_name, batch_size=3)
                total_processed += processed
            except gspread.exceptions.WorksheetNotFound:
                print(f"\n⚠️ Worksheet '{sheet_name}' not found. Skipping...")
                continue
            except Exception as e:
                print(f"\n⚠️ Error with worksheet '{sheet_name}': {e}")
                continue
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ AI PROCESSING COMPLETE!")
        print(f"📊 Total jobs scored: {total_processed}")
        print("=" * 70)
        print("\n💡 TIP: Jobs with scores 85-100 are Top MNC matches!")
        print("💡 Refresh your Streamlit dashboard to see the updated scores.")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("Please ensure:")
        print("  1. google_key.json is in the scrapper folder")
        print("  2. ai_config.json is in the scrapper folder")
        print("  3. master resume.txt is in the Assets folder")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
