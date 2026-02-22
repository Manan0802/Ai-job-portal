import sys
import os

from scrapper.networking_agent import NetworkingAgent
from scrapper.resume_tailor import ResumeTailor

def main():
    print("=== Testing Resume Tailor with openrouter/free ===")
    try:
        os.makedirs("Resumes", exist_ok=True)
        rt = ResumeTailor(config_path='scrapper/ai_config.json')
        sample_resume = "Manan Kumar. Software Engineer. Skills: Python, C++, MERN. Education: DTU."
        sample_jd = "We are looking for a backend engineer familiar with Python, Node.js, and Cloud deployment (AWS)."
        
        print("1. Analyzing Resume vs JD...")
        analysis = rt.analyze_gap(sample_resume, sample_jd)
        print(f"Missing Keywords: {analysis.get('missing_keywords', [])}")
        if 'suggested_points' in analysis and analysis['suggested_points']:
            print(f"First Suggested Point: {analysis['suggested_points'][0]}")
            
        print("\n2. Generating Cover Letter...")
        cl = rt.generate_cover_letter(sample_resume, sample_jd, "CloudTech")
        print(f"Cover Letter Snippet:\n{cl[:200]}...")
        
        print("\n3. Creating PDF...")
        sample_data = {
            "name": "Manan Kumar",
            "email": "manan@example.com",
            "summary": "Software Engineer",
            "skills": ["Python", "C++", "MERN"],
            "experience": [{"title": "Software Engineer - Test", "points": ["Built cool stuff"]}]
        }
        pdf_path = rt.create_pdf(sample_data, "test.pdf")
        print(f"PDF generated at: {pdf_path}")
        print("Resume Tailor tests completed successfully!\n\n")
    except Exception as e:
        print(f"Resume Tailor test failed: {e}\n")

if __name__ == "__main__":
    main()
