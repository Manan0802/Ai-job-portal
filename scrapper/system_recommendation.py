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
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# ========== CONFIGURATION ==========

def load_config():
    """Load AI configuration"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, 'ai_config.json')
    
    with open(config_file, 'r') as f:
        return json.load(f)

def load_resume():
    """Load the Master Resume (PDF or TXT)"""
    try:
        from resume_reader import get_master_resume
    except ImportError:
        from scrapper.resume_reader import get_master_resume
    text = get_master_resume()
    if text.startswith("Resume not"):
        raise FileNotFoundError(text)
    return text

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
    
    prompt = f"""Analyze this resume and extract key career details.
    
    Resume:
    {MASTER_RESUME[:3000]}
    
    Extract the following:
    1. **Experience Level**: Determine if candidates is "Fresher", "Intern", "Junior" (1-3 yrs), or "Senior".
    2. **Top 5 Job Roles**: Specific roles they are best fit for (e.g., "Python Intern", "Junior Backend Engineer").
       - If they are a student/fresher, append "Intern" or "Fresher" to roles.
    3. **Key 5 Skills**: The most important technical skills from the resume.
    4. **Preferred Locations**: Extract locations if mentioned, else default to ["India", "Remote"].
    
    Return ONLY a JSON object:
    {{
        "experience_level": "Fresher/Intern/Junior/Senior",
        "roles": ["role1", "role2", ...],
        "skills": ["skill1", "skill2", ...],
        "locations": ["location1", "location2", ...]
    }}
"""
    
def load_resume():
    """Load resume content from Assets folder (TXT or PDF)"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(os.path.dirname(script_dir), 'Assets')
        
        # Priority 1: PDF
        pdf_path = os.path.join(assets_dir, 'master resume.pdf')
        if os.path.exists(pdf_path):
            try:
                import pypdf
                with open(pdf_path, 'rb') as f:
                    reader = pypdf.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                print(f"📄 Loaded Master Resume (PDF)")
                return text.strip()
            except ImportError:
                print("⚠️ pypdf not installed. Falling back to TXT.")
            except Exception as e:
                print(f"⚠️ Error reading PDF: {e}")

        # Priority 2: TXT
        txt_path = os.path.join(assets_dir, 'master resume.txt')
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                print(f"📄 Loaded Master Resume (TXT)")
                return f.read().strip()
                
        # Priority 3: Any PDF in Assets
        for file in os.listdir(assets_dir):
            if file.endswith('.pdf'):
                try:
                    import pypdf
                    full_path = os.path.join(assets_dir, file)
                    with open(full_path, 'rb') as f:
                        reader = pypdf.PdfReader(f)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                    print(f"📄 Loaded Resume: {file}")
                    return text.strip()
                except:
                    continue
        
        print("❌ No resume found in Assets/")
        return ""
    except Exception as e:
        print(f"❌ Error loading resume: {e}")
        return ""

def analyze_resume_for_roles():
    """
    Analyze the master resume to identify role matches
    """
    resume_text = load_resume()
    if not resume_text:
        return {
             "roles": ["Software Engineer", "Full Stack Developer"],
             "skills": ["Python", "JavaScript"],
             "experience_level": "Fresher"
        }
    
    prompt = f"""
    Analyze this candidate's resume extensively and logically. Your goal is to extract their true experience level, top skills, certifications, and ideal job roles.

    RESUME:
    {resume_text[:4000]}
    
    CRITICAL INSTRUCTION:
    - Base the 'experience_level' strictly on their work history.
    - Base the 'roles' explicitly on their proven skills and certifications (e.g., if they have AI certs, include "AI Engineer").
    
    Return ONLY a JSON object:
    {{
        "experience_level": "Fresher/Intern/Junior/Senior",
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
            max_tokens=600
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
        return {
            "roles": ["Software Engineer", "Full Stack Developer", "Python Developer"],
            "skills": ["Python", "React", "Node.js", "Machine Learning"],
            "locations": ["India", "Remote", "USA"],
            "experience_level": "Fresher"
        }

def score_job_match(job_title, company, description):
    """
    Score a job against the master resume (0-100)
    """
    prompt = f"""Score this job against the candidate's resume (0-100) strictly and logically.

Resume:
{MASTER_RESUME[:1500]}

Job:
- Title: {job_title}
- Company: {company}
- Description: {description[:500]}

RULES:
1. Pure Logic: Base the score purely on how well the job description matches their experience level, technical skills, and certifications.
2. If the candidate is a Fresher/Intern and the job asks for 5 years experience, penalize heavily (Score < 30).
3. If the candidate has explicit certifications/projects validating the job requirements, boost the score (85-100).

Return ONLY a JSON:
{{"score": <number>, "reason": "<1 logical sentence why>"}}
"""
    
    try:
        response = client.chat.completions.create(
            model=config['model'],
            messages=[
                {"role": "system", "content": "You are a job matching AI. Be strict and selective."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1000
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

def scrape_jobs_by_category(roles, locations, skills=[], experience_level="Fresher", target_category=None):
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
    
    # Construct optimized search query
    top_role = roles[0] if roles else "Software Engineer"
    top_location = locations[0] if locations else "Remote"
    
    # Remove overly specific appending which breaks JobSpy search
    search_query = top_role
            
    # Override location based on target_category to guarantee relevant jobs
    if target_category:
        if "Indian" in target_category:
            top_location = "India"
            if "Remote" in target_category:
                search_query += " Remote"
        elif "International_Remote" in target_category:
            top_location = "Remote"
            
    print(f"\n🎯 Primary Search: '{search_query}' in '{top_location}' (Level: {experience_level})")
    
    # 1. JobSpy (LinkedIn, Indeed, Glassdoor) - Most recent first
    print("\n📱 Scraping JobSpy sources...")
    # Increase results explicitly
    jobspy_jobs = scrape_jobspy(search_query, top_location, results_wanted=50)
    
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
        
        # Determine category using robust location matching
        indian_keywords = ['india', 'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 
                          'chennai', 'pune', 'kolkata', 'ahmedabad', 'gurgaon', 'noida',
                          'chandigarh', 'jaipur', 'kochi', 'indore', 'bhopal', 'lucknow']
        is_india_loc = any(k in location_str for k in indian_keywords)
        
        if 'remote' in location_str or 'remote' in desc_str or str(job.get('source')) in ['WeWorkRemotely', 'Remotive']:
            if not is_india_loc:
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
    for category, cat_jobs in all_jobs.items():
        print(f"   - {category}: {len(cat_jobs)} jobs")
    
    return combined_jobs

# ========== RECOMMENDATION ENGINE ==========

def run_system_recommendation(target_category=None, limit=10):
    """
    Main recommendation engine
    1. Analyze resume
    2. Scrape jobs (Targeted if category provided)
    3. Score jobs
    4. Select top jobs
    5. Save to Google Sheets
    """
    # Initialize configuration and AI client
    initialize()
    
    print("="*70)
    print(f"[SYSTEM] RECOMMENDATION ENGINE | Target: {target_category or 'ALL'} | Limit: {limit}")
    print("="*70)
    
    # Step 1: Analyze resume
    analysis = analyze_resume_for_roles()
    roles = analysis.get('roles', [])
    locations = analysis.get('locations', ['Remote', 'India'])
    skills = analysis.get('skills', [])
    experience_level = analysis.get('experience_level', 'Fresher')
    
    print(f"\n[INFO] Experience Level: {experience_level}")
    print(f"[INFO] Target Roles: {', '.join(roles[:3])}")
    
    # Category Mapping
    all_categories = {
        "Direct_Portals": ["Greenhouse", "Lever", "Workday"],
        "International_Remote": ["Worldwide Remote", "US Remote", "Europe Remote"],
        "Indian_Remote": ["India Remote", "Bangalore Remote"],
        "Indian_Onsite": ["Bangalore", "Hyderabad", "Gurgaon", "Mumbai", "Pune", "Noida", "Chennai"],
        "Career_Portals": ["Google", "Microsoft", "Amazon", "Meta"]
    }
    
    # Filter categories if target is provided
    selected_cats = {}
    if target_category:
        # Normalize key (handle spaces vs underscores)
        norm_target = target_category.replace(" ", "_")
        # Try exact match or partial match
        for key in all_categories:
            if norm_target.lower() == key.lower():
                selected_cats = {key: all_categories[key]}
                break
        if not selected_cats:
            print(f"⚠️ Category '{target_category}' not found. Defaulting to ALL.")
            selected_cats = all_categories
    else:
        selected_cats = all_categories

    print(f"\n🔍 Starting Scan for: {list(selected_cats.keys())}")
    
    final_recommendations = []

    print(f"\n📂 Starting Global Scrape based on Resume")
    # Step 2: Scrape jobs matching candidate roles
    all_combined_jobs = scrape_jobs_by_category(roles, locations, skills, experience_level, target_category)
    
    if not all_combined_jobs:
        print(f"   [WARN] No jobs found from scrape!")
    else:
        # Filter jobs matching the specific selected categories
        filtered_jobs = []
        for job in all_combined_jobs:
            location_str = str(job.get('location', '')).lower()
            work_mode = job.get('work_mode', 'Onsite')
            source_str = str(job.get('source', '')).lower()
            
            # Check if from direct portals
            direct_portal_sources = ['Greenhouse', 'Lever', 'Google', 'Microsoft', 'Apple', 'Amazon', 'Meta', 'Netflix']
            direct_portal_urls = ['greenhouse.io', 'lever.co', 'google.com/careers', 'microsoft.com/careers']
            
            is_direct = (
                job.get('source') in direct_portal_sources or
                any(url_pattern in job.get('job_url', '').lower() for url_pattern in direct_portal_urls)
            )
            
            # Check if location is in India using keywords
            indian_keywords = ['india', 'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 
                              'chennai', 'pune', 'kolkata', 'ahmedabad', 'gurgaon', 'noida',
                              'chandigarh', 'jaipur', 'kochi', 'indore', 'bhopal', 'lucknow']
            
            is_india = any(k in location_str for k in indian_keywords)
            
            # Match routing logic from save_to_sheets
            is_remote_board = job.get('source') in ['WeWorkRemotely', 'Remotive']
            
            category_key = ''
            if is_direct:
                category_key = 'Direct_Portals'
            elif is_remote_board:
                category_key = 'International_Remote'
            elif is_india:
                if 'remote' in location_str or work_mode == 'Remote':
                    category_key = 'Indian_Remote'
                else:
                    category_key = 'Indian_Onsite'
            elif work_mode == 'International' or ('remote' in location_str and not is_india):
                 category_key = 'International_Remote'
            else:
                category_key = 'Career_Portals'
            # Override category if we explicitly scanned for it and it matches geographically
            if target_category and target_category in selected_cats:
                # If they want Indian Onsite, an ATS job in India Onsite can also fit that sheet,
                # but to avoid duplicates across categories, we should just let ALL valid jobs be processed 
                # that were scraped in this run and route them to their correct destination.
                pass
                
            filtered_jobs.append(job)
        
        print(f"   [AI] Scoring {min(len(filtered_jobs), limit)} matching jobs...")
        
        # Step 3: Score
        scored_jobs = []
        for job in filtered_jobs[:limit]:
            score, reason = score_job_match(
                job.get('title', ''),
                job.get('company', ''),
                job.get('description', '')
            )
            
            job['Score'] = score
            job['Summary'] = reason
            scored_jobs.append(job)
            
            print(f"   • {job.get('title', '')}: {score}/100")
            time.sleep(0.5)
        
        scored_jobs.sort(key=lambda x: x['Score'], reverse=True)
        final_recommendations.extend(scored_jobs)
        print(f"   [OK] Processed {len(scored_jobs)} jobs")

    # Step 4: Save to Google Sheets
    if final_recommendations:
        print(f"\n[SAVE] Saving {len(final_recommendations)} recommendations to Google Sheets...")
        save_to_sheets(final_recommendations)
    else:
        print("\n[WARN] No recommendations generated")
    
    print("\n" + "="*70)
    print("[SUCCESS] SYSTEM RECOMMENDATION COMPLETE!")
    print("="*70)
    
    # Return for external use if needed, though mostly run via CLI
    return final_recommendations

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
                    url = str(row.get('Link', '')).strip()
                    if url and url != '#':
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
            # Skip if already exists and is a valid URL
            job_url = str(job.get('job_url', '')).strip()
            if job_url and job_url != '#' and job_url in existing_urls:
                continue
            
            # Determine target sheet based on job characteristics
            location_str = str(job.get('location', '')).lower()
            work_mode = job.get('work_mode', 'Onsite')
            source_str = str(job.get('source', '')).lower()
            
            # Check if from direct portals (ATS or Big Tech)
            direct_portal_sources = ['Greenhouse', 'Lever', 'Google', 'Microsoft', 'Apple', 'Amazon', 'Meta', 'Netflix']
            direct_portal_urls = ['greenhouse.io', 'lever.co', 'google.com/careers', 'microsoft.com/careers']
            
            is_direct = (
                job.get('source') in direct_portal_sources or
                any(url_pattern in job['job_url'].lower() for url_pattern in direct_portal_urls)
            )
            
            # Check if location is in India using keywords
            indian_keywords = ['india', 'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 
                              'chennai', 'pune', 'kolkata', 'ahmedabad', 'gurgaon', 'noida',
                              'chandigarh', 'jaipur', 'kochi', 'indore', 'bhopal', 'lucknow']
            
            is_india = any(k in location_str for k in indian_keywords)
            
            # Routing logic - Simplified for robustness
            target_worksheet = None
            category_key = ''
            is_remote_board = job.get('source') in ['WeWorkRemotely', 'Remotive']
            
            if is_direct:
                target_worksheet = ws_direct_portals
                category_key = 'Direct_Portals'
            elif is_remote_board:
                target_worksheet = ws_international_remote
                category_key = 'International_Remote'
            elif is_india:
                if 'remote' in location_str or work_mode == 'Remote':
                    target_worksheet = ws_indian_remote
                    category_key = 'Indian_Remote'
                else:
                    target_worksheet = ws_indian_onsite
                    category_key = 'Indian_Onsite'
            elif work_mode == 'International' or ('remote' in location_str and not is_india):
                 target_worksheet = ws_international_remote
                 category_key = 'International_Remote'
            else:
                target_worksheet = ws_career_portals
                category_key = 'Career_Portals'
            
            # Use specific overrides if category was explicitly passed in scraping?
            # For now, auto-detect is safer to ensure correct placement.
            
            if target_worksheet:
                 # Prepare row data
                row = [
                    job.get('title', ''),
                    job.get('company', ''),
                    job.get('location', ''),
                    job.get('work_mode', ''),
                    job.get('job_url', ''),
                    job.get('source', ''),
                    job.get('salary_range', ''),
                    job.get('posted_date', ''),
                    job.get('Score', ''),
                    job.get('Summary', '')
                ]
                
                target_worksheet.append_row(row)
                job_counts[category_key] += 1
                existing_urls.add(job['job_url'])
        
        # Print summary
        total_added = sum(job_counts.values())
        print(f"\n[OK] Added {total_added} jobs to category sheets!")
        for cat, count in job_counts.items():
            if count > 0:
                print(f"   - {cat}: {count}")
        
    except Exception as e:
        print(f"[ERROR] Error saving to sheets: {e}")

# ========== MAIN ==========

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--category', type=str, default=None, help='Specific category to scrape')
    parser.add_argument('--limit', type=int, default=10, help='Number of jobs')
    args = parser.parse_args()

    try:
        run_system_recommendation(target_category=args.category, limit=args.limit)
    except Exception as e:
        print(f"\n[ERROR] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
