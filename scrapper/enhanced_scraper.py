"""
🚀 ENHANCED JOB SCRAPER - ALL PLATFORMS
Fast, comprehensive scraping from all sources
Sorts by most recent first
"""

import requests
from bs4 import BeautifulSoup
import feedparser
import pandas as pd
from jobspy import scrape_jobs
from datetime import datetime, timedelta
import time
import json
import os

# ========== JOBSPY SCRAPER (LinkedIn, Indeed, Glassdoor) ==========

def scrape_jobspy(role, location="Remote", results_wanted=60):
    """
    Scrape from LinkedIn, Indeed, Glassdoor using JobSpy
    Sorted by most recent first
    """
    print(f"\n🔍 JobSpy: Searching for '{role}' in '{location}'...")
    
    all_jobs = []
    sources = ['linkedin', 'indeed', 'glassdoor']
    
    for source in sources:
        try:
            jobs_df = scrape_jobs(
                site_name=[source],
                search_term=role,
                location=location,
                results_wanted=results_wanted,
                hours_old=168,  # Last 7 days
                country_indeed='USA',
                is_remote=True if location.lower() == 'remote' else False
            )
            
            if jobs_df is not None and not jobs_df.empty:
                # Sort by date_posted (most recent first)
                if 'date_posted' in jobs_df.columns:
                    jobs_df['date_posted'] = pd.to_datetime(jobs_df['date_posted'], errors='coerce')
                    jobs_df = jobs_df.sort_values('date_posted', ascending=False)
                
                for _, job in jobs_df.iterrows():
                    all_jobs.append({
                        'title': str(job.get('title', 'N/A')),
                        'company': str(job.get('company', 'N/A')),
                        'location': str(job.get('location', 'N/A')),
                        'job_url': str(job.get('job_url', '')),
                        'description': str(job.get('description', ''))[:500],
                        'source': source.capitalize(),
                        'posted_date': str(job.get('date_posted', '')),
                        'salary_range': str(job.get('salary_source', ''))
                    })
                
                print(f"   ✓ {source.capitalize()}: {len(jobs_df)} jobs")
                time.sleep(2)  # Rate limiting
                
        except Exception as e:
            print(f"   ⚠️ {source.capitalize()} error: {e}")
            continue
    
    return all_jobs

# ========== WE WORK REMOTELY ==========

def scrape_weworkremotely(category="programming"):
    """
    Scrape We Work Remotely
    Categories: programming, design, marketing, etc.
    """
    print(f"\n🌍 We Work Remotely: Scraping {category} jobs...")
    
    jobs = []
    
    try:
        url = f"https://weworkremotely.com/categories/remote-{category}-jobs"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        job_listings = soup.find_all('li', class_='feature')
        
        for listing in job_listings[:50]:  # Top 50
            try:
                title_elem = listing.find('span', class_='title')
                company_elem = listing.find('span', class_='company')
                link_elem = listing.find('a')
                
                if title_elem and company_elem and link_elem:
                    jobs.append({
                        'title': title_elem.text.strip(),
                        'company': company_elem.text.strip(),
                        'location': 'Remote',
                        'job_url': f"https://weworkremotely.com{link_elem['href']}",
                        'description': '',
                        'source': 'WeWorkRemotely',
                        'posted_date': '',
                        'salary_range': ''
                    })
            except:
                continue
        
        print(f"   ✓ Found {len(jobs)} jobs")
        
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
    
    return jobs

# ========== REMOTIVE ==========

def scrape_remotive(category="software-dev"):
    """
    Scrape Remotive via RSS feed
    Categories: software-dev, customer-support, design, etc.
    """
    print(f"\n🔗 Remotive: Scraping {category} jobs...")
    
    jobs = []
    
    try:
        feed_url = f"https://remotive.com/remote-jobs/{category}/feed"
        feed = feedparser.parse(feed_url)
        
        for entry in feed.entries[:50]:  # Top 50
            try:
                # Extract company from title (usually format: "Job Title at Company")
                title_parts = entry.title.split(' at ')
                job_title = title_parts[0] if title_parts else entry.title
                company = title_parts[1] if len(title_parts) > 1 else 'Unknown'
                
                jobs.append({
                    'title': job_title,
                    'company': company,
                    'location': 'Remote',
                    'job_url': entry.link,
                    'description': entry.get('summary', '')[:500],
                    'source': 'Remotive',
                    'posted_date': entry.get('published', ''),
                    'salary_range': ''
                })
            except:
                continue
        
        print(f"   ✓ Found {len(jobs)} jobs")
        
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
    
    return jobs

# ========== GREENHOUSE ATS ==========

def scrape_greenhouse(company_name, company_slug):
    """
    Scrape Greenhouse ATS
    Example: scrape_greenhouse("Stripe", "stripe")
    """
    print(f"\n🏢 Greenhouse: Scraping {company_name}...")
    
    jobs = []
    
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            for job in data.get('jobs', [])[:50]:  # Top 50
                jobs.append({
                    'title': job.get('title', 'N/A'),
                    'company': company_name,
                    'location': job.get('location', {}).get('name', 'N/A'),
                    'job_url': job.get('absolute_url', ''),
                    'description': '',
                    'source': 'Greenhouse',
                    'posted_date': job.get('updated_at', ''),
                    'salary_range': ''
                })
            
            print(f"   ✓ Found {len(jobs)} jobs")
        
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
    
    return jobs

# ========== LEVER ATS ==========

def scrape_lever(company_name, company_slug):
    """
    Scrape Lever ATS
    Example: scrape_lever("Netflix", "netflix")
    """
    print(f"\n🎬 Lever: Scraping {company_name}...")
    
    jobs = []
    
    try:
        url = f"https://api.lever.co/v0/postings/{company_slug}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            for job in data[:50]:  # Top 50
                jobs.append({
                    'title': job.get('text', 'N/A'),
                    'company': company_name,
                    'location': job.get('categories', {}).get('location', 'N/A'),
                    'job_url': job.get('hostedUrl', ''),
                    'description': '',
                    'source': 'Lever',
                    'posted_date': job.get('createdAt', ''),
                    'salary_range': ''
                })
            
            print(f"   ✓ Found {len(jobs)} jobs")
        
    except Exception as e:
        print(f"   ⚠️ Error: {e}")
    
    return jobs

# ========== BIG TECH COMPANIES ==========

# Greenhouse Companies
GREENHOUSE_COMPANIES = [
    ("Airbnb", "airbnb"),
    ("Stripe", "stripe"),
    ("GitLab", "gitlab"),
    ("Coinbase", "coinbase"),
    ("Notion", "notion"),
    ("Figma", "figma"),
    ("DoorDash", "doordash"),
    ("Instacart", "instacart"),
    ("Canva", "canva"),
    ("Dropbox", "dropbox"),
    ("Asana", "asana"),
    ("Grammarly", "grammarly"),
]

# Lever Companies
LEVER_COMPANIES = [
    ("Netflix", "netflix"),
    ("Shopify", "shopify"),
    ("Twitch", "twitch"),
    ("Reddit", "reddit"),
    ("Robinhood", "robinhood"),
    ("Lyft", "lyft"),
    ("Udemy", "udemy"),
    ("Eventbrite", "eventbrite"),
]

# ========== MASTER SCRAPER ==========

def scrape_all_platforms(role="Software Engineer", location="Remote", max_jobs_per_source=50):
    """
    Scrape from ALL platforms
    Returns sorted list (most recent first)
    """
    print("="*70)
    print("🚀 ENHANCED JOB SCRAPER - ALL PLATFORMS")
    print("="*70)
    
    all_jobs = []
    
    # 1. JobSpy (LinkedIn, Indeed, Glassdoor)
    jobspy_jobs = scrape_jobspy(role, location, max_jobs_per_source)
    all_jobs.extend(jobspy_jobs)
    
    # 2. We Work Remotely
    wwr_jobs = scrape_weworkremotely("programming")
    all_jobs.extend(wwr_jobs)
    
    # 3. Remotive
    remotive_jobs = scrape_remotive("software-dev")
    all_jobs.extend(remotive_jobs)
    
    # 4. Greenhouse Companies
    print("\n🏢 Scraping Greenhouse Companies...")
    for company_name, company_slug in GREENHOUSE_COMPANIES[:5]:  # Top 5 to save time
        greenhouse_jobs = scrape_greenhouse(company_name, company_slug)
        all_jobs.extend(greenhouse_jobs)
        time.sleep(1)
    
    # 5. Lever Companies
    print("\n🎬 Scraping Lever Companies...")
    for company_name, company_slug in LEVER_COMPANIES[:5]:  # Top 5 to save time
        lever_jobs = scrape_lever(company_name, company_slug)
        all_jobs.extend(lever_jobs)
        time.sleep(1)
    
    # Convert to DataFrame
    df = pd.DataFrame(all_jobs)
    
    # Remove duplicates
    if not df.empty and 'job_url' in df.columns:
        df = df.drop_duplicates(subset=['job_url'], keep='first')
    
    # Sort by posted_date (most recent first)
    if not df.empty and 'posted_date' in df.columns:
        df['posted_date'] = pd.to_datetime(df['posted_date'], errors='coerce')
        df = df.sort_values('posted_date', ascending=False, na_position='last')
    
    print("\n" + "="*70)
    print(f"✅ TOTAL JOBS FOUND: {len(df)}")
    print("="*70)
    
    # Breakdown by source
    if not df.empty and 'source' in df.columns:
        print("\nBreakdown by source:")
        print(df['source'].value_counts())
    
    return df

# ========== MAIN ==========

if __name__ == "__main__":
    # Example usage
    jobs_df = scrape_all_platforms(
        role="Software Engineer",
        location="Remote",
        max_jobs_per_source=50
    )
    
    # Save to CSV
    if not jobs_df.empty:
        output_file = "all_jobs_scraped.csv"
        jobs_df.to_csv(output_file, index=False)
        print(f"\n💾 Saved to {output_file}")
    else:
        print("\n⚠️ No jobs found")
