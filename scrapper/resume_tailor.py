
import json
import os
from openai import OpenAI
from fpdf import FPDF

class ResumeTailor:
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

    def analyze_gap(self, resume_text, job_description):
        """
        Analyze gaps between resume and job description
        Returns JSON with missing skills and suggested points
        """
        prompt = f"""
        Analyze this Resume against the Job Description (JD).
        
        RESUME:
        {resume_text[:2000]}
        
        JOB DESCRIPTION:
        {job_description[:2000]}
        
        Identify:
        1. **Missing Keywords**: Important skills/tools in JD but not in Resume.
        2. **Suggested Bullet Points**: 3-5 specific bullet points to ADD or MODIFY in the resume to better match the JD.
           - Focus on metrics, tools, and impact.
           - Map user's existing experience to JD keywords if possible.
        
        Return ONLY valid JSON:
        {{
            "missing_keywords": ["skill1", "skill2"],
            "suggested_points": [
                {{
                    "original": "Worked on backend",
                    "new": "Engineered scalable backend using [Missing Skill] to improve performance by 20%",
                    "reason": "JD emphasizes [Missing Skill] and performance optimization."
                }},
                ...
            ]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert ATS Resume Optimizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            return json.loads(content)
        except Exception as e:
            return {"error": str(e)}

    def generate_cover_letter(self, resume_text, job_description, company_name):
        """
        Generate a tailored cover letter
        """
        prompt = f"""
        Write a punchy, professional Cover Letter for {company_name}.
        
        RESUME:
        {resume_text[:2000]}
        
        JOB DESCRIPTION:
        {job_description[:2000]}
        
        Guidelines:
        - Hook the reader in the first sentence.
        - Map 2-3 key achievements from resume to JD requirements.
        - Show genuine enthusiasm for {company_name}.
        - Keep it under 250 words.
        - NO placeholders like [Your Name] - use "The Candidate".
        
        Return the cover letter text directly.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional career coach."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating cover letter: {str(e)}"

    def create_pdf(self, content_dict, filename):
        """
        Create a professional PDF resume using FPDF2
        content_dict: {'name': '...', 'email': '...', 'summary': '...', 'experience': [...], 'projects': [...], 'skills': '...'}
        """
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Helvetica", "B", 24)
        pdf.cell(0, 10, content_dict.get('name', 'Candidate Name'), new_x="LMARGIN", new_y="NEXT", align="C")
        
        pdf.set_font("Helvetica", "", 10)
        contact_info = f"{content_dict.get('email', '')} | {content_dict.get('phone', '')} | {content_dict.get('linkedin', '')}"
        pdf.cell(0, 5, contact_info, new_x="LMARGIN", new_y="NEXT", align="C")
        
        pdf.ln(5)
        
        # Sections
        sections = ['summary', 'experience', 'projects', 'education', 'skills']
        
        for section in sections:
            if section in content_dict and content_dict[section]:
                # Section Header
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(0, 8, section.upper(), new_x="LMARGIN", new_y="NEXT", fill=True)
                pdf.ln(2)
                
                # Content
                pdf.set_font("Helvetica", "", 10)
                
                if isinstance(content_dict[section], list):
                    for item in content_dict[section]:
                        # Item Title (e.g., Job Title, Project Name)
                        if 'title' in item:
                            pdf.set_font("Helvetica", "B", 10)
                            pdf.cell(0, 5, item['title'], new_x="LMARGIN", new_y="NEXT")
                        
                        # Subtitle (e.g., Company, Date)
                        if 'subtitle' in item:
                            pdf.set_font("Helvetica", "I", 9)
                            pdf.cell(0, 5, item['subtitle'], new_x="LMARGIN", new_y="NEXT")
                        
                        # Bullet points
                        pdf.set_font("Helvetica", "", 10)
                        if 'points' in item:
                            for point in item['points']:
                                pdf.multi_cell(0, 5, f"- {point}")
                        pdf.ln(2)
                else:
                    pdf.multi_cell(0, 5, content_dict[section])
                    pdf.ln(3)
                    
        try:
            pdf.output(filename)
            return filename
        except Exception as e:
            return None

