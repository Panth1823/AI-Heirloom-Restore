#!/usr/bin/env python3
"""
Test OpenRouter API with gemini-2.5-flash-image-preview model
"""
import os
import json
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

def test_openrouter_api():
    """Test OpenRouter API with gemini-2.5-flash-image-preview"""
    
    # Get API key from environment or ask user to input it
    openrouter_api_key = os.environ.get('OPENROUTER_API_KEY')
    
    if not openrouter_api_key:
        print("❌ OPENROUTER_API_KEY not found in environment")
        print("Please add your OpenRouter API key to the .env file:")
        print("OPENROUTER_API_KEY=your_key_here")
        return False
    
    print(f"✅ OpenRouter API Key: {openrouter_api_key[:10]}...")
    
    # Test 1: Simple text request
    print("\n🧪 Testing simple text request...")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",  # Your app URL
        "X-Title": "AI Heirloom Restore",  # Your app name
    }
    
    payload = {
        "model": "google/gemini-2.5-flash-image-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Say 'Hello from OpenRouter!' if you can read this."
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Text Response: {content}")
        else:
            print(f"❌ Text Request Failed: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    
    # Test 2: Image processing request
    print("\n🧪 Testing image processing...")
    
    # Create a simple test image (1x1 blue pixel)
    test_image_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    base64_image = base64.b64encode(test_image_data).decode('utf-8')
    
    image_payload = {
        "model": "google/gemini-2.5-flash-image-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Describe this image briefly."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=image_payload, timeout=30)
        
        print(f"📡 Image Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Image Response: {content}")
            return True
        else:
            print(f"❌ Image Request Failed: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False

def test_photo_restoration_openrouter():
    """Test photo restoration with OpenRouter"""
    
    openrouter_api_key = os.environ.get('OPENROUTER_API_KEY')
    if not openrouter_api_key:
        return False
    
    print("\n🧪 Testing photo restoration capability...")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "AI Heirloom Restore",
    }
    
    # Create test image
    test_image_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    base64_image = base64.b64encode(test_image_data).decode('utf-8')
    
    # Use your exact restoration prompt
    restoration_prompt = (
        "Restore and COLORIZE this historical photograph. Remove scratches/dust, gently enhance sharpness, and "
        "produce a realistic COLOR output with natural, period-accurate tones. Preserve subject identity, lighting, "
        "and scene authenticity. Avoid monochrome or stylized looks. IMPORTANT: The output must be in COLOR, "
        "not black and white. Add realistic colors based on the historical period and context."
    )
    
    payload = {
        "model": "google/gemini-2.5-flash-image-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": restoration_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"📡 Restoration Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✅ Restoration Response: {content}")
            return True
        else:
            print(f"❌ Restoration Failed: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 TESTING OPENROUTER API")
    print("="*50)
    
    # Test basic functionality
    basic_ok = test_openrouter_api()
    
    if basic_ok:
        # Test photo restoration
        restoration_ok = test_photo_restoration_openrouter()
        
        print("\n" + "="*50)
        print("📋 RESULTS:")
        print("✅ OpenRouter API is working!")
        print("✅ gemini-2.5-flash-image-preview is accessible!")
        
        if restoration_ok:
            print("✅ Photo restoration prompts work!")
            print("\n💡 SUCCESS: You can now use this for your app!")
            print("   Next step: Update server.py to use OpenRouter API")
        else:
            print("⚠️ Photo restoration needs testing with real images")
    else:
        print("\n❌ OpenRouter API test failed")
        print("   Please check your API key and try again")
    
    print("="*50)
