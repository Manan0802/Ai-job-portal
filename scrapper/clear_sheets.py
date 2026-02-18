"""
Clear all jobs from Google Sheets (keep headers)
Run this to start fresh with correct routing
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

def clear_all_sheets():
    """Clear all job data from Google Sheets (keep headers only)"""
    
    # Connect to Google Sheets
    script_dir = os.path.dirname(os.path.abspath(__file__))
    creds_file = os.path.join(script_dir, 'google_key.json')
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
    client = gspread.authorize(creds)
    
    # Open the sheet
    sheet = client.open('Ai Job Tracker')
    
    # List of sheets to clear
    sheet_names = [
        'Direct_Portals',
        'International_Remote',
        'Indian_Remote',
        'Indian_Onsite',
        'Career_Portals'
    ]
    
    print("Clearing all job data from Google Sheets...")
    print("(Headers will be kept)")
    print()
    
    for sheet_name in sheet_names:
        try:
            worksheet = sheet.worksheet(sheet_name)
            
            # Get all data
            all_data = worksheet.get_all_values()
            
            if len(all_data) > 1:  # If there's more than just headers
                # Keep only the header row (first row)
                worksheet.resize(rows=1)
                print(f"[OK] Cleared {sheet_name} - Removed {len(all_data) - 1} jobs")
            else:
                print(f"[SKIP] {sheet_name} - Already empty")
                
        except Exception as e:
            print(f"[ERROR] {sheet_name}: {e}")
    
    print()
    print("="*70)
    print("[SUCCESS] All sheets cleared!")
    print("="*70)
    print()
    print("Next steps:")
    print("1. Go to dashboard")
    print("2. Click 'Run System Recommendation'")
    print("3. Jobs will be routed correctly")

if __name__ == "__main__":
    confirm = input("This will DELETE all jobs from Google Sheets. Continue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        clear_all_sheets()
    else:
        print("Cancelled.")
