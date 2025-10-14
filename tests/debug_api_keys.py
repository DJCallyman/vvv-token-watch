#!/usr/bin/env python3
"""
Quick API key structure check for debugging Phase 3 key management
"""

import requests
import json

API_KEY = "27ITQlxI5wpLn8Z8RkhqT647-NTXM1tGQDRqEY8DmH"
BASE_URL = "https://api.venice.ai/api/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def check_api_keys():
    """Check the structure of API keys from Venice.ai"""
    print("🔍 Checking API keys structure...")
    
    try:
        # Get list of API keys
        response = requests.get(f"{BASE_URL}/api_keys", headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response structure: {json.dumps(data, indent=2)}")
            
            # Check individual key details
            if data.get("data") and len(data["data"]) > 0:
                first_key = data["data"][0]
                key_id = first_key.get("id")
                print(f"\n🔍 Checking individual key details for: {key_id}")
                
                key_response = requests.get(f"{BASE_URL}/api_keys/{key_id}", headers=headers, timeout=30)
                print(f"Individual key status: {key_response.status_code}")
                
                if key_response.status_code == 200:
                    key_data = key_response.json()
                    print(f"Individual key data: {json.dumps(key_data, indent=2)}")
                else:
                    print(f"Individual key error: {key_response.text}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_api_keys()