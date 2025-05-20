import streamlit as st
from openai import OpenAI
import PyPDF2
import os
from dotenv import load_dotenv
from langdetect import detect, LangDetectException
import streamlit.components.v1 as components
from io import BytesIO
from fpdf import FPDF

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Set up the page
st.set_page_config(page_title="Red Cross Job Assistant", page_icon="🧑‍💼")

st.title("🧑‍💼 Red Cross Job Assistant / Assistant Emploi Croix-Rouge")

# Session state
if "cv_feedback_given" not in st.session_state:
    st.session_state.cv_feedback_given = False
if "document_text" not in st.session_state:
    st.session_state.document_text = ""
if "feedback" not in st.session_state:
    st.session_state.feedback = ""
if "job_feedback" not in st.session_state:
    st.session_state.job_feedback = ""

# Default language fallback
INTERFACE_LANGUAGE = "fr"

# Helper functions
def extract_text(uploaded_file):
    if uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")

def detect_language(text):
    try:
        detected = detect(text[:1000])
        # Print detected language for debugging
        print(f"Detected language: {detected}")
        return detected
    except LangDetectException:
        print(f"Language detection failed, using default: {INTERFACE_LANGUAGE}")
        return INTERFACE_LANGUAGE

def get_language_code(lang):
    mapping = {
        "en": "en-US",
        "fr": "fr-FR",
        "es": "es-ES",
        "ar": "ar-SA",
        "de": "de-DE",
        "pt": "pt-PT",
        "it": "it-IT",
        "ru": "ru-RU"
    }
    # Print detected language for debugging
    st.sidebar.write(f"Detected language: {lang}")
    return mapping.get(lang, "en-US")

def create_pdf(content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in content.split("\n"):
    # Remove unsupported characters manually (basic Unicode cleanup)
        clean_line = line.encode("latin-1", "ignore").decode("latin-1")
        pdf.multi_cell(0, 10, clean_line)
    pdf_bytes = pdf.output(dest="S").encode("latin-1", "ignore")
    buffer = BytesIO(pdf_bytes)
    return buffer


# File upload section
st.header("1️⃣ Upload your CV or Cover Letter / Téléverse ton CV ou ta lettre de motivation")
uploaded_file = st.file_uploader("Upload a PDF or TXT file / Téléverse un fichier PDF ou TXT", type=["pdf", "txt"])

if uploaded_file:
    st.session_state.document_text = extract_text(uploaded_file)
    document_language = detect_language(st.session_state.document_text)
    st.session_state.document_language = document_language  # Store the language in session state

    if st.button("🔍 Analyze Document / Analyser le document"):
        text = st.session_state.document_text
        prompt = f"""
You are a job counselor for the Red Cross. Here is a CV or cover letter:

{text}

Your mission is to help someone in a vulnerable situation (e.g., no home, disability, etc.).

1. Give 3 simple positive points (e.g., clear layout, good experience).
2. Give 3 things to improve (be kind).
3. Suggest 5 concrete improvements (short, simple phrases).

Respond in the same language as the CV: {document_language}
Use very simple words. Short sentences. No complicated vocabulary.
Avoid using markdown or formatting symbols like ** or *.
"""
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800
        )
        st.session_state.feedback = response.choices[0].message.content
        st.session_state.cv_feedback_given = True

# Display feedback and TTS
if st.session_state.cv_feedback_given:
    st.subheader("📝 Feedback / Commentaires")
    st.markdown(st.session_state.feedback)

    # Download feedback as PDF
    pdf_buffer = create_pdf(st.session_state.feedback)
    st.download_button("📄 Download Feedback as PDF", data=pdf_buffer, file_name="cv_feedback.pdf", mime="application/pdf")

    # Read aloud section
    st.subheader("🗣️ Listen to the feedback / Écouter les commentaire" \
    "Languages / Langues: 🇬🇧🇫🇷🇪🇸🇸🇦🇩🇪🇵🇹🇮🇹🇷🇺")
    clean_text = st.session_state.feedback.replace("\n", " ").replace('"', '\\"')
    
    # Add speech rate control
    speech_rate = st.slider("Speed / Vitesse:", min_value=0.5, max_value=1.5, value=0.8, step=0.1, key="feedback_speech_rate")
    
    # Get the language code correctly
    lang_code = get_language_code(st.session_state.document_language)
    
    components.html(f"""
        <script>
            let utterance;
            function speak() {{
                if (utterance) window.speechSynthesis.cancel();
                
                // Debug language support
                console.log("Available voices:");
                let voices = window.speechSynthesis.getVoices();
                voices.forEach(voice => console.log(voice.name + " (" + voice.lang + ")"));
                
                utterance = new SpeechSynthesisUtterance("{clean_text}");
                
                // Set speech rate
                utterance.rate = {speech_rate};
                console.log("Speech rate set to: {speech_rate}");
                
                // For French, explicitly set fr-FR
                const detectedLang = "{st.session_state.document_language}";
                if (detectedLang === "fr") {{
                    utterance.lang = "fr-FR";
                    console.log("Setting French voice: fr-FR");
                    
                    // Try to find a French voice
                    const frenchVoices = voices.filter(voice => voice.lang.startsWith('fr'));
                    if (frenchVoices.length > 0) {{
                        utterance.voice = frenchVoices[0];
                        console.log("Found French voice: " + frenchVoices[0].name);
                    }}
                }} else {{
                    utterance.lang = "{lang_code}";
                    console.log("Using language code: " + "{lang_code}");
                }}
                
                window.speechSynthesis.speak(utterance);
            }}
            function stopSpeech() {{
                window.speechSynthesis.cancel();
            }}
        </script>
        <button onclick="speak()">▶️ Read Aloud / Lire à voix haute</button>
        <button onclick="stopSpeech()">⏹️ Stop</button>
    """, height=100)

    # Job description input
    st.header("2️⃣ Paste a Job Description / Colle une offre d'emploi")
    job_desc = st.text_area("Paste the job description here / Colle ici la description du poste")

    if st.button("🎯 Generate Interview Questions / Créer des questions d'entretien"):
        job_language = detect_language(job_desc)
        prompt = f"""
You are a Red Cross job counselor. Here's a job offer:

{job_desc}

Here is the CV of the person applying:

{st.session_state.document_text}

1. Suggest 5 simple interview questions tailored to this candidate and job.
2. Give a good answer to each (short and easy to remember).
3. Add a section with 5 Important Words:
   - For each: give a simple definition + a sentence example.

Respond in the same language as the job offer.
Use very simple words. Short sentences. No complicated vocabulary.
Avoid using markdown or formatting symbols like ** or *.
"""
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        st.session_state.job_feedback = response.choices[0].message.content
        st.session_state.job_language = job_language  # Store the job language

    if st.session_state.job_feedback:
        st.subheader("🎙️ Mock Interview & Definitions / Questions et mots clés")
        st.markdown(st.session_state.job_feedback)

        # Download interview as PDF
        job_pdf_buffer = create_pdf(st.session_state.job_feedback)
        st.download_button(
            label="📄 Download Interview Preparation as PDF",
            data=job_pdf_buffer,
            file_name="interview_questions.pdf",
            mime="application/pdf"
        )

        # Read aloud job feedback
        st.subheader("🗣️ Listen to the interview preparation / Écouter la préparation" \
        "Languages / Langues: 🇬🇧🇫🇷🇪🇸🇸🇦🇩🇪🇵🇹🇮🇹🇷🇺")
        job_clean = st.session_state.job_feedback.replace("\n", " ").replace('"', '\\"')
        
        # Add speech rate control
        job_speech_rate = st.slider("Speed / Vitesse:", min_value=0.5, max_value=1.5, value=0.8, step=0.1, key="job_speech_rate")
        
        job_lang_code = get_language_code(st.session_state.job_language)
        
        components.html(f"""
            <script>
                let jobUtterance;
                function speakJob() {{
                    if (jobUtterance) window.speechSynthesis.cancel();
                    
                    // Debug language support
                    console.log("Available voices for job:");
                    let voices = window.speechSynthesis.getVoices();
                    voices.forEach(voice => console.log(voice.name + " (" + voice.lang + ")"));
                    
                    jobUtterance = new SpeechSynthesisUtterance("{job_clean}");
                    
                    // Set speech rate
                    jobUtterance.rate = {job_speech_rate};
                    console.log("Job speech rate set to: {job_speech_rate}");
                    
                    // For French, explicitly set fr-FR
                    const detectedJobLang = "{st.session_state.job_language}";
                    if (detectedJobLang === "fr") {{
                        jobUtterance.lang = "fr-FR";
                        console.log("Setting French voice for job: fr-FR");
                        
                        // Try to find a French voice
                        const frenchVoices = voices.filter(voice => voice.lang.startsWith('fr'));
                        if (frenchVoices.length > 0) {{
                            jobUtterance.voice = frenchVoices[0];
                            console.log("Found French voice for job: " + frenchVoices[0].name);
                        }}
                    }} else {{
                        jobUtterance.lang = "{job_lang_code}";
                        console.log("Using job language code: " + "{job_lang_code}");
                    }}
                    
                    window.speechSynthesis.speak(jobUtterance);
                }}
                function stopJobSpeech() {{
                    window.speechSynthesis.cancel();
                }}
            </script>
            <button onclick="speakJob()">▶️ Read Aloud / Lire à voix haute</button>
            <button onclick="stopJobSpeech()">⏹️ Stop</button>
        """, height=100)

with st.sidebar:
    st.header("How to use this app / Comment utiliser cette application")
    st.markdown("""
    **English Instructions:**
    1. Upload your CV in any language (PDF or TXT)
    2. Click "Analyze Document" to get feedback
    3. Read, listen, or download the feedback
    4. Paste a job description in the text area
    5. Click "Generate Interview Questions" to create tailored questions
    6. Read, listen, or download the interview preparation    

    
    **Instructions en français:**
    1. Téléversez votre CV dans n'importe quelle langue (PDF ou TXT)
    2. Cliquez sur "Analyser le document" pour obtenir des commentaires
    3. Lisez, écoutez ou téléchargez les commentaires
    4. Collez une description de poste dans la zone de texte
    5. Cliquez sur "Créer des questions d'entretien" pour générer des questions adaptées
    6. Lisez, écoutez ou téléchargez la préparation à l'entretien  
    """)