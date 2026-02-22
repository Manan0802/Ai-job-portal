"""
🔍 COMPREHENSIVE JOB SCRAPER - ALL SOURCES
ATS Portals + Big Tech + Remote Boards + JobSpy
"""

from jobspy import scrape_jobs
import pandas as pd
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time
import feedparser
import re

# ========== CONFIGURATION ==========

INDIAN_CITIES = [
    "Bangalore", "Hyderabad", "Gurgaon", "Noida", 
    "Mumbai", "Pune", "Chennai", "Kolkata", 
    "Ahmedabad", "Delhi"
]

COUNTRIES = [
    "India", "USA", "Canada", "Australia", 
    "Singapore", "Malaysia", "Europe"
]

# ========== BIG TECH COMPANIES ==========

BIG_TECH_COMPANIES = {
    "Google": {
        "careers_url": "https://careers.google.com/api/v3/search/",
        "name": "Google"
    },
    "Microsoft": {
        "careers_url": "https://careers.microsoft.com/professionals/us/en/search-results",
        "name": "Microsoft"
    },
    "Apple": {
        "careers_url": "https://jobs.apple.com/api/role/search",
        "name": "Apple"
    },
    "Amazon": {
        "careers_url": "https://amazon.jobs/en/search.json",
        "name": "Amazon"
    },
    "Meta": {
        "careers_url": "https://www.metacareers.com/jobs",
        "name": "Meta"
    },
    "Netflix": {
        "careers_url": "https://jobs.netflix.com/api/search",
        "name": "Netflix"
    },
    "Salesforce": {
        "careers_url": "https://salesforce.wd1.myworkdayjobs.com/External_Career_Site",
        "name": "Salesforce"
    },
    "Oracle": {
        "careers_url": "https://oracle.taleo.net/careersection/2/jobsearch.ftl",
        "name": "Oracle"
    },
    "Adobe": {
        "careers_url": "https://careers.adobe.com/us/en/search-results",
        "name": "Adobe"
    },
    "Nvidia": {
        "careers_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        "name": "Nvidia"
    },
    "Intel": {
        "careers_url": "https://jobs.intel.com/ListJobs/All",
        "name": "Intel"
    },
    "IBM": {
        "careers_url": "https://www.ibm.com/employment/",
        "name": "IBM"
    }
}

# ========== SCRAPER FUNCTIONS ==========

def scrape_jobspy_sources(query, location, is_remote, country, results_wanted=20):
    """Scrape LinkedIn, Indeed, Glassdoor via JobSpy"""
    try:
        print("📊 Scraping LinkedIn, Indeed, Glassdoor...")
        
        jobs_df = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor"],
            search_term=query,
            location=location,
            results_wanted=results_wanted,
            hours_old=72,
            country_indeed=country if country else "USA",
            is_remote=is_remote
        )
        
        if jobs_df is not None and not jobs_df.empty:
            jobs_df = standardize_columns(jobs_df, "JobSpy")
            print(f"   ✓ Found {len(jobs_df)} jobs from JobSpy sources")
            return jobs_df
        
    except Exception as e:
        print(f"   ⚠️ JobSpy error: {e}")
    
    return pd.DataFrame()

def scrape_weworkremotely(query):
    """Scrape We Work Remotely via RSS feed"""
    try:
        print("🌍 Scraping We Work Remotely...")
        
        feed_url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
        feed = feedparser.parse(feed_url)
        
        jobs = []
        for entry in feed.entries[:20]:
            # Parse title to extract company and role
            title_parts = entry.title.split(':')
            company = title_parts[0].strip() if len(title_parts) > 0 else "Unknown"
            role = title_parts[1].strip() if len(title_parts) > 1 else entry.title
            
            # Check if query matches
            if query.lower() in role.lower() or query.lower() in entry.description.lower():
                jobs.append({
                    'title': role,
                    'company': company,
                    'location': 'Remote',
                    'job_url': entry.link,
                    'posted_date': entry.published if hasattr(entry, 'published') else '',
                    'description': entry.description[:500] if hasattr(entry, 'description') else '',
                    'source': 'We Work Remotely',
                    'work_mode': 'Remote'
                })
        
        if jobs:
            print(f"   ✓ Found {len(jobs)} jobs from We Work Remotely")
            return pd.DataFrame(jobs)
        
    except Exception as e:
        print(f"   ⚠️ WWR error: {e}")
    
    return pd.DataFrame()

def scrape_remotive(query):
    """Scrape Remotive via their API"""
    try:
        print("🌐 Scraping Remotive...")
        
        url = "https://remotive.com/api/remote-jobs"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            jobs = []
            
            for job in data.get('jobs', [])[:30]:
                # Filter by query
                if query.lower() in job.get('title', '').lower() or query.lower() in job.get('category', '').lower():
                    jobs.append({
                        'title': job.get('title', 'N/A'),
                        'company': job.get('company_name', 'N/A'),
                        'location': 'Remote',
                        'job_url': job.get('url', ''),
                        'posted_date': job.get('publication_date', ''),
                        'description': job.get('description', '')[:500],
                        'source': 'Remotive',
                        'work_mode': 'Remote',
                        'salary_range': job.get('salary', '')
                    })
            
            if jobs:
                print(f"   ✓ Found {len(jobs)} jobs from Remotive")
                return pd.DataFrame(jobs)
        
    except Exception as e:
        print(f"   ⚠️ Remotive error: {e}")
    
    return pd.DataFrame()

def scrape_greenhouse_jobs(query, location=None):
    """Scrape Greenhouse ATS boards"""
    try:
        print("🏢 Scraping Greenhouse ATS boards...")
        
        # Common Greenhouse boards
        greenhouse_companies = [
            "airbnb", "stripe", "gitlab", "coinbase", "notion",
            "figma", "databricks", "airtable", "webflow", "plaid"
        ]
        
        jobs = []
        for company in greenhouse_companies[:5]:  # Limit to 5 companies for speed
            try:
                url = f"https://boards.greenhouse.io/{company}/jobs"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    job_listings = soup.find_all('div', class_='opening')
                    
                    for job in job_listings[:5]:  # Max 5 jobs per company
                        title_elem = job.find('a')
                        if title_elem:
                            title = title_elem.text.strip()
                            job_url = f"https://boards.greenhouse.io{title_elem.get('href', '')}"
                            
                            # Check if query matches
                            if query.lower() in title.lower():
                                location_elem = job.find('span', class_='location')
                                job_location = location_elem.text.strip() if location_elem else 'Not specified'
                                
                                jobs.append({
                                    'title': title,
                                    'company': company.title(),
                                    'location': job_location,
                                    'job_url': job_url,
                                    'posted_date': '',
                                    'source': 'Greenhouse ATS',
                                    'work_mode': 'Remote' if 'remote' in job_location.lower() else 'Onsite'
                                })
            except:
                continue
        
        if jobs:
            print(f"   ✓ Found {len(jobs)} jobs from Greenhouse")
            return pd.DataFrame(jobs)
        
    except Exception as e:
        print(f"   ⚠️ Greenhouse error: {e}")
    
    return pd.DataFrame()

def scrape_lever_jobs(query, location=None):
    """Scrape Lever ATS boards"""
    try:
        print("🏢 Scraping Lever ATS boards...")
        
        # Common Lever boards
        lever_companies = [
            "netflix", "shopify", "twitch", "reddit", "robinhood",
            "canva", "grammarly", "discord", "square", "lyft"
        ]
        
        jobs = []
        for company in lever_companies[:5]:  # Limit to 5 companies
            try:
                url = f"https://jobs.lever.co/{company}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    job_listings = soup.find_all('div', class_='posting')
                    
                    for job in job_listings[:5]:  # Max 5 jobs per company
                        title_elem = job.find('h5')
                        link_elem = job.find('a', class_='posting-title')
                        
                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            job_url = link_elem.get('href', '')
                            
                            # Check if query matches
                            if query.lower() in title.lower():
                                location_elem = job.find('span', class_='sort-by-location')
                                job_location = location_elem.text.strip() if location_elem else 'Not specified'
                                
                                jobs.append({
                                    'title': title,
                                    'company': company.title(),
                                    'location': job_location,
                                    'job_url': job_url,
                                    'posted_date': '',
                                    'source': 'Lever ATS',
                                    'work_mode': 'Remote' if 'remote' in job_location.lower() else 'Onsite'
                                })
            except:
                continue
        
        if jobs:
            print(f"   ✓ Found {len(jobs)} jobs from Lever")
            return pd.DataFrame(jobs)
        
    except Exception as e:
        print(f"   ⚠️ Lever error: {e}")
    
    return pd.DataFrame()

def scrape_big_tech_simple(query, location=None):
    """
    Simplified Big Tech scraper - Returns sample jobs
    Note: Full implementation requires company-specific APIs
    """
    try:
        print("🚀 Searching Big Tech companies...")
        
        # For now, we'll create a note that these need individual integration
        # This is a placeholder that shows the structure
        
        jobs = []
        
        # Sample structure - in production, each company needs its own scraper
        big_tech_list = ["Google", "Microsoft", "Apple", "Amazon", "Meta", "Netflix", 
                        "Salesforce", "Oracle", "Adobe", "Nvidia", "Intel", "IBM"]
        
        print(f"   ℹ️ Big Tech integration requires company-specific APIs")
        print(f"   📋 Companies to integrate: {', '.join(big_tech_list)}")
        print(f"   💡 Tip: Use JobSpy sources which include some Big Tech jobs")
        
        return pd.DataFrame()
        
    except Exception as e:
        print(f"   ⚠️ Big Tech error: {e}")
    
    return pd.DataFrame()

# ========== MAIN SCRAPING FUNCTION ==========

def scrape_jobs_by_query(query, country=None, location=None, work_mode=None, results_wanted=50):
    """
    Comprehensive job scraper - ALL sources
    """
    
    print("\n" + "="*70)
    print("🔍 COMPREHENSIVE JOB SEARCH - ALL SOURCES")
    print("="*70)
    print(f"Query: {query}")
    print(f"Location: {location or country or 'All'}")
    print(f"Work Mode: {work_mode or 'All'}")
    print("="*70 + "\n")
    
    all_jobs = []
    
    # Determine search parameters
    if location and country == "India":
        search_location = f"{location}, India"
    elif country:
        search_location = country
    else:
        search_location = "Remote"
    
    is_remote = False
    if work_mode and len(work_mode) == 1 and work_mode[0] == "Remote":
        is_remote = True
    
    # ========== PHASE 1: JobSpy (LinkedIn, Indeed, Glassdoor) ==========
    jobspy_results = scrape_jobspy_sources(query, search_location, is_remote, country, results_wanted // 3)
    if not jobspy_results.empty:
        all_jobs.append(jobspy_results)
    
    # ========== PHASE 2: Remote Boards ==========
    wwr_results = scrape_weworkremotely(query)
    if not wwr_results.empty:
        all_jobs.append(wwr_results)
    
    remotive_results = scrape_remotive(query)
    if not remotive_results.empty:
        all_jobs.append(remotive_results)
    
    # ========== PHASE 3: ATS Portals ==========
    greenhouse_results = scrape_greenhouse_jobs(query, location)
    if not greenhouse_results.empty:
        all_jobs.append(greenhouse_results)
    
    lever_results = scrape_lever_jobs(query, location)
    if not lever_results.empty:
        all_jobs.append(lever_results)
    
    # ========== PHASE 4: Big Tech (Placeholder) ==========
    big_tech_results = scrape_big_tech_simple(query, location)
    if not big_tech_results.empty:
        all_jobs.append(big_tech_results)
    
    # ========== COMBINE RESULTS ==========
    if all_jobs:
        final_df = pd.concat(all_jobs, ignore_index=True)
        
        # Filter by work mode if specified
        if work_mode and len(work_mode) < 3:
            final_df = filter_by_work_mode(final_df, work_mode)
        
        # Remove duplicates
        final_df = final_df.drop_duplicates(subset=['job_url'], keep='first')
        
        # Fill NaNs to prevent JSON errors
        final_df = final_df.fillna("")
        
        print("\n" + "="*70)
        print(f"✅ TOTAL JOBS FOUND: {len(final_df)}")
        print("="*70)
        print("\nBreakdown by source:")
        print(final_df['source'].value_counts().to_string())
        print("="*70 + "\n")
        
        return final_df
    else:
        print("\n⚠️ No jobs found\n")
        return pd.DataFrame()

# ========== HELPER FUNCTIONS ==========

def standardize_columns(df, source_name):
    """Standardize column names"""
    column_mapping = {
        'title': 'title',
        'company': 'company',
        'location': 'location',
        'job_url': 'job_url',
        'date_posted': 'posted_date',
        'description': 'description',
        'salary_source': 'salary_range',
        'job_type': 'work_mode'
    }
    
    existing_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
    df = df.rename(columns=existing_cols)
    
    if 'source' not in df.columns:
        df['source'] = source_name
    
    required_cols = ['title', 'company', 'location', 'job_url', 'posted_date', 'source']
    optional_cols = ['description', 'salary_range', 'work_mode']
    
    final_cols = [col for col in required_cols + optional_cols if col in df.columns]
    return df[final_cols]

def filter_by_work_mode(df, work_mode):
    """Filter by work mode"""
    mode_keywords = {
        'Remote': ['remote', 'work from home', 'wfh'],
        'Hybrid': ['hybrid'],
        'Onsite': ['onsite', 'on-site', 'office']
    }
    
    def matches_work_mode(row):
        location_str = str(row.get('location', '')).lower()
        desc_str = str(row.get('description', ''))[:200].lower()
        
        for mode in work_mode:
            keywords = mode_keywords.get(mode, [])
            for keyword in keywords:
                if keyword in location_str or keyword in desc_str:
                    return True
        return False
    
    return df[df.apply(matches_work_mode, axis=1)]

def get_ai_role_suggestions(resume_text=None, generic=True):
    """Get role suggestions"""
    return [
        "Software Engineer", "Full Stack Developer", "Frontend Developer",
        "Backend Developer", "AI/ML Engineer", "Data Scientist",
        "Python Developer", "JavaScript Developer", "React Developer",
        "Node.js Developer", "DevOps Engineer", "Cloud Engineer",
        "Mobile Developer", "QA Engineer", "Product Manager"
    ]
