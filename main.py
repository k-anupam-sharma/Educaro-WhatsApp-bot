import os
import uuid
import base64
import requests
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
                {"role": "system", "content": "You are Voraus AI, a helpful consultant for moving to Germany, assisting international students and applicants with university admissions, vocational training (Ausbildung), and German bureaucracy. Always reply in English by default (unless the user explicitly speaks in another language). When an image or document is provided, read all visible text carefully, provide clear OCR extraction, and offer actionable advice. Keep your answers concise, friendly, and formatted nicely for WhatsApp (use emojis, bold text like *this*, bullet points, etc)."},
                {"role": "user", "content": content}
            ],
            temperature=0.5,
            max_tokens=1024,
        )
        return completion.choices[0].message.content or ""
    except Exception as e:
        print(f"Error calling Llama 3.2: {e}")
        return "Sorry, I'm having trouble connecting to my AI brain right now."

def send_whatsapp_message(phone_number_id: str, to: str, text: str):
    """
    Sends a text message using the WhatsApp Business API.
    """
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
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
    url = f"https://graph.facebook.com/v18.0/{media_id}"
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

def process_whatsapp_message(phone_number_id: str, sender_phone: str, text_content: str = "", media_id: str = None, mime_type: str = None):
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

    # 1. Get AI Response from Llama 3.2 Vision
    print("Asking Llama 3.2 Vision to process the message/image...")
    ai_reply = get_ai_response(text_content, image_uri)
    
    # 2. Send the AI reply back via WhatsApp
    send_whatsapp_message(phone_number_id, sender_phone, ai_reply)
    
    # 3. Store the chat in Supabase Database
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
                    
                    print(f"\n--- New Message Received ---")
                    print(f"From: {sender_phone}")
                    print(f"Type: {message_type}")

                    if message_type == "text":
                        text_content = message_data.get("text", {}).get("body", "")
                        print(f"Content: {text_content}")
                        background_tasks.add_task(
                            process_whatsapp_message, phone_number_id, sender_phone, text_content
                        )
                    
                    elif message_type in ["image", "document"]:
                        media_data = message_data.get(message_type, {})
                        media_id = media_data.get("id")
                        mime_type = media_data.get("mime_type")
                        caption = media_data.get("caption", "")
                        
                        print(f"Media Received. ID: {media_id}, Type: {mime_type}")
                        background_tasks.add_task(
                            process_whatsapp_message, phone_number_id, sender_phone, caption, media_id, mime_type
                        )
                
        return Response(content="EVENT_RECEIVED", status_code=200)
    else:
        raise HTTPException(status_code=404, detail="Not Found")
