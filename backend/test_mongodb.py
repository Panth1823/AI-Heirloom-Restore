#!/usr/bin/env python3
"""
Test MongoDB connection for the Heirloom AI Photo Restoration app
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent
env_path = ROOT_DIR / '.env'
print(f"[DEBUG] Loading .env from: {env_path}")
print(f"[DEBUG] .env exists: {env_path.exists()}")

# Read and manually parse the .env file to handle BOM
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig removes BOM
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"').strip("'")
                os.environ[key] = value
                print(f"[DEBUG] Set {key} = {value[:50]}...")

async def test_mongodb_connection():
    """Test MongoDB connection"""
    try:
        # Debug: Print what's in the environment
        print(f"[DEBUG] MONGO_URL from env: {os.environ.get('MONGO_URL', 'NOT_SET')}")
        
        # Get connection details
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'heirloom_ai')
        
        print(f"[INFO] Testing MongoDB connection...")
        print(f"   URL (first 50 chars): {mongo_url[:50]}...")
        print(f"   Database: {db_name}")
        
        # Create client
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Test connection
        await client.admin.command('ping')
        print("[SUCCESS] MongoDB connection successful!")
        
        # Test database operations
        test_collection = db.test_collection
        test_doc = {"test": "connection", "timestamp": "2024-01-01"}
        
        # Insert test document
        result = await test_collection.insert_one(test_doc)
        print(f"[SUCCESS] Test document inserted with ID: {result.inserted_id}")
        
        # Find test document
        found_doc = await test_collection.find_one({"_id": result.inserted_id})
        print(f"[SUCCESS] Test document found: {found_doc}")
        
        # Clean up test document
        await test_collection.delete_one({"_id": result.inserted_id})
        print("[SUCCESS] Test document cleaned up")
        
        # Close connection
        client.close()
        print("[SUCCESS] MongoDB test completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] MongoDB connection failed: {str(e)}")
        print("\n[TROUBLESHOOTING] Tips:")
        print("1. Check if MongoDB is running (for local) or Atlas cluster is accessible")
        print("2. Verify your connection string in .env file")
        print("3. Check network connectivity")
        print("4. Ensure database user has proper permissions")
        return False

if __name__ == "__main__":
    print("[TEST] MongoDB Connection Test for Heirloom AI")
    print("=" * 50)
    
    success = asyncio.run(test_mongodb_connection())
    
    if success:
        print("\n[SUCCESS] MongoDB is ready for the Heirloom AI app!")
    else:
        print("\n[INFO] Please fix the MongoDB connection before proceeding.")
