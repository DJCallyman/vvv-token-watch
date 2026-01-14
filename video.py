import requests
import time
import os

# Configuration
API_KEY = "27ITQlxI5wpLn8Z8RkhqT647-NTXM1tGQDRqEY8DmH"
BASE_URL = "https://api.venice.ai/api/v1"
MODEL = "wan-2.5-preview-text-to-video" # Example text-to-video model
PROMPT = "A cinematic shot of a futuristic city with flying vehicles at sunset."

def generate_video():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 1. Queue the video generation
    print(f"Queueing video generation for: '{PROMPT}'...")
    queue_payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "duration": "5s",
        "resolution": "720p"
    }
    
    # Note: If using an image-to-video model, add "image_url": "data:image/png;base64,..."
    
    response = requests.post(f"{BASE_URL}/video/queue", headers=headers, json=queue_payload)
    
    if response.status_code != 200:
        print(f"Error queueing video: {response.text}")
        return

    task_data = response.json()
    queue_id = task_data.get("queue_id")
    print(f"Task queued successfully. Queue ID: {queue_id}")

    # 2. Poll for the result
    print("Waiting for video to process (this may take a few minutes)...")
    retrieve_payload = {
        "model": MODEL,
        "queue_id": queue_id
    }

    while True:
        # Poll the retrieve endpoint
        res = requests.post(f"{BASE_URL}/video/retrieve", headers=headers, json=retrieve_payload)
        
        # Check if the response is the video file (binary) or a status update (JSON)
        content_type = res.headers.get("Content-Type", "")
        
        if "video/mp4" in content_type:
            # Success! Save the video
            filename = f"generated_video_{int(time.time())}.mp4"
            with open(filename, "wb") as f:
                f.write(res.content)
            print(f"\nSuccess! Video saved as {filename}")
            
            # 3. Optional: Cleanup (Delete from Venice storage)
            requests.post(f"{BASE_URL}/video/complete", headers=headers, json=retrieve_payload)
            break
            
        elif res.status_code == 200:
            # Still processing
            status_info = res.json()
            progress = status_info.get("execution_duration", 0) / 1000
            print(f"Status: {status_info.get('status')} ({progress:.1f}s elapsed)...", end="\r")
            time.sleep(10) # Wait 10 seconds before polling again
        else:
            print(f"\nError retrieving video: {res.text}")
            break

if __name__ == "__main__":
    if API_KEY == "your_venice_api_key_here":
        print("Please set your API_KEY in the script.")
    else:
        generate_video()