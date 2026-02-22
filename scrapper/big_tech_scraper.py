import json
import os
import requests

try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

class BigTechScraper:
    def __init__(self, config_path=None):
        if config_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'ai_config.json')
            
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.serp_api_key = self.config.get('serp_api_key', '')

    def scrape_big_tech(self, search_term="Software Engineer", location="Remote"):
        """Uses SerpAPI's Google Jobs engine to aggregate Direct Big Tech roles."""
        print(f"==================================================")
        print(f"🚀 BIG TECH SCRAPER - SERPAPI DIRECT AGGREGATOR")
        print(f"Searching for '{search_term}' in '{location}'")
        print(f"==================================================")

        jobs_list = []

        if not GoogleSearch or not self.serp_api_key:
            print("⚠️ SerpAPI key not found in config. Please set 'serp_api_key'.")
            return jobs_list

        params = {
            "engine": "google_jobs",
            "q": search_term + " Google | Microsoft | Apple | Amazon | Meta | Netflix",
            "location": location,
            "api_key": self.serp_api_key,
            "hl": "en",
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            jobs_results = results.get('jobs_results', [])
            
            for job in jobs_results:
                title = job.get('title', 'Unknown Title')
                company = job.get('company_name', 'Unknown Company')
                loc = job.get('location', 'Remote')
                # Many Google Jobs results return related links (Apply via X vs direct)
                related_links = job.get('apply_options', [])
                job_url = related_links[0].get('link') if related_links else ''
                desc = job.get('description', '')[:500]

                jobs_list.append({
                    'title': title,
                    'company': company,
                    'location': loc,
                    'job_url': job_url,
                    'description': desc + "...",
                    'source': "Direct: " + company,
                    'posted_date': job.get('detected_extensions', {}).get('posted_at', 'Recently')
                })
            
            print(f"   ✓ Extracted {len(jobs_list)} direct Big Tech jobs via SerpAPI")
        except Exception as e:
            print(f"   ⚠️ Could not fetch from SerpAPI: {e}")

        return jobs_list

if __name__ == "__main__":
    scraper = BigTechScraper()
    jobs = scraper.scrape_big_tech("AI Engineer Intern", "India")
    if jobs:
        print("\n".join([f"{j['company']} - {j['title']} ({j['source']})" for j in jobs[:5]]))
