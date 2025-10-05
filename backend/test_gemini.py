#!/usr/bin/env python3
"""
Test script to verify Gemini API connectivity and functionality
"""
import os
import sys
from dotenv import load_dotenv
import base64
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gemini_connection():
    """Test basic Gemini API connection"""
    try:
        # Check if API key is configured
        api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            print("❌ GOOGLE_API_KEY not found in environment variables")
            print("Please set your Google API key:")
            print("1. Get a free key at: https://makersuite.google.com/app/apikey")
            print("2. Set it in your .env file or environment")
            return False
        
        print(f"✅ API key found: {api_key[:10]}...")
        
        # Test import
        try:
            from google import genai
            print("✅ google-genai package imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import google-genai: {e}")
            print("Please install: pip install google-genai")
            return False
        
        # Test basic text generation
        print("🧪 Testing basic text generation...")
        client = genai.Client(api_key=api_key)
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-image-preview")
        
        response = client.models.generate_content(
            model=model,
            contents=[{"role": "user", "parts": [{"text": "Say 'Hello from Gemini!' if you can read this."}]}],
        )
        
        # Extract response text
        text = None
        try:
            if hasattr(response, "text") and isinstance(response.text, str):
                text = response.text
        except Exception:
            pass
        
        if not text:
            try:
                as_dict = response.to_dict() if hasattr(response, "to_dict") else None
                if as_dict:
                    # Search for text in response
                    def find_text(obj):
                        if isinstance(obj, dict):
                            if "text" in obj and isinstance(obj["text"], str):
                                return obj["text"]
                            for v in obj.values():
                                result = find_text(v)
                                if result:
                                    return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_text(item)
                                if result:
                                    return result
                        return None
                    text = find_text(as_dict)
            except Exception:
                pass
        
        if text:
            print(f"✅ Gemini response: {text}")
            return True
        else:
            print("❌ No text response from Gemini")
            return False
            
    except Exception as e:
        print(f"❌ Gemini test failed: {str(e)}")
        if "429" in str(e) or "quota" in str(e).lower():
            print("💡 This might be a quota issue. Try again later or check your API key.")
        elif "403" in str(e) or "invalid" in str(e).lower():
            print("💡 Invalid API key. Please check your Google API key.")
        return False

def test_image_processing():
    """Test image processing with a simple test image"""
    try:
        print("\n🧪 Testing image processing...")
        
        # Create a simple test image (1x1 pixel PNG)
        test_image_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        
        from google import genai
        client = genai.Client(api_key=os.environ.get('GOOGLE_API_KEY'))
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-image-preview")
        
        # Test image processing
        base64_image = base64.b64encode(test_image_data).decode('utf-8')
        
        response = client.models.generate_content(
            model=model,
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": "Describe this image briefly."},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64_image,
                            }
                        },
                    ],
                }
            ],
        )
        
        # Extract response
        text = None
        try:
            if hasattr(response, "text"):
                text = response.text
        except Exception:
            pass
        
        if text:
            print(f"✅ Image processing response: {text}")
            return True
        else:
            print("❌ No response from image processing")
            return False
            
    except Exception as e:
        print(f"❌ Image processing test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Gemini API Integration")
    print("=" * 50)
    
    # Test 1: Basic connection
    connection_ok = test_gemini_connection()
    
    if connection_ok:
        # Test 2: Image processing
        image_ok = test_image_processing()
        
        if image_ok:
            print("\n🎉 All tests passed! Gemini API is working correctly.")
            print("Your photo restoration service should work properly.")
        else:
            print("\n⚠️  Basic connection works, but image processing failed.")
            print("This might affect photo restoration functionality.")
    else:
        print("\n❌ Gemini API connection failed.")
        print("Please check your API key and try again.")
    
    print("\n" + "=" * 50)
