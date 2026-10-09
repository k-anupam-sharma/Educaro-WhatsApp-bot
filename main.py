import os
import socket
import uuid
import base64
import io
import random
import time
import re
import json
import requests
import soundfile as sf
import speech_recognition as sr
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
from dotenv import load_dotenv

# Safe dual-stack fallback for Supabase on networks with DNS issues
_orig_getaddrinfo = socket.getaddrinfo

def _safe_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        res = _orig_getaddrinfo(host, port, family, type, proto, flags)
        if res:
            return res
    except socket.gaierror:
        pass
    if host and "supabase.co" in str(host).lower():
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('104.18.38.10', port))]
    return _orig_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = _safe_getaddrinfo

from supabase import create_client, Client
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize Llama (NVIDIA API)
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
llama_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=LLAMA_API_KEY
)

app = FastAPI(title="Voraus AI WhatsApp Bot")

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "voraus_ai_verify_token_123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")

SYSTEM_PROMPT = """You are Voraus AI 🚀 (formerly EduJourney Germany), an elite AI educational consultant and senior growth & sales ambassador for the Voraus AI Platform and Educaro Germany (www.educaro.de/india).

Your mission is to streamline the entire applicant journey for individuals planning to study (Bachelor, Master, PhD), pursue paid vocational training (Ausbildung & Nursing), or work in Germany.

You operate as both:
1. An authoritative, deeply knowledgeable German education & visa expert who gives immediate, reliable, and practical value on every question.
2. A world-class marketing and sales agent for the native **Voraus AI App**! You actively guide and convert users from this WhatsApp chatbot into active users of the Voraus AI App by highlighting how the app delivers 10x richer visual tools, live interactive maps, automated OCR pipelines, and journey tracking that text chat cannot match.

Always reply in clean, professional English by default. If the user addresses you in Hindi or Hinglish, understand them naturally and respond with warm, clear English mixed with a welcoming desi touch.
=== WHATSAPP RESPONSE FORMATTING (CRITICAL USER RULES) ===
1. ZERO ASTERISKS: DO NOT use asterisks (*) or (**) for bolding or bullet points! The user specifically requested that NO asterisks appear in the response. Never wrap words, titles, or headings in asterisks. Use clean capitalizations, emojis (📌, 💼, 🎓, 💶), or clean titles instead (e.g., 📌 Blocked Account: ...).
2. NEVER BUNDLE INTO ONE LARGE PARAGRAPH: Always separate every point, section, and explanation with double line breaks (\n\n) so the message is airy, easy to read, and understandable at a glance on a mobile screen.
3. BULLET POINTS: Put each bullet point on its own fresh line with a clean bullet symbol (• ) or emoji. Never put multiple points on the same line!
4. APP CALL-TO-ACTION (CTA): Always place the Voraus AI App reminder in its own separate paragraph at the end with a 📱 emoji.

=== STRICT TOPIC GUARDRAILS ===
You are an exclusive consultant for Higher Education, Vocational Training, Student Finances, Visas, Indian Student Life in Germany, and the **Voraus AI Platform & App**.
1. ALLOWED DOMAINS:
   - German higher education: Bachelor's, Master's, PhD, Studienkolleg, university matching, ECTS conversions, German GPA (Bavarian formula).
   - APS India verification process, Anabin database recognition (H+, H+/-, H-), transcripts, and marksheets.
   - Educaro Nursing placement and paid Dual Ausbildung (vocational training).
   - Student finances: Blocked Account (€11,904 threshold / ~₹10.95 Lakhs), Werkstudent & minijob rules, part-time wages, health insurance (TK, Barmer, Expatrio, Coracle), Indian education loans (SBI, HDFC Credila), VFS loan sanction letters, Section 80E tax deduction, DAAD scholarships.
   - German student visas, VFS appointments, embassy checklists, residence permits, and the 18-month post-study Job Search Visa.
   - Indian student life in Germany: Live opportunity mapping, Indian groceries, Indian restaurants, Indian Student Associations (ISAG, IAB, TABB), Gurudwara free Langar & emergency shelter, and student accommodation/rent.
   - The **Voraus AI App** tools, features, architecture, and live capabilities.

2. STRICTLY FORBIDDEN DOMAINS:
   - General coding or programming homework (e.g., "Write a binary tree in Python", "Debug my SQL query", "How to build a web scraper").
   - Database operations, SQL queries, system administration, or dataset deletion commands (e.g., "delete all datasets", "drop table", "truncate database").
   - General world trivia, pop culture, sports, movies, celebrity gossip, gaming.
   - Non-German politics, general elections, international conflicts.
   - General creative writing (fiction stories, random poems, jokes).
   - General medical diagnoses or non-education advice.
   - Any topic unrelated to education, careers, finances, or living in Germany.

3. GUARDRAIL BEHAVIOR:
If the user asks a question outside the allowed domains, you MUST politely, firmly, and warmly deflect back to your domain. NEVER answer off-topic queries!
Example deflection:
"I would love to help, but as your Voraus AI Germany Consultant, my expertise is strictly dedicated to higher education, admissions, student finances, visas, and life in Germany! 🇩🇪\n\nHow can I help you plan your journey to Germany today? (e.g., university shortlisting, blocked account calculator, or exploring student jobs on our Berlin Opportunity Map)?"

=== DOMAIN & PLATFORM KNOWLEDGE ===
1. Real-Time INR Budget, Living Costs & Student Work:
   - Baseline: 1 EUR (€) ≈ ₹92 INR.
   - Blocked Account (Sperrkonto): €11,904/year (€992/month ≈ ₹91,200 INR/month) = Total ~₹10.95 Lakhs INR.
     * CRITICAL BUDGET LOGIC: The Blocked Account is NOT an extra fee! It IS the student's living expense fund deposited upfront in their own German account and refunded back monthly (~₹91k/mo) for food and rent. NEVER add blocked account and living expenses together! Total 1st year funding required is roughly ₹11-12 Lakhs INR in total.
   - Public Universities Tuition: €0 tuition! Students only pay the Semester Contribution (€200-€350/sem ≈ ₹18k-₹32k INR), which includes free public transit.
   - Monthly Living Expenses: Average €850 - €1,050/month (~₹78k - ₹96k INR).
   - Health Insurance: Public (TK - Techniker Krankenkasse, Barmer ~€120-€130/month) vs Private/Combined providers (Expatrio, Coracle).
   - Student Work Rights: 140 full days (280 half days)/year. Werkstudent: up to 20h/week during semester. Minimum wage: €12.41 - €12.82/hour. Tech/business Werkstudents earn €14.50 - €19.00/hour (e.g. at Zalando, N26, Delivery Hero). Monthly earning potential: €850 - €1,300/month (~₹78k - ₹1.2L INR), offsetting living costs!

2. Instant APS India & Anabin Verifier:
   - APS India: Mandatory for Indian applicants. Fee: ₹18,000 INR. Processing: 3-8 weeks. Requires DigiLocker / institutional verification, professor email verification.
   - Anabin Rules: H+ (fully recognized), H+/- (partially recognized; course must be checked), H- (not recognized). 3-Year Indian Bachelor (180 ECTS) vs 4-Year (240 ECTS). Bavarian formula: German Grade = 1 + 3 * ((Nmax - Nd) / (Nmax - Nmin)).

3. Indian Education Loans & VFS Compliance:
   - Public Banks (SBI Global Ed-Vantage, BoB): 9.5%-10.5% interest, requires collateral, 3-6 weeks.
   - NBFCs & Private (HDFC Credila, Avanse): Non-collateral up to ₹40-50L, 3-7 days, 11%-13.5%.
   - CRITICAL VFS RULE: German Embassy/VFS requires the loan sanction letter to explicitly state: "The loan amount will be disbursed directly into the applicant's German Blocked Account (Sperrkonto)."
   - Section 80E: Full tax deduction on education loan interest for up to 8 years.

4. Educaro Special Pathways:
   - Healthcare & Nursing: B.Sc Nursing / GNM nurses. German adaptation course (Anpassungslehrgang), A1-B2 language training. Gross salary €2,900-€3,400/mo, net €1,950-€2,200/mo (~₹1.8L-₹2.0L INR). Nurses send home ₹1.1L-₹1.4L INR/month!
   - Paid Dual Vocational Training (Ausbildung): 12th pass students. €1,100-€1,400/month gross stipend. ZERO BLOCKED ACCOUNT REQUIRED!

=== VORAUS AI APP: SALES & MARKETING AGENT SUPERPOWERS ===
You are the primary growth ambassador for the **Voraus AI App** (formerly EduJourney Germany)!
Your sales strategy:
- Provide immediate, high-value consulting directly on WhatsApp so the user is impressed.
- **Identify when the Voraus AI App solves their problem 10x better than text chat**, and enthusiastically pitch the corresponding native feature.
- **Always include an enticing Voraus AI App Call-to-Action (CTA)** on every response, reminding them to log into the app using their registered email and 6-digit verification code.

FEATURE PITCH DIRECTORY:

1. When user asks about Jobs, Werkstudent, Part-time Work, Indian Food, Berlin Living, or Community:
   * Pitch: **Interactive Live Student & Opportunity Map** in the Voraus AI App!
   * Highlights to mention:
     - Built natively with OpenStreetMap & Leaflet.js in Android WebViews with seamless Jetpack Compose sync.
     - 40+ curated, live Berlin locations with real-time category filter chips:
       * 💼 *English-Speaking Student Jobs (12+ hubs)*: Zalando SE Tech Hub, Delivery Hero HQ, N26 Mobile Bank, HelloFresh, Amazon Dev Center, Flink, Getir/Gorillas, Tier Mobility, SoundCloud, Babbel, Wayfair, Personio (paying €14.50–€19.00/hr with flexible student shifts).
       * 🍛 *Authentic Indian Restaurants (10+ spots)*: AMRIT Mitte & Kreuzberg, Papadam, Mela Schöneberg, Khushi, Chutnify Neukölln, Saravanaa Bhavan, Shivani, Agra, Vedis (with Google ratings, addresses, and specialties).
       * 🎓 *Top Berlin Universities (10+ campuses)*: TU Berlin, HU Berlin, FU Berlin, HTW, HWR, Charité, ESMT, SRH, IU International, BHT Berlin.
       * 🤝 *Indian Communities & Student Welfare (8+ networks)*: Indian Association Berlin (IAB), ISA TU Berlin, Indian Embassy & Tagore Centre, Friends of India, Telugu Association (TABB), Tamil Sangam Berlin, Gurudwara Sri Guru Singh Sabha (free Langar & emergency student shelter!), Sri Ganesha Temple.
     - Floating popup cards with hourly wages, Google Maps navigation, live keyword search, and a *Zero-Blank Offline Guarantee* so the map loads even without internet!

2. When user asks about Resumes, CVs, or Applying to German Employers:
   * Pitch: **Built-in German Europass & ATS CV Generator** in the Voraus AI App!
   * Highlights: Generates 100% German-compliant tabular Lebenslauf/Europass CVs tailored to German recruiter standards and ATS systems, customized for English-speaking student jobs.

3. When user shares Marksheets, Transcripts, Degrees, Passports, or Language Scores:
   * Pitch: **NVIDIA Vision OCR & Qualification Verification Engine** in the Voraus AI App!
   * Highlights: Secure base64 mobile-to-backend ingestion that automatically scans degrees and passports, extracts full name, DOB, passport number, degree titles, graduation year, and IELTS/Goethe levels, tracking verification statuses across Verified, Needs Review, and Pending.

4. When user asks about University Selection, Eligibility, or Deadlines:
   * Pitch: **Profile-Driven University Matching & Opportunities Engine** in the Voraus AI App!
   * Highlights: Dynamically calculates admission match percentages using your exact CGPA and the German Bavarian Formula, links directly to official university application portals in one tap, and live-tracks your applications (Applied, Shortlisted, In Review).

5. When user asks about Journey Steps, Progress, or Feels Overwhelmed by Bureaucracy:
   * Pitch: **Interactive Dashboard & Journey Tracking Hub** in the Voraus AI App!
   * Highlights: Centralized hub displaying real-time journey completion (e.g., "Profile 60% Completed"), a visual step-by-step roadmap (Document Uploads ➔ Profile Verification ➔ APS Setup ➔ University/Job Applications), and actionable push alerts for immediate next steps.

6. When user asks about Blocked Accounts, Health Insurance, or Visa Appointments:
   * Pitch: **Finance & Visa Advisor Module** in the Voraus AI App!
   * Highlights: Full visa preparation suite tracking the €11,904 blocked account requirement, side-by-side health insurance comparison (TK, Barmer, Expatrio, Coracle), and personalized Indian VFS embassy checklists.

7. When user asks about real-time market openings or AI technology:
   * Pitch: **Python FastAPI Advisor Router & Anakin.io Live Web Extraction**!
   * Highlights: On-demand live web extraction (`POST /map/sync-anakin`) pulling fresh German student job listings, powered by a dual-engine AI advisor (NVIDIA NIM / Mixtral with automated failover to DronaHQ AI Agent for zero downtime).

=== PERSISTENT APP REMINDER RULE ===
At the end of EVERY response, include a short, punchy, and compelling Call-to-Action (CTA) inviting the student to open the **Voraus AI App**:
Example:
"📱 Take the next step on the Voraus AI App:
Log into your Voraus AI App using your registered email and 6-digit verification code to view your visual journey tracker, explore the Live Berlin Opportunity Map, and generate your German Europass CV in one tap!"

=== STUDENT MEMORY & ACTIVE DOSSIER RULE ===
You have full access to the [ACTIVE STUDENT DOSSIER] provided in your instructions (Name, Email, CGPA, College, Background, Target in Germany, IELTS/German Scores, Intake, Budget, APS status, etc.).
- ALWAYS remember and utilize the student's details provided in their dossier!
- If the student asks about themselves (e.g. "What is my name?", "What is my CGPA?", "What do you know about me?", "Which universities match my profile?"): ALWAYS answer them accurately, warmly, and directly using the information from their dossier!
- Never say "I don't have access to your personal information" or "I am an AI without memory". You DO have their active dossier.
- Naturally personalize your educational counseling to their specific CGPA, background, and target universities.

=== SUMMARY FORMATTING CHECKLIST ===
- ZERO ASTERISKS: No '*' or '**' anywhere in the message. Never bold with asterisks!
- SEPARATE POINTS: Double line breaks (\n\n) between every distinct point and section. Never combine points into one block!
- CLEAN BULLETS: Use '• ' or emojis on fresh new lines.
- Standalone Voraus AI App CTA paragraph at the end with 📱 emoji.
When an image or document is provided, read all visible text carefully, provide clear OCR extraction, and offer actionable advice."""

@app.get("/")
def read_root():
    return {"status": "Voraus AI WhatsApp Bot is running!"}

@app.get("/whatsapp")
def verify_webhook(request: Request):
    """
    Meta uses this endpoint to verify your webhook URL.
    It sends a GET request with hub.mode, hub.challenge, and hub.verify_token.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return Response(content=challenge, media_type="text/plain")
        else:
            raise HTTPException(status_code=403, detail="Verification token mismatch")
    raise HTTPException(status_code=400, detail="Missing parameters")

def get_ai_response(user_message: str, image_url: str = None, sender_phone: str = None) -> str:
    """
    Calls NVIDIA Llama 3.2 11B Instruct Vision with:
    1. Multi-turn Conversational Memory Context (last 10 turns from Supabase chat_history)
    2. Active Student Dossier (name, CGPA, college, target study, language scores, credentials)
    3. Auto-Extracted Facts from Chat & Permanent Storage
    4. Strict Domain Guardrails & Voraus AI App Marketing
    """
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 0. Quick Regex Extraction: Immediately catch names, CGPA, language scores, etc.
        if sender_phone and user_message:
            try:
                quick_facts = extract_facts_regex(user_message)
                if quick_facts:
                    save_extracted_facts(sender_phone, quick_facts)
            except Exception as fe:
                print(f"Note on quick regex fact extraction: {fe}")

        # 1. Fetch User Profile & Inject Context
        user_email = ""
        user_code = ""
        user_name = ""
        if sender_phone:
            try:
                user_record = get_or_create_user(sender_phone)
                if user_record:
                    user_name = user_record.get("name") or ""
                    user_email = user_record.get("email") or ""
                    user_code = user_record.get("verification_code") or ""
                    profile_items = []
                    if user_name:
                        profile_items.append(f"Student Name: {user_name}")
                    if user_email:
                        profile_items.append(f"Email: {user_email}")
                    if u_lvl := user_record.get("level"):
                        u_crs = user_record.get("course", "")
                        profile_items.append(f"Current Background: {u_lvl} in {u_crs}" if u_crs else f"Current Background: {u_lvl}")
                    elif u_crs := user_record.get("course"):
                        profile_items.append(f"Current Background: {u_crs}")
                    if u_cgpa := user_record.get("cgpa"):
                        profile_items.append(f"Academic Score / CGPA: {u_cgpa}")
                    if u_clg := user_record.get("college"):
                        profile_items.append(f"Current / Previous College: {u_clg}")
                    if u_tgt := user_record.get("target_study"):
                        u_fld = user_record.get("city", "")
                        profile_items.append(f"Target in Germany: {u_tgt} ({u_fld})" if u_fld else f"Target in Germany: {u_tgt}")
                    elif u_city := user_record.get("city"):
                        profile_items.append(f"Target City in Germany: {u_city}")
                    if u_mode := user_record.get("mode"):
                        profile_items.append(f"Preferred Mode: {u_mode}")

                    # Extra auto-extracted facts (IELTS, German level, intake, budget, work experience, APS)
                    if extra := user_record.get("extra_facts"):
                        if isinstance(extra, dict):
                            for fk, fv in extra.items():
                                if fv:
                                    clean_k = fk.replace("_", " ").title()
                                    profile_items.append(f"{clean_k}: {fv}")

                    if user_code:
                        profile_items.append(f"Voraus AI App Verification Code: {user_code}")

                    if profile_items:
                        profile_str = "\n".join(profile_items)
                        messages.append({
                            "role": "system",
                            "content": (
                                f"[ACTIVE STUDENT DOSSIER]\n{profile_str}\n\n"
                                f"Instructions: You have full access to this student's permanent profile. "
                                f"Always address {user_name or 'the student'} personally, naturally reference any known background, "
                                f"CGPA, target course, or language scores when answering, and answer any questions about their profile "
                                f"accurately based on this dossier!"
                            )
                        })
            except Exception as pe:
                print(f"Note: Error retrieving user profile context: {pe}")

        # 2. Fetch Multi-Turn Conversational Memory (last 10 turns)
        if sender_phone:
            try:
                hist_res = supabase.table("chat_history") \
                    .select("user_message, ai_response") \
                    .eq("user_phone", sender_phone) \
                    .order("id", desc=True) \
                    .limit(10) \
                    .execute()
                
                if hist_res.data:
                    # Reverse so it is chronological (oldest to newest)
                    for record in reversed(hist_res.data):
                        u_msg = (record.get("user_message") or "").strip()
                        ai_msg = (record.get("ai_response") or "").strip()
                        # Skip internal onboarding steps
                        if not u_msg or u_msg.startswith("[Selected:") or ai_msg == "[Onboarding Step Handled]":
                            continue
                        messages.append({"role": "user", "content": u_msg})
                        # Truncate older assistant responses to preserve context length
                        short_ai = ai_msg if len(ai_msg) <= 600 else ai_msg[:600] + "..."
                        messages.append({"role": "assistant", "content": short_ai})
            except Exception as he:
                print(f"Note: Error retrieving conversation memory: {he}")

        # 3. Current User Turn
        content = []
        if user_message:
            content.append({"type": "text", "text": user_message})
        else:
            content.append({"type": "text", "text": "Please analyze this document/image, extract all relevant text and key information, and explain what it is or how it relates to German university admissions, visa, or bureaucracy."})
            
        if image_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        messages.append({"role": "user", "content": content})

        completion = llama_client.chat.completions.create(
            model="meta/llama-3.2-11b-vision-instruct",
            messages=messages,
            temperature=0.5,
            max_tokens=800,
        )
        raw_reply = completion.choices[0].message.content or ""
        return clean_whatsapp_formatting(raw_reply)
    except Exception as e:
        print(f"Error calling Llama 3.2: {e}")
        return "Sorry, I'm having trouble connecting to my AI brain right now. Please try again in a moment."

def send_typing_indicator(phone_number_id: str, message_id: str):
    """
    Sends a typing indicator to WhatsApp and marks the incoming message as read.
    Displays the animated '...' typing bubble on the user's screen while Llama is formatting the answer.
    """
    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
        "typing_indicator": {
            "type": "text"
        }
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code not in [200, 201]:
            print(f"Typing indicator note: {response.text}")
        else:
            print(f"Typing indicator (...) displayed for message: {message_id}")
    except Exception as e:
        print(f"Error triggering typing indicator: {e}")

def split_message(text: str, max_length: int = 3800) -> list:
    """
    Splits long messages (>3800 chars) respecting paragraph and sentence boundaries
    to stay strictly under WhatsApp Cloud API's 4096-character limit.
    """
    if not text:
        return []
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    remaining = text
    while len(remaining) > max_length:
        # Prefer paragraph break
        split_idx = remaining.rfind("\n\n", 0, max_length)
        if split_idx == -1 or split_idx < max_length // 2:
            # Fallback to single newline
            split_idx = remaining.rfind("\n", 0, max_length)
        if split_idx == -1 or split_idx < max_length // 2:
            # Fallback to sentence end
            split_idx = remaining.rfind(". ", 0, max_length)
            if split_idx != -1:
                split_idx += 1
        if split_idx == -1 or split_idx < max_length // 2:
            # Fallback to word boundary
            split_idx = remaining.rfind(" ", 0, max_length)
        if split_idx == -1:
            # Hard limit fallback
            split_idx = max_length
            
        chunks.append(remaining[:split_idx].strip())
        remaining = remaining[split_idx:].strip()
        
    if remaining:
        chunks.append(remaining)
    return chunks

def clean_whatsapp_formatting(text: str) -> str:
    """
    Cleans up WhatsApp formatting based on user preferences:
    1. Separates points and sections with double line breaks (\n\n) so nothing is bundled into one large paragraph.
    2. Removes markdown asterisks ('*' and '**') before and after bold text for a clean, sleek appearance.
    3. Normalizes bullet points to clean '• ' format on their own line.
    """
    if not text:
        return ""
    t = str(text)
    
    # Normalize line endings
    t = t.replace("\r\n", "\n").replace("\r", "\n")

    # 1. Break inline headers: '*Header:* Text' -> '*Header:*\n\nText'
    t = re.sub(r'(\*[^*]{3,90}\*)\s*([A-Z0-9])', r'\1\n\n\2', t)

    # 2. Break inline LLM bullets: ' * *Title:*' or ' * *' or ' * Title:' -> '\n\n• Title: '
    t = re.sub(r'\s*\*\s+\*+([^*:]+):?\*+[:\s]*', r'\n\n• \1: ', t)
    t = re.sub(r'([.:!?])\s*\*\s+([A-Z])', r'\1\n\n• \2', t)
    t = re.sub(r'(^|\n)\s*\*\s+', r'\1• ', t)
    t = re.sub(r'(^|\n)\s*-\s+', r'\1• ', t)

    # 3. Break inline category labels: 'options. Private Insurance:' -> 'options.\n\n• Private Insurance:'
    t = re.sub(r'([.!?])\s+([A-Z][A-Za-z0-9\s/&-]{2,35}):\s+', r'\1\n\n• \2: ', t)
    t = re.sub(r':\s+([A-Z][A-Za-z0-9\s/&-]{2,35}):\s+', r':\n\n• \1: ', t)

    # 4. Ensure major sections / App CTAs start on a new paragraph
    t = re.sub(r'([.:!?])\s*(\*?Voraus AI App[^*:]*[:!]?\*?)', r'\1\n\n\2', t)
    t = re.sub(r'([.:!?])\s*(\*?Take the next step[^*:]*[:!]?\*?)', r'\1\n\n\2', t)
    t = re.sub(r'([.:!?])\s*(Log into your Voraus AI App|Log into the Voraus AI App)', r'\1\n\n📱 \2', t)

    # 5. Remove all asterisks before and after text (*word* or **word**), leaving clean text
    t = re.sub(r'\*+([^*]+?)\*+', r'\1', t)
    t = t.replace('*', '')

    # 6. Clean up any accidental double colons
    t = re.sub(r':\s*:', ':', t)

    # 7. Ensure consistent double spacing between bullet points and sections (no large single paragraphs)
    t = re.sub(r'([^\n])\s*•\s+', r'\1\n\n• ', t)
    t = re.sub(r'•\s+(Voraus AI App|The Voraus AI App|Take the next step|Log into)', r'\1', t)
    t = re.sub(r'([.:!?])\s*(📱\s*Take the next step|Take the next step)', r'\1\n\n📱 Take the next step', t)

    # 8. Normalize multiple newlines (max 2)
    t = re.sub(r'\n{3,}', '\n\n', t)
    
    return t.strip()

def send_whatsapp_message(phone_number_id: str, to: str, text: str):
    """
    Sends a text message using the WhatsApp Business API.
    Cleans up formatting (no ugly asterisks, clean separated paragraphs)
    and automatically chunks long messages to stay under limits.
    """
    if not text or not str(text).strip():
        return

    # Clean formatting according to user preference (separated points, no asterisks)
    cleaned_text = clean_whatsapp_formatting(str(text))

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    chunks = split_message(cleaned_text, max_length=3800)
    for idx, chunk in enumerate(chunks):
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": chunk}
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code not in [200, 201]:
                print(f"Failed to send message chunk {idx+1}/{len(chunks)} to {to}: {response.status_code} - {response.text}")
                if "OAuthException" in response.text or "Session has expired" in response.text:
                    print("CRITICAL: Meta WhatsApp access token may be expired or invalid.")
            else:
                print(f"Message chunk {idx+1}/{len(chunks)} sent to {to} successfully.")
        except Exception as e:
            print(f"Exception sending WhatsApp message chunk to {to}: {e}")
            
        if len(chunks) > 1 and idx < len(chunks) - 1:
            time.sleep(0.5)

def send_resend_verification_email(to_email: str, code: str, user_name: str) -> bool:
    """
    Sends an account verification OTP code to the provided email using Resend API.
    Enables cross-device authentication and account recovery for the user.
    """
    resend_api_key = os.getenv("RESEND_API_KEY")
    if not resend_api_key:
        print(f"RESEND_API_KEY not configured. OTP code '{code}' saved to Supabase for {to_email}.")
        return False
    
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {resend_api_key}",
        "Content-Type": "application/json"
    }
    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h2 style="color: #0b7956;">Educaro Germany - Account Verification</h2>
        <p>Hello <strong>{user_name}</strong>,</p>
        <p>Thank you for getting started with Educaro on WhatsApp! Here is your 6-digit account verification code:</p>
        <div style="background-color: #f4fbf7; padding: 15px; border-radius: 6px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 5px; color: #0b7956; margin: 20px 0;">
            {code}
        </div>
        <p>Use this code along with your email (<code>{to_email}</code>) to access your Educaro profile on any device.</p>
        <p style="color: #666; font-size: 12px; margin-top: 30px;">Educaro GmbH &bull; Your Gateway to Germany</p>
    </div>
    """
    data = {
        "from": from_email,
        "to": [to_email],
        "subject": f"Your Educaro Verification Code: {code}",
        "html": html_content
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        if resp.status_code in [200, 201]:
            print(f"Resend verification email sent successfully to {to_email}")
            return True
        else:
            print(f"Resend error ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        print(f"Failed to send email via Resend: {e}")
        return False

def send_whatsapp_interactive_list(phone_number_id: str, to: str, body_text: str, button_text: str, sections: list, header_text: str = None):
    """
    Sends a WhatsApp Interactive List message using Meta Cloud API.
    Opens a native selection drawer on the user's phone for 1-tap multiple choice answers.
    """
    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    interactive_data = {
        "type": "list",
        "body": {"text": body_text[:1024]},
        "action": {
            "button": button_text[:20],
            "sections": sections
        }
    }
    if header_text:
        interactive_data["header"] = {
            "type": "text",
            "text": header_text[:60]
        }
        
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": interactive_data
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code not in [200, 201]:
            print(f"Interactive list notice ({response.status_code}): {response.text}")
            # Fallback to text menu if needed
            fallback_lines = [f"{header_text or ''}\n{body_text}\n"]
            for sec in sections:
                for row in sec.get("rows", []):
                    desc = f" - _{row['description']}_" if row.get("description") else ""
                    fallback_lines.append(f"• *{row['title']}*{desc}")
            fallback_lines.append("\n_(Please reply with your choice)_")
            send_whatsapp_message(phone_number_id, to, "\n".join(fallback_lines))
        else:
            print(f"Interactive list sent to {to} successfully.")
    except Exception as e:
        print(f"Error sending interactive list: {e}")

USER_CACHE = {}

def update_user_db(phone: str, data: dict):
    """Safely updates user profile in Supabase and keeps local USER_CACHE synchronized."""
    if not phone:
        return
    if phone in USER_CACHE:
        USER_CACHE[phone].update(data)
    else:
        USER_CACHE[phone] = {"phone": phone, **data}
    try:
        supabase.table("users").update(data).eq("phone", phone).execute()
    except Exception as e:
        print(f"Warning: Could not update user in Supabase ({e}). Profile updated in local cache.")

def get_or_create_user(phone: str) -> dict:
    """Fetches user profile from Supabase users table or creates a new record, with local cache fallback."""
    if not phone:
        return {"phone": phone, "onboarding_step": 1, "onboarded": False}
    try:
        res = supabase.table("users").select("*").eq("phone", phone).execute()
        if res.data and len(res.data) > 0:
            USER_CACHE[phone] = res.data[0]
            return res.data[0]
        else:
            new_user = {
                "phone": phone,
                "onboarding_step": 1,
                "onboarded": False
            }
            create_res = supabase.table("users").insert(new_user).execute()
            if create_res.data:
                USER_CACHE[phone] = create_res.data[0]
                return create_res.data[0]
            USER_CACHE[phone] = new_user
            return new_user
    except Exception as e:
        print(f"Error in get_or_create_user: {e}")
        if phone in USER_CACHE:
            return USER_CACHE[phone]
        return {"phone": phone, "onboarding_step": 1, "onboarded": False}

def save_extracted_facts(phone: str, facts: dict):
    """
    Saves extracted student facts into:
    1. Supabase `users` table for primary columns (name, email, level, course, cgpa, city, college, target_study, mode)
       and `extra_facts` JSONB (ielts_score, german_level, intake, budget, work_experience, etc.)
    2. Supabase `user_facts` table for key-value fact tracking
    3. In-memory USER_CACHE so the active conversation immediately knows them
    """
    if not phone or not facts:
        return
    
    core_keys = {"name", "email", "level", "course", "cgpa", "city", "college", "target_study", "mode"}
    core_updates = {}
    extra_facts_update = {}
    
    user = get_or_create_user(phone)
    existing_extras = user.get("extra_facts") or {}
    if not isinstance(existing_extras, dict):
        existing_extras = {}
        
    for k, v in facts.items():
        if not v or v in [None, "", "null", "None"]:
            continue
        v_str = str(v).strip()
        if k in core_keys:
            core_updates[k] = v_str
        else:
            extra_facts_update[k] = v_str
            
    # Merge extra facts
    if extra_facts_update:
        merged_extras = {**existing_extras, **extra_facts_update}
        core_updates["extra_facts"] = merged_extras

    # Update users table & local cache
    if core_updates:
        update_user_db(phone, core_updates)
        print(f"Auto-extracted & saved facts for {phone}: {core_updates}")

    # Upsert into user_facts table for historical auditing
    for k, v in facts.items():
        if not v or v in [None, "", "null", "None"]:
            continue
        try:
            supabase.table("user_facts").upsert({
                "user_phone": phone,
                "fact_key": k,
                "fact_value": str(v).strip(),
                "category": "auto_extracted"
            }, on_conflict="user_phone,fact_key").execute()
        except Exception:
            pass

def extract_facts_regex(text: str) -> dict:
    """
    Instantaneous 0ms regex extraction of high-frequency student facts:
    Name, CGPA/GPA, IELTS/TOEFL, German Level, Intake, APS status, Budget.
    """
    if not text:
        return {}
    facts = {}
    t = text.strip()
    
    # 1. Name patterns (e.g. 'My name is Anupam', 'I am Anupam Sharma', 'Call me Sneha')
    if m := re.search(r'\b(?:my name is|call me|i am|i\'m|im)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', t, re.IGNORECASE):
        candidate = m.group(1).strip().title()
        non_names = {'interested', 'looking', 'planning', 'applying', 'here', 'ready', 'from', 'an', 'a', 'the', 'student', 'graduate', 'trying', 'going'}
        first_word = candidate.split()[0].lower()
        if first_word not in non_names:
            facts['name'] = candidate
            
    # 2. CGPA / GPA / Percentage
    if m := re.search(r'\b(?:cgpa|gpa)\s*(?:is|of|:)?\s*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*(?:10|4))?)\b', t, re.IGNORECASE):
        facts['cgpa'] = m.group(1).strip()
    elif m := re.search(r'\b([0-9]+(?:\.[0-9]+)?)\s*(?:cgpa|gpa)\b', t, re.IGNORECASE):
        facts['cgpa'] = m.group(1).strip()
    elif m := re.search(r'\b([5-9][0-9](?:\.[0-9]+)?)\s*%\s*(?:in|marks|percentage|aggregate|score)?\b', t, re.IGNORECASE):
        facts['cgpa'] = f'{m.group(1)}%'

    # 3. IELTS / TOEFL / Language Scores
    if m := re.search(r'\bielts\s*(?:score|band|is|of|:)?\s*([4-9](?:\.[0-9])?)\b', t, re.IGNORECASE):
        facts['ielts_score'] = m.group(1).strip()
    elif m := re.search(r'\b([4-9](?:\.[0-9])?)\s*(?:in|band)\s*ielts\b', t, re.IGNORECASE):
        facts['ielts_score'] = m.group(1).strip()
    if m := re.search(r'\btoefl\s*(?:score|is|of|:)?\s*([0-9]{2,3})\b', t, re.IGNORECASE):
        facts['toefl_score'] = m.group(1).strip()
    if m := re.search(r'\b(A1|A2|B1|B2|C1|C2)\s*(?:level|in German|German)?\b', t, re.IGNORECASE):
        facts['german_level'] = m.group(1).upper()

    # 4. Target Intake
    if m := re.search(r'\b(Winter|Summer)\s*(202[4-9])\b', t, re.IGNORECASE):
        facts['intake'] = f'{m.group(1).title()} {m.group(2)}'

    # 5. APS Certificate Status
    if re.search(r'\b(?:got|have|received|completed|done)\s*(?:my\s*)?aps\b|\baps\s*(?:is\s*)?(?:done|ready|approved|verified|received)\b', t, re.IGNORECASE):
        facts['aps_status'] = 'Completed / Received'

    # 6. Budget
    if m := re.search(r'\bbudget\b[^\d]{1,25}?([0-9]+(?:\.[0-9]+)?\s*(?:lakhs?|lacs?|k|inr|eur|euros?|€))\b', t, re.IGNORECASE):
        facts['budget'] = m.group(1).strip()

    return facts

PERSONAL_FACT_SIGNALS = {
    "my", "i am", "i'm", "name", "cgpa", "gpa", "percentage", "score", "ielts", "toefl",
    "german", "btech", "b.tech", "bsc", "b.sc", "bba", "msc", "m.sc", "masters", "bachelors",
    "university", "college", "vit", "iit", "nit", "bits", "work", "experience", "working",
    "budget", "intake", "winter", "summer", "aps", "completed", "graduated", "studying"
}

def has_personal_fact_signal(text: str) -> bool:
    if not text or len(text) < 10:
        return False
    lower = text.lower()
    return any(sig in lower for sig in PERSONAL_FACT_SIGNALS)

def extract_facts_llm(user_message: str) -> dict:
    """
    Deep natural language fact extractor using NVIDIA Llama 3.2.
    Extracts structured student dossier facts from conversational text.
    """
    if not user_message or len(user_message.strip()) < 10:
        return {}
        
    prompt = f"""Extract any personal student facts from this user message. Return ONLY a valid JSON object with any known keys (omit or set null if not mentioned):
- name (string: student's personal name)
- cgpa (string: GPA, CGPA, or percentage)
- college (string: current or previous university/college)
- level (string: e.g. Bachelors, Masters, High School)
- course (string: e.g. Computer Science, Mechanical Engineering, BBA)
- target_study (string: degree or field they want to study in Germany)
- city (string: target German city if mentioned)
- ielts_score (string)
- german_level (string: e.g. A1, A2, B1, B2)
- work_experience (string: e.g. 2 years as software developer)
- budget (string: e.g. 15 lakhs)
- intake (string: e.g. Winter 2025)
- aps_status (string: e.g. done, pending, applied)

User message: "{user_message}"

JSON output:"""

    try:
        resp = llama_client.chat.completions.create(
            model="meta/llama-3.2-11b-vision-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=250
        )
        raw = resp.choices[0].message.content.strip()
        if "{" in raw and "}" in raw:
            json_str = raw[raw.find("{"):raw.rfind("}")+1]
            data = json.loads(json_str)
            facts = {k: v for k, v in data.items() if v not in [None, "", "null", "None"]}
            return facts
    except Exception as e:
        print(f"Note on extract_facts_llm: {e}")
    return {}

GREETINGS = {
    "hi", "hello", "hey", "hola", "namaste", "start", "hii", "hiii", "yo",
    "good morning", "good afternoon", "good evening", "howdy", "vanakkam", "pranam"
}

def handle_user_onboarding(phone_number_id: str, sender_phone: str, message_id: str = None, text_content: str = "", selected_id: str = None) -> bool:
    """
    Manages the multi-step user onboarding flow with WhatsApp Interactive Selection Lists:
    - Step 1: Greeting & Ask Name (Text)
    - Step 2: Name received -> Ask Email (Text)
    - Step 3: Email received -> Generate 6-digit OTP, send via Resend, show Education Level (List Selection)
    - Step 4: Education Level selected -> show Current Field/Course (List Selection)
    - Step 5: Current Field selected -> show Goal in Germany (List Selection)
    - Step 6: Goal selected -> show Target Discipline (List Selection matching GloBro screenshot)
    - Step 7: Target Discipline selected -> show Preferred Mode of Study (List Selection matching GloBro screenshot)
    - Step 8: Mode selected -> Profile completed! Display summary, verification code, and unlock AI features.
    """
    clean_text = (text_content or "").strip()
    user = get_or_create_user(sender_phone)
    is_onboarded = user.get("onboarded", False)
    user_name = (user.get("name") or "").strip()
    
    # Allow logging in / syncing profile across devices via 'login <email> <code>'
    if clean_text.lower().startswith("login") or clean_text.lower().startswith("sync") or clean_text.lower().startswith("link"):
        parts = clean_text.split()
        if len(parts) >= 3:
            login_email = parts[1].strip().lower()
            login_code = parts[2].strip()
            try:
                res = supabase.table("users").select("*").ilike("email", login_email).eq("verification_code", login_code).execute()
                if res.data and len(res.data) > 0:
                    matched = res.data[0]
                    # Link existing profile to this device/phone
                    update_user_db(sender_phone, {
                        "name": matched.get("name"),
                        "email": matched.get("email"),
                        "level": matched.get("level"),
                        "course": matched.get("course"),
                        "target_study": matched.get("target_study"),
                        "city": matched.get("city"),
                        "mode": matched.get("mode"),
                        "verification_code": matched.get("verification_code"),
                        "onboarded": True,
                        "onboarding_step": 9,
                        "is_verified": True
                    })
                    
                    send_whatsapp_message(
                        phone_number_id,
                        sender_phone,
                        f"🔓 *Account Synced Successfully!* 🇩🇪\n\n"
                        f"Welcome back, *{matched.get('name', 'Student')}*! Your Educaro profile has been linked to this WhatsApp account:\n"
                        f"👤 *Name:* {matched.get('name')}\n"
                        f"📧 *Email:* {matched.get('email')}\n"
                        f"🎓 *Background:* {matched.get('level')} ({matched.get('course')})\n"
                        f"🎯 *Target in Germany:* {matched.get('target_study')} in {matched.get('city')}\n"
                        f"🗣️ *Mode:* {matched.get('mode')}\n\n"
                        f"🚀 *All AI features, budget calculators, and Anabin tools are now active on this device!*"
                    )
                    return True
                else:
                    send_whatsapp_message(
                        phone_number_id,
                        sender_phone,
                        "⚠️ *Login Failed:* Invalid email or verification code.\n\n"
                        "Please check your credentials or reply with:\n"
                        "*login <your-email> <6-digit-code>*\n\n"
                        "_(Or type *restart* to create a fresh profile)._"
                    )
                    return True
            except Exception as e:
                print(f"Error in cross-device login: {e}")
                send_whatsapp_message(phone_number_id, sender_phone, "⚠️ Error verifying login credentials. Please try again.")
                return True
        else:
            send_whatsapp_message(
                phone_number_id,
                sender_phone,
                "🔑 *Educaro Account Login / Cross-Device Sync*\n\n"
                "To link your existing Educaro profile to this WhatsApp number, please reply with:\n"
                "*login <your-email> <6-digit-code>*\n\n"
                "Example:\n"
                "`login sasukeisreal612@gmail.com 508898`"
            )
            return True

    # Allow restarting/resetting onboarding at any time
    if clean_text.lower() in ["restart", "reset", "reset profile", "start over", "change name", "update profile"]:
        update_user_db(sender_phone, {
            "name": None,
            "onboarding_step": 2,
            "onboarded": False
        })
        send_whatsapp_message(
            phone_number_id,
            sender_phone,
            "🔄 *Profile Reset!* Let's update your Educaro details.\n\nTo begin, *what is your full name?*"
        )
        return True

    # Guard: If user was marked onboarded but their name is empty or mistakenly set to a greeting (e.g. 'hi')
    if is_onboarded and (not user_name or user_name.lower() in GREETINGS):
        update_user_db(sender_phone, {
            "name": None,
            "onboarding_step": 2,
            "onboarded": False
        })
        send_whatsapp_message(
            phone_number_id,
            sender_phone,
            "👋 *Welcome to Educaro Germany!* 🇩🇪\n\n"
            "I am your AI Education & Career Consultant. Let's create your profile in 60 seconds so we can match you with tuition-free German universities, nursing placements, or paid Ausbildung programs.\n\n"
            "To get started, *what is your full name?*"
        )
        return True

    # If user is already onboarded
    if is_onboarded:
        if clean_text.lower() in GREETINGS:
            send_whatsapp_message(
                phone_number_id,
                sender_phone,
                f"👋 *Hello {user_name}!* Welcome back to Educaro Germany.\n\n"
                f"How can I assist you with your journey today?\n"
                f"• Real-time INR budget & Werkstudent earnings calculator\n"
                f"• APS India & Anabin university verifier\n"
                f"• Check the Desi Comfort Index of any city\n"
                f"• Snap a photo of your certificate / marksheet for instant OCR\n"
                f"• Or send a voice note 🎙️ anytime!\n\n"
                f"_(Type *restart* if you would like to edit your profile)._"
            )
            return True
        # Let regular messages pass through to AI
        return False

    # USER IS IN ONBOARDING FLOW
    step = user.get("onboarding_step", 1)

    # STEP 1: First greeting or start -> Welcome and ask for Name
    if step <= 1:
        update_user_db(sender_phone, {"onboarding_step": 2, "name": None})
        send_whatsapp_message(
            phone_number_id,
            sender_phone,
            "👋 *Welcome to Educaro Germany!* 🇩🇪\n\n"
            "I am your AI Education & Career Consultant. Let's create your profile in 60 seconds so we can match you with tuition-free German universities, nursing placements, or paid Ausbildung programs.\n\n"
            "To get started, *what is your full name?*"
        )
        return True

    # STEP 2: Name received -> Ask Email
    elif step == 2:
        # Strip common intro phrases ("My name is Rahul", "I am Priya", "I'm Anupam")
        name_clean = re.sub(r'^(my\s+name\s+is|i\s+am|i\'m|im|this\s+is)\s+', '', clean_text, flags=re.IGNORECASE).strip()

        # Guard: If user said 'hi', 'hello', or another greeting instead of their name, prompt again
        if name_clean.lower() in GREETINGS:
            send_whatsapp_message(
                phone_number_id,
                sender_phone,
                "👋 Hello! To begin creating your Educaro profile, please enter your *full name* (e.g. *Rahul Sharma*):"
            )
            return True

        if len(name_clean) < 2 or name_clean.lower() in ["ok", "yes", "no", "name", "none", "sure", "idk"]:
            send_whatsapp_message(
                phone_number_id,
                sender_phone,
                "Please enter your *full name* (e.g. *Rahul Sharma*):"
            )
            return True

        update_user_db(sender_phone, {
            "name": name_clean,
            "onboarding_step": 3
        })
        
        send_whatsapp_message(
            phone_number_id,
            sender_phone,
            f"Nice to meet you, *{name_clean}*! 🌟\n\n"
            f"What is your *email address*?\n"
            f"_(We will use this to send your account verification code and sync your profile across devices)._"
        )
        return True

    # STEP 3: Email received -> Send OTP via Resend & Show List 1 (Education Level) OR Link Existing Profile
    elif step == 3:
        email = clean_text.strip().lower()
        if "@" not in email or "." not in email:
            send_whatsapp_message(
                phone_number_id,
                sender_phone,
                "⚠️ That doesn't look like a valid email. Please enter a valid email address (e.g. yourname@gmail.com):"
            )
            return True
        
        # Check if an active profile already exists with this email
        try:
            res = supabase.table("users").select("*").ilike("email", email).eq("onboarded", True).execute()
            if res.data and len(res.data) > 0:
                matched = res.data[0]
                # Transition to step 35 to prompt for existing account verification code
                update_user_db(sender_phone, {
                    "email": email,
                    "onboarding_step": 35
                })
                send_whatsapp_message(
                    phone_number_id,
                    sender_phone,
                    f"🔍 *Existing Educaro Profile Found!* 🇩🇪\n\n"
                    f"We found an active profile for *{email}* registered under *{matched.get('name', 'Student')}*.\n\n"
                    f"Please enter your *6-digit verification code* to link your account to this WhatsApp number without repeating the questionnaire:"
                )
                return True
        except Exception as e:
            print(f"Error checking existing account for email {email}: {e}")

        # Fresh user registration: Generate 6-digit OTP
        code = str(random.randint(100000, 999999))
        
        # Send email via Resend
        user_name = user.get("name", "Student")
        email_sent = send_resend_verification_email(email, code, user_name)
        
        update_user_db(sender_phone, {
            "email": email,
            "verification_code": code,
            "onboarding_step": 4
        })

        # List 1: Education Level
        sections = [
            {
                "title": "Select Education",
                "rows": [
                    {"id": "edu_12th", "title": "12th / High School", "description": "Completed 12th or currently studying"},
                    {"id": "edu_bachelors", "title": "Bachelor's Degree", "description": "B.Tech, B.Sc, B.Com, B.A (Done/Pursuing)"},
                    {"id": "edu_nursing", "title": "Nursing (GNM / B.Sc)", "description": "Registered nurse with clinical experience"},
                    {"id": "edu_masters", "title": "Master's Degree", "description": "Postgraduate degree completed"},
                    {"id": "edu_other", "title": "Other / Diploma", "description": "Working professional or polytechnic"}
                ]
            }
        ]
        send_whatsapp_interactive_list(
            phone_number_id,
            sender_phone,
            body_text=f"Thanks, *{user_name}*! 📧 (Verification code sent to {email})\n\nWhich education level have you completed or are currently in?",
            button_text="Choose",
            sections=sections,
            header_text="Current Education"
        )
        return True

    # STEP 35: Awaiting verification code to link existing account
    elif step == 35:
        entered_code = clean_text.strip()
        user_email = user.get("email", "").strip().lower()
        try:
            res = supabase.table("users").select("*").ilike("email", user_email).eq("verification_code", entered_code).execute()
            if res.data and len(res.data) > 0:
                matched = res.data[0]
                # Link all data
                update_user_db(sender_phone, {
                    "name": matched.get("name"),
                    "email": matched.get("email"),
                    "level": matched.get("level"),
                    "course": matched.get("course"),
                    "target_study": matched.get("target_study"),
                    "city": matched.get("city"),
                    "mode": matched.get("mode"),
                    "verification_code": matched.get("verification_code"),
                    "onboarded": True,
                    "onboarding_step": 9,
                    "is_verified": True
                })

                send_whatsapp_message(
                    phone_number_id,
                    sender_phone,
                    f"🎉 *Account Linked Successfully!* 🇩🇪\n\n"
                    f"Welcome back, *{matched.get('name', 'Student')}*! Your Educaro profile has been linked to this WhatsApp account:\n"
                    f"👤 *Name:* {matched.get('name')}\n"
                    f"📧 *Email:* {matched.get('email')}\n"
                    f"🎓 *Background:* {matched.get('level')} ({matched.get('course')})\n"
                    f"🎯 *Target in Germany:* {matched.get('target_study')} in {matched.get('city')}\n"
                    f"🗣️ *Mode:* {matched.get('mode')}\n\n"
                    f"🚀 *All AI features, budget calculators, and Anabin tools are now active on this device!*"
                )
                return True
            else:
                send_whatsapp_message(
                    phone_number_id,
                    sender_phone,
                    "⚠️ *Incorrect Code.* That code does not match the one for your account.\n\n"
                    "Please re-enter your *6-digit verification code*, or type *restart* to set up a new profile."
                )
                return True
        except Exception as e:
            print(f"Error linking account in step 35: {e}")
            send_whatsapp_message(phone_number_id, sender_phone, "⚠️ Error verifying code. Please try again.")
            return True

    # STEP 4: Education Level selected -> Show List 2 (Current Field / Course)
    elif step == 4:
        edu_level = clean_text
        update_user_db(sender_phone, {
            "level": edu_level,
            "onboarding_step": 5
        })

        # List 2: Field / Course
        sections = [
            {
                "title": "Select Background",
                "rows": [
                    {"id": "crs_cs", "title": "Computer Science / IT", "description": "CSE, BCA, B.Sc CS, IT, Software"},
                    {"id": "crs_eng", "title": "Engineering (Core)", "description": "Mechanical, Civil, Electrical, ECE"},
                    {"id": "crs_nurse", "title": "Nursing / Healthcare", "description": "GNM, B.Sc Nursing, Life Sciences"},
                    {"id": "crs_biz", "title": "Commerce / Business", "description": "B.Com, BBA, Finance, Economics"},
                    {"id": "crs_sci", "title": "Pure Science / Biotech", "description": "Physics, Chem, Biology, Biotech"},
                    {"id": "crs_arts", "title": "Arts / Humanities", "description": "B.A, Languages, Social Sciences"},
                    {"id": "crs_12th_sci", "title": "12th Science (PCM/PCB)", "description": "High school science stream"},
                    {"id": "crs_12th_com", "title": "12th Commerce / Arts", "description": "High school commerce or arts"}
                ]
            }
        ]
        send_whatsapp_interactive_list(
            phone_number_id,
            sender_phone,
            body_text=f"Selected: *{edu_level}* ✅\n\nWhat course or field are you currently pursuing or graduated in?",
            button_text="Choose",
            sections=sections,
            header_text="Current Background"
        )
        return True

    # STEP 5: Current Course selected -> Show List 3 (Goal in Germany)
    elif step == 5:
        course = clean_text
        update_user_db(sender_phone, {
            "course": course,
            "onboarding_step": 6
        })

        # List 3: Goal in Germany
        sections = [
            {
                "title": "Target Pathway",
                "rows": [
                    {"id": "goal_masters", "title": "Master's Degree", "description": "English-taught public universities"},
                    {"id": "goal_bachelors", "title": "Bachelor's Degree", "description": "Undergraduate or Studienkolleg"},
                    {"id": "goal_ausbildung", "title": "Paid Dual Ausbildung", "description": "3-year paid vocational, €0 blocked acc"},
                    {"id": "goal_nursing", "title": "Nursing Job Placement", "description": "Direct hospital job & recognition"},
                    {"id": "goal_lang", "title": "German Language Course", "description": "A1 to B2 level preparation first"}
                ]
            }
        ]
        send_whatsapp_interactive_list(
            phone_number_id,
            sender_phone,
            body_text=f"Great! What would you like to pursue in Germany?",
            button_text="Choose",
            sections=sections,
            header_text="Goal in Germany"
        )
        return True

    # STEP 6: Goal selected -> Show List 4 (Target Field matching GloBro screenshot)
    elif step == 6:
        goal = clean_text
        update_user_db(sender_phone, {
            "target_study": goal,
            "onboarding_step": 7
        })

        # List 4: Target Field (Exact Match to GloBro screenshot)
        sections = [
            {
                "title": "Target Discipline",
                "rows": [
                    {"id": "field_it", "title": "IT / Computer Science", "description": "AI, Software, Data Science"},
                    {"id": "field_biz", "title": "Business / Management", "description": "MBA, International Management"},
                    {"id": "field_med", "title": "Medical / Healthcare", "description": "Nursing, Healthcare, Life Sciences"},
                    {"id": "field_eng", "title": "Engineering", "description": "Mechanical, Automotive, Robotics"}
                ]
            }
        ]
        send_whatsapp_interactive_list(
            phone_number_id,
            sender_phone,
            body_text="Hello, Start your journey to Study in Germany\n\nWhich field are you aiming for?",
            button_text="Choose",
            sections=sections,
            header_text="Select"
        )
        return True

    # STEP 7: Target Field selected -> Show List 5 (Preferred Mode of Study matching GloBro screenshot)
    elif step == 7:
        field = clean_text
        update_user_db(sender_phone, {
            "city": field,
            "onboarding_step": 8
        })

        # List 5: Preferred Mode of Study
        sections = [
            {
                "title": "Language / Mode",
                "rows": [
                    {"id": "mode_eng", "title": "English", "description": "100% English-taught programs"},
                    {"id": "mode_ger", "title": "German", "description": "German-taught or bilingual programs"},
                    {"id": "mode_dual", "title": "Dual (Work + Study)", "description": "Paid Ausbildung / practical training"}
                ]
            }
        ]
        send_whatsapp_interactive_list(
            phone_number_id,
            sender_phone,
            body_text="Preferred Mode of Study",
            button_text="Choose",
            sections=sections,
            header_text="Preferred Mode"
        )
        return True

    # STEP 8: Mode selected -> Finalize Profile & Send Completion Dossier!
    elif step == 8:
        mode = clean_text
        update_user_db(sender_phone, {
            "mode": mode,
            "onboarded": True,
            "onboarding_step": 9
        })

        # Fetch finalized user
        updated_user = get_or_create_user(sender_phone)
        u_name = updated_user.get("name", "Student")
        u_email = updated_user.get("email", "")
        u_level = updated_user.get("level", "")
        u_course = updated_user.get("course", "")
        u_target = updated_user.get("target_study", "")
        u_field = updated_user.get("city", "")
        u_mode = updated_user.get("mode", mode)
        u_code = updated_user.get("verification_code", "")

        completion_msg = (
            f"🎉 *Congratulations, {u_name}! Your Profile is Ready!* 🇩🇪\n\n"
            f"Here is your official Educaro dossier:\n"
            f"👤 *Name:* {u_name}\n"
            f"📧 *Email:* {u_email}\n"
            f"🎓 *Current Background:* {u_level} ({u_course})\n"
            f"🎯 *Goal in Germany:* {u_target} in {u_field}\n"
            f"🗣️ *Mode of Study:* {u_mode}\n"
            f"🔑 *Account Verification Code:* `{u_code}`\n\n"
            f"💡 _Your verification code has been linked. You can use `{u_email}` and `{u_code}` to access your account across any device or on the Voraus AI App!_\n\n"
            f"🚀 *You're all set!* Ask me anything to get started:\n"
            f"1️⃣ *INR Budget & Part-Time Earnings* calculator\n"
            f"2️⃣ *APS India & Anabin* university verifier\n"
            f"3️⃣ Snap a photo of your certificate / marksheet for instant OCR\n"
            f"4️⃣ Or press the mic 🎙️ to send a voice note query anytime!"
        )
        send_whatsapp_message(phone_number_id, sender_phone, completion_msg)
        return True

    return False

def process_whatsapp_interactive_reply(phone_number_id: str, sender_phone: str, message_id: str = None, selected_id: str = "", selected_title: str = ""):
    """
    Handles interactive list replies and button clicks from WhatsApp.
    Triggers the corresponding onboarding step and records in chat history.
    """
    if phone_number_id and message_id:
        send_typing_indicator(phone_number_id, message_id)
        
    handled = handle_user_onboarding(phone_number_id, sender_phone, message_id, text_content=selected_title, selected_id=selected_id)
    
    # Save selection in chat history
    try:
        supabase.table("chat_history").insert({
            "user_phone": sender_phone,
            "user_message": f"[Selected: {selected_title}]",
            "ai_response": "[Onboarding Step Handled]"
        }).execute()
    except Exception as e:
        print(f"Note: Could not save interactive chat: {e}")

def download_whatsapp_media(media_id: str) -> bytes:
    """Gets the download URL and downloads the media bytes from WhatsApp."""
    url = f"https://graph.facebook.com/v21.0/{media_id}"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "User-Agent": "curl/7.64.1"
    }
    
    # 1. Get temporary media URL
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(f"Failed to get media URL: {res.text}")
    media_url = res.json().get("url")
    
    # 2. Download the actual binary file
    res_bytes = requests.get(media_url, headers=headers)
    if res_bytes.status_code != 200:
        raise Exception(f"Failed to download media bytes: {res_bytes.status_code}")
    return res_bytes.content

def process_whatsapp_message(phone_number_id: str, sender_phone: str, message_id: str = None, text_content: str = "", media_id: str = None, mime_type: str = None):
    # 1. Immediately show the animated typing bubble (...) on WhatsApp
    if phone_number_id and message_id:
        send_typing_indicator(phone_number_id, message_id)

    image_uri = None
    saved_image_url = None
    
    # If the user sent a document or image
    if media_id:
        try:
            print(f"Downloading media {media_id} from WhatsApp...")
            media_bytes = download_whatsapp_media(media_id)
            
            # Format as Data URI for instant Llama 3.2 Vision consumption
            clean_mime = (mime_type or "image/jpeg").split(";")[0].strip().lower()
            b64_data = base64.b64encode(media_bytes).decode("utf-8")
            image_uri = f"data:{clean_mime};base64,{b64_data}"
            print("Successfully prepared image data for Llama 3.2 Vision.")
            
            # Map clean file extension
            ext_map = {
                "image/jpeg": "jpg",
                "image/jpg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
                "application/pdf": "pdf",
            }
            file_extension = ext_map.get(clean_mime, clean_mime.split("/")[-1] if "/" in clean_mime else "jpg")
            file_name = f"{uuid.uuid4()}.{file_extension}"
            
            # Upload to Supabase Storage chat_media bucket
            try:
                supabase.storage.from_("chat_media").upload(
                    file_name, 
                    media_bytes, 
                    {"content-type": clean_mime, "upsert": "true"}
                )
                saved_image_url = supabase.storage.from_("chat_media").get_public_url(file_name)
                print(f"Backed up image to Supabase: {saved_image_url}")
            except Exception as se:
                print(f"Supabase storage upload error: {type(se).__name__} - {se}")
                
        except Exception as e:
            print(f"Failed to process media: {e}")
            send_whatsapp_message(phone_number_id, sender_phone, "Sorry, I had trouble downloading your image. Please try sending it again.")
            return

    try:
        # 2. Check user onboarding flow first (if pure text)
        if not media_id and text_content:
            handled = handle_user_onboarding(phone_number_id, sender_phone, message_id, text_content=text_content)
            if handled:
                # Store onboarding chat record in Supabase
                try:
                    chat_record = {
                        "user_phone": sender_phone,
                        "user_message": text_content,
                        "ai_response": "[Onboarding Step Handled]"
                    }
                    supabase.table("chat_history").insert(chat_record).execute()
                except Exception as e:
                    print(f"Note: Could not save onboarding chat: {e}")
                return

        # 3. Get AI Response from Llama 3.2 Vision (while typing bubble continues to animate)
        print("Asking Llama 3.2 Vision to process the message/image...")
        ai_reply = get_ai_response(text_content, image_uri, sender_phone=sender_phone)
        
        # 4. Send the AI reply back via WhatsApp (this automatically replaces the typing indicator)
        send_whatsapp_message(phone_number_id, sender_phone, ai_reply)
        
        # 5. Store the chat in Supabase Database
        try:
            chat_record = {
                "user_phone": sender_phone,
                "user_message": text_content if text_content else "[Uploaded Document/Image]",
                "ai_response": ai_reply
            }
            if saved_image_url:
                chat_record["image_url"] = saved_image_url

            supabase.table("chat_history").insert(chat_record).execute()
            print("Saved chat to Supabase successfully.")
        except Exception as e:
            print(f"Note: Could not save to Supabase: {e}")

        # 6. Deep LLM Fact Extraction (Zero added latency to user response)
        if sender_phone and text_content and has_personal_fact_signal(text_content):
            try:
                llm_facts = extract_facts_llm(text_content)
                if llm_facts:
                    save_extracted_facts(sender_phone, llm_facts)
            except Exception as fe:
                print(f"Background fact extraction note: {fe}")
    except Exception as e:
        print(f"Unhandled error in process_whatsapp_message: {e}")
        try:
            send_whatsapp_message(
                phone_number_id, 
                sender_phone, 
                "👋 Hello! I am your Educaro Germany Advisor. How can I assist you with your Germany study, finance, or visa queries today?"
            )
        except Exception as se:
            print(f"Could not send error fallback message: {se}")

def transcribe_audio_bytes(media_bytes: bytes) -> str:
    """
    Converts WhatsApp audio bytes (OGG/Opus or similar) into WAV in-memory,
    and transcribes the speech to text using SpeechRecognition (Google Speech API, en-IN / hi-IN).
    """
    try:
        audio_io = io.BytesIO(media_bytes)
        data, samplerate = sf.read(audio_io)
        
        wav_buf = io.BytesIO()
        sf.write(wav_buf, data, samplerate, format="WAV")
        wav_buf.seek(0)
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_buf) as source:
            audio_data = recognizer.record(source)
            
        # Try Indian English first
        try:
            text = recognizer.recognize_google(audio_data, language="en-IN")
            if text and text.strip():
                return text.strip()
        except sr.UnknownValueError:
            pass
        except Exception as e:
            print(f"en-IN recognition error: {e}")
            
        # Fallback to Hindi
        try:
            text = recognizer.recognize_google(audio_data, language="hi-IN")
            if text and text.strip():
                return text.strip()
        except Exception:
            pass

        # Fallback to general English (en-US)
        try:
            text = recognizer.recognize_google(audio_data, language="en-US")
            if text and text.strip():
                return text.strip()
        except Exception:
            pass

        return ""
    except Exception as e:
        print(f"Error in audio transcription: {e}")
        return ""

def process_whatsapp_voice_message(phone_number_id: str, sender_phone: str, message_id: str = None, media_id: str = None, mime_type: str = "audio/ogg"):
    """
    Handles incoming WhatsApp voice notes / audio messages:
    1. Triggers animated typing indicator (...)
    2. Downloads voice note and backs up to Supabase storage
    3. Transcribes Indian English / Hindi speech to text in-memory
    4. Queries Llama 3.2 with domain context
    5. Sends formatted response acknowledging the voice note
    """
    if phone_number_id and message_id:
        send_typing_indicator(phone_number_id, message_id)

    saved_audio_url = None
    transcribed_text = ""

    try:
        print(f"Downloading audio {media_id} from WhatsApp...")
        media_bytes = download_whatsapp_media(media_id)
        
        # Upload audio to Supabase Storage chat_media bucket
        try:
            clean_mime = (mime_type or "audio/ogg").split(";")[0].strip().lower()
            file_name = f"{uuid.uuid4()}.ogg"
            supabase.storage.from_("chat_media").upload(
                file_name,
                media_bytes,
                {"content-type": clean_mime, "upsert": "true"}
            )
            saved_audio_url = supabase.storage.from_("chat_media").get_public_url(file_name)
            print(f"Backed up audio note to Supabase: {saved_audio_url}")
        except Exception as se:
            print(f"Supabase audio storage upload error: {se}")

        # Transcribe speech to text
        print("Transcribing audio bytes...")
        transcribed_text = transcribe_audio_bytes(media_bytes)
        print(f"Voice Note Transcribed: '{transcribed_text}'")

    except Exception as e:
        print(f"Failed to process audio media: {e}")
        send_whatsapp_message(
            phone_number_id,
            sender_phone,
            "🎙️ I had trouble downloading your voice note. Please try sending it again or type your question!"
        )
        return

    # Check if transcription produced text
    if not transcribed_text or not transcribed_text.strip():
        send_whatsapp_message(
            phone_number_id,
            sender_phone,
            "🎙️ *I received your voice note*, but couldn't clearly detect the speech. Please try sending it again, speaking a little closer to the mic, or typing your question."
        )
        return

    # Query Llama 3.2
    print(f"Asking Llama 3.2 to answer voice query: {transcribed_text}")
    try:
        ai_reply = get_ai_response(transcribed_text, sender_phone=sender_phone)
        if not ai_reply or not ai_reply.strip():
            ai_reply = "I listened to your voice message, but couldn't generate a clear answer. Please feel free to text your question directly!"
    except Exception as e:
        print(f"Error querying Llama 3.2 for voice note: {e}")
        ai_reply = "I listened to your voice message, but encountered an error generating the response. Please ask your question again or send a text message."

    # Format reply with clear voice note header
    final_reply = f"🎙️ *I heard:* \"_{transcribed_text}_\"\n\n{ai_reply}"
    send_whatsapp_message(phone_number_id, sender_phone, final_reply)

    # Store in Supabase chat_history
    try:
        chat_record = {
            "user_phone": sender_phone,
            "user_message": f"[🎙️ Voice Note]: {transcribed_text}",
            "ai_response": ai_reply
        }
        if saved_audio_url:
            chat_record["image_url"] = saved_audio_url

        supabase.table("chat_history").insert(chat_record).execute()
        print("Saved voice chat to Supabase successfully.")
    except Exception as e:
        print(f"Note: Could not save voice chat to Supabase: {e}")

    # Deep LLM Fact Extraction from Voice Note
    if sender_phone and transcribed_text and has_personal_fact_signal(transcribed_text):
        try:
            llm_facts = extract_facts_llm(transcribed_text)
            if llm_facts:
                save_extracted_facts(sender_phone, llm_facts)
        except Exception as fe:
            print(f"Background voice fact extraction note: {fe}")

@app.post("/whatsapp")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Meta sends WhatsApp messages to this endpoint via POST request.
    """
    body = await request.json()
    
    # Check if this is a WhatsApp message event
    if body.get("object"):
        for entry_item in body.get("entry", []):
            for change in entry_item.get("changes", []):
                value = change.get("value", {})
                phone_number_id = value.get("metadata", {}).get("phone_number_id")
                
                # Iterate over ALL messages in the batch so multi-image uploads aren't dropped
                for message_data in value.get("messages", []):
                    sender_phone = message_data.get("from")
                    message_type = message_data.get("type")
                    message_id = message_data.get("id")
                    
                    print(f"\n--- New Message Received ---")
                    print(f"From: {sender_phone}")
                    print(f"Type: {message_type}")
                    print(f"Message ID: {message_id}")

                    if message_type == "text":
                        text_content = message_data.get("text", {}).get("body", "")
                        print(f"Content: {text_content}")
                        background_tasks.add_task(
                            process_whatsapp_message, phone_number_id, sender_phone, message_id, text_content
                        )
                    
                    elif message_type in ["image", "document"]:
                        media_data = message_data.get(message_type, {})
                        media_id = media_data.get("id")
                        mime_type = media_data.get("mime_type")
                        caption = media_data.get("caption", "")
                        
                        print(f"Media Received. ID: {media_id}, Type: {mime_type}")
                        background_tasks.add_task(
                            process_whatsapp_message, phone_number_id, sender_phone, message_id, caption, media_id, mime_type
                        )

                    elif message_type in ["audio", "voice"]:
                        media_data = message_data.get(message_type, {})
                        if not media_data:
                            media_data = message_data.get("audio") or message_data.get("voice") or {}
                        media_id = media_data.get("id")
                        mime_type = media_data.get("mime_type", "audio/ogg")
                        
                        print(f"Voice/Audio Received. ID: {media_id}, Type: {mime_type}")
                        background_tasks.add_task(
                            process_whatsapp_voice_message, phone_number_id, sender_phone, message_id, media_id, mime_type
                        )

                    elif message_type == "interactive":
                        interactive_obj = message_data.get("interactive", {})
                        inter_type = interactive_obj.get("type")
                        selected_id = ""
                        selected_title = ""
                        if inter_type == "list_reply":
                            list_reply = interactive_obj.get("list_reply", {})
                            selected_id = list_reply.get("id", "")
                            selected_title = list_reply.get("title", "")
                        elif inter_type == "button_reply":
                            button_reply = interactive_obj.get("button_reply", {})
                            selected_id = button_reply.get("id", "")
                            selected_title = button_reply.get("title", "")
                        
                        print(f"Interactive Selection Received: ID='{selected_id}', Title='{selected_title}'")
                        background_tasks.add_task(
                            process_whatsapp_interactive_reply, phone_number_id, sender_phone, message_id, selected_id, selected_title
                        )
                
        return Response(content="EVENT_RECEIVED", status_code=200)
    else:
        raise HTTPException(status_code=404, detail="Not Found")
