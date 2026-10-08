import os
import sys
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

from main import get_ai_response, transcribe_audio_bytes

FEATURE_PROMPTS = {
    "1": (
        "Real-Time INR Budget & Part-Time Calculator",
        "How much total INR budget do I need for a Master in Germany including blocked account, and how much can I earn doing a Werkstudent job?"
    ),
    "2": (
        "Instant APS India & Anabin Verifier",
        "I have a 3-year B.Sc from Mumbai University. Can I do a Masters in Germany? Do I need APS certificate?"
    ),
    "3": (
        "City Desi Comfort Index",
        "Which is better for an Indian student: Aachen or Munich? Tell me about Indian food and rent."
    ),
    "4": (
        "Voice Note Simulation",
        "Simulates a transcribed voice note: 'Hey Voraus AI, I want to study Mechanical Engineering in Germany. What are the public university options?'"
    ),
    "5": (
        "Forward-to-Parents Summary Card",
        "Can you give me a summary I can forward to my parents about studying in Germany?"
    ),
    "6": (
        "Indian Education Loan & Sponsor Advisor",
        "Which bank in India is best for an education loan for Germany, and what is the rule for the visa sanction letter?"
    ),
}

def print_menu():
    print("\n" + "="*60)
    print("🎓 VORAUS AI - FEATURE TESTING CLI")
    print("="*60)
    for key, (name, _) in FEATURE_PROMPTS.items():
        print(f"[{key}] {name}")
    print("[7] Enter Custom Prompt")
    print("[0] Exit")
    print("="*60)

def main():
    while True:
        print_menu()
        choice = input("\nSelect a feature to test (0-7): ").strip()
        
        if choice == "0":
            print("Exiting test tool.")
            break
            
        elif choice in FEATURE_PROMPTS:
            name, prompt = FEATURE_PROMPTS[choice]
            print(f"\n🧪 Testing Feature: {name}")
            print(f"📤 Query: {prompt}\n")
            print("⏳ Querying Llama 3.2 Vision Brain...\n")
            
            response = get_ai_response(prompt)
            print("="*60)
            print("📥 WhatsApp Bot Response:")
            print("="*60)
            print(response)
            print("="*60)
            
        elif choice == "7":
            custom_prompt = input("\nEnter your test query: ").strip()
            if not custom_prompt:
                continue
            print("\n⏳ Querying Llama 3.2 Vision Brain...\n")
            response = get_ai_response(custom_prompt)
            print("="*60)
            print("📥 WhatsApp Bot Response:")
            print("="*60)
            print(response)
            print("="*60)
        else:
            print("Invalid choice, please select 0-7.")

if __name__ == "__main__":
    main()
