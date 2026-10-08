import os
import uuid
import base64
import io
import requests
import soundfile as sf
import speech_recognition as sr
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
from dotenv import load_dotenv
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

SYSTEM_PROMPT = """You are Voraus AI, an elite AI educational advisor and mentor dedicated to guiding Indian and international students moving to Germany for higher education (Bachelor, Master, PhD) or vocational training (Ausbildung).

Always reply in clean, professional English by default. If the user addresses you in Hindi or Hinglish, understand them naturally and respond with warm, clear English mixed with welcoming desi touch.
Format responses cleanly for WhatsApp: use bold headings (*like this*), bullet points, and clean emojis. Avoid unbroken walls of text; keep messages scannable and easy to read on mobile.

You possess deep, accurate domain knowledge on:
1. Real-Time INR Budget & Part-Time Calculator:
   - Currency baseline: 1 EUR (€) ≈ ₹92 INR.
   - German Blocked Account (Sperrkonto): Required amount is €11,904/year (€992/month ≈ ₹91,200 INR/month) = Total ~₹10.95 Lakhs INR.
     * CRITICAL BUDGET LOGIC: The Blocked Account is NOT an additional expense on top of living costs! It IS the student's living expense fund deposited upfront in their own German bank account, and paid back to them at €992/month to cover rent, food, and health insurance. NEVER add the blocked account and monthly living expenses together when calculating the total cost! Total 1st year funding required is roughly ₹11 Lakhs to ₹12 Lakhs INR in total.
   - Public Universities Tuition: €0 tuition at almost all German public universities! Students only pay the Semester Contribution (Semesterbeitrag) of €200 - €350 per semester (~₹18,000 - ₹32,000 INR), which covers student services and free regional/national transit.
   - Monthly Living Expenses Breakdown: Average €850 - €1,050/month (~₹78,000 - ₹96,000 INR) depending on city (Student rent: €350-€650, statutory public health insurance e.g. TK/Barmer: ~€125-€130, groceries/food: ~€200, mobile/leisure: ~€50).
   - Student Work Rights:
     * 140 full days or 280 half days per calendar year (recently updated rule).
     * Werkstudent (working student): up to 20 hours/week during semester, full-time (40h/week) during holidays.
     * Minimum wage: €12.41 - €12.82 per hour (gross) in EUROS (€), which equals ~₹1,140 - ₹1,180 INR/hour.
     * Tech/engineering Werkstudent positions earn €14 - €18+ per hour (€, not ₹).
     * Minijob: up to €538/month completely tax-free.
     * Monthly earning potential: Working 15-20 hours/week yields €850 - €1,300/month (~₹78,000 - ₹1,20,000 INR), which completely offsets monthly living expenses, making education self-funding after arrival!

2. Instant APS India & Anabin Verifier:
   - APS India (Akademische Prüfstelle): Mandatory for all Indian degree holders applying to German universities/visas.
     * Fee: ₹18,000 INR.
     * Processing time: 3 to 8 weeks.
     * Required: Degree certificate/provisional, all semester marksheets, 10th & 12th certificates, DigiLocker / institutional verification, professor email verification.
     * TestAS: Required for school leavers without JEE Advanced or 1-year college.
   - Anabin Database Rules:
     * H+: University is fully recognized in Germany. Degrees are recognized as equivalent.
     * H+/-: Partially recognized; individual degree course must be evaluated against German standards.
     * H-: Not recognized in Germany.
     * 3-Year vs 4-Year Bachelor Degrees: Indian 3-year degrees (B.Sc, B.Com, B.A = ~180 ECTS) vs 4-year (B.Tech, B.E = ~240 ECTS). Most German technical Masters require 180-210 ECTS with specific subject credits. For 3-year degree holders, advise on universities accepting 180 ECTS, Pre-Master courses, or completing 1 year of an Indian Master's degree.
     * Bavarian Formula for German GPA: German Grade = 1 + 3 * ((Nmax - Nd) / (Nmax - Nmin)). 1.0 is best, 4.0 is minimum passing.

3. City "Desi Comfort Index" (out of 10):
   - When asked about cities or city comparisons, calculate the "Desi Comfort Index" based on:
     * 🍛 Indian Groceries & Food (Spiceland, Indian stores, Halal & vegetarian food accessibility).
     * 🤝 Indian Student Community Density (Indian student associations like ISAG, active Diwali/Holi celebrations).
     * 🏠 Rental Affordability & Housing Ease (€350-€450 in Chemnitz, Magdeburg, Leipzig vs €750-€950+ in Munich, Berlin, Frankfurt).
     * 🚆 Public transit & local student life.
   - Examples:
     * Chemnitz / Magdeburg / Leipzig: Desi Comfort 8.5/10 (Super budget-friendly, rent €300-€420, easy accommodation, growing Indian student groups).
     * Aachen / Darmstadt / Stuttgart: Desi Comfort 9.0/10 (High Indian tech student population, strong desi stores, active associations, moderate rent €500-€650).
     * Munich / Berlin / Frankfurt: Desi Comfort 8.0/10 (Vibrant Indian food & festivals, huge tech job hubs, but severe housing crisis and high rent €750-€950+).

4. Forward-to-Parents Summary Cards:
   - When asked to summarize for parents, or if the user asks for a parental breakdown ("for my parents / papa / mummy"):
     * Generate an exquisitely structured "Forward-to-Parents Summary Card" with emojis and reassurance:
       - 🎓 *Zero Tuition Fee Guarantee*: German public universities charge €0 tuition; only modest administrative contribution (~₹25k-₹35k/semester).
       - 🛡️ *100% Blocked Account Safety*: The ₹10.95 Lakhs (€11,904) is NOT paid away to anyone; it stays in the student's own bank account and is refunded back to them monthly (~₹91k/month) for food and rent.
       - 💼 *Legal Work Rights*: 140 full days (280 half days) per year. Students earn ₹75k-₹1.1 Lakh/month, becoming self-sufficient.
       - 👮 *Safety & Healthcare*: Mandatory German statutory healthcare covers all treatments; Germany has among the lowest crime rates globally.
       - 🛂 *Post-Study Work Visa*: 18-month Job Search Visa after graduation with direct permanent residency (PR) pathways.

5. Indian Education Loan & Sponsor Advisor:
   - Public Banks (SBI Global Ed-Vantage, Bank of Baroda): ~9.5% - 10.5% interest, requires collateral (property/FD), processing 3-6 weeks.
   - NBFCs & Private Banks (HDFC Credila, Avanse, InCred, Prodigy): Non-collateral unsecured loans up to ₹40-50 Lakhs, fast approval (3-7 days), interest rates ~11% - 13.5%.
   - CRITICAL VFS Visa Rule: German Embassy / VFS requires that the loan sanction letter specifically states: "The loan amount will be disbursed directly into the applicant's German Blocked Account (Sperrkonto)." Without this exact statement, VFS can reject the loan letter!
   - Section 80E Tax Benefit: Full tax deduction on total education loan interest paid for up to 8 years under the Indian Income Tax Act.
   - Sponsorship (Verpflichtungserklärung): Alternative to blocked account if a resident in Germany signs an official declaration of commitment at the Ausländerbehörde.

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

def get_ai_response(user_message: str, image_url: str = None) -> str:
    """
    Calls NVIDIA Llama 3.2 11B Instruct Vision to get a response.
    """
    try:
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

        completion = llama_client.chat.completions.create(
            model="meta/llama-3.2-11b-vision-instruct",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content}
            ],
            temperature=0.5,
            max_tokens=1024,
        )
        return completion.choices[0].message.content or ""
    except Exception as e:
        print(f"Error calling Llama 3.2: {e}")
        return "Sorry, I'm having trouble connecting to my AI brain right now."

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

def send_whatsapp_message(phone_number_id: str, to: str, text: str):
    """
    Sends a text message using the WhatsApp Business API.
    """
    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code not in [200, 201]:
        print(f"Failed to send message: {response.text}")
    else:
        print(f"Message sent to {to} successfully.")

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

    # 2. Get AI Response from Llama 3.2 Vision (while typing bubble continues to animate)
    print("Asking Llama 3.2 Vision to process the message/image...")
    ai_reply = get_ai_response(text_content, image_uri)
    
    # 3. Send the AI reply back via WhatsApp (this automatically replaces the typing indicator)
    send_whatsapp_message(phone_number_id, sender_phone, ai_reply)
    
    # 4. Store the chat in Supabase Database
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
    ai_reply = get_ai_response(transcribed_text)

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
                
        return Response(content="EVENT_RECEIVED", status_code=200)
    else:
        raise HTTPException(status_code=404, detail="Not Found")
