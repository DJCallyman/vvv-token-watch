import requests
import json

# The API endpoint for rate limit logs
url = "https://api.venice.ai/api/v1/api_keys/rate_limits/log"

# Your provided API Key
api_key = "VENICE-INFERENCE-KEY-u0zEdjJumW3nOUJw00badLHrCt8lfaM6SXpgyS6Dse"

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