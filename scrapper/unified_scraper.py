"""
🚀 UNIFIED JOB SCRAPER - ALL-IN-ONE
Combines all scraping functionality with different modes
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

# Import enhanced scraper functions
from enhanced_scraper import (
    scrape_jobspy, scrape_weworkremotely, scrape_remotive,
    scrape_greenhouse, scrape_lever,
    GREENHOUSE_COMPANIES, LEVER_COMPANIES
)

# ========== CONFIGURATION ==========

def load_config():
    """Load AI configuration"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, 'ai_config.json')
    
    with open(config_file, 'r') as f:
        return json.load(f)

def load_resume():
    """Load the Master Resume"""
    try:
        from resume_reader import get_master_resume
    except ImportError:
        from scrapper.resume_reader import get_master_resume
    text = get_master_resume()
    if text.startswith("Resume not"):
        raise FileNotFoundError(text)
    return text

# Global variables
config = None
MASTER_RESUME = None
client = None

def initialize():
    """Initialize configuration, resume, and AI client"""
    global config, MASTER_RESUME, client
    
    if config is None:
        config = load_config()
        MASTER_RESUME = load_resume()
        
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config['openrouter_key']
        )
        
        print(f"✓ Resume loaded ({len(MASTER_RESUME)} characters)")
        print(f"✓ Model: {config['model']}")

# ========== SCRAPING MODES ==========

class JobScraper:
    """Unified Job Scraper with multiple modes"""
    
    def __init__(self, mode='advanced'):
        """
        Initialize scraper
        
        Modes:
        - 'basic': JobSpy only, no AI, save to CSV
        - 'comprehensive': All platforms, no AI, save to CSV
        - 'advanced': All platforms + AI scoring + Google Sheets (DEFAULT)
        """
        self.mode = mode
        self.jobs = []
        
        if mode == 'advanced':
            initialize()
    
    def scrape(self, role=None, location=None, results_per_source=30):
        """
        Scrape jobs based on mode
        
        Args:
            role: Job role to search (optional in advanced mode)
            location: Location to search (optional in advanced mode)
            results_per_source: Number of results per source
        """
        print("="*70)
        print(f"🚀 UNIFIED JOB SCRAPER - {self.mode.upper()} MODE")
        print("="*70)
        
        if self.mode == 'basic':
            return self._scrape_basic(role, location, results_per_source)
        elif self.mode == 'comprehensive':
            return self._scrape_comprehensive(role, location, results_per_source)
        elif self.mode == 'advanced':
            return self._scrape_advanced(role, location, results_per_source)
    
    def _scrape_basic(self, role, location, results_per_source):
        """Basic mode: JobSpy only"""
        print(f"\n🔍 Basic Mode: Searching '{role}' in '{location}'")
        
        jobs = scrape_jobspy(role, location, results_per_source)
        
        df = pd.DataFrame(jobs)
        output_file = "jobs_basic.csv"
        df.to_csv(output_file, index=False)
        
        print(f"\n✅ Found {len(jobs)} jobs")
        print(f"💾 Saved to {output_file}")
        
        return df
    
    def _scrape_comprehensive(self, role, location, results_per_source):
        """Comprehensive mode: All platforms, no AI"""
        print(f"\n🌐 Comprehensive Mode: Searching '{role}' in '{location}'")
        
        all_jobs = []
        
        # 1. JobSpy
        print("\n📱 JobSpy...")
        all_jobs.extend(scrape_jobspy(role, location, results_per_source))
        
        # 2. We Work Remotely
        print("\n🌍 We Work Remotely...")
        all_jobs.extend(scrape_weworkremotely("programming"))
        
        # 3. Remotive
        print("\n🔗 Remotive...")
        all_jobs.extend(scrape_remotive("software-dev"))
        
        # 4. Greenhouse
        print("\n🏢 Greenhouse Companies...")
        for company_name, company_slug in GREENHOUSE_COMPANIES[:10]:
            all_jobs.extend(scrape_greenhouse(company_name, company_slug))
            time.sleep(1)
        
        # 5. Lever
        print("\n🎬 Lever Companies...")
        for company_name, company_slug in LEVER_COMPANIES[:8]:
            all_jobs.extend(scrape_lever(company_name, company_slug))
            time.sleep(1)
        
        df = pd.DataFrame(all_jobs)
        df = df.drop_duplicates(subset=['job_url'], keep='first')
        
        output_file = "jobs_comprehensive.csv"
        df.to_csv(output_file, index=False)
        
        print(f"\n✅ Found {len(df)} jobs (after deduplication)")
        print(f"💾 Saved to {output_file}")
        
        return df
    
    def _scrape_advanced(self, role=None, location=None, results_per_source=30):
        """Advanced mode: AI-powered with Google Sheets"""
        # This is the existing system_recommendation logic
        from system_recommendation import run_system_recommendation
        run_system_recommendation()

# ========== USAGE EXAMPLES ==========

if __name__ == "__main__":
    import sys
    
    # Check command line arguments for mode
    mode = sys.argv[1] if len(sys.argv) > 1 else 'advanced'
    
    scraper = JobScraper(mode=mode)
    
    if mode == 'basic':
        # Basic: Quick JobSpy search
        scraper.scrape(
            role="Software Engineer",
            location="Remote",
            results_per_source=20
        )
    
    elif mode == 'comprehensive':
        # Comprehensive: All platforms, no AI
        scraper.scrape(
            role="Full Stack Developer",
            location="Remote",
            results_per_source=30
        )
    
    elif mode == 'advanced':
        # Advanced: AI-powered recommendation (default)
        scraper.scrape()
    
    print("\n" + "="*70)
    print("✅ SCRAPING COMPLETE!")
    print("="*70)
