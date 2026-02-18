"""
🤖 SYSTEM RECOMMENDATION ENGINE
Analyzes master resume and recommends jobs from all platforms
Fetches 5 jobs per category: Remote, Onsite, Hybrid, International
"""

import json
import os
import pandas as pd
from jobspy import scrape_jobs
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI
import time

# ========== CONFIGURATION ==========

def load_config():
    """Load AI configuration"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, 'ai_config.json')
    
    with open(config_file, 'r') as f:
        return json.load(f)

def load_resume():
    """Load the Master Resume"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    resume_path = os.path.join(os.path.dirname(script_dir), 'Assets', 'master resume.txt')
    
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"Resume not found at: {resume_path}")
    
    with open(resume_path, 'r', encoding='utf-8') as f:
        return f.read()

# Configuration will be loaded when needed
config = None
MASTER_RESUME = None
client = None

def initialize():
    """Initialize configuration, resume, and AI client"""
    global config, MASTER_RESUME, client
    
    if config is None:
        config = load_config()
        MASTER_RESUME = load_resume()
        
        # Initialize OpenAI client for OpenRouter
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config['openrouter_key']
        )
        
        print(f"[OK] Resume loaded ({len(MASTER_RESUME)} characters)")
        print(f"[OK] Model: {config['model']}")

# ========== AI ANALYSIS ==========

def analyze_resume_for_roles():
    """
    Analyze master resume to extract suitable job roles and skills
    """
    print("\n🤖 Analyzing master resume...")
    
    prompt = f"""Analyze this resume and extract:
1. Top 5 job roles this person should apply for
2. Key skills to search for
3. Preferred locations (if mentioned)

Resume:
{MASTER_RESUME}

Return ONLY a JSON object:
{{
    "roles": ["role1", "role2", ...],
    "skills": ["skill1", "skill2", ...],
    "locations": ["location1", "location2", ...]
}}
"""
    
    try:
        response = client.chat.completions.create(
            model=config['model'],
            messages=[
                {"role": "system", "content": "You are a career advisor analyzing resumes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Extract JSON
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()
        
        result = json.loads(ai_response)
        
        print(f"   ✓ Identified {len(result.get('roles', []))} suitable roles")
        print(f"   ✓ Extracted {len(result.get('skills', []))} key skills")
        
        return result
        
    except Exception as e:
        print(f"   ⚠️ Error analyzing resume: {e}")
        # Fallback to default
        return {
            "roles": ["Software Engineer", "Full Stack Developer", "Python Developer"],
            "skills": ["Python", "React", "Node.js", "Machine Learning"],
            "locations": ["India", "Remote", "USA"]
        }

def score_job_match(job_title, company, description):
    """
    Score a job against the master resume (0-100)
    """
    prompt = f"""Score this job against the candidate's resume (0-100).

Resume:
{MASTER_RESUME[:1500]}

Job:
- Title: {job_title}
- Company: {company}
- Description: {description[:500]}

Return ONLY a JSON:
{{"score": <number>, "reason": "<1 sentence why>"}}
"""
    
    try:
        response = client.chat.completions.create(
            model=config['model'],
            messages=[
                {"role": "system", "content": "You are a job matching AI. Be strict and selective."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=150
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Extract JSON
        if "```json" in ai_response:
            ai_response = ai_response.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_response:
            ai_response = ai_response.split("```")[1].split("```")[0].strip()
        
        result = json.loads(ai_response)
        score = int(result.get('score', 50))
        reason = result.get('reason', 'Match analysis completed')
        
        return score, reason
        
    except Exception as e:
        print(f"   ⚠️ Scoring error: {e}")
        return 50, "Unable to score"

# ========== JOB SCRAPING ==========

def scrape_jobs_by_category(roles, locations):
    """
    Scrape jobs from ALL platforms using enhanced scraper
    Returns: {category: [jobs]}
    """
    print("\n📊 Scraping jobs from ALL platforms...")
    
    all_jobs = {
        'Remote': [],
        'Onsite': [],
        'Hybrid': [],
        'International': []
    }
    
    # Import enhanced scraper functions
    from enhanced_scraper import (
        scrape_jobspy, scrape_weworkremotely, scrape_remotive,
        scrape_greenhouse, scrape_lever,
        GREENHOUSE_COMPANIES, LEVER_COMPANIES
    )
    
    # Get top role
    top_role = roles[0] if roles else "Software Engineer"
    top_location = locations[0] if locations else "Remote"
    
    print(f"\n🎯 Primary Search: {top_role} in {top_location}")
    
    # 1. JobSpy (LinkedIn, Indeed, Glassdoor) - Most recent first
    print("\n📱 Scraping JobSpy sources...")
    jobspy_jobs = scrape_jobspy(top_role, top_location, results_wanted=30)
    
    # 2. We Work Remotely
    print("\n🌍 Scraping We Work Remotely...")
    wwr_jobs = scrape_weworkremotely("programming")
    
    # 3. Remotive
    print("\n🔗 Scraping Remotive...")
    remotive_jobs = scrape_remotive("software-dev")
    
    # 4. Greenhouse Companies (Top 10)
    print("\n🏢 Scraping Greenhouse Companies...")
    greenhouse_jobs = []
    for company_name, company_slug in GREENHOUSE_COMPANIES[:10]:
        jobs = scrape_greenhouse(company_name, company_slug)
        greenhouse_jobs.extend(jobs)
        time.sleep(1)
    
    # 5. Lever Companies (Top 8)
    print("\n🎬 Scraping Lever Companies...")
    lever_jobs = []
    for company_name, company_slug in LEVER_COMPANIES[:8]:
        jobs = scrape_lever(company_name, company_slug)
        lever_jobs.extend(jobs)
        time.sleep(1)
    
    # Combine all jobs
    combined_jobs = jobspy_jobs + wwr_jobs + remotive_jobs + greenhouse_jobs + lever_jobs
    
    print(f"\n✅ Total jobs scraped: {len(combined_jobs)}")
    
    # Categorize jobs
    for job in combined_jobs:
        location_str = str(job.get('location', '')).lower()
        desc_str = str(job.get('description', ''))[:200].lower()
        
        # Determine category
        if 'remote' in location_str or 'remote' in desc_str or job.get('source') in ['WeWorkRemotely', 'Remotive']:
            if 'india' not in location_str:
                category = 'International'
            else:
                category = 'Remote'
        elif 'hybrid' in location_str or 'hybrid' in desc_str:
            category = 'Hybrid'
        else:
            category = 'Onsite'
        
        # Add work_mode to job
        job['work_mode'] = category
        all_jobs[category].append(job)
    
    # Print category breakdown
    print("\n📊 Category Breakdown:")
    for category, jobs in all_jobs.items():
        print(f"   - {category}: {len(jobs)} jobs")
    
    return all_jobs

# ========== RECOMMENDATION ENGINE ==========

def run_system_recommendation():
    """
    Main recommendation engine
    1. Analyze resume
    2. Scrape jobs
    3. Score jobs
    4. Select top 5 per category
    5. Save to Google Sheets
    """
    # Initialize configuration and AI client
    initialize()
    
    print("="*70)
    print("[SYSTEM] RECOMMENDATION ENGINE")
    print("="*70)
    
    # Step 1: Analyze resume
    analysis = analyze_resume_for_roles()
    roles = analysis.get('roles', [])
    locations = analysis.get('locations', ['Remote', 'India'])
    
    print(f"\n[INFO] Target Roles: {', '.join(roles[:3])}")
    print(f"[INFO] Target Locations: {', '.join(locations[:3])}")
    
    # Step 2: Scrape jobs
    categorized_jobs = scrape_jobs_by_category(roles, locations)
    
    # Step 3: Score and filter top 5 per category
    print("\n[AI] Scoring jobs with AI...")
    
    final_recommendations = []
    
    for category, jobs in categorized_jobs.items():
        print(f"\n[CATEGORY] {category} ({len(jobs)} jobs found)")
        
        if not jobs:
            continue
        
        # Score each job (limit to 10 to save time, then pick top 5)
        scored_jobs = []
        for job in jobs[:10]:  # Only score top 10 to save API calls
            score, reason = score_job_match(
                job['title'],
                job['company'],
                job['description']
            )
            
            job['Score'] = score
            job['Summary'] = reason
            scored_jobs.append(job)
            
            print(f"   • {job['title']} at {job['company']}: {score}/100")
            time.sleep(1)  # Rate limiting
        
        # Sort by score and take top 5
        scored_jobs.sort(key=lambda x: x['Score'], reverse=True)
        top_5 = scored_jobs[:5]
        
        final_recommendations.extend(top_5)
        
        print(f"   [OK] Selected top 5 jobs for {category}")
    
    # Step 4: Save to Google Sheets
    if final_recommendations:
        print(f"\n[SAVE] Saving {len(final_recommendations)} recommendations to Google Sheets...")
        save_to_sheets(final_recommendations)
    else:
        print("\n[WARN] No recommendations generated")
    
    print("\n" + "="*70)
    print("[SUCCESS] SYSTEM RECOMMENDATION COMPLETE!")
    print("="*70)

# ========== GOOGLE SHEETS ==========

def save_to_sheets(jobs):
    """
    Save recommended jobs to the 5 category sheets based on job characteristics
    Routes to: Direct_Portals, International_Remote, Indian_Remote, Indian_Onsite, Career_Portals
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_file = os.path.join(script_dir, 'google_key.json')
        
        if not os.path.exists(credentials_file):
            print("⚠️ google_key.json not found")
            return
        
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client_gs = gspread.authorize(creds)
        
        sheet = client_gs.open('Ai Job Tracker')
        
        # Get all 5 worksheets
        try:
            ws_direct_portals = sheet.worksheet('Direct_Portals')
            ws_international_remote = sheet.worksheet('International_Remote')
            ws_indian_remote = sheet.worksheet('Indian_Remote')
            ws_indian_onsite = sheet.worksheet('Indian_Onsite')
            ws_career_portals = sheet.worksheet('Career_Portals')
        except:
            print("❌ Error: Required worksheets not found")
            return
        
        # Get existing URLs from all sheets to avoid duplicates
        all_worksheets = [ws_direct_portals, ws_international_remote, ws_indian_remote, ws_indian_onsite, ws_career_portals]
        existing_urls = set()
        
        for worksheet in all_worksheets:
            try:
                existing_data = worksheet.get_all_records()
                for row in existing_data:
                    url = row.get('Link', '')
                    if url:
                        existing_urls.add(url)
            except:
                continue
        
        # Route jobs to appropriate sheets
        job_counts = {
            'Direct_Portals': 0,
            'International_Remote': 0,
            'Indian_Remote': 0,
            'Indian_Onsite': 0,
            'Career_Portals': 0
        }
        
        for job in jobs:
            # Skip if already exists
            if job['job_url'] in existing_urls:
                continue
            
            # Determine target sheet based on job characteristics
            location_str = job['location'].lower()
            work_mode = job['work_mode']
            source_str = job['source'].lower()
            
            # Check if from direct portals (ATS or Big Tech)
            # More strict check - source must be exactly one of these OR URL must contain them
            direct_portal_sources = ['Greenhouse', 'Lever', 'Google', 'Microsoft', 'Apple', 'Amazon', 'Meta', 'Netflix']
            direct_portal_urls = ['greenhouse.io', 'lever.co', 'google.com/careers', 'microsoft.com/careers']
            
            is_direct = (
                job['source'] in direct_portal_sources or
                any(url_pattern in job['job_url'].lower() for url_pattern in direct_portal_urls)
            )
            
            # Routing logic - Check location/work_mode FIRST, then direct portals
            if work_mode == 'International':
                # Jobs categorized as International go to International_Remote
                target_worksheet = ws_international_remote
                job_counts['International_Remote'] += 1
            elif 'india' in location_str and work_mode == 'Remote':
                target_worksheet = ws_indian_remote
                job_counts['Indian_Remote'] += 1
            elif 'india' in location_str and work_mode in ['Onsite', 'Hybrid']:
                target_worksheet = ws_indian_onsite
                job_counts['Indian_Onsite'] += 1
            elif work_mode == 'Remote':
                # Other remote jobs (not India, not already categorized as International)
                target_worksheet = ws_international_remote
                job_counts['International_Remote'] += 1
            elif work_mode in ['Onsite', 'Hybrid'] and 'india' not in location_str:
                # Non-India Onsite/Hybrid jobs go to Career Portals
                # (unless they're from direct portals, checked below)
                if is_direct:
                    target_worksheet = ws_direct_portals
                    job_counts['Direct_Portals'] += 1
                else:
                    target_worksheet = ws_career_portals
                    job_counts['Career_Portals'] += 1
            elif is_direct:
                # Direct portals (Greenhouse/Lever) that don't match above categories
                target_worksheet = ws_direct_portals
                job_counts['Direct_Portals'] += 1
            else:
                target_worksheet = ws_career_portals
                job_counts['Career_Portals'] += 1
            
            # Prepare row data
            row = [
                job['title'],
                job['company'],
                job['location'],
                job['work_mode'],
                job['job_url'],
                job['source'],
                job.get('salary_range', ''),
                job.get('posted_date', ''),
                job.get('Score', ''),
                job.get('Summary', '')
            ]
            
            # Append to appropriate sheet
            target_worksheet.append_row(row)
            existing_urls.add(job['job_url'])
        
        # Print summary
        total_added = sum(job_counts.values())
        print(f"\n[OK] Added {total_added} jobs to category sheets!")
        print(f"   - Direct_Portals: {job_counts['Direct_Portals']}")
        print(f"   - International_Remote: {job_counts['International_Remote']}")
        print(f"   - Indian_Remote: {job_counts['Indian_Remote']}")
        print(f"   - Indian_Onsite: {job_counts['Indian_Onsite']}")
        print(f"   - Career_Portals: {job_counts['Career_Portals']}")
        
    except Exception as e:
        print(f"[ERROR] Error saving to sheets: {e}")

# ========== MAIN ==========

if __name__ == "__main__":
    try:
        run_system_recommendation()
    except Exception as e:
        print(f"\n[ERROR] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
