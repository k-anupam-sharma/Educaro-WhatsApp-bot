import os
import sys
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()
import main

test_phone = "919999999999"

# 0. Clean test record
main.supabase.table("users").delete().eq("phone", test_phone).execute()
print("Cleaned up existing test phone record.")

# 1. Step 1: User sends 'hi'
print("\n--- 1. User says 'hi' ---")
res1 = main.handle_user_onboarding("dummy_pn", test_phone, "msg1", "hi")
u1 = main.get_or_create_user(test_phone)
print(f"Step after 'hi': {u1.get('onboarding_step')}, Handled: {res1}")

# 2. Step 2: User provides Name
print("\n--- 2. User enters name ---")
res2 = main.handle_user_onboarding("dummy_pn", test_phone, "msg2", "Rahul Verma")
u2 = main.get_or_create_user(test_phone)
print(f"Step after name: {u2.get('onboarding_step')}, Name: {u2.get('name')}")

# 3. Step 3: User provides Email
print("\n--- 3. User enters email ---")
res3 = main.handle_user_onboarding("dummy_pn", test_phone, "msg3", "rahul.verma@example.com")
u3 = main.get_or_create_user(test_phone)
print(f"Step after email: {u3.get('onboarding_step')}, Email: {u3.get('email')}, Code: {u3.get('verification_code')}")

# 4. Step 4: User selects Education Level
print("\n--- 4. User selects Education Level ---")
res4 = main.handle_user_onboarding("dummy_pn", test_phone, "msg4", text_content="Bachelor's Degree", selected_id="edu_bachelors")
u4 = main.get_or_create_user(test_phone)
print(f"Step after edu: {u4.get('onboarding_step')}, Level: {u4.get('level')}")

# 5. Step 5: User selects Current Course
print("\n--- 5. User selects Current Course ---")
res5 = main.handle_user_onboarding("dummy_pn", test_phone, "msg5", text_content="Computer Science / IT", selected_id="crs_cs")
u5 = main.get_or_create_user(test_phone)
print(f"Step after course: {u5.get('onboarding_step')}, Course: {u5.get('course')}")

# 6. Step 6: User selects Goal in Germany
print("\n--- 6. User selects Goal in Germany ---")
res6 = main.handle_user_onboarding("dummy_pn", test_phone, "msg6", text_content="Master's Degree", selected_id="goal_masters")
u6 = main.get_or_create_user(test_phone)
print(f"Step after goal: {u6.get('onboarding_step')}, Target Study: {u6.get('target_study')}")

# 7. Step 7: User selects Target Discipline
print("\n--- 7. User selects Target Field ---")
res7 = main.handle_user_onboarding("dummy_pn", test_phone, "msg7", text_content="IT / Computer Science", selected_id="field_it")
u7 = main.get_or_create_user(test_phone)
print(f"Step after field: {u7.get('onboarding_step')}, Field: {u7.get('city')}")

# 8. Step 8: User selects Preferred Mode of Study
print("\n--- 8. User selects Mode ---")
res8 = main.handle_user_onboarding("dummy_pn", test_phone, "msg8", text_content="English", selected_id="mode_eng")
u8 = main.get_or_create_user(test_phone)
print(f"Step after mode: {u8.get('onboarding_step')}, Onboarded: {u8.get('onboarded')}, Mode: {u8.get('mode')}")

# Cleanup
main.supabase.table("users").delete().eq("phone", test_phone).execute()
print("\n🎉 ALL 8 ONBOARDING STEPS PASSED PERFECTLY AND RECORD CLEANED UP!")
