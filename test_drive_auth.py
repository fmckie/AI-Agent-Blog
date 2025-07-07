#!/usr/bin/env python3
"""
Test script for Google Drive authentication.

Run this to verify your Google Drive setup is working correctly.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from rag.drive.auth import GoogleDriveAuth

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Test Google Drive authentication."""
    print("=== Google Drive Authentication Test ===\n")
    
    try:
        # Create auth instance
        print("1. Creating authentication instance...")
        auth = GoogleDriveAuth()
        print("   ✓ Auth instance created\n")
        
        # Authenticate
        print("2. Authenticating with Google Drive...")
        print("   (This may open a browser window for authorization)")
        auth.authenticate()
        print("   ✓ Authentication successful\n")
        
        # Test connection
        print("3. Testing connection...")
        if auth.test_connection():
            print("   ✓ Connection test passed\n")
        else:
            print("   ✗ Connection test failed\n")
            return 1
        
        # Get service and list some files
        print("4. Listing files in Drive root...")
        service = auth.get_service()
        
        # List up to 5 files
        results = service.files().list(
            pageSize=5,
            fields="files(id, name, mimeType)"
        ).execute()
        
        files = results.get('files', [])
        if files:
            print(f"   Found {len(files)} files:")
            for file in files:
                print(f"   - {file['name']} ({file['mimeType']})")
        else:
            print("   No files found (Drive might be empty)")
        
        print("\n✅ All tests passed! Google Drive integration is working correctly.")
        print(f"\nToken saved to: {auth.token_path}")
        print("You won't need to authenticate again unless the token expires.\n")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure credentials.json is in your project root.")
        print("Download it from Google Cloud Console > APIs & Services > Credentials")
        return 1
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("\nCheck the logs above for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())