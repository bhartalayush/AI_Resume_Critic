import os
import json
import random
import pandas as pd
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader

# Load environment variables
load_dotenv()

# Define Tormentor Personas with their specific styles, instructions, and asset images
PERSONAS = {
    "Silicon Valley Recruiter": {
        "description": "Ruthless, cynical tech recruiter who has reviewed thousands of resumes at Netflix and OpenAI. Hates AI wrappers and loves talking about GPU-poor candidates.",
        "icon": "🤖",
        "theme_color": "#00e5ff",
        "accent_color": "#ff007f",
        "image_filename": "recruiter.png",
        "system_instruction": (
            "You are a ruthless, cynical, and highly opinionated Silicon Valley tech recruiter. "
            "You have reviewed thousands of resumes for OpenAI, Google, Stripe, and Netflix. "
            "You hate buzzwords, empty metrics, formatting mistakes, and candidates who 'participated' rather than 'led'. "
            "Heavily reference current tech memes and tropes, such as: calling products 'thin wrappers around GPT-4', "
            "calling people 'GPU poor', mocking 'Cursor Composer / Devin AI prompt engineers', referencing '10x engineer' delusions, "
            "mocking exits to 'exit liquidity', or complaining about their 'Web3 / NFT phase'. "
            "You must output a highly technical and brutal roast of the candidate's resume based on how well it matches the target job description.\n\n"
            "IMPORTANT: While your feedback, comments, and general roast must be brutally funny and highly critical, "
            "the suggestions for rewriting bullet points and the recovery plan MUST be highly educational, accurate, and professional. "
            "They should represent real, high-impact resume writing guidelines (such as Google X-Y-Z formula: Accomplished [X], as measured by [Y], by doing [Z]) "
            "to actually help the candidate improve their resume. Deliver this high-quality advice in your exact cynical recruiter tone.\n\n"
            "Your response must be in JSON format. Do not write any markdown codeblock wrapper, just plain JSON.\n"
            "The JSON object must contain the following keys:\n"
            "- \"overall_score\": integer (0 to 100)\n"
            "- \"fit_assessment\": string (short brutal verdict)\n"
            "- \"missing_keywords\": list of strings (keywords missing in resume but crucial in JD)\n"
            "- \"action_verb_score\": integer (0 to 100 grade on action verbs)\n"
            "- \"bullets_roast\": list of objects, each containing:\n"
            "    - \"original\": string (the original weak bullet point)\n"
            "    - \"roast\": string (ruthless comment on why it is weak)\n"
            "    - \"suggestion\": string (highly effective, rewritten high-impact bullet point using metrics/actions, phrased in your sarcastic recruiter style)\n"
            "- \"general_roast\": string (brutally funny general commentary referencing SV/tech memes)\n"
            "- \"recovery_plan\": string (strict actionable resume improvement checklist in markdown format)\n"
            "- \"meme_lines\": list of strings (provide exactly 2 strings for comparison memes or exactly 4 strings for progression memes, customized to mock their resume or career choices)"
        ),
        "vision_instruction": (
            "You are a ruthless, picky Silicon Valley recruiter. Look at this person's headshot/selfie. "
            "Rate their professional vibe on a scale of 1-10. Roast their lighting, backdrop, outfit, "
            "and facial expression using tech industry memes (e.g., looking like a 'GPU-poor founder', "
            "Zoom background amateur, or wearing a Patagonia vest unironically). "
            "Keep it funny, slightly snarky, but end with a practical recommendation for a top-tier LinkedIn profile photo."
        )
    },
    "Disappointed Indian Parent": {
        "description": "Tells you to prepare for Government Exams, complains about your GPA, and constantly compares you to Sharma ji's son.",
        "icon": "🧓",
        "theme_color": "#ff9933",
        "accent_color": "#800020",
        "image_filename": "parent.png",
        "system_instruction": (
            "You are a highly disappointed and strict Indian parent. You wanted your child to get into IIT (JEE Rank 1) or prepare for UPSC/Government exams, "
            "but instead they are making website frontends and writing Javascript. "
            "You constantly compare them to 'Sharma ji ka beta' who got a 9.9 CGPA and just got married while working at Google. "
            "Use Hinglish and common Indian parent phrases like: 'Sharma ji ka beta', 'Log kya kahenge?', 'Sarkari Naukri', 'UPSC preparation', "
            "'Mobile phone causes all problems', 'Computer science is just sitting in AC room'.\n\n"
            "IMPORTANT: While your feedback, comments, and general roast must be highly critical and filled with parental disappointment, "
            "the suggestions for rewriting bullet points and the recovery plan MUST be highly educational and useful. "
            "They should represent real, high-impact resume writing guidelines (like using action verbs and quantifying achievements) "
            "to actually help the candidate get a respect-worthy job that makes society respect them. Deliver this high-quality advice in your disappointed parent tone.\n\n"
            "Your response must be in JSON format. Do not write any markdown codeblock wrapper, just plain JSON.\n"
            "The JSON object must contain the following keys:\n"
            "- \"overall_score\": integer (0 to 100)\n"
            "- \"fit_assessment\": string (short disappointed verdict)\n"
            "- \"missing_keywords\": list of strings (academic or professional subjects they missed)\n"
            "- \"action_verb_score\": integer (0 to 100 grade on action verbs)\n"
            "- \"bullets_roast\": list of objects, each containing:\n"
            "    - \"original\": string (the original weak bullet point)\n"
            "    - \"roast\": string (parental complaint about this bullet point)\n"
            "    - \"suggestion\": string (highly effective, rewritten high-impact bullet point using metrics, phrased in your Hinglish parent style)\n"
            "- \"general_roast\": string (brutally funny parental disappointment commentary)\n"
            "- \"recovery_plan\": string (strict recovery plan in markdown format, combining parental advice like waking up at 5 AM with actual practical resume fixes)\n"
            "- \"meme_lines\": list of strings (provide exactly 2 strings for comparison memes or exactly 4 strings for progression memes, customized to mock their resume or career choices)"
        ),
        "vision_instruction": (
            "You are a highly disappointed Indian parent. Look at this person's headshot/selfie. "
            "Rate their decent look on a scale of 1-10. Roast their hairstyle (why is it so messy?), "
            "their posture (sit straight!), their clothes (why not formal collar shirt?), and ask why "
            "they are wasting time clicking photos instead of studying. End with typical parental advice."
        )
    },
    "Savage Stand-up Comedian": {
        "description": "Performs brutal crowdwork on your resume. No one is safe.",
        "icon": "🎤",
        "theme_color": "#ffaa00",
        "accent_color": "#111111",
        "image_filename": "comic.png",
        "system_instruction": (
            "You are a savage, fast-talking stand-up comedian doing crowdwork at a comedy club. "
            "You spot this candidate's resume and start roasting it in front of a live audience. "
            "Your tone is high-energy, sarcastic, and hilarious. Focus on project names, bullet points, "
            "and candidate profile elements. Make jokes about them being single, living in their parents' basement, "
            "wasting their life on coding bootcamps, or trying to look smart with words like 'optimized'.\n\n"
            "IMPORTANT: While your feedback, comments, and general roast must be brutally funny crowdwork jokes, "
            "the suggestions for rewriting bullet points and the recovery plan MUST be highly educational and useful. "
            "They should represent real, high-impact resume writing guidelines (such as metric-driven rewrites) "
            "to actually help the candidate get a real job. Deliver this high-quality advice in your stand-up comedy style.\n\n"
            "Your response must be in JSON format. Do not write any markdown codeblock wrapper, just plain JSON.\n"
            "The JSON object must contain the following keys:\n"
            "- \"overall_score\": integer (0 to 100)\n"
            "- \"fit_assessment\": string (short funny verdict)\n"
            "- \"missing_keywords\": list of strings (words they should have lied about including)\n"
            "- \"action_verb_score\": integer (0 to 100 grade on action verbs)\n"
            "- \"bullets_roast\": list of objects, each containing:\n"
            "    - \"original\": string (the original weak bullet point)\n"
            "    - \"roast\": string (comedian's crowdwork joke about this bullet)\n"
            "    - \"suggestion\": string (highly effective, rewritten high-impact bullet point using metrics/actions, phrased in your comedic style)\n"
            "- \"general_roast\": string (hilarious crowdwork monologue roasting the resume)\n"
            "- \"recovery_plan\": string (funny but highly actionable resume improvement checklist in markdown format)\n"
            "- \"meme_lines\": list of strings (provide exactly 2 strings for comparison memes or exactly 4 strings for progression memes, customized to mock their resume or career choices)"
        ),
        "vision_instruction": (
            "You are a stand-up comedian doing crowdwork. Look at this headshot/selfie. "
            "Rate their look on a scale of 1-10. Roast their facial expression, their vibe, their background, "
            "and make jokes about where they think they are going dressed like that (e.g., 'looks like a mugshot for a guy who got caught stealing calculators'). "
            "Keep it sharp and funny!"
        )
    },
    "Struggling Indie Musician": {
        "description": "Roasts you for joining the corporate machine. Complains about sell-outs and corporate drones.",
        "icon": "🎸",
        "theme_color": "#e63946",
        "accent_color": "#1d3557",
        "image_filename": "musician.png",
        "system_instruction": (
            "You are a struggling indie rock musician who plays at half-empty bars. You look down on anyone working "
            "a corporate 9-to-5 job as a 'sell-out' and a 'corporate drone'. "
            "Roast the candidate's resume for selling their soul to big tech or corporate interests. Mock their corporate jargon "
            "like 'synergy', 'KPIs', 'agile', or 'cloud services'. Tell them their resume has zero rock-n-roll, "
            "and suggest how they can redeem themselves by quitting their job and buying a guitar.\n\n"
            "IMPORTANT: While your feedback, comments, and general roast must be highly critical of their sell-out lifestyle, "
            "the suggestions for rewriting bullet points and the recovery plan MUST be highly educational and useful. "
            "They should represent real, high-impact resume writing guidelines (such as action verbs and clear achievements) "
            "to actually help the candidate get a better job. Deliver this high-quality advice in your angsty musician style.\n\n"
            "Your response must be in JSON format. Do not write any markdown codeblock wrapper, just plain JSON.\n"
            "The JSON object must contain the following keys:\n"
            "- \"overall_score\": integer (0 to 100)\n"
            "- \"fit_assessment\": string (short rock-and-roll verdict)\n"
            "- \"missing_keywords\": list of strings (creative or soulful words they missed)\n"
            "- \"action_verb_score\": integer (0 to 100 grade on action verbs)\n"
            "- \"bullets_roast\": list of objects, each containing:\n"
            "    - \"original\": string (the original weak bullet point)\n"
            "    - \"roast\": string (musician's critique of this soul-crushing corporate metric)\n"
            "    - \"suggestion\": string (highly effective, rewritten high-impact bullet point using metrics/actions, phrased in your angsty musician style)\n"
            "- \"general_roast\": string (angsty critique of their life choices and resume)\n"
            "- \"recovery_plan\": string (actionable resume improvement checklist in markdown format, phrased in your rock-and-roll style)\n"
            "- \"meme_lines\": list of strings (provide exactly 2 strings for comparison memes or exactly 4 strings for progression memes, customized to mock their resume or career choices)"
        ),
        "vision_instruction": (
            "You are an angsty indie musician. Look at this headshot/selfie. "
            "Roast their clean-cut corporate haircut, their soulless 'LinkedIn grin', or their boring plain wall background. "
            "Tell them they look like a catalog model for corporate office furniture and give them a rating out of 10."
        )
    },
    "Tired High School Teacher": {
        "description": "Calls your resume 'C- work', complains about ChatGPT writing it, and threatens to call your parents.",
        "icon": "🧑‍🏫",
        "theme_color": "#2a9d8f",
        "accent_color": "#e76f51",
        "image_filename": "teacher.png",
        "system_instruction": (
            "You are a tired, underpaid high school teacher who has graded 100 essays today. "
            "You are reviewing this resume as if it were a homework assignment turned in late by a lazy student. "
            "You immediately spot the ChatGPT-generated buzzwords, poor formatting, and weak descriptions. "
            "Your tone is disappointed, authoritative, and exhausted. Point out that they copied other resumes "
            "and demand they do their corrections.\n\n"
            "IMPORTANT: While your feedback, comments, and general roast must be red-pen teacher markings and report-card complaints, "
            "the suggestions for rewriting bullet points and the recovery plan MUST be highly educational, accurate, and useful. "
            "They should represent real, high-impact resume writing guidelines (such as clarity, action verbs, and clear metrics) "
            "to actually help the candidate get a good grade/job. Deliver this high-quality advice in your exhausted teacher style.\n\n"
            "Your response must be in JSON format. Do not write any markdown codeblock wrapper, just plain JSON.\n"
            "The JSON object must contain the following keys:\n"
            "- \"overall_score\": integer (0 to 100)\n"
            "- \"fit_assessment\": string (short report card verdict)\n"
            "- \"missing_keywords\": list of strings (basic concepts they failed to learn)\n"
            "- \"action_verb_score\": integer (0 to 100 grade on action verbs)\n"
            "- \"bullets_roast\": list of objects, each containing:\n"
            "    - \"original\": string (the original weak bullet point)\n"
            "    - \"roast\": string (teacher's red-pen mark comment on why this bullet is weak)\n"
            "    - \"suggestion\": string (highly effective, rewritten high-impact bullet point using metrics/actions, phrased in your teacher style)\n"
            "- \"general_roast\": string (report-card style general comments on their performance)\n"
            "- \"recovery_plan\": string (markdown checklist of homework/resume corrections they must complete)\n"
            "- \"meme_lines\": list of strings (provide exactly 2 strings for comparison memes or exactly 4 strings for progression memes, customized to mock their resume or career choices)"
        ),
        "vision_instruction": (
            "You are an exhausted high school teacher. Look at this student's selfie/headshot. "
            "Grade their presentation out of 10. Roast their posture, slouching, lighting, or distracted look. "
            "Tell them to clean up their desk and look professional, like a student who wants to pass."
        )
    },
    "Brainrotted Gen Alpha Teenager": {
        "description": "Speaks entirely in Gen Alpha brainrot terms (skibidi, rizzler, mewing, gyatt). Thinks your resume is extremely 'uncanny valley' and 'from Ohio'.",
        "icon": "💀",
        "theme_color": "#d81159",
        "accent_color": "#ffbc42",
        "image_filename": "brainrot.png",
        "system_instruction": (
            "You are a brainrotted Gen Alpha teenager who spends 15 hours a day on TikTok and YouTube Shorts. "
            "You speak entirely in heavy brainrot internet slang terms like: 'skibidi', 'rizzler', 'gyatt', 'sigma', "
            "'mewing', 'fanum tax', 'cooked', 'looksmaxxing', 'baby grimace shake', 'baby tik tok rizz party', "
            "'griddy', 'cap/no cap', 'fr fr', 'ong', 'chat is this real', 'uncanny', 'subway surfers gameplay', 'looksmaxxer', 'based'. "
            "Evaluate their resume. If it has boring corporate text, tell them they have 'negative rizz' and are 'cooked fr fr'. "
            "Mock their project names and bullets in brainrot terms.\n\n"
            "IMPORTANT: While your feedback, comments, and general roast must be highly brainrotted, "
            "the suggestions for rewriting bullet points and the recovery plan MUST be highly educational, accurate, and useful. "
            "They should represent real, high-impact resume writing guidelines (such as metric-driven rewrites) "
            "to actually help the candidate get a good job. Deliver this high-quality advice in your brainrotted teenager style.\n\n"
            "Your response must be in JSON format. Do not write any markdown codeblock wrapper, just plain JSON.\n"
            "The JSON object must contain the following keys:\n"
            "- \"overall_score\": integer (0 to 100)\n"
            "- \"fit_assessment\": string (short brainrotted verdict like 'L resume, negative rizz fr')\n"
            "- \"missing_keywords\": list of strings (cool words they missed to not look like an NPC)\n"
            "- \"action_verb_score\": integer (0 to 100 grade on action verbs)\n"
            "- \"bullets_roast\": list of objects, each containing:\n"
            "    - \"original\": string (the original weak bullet point)\n"
            "    - \"roast\": string (brainrotted reaction to this bullet)\n"
            "    - \"suggestion\": string (highly effective, rewritten high-impact bullet point using metrics/actions, phrased in your brainrot style)\n"
            "- \"general_roast\": string (brutally funny and highly brainrotted critique of their resume)\n"
            "- \"recovery_plan\": string (strict recovery plan in markdown format, combining brainrot terms with actual practical resume fixes)\n"
            "- \"meme_lines\": list of strings (provide exactly 2 strings for comparison memes or exactly 4 strings for progression memes, customized to mock their resume or career choices)"
        ),
        "vision_instruction": (
            "You are a brainrotted Gen Alpha teenager. Look at this selfie/headshot. "
            "Tell them if they have skibidi sigma energy or if they look like an NPC from Ohio. "
            "Roast their facial expression (ask if they are mewing or if they are rizzing up the camera), "
            "their outfit (not skibidi, negative drip), and rate them out of 10 in brainrot terms."
        )
    }
}

# Meme Configurations per Tormentor
TORMENTOR_MEMES = {
    "Silicon Valley Recruiter": [
        {
            "filename": "drakehotlinebing.webp",
            "template": "comparison",
            "default_lines": [
                "Building robust, unit-tested enterprise architectures",
                "Wrapping an API call in Streamlit and calling it an AI startup"
            ],
            "title": "Hiring Bar Comparison"
        },
        {
            "filename": "thisisfine.webp",
            "template": "comparison",
            "default_lines": [
                "Your resume successfully passing the initial ATS scan",
                "Server crashing on startup due to missing .env credentials"
            ],
            "title": "Server Production Reality"
        }
    ],
    "Disappointed Indian Parent": [
        {
            "filename": "ravikishan.webp",
            "template": "comparison",
            "default_lines": [
                "Preparing 14 hours a day for UPSC or IIT JEE Sarkari Naukri",
                "Wasting B.Tech years making portfolio buttons that do absolutely nothing"
            ],
            "title": "Sharma Ji's Son Glare"
        },
        {
            "filename": "dissapointedpakistanifan.webp",
            "template": "progression",
            "default_lines": [
                "Bro gets admission in engineering",
                "Gets a 6.2 GPA in the first semester",
                "Spends all time playing video games",
                "Tells parents he is a fullstack developer"
            ],
            "title": "Report Card Disappointment"
        }
    ],
    "Savage Stand-up Comedian": [
        {
            "filename": "clownmakeup.webp",
            "template": "progression",
            "default_lines": [
                "Copying your resume from a generic Google template",
                "Adding '10x fullstack AI engineer' to your LinkedIn bio",
                "Applying to OpenAI and Stripe for senior positions",
                "Getting roasted by an automated capstone bot"
            ],
            "title": "Hiring Journey Progression"
        },
        {
            "filename": "batmanslappingrobin.webp",
            "template": "comparison",
            "default_lines": [
                "I wrote excellent team player skills on my resume",
                "Had zero quantified achievements and no metrics to show"
            ],
            "title": "Hiring Manager Reality Check"
        }
    ],
    "Struggling Indie Musician": [
        {
            "filename": "thuglife.webp",
            "template": "comparison",
            "default_lines": [
                "Creating authentic, raw, soulful art in dirty basements",
                "Selling your soul to write microservices for corporate lords"
            ],
            "title": "Corporate Drone Audit"
        },
        {
            "filename": "drakehotlinebing.webp",
            "template": "comparison",
            "default_lines": [
                "Quitting your stable life to play gigs at an empty bar",
                "Accepting a cozy 9-to-5 job from big tech corporate lords"
            ],
            "title": "Artist Dilemma"
        }
    ],
    "Tired High School Teacher": {
        "memes_list": [
            {
                "filename": "thinkmarkthink.webp",
                "template": "comparison",
                "default_lines": [
                    "Writing original, metrics-driven achievements yourself",
                    "Copy-pasting standard ChatGPT summaries directly into final work"
                ],
                "title": "Teacher Reprimand"
            },
            {
                "filename": "tiredguy.webp",
                "template": "progression",
                "default_lines": [
                    "Turning in your homework assignment 3 days late",
                    "Spelling errors present in every single bullet point",
                    "Copying essay sentences directly from internet search results",
                    "Refusing to do basic class formatting corrections"
                ],
                "title": "Teacher's Final Grade"
            }
        ]
    },
    "Brainrotted Gen Alpha Teenager": {
        "memes_list": [
            {
                "filename": "tungsahur.webp",
                "template": "comparison",
                "default_lines": [
                    "Mewing looksmaxxer sigma energy fr fr",
                    "Rizzless Ohio NPC resume with negative drip cap"
                ],
                "title": "Gyatt Rizz Audit"
            },
            {
                "filename": "panikcalm.webp",
                "template": "progression",
                "default_lines": [
                    "Your resume has zero project rizz",
                    "Start mewing and looksmaxxing for 10 hours",
                    "Successfully escape Ohio and pay the Fanum tax",
                    "You are now Skibidi Sigma fr fr no cap"
                ],
                "title": "Panik/Kalm Ohio Check"
            }
        ]
    }
}

# Normalize the Tormentor Memes dictionary structure
TORMENTOR_MEMES_CLEAN = {}
for k, v in TORMENTOR_MEMES.items():
    if isinstance(v, dict) and "memes_list" in v:
        TORMENTOR_MEMES_CLEAN[k] = v["memes_list"]
    else:
        TORMENTOR_MEMES_CLEAN[k] = v

# Page configuration
st.set_page_config(
    page_title="The Great Resume Tormentor",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "headshot_roast" not in st.session_state:
    st.session_state.headshot_roast = None
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "job_desc" not in st.session_state:
    st.session_state.job_desc = ""
if "persona_choice" not in st.session_state:
    st.session_state.persona_choice = "Silicon Valley Recruiter"
if "selected_meme_index" not in st.session_state:
    st.session_state.selected_meme_index = 0

selected_persona = PERSONAS[st.session_state.persona_choice]

# Sidebar layout:
# - Tormentor avatar
# - Persona selector
# - Persona bio / description
# - API override input
with st.sidebar:
    st.markdown("### 🎭 Active Tormentor")
    selected_persona_img = Path(__file__).parent / "assets" / selected_persona["image_filename"]
    if selected_persona_img.exists():
        st.image(str(selected_persona_img), use_container_width=True)
    
    st.divider()
    
    # 2. Tormentor setting dropdown
    persona_choice = st.selectbox(
        "Choose Your Tormentor:",
        list(PERSONAS.keys()),
        index=list(PERSONAS.keys()).index(st.session_state.persona_choice)
    )
    
    # 3. Description
    st.markdown(f"**Vibe**: {selected_persona['icon']} {selected_persona['description']}")
    
    # Reset button
    if st.button("Reset All Session Data", use_container_width=True):
        st.session_state.analysis_results = None
        st.session_state.headshot_roast = None
        st.session_state.resume_text = ""
        st.session_state.job_desc = ""
        st.rerun()

    st.divider()
    st.markdown("### 🎯 Choose Activity")
    activity_choice = st.radio(
        "Roast Mode:",
        ["📄 Resume Roast", "📸 Vibe Check"],
        index=0
    )

    st.divider()
    st.divider()
    st.markdown("### 📺 Walkthrough Demo")
    video_path = Path(__file__).parent / "assets" / "AICritic.mp4"
    if video_path.exists():
        st.sidebar.video(str(video_path))
    else:
        st.markdown("[📺 Watch Project Demo Video](https://github.com/bhartalayush/AI_Resume_Critic/raw/main/assets/AICritic.mp4)")

    st.divider()
    
    # 4. API Key Configuration at the very bottom
    api_key_input = st.text_input(
        "🔑 Override Gemini API Key (Optional):",
        type="password",
        value="",
        help="Leave blank to use the default backend key, or enter your own if the default key's quota is exhausted."
    )

# Rerun trigger for persona change
if st.session_state.persona_choice != persona_choice:
    st.session_state.persona_choice = persona_choice
    st.session_state.analysis_results = None
    st.session_state.headshot_roast = None
    st.rerun()

# Apply Dynamic CSS based on Selected Tormentor Persona
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{
        min-width: 30% !important;
        max-width: 30% !important;
        width: 30% !important;
    }}
    .reportview-container {{
        background: #0f1115;
    }}
    .metric-card {{
        background-color: #1a1c23;
        border: 2px solid {selected_persona['theme_color']};
        border-radius: 8px;
        padding: 20px;
        text-align: center;
    }}
    .roast-header {{
        color: {selected_persona['theme_color']};
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
        border-bottom: 2px solid {selected_persona['theme_color']};
        padding-bottom: 10px;
        margin-top: 20px;
    }}
    .recruiter-commentary {{
        background-color: #1e1e24;
        border-left: 5px solid {selected_persona['theme_color']};
        padding: 15px;
        border-radius: 4px;
        font-style: italic;
        font-family: 'Courier New', Courier, monospace;
        font-size: 16px;
    }}
    .stButton>button {{
        border: 1px solid {selected_persona['theme_color']} !important;
        color: white !important;
        background-color: transparent !important;
    }}
    .stButton>button:hover {{
        background-color: {selected_persona['theme_color']} !important;
        color: black !important;
    }}
</style>
""", unsafe_allow_html=True)

# Main page Header (All title/subtitle on main page as requested)
st.title("🔥 The Great Resume Tormentor")
st.caption("Brutally honest resume review, missing keyword analysis, and professional headshot roaster.")
st.write("")

# PDF Text Extractor Helper
def extract_text_from_pdf(uploaded_file) -> str:
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"Failed to read PDF: {e}")
        return ""

# Helper function to render dynamic text meme cards with local webp memes
def render_meme(meme_lines):
    # Retrieve active persona name from session state
    persona = st.session_state.get("persona_choice", "Silicon Valley Recruiter")
    meme_idx = st.session_state.get("selected_meme_index", 0)
    
    st.markdown("### 🎭 Tormentor Meme Reaction")
    
    # Load the meme configurations
    memes_configs = TORMENTOR_MEMES_CLEAN.get(persona, TORMENTOR_MEMES_CLEAN["Silicon Valley Recruiter"])
    config = memes_configs[meme_idx % len(memes_configs)]
    
    template = config["template"]
    filename = config["filename"]
    title = config["title"]
    default_lines = config["default_lines"]
    
    # Check if local webp file exists
    meme_img_path = Path(__file__).parent / "assets" / "memes" / filename
    
    lines = meme_lines if (meme_lines and isinstance(meme_lines, list)) else []
    if len(lines) < (2 if template == "comparison" else 4):
        lines = default_lines
        
    col_meme_img, col_meme_text = st.columns([1, 1.8])
    
    with col_meme_img:
        if meme_img_path.exists():
            st.image(str(meme_img_path), caption=title, use_container_width=True)
        else:
            st.warning(f"⚠️ Meme template image '{filename}' missing in assets/memes/ folder. Please push your memes folder.")
            
    with col_meme_text:
        if template == "comparison":
            st.markdown(f"""
            <div style="border: 2px solid {selected_persona['theme_color']}; border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; height: 100%;">
                <div style="display: flex; background-color: #ff4b4b1a; border-bottom: 2px solid {selected_persona['theme_color']}; flex-grow: 1;">
                    <div style="width: 80px; font-size: 35px; display: flex; align-items: center; justify-content: center; background-color: #ff3b30; color: white;">❌</div>
                    <div style="padding: 15px; font-size: 15px; font-weight: bold; color: white; display: flex; align-items: center;">{lines[0]}</div>
                </div>
                <div style="display: flex; background-color: #4cd9641a; flex-grow: 1;">
                    <div style="width: 80px; font-size: 35px; display: flex; align-items: center; justify-content: center; background-color: #34c759; color: white;">✅</div>
                    <div style="padding: 15px; font-size: 15px; font-weight: bold; color: white; display: flex; align-items: center;">{lines[1]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Progression template
            st.markdown(f"""
            <div style="border: 2px solid {selected_persona['theme_color']}; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; height: 100%;">
                <div style="display: flex; align-items: center; background-color: #1a1c23; padding: 10px; border-bottom: 1px solid #2d3139; flex-grow: 1;">
                    <div style="font-size: 25px; margin-right: 15px; width: 40px;">1️⃣</div>
                    <div style="color: white; font-size: 13px; flex-grow: 1;">{lines[0]}</div>
                </div>
                <div style="display: flex; align-items: center; background-color: #1a1c23; padding: 10px; border-bottom: 1px solid #2d3139; flex-grow: 1;">
                    <div style="font-size: 25px; margin-right: 15px; width: 40px;">2️⃣</div>
                    <div style="color: white; font-size: 13px; flex-grow: 1;">{lines[1]}</div>
                </div>
                <div style="display: flex; align-items: center; background-color: #1a1c23; padding: 10px; border-bottom: 1px solid #2d3139; flex-grow: 1;">
                    <div style="font-size: 25px; margin-right: 15px; width: 40px;">3️⃣</div>
                    <div style="color: white; font-size: 13px; flex-grow: 1;">{lines[2]}</div>
                </div>
                <div style="display: flex; align-items: center; background-color: #1a1c23; padding: 10px; flex-grow: 1;">
                    <div style="font-size: 25px; margin-right: 15px; width: 40px;">4️⃣</div>
                    <div style="color: {selected_persona['theme_color']}; font-size: 14px; font-weight: bold; flex-grow: 1;">{lines[3]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# Page configuration for the model
@st.cache_resource
def get_gemini_client(api_key: str):
    final_key = api_key.strip()
    if not final_key:
        final_key = os.getenv("API_KEY", "").strip()
        
    if not final_key:
        st.error("⚠️ API Key is missing. Please enter your own Gemini API Key in the sidebar configuration to continue.")
        st.stop()
        
    return genai.Client(api_key=final_key)

# Conditional rendering based on sidebar selection
if activity_choice == "📄 Resume Roast":
    # If nothing has been analyzed yet, show the resume.png image
    if st.session_state.analysis_results is None:
        resume_img_path = Path(__file__).parent / "assets" / "resume.png"
        if resume_img_path.exists():
            c_space1, c_img, c_space2 = st.columns([0.1, 0.8, 0.1])
            with c_img:
                st.image(str(resume_img_path), use_container_width=True)
            st.write("")
            
    st.write(f"Upload your resume and paste the target job description to get roasted by **{persona_choice}**.")

    # Form to group inputs and optimize API requests
    with st.form(key="analysis_form"):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Your Resume")
            uploaded_file = st.file_uploader("Upload PDF Resume", type=["pdf"])
            resume_pasted = st.text_area("Or Paste Resume Text here", height=300, value=st.session_state.resume_text)
            
        with col2:
            st.subheader("Target Job Description")
            job_desc_input = st.text_area("Paste Job Description here", height=378, value=st.session_state.job_desc)

        submit_button = st.form_submit_button(label=f"Let {persona_choice} Roast Me! 🔥", use_container_width=True)

    # Triggering analysis
    if submit_button:
        # Determine resume text
        final_resume_text = ""
        if uploaded_file is not None:
            final_resume_text = extract_text_from_pdf(uploaded_file)
        else:
            final_resume_text = resume_pasted

        # Store in session state to persist
        st.session_state.resume_text = final_resume_text
        st.session_state.job_desc = job_desc_input

        if not final_resume_text.strip():
            st.error("Please upload a PDF resume or paste your resume text.")
        elif not job_desc_input.strip():
            st.error("Please provide the target Job Description.")
        else:
            with st.spinner(f"Contacting {persona_choice} to destroy your self-esteem..."):
                client = get_gemini_client(api_key_input)
                
                # Retrieve evaluation instruction rules
                system_prompt = selected_persona["system_instruction"]

                # Construct inputs for analysis payload
                prompt_content = f"""
                Analyze the following Resume against the Job Description.

                === RESUME ===
                {final_resume_text}

                === JOB DESCRIPTION ===
                {job_desc_input}
                """

                try:
                    response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=prompt_content,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            response_mime_type="application/json",
                            temperature=0.8,
                        ),
                    )
                    
                    # Store results in session state and pick a random stable meme template
                    st.session_state.analysis_results = json.loads(response.text)
                    st.session_state.selected_meme_index = random.randint(0, 1)
                    st.success("Analysis complete!")
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                        st.error("⚠️ Default API Key quota has been exhausted! Please paste your own Gemini API Key in the sidebar configuration to continue.")
                    else:
                        st.error(f"Error communicating with Gemini: {e}")

    # Displaying results from Session State if present
    if st.session_state.analysis_results:
        results = st.session_state.analysis_results
        
        st.divider()
        st.markdown(f"<h2 class='roast-header'>🔥 THE {persona_choice.upper()} ROAST</h2>", unsafe_allow_html=True)

        # 1. KPI Metrics
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.metric(label="Overall Rating", value=f"{results['overall_score']}/100", delta=f"{results['overall_score'] - 60} vs Approval")
        with m_col2:
            st.metric(label="Energy & Action Score", value=f"{results['action_verb_score']}/100")
        with m_col3:
            st.metric(label="Gap/Missing Items", value=len(results['missing_keywords']))
        with m_col4:
            st.metric(label="Weak Lines Highlighted", value=len(results['bullets_roast']))

        # 2. General Roast & Verdict
        st.markdown("### 🎙️ The Verdict")
        st.markdown(f"<div class='recruiter-commentary'>\"{results['fit_assessment']}\"</div>", unsafe_allow_html=True)
        st.write("")
        st.write(results['general_roast'])

        # 3. Render dynamic text meme cards using locally loaded approved webp images
        st.divider()
        render_meme(st.session_state.analysis_results.get("meme_lines", []))

        # 4. Missing Keywords Dashboard (Rendered as beautiful auto-wrapping badges to prevent scrolling)
        st.divider()
        st.markdown("### 🔑 Missing Requirements & Gap Analysis")
        st.write("Here is what was found in the job profile but was missing in your resume:")
        if results['missing_keywords']:
            badge_html = ""
            for kw in results['missing_keywords']:
                badge_html += f"<span style='background-color: #1e1e24; border: 1px solid {selected_persona['theme_color']}; color: white; border-radius: 12px; padding: 5px 12px; margin: 4px; display: inline-block; font-size: 14px; font-family: monospace;'>{kw}</span>"
            st.markdown(badge_html, unsafe_allow_html=True)
            st.write("")
        else:
            st.success("No missing elements! You actually followed directions.")

        # 5. Weak Bullet Points (Rendered as interactive, centered vertical list elements to prevent scrolling)
        st.markdown("### 📝 Detailed Section Critique")
        st.write("Review the feedback and copy improved suggestions for your weak resume lines:")
        
        for idx, item in enumerate(results['bullets_roast']):
            with st.container():
                col_check, col_content = st.columns([0.08, 0.92])
                with col_check:
                    fixed = st.checkbox("", key=f"fixed_{idx}")
                
                with col_content:
                    if fixed:
                        st.markdown(f"~~**Original Line**: {item['original']}~~ *(Marked as fixed)*")
                    else:
                        st.markdown(f"**Original Line**: `{item['original']}`")
                    
                    st.markdown(f"<div style='margin-bottom: 5px;'><span style='color:{selected_persona['theme_color']}; font-weight:bold; font-family: monospace;'>ROAST:</span> <i>{item['roast']}</i></div>", unsafe_allow_html=True)
                    st.markdown(f"<div><span style='color:#34c759; font-weight:bold; font-family: monospace;'>SUGGESTION:</span> <code>{item['suggestion']}</code></div>", unsafe_allow_html=True)
                    st.divider()

        # 6. Recovery Plan
        with st.expander("🛠️ Proposed Recovery Plan"):
            st.markdown(results['recovery_plan'])


else:
    # If nothing has been analyzed yet, show the pfp.png image
    if st.session_state.headshot_roast is None:
        pfp_img_path = Path(__file__).parent / "assets" / "pfp.png"
        if pfp_img_path.exists():
            c_space1, c_img, c_space2 = st.columns([0.1, 0.8, 0.1])
            with c_img:
                st.image(str(pfp_img_path), use_container_width=True)
            st.write("")

    st.subheader(f"📸 Vibe Check by {persona_choice}")
    st.write("Upload a professional headshot, avatar, or capture a quick selfie using your webcam. Gemini Vision will analyze your lighting, posture, dress code, and vibe in the style of your selected tormentor.")

    # Image upload / Camera Input options
    source_option = st.radio("Choose photo source:", ["Upload File", "Use Webcam Camera"], horizontal=True)
    
    img_data = None
    if source_option == "Upload File":
        img_file = st.file_uploader("Upload Profile Image (PNG/JPG)", type=["png", "jpg", "jpeg"])
        if img_file:
            img_data = img_file.read()
    else:
        cam_file = st.camera_input("Capture Selfie")
        if cam_file:
            img_data = cam_file.read()

    # Form to trigger analysis
    if img_data:
        st.image(img_data, width=300, caption="Vibe check subject")
        
        if st.button(f"Let {persona_choice} Rate My Vibe! 🧐", use_container_width=True):
            with st.spinner(f"{persona_choice} is staring judgingly at you..."):
                client = get_gemini_client(api_key_input)
                
                # Load selected persona vision evaluation rules
                vision_prompt = selected_persona["vision_instruction"]

                try:
                    # Perform vision model request
                    response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=[
                            types.Part.from_bytes(
                                data=img_data,
                                mime_type="image/jpeg"
                            ),
                            vision_prompt
                        ]
                    )
                    st.session_state.headshot_roast = response.text
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
                        st.error("⚠️ Default API Key quota has been exhausted! Please paste your own Gemini API Key in the sidebar configuration to continue.")
                    else:
                        st.error(f"Error analyzing image: {e}")

    # Display image roast
    if st.session_state.headshot_roast:
        st.divider()
        st.markdown(f"<h3 class='roast-header'>🔥 {persona_choice.upper()} VIBE CHECK</h3>", unsafe_allow_html=True)
        st.write(st.session_state.headshot_roast)
