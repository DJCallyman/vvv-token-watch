import requests
from datetime import datetime, timedelta
import os

def check_api_usage(api_key=None, days_back=30, currency="USD", limit=200):
    """
    Check Venice.ai API usage for billing period
    
    Args:
        api_key (str): Your Venice.ai API key (defaults to VENICE_API_KEY env var)
        days_back (int): How many days of history to fetch
        currency (str): Currency filter (USD, DIEM, or VCU)
        limit (int): Number of records to return (max 500)
    
    Returns:
        dict: API response containing usage data
    """
    api_key = "27ITQlxI5wpLn8Z8RkhqT647-NTXM1tGQDRqEY8DmH"
    if not api_key:
        raise ValueError("API key must be provided either as argument or VENICE_API_KEY environment variable")
    
    base_url = "https://api.venice.ai/api/v1"
    endpoint = "/billing/usage"
    
    end_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    params = {
        "startDate": start_date,
        "endDate": end_date,
        "currency": currency,
        "limit": limit,
        "sortOrder": "desc"
    }
    
    try:
        response = requests.get(f"{base_url}{endpoint}", headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": e.response.json() if e.response else None}

if __name__ == "__main__":
    # Get API key from environment variable (recommended) or replace directly
    usage_data = check_api_usage()
    
    if "error" in usage_data:
        print(f"❌ API Error: {usage_data['error']}")
        if usage_data.get("details"):
            print(f"Details: {usage_data['details']}")
    else:
        print(f"✅ Successfully retrieved {usage_data['pagination']['total']} usage records")
        print(f"Showing first {len(usage_data['data'])} records (sorted newest first):\n")
        
        for i, record in enumerate(usage_data["data"], 1):
            print(f"Record #{i} ({record['timestamp']}):")
            print(f"- SKU: {record['sku']}")
            print(f"- Units consumed: {record['units']}")
            print(f"- Amount: {record['amount']} {record['currency']}")
            print(f"- Notes: {record['notes']}")
            
            if record.get("inferenceDetails"):
                details = record["inferenceDetails"]
                print(f"- Request ID: {details['requestId']}")
                print(f"- Prompt tokens: {details.get('promptTokens', 'N/A')}")
                print(f"- Completion tokens: {details.get('completionTokens', 'N/A')}")
                print(f"- Execution time: {details.get('inferenceExecutionTime', 'N/A')}ms")
            
            print("-" * 50)