import json
import os
from openai import OpenAI
from fpdf import FPDF

try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

class InterviewWarRoom:
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
        self.serp_api_key = self.config.get('serp_api_key', '')

    def get_company_context(self, company_name, role_name):
        """Use SerpAPI to search for recent interview experiences."""
        if not GoogleSearch or not self.serp_api_key:
            return f"Company: {company_name}, Role: {role_name}"

        params = {
            "engine": "google",
            "q": f"site:glassdoor.com OR site:reddit.com '{company_name}' '{role_name}' interview questions",
            "api_key": self.serp_api_key,
            "num": 5
        }
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            snippets = [res.get('snippet', '') for res in results.get('organic_results', [])]
            return "\n".join(snippets)
        except Exception as e:
            print(f"SerpAPI Error: {e}")
            return ""

    def generate_cheat_sheet(self, company_name, role_name, resume_text):
        """Generate the interview cheat sheet content using AI."""
        context = self.get_company_context(company_name, role_name)
        
        prompt = f"""
        You are an elite Tech Interview Coach preparing a candidate for an interview at {company_name} for the {role_name} role.
        
        CANDIDATE RESUME:
        {resume_text[:2000]}
        
        INTERNET CONTEXT ABOUT THIS INTERVIEW:
        {context}
        
        Please provide a structured cheat sheet containing exactly:
        1. "Company Core Values & Mission" (Brief)
        2. "Top 5 Likely Technical Questions" (Specific to {role_name} and {company_name})
        3. "Top 3 Behavioral Questions" (And how to answer using their resume experience)
        4. "Questions to ask the interviewer" (2 insightful questions)

        Return the response as plain text formatted beautifully with Markdown-like bullet points (no asterisks if possible, use standard hyphens).
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a FAANG-level Interview Coach."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating cheat sheet: {e}"

    def create_pdf(self, content, company_name, role_name):
        """Saves the cheat sheet to a PDF."""
        # Ensure Output directory exists
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Assets')
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{company_name}_{role_name}_Interview_CheatSheet.pdf".replace(" ", "_")
        full_path = os.path.join(output_dir, filename)

        try:
            pdf = FPDF()
            pdf.add_page()
            
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, f"Interview War Room: {company_name}", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.set_font("Helvetica", "I", 12)
            pdf.cell(0, 10, f"Role: {role_name}", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.ln(5)
            
            pdf.set_font("Helvetica", "", 10)
            
            # encode to latin-1 to avoid fpdf errors
            clean_content = content.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 5, clean_content)
            
            pdf.output(full_path)
            return full_path
        except Exception as e:
            print(f"Error saving PDF: {e}")
            return None

if __name__ == "__main__":
    print("Testing Interview War Room...")
    try:
        from scrapper.resume_reader import get_master_resume
        resume = get_master_resume()
        war_room = InterviewWarRoom()
        print("Generating cheat sheet...")
        content = war_room.generate_cheat_sheet("Google", "AI Engineer", resume)
        print("Cheat sheet generated! Excerpt:\n", content[:200])
        pdf_path = war_room.create_pdf(content, "Google", "AI Engineer")
        print(f"Saved to: {pdf_path}")
    except Exception as e:
        print(f"Test failed: {e}")
