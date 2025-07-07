#!/usr/bin/env python3
"""
Setup script to create or find Google Drive folders for the SEO Content System.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rag.drive.auth import GoogleDriveAuth


def main():
    """Setup Google Drive folders."""
    print("=== Google Drive Folder Setup ===\n")
    
    try:
        # Authenticate
        auth = GoogleDriveAuth()
        service = auth.get_service()
        
        # Create main folders
        print("Creating folder structure...\n")
        
        # Create "SEO Content Automation" folder in root
        main_folder_name = "SEO Content Automation"
        
        # Check if it exists
        query = f"name = '{main_folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        if files:
            main_folder_id = files[0]['id']
            print(f"✓ Found existing folder: {main_folder_name}")
            print(f"  ID: {main_folder_id}")
        else:
            # Create it
            file_metadata = {
                'name': main_folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            main_folder_id = folder['id']
            print(f"✓ Created folder: {main_folder_name}")
            print(f"  ID: {main_folder_id}")
        
        # Create subfolders
        subfolders = [
            ("Generated Articles", "For uploaded SEO articles"),
            ("Research Documents", "For documents to process"),
            ("Archive", "For older content")
        ]
        
        print("\nCreating subfolders...")
        folder_ids = {}
        
        for folder_name, description in subfolders:
            # Check if exists
            query = f"name = '{folder_name}' and '{main_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            
            if files:
                folder_id = files[0]['id']
                print(f"✓ Found: {folder_name}")
            else:
                # Create it
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [main_folder_id]
                }
                folder = service.files().create(body=file_metadata, fields='id').execute()
                folder_id = folder['id']
                print(f"✓ Created: {folder_name}")
            
            folder_ids[folder_name] = folder_id
            print(f"  ID: {folder_id}")
            print(f"  Purpose: {description}")
        
        # Display configuration updates needed
        print("\n" + "="*50)
        print("IMPORTANT: Update your .env file with these IDs:")
        print("="*50)
        print(f"\n# For uploading generated articles:")
        print(f"GOOGLE_DRIVE_UPLOAD_FOLDER_ID={folder_ids['Generated Articles']}")
        print(f"\n# For watching research documents:")
        print(f"GOOGLE_DRIVE_FOLDER_ID={folder_ids['Research Documents']}")
        print("\n" + "="*50)
        
        # Also create a convenience file
        with open("drive_folder_ids.txt", "w") as f:
            f.write(f"# Google Drive Folder IDs\n")
            f.write(f"# Created by setup_drive_folders.py\n\n")
            f.write(f"Main Folder: {main_folder_name}\n")
            f.write(f"Main Folder ID: {main_folder_id}\n\n")
            f.write(f"Generated Articles ID: {folder_ids['Generated Articles']}\n")
            f.write(f"Research Documents ID: {folder_ids['Research Documents']}\n")
            f.write(f"Archive ID: {folder_ids['Archive']}\n")
        
        print("\nFolder IDs also saved to: drive_folder_ids.txt")
        print("\n✅ Setup complete! Update your .env file with the IDs above.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())