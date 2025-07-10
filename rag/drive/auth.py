"""
Google Drive authentication module for SEO Content Automation RAG system.

This module handles OAuth 2.0 authentication with Google Drive API,
token management, and service creation.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from config import get_config

# Set up module logger
logger = logging.getLogger(__name__)

# Define the scopes needed for Google Drive access
SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",  # Read metadata
    "https://www.googleapis.com/auth/drive.readonly",  # Read files
    "https://www.googleapis.com/auth/drive.file",  # Create/modify files we create
]


class GoogleDriveAuth:
    """
    Handles Google Drive OAuth 2.0 authentication and service creation.

    This class manages the authentication flow, token persistence, and
    provides authenticated Google Drive service instances.
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ):
        """
        Initialize the Google Drive authentication handler.

        Args:
            credentials_path: Path to the OAuth 2.0 credentials JSON file.
                            Defaults to GOOGLE_DRIVE_CREDENTIALS_PATH from env.
            token_path: Path where the OAuth token will be stored.
                       Defaults to GOOGLE_DRIVE_TOKEN_PATH from env.
            scopes: List of OAuth scopes to request. Defaults to SCOPES.
        """
        # Use environment variables if paths not provided
        config = get_config()
        self.credentials_path = credentials_path or str(
            config.google_drive_credentials_path
        )
        self.token_path = token_path or str(config.google_drive_token_path)
        self.scopes = scopes or SCOPES

        # Validate credentials file exists
        if not Path(self.credentials_path).exists():
            raise FileNotFoundError(
                f"Credentials file not found at: {self.credentials_path}. "
                "Please download it from Google Cloud Console."
            )

        # Initialize credentials and service as None
        self.creds: Optional[Credentials] = None
        self.service = None

        logger.info(
            f"Initialized GoogleDriveAuth with credentials at: {self.credentials_path}"
        )

    def authenticate(self) -> Credentials:
        """
        Perform OAuth 2.0 authentication flow.

        This method will:
        1. Check for existing valid token
        2. Refresh expired token if possible
        3. Run OAuth flow if no valid token exists

        Returns:
            Authenticated credentials object

        Raises:
            RefreshError: If token refresh fails
            Exception: For other authentication errors
        """
        # Check if token file exists and load it
        if Path(self.token_path).exists():
            logger.info(f"Loading existing token from: {self.token_path}")
            try:
                self.creds = Credentials.from_authorized_user_file(
                    self.token_path, self.scopes
                )
            except Exception as e:
                logger.error(f"Error loading token: {e}")
                # Invalid token file, will need to re-authenticate
                self.creds = None

        # Check if credentials are valid
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # Try to refresh the token
                logger.info("Token expired, attempting to refresh...")
                try:
                    self.creds.refresh(Request())
                    logger.info("Token refreshed successfully")
                except RefreshError as e:
                    logger.error(f"Token refresh failed: {e}")
                    # Refresh failed, need to re-authenticate
                    self.creds = None
                except Exception as e:
                    logger.error(f"Unexpected error during token refresh: {e}")
                    self.creds = None

            # If still no valid credentials, run the OAuth flow
            if not self.creds:
                logger.info("Running OAuth 2.0 flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.scopes
                )

                # Run local server for OAuth callback
                # Port 0 means use any available port
                self.creds = flow.run_local_server(
                    port=0,
                    success_message="Authentication successful! You can close this window.",
                    open_browser=True,
                )
                logger.info("OAuth flow completed successfully")

            # Save the credentials for next time
            self._save_credentials()

        return self.creds

    def _save_credentials(self) -> None:
        """
        Save credentials to token file for future use.

        This method saves the current credentials to a JSON file
        so they can be reused in future sessions.
        """
        if self.creds:
            try:
                # Ensure directory exists
                token_dir = Path(self.token_path).parent
                token_dir.mkdir(parents=True, exist_ok=True)

                # Save credentials to file
                with open(self.token_path, "w") as token_file:
                    token_file.write(self.creds.to_json())

                logger.info(f"Saved credentials to: {self.token_path}")

                # Set appropriate permissions (read/write for owner only)
                os.chmod(self.token_path, 0o600)
            except Exception as e:
                logger.error(f"Failed to save credentials: {e}")
                # Don't raise - authentication still succeeded

    def get_service(self, service_name: str = "drive", version: str = "v3"):
        """
        Get an authenticated Google API service instance.

        Args:
            service_name: Name of the Google service (default: 'drive')
            version: API version to use (default: 'v3')

        Returns:
            Authenticated service instance

        Raises:
            HttpError: If service creation fails
        """
        # Authenticate if not already done
        if not self.creds:
            self.authenticate()

        # Build and cache the service
        if not self.service:
            try:
                self.service = build(service_name, version, credentials=self.creds)
                logger.info(f"Created {service_name} service (version {version})")
            except HttpError as e:
                logger.error(f"Failed to create service: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error creating service: {e}")
                raise

        return self.service

    def revoke_credentials(self) -> bool:
        """
        Revoke the stored credentials and delete token file.

        This method revokes the OAuth token and removes the token file,
        requiring re-authentication on next use.

        Returns:
            True if revocation successful, False otherwise
        """
        try:
            # Revoke the token if it exists
            if self.creds:
                self.creds.revoke(Request())
                logger.info("Credentials revoked successfully")

            # Delete the token file
            if Path(self.token_path).exists():
                Path(self.token_path).unlink()
                logger.info(f"Deleted token file: {self.token_path}")

            # Clear instance variables
            self.creds = None
            self.service = None

            return True

        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test the Google Drive connection by making a simple API call.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Get the service
            service = self.get_service()

            # Try to get user's Drive info
            about = service.about().get(fields="user").execute()
            user_info = about.get("user", {})

            logger.info(
                f"Successfully connected to Google Drive as: "
                f"{user_info.get('displayName', 'Unknown')} "
                f"({user_info.get('emailAddress', 'Unknown')})"
            )

            return True

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    @property
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated with valid credentials.

        Returns:
            True if authenticated with valid credentials, False otherwise
        """
        return self.creds is not None and self.creds.valid


# Convenience function for getting an authenticated service
def get_drive_service(
    credentials_path: Optional[str] = None, token_path: Optional[str] = None
):
    """
    Convenience function to get an authenticated Google Drive service.

    Args:
        credentials_path: Optional path to credentials file
        token_path: Optional path to token file

    Returns:
        Authenticated Google Drive service instance
    """
    auth = GoogleDriveAuth(credentials_path, token_path)
    return auth.get_service()
