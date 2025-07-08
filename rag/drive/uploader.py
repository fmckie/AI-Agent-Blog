"""
Google Drive article uploader for SEO Content Automation RAG system.

This module handles uploading generated HTML articles to Google Drive,
converting them to Google Docs format, and organizing them in folders.
"""

import os
import json
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime
from io import BytesIO

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload
from google.auth.exceptions import RefreshError

from config import get_config
from .auth import GoogleDriveAuth

# Set up module logger
logger = logging.getLogger(__name__)

# MIME type mappings
MIME_TYPES = {
    '.html': 'text/html',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

# Google Docs MIME type for conversion
GOOGLE_DOCS_MIME = 'application/vnd.google-apps.document'


class ArticleUploader:
    """
    Handles uploading articles to Google Drive with folder organization.
    
    This class manages:
    - Converting HTML to Google Docs
    - Creating folder structures
    - Uploading with metadata
    - Version tracking
    """
    
    def __init__(
        self,
        auth: Optional[GoogleDriveAuth] = None,
        upload_folder_id: Optional[str] = None
    ):
        """
        Initialize the article uploader.
        
        Args:
            auth: GoogleDriveAuth instance. If None, creates new one.
            upload_folder_id: Target folder ID for uploads.
                            Defaults to GOOGLE_DRIVE_UPLOAD_FOLDER_ID from env.
        """
        # Get config
        config = get_config()
        
        # Initialize auth if not provided
        self.auth = auth or GoogleDriveAuth()
        
        # Get Drive service
        self.service = self.auth.get_service()
        
        # Set upload folder ID
        self.upload_folder_id = upload_folder_id or config.google_drive_upload_folder_id
        
        # Cache for folder IDs to avoid repeated lookups
        self._folder_cache: Dict[str, str] = {}
        
        logger.info(f"Initialized ArticleUploader with folder ID: {self.upload_folder_id}")
    
    def upload_html_as_doc(
        self,
        html_content: str,
        title: str,
        metadata: Optional[Dict[str, Any]] = None,
        folder_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload HTML content as a Google Doc.
        
        Args:
            html_content: HTML content to upload
            title: Document title (will be filename)
            metadata: Optional metadata to attach as properties
            folder_path: Optional subfolder path (e.g., "2025/01/07")
                        If None, uploads to root upload folder
        
        Returns:
            Dictionary with upload details including file ID and web link
            
        Raises:
            HttpError: If upload fails
        """
        try:
            # Determine target folder
            if folder_path:
                parent_folder_id = self._ensure_folder_path(folder_path)
            else:
                parent_folder_id = self.upload_folder_id
            
            # Prepare file metadata
            file_metadata = {
                'name': title,
                'mimeType': GOOGLE_DOCS_MIME,  # Convert to Google Doc
            }
            
            # Add parent folder if specified
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            # Add custom properties if provided
            if metadata:
                file_metadata['properties'] = self._prepare_metadata(metadata)
            
            # Create media upload from HTML content
            media = MediaIoBaseUpload(
                BytesIO(html_content.encode('utf-8')),
                mimetype='text/html',
                resumable=True
            )
            
            # Upload the file
            logger.info(f"Uploading '{title}' to Google Drive...")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, createdTime, parents'
            ).execute()
            
            logger.info(f"Successfully uploaded '{title}' with ID: {file['id']}")
            
            # Add additional info to response
            result = {
                'file_id': file['id'],
                'name': file['name'],
                'web_link': file.get('webViewLink', ''),
                'created_time': file.get('createdTime', ''),
                'parent_folder': parent_folder_id,
                'folder_path': folder_path or 'root'
            }
            
            return result
            
        except HttpError as e:
            logger.error(f"Failed to upload '{title}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading '{title}': {e}")
            raise
    
    def upload_file(
        self,
        file_path: Path,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        folder_path: Optional[str] = None,
        convert_to_docs: bool = True
    ) -> Dict[str, Any]:
        """
        Upload a file from disk to Google Drive.
        
        Args:
            file_path: Path to the file to upload
            title: Optional custom title (defaults to filename)
            metadata: Optional metadata to attach
            folder_path: Optional subfolder path
            convert_to_docs: Whether to convert compatible files to Google Docs
        
        Returns:
            Dictionary with upload details
            
        Raises:
            FileNotFoundError: If file doesn't exist
            HttpError: If upload fails
        """
        # Validate file exists
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine title
        title = title or file_path.name
        
        # Determine MIME type
        mime_type = MIME_TYPES.get(file_path.suffix.lower(), 'application/octet-stream')
        
        # Determine target folder
        if folder_path:
            parent_folder_id = self._ensure_folder_path(folder_path)
        else:
            parent_folder_id = self.upload_folder_id
        
        # Prepare file metadata
        file_metadata = {
            'name': title,
        }
        
        # Add parent folder if specified
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
        
        # Add custom properties if provided
        if metadata:
            file_metadata['properties'] = self._prepare_metadata(metadata)
        
        # Determine if we should convert to Google Docs
        if convert_to_docs and mime_type in ['text/html', 'text/plain', 'text/markdown']:
            file_metadata['mimeType'] = GOOGLE_DOCS_MIME
        
        # Create media upload
        media = MediaFileUpload(
            str(file_path),
            mimetype=mime_type,
            resumable=True
        )
        
        try:
            # Upload the file
            logger.info(f"Uploading '{title}' from {file_path}...")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, createdTime, parents'
            ).execute()
            
            logger.info(f"Successfully uploaded '{title}' with ID: {file['id']}")
            
            # Return result
            return {
                'file_id': file['id'],
                'name': file['name'],
                'web_link': file.get('webViewLink', ''),
                'created_time': file.get('createdTime', ''),
                'parent_folder': parent_folder_id,
                'folder_path': folder_path or 'root',
                'original_path': str(file_path)
            }
            
        except HttpError as e:
            logger.error(f"Failed to upload '{title}': {e}")
            raise
    
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Parent folder ID (None for root)
        
        Returns:
            ID of the created folder
            
        Raises:
            HttpError: If folder creation fails
        """
        # Check cache first
        cache_key = f"{parent_id or 'root'}/{folder_name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]
        
        # Check if folder already exists
        existing_id = self._find_folder(folder_name, parent_id)
        if existing_id:
            self._folder_cache[cache_key] = existing_id
            return existing_id
        
        # Create folder metadata
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        # Add parent if specified
        if parent_id:
            file_metadata['parents'] = [parent_id]
        elif self.upload_folder_id:
            # Use upload folder as default parent
            file_metadata['parents'] = [self.upload_folder_id]
        
        try:
            # Create the folder
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder['id']
            logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
            
            # Cache the result
            self._folder_cache[cache_key] = folder_id
            
            return folder_id
            
        except HttpError as e:
            logger.error(f"Failed to create folder '{folder_name}': {e}")
            raise
    
    def _ensure_folder_path(self, folder_path: str) -> str:
        """
        Ensure a folder path exists, creating folders as needed.
        
        Args:
            folder_path: Path like "2025/01/07" or "Research/Papers"
        
        Returns:
            ID of the final folder in the path
        """
        # Split path into components
        parts = folder_path.strip('/').split('/')
        
        # Start from upload folder or root
        current_parent = self.upload_folder_id
        
        # Create each folder in the path
        for part in parts:
            if part:  # Skip empty parts
                current_parent = self.create_folder(part, current_parent)
        
        return current_parent
    
    def _find_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Find a folder by name in a parent folder.
        
        Args:
            folder_name: Name of the folder to find
            parent_id: Parent folder ID to search in
        
        Returns:
            Folder ID if found, None otherwise
        """
        try:
            # Build query
            query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
            
            # Add parent constraint
            if parent_id:
                query += f" and '{parent_id}' in parents"
            elif self.upload_folder_id:
                query += f" and '{self.upload_folder_id}' in parents"
            
            # Add trashed check
            query += " and trashed = false"
            
            # Search for the folder
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                pageSize=1
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]['id']
            
            return None
            
        except HttpError as e:
            logger.error(f"Error searching for folder '{folder_name}': {e}")
            return None
    
    def _prepare_metadata(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Prepare metadata for Google Drive properties.
        
        Google Drive properties must be strings, so we convert values.
        
        Args:
            metadata: Dictionary of metadata
        
        Returns:
            Dictionary with string values suitable for Drive properties
        """
        properties = {}
        
        for key, value in metadata.items():
            # Convert values to strings
            if isinstance(value, (list, dict)):
                properties[key] = json.dumps(value)
            elif isinstance(value, bool):
                properties[key] = str(value).lower()
            elif value is not None:
                properties[key] = str(value)
        
        return properties
    
    def update_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata/properties for an existing file.
        
        Args:
            file_id: ID of the file to update
            metadata: Metadata to add/update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare properties
            properties = self._prepare_metadata(metadata)
            
            # Update the file
            self.service.files().update(
                fileId=file_id,
                body={'properties': properties}
            ).execute()
            
            logger.info(f"Updated metadata for file {file_id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to update metadata for {file_id}: {e}")
            return False
    
    def get_upload_folder_structure(self) -> Dict[str, Any]:
        """
        Get the folder structure under the upload folder.
        
        Returns:
            Dictionary representing the folder tree
        """
        if not self.upload_folder_id:
            logger.warning("No upload folder ID configured")
            return {}
        
        try:
            return self._get_folder_tree(self.upload_folder_id)
        except Exception as e:
            logger.error(f"Failed to get folder structure: {e}")
            return {}
    
    def _get_folder_tree(self, folder_id: str, level: int = 0, max_level: int = 3) -> Dict[str, Any]:
        """
        Recursively get folder structure.
        
        Args:
            folder_id: Starting folder ID
            level: Current recursion level
            max_level: Maximum recursion depth
        
        Returns:
            Dictionary with folder structure
        """
        if level > max_level:
            return {}
        
        try:
            # Get folder info
            folder = self.service.files().get(
                fileId=folder_id,
                fields='id, name'
            ).execute()
            
            # Get subfolders
            query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            subfolders = results.get('files', [])
            
            # Build tree
            tree = {
                'id': folder['id'],
                'name': folder['name'],
                'folders': {}
            }
            
            # Recursively get subfolders
            for subfolder in subfolders:
                tree['folders'][subfolder['name']] = self._get_folder_tree(
                    subfolder['id'], 
                    level + 1, 
                    max_level
                )
            
            return tree
            
        except Exception as e:
            logger.error(f"Error getting folder tree: {e}")
            return {}


class BatchUploader(ArticleUploader):
    """
    Batch uploader for processing multiple articles efficiently.
    
    Extends ArticleUploader with batch processing capabilities,
    retry logic, and queue management.
    """
    
    def __init__(
        self,
        auth: Optional[GoogleDriveAuth] = None,
        upload_folder_id: Optional[str] = None,
        drive_config: Optional['DriveConfig'] = None
    ):
        """
        Initialize batch uploader with configuration.
        
        Args:
            auth: GoogleDriveAuth instance (creates new one if not provided)
            upload_folder_id: Google Drive folder ID for uploads
            drive_config: Drive configuration (uses default if not provided)
        """
        super().__init__(auth, upload_folder_id)
        
        # Import here to avoid circular imports
        from .config import get_drive_config
        
        # Get configuration
        self.drive_config = drive_config or get_drive_config()
        
        # Upload statistics
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "skipped": 0
        }
        
        # Failed uploads for retry
        self.failed_uploads: List[Dict[str, Any]] = []
    
    async def upload_pending_articles(
        self,
        articles: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Upload multiple pending articles with progress tracking.
        
        Args:
            articles: List of article dictionaries with required fields
            progress_callback: Optional callback(current, total, message)
        
        Returns:
            Dictionary with upload statistics and results
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        self.stats = {
            "total": len(articles),
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "skipped": 0
        }
        
        results = []
        
        # Process in batches
        batch_size = self.drive_config.batch_size
        concurrent_limit = self.drive_config.concurrent_uploads
        
        # Create thread pool for concurrent uploads
        with ThreadPoolExecutor(max_workers=concurrent_limit) as executor:
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]
                
                # Process batch concurrently
                futures = []
                for article in batch:
                    future = executor.submit(self._upload_article_with_retry, article)
                    futures.append((article, future))
                
                # Wait for batch to complete
                for article, future in futures:
                    try:
                        result = future.result(timeout=self.drive_config.upload_timeout)
                        results.append(result)
                        
                        if result["success"]:
                            self.stats["successful"] += 1
                        else:
                            # Only count as failed if not skipped
                            error_msg = result.get("error", "")
                            if "Missing file_path" not in error_msg and "File not found" not in error_msg:
                                self.stats["failed"] += 1
                                self.failed_uploads.append(article)
                        
                        # Progress callback
                        if progress_callback:
                            current = i + len(results) % batch_size
                            progress_callback(
                                current,
                                self.stats["total"],
                                f"Uploaded: {article.get('title', 'Unknown')[:50]}..."
                            )
                    
                    except Exception as e:
                        logger.error(f"Upload failed for article {article.get('id')}: {e}")
                        self.stats["failed"] += 1
                        self.failed_uploads.append(article)
                        results.append({
                            "article_id": article.get("id"),
                            "success": False,
                            "error": str(e)
                        })
                
                # Small delay between batches to avoid rate limiting
                if i + batch_size < len(articles):
                    await asyncio.sleep(1)
        
        return {
            "stats": self.stats,
            "results": results,
            "failed_articles": self.failed_uploads
        }
    
    def _upload_article_with_retry(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload a single article with retry logic.
        
        Args:
            article: Article dictionary with required fields
        
        Returns:
            Result dictionary with upload status
        """
        import time
        
        article_id = article.get("id")
        max_retries = self.drive_config.max_retries
        retry_delay = self.drive_config.retry_delay
        
        for attempt in range(max_retries + 1):
            try:
                # Check if article has required fields
                if not article.get("file_path"):
                    logger.warning(f"Article {article_id} missing file_path, skipping")
                    self.stats["skipped"] += 1
                    return {
                        "article_id": article_id,
                        "success": False,
                        "error": "Missing file_path"
                    }
                
                # Read HTML content
                file_path = Path(article["file_path"])
                if not file_path.exists():
                    logger.warning(f"File not found: {file_path}")
                    self.stats["skipped"] += 1
                    return {
                        "article_id": article_id,
                        "success": False,
                        "error": f"File not found: {file_path}"
                    }
                
                html_content = file_path.read_text(encoding='utf-8')
                
                # Prepare metadata
                metadata = {
                    "article_id": str(article_id),
                    "keyword": article.get("keyword", ""),
                    "generation_timestamp": article.get("created_at", ""),
                    "local_path": str(file_path)
                }
                
                # Upload to Drive
                result = self.upload_html_as_doc(
                    html_content=html_content,
                    title=article.get("title", file_path.stem),
                    metadata=metadata
                )
                
                # Update statistics
                if attempt > 0:
                    self.stats["retried"] += 1
                
                logger.info(f"Successfully uploaded article {article_id} to Drive")
                
                return {
                    "article_id": article_id,
                    "success": True,
                    "drive_file_id": result["file_id"],
                    "drive_url": result["web_link"],
                    "folder_path": result["folder_path"],
                    "attempts": attempt + 1
                }
            
            except Exception as e:
                logger.error(f"Upload attempt {attempt + 1} failed for {article_id}: {e}")
                
                # If not the last attempt, wait with exponential backoff
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # Final failure
                    return {
                        "article_id": article_id,
                        "success": False,
                        "error": str(e),
                        "attempts": attempt + 1
                    }
    
    def retry_failed_uploads(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Retry previously failed uploads.
        
        Args:
            progress_callback: Optional progress callback
        
        Returns:
            Dictionary with retry results
        """
        if not self.failed_uploads:
            logger.info("No failed uploads to retry")
            return {
                "stats": {"total": 0, "successful": 0, "failed": 0},
                "results": []
            }
        
        logger.info(f"Retrying {len(self.failed_uploads)} failed uploads")
        
        # Clear failed list and retry
        articles_to_retry = self.failed_uploads.copy()
        self.failed_uploads.clear()
        
        # Use asyncio.run() to handle the async method
        import asyncio
        return asyncio.run(self.upload_pending_articles(articles_to_retry, progress_callback))
    
    def get_upload_stats(self) -> Dict[str, int]:
        """
        Get current upload statistics.
        
        Returns:
            Dictionary with upload statistics
        """
        return self.stats.copy()
    
    def clear_stats(self) -> None:
        """Reset upload statistics."""
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "retried": 0,
            "skipped": 0
        }
        self.failed_uploads.clear()