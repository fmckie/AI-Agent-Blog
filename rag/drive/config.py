"""
Google Drive configuration management for the RAG system.

This module handles all Drive-specific configuration including MIME types,
export formats, sync intervals, and retry settings.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DriveConfig(BaseSettings):
    """Configuration for Google Drive integration."""

    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_DRIVE_",
        case_sensitive=False,
        env_file=".env" if os.getenv("DISABLE_DOTENV") != "true" else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Upload settings
    auto_upload: bool = Field(
        default=True, description="Automatically upload articles after generation"
    )
    folder_structure: str = Field(
        default="YYYY/MM/DD",
        description="Folder structure pattern for organizing uploads",
    )
    default_folder_id: Optional[str] = Field(
        default=None, description="Default Google Drive folder ID for uploads"
    )
    create_folders: bool = Field(
        default=True, description="Create folders if they don't exist"
    )

    # Batch settings
    batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of articles to upload in a single batch",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts for failed uploads",
    )
    retry_delay: int = Field(
        default=60, ge=1, description="Initial delay in seconds between retry attempts"
    )
    concurrent_uploads: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of concurrent upload operations",
    )

    # Error handling
    log_failures: bool = Field(
        default=True, description="Log upload failures to database"
    )
    notify_on_error: bool = Field(
        default=False, description="Send notifications on upload errors"
    )
    quarantine_after_retries: int = Field(
        default=5,
        ge=1,
        description="Quarantine articles after this many total retry attempts",
    )

    # Supported MIME types
    supported_mime_types: List[str] = Field(
        default=[
            "text/html",
            "text/plain",
            "application/pdf",
            "application/vnd.google-apps.document",
            "application/vnd.google-apps.spreadsheet",
            "application/vnd.google-apps.presentation",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/markdown",
        ],
        description="MIME types supported for upload and processing",
    )

    # Export MIME type mappings
    export_mime_types: Dict[str, str] = Field(
        default={
            "text/html": "application/vnd.google-apps.document",
            "text/plain": "application/vnd.google-apps.document",
            "text/markdown": "application/vnd.google-apps.document",
            "application/pdf": "application/pdf",
            "application/msword": "application/vnd.google-apps.document",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "application/vnd.google-apps.document",
        },
        description="Mapping of source MIME types to Google Drive export types",
    )

    # Sync settings
    sync_interval: int = Field(
        default=300,  # 5 minutes
        ge=60,
        description="Interval in seconds between sync operations",
    )
    watch_folder_id: Optional[str] = Field(
        default=None, description="Google Drive folder ID to watch for new documents"
    )

    # Metadata settings
    include_keywords: bool = Field(
        default=True, description="Include keywords in document metadata"
    )
    include_sources: bool = Field(
        default=True, description="Include source URLs in document metadata"
    )
    include_generation_time: bool = Field(
        default=True, description="Include generation timestamp in metadata"
    )
    custom_properties: Dict[str, str] = Field(
        default={}, description="Additional custom properties to add to uploaded files"
    )

    # Rate limiting
    requests_per_minute: int = Field(
        default=60, ge=1, le=1000, description="Maximum API requests per minute"
    )
    upload_timeout: int = Field(
        default=300,  # 5 minutes
        ge=30,
        description="Timeout in seconds for upload operations",
    )

    @validator("folder_structure")
    def validate_folder_structure(cls, v):
        """Validate folder structure pattern."""
        valid_patterns = ["YYYY", "MM", "DD", "keyword", "title"]
        parts = v.split("/")
        for part in parts:
            # Check if part contains only valid patterns
            if part and not any(pattern in part for pattern in valid_patterns):
                # Allow literal strings (not patterns)
                if not all(c.isalnum() or c in "-_" for c in part):
                    raise ValueError(
                        f"Invalid folder structure pattern: {part}. "
                        f"Use combinations of: {', '.join(valid_patterns)}"
                    )
        return v

    @validator("retry_delay")
    def validate_retry_delay(cls, v):
        """Ensure retry delay is reasonable."""
        if v > 3600:  # 1 hour
            raise ValueError("Retry delay should not exceed 1 hour (3600 seconds)")
        return v


def load_drive_config(config_path: Optional[Path] = None) -> DriveConfig:
    """
    Load Drive configuration from file or environment.

    Args:
        config_path: Optional path to configuration JSON file

    Returns:
        DriveConfig: Loaded configuration object
    """
    if config_path and config_path.exists():
        with open(config_path, "r") as f:
            config_data = json.load(f)
        return DriveConfig(**config_data)

    # Load from environment variables
    return DriveConfig()


def save_drive_config(config: DriveConfig, config_path: Path) -> None:
    """
    Save Drive configuration to JSON file.

    Args:
        config: Configuration object to save
        config_path: Path to save configuration to
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(config.dict(exclude_unset=True), f, indent=2, default=str)


# Default configuration instance
_default_config: Optional[DriveConfig] = None


def get_drive_config() -> DriveConfig:
    """
    Get the default Drive configuration instance.

    Returns:
        DriveConfig: Default configuration
    """
    global _default_config
    if _default_config is None:
        # Try to load from default location
        default_path = Path("drive_config.json")
        if default_path.exists():
            _default_config = load_drive_config(default_path)
        else:
            _default_config = DriveConfig()

    return _default_config


def set_drive_config(config: DriveConfig) -> None:
    """
    Set the default Drive configuration instance.

    Args:
        config: Configuration to set as default
    """
    global _default_config
    _default_config = config
