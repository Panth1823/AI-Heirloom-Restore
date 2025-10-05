#!/usr/bin/env python3
"""
External test script to verify Gemini API using direct HTTP requests
This bypasses the google-genai SDK to test the API directly
"""
import os
import json
import requests
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_direct_http():
    """Test Gemini API using direct HTTP requests"""
    
    # Get API key
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY not found")
        return False
    
    print(f"✅ API Key: {api_key[:10]}...")
    
    # Gemini API endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
    
    # Simple text request payload
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": "Say 'Hello' if you can read this."}]
        }]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print("🧪 Testing direct HTTP request to Gemini API...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"📡 Response Status: {response.status_code}")
        print(f"📡 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! API is working")
            print(f"Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 429:
                print("💡 This confirms quota/rate limit issue")
            elif response.status_code == 403:
                print("💡 This indicates API key issue")
            elif response.status_code == 400:
                print("💡 This indicates request format issue")
                
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False

def test_gemini_with_image():
    """Test Gemini API with a simple image"""
    
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        return False
    
    print("\n🧪 Testing Gemini API with image...")
    
    # Create a simple 1x1 pixel PNG
    test_image_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    
    base64_image = base64.b64encode(test_image_data).decode('utf-8')
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": "Describe this image briefly."},
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": base64_image
                    }
                }
            ]
        }]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"📡 Image Test Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Image processing works!")
            print(f"Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Image test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Image test network error: {e}")
        return False

def generate_curl_commands():
    """Generate curl commands for external testing"""
    
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("❌ No API key found")
        return
    
    print("\n" + "="*60)
    print("📋 CURL COMMANDS FOR EXTERNAL TESTING")
    print("="*60)
    
    # Simple text test
    curl_text = f'''curl -X POST \\
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "contents": [
      {{
        "role": "user",
        "parts": [
          {{"text": "Say hello if you can read this."}}
        ]
      }}
    ]
  }}' '''
    
    print("🔤 TEXT TEST:")
    print(curl_text)
    
    # Image test
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    curl_image = f'''curl -X POST \\
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "contents": [
      {{
        "role": "user",
        "parts": [
          {{"text": "Describe this image."}},
          {{
            "inline_data": {{
              "mime_type": "image/png",
              "data": "{test_image_b64}"
            }}
          }}
        ]
      }}
    ]
  }}' '''
    
    print("\n🖼️ IMAGE TEST:")
    print(curl_image)
    
    print("\n" + "="*60)
    print("📋 POSTMAN SETUP")
    print("="*60)
    print("Method: POST")
    print(f"URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}")
    print("Headers:")
    print("  Content-Type: application/json")
    print("Body (raw JSON):")
    print('''{
  "contents": [
    {
      "role": "user",
      "parts": [
        {"text": "Say hello if you can read this."}
      ]
    }
  ]
}''')

if __name__ == "__main__":
    print("🚀 EXTERNAL GEMINI API TEST")
    print("="*50)
    
    # Test 1: Direct HTTP
    success = test_gemini_direct_http()
    
    if success:
        # Test 2: Image processing
        test_gemini_with_image()
    
    # Generate curl commands
    generate_curl_commands()
    
    print("\n" + "="*50)
    if success:
        print("🎉 External test successful! Your API key works.")
        print("The quota issue might be specific to the SDK or temporary.")
    else:
        print("❌ External test failed. Check the error details above.")
    print("="*50)
