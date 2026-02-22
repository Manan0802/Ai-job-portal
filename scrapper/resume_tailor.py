
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
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            return json.loads(content)
        except Exception as e:
            # Fallback: Return original resume content wrapped in expected structure
            print(f"Error in gap analysis: {e}")
            return {
                "missing_keywords": ["Error analyzing resume - check quotas or connection"],
                "suggested_points": [
                    {
                        "original": "Resume Analysis Failed",
                        "new": "Could not analyze resume. Please try again or manually edit.",
                        "reason": f"System error: {str(e)[:50]}..."
                    }
                ]
            }

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
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating cover letter: {str(e)}"
            
    def parse_resume(self, resume_text):
        """
        Parse raw resume text into structured JSON using AI
        """
        prompt = f"""
        You are an expert resume parser. Convert the following resume text into a structured JSON format.
        
        RESUME TEXT:
        {resume_text[:4000]}
        
        Return ONLY valid JSON with this exact structure:
        {{
            "name": "Candidate Name",
            "email": "email@example.com",
            "phone": "123-456-7890",
            "linkedin": "linkedin.com/in/...",
            "summary": "Professional summary...",
            "skills": ["Skill1", "Skill2", ...],
            "experience": [
                {{
                    "title": "Role - Company",
                    "subtitle": "Date",
                    "points": ["Bullet 1", "Bullet 2"]
                }}
            ],
            "education": [
                {{
                    "title": "Degree - University",
                    "subtitle": "Year",
                    "points": []
                }}
            ],
            "projects": [
                {{
                    "title": "Project Name",
                    "subtitle": "Tech Stack",
                    "points": ["Description bullet"]
                }}
            ]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            content = response.choices[0].message.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"Error parsing resume: {e}")
            return {}

    def create_pdf(self, content_dict, filename="Tailored_Resume.pdf"):
        """
        Create a professional PDF using FPDF2
        """
        try:
            # Ensure Resumes directory exists
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Resumes')
            os.makedirs(output_dir, exist_ok=True)
            
            # Clean filename
            safe_filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '-', '_', '.')]).rstrip()
            if not safe_filename.endswith('.pdf'):
                safe_filename += '.pdf'
                
            full_path = os.path.join(output_dir, safe_filename)

            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            # --- HEADER ---
            pdf.set_font("Helvetica", "B", 24)
            pdf.cell(0, 10, content_dict.get('name', 'Candidate'), new_x="LMARGIN", new_y="NEXT", align="C")
            
            pdf.set_font("Helvetica", "", 10)
            contact = f"{content_dict.get('email', '')} | {content_dict.get('phone', '')} | {content_dict.get('linkedin', '')}".strip(' |')
            pdf.cell(0, 5, contact, new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.ln(5)
            
            # --- SECTIONS ---
            def section_header(label):
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_fill_color(230, 230, 230)
                pdf.cell(0, 6, label.upper(), fill=True, new_x="LMARGIN", new_y="NEXT", align="L")
                pdf.ln(2)

            # SUMMARY
            if content_dict.get('summary'):
                section_header("Summary")
                pdf.set_font("Helvetica", "", 10)
                pdf.multi_cell(0, 5, content_dict['summary'])
                pdf.ln(3)

            # SKILLS
            if content_dict.get('skills'):
                section_header("Technical Skills")
                pdf.set_font("Helvetica", "", 10)
                skills = ", ".join(content_dict['skills']) if isinstance(content_dict['skills'], list) else str(content_dict['skills'])
                pdf.multi_cell(0, 5, skills)
                pdf.ln(3)

            # EXPERIENCE
            if content_dict.get('experience'):
                section_header("Experience")
                for item in content_dict['experience']:
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.cell(0, 5, item.get('title', ''), new_x="LMARGIN", new_y="NEXT")
                    
                    if item.get('subtitle'):
                        pdf.set_font("Helvetica", "I", 9)
                        pdf.cell(0, 5, item['subtitle'], new_x="LMARGIN", new_y="NEXT")
                    
                    # Bullets
                    pdf.set_font("Helvetica", "", 10)
                    points = item.get('points', [])
                    if isinstance(points, str): points = [points]
                    
                    for point in points:
                        # Sanitize text
                        clean_point = point.encode('latin-1', 'replace').decode('latin-1')
                        pdf.set_x(15) 
                        pdf.multi_cell(0, 5, f"- {clean_point}")
                    pdf.ln(2)

            # PROJECTS
            if content_dict.get('projects'):
                section_header("Projects")
                for item in content_dict['projects']:
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.cell(0, 5, item.get('title', ''), new_x="LMARGIN", new_y="NEXT")
                    
                    if item.get('subtitle'):
                        pdf.set_font("Helvetica", "I", 9)
                        pdf.cell(0, 5, item['subtitle'], new_x="LMARGIN", new_y="NEXT")
                    
                    pdf.set_font("Helvetica", "", 10)
                    points = item.get('points', [])
                    if isinstance(points, str): points = [points]
                    for point in points:
                        clean_point = point.encode('latin-1', 'replace').decode('latin-1')
                        pdf.set_x(15)
                        pdf.multi_cell(0, 5, f"- {clean_point}")
                    pdf.ln(2)

            # EDUCATION
            if content_dict.get('education'):
                section_header("Education")
                for item in content_dict['education']:
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.cell(0, 5, item.get('title', ''), new_x="LMARGIN", new_y="NEXT")
                    if item.get('subtitle'):
                        pdf.set_font("Helvetica", "I", 9)
                        pdf.cell(0, 5, item['subtitle'], new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(2)

            pdf.output(full_path)
            return full_path
            
        except Exception as e:
            print(f"Error saving PDF: {e}")
            return None

