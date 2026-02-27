import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# The API endpoint for rate limit logs
url = "https://api.venice.ai/api/v1/api_keys/rate_limits/log"

# Load API key from environment
api_key = os.getenv("VENICE_API_KEY") or os.getenv("VENICE_ADMIN_KEY")
if not api_key:
    print("Error: Set VENICE_API_KEY or VENICE_ADMIN_KEY in your .env file")
    exit(1)

# Setup the headers with Bearer authentication
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

try:
    # Make the GET request
    response = requests.get(url, headers=headers)
    
    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        print("Successfully retrieved rate limit logs:")
        print(json.dumps(data, indent=4))
        
        # Optional: Print a summary
        if data.get("data"):
            print(f"\nFound {len(data['data'])} recent rate limit events.")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"An error occurred: {e}")