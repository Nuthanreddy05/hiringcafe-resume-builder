
import os
import json
import gmail_helper

def check_env():
    print("🔍 Diagnostic Check")
    print("="*40)
    
    # Check Profile
    try:
        with open("profile.json") as f:
            p = json.load(f)
            pwd = p.get("default_password", "")
            if not pwd or pwd == "ChangeMe123!":
                 print("⚠️  WARNING: profile.json contains default password. Please update 'default_password'.")
            else:
                 print("✅ Profile Password Set")
    except:
        print("❌ profile.json missing or invalid")

    # Check Env
    gu = os.getenv("GMAIL_USER")
    gp = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gu or not gp:
        print("❌ GMAIL_USER or GMAIL_APP_PASSWORD not set in environment.")
        print("   export GMAIL_USER='your@gmail.com'")
        print("   export GMAIL_APP_PASSWORD='your-app-pwd'")
    else:
        print(f"✅ Gmail User: {gu}")
        print("✅ Gmail Password Set")
        
        # Test Connection
        print("\nTesting Gmail Connection...")
        try:
             mail = gmail_helper.get_gmail_service(gu, gp)
             if mail:
                 print("   ✅ Connection Successful!")
                 mail.logout()
             else:
                 print("   ❌ Connection Failed (Bad Credentials?)")
        except Exception as e:
             print(f"   ❌ Connection Error: {e}")

if __name__ == "__main__":
    check_env()
