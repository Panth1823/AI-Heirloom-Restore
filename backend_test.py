import requests
import sys
import time
import os
from datetime import datetime
from pathlib import Path

class HeirloomAPITester:
    def __init__(self, base_url="https://retro-renew.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.restoration_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else self.api_url
        headers = {}
        if data and not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, timeout=timeout)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {response_data}")
                    return True, response_data
                except:
                    print(f"   Response: Non-JSON response")
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test("Root API Endpoint", "GET", "", 200)

    def test_invalid_file_upload(self):
        """Test uploading invalid file type"""
        # Create a text file to test invalid file type
        test_content = "This is not an image file"
        files = {'file': ('test.txt', test_content, 'text/plain')}
        
        success, response = self.run_test(
            "Invalid File Upload", 
            "POST", 
            "upload", 
            400,  # Should return 400 for invalid file type
            files=files
        )
        return success

    def create_test_image(self):
        """Create a simple test image for upload"""
        try:
            # Create a minimal PNG image (1x1 pixel)
            png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
            return png_data
        except Exception as e:
            print(f"Failed to create test image: {e}")
            return None

    def test_photo_upload(self):
        """Test uploading a valid photo"""
        test_image = self.create_test_image()
        if not test_image:
            print("❌ Failed to create test image")
            return False

        files = {'file': ('test_photo.png', test_image, 'image/png')}
        
        success, response = self.run_test(
            "Photo Upload", 
            "POST", 
            "upload", 
            200,  # Should return 200 for successful upload
            files=files,
            timeout=60  # Longer timeout for AI processing
        )
        
        if success and 'id' in response:
            self.restoration_id = response['id']
            print(f"   Restoration ID: {self.restoration_id}")
            return True
        return False

    def test_restoration_status(self):
        """Test checking restoration status"""
        if not self.restoration_id:
            print("❌ No restoration ID available for status check")
            return False

        success, response = self.run_test(
            "Restoration Status Check",
            "GET",
            f"restoration/{self.restoration_id}",
            200
        )
        
        if success and 'status' in response:
            status = response['status']
            print(f"   Restoration Status: {status}")
            
            # If still processing, wait and check again
            if status == 'processing':
                print("   Waiting for restoration to complete...")
                time.sleep(10)  # Wait 10 seconds
                return self.test_restoration_status()  # Recursive check
            
            return True
        return False

    def test_download_restored_photo(self):
        """Test downloading the restored photo"""
        if not self.restoration_id:
            print("❌ No restoration ID available for download")
            return False

        # First check if restoration is completed
        status_success, status_response = self.run_test(
            "Pre-download Status Check",
            "GET",
            f"restoration/{self.restoration_id}",
            200
        )
        
        if not status_success or status_response.get('status') != 'completed':
            print(f"❌ Restoration not completed. Status: {status_response.get('status', 'unknown')}")
            return False

        # Test download endpoint
        url = f"{self.api_url}/download/{self.restoration_id}"
        print(f"\n🔍 Testing Download Restored Photo...")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
                print(f"   Content-Length: {len(response.content)} bytes")
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False
        finally:
            self.tests_run += 1

    def test_get_all_restorations(self):
        """Test getting all restorations"""
        return self.run_test("Get All Restorations", "GET", "restorations", 200)

    def test_nonexistent_restoration(self):
        """Test accessing non-existent restoration"""
        fake_id = "nonexistent-restoration-id"
        success, response = self.run_test(
            "Non-existent Restoration",
            "GET",
            f"restoration/{fake_id}",
            404  # Should return 404 for non-existent restoration
        )
        return success

def main():
    print("🚀 Starting Heirloom AI Photo Restoration API Tests")
    print("=" * 60)
    
    tester = HeirloomAPITester()
    
    # Test sequence
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Invalid File Upload", tester.test_invalid_file_upload),
        ("Photo Upload", tester.test_photo_upload),
        ("Restoration Status", tester.test_restoration_status),
        ("Download Restored Photo", tester.test_download_restored_photo),
        ("Get All Restorations", tester.test_get_all_restorations),
        ("Non-existent Restoration", tester.test_nonexistent_restoration),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            if not success:
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} - Unexpected error: {str(e)}")
            failed_tests.append(test_name)
    
    # Print final results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed / tester.tests_run * 100):.1f}%")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for test in failed_tests:
            print(f"   - {test}")
    else:
        print(f"\n🎉 All tests passed!")
    
    return 0 if len(failed_tests) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())