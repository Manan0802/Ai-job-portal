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
from resume_tailor import ResumeTailor
from networking_agent import NetworkingAgent
import json

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
    /* Global Font & Reset */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* Main background - Deep Cyberpunk/GenZ Vibe */
    .stApp {
        background: #09090b;
        background-image: 
            radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
            radial-gradient(at 50% 0%, hsla(225,39%,30%,1) 0, transparent 50%), 
            radial-gradient(at 100% 0%, hsla(339,49%,30%,1) 0, transparent 50%);
    }
    
    /* Headers with Gradient Text */
    h1, h2, h3 {
        background: linear-gradient(90deg, #FF3BFF 0%, #ECBFBF 50%, #5C24FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    
    /* Modern Cards (Glassmorphism) */
    .job-card {
        background: rgba(24, 24, 27, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-right: 1px solid rgba(255, 255, 255, 0.04);
        border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        border-radius: 24px;
        padding: 24px;
        backdrop-filter: blur(12px);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    .job-card:hover {
        transform: translateY(-4px) scale(1.01);
        background: rgba(39, 39, 42, 0.8);
        border-color: rgba(92, 36, 255, 0.5);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04), 0 0 20px rgba(92, 36, 255, 0.2);
    }
    
    /* Buttons - Neo-Brutalism/Pop */
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        border: none;
        transition: all 0.2s;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 14px;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
        color: white;
    }
    
    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        color: #e4e4e7;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
    }

    /* Badges */
    .metric-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 16px;
        text-align: center;
    }
    
    /* Input Fields */
    .stTextInput > div > div > input, .stSelectbox > div > div > select, .stTextArea > div > div > textarea {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        color: white;
        transition: border-color 0.2s;
    }
    
    .stTextInput > div > div > input:focus, .stSelectbox > div > div > select:focus {
        border-color: #a855f7;
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

@st.cache_data(ttl=60)
def load_my_network():
    """
    Load network connections from My_Network sheet
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_file = os.path.join(script_dir, 'google_key.json')
        if not os.path.exists(credentials_file): return pd.DataFrame()
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        sheet = client.open('Ai Job Tracker')
        
        try:
            worksheet = sheet.worksheet('My_Network')
            data = worksheet.get_all_records()
            return pd.DataFrame(data) if data else pd.DataFrame()
        except:
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
            str(job.get('title', 'N/A')),
            str(job.get('company', 'N/A')),
            str(job.get('location', 'N/A')),
            str(job.get('work_mode', job.get('Mode', 'Unknown'))),
            str(job.get('job_url', '')),
            str(job.get('source', 'Unknown')),
            str(job.get('salary_range', '')),
            str(job.get('posted_date', '')),
            str(job.get('Score', job.get('score', ''))),
            str(job.get('Summary', job.get('summary', ''))),
            'Applied'  # Status
        ]
        
        # Append the row
        worksheet.append_row(row_data)
        
        # Clear cache so the applied jobs list updates
        load_applied_jobs.clear()
        
        return True, "Job added successfully!"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def add_to_network(person, company, linkedin_url):
    """
    Save a connection to My_Network Google Sheet
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_file = os.path.join(script_dir, 'google_key.json')
        if not os.path.exists(credentials_file): return False, "No credentials"
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        sheet = client.open('Ai Job Tracker')
        
        try:
            worksheet = sheet.worksheet('My_Network')
        except:
            worksheet = sheet.add_worksheet(title='My_Network', rows=1000, cols=5)
            worksheet.append_row(['Name', 'Headline', 'Company', 'LinkedIn', 'Date_Added'])
            
        today = datetime.now().strftime('%Y-%m-%d')
        worksheet.append_row([str(person.get('name', '')), str(person.get('headline', '')), str(company), str(linkedin_url), today])
        return True, "Added to My Network"
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
    # Header with animated gradient
    st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="font-size: 4em; margin-bottom: 0;">
                🚀 CAREER <span style="color: #a855f7">COMMAND</span> CENTER
            </h1>
            <p style="color: #a1a1aa; font-size: 1.2em; margin-top: 5px; margin-bottom: 40px; letter-spacing: 2px;">
                AI-POWERED • AGENTIC • AUTOMATED
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ========== HORIZONTAL NAVIGATION ==========
    # Using Tabs for cleaner horizontal layout
    # tab_names = ["🤖 AI Headhunter", "🔍 Manual Hunt", "📝 Resume Tailor", "🤝 Networking God"]
    # tab1, tab2, tab3, tab4 = st.tabs(tab_names)
    
    # Custom CSS for tabs is already applied via style injection
    
    # Use option_menu-like styling with st.tabs
    tab1, tab2, tab_bigtech, tab3, tab4, tab_interview = st.tabs([
        "🤖 AI Headhunter", 
        "🔍 Manual Hunt", 
        "🏢 FAANG Scraper", 
        "📝 Resume Tailor", 
        "🤝 Networking God", 
        "🧠 Interview War Room"
    ])

    # Load data
    df = load_data()
    
    # Clear any previous error states if we have data
    if not df.empty and 'show_error' in st.session_state:
        del st.session_state['show_error']
        
    # Stats Bar (Horizontal) - Always visible
    with st.container():
        st.markdown("### 📊 Live Intel")
        c1, c2, c3, c4 = st.columns(4)
        total = len(df) if not df.empty else 0
        
        # Calculate high match safely
        high_match = 0
        if not df.empty and ('Score' in df.columns or 'score' in df.columns):
             score_col = 'Score' if 'Score' in df.columns else 'score'
             high_match = len(df[pd.to_numeric(df[score_col], errors='coerce') >= 80])
             
        applied_count = len(load_applied_jobs())
        
        c1.metric("Total Jobs", total, delta="Live")
        c2.metric("High Match", high_match, delta="Top 10%")
        c3.metric("Applied", applied_count, delta="Tracked")
        c4.metric("Status", "Online", delta_color="normal")
        st.markdown("---")

    # ========== TAB 1: AI HEADHUNTER ==========
    with tab1:
        st.subheader("🎯 AI Job Recommendations")
        
        col_act, col_filt = st.columns([1, 2])
        
        with col_act:
            with st.form("scan_form"):
                st.markdown("### ⚙️ Scan Settings")
                scan_category = st.selectbox(
                    "Target Category",
                    ["Direct_Portals", "International_Remote", "Indian_Remote", "Indian_Onsite", "Career_Portals"]
                )
                scan_limit = st.slider("Jobs to Fetch", 5, 60, 20)
                
                if st.form_submit_button("⚡ Run Targeted Scan", type="primary", use_container_width=True):
                    # Clear any previous errors
                    if 'show_error' in st.session_state:
                        del st.session_state['show_error']
                    
                    with st.spinner(f"🤖 AI Agent is scraping {scan_category} ({scan_limit} jobs)..."):
                        try:
                            import subprocess
                            import sys
                            
                            # Run system recommendation script
                            script_dir = os.path.dirname(os.path.abspath(__file__))
                            rec_script = os.path.join(script_dir, 'system_recommendation.py')
                            
                            # Pass arguments
                            cmd = [sys.executable, rec_script, "--category", scan_category, "--limit", str(scan_limit)]
                            
                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                cwd=script_dir
                            )
                            
                            if result.returncode == 0:
                                st.success("✅ Scan Complete!")
                                st.toast("Jobs added to Google Sheet!", icon="📊")
                                st.balloons()
                                time.sleep(1)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("❌ Error running recommendation engine")
                                with st.expander("Error Details"):
                                    st.code(result.stderr)
                                    st.code(result.stdout)
                                    
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

        with col_filt:
            category_filter = st.selectbox(
                "📂 Filter by Category",
                [
                    "All AI Recommendations", 
                    "Direct Portals", 
                    "International Remote", 
                    "Indian Remote", 
                    "Indian Onsite", 
                    "Career Portals"
                ],
                label_visibility="collapsed"
            )

        # Show Jobs
        if df.empty:
            st.info("👋 No jobs found yet. Click 'Run Full Scan' to start your job hunt!")
        else:
            if category_filter == "All AI Recommendations":
                display_category_jobs(df, "All Jobs")
            else:
                display_category_jobs(df, category_filter)
                
        st.markdown("---")
        st.markdown("### 📱 Notifications")
        if st.button("🔔 Test Telegram Alert"):
            try:
                from scrapper.alert_bot import AlertBot
            except ImportError:
                from alert_bot import AlertBot
            bot = AlertBot()
            if bot.telegram_token and bot.telegram_chat_id:
                bot.send_high_score_alert("Test Role", "Test Company", 99, "https://example.com")
                st.success("Test alert sent to Telegram! Check your phone.")
            else:
                st.error("Missing token or chat_id in ai_config.json")
            
    # ========== TAB 2: MANUAL SEARCH ==========
    with tab2:
        st.markdown("## 🔍 Manual Job Search")
        st.markdown("*Search for fresh jobs using natural language*")
        
        # Natural language search bar
        st.markdown("### 💬 What are you looking for?")
        query = st.text_area(
            "Describe the job you want",
            placeholder="e.g., Looking for tech jobs as fresher\nAI jobs for 1 year experience\nPython developer remote jobs",
            height=100,
            label_visibility="collapsed"
        )
        
        # Filters in columns
        st.markdown("### 🎯 Filters (Optional)")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            country = st.selectbox(
                "🌍 Country",
                ["All Countries", "India", "USA", "Canada", "Australia", "Singapore", "Malaysia", "Europe"]
            )
        
        with col2:
            location = None
            if country == "India":
                location = st.selectbox(
                    "📍 City (India)",
                    ["All Cities", "Bangalore", "Hyderabad", "Gurgaon", "Noida", 
                     "Mumbai", "Pune", "Chennai", "Kolkata", "Ahmedabad", "Delhi"]
                )
                if location == "All Cities":
                    location = None
        
        with col3:
            work_mode = st.multiselect(
                "🏠 Work Mode",
                ["Remote", "Hybrid", "Onsite"],
                default=["Remote", "Hybrid", "Onsite"]
            )

        st.markdown("---")
        
        if st.button("🚀 Search Jobs", type="primary", use_container_width=True):
            if query:
                with st.spinner("🔍 Searching for jobs..."):
                    try:
                        from manual_search import scrape_jobs_by_query
                        search_country = None if country == "All Countries" else country
                        
                        results_df = scrape_jobs_by_query(
                            query=query,
                            country=search_country,
                            location=location,
                            work_mode=work_mode,
                            results_wanted=50
                        )
                        st.session_state.manual_search_results = results_df
                    except Exception as e:
                        st.error(f"Search failed: {e}")

        # Display results
        if 'manual_search_results' in st.session_state and st.session_state.manual_search_results is not None:
             results_df = st.session_state.manual_search_results
             if results_df.empty:
                 st.warning("No jobs found.")
             else:
                 st.success(f"Found {len(results_df)} jobs!")
                 
                 # Fix for NaN values which are JSON-unfriendly for st.dataframe or subsequent processing
                 results_df = results_df.fillna("") 
                 st.session_state.manual_search_results = results_df # Update session state with clean DF
                 
                 # Render each job as a card so user can Apply
                 for idx, job in results_df.iterrows():
                     render_job_card(job, idx)

    # ========== TAB 3: RESUME TAILOR ==========
    with tab3:
        st.markdown("## 📝 Resume Tailor")
        st.markdown("*Adapt your resume for specific roles*")
        
        resume_tailor = ResumeTailor()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 1️⃣ Job Details")
            candidate_name = st.text_input("Your Name", "Manan Kumar")
            job_description = st.text_area("Paste Job Description", height=200)
            company_name = st.text_input("Company Name")
            target_role = st.text_input("Target Role", "Software Engineer")
            
        with col2:
             st.markdown("### 2️⃣ Actions")
             if st.button("🚀 Analyze & Tailor", type="primary", use_container_width=True):
                 if job_description:
                     with st.spinner("Analyzing & Parsing Master Resume..."):
                         # Load resume (PDF or TXT)
                         try:
                             from scrapper.resume_reader import get_master_resume
                             resume_text = get_master_resume()
                             
                             if resume_text:
                                 # 1. Analyze Gap
                                 analysis = resume_tailor.analyze_gap(resume_text, job_description)
                                 
                                 # 2. Parse Full Resume for PDF Generation
                                 parsed_data = resume_tailor.parse_resume(resume_text)
                                 
                                 # Store in session
                                 st.session_state.analysis_result = analysis
                                 st.session_state.parsed_resume = parsed_data
                                 
                                 st.session_state.tailor_company = company_name
                                 st.session_state.tailor_role = target_role
                                 st.session_state.tailor_jd = job_description
                                 st.session_state.tailor_resume_text = resume_text
                             else:
                                 st.error("Master resume (PDF or TXT) not found in Assets/!")
                         except Exception as e:
                             st.error(f"Error: {e}")
        
        if 'analysis_result' in st.session_state:
            res = st.session_state.analysis_result
            st.divider()
            
            # Gap Analysis
            st.subheader("🔍 Gap Analysis")
            missing = res.get('missing_keywords', [])
            if missing:
                st.write("**Missing Keywords identified:**")
                st.markdown(" ".join([f"`{k}`" for k in missing]))
            else:
                st.success("✅ No major missing keywords found!")
                
            # Bullet Point Suggestions
            st.subheader("✍️ Suggested Improvements")
            suggestions = res.get('suggested_points', [])
            selected_points = []
            
            for i, point in enumerate(suggestions):
                with st.container():
                    col_chk, col_content = st.columns([0.1, 0.9])
                    with col_chk:
                        if st.checkbox("", key=f"chk_{i}", value=True):
                            selected_points.append(point['new'])
                    with col_content:
                        st.markdown(f"**Original:** {point.get('original', 'New Addition')}")
                        st.markdown(f"**✨ Suggestion:** {point['new']}")
                        st.caption(f"💡 *Reason: {point['reason']}*")
                        st.markdown("---")
            
            # Final Actions
            st.subheader("📄 Generate Assets")
            
            col_gen1, col_gen2 = st.columns(2)
            
            with col_gen1:
                if st.button("💾 Generate Tailored PDF", type="primary", use_container_width=True):
                    with st.spinner("Generating Professional PDF..."):
                        # Get parsed base data
                        final_resume_data = st.session_state.parsed_resume.copy()
                        
                        # Update with User Inputs
                        if candidate_name:
                            final_resume_data['name'] = candidate_name
                        
                        # Inject Tailored Points into the most relevant Experience (First one for now)
                        if selected_points and final_resume_data.get('experience'):
                            # Prepend tailored points to the latest experience
                            current_points = final_resume_data['experience'][0].get('points', [])
                            if isinstance(current_points, str): current_points = [current_points]
                            
                            # Add tailored points at the top
                            final_resume_data['experience'][0]['points'] = selected_points + current_points
                        
                        # Add missing skills
                        if missing and final_resume_data.get('skills'):
                             current_skills = final_resume_data.get('skills', [])
                             if isinstance(current_skills, str): 
                                 current_skills = [s.strip() for s in current_skills.split(',')]
                             
                             final_resume_data['skills'] = list(set(current_skills + missing))
                        
                        # Generate Filename: Name_Company_Role.pdf
                        safe_company = "".join(x for x in st.session_state.tailor_company if x.isalnum())
                        safe_role = "".join(x for x in st.session_state.tailor_role if x.isalnum())
                        pdf_filename = f"{candidate_name.split()[0]}_{safe_company}_{safe_role}.pdf"
                        
                        result_path = resume_tailor.create_pdf(final_resume_data, pdf_filename)
                        
                        if result_path and os.path.exists(result_path):
                            st.success(f"✅ PDF Generated: {pdf_filename}")
                            with open(result_path, "rb") as pdf_file:
                                st.download_button(
                                    label="Download Resume PDF",
                                    data=pdf_file,
                                    file_name=pdf_filename,
                                    mime="application/pdf"
                                )
                        else:
                            st.error("Failed to generate PDF.")
            
            with col_gen2:
                if st.button("✉️ Generate Cover Letter", use_container_width=True):
                    cl = resume_tailor.generate_cover_letter(
                        st.session_state.tailor_resume_text,
                        st.session_state.tailor_jd,
                        st.session_state.tailor_company
                    )
                    st.text_area("Cover Letter", cl, height=300)

    # ========== TAB 4: NETWORKING GOD ==========
    with tab4:
        st.markdown("## 🤝 Networking God")
        st.markdown("*Find recruiters & alumni instantly*")
        
        networking_agent = NetworkingAgent()
        
        net_tabs = st.tabs(["🔍 Search Contacts", "📖 My Network"])
        
        with net_tabs[0]:
            c1, c2 = st.columns([2, 1])
            with c1:
                target_company = st.text_input("Target Company", placeholder="e.g. Google, Microsoft")
            with c2:
                user_linkedin = st.text_input("Your LinkedIn", placeholder="linkedin.com/in/you")
                
            if st.button("find_people.exe", type="primary", use_container_width=True):
                if target_company:
                    st.session_state.net_company = target_company
                    st.session_state.net_results = {} # Reset results
                    
                    # Categories to search
                    categories = ["Recruiter", "Talent Acquisition", "Software Engineer", "Alumni"]
                    
                    with st.spinner("🕵️ Scouring LinkedIn for contacts across all categories..."):
                        progress_text = st.empty()
                        for cat in categories:
                            progress_text.text(f"Searching for {cat}s...")
                            results = networking_agent.find_potential_contacts(target_company, cat)
                            st.session_state.net_results[cat] = results
                        progress_text.empty()
                        
            if 'net_results' in st.session_state and st.session_state.net_results:
                st.markdown(f"### Results for {st.session_state.net_company}")
                
                # Create Tabs for each category
                cat_tabs = st.tabs(["Recruiters", "Talent Acquisition", "Software Engineers", "Alumni"])
                
                categories = ["Recruiter", "Talent Acquisition", "Software Engineer", "Alumni"]
                
                for idx, cat in enumerate(categories):
                    with cat_tabs[idx]:
                        results = st.session_state.net_results.get(cat, [])
                        if not results:
                            st.info(f"No {cat}s found.")
                        else:
                            # Scrollable container for each tab
                            with st.container(height=400):
                                for i, p in enumerate(results):
                                    key_suffix = f"{cat}_{i}"
                                    num = i + 1
                                    with st.expander(f"{num}. {p['name']} - {p['headline']}"):
                                        st.write(f"**Profile:** [LinkedIn Profile]({p['link']})")
                                        
                                        col_a, col_b = st.columns(2)
                                        
                                        with col_a:
                                            if st.button("👋 Connect Request", key=f"req_{key_suffix}"):
                                                # Include LinkedIn in signature if provided
                                                sender_name = f"Manan | {user_linkedin}" if user_linkedin else "Manan"
                                                msg = networking_agent.generate_connection_request(
                                                    sender_name, p['name'], st.session_state.net_company
                                                )
                                                st.text_area("Copy this:", msg, height=100, key=f"txt_req_{key_suffix}")
                                                
                                            if st.button("💾 Save to My Network", key=f"save_net_{key_suffix}"):
                                                success, msg = add_to_network(p, st.session_state.net_company, p['link'])
                                                if success:
                                                    load_my_network.clear()
                                                    st.success("✅ Saved to Google Sheet!")
                                                else:
                                                    st.error(msg)
                                                
                                        with col_b:
                                            if st.button("📧 Cold Email Draft", key=f"email_{key_suffix}"):
                                                msg = networking_agent.generate_cold_email(
                                                    "Resume Summary", p['name'], st.session_state.net_company, "Software Engineer"
                                                )
                                                st.text_area("Email Draft:", msg, height=200, key=f"txt_email_{key_suffix}")
                                                st.info("ℹ️ Copy this draft. Email addresses are private and cannot be scraped legally.")

        with net_tabs[1]:
            st.markdown("### 📖 My Saved Network")
            net_df = load_my_network()
            if net_df.empty:
                st.info("No connections saved yet.")
            else:
                st.dataframe(net_df, use_container_width=True)

    # ========== TAB BIG TECH: FAANG SCRAPER ==========
    with tab_bigtech:
        st.markdown("## 🏢 FAANG Scraper - Direct Aggregator")
        st.markdown("*Bypass job boards and query Big Tech APIs directly using Google Jobs*")
        
        col_bt1, col_bt2 = st.columns([1, 2])
        with col_bt1:
            bt_role = st.text_input("Target FAANG Role", "Software Engineer", key="bt_role")
            bt_location = st.text_input("Target FAANG Location", "Remote", key="bt_loc")
            
            if st.button("🚀 Search Big Tech", type="primary", use_container_width=True):
                with st.spinner("Querying FAANG Direct Portals..."):
                    try:
                        from scrapper.big_tech_scraper import BigTechScraper
                        bt_scraper = BigTechScraper()
                        st.session_state.bt_results = bt_scraper.scrape_big_tech(bt_role, bt_location)
                    except Exception as e:
                        st.error(f"Failed to scrape: {e}")
                        
        with col_bt2:
            if 'bt_results' in st.session_state and st.session_state.bt_results is not None:
                bt_res = st.session_state.bt_results
                if len(bt_res) == 0:
                    st.warning("No direct FAANG jobs found. Try adjusting role/location/SerpApi Key.")
                else:
                    st.success(f"Found {len(bt_res)} direct Big Tech jobs!")
                    for idx, job in enumerate(bt_res):
                        with st.expander(f"{job['company']} - {job['title']} 🏢"):
                            st.write(f"**Location:** {job['location']}")
                            st.write(f"**Posted:** {job['posted_date']}")
                            st.write(f"**Description:** {job['description']}")
                            st.markdown(f"🔗 [Apply Directly on {job['company']}]({job['job_url']})")

    # ========== TAB INTERVIEW: INTERVIEW WAR ROOM ==========
    with tab_interview:
        st.markdown("## 🧠 Interview War Room")
        st.markdown("*Instantly generate a custom Cheat Sheet for your upcoming interview*")
        
        col_iw1, col_iw2 = st.columns([1, 1])
        with col_iw1:
            st.markdown("### 1️⃣ Interview Details")
            iw_company = st.text_input("Company Name", "Google", key="iw_comp")
            iw_role = st.text_input("Role", "Software Engineer", key="iw_role")
            
            if st.button("⚔️ Generate Battle Plan (PDF)", type="primary", use_container_width=True):
                with st.spinner(f"Scouring Glassdoor/Reddit for {iw_company} {iw_role} questions..."):
                    try:
                        from scrapper.interview_war_room import InterviewWarRoom
                        from scrapper.resume_reader import get_master_resume
                        
                        resume = get_master_resume()
                        if resume.startswith("Resume not"):
                            st.error(resume)
                        else:
                            war_room = InterviewWarRoom()
                            content = war_room.generate_cheat_sheet(iw_company, iw_role, resume)
                            st.session_state.iw_content = content
                            
                            pdf_path = war_room.create_pdf(content, iw_company, iw_role)
                            if pdf_path:
                                st.session_state.iw_pdf_path = pdf_path
                                st.success("✅ Cheat Sheet successfully generated!")
                            else:
                                st.error("PDF generation failed.")
                    except Exception as e:
                        st.error(f"War Room Error: {e}")
                        
        with col_iw2:
            st.markdown("### 2️⃣ Your Cheat Sheet")
            if 'iw_content' in st.session_state:
                st.text_area("Live Preview", st.session_state.iw_content, height=300)
                
            if 'iw_pdf_path' in st.session_state and os.path.exists(st.session_state.iw_pdf_path):
                with open(st.session_state.iw_pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Download Cheat Sheet PDF",
                        data=pdf_file,
                        file_name=os.path.basename(st.session_state.iw_pdf_path),
                        mime="application/pdf",
                        use_container_width=True
                    )


if __name__ == "__main__":
    main()
