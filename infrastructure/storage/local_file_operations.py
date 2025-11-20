"""
Local File Storage Operations

Drop-in replacement for S3Operations that uses local filesystem.
Perfect for testing Oracle Package Analyzer without AWS.

Design: Implements same interface as S3Operations but stores files locally.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class LocalFileOperations:
    """
    Local filesystem operations mirroring S3Operations interface.

    Provides identical API to S3Operations but stores everything locally.
    This allows testing workflows without AWS credentials.

    Directory structure:
        base_path/
        ├── oracle/
        │   ├── raw/              # Raw package source (.sql files)
        │   │   ├── BILLING/
        │   │   │   ├── PKG_POLICY_BILLING.sql
        │   │   │   └── PKG_CLAIMS.sql
        │   │   └── FINANCE/
        │   │       └── PKG_GL_PROCESSING.sql
        │   └── knowledge/        # Generated knowledge artifacts (.json)
        │       ├── BILLING.PKG_POLICY_BILLING.json
        │       └── FINANCE.PKG_GL_PROCESSING.json
    """

    def __init__(self, base_path: str = "./data", bucket_name: Optional[str] = None):
        """
        Initialize local file operations.

        Args:
            base_path: Root directory for all file storage (default: ./data)
            bucket_name: Ignored (kept for API compatibility with S3Operations)
        """
        self.base_path = Path(base_path).resolve()
        self.bucket = bucket_name or "local-storage"

        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """
        Convert S3-style key to local file path.

        Args:
            key: S3-style key (e.g., "oracle/raw/BILLING/PKG_POLICY_BILLING.sql")

        Returns:
            Absolute path to local file
        """
        return self.base_path / key

    def upload_file(self, local_path: str, s3_key: str) -> bool:
        """
        Copy local file to storage location.

        Args:
            local_path: Source file path
            s3_key: Destination key (relative path in storage)

        Returns:
            True if successful, False otherwise
        """
        try:
            source = Path(local_path)
            destination = self._get_file_path(s3_key)

            # Create parent directories
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            import shutil
            shutil.copy2(source, destination)

            return True
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Copy file from storage to local path.

        Args:
            s3_key: Source key in storage
            local_path: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            source = self._get_file_path(s3_key)
            destination = Path(local_path)

            # Create parent directories
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            import shutil
            shutil.copy2(source, destination)

            return True
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False

    def read_text(self, s3_key: str) -> str:
        """
        Read text file from storage.

        Args:
            s3_key: File key to read

        Returns:
            File contents as string, empty string on error
        """
        try:
            file_path = self._get_file_path(s3_key)

            if not file_path.exists():
                print(f"File not found: {file_path}")
                return ""

            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading text file: {e}")
            return ""

    def write_text(self, s3_key: str, content: str) -> bool:
        """
        Write text content to storage.

        Args:
            s3_key: Destination key
            content: Text content to write

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self._get_file_path(s3_key)

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"Error writing text file: {e}")
            return False

    def read_json(self, s3_key: str) -> Dict[str, Any]:
        """
        Read and parse JSON file from storage.

        Args:
            s3_key: File key to read

        Returns:
            Parsed JSON as dict, empty dict on error
        """
        try:
            text = self.read_text(s3_key)
            if text:
                return json.loads(text)
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return {}

    def write_json(self, s3_key: str, data: Dict[str, Any]) -> bool:
        """
        Write dict as JSON to storage.

        Args:
            s3_key: Destination key
            data: Dictionary to write as JSON

        Returns:
            True if successful, False otherwise
        """
        try:
            json_content = json.dumps(data, indent=2, ensure_ascii=False)
            return self.write_text(s3_key, json_content)
        except (TypeError, ValueError) as e:
            print(f"Error serializing JSON: {e}")
            return False

    def list_objects(self, prefix: str) -> List[str]:
        """
        List all file keys with given prefix.

        Args:
            prefix: Prefix to filter files (e.g., "oracle/raw/")

        Returns:
            List of file keys (relative paths), empty list on error
        """
        try:
            prefix_path = self._get_file_path(prefix)

            if not prefix_path.exists():
                return []

            # Recursively find all files under prefix
            files = []
            for file_path in prefix_path.rglob('*'):
                if file_path.is_file():
                    # Convert to relative path from base_path
                    relative = file_path.relative_to(self.base_path)
                    files.append(str(relative))

            return sorted(files)
        except Exception as e:
            print(f"Error listing files: {e}")
            return []

    def delete_object(self, s3_key: str) -> bool:
        """
        Delete file from storage.

        Args:
            s3_key: File key to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self._get_file_path(s3_key)

            if file_path.exists():
                file_path.unlink()

            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False

    def object_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            s3_key: File key to check

        Returns:
            True if file exists, False otherwise
        """
        file_path = self._get_file_path(s3_key)
        return file_path.exists()

    def get_storage_path(self) -> Path:
        """
        Get the absolute path to the storage directory.

        Returns:
            Absolute path to storage root
        """
        return self.base_path

    def cleanup(self):
        """
        Remove all files in storage (useful for testing).

        WARNING: This will delete all data in base_path!
        """
        import shutil
        if self.base_path.exists():
            shutil.rmtree(self.base_path)
            self.base_path.mkdir(parents=True, exist_ok=True)
