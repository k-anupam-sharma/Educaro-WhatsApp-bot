import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("WHATSAPP_TOKEN")

if not token:
    print("[ERROR] WHATSAPP_TOKEN not found in .env")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: .\\venv\\Scripts\\python.exe subscribe_waba.py <YOUR_WABA_ID>")
    print("Find your WhatsApp Business Account ID under: WhatsApp -> API Setup in Meta Developer Dashboard.")
    sys.exit(1)

waba_id = sys.argv[1].strip()

url = f"https://graph.facebook.com/v21.0/{waba_id}/subscribed_apps"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print(f"Subscribing WABA ID: {waba_id} to your Meta App...")
response = requests.post(url, headers=headers)

if response.status_code == 200:
    print(f"[SUCCESS] WABA successfully linked! Response: {response.json()}")
    print("\nVerifying subscription...")
    verify_res = requests.get(url, headers=headers)
    print(f"Subscribed Apps: {verify_res.json()}")
    print("\n>>> Done! Now send 'hi' on WhatsApp to your test number. The webhook POST will now arrive in Uvicorn.")
else:
    print(f"[FAILED] HTTP {response.status_code}: {response.text}")
