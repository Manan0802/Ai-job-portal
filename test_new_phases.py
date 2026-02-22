import sys
import os

from scrapper.interview_war_room import InterviewWarRoom
from scrapper.big_tech_scraper import BigTechScraper
from scrapper.alert_bot import AlertBot
from scrapper.resume_reader import get_master_resume

def main():
    print("=" * 60)
    print("Testing Phase A: Interview War Room")
    try:
        resume = get_master_resume()
        war_room = InterviewWarRoom(config_path="scrapper/ai_config.json")
        content = war_room.generate_cheat_sheet("Google", "AI Engineer", resume)
        pdf_path = war_room.create_pdf(content, "Google", "AI Engineer")
        if pdf_path:
            print(f"✅ Cheat sheet PDF created successfully at: {pdf_path}")
        else:
            print("❌ Cheat sheet generation failed.")
    except Exception as e:
        print(f"❌ Interview War Room Test Error: {e}")

    print("\n" + "=" * 60)
    print("Testing Phase B: Big Tech Scraper")
    try:
        scraper = BigTechScraper(config_path="scrapper/ai_config.json")
        jobs = scraper.scrape_big_tech("AI Engineer", "USA")
        if jobs:
            print(f"✅ Found {len(jobs)} direct Big Tech jobs.")
            print(f"   First Result: {jobs[0]['title']} at {jobs[0]['company']}")
        else:
            print("❌ Big Tech Scraper returned no results.")
    except Exception as e:
        print(f"❌ Big Tech Scraper Test Error: {e}")

    print("\n" + "=" * 60)
    print("Testing Phase C: Telegram Alert Bot")
    try:
        bot = AlertBot(config_path="scrapper/ai_config.json")
        bot.send_high_score_alert("Software Developer", "Apple", 98, "https://apple.com/jobs/123")
        print("✅ Telegram script triggered successfully.")
    except Exception as e:
        print(f"❌ Telegram Bot Test Error: {e}")

if __name__ == "__main__":
    main()
