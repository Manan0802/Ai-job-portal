"""
🌍 GLOBAL JOB HUNTER - ADVANCED ROUTING SYSTEM 🌍
Multi-source job aggregator with intelligent 5-sheet routing
Sources: LinkedIn, Indeed, Glassdoor, Remote Boards (WWR, Remotive, Wellfound)
Routing: Direct_Portals, International_Remote, Indian_Remote, Indian_Onsite, Career_Portals
Features: Deduplication, NaN cleaning, 7-day freshness filter
"""

try:
    from jobspy import scrape_jobs
    import pandas as pd
    from datetime import datetime, timedelta
    import os
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    import re
    
    # ========== CONFIGURATION ==========
    TECH_STACK_KEYWORDS = ['python', 'c++', 'mern', 'react', 'node', 'ai', 'machine learning', 'intern', 'software', 'developer']
    
    # Direct ATS portals and Big Tech career sites
    DIRECT_PORTALS = ['greenhouse.io', 'lever.co', 'careers.google.com', 'careers.microsoft.com', 
                      'jobs.apple.com', 'amazon.jobs', 'careers.meta.com', 'jobs.netflix.com']
    
    # Remote-first job boards (sources that are inherently remote-focused)
    REMOTE_BOARDS = ['weworkremotely', 'remotive', 'wellfound', 'angellist']
    
    # ========== USER TOGGLES ==========
    REMOTE_ONLY_MODE = False  # Set to True to filter only Remote jobs, False for all modes
    RESULTS_PER_SOURCE = 5    # Number of jobs to scrape from each source (set to 5 for testing)
    DAYS_OLD = 7              # Only fetch jobs from last 7 days
    
    def safe_str(value):
        """
        Safely convert any value to string, handling NaN, None, and other edge cases
        This prevents JSON serialization errors when pushing to Google Sheets
        """
        if pd.isna(value) or value is None or value == 'nan' or str(value).lower() == 'nan':
            return ''
        return str(value).strip()
    
    def categorize_location(location):
        """
        Categorize job as 'International' or 'National' based on location
        National = India-based locations
        International = Everything else
        """
        location_str = safe_str(location).lower()
        
        # Indian location indicators
        indian_keywords = ['india', 'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 
                          'chennai', 'pune', 'kolkata', 'ahmedabad', 'gurgaon', 'noida',
                          'chandigarh', 'jaipur', 'kochi', 'indore', 'bhopal', 'lucknow']
        
        # Check if location mentions India or Indian cities
        if any(keyword in location_str for keyword in indian_keywords):
            return 'National'
        
        # Remote jobs without specific country are considered International
        if 'remote' in location_str and not any(keyword in location_str for keyword in indian_keywords):
            return 'International'
        
        # Default to International for non-India locations
        return 'International'
    
    def extract_salary_range(description, title=''):
        """
        Extract salary range from job description or title
        Returns formatted salary string or empty string
        """
        if not description and not title:
            return ''
        
        text = f"{safe_str(description)} {safe_str(title)}".lower()
        
        # Common salary patterns
        patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*-\s*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $50,000 - $70,000
            r'(\d{1,3}(?:,\d{3})*)\s*-\s*(\d{1,3}(?:,\d{3})*)\s*(?:usd|dollars?|per year|\/year|annually)',  # 50,000 - 70,000 USD
            r'(\d{1,3})k\s*-\s*(\d{1,3})k',  # 50k - 70k
            r'₹\s*(\d{1,3}(?:,\d{3})*)\s*-\s*₹\s*(\d{1,3}(?:,\d{3})*)',  # ₹50,000 - ₹70,000
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return f"${match.group(1)}-${match.group(2)}"
        
        return ''
    
    def extract_seniority_level(title, description=''):
        """
        Extract seniority level from job title or description
        """
        text = f"{safe_str(title)} {safe_str(description)}".lower()
        
        seniority_map = {
            'intern': ['intern', 'internship', 'co-op', 'coop'],
            'entry': ['entry', 'junior', 'graduate', 'associate', 'early career'],
            'mid': ['mid-level', 'intermediate', 'experienced'],
            'senior': ['senior', 'sr.', 'lead', 'principal', 'staff'],
            'executive': ['director', 'vp', 'vice president', 'head of', 'chief', 'cto', 'ceo']
        }
        
        for level, keywords in seniority_map.items():
            if any(keyword in text for keyword in keywords):
                return level.capitalize()
        
        return 'Not Specified'
    
    def check_tech_stack_match(title, description=''):
        """
        Check if job mentions any of the required tech stack keywords
        Returns True if match found, False otherwise
        """
        text = f"{safe_str(title)} {safe_str(description)}".lower()
        
        for keyword in TECH_STACK_KEYWORDS:
            if keyword.lower() in text:
                return True
        return False
    
    def is_remote_job(location, description=''):
        """
        Check if job is remote
        """
        location_str = safe_str(location).lower()
        desc_str = safe_str(description).lower()
        
        return 'remote' in location_str or 'remote' in desc_str
    
    def calculate_priority(location, company, description='', job_url=''):
        """
        Calculate job priority based on:
        - Remote AND Startup = High Priority
        - Greenhouse/Lever portals = High Priority
        - Otherwise = Normal Priority
        """
        location_str = safe_str(location).lower()
        company_str = safe_str(company).lower()
        desc_str = safe_str(description).lower()
        url_str = safe_str(job_url).lower()
        
        # Check if Remote AND Startup
        is_remote = 'remote' in location_str or 'remote' in desc_str
        is_startup = 'startup' in company_str or 'startup' in desc_str
        
        # Check if from direct portals (Greenhouse/Lever/Big Tech)
        is_direct_portal = any(portal in url_str for portal in DIRECT_PORTALS)
        
        if (is_remote and is_startup) or is_direct_portal:
            return 'High'
        
        return 'Normal'
    
    def detect_work_mode(location, description=''):
        """
        Detect work mode: Remote, Onsite, or Hybrid
        """
        location_str = safe_str(location).lower()
        desc_str = safe_str(description).lower()
        combined_text = f"{location_str} {desc_str}"
        
        # Check for remote indicators
        if 'remote' in combined_text:
            # Check if it's hybrid (remote + onsite)
            if 'hybrid' in combined_text or 'on-site' in combined_text or 'onsite' in combined_text:
                return 'Hybrid'
            return 'Remote'
        
        # Check for hybrid indicators
        if 'hybrid' in combined_text:
            return 'Hybrid'
        
        # Default to Onsite if no remote/hybrid indicators
        return 'Onsite'
    
    def is_direct_portal(source, job_url=''):
        """
        Check if the job is from a direct ATS portal or Big Tech career site
        (Greenhouse, Lever, Google Careers, Microsoft Careers, etc.)
        """
        source_str = safe_str(source).lower()
        url_str = safe_str(job_url).lower()
        
        # Check if URL contains any direct portal domains
        if any(portal in url_str for portal in DIRECT_PORTALS):
            return True
        
        # Check if source mentions direct portals
        if any(portal.split('.')[0] in source_str for portal in DIRECT_PORTALS):
            return True
        
        return False
    
    def is_remote_board(source, job_url=''):
        """
        Check if the job is from a remote-first job board
        (We Work Remotely, Remotive, Wellfound, etc.)
        """
        source_str = safe_str(source).lower()
        url_str = safe_str(job_url).lower()
        
        # Check if source or URL contains remote board indicators
        if any(board in source_str or board in url_str for board in REMOTE_BOARDS):
            return True
        
        return False
    
    def is_career_portal(source, job_url=''):
        """
        Check if the job is from a company career portal
        (not from LinkedIn, Glassdoor, Indeed, or remote boards)
        This is used as a backup category
        """
        source_str = safe_str(source).lower()
        url_str = safe_str(job_url).lower()
        
        # Job board platforms
        job_boards = ['linkedin', 'glassdoor', 'indeed']
        
        # If it's a direct portal or remote board, it's not a generic career portal
        if is_direct_portal(source, job_url) or is_remote_board(source, job_url):
            return False
        
        # If source is explicitly from a job board, it's not a career portal
        if any(board in source_str for board in job_boards):
            return False
        
        # If URL contains job board domains, it's not a career portal
        if any(board in url_str for board in job_boards):
            return False
        
        # Otherwise, it's likely a company career portal
        return True
    
    def push_to_google_sheets(jobs_df):
        """
        Push new jobs to Google Sheets with intelligent 5-sheet routing:
        - Direct_Portals: ATS systems (Greenhouse, Lever) + Big Tech career sites
        - International_Remote: Remote boards (WWR, Remotive) + Non-India remote jobs
        - Indian_Remote: India location + Remote mode
        - Indian_Onsite: India location + Onsite/Hybrid mode
        - Career_Portals: Other company career sites (backup category)
        
        Returns the count of new jobs added
        """
        try:
            # Get the directory of the current script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Look for google_key.json in the scrapper folder
            credentials_file = os.path.join(script_dir, 'google_key.json')
            
            # Check if credentials file exists
            if not os.path.exists(credentials_file):
                print(f"\n⚠ Warning: google_key.json not found at {credentials_file}")
                print("Skipping Google Sheets upload.")
                return 0
            
            # Define the scope
            scope = ['https://spreadsheets.google.com/feeds',
                     'https://www.googleapis.com/auth/drive']
            
            # Authenticate using the credentials file
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
            client = gspread.authorize(creds)
            
            # Open the Google Sheet
            print("Looking for sheet: Ai Job Tracker...")
            sheet = client.open('Ai Job Tracker')
            
            # Get all five worksheets
            try:
                ws_direct_portals = sheet.worksheet('Direct_Portals')
                ws_international_remote = sheet.worksheet('International_Remote')
                ws_indian_remote = sheet.worksheet('Indian_Remote')
                ws_indian_onsite = sheet.worksheet('Indian_Onsite')
                ws_career_portals = sheet.worksheet('Career_Portals')
            except gspread.exceptions.WorksheetNotFound as e:
                print(f"\n⚠ Error: Required worksheet not found: {e}")
                print("Please create these 5 worksheets: Direct_Portals, International_Remote, Indian_Remote, Indian_Onsite, Career_Portals")
                return 0
            
            # Define the correct headers
            correct_headers = ['Role', 'Company', 'Location', 'Mode', 'Link', 'Source', 'Salary', 'Posted_Date']
            
            # Ensure each worksheet has the correct headers
            all_worksheets = [ws_direct_portals, ws_international_remote, ws_indian_remote, ws_indian_onsite, ws_career_portals]
            for worksheet in all_worksheets:
                try:
                    # Get the first row (headers)
                    existing_headers = worksheet.row_values(1)
                    
                    # If headers are missing or incorrect, set them
                    if not existing_headers or existing_headers != correct_headers:
                        print(f"Setting headers for {worksheet.title}...")
                        worksheet.clear()  # Clear the sheet
                        worksheet.append_row(correct_headers)  # Add headers
                except Exception as header_error:
                    print(f"Warning: Could not validate headers for {worksheet.title}: {header_error}")
                    # Try to add headers anyway
                    try:
                        worksheet.clear()
                        worksheet.append_row(correct_headers)
                    except:
                        pass
            
            # ========== GLOBAL DEDUPLICATION (Cross-Tab Check) ==========
            # Collect existing URLs from ALL 5 worksheets to avoid duplicates
            print("\n🔍 Checking for existing jobs across all 5 sheets...")
            existing_urls = set()  # Memory-efficient Set for fast lookup
            
            for worksheet in all_worksheets:
                try:
                    existing_data = worksheet.get_all_records()
                    sheet_urls = 0
                    for row in existing_data:
                        # Check multiple possible column names for URL
                        url = row.get('Link') or row.get('Job URL') or row.get('link') or ''
                        if url and url.strip():  # Only add non-empty URLs
                            existing_urls.add(url.strip())
                            sheet_urls += 1
                    
                    if sheet_urls > 0:
                        print(f"   ✓ {worksheet.title}: {sheet_urls} existing jobs found")
                except Exception as e:
                    # Don't crash if a sheet is empty or has issues
                    print(f"   ⚠ {worksheet.title}: Could not read (might be empty) - {e}")
                    continue  # Skip to next sheet
            
            print(f"   📊 Total existing URLs across all sheets: {len(existing_urls)}")
            
            # Count new jobs added to each worksheet
            job_counts = {
                'Direct_Portals': 0,
                'International_Remote': 0,
                'Indian_Remote': 0,
                'Indian_Onsite': 0,
                'Career_Portals': 0
            }
            
            duplicates_skipped = 0  # Track how many duplicates we skip
            
            # Iterate through jobs and route them to appropriate worksheets
            for _, job in jobs_df.iterrows():
                # Extract and clean job data (use fillna to avoid NaN)
                title = safe_str(job.get('title', ''))
                company = safe_str(job.get('company', ''))
                location = safe_str(job.get('location', ''))
                job_url = safe_str(job.get('job_url', ''))
                description = safe_str(job.get('description', ''))
                source = safe_str(job.get('source', ''))
                salary_range = safe_str(job.get('salary_range', ''))
                posted_date = safe_str(job.get('posted_date', ''))
                
                # Skip if job already exists in ANY sheet (Global Deduplication)
                if job_url and job_url.strip() in existing_urls:
                    duplicates_skipped += 1
                    continue
                
                # Detect work mode
                work_mode = detect_work_mode(location, description)
                
                # Check source type
                from_direct_portal = is_direct_portal(source, job_url)
                from_remote_board = is_remote_board(source, job_url)
                from_career_portal = is_career_portal(source, job_url)
                
                # Prepare the row data to match your Google Sheets structure
                # Columns: Role | Company | Location | Mode | Link | Source | Salary | Posted_Date
                new_row = [
                    title,           # Role
                    company,         # Company
                    location,        # Location
                    work_mode,       # Mode
                    job_url,         # Link
                    source,          # Source
                    salary_range,    # Salary
                    posted_date      # Posted_Date
                ]
                
                # ========== ENHANCED 5-SHEET ROUTING LOGIC ==========
                target_worksheet = None
                
                # PRIORITY 1: Direct Portals (ATS + Big Tech career sites)
                if from_direct_portal:
                    target_worksheet = ws_direct_portals
                    job_counts['Direct_Portals'] += 1
                
                # PRIORITY 2: Remote Boards → International_Remote
                elif from_remote_board:
                    target_worksheet = ws_international_remote
                    job_counts['International_Remote'] += 1
                
                # PRIORITY 3: Indian Remote
                elif 'india' in location.lower() and work_mode == 'Remote':
                    target_worksheet = ws_indian_remote
                    job_counts['Indian_Remote'] += 1
                
                # PRIORITY 4: Indian Onsite/Hybrid
                elif 'india' in location.lower() and work_mode in ['Onsite', 'Hybrid']:
                    target_worksheet = ws_indian_onsite
                    job_counts['Indian_Onsite'] += 1
                
                # PRIORITY 5: International Remote (non-India remote jobs)
                elif 'india' not in location.lower() and work_mode == 'Remote':
                    target_worksheet = ws_international_remote
                    job_counts['International_Remote'] += 1
                
                # PRIORITY 6: Career Portals (backup for other company sites)
                elif from_career_portal:
                    target_worksheet = ws_career_portals
                    job_counts['Career_Portals'] += 1
                
                # Fallback: If no rule matches, put in International_Remote
                else:
                    target_worksheet = ws_international_remote
                    job_counts['International_Remote'] += 1
                
                # Append the row to the appropriate worksheet
                if target_worksheet:
                    try:
                        target_worksheet.append_row(new_row)
                        existing_urls.add(job_url)  # Add to set to avoid duplicates in this batch
                    except Exception as append_error:
                        print(f"Warning: Could not append job to {target_worksheet.title}: {append_error}")
            
            # Calculate total new jobs
            total_new_jobs = sum(job_counts.values())
            
            # Print routing summary
            print(f"\n📊 ROUTING SUMMARY (5-Sheet System):")
            print(f"   - Direct_Portals: {job_counts['Direct_Portals']} jobs")
            print(f"   - International_Remote: {job_counts['International_Remote']} jobs")
            print(f"   - Indian_Remote: {job_counts['Indian_Remote']} jobs")
            print(f"   - Indian_Onsite: {job_counts['Indian_Onsite']} jobs")
            print(f"   - Career_Portals: {job_counts['Career_Portals']} jobs")
            
            if duplicates_skipped > 0:
                print(f"\n   🔄 Duplicates Skipped: {duplicates_skipped} jobs (already exist in sheets)")
            
            return total_new_jobs
            
        except gspread.exceptions.SpreadsheetNotFound:
            print("\n⚠ Error: Google Sheet 'Ai Job Tracker' not found.")
            print("Please make sure the sheet exists and is shared with the service account.")
            return 0
        except Exception as sheets_error:
            print(f"\n⚠ Error pushing to Google Sheets: {sheets_error}")
            return 0
    
    print("🌍 Starting GLOBAL JOB HUNTER - ADVANCED ROUTING SYSTEM...")
    print("=" * 70)
    print("✓ Tech Stack Filter: Python, C++, MERN, React, Node, AI, ML, Intern")
    print("✓ Direct Portals: Greenhouse, Lever, Big Tech Career Sites")
    print("✓ 5-Sheet Routing: Direct_Portals, International_Remote, Indian_Remote, Indian_Onsite, Career_Portals")
    print(f"✓ Remote Filter: {'REMOTE ONLY' if REMOTE_ONLY_MODE else 'ALL MODES (Remote/Hybrid/Onsite)'}")
    print(f"✓ Batch Size: {RESULTS_PER_SOURCE} jobs per source (Testing Mode)")
    print(f"✓ Freshness: Last {DAYS_OLD} days only")
    print("=" * 70)
    
    # Define search parameters (reduced for testing)
    job_titles = ['Software Developer Intern']  # Only one job title for faster testing
    locations = ['USA', 'Remote', 'India']
    
    # ========== BATCHED SCRAPING ==========
    # Scrape from each source separately for better control
    sources = ['linkedin', 'glassdoor', 'indeed']
    
    # Search parameters
    hours_old = DAYS_OLD * 24  # Convert days to hours (7 days = 168 hours)
    
    all_jobs = []
    
    # Search for each source separately (batching)
    for source in sources:
        print(f"\n{'='*70}")
        print(f"📦 BATCH SCRAPING FROM: {source.upper()}")
        print(f"{'='*70}")
        
        for job_title in job_titles:
            for location in locations:
                print(f"\n🔍 Searching for '{job_title}' in '{location}' on {source.upper()}...")
                
                try:
                    jobs = scrape_jobs(
                        site_name=[source],  # Single source at a time
                        search_term=job_title,
                        location=location,
                        results_wanted=RESULTS_PER_SOURCE,
                        hours_old=hours_old,
                        country_indeed='USA'
                    )
                    
                    if jobs is not None and not jobs.empty:
                        # Add source column to track where the job came from
                        jobs['source'] = source.capitalize()
                        all_jobs.append(jobs)
                        print(f"  ✓ Found {len(jobs)} jobs from {source.upper()}")
                    else:
                        print(f"  ✗ No jobs found on {source.upper()}")
                        
                except Exception as search_error:
                    print(f"  ✗ Error searching '{job_title}' in '{location}' on {source.upper()}: {search_error}")
                    continue
    
    # Combine all results
    if all_jobs:
        combined_jobs = pd.concat(all_jobs, ignore_index=True)
        
        # Remove duplicates based on job URL
        combined_jobs = combined_jobs.drop_duplicates(subset=['job_url'], keep='first')
        
        print(f"\n{'='*70}")
        print(f"📊 Processing {len(combined_jobs)} unique jobs...")
        print(f"{'='*70}")
        
        # ========== DEEP EXTRACTION & FILTERING ==========
        processed_jobs = []
        
        for _, job in combined_jobs.iterrows():
            title = safe_str(job.get('title', ''))
            company = safe_str(job.get('company', ''))
            location = safe_str(job.get('location', ''))
            job_url = safe_str(job.get('job_url', ''))
            description = safe_str(job.get('description', ''))
            source = safe_str(job.get('source', 'Unknown'))
            
            # TECH STACK FILTER: Only keep jobs mentioning required keywords
            if not check_tech_stack_match(title, description):
                continue
            
            # REMOTE FILTER: If REMOTE_ONLY_MODE is enabled, skip non-remote jobs
            if REMOTE_ONLY_MODE and not is_remote_job(location, description):
                continue
            
            # Extract additional information
            salary_range = extract_salary_range(description, title)
            seniority_level = extract_seniority_level(title, description)
            category = categorize_location(location)
            work_mode = detect_work_mode(location, description)  # Detect work mode
            
            # Extract posted date
            posted_date = ''
            if 'date_posted' in job and pd.notna(job['date_posted']):
                try:
                    posted_date = pd.to_datetime(job['date_posted']).strftime('%Y-%m-%d')
                except:
                    posted_date = safe_str(job.get('date_posted', ''))
            
            # Calculate priority
            priority = calculate_priority(location, company, description, job_url)
            
            processed_jobs.append({
                'title': title,
                'company': company,
                'location': location,
                'job_url': job_url,
                'description': description,  # Include description for routing
                'salary_range': salary_range,
                'posted_date': posted_date,
                'seniority_level': seniority_level,
                'priority': priority,
                'category': category,
                'source': source,
                'work_mode': work_mode  # Include work mode
            })
        
        if processed_jobs:
            # Convert to DataFrame
            final_jobs = pd.DataFrame(processed_jobs)
            
            # Sort by priority (High first), category (National first), and then by posted date
            final_jobs['priority_score'] = final_jobs['priority'].apply(lambda x: 1 if x == 'High' else 0)
            final_jobs['category_score'] = final_jobs['category'].apply(lambda x: 1 if x == 'National' else 0)
            final_jobs = final_jobs.sort_values(['priority_score', 'category_score', 'posted_date'], 
                                                 ascending=[False, False, False])
            final_jobs = final_jobs.drop(['priority_score', 'category_score'], axis=1)
            
            # Limit to top results (reduced for testing)
            final_jobs = final_jobs.head(5)
            
            # Get the directory of the current script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(script_dir, 'found_jobs.csv')
            
            # Save to CSV with NaN handling
            final_jobs.to_csv(output_file, index=False, encoding='utf-8')
            
            print("\n" + "=" * 70)
            print(f"✅ SEARCH COMPLETE! Found {len(final_jobs)} matching jobs.")
            print(f"   📊 BREAKDOWN:")
            print(f"   - High Priority Jobs: {len(final_jobs[final_jobs['priority'] == 'High'])}")
            print(f"   - Normal Priority Jobs: {len(final_jobs[final_jobs['priority'] == 'Normal'])}")
            print(f"   - National (India) Jobs: {len(final_jobs[final_jobs['category'] == 'National'])}")
            print(f"   - International Jobs: {len(final_jobs[final_jobs['category'] == 'International'])}")
            print(f"\n   🌐 SOURCE BREAKDOWN:")
            for source in final_jobs['source'].unique():
                count = len(final_jobs[final_jobs['source'] == source])
                print(f"   - {source}: {count} jobs")
            print(f"\n✓ Results saved to: {output_file}")
            
            # Push to Google Sheets
            print("\n📤 Pushing jobs to Google Sheets...")
            new_jobs_pushed = push_to_google_sheets(final_jobs)
            
            if new_jobs_pushed > 0:
                print(f"✅ Successfully pushed {new_jobs_pushed} new jobs to Google Sheets!")
            elif new_jobs_pushed == 0:
                print("ℹ️  No new jobs to push (all jobs already exist in the sheet).")
            
            print("=" * 70)
            
        else:
            print("\n" + "=" * 70)
            print("⚠️  No jobs matched the filters (tech stack or remote mode).")
            print("=" * 70)
            
            # Create empty CSV with headers
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(script_dir, 'found_jobs.csv')
            empty_df = pd.DataFrame(columns=['title', 'company', 'location', 'job_url', 'description', 'salary_range', 
                                            'posted_date', 'seniority_level', 'priority', 'category', 'source', 'work_mode'])
            empty_df.to_csv(output_file, index=False, encoding='utf-8')
        
    else:
        print("\n" + "=" * 70)
        print("✗ Job Search Complete! Found 0 jobs.")
        print("=" * 70)
        
        # Create empty CSV with headers
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, 'found_jobs.csv')
        empty_df = pd.DataFrame(columns=['title', 'company', 'location', 'job_url', 'description', 'salary_range', 
                                        'posted_date', 'seniority_level', 'priority', 'category', 'source', 'work_mode'])
        empty_df.to_csv(output_file, index=False, encoding='utf-8')

except ImportError as import_error:
    print("=" * 70)
    print("ERROR: Missing required library")
    print("=" * 70)
    print(f"Import Error: {import_error}")
    print("\nPlease install the required library:")
    print("  pip install python-jobspy gspread oauth2client")
    print("=" * 70)

except Exception as e:
    print("=" * 70)
    print("ERROR: An unexpected error occurred")
    print("=" * 70)
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {e}")
    print("\nThis might be due to:")
    print("  - Version conflicts with NumPy or Pandas")
    print("  - Network connectivity issues")
    print("  - API rate limiting from job sites")
    print("\nTry updating your libraries:")
    print("  pip install --upgrade python-jobspy pandas numpy gspread oauth2client")
    print("=" * 70)
