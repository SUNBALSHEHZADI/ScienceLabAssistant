# app.py
import streamlit as st
import pytesseract
from PIL import Image
import io
import requests
import re
from fpdf import FPDF
from datetime import datetime
import os
import pdfplumber  # Alternative PDF library


API_KEY = os.environ.get('OPENROUTER_API_KEY')
if not API_KEY:
    st.error("""
    **API Key Not Configured!**
    
    Please add your API key to Hugging Face Spaces secrets:
    1. Go to your Space settings
    2. Select "Variables and secrets" 
    3. Add a secret named: `OPENROUTER_API_KEY`
    4. Set its value to your actual API key
    5. Redeploy the space
    """)
    st.stop()

# --- API Configuration ---
API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama3-70b-8192"

# Set Tesseract path for different environments
try:
    # For Windows
    if os.name == 'nt':
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    # For Linux
    elif 'tesseract' not in os.environ.get('PATH', ''):
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
except Exception as e:
    st.warning(f"Tesseract configuration issue: {str(e)}")

# Set page config
st.set_page_config(
    page_title="🔬 Science Lab Assistant", 
    layout="centered",
    page_icon="🔬",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .header {
        font-size: 36px;
        color: #2e86c1;
        text-align: center;
        padding: 20px;
    }
    .subheader {
        font-size: 24px;
        color: #28b463;
        border-bottom: 2px solid #f4d03f;
        padding-bottom: 10px;
        margin-top: 30px;
    }
    .stButton>button {
        background-color: #28b463 !important;
        color: white !important;
        border-radius: 8px;
        padding: 8px 20px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #239b56 !important;
        transform: scale(1.05);
    }
    .score-card {
        background: linear-gradient(135deg, #e8f8f5, #d1f2eb);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .highlight {
        background-color: #f9e79f;
        padding: 5px;
        border-radius: 5px;
        font-weight: bold;
    }
    .tip-box {
        background-color: #eafaf1;
        border-left: 5px solid #28b463;
        padding: 15px;
        margin: 15px 0;
        border-radius: 0 8px 8px 0;
    }
    .error-box {
        background-color: #fdecea;
        border-left: 5px solid #e74c3c;
        padding: 15px;
        margin: 15px 0;
        border-radius: 0 8px 8px 0;
    }
    .experiment-card {
        background: linear-gradient(135deg, #f0f7ff, #e1effe);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        transition: all 0.3s;
    }
    .experiment-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .concept-box {
        background-color: #ebf5fb;
        border-left: 5px solid #3498db;
        padding: 15px;
        margin: 15px 0;
        border-radius: 0 8px 8px 0;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e8f8f5, #d1f2eb) !important;
    }
    .footer {
        text-align: center;
        padding: 20px;
        color: #7f8c8d;
        font-size: 14px;
    }
    .ocr-warning {
        background-color: #fef9e7;
        border-left: 5px solid #f1c40f;
        padding: 15px;
        margin: 15px 0;
        border-radius: 0 8px 8px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.markdown('<p class="header">🔬 Science Lab Assistant</p>', unsafe_allow_html=True)

# Introduction
st.markdown("""
<div style="text-align: center; margin-bottom: 30px;">
    <p style="font-size: 18px;">Your all-in-one science companion! Design experiments, generate reports, 
    and get AI-powered feedback on your lab work.</p>
</div>
""", unsafe_allow_html=True)

# Experiment templates
experiments = {
    "Vinegar + Baking Soda": {
        "hypothesis": "Mixing vinegar and baking soda will produce bubbles due to a chemical reaction.",
        "concept": "Acid-base reaction producing carbon dioxide."
    },
    "Floating Egg": {
        "hypothesis": "An egg will float in salt water but sink in plain water.",
        "concept": "Density difference between saltwater and freshwater."
    },
    "Lemon Battery": {
        "hypothesis": "A lemon can produce electricity to power a small LED.",
        "concept": "Chemical energy conversion to electrical energy."
    }
}

# AI Query Function
# Replace the query_ai function with this version
def query_ai(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful science teacher providing detailed explanations."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        
        # Check for 401 Unauthorized specifically
        if response.status_code == 401:
            st.error("""
            **Invalid API Key!**
            
            Your Groq API key is either:
            - Missing
            - Incorrect
            - Expired
            
            Please check your .env file and ensure you have a valid key.
            """)
            return None
            
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.HTTPError as err:
        st.error(f"API Error: {err.response.status_code} - {err.response.text}")
        return None
    except Exception as e:
        st.error(f"Error connecting to AI service: {str(e)}")
        return None
# Navigation
app_mode = st.radio("Choose Mode:", ["🧪 Experiment Assistant", "📝 Lab Report Analyzer"], 
                    horizontal=True, label_visibility="collapsed")

# Sidebar
with st.sidebar:
    st.markdown("### 🧪 Experiment Templates")
    st.caption("Quickly start with these pre-defined experiments:")
    
    selected_exp = st.selectbox("Choose an experiment template:", 
                               list(experiments.keys()) + ["Custom Experiment"])
    
    st.markdown("---")
    st.markdown("### 📘 Science Glossary Helper")
    term = st.text_input("Enter a science term (e.g., osmosis, catalyst)")
    if term:
        with st.spinner("Looking up term..."):
            ai_response = query_ai(f"Explain the term '{term}' in simple words for a student.")
        if ai_response:
            st.markdown(f"<div class='concept-box'>{ai_response}</div>", unsafe_allow_html=True)
        else:
            st.warning("Couldn't retrieve definition. Please try again.")

# --- Experiment Assistant Section ---
if app_mode == "🧪 Experiment Assistant":
    st.markdown('<p class="subheader">🔍 Design Your Experiment</p>', unsafe_allow_html=True)
    
    with st.form("experiment_form"):
        # Pre-fill if template selected
        if selected_exp != "Custom Experiment" and selected_exp in experiments:
            default_hypo = experiments[selected_exp]["hypothesis"]
            concept = experiments[selected_exp]["concept"]
            exp_name = selected_exp
        else:
            default_hypo = ""
            concept = ""
            exp_name = st.text_input("Experiment Name", placeholder="e.g., Effect of Temperature on Enzyme Activity")
        
        hypo = st.text_area("Your Hypothesis", value=default_hypo, 
                           placeholder="What do you predict will happen?")
        
        materials = st.text_area("Materials Needed", 
                               placeholder="List all materials needed for this experiment")
        
        procedure = st.text_area("Procedure Steps", 
                               placeholder="Step-by-step instructions for conducting the experiment")
        
        submit = st.form_submit_button("🔍 Generate Experiment Guide", use_container_width=True)
    
    if submit:
        if not exp_name or not hypo:
            st.warning("Please provide at least an experiment name and hypothesis")
            st.stop()
            
        with st.spinner("Designing your experiment guide..."):
            prompt = f"""
            Create a comprehensive guide for a science experiment with the following details:
            
            Experiment Name: {exp_name}
            Hypothesis: {hypo}
            Materials: {materials if materials else 'Not specified'}
            Procedure: {procedure if procedure else 'Not specified'}
            
            Please provide:
            1. A clear explanation of the scientific concept behind the experiment
            2. Step-by-step instructions for conducting the experiment
            3. Safety precautions
            4. Expected results and why they're expected
            5. How to interpret the results
            """
            
            explanation = query_ai(prompt)
        
        if explanation:
            st.success("✅ Experiment Guide Generated!")
            st.balloons()
            
            # Display explanation
            st.markdown("### 🧪 Experiment Guide")
            st.markdown(f"<div class='tip-box'>{explanation}</div>", unsafe_allow_html=True)
            
            # Generate PDF report
            def generate_pdf_report(exp_name, hypo, explanation, materials, procedure):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                
                # Title
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, txt="Science Experiment Guide", ln=True, align='C')
                pdf.ln(15)
                
                # Experiment details
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, txt=f"Experiment: {exp_name}", ln=True)
                pdf.ln(5)
                
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, txt="Hypothesis:", ln=True)
                pdf.set_font("Arial", '', 12)
                pdf.multi_cell(0, 8, txt=hypo)
                pdf.ln(5)
                
                if materials:
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, txt="Materials:", ln=True)
                    pdf.set_font("Arial", '', 12)
                    pdf.multi_cell(0, 8, txt=materials)
                    pdf.ln(5)
                
                if procedure:
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, txt="Procedure:", ln=True)
                    pdf.set_font("Arial", '', 12)
                    pdf.multi_cell(0, 8, txt=procedure)
                    pdf.ln(10)
                
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, txt="Experiment Guide:", ln=True)
                pdf.set_font("Arial", '', 12)
                pdf.multi_cell(0, 8, txt=explanation)
                
                filename = f"experiment_guide_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                pdf.output(filename)
                return filename
            
            pdf_file = generate_pdf_report(exp_name, hypo, explanation, materials, procedure)
            with open(pdf_file, "rb") as file:
                st.download_button("📄 Download Experiment Guide (PDF)", file, 
                                  file_name=f"{exp_name}_guide.pdf", 
                                  use_container_width=True)
    
    # Experiment examples
    st.markdown("---")
    st.markdown('<p class="subheader">🔬 Popular Science Experiments</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container():
            st.markdown('<div class="experiment-card">', unsafe_allow_html=True)
            st.markdown("#### 🧫 Vinegar + Baking Soda")
            st.markdown("**Hypothesis:** Mixing vinegar and baking soda will produce bubbles due to a chemical reaction.")
            st.markdown("**Concept:** Acid-base reaction producing carbon dioxide.")
            if st.button("Try This Experiment", key="vinegar", use_container_width=True):
                st.session_state.selected_exp = "Vinegar + Baking Soda"
            st.markdown('</div>', unsafe_allow_html=True)
            
        with st.container():
            st.markdown('<div class="experiment-card">', unsafe_allow_html=True)
            st.markdown("#### 🥚 Floating Egg")
            st.markdown("**Hypothesis:** An egg will float in salt water but sink in plain water.")
            st.markdown("**Concept:** Density difference between saltwater and freshwater.")
            if st.button("Try This Experiment", key="egg", use_container_width=True):
                st.session_state.selected_exp = "Floating Egg"
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        with st.container():
            st.markdown('<div class="experiment-card">', unsafe_allow_html=True)
            st.markdown("#### 🍋 Lemon Battery")
            st.markdown("**Hypothesis:** A lemon can produce electricity to power a small LED.")
            st.markdown("**Concept:** Chemical energy conversion to electrical energy.")
            if st.button("Try This Experiment", key="lemon", use_container_width=True):
                st.session_state.selected_exp = "Lemon Battery"
            st.markdown('</div>', unsafe_allow_html=True)
            
        with st.container():
            st.markdown('<div class="experiment-card">', unsafe_allow_html=True)
            st.markdown("#### 🌈 Rainbow in a Glass")
            st.markdown("**Hypothesis:** Different sugar solutions can form colorful layers in a glass.")
            st.markdown("**Concept:** Density gradient formation.")
            if st.button("Try This Experiment", key="rainbow", use_container_width=True):
                st.session_state.selected_exp = "Custom Experiment"
                st.session_state.custom_exp = "Rainbow in a Glass"
                st.session_state.custom_hypo = "Different sugar solutions will form distinct layers based on their density."
            st.markdown('</div>', unsafe_allow_html=True)

# --- Lab Report Analyzer Section ---
else:
    # --- File Upload ---
    st.markdown('<p class="subheader">📤 Upload Your Lab Report</p>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload image (JPG, PNG) or PDF", 
                                     type=["jpg", "jpeg", "png", "pdf"],
                                     label_visibility="collapsed")

    lab_text = ""
    if uploaded_file:
        file_bytes = uploaded_file.read()
        file_ext = uploaded_file.name.split(".")[-1].lower()

        if file_ext == "pdf":
            try:
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    for page in pdf.pages:
                        lab_text += page.extract_text() + "\n"
                st.success("✅ PDF text extracted successfully!")
            except Exception as e:
                st.error(f"Error reading PDF: {str(e)}")
        else:
            try:
                image = Image.open(io.BytesIO(file_bytes))
                st.image(image, caption="Uploaded Image", width=300)
                
                # OCR processing
                with st.spinner("Extracting text from image..."):
                    try:
                        lab_text = pytesseract.image_to_string(image)
                        st.success("✅ Text extracted from image!")
                    except pytesseract.pytesseract.TesseractNotFoundError:
                        st.error("""
                        **Tesseract OCR not found!** 
                        
                        To enable image text extraction:
                        1. Install Tesseract OCR on your system
                        2. Add it to your system PATH
                        3. Restart the application
                        
                        For Windows: Download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
                        For Linux: `sudo apt install tesseract-ocr`
                        For Mac: `brew install tesseract`
                        """)
                        st.stop()
                    except Exception as e:
                        st.error(f"OCR Error: {str(e)}")
                        st.stop()
            except Exception as e:
                st.error(f"Error processing image: {str(e)}")

        # Allow text editing
        if lab_text:
            st.markdown('<p class="subheader">✍️ Extracted Text</p>', unsafe_allow_html=True)
            st.caption("Review and edit the extracted text if needed before analysis")
            lab_text = st.text_area("", lab_text, height=300, label_visibility="collapsed")

    # --- AI Evaluation ---
    if lab_text.strip():
        # -- AI Evaluation Prompt --
        full_prompt = f"""You are a science teacher evaluating a student's lab report. Please provide a comprehensive analysis:
        Lab Report:
        {lab_text}
        Evaluation Guidelines:
        1. **Section Check**: Identify which of these sections are present and which are missing:
            - Title
            - Objective
            - Hypothesis
            - Materials
            - Procedure
            - Observations
            - Results
            - Conclusion
            - References
        
        2. **Completeness Score**: 
            - Assign a numerical score from 1-10 based on completeness
            - Justify the score based on missing sections and content quality
        
        3. **Improvement Tips**:
            - For each missing section, explain why it's important
            - Provide specific suggestions for improvement (e.g., "Try writing a more detailed observation section by including quantitative data")
            - Highlight any sections that need more detail or clarity
        
        4. **Structure Response**:
            - Start with: "### Missing Sections:"
            - Then: "### Completeness Score: X/10"
            - Then: "### Improvement Tips:"
            - Finally: "### Detailed Feedback:"
        
        Be concise but thorough in your analysis.
        """

        if st.button("🧪 Analyze Report", use_container_width=True):
            with st.spinner("🔍 Analyzing report with AI. This may take 20-30 seconds..."):
                result = query_ai(full_prompt)
                
            if result:
                st.success("✅ Analysis Complete!")
                st.balloons()
                
                # Extract score using regex
                score_match = re.search(r"Completeness Score:\s*(\d+)/10", result, re.IGNORECASE)
                score = int(score_match.group(1)) if score_match else None
                
                # Display score in a card
                if score is not None:
                    with st.container():
                        st.markdown('<div class="score-card">', unsafe_allow_html=True)
                        
                        # Create columns for score visualization
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            st.markdown(f"<h2 style='text-align: center; color: #28b463;'>{score}/10</h2>", 
                                       unsafe_allow_html=True)
                            st.markdown("<h4 style='text-align: center;'>Completeness Score</h4>", 
                                      unsafe_allow_html=True)
                        
                        with col2:
                            # Create a color gradient based on score
                            if score >= 8:
                                color = "#28b463"  # Green
                            elif score >= 5:
                                color = "#f39c12"  # Orange
                            else:
                                color = "#e74c3c"  # Red
                                
                            # Display progress bar with styling
                            st.progress(score/10, text=f"{score*10}% complete")
                            st.markdown(
                                f"<style>"
                                f".stProgress > div > div > div {{"
                                f"    background-color: {color} !important;"
                                f"    border-radius: 10px;"
                                f"}}"
                                f"</style>",
                                unsafe_allow_html=True
                            )
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                
                # Display AI analysis with formatting
                st.markdown("## 📝 Analysis Results")
                
                # Split sections for better display
                sections = {
                    "Missing Sections": None,
                    "Improvement Tips": None,
                    "Detailed Feedback": None
                }
                
                current_section = None
                for line in result.split('\n'):
                    if "### Missing Sections:" in line:
                        current_section = "Missing Sections"
                        sections[current_section] = []
                    elif "### Improvement Tips:" in line:
                        current_section = "Improvement Tips"
                        sections[current_section] = []
                    elif "### Detailed Feedback:" in line:
                        current_section = "Detailed Feedback"
                        sections[current_section] = []
                    elif current_section and line.strip():
                        sections[current_section].append(line)
                
                # Display each section
                if sections["Missing Sections"]:
                    st.markdown("### 🔍 Missing Sections")
                    missing_text = '\n'.join(sections["Missing Sections"])
                    st.markdown(f'<div class="highlight">{missing_text}</div>', unsafe_allow_html=True)
                
                if sections["Improvement Tips"]:
                    st.markdown("### 💡 Improvement Tips")
                    tips_text = '\n'.join(sections["Improvement Tips"])
                    st.markdown(f'<div class="tip-box">{tips_text}</div>', unsafe_allow_html=True)
                
                if sections["Detailed Feedback"]:
                    st.markdown("### 📋 Detailed Feedback")
                    st.write('\n'.join(sections["Detailed Feedback"]))
                
                # Show full AI response in expander
                with st.expander("View Full AI Analysis"):
                    st.markdown(result)
                
        # --- Question Answering Section ---
        st.markdown("---")
        st.markdown('<p class="subheader">❓ Ask About Your Report</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            user_question = st.text_input("Ask a question about your lab report", 
                                         placeholder="e.g., How can I improve my hypothesis?")
        with col2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            ask_button = st.button("🔍 Ask Question", use_container_width=True)
        
        if (ask_button or user_question) and user_question.strip():
            with st.spinner("Thinking..."):
                followup_prompt = f"""Lab Report:
                {lab_text}
                
                Question: {user_question}
                
                Answer the question based on the lab report. If the question can't be answered from the report, 
                suggest what information the student should add to answer it.
                """
                followup_response = query_ai(followup_prompt)
            
            if followup_response:
                st.markdown("### 💬 AI Response")
                st.markdown(f'<div class="tip-box">{followup_response}</div>', unsafe_allow_html=True)
    else:
        # Show sample report if no file uploaded
        st.markdown("---")
        st.markdown('<p class="subheader">📝 Sample Lab Report</p>', unsafe_allow_html=True)
        st.markdown("""
        **Title:** Effect of Temperature on Enzyme Activity  
        **Objective:** To investigate how temperature affects catalase enzyme activity  
        **Hypothesis:** Enzyme activity will increase with temperature up to 37°C, then decrease  
        **Materials:** Test tubes, hydrogen peroxide, liver extract, thermometer  
        **Procedure:**  
        1. Prepare test tubes at 5 different temperatures  
        2. Add equal amounts of hydrogen peroxide and liver extract  
        3. Measure oxygen production  
        **Observations:** More bubbles at 37°C compared to lower or higher temperatures  
        **Conclusion:** Enzyme activity peaks at body temperature  
        """)
        
        st.info("👆 Upload your own lab report to get a personalized analysis!")

# Footer
st.markdown("---")
st.markdown('<div class="footer">🔬 Science Lab Assistant | Made for Students & Educators</div>', unsafe_allow_html=True)
