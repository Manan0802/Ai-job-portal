import os
import glob
try:
    import PyPDF2
    import pdfplumber
except ImportError:
    pass

def get_master_resume():
    """
    Reads the master resume from the Assets folder.
    Prioritizes .pdf files over .txt files.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(os.path.dirname(script_dir), 'Assets')
    
    if not os.path.exists(assets_dir):
        return "Assets folder not found."
        
    # Check for PDFs first
    pdf_files = glob.glob(os.path.join(assets_dir, '*.pdf'))
    if pdf_files:
        try:
            # Let's try PyPDF2 first
            with open(pdf_files[0], 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                if text.strip():
                    return text.strip()
        except Exception as e:
            try:
                # Fallback to pdfplumber
                with pdfplumber.open(pdf_files[0]) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                    if text.strip():
                        return text.strip()
            except Exception as e2:
                print(f"Error reading PDF: {e} | {e2}")
                pass # Fallback to txt

    # Fallback to TXT
    txt_files = glob.glob(os.path.join(assets_dir, '*.txt'))
    if txt_files:
        with open(txt_files[0], 'r', encoding='utf-8') as f:
            return f.read().strip()
            
    return "Resume not found in Assets folder. Please add a pdf or txt file."
