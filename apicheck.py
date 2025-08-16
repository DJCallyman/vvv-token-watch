import requests
from datetime import datetime

# 🔐 Replace this with your NEW, SECURE API key
API_KEY = "27ITQlxI5wpLn8Z8RkhqT647-NTXM1tGQDRqEY8DmH"

# Venice API base URL
BASE_URL = "https://api.venice.ai/api/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def get_api_key_details():
    """Get your API key's rate limits, balances, and usage."""
    url = f"{BASE_URL}/api_keys/rate_limits"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json().get("data", {})
        balances = data.get("balances", {})
        api_tier = data.get("apiTier", {})

        print("✅ API Key Details:")
        print(f"Access Permitted: {data.get('accessPermitted', 'N/A')}")
        print(f"API Tier: {api_tier.get('id', 'N/A')} (Charged: {api_tier.get('isCharged', 'N/A')})")
        print(f"Next Reset: {data.get('nextEpochBegins', 'N/A')}")

        print("\n💰 Balances:")
        for currency, amount in balances.items():
            print(f"  {currency}: {amount}")

        print(f"\nRate Limits Remaining: {data.get('rateLimits', [{}])[0].get('rateLimits', 'N/A')}")
    else:
        print(f"❌ Failed to get details: {response.status_code} - {response.text}")

def get_billing_usage():
    """Get recent billing usage (last 200 entries by default)."""
    url = f"{BASE_URL}/billing/usage"
    params = {
        "limit": 10,  # Only get last 10 for testing
        "sortOrder": "desc"
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        usage_data = response.json().get("data", [])
        print(f"\n🧾 Last {len(usage_data)} Usage Records:")
        for record in usage_data:
            ts = record.get("timestamp", "Unknown")
            sku = record.get("sku", "Unknown")
            amount = record.get("amount")
            currency = record.get("currency")
            units = record.get("units")
            print(f"  [{ts}] {amount} {currency} | {units} units | {sku}")
    else:
        print(f"❌ Failed to get usage: {response.status_code} - {response.text}")

def list_models():
    """List available models."""
    url = f"{BASE_URL}/models"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        models = response.json().get("data", [])
        print(f"\n🤖 Available Models: {len(models)}")
        for m in models[:5]:  # Show first 5
            print(f"  - {m['id']} (type: {m['type']})")
        if len(models) > 5:
            print("  ...")
    else:
        print(f"❌ Failed to list models: {response.status_code} - {response.text}")

# Run the checks
if __name__ == "__main__":
    print("🔍 Checking your Venice.ai API access...\n")
    get_api_key_details()
    get_billing_usage()
    list_models()