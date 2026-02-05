import requests
import json
import uuid

API_URL = "http://localhost:8000/api/v1"
HEADERS = {
    "X-API-Key": "change-me-in-production",
    "Content-Type": "application/json"
}

def print_result(name, response):
    print(f"\n{'='*40}")
    print(f"TEST: {name}")
    print(f"{'='*40}")
    if response.status_code == 200:
        data = response.json()
        print("✅ SUCCESS")
        print(json.dumps(data, indent=2))
        return data.get('data')
    else:
        print(f"❌ FAILED (Status: {response.status_code})")
        print(response.text)
        return None

def verify_system():
    print("🚀 Starting Manual Verification...")

    # 1. Health Check
    try:
        r = requests.get("http://localhost:8000/health")
        print_result("Health Check", r)
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return

    # 2. Analyze Message
    payload = {"message": "Congratulations! You won $1,000,000. Send $500 to claim."}
    r = requests.post(f"{API_URL}/analyze-message", json=payload, headers=HEADERS)
    print_result("Analyze Message", r)

    # 3. Start Conversation
    payload = {
        "initial_message": "Hello, I am from Microsoft. Your PC has a virus.",
        "scammer_identifier": "scammer@microsoft-support.com"
    }
    r = requests.post(f"{API_URL}/start-conversation", json=payload, headers=HEADERS)
    data = print_result("Start Conversation", r)
    
    if data:
        conversation_id = data['conversation_id']
        
        # 4. Continue Conversation
        payload = {
            "conversation_id": conversation_id,
            "message": "Yes, please pay $50 via Gift Card to fix it."
        }
        r = requests.post(f"{API_URL}/continue-conversation", json=payload, headers=HEADERS)
        print_result("Continue Conversation", r)

if __name__ == "__main__":
    verify_system()
