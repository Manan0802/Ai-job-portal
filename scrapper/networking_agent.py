
import json
import os
from openai import OpenAI
from serpapi import GoogleSearch

class NetworkingAgent:
    def __init__(self, config_path=None):
        if config_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'ai_config.json')
            
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.config['openrouter_key']
        )
        self.model = self.config['model']
        self.serp_api_key = self.config.get('serp_api_key', 'YOUR_SERP_API_KEY')  # Needs SerpApi

    def find_potential_contacts(self, company_name, role_title="Recruiter"):
        """
        Use Google Dorks to find LinkedIn profiles for a company + role
        Requires SerpApi key or simple scraping (SerpApi recommended for stability)
        """
        query = f'site:linkedin.com/in/ "{company_name}" "{role_title}"'
        
        try:
            params = {
                "q": query,
                "api_key": self.serp_api_key,
                "num": 20
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            contacts = []
            if "organic_results" in results:
                for result in results["organic_results"]:
                    contacts.append({
                        "name": result.get("title", "").split(" - ")[0],  # "Name - Title | Company" -> "Name"
                        "headline": result.get("snippet", ""),
                        "link": result.get("link", "")
                    })
            return contacts
        except Exception as e:
            return [{"name": "Error finding contacts", "headline": str(e), "link": "#"}]

    def generate_connection_request(self, candidate_name, recipient_name, company_name, shared_interest="Generic"):
        """
        Generate a personalized connection request (<300 chars)
        """
        prompt = f"""
        Write a LinkedIn Connection Request (strict 300 char limit).
        
        Sender: {candidate_name} (Aspiring Software Engineer)
        Recipient: {recipient_name} at {company_name}
        Context: Apply for a job at their company.
        Hook: Mention {shared_interest} or admiration for their work.
        
        Return ONLY the message text.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return f"Hi {recipient_name}, I'm {candidate_name}, an aspiring engineer. I admire {company_name}'s work and would love to connect!"

    def generate_cold_email(self, candidate_resume, recipient_name, company_name, job_role):
        """
        Generate a cold email body
        """
        prompt = f"""
        Write a short, value-driven Cold Email to a Recruiter/Hiring Manager.
        
        Recipient: {recipient_name} at {company_name}
        Sender Profile: {candidate_resume[:500]}
        Target Role: {job_role}
        
        Structure:
        1. Professional Subject Line
        2. Hook (specific to {company_name})
        3. Value Proposition (2 bullet points from resume)
        4. Call to Action (15 min chat)
        
        Return the full email text with Subject line first.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except:
            return "Error generating email."
