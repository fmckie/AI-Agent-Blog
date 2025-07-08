"""
Test suite for Google Drive configuration module.

Tests DriveConfig validation, loading, saving, and integration.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open
import pytest
from pydantic import ValidationError

# Disable .env loading for tests
os.environ["DISABLE_DOTENV"] = "true"

# Clear any existing Google Drive env vars that might interfere
for key in list(os.environ.keys()):
    if key.startswith("GOOGLE_DRIVE_"):
        del os.environ[key]

from rag.drive.config import (
    DriveConfig, 
    load_drive_config, 
    save_drive_config,
    get_drive_config,
    set_drive_config
)


class TestDriveConfig:
    """Test DriveConfig model validation and defaults."""
    
    def test_default_configuration(self):
        """Test DriveConfig with default values."""
        config = DriveConfig()
        
        # Check defaults
        assert config.auto_upload is True
        assert config.folder_structure == "YYYY/MM/DD"
        assert config.default_folder_id is None
        assert config.create_folders is True
        assert config.batch_size == 10
        assert config.max_retries == 3
        assert config.retry_delay == 60
        assert config.concurrent_uploads == 3
        assert config.log_failures is True
        assert config.notify_on_error is False
        assert config.quarantine_after_retries == 5
        assert len(config.supported_mime_types) > 0
        assert "text/html" in config.supported_mime_types
        assert config.sync_interval == 300
        assert config.requests_per_minute == 60
        assert config.upload_timeout == 300
    
    def test_custom_configuration(self):
        """Test DriveConfig with custom values."""
        config = DriveConfig(
            auto_upload=False,
            batch_size=20,
            max_retries=5,
            retry_delay=120,
            concurrent_uploads=5,
            folder_structure="YYYY/keyword",
            custom_properties={"project": "seo", "version": "1.0"}
        )
        
        assert config.auto_upload is False
        assert config.batch_size == 20
        assert config.max_retries == 5
        assert config.retry_delay == 120
        assert config.concurrent_uploads == 5
        assert config.folder_structure == "YYYY/keyword"
        assert config.custom_properties["project"] == "seo"
        assert config.custom_properties["version"] == "1.0"
    
    def test_batch_size_validation(self):
        """Test batch_size constraints."""
        # Valid range
        config = DriveConfig(batch_size=50)
        assert config.batch_size == 50
        
        # Too small
        with pytest.raises(ValidationError) as exc_info:
            DriveConfig(batch_size=0)
        assert "greater than or equal to 1" in str(exc_info.value)
        
        # Too large
        with pytest.raises(ValidationError) as exc_info:
            DriveConfig(batch_size=101)
        assert "less than or equal to 100" in str(exc_info.value)
    
    def test_retry_delay_validation(self):
        """Test retry_delay validation."""
        # Valid delay
        config = DriveConfig(retry_delay=300)
        assert config.retry_delay == 300
        
        # Too long (more than 1 hour)
        with pytest.raises(ValidationError) as exc_info:
            DriveConfig(retry_delay=3601)
        assert "should not exceed 1 hour" in str(exc_info.value)
    
    def test_folder_structure_validation(self):
        """Test folder structure pattern validation."""
        # Valid patterns
        valid_patterns = [
            "YYYY/MM/DD",
            "YYYY/MM",
            "keyword/YYYY-MM",
            "title/YYYY",
            "Projects/YYYY/MM/DD",
            "SEO-Articles/keyword"
        ]
        
        for pattern in valid_patterns:
            config = DriveConfig(folder_structure=pattern)
            assert config.folder_structure == pattern
        
        # Invalid patterns
        invalid_patterns = [
            "folder@with@invalid",  # Invalid @ character
            "test!folder",  # Invalid ! character
            "path/with spaces and @/test"  # Multiple invalid chars
        ]
        
        for pattern in invalid_patterns:
            with pytest.raises(ValidationError):
                DriveConfig(folder_structure=pattern)
    
    def test_mime_type_configuration(self):
        """Test MIME type configuration."""
        config = DriveConfig()
        
        # Check default supported types
        assert "text/html" in config.supported_mime_types
        assert "application/pdf" in config.supported_mime_types
        assert "text/markdown" in config.supported_mime_types
        
        # Check export mappings
        assert config.export_mime_types["text/html"] == "application/vnd.google-apps.document"
        assert config.export_mime_types["text/plain"] == "application/vnd.google-apps.document"
        assert config.export_mime_types["application/pdf"] == "application/pdf"
    
    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "GOOGLE_DRIVE_AUTO_UPLOAD": "false",
            "GOOGLE_DRIVE_BATCH_SIZE": "25",
            "GOOGLE_DRIVE_MAX_RETRIES": "5",
            "GOOGLE_DRIVE_SYNC_INTERVAL": "600",
            "GOOGLE_DRIVE_FOLDER_STRUCTURE": "YYYY/keyword"
        }
        
        with patch.dict(os.environ, env_vars):
            config = DriveConfig()
            
            assert config.auto_upload is False
            assert config.batch_size == 25
            assert config.max_retries == 5
            assert config.sync_interval == 600
            assert config.folder_structure == "YYYY/keyword"
    
    def test_json_encoding(self):
        """Test JSON serialization of configuration."""
        config = DriveConfig(
            custom_properties={"test": "value"},
            supported_mime_types=["text/html", "text/plain"]
        )
        
        # Convert to dict
        config_dict = config.dict()
        
        # Ensure it's JSON serializable
        json_str = json.dumps(config_dict)
        assert isinstance(json_str, str)
        
        # Load back and verify
        loaded_dict = json.loads(json_str)
        assert loaded_dict["custom_properties"]["test"] == "value"
        assert "text/html" in loaded_dict["supported_mime_types"]


class TestDriveConfigIO:
    """Test configuration loading and saving."""
    
    def test_load_drive_config_from_file(self, tmp_path):
        """Test loading configuration from JSON file."""
        # Create test config file
        config_data = {
            "auto_upload": False,
            "batch_size": 15,
            "folder_structure": "keyword/YYYY",
            "custom_properties": {"env": "test"}
        }
        
        config_path = tmp_path / "drive_config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        # Load configuration
        config = load_drive_config(config_path)
        
        # Verify values
        assert config.auto_upload is False
        assert config.batch_size == 15
        assert config.folder_structure == "keyword/YYYY"
        assert config.custom_properties["env"] == "test"
    
    def test_load_drive_config_nonexistent_file(self):
        """Test loading when config file doesn't exist."""
        config = load_drive_config(Path("nonexistent.json"))
        
        # Should return default configuration
        assert config.auto_upload is True  # Default value
        assert config.batch_size == 10  # Default value
    
    def test_save_drive_config(self, tmp_path):
        """Test saving configuration to JSON file."""
        # Create configuration
        config = DriveConfig(
            auto_upload=False,
            batch_size=20,
            folder_structure="YYYY/title",
            custom_properties={"saved": "true"}
        )
        
        # Save to file
        config_path = tmp_path / "saved_config.json"
        save_drive_config(config, config_path)
        
        # Verify file exists and content
        assert config_path.exists()
        
        with open(config_path, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["auto_upload"] is False
        assert saved_data["batch_size"] == 20
        assert saved_data["folder_structure"] == "YYYY/title"
        assert saved_data["custom_properties"]["saved"] == "true"
    
    def test_save_drive_config_creates_directory(self, tmp_path):
        """Test saving creates parent directory if needed."""
        config = DriveConfig()
        
        # Save to nested path
        config_path = tmp_path / "nested" / "dir" / "config.json"
        save_drive_config(config, config_path)
        
        # Verify directory structure created
        assert config_path.exists()
        assert config_path.parent.exists()


class TestDriveConfigSingleton:
    """Test singleton configuration management."""
    
    def test_get_drive_config_default(self):
        """Test getting default configuration."""
        # Clear any existing config
        set_drive_config(None)
        
        # Get config
        config = get_drive_config()
        
        # Should return default values
        assert isinstance(config, DriveConfig)
        assert config.auto_upload is True
        assert config.batch_size == 10
    
    def test_get_drive_config_loads_from_file(self, tmp_path):
        """Test automatic loading from default location."""
        # Create config in default location
        config_data = {"batch_size": 30, "auto_upload": False}
        
        default_path = Path("drive_config.json")
        
        # Mock file operations
        with patch("pathlib.Path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps(config_data))), \
             patch("rag.drive.config._default_config", None):
            
            config = get_drive_config()
            
            assert config.batch_size == 30
            assert config.auto_upload is False
    
    def test_set_drive_config(self):
        """Test setting custom configuration."""
        # Create custom config
        custom_config = DriveConfig(
            batch_size=40,
            retry_delay=180,
            folder_structure="custom/YYYY"
        )
        
        # Set as default
        set_drive_config(custom_config)
        
        # Get and verify
        config = get_drive_config()
        assert config.batch_size == 40
        assert config.retry_delay == 180
        assert config.folder_structure == "custom/YYYY"
        
        # Same instance returned
        assert config is custom_config


class TestDriveConfigIntegration:
    """Test integration with other components."""
    
    def test_config_with_main_config(self):
        """Test DriveConfig works with main Config."""
        from config import Config
        
        # Create main config
        with patch.dict(os.environ, {
            "TAVILY_API_KEY": "test_tavily_key_that_is_long_enough",
            "OPENAI_API_KEY": "test_openai_key_that_is_long_enough"
        }):
            main_config = Config()
            drive_base = main_config.get_drive_base_config()
            
            # Verify drive base config
            assert "credentials_path" in drive_base
            assert "token_path" in drive_base
            assert "folder_id" in drive_base
            assert "upload_folder_id" in drive_base
            assert "sync_interval" in drive_base
    
    def test_config_validation_errors(self):
        """Test comprehensive validation error messages."""
        # Test multiple validation errors
        with pytest.raises(ValidationError) as exc_info:
            DriveConfig(
                batch_size=200,  # Too large
                max_retries=20,  # Too large
                retry_delay=7200,  # Too long
                concurrent_uploads=100,  # Too large
                sync_interval=30,  # Too short
                requests_per_minute=2000  # Too large
            )
        
        error_str = str(exc_info.value)
        assert "batch_size" in error_str
        assert "max_retries" in error_str
        assert "retry_delay" in error_str