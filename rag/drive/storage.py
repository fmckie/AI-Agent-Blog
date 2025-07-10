"""
Google Drive storage handler for database operations.

This module manages all database operations related to Google Drive sync,
including tracking uploaded files, sync status, and metadata.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

from config import get_config
from rag.config import get_rag_config

# Set up module logger
logger = logging.getLogger(__name__)


class DriveStorageHandler:
    """
    Handles database operations for Google Drive integration.

    This class manages:
    - Tracking uploaded articles and their Drive URLs
    - Sync status for files
    - Drive document metadata
    - Error tracking and recovery
    """

    def __init__(self, client: Optional[Client] = None):
        """
        Initialize the Drive storage handler.

        Args:
            client: Optional Supabase client instance
        """
        # Get configurations
        self.config = get_config()
        self.rag_config = get_rag_config()

        # Use provided client or create new one
        if client:
            self.client = client
        else:
            # Create Supabase client
            options = ClientOptions(auto_refresh_token=True, persist_session=True)
            self.client = create_client(
                self.rag_config.supabase_url,
                self.rag_config.supabase_service_key,
                options=options,
            )

        logger.info("Initialized DriveStorageHandler")

    def track_upload(
        self, article_id: UUID, drive_file_id: str, drive_url: str, folder_path: str
    ) -> bool:
        """
        Track a successful article upload to Google Drive.

        Args:
            article_id: ID of the generated article
            drive_file_id: Google Drive file ID
            drive_url: Web view link to the Drive document
            folder_path: Folder path in Drive (e.g., "2025/01/07")

        Returns:
            True if tracking successful, False otherwise
        """
        try:
            # Update the generated_articles table
            result = (
                self.client.table("generated_articles")
                .update(
                    {
                        "drive_file_id": drive_file_id,
                        "drive_url": drive_url,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .eq("id", str(article_id))
                .execute()
            )

            if result.data:
                logger.info(f"Tracked upload for article {article_id} to Drive")

                # Also create/update sync status
                self._update_sync_status(
                    file_id=drive_file_id,
                    local_path=f"article_{article_id}",
                    drive_url=drive_url,
                    status="synced",
                )

                return True
            else:
                logger.error(f"Failed to track upload for article {article_id}")
                return False

        except Exception as e:
            logger.error(f"Error tracking upload: {e}")
            return False

    def track_drive_document(
        self,
        file_id: str,
        file_name: str,
        mime_type: str,
        drive_url: str,
        folder_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[UUID]:
        """
        Track a document from Google Drive for RAG processing.

        Args:
            file_id: Google Drive file ID
            file_name: Name of the file
            mime_type: MIME type of the file
            drive_url: Web view link
            folder_path: Path in Drive
            metadata: Optional additional metadata

        Returns:
            Document ID if successful, None otherwise
        """
        try:
            # Prepare document data
            doc_data = {
                "source": file_name,
                "source_type": "drive",
                "drive_file_id": file_id,
                "metadata": json.dumps(
                    {
                        "mime_type": mime_type,
                        "folder_path": folder_path,
                        "drive_url": drive_url,
                        **(metadata or {}),
                    }
                ),
            }

            # Insert into research_documents
            result = self.client.table("research_documents").insert(doc_data).execute()

            if result.data and len(result.data) > 0:
                doc_id = result.data[0]["id"]
                logger.info(f"Tracked Drive document {file_name} with ID {doc_id}")

                # Update sync status
                self._update_sync_status(
                    file_id=file_id,
                    local_path=f"drive_doc_{doc_id}",
                    drive_url=drive_url,
                    status="processed",
                )

                return UUID(doc_id)
            else:
                logger.error(f"Failed to track Drive document {file_name}")
                return None

        except Exception as e:
            logger.error(f"Error tracking Drive document: {e}")
            return None

    def get_uploaded_articles(
        self, limit: int = 50, offset: int = 0, include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get list of articles uploaded to Google Drive.

        Args:
            limit: Maximum number of results
            offset: Pagination offset
            include_metadata: Whether to include full metadata

        Returns:
            List of uploaded articles with Drive information
        """
        try:
            # Query generated_articles with Drive info
            query = self.client.table("generated_articles").select(
                "id, title, keyword, drive_file_id, drive_url, updated_at, created_at"
            )

            # Filter only uploaded articles
            query = query.not_.is_("drive_file_id", "null")

            # Apply pagination
            query = query.order("updated_at", desc=True).limit(limit).offset(offset)

            result = query.execute()

            articles = result.data if result.data else []

            # Add metadata if requested
            if include_metadata and articles:
                for article in articles:
                    if article.get("drive_file_id"):
                        sync_status = self.get_sync_status(article["drive_file_id"])
                        if sync_status:
                            article["sync_status"] = sync_status

            return articles

        except Exception as e:
            logger.error(f"Error getting uploaded articles: {e}")
            return []

    def get_sync_status(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get sync status for a specific Drive file.

        Args:
            file_id: Google Drive file ID

        Returns:
            Sync status information or None
        """
        try:
            result = (
                self.client.table("drive_sync_status")
                .select("*")
                .eq("file_id", file_id)
                .single()
                .execute()
            )

            return result.data if result.data else None

        except Exception as e:
            logger.debug(f"No sync status found for {file_id}: {e}")
            return None

    def _update_sync_status(
        self,
        file_id: str,
        local_path: str,
        drive_url: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update or create sync status for a file.

        Args:
            file_id: Google Drive file ID
            local_path: Local reference path
            drive_url: Drive web URL
            status: Sync status (synced, pending, error, etc.)
            error_message: Optional error message

        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare sync data
            sync_data = {
                "file_id": file_id,
                "local_path": local_path,
                "drive_url": drive_url,
                "sync_status": status,
                "last_synced": datetime.now(timezone.utc).isoformat(),
                "error_message": error_message,
            }

            # Try to update existing record
            result = (
                self.client.table("drive_sync_status")
                .upsert(sync_data, on_conflict="file_id")
                .execute()
            )

            return bool(result.data)

        except Exception as e:
            logger.error(f"Error updating sync status: {e}")
            return False

    def get_pending_uploads(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get articles pending upload to Google Drive.

        Args:
            limit: Maximum number of pending articles to return

        Returns:
            List of articles that haven't been uploaded yet
        """
        try:
            # Get articles without Drive file ID
            result = (
                self.client.table("generated_articles")
                .select("id, title, keyword, file_path, created_at")
                .is_("drive_file_id", "null")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Error getting pending uploads: {e}")
            return []

    def mark_upload_error(self, article_id: UUID, error_message: str) -> bool:
        """
        Mark an article upload as failed with error details.

        Args:
            article_id: ID of the article that failed to upload
            error_message: Error description

        Returns:
            True if marked successfully, False otherwise
        """
        try:
            # Create error sync status
            self._update_sync_status(
                file_id=f"error_{article_id}",
                local_path=f"article_{article_id}",
                drive_url="",
                status="error",
                error_message=error_message,
            )

            return True

        except Exception as e:
            logger.error(f"Error marking upload failure: {e}")
            return False

    def get_drive_documents(
        self, source_type: str = "drive", limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get documents ingested from Google Drive.

        Args:
            source_type: Type of source to filter (default: "drive")
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of Drive documents with metadata
        """
        try:
            result = (
                self.client.table("research_documents")
                .select("id, source, drive_file_id, created_at, metadata")
                .eq("source_type", source_type)
                .not_.is_("drive_file_id", "null")
                .order("created_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )

            documents = result.data if result.data else []

            # Parse metadata JSON
            for doc in documents:
                if doc.get("metadata") and isinstance(doc["metadata"], str):
                    try:
                        doc["metadata"] = json.loads(doc["metadata"])
                    except:
                        doc["metadata"] = {}

            return documents

        except Exception as e:
            logger.error(f"Error getting Drive documents: {e}")
            return []

    def cleanup_orphaned_sync_records(
        self, dry_run: bool = True
    ) -> Tuple[int, List[str]]:
        """
        Clean up sync records that no longer have corresponding articles or documents.

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            Tuple of (count of records to delete, list of file IDs)
        """
        try:
            # Get all sync records
            sync_result = (
                self.client.table("drive_sync_status")
                .select("file_id, local_path")
                .execute()
            )
            sync_records = sync_result.data if sync_result.data else []

            orphaned = []

            for record in sync_records:
                file_id = record["file_id"]
                local_path = record["local_path"]

                # Check if it's an article reference
                if local_path.startswith("article_"):
                    article_id = local_path.replace("article_", "").replace(
                        "error_", ""
                    )
                    # Check if article exists
                    article_result = (
                        self.client.table("generated_articles")
                        .select("id")
                        .eq("id", article_id)
                        .execute()
                    )

                    if not article_result.data:
                        orphaned.append(file_id)

                # Check if it's a document reference
                elif local_path.startswith("drive_doc_"):
                    doc_id = local_path.replace("drive_doc_", "")
                    # Check if document exists
                    doc_result = (
                        self.client.table("research_documents")
                        .select("id")
                        .eq("id", doc_id)
                        .execute()
                    )

                    if not doc_result.data:
                        orphaned.append(file_id)

            # Delete orphaned records if not dry run
            if orphaned and not dry_run:
                for file_id in orphaned:
                    self.client.table("drive_sync_status").delete().eq(
                        "file_id", file_id
                    ).execute()
                logger.info(f"Deleted {len(orphaned)} orphaned sync records")

            return len(orphaned), orphaned

        except Exception as e:
            logger.error(f"Error cleaning up orphaned sync records: {e}")
            return 0, []
