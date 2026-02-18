"""
🚀 AI JOB TRACKER - STREAMLIT WEB APP
Professional job search interface with Google Sheets integration
"""

import streamlit as st
import pandas as pd
import os
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ========== PAGE CONFIGURATION ==========
st.set_page_config(
    page_title="AI Job Tracker",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CUSTOM CSS FOR DARK THEME ==========
st.markdown("""
    <style>
    /* Main background and text */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #00d4ff !important;
        font-weight: 700 !important;
    }
    
    /* Cards/Containers */
    .job-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid rgba(0, 212, 255, 0.3);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .job-card:hover {
        transform: translateY(-5px);
        border-color: rgba(0, 212, 255, 0.8);
        box-shadow: 0 10px 30px rgba(0, 212, 255, 0.3);
    }
    
    /* Priority badges */
    .priority-high {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        font-size: 12px;
    }
    
    .priority-normal {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        font-size: 12px;
    }
    
    /* Category badges */
    .category-national {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        color: #333;
        padding: 5px 12px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 11px;
        display: inline-block;
    }
    
    .category-international {
        background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);
        color: white;
        padding: 5px 12px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 11px;
        display: inline-block;
    }
    
    /* Source badges */
    .source-badge {
        background: rgba(255, 255, 255, 0.1);
        color: #00d4ff;
        padding: 4px 10px;
        border-radius: 10px;
        font-size: 10px;
        border: 1px solid rgba(0, 212, 255, 0.3);
        display: inline-block;
    }
    
    /* Apply button */
    .apply-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 10px 25px;
        border-radius: 25px;
        text-decoration: none;
        font-weight: bold;
        display: inline-block;
        transition: all 0.3s ease;
        border: none;
        cursor: pointer;
    }
    
    .apply-button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.5);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: rgba(0, 0, 0, 0.3);
    }
    
    /* Metrics */
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(0, 212, 255, 0.3);
    }
    
    /* Search box */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.05);
        color: white;
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 10px;
    }
    
    /* Select box */
    .stSelectbox > div > div > select {
        background: rgba(255, 255, 255, 0.05);
        color: white;
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ========== DATA LOADING FUNCTIONS ==========
@st.cache_data(ttl=30)  # Cache for 30 seconds (faster refresh)
def load_from_google_sheets():
    """
    Load jobs from ALL 5 Google Sheets and combine with deduplication
    Also tracks which sheet each job came from for category filtering
    """
    try:
        # Get credentials file path (updated to look in scrapper folder)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_file = os.path.join(script_dir, 'google_key.json')
        
        if not os.path.exists(credentials_file):
            return None
        
        # Authenticate
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        
        # Open sheet
        sheet = client.open('Ai Job Tracker')
        
        # Load from all 5 worksheets
        all_dfs = []
        sheet_names = ['Direct_Portals', 'International_Remote', 'Indian_Remote', 
                      'Indian_Onsite', 'Career_Portals']
        
        for sheet_name in sheet_names:
            try:
                worksheet = sheet.worksheet(sheet_name)
                data = worksheet.get_all_records()
                
                if data:
                    df_temp = pd.DataFrame(data)
                    # Add a column to track which sheet this job came from
                    df_temp['sheet_source'] = sheet_name
                    all_dfs.append(df_temp)
            except Exception as e:
                # Skip if sheet doesn't exist or is empty
                continue
        
        if not all_dfs:
            return None
        
        # Combine all dataframes
        df = pd.concat(all_dfs, ignore_index=True)
        
        # Rename columns to match our internal format
        column_mapping = {
            'Role': 'title',
            'Company': 'company',
            'Location': 'location',
            'Mode': 'work_mode',
            'Link': 'job_url',
            'Source': 'source',
            'Salary': 'salary_range',
            'Posted_Date': 'posted_date',
            'Score': 'Score',
            'Summary': 'Summary'
        }
        df = df.rename(columns=column_mapping)
        
        # ========== GLOBAL DEDUPLICATION ==========
        # Remove duplicates based on job_url (Link column)
        if 'job_url' in df.columns:
            df = df.drop_duplicates(subset=['job_url'], keep='first')
        
        return df
        
    except Exception as e:
        st.sidebar.warning(f"Could not load from Google Sheets: {e}")
        return None

@st.cache_data(ttl=300)
def load_from_csv():
    """
    Load jobs from CSV file as fallback
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_file = os.path.join(script_dir, 'found_jobs.csv')
        
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            return df
        
        return None
        
    except Exception as e:
        st.sidebar.warning(f"Could not load from CSV: {e}")
        return None

def load_data():
    """
    Load data from Google Sheets ONLY (no CSV fallback)
    """
    # Load from Google Sheets
    df = load_from_google_sheets()
    
    if df is not None and not df.empty:
        # Debug breakdown
        if 'sheet_source' in df.columns:
            counts = df['sheet_source'].value_counts()
            st.sidebar.markdown("### 📊 Database (Live)")
            for source, count in counts.items():
                st.sidebar.text(f"{source}: {count}")
        
        st.sidebar.success(f"✅ Loaded {len(df)} jobs total")
        return df
    
    # No fallback - return empty DataFrame
    st.sidebar.info("📭 No jobs in Google Sheets yet.")
    return pd.DataFrame()

@st.cache_data(ttl=60)  # Cache for 1 minute (shorter to see updates quickly)
def load_applied_jobs():
    """
    Load applied jobs from the Applied_Jobs sheet
    """
    try:
        # Get credentials file path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_file = os.path.join(script_dir, 'google_key.json')
        
        if not os.path.exists(credentials_file):
            return pd.DataFrame()
        
        # Authenticate
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        
        # Open sheet
        sheet = client.open('Ai Job Tracker')
        
        # Load Applied_Jobs worksheet
        try:
            worksheet = sheet.worksheet('Applied_Jobs')
            data = worksheet.get_all_records()
            
            if data:
                return pd.DataFrame(data)
            else:
                return pd.DataFrame()
        except:
            # Sheet doesn't exist or is empty
            return pd.DataFrame()
            
    except Exception as e:
        return pd.DataFrame()

def add_to_applied_jobs(job):
    """
    Add a job to the Applied_Jobs sheet in Google Sheets
    """
    try:
        # Get credentials file path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_file = os.path.join(script_dir, 'google_key.json')
        
        if not os.path.exists(credentials_file):
            return False, "Credentials file not found"
        
        # Authenticate
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        
        # Open sheet
        sheet = client.open('Ai Job Tracker')
        
        # Get or create Applied_Jobs worksheet
        try:
            worksheet = sheet.worksheet('Applied_Jobs')
        except:
            # Create the worksheet if it doesn't exist
            worksheet = sheet.add_worksheet(title='Applied_Jobs', rows=1000, cols=11)
            # Add headers
            headers = ['Role', 'Company', 'Location', 'Mode', 'Link', 'Source', 'Salary', 'Posted_Date', 'Score', 'Summary', 'status']
            worksheet.append_row(headers)
        
        # Prepare row data
        today = datetime.now().strftime('%Y-%m-%d')
        row_data = [
            job.get('title', 'N/A'),
            job.get('company', 'N/A'),
            job.get('location', 'N/A'),
            job.get('work_mode', job.get('Mode', 'Unknown')),
            job.get('job_url', ''),
            job.get('source', 'Unknown'),
            job.get('salary_range', ''),
            job.get('posted_date', ''),
            job.get('Score', job.get('score', '')),
            job.get('Summary', job.get('summary', '')),
            'Applied'  # Status
        ]
        
        # Append the row
        worksheet.append_row(row_data)
        
        # Clear cache so the applied jobs list updates
        load_applied_jobs.clear()
        
        return True, "Job added successfully!"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def display_category_jobs(df, category_name):
    """
    Display jobs from a specific category sheet only
    Filters by sheet_source column to show only jobs from that sheet
    """
    if df is None or df.empty:
        st.info("📭 No jobs to show yet!")
        st.markdown("""
        ### 🚀 Get Started:
        1. Click **"⚡ Run System Recommendation"** in the sidebar
        2. Wait 2-3 minutes while AI finds perfect jobs for you
        3. Jobs will appear here automatically!
        """)
        return
    
    # Map category display names to EXACT sheet names
    category_mapping = {
        "Direct Portals": "Direct_Portals",
        "International Remote": "International_Remote",
        "Indian Remote": "Indian_Remote",
        "Indian Onsite": "Indian_Onsite",
        "Career Portals": "Career_Portals"
    }
    
    # Get the target sheet name
    target_sheet = category_mapping.get(category_name)
    
    # Filter logic
    if category_name == "All Jobs":
        # Show everything
        category_df = df.copy()
    elif target_sheet and 'sheet_source' in df.columns:
        # STRICT FILTER: Only show jobs where sheet_source matches target_sheet
        category_df = df[df['sheet_source'] == target_sheet].copy()
    else:
        # Fallback (should not happen if data is loaded correctly)
        category_df = pd.DataFrame()
    
    # Debug info (optional - helps verify)
    # st.write(f"Showing {len(category_df)} jobs from {target_sheet if target_sheet else 'All'}")

    if category_df.empty:
        st.info(f"📭 No jobs found in {category_name}")
        st.markdown("""
        ### 🚀 What to do:
        1. Click **"⚡ Run System Recommendation"**
        2. Wait for jobs to be found and routed here
        """)
        return
    
    # Display stats
    st.metric("Total Jobs", len(category_df))
    
    # Display jobs
    for idx, job in category_df.iterrows():
        render_job_card(job, idx)

# Manual search results are NOT saved to a separate sheet
# Users can only save by clicking "Apply" button which saves to Applied_Jobs

# ========== HELPER FUNCTIONS ==========
def render_job_card(job, job_index=None):
    """
    Render an enhanced job card with AI score, summary, and Apply & Track button
    Using Streamlit native components instead of HTML to avoid rendering issues
    """
    # Get job details with safe defaults
    title = str(job.get('title', 'N/A'))
    company = str(job.get('company', 'N/A'))
    location = str(job.get('location', 'N/A'))
    work_mode = str(job.get('work_mode', job.get('Mode', 'Unknown')))
    source = str(job.get('source', 'Unknown'))
    salary_range = str(job.get('salary_range', ''))
    posted_date = str(job.get('posted_date', ''))
    job_url = str(job.get('job_url', '#'))
    
    # AI Score and Summary
    score = job.get('Score', job.get('score', ''))
    summary = str(job.get('Summary', job.get('summary', '')))
    
    # Create a container for the job card
    with st.container():
        # Card styling
        st.markdown("""
            <style>
            .job-card-container {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 15px;
                padding: 20px;
                margin: 15px 0;
                border: 1px solid rgba(0, 212, 255, 0.3);
                backdrop-filter: blur(10px);
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Score badge
        if score and str(score).strip():
            try:
                score_val = int(float(score))
                if score_val >= 80:
                    st.success(f"🎯 Excellent Match: {score_val}/100")
                elif score_val >= 60:
                    st.info(f"✨ Good Match: {score_val}/100")
                elif score_val >= 40:
                    st.warning(f"⚡ Moderate Match: {score_val}/100")
                else:
                    st.error(f"💡 Low Match: {score_val}/100")
            except:
                pass
        
        # Job title and company
        st.markdown(f"### {title}")
        st.markdown(f"**🏢 {company}**")
        
        # Location, mode, source in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text(f"📍 {location}")
        with col2:
            mode_emoji = "🏠" if "remote" in work_mode.lower() else "🔄" if "hybrid" in work_mode.lower() else "🏢"
            st.text(f"{mode_emoji} {work_mode}")
        with col3:
            st.text(f"🔗 {source}")
        
        # DEBUG: Show Source Sheet
        sheet_source = str(job.get('sheet_source', 'Unknown'))
        if sheet_source and sheet_source != 'Unknown':
            st.caption(f"📂 Source Sheet: `{sheet_source}`")
        
        # Salary and date
        if salary_range:
            st.text(f"💰 {salary_range}")
        if posted_date:
            st.text(f"📅 {posted_date}")
        
        # AI Summary (expandable)
        if summary and summary.strip():
            with st.expander("🤖 AI Analysis"):
                st.write(summary)
        
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 3])
        
        with col1:
            apply_key = f"apply_{job_index}_{hash(job_url)}" if job_index is not None else f"apply_{hash(job_url)}"
            
            if st.button("✅ Apply", key=apply_key, type="primary", use_container_width=True):
                success, message = add_to_applied_jobs(job)
                
                if success:
                    st.success("✅ Applied Successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Failed: {message}")
        
        with col2:
            ignore_key = f"ignore_{job_index}_{hash(job_url)}" if job_index is not None else f"ignore_{hash(job_url)}"
            
            if st.button("🚫 Ignore", key=ignore_key, use_container_width=True):
                if 'ignored_jobs' not in st.session_state:
                    st.session_state.ignored_jobs = []
                
                st.session_state.ignored_jobs.append(job_url)
                st.info("🚫 Job ignored for this session")
                time.sleep(0.5)
                st.rerun()
        
        with col3:
            st.link_button("🔗 Open Job Link", job_url, use_container_width=True)
        
        # Divider
        st.markdown("---")

def filter_jobs(df, role_search="", location_search="", remote_only=False):
    """
    Filter jobs based on search criteria with safe column access
    """
    filtered_df = df.copy()
    
    # Role filter - only if title column exists
    if role_search and 'title' in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df['title'].str.contains(role_search, case=False, na=False)
        ]
    
    # Location filter - only if location column exists
    if location_search and 'location' in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df['location'].str.contains(location_search, case=False, na=False)
        ]
    
    # Remote filter - only if location column exists
    if remote_only and 'location' in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df['location'].str.contains('remote', case=False, na=False)
        ]
    
    return filtered_df

# ========== MAIN APP ==========
def main():
    # Header
    st.markdown("""
        <h1 style="text-align: center; font-size: 3em; margin-bottom: 10px;">
            🌍 Global Job Hunter Dashboard
        </h1>
        <p style="text-align: center; color: #aaa; font-size: 1.2em; margin-bottom: 30px;">
            AI-Powered Job Matching System
        </p>
    """, unsafe_allow_html=True)
    
    # Load data
    df = load_data()
    
    # Clear any previous error states if we have data
    if not df.empty and 'show_error' in st.session_state:
        del st.session_state['show_error']
    
    # Don't return early - sidebar needs to render even when empty
    # if df.empty:
    #     st.error("No jobs available. Please run the job scraper first!")
    #     return
    
    # Load applied jobs and filter them out
    applied_jobs_df = load_applied_jobs()
    
    if not applied_jobs_df.empty and 'Link' in applied_jobs_df.columns:
        # Get list of applied job URLs
        applied_urls = applied_jobs_df['Link'].tolist()
        
        # Filter out jobs that have already been applied to
        original_count = len(df)
        df = df[~df['job_url'].isin(applied_urls)]
        filtered_count = original_count - len(df)
        
        if filtered_count > 0:
            st.sidebar.info(f"🎯 Hiding {filtered_count} already applied jobs")
    
    # Filter out ignored jobs from current session
    if 'ignored_jobs' in st.session_state and st.session_state.ignored_jobs:
        ignored_count = len(df)
        df = df[~df['job_url'].isin(st.session_state.ignored_jobs)]
        ignored_count = ignored_count - len(df)
        
        if ignored_count > 0:
            st.sidebar.info(f"🚫 Hiding {ignored_count} ignored jobs (this session)")
    
    # Calculate stats (handle empty dataframe)
    total_jobs = len(df) if not df.empty else 0
    
    # Calculate stats based on work_mode
    remote_jobs = 0
    onsite_jobs = 0
    hybrid_jobs = 0
    
    if not df.empty:
        if 'work_mode' in df.columns:
            remote_jobs = len(df[df['work_mode'].str.lower() == 'remote'])
            onsite_jobs = len(df[df['work_mode'].str.lower() == 'onsite'])
            hybrid_jobs = len(df[df['work_mode'].str.lower() == 'hybrid'])
        elif 'Mode' in df.columns:
            remote_jobs = len(df[df['Mode'].str.lower() == 'remote'])
            onsite_jobs = len(df[df['Mode'].str.lower() == 'onsite'])
            hybrid_jobs = len(df[df['Mode'].str.lower() == 'hybrid'])
    
    # Calculate AI score stats
    high_score_jobs = 0
    if not df.empty and ('Score' in df.columns or 'score' in df.columns):
        score_col = 'Score' if 'Score' in df.columns else 'score'
        try:
            df[score_col] = pd.to_numeric(df[score_col], errors='coerce')
            high_score_jobs = len(df[df[score_col] >= 80])
        except:
            pass
    
    # Sidebar
    st.sidebar.title("📊 Dashboard")
    
    # ========== MAIN NAVIGATION ==========
    st.sidebar.subheader("🎯 Main Menu")
    
    # Main page selection
    main_page = st.sidebar.radio(
        "Select View",
        ["🤖 AI Recommendations", "🔍 Manual Search"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    
    # ========== SYSTEM RECOMMENDATION BUTTON ==========
    st.sidebar.subheader("🚀 Quick Actions")
    
    if st.sidebar.button("⚡ Run System Recommendation", type="primary", use_container_width=True):
        # Clear any previous errors
        if 'show_error' in st.session_state:
            del st.session_state['show_error']
        
        with st.spinner("🤖 Analyzing your resume and finding perfect matches... This may take 2-3 minutes..."):
            try:
                import subprocess
                import sys
                
                # Run system recommendation script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                rec_script = os.path.join(script_dir, 'system_recommendation.py')
                
                result = subprocess.run(
                    [sys.executable, rec_script],
                    capture_output=True,
                    text=True,
                    cwd=script_dir
                )
                
                if result.returncode == 0:
                    st.success("✅ System Recommendation Complete!")
                    st.balloons()
                    st.info("📊 Jobs have been added to your Google Sheets. Refreshing dashboard...")
                    
                    # Show summary from output
                    if "Added" in result.stdout:
                        # Extract the summary line
                        for line in result.stdout.split('\n'):
                            if 'Added' in line or 'Direct_Portals' in line or 'International_Remote' in line:
                                st.text(line)
                    
                    # Clear cache to reload data
                    st.cache_data.clear()
                    time.sleep(2)
                    st.rerun()
                else:
                    # Only show error if there's an actual error
                    st.session_state['show_error'] = True
                    st.error("❌ Error running recommendation engine")
                    # Only show stderr if there's an actual error
                    if result.stderr and "Error" in result.stderr:
                        with st.expander("Error Details"):
                            st.code(result.stderr)
                    
            except Exception as e:
                st.session_state['show_error'] = True
                st.error(f"❌ Error running recommendation: {e}")
    
    # Refresh Data button
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # ========== SUB-NAVIGATION FOR AI RECOMMENDATIONS ==========
    if main_page == "🤖 AI Recommendations":
        st.sidebar.subheader("📂 Job Categories")
        page = st.sidebar.selectbox(
            "Select Category",
            [
                "All AI Recommendations", 
                "Direct Portals", 
                "International Remote", 
                "Indian Remote", 
                "Indian Onsite", 
                "Career Portals"
            ],
            key="category_select_v3",
            label_visibility="collapsed"
        )
    else:
        page = main_page
    
    st.sidebar.markdown("---")
    
    # ========== METRICS (MIDDLE) ==========
    st.sidebar.subheader("📈 Stats")
    
    st.sidebar.markdown(f"""
    <div class="metric-card">
        <h3 style="margin: 0; color: #00d4ff;">Total Jobs</h3>
        <h2 style="margin: 5px 0; color: white;">{total_jobs}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("🎯 High Score", high_score_jobs)
    with col2:
        st.metric("🏠 Remote", remote_jobs)
    
    col3, col4 = st.sidebar.columns(2)
    with col3:
        st.metric("🏢 Onsite", onsite_jobs)
    with col4:
        st.metric("🔄 Hybrid", hybrid_jobs)
    
    st.sidebar.markdown("---")
    
    # ========== FILTERS (BOTTOM) ==========
    st.sidebar.subheader("🔧 Filters")
    
    # Score filter
    if 'Score' in df.columns or 'score' in df.columns:
        min_score = st.sidebar.slider("Minimum AI Score", 0, 100, 0, 10)
    else:
        min_score = 0
    
    # Work mode filter
    work_mode_filter = st.sidebar.multiselect(
        "Work Mode",
        ["Remote", "Onsite", "Hybrid"],
        default=["Remote", "Onsite", "Hybrid"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"""
    <p style="color: #888; font-size: 0.9em; text-align: center;">
        Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </p>
    """, unsafe_allow_html=True)
    
    # Apply filters
    filtered_df = df.copy()
    
    # Apply score filter
    if min_score > 0 and ('Score' in df.columns or 'score' in df.columns):
        score_col = 'Score' if 'Score' in df.columns else 'score'
        filtered_df = filtered_df[pd.to_numeric(filtered_df[score_col], errors='coerce') >= min_score]
    
    # Apply work mode filter
    if 'work_mode' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['work_mode'].isin(work_mode_filter)]
    elif 'Mode' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Mode'].isin(work_mode_filter)]
    
    # ========== PAGE: AI RECOMMENDATIONS (ALL) ==========
    # BUG FIX: Legacy block disabled to prevent fallthrough when selectbox state is desynced
    if False and page == "🌟 All AI Recommendations":
        st.markdown("## 🤖 AI-Powered Recommendations")
        st.markdown("*Top jobs based on AI matching scores across all categories*")
        
        # Sort by score
        if 'Score' in filtered_df.columns or 'score' in filtered_df.columns:
            score_col = 'Score' if 'Score' in filtered_df.columns else 'score'
            filtered_df[score_col] = pd.to_numeric(filtered_df[score_col], errors='coerce')
            recommended_jobs = filtered_df.sort_values(score_col, ascending=False).head(50)
        else:
            recommended_jobs = filtered_df.head(50)
        
        if recommended_jobs.empty:
            st.info("📭 No jobs to show yet!")
            st.markdown("""
            ### 🚀 Get Started:
            1. Click **"⚡ Run System Recommendation"** in the sidebar
            2. Wait 2-3 minutes while AI analyzes your resume and finds perfect jobs
            3. Top 20 jobs (5 per category) will appear here!
            
            **What happens when you click Run:**
            - AI analyzes your master resume
            - Scrapes 200-300 jobs from all platforms
            - Scores each job against your profile
            - Saves top 5 per category to Google Sheets
            - Shows them here in the dashboard
            """)
        else:
            st.markdown(f"### 🌟 Found {len(recommended_jobs)} recommended jobs")
            
            for idx, job in recommended_jobs.iterrows():
                render_job_card(job, idx)
    
    # ========== PAGE: MANUAL SEARCH ==========
    elif page == "🔍 Manual Search":
        st.markdown("## 🔍 Manual Job Search")
        st.markdown("*Search for fresh jobs using natural language*")
        
        # Natural language search bar
        st.markdown("### 💬 What are you looking for?")
        query = st.text_area(
            "Describe the job you want",
            placeholder="e.g., Looking for tech jobs as fresher\nAI jobs for 1 year experience\nPython developer remote jobs",
            height=100,
            help="Use plain language to describe what you're looking for"
        )
        
        # Filters in columns
        st.markdown("### 🎯 Filters (Optional)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Country selection
            country = st.selectbox(
                "🌍 Country",
                ["All Countries", "India", "USA", "Canada", "Australia", "Singapore", "Malaysia", "Europe"],
                help="Select a specific country or leave as 'All Countries'"
            )
        
        with col2:
            # Location selection (only for India)
            location = None
            if country == "India":
                location = st.selectbox(
                    "📍 City (India)",
                    ["All Cities", "Bangalore", "Hyderabad", "Gurgaon", "Noida", 
                     "Mumbai", "Pune", "Chennai", "Kolkata", "Ahmedabad", "Delhi"]
                )
                if location == "All Cities":
                    location = None
            else:
                st.info("Select India to choose specific cities")
        
        with col3:
            # Work mode selection
            work_mode = st.multiselect(
                "🏠 Work Mode",
                ["Remote", "Hybrid", "Onsite"],
                default=["Remote", "Hybrid", "Onsite"],
                help="Select one or more work modes"
            )
        
        # AI Role Suggestions with Reasoning
        st.markdown("### 💡 AI-Powered Role Suggestions")
        
        with st.expander("🤖 Click to see personalized role recommendations based on your resume", expanded=False):
            try:
                # Load resume and get AI suggestions
                script_dir = os.path.dirname(os.path.abspath(__file__))
                resume_path = os.path.join(os.path.dirname(script_dir), 'Assets', 'master resume.txt')
                
                if os.path.exists(resume_path):
                    with open(resume_path, 'r', encoding='utf-8') as f:
                        resume_text = f.read()
                    
                    # Get AI role suggestions (cached to avoid repeated API calls)
                    if 'ai_role_suggestions' not in st.session_state:
                        with st.spinner("🤖 Analyzing your resume for best role matches..."):
                            from openai import OpenAI
                            import json
                            
                            # Load config
                            config_file = os.path.join(script_dir, 'ai_config.json')
                            with open(config_file, 'r') as f:
                                config = json.load(f)
                            
                            client = OpenAI(
                                base_url="https://openrouter.ai/api/v1",
                                api_key=config['openrouter_key']
                            )
                            
                            prompt = f"""Analyze this resume and suggest 5 best job roles with reasoning.

Resume:
{resume_text[:1500]}

Return ONLY a JSON array:
[
    {{"role": "Role Name", "reason": "Why this role fits (1 sentence)"}},
    ...
]
"""
                            
                            response = client.chat.completions.create(
                                model=config['model'],
                                messages=[
                                    {"role": "system", "content": "You are a career advisor."},
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
                            
                            suggestions = json.loads(ai_response)
                            st.session_state.ai_role_suggestions = suggestions
                    
                    # Display suggestions
                    suggestions = st.session_state.ai_role_suggestions
                    
                    for idx, suggestion in enumerate(suggestions):
                        role = suggestion.get('role', 'Unknown Role')
                        reason = suggestion.get('reason', 'No reason provided')
                        
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"**{idx+1}. {role}**")
                            st.caption(f"💡 {reason}")
                        
                        with col2:
                            if st.button(f"Search", key=f"ai_role_{idx}", use_container_width=True):
                                query = f"Looking for {role} positions"
                                st.session_state.manual_search_query = query
                                st.rerun()
                        
                        if idx < len(suggestions) - 1:
                            st.markdown("---")
                    
                else:
                    st.warning("Master resume not found. Using generic suggestions.")
                    # Fallback to generic suggestions
                    generic_roles = [
                        "Software Engineer", "Full Stack Developer", "AI/ML Engineer",
                        "Data Scientist", "Python Developer"
                    ]
                    for role in generic_roles:
                        if st.button(f"🎯 {role}", key=f"gen_role_{role}", use_container_width=True):
                            query = f"Looking for {role} positions"
                            st.rerun()
                    
            except Exception as e:
                st.error(f"Error getting AI suggestions: {e}")
                # Fallback to generic
                st.info("Using generic role suggestions")
                generic_roles = [
                    "Software Engineer", "Full Stack Developer", "AI/ML Engineer",
                    "Data Scientist", "Python Developer"
                ]
                for role in generic_roles:
                    if st.button(f"🎯 {role}", key=f"fallback_{role}", use_container_width=True):
                        query = f"Looking for {role} positions"
                        st.rerun()
        
        # Search button
        st.markdown("---")
        
        col_search, col_clear = st.columns([3, 1])
        
        with col_search:
            search_button = st.button("🚀 Search Jobs", type="primary", use_container_width=True)
        
        with col_clear:
            if st.button("🔄 Clear", use_container_width=True):
                st.session_state.manual_search_results = None
                st.rerun()
        
        # Perform search
        if search_button and query:
            with st.spinner("🔍 Searching for jobs... This may take 30-60 seconds..."):
                try:
                    # Import manual search module
                    from manual_search import scrape_jobs_by_query
                    
                    # Prepare parameters
                    search_country = None if country == "All Countries" else country
                    
                    # Scrape jobs
                    results_df = scrape_jobs_by_query(
                        query=query,
                        country=search_country,
                        location=location,
                        work_mode=work_mode if work_mode else None,
                        results_wanted=50
                    )
                    
                    # Store in session state
                    st.session_state.manual_search_results = results_df
                    
                except Exception as e:
                    st.error(f"❌ Error during search: {e}")
                    st.session_state.manual_search_results = None
        
        # Display results
        if 'manual_search_results' in st.session_state and st.session_state.manual_search_results is not None:
            results_df = st.session_state.manual_search_results
            
            if results_df.empty:
                st.warning("😕 No jobs found matching your criteria. Try adjusting your search!")
            else:
                st.success(f"✅ Found {len(results_df)} fresh jobs!")
                
                # Sorting options
                st.markdown("### 📊 Sort Results")
                sort_option = st.selectbox(
                    "Sort by",
                    ["Most Recent", "Company (A-Z)", "Location"]
                )
                
                # Apply sorting
                if sort_option == "Most Recent" and 'posted_date' in results_df.columns:
                    results_df = results_df.sort_values('posted_date', ascending=False)
                elif sort_option == "Company (A-Z)" and 'company' in results_df.columns:
                    results_df = results_df.sort_values('company')
                elif sort_option == "Location" and 'location' in results_df.columns:
                    results_df = results_df.sort_values('location')
                
                st.markdown("---")
                st.info("💡 Click 'Apply' on any job to save it to your Applied_Jobs sheet")
                st.markdown("---")
                
                # Display job cards
                for idx, job in results_df.iterrows():
                    render_job_card(job, idx)
        elif query and not search_button:
            st.info("👆 Click 'Search Jobs' to find opportunities!")
    
    # ========== CATEGORY PAGES ==========
    elif "All AI Recommendations" in page:
        st.markdown("## 🌟 All Recommended Jobs")
        st.markdown("*Top AI-matched jobs across all categories*")
        display_category_jobs(filtered_df, "All Jobs")

    elif "Direct Portals" in page:
        st.markdown("## 🌟 Direct Portals (ATS & Big Tech)")
        st.markdown("*Jobs from Greenhouse, Lever, Google, Microsoft, etc.*")
        display_category_jobs(filtered_df, "Direct Portals")
    
    elif "International Remote" in page:
        st.markdown("## 🌍 International Remote Jobs")
        st.markdown("*Remote jobs from around the world*")
        display_category_jobs(filtered_df, "International Remote")
    
    elif "Indian Remote" in page:
        st.markdown("## 🇮🇳 Indian Remote Jobs")
        st.markdown("*Remote opportunities in India*")
        display_category_jobs(filtered_df, "Indian Remote")
    
    elif "Indian Onsite" in page:
        st.markdown("## 🏢 Indian Onsite Jobs")
        st.markdown("*Onsite/Hybrid opportunities in India*")
        display_category_jobs(filtered_df, "Indian Onsite")
    
    elif "Career Portals" in page:
        st.markdown("## 💼 Career Portals")
        st.markdown("*Jobs from company career pages*")
        display_category_jobs(filtered_df, "Career Portals")
    
    # ========== PAGE: ALL JOBS ==========
    elif page == "📋 All Jobs":
        st.markdown("## 📋 All Jobs")
        st.markdown("*Complete job listing with search*")
        
        # Search filters
        col1, col2 = st.columns([2, 2])
        
        with col1:
            role_search = st.text_input("🎯 Search by Role", placeholder="e.g., Python Developer, AI Engineer")
        
        with col2:
            location_search = st.text_input("📍 Search by Location", placeholder="e.g., Remote, USA, India")
        
        st.markdown("---")
        
        # Apply search filters
        search_results = filter_jobs(filtered_df, role_search, location_search, False)
        
        # Display results
        if search_results.empty:
            st.warning("No jobs match your search criteria. Try different filters!")
        else:
            st.markdown(f"### Found {len(search_results)} jobs")
            
            # Sort options
            sort_by = st.selectbox(
                "Sort by",
                ["AI Score (High first)", "Date (Recent first)", "Company (A-Z)"]
            )
            
            # Apply sorting
            if sort_by == "AI Score (High first)" and ('Score' in search_results.columns or 'score' in search_results.columns):
                score_col = 'Score' if 'Score' in search_results.columns else 'score'
                search_results[score_col] = pd.to_numeric(search_results[score_col], errors='coerce')
                search_results = search_results.sort_values(score_col, ascending=False, na_position='last')
            elif sort_by == "Date (Recent first)" and 'posted_date' in search_results.columns:
                search_results = search_results.sort_values('posted_date', ascending=False)
            elif sort_by == "Company (A-Z)" and 'company' in search_results.columns:
                search_results = search_results.sort_values('company')
            
            for idx, job in search_results.iterrows():
                render_job_card(job, idx)



if __name__ == "__main__":
    main()

